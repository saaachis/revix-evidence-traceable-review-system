# Contributing

Three people, twelve weeks, one repository. These rules exist so that nobody spends a Sunday resolving a merge conflict in the schema.

---

## 1. Before your first commit — set your identity

Commits are attributed by the email in your git config, **not** by which account you are logged into. If you use a work laptop, check this before you commit anything, otherwise your work shows up under the wrong account and cannot be reattributed without a history rewrite.

```bash
git config user.name  "Your Name"
git config user.email "your-personal-email@example.com"    # the email on your GitHub account
```

Run it inside the repository (no `--global`), so it only applies here. Then verify:

```bash
git config user.email          # must be your personal email
git log -1 --pretty='%an <%ae>'   # after your first commit
```

If your GitHub email is private, use your `username@users.noreply.github.com` address instead — GitHub still links the commit to your profile.

## 2. Branching

`main` is always deployable. Nobody commits to it directly.

```
main
 ├── feat/connector-cardekho
 ├── feat/entity-resolution-blocking
 ├── fix/verdict-interval-rounding
 └── docs/revise-aspect-taxonomy
```

| Prefix | For |
|---|---|
| `feat/` | New capability |
| `fix/` | Bug fix |
| `docs/` | Documentation |
| `chore/` | Tooling, CI, dependencies |
| `exp/` | Experiments not intended to merge as-is |

Branch off `main`, keep branches short-lived, rebase rather than merge `main` into your branch.

## 3. Commits

Conventional commits, present tense, one logical change per commit.

```
feat(pipeline): add token-bucket rate limiter to connector framework
fix(api): return 404 rather than 500 for unseeded variants
docs(proposal): record why NLI contradiction detection was dropped
chore(ci): run alembic migrations before the test job
```

Scopes: `web`, `api`, `pipeline`, `db`, `docs`, `ci`, `eval`.

Never commit: `.env`, credentials, API keys, raw scraped payloads, model binaries, `node_modules`, `__pycache__`, or anything under `data/raw/`. **This repository is public.** If a secret is ever committed, rotate the key first and rewrite history second — in that order.

## 4. Pull requests

Every change reaches `main` through a PR, including your own area.

- Open it early as a draft. A visible half-finished branch is better than an invisible finished one.
- Keep it under roughly 400 changed lines where you can. Large PRs do not get reviewed, they get approved.
- Fill in the template: what changed, why, how it was checked.
- **One approval from someone who does not own that area.** Cross-area review is how the three of us stay able to demo each other's work.
- CI must be green.
- Squash-merge, and delete the branch.

## 5. Areas of ownership

| Path | Owner | Meaning |
|---|---|---|
| `pipeline/**` | Aditya | Connectors, orchestration, raw store |
| `db/**`, entity resolution, fusion, `data/gold/**` | Devika | Schema evolution, intelligence, evaluation |
| `apps/**` | Saachi | API contract, frontend, deployment |
| `docs/**` | shared | Anyone, but a change to `proposal.md` needs one review |

Ownership means *you are the reviewer of last resort*, not that only you may touch it.

**The schema is jointly owned.** Any migration under `db/migrations/` needs review from all three, because it is the one thing that breaks everybody at once.

## 6. Architectural invariants

Some rules are not stylistic. Breaking one means updating [docs/proposal.md](docs/proposal.md) with the reasoning, not leaving a PR comment:

1. No model inference on the read path.
2. Every derived table is recomputable from `raw` and `core`.
3. Every claim rendered in the interface has rows in `verdict_claim_evidence`.
4. The application renders a complete verdict with `LLM_ENABLED=false`.
5. A dead connector degrades the product; it never breaks it.

## 7. Collecting data responsibly

Before writing any connector:

- Read the site's `robots.txt` and terms, and record what you found in the connector's module docstring. This goes into the report.
- Rate-limit. Use the framework's token bucket; do not bypass it.
- Cache aggressively and persist the raw payload, so we never fetch the same thing twice.
- Store references and derived structure. Do not mirror full article or review text where the terms forbid it.
- Attribute and link back on every surface that shows the evidence.
- Store author identities pseudonymously. No names, no emails, no profile URLs beyond what is needed to link back.
- Prefer official APIs (Reddit, YouTube) over scraping wherever one exists.

If a source's terms clearly forbid what we want to do, we drop the source and document why. The resilience contract means the product survives it.

## 8. Local setup

Full instructions land in week 1 with the schema. For now:

```bash
git clone https://github.com/saaachis/revix-evidence-traceable-review-system.git
cd revix-evidence-traceable-review-system
cp .env.example .env        # fill in your own values; never commit this file
```

## 9. Weekly rhythm

- **The deployed application must work every Friday.** This is the single most important discipline in the project.
- Checkpoints at **week 4** and **week 8**. If week 8 slips, cut in the order agreed in [docs/proposal.md](docs/proposal.md) section 24 — and never cut the fusion toggle, the metrics page or the admin dashboard.
