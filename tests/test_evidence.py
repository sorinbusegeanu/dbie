from dbie.domain.enums import EvidenceDirection, EvidenceTier, EvidenceType
from dbie.domain.evidence import (
    can_validate_fatal_assumption,
    independent_lineage_count,
)
from dbie.domain.models import EvidenceItem


def evidence(
    identifier: str,
    lineage: str,
    *,
    tier: EvidenceTier = EvidenceTier.PRIMARY,
    evidence_type: EvidenceType = EvidenceType.OBSERVED,
) -> EvidenceItem:
    return EvidenceItem(
        run_id="run-1",
        source_identifier=identifier,
        source_type="report",
        extracted_fact="A decision-relevant observation.",
        tier=tier,
        evidence_type=evidence_type,
        direction=EvidenceDirection.SUPPORTS,
        reliability_score=0.9,
        freshness_score=0.9,
        lineage_group_id=lineage,
        content_hash=(identifier * 32)[:32],
    )


def test_syndicated_sources_count_as_one_lineage() -> None:
    items = [evidence("a", "press-release-1"), evidence("b", "press-release-1")]

    assert independent_lineage_count(items) == 1
    assert can_validate_fatal_assumption(items) is False


def test_two_independent_primary_sources_can_validate() -> None:
    items = [evidence("a", "lineage-a"), evidence("b", "lineage-b")]

    assert can_validate_fatal_assumption(items) is True


def test_model_consensus_is_not_evidence() -> None:
    items = [
        evidence(
            "a",
            "model-a",
            tier=EvidenceTier.MODEL_ONLY,
            evidence_type=EvidenceType.MODEL_JUDGMENT,
        ),
        evidence(
            "b",
            "model-b",
            tier=EvidenceTier.MODEL_ONLY,
            evidence_type=EvidenceType.MODEL_JUDGMENT,
        ),
    ]

    assert can_validate_fatal_assumption(items) is False


def test_observed_behavior_has_precedence() -> None:
    item = evidence("a", "experiment-1", tier=EvidenceTier.OBSERVED_BEHAVIOR)

    assert can_validate_fatal_assumption([item]) is True
