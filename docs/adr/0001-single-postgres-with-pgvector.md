# ADR 0001 — One PostgreSQL database with pgvector, not a separate vector store

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-30 |
| **Deciders** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |

## Context

Revix stores relational records (vehicles, evidence units, verdicts, citation links) and embeddings (evidence chunks, for similarity in entity resolution). The earlier version of the concept used Qdrant for vectors, Redis for caching and Neo4j for a reviewer graph, alongside Postgres — four datastores for three people on free tiers over twelve weeks.

Every embedding in this system belongs to a row that already lives in Postgres, and every vector query is filtered by relational predicates (manufacturer, class, year window) before similarity is even relevant.

## Decision

One PostgreSQL database with the `pgvector` extension, on a free tier (Supabase or Neon). Four schemas by lifecycle: `raw`, `core`, `analysis`, `serving`. Embeddings are a `vector(384)` column on `evidence_chunk`, in the same transaction as the row they describe.

## Alternatives considered

| Option | Why not |
|---|---|
| **Qdrant** for vectors | pgvector is sufficient at this corpus size (~10⁵ chunks). A separate store introduces a whole class of Postgres-to-vector-store synchronisation bugs, plus a second connection string, backup story and free-tier limit. To be justified by measured recall@k and latency, not assumed. |
| **Redis** for caching | Verdicts are precomputed rows. There is nothing to cache. |
| **Neo4j** for a reviewer graph | A fourth datastore for no payoff at this scale. Graph features are computed in-process and stored as scalar columns. |
| **SQLite + FAISS** | No hosted free tier that the API and the nightly pipeline can both write to. |

## Consequences

**We get**

- Records and vectors transactionally consistent. An evidence chunk cannot exist without its embedding, or vice versa.
- One connection string, one migration path, one backup story, one thing to keep warm before the demo.
- Filtered similarity search is a plain `WHERE` clause, which is exactly the shape our entity-resolution queries take.

**We give up**

- Best-in-class ANN performance at very large scale, which we do not have and will not reach.
- Some specialised index tuning options.

**We will know this was wrong if**

- ANN recall@10 on the entity-resolution blocking step falls below what the cross-encoder can recover from, or
- p95 similarity query latency in the nightly pipeline makes a full re-embed run exceed the overnight window.

Both are measurable, and both are reported on the metrics page.
