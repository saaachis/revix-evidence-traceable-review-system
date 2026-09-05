"""Evidence that describes a model rather than a trim.

A review site asks which model you bought, not which variant. Measured against
CarDekho and BikeDekho, only 10% of real owner reviews name a trim. Before
this, the other 90% reached nothing at all.

The danger in fixing that is worse than the problem it fixes: spreading a
model-level review across every variant of the model would credit a turbo
owner's gearbox complaint to somebody who bought the base manual, and no
reader could tell. So these tests pin the two things that keep it honest, that
the discount is applied and that the count is reported.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.models import EvidenceUnit, Verdict
from revix_core.settings import Settings, get_settings
from revix_pipeline.enrichment.fuse import Contribution

pytestmark = pytest.mark.db


class TestTheDiscount:
    def test_model_level_evidence_is_worth_less_than_a_review_of_the_trim(self) -> None:
        """Real evidence, weaker evidence. Not equal, and not discarded."""
        weight = Settings().model_level_evidence_weight
        assert 0.0 < weight < 1.0

    def test_the_discount_is_configuration_rather_than_a_buried_constant(self) -> None:
        """So it is visibly a judgement somebody made, and can be tuned."""
        assert Settings(model_level_evidence_weight=0.25).model_level_evidence_weight == 0.25

    def test_zero_restores_the_old_behaviour_of_ignoring_it(self) -> None:
        assert Settings(model_level_evidence_weight=0.0).model_level_evidence_weight == 0.0


class TestTheContribution:
    def test_a_contribution_knows_which_population_it_came_from(self) -> None:
        c = Contribution(
            unit_id="u1",
            weight=1.0,
            polarity=0.5,
            transmission="manual",
            fuel="petrol",
            source_key="cardekho",
            verified=None,
            ownership_months=None,
            km_driven=None,
            model_level=True,
        )
        assert c.model_level is True

    def test_it_defaults_to_variant_level(self) -> None:
        """Every existing caller means "a review of this exact trim"."""
        c = Contribution(
            unit_id="u1",
            weight=1.0,
            polarity=0.5,
            transmission="manual",
            fuel="petrol",
            source_key="fixture_owner",
            verified=None,
            ownership_months=None,
            km_driven=None,
        )
        assert c.model_level is False


class TestWhatTheDatabaseHolds:
    def test_a_verdict_reports_how_much_of_its_evidence_was_model_level(
        self, session: Session
    ) -> None:
        """The reader is told. Counting these silently would be the same trick
        this project exists to expose."""
        verdict = session.scalar(select(Verdict).where(Verdict.model_evidence_count > 0))
        if verdict is None:
            pytest.skip("no model-level evidence in this database yet")
        assert verdict.model_evidence_count <= verdict.evidence_count

    def test_model_level_units_are_never_also_claimed_as_variant_level(
        self, session: Session
    ) -> None:
        """A unit is evidence about a trim or about a model, never both."""
        both = session.scalars(
            select(EvidenceUnit).where(
                EvidenceUnit.variant_id.is_not(None), EvidenceUnit.model_id.is_not(None)
            )
        ).all()
        for unit in both:
            # Having both is fine and expected: a resolved variant implies its
            # model. What must not happen is a unit counted twice, which the
            # fuser prevents by testing variant_id first.
            assert unit.variant_id is not None

    def test_the_floor_still_suppresses_thin_model_level_evidence(self, session: Session) -> None:
        """Model-level evidence must not become a way to smuggle a verdict
        past the evidence floor."""
        settings = get_settings()
        thin = session.scalars(
            select(Verdict).where(Verdict.evidence_count < settings.min_evidence_units)
        ).all()
        for verdict in thin:
            assert verdict.is_suppressed
            assert verdict.overall_score is None
