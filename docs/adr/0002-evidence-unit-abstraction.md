# ADR 0002 — Every source becomes one Evidence Unit abstraction

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-30 |
| **Deciders** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |

## Context

Revix ingests six to eight sources whose native shapes have nothing in common: a star-rated owner review, a scored expert road test, a forum post inside a hundred-page thread, a timestamped video transcript segment, a recall notice, a row in a public dataset.

Every downstream stage — chunking, embedding, aspect extraction, credibility scoring, fusion, citation — has to operate on all of them. The choice is whether that happens once, at the boundary, or repeatedly, inside every stage.

This is a day-one decision. It cannot be retrofitted in week six without rewriting the pipeline.

## Decision

Every source normalises, at parse time, into a single `evidence_unit` row. A connector's only job is to produce `EvidenceUnitDraft` objects. Nothing downstream of ingestion knows or cares which source a unit came from, except through `source_id` and the `kind` enum.

Source-specific richness that does not fit the common shape is preserved in the immutable raw payload and in typed nullable columns (`rating_raw`, `ownership_duration_months`, `km_driven`, `helpful_votes`), never in per-source tables.

## Alternatives considered

| Option | Why not |
|---|---|
| **A table per source kind** (`owner_review`, `forum_post`, `video_segment`, …) | Every downstream stage becomes a union over N tables. Adding a source in week 6 means touching every stage. The fusion query becomes unreadable. |
| **A single JSONB blob per source** | No constraints, no indexes, no type safety. Bugs surface at fusion time, weeks after ingestion. |
| **Normalise later, in enrichment** | Pushes the same problem into the DAG and means the raw store has no consistent contract for replay. |

## Consequences

**We get**

- Adding a connector is genuinely additive. The pipeline does not change.
- `content_hash` deduplication and `(source_id, external_id)` uniqueness work uniformly, which is what makes every connector re-runnable.
- Credibility, fusion and citation are written once, not per source.
- The resilience contract is possible: if a connector dies, its units are simply absent, and nothing else notices.

**We give up**

- Some source-specific structure is flattened. A forum thread's reply hierarchy becomes ordering metadata rather than a first-class tree.
- The nullable-column set widens as sources accumulate.

**We will know this was wrong if**

- A planned source cannot be expressed as evidence units without a new table, or
- more than about a quarter of the columns on `evidence_unit` are populated by only one source.
