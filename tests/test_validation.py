from dbie.domain.enums import AssumptionStatus, DecisionType
from dbie.services.assumption_pipeline import decompose_idea
from dbie.services.validation import RedTeamFinding, validation_decision
from tests.conftest import make_idea


def test_red_team_is_mandatory() -> None:
    assumptions = decompose_idea(make_idea())
    assert validation_decision(assumptions, []).reason_codes == ["RED_TEAM_REQUIRED"]


def test_supported_fatal_assumptions_and_resolved_attack_can_build() -> None:
    assumptions = decompose_idea(make_idea())
    for item in assumptions:
        item.status = AssumptionStatus.RESEARCH_SUPPORTED
    finding = RedTeamFinding(
        candidate_id=assumptions[0].idea_id,
        actor="Market Skeptic",
        attack="Buyer urgency may be overstated",
        severity=3,
        unresolved=False,
    )
    result = validation_decision(assumptions, [finding], heterogeneous_review=True)
    assert result.decision is DecisionType.BUILD
    assert result.independence_level.value == 3
