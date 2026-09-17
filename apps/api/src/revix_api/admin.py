"""The operations surface. Proposal section 19.

This is the first authenticated code in the project and the first thing that
writes during a request, so both deserve stating rather than being discovered
by whoever reads this next.

**It fails closed.** If the operator credentials are not configured, every
route here answers 503 and none of them touch the database. The tempting
alternative, leaving admin open when no password is set so it "just works" in
development, is how an operations console ends up on the public internet with
no password: it behaves identically in both cases, so nothing ever tells you
which case you are in. A 503 is loud, and the message says exactly which two
variables are missing.

**Only one route writes**, and it writes one nullable foreign key on one row.
Everything else here is a read. The project's claim that the public API is
read-only is still true; this is a separate, authenticated surface, and the
non-functional requirements document says so in those words rather than
quietly continuing to claim the API has no write path at all.

**Nothing here is cached.** An operator looking at connector health after a
failed run needs the state now, not the state five minutes ago, and a stale
operations console is worse than none because it is confidently wrong.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from revix_api.schemas import (
    AdjudicationDecision,
    AdjudicationItemOut,
    ConnectorHealthOut,
    CoverageRowOut,
    FreshnessCellOut,
    FreshnessOut,
    FusionConfigAdminOut,
    IngestRunOut,
    WhoAmIOut,
)
from revix_core.db import get_session
from revix_core.enums import RunStatus
from revix_core.models import (
    EvidenceSource,
    EvidenceUnit,
    FusionConfig,
    IngestRun,
    SourceListing,
    VehicleModel,
    VehicleVariant,
    Verdict,
)
from revix_core.settings import get_settings

#: auto_error=False so a missing header reaches our handler and gets the same
#: WWW-Authenticate treatment as a wrong password. With the default, FastAPI
#: raises first and the browser never learns it should prompt.
_basic = HTTPBasic(auto_error=False)

#: A source that has not succeeded within this is stale. Chosen to be a little
#: over one nightly cycle, so a single missed run shows as stale rather than a
#: run that merely started late.
STALENESS_HOURS = 30

router = APIRouter(prefix="/admin", tags=["admin"])

SessionDep = Annotated[Session, Depends(get_session)]


def require_admin(
    response: Response,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)] = None,
) -> str:
    """The gate. Every route in this module depends on it.

    Basic authentication, which is the right size for one operator account
    over HTTPS and honest about what it is. There are no user accounts in
    Revix and there is nothing to authorise beyond "is this the operator", so
    a session store, a token service and a refresh flow would be machinery
    guarding a single boolean.

    Both halves are compared in constant time, and both are always compared.
    Returning early on a wrong username would make the response time leak
    whether a username exists, which is a small leak but a free one to avoid.
    """
    settings = get_settings()
    # Never cached, and said here rather than per route so a new route cannot
    # forget it.
    response.headers["Cache-Control"] = "no-store"

    if not settings.admin_configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The admin surface is not configured on this deployment. "
            "Set ADMIN_USERNAME and ADMIN_PASSWORD to enable it.",
        )

    supplied_user = credentials.username if credentials else ""
    supplied_pass = credentials.password if credentials else ""
    user_ok = secrets.compare_digest(supplied_user, settings.admin_username)
    pass_ok = secrets.compare_digest(supplied_pass, settings.admin_password)

    if not (user_ok and pass_ok):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect operator credentials.",
            # Without this the browser has no idea it should ask, and a human
            # hitting the URL directly sees a bare 401 with no way forward.
            headers={"WWW-Authenticate": 'Basic realm="Revix admin"'},
        )
    return settings.admin_username


AdminDep = Annotated[str, Depends(require_admin)]


def _hours_since(moment: datetime | None) -> float | None:
    if moment is None:
        return None
    # Rows written before timezone awareness was enforced would otherwise
    # raise on subtraction rather than simply reading as old.
    aware = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return round((datetime.now(UTC) - aware).total_seconds() / 3600, 1)


@router.get("/whoami", response_model=WhoAmIOut)
def whoami(operator: AdminDep) -> WhoAmIOut:
    """Cheapest possible credential check.

    The sign-in form calls this rather than a real page, so a wrong password
    costs one row-free request instead of the heaviest query on the surface.
    """
    return WhoAmIOut(username=operator, authenticated=True)


@router.get("/connectors", response_model=list[ConnectorHealthOut])
def connector_health(session: SessionDep, operator: AdminDep) -> list[ConnectorHealthOut]:
    """One card per source: is it alive, when did it last work, what broke.

    The public /sources/health answers "should a reader trust this corpus".
    This answers "what do I have to fix tonight", so it carries the things a
    reader has no use for: how long the last run took, how many units it
    actually inserted against how many it skipped as duplicates, and the last
    error in full rather than summarised.
    """
    out: list[ConnectorHealthOut] = []
    for source in session.scalars(select(EvidenceSource).order_by(EvidenceSource.source_key)):
        latest = session.scalar(
            select(IngestRun)
            .where(IngestRun.source_id == source.id)
            .order_by(IngestRun.started_at.desc())
            .limit(1)
        )
        last_success = session.scalar(
            select(IngestRun.finished_at)
            .where(IngestRun.source_id == source.id, IngestRun.status == RunStatus.SUCCEEDED)
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
        duration = None
        if latest is not None and latest.finished_at and latest.started_at:
            duration = round((latest.finished_at - latest.started_at).total_seconds(), 1)

        stale_after = _hours_since(last_success)
        out.append(
            ConnectorHealthOut(
                source_key=source.source_key,
                display_name=source.display_name,
                kind=source.kind.value,
                is_enabled=source.is_enabled,
                status=latest.status.value if latest else None,
                last_run_at=latest.started_at if latest else None,
                last_success_at=last_success,
                hours_since_success=stale_after,
                # No successful run at all is stale by definition, not unknown.
                is_stale=stale_after is None or stale_after > STALENESS_HOURS,
                last_run_seconds=duration,
                units_total=units,
                units_inserted=latest.units_inserted if latest else 0,
                units_skipped=latest.units_skipped if latest else 0,
                error_count=latest.error_count if latest else 0,
                last_error=latest.last_error if latest else None,
            )
        )
    return out


@router.get("/runs", response_model=list[IngestRunOut])
def ingest_runs(
    session: SessionDep,
    operator: AdminDep,
    source: str | None = Query(None, description="Filter to one source key."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[IngestRunOut]:
    """Every run, newest first. The log you read when last night went wrong."""
    stmt: Select[Any] = (
        select(IngestRun, EvidenceSource)
        .join(EvidenceSource, IngestRun.source_id == EvidenceSource.id)
        .order_by(IngestRun.started_at.desc())
    )
    if source:
        stmt = stmt.where(EvidenceSource.source_key == source)

    rows = session.execute(stmt.limit(limit).offset(offset)).all()
    return [
        IngestRunOut(
            id=run.id,
            source_key=src.source_key,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_seconds=(
                round((run.finished_at - run.started_at).total_seconds(), 1)
                if run.finished_at
                else None
            ),
            refs_discovered=run.refs_discovered,
            payloads_fetched=run.payloads_fetched,
            units_inserted=run.units_inserted,
            units_skipped=run.units_skipped,
            error_count=run.error_count,
            last_error=run.last_error,
        )
        for run, src in rows
    ]


@router.get("/freshness", response_model=FreshnessOut)
def freshness(session: SessionDep, operator: AdminDep) -> FreshnessOut:
    """Source by model, coloured by age. Coverage holes become visible.

    One grouped aggregate rather than a query per cell. A model with no cell
    for a source has never had anything collected from it, and that absence is
    the whole point of the grid: it is the shape of what we are missing, which
    a list of what we have cannot show.
    """
    rows = session.execute(
        select(
            EvidenceUnit.model_id,
            EvidenceSource.source_key,
            func.max(EvidenceUnit.collected_at),
            func.count(),
        )
        .join(EvidenceSource, EvidenceUnit.source_id == EvidenceSource.id)
        .where(EvidenceUnit.model_id.is_not(None))
        .group_by(EvidenceUnit.model_id, EvidenceSource.source_key)
    ).all()

    models = {
        m.id: m
        for m in session.scalars(
            select(VehicleModel).order_by(VehicleModel.vehicle_class, VehicleModel.name)
        )
    }
    sources = sorted(
        {key for _, key, _, _ in rows}
        | {s.source_key for s in session.scalars(select(EvidenceSource))}
    )

    cells = [
        FreshnessCellOut(
            model_id=model_id,
            source_key=source_key,
            last_collected_at=collected,
            hours_since=_hours_since(collected),
            units=count,
        )
        for model_id, source_key, collected, count in rows
        if model_id in models
    ]
    return FreshnessOut(
        sources=sources,
        models=[
            {"id": str(m.id), "name": m.name, "vehicle_class": m.vehicle_class.value}
            for m in models.values()
        ],
        cells=cells,
    )


@router.get("/coverage", response_model=list[CoverageRowOut])
def coverage(
    session: SessionDep,
    operator: AdminDep,
    only_suppressed: bool = Query(True, description="Only variants below the evidence floor."),
    limit: int = Query(100, ge=1, le=500),
) -> list[CoverageRowOut]:
    """Where seeding effort should go next, rather than where it feels needed.

    A suppressed variant is not a bug, it is the evidence floor doing its job.
    What an operator needs is which ones are close to clearing it and which
    are nowhere near, because those are different problems: the first wants
    one more source, the second wants a decision about whether the vehicle
    belongs in the catalogue at all.
    """
    settings = get_settings()
    default_config = session.scalar(select(FusionConfig).where(FusionConfig.is_default))
    if default_config is None:  # pragma: no cover - reference data guarantees one
        raise HTTPException(503, "no default weighting configured")

    stmt = (
        select(VehicleVariant, VehicleModel, Verdict)
        .join(VehicleModel, VehicleVariant.model_id == VehicleModel.id)
        .outerjoin(
            Verdict,
            (Verdict.variant_id == VehicleVariant.id)
            & (Verdict.fusion_config_id == default_config.id),
        )
    )
    if only_suppressed:
        stmt = stmt.where((Verdict.id.is_(None)) | (Verdict.is_suppressed.is_(True)))

    # Distinct sources per variant, in one pass rather than per row.
    source_counts: dict[uuid.UUID | None, int] = dict(
        session.execute(
            select(EvidenceUnit.variant_id, func.count(func.distinct(EvidenceUnit.source_id)))
            .where(EvidenceUnit.variant_id.is_not(None))
            .group_by(EvidenceUnit.variant_id)
        )
        .tuples()
        .all()
    )

    out: list[CoverageRowOut] = []
    for variant, model, verdict in session.execute(stmt.limit(limit)).all():
        evidence = verdict.evidence_count if verdict else 0
        distinct_sources = source_counts.get(variant.id, 0)
        out.append(
            CoverageRowOut(
                variant_id=variant.id,
                manufacturer=model.manufacturer.name,
                model=model.name,
                variant_name=variant.variant_name,
                vehicle_class=model.vehicle_class.value,
                evidence_count=evidence,
                model_evidence_count=verdict.model_evidence_count if verdict else 0,
                distinct_sources=distinct_sources,
                is_suppressed=verdict.is_suppressed if verdict else True,
                suppression_reason=(
                    verdict.suppression_reason if verdict else "no verdict computed yet"
                ),
                units_short_of_floor=max(0, settings.min_evidence_units - evidence),
                sources_short_of_floor=max(0, settings.min_distinct_sources - distinct_sources),
            )
        )
    # Closest to clearing the floor first, because that is where one more
    # source changes an outcome rather than merely improving a number.
    out.sort(key=lambda r: (r.sources_short_of_floor, r.units_short_of_floor))
    return out


@router.get("/adjudication", response_model=list[AdjudicationItemOut])
def adjudication_queue(
    session: SessionDep,
    operator: AdminDep,
    limit: int = Query(50, ge=1, le=200),
) -> list[AdjudicationItemOut]:
    """Listings the resolver would not place, for a person to decide.

    Human-in-the-loop by design rather than as an admission of failure. The
    resolver is deliberately unwilling to guess below its confidence floor,
    and something has to happen to what it refuses, otherwise the floor just
    silently loses evidence.

    Ordered by how much evidence is waiting behind each decision, so an hour
    spent here buys the most it can.
    """
    waiting: dict[uuid.UUID | None, int] = dict(
        session.execute(
            select(EvidenceUnit.source_listing_id, func.count())
            .where(EvidenceUnit.source_listing_id.is_not(None))
            .group_by(EvidenceUnit.source_listing_id)
        )
        .tuples()
        .all()
    )

    rows = session.execute(
        select(SourceListing, EvidenceSource)
        .join(EvidenceSource, SourceListing.source_id == EvidenceSource.id)
        .where(SourceListing.variant_id.is_(None))
        .limit(limit * 4)
    ).all()

    items = [
        AdjudicationItemOut(
            listing_id=listing.id,
            source_key=src.source_key,
            raw_title=listing.raw_title,
            url=listing.url,
            match_method=listing.match_method,
            match_confidence=(
                float(listing.match_confidence) if listing.match_confidence is not None else None
            ),
            resolved_model_id=listing.model_id,
            evidence_waiting=waiting.get(listing.id, 0),
        )
        for listing, src in rows
    ]
    items.sort(key=lambda i: i.evidence_waiting, reverse=True)
    return items[:limit]


@router.post("/adjudication/{listing_id}", response_model=AdjudicationItemOut)
def adjudicate(
    listing_id: uuid.UUID,
    decision: AdjudicationDecision,
    session: SessionDep,
    operator: AdminDep,
) -> AdjudicationItemOut:
    """A person's decision about one listing. The only write on this surface.

    Recorded as match_method='human' so it is never mistaken for something the
    resolver worked out, and so a later evaluation can separate what we were
    told from what we inferred. That distinction is the entire value of this
    queue: a human decision mixed indistinguishably into automated ones is a
    gold set contaminated by its own answers.

    The verdict does not move until the pipeline runs again. Fusion is a batch
    stage and this endpoint deliberately does not reach into it, because a
    request that triggers a recomputation is a request that can time out
    halfway through one.
    """
    listing = session.get(SourceListing, listing_id)
    if listing is None:
        raise HTTPException(404, "unknown listing")

    if decision.variant_id is not None:
        variant = session.get(VehicleVariant, decision.variant_id)
        if variant is None:
            raise HTTPException(422, "unknown variant")
        listing.variant_id = variant.id
        listing.model_id = variant.model_id
    elif decision.model_id is not None:
        model = session.get(VehicleModel, decision.model_id)
        if model is None:
            raise HTTPException(422, "unknown model")
        # Model without variant is a real answer, not a partial one. Most
        # owner reviews name a model and never a trim.
        listing.variant_id = None
        listing.model_id = model.id
    else:
        # "Neither" is also a decision: this listing is not one of ours.
        listing.variant_id = None
        listing.model_id = None

    listing.match_method = "human"
    listing.match_confidence = 1.0 if not decision.is_rejection else 0.0
    listing.resolved_at = datetime.now(UTC)
    session.flush()

    source = session.get(EvidenceSource, listing.source_id)
    waiting = (
        session.scalar(
            select(func.count())
            .select_from(EvidenceUnit)
            .where(EvidenceUnit.source_listing_id == listing.id)
        )
        or 0
    )
    return AdjudicationItemOut(
        listing_id=listing.id,
        source_key=source.source_key if source else "unknown",
        raw_title=listing.raw_title,
        url=listing.url,
        match_method=listing.match_method,
        match_confidence=float(listing.match_confidence)
        if listing.match_confidence is not None
        else None,
        resolved_model_id=listing.model_id,
        evidence_waiting=waiting,
    )


@router.get("/fusion-configs", response_model=list[FusionConfigAdminOut])
def fusion_configs(session: SessionDep, operator: AdminDep) -> list[FusionConfigAdminOut]:
    """Every weighting, its parameters, and how many verdicts it actually has.

    Read-only, and that is a decision rather than an unfinished feature.
    Creating a configuration here would put it on the public switch
    immediately, because /fusion-configs lists whatever exists, while its
    verdicts would not exist until the pipeline next ran. Every variant would
    answer "no verdict" under the new weighting and the flagship control would
    be visibly broken until morning.

    A weighting is only real once its verdicts are computed, so creating one
    belongs where the computation happens: `revix fuse` in the pipeline. What
    an operator needs here is to see what exists and whether it is fully
    populated, and that is what this returns.
    """
    counts: dict[uuid.UUID, int] = dict(
        session.execute(
            select(Verdict.fusion_config_id, func.count()).group_by(Verdict.fusion_config_id)
        )
        .tuples()
        .all()
    )
    variants = session.scalar(select(func.count()).select_from(VehicleVariant)) or 0

    return [
        FusionConfigAdminOut(
            id=config.id,
            name=config.name,
            label=config.label,
            description=config.description,
            is_default=config.is_default,
            params=config.params,
            verdict_count=counts.get(config.id, 0),
            variant_count=variants,
            is_complete=counts.get(config.id, 0) >= variants,
        )
        for config in session.scalars(select(FusionConfig).order_by(FusionConfig.display_order))
    ]


__all__ = ["STALENESS_HOURS", "require_admin", "router"]
