"""Least-privilege discovery, ideation, validation and red-team actors."""

from __future__ import annotations

import re
from dataclasses import dataclass

from crewai import Agent

from dbie.crews.router_llm import RouterLLM
from dbie.models.performance import ModelExecutionContext
from dbie.models.roles import ModelRole, ModelSelection
from dbie.models.task_roles import TaskClass
from dbie.tools.contracts import ToolName
from dbie.tools.crewai_tools import CrewAIToolContext, crewai_tools_for
from dbie.tools.gateway import ToolGateway


@dataclass(frozen=True)
class ActorSpec:
    role: str
    group: str
    goal: str
    tools: tuple[ToolName, ...]
    model_role: ModelRole


DISCOVERY_SPECS = (
    ActorSpec(
        "Trend Scout",
        "discovery",
        "Find emerging demand signals",
        (ToolName.WEB_SEARCH, ToolName.FETCH_PAGE),
        ModelRole.DOER,
    ),
    ActorSpec(
        "Pain-Point Miner",
        "discovery",
        "Find repeated costly pains",
        (ToolName.WEB_SEARCH, ToolName.SEARCH_COMMUNITY),
        ModelRole.DOER,
    ),
    ActorSpec(
        "Industry Analyst",
        "discovery",
        "Map industry workflow gaps",
        (ToolName.WEB_SEARCH, ToolName.SEARCH_COMPANIES),
        ModelRole.DOER,
    ),
    ActorSpec(
        "Regulatory Scout",
        "discovery",
        "Find regulation-driven needs",
        (ToolName.SEARCH_REGULATIONS, ToolName.READ_DOCUMENT),
        ModelRole.DOER,
    ),
    ActorSpec(
        "Technology Scout",
        "discovery",
        "Find newly feasible products",
        (ToolName.SEARCH_GITHUB, ToolName.WEB_SEARCH),
        ModelRole.DOER,
    ),
    ActorSpec(
        "Contrarian Scout",
        "discovery",
        "Search neglected and dissimilar problems",
        (ToolName.WEB_SEARCH, ToolName.SEMANTIC_MEMORY_SEARCH),
        ModelRole.DOER,
    ),
)

IDEATION_SPECS = tuple(
    ActorSpec(
        name,
        "ideation",
        f"Generate ideas through the {name}",
        (ToolName.DATABASE_QUERY, ToolName.SEMANTIC_MEMORY_SEARCH),
        ModelRole.THINKER,
    )
    for name in (
        "Automation Lens",
        "AI-Native Lens",
        "Regulatory Lens",
        "Vertical SaaS Lens",
        "API/Data Lens",
        "Services-to-Software Lens",
        "Capability-Inversion Lens",
        "Cross-Industry Analogy Lens",
    )
)

VALIDATION_SPECS = tuple(
    ActorSpec(
        name,
        "validation",
        f"Independently validate {name}",
        tools,
        ModelRole.DOER,
    )
    for name, tools in (
        (
            "Demand Validator",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_COMMUNITY,
            ),
        ),
        (
            "Economics Analyst",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_COMPANIES,
                ToolName.PYTHON_EXECUTE,
            ),
        ),
        (
            "Distribution Analyst",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_COMMUNITY,
                ToolName.SEARCH_COMPANIES,
            ),
        ),
        (
            "Technical Analyst",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_GITHUB,
                ToolName.PYTHON_EXECUTE,
            ),
        ),
        (
            "Competitive Analyst",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_COMPANIES,
                ToolName.SEARCH_GITHUB,
            ),
        ),
        (
            "Regulatory Validator",
            (
                ToolName.DATABASE_QUERY,
                ToolName.WEB_SEARCH,
                ToolName.FETCH_PAGE,
                ToolName.SEARCH_REGULATIONS,
                ToolName.READ_DOCUMENT,
            ),
        ),
    )
)

RED_TEAM_SPECS = tuple(
    ActorSpec(
        name,
        "red_team",
        f"Attack the candidate as {name}",
        (
            ToolName.DATABASE_QUERY,
            ToolName.WEB_SEARCH,
            ToolName.FETCH_PAGE,
            ToolName.SEARCH_COMPANIES,
            ToolName.SEMANTIC_MEMORY_SEARCH,
        ),
        ModelRole.JUDGE,
    )
    for name in (
        "Market Skeptic",
        "Incumbent Response Analyst",
        "Commoditization Analyst",
        "Distribution Skeptic",
        "Economics Skeptic",
        "Automation/Operations Skeptic",
    )
)

SYNTHESIS_SPECS = tuple(
    ActorSpec(name, "synthesis", goal, tools, ModelRole.THINKER)
    for name, goal, tools in (
        (
            "Opportunity Synthesizer",
            (
                "Synthesize qualified opportunities and write a concrete, "
                "evidence-aware business-opportunity description of at least 100 words"
            ),
            (ToolName.DATABASE_QUERY, ToolName.SEMANTIC_MEMORY_SEARCH),
        ),
        (
            "Assumption Decomposer",
            "Create falsifiable atomic assumptions",
            (ToolName.DATABASE_QUERY, ToolName.SEMANTIC_MEMORY_SEARCH),
        ),
        (
            "Research Planner",
            "Plan evidence collection by information gain",
            (ToolName.DATABASE_QUERY, ToolName.SEMANTIC_MEMORY_SEARCH),
        ),
        (
            "Evidence Reconciler",
            "Reconcile evidence and contradictions",
            (ToolName.DATABASE_QUERY, ToolName.SEMANTIC_MEMORY_SEARCH),
        ),
        (
            "Experiment Designer",
            "Design the cheapest falsifying experiment",
            (
                ToolName.DATABASE_QUERY,
                ToolName.SEMANTIC_MEMORY_SEARCH,
                ToolName.PYTHON_EXECUTE,
            ),
        ),
        (
            "Portfolio Reasoner",
            "Reason about uncertainty and portfolio value",
            (
                ToolName.DATABASE_QUERY,
                ToolName.SEMANTIC_MEMORY_SEARCH,
                ToolName.PYTHON_EXECUTE,
            ),
        ),
    )
)

