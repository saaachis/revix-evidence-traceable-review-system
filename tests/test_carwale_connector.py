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

    def test_two_wheelers_are_skipped_on_purpose(self) -> None:
        """BikeWale exposes one review per page however many you ask for."""
        assert list(CarWaleConnector().discover(BIKE)) == []

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
