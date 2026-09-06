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
from revix_core.settings import get_settings

#: Topic cues. Multi-word phrases first so "service centre" wins over "service".
#:
#: Two-wheeler vocabulary sits alongside the car vocabulary rather than in a
#: separate table. A cue list per vehicle class would need the extractor to
#: know which class a unit belongs to before it has been resolved to a vehicle,
#: which is the wrong way round: resolution happens after extraction. The cost
#: of one shared list is that "chain" could in principle fire on a car review
#: about a timing chain, which is a fair trade for the 21 of 30 real bike
#: reviews that previously produced nothing at all.
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
        "performance",
        "dct",
        "amt",
        "cvt",
        # Two-wheeler drivetrain. A bike has no gearbox worth the name to
        # a rider; it has a clutch, a chain and a kick start.
        "chain",
        "kick start",
        "self start",
        "gear shift",
        "top speed",
        "refinement",
        "vibration",
    ),
    AspectKey.RIDE_HANDLING_NVH: (
        "ride quality",
        "suspension",
        "handling",
        "handles",
        "handle",
        "nvh",
        "road noise",
        "cabin noise",
        "potholes",
        "body roll",
        "steering",
        "bumps",
        "ride",
        # A rider feels the road through the bars and the seat, so the
        # vocabulary is different from a car cabin.
        "handlebar",
        "handle bar",
        "cornering",
        "stability",
        "riding comfort",
        "shocks",
        "balance",
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
        # "milage" outnumbers "mileage" in Indian owner reviews and is not
        # a typo we can afford to be precious about.
        "milage",
        "average",
        "fuel average",
        "km per litre",
        "kmph per litre",
        "maintenance cost",
        "petrol",
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
        "seat height",
        "seat",
        "footrest",
        "foot rest",
        "riding position",
        "under seat",
        "leg space",
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
        "headlight",
        "head light",
        "led",
        "console",
        "digital meter",
        "usb",
        "bluetooth",
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
        "body panel",
        "plastic quality",
        "rusting",
        "rust",
        "finishing",
        "sturdy",
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
        "brake",
        "disc brake",
        "grip",
        "tyre grip",
        "skid",
        "helmet",
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
        "service",
        "showroom",
        "mechanic",
        "parts",
        "warranty claim",
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
        "durability",
        "durable",
        "long run",
        "years of use",
        "no issue",
        "trouble",
        "starting problem",
        "wear",
    ),
}

POSITIVE_CUES: tuple[str, ...] = (
    # How people actually write when they like something, which is not how a
    # car magazine writes. "best" was missing entirely, and it is close to the
    # most common evaluative word in an Indian owner review.
    "best",
    "perfect",
    "awesome",
    "amazing",
    "superb",
    "fantastic",
    "love",
    "loved",
    "nice",
    "worth",
    "satisfied",
    "recommend",
    "no vibration",
    "no issues",
    "no problem",
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
    # Things breaking. All of these were absent, which meant "the self start
    # failed within a year" scored as neutral: a reliability complaint read as
    # a shrug, on the aspect the proposal says matters most.
    "failed",
    "fails",
    "failure",
    "broke",
    "broken",
    "stopped working",
    "leaking",
    "damaged",
    "annoying",
    "worst",
    "waste",
    "disappointing",
    "disappointed",
    "vibration",
    "vibrations",
    "weak",
    "uncomfortable",
    "complaint",
    "complaints",
    "regret",
    "avoid",
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

#: Runs of dots are one pause, not four sentence endings. Indian owner reviews
#: use "....." the way other people use a comma, and splitting on each dot
#: produced fragments like "It....." and "And the good one is....." that carry
#: no topic and no sentiment and were then counted as reviews saying nothing.
_ELLIPSIS = re.compile(r"\.{2,}")

#: Below this a fragment cannot carry an opinion about a topic, and letting one
#: through means a stray "It." is scored and discarded as a real observation.
MIN_SENTENCE_CHARS = 15


def split_sentences(text: str) -> list[str]:
    normalised = _ELLIPSIS.sub(". ", text)
    return [
        s.strip() for s in _SENTENCE_SPLIT.split(normalised) if len(s.strip()) >= MIN_SENTENCE_CHARS
    ]


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


def aspects_in(sentence: str, classifier: object | None = None) -> set[AspectKey]:
    """Which topics this sentence is about.

    The trained classifier when one exists, the cue lexicon otherwise. ADR
    0004 promised the pipeline would keep running with nothing trained, and
    this is where that promise is kept.
    """
    if classifier is not None:
        return classifier.predict(sentence)  # type: ignore[attr-defined,no-any-return]
    lowered = sentence.casefold()
    return {a for a, cues in ASPECT_CUES.items() if any(cue in lowered for cue in cues)}


def extract_from_text(text: str, classifier: object | None = None) -> list[Extraction]:
    """One extraction per (sentence, topic) pair the sentence actually mentions."""
    out: list[Extraction] = []
    for sentence in split_sentences(text):
        polarity, confidence = score_sentence(sentence)
        for aspect in aspects_in(sentence, classifier):
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
    stats = {"units": 0, "opinions": 0, "skipped_no_opinion": 0, "used_classifier": 0}

    # Loaded once, not per unit. Absent is the normal case on a fresh
    # checkout, and it must not be an error.
    classifier = None
    if get_settings().aspect_classifier_enabled:
        try:
            from revix_pipeline.ml.aspect_model import AspectClassifier

            classifier = AspectClassifier.load()
        except ImportError:
            # The ml extra is not installed. Expected in the API image, which
            # has no reason to carry scikit-learn.
            classifier = None
    stats["used_classifier"] = 1 if classifier is not None else 0

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
        extractions = extract_from_text(unit.text, classifier)
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
