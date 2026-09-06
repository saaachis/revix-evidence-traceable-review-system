"""CarWale, offline.

The payload is the real shape, trimmed. What matters here is what CarWale has
that CarDekho does not: a date on every review, and pagination that returns
genuinely different reviews rather than page one again.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from revix_pipeline.connectors import registry
from revix_pipeline.connectors.base import CatalogSeed, ExternalRef, RawPayload
from revix_pipeline.connectors.carwale import CarWaleConnector

CAR = CatalogSeed("1", "Hyundai", "Creta", "SX (O) Turbo DCT", "car")
BIKE = CatalogSeed("2", "Royal Enfield", "Classic 350", "Chrome", "two_wheeler")

PRODUCT = {
    "@type": "Product",
    "name": "Hyundai Creta",
    "review": [
        {
            "@type": "Review",
            "author": {"@type": "Person", "name": "Er Mohit Kumar Sahyogi "},
            "datePublished": "2024-09-07T00:32:40+05:30",
            "name": "Creative CRETA",
            "reviewBody": (
                "I purchased the SX(O) diesel recently and am happy to have it. "
                "Comfortable driving and seating, nice interiors and exteriors."
            ),
            "reviewRating": {"@type": "Rating", "ratingValue": "5"},
        },
        {
            "@type": "Review",
            "author": {"@type": "Person", "name": "CarWale User"},
            "datePublished": "2023-01-02T10:00:00+05:30",
            "name": "Good",
            "reviewBody": "ok",
            "reviewRating": {"@type": "Rating", "ratingValue": "3"},
        },
    ],
}


def _raw(url: str = "https://www.carwale.com/hyundai-cars/creta/reviews/") -> RawPayload:
    html = f'<html><script type="application/ld+json">{json.dumps(PRODUCT)}</script></html>'
    return RawPayload(
        ref=ExternalRef(external_id=url, url=url, seed=CAR, hint={"model": "Hyundai Creta"}),
        body=html.encode("utf-8"),
        fetched_at=datetime.now(UTC),
        http_status=200,
    )


class TestParsing:
    connector = CarWaleConnector()

    def test_a_one_word_review_is_not_evidence(self) -> None:
        assert len(self.connector.parse(_raw())) == 1

    def test_every_review_carries_its_date(self) -> None:
        """The whole reason this source is worth having: CarDekho has none,
        so the recency weighting had nothing to work with on real data."""
        draft = self.connector.parse(_raw())[0]
        assert draft.published_at is not None
        assert draft.published_at.tzinfo is not None
        assert draft.published_at.year == 2024

    def test_the_star_rating_survives(self) -> None:
        draft = self.connector.parse(_raw())[0]
        assert draft.rating_raw == 5.0
        assert draft.rating_normalized == 1.0

    def test_the_site_placeholder_is_not_treated_as_a_person(self) -> None:
        """ "CarWale User" is what an unnamed post shows, not somebody's name."""
        assert self.connector.parse(_raw())[0].author_ref == "Er Mohit Kumar Sahyogi"

    def test_ownership_is_never_asserted_as_verified(self) -> None:
        for draft in self.connector.parse(_raw()):
            assert draft.is_verified_owner is None

    def test_a_named_trim_reaches_the_resolver(self) -> None:
        draft = self.connector.parse(_raw())[0]
        assert draft.variant_hint is not None
        assert "sx(o)" in draft.variant_hint
        assert draft.listing_title.startswith("Hyundai Creta")

    def test_identity_ignores_the_page_number(self) -> None:
        """A review moves from page 3 to page 4 as newer ones arrive above it.
        If the page were part of its identity it would be inserted twice."""
        page3 = self.connector.parse(_raw("https://www.carwale.com/x/y/reviews/?page=3"))
        page4 = self.connector.parse(_raw("https://www.carwale.com/x/y/reviews/?page=4"))
        assert [d.external_id for d in page3] == [d.external_id for d in page4]

    def test_a_non_200_yields_nothing(self) -> None:
        raw = _raw()
        broken = RawPayload(ref=raw.ref, body=raw.body, fetched_at=raw.fetched_at, http_status=503)
        assert self.connector.parse(broken) == []


