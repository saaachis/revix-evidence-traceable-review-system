"""How much should this review count?

Credibility is not one number per review. It is a short vector across topic
groups, because the same person is a good witness to one thing and a poor
witness to another. An owner at 500 km can tell you about the showroom and
can tell you nothing about whether the clutch survives 60,000 km. At 60,000
km it is exactly the reverse.

Indian review platforms record ownership duration and kilometres driven and
then throw that information away by averaging everything equally. This module
is where we use it, and it is the part of the system that is only possible
because the domain is automobiles.

    weight = source_prior x (1 - spam) x reliability x aspect_fit
             x recency x launch_window

The five terms other than aspect_fit are ordinary. aspect_fit is the one that
makes the argument.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import ASPECT_GROUPS, AspectGroup, AspectKey
from revix_core.models import EvidenceUnit

#: Reviews written in the first weeks of ownership are systematically kinder,
#: because the people who write them have just chosen to buy the thing. This
#: is the launch-window correction from proposal section 15.2.
LAUNCH_WINDOW_DAYS = 90
LAUNCH_WINDOW_PENALTY = 0.7

#: How quickly an opinion stops describing the current car. Eighteen months.
RECENCY_HALF_LIFE_DAYS = 540


@dataclass(slots=True)
class Credibility:
    """The stored credibility vector for one evidence unit."""

    base: float
    durability: float
    immediate: float
    service: float
    efficiency: float
    #: The same figure with every metadata signal removed, so section 18.1's
    #: required ablation is a lookup rather than a second scoring pass. If the
    #: textual and behavioural features carry no weight on their own, this is
    #: the number that shows it.
    base_textual: float = 0.0

    def for_aspect(self, aspect: AspectKey) -> float:
        group = ASPECT_GROUPS[aspect]
        return {
            AspectGroup.DURABILITY: self.durability,
            AspectGroup.IMMEDIATE: self.immediate,
            AspectGroup.SERVICE: self.service,
            AspectGroup.EFFICIENCY: self.efficiency,
        }[group]

    def as_json(self) -> dict[str, object]:
        return {
            "base": self.base,
            "base_textual": self.base_textual,
            "by_aspect_group": {
                "durability": self.durability,
                "immediate": self.immediate,
                "service": self.service,
                "efficiency": self.efficiency,
            },
        }


# ---------------------------------------------------------------------------
# spam
# ---------------------------------------------------------------------------

#: Until the supervised classifier is trained, this is a transparent proxy.
#: It is not a filter. A high score down-weights a review; it never deletes it.
GENERIC_PHRASES: tuple[str, ...] = (
    "best car in segment",
    "value for money",
    "fully satisfied",
    "must buy",
    "everyone should buy",
    "superb car",
    "nice car",
    "good car",
    "worth every penny",
)


def spam_probability(unit: EvidenceUnit) -> float:
    """A transparent proxy, replaced by the trained classifier later.

    The features are the ones the literature says matter, in a form anyone can
    read: very short text, no specifics, superlative density, and a rating at
    the extreme with nothing said to justify it.
    """
    text = unit.text.strip()
    lowered = text.casefold()
    score = 0.0

    words = len(text.split())
    if words < 15:
        score += 0.35
    elif words < 30:
        score += 0.15

    generic_hits = sum(1 for phrase in GENERIC_PHRASES if phrase in lowered)
    score += min(0.3, generic_hits * 0.15)

    # Specifics are the strongest honest signal. A number, a unit, a duration.
    has_numbers = bool(re.search(r"\d", text))
    has_units = bool(re.search(r"\b(km|kmpl|months?|years?|service|rs\.?|lakh)\b", lowered))
    if not has_numbers:
        score += 0.15
    if not has_units:
        score += 0.10

    # A perfect score with nothing said to earn it.
    if unit.rating_normalized is not None and float(unit.rating_normalized) >= 0.99 and words < 40:
        score += 0.20

    if unit.is_verified_owner:
        score -= 0.20

    return round(max(0.0, min(1.0, score)), 3)


# ---------------------------------------------------------------------------
# reliability and aspect fit
# ---------------------------------------------------------------------------


def reliability(unit: EvidenceUnit, *, use_metadata: bool = True) -> float:
    """Behavioural and textual signals, independent of topic.

    `use_metadata=False` drops the platform's verified-owner flag and leaves
    only what can be read from the writing itself. That is the ablation
    section 18.1 demands, and it is a parameter rather than a separate
    function so the two can never drift apart.
    """
    score = 0.4
    if use_metadata and unit.is_verified_owner:
        score += 0.25

    words = len(unit.text.split())
    # Detail helps, up to a point. A 2,000 word essay is not eight times more
    # trustworthy than a 250 word one.
    score += min(0.20, math.log1p(words) / 30.0)

    if unit.helpful_votes and unit.total_votes:
        ratio = unit.helpful_votes / max(1, unit.total_votes)
        score += 0.15 * min(1.0, ratio * 2)

    if re.search(r"\d", unit.text):
        score += 0.05

    return round(max(0.05, min(1.0, score)), 3)


def aspect_fit(unit: EvidenceUnit, group: AspectGroup) -> float:
    """Is this person a good witness to THIS kind of question?

    The whole argument of the project sits in this function.
    """
    months = unit.ownership_duration_months
    km = unit.km_driven

    if months is None and km is None:
        # No metadata. Neutral rather than penalised: absence of evidence
        # about the witness is not evidence they are a bad one.
        return 0.6

    months = months or 0
    km = km or 0

    if group is AspectGroup.DURABILITY:
        # Long-term reliability, build, drivetrain wear. Needs time and distance.
        by_time = min(1.0, months / 36.0)
        by_distance = min(1.0, km / 40000.0)
        return round(0.15 + 0.85 * max(by_time, by_distance), 3)

    if group is AspectGroup.IMMEDIATE:
        # Ride, comfort, features, showroom. Known on day one, and a very long
        # ownership does not make the first impression more accurate.
        return round(1.0 if months <= 12 else max(0.55, 1.0 - (months - 12) / 96.0), 3)

    if group is AspectGroup.SERVICE:
        # Needs to have actually been to a service centre. Roughly one visit
        # per year or per 10,000 km.
        visits = max(months / 12.0, km / 10000.0)
        return round(0.10 + 0.90 * min(1.0, visits / 3.0), 3)

    # EFFICIENCY: a few tanks of fuel is enough, so this saturates early.
    return round(0.20 + 0.80 * min(1.0, km / 5000.0), 3)


def recency_decay(unit: EvidenceUnit, *, half_life_days: int = RECENCY_HALF_LIFE_DAYS) -> float:
    if unit.published_at is None:
        return 0.7
    published = unit.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    age_days = max(0.0, (datetime.now(UTC) - published).days)
    return round(float(0.5 ** (age_days / half_life_days)), 3)


def launch_window_correction(unit: EvidenceUnit) -> float:
    """Down-weight the honeymoon.

    We do not know a vehicle's launch date per review, but we do know how long
    this person has owned it, and a review written in the first weeks is the
    same bias by another route.
    """
    months = unit.ownership_duration_months
    if months is None:
        return 1.0
    return LAUNCH_WINDOW_PENALTY if months * 30 < LAUNCH_WINDOW_DAYS else 1.0


def compute_credibility(unit: EvidenceUnit) -> Credibility:
    spam = spam_probability(unit)
    base = round(reliability(unit) * (1.0 - spam), 3)
    return Credibility(
        base=base,
        base_textual=round(reliability(unit, use_metadata=False) * (1.0 - spam), 3),
        durability=round(base * aspect_fit(unit, AspectGroup.DURABILITY), 3),
        immediate=round(base * aspect_fit(unit, AspectGroup.IMMEDIATE), 3),
        service=round(base * aspect_fit(unit, AspectGroup.SERVICE), 3),
        efficiency=round(base * aspect_fit(unit, AspectGroup.EFFICIENCY), 3),
    )


def score_credibility(session: Session, *, recompute: bool = False) -> dict[str, int]:
    """Score every resolved unit. Cheap enough to redo from scratch."""
    stats = {"scored": 0, "skipped": 0}
    stmt = select(EvidenceUnit).where(EvidenceUnit.variant_id.is_not(None))
    for unit in session.scalars(stmt).yield_per(500):
        if not recompute and unit.credibility_json is not None:
            stats["skipped"] += 1
            continue
        unit.spam_probability = spam_probability(unit)
        unit.credibility_json = compute_credibility(unit).as_json()
        stats["scored"] += 1
    session.flush()
    return stats


def credibility_from_json(payload: dict[str, object] | None) -> Credibility:
    """Read back a stored vector, tolerating a unit that was never scored."""
    if not payload:
        return Credibility(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    groups = payload.get("by_aspect_group") or {}
    if not isinstance(groups, dict):  # pragma: no cover - defensive
        groups = {}
    base = float(payload.get("base", 0.5))  # type: ignore[arg-type]
    return Credibility(
        base=base,
        durability=float(groups.get("durability", 0.5)),
        immediate=float(groups.get("immediate", 0.5)),
        service=float(groups.get("service", 0.5)),
        efficiency=float(groups.get("efficiency", 0.5)),
        # Rows scored before the ablation existed have no textual figure. Fall
        # back to the full one rather than to a default, so an un-rescored
        # database understates the ablation gap instead of inventing one.
        base_textual=float(payload.get("base_textual", base)),  # type: ignore[arg-type]
    )


__all__ = [
    "Credibility",
    "aspect_fit",
    "compute_credibility",
    "credibility_from_json",
    "launch_window_correction",
    "recency_decay",
    "reliability",
    "score_credibility",
    "spam_probability",
]
