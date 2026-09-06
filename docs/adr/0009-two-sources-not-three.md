# 9. Two sources, not three

**Status:** accepted · **Date:** 2026-09-06

## Context

The evidence floor suppresses a verdict below `min_evidence_units` (40) and
`min_distinct_sources` (3). It exists so that no verdict rests on one
platform's culture: a site whose reviewers are enthusiasts and a site whose
reviewers are first-time buyers will disagree, and a score drawn from only one
of them is a measurement of that site rather than of the vehicle.

Three was written into [proposal.md](../proposal.md) section 16 before we had
surveyed what the Indian review landscape actually permits. It turned out to be
a number about a market we had not looked at yet.

Measured on the live site after the first real ingestion:

| | With a verdict |
|---|---|
| Cars | 17 of 28 |
| **Two-wheelers** | **0 of 15** |

Every bike in the catalogue published nothing.

## What we checked before moving the number

For two-wheelers there are only two publishers that permit us at all, and this
is not for want of looking:

| Source | Outcome |
|---|---|
| BikeDekho | **In use.** ~30 reviews per model, no pagination |
| YouTube | **In use.** Comments on review videos |
| ZigWheels | `robots.txt`: `Disallow: /user-reviews/*/*/*` |
| 91wheels | `robots.txt`: `Disallow: /` outright |
| BikeWale | Exposes exactly one review per model in its JSON-LD, whatever page you ask for |
| DriveSpark | No usable review pages found |
| Reddit | Self-serve API access closed, see ADR 0006 |

Counting BikeDekho and CarDekho as two sources was considered and rejected:
they are one publisher, Girnar, and splitting them would be gaming our own
quality rule rather than meeting it. CarWale counts separately because it
belongs to CarTrade, a genuinely different company.

So holding out for three meant two-wheelers would publish nothing, in a
project whose section 6.3 argues at length for why two-wheelers belong in
scope.

## Decision

**`min_distinct_sources` becomes 2.**

Two genuinely independent platforms is a real guard against one platform's
culture dominating a verdict, which is what this floor is for. One is not. The
difference between one and two is the difference between a measurement and an
echo; the difference between two and three is a matter of degree.

The verdict page prints the source count alongside every score, so a reader can
weigh a two-source verdict for themselves rather than taking our word that it
is sound. That disclosure is what makes this defensible rather than convenient,
and it must not be removed.

`min_evidence_units` stays at 40. Nothing we learned suggests 40 was wrong.

## The other half, which matters as much

Lowering the source floor alone would have unblocked **two of fifteen**
two-wheelers. The other thirteen fail on unit count, not source count: the
observed distribution was 10 to 25 units for most, and only two variants at 59.

So the floor change is paired with more evidence per vehicle:

- **YouTube: 4 videos per model to 8.** The search is the expensive call at 100
  quota units and happens once per model either way; each additional video's
  comments cost 1 unit. This roughly doubles the evidence for about 130 extra
  units a night out of 10,000.
- **CarWale: 5 pages per model to 8.** Five cleared the 40-unit floor on paper
  and did not in practice, because not every sentence carries an opinion the
  extractor can use.

Either change alone would have been close to useless. That is worth recording,
because "we lowered the threshold and coverage improved" would have been the
wrong lesson to take from it.

## Consequences

**More of the evidence now comes from the weakest source.** YouTube supplies the
most units and has the lowest source prior for good reason: comment sections
are anonymous, unverified, and full of people asking whether to buy rather than
describing what they own. Doubling its share is a real cost, and the
credibility weighting is what is supposed to absorb it. Whether it does is
measurable, and is exactly the question section 18.1 was designed to answer.

**This is a change to a quality commitment in the proposal, not a tuning
tweak.** It is recorded here rather than edited quietly into a settings file,
and the proposal text should be updated to match rather than left disagreeing
with the code.

**It is reversible in one line.** If a third two-wheeler publisher becomes
available, `min_distinct_sources` goes back to 3 and the affected verdicts
suppress themselves again on the next nightly.
