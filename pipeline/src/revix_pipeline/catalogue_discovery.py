"""Building the catalogue from what the sources publish about themselves.

The seeded catalogue was hand-written, which was fine for sixteen models and
does not scale to the hundred-odd variants section 25 asks for. Typing specs
by hand does not scale either, and worse, a hand-typed spec is a spec somebody
half-remembered: an ARAI figure that is out by two, a variant that was
discontinued last year.

So the specs come from the same place the reviews do. CarDekho publishes a
schema.org ProductGroup on each model's price page listing every variant, and
each variant's own page carries a Car object with fuel, gearbox, displacement,
ARAI mileage, seating and boot volume. That is markup published for machines,
under the same permission we already read reviews under.

Two-wheelers are thinner. BikeDekho publishes the ProductGroup with names and
prices but no specs on the variant pages, so displacement is read from the
name, which two-wheelers put there reliably ("Activa 125", "Classic 350",
"Apache RTR 160"), and fuel and gearbox come from the curated body style: an
Indian scooter has a CVT and a geared motorcycle has a manual box. Electric
two-wheelers are excluded from the candidate list rather than guessed at.

Run occasionally and by hand, never in the nightly. A catalogue that changes
under a running pipeline is a catalogue nobody can reason about.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from revix_pipeline.connectors.politeness import PoliteClient
from revix_pipeline.connectors.schema_org import _LD_JSON
from revix_pipeline.enrichment.resolve import detect_engine_cc, detect_transmission

CAR_HOST = "https://www.cardekho.com"
BIKE_HOST = "https://www.bikedekho.com"

#: Same rate as the review connectors. This runs rarely, so there is no reason
#: to be in more of a hurry than usual.
RATE_LIMIT_RPM = 10

#: "Price in India is ₹10.91 Lakh" on cars, "price in India is ₹59,477" on
#: two-wheelers, which are cheap enough to quote in rupees. The offer object
#: alongside carries the ON-ROAD price instead, and mixing ex-showroom with
#: on-road across one catalogue would make every price comparison quietly
#: wrong, so the description is the field we read.
_EX_SHOWROOM = re.compile(r"is\s*₹\s*([\d.,]+)\s*(Lakh|Crore)?", re.IGNORECASE)

#: A bare figure below this is not a vehicle price, it is a decimal somebody
#: wrote without a unit. Refusing it stops "₹10.91" becoming eleven rupees.
_MIN_BARE_PRICE = 1000

_FUEL_WORDS = {
    "petrol": "petrol",
    "diesel": "diesel",
    "cng": "cng",
    "electric": "electric",
    "hybrid": "hybrid",
    "petrol/hybrid": "hybrid",
    "strong hybrid": "hybrid",
}


@dataclass(slots=True)
class DiscoveredVariant:
    """One variant, as the source describes it."""

    variant_name: str
    fuel_type: str
    transmission: str
    price_min: int | None = None
    engine_cc: int | None = None
    engine_power_bhp: float | None = None
    arai_mileage_kmpl: float | None = None
    seating_capacity: int | None = None
    boot_litres: int | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "variant_name": self.variant_name,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
        }
        for key in (
            "engine_cc",
            "engine_power_bhp",
            "arai_mileage_kmpl",
            "seating_capacity",
            "boot_litres",
        ):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.price_min is not None:
            out["price_min"] = self.price_min
            out["price_max"] = self.price_min
        return out


@dataclass(slots=True)
class Candidate:
    """A model we want in the catalogue, and where to find it."""

    manufacturer: str
    name: str
    slug: str
    vehicle_class: str
    body_style: str
    segment: str
    launch_year: int
    source_make: str
    source_model: str
    variants: int = 4
    notes: str = ""
    discovered: list[DiscoveredVariant] = field(default_factory=list)


def _json_ld(html: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for block in _LD_JSON.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict):
                found.append(item)
    return found


def _ex_showroom(description: str) -> int | None:
    match = _EX_SHOWROOM.search(description or "")
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "").casefold()
    if unit == "crore":
        return int(amount * 10_000_000)
    if unit == "lakh":
        return int(amount * 100_000)
    # No unit, so the figure is already in rupees. Guarded, because a decimal
    # with the unit missing would otherwise become a two-digit price.
    return int(amount) if amount >= _MIN_BARE_PRICE else None


def _described(entry: dict[str, Any]) -> str:
    """CarDekho capitalises the key, BikeDekho does not."""
    return str(entry.get("Description") or entry.get("description") or "")


def _first(value: Any) -> Any:
    """These fields arrive as one-element lists about half the time."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def product_group(html: str) -> dict[str, Any] | None:
    for item in _json_ld(html):
        if item.get("@type") == "ProductGroup":
            return item
    return None


def car_specs(html: str) -> dict[str, Any]:
    """Fuel, gearbox, displacement, ARAI mileage, seating and boot."""
    out: dict[str, Any] = {}
    for item in _json_ld(html):
        if item.get("@type") not in ("Car", "Vehicle", "Product"):
            continue
        engine = _first(item.get("vehicleEngine")) or {}
        if isinstance(engine, dict):
            fuel = str(engine.get("fuelType") or "").strip().casefold()
            if fuel in _FUEL_WORDS:
                out["fuel_type"] = _FUEL_WORDS[fuel]
            if (cc := _number(engine.get("name"))) is not None:
                out["engine_cc"] = int(cc)
        gearbox = _first(item.get("vehicleTransmission"))
        if gearbox:
            out["gearbox_word"] = str(gearbox).strip().casefold()
        if (mileage := _number(_first(item.get("fuelEfficiency")) or {})) is None:
            economy = _first(item.get("fuelEfficiency"))
            if isinstance(economy, dict):
                mileage = _number(economy.get("name"))
        if mileage is not None:
            out["arai_mileage_kmpl"] = round(mileage, 2)
        if (seats := _number(item.get("vehicleSeatingCapacity"))) is not None:
            out["seating_capacity"] = int(seats)
        if (boot := _number(_first(item.get("cargoVolume")))) is not None:
            out["boot_litres"] = int(boot)
        if out:
            break
    return out


