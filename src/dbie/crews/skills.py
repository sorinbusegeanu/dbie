"""Versioned, concise procedural skills injected into CrewAI task context."""

from dataclasses import dataclass
from pathlib import Path

from dbie.models.task_roles import TaskClass


@dataclass(frozen=True)
class AgentSkill:
    skill_id: str
    version: str
    tasks: frozenset[TaskClass]
    instructions: str

    @property
    def identifier(self) -> str:
        return f"{self.skill_id}@{self.version}"


_SKILL_FILES: dict[str, tuple[frozenset[TaskClass], str]] = {
    "opportunity-discovery": (frozenset({TaskClass.DISCOVERY_IDEATION}), "opportunity_discovery.md"),
    "demand-validation": (frozenset({TaskClass.MARKET_EVIDENCE, TaskClass.ASSUMPTION_VALIDATION}), "demand_validation.md"),
    "competitive-analysis": (frozenset({TaskClass.COMPETITOR_RESEARCH}), "competitive_analysis.md"),
    "financial-modeling": (frozenset({TaskClass.FINANCIAL_ANALYSIS}), "financial_modeling.md"),
    "evidence-assessment": (frozenset({TaskClass.EVIDENCE_EXTRACTION, TaskClass.EVIDENCE_RECONCILIATION, TaskClass.REGULATORY_RESEARCH, TaskClass.GITHUB_RESEARCH}), "evidence_assessment.md"),
    "adversarial-review": (frozenset({TaskClass.INDEPENDENT_RED_TEAM, TaskClass.PRODUCTIZATION_CHALLENGE}), "adversarial_review.md"),
    "investment-decision": (frozenset({TaskClass.INVESTMENT_DECISION, TaskClass.JUDGE_INVESTMENT_DECISION, TaskClass.OPPORTUNITY_SYNTHESIS}), "investment_decision.md"),
}


def skills_for_task(task_class: TaskClass, root: Path | None = None) -> list[AgentSkill]:
    directory = root or Path(__file__).resolve().parents[1] / "skills"
    skills = []
    for skill_id, (tasks, filename) in _SKILL_FILES.items():
        if task_class not in tasks:
            continue
        path = directory / filename
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        version = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("version:")), "1")
        skills.append(AgentSkill(skill_id, version, tasks, text))
    return skills
