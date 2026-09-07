# Revix

### driven by reviews.

**An evidence-traceable consumer decision support platform for the Indian automobile market.**

A cross-source review system for cars and two-wheelers, covering what owners, experts, forums and official records actually say — and telling you which of them deserves to be believed.

> Modern Application Development · M.Sc. Data Science · Nilkamal School of Mathematics, Applied Statistics and Analytics, SVKM's NMIMS Mumbai

---

## The problem

A person buying a vehicle in India reads owner reviews on CarDekho, then the same vehicle on CarWale or BikeWale, then a forty-page Team-BHP ownership thread, then three YouTube reviews, then a road test in Autocar India. They finish with six opinions that disagree with one another and no way to judge which of them deserves to be believed.

The bias always runs one way. Early reviews are kinder than late ones. Media is kinder than owners. Nobody shows the disagreement, because disagreement makes a product page look bad.

**Revix reads all of them, works out which reviews deserve trust, and gives one clear verdict where every number links back to the reviews behind it.**

## What it does

| | | | | |
|---|---|---|---|---|
| **COLLECT** | **MATCH** | **SCORE** | **COMBINE** | **EXPLAIN** |
| Owner reviews, expert reviews, forums, videos, official records | Everything mapped to one exact vehicle variant | Opinion split by topic; each review scored for trust | Weighted into a verdict with a confidence range | Every number linked to the reviews behind it |

It is a review **system**, not a review summariser. Three differences:

1. It reads **across** platforms instead of inside one.
2. It **weighs** reviews by how much they can be trusted, instead of averaging stars.
3. Every claim **links to its source reviews**, guaranteed by the database schema, not by asking a language model nicely.

## What the user sees

<img src="docs/assets/verdict-card.png" alt="The Revix verdict screen: an overall score of 7.8 with a confidence range of 7.1 to 8.4, a weighting switch, and vehicle topics ordered by how much owners disagree about them" width="820">

*Illustrative layout. Figures are placeholders. Topics are ordered by how much people disagree, not by score.*

**The flagship feature is the weighting switch.** Flip between equal weighting and credibility weighting and watch every score, interval and ranking move. That is the intellectual content of the project, made visible in thirty seconds.

## Status

| | |
|---|---|
| **Stage** | S1 and S2 submitted. Pipeline, API and site all live on real data. |
| **Live URL** | [revix-reviews.vercel.app](https://revix-reviews.vercel.app), API at [revix-api-tcyq.onrender.com](https://revix-api-tcyq.onrender.com) |
| **Next milestone** | **S3 Lab work, Friday 2 October 2026.** [What we submit](docs/s3-lab-work/01-lab-work-submission.md) |
| **Then** | S3 Working demo, Friday 16 October 2026. [Runbook](docs/s3-working-demo/01-working-demo-runbook.md) |

## Documentation

Two documents are the source of truth. Everything else defers to them.

| Document | What it covers |
|---|---|
| [**Full proposal**](docs/proposal.md) | The complete concept note and software design specification — architecture, data model, fusion engine, evaluation strategy, twelve-week roadmap, scope and glossary |
| [**Review 1 — concept, market gap and literature review**](docs/review-1/01-concept-market-gap-and-literature-review.md) | The idea and what it means, the competitive gap analysis, the background study, and what we are and are not claiming |
| [Milestone 2 — wireframe demo](docs/review-1/02-milestone-2-wireframe-demo.md) | What we are building by 14 August 2026, how, by whom, and by when |
| [**Non-functional requirements**](docs/non-functional-requirements.md) | All nine categories audited against the code: where each is met, how it was measured, and the two limits we state rather than hide |
| [S3 lab work](docs/s3-lab-work/01-lab-work-submission.md) | What the 2 October submission contains, mapped to the four marks, with a [speaking script](docs/s3-lab-work/02-lab-work-speaking-script.md) |
| [S3 working demo](docs/s3-working-demo/01-working-demo-runbook.md) | The 16 October demo: pre-flight checks, the flow, what to do when something breaks, with a [speaking script](docs/s3-working-demo/02-working-demo-speaking-script.md) |
| [Contributing](CONTRIBUTING.md) | Branching, commits, reviews, local setup, how we collect data responsibly |
| [Developing](DEVELOPING.md) | Running it locally, the quality gate, the live connectors, the fusion experiment |
| [Deploying](DEPLOYING.md) | Neon, Render and Vercel, and the two settings that fail silently |
| [Labelling the gold set](docs/labelling-the-gold-set.md) | The one task no tool can do for us, and why a number without it is a lie with decimals |

## Repository layout

```
revix/
├── apps/
│   ├── web/           Next.js + TypeScript + Tailwind — the user-facing application
│   └── api/           FastAPI, read-only, contract-first serving layer
├── pipeline/
│   ├── connectors/    One isolated connector per source; any of them can fail safely
│   └── enrichment/    resolve → embed → extract → score → verify → fuse → narrate
├── db/
│   └── migrations/    Alembic migrations. One PostgreSQL database with pgvector.
├── data/
│   ├── seed/          Catalogue seed lists
│   └── gold/          Hand-labelled evaluation sets
├── wireframes/        Milestone 2 screens as working HTML, published to GitHub Pages
├── scripts/           Operational and one-off scripts
└── docs/              Everything above
```

## Technology

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, Recharts |
| API | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Alembic |
| Database | PostgreSQL + pgvector — **one** database, not four services |
| Orchestration | Prefect, nightly batch |
| ML | sentence-transformers, scikit-learn |
| Language model | One free-tier provider behind a thin interface. Batch narration only, and **never required** |
| CI/CD | GitHub Actions |

Everything is on a free tier. The application renders a complete verdict with the language model switched off entirely.

## Scope

**We are building.** Indian cars and two-wheelers · about 120 to 150 popular variants · six to eight sources · verdict, compare, evidence and admin screens · measured accuracy for everything we build.

**We are not building.** Commercial vehicles · used-vehicle pricing · live scraping per request · vehicles outside our list · booking or dealer integration · user accounts · mobile apps.

## Team

| Name | Ownership area |
|---|---|
| Aditya Nariyapara | Platform and ingestion — connector framework, orchestration, raw store, admin backend |
| Devika Jonjale | Intelligence — entity resolution, aspect extraction, credibility, fusion, evaluation |
| Saachi Shinde | Application and experience — API contract, frontend, all user-facing surfaces, deployment |

Roles are ownership areas, not silos. The schema in week 1 is owned by all three.

## Data and ethics

Sources are read at a polite rate, cached, credited and linked back to. We store references and derived structure, not mirrored copies of anyone's content. Author identities are stored pseudonymously and never as personal data. Every screen states how many reviews it used and when it last refreshed. Verdicts below an evidence floor are suppressed rather than published badly.

## License

[MIT](LICENSE) — academic project, free to read, use and learn from.
