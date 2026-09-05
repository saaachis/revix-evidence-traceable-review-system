"""Aspect extraction: which topic is this sentence about, and how does it feel?

A lexicon and rule baseline, deliberately. Three reasons:

  1. It needs no labelled data to start, so the rest of the pipeline can be
     built and measured before anyone hand-labels 500 sentences.
  2. It is the honest baseline the distilled classifier must beat. Reporting
     "our model scores 0.79" means nothing without knowing what a keyword
     matcher scores.
  3. It is fast enough to run over the whole corpus in seconds, which keeps
     the nightly job cheap.

It is replaceable. `extract_from_text` is the seam: swap the body for a
classifier and nothing else in the pipeline changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import AspectKey
from revix_core.models import AspectOpinion, EvidenceUnit

#: Topic cues. Multi-word phrases first so "service centre" wins over "service".
ASPECT_CUES: dict[AspectKey, tuple[str, ...]] = {
    AspectKey.ENGINE_GEARBOX: (
        "gearbox",
        "transmission",
        "clutch",
        "engine",
        "pickup",
        "power delivery",
        "shift",
        "shifts",
        "torque",
        "acceleration",
        "dct",
        "amt",
        "cvt",
    ),
    AspectKey.RIDE_HANDLING_NVH: (
        "ride quality",
        "suspension",
        "handling",
        "nvh",
        "road noise",
        "cabin noise",
        "potholes",
        "body roll",
        "steering",
        "bumps",
        "ride",
    ),
    AspectKey.RUNNING_COST: (
        "mileage",
        "kmpl",
        "fuel efficiency",
        "running cost",
        "economy",
        "fuel consumption",
        "petrol cost",
        "diesel cost",
    ),
    AspectKey.SPACE_COMFORT: (
        "rear seat",
        "legroom",
        "headroom",
        "boot space",
        "seat comfort",
        "under thigh",
        "cabin space",
        "pillion",
        "seats",
        "storage",
    ),
    AspectKey.FEATURES: (
        "touchscreen",
        "infotainment",
        "connected",
        "sunroof",
        "features",
        "android auto",
        "carplay",
        "instrument cluster",
        "software",
    ),
    AspectKey.BUILD_QUALITY: (
        "build quality",
        "panel gap",
        "plastics",
        "rattle",
        "rattles",
        "fit and finish",
        "paint",
        "doors shut",
        "materials",
    ),
    AspectKey.SAFETY: (
        "airbag",
        "airbags",
        "ncap",
        "abs",
        "esp",
        "stability control",
        "braking",
        "brakes",
        "safety",
        "visibility",
    ),
    AspectKey.SERVICE_AFTERSALES: (
        "service centre",
        "service center",
        "spare",
        "spares",
        "workshop",
        "after sales",
        "aftersales",
        "dealer",
        "advisor",
        "service cost",
        "servicing",
    ),
    AspectKey.LONG_TERM_RELIABILITY: (
        "reliability",
        "reliable",
        "breakdown",
        "niggle",
        "niggles",
        "gone wrong",
        "dependable",
        "issues",
        "problems",
        "electrical",
    ),
}

POSITIVE_CUES: tuple[str, ...] = (
    "excellent",
    "great",
    "good",
    "smooth",
    "solid",
    "comfortable",
    "responsive",
    "quick",
    "generous",
    "supportive",
    "reasonable",
    "quiet",
    "strong",
    "better",
    "impressed",
    "happy",
    "dependable",
    "cleanly",
    "linear",
    "consistent",
    "low",
    "reassuring",
    "confidence",
    "immediately",
    "properly",
    "well",
)

NEGATIVE_CUES: tuple[str, ...] = (
    "poor",
    "bad",
    "terrible",
    "jerky",
    "jerkiness",
    "hesitates",
    "hesitation",
    "cramped",
    "cheap",
    "rattle",
    "rattles",
    "lags",
    "disconnects",
    "expensive",
    "high",
    "noise",
    "noisy",
    "firm",
    "crashes",
    "nowhere near",
    "disappears",
    "inconsistent",
    "faded",
    "misbehaves",
    "niggles",
    "wrong",
    "took three weeks",
    "not",
    "never",
    "problem",
    "problems",
    "issue",
    "issues",
    "awkward",
    "late",
)

NEGATORS: tuple[str, ...] = ("not", "no", "never", "hardly", "barely", "nowhere")

#: An unhedged claim is worth more than a hedged one, and the extractor should
#: say so rather than pretending both are equally certain.
HEDGES: tuple[str, ...] = ("maybe", "perhaps", "possibly", "i think", "seems", "somewhat")


@dataclass(slots=True)
class Extraction:
    aspect: AspectKey
    polarity: float
    confidence: float
    span: str


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _count(text: str, cues: tuple[str, ...]) -> int:
    lowered = text.casefold()
    return sum(1 for cue in cues if cue in lowered)


def score_sentence(sentence: str) -> tuple[float, float]:
    """Return (polarity, confidence) for one sentence, ignoring topic."""
    lowered = sentence.casefold()
    positives = _count(sentence, POSITIVE_CUES)
    negatives = _count(sentence, NEGATIVE_CUES)

    # A negator flips whatever sentiment follows it. Crude, but it is the
    # single biggest error a bag of cues makes without it.
    if any(re.search(rf"\b{n}\b", lowered) for n in NEGATORS) and positives > negatives:
        positives, negatives = negatives, positives

    total = positives + negatives
    if total == 0:
        return 0.0, 0.15

    polarity = (positives - negatives) / total
    # More cues means more evidence for the reading, up to a point.
    confidence = min(0.9, 0.35 + 0.15 * total)
    if any(h in lowered for h in HEDGES):
        confidence *= 0.7
    return round(polarity, 3), round(confidence, 3)


def extract_from_text(text: str) -> list[Extraction]:
    """One extraction per (sentence, topic) pair the sentence actually mentions."""
    out: list[Extraction] = []
    for sentence in split_sentences(text):
        polarity, confidence = score_sentence(sentence)
        lowered = sentence.casefold()
        for aspect, cues in ASPECT_CUES.items():
            if not any(cue in lowered for cue in cues):
                continue
            if confidence < 0.2:
                # It mentions the topic but says nothing evaluative about it.
                continue
            out.append(
                Extraction(
                    aspect=aspect,
                    polarity=polarity,
                    confidence=confidence,
                    span=sentence[:400],
                )
            )
    return out


def extract_opinions(session: Session, *, batch_size: int = 500) -> dict[str, int]:
    """Extract for every resolved unit that has not been extracted yet."""
    stats = {"units": 0, "opinions": 0, "skipped_no_opinion": 0}

    already = {row[0] for row in session.execute(select(AspectOpinion.evidence_unit_id).distinct())}

    # Model-level units count too. A review placed on the Creta but not on a
    # trim is still evidence, and skipping it here would quietly undo the
    # whole point of resolving to a model in the first place.
    stmt = select(EvidenceUnit).where(
        EvidenceUnit.variant_id.is_not(None) | EvidenceUnit.model_id.is_not(None)
    )
    for unit in session.scalars(stmt).yield_per(batch_size):
        if unit.id in already:
            continue
        stats["units"] += 1
        extractions = extract_from_text(unit.text)
        if not extractions:
            stats["skipped_no_opinion"] += 1
            continue
        # One row per (unit, aspect). Where a review says several things about
        # the same topic, take the confidence-weighted mean rather than
        # letting a chatty reviewer count several times.
        by_aspect: dict[AspectKey, list[Extraction]] = {}
        for ex in extractions:
            by_aspect.setdefault(ex.aspect, []).append(ex)

        for aspect, group in by_aspect.items():
            weight = sum(e.confidence for e in group) or 1.0
            polarity = sum(e.polarity * e.confidence for e in group) / weight
            session.add(
                AspectOpinion(
                    evidence_unit_id=unit.id,
                    aspect_key=aspect,
                    polarity=round(max(-1.0, min(1.0, polarity)), 3),
                    confidence=round(min(0.95, weight / len(group)), 3),
                    extracted_span=max(group, key=lambda e: e.confidence).span,
                )
            )
            stats["opinions"] += 1

    session.flush()
    return stats
