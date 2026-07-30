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

Runs every night in the background, so the app itself is instant.

It is a review **system**, not a review summariser. Three differences:

1. It reads **across** platforms instead of inside one.
2. It **weighs** reviews by how much they can be trusted, instead of averaging stars.
3. Every claim **links to its source reviews**, guaranteed by the database schema, not by asking a language model nicely.

## What the user sees

```
┌──────────────────────────────────────────────────────────────────────┐
│  Hyundai Creta SX (O) 1.5 Diesel AT              ₹19.2L - ₹20.4L     │
│                                                                       │
│  ████████████░░░░  7.8 / 10        [ 7.1 ─────── 8.4 ]               │
│  412 reviews · 6 sources · effective n = 178 · updated 2d ago        │
│                                                                       │
│  Weighting:  [ Equal ]  [ By source ]  [ ✓ By credibility ]  ← FLAGSHIP│
├──────────────────────────────────────────────────────────────────────┤
│  ⚠ MOST DISAGREEMENT                                                 │
│  Gearbox & transmission        6.2  [5.4 ── 7.1]      divergence 0.61│
│  71% of the split is explained by transmission type.                 │
│  Automatic owners: 6.2   ·   Manual owners: 8.8      [ 34 reviews ▾ ]│
├──────────────────────────────────────────────────────────────────────┤
│  Ride & comfort                8.6  [8.2 ── 8.9]      divergence 0.12│
│  Service & after-sales         5.9  [5.1 ── 6.6]      divergence 0.44│
│  Real-world mileage           17.2 kmpl   ARAI claims 21.4  (−19.6%) │
├──────────────────────────────────────────────────────────────────────┤
│  EXPERT vs OWNER                                                      │
│  Media 8.9  ████████████████░░   Owners 7.4  █████████████░░░░░       │
│  Largest gap: service & after-sales (media 8.5, owners 5.9)          │
├──────────────────────────────────────────────────────────────────────┤
│  OFFICIAL RECORD                                                      │
│  Bharat NCAP 5★ adult / 4★ child  ·  1 recall (2024, fuel pump)      │
└──────────────────────────────────────────────────────────────────────┘
```

*Illustrative layout. Figures are placeholders. Topics are ordered by how much people disagree, not by score.*

**The flagship feature is the weighting switch.** Flip between equal weighting and credibility weighting and watch every score, interval and ranking move. That is the intellectual content of the project, made visible in thirty seconds.

## Status

| | |
|---|---|
| **Stage** | S1 Business Need submitted. Repository initialised, week 1 of 12. |
| **Live URL** | Not deployed yet |
| **Next milestone** | Schema, CI and deployment skeleton — see [roadmap](docs/roadmap.md) |

## Documentation

| Document | What it covers |
|---|---|
| [Business need](docs/business-need.md) | S1 submission: the problem, the market gap, the ask |
| [Full proposal](docs/proposal.md) | The complete concept note and software design specification |
| [Architecture](docs/architecture.md) | Tiers, pipeline stages, data flow, the traceability guarantee |
| [Data model](docs/data-model.md) | Canonical entities, the Evidence Unit abstraction, verdict tables |
| [Evaluation](docs/evaluation.md) | The held-out fusion experiment, calibration, the metrics dashboard |
| [Roadmap](docs/roadmap.md) | Twelve weeks, two hard checkpoints, the agreed cut list |
| [Glossary](docs/glossary.md) | Every term used in this repository, defined once |
| [Decision records](docs/adr/) | Why the architecture is the way it is |
| [Contributing](CONTRIBUTING.md) | Branching, commits, reviews, local setup |

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
