import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dbie.evaluation.commercial_benchmark import (
    HistoricalBenchmark,
    evaluate_forecast,
    evaluate_historical_benchmark,
    evaluate_prediction_outcome,
    load_historical_benchmark,
    write_historical_report,
)
from dbie.domain.models import ExperimentOutcome, ExperimentPrediction
from pydantic import ValidationError


def test_synthetic_historical_benchmark_is_cutoff_safe_and_reports_metrics(tmp_path):
    source = Path("benchmarks/commercial_opportunities_synthetic.json")
    benchmark = load_historical_benchmark(source)
    metrics = evaluate_historical_benchmark(benchmark, k=2)
    assert metrics["excluded_future_evidence_count"] == 1
    assert metrics["false_positive_investments"] == 0
    assert metrics["missed_successful_opportunities"] == 0
    assert metrics["labeled_opportunity_count"] == 3
    json_path, md_path = write_historical_report(metrics, tmp_path)
    assert json.loads(json_path.read_text())["ndcg_at_k"] == metrics["ndcg_at_k"]
    assert "Precision@2" in md_path.read_text()


def test_forecast_error_and_interval_coverage_are_defined_only_when_valid():
    report = evaluate_forecast(
        {"revenue": 90, "cac": 20},
        {"revenue": 100, "cac": 0},
        {"revenue": {"lower": 80, "upper": 110}},
    )
    assert report["errors"]["revenue"]["absolute_error"] == 10
    assert report["errors"]["revenue"]["percentage_error"] == 0.1
    assert report["errors"]["cac"]["percentage_error"] is None
    assert report["interval_coverage"] == 1


def test_benchmark_rejects_outcome_before_decision():
    payload = {
        "benchmark_id": "bad",
        "opportunities": [{
            "opportunity_id": "one", "description": "Synthetic opportunity case.", "decision_date": "2022-01-01T00:00:00Z",
            "outcome_date": "2021-01-01T00:00:00Z", "commercially_successful": False,
            "outcome_provenance": ["fixture"], "dbie_recommendation": "KILL", "dbie_score": 0, "dbie_rank": 1,
        }],
    }
    with pytest.raises(ValidationError, match="must follow"):
        HistoricalBenchmark.model_validate(payload)


def test_experiment_forecasts_are_structured_immutable_and_outcomes_provenanced():
    prediction = ExperimentPrediction(
        run_id="run", experiment_id="experiment", predicted_value="forecast",
        rationale="Preregistered before any outcome.",
        predicted_metrics={"revenue": 100},
        scenario_intervals={"revenue": {"lower": 80, "upper": 120}},
    )
    with pytest.raises(ValidationError):
        prediction.predicted_metrics.revenue = 120
    with pytest.raises(ValidationError, match="measured_at"):
        ExperimentOutcome(
            run_id="run", experiment_id="experiment", observed_value="observed",
            sample_size=1, interpretation="Measured result.", observed_metrics={"revenue": 90},
        )
    outcome = ExperimentOutcome(
        run_id="run", experiment_id="experiment", observed_value="observed",
        sample_size=1, interpretation="Measured result.", measured_at="2025-01-01T00:00:00Z",
        observed_metrics={"revenue": 90}, evidence_source_ids=["evidence"],
    )
    assert outcome.observed_metrics.revenue == 90
    comparison = evaluate_prediction_outcome(prediction, outcome)
    assert comparison["errors"]["revenue"]["absolute_error"] == 10
    assert comparison["interval_coverage"] == 1
