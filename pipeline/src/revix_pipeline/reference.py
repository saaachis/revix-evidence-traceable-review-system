"""Reference data: the nine aspects and the weighting configurations.

These are not user data and not scraped data. They are the fixed vocabulary
the rest of the system is defined against, so they are seeded from code and
are idempotent: running this twice changes nothing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import ASPECT_GROUPS, ASPECT_LABELS, AspectKey, VehicleClass
from revix_core.models import Aspect, FusionConfig, utcnow

#: Display order on the verdict page is by disagreement at render time, so this
#: is only the fallback order used where nothing has been computed yet.
ASPECT_ORDER: tuple[AspectKey, ...] = (
    AspectKey.ENGINE_GEARBOX,
    AspectKey.RIDE_HANDLING_NVH,
    AspectKey.RUNNING_COST,
    AspectKey.SPACE_COMFORT,
    AspectKey.FEATURES,
    AspectKey.BUILD_QUALITY,
    AspectKey.SAFETY,
    AspectKey.SERVICE_AFTERSALES,
    AspectKey.LONG_TERM_RELIABILITY,
)


def config_hash(params: dict[str, Any]) -> str:
    """Stable hash of a parameter set, so two identical configs cannot coexist."""
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


#: The strategies the interface switch moves between. Every one of these is
#: computed for every variant, which is what makes switching a lookup rather
#: than a recomputation.
#:
#: S3 and S4 from proposal section 15.1 are deliberately absent for now. They
#: are additional rows in this list when the fusion engine supports them, not
#: additional architecture.
FUSION_CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "name": "equal",
        "label": "Every review equally",
        "description": (
            "One review, one vote. This is what every review site in India shows you today, "
            "and it is the baseline the other strategies are measured against."
        ),
        "display_order": 0,
        "is_default": False,
        "params": {
            "use_source_prior": False,
            "use_spam": False,
            "use_reliability": False,
            "use_aspect_fit": False,
            "use_recency": False,
            "use_launch_window": False,
        },
    },
    {
        "name": "source_weighted",
        "label": "By source",
        "description": (
            "Expert publications, owner reviews and forum posts carry different fixed weights, "
            "but every review from a given source counts the same."
        ),
        "display_order": 1,
        "is_default": False,
        "params": {
            "use_source_prior": True,
            "use_spam": False,
            "use_reliability": False,
            "use_aspect_fit": False,
            "use_recency": False,
            "use_launch_window": False,
        },
    },
    {
        "name": "credibility_weighted",
        "label": "By how much each can be trusted",
        "description": (
            "Each review is weighted by spam risk, detail and corroboration, and by whether "
            "that owner is a good witness to this particular topic."
        ),
        "display_order": 2,
        "is_default": True,
        "params": {
            "use_source_prior": True,
            "use_spam": True,
            "use_reliability": True,
            "use_aspect_fit": True,
            "use_recency": True,
            "use_launch_window": True,
            "recency_half_life_days": 540,
            "launch_window_days": 90,
            "launch_window_penalty": 0.7,
        },
    },
)


def seed_aspects(session: Session) -> int:
    """Insert any missing aspect rows. Returns how many were added."""
    existing = {a.key for a in session.scalars(select(Aspect))}
    added = 0
    for order, key in enumerate(ASPECT_ORDER):
        if key in existing:
            continue
        session.add(
            Aspect(
                key=key,
                label_car=ASPECT_LABELS[key][VehicleClass.CAR],
                label_two_wheeler=ASPECT_LABELS[key][VehicleClass.TWO_WHEELER],
                aspect_group=ASPECT_GROUPS[key].value,
                display_order=order,
            )
        )
        added += 1
    return added


def seed_fusion_configs(session: Session) -> int:
    """Insert any missing weighting configurations. Returns how many were added."""
    existing = {c.name for c in session.scalars(select(FusionConfig))}
    added = 0
    for spec in FUSION_CONFIGS:
        if spec["name"] in existing:
            continue
        session.add(
            FusionConfig(
                name=spec["name"],
                label=spec["label"],
                description=spec["description"],
                display_order=spec["display_order"],
                is_default=spec["is_default"],
                params=spec["params"],
                config_hash=config_hash(spec["params"]),
                created_at=utcnow(),
            )
        )
        added += 1
    return added


def seed_all(session: Session) -> dict[str, int]:
    return {
        "aspects": seed_aspects(session),
        "fusion_configs": seed_fusion_configs(session),
    }
