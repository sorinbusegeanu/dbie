"""Candidate state transitions and decision preconditions."""

from collections.abc import Iterable

from dbie.domain.enums import (
    AssumptionCriticality,
    AssumptionStatus,
    CandidateState,
    DecisionType,
)
from dbie.domain.models import Assumption
from dbie.exceptions import DomainRuleViolation, InvalidStateTransition

ALLOWED_TRANSITIONS: dict[CandidateState, set[CandidateState]] = {
    CandidateState.DISCOVERED: {CandidateState.GENERATED},
    CandidateState.GENERATED: {CandidateState.ELIGIBLE, CandidateState.KILL},
    CandidateState.ELIGIBLE: {CandidateState.VALIDATING, CandidateState.KILL},
    CandidateState.VALIDATING: {
        CandidateState.RED_TEAM,
        CandidateState.MORE_EVIDENCE,
        CandidateState.KILL,
    },
    CandidateState.MORE_EVIDENCE: {CandidateState.VALIDATING, CandidateState.KILL},
    CandidateState.RED_TEAM: {
        CandidateState.FINALIST,
        CandidateState.MORE_EVIDENCE,
        CandidateState.KILL,
    },
    CandidateState.FINALIST: {
        CandidateState.EXPERIMENTING,
        CandidateState.BUILD,
        CandidateState.ITERATE,
        CandidateState.KILL,
        CandidateState.MORE_EVIDENCE,
    },
    CandidateState.EXPERIMENTING: {
        CandidateState.BUILD,
        CandidateState.ITERATE,
        CandidateState.KILL,
        CandidateState.MORE_EVIDENCE,
    },
    CandidateState.BUILD: set(),
    CandidateState.ITERATE: set(),
    CandidateState.KILL: set(),
}


def validate_transition(current: CandidateState, target: CandidateState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"cannot transition {current} -> {target}")


def unresolved_fatal_assumptions(
    assumptions: Iterable[Assumption],
) -> list[Assumption]:
    resolved = {
        AssumptionStatus.RESEARCH_SUPPORTED,
        AssumptionStatus.EXPERIMENT_SUPPORTED,
    }
    return [
        item
        for item in assumptions
        if item.criticality is AssumptionCriticality.FATAL
        and item.status not in resolved
    ]


def validate_finalist_promotion(assumptions: Iterable[Assumption]) -> None:
    unresolved = unresolved_fatal_assumptions(assumptions)
    if unresolved:
        ids = ", ".join(item.id for item in unresolved)
        raise DomainRuleViolation(f"unresolved fatal assumptions: {ids}")


def decision_to_state(decision: DecisionType) -> CandidateState:
    return CandidateState(decision.value)
