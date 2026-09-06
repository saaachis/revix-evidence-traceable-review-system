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

import json
import logging
import pathlib
import time
from typing import Any

import typer
from sqlalchemy import delete, func, select, text

from revix_core.db import session_scope
from revix_core.models import (
    Aspect,
    AspectOpinion,
    EvalRun,
    EvidenceSource,
    EvidenceUnit,
    FusionConfig,
    SourceListing,
    VehicleVariant,
    Verdict,
)
from revix_core.settings import get_settings
from revix_pipeline.catalogue import seed_catalogue
from revix_pipeline.connectors import registry, run_connector
from revix_pipeline.connectors.base import CatalogSeed
from revix_pipeline.enrichment import (
    extract_opinions,
    fuse_all,
    resolve_listings,
    score_credibility,
)
from revix_pipeline.evaluation import ExperimentReport, run_fusion_experiment
from revix_pipeline.reference import seed_all

#: Kept as a named constant rather than inline, because a default naming a
#: connector that no longer exists silently ingests nothing. That happened
#: once: the fixture sources were renamed and this default was not, so CI
#: built an empty database and suppressed every verdict without failing.
DEFAULT_SOURCES = "fixture_owner,fixture_forum,fixture_expert"

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
eval_app = typer.Typer(help="Does the weighting actually help?", no_args_is_help=True)
gold_app = typer.Typer(help="The hand-labelled sets.", no_args_is_help=True)
model_app = typer.Typer(help="Train and measure the aspect classifier.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(enrich_app, name="enrich")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(eval_app, name="eval")
app.add_typer(gold_app, name="gold")
app.add_typer(model_app, name="model")


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


@app.command("probe")
def probe(
    source: str = typer.Option(..., "--source", "-s", help="Connector source_key."),
    manufacturer: str = typer.Option("Hyundai", "--manufacturer"),
    model: str = typer.Option("Creta", "--model"),
    variant: str = typer.Option("SX (O) Turbo DCT", "--variant"),
    vehicle_class: str = typer.Option("car", "--class", help="car or two_wheeler."),
) -> None:
    """Does this source still work? Answers without touching the database.

    Runs one connector's discover, fetch and parse for a single vehicle and
    reports what came back. Nothing is written anywhere.

    Two jobs. Checking a credential without granting anyone database access,
    and finding out whether a site has changed its markup before a nightly run
    quietly returns nothing at four in the morning.
    """
    try:
        connector = registry.get(source)
    except KeyError as exc:
        typer.secho(str(exc), fg="red")
        raise typer.Exit(1) from exc

    seed = CatalogSeed(
        variant_id="probe",
        manufacturer=manufacturer,
        model=model,
        variant_name=variant,
        vehicle_class=vehicle_class,
    )
    typer.secho(f"{source}: {manufacturer} {model} ({vehicle_class})", bold=True)

    start = time.monotonic()
    try:
        refs = list(connector.discover(seed))
    except Exception as exc:
        typer.secho(f"    discover failed: {type(exc).__name__}: {exc}", fg="red")
        raise typer.Exit(1) from exc

    typer.echo(f"    discovered            {len(refs):>6,}")
    if not refs:
        typer.secho(
            "    nothing to fetch. Either this source skips this vehicle class, "
            "or its search returned no results.",
            fg="yellow",
        )
        raise typer.Exit(1)

    drafts = []
    failures = 0
    for ref in refs:
        try:
            drafts.extend(connector.parse(connector.fetch(ref)))
        except Exception as exc:
            failures += 1
            typer.secho(f"    {ref.url}: {type(exc).__name__}: {exc}", fg="yellow")

    typer.echo(f"    fetched               {len(refs) - failures:>6,}")
    typer.echo(f"    parsed into units     {len(drafts):>6,}")
    typer.echo(
        f"    with a rating         {sum(1 for d in drafts if d.rating_raw is not None):>6,}"
    )
    typer.echo(f"    with a date           {sum(1 for d in drafts if d.published_at):>6,}")
    typer.echo(f"    naming a variant      {sum(1 for d in drafts if d.variant_hint):>6,}")
    typer.echo(
        f"    stating ownership     {sum(1 for d in drafts if d.ownership_duration_months):>6,}"
    )
    typer.echo(f"    took                  {time.monotonic() - start:>6.1f}s")

    if drafts:
        sample = drafts[0]
        typer.secho("\n    a sample unit", fg="cyan")
        typer.echo(f"      listing   {sample.listing_title}")
        typer.echo(f"      rating    {sample.rating_raw} / {sample.rating_scale_max}")
        typer.echo(f"      published {sample.published_at}")
        typer.echo(f"      text      {sample.text[:120].replace(chr(10), ' ')}...")

    # Reaching a source and getting nothing usable out of it is a failure, and
    # a scheduled check that exits 0 on that would be worse than no check.
    if not drafts:
        typer.secho("\n    fetched, but parsed nothing. The markup may have changed.", fg="red")
        raise typer.Exit(1)


@catalogue_app.command("discover")
def catalogue_discover(
    candidates: str = typer.Option("data/seed/candidates.json", "--candidates"),
    catalogue: str = typer.Option("data/seed/catalogue.json", "--catalogue"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report, write nothing."),
) -> None:
    """Read variant specs from the sources and add them to the catalogue.

    Run by hand, never in the nightly. A catalogue that changes under a
    running pipeline is a catalogue nobody can reason about.

    Specs come from the same sites the reviews do, under the same permission:
    CarDekho publishes a schema.org ProductGroup per model and a Car object
    per variant carrying fuel, gearbox, displacement and the ARAI figure.
    Typing those by hand would scale badly and, worse, would mean a spec
    somebody half-remembered.
    """
    from revix_pipeline.catalogue_discovery import Candidate, discover
    from revix_pipeline.connectors.politeness import PoliteClient

    src = json.loads(pathlib.Path(candidates).read_text(encoding="utf-8"))
    book = json.loads(pathlib.Path(catalogue).read_text(encoding="utf-8"))
    known_models = {m["slug"] for m in book["models"]}
    known_makes = {m["slug"] for m in book["manufacturers"]}
    # A model refers to its manufacturer by slug, not by display name. Writing
    # the name here produced a catalogue that looked right and blew up in the
    # seeder with KeyError: 'Maruti Suzuki'.
    slug_for_make = {m["name"]: m["slug"] for m in book["manufacturers"]}
    slug_for_make.update({m["name"]: m["slug"] for m in src.get("manufacturers", [])})

    client = PoliteClient("catalogue", rate_limit_rpm=10, respect_robots=True)
    added_models: list[dict[str, Any]] = []
    empty: list[str] = []
    start = time.monotonic()

    for row in src["candidates"]:
        if row["slug"] in known_models:
            continue
        candidate = Candidate(**{k: v for k, v in row.items() if k != "notes"})
        variants = discover(candidate, client)
        label = f"{candidate.manufacturer} {candidate.name}"
        if not variants:
            # Recorded rather than skipped silently. A model that yields
            # nothing is a slug that has moved, and finding that out three
            # weeks later from an empty page is the expensive way.
            empty.append(label)
            typer.secho(f"  {label:34} nothing found", fg="yellow")
            continue
        typer.secho(f"  {label:34} {len(variants)} variants", fg="green")
        make_slug = slug_for_make.get(candidate.manufacturer)
        if make_slug is None:
            typer.secho(
                f"  {label:34} unknown manufacturer, add it to the candidates file",
                fg="red",
            )
            empty.append(label)
            continue
        added_models.append(
            {
                "manufacturer": make_slug,
                "slug": candidate.slug,
                "name": candidate.name,
                "vehicle_class": candidate.vehicle_class,
                "body_style": candidate.body_style,
                "segment": candidate.segment,
                "launch_year": candidate.launch_year,
                "variants": [v.as_dict() for v in variants],
            }
        )

    new_makes = [m for m in src.get("manufacturers", []) if m["slug"] not in known_makes]
    total_variants = sum(len(m["variants"]) for m in added_models)

    typer.secho(
        f"\n{len(added_models)} models, {total_variants} variants, "
        f"{len(new_makes)} new manufacturers, in {time.monotonic() - start:.0f}s",
        bold=True,
    )
    if empty:
        typer.secho(f"    {len(empty)} yielded nothing: {', '.join(empty)}", fg="yellow")

    if dry_run:
        typer.echo("    dry run, nothing written")
        return
    if not added_models:
        typer.secho("    nothing new to add", fg="yellow")
        return

    book["manufacturers"].extend(new_makes)
    book["models"].extend(added_models)
    pathlib.Path(catalogue).write_text(
        json.dumps(book, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    grand = sum(len(m.get("variants", [])) for m in book["models"])
    typer.secho(
        f"    {catalogue} now holds {len(book['models'])} models and {grand} variants",
        fg="green",
        bold=True,
    )
    typer.secho("    now run: uv run revix catalogue seed", fg="cyan")


# ---------------------------------------------------------------- gold sets


@gold_app.command("sample")
def gold_sample(
    per_aspect: int = typer.Option(40, "--per-aspect", help="Sentences to draw per topic."),
    out: str = typer.Option("data/gold/aspects.jsonl", "--out"),
) -> None:
    """Draw a spread of real sentences for somebody to label.

    Stratified by topic, because a random draw returns a pile of sentences
    about looks and mileage and almost nothing about the service centre, which
    is the aspect this project cares most about. It also includes a bucket the
    lexicon matched to nothing, because that is exactly where a classifier can
    beat it.

    Appends to whatever is already labelled rather than replacing it.
    """
    from revix_pipeline.ml.gold import coverage, load_gold, sample_for_labelling, save_gold

    path = pathlib.Path(out)
    existing = load_gold(path)
    with session_scope() as session:
        drawn = sample_for_labelling(session, per_aspect=per_aspect, existing=existing)

    if not drawn:
        typer.secho("no sentences to draw. Ingest some evidence first.", fg="yellow")
        raise typer.Exit(1)

    save_gold(existing + drawn, path)
    typer.secho(f"{len(drawn):,} new sentences written to {path}", fg="green", bold=True)
    typer.secho("    READ docs/labelling-the-gold-set.md BEFORE LABELLING.", fg="yellow", bold=True)
    typer.echo("    It covers how to split the work, what an empty list means, and")
    typer.echo("    why agreeing with the lexicon out of laziness ruins the whole set.")
    _report("gold set", coverage(load_gold(path)), 0.0)


@gold_app.command("status")
def gold_status(path: str = typer.Option("data/gold/aspects.jsonl", "--path")) -> None:
    """How much is labelled, and which topics are still thin."""
    from revix_pipeline.ml.gold import coverage, load_gold

    items = load_gold(pathlib.Path(path))
    if not items:
        typer.secho(f"no gold set at {path}. Run: revix gold sample", fg="yellow")
        raise typer.Exit(1)
    stats = coverage(items)
    _report("gold set", stats, 0.0)
    if stats["unlabelled"]:
        typer.secho(
            f"    {stats['unlabelled']:,} still to label. See docs/labelling-the-gold-set.md",
            fg="yellow",
        )


# ---------------------------------------------------------------- the model


@model_app.command("train")
def model_train(
    out: str = typer.Option("data/models/aspect_classifier.joblib", "--out"),
    gold_path: str = typer.Option("data/gold/aspects.jsonl", "--gold"),
) -> None:
    """Train the aspect classifier on weak labels from the lexicon.

    The gold sentences are held out of training, so the evaluation afterwards
    is on text the model has never seen. That is the difference between a test
    score and a memory test.
    """
    from revix_pipeline.ml.aspect_model import build_training_set, train_classifier
    from revix_pipeline.ml.gold import load_gold

    gold = load_gold(pathlib.Path(gold_path))
    held_out = {item.text for item in gold}

    start = time.monotonic()
    with session_scope() as session:
        sentences, targets = build_training_set(session, exclude=held_out)

    typer.echo(f"    training sentences    {len(sentences):>8,}")
    typer.echo(f"    held out for testing  {len(held_out):>8,}")
    classifier = train_classifier(sentences, targets)
    path = classifier.save(pathlib.Path(out))
    typer.secho(
        f"trained in {time.monotonic() - start:.1f}s, written to {path}", fg="green", bold=True
    )


@model_app.command("evaluate")
def model_evaluate(
    gold_path: str = typer.Option("data/gold/aspects.jsonl", "--gold"),
    model_path: str = typer.Option("data/models/aspect_classifier.joblib", "--model"),
    record: bool = typer.Option(False, "--record", help="Write the result to eval_run."),
) -> None:
    """Score the lexicon and the classifier on the same hand-labelled set.

    Reports macro F1 as the headline. Micro is dominated by the common topics,
    so a system that handles looks and mileage well and the service centre
    badly scores respectably on it; macro treats every topic equally and is
    the number that notices.
    """
    from revix_pipeline.ml.aspect_model import AspectClassifier, evaluate_against_gold
    from revix_pipeline.ml.gold import load_gold

    gold = load_gold(pathlib.Path(gold_path))
    labelled = [item for item in gold if item.is_labelled]
    if not labelled:
        typer.secho(
            f"nothing labelled in {gold_path}. A classifier with no gold set is a "
            "lexicon with extra steps, so this refuses to print a number. "
            "    Start here: docs/labelling-the-gold-set.md",
            fg="red",
        )
        raise typer.Exit(1)

    classifier = AspectClassifier.load(pathlib.Path(model_path))
    results = evaluate_against_gold(gold, classifier)

    typer.secho(f"measured on {len(labelled):,} hand-labelled sentences", bold=True)
    typer.echo(f"    {'system':14} {'macro F1':>9} {'micro F1':>9}")
    for result in results:
        typer.echo(f"    {result.name:14} {result.macro_f1:>9.3f} {result.micro_f1:>9.3f}")

    if len(results) == 2:
        delta = results[1].macro_f1 - results[0].macro_f1
        colour = "green" if delta > 0 else "yellow"
        verdict = "better than" if delta > 0 else "no better than"
        typer.secho(
            f"\n    the classifier is {verdict} the lexicon by {delta:+.3f} macro F1", fg=colour
        )

    typer.secho("\n    per topic, best system", fg="cyan")
    best = results[-1]
    for aspect, scores in sorted(best.per_aspect.items(), key=lambda kv: -kv[1]["f1"]):
        typer.echo(
            f"      {aspect:22} F1 {scores['f1']:.3f}  "
            f"P {scores['precision']:.3f}  R {scores['recall']:.3f}  n={int(scores['support'])}"
        )

    if record:
        with session_scope() as session:
            for result in results:
                session.add(
                    EvalRun(
                        component="aspect_extraction",
                        system=result.name,
                        git_sha=_git_sha(),
                        n_items=result.n_items,
                        primary_metric="macro_f1",
                        primary_value=round(result.macro_f1, 4),
                        detail=result.as_dict(),
                    )
                )
        typer.secho(f"\n    {len(results)} result(s) recorded to eval_run", fg="green")


def _git_sha() -> str | None:
    """Which commit produced a number, so it can be traced to code."""
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()[:40]
    except Exception:
        return None


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


@db_app.command("purge")
def db_purge(
    source: list[str] = typer.Option(
        ..., "--source", "-s", help="Source key to remove. Repeat for several."
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Remove every trace of a source, and the verdicts built on it.

    Written for one specific job: replacing generated development evidence
    with real reviews, without hand-editing a production database.

    Deleting the source row cascades to its raw payloads, ingest runs,
    listings and evidence units, and from those to aspect opinions and claim
    citations. Verdicts go too. They are fully derived, recomputing them costs
    one `revix enrich fuse`, and leaving them would publish scores built on
    evidence that no longer exists, with citations pointing at deleted rows.

    The catalogue and the reference data are untouched.
    """
    with session_scope() as session:
        rows = session.execute(
            select(EvidenceSource.id, EvidenceSource.source_key, EvidenceSource.display_name).where(
                EvidenceSource.source_key.in_(source)
            )
        ).all()
        found = {r.source_key for r in rows}
        missing = sorted(set(source) - found)
        if missing:
            typer.secho(f"unknown source(s): {', '.join(missing)}", fg="red")
            raise typer.Exit(1)

        units = session.scalar(
            select(func.count())
            .select_from(EvidenceUnit)
            .where(EvidenceUnit.source_id.in_([r.id for r in rows]))
        )
        verdicts = session.scalar(select(func.count()).select_from(Verdict))

        typer.secho("This will permanently delete:", fg="yellow", bold=True)
        for row in rows:
            typer.echo(f"    {row.source_key:20} {row.display_name}")
        typer.echo(f"    {units:,} evidence units, and every opinion and citation from them")
        typer.echo(f"    {verdicts:,} verdicts, which must be recomputed afterwards")

        if not yes and not typer.confirm("\nProceed?"):
            typer.echo("nothing was deleted.")
            raise typer.Exit(1)

        session.execute(delete(Verdict))
        session.execute(delete(EvidenceSource).where(EvidenceSource.id.in_([r.id for r in rows])))

    typer.secho("\npurged.", fg="green", bold=True)
    with session_scope() as session:
        remaining = session.scalar(select(func.count()).select_from(EvidenceUnit))
        typer.echo(f"    {remaining:,} evidence units remain")
    typer.secho("    now run: revix pipeline nightly --sources <the sources you want>", fg="cyan")


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
    # `nightly` deliberately survives a dead source. A bare `ingest --source x`
    # is different: one source was asked for, and reporting success when it
    # produced nothing is how a green run that did no work gets missed.
    if not result.ok:
        raise typer.Exit(1)


# ---------------------------------------------------------------- evaluation


def _print_experiment(report: ExperimentReport) -> None:
    typer.secho(
        f"gold targets {report.gold_targets:,} across {report.eligible_variants:,} variants, "
        f"{report.replicates:,} replicates",
        bold=True,
    )
    typer.echo(f"    sources in the pool: {', '.join(report.sources_present) or 'none'}")

    if not report.ran:
        for note in report.notes:
            typer.secho(f"\n{note}", fg="yellow")
        return

    for title, rows in (("with metadata", report.results), ("without metadata", report.ablation)):
        if not rows:
            continue
        typer.secho(f"\n{title}", fg="cyan", bold=True)
        typer.echo(
            f"    {'strategy':22} {'k':>4} {'RMSE':>8} {'MAE':>8} "
            f"{'bias':>8} {'rho':>7} {'(n)':>5} {'cover80':>8} {'ECE':>7}"
        )
        for row in sorted(rows, key=lambda r: (r.k, r.strategy)):
            rho = row.spearman_mean
            typer.echo(
                f"    {row.strategy:22} {row.k:>4} {row.rmse:>8.3f} "
                f"{row.mean_absolute_error:>8.3f} {row.bias:>+8.3f} "
                f"{(f'{rho:.3f}' if rho == rho else '   n/a'):>7} "
                f"{row.spearman_n_variants:>5} "
                f"{row.coverage.get('0.80', float('nan')):>8.3f} "
                f"{row.expected_calibration_error:>7.3f}"
            )

    for note in report.notes:
        typer.secho(f"\n{note}", fg="yellow")


@eval_app.command("fusion")
def eval_fusion(
    replicates: int = typer.Option(200, "--replicates", help="Random subsamples per target."),
    ks: str = typer.Option("10,20,30,50", "--k", help="Comma-separated subsample sizes."),
    limit_variants: int | None = typer.Option(None, "--limit", help="Only the first N variants."),
    out: str | None = typer.Option(None, "--out", help="Write the full report as JSON."),
) -> None:
    """The section 18.1 experiment: does weighting beat counting?

    Holds out verified long-term owners as the target, estimates them from
    what is left, and scores every strategy against them. Reports the required
    ablation alongside, because a credibility model that only restates the
    platform's own verified flag has not learned anything.
    """
    sizes = tuple(int(k.strip()) for k in ks.split(",") if k.strip())
    start = time.monotonic()
    with session_scope() as session:
        report = run_fusion_experiment(
            session, variant_limit=limit_variants, ks=sizes, replicates=replicates
        )

    _print_experiment(report)
    typer.secho(f"\nfinished in {time.monotonic() - start:.1f}s", bold=True)

    if out:
        path = pathlib.Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
        typer.echo(f"report written to {path}")

    # Nothing measurable is not success. A silent zero here is exactly how a
    # scheduled run reports "the experiment is fine" while measuring nothing.
    if not report.ran:
        raise typer.Exit(1)


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
    sources: str = typer.Option(DEFAULT_SOURCES, "--sources", help="Comma-separated source keys."),
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

    requested = [s.strip() for s in sources.split(",") if s.strip()]
    failed: list[str] = []
    for key in requested:
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

    # Losing some sources is the resilience contract working as designed.
    # Losing all of them is a broken run and must not exit zero: every stage
    # downstream will happily "succeed" over an empty database and suppress
    # every verdict, which looks like a healthy run from the outside.
    if requested and len(failed) == len(requested):
        typer.secho(
            f"every requested source failed ({', '.join(requested)}). "
            "Nothing was ingested, so nothing downstream means anything.",
            fg="red",
            bold=True,
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
