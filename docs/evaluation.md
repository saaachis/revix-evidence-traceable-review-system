# Evaluation

This is what separates a good application from an impressive one, and it needs no manual labelling beyond two small gold sets.

---

## 1. The central fusion experiment

The naive question — *"is our consensus correct?"* — has no ground truth and must not be asked. Instead:

> **Gold consensus (held out).** For each variant, compute the aspect score over evidence units that are verified owners with at least twelve months of ownership and at least 10,000 km, using equal weights within that subset. **These units are then removed from the estimation pool.**
>
> **Task.** From the remaining mixed-quality pool, draw `k` units and estimate the gold consensus.
>
> **Compare.** `S0 equal` vs `S1 source_weighted` vs `S2 credibility_weighted`, at `k ∈ {10, 20, 30, 50}`, over many random subsamples and all eligible variants.
>
> **Report.** RMSE, Spearman rank correlation across variants, and interval coverage.

This is non-circular, because the target is defined by metadata entirely excluded from the estimation pool. It tests exactly the hypothesis the project rests on:

*Do credibility signals identify which of the ordinary, unverified, mixed-quality evidence actually carries signal?*

It also supplies the **training objective for the reliability weights**, which is what makes "learned credibility" an honest phrase rather than a hand-wave.

**Required ablation for honesty.** Report results both with and without the metadata features (`is_verified_owner`, ownership duration), to show that the textual and behavioural features carry weight on their own. State this caveat explicitly in the report. A reviewer who finds it before you do costs more than the caveat itself.

## 2. External validity checks

| Check | Expectation |
|---|---|
| Fused safety sentiment vs Bharat and Global NCAP stars | Positive rank correlation |
| Fused reliability sentiment vs recall incidence | Negative rank correlation |
| Fused mileage estimate vs ARAI claimed figure | A consistent, quantifiable optimism gap |
| Fused value sentiment vs three-year resale retention | Positive rank correlation |

None is load-bearing alone. Agreement across four independent anchors is what persuades. For two-wheelers the NCAP anchor does not exist; the safety check falls back to braking specification and recall incidence, and this is reported as a gap rather than hidden.

## 3. Calibration

Across all subsample runs, measure whether the 80% predicted interval contains the gold consensus 80% of the time. Produce a reliability diagram and expected calibration error.

**This makes the confidence meter an evidenced claim rather than a decoration**, and it is the most sophisticated single element of the project.

## 4. Component metrics

| # | Component | Measured by |
|---|---|---|
| 1 | Entity resolution | Precision, recall, F1 on ~400 gold pairs; unresolved rate |
| 2 | Aspect extraction | Macro-F1 on ~500 gold sentences, reported per language |
| 3 | Spam detection | Precision, recall, F1, AUC on held-out data |
| 4 | Reliability weighting | Improvement in fusion RMSE over equal weighting |
| 5 | Divergence analysis | Stability across resamples, qualitative review |
| 6 | Claim verification | Precision on a hand-checked sample of 200 claims |
| 7 | Grounded narration | Faithfulness, guard pass rate, citation coverage |

## 5. Gold sets

Two, both small, both version-controlled under [`data/gold/`](../data/gold/).

| Set | Size | Built by | Used for |
|---|---|---|---|
| Entity-resolution pairs | ~400 | Two annotators, disagreements adjudicated by the third | ER precision/recall/F1 |
| Aspect sentences | ~500 | LLM-assisted bootstrap, then human correction; stratified by language | Aspect macro-F1, per-language F1 |

The admin adjudication queue feeds corrected decisions back into the ER gold set over the semester, so it grows for free.

## 6. The live metrics dashboard

Every metric above runs **in CI on every push** against frozen test sets, writes to an `eval_run` table, and is rendered at a public `/metrics` route inside the application, including trend over time.

| Group | Metrics |
|---|---|
| Entity resolution | Precision, recall, F1, unresolved rate |
| Aspect extraction | Macro-F1, per-aspect F1, per-language F1 |
| Spam detection | Precision, recall, F1, AUC |
| Fusion | RMSE and Spearman by strategy and by `k` |
| Confidence | Coverage at 80%, expected calibration error, reliability diagram |
| Grounding | Faithfulness, numeric-guard pass rate, citation coverage |
| Pipeline | Freshness by source, catalogue coverage, p50 and p95 latency |

Showing a metric **trending over twelve weeks** is what makes this read as real engineering practice rather than a one-off report. Which means the harness has to exist early, even when the numbers it produces are bad.

## 7. Handling code-mixed text honestly

Indian owner reviews are heavily Hinglish and often transliterated. Mitigations: a multilingual sentence encoder rather than an English-only model, transliteration-tolerant preprocessing, and language detection stored on every evidence unit so **per-language F1 is reported separately**.

Being transparent about degraded Hinglish performance is more credible than concealing it.
