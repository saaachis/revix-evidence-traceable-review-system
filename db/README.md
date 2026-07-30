# db

One PostgreSQL database with `pgvector`. Alembic migrations. Four schemas by lifecycle: `raw`, `core`, `analysis`, `serving`.

**Jointly owned by all three of us.** A migration is the one change that breaks everybody at once, so every PR touching `migrations/` needs three approvals.

See [docs/data-model.md](../docs/data-model.md) for the full model and [ADR 0001](../docs/adr/0001-single-postgres-with-pgvector.md) for why there is only one datastore.

## Rules

- Every derived table is recomputable from `raw` and `core`. Nothing important lives only in a derived table.
- `(source_id, external_id)` is unique; `content_hash` deduplicates. Re-running a connector is always safe.
- Migrations run in CI before deployment. Never edit a migration that has been applied to the shared database — write a new one.
- Indexes to remember: trigram GIN on normalised trim strings, ANN on `evidence_chunk.embedding`, B-tree on `(variant_id, aspect_id)` and `(verdict_id)`.
- The API reads only from `serving`, refreshed at the end of each enrichment run.

## Usage

```bash
alembic revision --autogenerate -m "add vehicle_class to vehicle_model"
alembic upgrade head
alembic downgrade -1
```

Autogenerate is a starting point, not an answer. Read every generated migration before committing it — especially anything it wants to drop.
