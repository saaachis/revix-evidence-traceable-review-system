# Glossary

Every term used across this repository, defined once. If a term in code or a PR is not here and is not obvious, add it here.

| Term | Meaning |
|---|---|
| **Evidence unit** | One piece of evidence from one source about one vehicle: an owner review, an expert review, a forum post, a video transcript segment, a recall notice or a news item. The universal abstraction the whole pipeline operates on. |
| **Canonical variant** | The single true vehicle configuration that many differently worded listings across many sources all refer to. |
| **Entity resolution** | Deciding that two differently worded listings describe the same real vehicle variant. |
| **Aspect** | A specific dimension of the ownership experience — ride quality, after-sales service — as opposed to a single overall rating. Revix uses nine, fixed. |
| **Polarity** | How positive or negative a piece of evidence is about one aspect, on a scale from −1 to +1. |
| **Credibility** | How much weight a piece of evidence should carry, combining spam likelihood, author behaviour, textual specificity and corroboration. In Revix it is **conditional on the aspect being judged**. |
| **Aspect-conditional credibility** | The idea that a 500 km owner is a good witness to delivery experience and a poor one to long-term reliability, and a 60,000 km owner is the reverse. Stored as a short vector, not a scalar. |
| **Fusion** | Combining many weighted pieces of evidence into one score per aspect per variant. |
| **Fusion configuration** | A named, versioned, hashable set of weighting parameters. Verdicts are keyed by it, which is what allows strategies to be compared side by side and switched live in the interface. |
| **The fusion toggle** | The user-facing control that switches between equal, source-weighted and credibility-weighted verdicts. The flagship feature. |
| **Divergence index** | The weighted share of evidence disagreeing with the majority opinion on an aspect. |
| **Covariate attribution** | Identifying which characteristic — fuel type, transmission, model year — best explains a disagreement. |
| **Effective sample size** | The Kish quantity `(Σw)² / Σw²`, measuring how much independent information a weighted sample actually carries. Drives confidence interval width. |
| **Calibration** | Whether an 80% confidence interval actually contains the truth 80% of the time. Measured, not assumed. |
| **Provenance / traceability** | The stored mapping from every generated claim to the exact evidence units that produced it. A database join, not a prompt instruction. |
| **Connector** | An isolated, rate-limited, resumable adapter for one source, implementing `discover` / `fetch` / `parse`. |
| **Raw payload** | The unparsed response persisted immutably before parsing, so evidence can be re-derived when a parser improves without re-contacting the source. |
| **Ingest run** | One execution of one connector, with counts, timings and errors, surfaced on the admin health dashboard. |
| **Gold set** | A small hand-labelled dataset used to measure a component. Revix has two: entity-resolution pairs and aspect sentences. |
| **Gold consensus** | The held-out target of the central fusion experiment: the aspect score computed over long-term verified owners, who are then excluded from the estimation pool. |
| **Launch-window correction** | Adjusting for the fact that reviews written soon after launch are systematically kinder than later ones. |
| **The deterministic guard** | Post-generation validation in code: every citation marker resolves, every number in the prose was computed, every entity appears in the verdict payload. On failure, a template renders instead. |
| **Precompute-and-serve** | The architectural stance that all expensive work happens in scheduled batch, and every user request is a single indexed read. |
| **Variant class** | `car` or `two_wheeler`. Determines which specification fields apply and how two of the nine aspects are read. |
