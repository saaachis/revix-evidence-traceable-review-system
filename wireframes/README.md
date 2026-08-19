# Wireframes

Milestone 2. The screens of Revix, drawn as working HTML rather than static pictures, so the
weighting switch can actually be switched.

**Live:** published to GitHub Pages from this folder by [.github/workflows/pages.yml](../.github/workflows/pages.yml).
**Local:** open `index.html` in any browser. No server, no build step, no network.

## The flow

```
index.html          Home, the search entry point
   |
   +-- search.html          results for "creta": model, variants, near misses
   +-- browse.html          the catalogue, filtered, with one suppressed variant
   |
   +-- model.html           Hyundai Creta: seven variants, seven different verdicts
          |
          +-- verdict.html          THE product. Car example
          +-- verdict-bike.html     the same design for a two-wheeler
                 |
                 +-- evidence.html  the reviews behind one number, with weights
                 +-- compare.html   Creta against Seltos, including "too close to call"

   method.html       how a score is worked out, in plain language
   metrics.html      our own accuracy, including where we are weak
   sources.html      every source, what we take, how we behave
   admin.html        connector health, with one source deliberately failing
   preferences.html  settings, no account required
   suppressed.html   not enough evidence, so no score. A designed state
```

## Four rules the design follows

1. **One quantity, one encoding.** A score is a numeral plus one dot on one track. The band around
   the dot is the confidence range. Nothing else encodes the same number twice.
2. **Words before numbers.** `0.61` is meaningless to a buyer, so the interface says
   **Sharply split**. Three levels: broad agreement, some disagreement, sharply split.
3. **Colour encodes disagreement, never quality.** Grey means agreed, amber means some disagreement,
   red means sharply split. Quality is shown only by position on the track, so a contested 6.2 never
   reads as "bad", it reads as "contested". That is the product's whole argument.
4. **Three kinds of content, three visual forms.** Opinion gets score rows with ranges. Measured
   facts get tiles with no range. Metadata gets a quiet strip.

## The switch is real

`assets/revix.js` holds three precomputed strategies per vehicle, in the shape the fusion engine
would emit. Flipping the switch re-renders every score, every range, the ordering of the topics, and
the effective sample size, then reports what moved against the equal-weighted baseline. It is not
two drawings with a hotspot between them.

## Files

| File | What it is |
|---|---|
| `assets/revix.css` | Every token and component. One stylesheet for all fourteen screens, so consistency is enforced rather than checked by eye. |
| `assets/revix.js` | The vehicle data, the render, and the shared nav and footer. |
| `assets/fonts/` | The wordmark face, subset to five glyphs and embedded in the CSS. See `NOTICE.md`. |

## House style

No em dashes anywhere. Use a comma, colon, semicolon or plain hyphen. CI fails the build if one
appears.

## What happens to this next

These are not throwaway drawings. The tokens in `revix.css` become the shadcn and Tailwind theme,
and the markup becomes the components, when the Next.js build starts. See
[docs/proposal.md](../docs/proposal.md) section 20 for the surfaces and section 24 for the schedule.
