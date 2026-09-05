"""The section 18.1 experiment, on data where the right answer is known.

An evaluation harness that is wrong is worse than no harness, because it
produces a number and a number gets believed. So these tests do not check that
the experiment runs; they construct corpora whose correct verdict is decided in
advance and check that it reaches it.
"""

from __future__ import annotations

import math

import pytest

from revix_pipeline.enrichment.fuse import Contribution, to_ten
from revix_pipeline.evaluation.fusion_experiment import (
    GOLD_MIN_KM,
    GOLD_MIN_MONTHS,
    gold_score,
    is_gold_unit,
    spearman,
    split_gold_and_pool,
)


def unit(
    uid: str,
    polarity: float,
    *,
    weight: float = 1.0,
    verified: bool | None = None,
    months: int | None = None,
    km: int | None = None,
    source: str = "s1",
) -> Contribution:
    return Contribution(
        unit_id=uid,
        weight=weight,
        polarity=polarity,
        transmission="manual",
        fuel="petrol",
        source_key=source,
        verified=verified,
        ownership_months=months,
        km_driven=km,
    )


class TestSpearman:
    def test_perfect_agreement(self) -> None:
        assert spearman([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0]) == pytest.approx(1.0)

    def test_perfect_disagreement(self) -> None:
        assert spearman([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0]) == pytest.approx(-1.0)

    def test_ties_get_average_ranks(self) -> None:
        """The shortcut formula is wrong when values repeat, so we do not use it."""
        rho = spearman([1.0, 2.0, 2.0, 3.0], [1.0, 2.0, 2.0, 3.0])
        assert rho == pytest.approx(1.0)

    def test_a_flat_series_has_no_correlation_rather_than_a_zero(self) -> None:
        assert math.isnan(spearman([5.0, 5.0, 5.0, 5.0], [1.0, 2.0, 3.0, 4.0]))

    def test_too_few_points_is_not_a_measurement(self) -> None:
        assert math.isnan(spearman([1.0, 2.0], [1.0, 2.0]))

    def test_known_value(self) -> None:
        """Ranks [1,2,3,4,5] against [1,2,5,3,4].

        d = [0, 0, -2, 1, 1], so sum d^2 = 6 and rho = 1 - 36/120 = 0.7. No
        ties here, so the shortcut formula is valid and worth checking the
        rank implementation against.
        """
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [1.0, 2.0, 5.0, 3.0, 4.0]
        assert spearman(xs, ys) == pytest.approx(1 - (6 * 6) / (5 * (25 - 1)))


class TestTheGoldSplit:
    """The whole non-circularity of the experiment rests on this boundary."""

    def test_all_three_conditions_are_required(self) -> None:
        assert is_gold_unit(unit("a", 0.5, verified=True, months=24, km=40_000))
        assert not is_gold_unit(unit("b", 0.5, verified=None, months=24, km=40_000))
        assert not is_gold_unit(unit("c", 0.5, verified=True, months=None, km=40_000))
        assert not is_gold_unit(unit("d", 0.5, verified=True, months=24, km=None))

    def test_the_thresholds_are_the_ones_the_proposal_names(self) -> None:
        assert not is_gold_unit(
            unit("e", 0.5, verified=True, months=GOLD_MIN_MONTHS - 1, km=GOLD_MIN_KM)
        )
        assert not is_gold_unit(
            unit("f", 0.5, verified=True, months=GOLD_MIN_MONTHS, km=GOLD_MIN_KM - 1)
        )
        assert is_gold_unit(unit("g", 0.5, verified=True, months=GOLD_MIN_MONTHS, km=GOLD_MIN_KM))

    def test_an_unverifiable_platform_contributes_no_gold(self) -> None:
        """Reddit and YouTube produce null verification on every unit."""
        reddit_like = [unit(str(i), 0.5, verified=None, months=36, km=90_000) for i in range(20)]
        gold, pool = split_gold_and_pool(reddit_like)
        assert gold == []
        assert len(pool) == 20

    def test_gold_units_are_removed_from_the_pool(self) -> None:
        """If they stayed, the estimate would contain its own target."""
        contributions = [
            unit("gold1", 0.8, verified=True, months=24, km=40_000),
            unit("gold2", 0.6, verified=True, months=18, km=20_000),
            unit("pool1", -0.2),
            unit("pool2", 0.1),
        ]
        gold, pool = split_gold_and_pool(contributions)
        assert {c.unit_id for c in gold} == {"gold1", "gold2"}
        assert {c.unit_id for c in pool} == {"pool1", "pool2"}
        assert not ({c.unit_id for c in gold} & {c.unit_id for c in pool})


class TestTheTarget:
    def test_the_gold_consensus_ignores_weights_entirely(self) -> None:
        """A target that shares a term with its estimators is not independent.

        Both units say the same thing; one is weighted twenty times heavier.
        The target must not notice.
        """
        heavy = unit("a", 1.0, weight=20.0, verified=True, months=24, km=40_000)
        light = unit("b", 0.0, weight=1.0, verified=True, months=24, km=40_000)
        assert gold_score([heavy, light]) == to_ten(0.5)

    def test_an_empty_gold_set_scores_zero_rather_than_dividing_by_zero(self) -> None:
        assert gold_score([]) == 0.0

    def test_the_scale_is_the_one_a_reader_sees(self) -> None:
        assert gold_score([unit("a", 1.0)]) == 10.0
        assert gold_score([unit("a", -1.0)]) == 0.0
        assert gold_score([unit("a", 0.0)]) == 5.0
