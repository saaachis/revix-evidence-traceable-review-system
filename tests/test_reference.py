"""The fixed vocabulary must stay fixed.

These are cheap tests, but they guard the two invariants the whole design
rests on: the taxonomy is exactly nine, and a weighting configuration is
identified by the hash of its parameters.
"""

from __future__ import annotations

from revix_core.enums import (
    ASPECT_GROUPS,
    ASPECT_LABELS,
    AspectKey,
    VehicleClass,
)
from revix_pipeline.reference import ASPECT_ORDER, FUSION_CONFIGS, config_hash


class TestAspectTaxonomy:
    def test_taxonomy_is_exactly_nine(self) -> None:
        """Proposal section 6.3: adding two-wheelers did not widen the taxonomy."""
        assert len(AspectKey) == 9

    def test_every_aspect_has_labels_for_both_vehicle_classes(self) -> None:
        for key in AspectKey:
            assert key in ASPECT_LABELS, f"{key} has no labels"
            for vehicle_class in VehicleClass:
                label = ASPECT_LABELS[key].get(vehicle_class)
                assert label, f"{key} has no label for {vehicle_class}"

    def test_car_and_two_wheeler_labels_differ_where_they_should(self) -> None:
        """A motorcycle has no interior, so two labels are re-read per class."""
        differing = {
            key
            for key in AspectKey
            if ASPECT_LABELS[key][VehicleClass.CAR] != ASPECT_LABELS[key][VehicleClass.TWO_WHEELER]
        }
        assert differing == {
            AspectKey.SPACE_COMFORT,
            AspectKey.FEATURES,
            AspectKey.RIDE_HANDLING_NVH,
        }

    def test_every_aspect_belongs_to_a_credibility_group(self) -> None:
        """aspect_fit needs a group for every aspect or the weight is undefined."""
        assert set(ASPECT_GROUPS) == set(AspectKey)

    def test_seed_order_covers_the_taxonomy_exactly_once(self) -> None:
        assert len(ASPECT_ORDER) == len(AspectKey)
        assert set(ASPECT_ORDER) == set(AspectKey)


class TestFusionConfigs:
    def test_exactly_one_default(self) -> None:
        defaults = [c for c in FUSION_CONFIGS if c["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "credibility_weighted"

    def test_names_and_display_orders_are_unique(self) -> None:
        names = [c["name"] for c in FUSION_CONFIGS]
        orders = [c["display_order"] for c in FUSION_CONFIGS]
        assert len(set(names)) == len(names)
        assert len(set(orders)) == len(orders)

    def test_the_baseline_uses_no_weighting_at_all(self) -> None:
        """`equal` is the control. If any term crept in, the comparison is void."""
        equal = next(c for c in FUSION_CONFIGS if c["name"] == "equal")
        assert not any(v for k, v in equal["params"].items() if k.startswith("use_"))

    def test_credibility_uses_every_term(self) -> None:
        cred = next(c for c in FUSION_CONFIGS if c["name"] == "credibility_weighted")
        assert all(v for k, v in cred["params"].items() if k.startswith("use_"))

    def test_config_hash_is_stable_and_order_independent(self) -> None:
        a = config_hash({"alpha": 1, "beta": 2})
        b = config_hash({"beta": 2, "alpha": 1})
        assert a == b
        assert a == config_hash({"alpha": 1, "beta": 2})

    def test_config_hash_changes_when_a_parameter_changes(self) -> None:
        base = config_hash({"use_spam": True})
        assert base != config_hash({"use_spam": False})

    def test_every_config_hashes_differently(self) -> None:
        hashes = {config_hash(c["params"]) for c in FUSION_CONFIGS}
        assert len(hashes) == len(FUSION_CONFIGS)
