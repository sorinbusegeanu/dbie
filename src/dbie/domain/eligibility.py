"""Deterministic hard eligibility rules."""

from pydantic import BaseModel, ConfigDict, Field

from dbie.domain.models import AutonomousScalability, BusinessIdea


class EligibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: bool
    reason_codes: list[str] = Field(default_factory=list)


def evaluate_eligibility(idea: BusinessIdea) -> EligibilityResult:
    reasons: list[str] = []
    digital = idea.digital_eligibility
    if digital is None:
        reasons.append("DIGITAL_ELIGIBILITY_MISSING")
    else:
        for dimension, passed in digital.model_dump().items():
            if not passed:
                reasons.append(f"DIGITAL_{dimension.upper()}_FAILED")

    scalability = idea.autonomous_scalability
    if scalability is None:
        reasons.append("AUTONOMOUS_SCALABILITY_MISSING")
    else:
        reasons.extend(_scalability_reasons(scalability))

    if not idea.target_customer.strip():
        reasons.append("CUSTOMER_MISSING")
    if not idea.buyer or not idea.buyer.strip():
        reasons.append("ECONOMIC_BUYER_MISSING")

    return EligibilityResult(eligible=not reasons, reason_codes=reasons)


def _scalability_reasons(value: AutonomousScalability) -> list[str]:
    reasons: list[str] = []
    if not value.credible_transition_plan:
        reasons.append("AUTOMATION_TRANSITION_NOT_CREDIBLE")
    if value.target_automation_ratio <= 0:
        reasons.append("AUTOMATION_TARGET_MISSING")
    if value.human_minutes_per_customer_at_10x >= value.human_minutes_per_customer:
        reasons.append("HUMAN_BURDEN_NOT_IMPROVING_AT_10X")
    return reasons
