# data

Only two things live here, and both are committed deliberately.

```
data/
├── seed/    catalogue seed lists — which variants we deliberately cover
└── gold/    hand-labelled evaluation sets
```

**Nothing else.** `data/raw/`, `data/cache/`, `data/interim/` and `data/processed/` are gitignored and CI fails the build if they appear. Raw payloads belong in the `raw` schema in Postgres, not in git.

## seed/

The catalogue is seeded **deliberately**, not sampled randomly, because evidence volume is heavily skewed towards popular models. Budget: 120 to 150 variants total, roughly 60% cars and 40% two-wheelers, weighted by evidence volume.

Each seed file is a CSV or JSON list of `(manufacturer, model, vehicle_class, years)` with a one-line note on why that model is in. Coverage against this list is reported in the admin dashboard.

## gold/

| Set | Size | Used for |
|---|---|---|
| `entity_resolution_pairs` | ~400 | ER precision, recall, F1 |
| `aspect_sentences` | ~500 | Aspect macro-F1, stratified and reported per language |

Rules for gold sets:

- Two annotators, disagreements adjudicated by the third. Record who labelled what.
- **Frozen once CI depends on them.** Growing a gold set is fine; silently changing labels to make a metric look better is not.
- The admin adjudication queue feeds corrected ER decisions back in over the semester, so the set grows for free. Log each addition in the PR.
- Never include personal data. Author identifiers are pseudonymous keys, not names, emails or profile URLs.
