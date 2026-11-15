"""Offline historical opportunity benchmark and forecast error reports."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dbie.domain.models import (
    CommercialForecastMetrics,
    ExperimentOutcome,
    ExperimentPrediction,
    ForecastIntervals,
)
from dbie.domain.enums import DecisionType

FORECAST_METRIC_FIELDS = {
    "demand", "conversion_rate", "revenue", "cac", "gross_margin",
    "contribution_margin", "implementation_cost", "time_to_launch_months",
    "time_to_first_revenue_months",
}


class HistoricalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str
    available_at: datetime
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def timestamp_has_timezone(self) -> HistoricalEvidence:
        if self.available_at.utcoffset() is None:
            raise ValueError("historical evidence timestamp must include a timezone")
        return self


class HistoricalOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str = Field(min_length=1)
    description: str = Field(min_length=10)
    decision_date: datetime
    evidence: list[HistoricalEvidence] = Field(default_factory=list)
    outcome_date: datetime
    commercially_successful: bool | None
    outcome_provenance: list[str] = Field(min_length=1)
    dbie_recommendation: DecisionType
    dbie_score: float
    dbie_rank: int = Field(gt=0)
    baseline_recommendation: DecisionType = DecisionType.MORE_EVIDENCE
    baseline_score: float = 0

    @model_validator(mode="after")
    def outcomes_follow_decision(self) -> HistoricalOpportunity:
        if self.outcome_date.utcoffset() is None or self.decision_date.utcoffset() is None:
            raise ValueError("historical decision and outcome dates must include a timezone")
        if self.outcome_date <= self.decision_date:
            raise ValueError("outcome_date must follow historical decision_date")
        return self

    def evidence_at_cutoff(self) -> list[HistoricalEvidence]:
        return [item for item in self.evidence if item.available_at <= self.decision_date]


class HistoricalBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    benchmark_id: str
    opportunities: list[HistoricalOpportunity]

    @model_validator(mode="after")
    def unique_opportunity_ids(self) -> HistoricalBenchmark:
        identifiers = [item.opportunity_id for item in self.opportunities]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("historical opportunity IDs must be unique")
        return self


class ForecastEvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    opportunity_id: str
    experiment_id: str | None = None
    prediction_id: str | None = None
    outcome_id: str | None = None
    recommendation: DecisionType
    commercially_successful: bool | None = None
    predicted_metrics: CommercialForecastMetrics
    scenario_intervals: ForecastIntervals = Field(default_factory=ForecastIntervals)
    observed_metrics: CommercialForecastMetrics
    measured_at: datetime
    evidence_source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_measured_record(self) -> ForecastEvaluationInput:
        if self.measured_at.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        if self.predicted_metrics.model_dump(exclude={"currency", "period_months"}, exclude_none=True) == {}:
            raise ValueError("at least one predicted metric is required")
        if self.observed_metrics.model_dump(exclude={"currency", "period_months"}, exclude_none=True) == {}:
            raise ValueError("at least one observed metric is required")
        if (self.predicted_metrics.currency, self.predicted_metrics.period_months) != (
            self.observed_metrics.currency, self.observed_metrics.period_months
        ):
            raise ValueError("prediction and outcome currency/period units must match")
        return self


def _dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(index + 2) for index, rel in enumerate(relevances))


def evaluate_historical_benchmark(benchmark: HistoricalBenchmark, k: int = 5) -> dict[str, Any]:
    if k < 1:
        raise ValueError("k must be positive")
    opportunities = benchmark.opportunities
    labeled = [item for item in opportunities if item.commercially_successful is not None]
    ranked_labeled = sorted(labeled, key=lambda x: (-x.dbie_score, x.dbie_rank, x.opportunity_id))
    top = ranked_labeled[:k]
    successes = sum(item.commercially_successful is True for item in labeled)
    hits = sum(item.commercially_successful is True for item in top)
    precision = hits / len(top) if top else 0.0
    recall = hits / successes if successes else 0.0
    dcg = _dcg([int(item.commercially_successful is True) for item in top])
    ideal = _dcg([1] * min(successes, k))
    actual_predictions = [item.dbie_recommendation == "BUILD" for item in labeled]
    actual = [item.commercially_successful is True for item in labeled]
    tp = sum(p and a for p, a in zip(actual_predictions, actual, strict=True))
    tn = sum(not p and not a for p, a in zip(actual_predictions, actual, strict=True))
    fp = sum(p and not a for p, a in zip(actual_predictions, actual, strict=True))
    fn = sum(not p and a for p, a in zip(actual_predictions, actual, strict=True))
    calibration = [item for item in labeled if 0 <= item.dbie_score <= 1]
    brier = (sum((item.dbie_score - int(item.commercially_successful is True)) ** 2 for item in calibration) / len(calibration)) if calibration else None
    coverage = sum(bool(item.evidence_at_cutoff()) for item in opportunities) / len(opportunities) if opportunities else 0.0
    confidence_pairs = [(sum(ev.confidence for ev in item.evidence_at_cutoff()) / len(item.evidence_at_cutoff()), int(item.commercially_successful is True)) for item in labeled if item.evidence_at_cutoff()]
    confidence_brier = sum((confidence - outcome) ** 2 for confidence, outcome in confidence_pairs) / len(confidence_pairs) if confidence_pairs else None
    baseline_tp = sum(item.baseline_recommendation == "BUILD" and item.commercially_successful is True for item in opportunities)
    baseline_fp = sum(item.baseline_recommendation == "BUILD" and item.commercially_successful is False for item in opportunities)
    baseline_labeled = [item for item in opportunities if item.commercially_successful is not None]
    baseline_ranked = sorted(labeled, key=lambda x: (-x.baseline_score, x.opportunity_id))
    baseline_top = [item for item in baseline_ranked[:k] if item.commercially_successful is not None]
    baseline_hits = sum(item.commercially_successful is True for item in baseline_top)
    baseline_ndcg = _dcg([int(item.commercially_successful is True) for item in baseline_ranked[:k]]) / ideal if ideal else 0.0
    baseline_correct = sum((item.baseline_recommendation == "BUILD") == item.commercially_successful for item in baseline_labeled)
    return {
        "benchmark_id": benchmark.benchmark_id,
        "format_version": benchmark.format_version,
        "k": k,
        "opportunity_count": len(opportunities),
        "labeled_opportunity_count": len(labeled),
        "precision_at_k": precision,
        "labeled_at_k": len(top),
        "recall_at_k": recall,
        "ndcg_at_k": dcg / ideal if ideal else 0.0,
        "decision_accuracy": (tp + tn) / len(labeled) if labeled else 0.0,
        "confusion_matrix": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
        "false_positive_investments": fp,
        "missed_successful_opportunities": fn,
        "baseline_build_precision": baseline_tp / (baseline_tp + baseline_fp) if baseline_tp + baseline_fp else 0.0,
        "baseline_precision_at_k": baseline_hits / len(baseline_top) if baseline_top else 0.0,
        "baseline_ndcg_at_k": baseline_ndcg,
        "baseline_decision_accuracy": baseline_correct / len(baseline_labeled) if baseline_labeled else 0.0,
        "evidence_cutoff_coverage": coverage,
        "score_brier": brier,
        "evidence_confidence_brier": confidence_brier,
        "excluded_future_evidence_count": sum(len(item.evidence) - len(item.evidence_at_cutoff()) for item in opportunities),
    }


def benchmark_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        f"# Commercial opportunity benchmark: {metrics['benchmark_id']}", "",
        f"Format version: {metrics['format_version']}",
        f"Opportunities: {metrics['opportunity_count']} ({metrics['labeled_opportunity_count']} labeled)",
        f"Precision@{metrics['k']}: {metrics['precision_at_k']:.3f} on {metrics['labeled_at_k']} labeled top-ranked cases",
        f"Recall@{metrics['k']}: {metrics['recall_at_k']:.3f}",
        f"NDCG@{metrics['k']}: {metrics['ndcg_at_k']:.3f}",
        f"Decision accuracy: {metrics['decision_accuracy']:.3f}",
        f"False-positive investments: {metrics['false_positive_investments']}",
        f"Missed successful opportunities: {metrics['missed_successful_opportunities']}",
        f"Historical evidence coverage: {metrics['evidence_cutoff_coverage']:.3f}",
        f"Score Brier: {metrics['score_brier']}",
        f"Evidence-confidence Brier: {metrics['evidence_confidence_brier']}",
        f"Excluded post-decision evidence: {metrics['excluded_future_evidence_count']}",
        "", "## Comparison baseline", "",
        f"Baseline precision@{metrics['k']}: {metrics['baseline_precision_at_k']:.3f}",
        f"Baseline NDCG@{metrics['k']}: {metrics['baseline_ndcg_at_k']:.3f}",
        f"Baseline decision accuracy: {metrics['baseline_decision_accuracy']:.3f}",
        f"Baseline BUILD precision: {metrics['baseline_build_precision']:.3f}",
        "", "## Confusion matrix", "", "```json",
        json.dumps(metrics["confusion_matrix"], indent=2, sort_keys=True), "```", "",
    ]
    return "\n".join(lines)


def load_historical_benchmark(path: Path) -> HistoricalBenchmark:
    return HistoricalBenchmark.model_validate_json(path.read_text(encoding="utf-8"))


def write_historical_report(metrics: dict[str, Any], directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path, md_path = directory / "commercial_benchmark.json", directory / "commercial_benchmark.md"
    json_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(benchmark_markdown(metrics), encoding="utf-8")
    return json_path, md_path


def evaluate_forecast(
    predicted: dict[str, float],
    observed: dict[str, float],
    intervals: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Compute deterministic point errors for matching numeric forecast fields."""
    errors: dict[str, dict[str, float | None]] = {}
    for key in sorted(observed):
        actual = observed[key]
        forecast = predicted.get(key)
        if forecast is None:
            continue
        absolute = abs(forecast - actual)
        errors[key] = {"absolute_error": absolute, "percentage_error": absolute / abs(actual) if actual else None, "signed_error": forecast - actual}
    covered = [key for key, interval in (intervals or {}).items() if key in observed and interval.get("lower", float("inf")) <= observed[key] <= interval.get("upper", float("-inf"))]
    defined = [key for key in (intervals or {}) if key in observed]
    return {
        "errors": errors,
        "interval_outcomes": {key: key in covered for key in defined},
        "interval_coverage": len(covered) / len(defined) if defined else None,
        "intervals_evaluated": len(defined),
    }


