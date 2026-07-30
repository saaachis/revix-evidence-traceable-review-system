# ADR 0004 — Distributional divergence with covariate attribution, not NLI contradiction detection

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-30 |
| **Deciders** | Aditya Nariyapara, Devika Jonjale, Saachi Shinde |

## Context

Disagreement between reviews is the most valuable signal in the corpus and the thing every competitor hides. The question is how to detect and explain it.

An earlier version of this proposal used an off-the-shelf natural language inference model to detect contradictions between review sentences, and surfaced them as a "contradiction" badge.

Two problems became clear. NLI models are trained on clean, purpose-built sentence pairs; Indian owner-review text is noisy, code-mixed and transliterated. And more fundamentally, most disagreement in this corpus is **legitimate**: it arises from different variants, cities, service centres, model years and use patterns. "The gearbox is jerky" and "the gearbox is smooth" are not contradictory when one owner drives an automatic in Mumbai traffic and the other a manual on highways. NLI would flag that as a contradiction, which is simply wrong.

## Decision

Contradiction detection is removed. In its place:

1. **Divergence index** — the weighted fraction of evidence disagreeing with the majority polarity sign, per aspect per variant.
2. **Covariate attribution** — for each covariate (fuel type, transmission, model year, ownership bucket, source kind, verified status), compute between-group variance in polarity and report the covariate that explains the most.

Aspect cards in the interface are sorted by divergence, not by score.

## Alternatives considered

| Option | Why not |
|---|---|
| **Off-the-shelf NLI** | Unreliable on code-mixed noisy text; the heaviest inference cost in the pipeline for the least reliable output; and conceptually wrong, because it treats legitimate variation as contradiction. |
| **Fine-tuned NLI on our own labels** | Requires a labelled contradiction set we do not have time to build, to solve a problem statistics already solves. |
| **Just report variance** | Tells the user opinion is split but not why, which is the half that is actually useful. |

## Consequences

**We get**

- Statements of real value: *"Opinion on the gearbox is split. 71% of the disagreement is explained by transmission: automatic owners rate it 0.62, manual owners 0.88."*
- Deterministic, cheap, reproducible output that needs no inference at all.
- An explanation a non-technical evaluator understands in one sentence.
- Something no competitor shows, because it makes a product page look complicated.

**We give up**

- Detection of genuine factual contradiction between two specific sentences — for example, one review claiming 21 kmpl and another 14. That case is handled instead by claim verification against the specification knowledge base, which is more reliable anyway.

**We will know this was wrong if**

- The top covariate is unstable across bootstrap resamples, meaning the attribution is noise rather than signal. This is measured, and reported in [evaluation.md](../evaluation.md).

**Removing NLI is a design decision and should be presented as one**, not quietly omitted.
