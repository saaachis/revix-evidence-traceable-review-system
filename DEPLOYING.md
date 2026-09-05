# Deploying Revix

Section 24 of the proposal sets one discipline above the schedule: **the
deployed application must work every Friday.** A project that is live in week 2
and improves weekly beats one that integrates in week 11, every time.

Three free services, about forty minutes the first time. Nothing here needs a
card except Neon, which does not ask for one on the free plan.

| Piece | Where | Why there |
|---|---|---|
| Database | **Neon** | Postgres 16 with `pgvector` and `pg_trgm` on the free plan, and a Singapore region |
| API | **Render** | Runs our Dockerfile directly, so the uv workspace installs exactly as it does locally |
| Web | **Vercel** | Builds Next.js natively and serves it from a CDN |

Render's own free Postgres is deliberately not used: it expires after 30 days,
and week 11 is a bad time to find that out.

---

## 1. The database, on Neon

1. Create a project at <https://neon.tech>. Region **AWS ap-southeast-1
   (Singapore)**, the closest free region to Indian users.
2. Copy the connection string. It looks like
   `postgresql://user:pass@ep-something.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
3. Rewrite the scheme for psycopg 3, which is what this project uses:

   ```
   postgresql+psycopg://user:pass@ep-something.../neondb?sslmode=require
   ```

   Keep `sslmode=require`. Neon refuses plaintext connections and the error it
   returns does not obviously say so.

Neon suspends an idle database and wakes it in about half a second, which is
fine. Do not disable that; it is what keeps the free plan free.

## 2. Bootstrap the schema and the data

Do this before deploying anything, so the API has something to serve on its
first request.

1. In GitHub: **Settings, Secrets and variables, Actions**, add a repository
   secret `DATABASE_URL` with the string from step 1.
2. **Actions, Nightly pipeline, Run workflow.** It runs `alembic upgrade head`,
   seeds the reference data and the catalogue, ingests, and fuses.
3. Check the run's final step. `revix db status` should report 43 variants and
   a non-zero verdict count.

That workflow is also the scheduled orchestrator, at 04:00 IST daily. See
[ADR 0002](docs/adr/0002-scheduled-ci-instead-of-prefect.md) for why this is
GitHub Actions and not Prefect.

To ingest real sources instead of fixtures, add `REDDIT_CLIENT_ID`,
`REDDIT_CLIENT_SECRET` and `YOUTUBE_API_KEY` as secrets too, then dispatch the
workflow with `reddit,youtube` in the sources box. See DEVELOPING.md.

## 3. The API, on Render

1. <https://render.com>, **New, Blueprint**, connect this repository. It reads
   [render.yaml](render.yaml) and creates the service.
2. Set the two environment variables the blueprint deliberately leaves empty:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the same string as step 1 |
   | `CORS_ALLOWED_ORIGINS` | your Vercel URL, e.g. `https://revix.vercel.app` |

   You will not know the Vercel URL yet. Put a placeholder, finish step 4, then
   come back. **This is the single most common way to end up with a site whose
   search box silently does nothing**, because the API answers 200, the browser
   discards the response, and the page says only that search is unavailable.

3. Wait for the first deploy, then check `https://<your-api>.onrender.com/health`.
   It should say `{"status":"ok","database":true,...}`.

## 4. The web app, on Vercel

1. <https://vercel.com>, **Add New, Project**, import this repository.
2. **Root Directory: `apps/web`.** Vercel then detects Next.js on its own.
3. Add one environment variable, for **all** environments:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<your-api>.onrender.com` |

   `NEXT_PUBLIC_` variables are compiled into the browser bundle at build time,
   not read at runtime. Changing it later needs a redeploy, not a restart.
4. Deploy, then go back to Render and put the real Vercel URL into
   `CORS_ALLOWED_ORIGINS`.

## 5. Confirm it actually works

Not "the pages load". Load them and check the parts that break quietly:

```bash
curl -s https://<your-api>.onrender.com/health
```

- [ ] The home page shows vehicles, not an empty state.
- [ ] **Type "Creta" in the search box and see results.** This is the CORS
      check, and it is the one that fails silently.
- [ ] Open a verdict and flip the weighting switch. The numbers must change.
- [ ] Click through to the evidence behind a claim.

---

## The cold start, and being honest about it

Render's free tier stops a service after fifteen minutes without traffic, and
the next request waits the better part of a minute while it starts. Everything
after that is fast; the p95 measured against this stack is well inside the
proposal's 300 ms target once the instance is warm.

[keepwarm.yml](.github/workflows/keepwarm.yml) sends a request every ten
minutes between 08:30 and 22:30 IST to avoid a cold start in front of an
audience. Set the `API_BASE_URL` repository **variable** to switch it on. It is
not on overnight, and if the API ever moves to a host that wakes quickly,
delete the workflow rather than keeping it out of habit.

**Before any live demo, open the site once a few minutes early.** That is worth
more than the workflow.

## Rolling back

Render keeps previous deploys: **Deploys**, pick the last good one, **Redeploy**.
Vercel is the same under **Deployments**, **Promote to Production**.

Neither rolls back the database. Migrations in this project are reversible and
the downgrade path is tested in CI, but a rollback across a migration is a
deliberate act: run `uv run alembic downgrade -1` against `DATABASE_URL`
yourself, having read what the migration did.

## What is not deployed

The wireframes at
<https://saaachis.github.io/revix-evidence-traceable-review-system/> are served
by GitHub Pages from [pages.yml](.github/workflows/pages.yml) and are unrelated
to any of the above. They are the Milestone 2 artefact and stay as they are.
