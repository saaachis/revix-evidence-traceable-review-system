"""The CarDekho and BikeDekho connector, offline.

The payload below is the real shape, trimmed: schema.org Review objects inside
a Product's JSON-LD block, with the awkward cases these pages actually
contain. A placeholder author, a one-line review, a malformed block.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from revix_pipeline.connectors import registry
from revix_pipeline.connectors.base import CatalogSeed, ExternalRef, RawPayload
from revix_pipeline.connectors.dekho import DekhoConnector, _variant_tokens

SEED = CatalogSeed(
    variant_id="00000000-0000-0000-0000-000000000001",
    manufacturer="Hyundai",
    model="Creta",
    variant_name="SX (O) Turbo DCT",
    vehicle_class="car",
)

PRODUCT = {
    "@type": "Product",
    "name": "Hyundai Creta",
    "review": [
        {
            "@type": "Review",
            "author": {"@type": "Person", "name": "Triyax Chauhan"},
            "name": "Amazing Car Good For Long Route",
            "reviewBody": (
                "Bought the SX(O) diesel manual two years ago and have done 45,000 km. "
                "Ride quality is very good on the highway but the service centre "
                "experience has been poor every time."
            ),
            "reviewRating": {"@type": "Rating", "ratingValue": "4.6"},
        },
        {
            # The site's placeholder for a review posted without a display name.
            "@type": "Review",
            "author": {"@type": "Person", "name": "user"},
            "name": "Long Term Review",
            "reviewBody": (
                "Best vehicle in the Indian market if you want mileage and power "
                "within an affordable cost, no major issues so far at all."
            ),
            "reviewRating": {"@type": "Rating", "ratingValue": "4"},
        },
        # Too short to carry an opinion the extractor can use.
        {"@type": "Review", "name": "Good", "reviewBody": "nice car", "author": {"name": "x"}},
    ],
}


def _raw(html: str, url: str = "https://www.cardekho.com/hyundai/creta/user-reviews") -> RawPayload:
    return RawPayload(
        ref=ExternalRef(external_id=url, url=url, seed=SEED, hint={"model": "Hyundai Creta"}),
        body=html.encode("utf-8"),
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_type="text/html",
    )


def _page(*products: object) -> str:
    blocks = "".join(
        f'<script type="application/ld+json">{json.dumps(p)}</script>' for p in products
    )
    return f"<html><head>{blocks}</head><body>irrelevant markup</body></html>"


class TestParsing:
    connector = DekhoConnector()

    def test_substantial_reviews_become_evidence_and_one_liners_do_not(self) -> None:
        drafts = self.connector.parse(_raw(_page(PRODUCT)))
        assert len(drafts) == 2

    def test_the_star_rating_is_carried_and_normalised(self) -> None:
        """The first source in the project that has a rating at all."""
        first = self.connector.parse(_raw(_page(PRODUCT)))[0]
        assert first.rating_raw == 4.6
        assert first.rating_scale_max == 5.0
        assert first.rating_normalized == 0.92

    def test_the_placeholder_author_is_not_treated_as_a_person(self) -> None:
        """Pooling every anonymous poster into one reputation would be wrong."""
        drafts = self.connector.parse(_raw(_page(PRODUCT)))
        assert drafts[0].author_ref == "Triyax Chauhan"
        assert drafts[1].author_ref is None

    def test_ownership_is_never_asserted_as_verified(self) -> None:
        """Self-declared. Nothing here may enter the section 18.1 gold set."""
        for draft in self.connector.parse(_raw(_page(PRODUCT))):
            assert draft.is_verified_owner is None

    def test_no_date_is_invented(self) -> None:
        """The JSON-LD has none, and a fetch time would fake perfect recency."""
        for draft in self.connector.parse(_raw(_page(PRODUCT))):
            assert draft.published_at is None

    def test_a_review_that_names_its_trim_gets_its_own_listing(self) -> None:
        """This is the only thing that lets a model-level page reach a variant."""
        first = self.connector.parse(_raw(_page(PRODUCT)))[0]
        assert first.variant_hint is not None
        assert "sx (o)" in first.variant_hint or "sx(o)" in first.variant_hint
        assert "diesel" in first.variant_hint
        assert first.listing_title.startswith("Hyundai Creta")
        assert first.listing_title != "Hyundai Creta"

    def test_a_review_that_names_nothing_stays_at_model_level(self) -> None:
        second = self.connector.parse(_raw(_page(PRODUCT)))[1]
        assert second.listing_title == "Hyundai Creta"

    def test_ownership_signals_are_read_out_of_the_prose(self) -> None:
        first = self.connector.parse(_raw(_page(PRODUCT)))[0]
        assert first.km_driven == 45000
        assert first.ownership_duration_months == 24

    def test_identity_is_stable_across_refetches(self) -> None:
        """Reading the page again must recognise the same review, not re-add it."""
        a = self.connector.parse(_raw(_page(PRODUCT)))
        b = self.connector.parse(_raw(_page(PRODUCT)))
        assert [d.external_id for d in a] == [d.external_id for d in b]

    def test_a_malformed_block_does_not_cost_us_the_others(self) -> None:
        html = '<script type="application/ld+json">{not json</script>' + _page(PRODUCT)
        assert len(self.connector.parse(_raw(html))) == 2

    def test_a_non_200_yields_nothing(self) -> None:
        raw = _raw(_page(PRODUCT))
        broken = RawPayload(ref=raw.ref, body=raw.body, fetched_at=raw.fetched_at, http_status=404)
        assert self.connector.parse(broken) == []


class TestDiscovery:
    def test_the_two_hosts_are_chosen_by_vehicle_class(self) -> None:
        connector = DekhoConnector()
        car = next(iter(connector.discover(SEED)))
        bike_seed = CatalogSeed("2", "Royal Enfield", "Classic 350", "Chrome", "two_wheeler")
        bike = next(iter(connector.discover(bike_seed)))
        assert car.url == "https://www.cardekho.com/hyundai/creta/user-reviews"
        assert bike.url == "https://www.bikedekho.com/royal-enfield/classic-350/reviews"

    def test_one_model_page_is_visited_once_however_many_variants_share_it(self) -> None:
        """Six Creta variants must not fetch the same thirty reviews six times."""
        connector = DekhoConnector()
        assert len(list(connector.discover(SEED))) == 1
        sibling = CatalogSeed("9", "Hyundai", "Creta", "E 1.5 Petrol MT", "car")
        assert list(connector.discover(sibling)) == []


class TestRegistration:
    def test_it_is_registered_and_ranks_between_anonymous_and_expert(self) -> None:
        assert "cardekho" in registry
        prior = registry.get("cardekho").default_source_prior
        assert registry.get("youtube").default_source_prior < prior < 0.8


class TestVariantTokenExtraction:
    """These tokens become listing titles, so a false positive costs a row."""

    def test_a_rating_or_a_dimension_is_not_an_engine_size(self) -> None:
        """Live data produced "Tata Nexon 4.5" and "Tata Nexon 6.2" before this."""
        assert _variant_tokens("rated 4.5 stars overall") == ""
        assert _variant_tokens("ground clearance 6.2 inches") == ""

    def test_a_stated_engine_size_is_kept(self) -> None:
        assert "1.5" in _variant_tokens("the 1.5 turbo petrol is great")
        assert "1.2" in _variant_tokens("1.2 L engine")

    def test_a_word_containing_a_trim_is_not_a_trim(self) -> None:
        assert _variant_tokens("I am a petrolhead") == ""

    def test_the_bracketed_trim_survives_intact(self) -> None:
        """A trailing word boundary used to truncate this to "sx(o"."""
        assert _variant_tokens("bought the SX(O)") == "sx(o)"
        assert _variant_tokens("bought the SX ( O )") == "sx(o)"
