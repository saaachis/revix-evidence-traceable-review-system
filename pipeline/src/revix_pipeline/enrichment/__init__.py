"""The nightly enrichment stages.

    resolve -> extract -> score -> fuse

Each stage writes its output and can be re-run independently, which is what
lets a scheduled workflow simply call them in order and retry on failure.
"""

from revix_pipeline.enrichment.credibility import score_credibility
from revix_pipeline.enrichment.extract import extract_opinions
from revix_pipeline.enrichment.fuse import fuse_all
from revix_pipeline.enrichment.resolve import resolve_listings

__all__ = ["extract_opinions", "fuse_all", "resolve_listings", "score_credibility"]
