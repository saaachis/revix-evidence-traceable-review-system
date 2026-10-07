"""The fixture connector, which stands in for real sources in development.

It fetches nothing; it generates a deterministic corpus seeded by the variant
id, so a given variant always produces the same reviews and the rest of the
suite can assert on exact numbers. These tests pin that determinism and the
shape of what it produces, driving it with a minimal seed stand-in.
"""

from __future__ import annotations

from types import SimpleNamespace

from revix_pipeline.connectors.fixture import FixtureConnector


def seed(
    variant_id: str = "creta-sx-at",
    name: str = "SX (O) 1.5 Turbo DCT",
    *,
    manufacturer: str = "Hyundai",
    model: str = "Creta",
) -> SimpleNamespace:
    return SimpleNamespace(
        variant_id=variant_id,
        variant_name=name,
        manufacturer=manufacturer,
        model=model,
    )


class TestGeneration:
    def test_it_produces_exactly_the_requested_number_of_reviews(self) -> None:
        connector = FixtureConnector(per_variant=25)
        drafts = list(connector._generate(seed()))
        assert len(drafts) == 25

    def test_the_same_variant_always_produces_the_same_corpus(self) -> None:
        connector = FixtureConnector(per_variant=10)
        first = [d.text for d in connector._generate(seed())]
        second = [d.text for d in connector._generate(seed())]
        assert first == second, "seeded by the variant id, so it must be reproducible"

    def test_different_variants_produce_different_corpora(self) -> None:
        connector = FixtureConnector(per_variant=10)
        a = [d.text for d in connector._generate(seed("creta-e-mt", "E 1.5 Petrol MT"))]
        b = [d.text for d in connector._generate(seed("seltos-gtx", "GTX Plus DCT"))]
        assert a != b

    def test_each_draft_carries_the_metadata_the_weighting_needs(self) -> None:
        draft = next(iter(FixtureConnector(per_variant=5)._generate(seed())))
        assert draft.text.startswith("Owned for")
        assert 1.0 <= draft.rating_raw <= 5.0
        assert isinstance(draft.is_verified_owner, bool)
        assert draft.ownership_duration_months is not None
        assert draft.external_id.endswith("0000")


class TestTheConnectorSurface:
    def test_a_fetch_records_a_replayable_payload_without_touching_the_network(self) -> None:
        connector = FixtureConnector()
        ref = SimpleNamespace(external_id="fixture:creta-sx-at", seed=seed())
        payload = connector.fetch(ref)
        assert payload.http_status == 200
        assert payload.body

    def test_parse_turns_a_payload_back_into_drafts(self) -> None:
        connector = FixtureConnector(per_variant=8)
        raw = SimpleNamespace(ref=SimpleNamespace(seed=seed()))
        assert len(connector.parse(raw)) == 8

    def test_three_fixtures_can_stand_in_for_three_distinct_sources(self) -> None:
        # A single source makes source-weighting meaningless, which is the
        # reason the connector is parameterised by source key at all.
        owner = FixtureConnector(source_key="fixture_owner", source_prior=0.6)
        expert = FixtureConnector(source_key="fixture_expert", source_prior=0.9)
        assert owner.source_key != expert.source_key
        assert owner.default_source_prior != expert.default_source_prior
