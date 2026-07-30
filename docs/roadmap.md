# Roadmap

Three people, twelve weeks. Roles are ownership areas, not silos. The schema in week 1 is owned by all three.

## Ownership

| Owner | Area |
|---|---|
| **Aditya Nariyapara** — Platform and Ingestion | Connector framework, all connectors, orchestration, raw store, freshness, admin backend |
| **Devika Jonjale** — Intelligence | Entity resolution, aspect extraction, credibility, fusion, claim verification, evaluation harness |
| **Saachi Shinde** — Application and Experience | API contract, frontend, verdict and compare pages, evidence explorer, metrics and admin interfaces, deployment |

## Schedule

| Week | Milestone | Exit criterion |
|---|---|---|
| **1** | Schema, repository, CI, deployment skeleton, API contract | Migrations run; empty application deployed; CI green |
| **2** | Connectors 1 and 2; catalogue seeded from a public dataset; first evidence units stored | **A live URL showing real evidence by day 10** |
| **3–4** | Variant-level entity resolution with gold set and metrics; connectors 3 and 4; admin health page v1 | **Checkpoint A** — ER precision and recall reported; four sources flowing |
| **5–6** | Aspect taxonomy, gold set and classifier; spam classifier; equal-weight verdict end to end; verdict page v1 | A real verdict renders in the browser |
| **7–8** | Credibility model; fusion engine; versioned configurations; subsample evaluation harness; ablations; **fusion toggle in the interface** | **Checkpoint B** — all strategies live and switchable |
| **9–10** | Confidence intervals and calibration study; divergence and covariate attribution; claim verification; grounded narration with guard and fallback | Calibration curve produced; guard passing |
| **11** | Compare view, evidence explorer, method page, public metrics page, performance, accessibility, seeded demo catalogue | p95 under 300 ms; demo rehearsed once |
| **12** | Report, video, final rehearsal, buffer | Everything frozen 48 hours before submission |

## Connector order

| Connector | Kind | Week |
|---|---|---|
| `dataset_seed` | dataset | 1 — bootstraps the catalogue and specifications |
| `owner_reviews_a` | owner_review | 2 |
| `owner_reviews_b` | owner_review | 2 |
| `regulatory` | regulatory | 3 — recalls and crash ratings |
| `expert_reviews` | expert_review | 4 |
| `forum` | forum | 4 |
| `reddit` | social | 6 — via the official API |
| `youtube` | video | 6 — Data API plus transcripts |

## Two disciplines that matter more than the schedule

1. **The deployed application must work every Friday.** A project that is live in week 2 and improves weekly beats one that integrates in week 11, every time.
2. **If Checkpoint B slips, cut in this order:** claim verification → persona ranking → image identification. **Never cut** the fusion toggle, the metrics page or the admin dashboard.

## Effort allocation

Roughly **60% application and data engineering, 40% machine learning**. If week 7 arrives with a beautiful credibility model and no deployed verdict page, the project is losing.

## The one thing to protect above all else

The fusion toggle and the language-model-off fallback, demonstrated together. Those two moments take about ninety seconds and communicate more about the quality of this project than the entire written report.

## Demo script — six minutes, rehearsed

| # | Action | The point being made |
|---|---|---|
| 1 | Search a popular vehicle; the verdict renders instantly | Precomputed, fast, real data |
| 2 | Read the header: score, interval, evidence count, effective n, freshness | Honest quantification |
| 3 | The top aspect card is the *most disagreed-upon* one; read the covariate explanation | Divergence, not averaging |
| 4 | Click a score; the evidence drawer opens with real reviews and their weights | Structural traceability |
| 5 | **Flip the fusion toggle.** The score moves, two vehicles swap rank, the interval narrows | The core idea, made visible |
| 6 | Show the ARAI-versus-real-world gap and a verified claim from a video transcript | Claim verification against a real knowledge base |
| 7 | Compare view: two rivals with overlapping intervals on one aspect | "Too close to call" is an honest answer |
| 8 | **Disable the language-model key and reload.** The full verdict still renders | *The intelligence is in the pipeline, not the model* |
| 9 | Admin: one connector deliberately failing, the system degraded and still serving | Real operational engineering |
| 10 | Metrics page with twelve weeks of trend data | Continuous evaluation |

Step 8 is the moment that separates this from every other project in the room. Rehearse it.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| A source blocks collection | High | Connector isolation, caching, immutable raw store for replay, a documented fallback dataset per connector, and a system that stays complete with three of eight alive |
| Terms-of-service exposure | High | Read robots and terms before writing each connector and record the findings; rate-limit and cache; store references not mirrors; attribute and link back; avoid absolute claims about any manufacturer |
| Thin evidence for less popular variants | High | Seed the 120–150 highest-volume variants deliberately; show coverage honestly; suppress verdicts below an evidence floor |
| Entity resolution errors | Medium | Hard specification constraints; a confidence floor routes ambiguity to manual adjudication rather than guessing |
| Aspect classifier underperforms on Hinglish | Medium | Multilingual encoder, transliteration-tolerant preprocessing, per-language F1 reported openly |
| Language-model downtime or hallucination | Medium | Batch-only generation cached by content hash, a deterministic validator, a template fallback |
| **Free-tier cold start during the presentation** | **High** | Warm-up cron, pre-warm before presenting, seeded database, verified golden demo variants, recorded backup video. *The most likely cause of a bad demo, and entirely preventable.* |
| Scope creep | High | Checkpoints at weeks 4 and 8 with a pre-agreed cut list; secondary objectives may not start until all primary ones are green |
| Team bandwidth across three people | Medium | Schema owned jointly in week 1, then clean interface boundaries; a working deployed application every Friday |
| Data staleness | Low | Nightly refresh, `last_updated` on every surface, a freshness heatmap in admin |
