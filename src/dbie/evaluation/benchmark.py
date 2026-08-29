"""DBIE-specific, provider-neutral model benchmark runner."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dbie.exceptions import ModelProviderError
from dbie.models.base import ChatMessage, GenerationRequest
from dbie.models.router import ModelRouter

BENCHMARK_CATEGORIES = {
    "tool_selection",
    "tool_arguments",
    "structured_output",
    "multi_step_recovery",
    "evidence_extraction",
    "unsupported_claim",
    "assumption_decomposition",
    "adversarial_critique",
    "pairwise_ranking",
    "runtime",
}


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    prompt: str
    expected: dict[str, object]
    weight: float = Field(default=1, gt=0)


class BenchmarkResult(BaseModel):
    case_id: str
    category: str
    profile: str
    score: float = Field(ge=0, le=1)
    latency_seconds: float = Field(ge=0)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None


class BenchmarkReport(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[BenchmarkResult]

    def score_by_profile(self) -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for result in self.results:
            grouped.setdefault(result.profile, []).append(result.score)
        return {
            profile: sum(scores) / len(scores) for profile, scores in grouped.items()
        }

    def to_markdown(self) -> str:
        lines = [
            "# DBIE Model Benchmark",
            "",
            "| Profile | Mean score | Cases |",
            "|---|---:|---:|",
        ]
        scores = self.score_by_profile()
        for profile in sorted(scores):
            count = sum(result.profile == profile for result in self.results)
            lines.append(f"| {profile} | {scores[profile]:.3f} | {count} |")
        lines.extend(
            [
                "",
                "## Case results",
                "",
                "| Profile | Case | Category | Score | Error |",
                "|---|---|---|---:|---|",
            ]
        )
        for result in self.results:
            lines.append(
                f"| {result.profile} | {result.case_id} | {result.category} | "
                f"{result.score:.3f} | {result.error or ''} |"
            )
        return "\n".join(lines) + "\n"


class ModelBenchmarkRunner:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    def run(
        self, cases: Iterable[BenchmarkCase], profiles: Iterable[str]
    ) -> BenchmarkReport:
        results: list[BenchmarkResult] = []
        for profile in profiles:
            for case in cases:
                if case.category not in BENCHMARK_CATEGORIES:
                    raise ValueError(f"unknown benchmark category: {case.category}")
                try:
                    response = self.router.generate(
                        GenerationRequest(
                            messages=[
                                ChatMessage(
                                    role="system",
                                    content="Return one JSON object and no prose.",
                                ),
                                ChatMessage(role="user", content=case.prompt),
                            ],
                            temperature=0,
                            context_tokens=4096,
                        ),
                        profile_name=profile,
                        allow_fallback=False,
                    )
                    parsed = json.loads(response.content)
                    score = _expected_subset_score(parsed, case.expected)
                    results.append(
                        BenchmarkResult(
                            case_id=case.id,
                            category=case.category,
                            profile=profile,
                            score=score,
                            latency_seconds=response.latency_seconds,
                            prompt_tokens=response.prompt_tokens,
                            completion_tokens=response.completion_tokens,
                        )
                    )
                except (ValueError, json.JSONDecodeError, ModelProviderError) as exc:
                    results.append(
                        BenchmarkResult(
                            case_id=case.id,
                            category=case.category,
                            profile=profile,
                            score=0,
                            latency_seconds=0,
                            error=str(exc),
                        )
                    )
        return BenchmarkReport(results=results)


def load_benchmark_cases(path: Path) -> list[BenchmarkCase]:
    return [BenchmarkCase.model_validate(item) for item in json.loads(path.read_text())]


def write_benchmark_report(report: BenchmarkReport, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "benchmark.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    (directory / "benchmark.md").write_text(report.to_markdown(), encoding="utf-8")


def _expected_subset_score(actual: object, expected: dict[str, object]) -> float:
    if not isinstance(actual, dict) or not expected:
        return 0.0
    matched = sum(actual.get(key) == value for key, value in expected.items())
    return matched / len(expected)
