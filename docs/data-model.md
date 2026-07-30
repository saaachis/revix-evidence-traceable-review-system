# Data model

One PostgreSQL database with the `pgvector` extension, hosted on a free tier (Supabase or Neon). Records and vectors stay transactionally consistent; there is one connection string, one migration path and one backup story. See [ADR 0001](adr/0001-single-postgres-with-pgvector.md).

## Four schemas, by lifecycle

| Schema | Contents | Mutability |
|---|---|---|
| `raw` | Immutable fetched payloads and references | Append-only |
| `core` | Canonical entities, evidence units, sources | Slowly changing |
| `analysis` | Aspect opinions, credibility, claims, divergence | Recomputable |
| `serving` | Materialised verdicts and views for the API | Fully derived |

**Design rules**

- Every derived table is recomputable from `raw` and `core`.
- `(source_id, external_id)` is unique; `content_hash` deduplicates. Re-running a connector is idempotent.
- Migrations are versioned with Alembic and run in CI before deployment.
- Indexes: trigram GIN on normalised trim strings, an ANN index on embeddings, B-tree on `(variant_id, aspect_id)` and `(verdict_id)`.
- The API reads only from `serving`, refreshed at the end of each enrichment run.

---

## Canonical entities

The `vehicle_variant` is the centre of the system. Everything resolves to it, every verdict is keyed by it, and its specifications provide both hard matching constraints and claim-verification ground truth.

```sql
manufacturer(id, name, slug, country)

vehicle_model(
    id, manufacturer_id, name, slug,
    vehicle_class,         -- car | two_wheeler
    body_style,            -- hatchback | sedan | SUV | MUV | commuter | cruiser | sport | scooter
    segment,               -- micro | compact | midsize | premium | luxury | 100-125cc | 150-250cc | ...
    launch_year, discontinued_year
)

vehicle_variant(                       -- THE canonical entity
    id, model_id,
    variant_name,                      -- "SX (O) Knight"
    trim_code,                         -- normalised: "sx-o-knight"
    fuel_type,                         -- petrol | diesel | cng | hybrid | electric
    transmission,                      -- mt | at | amt | cvt | dct | ivt
    drivetrain,
    engine_cc, engine_power_bhp, engine_torque_nm,
    arai_mileage_kmpl,
    length_mm, width_mm, height_mm, wheelbase_mm,
    ground_clearance_mm, fuel_tank_litres,
    boot_litres, seating_capacity,     -- cars
    kerb_weight_kg, seat_height_mm,
    braking_type,                      -- two-wheelers: drum | disc-front | dual-disc | abs-single | abs-dual
    ex_showroom_price_min, ex_showroom_price_max, price_band,
    launch_date, production_status,
    spec_completeness,                 -- 0..1, how much of the sheet we hold
    spec_source_refs jsonb             -- provenance for every spec field
)

variant_feature(variant_id, feature_key, feature_value, is_standard)

source_listing(                        -- what each source calls this variant
    id, source_id, external_id, url,
    raw_title, raw_specs jsonb,
    variant_id,                        -- null until resolved
    match_method,                      -- exact | spec_constraint | embedding
                                       -- | verifier | manual
    match_confidence, resolved_at
)
```

Class-specific specification fields are nullable by design. `spec_completeness` is computed against the field set applicable to the row's `vehicle_class`, so a motorcycle is not penalised for having no boot space.

### Entity resolution

A hybrid rule-and-model system. It beats a pure embedding approach because automobile specifications behave as **hard constraints**.

1. **Blocking** on manufacturer + model + year window.
2. **Hard constraints.** Fuel type, transmission family and engine displacement must agree. A petrol listing is never a diesel variant, whatever the embeddings say. This kills most candidate pairs deterministically and is why precision can be very high here.
3. **Normalised trim matching** with a synonym dictionary (`SX(O)` = `SX Optional` = `SX Opt`) and trigram similarity.
4. **Embedding similarity** on the residual, over the concatenated title and specification string.
5. **Cross-encoder verification** on remaining ambiguous pairs.
6. **Manual adjudication queue** in admin for anything below the confidence floor. Human-in-the-loop is a designed feature, not an admission of failure.

Measured against a hand-labelled gold set of roughly 400 pairs: precision, recall, F1 and residual unresolved rate.

