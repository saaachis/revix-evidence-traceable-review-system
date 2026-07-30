# apps/web

The user-facing application. Next.js (App Router), TypeScript, Tailwind, shadcn/ui, Recharts.

**Owner:** Saachi Shinde · **Lands:** week 1 (skeleton), week 5–6 (verdict page v1)

## Surfaces

| Route | Purpose |
|---|---|
| `/` | One search box over make, model and variant. Featured verdicts. Nothing else. |
| `/v/[variantId]` | **The verdict page.** The product. |
| `/compare` | Two or three variants side by side, aspect by aspect, intervals drawn. |
| `/evidence` | Filterable corpus view: source, date, verified status, ownership duration, aspect, polarity. |
| `/method` | Plain-language explanation of how scores, weights and confidence are computed. |
| `/metrics` | The public evaluation dashboard, refreshed by CI. |
| `/admin` | Connector health and operations. Authentication-gated. |

## The design decisions that matter

- **Aspect cards sort by divergence, not by score.** Conflict first. This is the product's identity and the opposite of what every competitor does.
- **Every number is clickable**, opening the evidence drawer with the exact contributing units, their weights and outbound links.
- **Confidence is an interval bar, never a percentage.** In Compare, overlapping intervals honestly say *"these two are not distinguishable on this aspect"* — something no comparison site will ever say.
- **The claimed-versus-actual mileage gap is a headline number.**
- **The fusion toggle is the flagship.** Switching weighting re-renders every score, interval and ranking with an animated transition and a "what changed" delta chip. It belongs on the first slide and at the top of the README.

## Notes

- The verdict page uses server components. It is the highest-value page and must render server-side with no client waterfall.
- The API client is **generated from the OpenAPI schema** — never hand-written, so the two cannot drift.
- Everything on screen is a precomputed row. If a component wants to compute something, that computation belongs in the pipeline.
