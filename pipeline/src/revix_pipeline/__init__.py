"""Ingestion connectors and the nightly enrichment stages.

Every stage is a command on the `revix` CLI, scheduled by GitHub Actions
rather than a dedicated orchestrator. See docs/adr/0002 for why.
"""

__version__ = "0.1.0"
