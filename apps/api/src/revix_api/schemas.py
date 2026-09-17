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
from typing import Any

from pydantic import BaseModel, ConfigDict


class Health(BaseModel):
    status: str
    database: bool
    variants: int
    verdicts: int


class EvalRunOut(BaseModel):
    """One recorded measurement, for the public metrics page."""

    model_config = ConfigDict(from_attributes=True)

    component: str
    system: str
    n_items: int
    primary_metric: str
    primary_value: float
    git_sha: str | None
    created_at: datetime
    detail: dict[str, Any] | None


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
    model_evidence_count: int = 0
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
    #: How many of those describe the model rather than this exact trim.
    #: Shown to the reader, because a review of the Creta and a review of
    #: the Creta SX(O) Turbo DCT are not the same claim.
    model_evidence_count: int
    effective_sample_size: float | None
    # No defaults on these two. A field with a default is optional in the
    # generated OpenAPI schema, which would make the frontend treat an
    # always-present list as possibly undefined. The API always sends both.
    sources_used: list[str]

    #: Ordered by disagreement, never by score. Conflict first is the product's
    #: identity and the opposite of what every competitor does.
    aspects: list[AspectOut]


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


# ---------- admin (proposal section 19) ----------
#
# Separate from the public models above on purpose. These carry operational
# detail a reader has no use for and should not be handed: full error strings,
# run durations, and how much evidence is waiting behind an unmade decision.


class WhoAmIOut(BaseModel):
    """What the sign-in form checks against."""

    username: str
    authenticated: bool


class ConnectorHealthOut(BaseModel):
    source_key: str
    display_name: str
    kind: str
    is_enabled: bool
    status: str | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    hours_since_success: float | None
    is_stale: bool
    last_run_seconds: float | None
    units_total: int
    units_inserted: int
    units_skipped: int
    error_count: int
    last_error: str | None


class IngestRunOut(BaseModel):
    id: uuid.UUID
    source_key: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    refs_discovered: int
    payloads_fetched: int
    units_inserted: int
    units_skipped: int
    error_count: int
    last_error: str | None


class FreshnessCellOut(BaseModel):
    model_id: uuid.UUID
    source_key: str
    last_collected_at: datetime | None
    hours_since: float | None
    units: int


class FreshnessOut(BaseModel):
    """A grid rather than a list, because the absences are the information."""

    sources: list[str]
    models: list[dict[str, str]]
    cells: list[FreshnessCellOut]


class CoverageRowOut(BaseModel):
    variant_id: uuid.UUID
    manufacturer: str
    model: str
    variant_name: str
    vehicle_class: str
    evidence_count: int
    model_evidence_count: int
    distinct_sources: int
    is_suppressed: bool
    suppression_reason: str | None
    #: How far this variant is from clearing each half of the evidence floor.
    #: Two numbers rather than one, because "needs another source" and "needs
    #: more of the same" are different jobs.
    units_short_of_floor: int
    sources_short_of_floor: int


class AdjudicationItemOut(BaseModel):
    listing_id: uuid.UUID
    source_key: str
    raw_title: str
    url: str | None
    match_method: str | None
    match_confidence: float | None
    resolved_model_id: uuid.UUID | None
    #: Evidence units already collected against this listing, and therefore
    #: unusable until somebody decides what vehicle it is about.
    evidence_waiting: int


class AdjudicationDecision(BaseModel):
    """A person's answer. All three fields absent means "not one of ours"."""

    variant_id: uuid.UUID | None = None
    model_id: uuid.UUID | None = None
    #: Distinguishes "I looked and it is nothing" from "I have not looked".
    #: Both clear the queue; only one of them is a judgement.
    is_rejection: bool = False


class FusionConfigAdminOut(BaseModel):
    id: uuid.UUID
    name: str
    label: str
    description: str | None
    is_default: bool
    params: dict[str, Any]
    verdict_count: int
    variant_count: int
    #: False means this weighting would answer "no verdict" for some variants,
    #: which is what an operator needs to know before making it the default.
    is_complete: bool
