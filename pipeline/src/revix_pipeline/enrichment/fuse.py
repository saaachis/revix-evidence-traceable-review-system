"""Fusion: many weighted opinions into one verdict, with its own uncertainty.

This is where the project's argument becomes arithmetic.

    weight(e, a) = source_prior(e)
                 x (1 - spam(e))
                 x reliability(e)
                 x aspect_fit(e, a)
                 x recency(e)
                 x launch_window(e)

    score(v, a)  = sum w(e,a) * polarity(e,a)  /  sum w(e,a)

Three things fall out of it that are worth more than the score itself.

**Effective sample size.** Kish's n_eff = (sum w)^2 / sum w^2. Once reviews
carry different weights, counting them stops measuring how much you know. Two
hundred low-weight reviews can carry less information than thirty high-weight
ones, which is why weighting properly makes the interval *wider*. Being more
careful about which evidence counts means admitting you have less of it.

**Divergence.** The weighted share of evidence disagreeing with the majority
sign. The interface sorts on this rather than on score, because the contested
topic is the one that decides a purchase.

**Covariate attribution.** Which characteristic best explains a disagreement,
by between-group variance. This produces "71% of the split on the gearbox is
explained by transmission type", which is a statistical decomposition rather
than a language model's opinion.

Every claim written here gets its contributing evidence written alongside it,
in the same transaction, before any prose exists. That ordering is the whole
traceability guarantee.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from revix_core.enums import ASPECT_GROUPS, AspectKey
from revix_core.models import (
    AspectOpinion,
    EvidenceSource,
    EvidenceUnit,
    FusionConfig,
    VehicleVariant,
    Verdict,
    VerdictAspect,
    VerdictClaim,
    VerdictClaimEvidence,
    utcnow,
)
from revix_core.settings import get_settings
from revix_pipeline.enrichment.credibility import (
    credibility_from_json,
    launch_window_correction,
    recency_decay,
)

BOOTSTRAP_SAMPLES = 400
CONFIDENCE_LEVEL = 0.80
#: How many contributing reviews to record per claim. The drawer shows the top
#: contributors, not all four hundred, and storing every link for every claim
#: would be a lot of rows for no additional honesty.
EVIDENCE_LINKS_PER_CLAIM = 25


@dataclass(slots=True)
class Contribution:
    """One evidence unit's contribution to one aspect score."""

    unit_id: Any
    weight: float
    polarity: float
    # Covariates, carried along so attribution does not need a second query.
    transmission: str
    fuel: str
    source_key: str
    verified: bool | None
    ownership_months: int | None
    km_driven: int | None
    #: True when this review is about the model and not about this exact trim.
    #: Carried on the contribution rather than looked up later, because the
    #: reader is told the split and a number nobody can trace back is not
    #: something this project publishes.
    model_level: bool = False


def to_ten(polarity: float) -> float:
    """Map -1..+1 onto 0..10, which is what a person expects to read."""
    return round((polarity + 1.0) * 5.0, 2)


def kish_effective_sample(weights: list[float]) -> float:
    """(sum w)^2 / sum w^2. Kish, 1965."""
    total = sum(weights)
    squares = sum(w * w for w in weights)
    if squares <= 0:
        return 0.0
    return round((total * total) / squares, 2)


def weighted_mean(contributions: list[Contribution]) -> float:
    total = sum(c.weight for c in contributions)
    if total <= 0:
        return 0.0
    return sum(c.weight * c.polarity for c in contributions) / total


def divergence_index(contributions: list[Contribution]) -> float:
    """Weighted share of evidence disagreeing with the majority sign."""
    if not contributions:
        return 0.0
    mean = weighted_mean(contributions)
    majority_sign = 1.0 if mean >= 0 else -1.0
    disagreeing = sum(
        c.weight for c in contributions if (1.0 if c.polarity >= 0 else -1.0) != majority_sign
    )
    total = sum(c.weight for c in contributions)
    return round(disagreeing / total, 3) if total else 0.0


