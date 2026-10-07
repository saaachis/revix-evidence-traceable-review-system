"""The two-wheeler path and the small readers around it.

The car path is covered elsewhere; this pins the pieces that only a bike
exercises (no published specs, displacement read from the name) and the field
readers that tolerate the shapes two sites disagree on.
"""

from __future__ import annotations

from revix_pipeline.catalogue_discovery import (
    Candidate,
    DiscoveredVariant,
    _bike_variant,
    _described,
    _first,
    _number,
    transmission_of,
)


def candidate(body_style: str = "motorcycle", name: str = "Classic 350") -> Candidate:
    return Candidate(
        manufacturer="Royal Enfield",
        name=name,
        slug="classic-350",
        vehicle_class="two-wheeler",
        body_style=body_style,
        segment="cruiser",
        launch_year=2021,
        source_make="royal-enfield",
        source_model="classic-350",
    )


class TestFieldReaders:
    def test_a_one_element_list_is_unwrapped(self) -> None:
        assert _first(["only"]) == "only"
        assert _first([]) is None
        assert _first("already-scalar") == "already-scalar"

    def test_a_number_is_pulled_out_of_a_noisy_string(self) -> None:
        assert _number("1,497 cc") == 1497.0
        assert _number("17.4 kmpl") == 17.4
        assert _number(None) is None
        assert _number("no digits here") is None

    def test_either_sites_description_casing_is_read(self) -> None:
        assert _described({"Description": "Cap D"}) == "Cap D"
        assert _described({"description": "lower d"}) == "lower d"
        assert _described({}) == ""


class TestTransmissionOf:
    def test_the_name_wins_when_it_is_specific(self) -> None:
        # A name that states the gearbox beats the site's coarse word.
        assert transmission_of("SX (O) Turbo DCT", "Automatic") == "dct"

    def test_it_falls_back_to_the_sites_word(self) -> None:
        assert transmission_of("Base", "Manual") == "mt"
        assert transmission_of("Base", "Automatic") == "at"

    def test_it_defaults_to_manual_when_nothing_is_said(self) -> None:
        assert transmission_of("Base", None) == "mt"


class TestBikeVariant:
    def test_a_scooter_gets_a_cvt_and_a_motorcycle_a_manual_box(self) -> None:
        scooter = _bike_variant("STD", {"_price": 80000}, candidate(body_style="scooter"))
        motorcycle = _bike_variant("STD", {"_price": 200000}, candidate(body_style="motorcycle"))
        assert scooter.transmission == "cvt"
        assert motorcycle.transmission == "mt"
        assert scooter.fuel_type == motorcycle.fuel_type == "petrol"

    def test_displacement_is_read_from_the_name(self) -> None:
        variant = _bike_variant("Classic 350", {"_price": 200000}, candidate())
        assert variant.engine_cc == 350
        assert variant.price_min == 200000


class TestAsDict:
    def test_absent_specs_are_omitted_and_a_price_fills_both_bounds(self) -> None:
        variant = DiscoveredVariant(
            variant_name="SX (O)",
            fuel_type="diesel",
            transmission="at",
            price_min=1920000,
            engine_cc=1493,
        )
        out = variant.as_dict()
        assert out["engine_cc"] == 1493
        assert out["price_min"] == out["price_max"] == 1920000
        # A field left as None never appears.
        assert "boot_litres" not in out
