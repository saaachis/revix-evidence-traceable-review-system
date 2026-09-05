# 2. Scheduled CI instead of Prefect

**Status:** accepted · **Date:** 2026-09-05
**Supersedes:** the orchestration row in [proposal.md](../proposal.md) section 23

## Context

The proposal selects Prefect for orchestration. Reassessing it against what the
pipeline actually is:

- The enrichment DAG is **linear**: resolve, embed, extract, score, fuse, narrate.
  There is no branching and no fan-out that needs a scheduler to reason about.
- Every stage is **idempotent** by design, because the schema enforces it
  through `(source_id, external_id)` and `content_hash`. Re-running a stage is
  always safe, so recovery is "run it again", not "resume from checkpoint".
- Prefect wants a server or a Cloud workspace. That is another service to keep
  alive on a free tier, and free-tier cold start is already the top-rated risk
  in proposal section 22.
- We have six weeks.

## Decision

Each stage is a subcommand of a Typer CLI. A scheduled GitHub Actions workflow
calls them in order nightly. Failures surface as a red run with a full log,
and re-running is a button.

## Consequences

**We accept:** no DAG visualisation, and no orchestrator UI to show in the viva.
Observability is the Actions log plus the `ingest_run` table, which is what the
system status page reads from anyway.

**We gain:** zero additional infrastructure, no service to keep warm, the same
commands run locally and in CI, and retry semantics we did not have to
configure.

**Reversible:** if orchestration grows to need real DAG semantics, Prefect wraps
CLI commands as tasks without changing any pipeline code. The decision costs
nothing to undo.
