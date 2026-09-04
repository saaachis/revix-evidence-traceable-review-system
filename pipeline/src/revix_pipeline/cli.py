"""The `revix` command line.

Each enrichment stage is a subcommand that is safe to re-run. That property is
what lets a scheduled workflow just call them in order and retry on failure,
without needing an orchestrator to hold state.
"""

from __future__ import annotations

import typer
from sqlalchemy import select, text

from revix_core.db import session_scope
from revix_core.models import Aspect, FusionConfig
from revix_core.settings import get_settings
from revix_pipeline.reference import seed_all


def redact_dsn(dsn: str) -> str:
    """Strip the password so a DSN is safe to print or paste into an issue."""
    if "@" not in dsn or "//" not in dsn:
        return dsn
    scheme, _, rest = dsn.partition("//")
    creds, _, host = rest.rpartition("@")
    user = creds.split(":", 1)[0] if creds else ""
    return f"{scheme}//{user}:***@{host}" if user else f"{scheme}//{host}"


app = typer.Typer(
    name="revix",
    help="Revix pipeline: ingestion and nightly enrichment.",
    no_args_is_help=True,
    add_completion=False,
)

db_app = typer.Typer(help="Database maintenance and reference data.", no_args_is_help=True)
app.add_typer(db_app, name="db")


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

    # PostgresDsn is a MultiHostUrl, so there is no .host attribute. Print the
    # DSN with the password removed rather than reaching for one.
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
    total = sum(added.values())
    if total == 0:
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


if __name__ == "__main__":
    app()
