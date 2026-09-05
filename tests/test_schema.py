"""The schema invariants that everything downstream assumes.

Marked `db` because they need a live PostgreSQL with pgvector and pg_trgm.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from revix_core.enums import FuelType, Modality, SourceKind, Transmission, VehicleClass
from revix_core.models import (
    ALL_SCHEMAS,
    EvidenceSource,
    EvidenceUnit,
    Manufacturer,
    VehicleModel,
    VehicleVariant,
)
from revix_pipeline.reference import seed_all

pytestmark = pytest.mark.db


def _variant(session: Session, *, fuel: FuelType = FuelType.DIESEL) -> VehicleVariant:
    mfr = Manufacturer(name="Testyundai", slug=f"testyundai-{uuid.uuid4().hex[:8]}")
    model = VehicleModel(
        manufacturer=mfr,
        name="Testa",
        slug=f"testa-{uuid.uuid4().hex[:8]}",
        vehicle_class=VehicleClass.CAR,
    )
    variant = VehicleVariant(
        model=model,
        variant_name="SX (O)",
        trim_code="sx-o",
        fuel_type=fuel,
        transmission=Transmission.AT,
        engine_cc=1493,
    )
    session.add(variant)
    session.flush()
    return variant


def _source(session: Session) -> EvidenceSource:
    src = EvidenceSource(
        source_key=f"test-{uuid.uuid4().hex[:8]}",
        display_name="Test source",
        kind=SourceKind.OWNER_REVIEW,
    )
    session.add(src)
    session.flush()
    return src


class TestSchemaShape:
    def test_all_four_schemas_exist(self, session: Session) -> None:
        rows = session.execute(
            text("select nspname from pg_namespace where nspname = any(:names)"),
            {"names": list(ALL_SCHEMAS)},
        ).all()
        assert {r[0] for r in rows} == set(ALL_SCHEMAS)

    def test_the_api_only_ever_needs_the_serving_schema(self, session: Session) -> None:
        """Verdict rows must be reachable without joining core or analysis."""
        cols = session.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema='serving' and table_name='verdict'"
            )
        ).all()
        names = {c[0] for c in cols}
        # Everything the verdict header shows is on the row itself.
        assert {
            "overall_score",
            "confidence_low",
            "confidence_high",
            "evidence_count",
            "effective_sample_size",
            "sources_used",
            "computed_at",
        } <= names


class TestIdempotency:
    """Re-running any connector must be safe. Proposal section 13."""

    def test_same_source_and_external_id_cannot_be_inserted_twice(self, session: Session) -> None:
        src = _source(session)
        common = {
            "source_id": src.id,
            "external_id": "review-1",
            "text": "Fine car.",
            "modality": Modality.TEXT,
            "collected_at": datetime.now(UTC),
        }
        session.add(EvidenceUnit(**common, content_hash="a" * 64))
        session.flush()
        session.add(EvidenceUnit(**common, content_hash="b" * 64))
        with pytest.raises(IntegrityError):
            session.flush()

    def test_identical_text_cannot_arrive_under_a_different_id(self, session: Session) -> None:
        src = _source(session)
        digest = "c" * 64
        session.add(
            EvidenceUnit(
                source_id=src.id,
                external_id="review-1",
                text="Same words.",
                modality=Modality.TEXT,
                collected_at=datetime.now(UTC),
                content_hash=digest,
            )
        )
        session.flush()
        session.add(
            EvidenceUnit(
                source_id=src.id,
                external_id="review-2",
                text="Same words.",
                modality=Modality.TEXT,
                collected_at=datetime.now(UTC),
                content_hash=digest,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


class TestConstraints:
    def test_a_variant_cannot_repeat_trim_fuel_and_gearbox(self, session: Session) -> None:
        """The Creta diesel AT and the Creta diesel MT are different rows."""
        v = _variant(session)
        session.add(
            VehicleVariant(
                model_id=v.model_id,
                variant_name="SX (O) again",
                trim_code="sx-o",
                fuel_type=FuelType.DIESEL,
                transmission=Transmission.AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()

    def test_same_trim_with_a_different_fuel_is_allowed(self, session: Session) -> None:
        v = _variant(session)
        session.add(
            VehicleVariant(
                model_id=v.model_id,
                variant_name="SX (O) petrol",
                trim_code="sx-o",
                fuel_type=FuelType.PETROL,
                transmission=Transmission.AT,
            )
        )
        session.flush()  # must not raise

    def test_spam_probability_outside_zero_to_one_is_rejected(self, session: Session) -> None:
        src = _source(session)
        session.add(
            EvidenceUnit(
                source_id=src.id,
                external_id="bad",
                text="x",
                modality=Modality.TEXT,
                collected_at=datetime.now(UTC),
                content_hash="d" * 64,
                spam_probability=1.5,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


class TestReferenceSeeding:
    def test_seeding_loads_the_taxonomy_and_the_strategies(self, session: Session) -> None:
        added = seed_all(session)
        session.flush()
        assert added["aspects"] in (0, 9)
        assert added["fusion_configs"] in (0, 3)

    def test_seeding_twice_adds_nothing_the_second_time(self, session: Session) -> None:
        seed_all(session)
        session.flush()
        again = seed_all(session)
        assert again == {"aspects": 0, "fusion_configs": 0}


class TestVectorSupport:
    def test_pgvector_accepts_the_embedding_dimension_we_use(self, session: Session) -> None:
        from revix_core.models import EMBEDDING_DIM

        dim = session.execute(
            # cast(... as vector) rather than ::vector, because "::" collides
            # with SQLAlchemy's own bind parameter syntax.
            text("select vector_dims(cast(:v as vector))"),
            {"v": str([0.0] * EMBEDDING_DIM)},
        ).scalar_one()
        assert dim == EMBEDDING_DIM

    def test_trigram_similarity_is_available_for_trim_matching(self, session: Session) -> None:
        """ "SX(O)" against "SX Optional" is the matching problem in miniature."""
        score = session.execute(
            text("select similarity('sx-o-knight', 'sx-optional-knight')")
        ).scalar_one()
        assert 0.0 < float(score) < 1.0


class TestSeedingIsVisible:
    def test_default_strategy_is_unique(self, session: Session) -> None:
        seed_all(session)
        session.flush()
        from revix_core.models import FusionConfig

        defaults = list(session.scalars(select(FusionConfig).where(FusionConfig.is_default)))
        assert len(defaults) == 1
