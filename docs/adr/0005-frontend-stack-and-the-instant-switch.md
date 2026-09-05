# 5. The frontend stack, and why the switch is instant

**Status:** accepted · **Date:** 2026-09-05

## Context

[proposal.md](../proposal.md) section 23 specifies Next.js with the App Router,
TypeScript, Tailwind, shadcn/ui and Recharts, with a typed client generated
from the OpenAPI schema.

## Decisions

**Next.js 16, not 15.** npm flagged a security advisory against the 15.x line
and the only clean fix was the next major. We had written no page code at that
point, so the upgrade cost nothing. Waiting would have meant either shipping a
known-vulnerable build or paying for the migration later with a full app to
port. `npm audit` now reports zero vulnerabilities.

**Tailwind v4, CSS-first.** The Milestone 2 wireframe design system is a set of
custom properties. Tailwind v4's `@theme` block takes those directly, so what
was signed off in August is literally the same token values that ship, rather
than a translation of them into a JavaScript config.

**No shadcn/ui.** It is a component library for buttons, dialogs and form
controls. This product has almost none of those. Its interface is a score
track, an agreement chip and a segmented switch, all of which are twenty lines
of CSS against tokens we already had. Adding shadcn would mean adding Radix and
a component generator to avoid writing sixty lines.

**No Recharts.** Every visualisation here is a horizontal position on a track,
which is a `div` with a CSS custom property. A charting library would ship
around 100 KB to draw a coloured rectangle, and it would draw it slightly
differently from the wireframe.

**typedRoutes off.** Nearly every link in this app is built at runtime from API
data, `/v/${variant.id}` and `/evidence/${claim.id}`, which typedRoutes cannot
check. Enabling it means casting every link, and a cast on every link is worse
than no checking, because it trains you to ignore the type.

**playwright-core, not playwright.** Same API, drives an already-installed
Chrome instead of downloading a browser. On a free CI tier that is a minute of
runtime and a few hundred megabytes per run.

## The switch is fetched, not requested

The verdict page fetches **all three weighting strategies on the server** and
hands them to one client component. Flipping the switch is a `useState` change
over data already in the payload: no request, no spinner, no loading state.

This matters more than it looks. The switch is the single moment the whole
project rests on, and [proposal.md](../proposal.md) section 22 rates free-tier
cold start as the most likely cause of a bad demo. A switch that fetches would
put a cold database in the path of that moment. A switch that does not, cannot
fail.

It is only affordable because the pipeline computes every strategy for every
variant overnight, so switching is a lookup rather than a recomputation. The
architecture and the interface are making the same argument.

## Consequences

The verdict page payload carries three verdicts instead of one, around 48 KB of
HTML. That is the correct trade: bytes are cheap and the demo moment is not.
