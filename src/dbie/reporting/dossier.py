"""Phase 12 reproducible Markdown dossier rendering."""

from __future__ import annotations

import re
import json
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
    economics: dict[str, object] = Field(default_factory=dict)
    readiness: dict[str, object] = Field(default_factory=dict)
    opportunity_investment_thesis: str | None = None
    addressable_market: dict[str, object] = Field(default_factory=dict)
    reachable_market: dict[str, object] = Field(default_factory=dict)
    willingness_to_pay_evidence: list[str] = Field(default_factory=list)
    commercial_evidence_grades: list[dict[str, object]] = Field(default_factory=list)
    critical_assumptions: list[dict[str, object]] = Field(default_factory=list)
    recommended_experiment: dict[str, object] = Field(default_factory=dict)
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
    scenario_map = dossier.economics.get("scenarios", {})
    base_scenario = scenario_map.get("base", {}) if isinstance(scenario_map, dict) else {}
    if not isinstance(base_scenario, dict):
        base_scenario = {}
    def commercial_value(key: str) -> str:
        value = base_scenario.get(key)
        if value is None:
            return "Unknown"
        return json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)

    input_assumptions = dossier.economics.get("assumptions", {})

    def operating_cost_input(name: str) -> str:
        item = input_assumptions.get(name, {}) if isinstance(input_assumptions, dict) else {}
        if not isinstance(item, dict):
            return "Unknown"
        value = "Unknown" if item.get("value") is None else str(item["value"])
        basis = item.get("basis", "UNKNOWN")
        if name == "fixed_cost_per_month":
            unit = f"{dossier.economics.get('currency', 'Unknown')}/month"
        else:
            unit = f"{dossier.economics.get('currency', 'Unknown')}/customer/month"
        return f"{value} {unit} ({basis})"

    lines = [
        f"# {dossier.title}",
        "",
        "## Executive decision summary",
        "",
        f"**Investment thesis:** {dossier.opportunity_investment_thesis or dossier.thesis}",
        f"**Recommendation:** {dossier.decision.value} ({', '.join(dossier.reason_codes) or 'no reason codes'})",
        f"**Target customer / economic buyer:** {dossier.customer} / {dossier.buyer or 'Unknown'}",
        f"**Evidence confidence / coverage:** {dossier.readiness.get('evidence_confidence', 'Unknown')} / {dossier.readiness.get('evidence_coverage', 'Unknown')}",
        f"**Readiness recommendation:** {dossier.readiness.get('recommendation', 'Unknown')}",
        f"**Deterministic readiness score:** {dossier.readiness.get('readiness_score', 'Unknown')} / 10",
        f"**Scenario uncertainty:** {dossier.readiness.get('scenario_uncertainty') if dossier.readiness.get('scenario_uncertainty') is not None else 'Unknown'}",
        f"**Pipeline finalist gate:** {dossier.readiness.get('pipeline_validation_decision', 'Unknown')}",
        f"**Readiness reasons:** {', '.join(dossier.readiness.get('reason_codes', [])) or 'None recorded'}",
        f"**Principal uncertainties:** {', '.join(dossier.unknowns) or 'None recorded'}",
        f"**Addressable market:** {json.dumps(dossier.addressable_market, sort_keys=True) if dossier.addressable_market else 'Unknown'}",
        f"**Realistically reachable market:** {json.dumps(dossier.reachable_market, sort_keys=True) if dossier.reachable_market else 'Unknown'}",
        f"**Willingness-to-pay evidence:** {', '.join(dossier.willingness_to_pay_evidence) or 'Unknown'}",
        f"**Revenue scenarios:** currency={dossier.economics.get('currency', 'Unknown')}; period={dossier.economics.get('period_months', 'Unknown')} months",
        f"**Base case CAC / LTV:** {commercial_value('cac')} / {commercial_value('ltv')} {dossier.economics.get('currency', '')}",
        f"**Base case gross / contribution margin:** {commercial_value('gross_margin')} / {commercial_value('contribution_margin')}",
        f"**Base case break-even customers / revenue:** {commercial_value('break_even_customers')} / {commercial_value('break_even_revenue')} {dossier.economics.get('currency', '')}",
        f"**Initial investment / payback:** {commercial_value('initial_investment')} / {commercial_value('payback_months')} months",
        f"**Time to first revenue:** {commercial_value('first_revenue_month')} months",
        f"**Expected operating costs:** fixed={operating_cost_input('fixed_cost_per_month')}; variable={operating_cost_input('variable_cost_per_customer')}",
        f"**Readiness blockers:** {', '.join(dossier.readiness.get('blockers', [])) or 'None'}",
        f"**Automation ratio / human minutes per customer at 10x:** {dossier.automation_ratio} / {dossier.human_minutes_per_customer_at_10x}",
        f"**Recommended next experiment:** {json.dumps(dossier.recommended_experiment, sort_keys=True) if dossier.recommended_experiment else (dossier.recommended_experiments[0] if dossier.recommended_experiments else 'None recorded')}",
        "",
        "Financial inputs retain observed, assumed, estimated, or unknown basis, ranges, notes, and evidence IDs below and in the JSON dossier.",
        "",
        "| Scenario | Revenue | CAC | LTV | Gross margin | Contribution margin | Break-even customers | Break-even revenue | Investment | Payback months | First revenue month |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if scenario_map:
        fields = ["revenue", "cac", "ltv", "gross_margin", "contribution_margin", "break_even_customers", "break_even_revenue", "initial_investment", "payback_months", "first_revenue_month"]
        for name in ("pessimistic", "base", "optimistic"):
            scenario = scenario_map.get(name)
            if isinstance(scenario, dict):
                values = ["Unknown" if scenario.get(key) is None else str(scenario[key]) for key in fields]
                lines.append(f"| {name.title()} | " + " | ".join(values) + " |")
    else:
        lines.append("| Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |")
    if dossier.critical_assumptions:
        lines.extend(["", "### Critical assumptions", ""])
        for item in dossier.critical_assumptions:
            lines.append(f"- {item.get('statement', 'Assumption')} — status `{item.get('status', 'UNKNOWN')}`, evidence for {item.get('evidence_for_ids', [])}, evidence against {item.get('evidence_against_ids', [])}.")
    if dossier.commercial_evidence_grades:
        lines.extend(["", "### Commercial evidence grades", ""])
        for item in dossier.commercial_evidence_grades:
            lines.append(
                f"- Assumption `{item.get('assumption_id')}`: support `{item.get('supporting_grade')}`, "
                f"contradiction `{item.get('contradicting_grade')}`, product support `{item.get('product_supporting_grade')}`, "
                f"independent sources {item.get('independent_sources')}, confidence {item.get('supporting_confidence')}, "
                f"evidence IDs {item.get('evidence_ids', [])}."
            )
    financial_assumptions = dossier.economics.get("assumptions")
    if isinstance(financial_assumptions, dict):
        lines.extend([
            "", "### Financial assumptions and provenance", "",
            f"Currency: `{financial_assumptions.get('currency', dossier.economics.get('currency', 'Unknown'))}`; projection period: `{financial_assumptions.get('period_months', dossier.economics.get('period_months', 'Unknown'))}` months.",
            "", "| Input | Value | Basis | Range | Evidence IDs | Assumption note | Unknown reason |",
            "|---|---:|---|---|---|---|---|",
        ])
        for name, item in sorted(financial_assumptions.items()):
            if name in {"currency", "period_months"} or not isinstance(item, dict):
                continue
            value = "Unknown" if item.get("value") is None else str(item["value"])
            bounds = [item.get("lower"), item.get("upper")]
            range_text = "Unknown" if all(value is None for value in bounds) else f"{bounds[0] if bounds[0] is not None else '—'} to {bounds[1] if bounds[1] is not None else '—'}"
            references = ", ".join(item.get("evidence_ids", [])) or "None"
            reason = item.get("reason_unknown") or "—"
            lines.append(f"| {name} | {value} | {item.get('basis', 'UNKNOWN')} | {range_text} | {references} | {item.get('note') or '—'} | {reason} |")
    lines.extend([
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
    ])
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
