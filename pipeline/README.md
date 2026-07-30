# pipeline

Everything that runs on the write path. Nightly, scheduled, resumable, idempotent. Orchestrated with Prefect.

**Owner:** Aditya Nariyapara (ingestion, orchestration) · Devika Jonjale (enrichment stages)

```
pipeline/
├── connectors/     one isolated adapter per source
└── enrichment/     the DAG: resolve → embed → extract → score → verify → fuse → narrate
```

## connectors/

Every source implements one interface:

```python
class Connector(Protocol):
    source_key: str

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]: ...
    def fetch(self, ref: ExternalRef) -> RawPayload: ...
    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]: ...
```

Cross-cutting behaviour comes from the framework, never reimplemented per connector: robots and terms checking, token-bucket rate limiting, exponential backoff, circuit breaker, checkpointing, content hashing, and telemetry to `ingest_run`.

**Raw payloads are persisted immutably before parsing**, so evidence is re-derived when a parser improves without re-contacting the source.

> **Resilience contract.** A connector never fails the pipeline. It fails itself, marks its source stale, and reports to the admin dashboard. **The product must remain complete and demonstrable with only three of eight connectors alive.**

Every connector's module docstring records what its source's `robots.txt` and terms say, and the date it was read. That text goes into the report.

| Connector | Kind | Week |
|---|---|---|
| `dataset_seed` | dataset | 1 |
| `owner_reviews_a` | owner_review | 2 |
| `owner_reviews_b` | owner_review | 2 |
| `regulatory` | regulatory | 3 |
| `expert_reviews` | expert_review | 4 |
| `forum` | forum | 4 |
| `reddit` | social | 6 (official API) |
| `youtube` | video | 6 (Data API + transcripts) |

## enrichment/

```
resolve_entities   → chunk_and_embed → extract_aspects → score_credibility
                   → verify_claims   → analyse_divergence → fuse → narrate
```

Each stage writes its output and can be re-run independently. `fuse` runs once **per fusion configuration** — a loop, not extra architecture.

Full detail in [docs/architecture.md](../docs/architecture.md).
