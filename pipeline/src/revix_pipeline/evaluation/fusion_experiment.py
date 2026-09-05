"""The central fusion experiment, proposal section 18.1.

The naive question is "is our consensus correct?". It has no ground truth and
asking it would produce a number that means nothing. So the question is
narrowed until it does have an answer:

    Gold consensus (held out)
        For each variant and aspect, the score over evidence units that are
        verified owners with at least twelve months of ownership and at least
        10,000 km, equally weighted. Those units are then REMOVED from the
        estimation pool.

    Task
        From the remaining mixed-quality pool, draw k units and estimate the
        gold consensus.

    Compare
        equal versus source_weighted versus credibility_weighted, at several
        values of k, over many random subsamples and every eligible variant.

    Report
        RMSE, Spearman rank correlation across variants, interval coverage.

This is not circular, because the target is defined entirely by metadata that
is excluded from the pool the estimate is drawn from. It tests exactly the
hypothesis the project rests on: do credibility signals identify which of the
ordinary, unverified, mixed-quality evidence actually carries signal?

Two design points that decide whether the numbers mean anything:

**Every strategy sees the same draw.** Within one replicate the units are
sampled once and all three strategies estimate from that same set. Sampling
independently per strategy would measure sampling noise and report it as a
difference between strategies.

**The gold consensus is a plain mean.** Not the equal-weight strategy, which
still carries extraction confidence. The target has to be free of anything the
estimators use, or the comparison quietly favours whichever strategy resembles
the target's own weighting.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import AspectKey
from revix_core.models import FusionConfig, VehicleVariant
from revix_pipeline.enrichment.fuse import (
    BOOTSTRAP_SAMPLES,
    Contribution,
    bootstrap_means,
    gather_contributions,
    interval_from_means,
    to_ten,
    weighted_mean,
)

#: Section 18.1's definition of a witness whose account is the target rather
#: than an estimate of it.
GOLD_MIN_MONTHS = 12
GOLD_MIN_KM = 10_000

#: Below this the "gold consensus" is one or two people's opinion, and an
#: estimator being wrong about it says more about them than about the estimator.
MIN_GOLD_UNITS = 5

#: Nominal levels for the reliability diagram in section 18.3. One bootstrap
#: answers all of them.
CALIBRATION_LEVELS: tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90)

DEFAULT_K: tuple[int, ...] = (10, 20, 30, 50)
DEFAULT_REPLICATES = 200


@dataclass(slots=True)
class GoldConsensus:
    """One held-out target: a variant, an aspect, and what its owners said."""

    variant_id: Any
    variant_label: str
    aspect: AspectKey
    score: float
    n_units: int


@dataclass(slots=True)
class StrategyResult:
    """How one strategy did at one value of k."""

    strategy: str
    k: int
    n_estimates: int
    rmse: float
    mean_absolute_error: float
    bias: float
    spearman_by_aspect: dict[str, float] = field(default_factory=dict)
    spearman_mean: float = 0.0
    #: How many variants each rank correlation was computed over. Spearman on
    #: four variants is noise wearing a decimal point, and printing it without
    #: this number invites someone to quote it.
    spearman_n_variants: int = 0
    coverage: dict[str, float] = field(default_factory=dict)
    expected_calibration_error: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "k": self.k,
            "n_estimates": self.n_estimates,
            "rmse": round(self.rmse, 4),
            "mae": round(self.mean_absolute_error, 4),
            "bias": round(self.bias, 4),
            "spearman_by_aspect": {a: round(v, 4) for a, v in self.spearman_by_aspect.items()},
            "spearman_mean": round(self.spearman_mean, 4),
            "spearman_n_variants": self.spearman_n_variants,
            "coverage": {k: round(v, 4) for k, v in self.coverage.items()},
            "expected_calibration_error": round(self.expected_calibration_error, 4),
        }


@dataclass(slots=True)
class ExperimentReport:
    """Everything the experiment produced, including why it produced nothing."""

    eligible_variants: int
    gold_targets: int
    replicates: int
    sources_present: list[str]
    results: list[StrategyResult] = field(default_factory=list)
    ablation: list[StrategyResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ran(self) -> bool:
        return bool(self.results)

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible_variants": self.eligible_variants,
            "gold_targets": self.gold_targets,
            "replicates": self.replicates,
            "sources_present": self.sources_present,
            "with_metadata": [r.as_dict() for r in self.results],
            "without_metadata": [r.as_dict() for r in self.ablation],
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def _ranks(values: list[float]) -> list[float]:
    """Average ranks, so ties do not distort the correlation."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for position in range(i, j + 1):
            ranks[order[position]] = shared
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, computed here rather than pulled in from scipy.

    The pipeline has no scientific-computing dependency and adding one for a
    dozen lines would be a poor trade. Ties get average ranks, so this is
    Pearson on ranks rather than the shortcut formula, which is wrong when
    values repeat.
    """
    if len(xs) != len(ys) or len(xs) < 3:
        return float("nan")
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


# ---------------------------------------------------------------------------
# the split
# ---------------------------------------------------------------------------


def is_gold_unit(c: Contribution) -> bool:
    """A verified long-term owner, as section 18.1 defines one.

    All three conditions, and none of them inferred. A unit whose platform
    cannot verify ownership is not gold, however convincing it reads: the
    entire non-circularity of the experiment rests on the target being defined
    by metadata that the estimators never see.
    """
    return (
        c.verified is True
        and c.ownership_months is not None
        and c.ownership_months >= GOLD_MIN_MONTHS
        and c.km_driven is not None
        and c.km_driven >= GOLD_MIN_KM
    )


def split_gold_and_pool(
    contributions: list[Contribution],
) -> tuple[list[Contribution], list[Contribution]]:
    """Held-out target units, and everything left to estimate them from."""
    gold = [c for c in contributions if is_gold_unit(c)]
    pool = [c for c in contributions if not is_gold_unit(c)]
    return gold, pool


def gold_score(gold: list[Contribution]) -> float:
    """A plain unweighted mean, on the 0..10 scale.

    Equal weights means equal. Reusing the "equal" strategy would carry
    extraction confidence into the target, and a target that shares a term
    with its estimators is not independent of them.
    """
    if not gold:
        return 0.0
    return to_ten(sum(c.polarity for c in gold) / len(gold))


# ---------------------------------------------------------------------------
# the experiment
# ---------------------------------------------------------------------------


def _strategy_params(session: Session) -> dict[str, dict[str, Any]]:
    configs = session.scalars(select(FusionConfig).order_by(FusionConfig.display_order)).all()
    return {c.name: dict(c.params) for c in configs}


def _collect(
    session: Session,
    variant_limit: int | None,
    *,
    use_metadata: bool,
) -> tuple[
    list[GoldConsensus], dict[tuple[Any, AspectKey, str], dict[Any, Contribution]], list[str]
]:
    """Gold targets, and each strategy's weighting of each pool unit.

    Indexed by unit id, so a replicate can draw unit ids once and then ask
    every strategy what it thinks of exactly those units.
    """
    strategies = _strategy_params(session)
    stmt = select(VehicleVariant).order_by(VehicleVariant.trim_code)
    if variant_limit:
        stmt = stmt.limit(variant_limit)

    targets: list[GoldConsensus] = []
    pools: dict[tuple[Any, AspectKey, str], dict[Any, Contribution]] = {}
    sources: set[str] = set()

    for variant in session.scalars(stmt):
        by_strategy = {
            name: gather_contributions(
                session, variant.id, {**params, "use_metadata": use_metadata}
            )
            for name, params in strategies.items()
        }
        # The gold split is a property of the units, not of any weighting, so
        # it is read off one strategy and applied to all of them.
        reference = by_strategy.get("equal") or next(iter(by_strategy.values()), {})
        label = f"{variant.trim_code}"

        for aspect, contributions in reference.items():
            gold, pool = split_gold_and_pool(contributions)
            if len(gold) < MIN_GOLD_UNITS or not pool:
                continue
            gold_ids = {c.unit_id for c in gold}
            targets.append(
                GoldConsensus(
                    variant_id=variant.id,
                    variant_label=label,
                    aspect=aspect,
                    score=gold_score(gold),
                    n_units=len(gold),
                )
            )
            for name, per_aspect in by_strategy.items():
                pools[(variant.id, aspect, name)] = {
                    c.unit_id: c for c in per_aspect.get(aspect, []) if c.unit_id not in gold_ids
                }
            sources.update(c.source_key for c in pool)

    return targets, pools, sorted(sources)


def _evaluate(
    targets: list[GoldConsensus],
    pools: dict[tuple[Any, AspectKey, str], dict[Any, Contribution]],
    strategies: list[str],
    *,
    ks: tuple[int, ...],
    replicates: int,
    seed: int,
    bootstrap_samples: int,
) -> list[StrategyResult]:
    # errors[(strategy, k)] -> list of (estimate - gold)
    errors: dict[tuple[str, int], list[float]] = defaultdict(list)
    # per_variant[(strategy, k, aspect)] -> variant -> [estimates]
    per_variant: dict[tuple[str, int, str], dict[Any, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    # hits[(strategy, k, level)] -> [0/1]
    hits: dict[tuple[str, int, float], list[int]] = defaultdict(list)

    for target in targets:
        frames = {
            name: pools.get((target.variant_id, target.aspect, name), {}) for name in strategies
        }
        # One sampling frame for every strategy, taken from the strategy that
        # weights least. A unit missing from another strategy's frame was
        # dropped by that strategy's own zero-weight rule and is simply absent
        # from its estimate.
        frame_ids = sorted(
            frames.get("equal") or next((f for f in frames.values() if f), {}),
            key=str,
        )
        if not frame_ids:
            continue

        for k in ks:
            if len(frame_ids) < k:
                continue
            rng = random.Random(f"{seed}|{target.variant_id}|{target.aspect}|{k}")
            for replicate in range(replicates):
                drawn = rng.sample(frame_ids, k)
                for name in strategies:
                    picked = [frames[name][uid] for uid in drawn if uid in frames[name]]
                    if not picked:
                        continue
                    estimate = to_ten(weighted_mean(picked))
                    errors[(name, k)].append(estimate - target.score)
                    per_variant[(name, k, target.aspect.value)][target.variant_id].append(estimate)

                    # Calibration is expensive, so it runs on a subset of the
                    # replicates. The coverage question needs hundreds of
                    # trials, not tens of thousands, and the bootstrap inside
                    # each one is the dominant cost of the whole experiment.
                    if replicate % 10 == 0:
                        means = bootstrap_means(
                            picked,
                            samples=bootstrap_samples,
                            seed=hash((str(target.variant_id), k, replicate)) % 2**31,
                        )
                        for level in CALIBRATION_LEVELS:
                            lo, hi = interval_from_means(means, level)
                            hits[(name, k, level)].append(int(lo <= target.score <= hi))

    gold_by_variant_aspect = {(t.variant_id, t.aspect.value): t.score for t in targets}
    results: list[StrategyResult] = []
    for name in strategies:
        for k in ks:
            deltas = errors[(name, k)]
            if not deltas:
                continue
            rmse = math.sqrt(sum(d * d for d in deltas) / len(deltas))
            mae = sum(abs(d) for d in deltas) / len(deltas)
            bias = sum(deltas) / len(deltas)

            spearman_by_aspect: dict[str, float] = {}
            n_variants = 0
            for (strategy, kk, aspect), by_variant in per_variant.items():
                if strategy != name or kk != k or len(by_variant) < 3:
                    continue
                n_variants = max(n_variants, len(by_variant))
                estimates, golds = [], []
                for variant_id, values in by_variant.items():
                    estimates.append(sum(values) / len(values))
                    golds.append(gold_by_variant_aspect[(variant_id, aspect)])
                rho = spearman(estimates, golds)
                if not math.isnan(rho):
                    spearman_by_aspect[aspect] = rho

            coverage = {
                f"{level:.2f}": sum(hits[(name, k, level)]) / len(hits[(name, k, level)])
                for level in CALIBRATION_LEVELS
                if hits[(name, k, level)]
            }
            ece = (
                sum(abs(float(level) - empirical) for level, empirical in coverage.items())
                / len(coverage)
                if coverage
                else 0.0
            )
            results.append(
                StrategyResult(
                    strategy=name,
                    k=k,
                    n_estimates=len(deltas),
                    rmse=rmse,
                    mean_absolute_error=mae,
                    bias=bias,
                    spearman_by_aspect=spearman_by_aspect,
                    spearman_mean=(
                        sum(spearman_by_aspect.values()) / len(spearman_by_aspect)
                        if spearman_by_aspect
                        else float("nan")
                    ),
                    spearman_n_variants=n_variants,
                    coverage=coverage,
                    expected_calibration_error=ece,
                )
            )
    return results


def run_fusion_experiment(
    session: Session,
    *,
    variant_limit: int | None = None,
    ks: tuple[int, ...] = DEFAULT_K,
    replicates: int = DEFAULT_REPLICATES,
    seed: int = 20260905,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES // 4,
) -> ExperimentReport:
    """Run the experiment and the ablation it requires.

    Returns a report even when nothing could be measured, because "no variant
    has five verified long-term owners" is a finding about the corpus and
    needs saying out loud rather than appearing as an empty table.
    """
    strategies = sorted(_strategy_params(session))
    notes: list[str] = []

    targets, pools, sources = _collect(session, variant_limit, use_metadata=True)
    report = ExperimentReport(
        eligible_variants=len({t.variant_id for t in targets}),
        gold_targets=len(targets),
        replicates=replicates,
        sources_present=sources,
    )

    if not targets:
        report.notes.append(
            "No variant has at least "
            f"{MIN_GOLD_UNITS} verified owners with {GOLD_MIN_MONTHS}+ months and "
            f"{GOLD_MIN_KM:,}+ km. The experiment needs a source that verifies "
            "ownership; Reddit and YouTube do not, so is_verified_owner is null "
            "on every unit they produce."
        )
        return report

    report.results = _evaluate(
        targets,
        pools,
        strategies,
        ks=ks,
        replicates=replicates,
        seed=seed,
        bootstrap_samples=bootstrap_samples,
    )

    # The ablation. Same targets, same draws, weights recomputed with every
    # metadata signal removed. If the gap is small, "learned credibility" is
    # mostly a restatement of the platform's own verified flag.
    ablation_targets, ablation_pools, _ = _collect(session, variant_limit, use_metadata=False)
    report.ablation = _evaluate(
        ablation_targets,
        ablation_pools,
        strategies,
        ks=ks,
        replicates=replicates,
        seed=seed,
        bootstrap_samples=bootstrap_samples,
    )
    notes.append(
        "Coverage is the share of bootstrap intervals containing the gold "
        "consensus. The bootstrap quantifies sampling variation within the "
        "pool, so coverage below the nominal level means the pool and the "
        "verified owners disagree systematically, not that the interval "
        "arithmetic is wrong. That gap is the finding, not a defect."
    )
    notes.append(
        "The ablation removes is_verified_owner, ownership duration and "
        "distance from the weighting only. The gold set is still defined by "
        "them, which is what keeps the target independent of the estimators."
    )
    if len(sources) < 2:
        notes.append(
            f"Only {len(sources)} source in the pool, so source_weighted cannot "
            "differ from equal by construction."
        )
    if sources and all(s.startswith("fixture") for s in sources):
        notes.append(
            "EVERY SOURCE IN THIS RUN IS SYNTHETIC. These numbers describe the "
            "fixture generator, whose covariate effects we chose ourselves, and "
            "they are not evidence about anything. The experiment is only a "
            "finding once real evidence is in the pool."
        )
    report.notes.extend(notes)
    return report
