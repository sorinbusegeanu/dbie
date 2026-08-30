import json
import subprocess

import pytest
from pydantic import ValidationError

from dbie.domain.enums import DecisionType
from dbie.observability.metrics import MetricsCollector, gpu_snapshot
from dbie.reporting.dossier import (
    AssumptionSummary,
    Dossier,
    EvidenceReference,
    write_dossier,
)


def dossier() -> Dossier:
    return Dossier(
        run_id="run",
        candidate_id="idea",
        title="Compliance automation",
        thesis="Automate a bounded compliance workflow.",
        description=" ".join(
            [
                (
                    "This detailed opportunity description explains the customer "
                    "problem, buyer, workflow, product behavior, delivery model, "
                    "evidence, risks, economics, automation boundaries, validation "
                    "needs, and next experiment."
                )
            ]
            * 8
        ),
        why_now="Machine-readable rules",
        customer="Compliance teams",
        buyer="CCO",
        assumptions=[
            AssumptionSummary(
                statement="Pain exists",
                status="RESEARCH_SUPPORTED",
                evidence_for=[
                    EvidenceReference(
                        title="Official regulator — Primary evidence",
                        summary="The measured workflow burden is documented.",
                    )
                ],
                independent_lineages=2,
            )
        ],
        unknowns=["Price elasticity"],
        competitors=["Manual consulting"],
        business_model_variants=["Subscription"],
        economics={"gross_margin_base": 0.8},
        automation_ratio=0.95,
        human_minutes_per_customer_at_10x=2,
        red_team_findings=["Incumbent bundling risk"],
        ranking={"rank": 1, "stability": 1.0},
        recommended_experiments=["Price-choice test"],
        decision=DecisionType.BUILD,
        reason_codes=["HARD_GATES_PASSED"],
    )


def test_dossier_is_reproducible_markdown_and_machine_state(tmp_path) -> None:
    markdown, state = write_dossier(dossier(), tmp_path)
    assert "## Assumption map and evidence" in markdown.read_text()
    assert json.loads(state.read_text())["decision"] == "BUILD"
    assert "## Opportunity description" in markdown.read_text()
    rendered = markdown.read_text()
    assert "Official regulator — Primary evidence" in rendered
    assert "## Economics" in rendered
    assert "Expected base gross margin: **80%**" in rendered
    assert "## Portfolio position" in rendered
    assert '"gross_margin_base"' not in rendered
    assert '"idea_id"' not in rendered


def test_dossier_rejects_short_opportunity_description() -> None:
    payload = dossier().model_dump()
    payload["description"] = "Too short"
    with pytest.raises(ValidationError, match="at least 100 words"):
        Dossier.model_validate(payload)


def test_metrics_cover_labels_latency_queue_and_gpu() -> None:
    metrics = MetricsCollector()
    metrics.increment("tool_calls", tool="web_search", actor="TrendScout")
    metrics.observe_latency("model_latency", 1.25, model="gpt-oss:20b-64k")
    metrics.set_gauge("queue_depth", 2)
    snapshot = metrics.snapshot()
    assert snapshot.counters["tool_calls{actor=TrendScout,tool=web_search}"] == 1
    assert snapshot.gauges["queue_depth"] == 2

    fake = lambda *args, **kwargs: subprocess.CompletedProcess(
        args[0], 0, "0, 123, 16384, 42\n", ""
    )
    assert gpu_snapshot(fake)["devices"][0]["memory_used_mb"] == 123
