"""Phase 10 independence ladder and mandatory adversarial gate."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field

from dbie.domain.enums import (
    AssumptionCategory,
    AssumptionCriticality,
    AssumptionStatus,
    DecisionType,
)
from dbie.domain.models import Assumption


class IndependenceLevel(IntEnum):
    MODEL_JUDGMENT = 0
    EVIDENCE_AND_CHECKS = 1
    ISOLATED_CONTEXT_STABILITY = 2
    HETEROGENEOUS_LOCAL_MODEL = 3
    EXTERNAL_REVIEW = 4
    OBSERVED_MARKET_EXPERIMENT = 5


class RedTeamFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    actor: str
    attack: str = Field(min_length=1)
    severity: int = Field(ge=1, le=5)
    evidence_ids: list[str] = Field(default_factory=list)
    unresolved: bool = True


class ValidationDecision(BaseModel):
    decision: DecisionType
    reason_codes: list[str]
    independence_level: IndependenceLevel


def validation_decision(
    assumptions: list[Assumption],
    red_team_findings: list[RedTeamFinding],
    *,
    heterogeneous_review: bool = False,
) -> ValidationDecision:
    if not red_team_findings:
        return ValidationDecision(
            decision=DecisionType.MORE_EVIDENCE,
            reason_codes=["RED_TEAM_REQUIRED"],
            independence_level=IndependenceLevel.EVIDENCE_AND_CHECKS,
        )
    contradicted_fatal = any(
        item.criticality is AssumptionCriticality.FATAL
        and item.status is AssumptionStatus.RESEARCH_CONTRADICTED
        for item in assumptions
    )
    if contradicted_fatal:
        return ValidationDecision(
            decision=DecisionType.KILL,
            reason_codes=["FATAL_ASSUMPTION_CONTRADICTED"],
            independence_level=IndependenceLevel.EVIDENCE_AND_CHECKS,
        )
    unresolved = [
        item
        for item in assumptions
        if item.criticality is AssumptionCriticality.FATAL
        and item.status
        not in {
            AssumptionStatus.RESEARCH_SUPPORTED,
            AssumptionStatus.EXPERIMENT_SUPPORTED,
        }
    ]
    demand_or_price_without_evidence = any(
        item.category in {AssumptionCategory.DEMAND, AssumptionCategory.WTP}
        and item.status
        not in {
            AssumptionStatus.RESEARCH_SUPPORTED,
            AssumptionStatus.EXPERIMENT_SUPPORTED,
        }
        for item in assumptions
    )
    severe_attack = any(
        item.unresolved and item.severity >= 4 for item in red_team_findings
    )
    if unresolved or demand_or_price_without_evidence or severe_attack:
        reasons = ["UNRESOLVED_FATAL_ASSUMPTIONS"] if unresolved else []
        if demand_or_price_without_evidence:
            reasons.append("DEMAND_OR_PRICING_REQUIRES_NON_MODEL_EVIDENCE")
        if severe_attack:
            reasons.append("UNRESOLVED_RED_TEAM_FINDING")
        return ValidationDecision(
            decision=DecisionType.MORE_EVIDENCE,
            reason_codes=reasons,
            independence_level=IndependenceLevel.EVIDENCE_AND_CHECKS,
        )
    return ValidationDecision(
        decision=DecisionType.BUILD,
        reason_codes=["HARD_GATES_PASSED"],
        independence_level=(
            IndependenceLevel.HETEROGENEOUS_LOCAL_MODEL
            if heterogeneous_review
            else IndependenceLevel.EVIDENCE_AND_CHECKS
        ),
    )