---

## The Evidence Unit

Every source, whatever its shape, becomes one abstraction. This is decided on day one and it constrains everything after it, which is exactly why it is the highest-leverage decision in the project. See [ADR 0002](adr/0002-evidence-unit-abstraction.md).

```sql
evidence_source(                       -- connector registry
    id, source_key, display_name,
    kind,                              -- owner_review | expert_review | forum
                                       -- | video | social | regulatory
                                       -- | news | dataset
    base_url, robots_policy, rate_limit_rpm,
    default_source_prior,              -- used by the source-weighted strategy
    is_enabled, notes
)

evidence_unit(                         -- THE unified abstraction
    id, source_id,
    variant_id,                        -- resolved target, nullable
    model_id,                          -- fallback granularity when unknown
    external_id, url, author_ref,      -- pseudonymous author key, never PII
    text, lang, modality,              -- text | transcript | structured
    published_at, collected_at,
    rating_raw, rating_normalized,     -- mapped to 0..1 across differing scales
    is_verified_owner,
    helpful_votes, total_votes,
    ownership_duration_months,         -- automobile-specific, high value
    km_driven,                         -- automobile-specific, high value
    raw_ref, ingest_run_id, content_hash,
    spam_probability, credibility_json -- filled by enrichment
)

evidence_chunk(
    id, evidence_unit_id, chunk_index, text, embedding vector(384)
)

aspect_opinion(
    id, evidence_unit_id, chunk_id, aspect_id,
    polarity,                          -- -1..+1
    confidence, extracted_span
)

factual_claim(
    id, evidence_unit_id, claim_type,  -- mileage | dimension | feature
                                       -- | price | spec
    claimed_value, claimed_unit, normalized_value,
    variant_id, spec_field, spec_value,
    verdict,                           -- supported | contradicted | unverifiable
    delta
)
```

### Why `ownership_duration_months` and `km_driven` matter more than they look

They enable **aspect-conditional credibility**. An owner at 500 km is a credible witness to delivery experience and showroom behaviour, and a poor witness to long-term reliability. An owner at 60,000 km is the reverse.

Credibility is therefore not a scalar. It is a short vector over aspect groups:

```json
{
  "base": 0.71,
  "by_aspect_group": {
    "durability": 0.88,
    "immediate":  0.42,
    "service":    0.83,
    "efficiency": 0.79
  }
}
```

Cheap to compute, explainable to a non-technical audience in one sentence, and a genuinely better model of the world than a single trust score. Available only because the domain is automobiles.

---

## Verdicts and traceability

```sql
fusion_config(id, name, config_hash, params jsonb, is_default, created_at)

verdict(
    id, variant_id, fusion_config_id, computed_at,
    overall_score, confidence_low, confidence_high,
    evidence_count, effective_sample_size, sources_used jsonb,
    payload jsonb, narrative_id
)

verdict_aspect(
    id, verdict_id, aspect_id,
    score, ci_low, ci_high, support_count,
    divergence_index, top_covariate, covariate_explanation jsonb
)

verdict_claim(                          -- every assertable statement
    id, verdict_id, claim_type,
    claim_template, computed_values jsonb
)

verdict_claim_evidence(                 -- THE traceability table
    verdict_claim_id, evidence_unit_id,
    contribution_weight, rank
)
```

Verdicts are keyed by `(variant_id, fusion_config_id)`. That composite key is the entire reason the weighting switch in the interface is a lookup rather than a computation.

---

## The aspect taxonomy

Nine aspects, fixed, India-specific.

| # | Aspect | Reading for two-wheelers |
|---|---|---|
| 1 | Engine and performance | same |
| 2 | Ride quality, handling and NVH | same |
| 3 | Real-world mileage and running cost | same |
| 4 | Interior space and comfort | ergonomics and pillion comfort |
| 5 | Features and infotainment | same |
| 6 | Build quality | absorbs fit and finish |
| 7 | Safety | anchored on braking and ABS, not NCAP stars |
| 8 | **Service, after-sales and spare-part cost** | same |
| 9 | **Long-term reliability** | same |

Aspects 8 and 9 dominate Indian ownership satisfaction and are captured by no specification sheet or star rating. They are the product's reason to exist.