def bootstrap_means(
    contributions: list[Contribution],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = 20260905,
) -> list[float]:
    """Sorted resampled means, on the 0..10 scale.

    Separated from the interval because the calibration study in section 18.3
    reads several nominal levels off one resampling. Doing the work once and
    slicing it is both faster and, more importantly, means every level
    describes the same bootstrap rather than a different one.
    """
    if not contributions:
        return []
    rng = random.Random(seed)
    n = len(contributions)
    means = [
        to_ten(weighted_mean([contributions[rng.randrange(n)] for _ in range(n)]))
        for _ in range(samples)
    ]
    means.sort()
    return means


def interval_from_means(means: list[float], level: float) -> tuple[float, float]:
    """A two-sided interval at `level`, from an already sorted bootstrap."""
    if not means:
        return 0.0, 0.0
    samples = len(means)
    tail = (1.0 - level) / 2.0
    lo = means[max(0, int(tail * samples))]
    hi = means[min(samples - 1, int((1.0 - tail) * samples))]
    return round(lo, 2), round(hi, 2)


def bootstrap_interval(
    contributions: list[Contribution],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    level: float = CONFIDENCE_LEVEL,
    seed: int = 20260905,
) -> tuple[float, float]:
    """Weighted bootstrap over the contributing units.

    Deterministic seed, so the same evidence always produces the same interval
    and a verdict does not wobble between nightly runs for no reason.
    """
    if len(contributions) < 2:
        value = to_ten(weighted_mean(contributions)) if contributions else 0.0
        return value, value
    return interval_from_means(bootstrap_means(contributions, samples=samples, seed=seed), level)


#: Only characteristics that actually VARY between reviews of one variant.
#: Transmission and fuel are deliberately absent: they are fixed by the variant
#: itself, so within one variant every review shares them and they can explain
#: none of the spread. The proposal's "71% explained by transmission" is a
#: statement about a whole MODEL, across its variants, and belongs to
#: model-level fusion rather than here.
COVARIATES: tuple[str, ...] = ("source", "verified", "ownership_bucket", "distance_bucket")


def _covariate_value(c: Contribution, name: str) -> str | None:
    if name == "source":
        return c.source_key
    if name == "verified":
        return None if c.verified is None else ("verified" if c.verified else "unverified")
    if name == "ownership_bucket":
        if c.ownership_months is None:
            return None
        if c.ownership_months < 6:
            return "under 6 months"
        if c.ownership_months < 24:
            return "6 to 24 months"
        return "over 2 years"
    if name == "distance_bucket":
        if c.km_driven is None:
            return None
        if c.km_driven < 10000:
            return "under 10,000 km"
        if c.km_driven < 40000:
            return "10,000 to 40,000 km"
        return "over 40,000 km"
    return None  # pragma: no cover


def attribute_divergence(contributions: list[Contribution]) -> dict[str, Any] | None:
    """Which characteristic explains most of the disagreement?

    Between-group variance over total variance, which is the share of the
    spread a covariate accounts for. Standard statistics, and far cheaper and
    more reliable than asking a model to speculate.
    """
    if len(contributions) < 8:
        return None

    grand_mean = weighted_mean(contributions)
    total_weight = sum(c.weight for c in contributions)
    total_variance = (
        sum(c.weight * (c.polarity - grand_mean) ** 2 for c in contributions) / total_weight
        if total_weight
        else 0.0
    )
    if total_variance <= 1e-9:
        return None

    best: dict[str, Any] | None = None
    for name in COVARIATES:
        groups: dict[str, list[Contribution]] = defaultdict(list)
        for c in contributions:
            value = _covariate_value(c, name)
            if value is not None:
                groups[value].append(c)

        # Two groups minimum, and each needs enough behind it to mean anything.
        usable = {
            k: v for k, v in groups.items() if sum(x.weight for x in v) >= 0.05 * total_weight
        }
        if len(usable) < 2:
            continue

        between = 0.0
        detail = []
        for value, members in usable.items():
            w = sum(m.weight for m in members)
            mean = weighted_mean(members)
            between += w * (mean - grand_mean) ** 2
            detail.append(
                {
                    "value": value,
                    "score": to_ten(mean),
                    "weight_share": round(w / total_weight, 3),
                    "count": len(members),
                }
            )
        between /= total_weight
        share = between / total_variance
        if best is None or share > float(best["explained_share"]):
            detail.sort(key=lambda d: float(d["score"]))  # type: ignore[arg-type]
            best = {
                "covariate": name,
                "explained_share": round(min(1.0, share), 3),
                "groups": detail,
            }

    # Below a fifth, the covariate is not really explaining anything and
    # claiming otherwise would be overreading noise.
    if best is None or float(best["explained_share"]) < 0.20:
        return None
    return best


