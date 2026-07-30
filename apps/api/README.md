# apps/api

The serving layer. FastAPI, Pydantic v2, SQLAlchemy. Read-only, contract-first.

**Owner:** Saachi Shinde · **Lands:** week 1

## Rules

1. **The OpenAPI schema is the source of truth.** The frontend's TypeScript client is generated from it.
2. **Every endpoint is a single indexed read** from the `serving` schema. No joins across `analysis`, no aggregation, no model inference. If an endpoint needs to compute something, the pipeline should have precomputed it.
3. **Read-only**, except admin mutations (re-run a connector, adjudicate a match, create a fusion config).
4. **p95 under 300 ms.** Measured and reported on `/metrics`, not assumed.

## Planned endpoints

```
GET  /health
GET  /variants?q=&class=&manufacturer=          search and filter
GET  /variants/{id}                             specifications
GET  /variants/{id}/verdict?fusion=             THE endpoint
GET  /variants/{id}/aspects?fusion=             per-aspect scores, intervals, divergence
GET  /claims/{id}/evidence                      the traceability drawer
GET  /evidence?variant=&source=&aspect=         corpus explorer
GET  /compare?variants=a,b,c&fusion=            side-by-side
GET  /fusion-configs                            what the toggle offers
GET  /metrics/latest                            evaluation dashboard feed
GET  /sources/health                            connector status
POST /admin/...                                 auth-gated mutations
```

`fusion` defaults to the configuration flagged `is_default`. Passing a different one is a lookup by `(variant_id, fusion_config_id)`, not a recomputation — which is the only reason the interface toggle is affordable.

## Responses state their own honesty

Every verdict response carries `evidence_count`, `effective_sample_size`, `sources_used` and `computed_at`. Variants below the evidence floor return a `suppressed` verdict with a reason, never a bad score.
