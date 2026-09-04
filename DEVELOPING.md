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
uv run revix pipeline nightly     # seed, ingest, resolve, extract, score, fuse
uv run revix db status
```

That last command should report a few thousand evidence units and a hundred or
so verdicts. Then start the API:

```bash
uv run uvicorn revix_api.main:app --reload --port 8000
```

`http://localhost:8000/docs` is the generated OpenAPI browser. The endpoint
worth looking at first is:

```
GET /variants/{id}/verdict?fusion=equal
GET /variants/{id}/verdict?fusion=credibility_weighted
```

Switching between those is the whole product. The overall score moves, the
topics reorder, and the effective sample size drops while the interval widens,
because weighting carefully means admitting you have less evidence than the
raw count suggests.

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
uv run mypy packages/revix_core/src pipeline/src apps/api/src   # types
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
uv run revix sources                 # every registered connector
uv run revix db status               # how much of everything exists
uv run revix enrich fuse             # recompute verdicts without re-ingesting
docker compose logs -f db            # database logs
docker compose down -v               # wipe the database completely
uv run pytest -m "not db"            # tests that need no database
```
