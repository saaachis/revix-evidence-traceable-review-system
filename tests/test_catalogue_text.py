"""Trim normalisation, the seed read, and spec completeness.

These are the small pure pieces of the catalogue that decide whether two
spellings of one trim are treated as the same car and how much of a spec sheet
is actually held. None of it needs a database.
"""

from __future__ import annotations

from revix_pipeline.catalogue import _completeness, load_seed, normalise_trim
from revix_pipeline.reference import config_hash


class TestNormaliseTrim:
    def test_two_spellings_of_one_trim_collapse_to_one_key(self) -> None:
        assert normalise_trim("SX (O)") == normalise_trim("SX Optional") == "sx-o"

    def test_an_automatic_badge_is_canonicalised(self) -> None:
        assert normalise_trim("1.5 Automatic") == "1-5-at"

    def test_a_decimal_engine_size_keeps_its_digits(self) -> None:
        # 1.5 and 1.2 are different engines, so the digits must survive.
        assert normalise_trim("1.5 Petrol") != normalise_trim("1.2 Petrol")

    def test_normalisation_is_idempotent(self) -> None:
        once = normalise_trim("  SX(O)  1.5   CRDi ")
        assert normalise_trim(once) == once


class TestCompleteness:
    def test_an_empty_spec_is_zero(self) -> None:
        assert _completeness({}) == 0.0

    def test_six_filled_fields_count_as_a_full_sheet(self) -> None:
        spec = {
            "engine_cc": 1497,
            "engine_power_bhp": 113,
            "arai_mileage_kmpl": 17.4,
            "price_min": 1100000,
            "seating_capacity": 5,
            "boot_litres": 433,
        }
        assert _completeness(spec) == 1.0

    def test_a_missing_value_does_not_count(self) -> None:
        assert _completeness({"engine_cc": 1497, "price_min": None}) < 0.5


class TestSeedAndConfigHash:
    def test_the_seed_file_reads_as_a_non_empty_mapping(self) -> None:
        payload = load_seed()
        assert isinstance(payload, dict)
        assert payload

    def test_the_config_hash_ignores_key_order(self) -> None:
        assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})

    def test_different_parameters_hash_differently(self) -> None:
        assert config_hash({"use_spam": True}) != config_hash({"use_spam": False})