BUILDER_SPECS = tuple(
    ActorSpec(name, "builder", goal, (), ModelRole.BUILDER)
    for name, goal in (
        ("MVP Implementer", "Implement a preregistered MVP specification"),
        ("Test Repair Agent", "Generate tests and repair bounded failures"),
        ("Integration Agent", "Integrate approved MVP components"),
    )
)


class CrewCatalog:
    def __init__(self, gateway: ToolGateway, llm: RouterLLM, *, memory_search_policy: dict[str, float | int] | None = None) -> None:
        self.gateway = gateway
        self.llm = llm
        self.memory_search_policy = memory_search_policy or {
            "minimum_retrieval_similarity": 0.15, "retrieval_limit": 5
        }

    @property
    def specs(self) -> tuple[ActorSpec, ...]:
        return (
            DISCOVERY_SPECS
            + IDEATION_SPECS
            + VALIDATION_SPECS
            + SYNTHESIS_SPECS
            + BUILDER_SPECS
            + RED_TEAM_SPECS
        )

    def build_agent(
        self,
        spec: ActorSpec,
        context: CrewAIToolContext,
        *,
        selection: ModelSelection = ModelSelection.PRIMARY,
        skill_ids: list[str] | None = None,
        task_class: TaskClass | None = None,
    ) -> Agent:
        actor_id = actor_id_for(spec.role)
        actor_context = CrewAIToolContext(
            run_id=context.run_id,
            stage_id=context.stage_id,
            task_id=context.task_id,
            actor_id=actor_id,
            candidate_id=context.candidate_id,
            assumption_id=context.assumption_id,
        )
        return Agent(
            role=spec.role,
            goal=spec.goal,
            backstory=(
                "You operate inside DBIE. Cite provenance, distinguish unknowns, "
                "and never treat model agreement as market evidence."
            ),
            llm=self.llm.for_execution(
                spec.model_role,
                ModelExecutionContext(
                    run_id=context.run_id,
                    crew_id=spec.group,
                    agent_id=actor_id,
                    task_id=context.task_id,
                    task_class=task_class or task_class_for_actor(spec),
                    skill_ids=skill_ids or [],
                ),
                selection=selection,
            ),
            tools=crewai_tools_for(self.gateway, actor_context, list(spec.tools)),
            allow_delegation=False,
            allow_code_execution=False,
            max_iter=8,
            verbose=False,
        )


def exploration_allocation(total: int, fraction: float = 0.20) -> tuple[int, int]:
    if not 0.15 <= fraction <= 0.25:
        raise ValueError("exploration fraction must be between 15% and 25%")
    exploration = round(total * fraction)
    return total - exploration, exploration


def actor_id_for(role: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", role)


def task_class_for_actor(spec: ActorSpec) -> TaskClass:
    by_role = {
        "Regulatory Scout": TaskClass.REGULATORY_RESEARCH,
        "Technology Scout": TaskClass.GITHUB_RESEARCH,
        "Industry Analyst": TaskClass.COMPETITOR_RESEARCH,
        "Regulatory Validator": TaskClass.REGULATORY_RESEARCH,
        "Competitive Analyst": TaskClass.COMPETITOR_RESEARCH,
        "Opportunity Synthesizer": TaskClass.OPPORTUNITY_SYNTHESIS,
        "Assumption Decomposer": TaskClass.ASSUMPTION_DECOMPOSITION,
        "Research Planner": TaskClass.RESEARCH_PLANNING,
        "Evidence Reconciler": TaskClass.EVIDENCE_RECONCILIATION,
        "Experiment Designer": TaskClass.EXPERIMENT_DESIGN,
        "Portfolio Reasoner": TaskClass.EVIDENCE_RECONCILIATION,
        "Portfolio Judge": TaskClass.INDEPENDENT_RED_TEAM,
        "MVP Implementer": TaskClass.MVP_IMPLEMENTATION,
        "Test Repair Agent": TaskClass.TEST_FIX_LOOP,
        "Integration Agent": TaskClass.MVP_IMPLEMENTATION,
    }
    if spec.group == "ideation":
        return TaskClass.DISCOVERY_IDEATION
    if spec.role in by_role:
        return by_role[spec.role]
    if spec.group == "red_team":
        return TaskClass.INDEPENDENT_RED_TEAM
    return TaskClass.MARKET_EVIDENCE


def task_class_for_request(request: object) -> TaskClass:
    """Resolve stage-specific classes where the same actor does different work."""
    task_id = str(getattr(request, "task_id", ""))
    if task_id == "portfolio-tournament":
        return TaskClass.JUDGE_INVESTMENT_DECISION
    if task_id in {"observed-outcome-decision", "run-conclusion"}:
        return TaskClass.INVESTMENT_DECISION
    if task_id == "dossier-synthesis":
        return TaskClass.OPPORTUNITY_SYNTHESIS
    if task_id == "business-model-comparison":
        return TaskClass.FINANCIAL_ANALYSIS
    if task_id == "evidence-reconciliation":
        return TaskClass.ASSUMPTION_VALIDATION
    return task_class_for_actor(getattr(request, "spec"))


def deduplicate_idea_theses(theses: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for thesis in theses:
        key = " ".join(thesis.casefold().split())
        if key not in seen:
            seen.add(key)
            result.append(thesis)
    return result
