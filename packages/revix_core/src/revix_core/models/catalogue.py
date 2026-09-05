"""The canonical catalogue.

vehicle_variant is the centre of the system. Everything resolves to it, every
verdict is keyed by it, and its specifications provide both the hard
constraints used during matching and the ground truth used to check claims.

The reason variant granularity matters, and model granularity does not, is on
the model page of the prototype: the Creta diesel manual and the Creta turbo
automatic sit 1.1 points apart. Averaging them produces the number least
useful to someone choosing between them.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revix_core.enums import AspectKey, FuelType, Transmission, VehicleClass
from revix_core.models.base import SCHEMA_CORE, Base, TimestampMixin, uuid_pk


class Manufacturer(Base, TimestampMixin):
    __tablename__ = "manufacturer"
    __table_args__ = {"schema": SCHEMA_CORE}

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    country: Mapped[str | None] = mapped_column(String(2))

    models: Mapped[list[VehicleModel]] = relationship(back_populates="manufacturer")


class VehicleModel(Base, TimestampMixin):
    __tablename__ = "vehicle_model"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "slug"),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.manufacturer.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)

    # The class discriminator. A motorcycle is a catalogue row with a different
    # specification profile, not a separate subsystem. Proposal section 6.3.
    vehicle_class: Mapped[VehicleClass] = mapped_column(
        Enum(VehicleClass, name="vehicle_class", schema=SCHEMA_CORE), nullable=False
    )
    body_style: Mapped[str | None] = mapped_column(String(40))
    segment: Mapped[str | None] = mapped_column(String(40))
    launch_year: Mapped[int | None] = mapped_column(SmallInteger)
    discontinued_year: Mapped[int | None] = mapped_column(SmallInteger)

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="models")
    variants: Mapped[list[VehicleVariant]] = relationship(back_populates="model")


class VehicleVariant(Base, TimestampMixin):
    """THE canonical entity."""

    __tablename__ = "vehicle_variant"
    __table_args__ = (
        UniqueConstraint("model_id", "trim_code", "fuel_type", "transmission"),
        CheckConstraint(
            "spec_completeness >= 0 AND spec_completeness <= 1", name="spec_completeness_range"
        ),
        Index(
            "ix_vehicle_variant_trim_trgm",
            "trim_code",
            postgresql_using="gin",
            postgresql_ops={"trim_code": "gin_trgm_ops"},
        ),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_model.id", ondelete="CASCADE"), nullable=False
    )

    variant_name: Mapped[str] = mapped_column(String(160), nullable=False)
    # Normalised for matching: "SX (O) Knight" becomes "sx-o-knight". The
    # trigram index above is on this column, not on the display name.
    trim_code: Mapped[str] = mapped_column(String(160), nullable=False)

    # These three are the hard constraints. A petrol listing is never matched
    # to a diesel variant, whatever the embeddings say. Eliminating candidates
    # deterministically is what lets matching reach high precision cheaply.
    fuel_type: Mapped[FuelType] = mapped_column(
        Enum(FuelType, name="fuel_type", schema=SCHEMA_CORE), nullable=False
    )
    transmission: Mapped[Transmission] = mapped_column(
        Enum(Transmission, name="transmission", schema=SCHEMA_CORE), nullable=False
    )
    engine_cc: Mapped[int | None] = mapped_column(Integer)

    drivetrain: Mapped[str | None] = mapped_column(String(20))
    engine_power_bhp: Mapped[float | None] = mapped_column(Numeric(6, 2))
    engine_torque_nm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    arai_mileage_kmpl: Mapped[float | None] = mapped_column(Numeric(5, 2))

    length_mm: Mapped[int | None] = mapped_column(Integer)
    width_mm: Mapped[int | None] = mapped_column(Integer)
    height_mm: Mapped[int | None] = mapped_column(Integer)
    wheelbase_mm: Mapped[int | None] = mapped_column(Integer)
    ground_clearance_mm: Mapped[int | None] = mapped_column(Integer)
    fuel_tank_litres: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Car-specific
    boot_litres: Mapped[int | None] = mapped_column(Integer)
    seating_capacity: Mapped[int | None] = mapped_column(SmallInteger)

    # Two-wheeler specific
    kerb_weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    seat_height_mm: Mapped[int | None] = mapped_column(Integer)
    braking_type: Mapped[str | None] = mapped_column(String(40))

    ex_showroom_price_min: Mapped[int | None] = mapped_column(Integer)
    ex_showroom_price_max: Mapped[int | None] = mapped_column(Integer)
    price_band: Mapped[str | None] = mapped_column(String(30))
    production_status: Mapped[str | None] = mapped_column(String(20))

    spec_completeness: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    spec_source_refs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    model: Mapped[VehicleModel] = relationship(back_populates="variants")
    features: Mapped[list[VariantFeature]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class VariantFeature(Base):
    __tablename__ = "variant_feature"
    __table_args__ = (
        UniqueConstraint("variant_id", "feature_key"),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_variant.id", ondelete="CASCADE"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(Text)
    is_standard: Mapped[bool] = mapped_column(default=True, nullable=False)

    variant: Mapped[VehicleVariant] = relationship(back_populates="features")


class Aspect(Base):
    """The nine topics, as rows.

    Kept as a table rather than only an enum so that verdict_aspect can carry
    a foreign key, and so display labels and ordering can change without a
    migration.
    """

    __tablename__ = "aspect"
    __table_args__ = {"schema": SCHEMA_CORE}

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[AspectKey] = mapped_column(
        Enum(AspectKey, name="aspect_key", schema=SCHEMA_CORE), nullable=False, unique=True
    )
    label_car: Mapped[str] = mapped_column(String(80), nullable=False)
    label_two_wheeler: Mapped[str] = mapped_column(String(80), nullable=False)
    aspect_group: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
