# 7. How the fusion experiment avoids fooling us

**Status:** accepted · **Date:** 2026-09-05

## Context

[proposal.md](../proposal.md) section 18.1 is the piece of work that the whole
project rests on. Every other component computes a verdict; this one asks
whether the verdict is any better than counting reviews, which is the only
question a reviewer actually cares about.

It is also the easiest thing in the repository to get quietly wrong. An
evaluation harness that is subtly circular still produces a table, the table
still has decimals in it, and decimals get believed.

## The decisions

**The target is a plain unweighted mean, not the `equal` strategy.** The
obvious implementation reuses `equal` for the gold consensus. That would be
wrong: `equal` still multiplies by extraction confidence, so the target would
share a term with every estimator, and the comparison would quietly favour
whichever strategy most resembles the target's own weighting. `gold_score` is
an arithmetic mean of polarity and nothing else.

**Every strategy sees the same draw.** Within one replicate the units are
sampled once, and all three strategies estimate from exactly that set. Drawing
independently per strategy would measure sampling noise and then report the
difference between two noise draws as a difference between strategies. This is
why the pools are indexed by unit id rather than held as lists.

**Gold membership is never inferred.** All three conditions from 18.1 are
required and all three come from platform metadata: verified owner, at least
twelve months, at least 10,000 km. A unit that reads exactly like a long-term
owner's account but whose platform cannot verify it is not gold. The entire
non-circularity claim rests on the target being defined by fields the
estimators never see, so `looks_like_ownership_account` in the connector layer
is deliberately not consulted here.

**The ablation shares the production weighting path.** Section 18.1 requires
results with and without the metadata features. Rather than a second scoring
implementation that would drift, `reliability()` takes `use_metadata` and
`gather_contributions` takes it through the params dict, so the ablation runs
the real code with one flag flipped. `Credibility` stores `base_textual`
alongside `base` so this costs a lookup rather than a rescoring pass.

Because that field is new, rows scored before it existed fall back to `base`,
which **understates** the ablation gap rather than inventing one. Run
`uv run revix enrich score --recompute` before quoting ablation numbers.

**The harness says when its own numbers are meaningless.** Three guards, all of
which fire in the output rather than living in someone's memory:

- If every source in the pool is a fixture, the report says in capitals that
  the numbers describe our own generator and are not evidence about anything.
- Every Spearman figure is printed with the number of variants it was computed
  over. A rank correlation across four variants is noise wearing a decimal
  point.
- If nothing is measurable, `revix eval fusion` exits non-zero. A silent zero
  is how a scheduled run reports "the experiment is fine" while measuring
  nothing, which is a failure mode this repository has already hit twice in CI
  for other reasons.

**Coverage below nominal is a finding, not a bug.** The bootstrap quantifies
sampling variation within the pool. When the pool and the verified owners
disagree systematically, the interval is correct about sampling and still
misses the target. That gap is precisely what section 18.3 exists to measure,
so the report explains it rather than tuning it away.

## Consequences

**No scientific-computing dependency.** Spearman with average ranks is a dozen
lines, and pulling in scipy for it would add a large build dependency to a
pipeline that otherwise has none. Ties get average ranks, so this is Pearson on
ranks rather than the `1 - 6Σd²/n(n²-1)` shortcut, which is wrong when values
repeat.

**The experiment currently cannot run on live data.** Reddit and YouTube do not
verify ownership, so `is_verified_owner` is null on every unit they produce and
the gold set is empty. The report says exactly this instead of returning an
empty table. Getting the experiment to run on real evidence therefore requires
a source that verifies ownership, which is now the strongest argument for the
third connector, ahead of the evidence floor.

**Results are not persisted yet.** Section 18.4 specifies an `eval_run` table
and a public `/metrics` route with trend over time. That needs a migration, and
per CONTRIBUTING section 5 the schema is jointly owned, so it is deliberately a
separate change for all three of us to approve rather than something smuggled
in alongside the harness.
