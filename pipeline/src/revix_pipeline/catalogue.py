"""Loading the seeded catalogue, and normalising trim codes.

`normalise_trim` is small but it is load-bearing. It is the first thing
entity resolution reaches for, and it is what turns the many ways a source
can spell a variant into one comparable key:

    "SX (O) 1.5 Diesel AT"           -> sx-o-1-5-diesel-at
    "1.5 CRDi SX Optional Automatic" -> 1-5-crdi-sx-optional-automatic

The synonym pass then collapses the second onto the first.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import FuelType, Transmission, VehicleClass
from revix_core.models import Manufacturer, VehicleModel, VehicleVariant

SEED_PATH = Path("data/seed/catalogue.json")

#: Different sources spell the same trim differently. Collapsing these before
#: any similarity scoring is what lets matching stay precise without a model.
#: Longest keys first, so "sx optional" wins over "optional".
TRIM_SYNONYMS: tuple[tuple[str, str], ...] = (
    ("sx optional", "sx-o"),
    ("sx opt", "sx-o"),
    ("sx (o)", "sx-o"),
    ("sxo", "sx-o"),
    ("automatic", "at"),
    ("manual", "mt"),
    ("dual clutch", "dct"),
    ("dsg", "dct"),
    ("dca", "dct"),
    ("crdi", "diesel"),
    ("tdi", "diesel"),
    ("tsi", "petrol"),
    ("dual channel", "dual-channel"),
    ("single channel", "single-channel"),
)


def normalise_trim(raw: str) -> str:
    """Lower-case, expand synonyms, strip punctuation, hyphen-join."""
    text = raw.casefold().strip()
    for pattern, replacement in TRIM_SYNONYMS:
        text = text.replace(pattern, replacement)
    # Decimals matter: 1.5 and 1.2 are different engines, so keep the digits
    # but flatten the separator so "1.5" and "1-5" compare equal.
    text = re.sub(r"(\d)[.,](\d)", r"\1-\2", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def load_seed(path: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((path or SEED_PATH).read_text(encoding="utf-8"))
    return payload


def seed_catalogue(session: Session, path: Path | None = None) -> dict[str, int]:
    """Load manufacturers, models and variants. Idempotent on slug and trim."""
    data = load_seed(path)
    counts = {"manufacturers": 0, "models": 0, "variants": 0}

    by_slug = {m.slug: m for m in session.scalars(select(Manufacturer))}
    for spec in data["manufacturers"]:
        if spec["slug"] in by_slug:
            continue
        mfr = Manufacturer(slug=spec["slug"], name=spec["name"], country=spec.get("country"))
        session.add(mfr)
        by_slug[spec["slug"]] = mfr
        counts["manufacturers"] += 1
    session.flush()

    models_by_slug = {m.slug: m for m in session.scalars(select(VehicleModel))}
    variants_seen = {
        (v.model_id, v.trim_code, v.fuel_type, v.transmission)
        for v in session.scalars(select(VehicleVariant))
    }

    for spec in data["models"]:
        model = models_by_slug.get(spec["slug"])
        if model is None:
            model = VehicleModel(
                manufacturer_id=by_slug[spec["manufacturer"]].id,
                slug=spec["slug"],
                name=spec["name"],
                vehicle_class=VehicleClass(spec["vehicle_class"]),
                body_style=spec.get("body_style"),
                segment=spec.get("segment"),
                launch_year=spec.get("launch_year"),
            )
            session.add(model)
            session.flush()
            models_by_slug[spec["slug"]] = model
            counts["models"] += 1

        for vspec in spec["variants"]:
            trim = normalise_trim(vspec["variant_name"])
            fuel = FuelType(vspec["fuel_type"])
            gearbox = Transmission(vspec["transmission"])
            if (model.id, trim, fuel, gearbox) in variants_seen:
                continue
            session.add(
                VehicleVariant(
                    model_id=model.id,
                    variant_name=vspec["variant_name"],
                    trim_code=trim,
                    fuel_type=fuel,
                    transmission=gearbox,
                    engine_cc=vspec.get("engine_cc"),
                    engine_power_bhp=vspec.get("engine_power_bhp"),
                    arai_mileage_kmpl=vspec.get("arai_mileage_kmpl"),
                    seating_capacity=vspec.get("seating_capacity"),
                    boot_litres=vspec.get("boot_litres"),
                    kerb_weight_kg=vspec.get("kerb_weight_kg"),
                    seat_height_mm=vspec.get("seat_height_mm"),
                    braking_type=vspec.get("braking_type"),
                    ex_showroom_price_min=vspec.get("price_min"),
                    ex_showroom_price_max=vspec.get("price_max"),
                    spec_completeness=_completeness(vspec),
                    spec_source_refs={"seed": str(path or SEED_PATH)},
                )
            )
            variants_seen.add((model.id, trim, fuel, gearbox))
            counts["variants"] += 1

    return counts


_SPEC_FIELDS = (
    "engine_cc",
    "engine_power_bhp",
    "arai_mileage_kmpl",
    "price_min",
    "seating_capacity",
    "boot_litres",
    "kerb_weight_kg",
    "seat_height_mm",
    "braking_type",
)


def _completeness(spec: dict[str, Any]) -> float:
    """How much of the specification sheet we actually hold, 0 to 1.

    Cars and two-wheelers have different applicable fields, so this is scored
    against whichever subset is present rather than against all of them.
    """
    present = sum(1 for f in _SPEC_FIELDS if spec.get(f) is not None)
    # Six fields is a full sheet for either class; the other three are
    # class-specific and only one class can have them.
    return round(min(present / 6.0, 1.0), 2)
