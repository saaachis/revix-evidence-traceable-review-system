"""Learned components, and the gold sets that let us say whether they work.

Everything in `enrichment` is a rule somebody wrote by hand. That is a
defensible way to build a pipeline and a poor way to end a data science
project, because a hand-written rule cannot be wrong in an interesting way:
it can only be wrong in the way you wrote it.

This package holds the parts that are learned, and more importantly the
measurement that says whether learning helped. A classifier with no gold set
is a lexicon with extra steps.
"""

from revix_pipeline.ml.aspect_model import (
    AspectClassifier,
    Evaluation,
    evaluate_against_gold,
    train_classifier,
)
from revix_pipeline.ml.gold import GoldItem, load_gold, sample_for_labelling, save_gold

__all__ = [
    "AspectClassifier",
    "Evaluation",
    "GoldItem",
    "evaluate_against_gold",
    "load_gold",
    "sample_for_labelling",
    "save_gold",
    "train_classifier",
]
