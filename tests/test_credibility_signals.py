"""The credibility signals, read off constructed evidence units.

These are the functions the whole weighting argument rests on, and each is a
pure reading of one review. They are exercised here with lightweight stand-ins
carrying only the attributes each signal inspects, so the behaviour is pinned
without a database or a scoring pass over one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from revix_core.enums import AspectGroup, AspectKey
from revix_pipeline.enrichment.credibility import (
    Credibility,
    aspect_fit,
    compute_credibility,
    credibility_from_json,
    launch_window_correction,
    recency_decay,
    reliability,
    spam_probability,
)


def unit(
    text: str = "Owned 24 months and 20000 km. The gearbox is smooth and the mileage is 18 kmpl.",
    *,
    verified: bool = True,
    rating: float | None = 0.8,
    helpful: int | None = 10,
    total: int | None = 20,
    months: int | None = 24,
    km: int | None = 20000,
    published: datetime | None = None,
) -> Any:
    return SimpleNamespace(
        text=text,
        is_verified_owner=verified,
        rating_normalized=rating,
        helpful_votes=helpful,
        total_votes=total,
        ownership_duration_months=months,
        km_driven=km,
        published_at=published,
    )


class TestSpam:
    def test_a_short_generic_five_star_review_scores_high(self) -> None:
        u = unit(
            "Best car in segment, value for money, fully satisfied.", verified=False, rating=1.0
        )
        assert spam_probability(u) >= 0.6

    def test_a_long_specific_verified_review_scores_low(self) -> None:
        u = unit(
            "After 30000 km and 24 months the clutch needed service at 18000 km, "
            "costing about Rs 4000, and the mileage settled near 16 kmpl in the city.",
            verified=True,
            rating=0.8,
        )
        assert spam_probability(u) <= 0.2

    def test_the_score_is_bounded_to_the_unit_interval(self) -> None:
        worst = unit("nice car", verified=False, rating=1.0)
        assert 0.0 <= spam_probability(worst) <= 1.0


class TestReliability:
    def test_a_verified_owner_is_more_reliable_with_metadata_than_without(self) -> None:
        u = unit(verified=True)
        assert reliability(u, use_metadata=True) > reliability(u, use_metadata=False)

    def test_reliability_never_drops_below_the_floor(self) -> None:
        bare = unit("ok", verified=False, helpful=0, total=0)
        assert reliability(bare, use_metadata=False) >= 0.05

    def test_helpful_votes_raise_reliability(self) -> None:
        plain = unit(helpful=0, total=0)
        endorsed = unit(helpful=40, total=40)
        assert reliability(endorsed) > reliability(plain)


class TestAspectFit:
    def test_no_metadata_is_neutral_rather_than_penalised(self) -> None:
        anon = unit(months=None, km=None)
        assert aspect_fit(anon, AspectGroup.DURABILITY) == 0.6

    def test_long_ownership_is_a_good_witness_to_durability(self) -> None:
        veteran = unit(months=48, km=60000)
        newcomer = unit(months=1, km=500)
        assert aspect_fit(veteran, AspectGroup.DURABILITY) > aspect_fit(
            newcomer, AspectGroup.DURABILITY
        )

    def test_a_first_impression_is_best_judged_early(self) -> None:
        fresh = unit(months=3)
        assert aspect_fit(fresh, AspectGroup.IMMEDIATE) == 1.0


class TestRecencyAndLaunchWindow:
    def test_an_undated_review_gets_a_stated_default(self) -> None:
        assert recency_decay(unit(published=None)) == 0.7

    def test_a_recent_review_decays_less_than_an_old_one(self) -> None:
        recent = unit(published=datetime.now(UTC) - timedelta(days=30))
        old = unit(published=datetime.now(UTC) - timedelta(days=1080))
        assert recency_decay(recent) > recency_decay(old)

    def test_a_naive_timestamp_is_treated_as_utc_without_crashing(self) -> None:
        naive = unit(published=datetime.now() - timedelta(days=10))  # noqa: DTZ005
        assert 0.0 < recency_decay(naive) <= 1.0

    def test_a_honeymoon_review_is_down_weighted(self) -> None:
        assert launch_window_correction(unit(months=1)) == 0.7
        assert launch_window_correction(unit(months=12)) == 1.0
        assert launch_window_correction(unit(months=None)) == 1.0


class TestComputeAndReadBack:
    def test_the_computed_vector_is_internally_consistent(self) -> None:
        cred = compute_credibility(unit())
        assert isinstance(cred, Credibility)
        assert 0.0 <= cred.base <= 1.0
        # Every per-aspect figure is the base scaled by that aspect's fit, so
        # none can exceed the base it was derived from.
        for group_value in (cred.durability, cred.immediate, cred.service, cred.efficiency):
            assert group_value <= cred.base + 1e-9

    def test_an_unscored_unit_reads_back_as_the_neutral_vector(self) -> None:
        cred = credibility_from_json(None)
        assert cred.base == 0.5
        assert cred.for_aspect(AspectKey.ENGINE_GEARBOX) == 0.5

    def test_a_stored_vector_round_trips_through_json(self) -> None:
        original = compute_credibility(unit())
        restored = credibility_from_json(original.as_json())
        assert restored.base == original.base
        assert restored.for_aspect(AspectKey.LONG_TERM_RELIABILITY) == original.durability
