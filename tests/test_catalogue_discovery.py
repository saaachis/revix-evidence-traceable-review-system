"""Reading a catalogue out of what the sources publish about themselves.

The risk here is not a crash. It is a catalogue that looks fine and is wrong:
an on-road price recorded as ex-showroom, a decimal read as a whole number of
rupees, or a model that silently contributed nothing and was never noticed.
"""

from __future__ import annotations

import json

import pytest

from revix_pipeline.catalogue_discovery import (
    Candidate,
    _clean_name,
    _ex_showroom,
    car_specs,
    product_group,
    sample_variants,
    transmission_of,
)


def candidate(manufacturer: str = "Hyundai", name: str = "Creta") -> Candidate:
    return Candidate(
        manufacturer=manufacturer,
        name=name,
        slug="creta",
        vehicle_class="car",
        body_style="SUV",
        segment="midsize",
        launch_year=2015,
        source_make="hyundai",
        source_model="creta",
    )


class TestPrices:
    """Cars are quoted in lakh, two-wheelers in rupees, and the offer object
    alongside carries the on-road price, which is a different number."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Price in India is ₹10.91 Lakh.", 1_091_000),
            ("model price in India is ₹59,477. Check specifications", 59_477),
            ("is ₹1.2 Crore", 12_000_000),
            # A decimal with the unit missing. Eleven rupees is not a price,
            # and accepting it would put a rounding error on the compare page.
            ("is ₹10.91", None),
            ("no price here", None),
        ],
    )
    def test_ex_showroom(self, text: str, expected: int | None) -> None:
        assert _ex_showroom(text) == expected


class TestVariantNames:
    def test_the_make_and_model_are_stripped(self) -> None:
        assert _clean_name("Hyundai Creta SX (O) Turbo DCT", candidate()) == "SX (O) Turbo DCT"

    def test_the_source_spells_the_brand_its_own_way(self) -> None:
        """ "TVS Motor" appears as "TVS", so a whole-name prefix match failed
        and those rows kept reading "TVS NTORQ 125 Disc"."""
        c = candidate("TVS Motor", "Ntorq 125")
        assert _clean_name("TVS NTORQ 125 Disc", c) == "Disc"
        c = candidate("Suzuki Motorcycle", "Access 125")
        assert _clean_name("Suzuki Access 125 Standard Edition", c) == "Standard Edition"

    def test_a_name_that_is_all_noise_keeps_its_original(self) -> None:
        """Rather than emitting an empty variant name."""
        assert _clean_name("Hyundai Creta", candidate()) == "Hyundai Creta"

    def test_a_name_with_no_noise_is_untouched(self) -> None:
        assert _clean_name("Military", candidate("Royal Enfield", "Bullet 350")) == "Military"


class TestTransmission:
    def test_the_variant_name_beats_the_sites_coarse_word(self) -> None:
        """CarDekho only says Manual or Automatic, collapsing AMT, CVT and DCT
        into one bucket. A Creta DCT and a Creta CVT are different cars."""
        assert transmission_of("SX (O) Turbo DCT", "automatic") == "dct"
        assert transmission_of("VXi AMT", "automatic") == "amt"

    def test_the_site_word_is_used_when_the_name_is_silent(self) -> None:
        assert transmission_of("E", "manual") == "mt"
        assert transmission_of("SX", "automatic") == "at"

    def test_an_unknown_gearbox_does_not_crash(self) -> None:
        assert transmission_of("Base", None) == "mt"


class TestSampling:
    def _priced(self, *prices: int) -> list[dict[str, object]]:
        return [{"name": f"v{p}", "_price": p} for p in prices]

    def test_a_spread_across_the_price_ladder_not_the_cheapest(self) -> None:
        """A catalogue of base trims would make every verdict one about base
        trims. The entry car and the loaded one both have to be in."""
        picked = sample_variants(self._priced(100, 200, 300, 400, 500, 600), 3)
        assert [v["_price"] for v in picked] == [100, 300, 600]

    def test_everything_is_kept_when_there_is_little(self) -> None:
        assert len(sample_variants(self._priced(100, 200), 4)) == 2

    def test_a_source_that_stops_publishing_prices_still_yields_variants(self) -> None:
        """Returning nothing here is how nine two-wheelers silently vanished
        from a discovery run."""
        unpriced = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        assert len(sample_variants(unpriced, 2)) == 2


class TestParsing:
    def test_a_product_group_is_found_among_other_blocks(self) -> None:
        html = (
            '<script type="application/ld+json">{"@type":"WebPage"}</script>'
            '<script type="application/ld+json">'
            '{"@type":"ProductGroup","hasVariant":[{"name":"E"}]}</script>'
        )
        group = product_group(html)
        assert group is not None
        assert len(group["hasVariant"]) == 1

    def test_car_specs_are_read_from_the_car_object(self) -> None:
        car = {
            "@type": "Car",
            "vehicleEngine": [{"fuelType": "Diesel", "name": "1493"}],
            "vehicleTransmission": ["Automatic"],
            "fuelEfficiency": [{"name": "19.1"}],
            "vehicleSeatingCapacity": 5,
        }
        specs = car_specs(f'<script type="application/ld+json">{json.dumps(car)}</script>')
        assert specs["fuel_type"] == "diesel"
        assert specs["engine_cc"] == 1493
        assert specs["arai_mileage_kmpl"] == 19.1
        assert specs["seating_capacity"] == 5
        assert specs["gearbox_word"] == "automatic"

    def test_malformed_json_does_not_lose_the_page(self) -> None:
        html = (
            '<script type="application/ld+json">{not json</script>'
            '<script type="application/ld+json">{"@type":"ProductGroup","hasVariant":[]}</script>'
        )
        assert product_group(html) is not None


class TestTheSeededCatalogue:
    """The committed file is generated, so these guard the output, not the code."""

    def _catalogue(self) -> dict[str, object]:
        import pathlib

        return json.loads(pathlib.Path("data/seed/catalogue.json").read_text(encoding="utf-8"))

    def test_it_meets_the_scope_the_proposal_sets(self) -> None:
        """Section 25 asks for roughly 120 to 150 variants."""
        models = self._catalogue()["models"]
        variants = [v for m in models for v in m["variants"]]  # type: ignore[index,union-attr]
        assert len(variants) >= 100

    def test_every_variant_has_a_price(self) -> None:
        """The compare page pairs by price, so a missing one silently drops a
        vehicle out of every suggestion."""
        models = self._catalogue()["models"]
        missing = [
            v["variant_name"]
            for m in models  # type: ignore[union-attr]
            for v in m["variants"]
            if not v.get("price_min")
        ]
        assert missing == []

    def test_every_model_points_at_a_manufacturer_that_exists(self) -> None:
        """A model refers to its manufacturer by slug, not display name.

        Emitting the name produced a catalogue that read correctly and died in
        the seeder with KeyError: 'Maruti Suzuki'. The file is the wrong place
        to find that out; this is.
        """
        book = self._catalogue()
        slugs = {m["slug"] for m in book["manufacturers"]}  # type: ignore[union-attr]
        unknown = sorted(
            {
                m["manufacturer"]
                for m in book["models"]  # type: ignore[union-attr]
                if m["manufacturer"] not in slugs
            }
        )
        assert unknown == []

    def test_no_variant_name_repeats_its_own_make(self) -> None:
        models = self._catalogue()["models"]
        offenders = [
            f"{m['manufacturer']} / {v['variant_name']}"
            for m in models  # type: ignore[union-attr]
            for v in m["variants"]
            if v["variant_name"].casefold().startswith(m["manufacturer"].split()[0].casefold())
        ]
        assert offenders == []