def gather_contributions(
    session: Session, variant_id: Any, params: dict[str, Any]
) -> dict[AspectKey, list[Contribution]]:
    """Load every opinion about one variant and weight it under one strategy."""
    # The variant itself, so its model can be matched against model-level
    # evidence. One extra lookup per variant per strategy, against an indexed
    # primary key.
    variant_row = session.get(VehicleVariant, variant_id)
    model_id = variant_row.model_id if variant_row is not None else None

    # Two populations, deliberately in one query. Reviews of this exact trim,
    # and reviews of the model that nobody could pin to a trim because the
    # source never asked. Ninety percent of real owner reviews are the second
    # kind: a review site asks which model you bought, not which variant.
    rows = session.execute(
        select(AspectOpinion, EvidenceUnit, EvidenceSource, VehicleVariant)
        .join(EvidenceUnit, AspectOpinion.evidence_unit_id == EvidenceUnit.id)
        .join(EvidenceSource, EvidenceUnit.source_id == EvidenceSource.id)
        .join(VehicleVariant, VehicleVariant.id == variant_id)
        .where(
            (EvidenceUnit.variant_id == variant_id)
            | (
                (EvidenceUnit.variant_id.is_(None))
                & (EvidenceUnit.model_id == model_id)
                & (model_id is not None)
            )
        )
    ).all()

    settings = get_settings()
    by_aspect: dict[AspectKey, list[Contribution]] = defaultdict(list)
    for opinion, unit, source, variant in rows:
        aspect = opinion.aspect_key
        weight = 1.0

        if params.get("use_source_prior"):
            weight *= float(source.default_source_prior)
        if params.get("use_spam"):
            weight *= 1.0 - float(unit.spam_probability or 0.0)
        # The ablation section 18.1 requires: run the same strategy with every
        # metadata signal removed, so the claim that textual and behavioural
        # features carry weight on their own is tested rather than asserted.
        # aspect fit and the launch-window correction are pure metadata, so
        # they do not survive it at all.
        use_metadata = params.get("use_metadata", True)
        cred = credibility_from_json(unit.credibility_json)
        reliability_value = cred.base if use_metadata else cred.base_textual
        if params.get("use_reliability"):
            weight *= reliability_value if reliability_value > 0 else 0.05
        if params.get("use_aspect_fit") and use_metadata:
            # base is already inside the per-group figure, so divide it back
            # out to avoid applying reliability twice.
            fit = cred.for_aspect(aspect) / cred.base if cred.base > 0 else 1.0
            weight *= max(0.05, min(1.0, fit))
        if params.get("use_recency"):
            weight *= recency_decay(
                unit, half_life_days=int(params.get("recency_half_life_days", 540))
            )
        if params.get("use_launch_window") and use_metadata:
            weight *= launch_window_correction(unit)

        # Extraction confidence always applies. A guess about what a sentence
        # meant should not count as much as a certainty, under any strategy.
        weight *= float(opinion.confidence)

        # A review of "the Creta" is real evidence about a Creta SX(O) Turbo
        # DCT and weaker evidence than a review of that trim. The discount is
        # a setting rather than a constant here, and it is identical across
        # strategies, so it cannot flatter one of them in the 18.1 comparison.
        model_level = unit.variant_id is None
        if model_level:
            weight *= settings.model_level_evidence_weight

        if weight <= 0:
            continue

        by_aspect[aspect].append(
            Contribution(
                unit_id=unit.id,
                weight=weight,
                polarity=float(opinion.polarity),
                transmission=variant.transmission.value,
                fuel=variant.fuel_type.value,
                source_key=source.source_key,
                verified=unit.is_verified_owner,
                ownership_months=unit.ownership_duration_months,
                km_driven=unit.km_driven,
                model_level=model_level,
            )
        )
    return by_aspect


