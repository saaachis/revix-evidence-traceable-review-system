"""The classifier's lexicon-only contract.

scikit-learn is an optional extra (ADR 0004: the pipeline runs with nothing
trained), so these cover the paths that hold whether or not a model exists:
training refuses too little evidence, a missing model loads as None rather than
crashing, and evaluation still scores the lexicon on its own.
"""

from __future__ import annotations

import pathlib

import pytest

from revix_core.enums import AspectKey
from revix_pipeline.ml.aspect_model import (
    AspectClassifier,
    evaluate_against_gold,
    train_classifier,
)
from revix_pipeline.ml.gold import GoldItem


def test_too_little_evidence_refuses_to_train() -> None:
    # The guard fires before scikit-learn is imported, so this holds even
    # where the optional ml extra is not installed.
    with pytest.raises(ValueError, match="at least"):
        train_classifier(["one short sentence"], [[0] * len(list(AspectKey))])


def test_a_missing_model_loads_as_none_rather_than_raising(tmp_path: pathlib.Path) -> None:
    assert AspectClassifier.load(tmp_path / "there-is-no-model.joblib") is None


class TestEvaluationAgainstGold:
    def test_the_lexicon_is_scored_even_with_no_classifier(self) -> None:
        gold = [GoldItem(id="g1", text="the gearbox is smooth", aspects=[], labelled_by="me")]
        results = evaluate_against_gold(gold, None)
        assert len(results) == 1
        assert results[0].as_dict()["name"] == "lexicon"

    def test_an_unlabelled_gold_set_scores_nothing(self) -> None:
        unsigned = [GoldItem(id="g1", text="x y z", aspects=[], labelled_by="")]
        assert evaluate_against_gold(unsigned, None) == []
