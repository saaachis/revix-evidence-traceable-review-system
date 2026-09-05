"""Measuring whether the weighting actually helps.

Everything else in this repository computes a verdict. This package asks
whether the verdict is any good, which is a different question and a harder
one, because there is no ground truth for "is this car good".

Section 18 of the proposal answers that by refusing the naive question and
asking a narrower one that does have an answer. See `fusion_experiment`.
"""

from revix_pipeline.evaluation.fusion_experiment import (
    ExperimentReport,
    GoldConsensus,
    run_fusion_experiment,
    spearman,
)

__all__ = [
    "ExperimentReport",
    "GoldConsensus",
    "run_fusion_experiment",
    "spearman",
]