def transmission_of(variant_name: str, gearbox_word: str | None) -> str:
    """The name first, the site's own word second.

    CarDekho only ever says "Manual" or "Automatic", which collapses AMT, CVT,
    DCT and a torque converter into one bucket. The variant name usually says
    which, and a Creta DCT and a Creta CVT are different cars to drive, so the
    finer answer wins where there is one.
    """
    detected = detect_transmission(variant_name)
    if detected:
        return next(iter(detected)).value
    word = (gearbox_word or "").casefold()
    if "manual" in word:
        return "mt"
    if "automatic" in word or "auto" in word:
        return "at"
    return "mt"


def sample_variants(variants: list[dict[str, Any]], wanted: int) -> list[dict[str, Any]]:
    """A spread across the price ladder rather than the cheapest N.

    A catalogue of base trims would make every verdict a verdict about base
    trims. Evenly spaced by price keeps the entry car, the one most people buy
    and the loaded one, which is the range a reader is actually choosing in.
    """
    priced = [v for v in variants if v.get("_price") is not None]
    if not priced:
        # A source that stops publishing prices should cost us the price
        # ordering, not the whole model. Returning nothing here is how nine
        # two-wheelers silently vanished from a discovery run.
        return variants[:wanted]
    priced.sort(key=lambda v: v["_price"])
    if len(priced) <= wanted:
        return priced
    step = (len(priced) - 1) / (wanted - 1) if wanted > 1 else 1
    picked: list[dict[str, Any]] = []
    seen: set[int] = set()
    for i in range(wanted):
        index = min(len(priced) - 1, round(i * step))
        if index not in seen:
            seen.add(index)
            picked.append(priced[index])
    return picked


def discover(candidate: Candidate, client: PoliteClient) -> list[DiscoveredVariant]:
    """Every variant we want for one model, with whatever specs exist."""
    host = BIKE_HOST if candidate.vehicle_class == "two_wheeler" else CAR_HOST
    listing = client.get(f"{host}/{candidate.source_make}/{candidate.source_model}/price-in-india")
    if listing.status_code != 200:
        return []
    group = product_group(listing.text)
    if not group:
        return []

    raw = []
    for entry in group.get("hasVariant") or []:
        if not isinstance(entry, dict):
            continue
        entry["_price"] = _ex_showroom(_described(entry))
        raw.append(entry)

    out: list[DiscoveredVariant] = []
    for entry in sample_variants(raw, candidate.variants):
        name = _clean_name(str(entry.get("name") or ""), candidate)
        if not name:
            continue
        if candidate.vehicle_class == "two_wheeler":
            out.append(_bike_variant(name, entry, candidate))
            continue
        specs: dict[str, Any] = {}
        url = str(entry.get("url") or "")
        if url:
            page = client.get(url)
            if page.status_code == 200:
                specs = car_specs(page.text)
        out.append(
            DiscoveredVariant(
                variant_name=name,
                fuel_type=str(specs.get("fuel_type") or "petrol"),
                transmission=transmission_of(name, specs.get("gearbox_word")),
                price_min=entry.get("_price"),
                engine_cc=specs.get("engine_cc"),
                arai_mileage_kmpl=specs.get("arai_mileage_kmpl"),
                seating_capacity=specs.get("seating_capacity"),
                boot_litres=specs.get("boot_litres"),
            )
        )
    return out


def _bike_variant(name: str, entry: dict[str, Any], candidate: Candidate) -> DiscoveredVariant:
    """A two-wheeler, where the source publishes no specs at all.

    Displacement comes from the name, which two-wheelers state reliably.
    Fuel and gearbox come from the curated body style: an Indian scooter has a
    CVT and a geared motorcycle has a manual box. Electric two-wheelers are
    kept out of the candidate list rather than guessed at, which is why petrol
    is safe to assume here and would not be otherwise.
    """
    scooter = candidate.body_style.casefold() == "scooter"
    return DiscoveredVariant(
        variant_name=name,
        fuel_type="petrol",
        transmission="cvt" if scooter else "mt",
        price_min=entry.get("_price"),
        engine_cc=detect_engine_cc(f"{candidate.name} {name}"),
    )


def _clean_name(raw: str, candidate: Candidate) -> str:
    """ "Hyundai Creta SX (O)" becomes "SX (O)".

    Leading words are dropped while they belong to the manufacturer or the
    model, rather than matching the full names as prefixes. The source writes
    the brand its own way, so "TVS Motor" appears as "TVS" and "Suzuki
    Motorcycle" as "Suzuki", and a whole-string prefix match left those rows
    reading "TVS NTORQ 125 Disc" while Royal Enfield's came out clean.

    Repeating the make and model inside every variant name makes a table read
    like a stutter, and it inflates the trim residual the resolver scores on.
    """
    words = raw.strip().split()
    noise = {
        w.casefold().strip("()")
        for part in (candidate.manufacturer, candidate.name)
        for w in part.split()
    }
    while words and words[0].casefold().strip("()") in noise:
        words.pop(0)
    cleaned = " ".join(words).strip()
    # Everything was noise, which happens when a variant is named exactly like
    # its model. Keep the original rather than emit an empty name.
    return cleaned or raw.strip()
