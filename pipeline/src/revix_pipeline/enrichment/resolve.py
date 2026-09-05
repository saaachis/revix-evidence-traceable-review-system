"""Entity resolution: which vehicle is this listing actually about?

A hybrid rule-and-model system, and it is stronger than pure similarity
because automobile specifications behave as hard constraints. A petrol
listing is never a diesel variant, whatever the text says. Eliminating
candidates deterministically before any scoring is what lets this reach
high precision cheaply.

    1. Block      by manufacturer and model
    2. Constrain  fuel and transmission must agree, engine size must be close
    3. Score      trigram similarity on the normalised trim code
    4. Decide     accept above the floor, otherwise leave it for a person

Step 4 is the part that matters. Anything below the confidence floor is left
unresolved and shows up in the adjudication queue, rather than being guessed
at and quietly polluting a score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import FuelType, MatchMethod, Transmission
from revix_core.models import (
    EvidenceUnit,
    SourceListing,
    VehicleModel,
    VehicleVariant,
    utcnow,
)
from revix_pipeline.catalogue import normalise_trim

#: Above this we accept the match. Below it the pair waits for a person.
#: Set high on purpose: a wrong match pollutes every number downstream, and an
#: unresolved listing costs only coverage.
ACCEPT_THRESHOLD = 0.82

#: Engine displacement rarely matches exactly across sources, because some
#: quote 1497 and others 1.5. Ten percent covers rounding without letting a
#: 1.2 match a 1.5.
ENGINE_TOLERANCE = 0.10

FUEL_TOKENS: dict[FuelType, tuple[str, ...]] = {
    FuelType.DIESEL: ("diesel", "crdi", "tdi", "dci", "multijet"),
    FuelType.PETROL: ("petrol", "tsi", "vtvt", "mpfi", "turbo petrol"),
    FuelType.CNG: ("cng", "s-cng"),
    FuelType.HYBRID: ("hybrid", "e-cvt", "strong hybrid"),
    FuelType.ELECTRIC: ("electric", "ev", "kwh"),
}

TRANSMISSION_TOKENS: dict[Transmission, tuple[str, ...]] = {
    Transmission.MT: ("mt", "manual", "5mt", "6mt"),
    Transmission.AT: ("at", "automatic", "torque converter"),
    Transmission.AMT: ("amt", "ags"),
    Transmission.CVT: ("cvt", "e-cvt"),
    Transmission.DCT: ("dct", "dsg", "dca", "dual clutch", "dct"),
    Transmission.IVT: ("ivt",),
}


@dataclass(slots=True)
class MatchCandidate:
    variant_id: str
    score: float
    method: MatchMethod


def _detect(text: str, tokens: dict[object, tuple[str, ...]]) -> set[object]:
    lowered = f" {text.casefold()} "
    found = set()
    for key, words in tokens.items():
        for word in words:
            if re.search(rf"[\s\-/(]{re.escape(word)}[\s\-/),.]", lowered):
                found.add(key)
                break
    return found


def detect_fuel(text: str) -> set[FuelType]:
    return _detect(text, FUEL_TOKENS)  # type: ignore[arg-type,return-value]


def detect_transmission(text: str) -> set[Transmission]:
    return _detect(text, TRANSMISSION_TOKENS)  # type: ignore[arg-type,return-value]


def detect_engine_cc(text: str) -> int | None:
    """Read a displacement, whether written as 1497 or 1.5."""
    if m := re.search(r"\b(\d{3,4})\s*cc\b", text, re.I):
        return int(m.group(1))
    if m := re.search(r"\b(\d)\.(\d)\b", text):
        return int(f"{m.group(1)}{m.group(2)}00")
    if m := re.search(r"\b(\d{3,4})\b", text):
        value = int(m.group(1))
        if 50 <= value <= 6000:
            return value
    return None


def satisfies_hard_constraints(listing_text: str, variant: VehicleVariant) -> bool:
    """The deterministic filter. This is what makes the matching precise."""
    fuels = detect_fuel(listing_text)
    if fuels and variant.fuel_type not in fuels:
        return False

    gearboxes = detect_transmission(listing_text)
    if gearboxes and variant.transmission not in gearboxes:
        return False

    cc = detect_engine_cc(listing_text)
    if cc and variant.engine_cc:
        tolerance = variant.engine_cc * ENGINE_TOLERANCE
        if abs(cc - variant.engine_cc) > tolerance:
            return False

    return True


def trim_residual(listing_text: str, variant: VehicleVariant) -> str:
    """The listing title with the make and model removed.

    The model name has already done its work during blocking. Leaving it in
    the string being scored just adds tokens both sides share, which inflates
    every candidate equally and makes them harder to tell apart.
    """
    text = listing_text
    for noise in (variant.model.manufacturer.name, variant.model.name):
        text = re.sub(re.escape(noise), " ", text, flags=re.I)
    return normalise_trim(text)


def score_trim(listing_text: str, variant: VehicleVariant) -> float:
    """Similarity on normalised trim codes, 0 to 1."""
    left = trim_residual(listing_text, variant)
    right = variant.trim_code
    # rapidfuzz tokenises on whitespace, so the hyphens that make a trim code
    # readable have to come back out before comparing, or the whole code is
    # treated as one token and token_set_ratio degrades to a plain ratio.
    left_tokens = left.replace("-", " ")
    right_tokens = right.replace("-", " ")
    # token_set, because sources reorder the parts of a trim name freely:
    # "SX (O) 1.5 Diesel AT" and "1.5 Diesel SX Optional AT" are the same car.
    return fuzz.token_set_ratio(left_tokens, right_tokens) / 100.0


def candidates_for(session: Session, listing: SourceListing) -> list[MatchCandidate]:
    """Block, constrain, then score whatever survives."""
    title = listing.raw_title
    hint = (listing.raw_specs or {}).get("model_hint") or ""

    # 1. Blocking. Only variants whose model name appears in the title are
    #    even considered, which removes almost everything before any scoring.
    stmt = select(VehicleVariant).join(VehicleVariant.model)
    blocked: list[VehicleVariant] = []
    lowered = title.casefold()
    for variant in session.scalars(stmt):
        model: VehicleModel = variant.model
        if model.name.casefold() in lowered or (hint and hint.casefold() == model.name.casefold()):
            blocked.append(variant)

    # 2. Hard constraints, then 3. scoring on the survivors.
    results: list[MatchCandidate] = []
    for variant in blocked:
        if not satisfies_hard_constraints(title, variant):
            continue
        score = score_trim(title, variant)
        method = MatchMethod.SPEC_CONSTRAINT if score >= 0.99 else MatchMethod.TRIGRAM
        results.append(MatchCandidate(str(variant.id), round(score, 3), method))

    results.sort(key=lambda c: c.score, reverse=True)
    return results


def resolve_listings(session: Session, *, threshold: float = ACCEPT_THRESHOLD) -> dict[str, int]:
    """Resolve every unresolved listing, then propagate to its evidence units."""
    stats = {"considered": 0, "resolved": 0, "ambiguous": 0, "no_candidate": 0, "units_linked": 0}

    unresolved = session.scalars(
        select(SourceListing).where(SourceListing.variant_id.is_(None))
    ).all()

    for listing in unresolved:
        stats["considered"] += 1
        candidates = candidates_for(session, listing)
        if not candidates:
            stats["no_candidate"] += 1
            continue

        best = candidates[0]
        runner_up = candidates[1].score if len(candidates) > 1 else 0.0
        # A clear winner is required, not just a high score. Two variants both
        # scoring 0.95 means we cannot tell them apart, which is exactly the
        # case that must go to a person rather than to a coin flip.
        if best.score < threshold or (best.score - runner_up) < 0.02:
            stats["ambiguous"] += 1
            continue

        listing.variant_id = best.variant_id  # type: ignore[assignment]
        listing.match_method = best.method.value
        listing.match_confidence = best.score
        listing.resolved_at = utcnow()
        stats["resolved"] += 1

    session.flush()

    # Propagate. Every unit from a resolved listing inherits its variant.
    linked = session.execute(
        select(EvidenceUnit, SourceListing.variant_id)
        .join(SourceListing, EvidenceUnit.source_listing_id == SourceListing.id)
        .where(EvidenceUnit.variant_id.is_(None), SourceListing.variant_id.is_not(None))
    ).all()
    for unit, variant_id in linked:
        unit.variant_id = variant_id
        stats["units_linked"] += 1

    session.flush()
    return stats
