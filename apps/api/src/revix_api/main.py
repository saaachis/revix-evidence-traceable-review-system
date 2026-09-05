"""The serving layer.

Read-only, contract-first, and every endpoint is a single indexed read from
the serving schema. No model runs here and nothing is computed on the read
path. If an endpoint would need to calculate something, the pipeline should
have calculated it overnight.

That constraint is not a style preference. It is what makes p95 under 300 ms
achievable by design rather than by optimisation, and it is why a demo does
not depend on a language model being reachable.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from revix_api.schemas import (
    AspectOut,
    ClaimEvidenceOut,
    EvalRunOut,
    EvidenceOut,
    FusionConfigOut,
    Health,
    SourceHealthOut,
    SpecOut,
    VariantSummary,
    VerdictOut,
)
from revix_core.db import get_session, session_scope
from revix_core.enums import ASPECT_LABELS, AspectKey, RunStatus, VehicleClass
from revix_core.models import (
    EvalRun,
    EvidenceSource,
    EvidenceUnit,
    FusionConfig,
    IngestRun,
    VehicleModel,
    VehicleVariant,
    Verdict,
    VerdictClaim,
    VerdictClaimEvidence,
)
from revix_core.settings import get_settings

SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI(
    title="Revix API",
    version="0.1.0",
    description=(
        "Read-only serving layer for Revix. Every response is a precomputed row. "
        "Verdicts carry the evidence count, the effective sample size and the "
        "sources they were built from, so a caller can judge them rather than "
        "having to trust them."
    ),
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def agreement_word(divergence: float | None) -> str:
    """Words rather than a decimal.

    "0.61" is meaningless to somebody choosing a car. Three levels are enough
    to act on, and the number stays available for anyone who wants it.
    """
    if divergence is None:
        return "unknown"
    if divergence >= 0.40:
        return "sharply split"
    if divergence >= 0.22:
        return "some disagreement"
    return "broad agreement"


def _variant_summary(variant: VehicleVariant, verdict: Verdict | None = None) -> VariantSummary:
    model = variant.model
    return VariantSummary(
        id=variant.id,
        manufacturer=model.manufacturer.name,
        model=model.name,
        model_slug=model.slug,
        vehicle_class=model.vehicle_class.value,
        variant_name=variant.variant_name,
        fuel_type=variant.fuel_type.value,
        transmission=variant.transmission.value,
        price_min=variant.ex_showroom_price_min,
        price_max=variant.ex_showroom_price_max,
        overall_score=float(verdict.overall_score) if verdict and verdict.overall_score else None,
        confidence_low=float(verdict.confidence_low)
        if verdict and verdict.confidence_low
        else None,
        confidence_high=(
            float(verdict.confidence_high) if verdict and verdict.confidence_high else None
        ),
        evidence_count=verdict.evidence_count if verdict else 0,
        model_evidence_count=verdict.model_evidence_count if verdict else 0,
        is_suppressed=verdict.is_suppressed if verdict else True,
    )


def _resolve_config(session: Session, fusion: str | None) -> FusionConfig:
    if fusion:
        config = session.scalar(select(FusionConfig).where(FusionConfig.name == fusion))
        if config is None:
            known = [c.name for c in session.scalars(select(FusionConfig))]
            raise HTTPException(404, f"unknown weighting '{fusion}'. Available: {known}")
        return config
    config = session.scalar(select(FusionConfig).where(FusionConfig.is_default))
    if config is None:  # pragma: no cover - reference data guarantees one
        raise HTTPException(503, "no default weighting configured")
    return config


@app.get(
    "/health",
    response_model=Health,
    tags=["meta"],
    responses={503: {"model": Health, "description": "The database is unreachable."}},
)
def health(response: Response) -> Health:
    """Is this instance able to serve?

    Deliberately not using the session dependency. If it did, an unreachable
    database would raise during dependency resolution, before the handler ran,
    and the health endpoint would answer 500 with a SQLAlchemy stack trace: no
    diagnosis for us and a stack trace for everyone else. Opening the session
    here means the failure is a value this function can report.

    503 rather than 200 on failure, because a platform health check reads the
    status code and nothing else, and an instance that cannot reach its
    database must not be sent traffic.
    """
    try:
        with session_scope() as session:
            variants = session.scalar(select(func.count()).select_from(VehicleVariant)) or 0
            verdicts = session.scalar(select(func.count()).select_from(Verdict)) or 0
    except SQLAlchemyError:
        response.status_code = 503
        return Health(status="degraded", database=False, variants=0, verdicts=0)
    return Health(status="ok", database=True, variants=variants, verdicts=verdicts)


@app.get("/metrics", response_model=list[EvalRunOut], tags=["meta"])
def metrics(session: SessionDep, component: str | None = None, limit: int = 50) -> Sequence[Any]:
    """Every measurement we have recorded, newest first.

    Proposal section 18.4. Published rather than kept internal, because a
    project that asks you to trust its numbers should show how well those
    numbers hold up, including when the answer is unflattering. The first
    recorded comparison had our own classifier losing to the lexicon it was
    trained from, and that is on this endpoint like everything else.

    Empty is a truthful answer. It means nothing has been measured yet.
    """
    stmt = select(EvalRun).order_by(EvalRun.created_at.desc())
    if component:
        stmt = stmt.where(EvalRun.component == component)
    return list(session.scalars(stmt.limit(max(1, min(limit, 200)))))


@app.get("/fusion-configs", response_model=list[FusionConfigOut], tags=["meta"])
def fusion_configs(session: SessionDep) -> Sequence[FusionConfig]:
    """What the weighting switch offers.

    Switching between these is a lookup by (variant, config), never a
    recomputation. That is the only reason the switch is affordable.
    """
    return list(session.scalars(select(FusionConfig).order_by(FusionConfig.display_order)))


@app.get("/variants", response_model=list[VariantSummary], tags=["catalogue"])
def list_variants(
    session: SessionDep,
    q: str | None = Query(None, description="Free text over manufacturer, model and variant."),
    vehicle_class: str | None = Query(None, pattern="^(car|two_wheeler)$"),
    fusion: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[VariantSummary]:
    config = _resolve_config(session, fusion)
    stmt = (
        select(VehicleVariant, Verdict)
        .join(VehicleModel, VehicleVariant.model_id == VehicleModel.id)
        .outerjoin(
            Verdict,
            (Verdict.variant_id == VehicleVariant.id) & (Verdict.fusion_config_id == config.id),
        )
    )
    if vehicle_class:
        stmt = stmt.where(VehicleModel.vehicle_class == VehicleClass(vehicle_class))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            func.concat(VehicleModel.name, " ", VehicleVariant.variant_name).ilike(pattern)
        )
    stmt = stmt.order_by(VehicleModel.name, VehicleVariant.variant_name).limit(limit).offset(offset)
    return [_variant_summary(v, verdict) for v, verdict in session.execute(stmt).all()]


@app.get("/variants/{variant_id}/verdict", response_model=VerdictOut, tags=["verdict"])
def get_verdict(
    variant_id: uuid.UUID, session: SessionDep, fusion: str | None = None
) -> VerdictOut:
    """THE endpoint. One indexed read, no computation."""
    config = _resolve_config(session, fusion)
    variant = session.get(VehicleVariant, variant_id)
    if variant is None:
        raise HTTPException(404, "unknown variant")

    verdict = session.scalar(
        select(Verdict).where(
            Verdict.variant_id == variant_id, Verdict.fusion_config_id == config.id
        )
    )
    if verdict is None:
        raise HTTPException(404, "no verdict computed for this variant yet")

    vehicle_class = variant.model.vehicle_class
    claims = {
        c.computed_values.get("aspect"): c.id
        for c in session.scalars(
            select(VerdictClaim).where(
                VerdictClaim.verdict_id == verdict.id,
                VerdictClaim.claim_type == "aspect_score",
            )
        )
    }

    aspects = [
        AspectOut(
            aspect_key=row.aspect_key.value,
            label=ASPECT_LABELS[AspectKey(row.aspect_key)][vehicle_class],
            score=float(row.score) if row.score is not None else None,
            ci_low=float(row.ci_low) if row.ci_low is not None else None,
            ci_high=float(row.ci_high) if row.ci_high is not None else None,
            support_count=row.support_count,
            divergence_index=(
                float(row.divergence_index) if row.divergence_index is not None else None
            ),
            agreement=agreement_word(
                float(row.divergence_index) if row.divergence_index is not None else None
            ),
            top_covariate=row.top_covariate,
            covariate_explanation=row.covariate_explanation,
            claim_id=claims.get(row.aspect_key.value),
        )
        for row in sorted(
            verdict.aspects,
            key=lambda a: float(a.divergence_index or 0),
            reverse=True,
        )
    ]

    sources: list[str] = []
    if verdict.sources_used:
        raw: Any = verdict.sources_used.get("sources", [])
        sources = list(raw)

    return VerdictOut(
        variant=_variant_summary(variant, verdict),
        specs=SpecOut(
            engine_cc=variant.engine_cc,
            engine_power_bhp=(
                float(variant.engine_power_bhp) if variant.engine_power_bhp else None
            ),
            arai_mileage_kmpl=(
                float(variant.arai_mileage_kmpl) if variant.arai_mileage_kmpl else None
            ),
            seating_capacity=variant.seating_capacity,
            boot_litres=variant.boot_litres,
            kerb_weight_kg=float(variant.kerb_weight_kg) if variant.kerb_weight_kg else None,
            seat_height_mm=variant.seat_height_mm,
            braking_type=variant.braking_type,
            spec_completeness=float(variant.spec_completeness),
        ),
        fusion=config.name,
        computed_at=verdict.computed_at,
        overall_score=float(verdict.overall_score) if verdict.overall_score is not None else None,
        confidence_low=(
            float(verdict.confidence_low) if verdict.confidence_low is not None else None
        ),
        confidence_high=(
            float(verdict.confidence_high) if verdict.confidence_high is not None else None
        ),
        is_suppressed=verdict.is_suppressed,
        suppression_reason=verdict.suppression_reason,
        evidence_count=verdict.evidence_count,
        model_evidence_count=verdict.model_evidence_count,
        effective_sample_size=(
            float(verdict.effective_sample_size)
            if verdict.effective_sample_size is not None
            else None
        ),
        sources_used=sources,
        aspects=aspects,
    )


@app.get("/claims/{claim_id}/evidence", response_model=ClaimEvidenceOut, tags=["verdict"])
def claim_evidence(claim_id: uuid.UUID, session: SessionDep) -> ClaimEvidenceOut:
    """The traceability drawer.

    A read of verdict_claim_evidence ordered by contribution weight, and
    nothing else. These rows were written by the fusion engine before any
    prose existed, and the score was computed from them, which is why the
    citation cannot be wrong.
    """
    claim = session.get(VerdictClaim, claim_id)
    if claim is None:
        raise HTTPException(404, "unknown claim")

    rows = session.execute(
        select(VerdictClaimEvidence, EvidenceUnit, EvidenceSource)
        .join(EvidenceUnit, VerdictClaimEvidence.evidence_unit_id == EvidenceUnit.id)
        .join(EvidenceSource, EvidenceUnit.source_id == EvidenceSource.id)
        .where(VerdictClaimEvidence.verdict_claim_id == claim_id)
        .order_by(VerdictClaimEvidence.rank)
    ).all()

    return ClaimEvidenceOut(
        claim_id=claim.id,
        aspect_key=str(claim.computed_values.get("aspect", "")),
        score=float(claim.computed_values.get("score", 0)),
        total_contributors=int(claim.computed_values.get("support", 0)),
        evidence=[
            EvidenceOut(
                id=unit.id,
                source=source.display_name,
                source_kind=source.kind.value,
                url=unit.url,
                text=unit.text,
                published_at=unit.published_at,
                is_verified_owner=unit.is_verified_owner,
                ownership_duration_months=unit.ownership_duration_months,
                km_driven=unit.km_driven,
                rating_normalized=(
                    float(unit.rating_normalized) if unit.rating_normalized is not None else None
                ),
                contribution_weight=float(link.contribution_weight),
                rank=link.rank,
            )
            for link, unit, source in rows
        ],
    )


@app.get("/sources/health", response_model=list[SourceHealthOut], tags=["ops"])
def sources_health(session: SessionDep) -> list[SourceHealthOut]:
    """Where every source stands. A dead source degrades, it does not break."""
    out: list[SourceHealthOut] = []
    for source in session.scalars(select(EvidenceSource).order_by(EvidenceSource.source_key)):
        latest = session.scalar(
            select(IngestRun)
            .where(IngestRun.source_id == source.id)
            .order_by(IngestRun.started_at.desc())
            .limit(1)
        )
        units = (
            session.scalar(
                select(func.count())
                .select_from(EvidenceUnit)
                .where(EvidenceUnit.source_id == source.id)
            )
            or 0
        )
        attempted = (latest.payloads_fetched + latest.error_count) if latest is not None else 0
        out.append(
            SourceHealthOut(
                source_key=source.source_key,
                display_name=source.display_name,
                kind=source.kind.value,
                is_enabled=source.is_enabled,
                status=latest.status.value if latest else None,
                last_success=(
                    latest.finished_at if latest and latest.status is RunStatus.SUCCEEDED else None
                ),
                units_total=units,
                error_rate=(
                    latest.error_count / attempted if latest is not None and attempted else None
                ),
                last_error=latest.last_error if latest else None,
            )
        )
    return out
