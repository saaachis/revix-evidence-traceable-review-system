# Architecture Decision Records

An ADR records **one decision, the reasoning behind it, and what we gave up**. It is written when the decision is made, not afterwards, and it is never edited after acceptance — if a decision changes, write a new ADR that supersedes the old one and leave the original in place.

Stating what was rejected is a stronger signal than listing what was adopted. That is the whole point of this folder.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-single-postgres-with-pgvector.md) | One PostgreSQL database with pgvector, not a separate vector store | Accepted |
| [0002](0002-evidence-unit-abstraction.md) | Every source becomes one Evidence Unit abstraction | Accepted |
| [0003](0003-precompute-and-serve.md) | Precompute and serve: no model inference on the read path | Accepted |
| [0004](0004-divergence-instead-of-nli.md) | Distributional divergence with covariate attribution, not NLI contradiction detection | Accepted |

## When to write one

Write an ADR when a choice is **hard to reverse**, **affects more than one person's area**, or **someone will ask "why did you do it that way?"** in the viva. Anything that changes one of the non-negotiables in [architecture.md](../architecture.md#non-negotiables) requires one.

Do not write one for library choices with no downstream consequence.

## How

Copy [`template.md`](template.md), number it sequentially, open it as a PR. The discussion happens in the PR; the merged file is the record.
