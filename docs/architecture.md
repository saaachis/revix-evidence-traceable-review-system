# Architecture

Condensed from [proposal.md](proposal.md) sections 8 to 16. This is the document to read before writing code.

---

## The one decision everything else follows from

**The write path is strictly separated from the read path. No model runs during a user request.**

Revix is a *precompute-and-serve* platform. All expensive work happens in scheduled batch pipelines. Every user-facing request is a single indexed read of a precomputed row.

That one decision simultaneously solves latency, inference cost, source rate limits, language-model availability and — critically — live-demo reliability.

## The tiers

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

### Ingestion

Every source is a **connector** conforming to one interface, registered in the database, executed as an isolated flow.

```python
class Connector(Protocol):
    source_key: str

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]: ...
    def fetch(self, ref: ExternalRef) -> RawPayload: ...
    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]: ...
```

Cross-cutting behaviour lives in the framework, never in a connector: robots and terms checking, token-bucket rate limiting, exponential backoff, a circuit breaker, checkpointing for resumability, content hashing for deduplication, and telemetry written to `ingest_run`.

**Raw payloads are persisted immutably before parsing.** When a parser improves, evidence is re-derived without re-contacting the source. Better engineering, and the respectful thing to do.

> **Resilience contract.** A connector never fails the pipeline. It fails itself, marks its source stale and reports to the admin dashboard. **The product must remain complete and demonstrable with only three of eight connectors alive.** That is a requirement, not an aspiration.

### Enrichment

A deterministic, resumable, idempotent DAG. Each stage writes its output and can be re-run independently.

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

`fuse` runs **once per fusion configuration**. Producing every strategy for every variant is a loop, not extra architecture — and it is what powers the flagship interface feature.

### Serving

FastAPI, contract-first. The OpenAPI schema is the source of truth and the frontend's TypeScript client is generated from it, so the two cannot drift. Read-only except admin mutations. Target: **p95 under 300 ms**, achievable because responses are materialised rows.

### Presentation

Next.js App Router with server components for the verdict page, so the highest-value page renders server-side with no client waterfall.

---

## Data flow

**Ingestion** — nightly for evidence, weekly for the catalogue:

```
seed catalogue → connector.discover → connector.fetch → persist raw payload
   → connector.parse → EvidenceUnitDraft → dedupe by content_hash
   → insert evidence_unit → mark ingest_run complete
```

**Enrichment** — triggered on new evidence:

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

**Read** — a user request:

```
GET /variants/{id}/verdict?fusion=credibility_weighted
   → single indexed read from serving.verdict_current
   → JSON response, no computation
```

---

## The fusion engine

| Strategy | Description |
|---|---|
| `S0 equal` | Every evidence unit counts once. The baseline. |
| `S1 source_weighted` | Fixed per-source priors. |
| `S2 credibility_weighted` | Per-unit, aspect-conditional credibility weights. |
| `S3 credibility_recency` | S2 plus recency decay and launch-window correction. |
| `S4 stratified` | S3 plus covariate stratification. |

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

**Confidence intervals** come from weighted bootstrap over contributing units. Interval width is driven by the **Kish effective sample size**:

```
n_eff = (Σ w)² / Σ w²
```

Two hundred low-credibility reviews can carry a *smaller* effective sample than thirty high-credibility ones, so the interval correctly stays wide. One line of code; it is what makes the confidence meter defensible rather than decorative.

**Divergence index** is the weighted fraction of evidence disagreeing with the majority polarity sign.

**Covariate attribution** explains the split. For each covariate (fuel type, transmission, model year, ownership bucket, source kind, verified status), compute between-group variance in polarity and report the covariate explaining the most:

> *Opinion on the gearbox is split. 71% of the disagreement is explained by transmission: automatic owners rate it 0.62, manual owners 0.88.*

That is statistics, not natural language inference — cheaper, more reliable, more honest and far more useful than a contradiction badge. See [ADR 0004](adr/0004-divergence-instead-of-nli.md).

---

## The traceability guarantee

Traceability is **produced by the fusion engine and stored as rows**. It is never requested from a language model.

```
verdict ──┬── verdict_aspect        score, interval, divergence, covariate
          └── verdict_claim ──── verdict_claim_evidence ──── evidence_unit
                                  (contribution_weight, rank)
```

### The generation contract

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

### The deterministic guard

Post-generation validation, in code, not by another model:

1. Every `[Cn]` marker resolves to a real `verdict_claim`.
2. Every number in the prose appears in the corresponding `computed_values`.
3. Every named entity in the prose appears in the verdict payload.

Failure regenerates once, then falls back to a **template-rendered verdict**.

> **Revix cannot assert a number it did not compute, and it renders a complete verdict with the language model switched off entirely.**

Client-side, `[Cn]` markers resolve into citation chips. Clicking one opens the evidence drawer populated from `verdict_claim_evidence`, ordered by contribution weight. Traceability is a database join, made visible in the interface.

---

## Non-negotiables

These are architectural invariants. Changing one requires an ADR.

1. Every derived table is recomputable from `raw` and `core`. Nothing important lives only in a derived table.
2. `(source_id, external_id)` is unique and `content_hash` deduplicates, so re-running any connector is safe.
3. No model inference on the read path. Ever.
4. Every claim rendered in the interface has rows in `verdict_claim_evidence`.
5. The application renders a complete verdict with `LLM_ENABLED=false`.
6. A dead connector degrades the product; it never breaks it.