class TestDiscovery:
    def test_it_asks_for_several_pages_because_they_differ(self) -> None:
        """CarDekho ignores ?page and returns page one; CarWale does not."""
        refs = list(CarWaleConnector(pages_per_model=4).discover(CAR))
        assert len(refs) == 4
        assert refs[0].url.endswith("/reviews/")
        assert refs[3].url.endswith("?page=4")

    def test_two_wheelers_go_to_bikewale(self) -> None:
        """Same publisher, so the same source key: counting BikeWale
        separately from CarWale would inflate our own source count."""
        refs = list(CarWaleConnector().discover(BIKE))
        assert len(refs) == 1
        assert refs[0].url == "https://www.bikewale.com/royalenfield-bikes/classic-350/reviews/"

    def test_bikewale_uses_its_own_spelling_of_a_manufacturer(self) -> None:
        """ "Royal Enfield" is one word there, "Hero MotoCorp" loses half."""
        for mfr, expected in (
            ("Hero MotoCorp", "hero"),
            ("TVS Motor", "tvs"),
            ("Bajaj Auto", "bajaj"),
        ):
            seed = CatalogSeed("9", mfr, "Some Model", "Base", "two_wheeler")
            url = next(iter(CarWaleConnector().discover(seed))).url
            assert f"/{expected}-bikes/" in url, url

    def test_a_bike_page_asks_for_one_page_only(self) -> None:
        """BikeWale ignores ?page and returns the same ten reviews."""
        refs = list(CarWaleConnector(pages_per_model=5).discover(BIKE))
        assert len(refs) == 1
        assert "?page=" not in refs[0].url

    def test_one_model_is_visited_once_however_many_variants_share_it(self) -> None:
        connector = CarWaleConnector(pages_per_model=2)
        assert len(list(connector.discover(CAR))) == 2
        sibling = CatalogSeed("9", "Hyundai", "Creta", "E 1.5 Petrol MT", "car")
        assert list(connector.discover(sibling)) == []

    def test_the_slug_matches_what_the_site_uses(self) -> None:
        refs = list(
            CarWaleConnector(pages_per_model=1).discover(
                CatalogSeed("3", "Maruti Suzuki", "Swift", "VXi", "car")
            )
        )
        assert refs[0].url == "https://www.carwale.com/maruti-suzuki-cars/swift/reviews/"


class TestRegistration:
    def test_it_is_a_distinct_source_from_cardekho(self) -> None:
        """Different publishers: CarTrade and Girnar. Counting two sites owned
        by one company as two sources would game our own evidence floor."""
        assert "carwale" in registry
        assert "cardekho" in registry
        assert registry.get("carwale").source_key != registry.get("cardekho").source_key


BIKEWALE_CARD = """
<html><body>
  <div class="o-xY">
    <a href="/honda-bikes/activa-125/reviews/271352/">Best scooty in 125cc</a>
    <div></div>
    <div>6 years ago Soutam Ghosh</div>
    <div>Mileage is genuinely good at 57 km per litre in city riding, and the
         front disc brake gives real confidence in traffic. Seat is comfortable
         for a pillion on longer rides too.</div>
    <div>Was this review helpful? 41 9</div>
  </div>
  <div class="o-xY">
    <a href="/honda-bikes/activa-125/reviews/271353/">Short</a>
    <div>2 months ago Someone</div>
    <div>ok</div>
    <div>Was this review helpful? 1 0</div>
  </div>
</body></html>
"""


