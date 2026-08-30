"""Phase 12 reproducible Markdown dossier rendering."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dbie.domain.enums import DecisionType


class EvidenceReference(BaseModel):
    title: str
    summary: str
    url: str | None = None
    publisher: str | None = None
    tier: str | None = None


class AssumptionSummary(BaseModel):
    statement: str
    status: str
    evidence_for: list[EvidenceReference] = Field(default_factory=list)
    evidence_against: list[EvidenceReference] = Field(default_factory=list)
    independent_lineages: int = 0


class Dossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    candidate_id: str
    title: str
    thesis: str
    description: str
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

    @field_validator("description")
    @classmethod
    def description_has_at_least_100_words(cls, value: str) -> str:
        if len(re.findall(r"\b[\w'-]+\b", value)) < 100:
            raise ValueError("opportunity description must contain at least 100 words")
        return value


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
        "## Opportunity description",
        "",
        dossier.description,
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
                "Supporting evidence:",
                "",
            ]
        )
        if item.evidence_for:
            for evidence in item.evidence_for:
                title = (
                    f"[{evidence.title}]({evidence.url})"
                    if evidence.url
                    else f"**{evidence.title}**"
                )
                lines.append(f"- {title} — {evidence.summary}")
        else:
            lines.append("- None recorded")
        lines.extend(["", "Contradicting evidence:", ""])
        if item.evidence_against:
            for evidence in item.evidence_against:
                title = (
                    f"[{evidence.title}]({evidence.url})"
                    if evidence.url
                    else f"**{evidence.title}**"
                )
                lines.append(f"- {title} — {evidence.summary}")
        else:
            lines.append("- None recorded")
        lines.append("")
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
    gross_margin = dossier.economics.get("gross_margin_base")
    gross_margin_text = (
        f"{gross_margin:.0%}" if isinstance(gross_margin, (int, float)) else "Unknown"
    )
    rank = dossier.ranking.get("rank")
    portfolio_size = dossier.ranking.get("portfolio_size")
    match_count = dossier.ranking.get("match_count", 0)
    stability = dossier.ranking.get("stability")
    stability_text = (
        f"{stability:.0%}" if isinstance(stability, (int, float)) else "Unknown"
    )
    lines.extend(
        [
            "## Economics",
            "",
            f"- Expected base gross margin: **{gross_margin_text}**",
            "",
            "## Automation and marginal human burden",
            "",
            f"Automation ratio: {dossier.automation_ratio}",
            "",
            f"Human minutes/customer at 10x: {dossier.human_minutes_per_customer_at_10x}",
            "",
            "## Portfolio position",
            "",
            f"- Rank: **#{rank} of {portfolio_size or 'the finalist portfolio'}**",
            f"- Pairwise comparisons completed: **{match_count}**",
            f"- Ranking stability: **{stability_text}**",
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
