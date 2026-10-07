"""The fusion arithmetic, exercised on constructed evidence rather than a database.

Everything here operates on in-memory ``Contribution`` values and duck-typed
rows, so the scoring maths is pinned without a Postgres round trip. The point
is the branches that the end-to-end pipeline run never reaches: an empty
population, a single contributor, a negated majority, and each weighting signal
turned on by itself so one cannot quietly cancel another.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from revix_core.enums import AspectKey
from revix_pipeline.enrichment.fuse import (
    Contribution,
    attribute_divergence,
    bootstrap_interval,
    bootstrap_means,
    divergence_index,
    interval_from_means,
    kish_effective_sample,
    to_ten,
    weight_rows,
    weighted_mean,
)


def contrib(
    polarity: float,
    weight: float = 1.0,
    *,
    source_key: str = "owner",
    verified: bool | None = True,
    ownership_months: int | None = 24,
    km_driven: int | None = 20000,
) -> Contribution:
    return Contribution(
        unit_id=f"u{polarity}-{weight}",
        weight=weight,
        polarity=polarity,
        transmission="automatic",
        fuel="petrol",
        source_key=source_key,
        verified=verified,
        ownership_months=ownership_months,
        km_driven=km_driven,
    )


class TestTheScalarMaths:
    def test_polarity_maps_onto_a_ten_point_scale(self) -> None:
        assert to_ten(-1.0) == 0.0
        assert to_ten(0.0) == 5.0
        assert to_ten(1.0) == 10.0

    def test_the_effective_sample_falls_when_weight_concentrates(self) -> None:
        # Equal weights: every unit counts, so the effective sample is the count.
        assert kish_effective_sample([1.0, 1.0, 1.0, 1.0]) == 4.0
        # One unit carrying almost all the weight is close to a sample of one.
        assert kish_effective_sample([100.0, 1.0, 1.0]) < 1.2

    def test_a_degenerate_weight_vector_is_a_sample_of_zero(self) -> None:
        assert kish_effective_sample([]) == 0.0
        assert kish_effective_sample([0.0, 0.0]) == 0.0

    def test_the_weighted_mean_leans_toward_the_heavier_opinion(self) -> None:
        cs = [contrib(1.0, weight=3.0), contrib(-1.0, weight=1.0)]
        assert weighted_mean(cs) == 0.5

    def test_a_weightless_population_has_no_mean(self) -> None:
        assert weighted_mean([]) == 0.0
        assert weighted_mean([contrib(1.0, weight=0.0)]) == 0.0


class TestDisagreement:
    def test_unanimity_has_no_divergence(self) -> None:
        assert divergence_index([contrib(0.8), contrib(0.6), contrib(0.9)]) == 0.0

    def test_a_dissenting_minority_is_its_weight_share(self) -> None:
        # Three agree positive (weight 3), one dissents negative (weight 1).
        cs = [contrib(0.5), contrib(0.5), contrib(0.5), contrib(-0.5)]
        assert divergence_index(cs) == 0.25

    def test_an_empty_population_does_not_divide_by_zero(self) -> None:
        assert divergence_index([]) == 0.0


class TestTheBootstrapInterval:
    def test_one_contributor_is_its_own_interval(self) -> None:
        lo, hi = bootstrap_interval([contrib(0.4)])
        assert lo == hi == to_ten(0.4)

    def test_an_empty_population_collapses_to_zero(self) -> None:
        assert bootstrap_interval([]) == (0.0, 0.0)

    def test_the_interval_is_deterministic_and_brackets_the_mean(self) -> None:
        cs = [contrib(p) for p in (0.1, 0.3, 0.5, 0.7, 0.9, -0.1, 0.2, 0.6)]
        first = bootstrap_interval(cs, seed=7)
        second = bootstrap_interval(cs, seed=7)
        assert first == second, "the same seed must give the same interval"
        lo, hi = first
        assert lo <= to_ten(weighted_mean(cs)) <= hi

    def test_widening_the_sorted_draw_widens_the_interval(self) -> None:
        means = [float(x) for x in range(11)]  # 0..10 sorted
        narrow = interval_from_means(means, level=0.50)
        wide = interval_from_means(means, level=0.95)
        assert (wide[1] - wide[0]) >= (narrow[1] - narrow[0])

    def test_no_resamples_is_an_empty_draw(self) -> None:
        assert bootstrap_means([]) == []
        assert interval_from_means([], level=0.9) == (0.0, 0.0)


class TestAttributeDivergence:
    def test_too_few_contributors_explains_nothing(self) -> None:
        assert attribute_divergence([contrib(0.5) for _ in range(4)]) is None

    def test_a_single_opinion_with_no_spread_explains_nothing(self) -> None:
        # Eight identical contributions: variance is zero, so there is nothing
        # for any covariate to account for.
        assert attribute_divergence([contrib(0.5) for _ in range(8)]) is None

    def test_a_clean_split_on_one_covariate_is_found_and_named(self) -> None:
        verified_group = [contrib(0.9, verified=True) for _ in range(6)]
        unverified_group = [contrib(-0.9, verified=False) for _ in range(6)]
        result = attribute_divergence(verified_group + unverified_group)
        assert result is not None
        assert result["covariate"] == "verified"
        assert result["explained_share"] >= 0.8
        # Groups come back ordered by score, lowest first, each traceable.
        scores = [g["score"] for g in result["groups"]]
        assert scores == sorted(scores)
        assert sum(g["count"] for g in result["groups"]) == 12


class TestWeightRows:
    """``weight_rows`` turns loaded opinion rows into weighted contributions.

    The rows are ordinary 4-tuples in production; here they are small stand-ins
    carrying exactly the attributes the function reads, so each weighting signal
    can be switched on in isolation.
    """

    def _row(
        self,
        *,
        aspect: AspectKey = AspectKey.ENGINE_GEARBOX,
        polarity: float = 0.6,
        confidence: float = 1.0,
        spam: float = 0.0,
        prior: float = 0.5,
        variant_id: Any = "v1",
    ) -> tuple[Any, Any, Any, Any]:
        opinion = SimpleNamespace(aspect_key=aspect, polarity=polarity, confidence=confidence)
        unit = SimpleNamespace(
            id="unit-1",
            spam_probability=spam,
            credibility_json=None,
            variant_id=variant_id,
            is_verified_owner=True,
            ownership_duration_months=24,
            km_driven=20000,
            published_at=None,
        )
        source = SimpleNamespace(default_source_prior=prior, source_key="owner")
        variant = SimpleNamespace(
            transmission=SimpleNamespace(value="automatic"),
            fuel_type=SimpleNamespace(value="petrol"),
        )
        return (opinion, unit, source, variant)

    def test_the_bare_strategy_only_applies_extraction_confidence(self) -> None:
        by_aspect = weight_rows([self._row(confidence=0.8)], {})
        [c] = by_aspect[AspectKey.ENGINE_GEARBOX]
        assert c.weight == 0.8
        assert c.polarity == 0.6
        assert c.model_level is False

    def test_a_zero_confidence_opinion_is_dropped_entirely(self) -> None:
        assert weight_rows([self._row(confidence=0.0)], {}) == {}

    def test_the_source_prior_scales_the_weight(self) -> None:
        [c] = weight_rows([self._row(prior=0.4)], {"use_source_prior": True})[
            AspectKey.ENGINE_GEARBOX
        ]
        assert c.weight == 0.4

    def test_spam_probability_discounts_a_generic_review(self) -> None:
        [c] = weight_rows([self._row(spam=0.75)], {"use_spam": True})[AspectKey.ENGINE_GEARBOX]
        assert c.weight == 0.25

    def test_a_model_level_review_is_marked_and_discounted(self) -> None:
        by_aspect = weight_rows([self._row(variant_id=None)], {})
        [c] = by_aspect[AspectKey.ENGINE_GEARBOX]
        assert c.model_level is True
        assert 0.0 < c.weight < 1.0, "the model-level discount leaves it weaker, not gone"

    def test_every_signal_together_still_produces_a_usable_contribution(self) -> None:
        params = {
            "use_source_prior": True,
            "use_spam": True,
            "use_reliability": True,
            "use_aspect_fit": True,
            "use_recency": True,
            "use_launch_window": True,
            "use_metadata": True,
        }
        [c] = weight_rows([self._row()], params)[AspectKey.ENGINE_GEARBOX]
        assert c.weight > 0.0
