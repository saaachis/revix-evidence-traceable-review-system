# ADR 0003 — Precompute and serve: no model inference on the read path

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-30 |
| **Deciders** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |

## Context

The obvious architecture for a system like this is retrieval-augmented: the user asks about a vehicle, the application retrieves relevant reviews, and a language model reasons over them and answers. It is the default shape of most projects in this space.

It is also the shape that produces a different answer every time, cannot state a confidence, cannot be evaluated, depends on a free-tier API being awake during a graded demonstration, and costs an inference call per page view.

Our domain has a property that makes the alternative available: **model lineups change yearly, not hourly**. Nothing about a verdict needs to be computed at request time.

## Decision

All expensive work — resolution, embedding, extraction, scoring, verification, fusion, narration — happens in a nightly scheduled batch and is written to materialised rows in the `serving` schema.

Every API endpoint is a single indexed read. **No model runs during a user request.** The language model is invoked in batch, only to render prose over an already-computed verdict, and the application renders a complete verdict with `LLM_ENABLED=false`.

## Alternatives considered

| Option | Why not |
|---|---|
| **RAG at request time** | Non-deterministic, unevaluable, no confidence, slow, and fails live if the provider rate-limits. Also makes traceability a prompt instruction rather than a guarantee. |
| **Compute on first request, then cache** | Same failure modes as RAG, just less often. The first demo request is the one that matters, and it is the one that would be slow. |
| **Compute at request time, no model** | Weighted bootstrap over a few hundred evidence units per aspect per config is not a 300 ms operation, and it would be repeated identically for every visitor. |

## Consequences

**We get**

- p95 under 300 ms as an architectural property rather than an optimisation target.
- Determinism: the same verdict is served to the evaluator and to us, and it is reproducible from `raw` and `core`.
- Free-tier survivability. Inference cost is bounded by catalogue size, not traffic.
- The fusion toggle becomes a lookup by `(variant_id, fusion_config_id)` instead of a live recomputation — which is the only reason the flagship feature is affordable.
- Demo reliability. Nothing on the critical path can rate-limit us mid-presentation.

**We give up**

- Free-text questions about arbitrary vehicles. A user cannot ask something we did not precompute, and vehicles outside the seeded catalogue have no verdict at all. This is stated in scope, not hidden.
- Freshness within the day. Acceptable in a domain that moves yearly, and `last_updated` is shown on every surface.

**We will know this was wrong if**

- The full nightly pipeline stops fitting in an overnight window at 150 variants × 8 sources × 5 fusion configs, or
- evaluators consistently ask questions the precomputed surface cannot answer.
