"""A deterministic development fixture.

This is NOT a real source and it is labelled as such everywhere it appears.
It exists for two reasons the project genuinely needs:

  1. Tests need input that does not change between runs. Asserting on scraped
     text would make the suite fail whenever a website edits a page.
  2. Every connector needs a documented fallback, per proposal section 22, so
     that a blocked source degrades coverage rather than stopping work.

The text is generated from templates rather than copied from any site, so
nothing here is anyone else's writing. The covariate structure is deliberate:
automatic owners are less happy about the gearbox, smaller-city owners are
less happy about service, and early build years are less happy about
reliability. That gives the divergence analysis something real to find, and it
mirrors the patterns the literature says exist.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from revix_core.enums import Modality, SourceKind
from revix_pipeline.connectors.base import (
    CatalogSeed,
    EvidenceUnitDraft,
    ExternalRef,
    RawPayload,
)

SOURCE_KEY = "fixture"

#: (aspect phrasing, polarity) pairs. Polarity is on -1..+1, the same scale
#: the extractor produces, so the fixture exercises the real range.
POSITIVE: dict[str, tuple[str, ...]] = {
    "engine_gearbox": (
        "The engine pulls cleanly from low revs and the gearbox is smooth in traffic.",
        "Power delivery is linear and the shifts are quick without being jerky.",
    ),
    "ride_handling_nvh": (
        "Ride quality over broken roads is genuinely excellent and the cabin stays quiet.",
        "It soaks up potholes far better than anything else I test drove.",
    ),
    "running_cost": (
        "Mileage in mixed driving has been better than I expected.",
        "Running cost is low and servicing has not been expensive so far.",
    ),
    "space_comfort": (
        "Rear seat space is generous and three adults fit without complaint.",
        "Seats are supportive on long drives and there is plenty of storage.",
    ),
    "features": (
        "The touchscreen is responsive and connected features actually work.",
        "Feature list at this price is hard to argue with.",
    ),
    "build_quality": (
        "Panel gaps are consistent and nothing has rattled loose.",
        "Build feels solid, doors shut with a reassuring weight.",
    ),
    "safety": (
        "Six airbags and stability control as standard gave me confidence.",
        "Braking is strong and the structure feels reassuring.",
    ),
    "service_aftersales": (
        "Service centre was quick and the staff explained the bill properly.",
        "Spares were available immediately and the cost was reasonable.",
    ),
    "long_term_reliability": (
        "Three years in and nothing significant has gone wrong.",
        "It has been dependable through two monsoons without drama.",
    ),
}

NEGATIVE: dict[str, tuple[str, ...]] = {
    "engine_gearbox": (
        "In bumper to bumper traffic the gearbox hesitates on the one to two shift.",
        "Low speed jerkiness has been there since delivery and nobody can fix it.",
    ),
    "ride_handling_nvh": (
        "There is noticeable road noise at highway speeds and the ride is firm.",
        "The suspension crashes over sharp bumps and passengers notice.",
    ),
    "running_cost": (
        "Real world mileage is nowhere near the claimed figure.",
        "Running costs have been higher than I budgeted for.",
    ),
    "space_comfort": (
        "Rear seat is cramped for adults and under thigh support is poor.",
        "Boot space disappears once you fit the spare properly.",
    ),
    "features": (
        "The infotainment lags and disconnects from the phone repeatedly.",
        "Software has needed two updates and still misbehaves.",
    ),
    "build_quality": (
        "Interior plastics feel cheap and there are rattles from the dashboard.",
        "Paint quality is inconsistent and one panel has already faded.",
    ),
    "safety": (
        "Braking feel is inconsistent and the electronics intervene too late.",
        "Visibility over the shoulder is poor which makes lane changes awkward.",
    ),
    "service_aftersales": (
        "Spare parts took three weeks to arrive and the car sat at the workshop.",
        "Service costs are high and the advisor kept adding items I did not ask for.",
    ),
    "long_term_reliability": (
        "Multiple electrical niggles after the second year.",
        "Something has needed attention at almost every service visit.",
    ),
}

CITIES_METRO = ("Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune")
CITIES_SMALL = ("Nashik", "Indore", "Coimbatore", "Rajkot", "Guwahati", "Raipur")

#: Which topics each covariate moves, and by how much. Kept explicit so the
#: fixture's structure can be read rather than reverse engineered.
COVARIATE_EFFECTS: dict[str, dict[str, float]] = {
    "automatic": {"engine_gearbox": -0.55},
    "small_city": {"service_aftersales": -0.45},
    "early_year": {"long_term_reliability": -0.50},
}


class FixtureConnector:
    """Generates deterministic synthetic evidence for one variant.

    Parameterised by source kind so that several can be registered. That is
    not padding: a single source makes the source-weighted strategy
    meaningless, because there is nothing to weight differently, and it can
    never clear the three-source evidence floor. Three fixtures standing in
    for owner reviews, a forum and an expert publication exercise both.
    """

    base_url: str | None = None
    robots_policy: str | None = "Not applicable. Generated locally, nothing is fetched."
    rate_limit_rpm: int = 6000

    def __init__(
        self,
        *,
        source_key: str = SOURCE_KEY,
        display_name: str | None = None,
        kind: SourceKind = SourceKind.DATASET,
        source_prior: float = 0.5,
        per_variant: int = 60,
        verified_rate: float = 0.62,
        detail_bias: float = 0.0,
    ) -> None:
        self.source_key = source_key
        self.display_name = display_name or f"Development fixture: {source_key} (synthetic)"
        self.kind = kind
        self.default_source_prior = source_prior
        self.per_variant = per_variant
        self.verified_rate = verified_rate
        # Shifts how positive this source runs. Expert publications review
        # pre-production cars for a weekend and come out kinder than owners,
        # which is the media-versus-owner gap the verdict page reports.
        self.detail_bias = detail_bias

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]:
        yield ExternalRef(
            external_id=f"{self.source_key}:{seed.variant_id}",
            url=f"{self.source_key}://{seed.variant_id}",
            seed=seed,
        )

    def fetch(self, ref: ExternalRef) -> RawPayload:
        # Nothing is fetched. The payload records what was asked for, so the
        # raw store still has a replayable record of every generated batch.
        body = f"{self.source_key} request for {ref.external_id}".encode()
        return RawPayload(ref=ref, body=body, fetched_at=datetime.now(UTC), http_status=200)

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]:
        seed = raw.ref.seed
        if seed is None:  # pragma: no cover - discover always attaches one
            return []
        return list(self._generate(seed))

    def _generate(self, seed: CatalogSeed) -> Iterable[EvidenceUnitDraft]:
        # Seeded by variant id, so the same variant always produces the same
        # corpus and tests can assert on exact numbers.
        rng = random.Random(f"revix:{self.source_key}:{seed.variant_id}")
        name = seed.variant_name.casefold()
        is_automatic = any(t in name for t in (" at", "dct", "cvt", "amt", "ivt", "dsg", "dca"))
        now = datetime.now(UTC)

        for i in range(self.per_variant):
            months = rng.choice([1, 2, 3, 6, 9, 12, 18, 24, 30, 36, 44, 52])
            km = int(months * rng.uniform(600, 1800))
            small_city = rng.random() < 0.4
            city = rng.choice(CITIES_SMALL if small_city else CITIES_METRO)
            early_year = rng.random() < 0.35
            verified = rng.random() < self.verified_rate

            bias = self.detail_bias
            if is_automatic:
                bias += COVARIATE_EFFECTS["automatic"]["engine_gearbox"] * 0.2
            aspects = rng.sample(sorted(POSITIVE), k=rng.randint(2, 4))

            sentences: list[str] = []
            polarities: list[float] = []
            for aspect in aspects:
                base = rng.gauss(0.45, 0.45)
                if aspect == "engine_gearbox" and is_automatic:
                    base += COVARIATE_EFFECTS["automatic"]["engine_gearbox"]
                if aspect == "service_aftersales" and small_city:
                    base += COVARIATE_EFFECTS["small_city"]["service_aftersales"]
                if aspect == "long_term_reliability" and early_year:
                    base += COVARIATE_EFFECTS["early_year"]["long_term_reliability"]
                base = max(-1.0, min(1.0, base + bias))
                pool = POSITIVE[aspect] if base >= 0 else NEGATIVE[aspect]
                sentences.append(rng.choice(pool))
                polarities.append(base)

            mean_polarity = sum(polarities) / len(polarities)
            opening = f"Owned for {months} months, {km:,} km, driving mostly in {city}."
            text = " ".join([opening, *sentences])

            yield EvidenceUnitDraft(
                external_id=f"{self.source_key}:{seed.variant_id}:{i:04d}",
                text=text,
                modality=Modality.TEXT,
                url=f"{self.source_key}://{seed.variant_id}/{i:04d}",
                author_ref=f"fx-{rng.getrandbits(48):012x}",
                lang="en",
                published_at=now - timedelta(days=rng.randint(10, 1200)),
                rating_raw=round(min(5.0, max(1.0, 3.0 + mean_polarity * 2)), 1),
                rating_scale_max=5.0,
                is_verified_owner=verified,
                helpful_votes=rng.randint(0, 40),
                total_votes=rng.randint(40, 80),
                ownership_duration_months=months,
                km_driven=km,
                listing_title=f"{seed.manufacturer} {seed.model} {seed.variant_name}",
                variant_hint=seed.variant_name,
                model_hint=seed.model,
            )
