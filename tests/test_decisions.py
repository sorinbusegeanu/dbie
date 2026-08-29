import pytest
from pydantic import ValidationError

from dbie.domain.decisions import validate_finalist_promotion, validate_transition
from dbie.domain.enums import (
    AssumptionCategory,
    AssumptionCriticality,
    AssumptionStatus,
    CandidateState,
)
from dbie.domain.models import Assumption, ExperimentPrediction
from dbie.exceptions import DomainRuleViolation, InvalidStateTransition


def fatal_assumption(status: AssumptionStatus) -> Assumption:
    return Assumption(
        run_id="run-1",
        idea_id="idea-1",
        category=AssumptionCategory.DEMAND,
        statement="The buyer has an urgent recurring problem.",
        criticality=AssumptionCriticality.FATAL,
        falsification_condition="No observed recurring pain.",
        validation_condition="Independent sources establish recurring pain.",
        status=status,
    )


def test_unresolved_fatal_assumption_prevents_finalist() -> None:
    with pytest.raises(DomainRuleViolation, match="unresolved fatal"):
        validate_finalist_promotion([fatal_assumption(AssumptionStatus.UNKNOWN)])


def test_supported_fatal_assumption_allows_finalist() -> None:
    validate_finalist_promotion([fatal_assumption(AssumptionStatus.RESEARCH_SUPPORTED)])


def test_state_machine_rejects_shortcut() -> None:
    with pytest.raises(InvalidStateTransition):
        validate_transition(CandidateState.GENERATED, CandidateState.FINALIST)


def test_experiment_prediction_is_immutable() -> None:
    prediction = ExperimentPrediction(
        run_id="run-1",
        experiment_id="experiment-1",
        predicted_value="At least 10% conversion",
        rationale="Pre-registered expectation",
    )

    with pytest.raises(ValidationError):
        prediction.predicted_value = "Rewritten after observing the result"
