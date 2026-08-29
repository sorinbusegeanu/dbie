"""DBIE command-line entry point."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from dbie.bootstrap import build_runtime
from dbie.config import load_settings
from dbie.domain.models import (
    AutonomousScalability,
    BusinessIdea,
    DigitalEligibility,
)
from dbie.evaluation.benchmark import (
    ModelBenchmarkRunner,
    load_benchmark_cases,
    write_benchmark_report,
)
from dbie.flows.checkpoints import JsonCheckpointStore
from dbie.flows.idea_pipeline import IdeaPipelineFlow
from dbie.flows.state import PipelineState
from dbie.models.base import ChatMessage, GenerationRequest
from dbie.observability.logging import configure_logging
from dbie.persistence.repositories import CandidateRepository, RunRepository
from dbie.services.candidate_service import CandidateService
from dbie.services.fixture_mvp import FixtureMVPExecutor
from dbie.services.run_service import RunService
from dbie.web import create_dashboard_app

app = typer.Typer(no_args_is_help=True, help="Digital Business Idea Engine")


def _emit(value: dict[str, Any]) -> None:
    typer.echo(json.dumps(value, indent=2, sort_keys=True, default=str))


@app.command("init")
def initialize(
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Initialize durable storage without invoking an LLM."""
    runtime = build_runtime(str(config))
    configure_logging(runtime.settings.log_level, runtime.settings.json_logs)
    runtime.database.initialize()
    _emit({"database": runtime.settings.database_url, "initialized": True})


@app.command()
def doctor(
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
    strict: Annotated[
        bool, typer.Option(help="Exit non-zero when a configured model is absent.")
    ] = True,
) -> None:
    """Check Python, database, Ollama, and exact configured model readiness."""
    runtime = build_runtime(str(config))
    configure_logging(runtime.settings.log_level, runtime.settings.json_logs)
    checks: dict[str, Any] = {
        "python": {
            "ok": tuple(map(int, platform.python_version_tuple())) >= (3, 12, 0),
            "version": platform.python_version(),
        }
    }
    try:
        runtime.database.initialize()
        checks["database"] = {
            "ok": runtime.database.ping(),
            "url": runtime.settings.database_url,
        }
    except (OSError, SQLAlchemyError) as exc:
        checks["database"] = {"ok": False, "error": str(exc)}

    health = runtime.ollama.health()
    configured_models = {
        name: profile.model for name, profile in runtime.models_config.profiles.items()
    }
    installed = set(health.installed_models)
    model_checks = {
        name: {"model": model, "ok": model in installed}
        for name, model in configured_models.items()
    }
    checks["ollama"] = health.model_dump()
    checks["models"] = model_checks
    fatal = (
        not checks["python"]["ok"]
        or not checks["database"]["ok"]
        or not health.reachable
        or (strict and not all(item["ok"] for item in model_checks.values()))
    )
    checks["ready"] = not fatal
    _emit(checks)
    if fatal:
        raise typer.Exit(code=1)