def fuse_variant(
    session: Session,
    variant: VehicleVariant,
    config: FusionConfig,
) -> Verdict:
    """Compute and persist one verdict for one variant under one strategy."""
    settings = get_settings()
    params = dict(config.params)
    by_aspect = gather_contributions(session, variant.id, params)

    # Replace rather than update. A verdict is fully derived, so recomputing
    # it from scratch is both simpler and safer than reconciling a diff.
    existing = session.scalar(
        select(Verdict).where(
            Verdict.variant_id == variant.id, Verdict.fusion_config_id == config.id
        )
    )
    if existing is not None:
        session.execute(delete(Verdict).where(Verdict.id == existing.id))
        session.flush()

    all_contributions = [c for group in by_aspect.values() for c in group]
    unit_ids = {c.unit_id for c in all_contributions}
    source_keys = sorted({c.source_key for c in all_contributions})
    # Counted over units rather than contributions, because one review can
    # speak to several aspects and would otherwise be counted several times.
    model_unit_ids = {c.unit_id for c in all_contributions if c.model_level}

    verdict = Verdict(
        variant_id=variant.id,
        fusion_config_id=config.id,
        computed_at=utcnow(),
        evidence_count=len(unit_ids),
        model_evidence_count=len(model_unit_ids),
        sources_used={"sources": source_keys, "count": len(source_keys)},
    )

    # The evidence floor. Below it we publish nothing rather than a number we
    # do not believe, and we record why so the interface can explain itself.
    if (
        len(unit_ids) < settings.min_evidence_units
        or len(source_keys) < settings.min_distinct_sources
    ):
        verdict.is_suppressed = True
        verdict.suppression_reason = (
            f"{len(unit_ids)} reviews from {len(source_keys)} "
            f"{'source' if len(source_keys) == 1 else 'sources'}. "
            f"We want at least {settings.min_evidence_units} from "
            f"{settings.min_distinct_sources} before scoring a vehicle."
        )
        session.add(verdict)
        session.flush()
        return verdict

    # Kish is computed over one weight per evidence unit, not per opinion. A
    # review that happens to mention four topics is still one witness, and
    # counting it four times would put n_eff above the number of reviews.
    weight_by_unit: dict[Any, float] = defaultdict(float)
    aspect_rows: list[tuple[VerdictAspect, list[Contribution]]] = []

    for aspect in AspectKey:
        contributions = by_aspect.get(aspect, [])
        if not contributions:
            continue
        score = to_ten(weighted_mean(contributions))
        lo, hi = bootstrap_interval(contributions)
        attribution = attribute_divergence(contributions)

        row = VerdictAspect(
            aspect_key=aspect,
            score=score,
            # The bootstrap can put the point estimate marginally outside its
            # own interval on small samples; clamp so the stored row always
            # satisfies the check constraint.
            ci_low=min(lo, score),
            ci_high=max(hi, score),
            support_count=len({c.unit_id for c in contributions}),
            divergence_index=divergence_index(contributions),
            top_covariate=attribution["covariate"] if attribution else None,
            covariate_explanation=attribution,
        )
        aspect_rows.append((row, contributions))
        for c in contributions:
            weight_by_unit[c.unit_id] = max(weight_by_unit[c.unit_id], c.weight)

    if not aspect_rows:
        verdict.is_suppressed = True
        verdict.suppression_reason = "No topic could be scored from the available reviews."
        session.add(verdict)
        session.flush()
        return verdict

    # Overall is the mean of the aspect scores rather than of every opinion,
    # so a chatty topic does not dominate the headline number.
    overall = sum(float(r.score or 0) for r, _ in aspect_rows) / len(aspect_rows)
    overall_lo = sum(float(r.ci_low or 0) for r, _ in aspect_rows) / len(aspect_rows)
    overall_hi = sum(float(r.ci_high or 0) for r, _ in aspect_rows) / len(aspect_rows)

    verdict.overall_score = round(overall, 2)
    verdict.confidence_low = round(min(overall_lo, overall), 2)
    verdict.confidence_high = round(max(overall_hi, overall), 2)
    verdict.effective_sample_size = kish_effective_sample(list(weight_by_unit.values()))
    session.add(verdict)
    session.flush()

    for row, _ in aspect_rows:
        row.verdict_id = verdict.id
        session.add(row)
    session.flush()

    _write_claims(session, verdict, aspect_rows)
    return verdict


