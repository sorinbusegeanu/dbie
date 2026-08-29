"""Phase 9 atomic assumptions, evidence routing and deterministic stopping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dbie.domain.enums import (
    AssumptionCategory,
    AssumptionCriticality,
    AssumptionStatus,
    EvidenceDirection,
)
from dbie.domain.evidence import can_validate_fatal_assumption
from dbie.domain.models import Assumption, BusinessIdea, EvidenceItem
from dbie.tools.contracts import ToolName


@dataclass(frozen=True)
class AssumptionTemplate:
    category: AssumptionCategory
    statement: str
    falsification: str
    validation: str
    criticality: AssumptionCriticality = AssumptionCriticality.MATERIAL


TEMPLATES = (
    AssumptionTemplate(
        AssumptionCategory.DEMAND,
        "The target problem exists and is severe",
        "Independent sources show the problem is rare or immaterial",
        "At least two independent non-model sources quantify repeated pain",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.BUYER,
        "An identifiable buyer owns the problem",
        "No role owns budget or accountability",
        "A named role owns budget and the relevant outcome",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.WTP,
        "The buyer is willing to pay",
        "Observed behavior rejects the viable price range",
        "Primary or observed evidence supports the price range",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.DISTRIBUTION,
        "The buyer is reachable through a repeatable digital channel",
        "No compliant repeatable channel reaches the buyer",
        "A measurable digital channel reaches the buyer",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.FEASIBILITY,
        "The product is technically feasible",
        "A required capability cannot meet the quality threshold",
        "A bounded prototype or primary technical evidence meets it",
    ),
    AssumptionTemplate(
        AssumptionCategory.AUTOMATION,
        "At least 90% of delivery can be automated",
        "Human work scales linearly with customers",
        "Automation design keeps marginal human work sublinear",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.AUTOMATION,
        "Marginal human burden stays low at 10x scale",
        "Human minutes per customer do not decrease at 10x",
        "Estimated human minutes per customer decrease at 10x",
    ),
    AssumptionTemplate(
        AssumptionCategory.ECONOMICS,
        "Unit economics can sustain the delivery model",
        "Conservative gross margin is structurally negative",
        "Conservative costs support positive gross margin",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.DEFENSIBILITY,
        "Substitutes do not erase the value proposition",
        "An existing substitute is cheaper and equally effective",
        "Evidence shows a material underserved gap",
    ),
    AssumptionTemplate(
        AssumptionCategory.DEFENSIBILITY,
        "The product can retain a defensible advantage",
        "Capabilities are immediately commoditized with no wedge",
        "A data, workflow, distribution, or trust wedge persists",
    ),
    AssumptionTemplate(
        AssumptionCategory.REGULATORY,
        "The product can operate compliantly",
        "Official rules prohibit the delivery model",
        "Official sources support a compliant operating path",
        AssumptionCriticality.FATAL,
    ),
    AssumptionTemplate(
        AssumptionCategory.TIMING,
        "A verifiable why-now catalyst exists",
        "The claimed catalyst is absent or already reversed",
        "Dated evidence supports a current catalyst",
    ),
)


EVIDENCE_ROUTES: dict[AssumptionCategory, tuple[ToolName, ...]] = {
    AssumptionCategory.DEMAND: (
        ToolName.WEB_SEARCH,
        ToolName.SEARCH_REDDIT,
        ToolName.FETCH_PAGE,
    ),
    AssumptionCategory.BUYER: (ToolName.SEARCH_COMPANIES, ToolName.WEB_SEARCH),
    AssumptionCategory.WTP: (ToolName.SEARCH_COMPANIES, ToolName.WEB_SEARCH),
    AssumptionCategory.DISTRIBUTION: (ToolName.WEB_SEARCH, ToolName.SEARCH_COMPANIES),
    AssumptionCategory.FEASIBILITY: (ToolName.SEARCH_GITHUB, ToolName.PYTHON_EXECUTE),
    AssumptionCategory.AUTOMATION: (ToolName.SEARCH_GITHUB, ToolName.PYTHON_EXECUTE),
    AssumptionCategory.ECONOMICS: (ToolName.PYTHON_EXECUTE, ToolName.SEARCH_COMPANIES),
    AssumptionCategory.DEFENSIBILITY: (ToolName.SEARCH_COMPANIES, ToolName.WEB_SEARCH),
    AssumptionCategory.REGULATORY: (
        ToolName.SEARCH_REGULATIONS,
        ToolName.READ_DOCUMENT,
    ),
    AssumptionCategory.TIMING: (ToolName.WEB_SEARCH, ToolName.SEARCH_REGULATIONS),
}


def decompose_idea(idea: BusinessIdea) -> list[Assumption]:
    return [
        Assumption(
            run_id=idea.run_id,
            idea_id=idea.id,
            category=template.category,
            statement=template.statement,
            criticality=template.criticality,
            falsification_condition=template.falsification,
            validation_condition=template.validation,
        )
        for template in TEMPLATES
    ]


class StopReason(StrEnum):
    CONTINUE = "CONTINUE"
    THRESHOLD_MET = "THRESHOLD_MET"
    CONFLICT_ESCALATION = "CONFLICT_ESCALATION"
    DIVERSITY_SATURATED = "DIVERSITY_SATURATED"
    LOW_INFORMATION_GAIN = "LOW_INFORMATION_GAIN"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


def evidence_stop_reason(
    *,
    independent_sources: int,
    required_sources: int,
    supports: int,
    contradicts: int,
    repeated_lineage_queries: int,
    expected_information_gain: float,
    calls_used: int,
    call_budget: int,
) -> StopReason:
    if calls_used >= call_budget:
        return StopReason.BUDGET_EXHAUSTED
    if supports and contradicts and independent_sources >= required_sources:
        return StopReason.CONFLICT_ESCALATION
    if independent_sources >= required_sources:
        return StopReason.THRESHOLD_MET
    if repeated_lineage_queries >= 3:
        return StopReason.DIVERSITY_SATURATED
    if expected_information_gain < 0.1:
        return StopReason.LOW_INFORMATION_GAIN
    return StopReason.CONTINUE


def validate_assumption(
    assumption: Assumption, items: list[EvidenceItem]
) -> Assumption:
    result = assumption.model_copy(deep=True)
    supporting = [
        item for item in items if item.direction is EvidenceDirection.SUPPORTS
    ]
    contradicting = [
        item for item in items if item.direction is EvidenceDirection.CONTRADICTS
    ]
    result.evidence_for_ids = [item.id for item in supporting]
    result.evidence_against_ids = [item.id for item in contradicting]
    if contradicting and can_validate_fatal_assumption(contradicting):
        result.status = AssumptionStatus.RESEARCH_CONTRADICTED
        result.uncertainty = 0.2
    elif supporting and can_validate_fatal_assumption(supporting):
        result.status = AssumptionStatus.RESEARCH_SUPPORTED
        result.uncertainty = 0.25
    elif supporting or contradicting:
        result.status = AssumptionStatus.INCONCLUSIVE
        result.uncertainty = 0.65
    else:
        result.status = AssumptionStatus.UNKNOWN
        result.uncertainty = 1.0
    return result
