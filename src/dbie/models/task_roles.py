"""Task-class to logical model-role contract from design section 36."""

from enum import StrEnum

from dbie.models.roles import ModelRole


class TaskClass(StrEnum):
    DISCOVERY_IDEATION = "discovery_ideation"
    OPPORTUNITY_SYNTHESIS = "opportunity_synthesis"
    ASSUMPTION_DECOMPOSITION = "assumption_decomposition"
    RESEARCH_PLANNING = "research_planning"
    MARKET_EVIDENCE = "market_evidence"
    COMPETITOR_RESEARCH = "competitor_research"
    REGULATORY_RESEARCH = "regulatory_research"
    GITHUB_RESEARCH = "github_research"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    EVIDENCE_RECONCILIATION = "evidence_reconciliation"
    EXPERIMENT_DESIGN = "experiment_design"
    MVP_IMPLEMENTATION = "mvp_implementation"
    TEST_FIX_LOOP = "test_fix_loop"
    INDEPENDENT_RED_TEAM = "independent_red_team"
    PRODUCTIZATION_CHALLENGE = "productization_challenge"
    ASSUMPTION_VALIDATION = "assumption_validation"
    FINANCIAL_ANALYSIS = "financial_analysis"
    INVESTMENT_DECISION = "investment_decision"
    JUDGE_INVESTMENT_DECISION = "judge_investment_decision"


TASK_MODEL_ROLES: dict[TaskClass, ModelRole] = {
    TaskClass.DISCOVERY_IDEATION: ModelRole.THINKER,
    TaskClass.OPPORTUNITY_SYNTHESIS: ModelRole.THINKER,
    TaskClass.ASSUMPTION_DECOMPOSITION: ModelRole.THINKER,
    TaskClass.RESEARCH_PLANNING: ModelRole.THINKER,
    TaskClass.MARKET_EVIDENCE: ModelRole.DOER,
    TaskClass.COMPETITOR_RESEARCH: ModelRole.DOER,
    TaskClass.REGULATORY_RESEARCH: ModelRole.DOER,
    TaskClass.GITHUB_RESEARCH: ModelRole.DOER,
    TaskClass.EVIDENCE_EXTRACTION: ModelRole.DOER,
    TaskClass.EVIDENCE_RECONCILIATION: ModelRole.THINKER,
    TaskClass.EXPERIMENT_DESIGN: ModelRole.THINKER,
    TaskClass.MVP_IMPLEMENTATION: ModelRole.BUILDER,
    TaskClass.TEST_FIX_LOOP: ModelRole.BUILDER,
    TaskClass.INDEPENDENT_RED_TEAM: ModelRole.JUDGE,
    TaskClass.PRODUCTIZATION_CHALLENGE: ModelRole.JUDGE,
    TaskClass.ASSUMPTION_VALIDATION: ModelRole.DOER,
    TaskClass.FINANCIAL_ANALYSIS: ModelRole.THINKER,
    TaskClass.INVESTMENT_DECISION: ModelRole.THINKER,
    TaskClass.JUDGE_INVESTMENT_DECISION: ModelRole.JUDGE,
}


def role_for_task(task_class: TaskClass) -> ModelRole:
    return TASK_MODEL_ROLES[task_class]
