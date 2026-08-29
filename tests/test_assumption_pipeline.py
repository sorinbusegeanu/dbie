from dbie.domain.enums import EvidenceDirection, EvidenceTier, EvidenceType
from dbie.domain.models import EvidenceItem
from dbie.services.assumption_pipeline import (
    EVIDENCE_ROUTES,
    StopReason,
    decompose_idea,
    evidence_stop_reason,
    validate_assumption,
)
from tests.conftest import make_idea


def evidence(run_id: str, direction: EvidenceDirection, lineage: str, *, model=False):
    return EvidenceItem(
        run_id=run_id,
        source_identifier=f"source-{lineage}",
        source_type="fixture",
        extracted_fact="A traceable fact",
        tier=EvidenceTier.MODEL_ONLY if model else EvidenceTier.PRIMARY,
        evidence_type=EvidenceType.MODEL_JUDGMENT if model else EvidenceType.MEASURED,
        direction=direction,
        reliability_score=0.8,
        freshness_score=0.9,
        lineage_group_id=lineage,
        content_hash=(lineage * 32)[:32],
    )


def test_decomposition_creates_all_twelve_atomic_assumptions_with_routes() -> None:
    assumptions = decompose_idea(make_idea())
    assert len(assumptions) == 12
    assert all(
        item.falsification_condition and item.validation_condition
        for item in assumptions
    )
    assert all(item.category in EVIDENCE_ROUTES for item in assumptions)


def test_model_agreement_cannot_validate_fatal_assumption() -> None:
    assumption = decompose_idea(make_idea())[0]
    items = [
        evidence(assumption.run_id, EvidenceDirection.SUPPORTS, "a", model=True),
        evidence(assumption.run_id, EvidenceDirection.SUPPORTS, "b", model=True),
    ]
    assert validate_assumption(assumption, items).status.value == "INCONCLUSIVE"


def test_evidence_stopping_is_deterministic() -> None:
    assert (
        evidence_stop_reason(
            independent_sources=2,
            required_sources=2,
            supports=2,
            contradicts=0,
            repeated_lineage_queries=0,
            expected_information_gain=0.8,
            calls_used=2,
            call_budget=10,
        )
        is StopReason.THRESHOLD_MET
    )