def evaluate_prediction_outcome(
    prediction: ExperimentPrediction, outcome: ExperimentOutcome,
) -> dict[str, Any]:
    """Compare immutable prediction and measured outcome in matching units."""
    predicted_metrics = prediction.predicted_metrics
    observed_metrics = outcome.observed_metrics
    if (predicted_metrics.currency, predicted_metrics.period_months) != (
        observed_metrics.currency, observed_metrics.period_months
    ):
        raise ValueError("prediction and outcome currency/period units must match")
    metric_names = sorted(FORECAST_METRIC_FIELDS)
    predicted = {name: getattr(predicted_metrics, name) for name in metric_names if getattr(predicted_metrics, name) is not None}
    observed = {name: getattr(observed_metrics, name) for name in metric_names if getattr(observed_metrics, name) is not None}
    intervals = {
        name: getattr(prediction.scenario_intervals, name).model_dump()
        for name in metric_names
        if getattr(prediction.scenario_intervals, name) is not None
    }
    return {
        **evaluate_forecast(predicted, observed, intervals),
        "measured_at": outcome.measured_at.isoformat() if outcome.measured_at else None,
        "evidence_source_ids": outcome.evidence_source_ids,
        "prediction_id": prediction.id,
        "outcome_id": outcome.id,
    }


