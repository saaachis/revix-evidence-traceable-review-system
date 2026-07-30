# Revix

### driven by reviews.

## An Evidence-Traceable Consumer Decision Support Platform for the Indian Automobile Market

**Concept Note and Software Design Specification**

*A cross-source review system for cars and two-wheelers, covering what owners, experts, forums and official records actually say.*

| | |
|---|---|
| **Programme** | M.Sc. Data Science, Nilkamal School of Mathematics, Applied Statistics and Analytics, SVKM NMIMS Mumbai |
| **Subject** | Modern Application Development |
| **Team** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |
| **Document status** | Version 2.1. Renamed from CarSense to Revix; scope extended to two-wheelers |
| **Date** | July 2026 |

> **In one line.** Revix collects everything that has been said about a car across owner reviews, expert reviews, forums, videos, community discussion and public regulatory data, weighs each piece of evidence by how much it can be trusted, and produces a verdict where every single claim traces back to the exact evidence that produced it.

---

## Table of Contents

1. [Project Introduction](#1-project-introduction)
2. [Motivation](#2-motivation)
3. [Problem Statement](#3-problem-statement)
4. [Vision](#4-vision)
5. [Objectives](#5-objectives)
6. [Why Automobiles, and Why India](#6-why-automobiles-and-why-india)
7. [Existing Solutions and Their Limitations](#7-existing-solutions-and-their-limitations)
8. [Proposed Solution](#8-proposed-solution)
9. [Complete System Architecture](#9-complete-system-architecture)
10. [Data Flow](#10-data-flow)
11. [Canonical Entity Model](#11-canonical-entity-model)
12. [Evidence Model](#12-evidence-model)
13. [Database Design Concepts](#13-database-design-concepts)
14. [Connector Architecture](#14-connector-architecture)
15. [Fusion Pipeline](#15-fusion-pipeline)
16. [Explainability and Traceability](#16-explainability-and-traceability)
17. [Machine Learning Pipeline](#17-machine-learning-pipeline)
18. [Evaluation Strategy](#18-evaluation-strategy)
19. [Admin and Operational Capabilities](#19-admin-and-operational-capabilities)
20. [User Experience and Application Features](#20-user-experience-and-application-features)
21. [User Journey and Demo Flow](#21-user-journey-and-demo-flow)
22. [Risks and Mitigation](#22-risks-and-mitigation)
23. [Technology Stack](#23-technology-stack)
24. [Development Roadmap](#24-development-roadmap)
25. [Scope Boundaries](#25-scope-boundaries)
26. [Future Enhancements](#26-future-enhancements)
27. [Final Expected Product](#27-final-expected-product)
- [Appendix A: What Changed From the Previous Proposal](#appendix-a-what-changed-from-the-previous-proposal)
- [Appendix B: Glossary](#appendix-b-glossary)

---

## 1. Project Introduction

Revix is a web application that answers a question every Indian car and two-wheeler buyer asks and that nothing currently answers well:

> **Across everything that has been said about this vehicle, what is actually true, how much of it can I trust, and where do people disagree?**

The application continuously collects evidence about Indian passenger cars and two-wheelers from owner reviews, expert reviews, enthusiast forums, video reviews, community discussion and public regulatory data. It resolves every piece of evidence to a single canonical vehicle variant, scores each piece for credibility, fuses it into an aspect-by-aspect verdict with an explicit confidence interval, and presents that verdict with every claim traceable back to the exact evidence that produced it.

Three properties distinguish Revix from a review summariser:

1. **The output is a structured verdict object, not generated text.** A language model renders the final prose, and the application works correctly with that model switched off entirely.
2. **Traceability is enforced by the database schema**, not requested from a prompt. Citations are rows in a join table produced by the fusion engine.
3. **The weighting strategy is a first-class, user-switchable configuration.** An evaluator can flip between equal weighting, source weighting and credibility weighting and watch the verdict change in real time.

This is an engineering project with substantial, well-integrated machine learning. It is not a research thesis and it does not claim a novel research contribution. It claims a well-built system that does something no existing product does.

---

## 2. Motivation

Buying a car or a two-wheeler in India is a high-stakes, low-frequency, high-anxiety decision. A typical buyer spends six to twelve weeks researching a purchase worth eight to thirty times their monthly income, and conducts that research by opening fifteen browser tabs.

The information exists. It is simply unusable in the form it exists in:

- **CarDekho, CarWale, BikeWale and ZigWheels** each host thousands of owner reviews, presented as a star average that hides everything interesting about the distribution.
- **Team-BHP** contains some of the most detailed long-term ownership writing anywhere in the world, buried inside three-hundred-page forum threads.
- **YouTube** reviewers produce forty-minute videos, mostly about cars they were lent for a weekend by the manufacturer.
- **Expert publications** review pre-production cars on closed roads and rarely revisit them at 40,000 km.
- **Public data** on crash safety, recalls, claimed fuel efficiency and resale value exists in official sources that no consumer product joins to the review corpus.

The result is systematic distortion in a predictable direction. Early reviews are more positive than late ones. Media reviews are more positive than owner reviews. Nobody surfaces the disagreement, because disagreement makes for a worse-looking product page.

**Revix treats that disagreement as the most valuable signal in the dataset.**

---

## 3. Problem Statement

Evidence about a vehicle is scattered across heterogeneous sources, described in incompatible vocabularies, keyed to inconsistent product identities, and of wildly varying trustworthiness. Consumers cannot aggregate it. Existing platforms aggregate only within their own walls. No system exposes how much of a conclusion rests on which evidence.

The engineering problem is therefore threefold:

1. **Identity.** Resolve heterogeneous listings and mentions to a single canonical vehicle variant.
2. **Structure.** Convert unstructured, multi-source, multi-quality evidence into a comparable structured form.
3. **Aggregation with accountability.** Combine that evidence in a way that is weighted, uncertain, explainable and fully traceable, then serve the result as a fast and reliable web application.

---

## 4. Vision

An application where a buyer types a vehicle name and, within one screen and under three hundred milliseconds, sees:

- what the car is genuinely good and bad at, aspect by aspect,
- how confident that judgement is, and why,
- exactly where opinion splits and what explains the split,
- how owner experience diverges from media coverage,
- what the objective public record says about safety, recalls and claimed efficiency,
- and, for every one of those statements, the specific reviews, posts and transcripts that produced it.

---

## 5. Objectives

### Primary objectives (must ship)

1. Build a canonical vehicle catalogue at **variant** granularity for the Indian market, with structured specifications.
2. Build a resilient, monitored, idempotent multi-source ingestion platform on a uniform **Evidence Unit** abstraction.
3. Resolve every ingested listing and mention to a canonical variant, and measure that resolution with precision and recall.
4. Extract aspect-level opinion from unstructured evidence and measure it against a hand-labelled gold set.
5. Score evidence credibility, combining a supervised spam classifier with behavioural and textual reliability features.
6. Fuse evidence into a versioned, configuration-keyed verdict with calibrated confidence intervals.
7. Guarantee claim-to-evidence traceability structurally, at the database layer.
8. Ship a polished, deployed, responsive web application with a flagship interactive fusion-strategy comparison.
9. Expose an internal evaluation dashboard with live metrics, refreshed by continuous integration.
10. Expose an operational admin dashboard for connector health and pipeline observability.

### Secondary objectives (only once every primary objective is green)

11. Verify factual claims made in reviews against the structured specification knowledge base.
12. Persona-based reweighting: best for city use, for highway use, for low running cost, for resale.
13. Image-based vehicle identification.

---

## 6. Why Automobiles, and Why India

### 6.1 Why automobiles rather than general ecommerce

| Factor | Impact on this project |
|---|---|
| **Bounded catalogue** | A few hundred variants covers most of the market. The entire corpus can be precomputed, which makes the application fast, cheap and reliable by design rather than by optimisation. |
| **Entity resolution is right-sized** | Model-level matching is nearly a primary key, but **variant-level** matching is genuinely hard and genuinely useful. `Creta SX (O) 1.5 diesel AT` versus `Creta 1.5 CRDi SX Optional Automatic` is a real problem with a real solution, solvable in a semester. |
| **Specifications are structured and authoritative** | This gives us a knowledge base, which gives us hard constraints for matching and ground truth for claim verification. Ecommerce has no equivalent. |
| **Evidence is unusually rich** | Owner reviews carry ownership duration and kilometres driven. That metadata enables aspect-conditional credibility, the most sophisticated idea in this design, and it is simply unavailable elsewhere. |
| **Objective public signals exist** | Crash ratings, recall notices, claimed efficiency and resale value provide external reference points for validating our aggregation. |
| **Low freshness pressure** | Model lineups change yearly, not hourly. A nightly refresh is architecturally correct rather than a compromise. |
| **Service and after-sales is a first-class aspect** | In India this frequently dominates ownership satisfaction and is invisible in any specification sheet or star rating. It is a large, under-served information gap. |

**The honest cost of this choice:** automobiles have fewer evidence units per item than ecommerce, so the catalogue must be seeded with popular models deliberately rather than sampled randomly. This is tracked as a risk in Section 22.

### 6.2 Why India specifically

Restricting to the Indian market makes the corpus internally consistent. The reviews, the specifications, the safety ratings, the recall notices, the fuel-efficiency claims and the resale data all describe the same vehicles, sold in the same market, to the same buyers. A US-anchored design using NHTSA data would have produced an objective signal that does not overlap with an Indian review corpus, which would have been a fatal inconsistency.

**Indian objective reference signals used:**

| Signal | Source | What it anchors |
|---|---|---|
| Crash safety star ratings | Bharat NCAP, Global NCAP `#SaferCarsForIndia` | The safety aspect |
| Recall notices | SIAM voluntary recall portal, MoRTH notices | The reliability aspect |
| Claimed fuel efficiency | ARAI figures published in specifications | Real-world mileage, and the claimed-versus-actual gap |
| Resale and depreciation | Public used-car listing datasets | The resale-value aspect |
| Registration and sales volume | Vahan dashboard, SIAM and FADA monthly reports | Market revealed preference, as a sanity check |

No single anchor is load-bearing. Agreement across several independent anchors is what makes the aggregation credible.

### 6.3 Why two-wheelers are included

Two-wheelers were out of scope in version 2.0 of this document and are in scope from version 2.1. The reasoning:

| Factor | Why it argues for inclusion |
|---|---|
| **Audience size** | Two-wheelers outsell passenger cars several times over in India. They are the larger half of the market and the worse served one. |
| **Zero architectural cost** | A motorcycle is a `vehicle_variant` row with a different specification profile. The Evidence Unit abstraction, entity resolution, credibility scoring and fusion engine are unchanged. |
| **The same sources** | BikeWale, ZigWheels, Team-BHP and xBhp, YouTube and the same regulatory portals already cover both. Most connectors gain a second seed list, not a rewrite. |
| **Matching is equally hard** | `Classic 350 Chrome` versus `Classic 350 (Chrome, dual-channel ABS)` is the same entity-resolution problem as the Creta example above. |
| **Better evidence density** | Popular two-wheelers carry very high owner-review volume relative to their price, which helps the thin-evidence risk in Section 22. |

**What actually changes.** Three things, all bounded:

1. **A `vehicle_class` discriminator** (`car` \| `two_wheeler`) on `vehicle_model`, and a class-specific subset of specification fields. Cars carry `boot_litres` and `seating_capacity`; two-wheelers carry `kerb_weight_kg`, `seat_height_mm` and `braking_type`.
2. **Two aspects are re-read per class.** *Interior space and comfort* becomes *ergonomics and pillion comfort* for two-wheelers; *build quality* absorbs *fit and finish*. The other seven aspects in Section 17 apply unchanged. The taxonomy stays at nine.
3. **Crash safety has no two-wheeler equivalent.** Bharat NCAP does not rate motorcycles. The safety aspect for two-wheelers is anchored on braking specification, ABS availability and recall incidence instead, and the interface must state that the NCAP anchor is absent rather than show an empty star rating.

**Scope discipline.** The catalogue budget of 120 to 150 variants is not increased. It is split, roughly 60% cars and 40% two-wheelers, weighted by evidence volume. Adding two-wheelers widens the audience without widening the workload.

---

## 7. Existing Solutions and Their Limitations

| System | Strength | Limitation |
|---|---|---|
| CarDekho, CarWale, BikeWale, ZigWheels user reviews | Volume of Indian owner opinion | Single platform, star average only, no credibility model, launch-window bias uncorrected |
| Team-BHP | Exceptional depth of long-term ownership reporting | Unstructured, unsearchable at scale, no aggregation, high expertise barrier |
| YouTube reviews | Detailed, visual, personality-driven | Systematically favourable, no aggregation, no accountability for claims |
| Expert publications | Professional testing methodology | Pre-production cars, short exposure, commercial relationships, narrow catalogue |
| Bharat NCAP and recall portals | Authoritative and objective | Narrow scope, not joined to consumer experience, poor discoverability |
| Generic LLM assistants | Broad reasoning | No explicit credibility model, no traceability to specific evidence, no confidence, unverifiable |
| Fakespot (shut down 2025), ReviewMeta (defunct) | Fake-review flagging | Single platform, no aspect analysis, no consensus, no longer available |
| **Revix** | Cross-source, credibility-weighted, divergence-aware, confidence-scored, structurally traceable verdicts | Harder to build; addressed by precomputation, a bounded catalogue and staged delivery |

The gap is specific and defensible: **every existing system either aggregates within one wall, or reasons without traceability, and none joins consumer evidence to the objective public record.**

---

## 8. Proposed Solution

Revix is a **precompute-and-serve** platform. All expensive work happens in scheduled batch pipelines. Every user-facing request is a read of precomputed rows.

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION     Next.js + TypeScript + Tailwind + shadcn/ui        │
│                   Verdict · Compare · Evidence · Method · Metrics    │
│                   · Admin                                             │
└─────────────────────────────▲────────────────────────────────────────┘
                              │  typed client generated from OpenAPI
┌─────────────────────────────┴────────────────────────────────────────┐
│  SERVING          FastAPI, read-only, contract-first                 │
│                   every endpoint is a single Postgres read           │
└─────────────────────────────▲────────────────────────────────────────┘
                              │
┌─────────────────────────────┴────────────────────────────────────────┐
│  STORAGE          PostgreSQL + pgvector (one database)               │
│                   schemas: raw · core · analysis · serving           │
└─────────────────────────────▲────────────────────────────────────────┘
                              │
┌─────────────────────────────┴────────────────────────────────────────┐
│  ENRICHMENT       Batch DAG: resolve → extract → score → verify      │
│                              → fuse → narrate                         │
└─────────────────────────────▲────────────────────────────────────────┘
                              │
┌─────────────────────────────┴────────────────────────────────────────┐
│  INGESTION        Connector registry, isolated and idempotent        │
│                   owner · expert · forum · video · social            │
│                   · regulatory · dataset                              │
└──────────────────────────────────────────────────────────────────────┘
```

**The single most important architectural decision is the strict separation of the write path from the read path.** No model runs during a user request. This one decision simultaneously solves latency, inference cost, rate limits, language-model availability, and, critically, live-demo reliability.

---

## 9. Complete System Architecture

### 9.1 Ingestion tier

Every source is implemented as a **connector** conforming to a single interface, registered in the database, and executed as an isolated orchestrated flow. A connector never fails the pipeline. It fails itself, marks its source stale, and reports to the health dashboard.

Cross-cutting behaviour is provided by the framework rather than reimplemented per connector: robots and terms checking, token-bucket rate limiting, exponential backoff, a circuit breaker, checkpointing for resumability, content hashing for deduplication, and telemetry written to `ingest_run`.

**Raw payloads are persisted immutably before parsing.** This makes the pipeline **replayable**: when a parser improves, evidence is re-derived without re-contacting the source. This is better engineering and it is also the respectful thing to do.

### 9.2 Enrichment tier

A deterministic, resumable, idempotent directed acyclic graph. Each stage writes its output and can be re-run independently.

```
resolve_entities    listings and mentions → canonical variant
        ↓
chunk_and_embed     evidence text → chunks → vectors (pgvector)
        ↓
extract_aspects     chunks → (aspect, polarity, span, confidence)
        ↓
score_credibility   spam probability × reliability features
                    → aspect-conditional weights
        ↓
verify_claims       extracted factual claims → compared against the
                    specification knowledge base
        ↓
analyse_divergence  aspect distributions → divergence index
                    + covariate attribution
        ↓
fuse                weighted aggregation per (variant, aspect,
                    fusion_config) → verdict + claims + evidence links
                    + confidence intervals
        ↓
narrate             constrained LLM rendering + deterministic
                    validation + template fallback
```

The `fuse` stage runs once **per fusion configuration**. Producing all strategies for every variant is a loop, not extra architecture, and it is what powers the flagship user interface feature.

### 9.3 Serving tier

FastAPI, contract-first. The OpenAPI schema is the source of truth, and the TypeScript client used by the frontend is generated from it, so the two cannot drift. All endpoints are read-only except admin mutations. Response-time target: p95 under 300 ms, achievable because responses are materialised rows.

### 9.4 Presentation tier

Next.js App Router with server components for the verdict page, so the highest-value page renders server-side with no client waterfall.

---

## 10. Data Flow

**Ingestion path** (scheduled: nightly for evidence, weekly for the catalogue):

```
seed catalogue → connector.discover → connector.fetch → persist raw payload
   → connector.parse → EvidenceUnitDraft → dedupe by content_hash
   → insert evidence_unit → mark ingest_run complete
```

**Enrichment path** (triggered on new evidence):

```
unresolved listings → entity resolution → variant_id assigned
new evidence units  → chunk → embed → aspect extraction
                    → credibility scoring
                    → claim extraction and verification
                    → divergence analysis
                    → fusion (× N configurations)
                    → verdict + verdict_aspect + verdict_claim
                      + verdict_claim_evidence
                    → narrative generation + validation
                    → refresh serving materialised views
```

**Read path** (user request):

```
GET /variants/{id}/verdict?fusion=credibility_weighted
   → single indexed read from serving.verdict_current
   → JSON response, no computation
```

---

## 11. Canonical Entity Model

The `vehicle_variant` is the centre of the system. Everything resolves to it, every verdict is keyed by it, and its specifications provide both hard matching constraints and claim-verification ground truth.

```sql
manufacturer(id, name, slug, country)

vehicle_model(
    id, manufacturer_id, name, slug,
    body_style,            -- hatchback | sedan | SUV | MUV | ...
    segment,               -- micro | compact | midsize | premium | luxury
    launch_year, discontinued_year
)

vehicle_variant(                       -- THE canonical entity
    id, model_id,
    variant_name,                      -- "SX (O) Knight"
    trim_code,                         -- normalised: "sx-o-knight"
    fuel_type,                         -- petrol | diesel | cng | hybrid | electric
    transmission,                      -- mt | at | amt | cvt | dct | ivt
    drivetrain,
    engine_cc, engine_power_bhp, engine_torque_nm,
    arai_mileage_kmpl,
    length_mm, width_mm, height_mm, wheelbase_mm,
    ground_clearance_mm, boot_litres, fuel_tank_litres,
    seating_capacity,
    ex_showroom_price_min, ex_showroom_price_max, price_band,
    launch_date, production_status,
    spec_completeness,                 -- 0..1, how much of the sheet we hold
    spec_source_refs jsonb             -- provenance for every spec field
)

variant_feature(variant_id, feature_key, feature_value, is_standard)

source_listing(                        -- what each source calls this variant
    id, source_id, external_id, url,
    raw_title, raw_specs jsonb,
    variant_id,                        -- null until resolved
    match_method,                      -- exact | spec_constraint | embedding
                                       -- | verifier | manual
    match_confidence, resolved_at
)
```

### Entity resolution design

This is a **hybrid rule-and-model system**, and it is stronger than a pure embedding approach because automobile specifications behave as hard constraints:

1. **Blocking** on manufacturer plus model plus year window.
2. **Hard constraints.** Fuel type, transmission family and engine displacement must agree. A petrol listing is never a diesel variant, regardless of what the embeddings say. This eliminates the majority of candidate pairs deterministically and is why automobile entity resolution can reach very high precision.
3. **Normalised trim matching** with a synonym dictionary (`SX(O)` = `SX Optional` = `SX Opt`) and trigram similarity.
4. **Embedding similarity** on the residual, using a multilingual sentence encoder over the concatenated title and specification string.
5. **Cross-encoder verification** on the remaining ambiguous pairs.
6. **Manual adjudication queue** in the admin dashboard for anything below the confidence floor. Human-in-the-loop is a designed feature, not an admission of failure, and it demonstrates well.

Measured against a hand-labelled gold set of roughly 400 pairs, reporting precision, recall, F1 and the residual unresolved-listing rate.

---

## 12. Evidence Model

Every source, regardless of shape, becomes one abstraction. This decision is made on day one and it constrains everything after it, which is exactly why it is the highest-leverage decision in the project.

```sql
evidence_source(                       -- connector registry
    id, source_key, display_name,
    kind,                              -- owner_review | expert_review | forum
                                       -- | video | social | regulatory
                                       -- | news | dataset
    base_url, robots_policy, rate_limit_rpm,
    default_source_prior,              -- used by the source-weighted strategy
    is_enabled, notes
)

evidence_unit(                         -- THE unified abstraction
    id, source_id,
    variant_id,                        -- resolved target, nullable
    model_id,                          -- fallback granularity when unknown
    external_id, url, author_ref,      -- pseudonymous author key, never PII
    text, lang, modality,              -- text | transcript | structured
    published_at, collected_at,
    rating_raw, rating_normalized,     -- mapped to 0..1 across differing scales
    is_verified_owner,
    helpful_votes, total_votes,
    ownership_duration_months,         -- automobile-specific, high value
    km_driven,                         -- automobile-specific, high value
    raw_ref, ingest_run_id, content_hash,
    spam_probability, credibility_json -- filled by enrichment
)

evidence_chunk(
    id, evidence_unit_id, chunk_index, text, embedding vector(384)
)

aspect_opinion(
    id, evidence_unit_id, chunk_id, aspect_id,
    polarity,                          -- -1..+1
    confidence, extracted_span
)

factual_claim(
    id, evidence_unit_id, claim_type,  -- mileage | dimension | feature
                                       -- | price | spec
    claimed_value, claimed_unit, normalized_value,
    variant_id, spec_field, spec_value,
    verdict,                           -- supported | contradicted | unverifiable
    delta
)
```

### Why `ownership_duration_months` and `km_driven` matter more than they look

They enable **aspect-conditional credibility**. An owner at 500 km is a credible witness to delivery experience and showroom behaviour, and a poor witness to long-term reliability. An owner at 60,000 km is the reverse.

Credibility is therefore not a scalar. It is a short vector over aspect groups:

```json
{
  "base": 0.71,
  "by_aspect_group": {
    "durability": 0.88,
    "immediate":  0.42,
    "service":    0.83,
    "efficiency": 0.79
  }
}
```

This is cheap to compute, explainable to a non-technical audience in one sentence, and a genuinely better model of the world than a single trust score. It is available only because the domain is automobiles.

---

## 13. Database Design Concepts

**One database.** PostgreSQL with the `pgvector` extension, hosted on a free tier (Supabase or Neon). Records and vectors stay transactionally consistent, there is one connection string, one migration path and one backup story.

**Four schemas, by lifecycle:**

| Schema | Contents | Mutability |
|---|---|---|
| `raw` | Immutable fetched payloads and references | Append-only |
| `core` | Canonical entities, evidence units, sources | Slowly changing |
| `analysis` | Aspect opinions, credibility, claims, divergence | Recomputable |
| `serving` | Materialised verdicts and views for the API | Fully derived |

**Design rules:**

- Every derived table is **recomputable from `raw` and `core`**. Nothing important lives only in a derived table.
- `(source_id, external_id)` is unique, and `content_hash` deduplicates. Re-running any connector is therefore safe and idempotent.
- Migrations are versioned with Alembic and run in continuous integration before deployment.
- Indexes: trigram GIN on normalised trim strings for entity resolution, an approximate-nearest-neighbour index on embeddings, and B-tree indexes on `(variant_id, aspect_id)` and `(verdict_id)`.
- The API reads from materialised views in `serving`, refreshed at the end of each enrichment run.

---

## 14. Connector Architecture

Every source implements one interface:

```python
class Connector(Protocol):
    source_key: str

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]: ...
    def fetch(self, ref: ExternalRef) -> RawPayload: ...
    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]: ...
```

**Planned connectors:**

| Connector | Kind | Priority |
|---|---|---|
| `dataset_seed` | dataset | Week 1, bootstraps the catalogue and specifications |
| `owner_reviews_a` | owner_review | Week 2 |
| `owner_reviews_b` | owner_review | Week 2 |
| `regulatory` | regulatory | Week 3, recalls and crash ratings |
| `expert_reviews` | expert_review | Week 4 |
| `forum` | forum | Week 4 |
| `reddit` | social | Week 6, via the official API |
| `youtube` | video | Week 6, Data API plus transcripts |

**Resilience contract.** Every connector is isolated, rate limited, resumable from a checkpoint, and wrapped in a circuit breaker. A failure marks the source stale and reports to the admin dashboard. **The product must remain complete and demonstrable with only three of eight connectors alive.** That is a design requirement, not an aspiration.

---

## 15. Fusion Pipeline

### 15.1 Configurations

```sql
fusion_config(id, name, config_hash, params jsonb, is_default, created_at)
```

| Strategy | Description |
|---|---|
| `S0 equal` | Every evidence unit counts once. The baseline. |
| `S1 source_weighted` | Fixed per-source priors. Expert review, owner review and social carry different weights. |
| `S2 credibility_weighted` | Per-unit, aspect-conditional credibility weights. |
| `S3 credibility_recency` | S2 plus recency decay and launch-window correction. |
| `S4 stratified` | S3 plus covariate stratification, reported per fuel type, transmission and model year. |

### 15.2 The aggregation

For aspect `a` of variant `v`:

```
weight(e, a) = source_prior(e)
             × (1 − spam_probability(e))
             × reliability(e)
             × aspect_fit(e, a)             # the aspect-conditional term
             × recency_decay(e)
             × launch_window_correction(e)

score(v, a)  = Σ weight(e,a) · polarity(e,a)  /  Σ weight(e,a)
```

**Confidence intervals** are produced by weighted bootstrap over the contributing evidence units. Interval width is driven by the **Kish effective sample size**:

```
n_eff = (Σ w)² / Σ w²
```

This is a standard quantity from survey sampling and it captures something genuinely useful: two hundred low-credibility reviews can yield a *smaller* effective sample than thirty high-credibility ones, so the interval correctly stays wide. It is one line of code and it makes the confidence meter defensible rather than decorative.

**Divergence index** is the weighted fraction of evidence disagreeing with the majority polarity sign.

**Covariate attribution** then explains the split. For each covariate (fuel type, transmission, model year, ownership bucket, source kind, verified status), compute between-group variance in polarity and report the covariate explaining the most. This produces statements of real value:

> *Opinion on the gearbox is split. 71% of the disagreement is explained by transmission: DCT owners rate it 0.62, manual owners 0.88.*

That is statistics, not natural language inference. It is cheaper, more reliable, more honest and far more useful than a contradiction badge.

### 15.3 Why natural language inference was removed

An earlier version of this proposal used off-the-shelf NLI for contradiction detection. It is deliberately absent here.

NLI models are trained on clean, purpose-built sentence pairs. Owner-review text in India is noisy, code-mixed, and full of *legitimate* disagreement arising from different variants, cities, service centres and model years. NLI would have flagged that as contradiction, which is wrong, and it would have added the heaviest inference cost in the pipeline for the least reliable output.

The replacement, distributional divergence with covariate attribution, is superior on every axis: cost, reliability, explainability and usefulness. **Removing NLI is a design decision and should be presented as one.**

---

## 16. Explainability and Traceability

### 16.1 The architectural guarantee

Traceability is not requested from the language model. It is produced by the fusion engine and stored.

```sql
verdict(
    id, variant_id, fusion_config_id, computed_at,
    overall_score, confidence_low, confidence_high,
    evidence_count, effective_sample_size, sources_used jsonb,
    payload jsonb, narrative_id
)

verdict_aspect(
    id, verdict_id, aspect_id,
    score, ci_low, ci_high, support_count,
    divergence_index, top_covariate, covariate_explanation jsonb
)

verdict_claim(                          -- every assertable statement
    id, verdict_id, claim_type,
    claim_template, computed_values jsonb
)

verdict_claim_evidence(                 -- THE traceability table
    verdict_claim_id, evidence_unit_id,
    contribution_weight, rank
)
```

### 16.2 The generation contract

The language model receives **only** the structured verdict and a list of claims with opaque identifiers. It never sees raw review text and never emits an evidence identifier.

```
INPUT to the model:
  claims: [
    {id: "C1", template: "overall_positive",
     values: {score: 0.78, ci: [0.71, 0.84], n: 412}},
    {id: "C2", template: "aspect_strength",
     values: {aspect: "ride_quality", score: 0.86}},
    {id: "C3", template: "aspect_divergence",
     values: {aspect: "gearbox", covariate: "transmission"}}
  ]

INSTRUCTION: write four sentences of plain prose, marking each with its claim id.

OUTPUT: "... rides well [C2] ... opinion splits on the gearbox [C3] ..."
```

### 16.3 The deterministic guard

Post-generation validation, in code, not by another model:

1. Every `[Cn]` marker resolves to a real `verdict_claim`.
2. Every number appearing in the prose appears in the corresponding `computed_values`.
3. Every named entity appearing in the prose appears in the verdict payload.

Failure regenerates once, then falls back to a **template-rendered verdict**. The application therefore has a guaranteed property that very few student projects can state:

> **Revix cannot assert a number it did not compute, and it renders a complete verdict with the language model switched off entirely.**

The `[Cn]` markers are resolved client-side into citation chips. Clicking one opens the evidence drawer populated from `verdict_claim_evidence`, ordered by contribution weight. Traceability is a database join, made visible in the interface.

---

## 17. Machine Learning Pipeline

| # | Component | Approach | Effort | Measured by |
|---|---|---|---|---|
| 1 | **Entity resolution** | Blocking → hard spec constraints → trigram trim match → embeddings → cross-encoder verifier → manual queue | High | Precision, recall, F1 on 400 gold pairs |
| 2 | **Aspect extraction** | Fixed taxonomy; LLM-assisted bootstrap labelling; distilled multilingual classifier for batch inference | High | Macro-F1 on 500 gold sentences, reported per language |
| 3 | **Spam detection** | Supervised classifier trained on public labelled deceptive-review corpora | Medium | Precision, recall, F1, AUC on held-out data |
| 4 | **Reliability weighting** | Behavioural and textual features, weights learned against the fusion objective in Section 18 | Medium | Improvement in fusion RMSE over equal weighting |
| 5 | **Divergence analysis** | Weighted distributional statistics plus covariate variance attribution | Low | Stability across resamples, qualitative review |
| 6 | **Claim verification** | Rule-based and LLM-assisted claim extraction, unit normalisation, comparison to the specification KB | Medium | Precision on a hand-checked sample of 200 claims |
| 7 | **Grounded narration** | Constrained generation over structured claims with a deterministic validator | Low | Faithfulness score, guard pass rate, citation coverage |

### The aspect taxonomy

Nine aspects, fixed, India-specific:

1. Engine and performance
2. Ride quality, handling and NVH
3. Real-world mileage and running cost
4. Interior space and comfort
5. Features and infotainment
6. Build quality
7. Safety
8. **Service, after-sales and spare-part cost**
9. **Long-term reliability**

Aspects 8 and 9 dominate Indian ownership satisfaction and are captured by no specification sheet or star rating. They are the product's reason to exist.

### Handling code-mixed text

Indian owner reviews are heavily Hinglish and often transliterated. Mitigations: a multilingual sentence encoder rather than an English-only model; transliteration-tolerant preprocessing; and language detection stored on every evidence unit so that **per-language F1 is reported separately** on the metrics page. Being transparent about degraded Hinglish performance is more credible than concealing it, and multilingual handling is a genuine team strength worth advertising.

---

## 18. Evaluation Strategy

This section separates a good application from an impressive one, and it requires no manual labelling beyond two small gold sets.

### 18.1 The central fusion experiment

The naive question, "is our consensus correct?", has no ground truth and must not be asked. Instead:

> **Gold consensus (held out).** For each variant, compute the aspect score over evidence units that are verified owners with at least twelve months of ownership and at least 10,000 km, using equal weights within that subset. **These units are then removed from the estimation pool.**
>
> **Task.** From the remaining mixed-quality pool, draw `k` units and estimate the gold consensus.
>
> **Compare.** `S0 equal` versus `S1 source_weighted` versus `S2 credibility_weighted`, at `k ∈ {10, 20, 30, 50}`, over many random subsamples and all eligible variants.
>
> **Report.** RMSE, Spearman rank correlation across variants, and interval coverage.

This is non-circular, because the target is defined by metadata entirely excluded from the estimation pool. It tests exactly the hypothesis the project rests on: *do credibility signals identify which of the ordinary, unverified, mixed-quality evidence actually carries signal?*

It also supplies the **training objective for the reliability weights** in component 4, which is what makes "learned credibility" an honest phrase rather than a hand-wave.

**Required ablation for honesty.** Report results both with and without the metadata features (`is_verified_owner`, ownership duration), to demonstrate that the textual and behavioural features carry weight on their own. State this caveat explicitly. A reviewer who finds it before you do costs you more than the caveat itself.

### 18.2 External validity checks

| Check | Expectation |
|---|---|
| Fused safety sentiment vs Bharat and Global NCAP stars | Positive rank correlation |
| Fused reliability sentiment vs recall incidence | Negative rank correlation |
| Fused mileage estimate vs ARAI claimed figure | A consistent, quantifiable optimism gap |
| Fused value sentiment vs three-year resale retention | Positive rank correlation |

None is load-bearing alone. Agreement across four independent anchors is persuasive.

### 18.3 Calibration

Across all subsample runs, measure whether the 80% predicted interval contains the gold consensus 80% of the time. Produce a reliability diagram and expected calibration error. **This makes the confidence meter an evidenced claim rather than a decoration**, and it is the most sophisticated single element of the project.

### 18.4 The live metrics dashboard

Every metric above runs in **continuous integration on every push** against frozen test sets, writes to an `eval_run` table, and is rendered at a public `/metrics` route inside the application, including trend over time.

| Group | Metrics |
|---|---|
| Entity resolution | Precision, recall, F1, unresolved rate |
| Aspect extraction | Macro-F1, per-aspect F1, per-language F1 |
| Spam detection | Precision, recall, F1, AUC |
| Fusion | RMSE and Spearman by strategy and by `k` |
| Confidence | Coverage at 80%, expected calibration error, reliability diagram |
| Grounding | Faithfulness, numeric-guard pass rate, citation coverage |
| Pipeline | Freshness by source, catalogue coverage, p50 and p95 latency |

Showing a metric **trending over twelve weeks** is what makes this read as real engineering practice rather than a one-off report.

---

## 19. Admin and Operational Capabilities

Authentication-gated, and treated as a genuine product surface rather than a debug page.

- **Connector health.** One card per source: status, last successful run, duration, units ingested, error rate, staleness against its service-level target, last error sample, and a manual re-run button that enqueues a flow.
- **Ingestion run log.** Every `ingest_run` with counts, timings, error samples, and a link to the raw payloads it produced.
- **Freshness heatmap.** Source by variant, coloured by last-collected age. Coverage holes become visible instantly.
- **Catalogue coverage.** Variants below the minimum evidence threshold, so seeding effort is directed rather than guessed.
- **Entity-resolution adjudication queue.** Low-confidence candidates presented side by side for a one-click human decision, feeding back into the gold set.
- **Fusion configuration manager.** Create or clone a configuration, adjust parameters, trigger recomputation, and compare the result against the current default. This is the operator-side counterpart of the user-facing toggle.

---

## 20. User Experience and Application Features

### 20.1 Pages

| Page | Purpose |
|---|---|
| **Landing** | One search box over make, model and variant. Featured verdicts. Nothing else. |
| **Verdict** | The product. Detailed below. |
| **Compare** | Two or three variants side by side, aspect by aspect, with confidence intervals drawn. |
| **Evidence explorer** | Filterable corpus view: source, date, verified status, ownership duration, aspect, polarity. Every unit links to its origin. |
| **Method** | Plain-language explanation of how scores, weights and confidence are computed. |
| **Metrics** | The public evaluation dashboard. |
| **Admin** | Operations, authentication-gated. |

### 20.2 The verdict page

```
┌──────────────────────────────────────────────────────────────────────┐
│  Hyundai Creta SX (O) 1.5 Diesel AT              ₹19.2L - ₹20.4L     │
│                                                                       │
│  ████████████░░░░  7.8 / 10        [ 7.1 ─────── 8.4 ]               │
│  412 evidence units · 6 sources · effective n = 178 · updated 2d ago │
│                                                                       │
│  Weighting:  [ Equal ]  [ Source ]  [ ✓ Credibility ]   ← FLAGSHIP   │
├──────────────────────────────────────────────────────────────────────┤
│  ⚠ MOST DISAGREEMENT                                                 │
│  Gearbox & transmission        6.2  [5.4 ── 7.1]      divergence 0.61│
│  71% of the split is explained by transmission type.                 │
│  DCT owners: 6.2   ·   Manual owners: 8.8            [ 34 sources ▾ ]│
├──────────────────────────────────────────────────────────────────────┤
│  Ride & comfort                8.6  [8.2 ── 8.9]      divergence 0.12│
│  Service & after-sales         5.9  [5.1 ── 6.6]      divergence 0.44│
│  Real-world mileage           17.2 kmpl   ARAI claims 21.4  (−19.6%) │
├──────────────────────────────────────────────────────────────────────┤
│  EXPERT vs OWNER                                                      │
│  Media 8.9  ████████████████░░   Owners 7.4  █████████████░░░░░       │
│  Largest gap: service & after-sales (media 8.5, owners 5.9)          │
├──────────────────────────────────────────────────────────────────────┤
│  OBJECTIVE RECORD                                                     │
│  Bharat NCAP 5★ adult / 4★ child  ·  1 recall (2024, fuel pump)      │
└──────────────────────────────────────────────────────────────────────┘
```

*Illustrative layout. Figures shown are placeholders.*

### 20.3 The design decisions that matter

**Aspect cards are sorted by divergence, not by score.** Conflict first. This is the product's identity and the opposite of what every competitor does.

**Every number is clickable.** Clicking opens the evidence drawer with the exact contributing units, their weights, and outbound links. Traceability a user can touch.

**Confidence is an interval bar, never a percentage.** In the Compare view, overlapping intervals honestly communicate "these two cars are not distinguishable on this aspect", which is genuinely useful and something no comparison site will ever say.

**The claimed-versus-actual mileage gap is a headline number.** Instantly legible, immediately useful, and surfaced by no consumer product today.

### 20.4 The flagship: the fusion strategy toggle

Switching between Equal, Source and Credibility weighting re-renders the overall score, every aspect score, every confidence interval and the comparison ranking, with an animated transition and a "what changed" delta chip.

This is the highest-value feature in the application, for three reasons:

1. It converts an appendix table into a thirty-second interactive demonstration.
2. It makes the intellectual content of the project *visible* rather than described.
3. It costs almost nothing, because all strategies are computed anyway for the evaluation.

It belongs on the first slide, in the demo script, and at the top of the repository README.

---

## 21. User Journey and Demo Flow

### 21.1 User journey

```
Search "Creta"  →  variant picker  →  verdict page
      ↓                                    ↓
compare with a rival          click any number → evidence drawer → source
```

Three clicks to the verdict, one more to the underlying evidence.

### 21.2 Demo script, six minutes, rehearsed

| # | Action | The point being made |
|---|---|---|
| 1 | Search a popular SUV; the verdict renders instantly | Precomputed, fast, real data |
| 2 | Read the header: score, interval, evidence count, effective n, freshness | Honest quantification |
| 3 | The top aspect card is the *most disagreed-upon* one; read the covariate explanation | Divergence, not averaging |
| 4 | Click a score; the evidence drawer opens with real reviews and their weights | Structural traceability |
| 5 | **Flip the fusion toggle.** The score moves, two cars swap rank, the interval narrows | The core idea, made visible |
| 6 | Show the ARAI-versus-real-world gap and a verified claim from a video transcript | Claim verification against a real knowledge base |
| 7 | Compare view: two rivals with overlapping intervals on one aspect | "Too close to call" is an honest answer |
| 8 | **Disable the language-model key and reload.** The full verdict still renders | *The intelligence is in the pipeline, not the model* |
| 9 | Admin: one connector deliberately failing, the system degraded and still serving | Real operational engineering |
| 10 | Metrics page with twelve weeks of trend data | Continuous evaluation |

Step 8 is the moment that separates this from every other project in the room. Rehearse it.

---

## 22. Risks and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| A source blocks collection | High | Connector isolation, aggressive caching, an immutable raw store enabling replay, a documented fallback dataset for every connector, and a system that stays complete with three of eight connectors alive |
| Terms-of-service and legal exposure | High | Read robots and terms before writing each connector and record the findings in the report; rate-limit and cache; store references rather than mirroring full text; attribute and link back; present evidence with sources and confidence and avoid absolute claims about any manufacturer |
| Thin evidence for less popular variants | High | Seed the catalogue with the 120 to 150 highest-volume Indian variants deliberately; show coverage honestly in the interface; suppress verdicts below an evidence floor rather than publishing a bad one |
| Entity resolution errors | Medium | Hard specification constraints eliminate most false positives; a confidence floor routes ambiguity to the manual adjudication queue rather than guessing |
| Aspect classifier underperforms on Hinglish | Medium | Multilingual encoder, transliteration-tolerant preprocessing, per-language F1 reported openly |
| Language-model downtime, rate limits or hallucination | Medium | Batch-only generation cached by content hash, a deterministic validator, and a template fallback that renders a complete verdict with no model at all |
| **Free-tier cold start during the presentation** | **High** | Warm-up cron, pre-warm immediately before presenting, a fully seeded database, verified "golden" demo variants, and a recorded backup video. *This is the most likely cause of a bad demo and it is entirely preventable.* |
| Scope creep | High | Hard checkpoints at week 4 and week 8 with a pre-agreed cut list; secondary objectives may not start until all primary objectives are green |
| Team bandwidth across three people | Medium | The schema is owned jointly in week 1, then clean interface boundaries; a working deployed application every Friday |
| Data staleness | Low | Nightly refresh, `last_updated` shown on every surface, a freshness heatmap in admin, and a domain where lineups change yearly |

---

## 23. Technology Stack

Deliberately short. Every item earns its place.

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, Recharts | Industry standard; server components make the verdict page fast |
| Frontend hosting | Vercel | Free, fast, zero configuration |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Alembic | Contract-first API with a generated TypeScript client |
| Backend hosting | Render or Fly.io | Free tier adequate for a read-only serving layer |
| Database | **PostgreSQL + pgvector** (Supabase or Neon) | **One database.** Records and vectors stay transactionally consistent |
| Orchestration | Prefect | Ingestion and enrichment flows with retries and observability |
| Collection | httpx, Scrapy or Playwright where required, trafilatura, extruct, official platform APIs | Standard, respectful, rate-limited |
| Embeddings | sentence-transformers, multilingual model | Handles code-mixed Indian text |
| Verification | Cross-encoder, entity resolution only | High-precision pair adjudication |
| Classical ML | scikit-learn, imbalanced-learn | Spam classifier, aspect classifier, reliability weights |
| Language model | A single free-tier provider behind a thin interface | Batch narration only, swappable, never required |
| Evaluation | RAGAS plus scikit-learn metrics, run in CI | Faithfulness and component metrics |
| Observability | Langfuse | Real traces available during the viva |
| CI/CD | GitHub Actions | Tests, evaluation harness, migrations, deploys |
| Testing | pytest, Vitest, Playwright smoke tests | Real testing discipline |

### Deliberately excluded, and why

Stating what was rejected is a stronger signal than listing what was adopted.

| Excluded | Reason |
|---|---|
| **Qdrant** | pgvector is sufficient at this corpus size and removes an entire class of Postgres-to-vector-store synchronisation bugs. Justified by measured recall@k and latency. |
| **Redis** | Verdicts are precomputed. There is nothing to cache. |
| **Neo4j** | A reviewer graph adds a fourth datastore for no payoff at this scale. Graph features are computed in-process and stored as scalars. |
| **LangChain, LlamaIndex, Haystack** | The generation step is a structured payload and a template. Frameworks would hide the engineering rather than showcase it. |
| **NLI contradiction detection** | Unreliable on noisy code-mixed review text and the heaviest inference cost in the pipeline. Replaced by divergence statistics with covariate attribution. |
| **Finance and healthcare verticals** | Removed from the original multi-market concept. One domain, done deeply. |
| **A second evaluation framework** | Two evaluation frameworks is inventory, not rigour. |

---

## 24. Development Roadmap

Three people, twelve weeks. Roles are ownership areas, not silos. The schema in week 1 is owned by all three.

| Role | Ownership |
|---|---|
| **Platform and Ingestion** | Connector framework, all connectors, orchestration, raw store, freshness, admin backend |
| **Intelligence** | Entity resolution, aspect extraction, credibility, fusion, claim verification, evaluation harness |
| **Application and Experience** | API contract, frontend, verdict and compare pages, evidence explorer, metrics and admin interfaces, deployment |

| Week | Milestone | Exit criterion |
|---|---|---|
| **1** | Schema, repository, CI, deployment skeleton, API contract | Migrations run; empty application deployed; CI green |
| **2** | Connectors 1 and 2; catalogue seeded from a public dataset; first evidence units stored | **A live URL showing real evidence by day 10** |
| **3-4** | Variant-level entity resolution with gold set and metrics; connectors 3 and 4; admin health page v1 | **Checkpoint A:** ER precision and recall reported; four sources flowing |
| **5-6** | Aspect taxonomy, gold set and classifier; spam classifier; equal-weight verdict end to end; verdict page v1 | A real verdict renders in the browser |
| **7-8** | Credibility model; fusion engine; versioned configurations; subsample evaluation harness; ablations; **fusion toggle in the interface** | **Checkpoint B:** all strategies live and switchable |
| **9-10** | Confidence intervals and calibration study; divergence and covariate attribution; claim verification; grounded narration with guard and fallback | Calibration curve produced; guard passing |
| **11** | Compare view, evidence explorer, method page, public metrics page, performance, accessibility, seeded demo catalogue | p95 under 300 ms; demo rehearsed once |
| **12** | Report, video, final rehearsal, buffer | Everything frozen 48 hours before submission |

**Two disciplines that matter more than the schedule:**

1. **The deployed application must work every Friday.** A project that is live in week 2 and improves weekly beats one that integrates in week 11, every time.
2. **If Checkpoint B slips, cut in this order:** claim verification, then persona ranking, then image identification. Never cut the fusion toggle, the metrics page or the admin dashboard.

---

## 25. Scope Boundaries

**In scope.** Indian passenger cars and two-wheelers; a curated catalogue of roughly 120 to 150 high-evidence variants; six to eight connectors; the seven machine-learning components in Section 17; a precomputed, nightly-refreshed corpus; the seven application surfaces in Section 20.

**Explicitly out of scope.** Commercial vehicles; used-vehicle listings and pricing; live per-request scraping; arbitrary vehicles outside the seeded catalogue; purchase, booking or dealer integration; user accounts beyond what admin access requires; mobile applications; browser extensions.

**Deferred.** Price and deal tracking, watchlists and alerts, personalised trust preferences, additional Indian languages beyond Hinglish handling, a public API.

**Deliberately not attempted.** Any claim of research novelty; statistical calibration beyond what the held-out experiment supports; or absolute assertions about vehicle quality that are not traceable to cited evidence.

---

## 26. Future Enhancements

- **Commercial-vehicle expansion**, reusing the entire engine with a new catalogue and connector set.
- **Price and value tracking** over time, with a deal-or-overpriced verdict from historical snapshots.
- **Watchlists and alerts** on new evidence, new recalls or price movement.
- **Personalised trust preferences**, letting a user say which sources they trust and re-fusing accordingly. The fusion configuration system already supports this.
- **Additional Indian languages** for both input and output.
- **A public read-only API**, since the serving layer is already contract-first.
- **A dealer and manufacturer view**, showing how a model's owner sentiment compares with its segment.
- **Image-based identification**, letting a user photograph a car and reach its verdict.

---

## 27. Final Expected Product

1. A **deployed, publicly reachable web application** with verdict, compare, evidence explorer, method, metrics and admin surfaces.
2. A **canonical catalogue** of Indian vehicle variants with structured specifications and measured entity resolution.
3. A **monitored, resilient ingestion platform** spanning six to eight heterogeneous sources with a live health dashboard.
4. A **versioned fusion engine** with switchable strategies and an interactive comparison in the interface.
5. **Structural claim-to-evidence traceability**, demonstrable by clicking any number in the interface.
6. **Calibrated confidence intervals** with a reliability diagram as evidence.
7. A **live evaluation dashboard**, refreshed by CI, with trend history.
8. A **public repository** with migrations, tests, CI, architecture decision records, and a README leading with the ablation table.
9. A **written report** and a **six-minute rehearsed demonstration** with a recorded backup.

---

## Appendix A: What Changed From the Previous Proposal

Worth having ready for the viva, because faculty will ask why the concept moved.

### Version 2.1 (current)

| Change | Reason |
|---|---|
| **Renamed CarSense to Revix**, tagline *driven by reviews* | The product is a review system across cars *and* two-wheelers. A name containing "car" would have been wrong within a week, and "Revix" is short, unclaimed and pronounceable |
| **Two-wheelers moved from out-of-scope to in-scope** | The larger and worse-served half of the Indian market, at effectively zero architectural cost. Reasoned in full in Section 6.3 |
| **Catalogue budget split rather than expanded** | 120 to 150 variants total, roughly 60% cars and 40% two-wheelers. Scope discipline is preserved |

### Version 2.0: Removed

| Removed | Reason |
|---|---|
| Finance and healthcare verticals | One domain deeply beats three shallowly |
| NLI contradiction detection | Unreliable on noisy code-mixed reviews; replaced with divergence statistics plus covariate attribution |
| Qdrant, Redis, Neo4j, the LangChain family | Four services replaced by one Postgres with pgvector |
| Research framing and unprovable novelty claims | The subject is Application Development; the claim is now a well-engineered system, not a contribution |
| A question-answering chatbot as a headline feature | It is what makes a project look like a wrapper; demoted or dropped |

### Version 2.0: Added

| Added | Reason |
|---|---|
| Canonical variant model with a specification knowledge base | Central entity, hard matching constraints, and claim-verification ground truth |
| The Evidence Unit abstraction | One schema for every source; the highest-leverage day-one decision |
| Structural provenance via `verdict_claim_evidence` | Traceability becomes a guarantee rather than a prompt instruction |
| Versioned verdicts plus the fusion toggle | Turns the evaluation into the flagship feature |
| Aspect-conditional credibility | Uses ownership duration and kilometres driven, which only automobiles provide |
| The held-out gold-consensus experiment | Makes credibility weighting measurable and calibration real |
| Connector health and live metrics dashboards | Directly targets an Application Development rubric |
| The deterministic hallucination guard and language-model-off fallback | Proves the intelligence lives in the pipeline |

### Effort allocation

Roughly **60% application and data engineering, 40% machine learning**. If week 7 arrives with a beautiful credibility model and no deployed verdict page, the project is losing.

### The one thing to protect above all else

The fusion toggle and the language-model-off fallback, demonstrated together. Those two moments take about ninety seconds and communicate more about the quality of this project than the entire written report.

---

## Appendix B: Glossary

- **Evidence unit.** One piece of evidence from one source about one vehicle: an owner review, an expert review, a forum post, a video transcript segment, a recall notice or a news item. The universal abstraction the whole pipeline operates on.
- **Canonical variant.** The single true vehicle configuration that many differently worded listings across many sources all refer to.
- **Entity resolution.** Deciding that two differently worded listings describe the same real vehicle variant.
- **Aspect.** A specific dimension of the ownership experience, such as ride quality or after-sales service, as opposed to a single overall rating.
- **Polarity.** How positive or negative a piece of evidence is about one aspect, on a scale from −1 to +1.
- **Credibility.** How much weight a piece of evidence should carry, combining spam likelihood, author behaviour, textual specificity and corroboration. In Revix it is conditional on the aspect being judged.
- **Fusion.** Combining many weighted pieces of evidence into one score per aspect per variant.
- **Fusion configuration.** A named, versioned, hashable set of weighting parameters. Verdicts are keyed by it, which is what allows strategies to be compared side by side.
- **Divergence index.** The weighted share of evidence disagreeing with the majority opinion on an aspect.
- **Covariate attribution.** Identifying which characteristic, such as fuel type or model year, best explains a disagreement.
- **Effective sample size.** The Kish quantity `(Σw)² / Σw²`, which measures how much independent information a weighted sample actually carries.
- **Provenance.** The stored mapping from every generated claim to the exact evidence units that produced it.
