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

Then the frontend, in a second terminal:

```bash
cd apps/web
npm install
npm run dev          # http://localhost:3000
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

npm run lint      --prefix apps/web                   # eslint
npm run typecheck --prefix apps/web                   # tsc
npm run build     --prefix apps/web                   # next build
npm run e2e       --prefix apps/web                   # browser smoke test
```

The browser smoke test needs the API on :8000 and the web app on :3000, both
already running. It drives a real Chrome and its most important assertion is
that flipping the weighting switch changes the numbers. If that ever stopped
being true the product would have no point, and no unit test would notice.

## The typed API client

`apps/web/src/lib/api-types.ts` is generated from the OpenAPI schema and must
never be hand-edited. After changing any response model:

```bash
npm run openapi --prefix apps/web     # regenerate the schema and the types
```

CI regenerates and diffs against what is committed, so the frontend and the
serving layer cannot drift apart without the build going red.

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
apps/web/              Next.js 16, Tailwind v4, typed client from OpenAPI
db/migrations/         Alembic
docs/adr/              why things are the way they are
```

## The sources, and which are real

| Source | What it is | Credentials | Notes |
|---|---|---|---|
| `carwale` | CarWale owner reviews | none | Cars only. Paginated, ~50 per model, and the only source with dates |
| `cardekho` | CarDekho and BikeDekho | none | ~22 per model, no pagination, no dates |
| `youtube` | Comments on review videos | API key | ~82 per model, many are questions rather than reviews |
| `reddit` | r/CarsIndia and friends | approval | Reddit closed self-serve API access; see ADR 0006 |
| `fixture_*` | Generated | none | Development and CI only. Never publish a demo from these |

Check any of them without a database, and without handing anyone a key:

```bash
uv run revix probe --source carwale
uv run revix probe --source youtube --manufacturer Tata --model Nexon
```

It runs discover, fetch and parse for one vehicle and reports what came back.
Use it when a nightly returns less than you expected, because a site changing
its markup looks exactly like a site having no reviews.

## Running the live connectors

Everything works without these. `fixture_owner`, `fixture_forum` and
`fixture_expert` generate synthetic evidence, which is what CI runs and what
you want while working on anything downstream of ingestion.

The two live sources need credentials, and both are free. Neither takes longer
than five minutes.

**Reddit.** Go to <https://www.reddit.com/prefs/apps>, "create another app",
choose type **script**, put anything in the redirect URI. Copy the id under the
app name and the secret beside it into `.env`:

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=revix/0.1 (academic project; contact: you@example.com)
```

Reddit asks for a descriptive user agent with a contact in it. Give it a real
one; a generic agent is how a client gets rate limited.

**YouTube.** In a Google Cloud project, enable **YouTube Data API v3**, then
create an API key under Credentials:

```
YOUTUBE_API_KEY=...
```

The free quota is 10,000 units a day. A search costs 100 and a page of comments
costs 1, so a full run over 43 variants spends roughly 4,500. The connector
refuses a call it cannot afford rather than letting the quota run out mid-run.

Then:

```bash
uv run revix ingest --source reddit --limit 5     # start small
uv run revix ingest --source youtube --limit 5
uv run revix pipeline nightly --sources reddit,youtube
```

Without credentials these fail by name, telling you which variable is missing,
and exit non-zero. That is a configuration state rather than a crash, and
`revix pipeline nightly` still runs every other stage around a dead source.

Which subreddits get read is configuration, not code:

```
REDDIT_SUBREDDITS_CAR=CarsIndia
REDDIT_SUBREDDITS_TWO_WHEELER=indianbikes
```

**Confirm each name exists before a real run.** One that is private, renamed or
misspelled is skipped silently, because failing the whole source over one bad
name in a list would be worse.

Note that with only two live sources, `min_evidence_units` and
`min_distinct_sources` will suppress most verdicts. That is the evidence floor
working, not a fault. See [ADR 0006](docs/adr/0006-official-apis-only-for-ingestion.md).

## The fusion experiment

The question the project rests on: does weighting evidence beat counting it?

```bash
uv run revix enrich score --recompute   # needed once, see below
uv run revix eval fusion --replicates 200 --k 10,20,30,50 --out data/eval/fusion.json
```

It holds out verified owners with 12+ months and 10,000+ km as the target,
estimates them from everything else, and scores each strategy on RMSE, Spearman
across variants and interval coverage. The ablation runs alongside, with every
metadata signal removed from the weighting, because a credibility model that
only restates the platform's verified flag has not learned anything.

`--recompute` is needed once because the ablation reads a `base_textual` figure
that older credibility rows do not have. Without it the ablation understates
the gap rather than inventing one, which is the safe direction to be wrong in
but still wrong.

**On fixture data the output is not a finding, and the report says so in
capitals.** The numbers describe the generator we wrote. The experiment becomes
a measurement only once real evidence is in the pool, and today it cannot run
on Reddit or YouTube data at all, since neither verifies ownership and the gold
set comes out empty. See [ADR 0007](docs/adr/0007-how-the-fusion-experiment-avoids-fooling-us.md).

## Useful commands

```bash
uv run revix --help                  # every pipeline stage
uv run revix db show-reference       # the nine aspects, the three strategies
uv run revix sources                 # every registered connector
uv run revix db status               # how much of everything exists
uv run revix enrich fuse             # recompute verdicts without re-ingesting
uv run revix eval fusion             # does weighting beat counting? (section 18.1)
docker compose logs -f db            # database logs
docker compose down -v               # wipe the database completely
uv run pytest -m "not db"            # tests that need no database
```