def aggregate_forecasts(records: list[dict[str, Any]], group_by: str = "run_id") -> dict[str, dict[str, Any]]:
    """Aggregate prediction/observation rows by run, opportunity, or portfolio."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        key = "portfolio" if group_by == "portfolio" else str(row.get(group_by, "unknown"))
        grouped.setdefault(key, []).append(row)
    reports = {}
    for key, rows in grouped.items():
        forecasts = []
        units: set[tuple[str, int]] = set()
        for row in rows:
            predicted_unit = row.get("predicted_metrics", {})
            observed_unit = row.get("observed_metrics", {})
            unit = (
                str(predicted_unit.get("currency", "USD")),
                int(predicted_unit.get("period_months", 1)),
            )
            observed_unit_value = (
                str(observed_unit.get("currency", unit[0])),
                int(observed_unit.get("period_months", unit[1])),
            )
            if unit != observed_unit_value:
                raise ValueError("prediction and outcome currency/period units must match")
            units.add(unit)
            predicted = {name: value for name, value in row.get("predicted_metrics", {}).items() if name in FORECAST_METRIC_FIELDS and isinstance(value, (float, int))}
            observed = {name: value for name, value in row.get("observed_metrics", {}).items() if name in FORECAST_METRIC_FIELDS and isinstance(value, (float, int))}
            intervals = {name: value for name, value in row.get("scenario_intervals", {}).items() if name in FORECAST_METRIC_FIELDS and isinstance(value, dict)}
            forecasts.append(evaluate_forecast(predicted, observed, intervals))
        if len(units) > 1:
            raise ValueError("aggregate forecast rows must use one currency and period")
        errors_by_metric: dict[str, list[dict[str, float | None]]] = {}
        for report in forecasts:
            for metric, error in report["errors"].items():
                errors_by_metric.setdefault(metric, []).append(error)
        metric_errors = {
            metric: {
                "count": len(errors),
                "mean_absolute_error": sum(item["absolute_error"] for item in errors) / len(errors),
                "mean_percentage_error": (
                    sum(item["percentage_error"] for item in errors if item["percentage_error"] is not None)
                    / sum(item["percentage_error"] is not None for item in errors)
                    if any(item["percentage_error"] is not None for item in errors) else None
                ),
                "forecast_bias": sum(item["signed_error"] for item in errors) / len(errors),
                "interval_coverage": (
                    sum(report["interval_outcomes"][metric] for report in forecasts if metric in report["interval_outcomes"])
                    / sum(metric in report["interval_outcomes"] for report in forecasts)
                    if any(metric in report["interval_outcomes"] for report in forecasts) else None
                ),
            }
            for metric, errors in sorted(errors_by_metric.items())
        }
        interval_counts = sum(report["intervals_evaluated"] for report in forecasts)
        covered_count = sum((report["interval_coverage"] or 0) * report["intervals_evaluated"] for report in forecasts)
        reports[key] = {
            "observation_count": len(rows),
            "currency": next(iter(units))[0] if units else None,
            "period_months": next(iter(units))[1] if units else None,
            "metric_count": sum(len(errors) for errors in errors_by_metric.values()),
            "errors_by_metric": metric_errors,
            "interval_coverage": covered_count / interval_counts if interval_counts else None,
        }
    return reports


def decision_outcomes(records: list[dict[str, Any]]) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, list[bool]] = {}
    for record in records:
        category = str(record.get("recommendation", "UNKNOWN"))
        outcome = record.get("commercially_successful")
        if outcome is not None:
            grouped.setdefault(category, []).append(bool(outcome))
    return {
        category: {
            "observed": len(outcomes),
            "successful": sum(outcomes),
            "success_rate": sum(outcomes) / len(outcomes),
        }
        for category, outcomes in grouped.items()
    }


def write_forecast_report(
    records: list[dict[str, Any]], directory: Path,
) -> tuple[Path, Path]:
    validated_records = [ForecastEvaluationInput.model_validate(row) for row in records]
    records = [item.model_dump(mode="json", exclude_none=True) for item in validated_records]
    observations = []
    for item in validated_records:
        predicted = {
            name: value for name, value in item.predicted_metrics.model_dump(exclude_none=True).items()
            if name in FORECAST_METRIC_FIELDS
        }
        observed = {
            name: value for name, value in item.observed_metrics.model_dump(exclude_none=True).items()
            if name in FORECAST_METRIC_FIELDS
        }
        intervals = {
            name: value.model_dump()
            for name, value in item.scenario_intervals
            if value is not None and name in FORECAST_METRIC_FIELDS
        }
        observations.append({
            "run_id": item.run_id,
            "opportunity_id": item.opportunity_id,
            "experiment_id": item.experiment_id,
            "prediction_id": item.prediction_id,
            "outcome_id": item.outcome_id,
            "recommendation": item.recommendation.value,
            "commercially_successful": item.commercially_successful,
            "measured_at": item.measured_at.isoformat(),
            "evidence_source_ids": item.evidence_source_ids,
            "evaluation": evaluate_forecast(predicted, observed, intervals),
        })
    report = {
        "format_version": "1.0",
        "observations": observations,
        "grouped_by_run": aggregate_forecasts(records, "run_id"),
        "grouped_by_opportunity": aggregate_forecasts(records, "opportunity_id"),
        "portfolio": aggregate_forecasts(records, "portfolio"),
        "decision_outcomes": decision_outcomes(records),
    }
    directory.mkdir(parents=True, exist_ok=True)
    json_path, md_path = directory / "forecast_report.json", directory / "forecast_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Commercial forecast versus outcome report", ""]
    for section, key in (
        ("Observation provenance", "observations"),
        ("By run", "grouped_by_run"),
        ("By opportunity", "grouped_by_opportunity"),
        ("Portfolio", "portfolio"),
        ("Decision outcomes", "decision_outcomes"),
    ):
        lines.extend([f"## {section}", "", "```json", json.dumps(report[key], indent=2, sort_keys=True), "```", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
