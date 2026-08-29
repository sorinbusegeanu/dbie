"""Uncertainty-aware deterministic portfolio metrics."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from dbie.domain.enums import EvidenceType


class MetricValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower: float = Field(ge=0, le=10)
    base: float = Field(ge=0, le=10)
    upper: float = Field(ge=0, le=10)
    evidence_type: EvidenceType


class PortfolioTriage(BaseModel):
    lower: float
    base: float
    upper: float
    coverage: float = Field(ge=0, le=1)


DEFAULT_WEIGHTS: dict[str, float] = {
    "problem_severity": 0.12,
    "willingness_to_pay": 0.12,
    "reachable_market": 0.09,
    "growth_why_now": 0.08,
    "digital_automation": 0.12,
    "gross_margin": 0.08,
    "distribution": 0.10,
    "differentiation": 0.07,
    "defensibility": 0.07,
    "technical_feasibility": 0.06,
    "capital_efficiency": 0.05,
    "low_human_burden": 0.04,
}


def calculate_triage(
    metrics: Mapping[str, MetricValue],
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
) -> PortfolioTriage:
    known = {name: value for name, value in metrics.items() if name in weights}
    covered_weight = sum(weights[name] for name in known)
    if covered_weight == 0:
        return PortfolioTriage(lower=0, base=0, upper=10, coverage=0)

    def weighted(field: str) -> float:
        return (
            sum(getattr(value, field) * weights[name] for name, value in known.items())
            / covered_weight
        )

    return PortfolioTriage(
        lower=weighted("lower"),
        base=weighted("base"),
        upper=weighted("upper"),
        coverage=covered_weight / sum(weights.values()),
    )
