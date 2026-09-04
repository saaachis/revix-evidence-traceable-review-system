"""Closed vocabularies.

These are stored as native PostgreSQL enums so the database rejects a bad
value rather than trusting the application to have checked. The aspect
taxonomy is deliberately fixed at nine, per proposal section 17: a fixed
taxonomy is comparable across vehicles and measurable against a gold set,
which open aspect extraction is not.
"""

from __future__ import annotations

from enum import StrEnum


class VehicleClass(StrEnum):
    CAR = "car"
    TWO_WHEELER = "two_wheeler"


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    CNG = "cng"
    HYBRID = "hybrid"
    ELECTRIC = "electric"


class Transmission(StrEnum):
    MT = "mt"
    AT = "at"
    AMT = "amt"
    CVT = "cvt"
    DCT = "dct"
    IVT = "ivt"


class SourceKind(StrEnum):
    OWNER_REVIEW = "owner_review"
    EXPERT_REVIEW = "expert_review"
    FORUM = "forum"
    VIDEO = "video"
    SOCIAL = "social"
    REGULATORY = "regulatory"
    NEWS = "news"
    DATASET = "dataset"


class Modality(StrEnum):
    TEXT = "text"
    TRANSCRIPT = "transcript"
    STRUCTURED = "structured"


class MatchMethod(StrEnum):
    """How a source listing was resolved to a canonical variant.

    Ordered from most to least certain. Anything resolved by MANUAL came out
    of the adjudication queue, and those decisions feed back into the gold set.
    """

    EXACT = "exact"
    SPEC_CONSTRAINT = "spec_constraint"
    TRIGRAM = "trigram"
    EMBEDDING = "embedding"
    MANUAL = "manual"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"


class AspectKey(StrEnum):
    """The nine topics. Fixed. See proposal section 17.

    Two of these, service and long-term reliability, dominate Indian ownership
    satisfaction and appear in no specification sheet or star rating. They are
    the product's reason to exist.
    """

    ENGINE_GEARBOX = "engine_gearbox"
    RIDE_HANDLING_NVH = "ride_handling_nvh"
    RUNNING_COST = "running_cost"
    SPACE_COMFORT = "space_comfort"
    FEATURES = "features"
    BUILD_QUALITY = "build_quality"
    SAFETY = "safety"
    SERVICE_AFTERSALES = "service_aftersales"
    LONG_TERM_RELIABILITY = "long_term_reliability"


#: Display labels differ by vehicle class. A motorcycle has no interior, so
#: "interior space and comfort" is read as "ergonomics and pillion comfort".
#: The taxonomy still has exactly nine members, per proposal section 6.3.
ASPECT_LABELS: dict[AspectKey, dict[VehicleClass, str]] = {
    AspectKey.ENGINE_GEARBOX: {
        VehicleClass.CAR: "Engine and gearbox",
        VehicleClass.TWO_WHEELER: "Engine and gearbox",
    },
    AspectKey.RIDE_HANDLING_NVH: {
        VehicleClass.CAR: "Ride quality, handling and NVH",
        VehicleClass.TWO_WHEELER: "Ride quality and NVH",
    },
    AspectKey.RUNNING_COST: {
        VehicleClass.CAR: "Real-world mileage and running cost",
        VehicleClass.TWO_WHEELER: "Real-world mileage and running cost",
    },
    AspectKey.SPACE_COMFORT: {
        VehicleClass.CAR: "Interior space and comfort",
        VehicleClass.TWO_WHEELER: "Ergonomics and pillion comfort",
    },
    AspectKey.FEATURES: {
        VehicleClass.CAR: "Features and infotainment",
        VehicleClass.TWO_WHEELER: "Features and instrumentation",
    },
    AspectKey.BUILD_QUALITY: {
        VehicleClass.CAR: "Build quality",
        VehicleClass.TWO_WHEELER: "Build quality",
    },
    AspectKey.SAFETY: {
        VehicleClass.CAR: "Safety",
        VehicleClass.TWO_WHEELER: "Safety",
    },
    AspectKey.SERVICE_AFTERSALES: {
        VehicleClass.CAR: "Service, after-sales and parts",
        VehicleClass.TWO_WHEELER: "Service, after-sales and parts",
    },
    AspectKey.LONG_TERM_RELIABILITY: {
        VehicleClass.CAR: "Long-term reliability",
        VehicleClass.TWO_WHEELER: "Long-term reliability",
    },
}


class AspectGroup(StrEnum):
    """Groups used by aspect-conditional credibility.

    An owner at 500 km is a credible witness to DELIVERY and a poor one to
    DURABILITY. At 60,000 km it is the reverse. Grouping keeps that judgement
    to four coefficients instead of nine.
    """

    DURABILITY = "durability"
    IMMEDIATE = "immediate"
    SERVICE = "service"
    EFFICIENCY = "efficiency"


ASPECT_GROUPS: dict[AspectKey, AspectGroup] = {
    AspectKey.ENGINE_GEARBOX: AspectGroup.DURABILITY,
    AspectKey.RIDE_HANDLING_NVH: AspectGroup.IMMEDIATE,
    AspectKey.RUNNING_COST: AspectGroup.EFFICIENCY,
    AspectKey.SPACE_COMFORT: AspectGroup.IMMEDIATE,
    AspectKey.FEATURES: AspectGroup.IMMEDIATE,
    AspectKey.BUILD_QUALITY: AspectGroup.DURABILITY,
    AspectKey.SAFETY: AspectGroup.IMMEDIATE,
    AspectKey.SERVICE_AFTERSALES: AspectGroup.SERVICE,
    AspectKey.LONG_TERM_RELIABILITY: AspectGroup.DURABILITY,
}
