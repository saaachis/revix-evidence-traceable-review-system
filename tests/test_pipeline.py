"""Unit tests for the pipeline logic, none of which need a database.

These target the claims the project actually makes, not line coverage. If
aspect_fit stopped preferring a long-term owner on a durability question, the
central argument would be broken and no amount of green elsewhere would matter.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from revix_core.enums import AspectGroup, FuelType, Transmission
from revix_pipeline.catalogue import normalise_trim
from revix_pipeline.connectors.politeness import (
    CircuitBreaker,
    CircuitOpenError,
    TokenBucket,
)
from revix_pipeline.enrichment.credibility import (
    aspect_fit,
    launch_window_correction,
    recency_decay,
    reliability,
    spam_probability,
)
from revix_pipeline.enrichment.extract import (
    extract_from_text,
    score_sentence,
    split_sentences,
)
from revix_pipeline.enrichment.fuse import (
    Contribution,
    attribute_divergence,
    divergence_index,
    kish_effective_sample,
    to_ten,
    weighted_mean,
)
from revix_pipeline.enrichment.resolve import (
    detect_engine_cc,
    detect_fuel,
    detect_transmission,
)


class FakeUnit:
    """Just enough of an EvidenceUnit for the scoring functions."""

    def __init__(self, **kw: object) -> None:
        self.text: str = str(kw.get("text", "A perfectly ordinary review with 12000 km covered."))
        self.is_verified_owner = kw.get("is_verified_owner")
        self.helpful_votes = kw.get("helpful_votes")
        self.total_votes = kw.get("total_votes")
        self.ownership_duration_months = kw.get("ownership_duration_months")
        self.km_driven = kw.get("km_driven")
        self.published_at = kw.get("published_at")
        self.rating_normalized = kw.get("rating_normalized")


class TestTrimNormalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("SX (O) 1.5 Diesel AT", "sx-o-1-5-diesel-at"),
            ("SX Optional 1.5 Diesel Automatic", "sx-o-1-5-diesel-at"),
            ("SX Opt 1.5 CRDi Automatic", "sx-o-1-5-diesel-at"),
        ],
    )
    def test_the_same_car_spelled_three_ways_normalises_identically(
        self, raw: str, expected: str
    ) -> None:
        """This is the entity resolution problem in miniature."""
        assert normalise_trim(raw) == expected

    def test_engine_size_survives_normalisation(self) -> None:
        """1.2 and 1.5 are different engines and must not collapse together."""
        assert normalise_trim("1.2 Petrol") != normalise_trim("1.5 Petrol")


class TestHardConstraints:
    def test_fuel_is_detected_from_marketing_names(self) -> None:
        assert FuelType.DIESEL in detect_fuel("Creta 1.5 CRDi SX")
        assert FuelType.PETROL in detect_fuel("Taigun 1.0 TSI Highline")

    def test_transmission_is_detected(self) -> None:
        assert Transmission.DCT in detect_transmission("GT Plus 1.5 TSI DSG")
        assert Transmission.MT in detect_transmission("ZXi 1.2 Manual")

    def test_displacement_reads_both_ways_of_writing_it(self) -> None:
        assert detect_engine_cc("1497 cc") == 1497
        assert detect_engine_cc("Creta 1.5 diesel") == 1500

    def test_a_petrol_listing_never_reads_as_diesel(self) -> None:
        """The constraint that makes matching precise without a model."""
        assert FuelType.DIESEL not in detect_fuel("Creta 1.5 TSI petrol")


class TestSentimentBaseline:
    def test_a_complaint_scores_negative(self) -> None:
        polarity, _ = score_sentence("The infotainment lags and disconnects repeatedly.")
        assert polarity < 0

    def test_praise_scores_positive(self) -> None:
        polarity, _ = score_sentence("Ride quality is genuinely excellent and the cabin is quiet.")
        assert polarity > 0

    def test_a_sentence_with_no_opinion_carries_low_confidence(self) -> None:
        _, confidence = score_sentence("I bought it in March.")
        assert confidence < 0.2

    def test_extraction_files_a_sentence_under_the_topic_it_mentions(self) -> None:
        found = extract_from_text("The service centre took three weeks to find a spare part.")
        assert any(e.aspect.value == "service_aftersales" for e in found)

    def test_one_review_can_praise_one_topic_and_condemn_another(self) -> None:
        """The reason a single star rating loses information."""
        found = extract_from_text(
            "Ride quality is excellent and the cabin is quiet. "
            "The service centre is poor and spares took three weeks."
        )
        by_aspect = {e.aspect.value: e.polarity for e in found}
        assert by_aspect["ride_handling_nvh"] > 0
        assert by_aspect["service_aftersales"] < 0


class TestAspectConditionalCredibility:
    """The central argument of the project lives in these four tests."""

    def test_a_long_term_owner_outweighs_a_new_one_on_durability(self) -> None:
        new = FakeUnit(ownership_duration_months=1, km_driven=500)
        old = FakeUnit(ownership_duration_months=48, km_driven=60000)
        assert aspect_fit(old, AspectGroup.DURABILITY) > aspect_fit(new, AspectGroup.DURABILITY)

    def test_a_new_owner_is_not_penalised_on_first_impressions(self) -> None:
        """At 500 km you know exactly what the seats feel like."""
        new = FakeUnit(ownership_duration_months=1, km_driven=500)
        assert aspect_fit(new, AspectGroup.IMMEDIATE) >= 0.95

    def test_the_ordering_reverses_between_topics(self) -> None:
        """Not one trust score. The same person is a good and a bad witness."""
        new = FakeUnit(ownership_duration_months=1, km_driven=500)
        old = FakeUnit(ownership_duration_months=48, km_driven=60000)
        assert aspect_fit(new, AspectGroup.IMMEDIATE) > aspect_fit(old, AspectGroup.IMMEDIATE)
        assert aspect_fit(old, AspectGroup.DURABILITY) > aspect_fit(new, AspectGroup.DURABILITY)

    def test_someone_who_has_never_been_to_a_service_centre_says_little_about_service(
        self,
    ) -> None:
        never = FakeUnit(ownership_duration_months=2, km_driven=1200)
        regular = FakeUnit(ownership_duration_months=40, km_driven=45000)
        assert aspect_fit(never, AspectGroup.SERVICE) < 0.4
        assert aspect_fit(regular, AspectGroup.SERVICE) > 0.9

    def test_missing_metadata_is_neutral_rather_than_penalised(self) -> None:
        unknown = FakeUnit()
        assert 0.5 <= aspect_fit(unknown, AspectGroup.DURABILITY) <= 0.7


class TestSpamAndReliability:
    def test_a_short_generic_five_star_review_scores_high_for_spam(self) -> None:
        unit = FakeUnit(text="Best car in segment. Fully satisfied.", rating_normalized=1.0)
        assert spam_probability(unit) > 0.6

    def test_a_specific_verified_review_scores_low(self) -> None:
        unit = FakeUnit(
            text=(
                "Owned for 38 months and 61,000 km. The DCT hesitates in traffic "
                "but is excellent on the highway. Service cost about Rs 9,000."
            ),
            is_verified_owner=True,
        )
        assert spam_probability(unit) < 0.2

    def test_spam_is_a_weight_not_a_filter(self) -> None:
        """Down-weighted, never deleted. Nothing returns exactly 1.0."""
        unit = FakeUnit(text="Nice car.", rating_normalized=1.0)
        assert spam_probability(unit) < 1.0

    def test_verified_owners_are_more_reliable_than_anonymous_ones(self) -> None:
        anon = FakeUnit(text="It is fine, 10000 km so far.")
        verified = FakeUnit(text="It is fine, 10000 km so far.", is_verified_owner=True)
        assert reliability(verified) > reliability(anon)

    def test_the_honeymoon_is_discounted(self) -> None:
        fresh = FakeUnit(ownership_duration_months=1)
        settled = FakeUnit(ownership_duration_months=24)
        assert launch_window_correction(fresh) < launch_window_correction(settled)

    def test_older_opinions_decay(self) -> None:
        recent = FakeUnit(published_at=datetime.now(UTC) - timedelta(days=30))
        ancient = FakeUnit(published_at=datetime.now(UTC) - timedelta(days=1500))
        assert recency_decay(recent) > recency_decay(ancient)


class TestFusionArithmetic:
    def test_polarity_maps_onto_a_ten_point_scale(self) -> None:
        assert to_ten(-1.0) == 0.0
        assert to_ten(0.0) == 5.0
        assert to_ten(1.0) == 10.0

    def test_equal_weights_give_the_plain_mean(self) -> None:
        c = [_contribution(1.0, 0.5), _contribution(1.0, -0.5)]
        assert weighted_mean(c) == pytest.approx(0.0)

    def test_weighting_moves_the_answer(self) -> None:
        c = [_contribution(9.0, 0.5), _contribution(1.0, -0.5)]
        assert weighted_mean(c) == pytest.approx(0.4)

    def test_kish_equals_the_count_when_every_weight_is_equal(self) -> None:
        assert kish_effective_sample([1.0] * 40) == pytest.approx(40.0)

    def test_kish_falls_when_weights_are_lopsided(self) -> None:
        """The claim on the verdict page: 200 weak reviews < 30 strong ones."""
        many_weak = kish_effective_sample([0.02] * 199 + [1.0])
        few_strong = kish_effective_sample([1.0] * 30)
        assert many_weak < few_strong

    def test_kish_never_exceeds_the_sample_size(self) -> None:
        """n_eff above n would be nonsense, and was a real bug once."""
        for weights in ([1.0] * 10, [0.1, 0.9, 0.4], [0.5] * 3):
            assert kish_effective_sample(weights) <= len(weights) + 1e-9

    def test_divergence_is_zero_when_everyone_agrees(self) -> None:
        assert divergence_index([_contribution(1.0, 0.6) for _ in range(5)]) == 0.0

    def test_divergence_rises_when_opinion_splits(self) -> None:
        split = [_contribution(1.0, 0.6) for _ in range(5)]
        split += [_contribution(1.0, -0.6) for _ in range(4)]
        assert divergence_index(split) > 0.4


class TestCovariateAttribution:
    def test_it_finds_the_characteristic_that_explains_a_split(self) -> None:
        contributions = [_contribution(1.0, 0.8, verified=True) for _ in range(12)] + [
            _contribution(1.0, -0.8, verified=False) for _ in range(12)
        ]
        result = attribute_divergence(contributions)
        assert result is not None
        assert result["covariate"] == "verified"
        assert result["explained_share"] > 0.8

    def test_it_reports_nothing_when_nothing_explains_the_spread(self) -> None:
        """Better silent than confidently wrong about a pattern that is noise."""
        contributions = [
            _contribution(1.0, 0.5 if i % 2 else -0.5, verified=bool(i % 3)) for i in range(24)
        ]
        result = attribute_divergence(contributions)
        assert result is None or result["explained_share"] < 0.5

    def test_too_little_evidence_produces_no_claim(self) -> None:
        assert attribute_divergence([_contribution(1.0, 0.5) for _ in range(3)]) is None


class TestPoliteness:
    def test_the_bucket_allows_a_small_burst_then_throttles(self) -> None:
        bucket = TokenBucket(rate_per_minute=60, capacity=3)
        assert all(bucket.acquire(sleep=False) == 0.0 for _ in range(3))
        assert bucket.acquire(sleep=False) > 0.0

    def test_the_bucket_refills_over_time(self) -> None:
        bucket = TokenBucket(rate_per_minute=6000, capacity=1)
        bucket.acquire(sleep=False)
        time.sleep(0.05)
        assert bucket.acquire(sleep=False) == 0.0

    def test_the_breaker_opens_after_repeated_refusals(self) -> None:
        """Continuing to hammer a site returning 403 is useless and rude."""
        breaker = CircuitBreaker(threshold=3)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.is_open
        with pytest.raises(CircuitOpenError):
            breaker.check("some-source")

    def test_one_success_resets_it(self) -> None:
        breaker = CircuitBreaker(threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        assert breaker.failures == 0
        assert not breaker.is_open

    def test_it_half_opens_after_the_cooldown(self) -> None:
        breaker = CircuitBreaker(threshold=2, reset_after=0.01)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open
        time.sleep(0.02)
        assert not breaker.is_open


def _contribution(weight: float, polarity: float, *, verified: bool | None = None) -> Contribution:
    return Contribution(
        unit_id=object(),
        weight=weight,
        polarity=polarity,
        transmission="at",
        fuel="diesel",
        source_key="test",
        verified=verified,
        ownership_months=24,
        km_driven=20000,
    )


class TestTwoWheelerExtraction:
    """The lexicon was written by somebody thinking about a car.

    Measured on real BikeDekho reviews, 21 of 30 Pulsar NS200 reviews produced
    no opinion at all, which is why every two-wheeler on the site sat under the
    evidence floor. The source had the data; we were discarding it.
    """

    @pytest.mark.parametrize(
        "sentence",
        [
            "Chain needs adjustment every 2000 km which is annoying.",
            "Kick start works but the self start failed within a year.",
            "Handlebar vibration at 80 kmph is really bad.",
            "Seat height is too much for short riders and it feels awkward.",
            "The milage is around 55 kmpl which is very good for this segment.",
            "Disc brake grip is excellent even in the rain.",
        ],
    )
    def test_a_bike_review_produces_an_opinion(self, sentence: str) -> None:
        assert extract_from_text(sentence), f"nothing extracted from: {sentence}"

    def test_best_is_a_positive_word(self) -> None:
        """It was missing, and it is close to the most common evaluative word
        in an Indian owner review."""
        polarity, confidence = score_sentence("Best bike in this segment, engine is superb.")
        assert polarity > 0
        assert confidence >= 0.2


class TestSentenceSplitting:
    """Indian owner reviews use "....." the way other people use a comma."""

    def test_a_run_of_dots_is_one_pause_not_four_sentences(self) -> None:
        parts = split_sentences("The engine is smooth..... but the seat is hard.")
        assert len(parts) == 2
        assert all("....." not in p for p in parts)

    def test_fragments_too_short_to_carry_an_opinion_are_dropped(self) -> None:
        """ "It....." used to survive as a sentence and be scored as evidence."""
        assert "It" not in split_sentences("It..... the mileage is genuinely good here.")

    def test_a_decimal_does_not_end_a_sentence(self) -> None:
        parts = split_sentences("It is powered by a 199.5 cc engine which feels strong.")
        assert len(parts) == 1

    def test_ordinary_sentences_still_split(self) -> None:
        assert len(split_sentences("The ride is good. The service is poor.")) == 2
