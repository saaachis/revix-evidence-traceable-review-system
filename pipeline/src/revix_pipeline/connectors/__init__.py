"""Ingestion connectors, and the framework that makes them polite."""

from revix_core.enums import SourceKind
from revix_pipeline.connectors.base import (
    CatalogSeed,
    Connector,
    ConnectorRegistry,
    EvidenceUnitDraft,
    ExternalRef,
    RawPayload,
    registry,
)
from revix_pipeline.connectors.fixture import FixtureConnector
from revix_pipeline.connectors.runner import RunResult, run_connector

# Three fixtures rather than one, standing in for the three source kinds the
# real connectors will occupy. A single source cannot clear the evidence floor
# and gives the source-weighted strategy nothing to weight.
registry.register(
    FixtureConnector(
        source_key="fixture_owner",
        display_name="Development fixture: owner reviews (synthetic)",
        kind=SourceKind.OWNER_REVIEW,
        source_prior=0.55,
        per_variant=60,
        verified_rate=0.70,
    )
)
registry.register(
    FixtureConnector(
        source_key="fixture_forum",
        display_name="Development fixture: forum threads (synthetic)",
        kind=SourceKind.FORUM,
        source_prior=0.70,
        per_variant=22,
        verified_rate=0.45,
    )
)
registry.register(
    FixtureConnector(
        source_key="fixture_expert",
        display_name="Development fixture: expert publications (synthetic)",
        kind=SourceKind.EXPERT_REVIEW,
        source_prior=0.85,
        per_variant=6,
        verified_rate=0.0,
        # Media drive it for a weekend. Owners live with the service centre.
        detail_bias=0.35,
    )
)

__all__ = [
    "CatalogSeed",
    "Connector",
    "ConnectorRegistry",
    "EvidenceUnitDraft",
    "ExternalRef",
    "FixtureConnector",
    "RawPayload",
    "RunResult",
    "registry",
    "run_connector",
]
