import json
from pathlib import Path

from dbie.evaluation.benchmark import (
    BenchmarkCase,
    ModelBenchmarkRunner,
    write_benchmark_report,
)
from dbie.models.base import GenerationResponse


class FakeRouter:
    def generate(self, request, *, profile_name, allow_fallback):
        content = (
            '{"tool":"fetch_page","extra":"preserved"}'
            if profile_name == "good"
            else "not-json"
        )
        return GenerationResponse(
            provider="fake",
            model=profile_name,
            content=content,
            latency_seconds=0.1,
        )


def test_benchmark_scores_expected_subset_and_invalid_json() -> None:
    runner = ModelBenchmarkRunner(FakeRouter())  # type: ignore[arg-type]
    case = BenchmarkCase(
        id="case",
        category="tool_selection",
        prompt="choose",
        expected={"tool": "fetch_page"},
    )

    report = runner.run([case], ["good", "bad"])

    assert report.score_by_profile() == {"good": 1.0, "bad": 0.0}
    assert report.results[1].error is not None


def test_benchmark_writes_machine_and_markdown_reports(tmp_path: Path) -> None:
    runner = ModelBenchmarkRunner(FakeRouter())  # type: ignore[arg-type]
    report = runner.run(
        [
            BenchmarkCase(
                id="case",
                category="tool_selection",
                prompt="choose",
                expected={"tool": "fetch_page"},
            )
        ],
        ["good"],
    )

    write_benchmark_report(report, tmp_path)

    assert (
        json.loads((tmp_path / "benchmark.json").read_text())["results"][0]["score"]
        == 1.0
    )
    assert "| good | 1.000 | 1 |" in (tmp_path / "benchmark.md").read_text()


def test_unknown_benchmark_category_fails_before_model_call() -> None:
    runner = ModelBenchmarkRunner(FakeRouter())  # type: ignore[arg-type]
    case = BenchmarkCase(
        id="bad",
        category="unknown",
        prompt="x",
        expected={"x": 1},
    )

    try:
        runner.run([case], ["good"])
    except ValueError as exc:
        assert "unknown benchmark category" in str(exc)
    else:
        raise AssertionError("unknown benchmark category was accepted")
