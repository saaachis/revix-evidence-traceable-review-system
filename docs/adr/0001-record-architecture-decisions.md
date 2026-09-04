# 1. Record architecture decisions

**Status:** accepted · **Date:** 2026-09-05

## Context

The proposal in [proposal.md](../proposal.md) fixes the architecture. Implementation
will inevitably depart from it in places, and "frameworks with justification" is
a marked component of the S3 submission. A decision that is only recorded in a
pull request comment is a decision nobody can defend two months later.

## Decision

Every departure from the proposal, and every framework choice that had a real
alternative, gets a short record in `docs/adr/`. Context, the decision, and
the consequences we accept. Numbered, immutable once accepted, superseded
rather than edited.

## Consequences

The viva question "why did you use X" has a written answer with a date on it.
The cost is a few minutes per decision.