@app.command()
def smoke(
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Exercise run and candidate persistence without CrewAI or an LLM."""
    runtime = build_runtime(str(config))
    runtime.database.initialize()
    run_service = RunService(RunRepository(runtime.database), runtime.settings)
    candidate_service = CandidateService(CandidateRepository(runtime.database))

    run = run_service.create("Deterministic foundation smoke test")
    run_service.resume(run.id)
    idea = BusinessIdea(
        run_id=run.id,
        problem_id="synthetic-problem",
        title="Synthetic digital workflow",
        one_sentence_thesis="Automate a bounded digital workflow.",
        target_customer="Synthetic operators",
        buyer="Operations lead",
        user="Operations analyst",
        value_proposition="Reduce repetitive digital work.",
        product_form="Software service",
        delivery_model="Self-service web application",
        why_now="Synthetic acceptance fixture",
        digital_eligibility=DigitalEligibility(
            product_service=True,
            acquisition=True,
            sales=True,
            fulfilment=True,
            operations=True,
            infrastructure=True,
            payments=True,
            support=True,
            scaling=True,
            geography=True,
        ),
        autonomous_scalability=AutonomousScalability(
            target_automation_ratio=0.95,
            human_minutes_per_customer=10,
            human_minutes_per_customer_at_10x=1,
            human_only_tasks=["exception approval"],
            credible_transition_plan=True,
        ),
    )
    candidate_service.register(idea)
    result = candidate_service.apply_eligibility(idea.id)
    reloaded = candidate_service.repository.get(idea.id)
    run_service.close(run.id)
    _emit(
        {
            "run_id": run.id,
            "candidate_id": idea.id,
            "eligible": result.eligible,
            "reloaded_identically": reloaded.id == idea.id,
            "state": reloaded.lifecycle_state.value,
        }
    )


@app.command("acceptance-run")
def acceptance_run(
    mandate: Annotated[str, typer.Option(help="Business discovery mandate")] = (
        "Find fully digital, autonomously scalable compliance products"
    ),
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Run the complete deterministic MVP fixture and write dossiers/checkpoints."""
    runtime = build_runtime(str(config))
    run_id = str(uuid4())
    checkpoint_store = JsonCheckpointStore(runtime.settings.run_directory)
    flow = IdeaPipelineFlow(
        state=PipelineState(run_id=run_id, mandate=mandate),
        executor=FixtureMVPExecutor(runtime.database, runtime.settings.run_directory),
        checkpoint_store=checkpoint_store,
    )
    flow.kickoff()
    _emit(
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "finalist_ids": flow.state.finalist_ids,
            "dossiers": flow.state.artifacts["dossier_paths"],
            "checkpoint": str(checkpoint_store.path_for(run_id)),
        }
    )


@app.command("dashboard")
def dashboard_command(
    host: Annotated[str | None, typer.Option(help="Dashboard bind address.")] = None,
    port: Annotated[int | None, typer.Option(min=1, max=65535)] = None,
    runs_dir: Annotated[
        Path | None, typer.Option(help="Filesystem directory containing DBIE runs.")
    ] = None,
    refresh: Annotated[
        int | None, typer.Option(min=0, max=60, help="Page refresh interval in seconds.")
    ] = None,
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Serve the read-only local run dashboard."""
    import uvicorn

    settings = load_settings(config)
    viewer = settings.web_viewer
    application = create_dashboard_app(
        runs_dir or viewer.runs_dir,
        current_run=viewer.current_run,
        auto_refresh_seconds=(
            viewer.auto_refresh_seconds if refresh is None else refresh
        ),
        max_text_bytes=viewer.max_text_bytes,
    )
    uvicorn.run(
        application,
        host=host or viewer.host,
        port=port or viewer.port,
        log_level=settings.log_level.lower(),
    )


class _ProbeResponse(BaseModel):
    ok: bool
    provider_under_test: str


@app.command("benchmark")
def benchmark_command(
    profile: Annotated[
        str | None, typer.Option(help="Configured profile; defaults to primary.")
    ] = None,
    cases: Annotated[Path, typer.Option(exists=True)] = Path(
        "benchmarks/dbie_mvp.json"
    ),
    output: Annotated[Path, typer.Option()] = Path("runs/benchmarks/latest"),
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Measure one configured model on the provider-neutral DBIE benchmark."""
    runtime = build_runtime(str(config))
    selected = profile or runtime.models_config.default_profile
    report = ModelBenchmarkRunner(runtime.router).run(
        load_benchmark_cases(cases), [selected]
    )
    write_benchmark_report(report, output)
    _emit(
        {
            "profile": selected,
            "score": report.score_by_profile()[selected],
            "cases": len(report.results),
            "output": str(output),
        }
    )


@app.command("model-probe")
def model_probe(
    profile: Annotated[
        str | None, typer.Option(help="Configured profile name.")
    ] = None,
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Perform one schema-constrained generation through the configured router."""
    runtime = build_runtime(str(config))
    selected = profile or runtime.models_config.default_profile
    response = runtime.router.structured_generate(
        GenerationRequest(
            messages=[
                ChatMessage(
                    role="system",
                    content="Return only the requested structured object.",
                ),
                ChatMessage(
                    role="user",
                    content=(
                        "Set ok to true and provider_under_test to the literal "
                        f"profile name {selected}."
                    ),
                ),
            ],
            temperature=0,
            context_tokens=4096,
        ),
        _ProbeResponse,
        profile_name=selected,
        allow_fallback=False,
    )
    _emit({"profile": selected, "structured_response": response.model_dump()})


if __name__ == "__main__":
    app()
