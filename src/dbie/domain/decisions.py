"""Candidate state transitions and decision preconditions."""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from dbie.domain.enums import (
    AssumptionCriticality,
    AssumptionStatus,
    CandidateState,
    DecisionType,
)
from dbie.domain.models import Assumption
from dbie.domain.eligibility import evaluate_eligibility
from dbie.domain.commercial import CommercialEconomics, CommercialEvidenceGrade
from dbie.domain.models import BusinessIdea
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


class ReadinessPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_evidence_coverage: float = Field(default=0.6, ge=0, le=1)
    minimum_independent_sources: int = Field(default=2, ge=1)
    minimum_ltv_to_cac: float = Field(default=3.0, ge=0)
    require_customer_validation_for_build: bool = True
    minimum_automation_ratio: float = Field(default=0.8, ge=0, le=1)
    maximum_human_minutes_per_customer_at_10x: float = Field(default=15, gt=0)
    minimum_supporting_evidence_confidence: float = Field(default=0.5, ge=0, le=1)
    maximum_scenario_spread: float = Field(default=1.0, ge=0)


class ReadinessAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: DecisionType
    reason_codes: list[str]
    blockers: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    required_next_actions: list[str] = Field(default_factory=list)
    evidence_coverage: float = Field(ge=0, le=1)
    evidence_confidence: float = Field(default=0, ge=0, le=1)
    readiness_score: float = Field(default=0, ge=0, le=10)
    scenario_uncertainty: float | None = Field(default=None, ge=0)


