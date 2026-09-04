"""The `revix` command line.

Each stage is a subcommand that is safe to re-run. That property is what lets
a scheduled workflow call them in order and retry on failure without needing
an orchestrator to hold state. See docs/adr/0002.

    revix db check
    revix db seed-reference
    revix catalogue seed
    revix ingest --source fixture
    revix enrich resolve
    revix enrich extract
    revix enrich score
    revix enrich fuse
    revix pipeline nightly      # all of the above, in order
"""

from __future__ import annotations

import logging
import time

import typer
from sqlalchemy import func, select, text

from revix_core.db import session_scope
from revix_core.models import (
    Aspect,
    AspectOpinion,
    EvidenceUnit,
    FusionConfig,
    SourceListing,
    VehicleVariant,
    Verdict,
)
from revix_core.settings import get_settings
from revix_pipeline.catalogue import seed_catalogue
from revix_pipeline.connectors import registry, run_connector
from revix_pipeline.enrichment import (
    extract_opinions,
    fuse_all,
    resolve_listings,
    score_credibility,
)
from revix_pipeline.reference import seed_all

app = typer.Typer(
    name="revix",
    help="Revix pipeline: ingestion and nightly enrichment.",
    no_args_is_help=True,
    add_completion=False,
)

db_app = typer.Typer(help="Database maintenance and reference data.", no_args_is_help=True)
catalogue_app = typer.Typer(help="The seeded vehicle catalogue.", no_args_is_help=True)
enrich_app = typer.Typer(help="The nightly enrichment stages.", no_args_is_help=True)
pipeline_app = typer.Typer(help="Whole-pipeline runs.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(enrich_app, name="enrich")
app.add_typer(pipeline_app, name="pipeline")


def redact_dsn(dsn: str) -> str:
    """Strip the password so a DSN is safe to print or paste into an issue."""
    if "@" not in dsn or "//" not in dsn:
        return dsn
    scheme, _, rest = dsn.partition("//")
    creds, _, host = rest.rpartition("@")
    user = creds.split(":", 1)[0] if creds else ""
    return f"{scheme}//{user}:***@{host}" if user else f"{scheme}//{host}"


def _report(title: str, stats: dict[str, int], elapsed: float) -> None:
    typer.secho(f"{title}  ({elapsed:.1f}s)", fg="cyan", bold=True)
    for key, value in stats.items():
        typer.echo(f"    {key:22} {value:>8,}")


# ---------------------------------------------------------------- db


@db_app.command("check")
def db_check() -> None:
    """Confirm the database is reachable and the extensions are installed."""
    settings = get_settings()
    with session_scope() as session:
        version = session.execute(text("select version()")).scalar_one()
        extensions = sorted(
            r[0] for r in session.execute(text("select extname from pg_extension")).all()
        )
        tables = session.execute(
            text(
                "select count(*) from information_schema.tables "
                "where table_schema in ('raw','core','analysis','serving')"
            )
        ).scalar_one()

    typer.echo(f"database   {redact_dsn(settings.sync_database_url)}")
    typer.echo(f"server     {str(version).split(' on ')[0]}")
    typer.echo(f"extensions {', '.join(extensions)}")
    typer.echo(f"tables     {tables}")

    missing = {"vector", "pg_trgm"} - set(extensions)
    if missing:
        typer.secho(f"missing extensions: {', '.join(sorted(missing))}", fg="red")
        raise typer.Exit(1)


@db_app.command("seed-reference")
def db_seed_reference() -> None:
    """Load the nine aspects and the weighting configurations. Idempotent."""
    with session_scope() as session:
        added = seed_all(session)
    if sum(added.values()) == 0:
        typer.echo("reference data already present, nothing to do")
    else:
        for name, count in added.items():
            typer.echo(f"  + {count} {name}")


@db_app.command("show-reference")
def db_show_reference() -> None:
    """Print the seeded reference data, to confirm what the pipeline will use."""
    with session_scope() as session:
        aspects = list(session.scalars(select(Aspect).order_by(Aspect.display_order)))
        configs = list(session.scalars(select(FusionConfig).order_by(FusionConfig.display_order)))

    typer.echo(f"aspects ({len(aspects)})")
    for a in aspects:
        typer.echo(f"  {a.display_order}  {a.key.value:24} {a.label_car}")
    typer.echo(f"\nweighting configurations ({len(configs)})")
    for c in configs:
        default = "  [default]" if c.is_default else ""
        typer.echo(f"  {c.display_order}  {c.name:22} {c.label}{default}")


@db_app.command("status")
def db_status() -> None:
    """How much of everything exists right now."""
    with session_scope() as session:
        counts = {
            "variants": session.scalar(select(func.count()).select_from(VehicleVariant)) or 0,
            "listings": session.scalar(select(func.count()).select_from(SourceListing)) or 0,
            "listings resolved": session.scalar(
                select(func.count())
                .select_from(SourceListing)
                .where(SourceListing.variant_id.is_not(None))
            )
            or 0,
            "evidence units": session.scalar(select(func.count()).select_from(EvidenceUnit)) or 0,
            "units resolved": session.scalar(
                select(func.count())
                .select_from(EvidenceUnit)
                .where(EvidenceUnit.variant_id.is_not(None))
            )
            or 0,
            "aspect opinions": session.scalar(select(func.count()).select_from(AspectOpinion)) or 0,
            "verdicts": session.scalar(select(func.count()).select_from(Verdict)) or 0,
            "verdicts suppressed": session.scalar(
                select(func.count()).select_from(Verdict).where(Verdict.is_suppressed)
            )
            or 0,
        }
    for key, value in counts.items():
        typer.echo(f"  {key:22} {value:>8,}")


# ---------------------------------------------------------------- catalogue


@catalogue_app.command("seed")
def catalogue_seed() -> None:
    """Load the seeded vehicles from data/seed/catalogue.json. Idempotent."""
    start = time.monotonic()
    with session_scope() as session:
        counts = seed_catalogue(session)
    _report("catalogue seeded", counts, time.monotonic() - start)


# ---------------------------------------------------------------- ingest


@app.command("sources")
def list_sources() -> None:
    """Every registered connector."""
    for connector in registry.all():
        typer.echo(
            f"  {connector.source_key:20} {connector.kind.value:15} {connector.display_name}"
        )


@app.command("ingest")
def ingest(
    source: str = typer.Option(..., "--source", "-s", help="Connector source_key."),
    limit_variants: int | None = typer.Option(None, "--limit", help="Only the first N variants."),
) -> None:
    """Run one connector. A failure here never fails the pipeline."""
    try:
        connector = registry.get(source)
    except KeyError as exc:
        typer.secho(str(exc), fg="red")
        raise typer.Exit(1) from exc

    start = time.monotonic()
    with session_scope() as session:
        result = run_connector(session, connector, limit_variants=limit_variants)

    colour = "green" if result.ok else "yellow"
    typer.secho(
        f"{source}: {result.status.value}  ({time.monotonic() - start:.1f}s)",
        fg=colour,
        bold=True,
    )
    typer.echo(f"    refs discovered        {result.refs_discovered:>8,}")
    typer.echo(f"    payloads fetched       {result.payloads_fetched:>8,}")
    typer.echo(f"    units inserted         {result.units_inserted:>8,}")
    typer.echo(f"    units skipped (dupes)  {result.units_skipped:>8,}")
    typer.echo(f"    errors                 {result.error_count:>8,}")
    if result.last_error:
        typer.secho(f"    last error: {result.last_error}", fg="yellow")


# ---------------------------------------------------------------- enrichment


@enrich_app.command("resolve")
def enrich_resolve() -> None:
    """Decide which vehicle each listing describes."""
    start = time.monotonic()
    with session_scope() as session:
        stats = resolve_listings(session)
    _report("entity resolution", stats, time.monotonic() - start)


@enrich_app.command("extract")
def enrich_extract() -> None:
    """Pull topic-level opinion out of every resolved review."""
    start = time.monotonic()
    with session_scope() as session:
        stats = extract_opinions(session)
    _report("aspect extraction", stats, time.monotonic() - start)


@enrich_app.command("score")
def enrich_score(
    recompute: bool = typer.Option(False, "--recompute", help="Re-score already scored units."),
) -> None:
    """Work out how much each review should count."""
    start = time.monotonic()
    with session_scope() as session:
        stats = score_credibility(session, recompute=recompute)
    _report("credibility scoring", stats, time.monotonic() - start)


@enrich_app.command("fuse")
def enrich_fuse(
    limit: int | None = typer.Option(None, "--limit", help="Only the first N variants."),
) -> None:
    """Combine everything into verdicts, one per variant per strategy."""
    start = time.monotonic()
    with session_scope() as session:
        stats = fuse_all(session, variant_limit=limit)
    _report("fusion", stats, time.monotonic() - start)


# ---------------------------------------------------------------- whole pipeline


@pipeline_app.command("nightly")
def pipeline_nightly(
    sources: str = typer.Option("fixture", "--sources", help="Comma-separated source keys."),
    limit_variants: int | None = typer.Option(None, "--limit", help="Only the first N variants."),
) -> None:
    """Everything, in order. This is what the scheduled workflow calls.

    A source that fails is reported and skipped. The stages after it still
    run, because the product is meant to stay complete with three of eight
    sources alive.
    """
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    overall = time.monotonic()

    with session_scope() as session:
        seed_all(session)
        seed_catalogue(session)

    failed: list[str] = []
    for key in [s.strip() for s in sources.split(",") if s.strip()]:
        try:
            connector = registry.get(key)
        except KeyError as exc:
            typer.secho(f"  {key}: {exc}", fg="red")
            failed.append(key)
            continue
        with session_scope() as session:
            result = run_connector(session, connector, limit_variants=limit_variants)
        colour = "green" if result.ok else "yellow"
        typer.secho(
            f"  ingest {key:16} {result.status.value:14} "
            f"+{result.units_inserted:,} units, {result.units_skipped:,} skipped",
            fg=colour,
        )
        if not result.ok:
            failed.append(key)

    for name, fn in (
        ("resolve", resolve_listings),
        ("extract", extract_opinions),
        ("score", score_credibility),
    ):
        start = time.monotonic()
        with session_scope() as session:
            stats = fn(session)
        _report(name, stats, time.monotonic() - start)

    start = time.monotonic()
    with session_scope() as session:
        stats = fuse_all(session, variant_limit=limit_variants)
    _report("fuse", stats, time.monotonic() - start)

    typer.secho(f"\nnightly finished in {time.monotonic() - overall:.1f}s", bold=True)
    if failed:
        typer.secho(f"sources that did not succeed: {', '.join(failed)}", fg="yellow")


if __name__ == "__main__":
    app()
