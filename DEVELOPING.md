# Developing Revix

Local setup, end to end, on a clean machine.

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.12 | pinned in `.python-version` |
| [uv](https://docs.astral.sh/uv/) | 0.9+ | workspace resolution and locking |
| Docker | any recent | runs PostgreSQL with pgvector |
| Node | 22 | the web app, from phase 1 |

## Setup

```bash
uv sync --all-packages     # install all three Python packages
docker compose up -d       # PostgreSQL 16 + pgvector on localhost:5433
uv run alembic upgrade head
uv run revix db seed-reference
uv run revix db check
```

`revix db check` prints the server version, the installed extensions and the
table count. If it exits non-zero, the extensions are missing and nothing
downstream will work.

No `.env` is needed for local work. The defaults in `revix_core.settings`
point at the compose database. Copy `.env.example` to `.env` when you need
source credentials.

## The quality gate

Run this before opening a pull request. CI runs exactly the same commands.

```bash
uv run ruff check .                                   # lint
uv run ruff format --check .                          # formatting
uv run mypy packages/revix_core/src pipeline/src      # types
uv run alembic check                                  # models match migrations
uv run pytest --cov                                   # tests
```

## Working on the schema

The schema is jointly owned. A migration is the one change that breaks
everybody at once, so every PR touching `db/migrations/` needs three approvals.

```bash
# after editing a model
uv run alembic revision --autogenerate -m "what changed"
```

Then **read the generated file before committing it**. Autogenerate is a
starting point, not an answer. Two things it reliably gets wrong here:

1. It emits pgvector column types without importing pgvector. The template in
   `db/migrations/script.py.mako` adds the import, but check it survived.
2. It creates PostgreSQL enum types alongside tables and never drops them in
   the downgrade. Add the `DROP TYPE` calls, or the next `upgrade` after a
   `downgrade` dies on "type already exists".

Always verify a migration reverses:

```bash
uv run alembic downgrade base && uv run alembic upgrade head
```

CI does this too, because a migration you cannot reverse is one you cannot
recover from.

## Layout

```
packages/revix_core/   models, settings, session. Imports neither of the others.
pipeline/              connectors, enrichment stages, the `revix` CLI
apps/api/              FastAPI, reads only from the serving schema
apps/web/              Next.js
db/migrations/         Alembic
docs/adr/              why things are the way they are
```

## Useful commands

```bash
uv run revix --help                  # every pipeline stage
uv run revix db show-reference       # the nine aspects, the three strategies
docker compose logs -f db            # database logs
docker compose down -v               # wipe the database completely
uv run pytest -m "not db"            # tests that need no database
```
