# 3. A uv workspace with three packages

**Status:** accepted · **Date:** 2026-09-05

## Context

The API and the pipeline both need the ORM models, the settings and the session
factory. Three ways to arrange that: duplicate them, put them in the pipeline
and have the API depend on the pipeline, or extract a shared package.

## Decision

A `uv` workspace with three members and a one-way dependency:

```
revix-api ──────┐
                ├──> revix-core
revix-pipeline ─┘
```

`revix-core` imports neither of the other two.

## Consequences

The read path cannot accidentally import a scraper, and the write path cannot
accidentally import a FastAPI router. The rule is visible in the manifests
rather than living in someone's head.

`uv` over pip or poetry because it resolves the workspace in seconds, and
`uv sync --frozen` in CI gives byte-identical installs.

The cost is three `pyproject.toml` files instead of one.
