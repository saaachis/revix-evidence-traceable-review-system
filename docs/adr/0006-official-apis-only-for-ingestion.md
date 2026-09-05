# 6. Official APIs only, and what we checked before deciding

**Status:** accepted · **Date:** 2026-09-05

## Context

[proposal.md](../proposal.md) section 14 promises six to eight connectors and a
framework that is polite by construction. Section 24 puts the first real
connectors in week 2, with the exit criterion "a live URL showing real evidence
by day 10". Until now every number in the system came from
`FixtureConnector`, which is generated data with covariate effects we wrote
ourselves.

That matters more than it looks. Section 18.1 defines the central fusion
experiment: hold out verified long-term owners, estimate their consensus from
the remaining mixed pool, and compare the three strategies. Run on synthetic
data, that experiment recovers the parameters of our own generator and proves
nothing. **The evaluation cannot be trusted before the evidence is real**,
which is why connectors come before the experiment rather than after it.

## The decision

**We ingest only from official APIs, and from structured data a site publishes
for machines. We do not scrape.**

This was not a principle we started with. It is what the evidence supported
after checking each candidate:

| Source | What we found | Outcome |
|---|---|---|
| **Reddit** | Official OAuth API, free read access for a script app, documented 100 rpm limit | **Adopted.** `reddit` |
| **YouTube** | Official Data API v3, free 10,000 unit daily quota | **Adopted.** `youtube` |
| ZigWheels | `robots.txt` contains `Disallow: /user-reviews/*/*/*` | Rejected. They said no. |
| BikeWale | `robots.txt` permits it, and the listing page carries one schema.org `Review` in JSON-LD. But the other 565 reviews are in markup whose class names are hashed (`o-j4 o-jj`), and each full review needs its own request | Rejected. Brittle and slow. |
| Team-BHP | `robots.txt` permits the forum. The accessible sitemaps cover the new-car CMS, not ownership threads, which are reachable only through a search path that `robots.txt` disallows | Rejected for now. |

The BikeWale finding is the instructive one. Permission was not the obstacle;
durability was. A connector built on hashed class names breaks on their next
deploy, silently, and the first symptom would be a verdict quietly losing a
third of its evidence. An API contract breaks with a deprecation notice.

## Consequences

**Two live sources, and the evidence floor is now doing real work.**
`min_distinct_sources` is 3. With Reddit and YouTube alone, live-only ingestion
will correctly suppress most variants. That is the floor behaving exactly as
designed and it is the honest state of the project, not a bug to route around
by lowering the constant. A third source is the next connector task.

**Neither source can tell us who actually owns the vehicle.** There is no
verified-owner flag on Reddit or on a YouTube comment, so `is_verified_owner`
stays null on every unit from both, rather than being inferred. The gold set in
section 18.1 therefore has to be built from `ownership_duration_months` and
`km_driven`, and on these platforms those exist only inside the prose. See
`connectors/hints.py`, which is deliberately conservative: a missing hint
merely excludes a unit from the gold set, whereas a wrong one puts a
two-week impression into the pool that the strategies are scored against.

**robots.txt is not consulted for authenticated API calls.** `robots.txt`
governs crawlers. A client presenting credentials to the endpoint that the
platform issued those credentials for is not crawling, and applying robots
there would block the documented API on `www.reddit.com`. Every unauthenticated
fetch still goes through `RobotsCache`.

**Quota is a design input, not an afterthought.** A YouTube search costs 100
units against a daily 10,000 and a page of comments costs 1, so the connector
spends one search per variant and then reads deeply. It refuses a call it
cannot afford, because overrunning the quota does not fail loudly; it returns
403 for the rest of the day and would look like a broken connector the next
morning rather than a budget that ran out.

**Missing credentials are a configuration state, not a crash.** Both connectors
are registered whether or not their keys are present, so `revix ingest --source
reddit` names the missing variable and where to get it, instead of the source
vanishing from the registry and leaving you wondering whether you typed it
wrong. `revix ingest` exits non-zero when the one source you asked for produced
nothing; `revix pipeline nightly` still survives a dead source, because the
product is meant to stay complete with three of eight sources alive.
