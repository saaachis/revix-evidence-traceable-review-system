# apps/web

The user-facing application. Next.js 16 (App Router), TypeScript, Tailwind v4.

**Owner:** Saachi Shinde

```bash
npm install
npm run dev          # needs the API running on :8000
```

## Surfaces

| Route | Purpose |
|---|---|
| `/` | Search, featured verdicts, the three claims. |
| `/browse` | The whole catalogue, filterable by class. |
| `/search` | Results, with a designed empty state. |
| `/v/[variantId]` | **The verdict page.** The product. |
| `/evidence/[claimId]` | The reviews behind one number, with the weight each carried. |
| `/compare` | Two vehicles, including "too close to call". |
| `/method` | How a score is worked out, in plain language. |
| `/accuracy` | What we measure, and what we already know we are bad at. |
| `/sources` | Every source, what we take, how we behave. |
| `/status` | Live source health. A dead source degrades, it does not break. |

## The design decisions that matter

- **One quantity, one encoding.** `ScoreTrack` draws every score in the
  product. A 7.8 on the home page, the verdict page and the comparison all mean
  the same thing and are read the same way.
- **Colour encodes disagreement, never quality.** Grey agreed, amber some
  disagreement, red sharply split. Quality is position on the track and nothing
  else, so a contested 6.2 reads as contested rather than bad.
- **Words before numbers.** "Sharply split", not "0.61".
- **Topics sort by disagreement, never by score.** Conflict first. This is the
  product's identity and the opposite of what every competitor does.
- **The switch is instant.** All three strategies are fetched on the server and
  handed to one client component, so flipping it makes no request. See
  [ADR 0005](../../docs/adr/0005-frontend-stack-and-the-instant-switch.md).

## Rules

- `src/lib/api-types.ts` is **generated**. Never hand-edit it. Run
  `npm run openapi` after any change to an API response model. CI diffs the
  regenerated types against what is committed.
- Everything on screen is a precomputed row. If a component wants to calculate
  something, that calculation belongs in the pipeline.
- A section that fails should degrade, not crash. `tryGet` and the
  `Unavailable` component exist for exactly that.
