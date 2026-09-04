"""Response models.

These are the contract. The OpenAPI schema generated from them is the source
of truth for the frontend's typed client, so the two cannot drift.

Every verdict response carries evidence_count, effective_sample_size,
sources_used and computed_at. A response that states how much it rests on and
when it was computed is one a caller can judge; one that does not is a number
you have to take on faith.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: str
    database: bool
    variants: int
    verdicts: int


class ManufacturerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    slug: str


class VariantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manufacturer: str
    model: str
    model_slug: str
    vehicle_class: str
    variant_name: str
    fuel_type: str
    transmission: str
    price_min: int | None = None
    price_max: int | None = None
    overall_score: float | None = None
    confidence_low: float | None = None
    confidence_high: float | None = None
    evidence_count: int = 0
    is_suppressed: bool = False


class SpecOut(BaseModel):
    engine_cc: int | None = None
    engine_power_bhp: float | None = None
    arai_mileage_kmpl: float | None = None
    seating_capacity: int | None = None
    boot_litres: int | None = None
    kerb_weight_kg: float | None = None
    seat_height_mm: int | None = None
    braking_type: str | None = None
    spec_completeness: float = 0.0


class CovariateGroup(BaseModel):
    value: str
    score: float
    weight_share: float
    count: int


class CovariateExplanation(BaseModel):
    covariate: str
    explained_share: float
    groups: list[CovariateGroup]


class AspectOut(BaseModel):
    aspect_key: str
    label: str
    score: float | None
    ci_low: float | None
    ci_high: float | None
    support_count: int
    divergence_index: float | None
    #: Words, not a decimal. "0.61" means nothing to a person reading it.
    agreement: str
    top_covariate: str | None = None
    covariate_explanation: CovariateExplanation | None = None
    claim_id: uuid.UUID | None = None


class FusionConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    label: str
    description: str | None
    is_default: bool
    display_order: int


class VerdictOut(BaseModel):
    variant: VariantSummary
    specs: SpecOut
    fusion: str
    computed_at: datetime

    overall_score: float | None
    confidence_low: float | None
    confidence_high: float | None

    is_suppressed: bool
    suppression_reason: str | None

    evidence_count: int
    effective_sample_size: float | None
    sources_used: list[str] = Field(default_factory=list)

    #: Ordered by disagreement, never by score. Conflict first is the product's
    #: identity and the opposite of what every competitor does.
    aspects: list[AspectOut] = Field(default_factory=list)


class EvidenceOut(BaseModel):
    id: uuid.UUID
    source: str
    source_kind: str
    url: str | None
    text: str
    published_at: datetime | None
    is_verified_owner: bool | None
    ownership_duration_months: int | None
    km_driven: int | None
    rating_normalized: float | None
    #: How much this review counted towards the number that opened the drawer.
    contribution_weight: float
    rank: int


class ClaimEvidenceOut(BaseModel):
    claim_id: uuid.UUID
    aspect_key: str
    score: float
    total_contributors: int
    evidence: list[EvidenceOut]


class SourceHealthOut(BaseModel):
    source_key: str
    display_name: str
    kind: str
    is_enabled: bool
    status: str | None
    last_success: datetime | None
    units_total: int
    error_rate: float | None
    last_error: str | None