def _write_claims(
    session: Session,
    verdict: Verdict,
    aspect_rows: list[tuple[VerdictAspect, list[Contribution]]],
) -> None:
    """Every assertable statement, with the evidence that produced it.

    Written before any prose exists. The score is computed from these links,
    which is why a citation here cannot be wrong: it is not an annotation
    added afterwards, and no language model was asked to produce it.
    """
    order = 0
    for row, contributions in sorted(
        aspect_rows, key=lambda pair: float(pair[0].divergence_index or 0), reverse=True
    ):
        claim = VerdictClaim(
            verdict_id=verdict.id,
            claim_type="aspect_score",
            claim_template="aspect_score",
            display_order=order,
            computed_values={
                "aspect": row.aspect_key.value,
                "score": float(row.score or 0),
                "ci": [float(row.ci_low or 0), float(row.ci_high or 0)],
                "support": row.support_count,
                "divergence": float(row.divergence_index or 0),
                "group": ASPECT_GROUPS[row.aspect_key].value,
            },
        )
        session.add(claim)
        session.flush()

        top = sorted(contributions, key=lambda c: c.weight, reverse=True)
        seen: set[Any] = set()
        rank = 0
        total_weight = sum(c.weight for c in contributions) or 1.0
        for c in top:
            if c.unit_id in seen:
                continue
            seen.add(c.unit_id)
            rank += 1
            session.add(
                VerdictClaimEvidence(
                    verdict_claim_id=claim.id,
                    evidence_unit_id=c.unit_id,
                    contribution_weight=round(min(0.99999, c.weight / total_weight), 5),
                    rank=rank,
                )
            )
            if rank >= EVIDENCE_LINKS_PER_CLAIM:
                break

        if row.covariate_explanation:
            session.add(
                VerdictClaim(
                    verdict_id=verdict.id,
                    claim_type="aspect_divergence",
                    claim_template="aspect_divergence",
                    display_order=order,
                    computed_values={
                        "aspect": row.aspect_key.value,
                        **row.covariate_explanation,
                    },
                )
            )
        order += 1
    session.flush()


def fuse_all(session: Session, *, variant_limit: int | None = None) -> dict[str, int]:
    """Every variant, under every strategy.

    Computing all strategies for every variant is a loop, not extra
    architecture, and it is what makes the interface switch a lookup rather
    than a recomputation.
    """
    configs = list(session.scalars(select(FusionConfig).order_by(FusionConfig.display_order)))
    # Ordered before limiting, and ordered the SAME way as seeds_for in the
    # runner. A bare LIMIT returns arbitrary rows in Postgres, so with
    # --limit N the ingest stage collected one set of N variants and this
    # stage fused a different set, producing a database full of evidence and
    # a page full of suppressed verdicts.
    stmt = select(VehicleVariant).order_by(VehicleVariant.trim_code)
    if variant_limit:
        stmt = stmt.limit(variant_limit)
    variants = list(session.scalars(stmt))

    stats = {"variants": 0, "verdicts": 0, "suppressed": 0}
    for variant in variants:
        stats["variants"] += 1
        for config in configs:
            verdict = fuse_variant(session, variant, config)
            stats["verdicts"] += 1
            if verdict.is_suppressed:
                stats["suppressed"] += 1
    session.flush()
    return stats


__all__ = [
    "Contribution",
    "attribute_divergence",
    "bootstrap_interval",
    "divergence_index",
    "fuse_all",
    "fuse_variant",
    "gather_contributions",
    "kish_effective_sample",
    "math",
    "to_ten",
    "weighted_mean",
]
