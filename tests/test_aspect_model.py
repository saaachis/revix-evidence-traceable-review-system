"""The aspect classifier, and the gold set that decides whether it earned its place.

The failure mode this file exists to prevent is not a crash. It is a
classifier that is measured against the rules it was trained from, scores 0.9,
and gets shipped while being worse than the rules at the actual job.
"""

from __future__ import annotations

import pathlib

import pytest

from revix_core.enums import AspectKey
from revix_core.settings import Settings
from revix_pipeline.ml.aspect_model import lexicon_aspects, score_predictions
from revix_pipeline.ml.gold import GoldItem, coverage, load_gold, save_gold


def item(uid: str, text: str, aspects: list[str], by: str = "a-person") -> GoldItem:
    return GoldItem(id=uid, text=text, aspects=aspects, labelled_by=by)


class TestTheGoldFormat:
    def test_an_empty_aspect_list_is_a_real_label(self) -> None:
        """A sentence about nothing in particular is a useful data point, so
        "labelled" means somebody signed it, not that the list is non-empty."""
        assert item("a", "The colour is red.", []).is_labelled

    def test_an_unsigned_item_is_not_labelled_however_full_it_looks(self) -> None:
        assert not GoldItem(id="b", text="x", aspects=["safety"], labelled_by="").is_labelled

    def test_a_typo_in_a_label_is_an_error_not_a_silent_drop(self) -> None:
        """Silently ignoring an unknown key would quietly shrink the gold set."""
        with pytest.raises(ValueError, match="unknown aspect"):
            _ = item("c", "x", ["safty"]).aspect_keys

    def test_a_round_trip_through_the_file_keeps_everything(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "gold.jsonl"
        original = [item("a", "Seats are soft.", ["space_comfort"]), item("b", "Hmm.", [])]
        save_gold(original, path)
        back = load_gold(path)
        assert [(i.id, i.aspects, i.labelled_by) for i in back] == [
            (i.id, i.aspects, i.labelled_by) for i in original
        ]

    def test_a_missing_file_is_an_empty_set_not_a_crash(self, tmp_path: pathlib.Path) -> None:
        assert load_gold(tmp_path / "nothing.jsonl") == []

    def test_coverage_counts_what_is_left_to_do(self) -> None:
        stats = coverage(
            [
                item("a", "x", ["safety"]),
                item("b", "y", []),
                GoldItem(id="c", text="z", labelled_by=""),
            ]
        )
        assert stats["total"] == 3
        assert stats["labelled"] == 2
        assert stats["unlabelled"] == 1
        assert stats["with_no_aspect"] == 1
        assert stats["safety"] == 1


class TestScoring:
    def test_a_perfect_system_scores_one(self) -> None:
        gold = [item("a", "x", ["safety"]), item("b", "y", ["running_cost"])]
        predictions = [{AspectKey.SAFETY}, {AspectKey.RUNNING_COST}]
        result = score_predictions("perfect", gold, predictions)
        assert result.macro_f1 == pytest.approx(1.0)
        assert result.micro_f1 == pytest.approx(1.0)

    def test_a_system_that_says_nothing_scores_zero(self) -> None:
        gold = [item("a", "x", ["safety"])]
        result = score_predictions("silent", gold, [set()])
        assert result.macro_f1 == 0.0

    def test_macro_notices_a_topic_that_micro_hides(self) -> None:
        """The whole reason both are reported.

        Nine sentences about a common topic handled perfectly, one about a
        rare topic missed entirely. Micro barely moves; macro should fall.
        """
        gold = [item(str(i), "x", ["features"]) for i in range(9)]
        gold.append(item("rare", "y", ["service_aftersales"]))
        predictions: list[set[AspectKey]] = [{AspectKey.FEATURES} for _ in range(9)]
        predictions.append(set())

        result = score_predictions("lopsided", gold, predictions)
        assert result.micro_f1 > 0.9
        # Two topics in play, one perfect and one missed entirely, so macro
        # sits at 0.5 while micro stays above 0.9. The gap is the point.
        assert result.macro_f1 == pytest.approx(0.5)
        assert result.macro_f1 < result.micro_f1 - 0.4

    def test_the_macro_average_says_which_topics_it_covers(self) -> None:
        """A macro F1 over two topics and one over nine are different claims."""
        gold = [item("a", "x", ["safety"])]
        result = score_predictions("s", gold, [{AspectKey.SAFETY}])
        assert result.aspects_scored == ["safety"]

    def test_a_false_positive_on_an_absent_topic_still_costs(self) -> None:
        """Otherwise a system could predict everything and be scored on nothing."""
        gold = [item("a", "x", ["safety"])]
        result = score_predictions("noisy", gold, [{AspectKey.SAFETY, AspectKey.FEATURES}])
        assert "features" in result.aspects_scored
        assert result.macro_f1 < 1.0

    def test_support_is_reported_so_a_score_on_two_items_is_visible(self) -> None:
        gold = [item("a", "x", ["safety"]), item("b", "y", ["safety"])]
        result = score_predictions("s", gold, [{AspectKey.SAFETY}, {AspectKey.SAFETY}])
        assert result.per_aspect["safety"]["support"] == 2.0
        assert result.per_aspect["features"]["support"] == 0.0


class TestTheLexiconBaseline:
    def test_it_finds_the_obvious_cases(self) -> None:
        assert AspectKey.SERVICE_AFTERSALES in lexicon_aspects(
            "the service centre experience was poor"
        )

    def test_it_is_what_the_classifier_has_to_beat(self) -> None:
        """Not a strawman. It is what currently runs in production."""
        assert lexicon_aspects("mileage is good on the highway")


class TestTheSafetyCatch:
    def test_the_classifier_is_off_until_it_earns_its_place(self) -> None:
        """The first measured comparison had it losing to the lexicon by 0.34
        macro F1. Loading a model merely because a file exists would let one
        person's local experiment silently downgrade the pipeline."""
        assert Settings().aspect_classifier_enabled is False