def assess_decision_readiness(
    idea: BusinessIdea,
    assumptions: Iterable[Assumption],
    evidence_grades: Iterable[CommercialEvidenceGrade] = (),
    economics: CommercialEconomics | None = None,
    *,
    policy: ReadinessPolicy | None = None,
    implementation_feasible: bool | None = None,
    differentiation_supported: bool | None = None,
) -> ReadinessAssessment:
    """Deterministic recommendation with eligibility and evidence gates first."""
    policy = policy or ReadinessPolicy()
    assumptions = list(assumptions)
    grades = list(evidence_grades)
    eligibility = evaluate_eligibility(idea)
    scalability = idea.autonomous_scalability
    hard_failures = list(eligibility.reason_codes)
    if scalability and scalability.target_automation_ratio < policy.minimum_automation_ratio:
        hard_failures.append("AUTOMATION_RATIO_BELOW_POLICY_THRESHOLD")
    if scalability and scalability.human_minutes_per_customer_at_10x > policy.maximum_human_minutes_per_customer_at_10x:
        hard_failures.append("HUMAN_WORKLOAD_EXCEEDS_POLICY_THRESHOLD")
    if hard_failures:
        return ReadinessAssessment(
            recommendation=DecisionType.KILL,
            reason_codes=["HARD_ELIGIBILITY_FAILURE", *hard_failures],
            blockers=hard_failures,
            required_next_actions=["Redesign the opportunity to satisfy digital eligibility and autonomous scalability."],
            evidence_coverage=0.0,
        )
    contradicted = [a for a in assumptions if a.criticality is AssumptionCriticality.FATAL and a.status in {AssumptionStatus.RESEARCH_CONTRADICTED, AssumptionStatus.EXPERIMENT_CONTRADICTED}]
    if contradicted:
        return ReadinessAssessment(
            recommendation=DecisionType.KILL,
            reason_codes=["FATAL_ASSUMPTION_CONTRADICTED"],
            blockers=[a.id for a in contradicted],
            required_next_actions=["Stop investment or reformulate the contradicted thesis."],
            evidence_coverage=0.0,
        )
    critical = [a for a in assumptions if a.criticality is AssumptionCriticality.FATAL]
    unresolved = [a for a in critical if a.status not in {AssumptionStatus.RESEARCH_SUPPORTED, AssumptionStatus.EXPERIMENT_SUPPORTED}]
    coverage = (sum(1 for grade in grades if grade.coverage > 0) / len(grades)) if grades else 0.0
    independent = min((g.independent_sources for g in grades), default=0)
    supporting = sorted({eid for grade in grades for eid in grade.evidence_ids})
    blockers: list[str] = []
    reasons: list[str] = []
    actions: list[str] = []
    if unresolved:
        blockers.extend(a.id for a in unresolved)
        reasons.append("UNRESOLVED_FATAL_ASSUMPTIONS")
        actions.append("Run the smallest experiment that can resolve each fatal assumption.")
    if coverage < policy.minimum_evidence_coverage:
        reasons.append("COMMERCIAL_EVIDENCE_COVERAGE_BELOW_THRESHOLD")
        blockers.append("commercial_evidence_coverage")
        actions.append("Collect independent evidence for uncovered commercial assumptions.")
    if independent < policy.minimum_independent_sources:
        reasons.append("INSUFFICIENT_INDEPENDENT_EVIDENCE")
        blockers.append("commercial_evidence_independence")
        actions.append("Collect evidence from independent source lineages.")
    demand = [g for g in grades if g.product_supporting_grade.value in {"CUSTOMER_VALIDATION", "PURCHASE_INTENT", "OBSERVED_TRANSACTION"}]
    if policy.require_customer_validation_for_build and not demand:
        reasons.append("PRODUCT_SPECIFIC_DEMAND_NOT_VALIDATED")
        blockers.append("product_specific_demand")
        actions.append("Validate product-specific willingness to pay with customers or transactions.")
    elif demand and max(g.product_supporting_confidence for g in demand) < policy.minimum_supporting_evidence_confidence:
        reasons.append("PRODUCT_DEMAND_EVIDENCE_CONFIDENCE_BELOW_THRESHOLD")
        blockers.append("product_demand_evidence_confidence")
        actions.append("Improve source reliability or collect independent product-specific evidence.")
    base = economics.scenarios.get("base") if economics else None
    scenario_spread = None
    if economics and base:
        spreads = []
        for metric in ("revenue", "ltv", "cac"):
            values = [getattr(economics.scenarios[name], metric) for name in ("pessimistic", "base", "optimistic")]
            if all(value is not None for value in values) and values[1] not in {None, 0}:
                spreads.append((max(values) - min(values)) / abs(values[1]))
        if spreads:
            scenario_spread = max(spreads)
            if scenario_spread > policy.maximum_scenario_spread:
                reasons.append("SCENARIO_UNCERTAINTY_ABOVE_THRESHOLD")
                blockers.append("scenario_uncertainty")
                actions.append("Collect evidence to narrow the assumptions driving the scenario spread.")
    if base is None or base.ltv is None or base.cac is None or base.contribution_margin is None:
        reasons.append("ECONOMICS_INSUFFICIENTLY_SPECIFIED")
        blockers.append("commercial_economics")
        actions.append("Record price, contribution margin, lifetime, and acquisition cost assumptions.")
    elif base.cac > 0 and base.ltv / base.cac < policy.minimum_ltv_to_cac:
        reasons.append("LTV_TO_CAC_BELOW_THRESHOLD")
        blockers.append("base_case_ltv_to_cac")
        actions.append("Improve pricing or reduce acquisition costs, then recalculate unit economics.")
    if economics and all(economics.scenarios[name].contribution_margin is not None and economics.scenarios[name].contribution_margin <= 0 for name in ("pessimistic", "base", "optimistic")):
        reasons.append("NONPOSITIVE_CONTRIBUTION_MARGIN")
        blockers.append("contribution_margin")
    if implementation_feasible is False:
        reasons.append("IMPLEMENTATION_NOT_FEASIBLE")
        blockers.append("implementation_feasibility")
        actions.append("Reduce implementation scope or resolve the blocking dependency.")
    elif implementation_feasible is None:
        reasons.append("IMPLEMENTATION_FEASIBILITY_UNKNOWN")
        actions.append("Estimate build effort, dependencies, and launch constraints.")
    if differentiation_supported is False:
        reasons.append("DIFFERENTIATION_UNSUPPORTED")
        actions.append("Test a specific advantage against named competitors.")
    elif differentiation_supported is None:
        reasons.append("DIFFERENTIATION_NOT_ASSESSED")
        actions.append("Compare the product against named alternatives using customer-relevant criteria.")
    if base and base.contribution_margin is not None and base.contribution_margin <= 0:
        reasons.append("NONPOSITIVE_BASE_CASE_CONTRIBUTION_MARGIN")
        blockers.append("base_case_contribution_margin")
        actions.append("Redesign price and cost structure to create positive contribution margin.")
    elif economics and economics.scenarios.get("pessimistic") and economics.scenarios["pessimistic"].contribution_margin is not None and economics.scenarios["pessimistic"].contribution_margin <= 0:
        reasons.append("PESSIMISTIC_SCENARIO_HAS_NONPOSITIVE_CONTRIBUTION_MARGIN")
        actions.append("Test whether pricing and costs remain viable under pessimistic assumptions.")
    if reasons:
        recommendation = DecisionType.MORE_EVIDENCE if any("INSUFFICIENT" in r or "BELOW_THRESHOLD" in r or "UNRESOLVED" in r or "NOT_VALIDATED" in r or "NOT_ASSESSED" in r or "UNKNOWN" in r or "UNCERTAINTY" in r for r in reasons) else DecisionType.ITERATE
    else:
        recommendation = DecisionType.BUILD
        reasons.append("READINESS_GATES_PASSED")
    class_strength = {
        "MARKET_SIGNAL": 0.2,
        "EXISTING_MARKET": 0.4,
        "CUSTOMER_VALIDATION": 0.6,
        "PURCHASE_INTENT": 0.8,
        "OBSERVED_TRANSACTION": 1.0,
    }
    demand_strength = max(
        (class_strength.get(item.product_supporting_grade.value, 0) * item.product_supporting_confidence for item in grades),
        default=0.0,
    )
    if base is None or base.ltv is None or base.cac is None or base.contribution_margin is None:
        economic_strength = 0.5
    elif base.contribution_margin <= 0 or (base.cac > 0 and base.ltv / base.cac < policy.minimum_ltv_to_cac):
        economic_strength = 0.0
    else:
        economic_strength = 1.0
    implementation_strength = 0.5 if implementation_feasible is None else float(implementation_feasible)
    differentiation_strength = 0.5 if differentiation_supported is None else float(differentiation_supported)
    automation_strength = (idea.autonomous_scalability.target_automation_ratio if idea.autonomous_scalability else 0.0)
    readiness_score = round(10 * (
        0.25 * coverage
        + 0.15 * ((sum(item.supporting_confidence for item in grades) / len(grades)) if grades else 0.0)
        + 0.20 * economic_strength
        + 0.15 * demand_strength
        + 0.10 * implementation_strength
        + 0.10 * differentiation_strength
        + 0.05 * automation_strength
    ), 4)
    return ReadinessAssessment(
        recommendation=recommendation,
        reason_codes=reasons,
        blockers=blockers,
        supporting_evidence_ids=supporting,
        required_next_actions=actions,
        evidence_coverage=coverage,
        evidence_confidence=(sum(item.supporting_confidence for item in grades) / len(grades)) if grades else 0.0,
        readiness_score=readiness_score,
        scenario_uncertainty=scenario_spread,
    )
