"""All ORM models, re-exported so Alembic sees one metadata object."""

from revix_core.models.analysis import (
    EMBEDDING_DIM,
    AspectOpinion,
    EvalRun,
    EvidenceChunk,
    FusionConfig,
)
from revix_core.models.base import ALL_SCHEMAS, Base, utcnow
from revix_core.models.catalogue import (
    Aspect,
    Manufacturer,
    VariantFeature,
    VehicleModel,
    VehicleVariant,
)
from revix_core.models.evidence import (
    EvidenceSource,
    EvidenceUnit,
    IngestRun,
    RawPayload,
    SourceListing,
)
from revix_core.models.serving import (
    Verdict,
    VerdictAspect,
    VerdictClaim,
    VerdictClaimEvidence,
)

__all__ = [
    "ALL_SCHEMAS",
    "EMBEDDING_DIM",
    "Aspect",
    "AspectOpinion",
    "Base",
    "EvalRun",
    "EvidenceChunk",
    "EvidenceSource",
    "EvidenceUnit",
    "FusionConfig",
    "IngestRun",
    "Manufacturer",
    "RawPayload",
    "SourceListing",
    "VariantFeature",
    "VehicleModel",
    "VehicleVariant",
    "Verdict",
    "VerdictAspect",
    "VerdictClaim",
    "VerdictClaimEvidence",
    "utcnow",
]
