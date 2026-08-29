"""Phase 12 reproducible Markdown dossier rendering."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dbie.domain.enums import DecisionType


class AssumptionSummary(BaseModel):
    statement: str
    status: str
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    independent_lineages: int = 0


class Dossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    candidate_id: str
    title: str
    thesis: str
    why_now: str | None = None
    customer: str
    buyer: str | None = None
    assumptions: list[AssumptionSummary]
    unknowns: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    business_model_variants: list[str] = Field(default_factory=list)
    economics: dict[str, str | float] = Field(default_factory=dict)
    automation_ratio: float | None = None
    human_minutes_per_customer_at_10x: float | None = None
    red_team_findings: list[str] = Field(default_factory=list)
    ranking: dict[str, str | float | int] = Field(default_factory=dict)
    recommended_experiments: list[str] = Field(default_factory=list)
    decision: DecisionType
    reason_codes: list[str]


def render_dossier(dossier: Dossier) -> str:
    lines = [
        f"# {dossier.title}",
        "",
        f"- Run: `{dossier.run_id}`",
        f"- Candidate: `{dossier.candidate_id}`",
        f"- Decision: **{dossier.decision.value}**",
        f"- Customer: {dossier.customer}",
        f"- Buyer: {dossier.buyer or 'Unknown'}",
        "",
        "## Thesis",
        "",
        dossier.thesis,
        "",
        "## Why now",
        "",
        dossier.why_now or "Unknown",
        "",
        "## Assumption map and evidence",
        "",
    ]
    for item in dossier.assumptions:
        lines.extend(
            [
                f"### {item.statement}",
                "",
                f"Status: `{item.status}`; independent lineages: {item.independent_lineages}",
                "",
                "Supports: " + (", ".join(item.evidence_for) or "None"),
                "",
                "Contradicts: " + (", ".join(item.evidence_against) or "None"),
                "",
            ]
        )
    sections = {
        "Unknowns": dossier.unknowns,
        "Competitors": dossier.competitors,
        "Business model variants": dossier.business_model_variants,
        "Red-team findings": dossier.red_team_findings,
        "Recommended next experiments": dossier.recommended_experiments,
        "Reason codes": dossier.reason_codes,
    }
    for heading, values in sections.items():
        lines.extend([f"## {heading}", ""])
        lines.extend([f"- {value}" for value in values] or ["- None"])
        lines.append("")
    lines.extend(
        [
            "## Deterministic economics",
            "",
            "```json",
            json.dumps(dossier.economics, indent=2, sort_keys=True),
            "```",
            "",
            "## Automation and marginal human burden",
            "",
            f"Automation ratio: {dossier.automation_ratio}",
            "",
            f"Human minutes/customer at 10x: {dossier.human_minutes_per_customer_at_10x}",
            "",
            "## Ranking",
            "",
            "```json",
            json.dumps(dossier.ranking, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_dossier(dossier: Dossier, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    markdown_path = directory / f"{dossier.candidate_id}.md"
    state_path = directory / f"{dossier.candidate_id}.json"
    markdown_path.write_text(render_dossier(dossier), encoding="utf-8")
    state_path.write_text(dossier.model_dump_json(indent=2), encoding="utf-8")
    return markdown_path, state_path