class TestBikeWaleCards:
    """Read by the shape of the card, because the class names are hashed and
    change on every deploy while a title/date/body/votes card does not."""

    def _raw(self) -> RawPayload:
        url = "https://www.bikewale.com/honda-bikes/activa-125/reviews/"
        return RawPayload(
            ref=ExternalRef(external_id=url, url=url, seed=BIKE, hint={"model": "Honda Activa"}),
            body=BIKEWALE_CARD.encode("utf-8"),
            fetched_at=datetime.now(UTC),
            http_status=200,
        )

    def test_a_substantial_card_becomes_evidence_and_a_one_word_one_does_not(self) -> None:
        assert len(CarWaleConnector().parse(self._raw())) == 1

    def test_the_body_is_the_longest_child_not_the_first(self) -> None:
        draft = CarWaleConnector().parse(self._raw())[0]
        assert "57 km per litre" in draft.text
        assert "Was this review helpful" not in draft.text

    def test_the_author_is_read_from_the_date_line(self) -> None:
        assert CarWaleConnector().parse(self._raw())[0].author_ref == "Soutam Ghosh"

    def test_a_relative_age_becomes_an_approximate_date(self) -> None:
        """Approximate is worth having: recency weighting cares about the year,
        not which Tuesday it was."""
        draft = CarWaleConnector().parse(self._raw())[0]
        assert draft.published_at is not None
        assert 2000 < draft.published_at.year < datetime.now(UTC).year + 1

    def test_helpful_votes_are_captured(self) -> None:
        """CarDekho has none of these, so they are worth reading here."""
        draft = CarWaleConnector().parse(self._raw())[0]
        assert draft.helpful_votes == 41
        assert draft.total_votes == 50

    def test_ownership_is_still_never_asserted(self) -> None:
        for draft in CarWaleConnector().parse(self._raw()):
            assert draft.is_verified_owner is None


class TestPaginationStopsWhenAModelRunsOut:
    """discover() has to yield every page up front, since it cannot know where
    a model's list ends. fetch() is where that guess gets corrected."""

    def _page(self, url: str, body: bytes = b"", status: int | None = 200) -> RawPayload:
        return RawPayload(
            ref=ExternalRef(external_id=url, url=url, seed=CAR, hint={"model": "Hyundai Creta"}),
            body=body,
            fetched_at=datetime.now(UTC),
            http_status=status,
        )

    def _html(self, *titles: str) -> bytes:
        product = {
            "@type": "Product",
            "review": [
                {
                    "@type": "Review",
                    "author": {"@type": "Person", "name": "A Person"},
                    "datePublished": "2024-09-07T00:32:40+05:30",
                    "name": title,
                    "reviewBody": (
                        f"{title}: the ride is comfortable and the mileage is genuinely "
                        "good in city traffic, no complaints after a year."
                    ),
                    "reviewRating": {"@type": "Rating", "ratingValue": "4"},
                }
                for title in titles
            ],
        }
        return (
            f'<html><script type="application/ld+json">{json.dumps(product)}</script></html>'
        ).encode()

    def test_an_empty_page_ends_the_model(self) -> None:
        """Past the last page CarWale serves the shell with no reviews in it.

        The first version required a page to be non-empty before it counted as
        exhausted, so the early stop never fired and every model paid for all
        twenty pages.
        """
        c = CarWaleConnector()
        base = "https://www.carwale.com/hyundai-cars/creta/reviews/"
        c.parse(self._page(base, self._html("One", "Two")))
        c.parse(self._page(f"{base}?page=2", self._html()))

        after = c.fetch(ExternalRef(external_id=f"{base}?page=3", url=f"{base}?page=3", seed=CAR))
        assert after.http_status is None, "a request was made after the list ended"
        assert after.body == b""

    def test_a_page_that_only_repeats_earlier_reviews_ends_the_model(self) -> None:
        c = CarWaleConnector()
        base = "https://www.carwale.com/hyundai-cars/creta/reviews/"
        c.parse(self._page(base, self._html("One", "Two")))
        c.parse(self._page(f"{base}?page=2", self._html("One", "Two")))

        after = c.fetch(ExternalRef(external_id=f"{base}?page=3", url=f"{base}?page=3", seed=CAR))
        assert after.http_status is None

    def test_a_page_with_new_reviews_does_not_end_the_model(self) -> None:
        c = CarWaleConnector()
        base = "https://www.carwale.com/hyundai-cars/creta/reviews/"
        c.parse(self._page(base, self._html("One", "Two")))
        c.parse(self._page(f"{base}?page=2", self._html("Three", "Four")))
        assert base not in c._exhausted

    def test_one_model_running_out_does_not_stop_another(self) -> None:
        c = CarWaleConnector()
        creta = "https://www.carwale.com/hyundai-cars/creta/reviews/"
        venue = "https://www.carwale.com/hyundai-cars/venue/reviews/"
        c.parse(self._page(creta, self._html()))
        assert creta in c._exhausted
        assert venue not in c._exhausted

    def test_the_ceiling_is_a_ceiling_not_a_target(self) -> None:
        refs = list(CarWaleConnector().discover(CAR))
        assert len(refs) == 20
