"""DBIE command-line entry point."""

from __future__ import annotations

import json
import platform
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from dbie.bootstrap import build_runtime
from dbie.config import load_readiness_policy, load_settings, load_tools_config
from dbie.crews.catalog import CrewCatalog
from dbie.crews.stage_runner import CrewAIStageRunner
from dbie.domain.enums import RunStatus
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
from dbie.evaluation.commercial_benchmark import (
    evaluate_historical_benchmark,
    load_historical_benchmark,
    write_historical_report,
    write_forecast_report,
)
from dbie.flows.checkpoints import JsonCheckpointStore
from dbie.flows.idea_pipeline import IdeaPipelineFlow
from dbie.flows.state import PipelineState
from dbie.models.base import ChatMessage, GenerationRequest
from dbie.observability.logging import configure_logging
from dbie.persistence.repositories import CandidateRepository, RunRepository
from dbie.services.candidate_service import CandidateService
from dbie.services.fixture_mvp import FixtureMVPExecutor
from dbie.services.live_mvp import LiveMVPConfig, LiveMVPExecutor
from dbie.services.run_service import RunService
from dbie.tools.adapters.embeddings import FastEmbedBGEEmbeddingService
from dbie.tools.audit import CompositeAuditSink, JsonlToolAuditSink
from dbie.tools.oss_local import OSSLocalStack, build_oss_stack
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
        bool,
        typer.Option(
            help="Exit non-zero unless models, ten tools, and local embeddings are ready."
        ),
    ] = True,
) -> None:
    """Check Python, database, Ollama, models, ten tools, and embeddings."""
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
    live_ready = False
    try:
        stack, _, _ = _live_stack(runtime)
        live_checks = _live_preflight(runtime, stack)
        checks["tools"] = live_checks["tools"]
        checks["internal_adapters"] = live_checks["internal_adapters"]
        checks["embedding"] = live_checks["embedding"]
        live_ready = live_checks["ready"]
    except Exception as exc:  # noqa: BLE001 - doctor reports setup gaps
        checks["tools"] = {"ok": False, "error": str(exc)}
        checks["internal_adapters"] = {"ok": False, "error": str(exc)}
        checks["embedding"] = {"available": False, "error": str(exc)}
    fatal = (
        not checks["python"]["ok"]
        or not checks["database"]["ok"]
        or not health.reachable
        or (strict and not all(item["ok"] for item in model_checks.values()))
        or (strict and not live_ready)
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
        executor=FixtureMVPExecutor(
            runtime.database,
            runtime.settings.run_directory,
            load_readiness_policy(runtime.settings),
        ),
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


def _live_stack(runtime: Any) -> tuple[OSSLocalStack, CrewAIStageRunner, LiveMVPConfig]:
    tools_config = load_tools_config(runtime.settings)
    embedding_config = tools_config.get("embedding_profile", {})
    embeddings = FastEmbedBGEEmbeddingService(
        model_id=embedding_config.get("model", "BAAI/bge-small-en-v1.5"),
        cache_dir=(
            Path(embedding_config["cache_dir"])
            if embedding_config.get("cache_dir")
            else None
        ),
        # A live run must never silently download a model.  Install/cache the
        # configured BGE/E5 model explicitly, then rerun doctor/live-run.
        local_files_only=True,
    )
    audit = CompositeAuditSink(
        [JsonlToolAuditSink(runtime.settings.run_directory)]
    )
    stack = build_oss_stack(
        database=runtime.database,
        embeddings=embeddings,
        tools_config=tools_config,
        audit=audit,
    )
    catalog = CrewCatalog(stack.gateway, runtime.crew_llm)
    runner = CrewAIStageRunner(
        catalog,
        runtime.settings.run_directory,
        performance_sink=runtime.model_performance,
    )
    mvp_config = LiveMVPConfig.model_validate(tools_config.get("mvp", {}))
    return stack, runner, mvp_config


def _live_preflight(runtime: Any, stack: OSSLocalStack) -> dict[str, Any]:
    health = runtime.ollama.health()
    configured = {
        profile.model for profile in runtime.models_config.profiles.values()
    }
    installed = set(health.installed_models)
    model_state = {
        model: model in installed for model in sorted(configured)
    }
    adapters = {}
    for tool, adapter_name in stack.gateway.routes.items():
        adapter = stack.gateway.registry.get(adapter_name)
        status = adapter.health()
        adapters[tool.value] = status.model_dump(mode="json")
    internal_adapters = {
        status.name: status.model_dump(mode="json")
        for status in stack.gateway.registry.health()
    }
    embedding_error = None
    try:
        stack.embeddings.embed(["DBIE local embedding health check"])
        embedding_available = True
    except Exception as exc:  # noqa: BLE001 - preflight reports a normalized gap
        embedding_available = False
        embedding_error = str(exc)
    ready = (
        health.reachable
        and all(model_state.values())
        and all(item["available"] for item in adapters.values())
        and all(item["available"] for item in internal_adapters.values())
        and embedding_available
    )
    return {
        "ready": ready,
        "ollama": health.model_dump(mode="json"),
        "models": model_state,
        "tools": adapters,
        "internal_adapters": internal_adapters,
        "embedding": {
            "available": embedding_available,
            "model": stack.embeddings.model_id,
            "error": embedding_error,
        },
    }


def _live_executor(
    runtime: Any,
    stack: OSSLocalStack,
    runner: CrewAIStageRunner,
    mvp_config: LiveMVPConfig,
) -> LiveMVPExecutor:
    fingerprint = sha256(
        (
            runtime.models_config.model_dump_json()
            + json.dumps(load_tools_config(runtime.settings), sort_keys=True)
        ).encode()
    ).hexdigest()
    return LiveMVPExecutor(
        runtime.database,
        runtime.settings.run_directory,
        stack.gateway,
        runner,
        stack.memory,
        config=mvp_config,
        readiness_policy=load_readiness_policy(runtime.settings),
        configuration_hash=fingerprint,
    )


def _restored_live_config(
    configured: LiveMVPConfig,
    state: PipelineState,
) -> LiveMVPConfig:
    stored = state.artifacts.get("live_mvp_config")
    if stored is None:
        return configured
    return LiveMVPConfig.model_validate(stored)


@app.command("live-run")
def live_run(
    mandate: Annotated[str, typer.Option(help="Business discovery mandate")] = (
        "Find fully digital, autonomously scalable compliance products"
    ),
    signals: Annotated[int | None, typer.Option(min=1, max=500)] = None,
    ideas: Annotated[int | None, typer.Option(min=1, max=500)] = None,
    candidates: Annotated[int | None, typer.Option(min=1, max=25)] = None,
    strict_targets: Annotated[bool, typer.Option()] = True,
    preflight: Annotated[bool, typer.Option()] = True,
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Run every v0.6 MVP stage through real CrewAI/Ollama agents and OSS tools."""
    runtime = build_runtime(str(config))
    runtime.database.initialize()
    stack, runner, configured = _live_stack(runtime)
    if preflight:
        checks = _live_preflight(runtime, stack)
        if not checks["ready"]:
            _emit({"status": "PREFLIGHT_FAILED", "checks": checks})
            raise typer.Exit(code=1)
    selected = configured.model_copy(
        update={
            "target_signals": signals or configured.target_signals,
            "target_raw_ideas": ideas or configured.target_raw_ideas,
            "max_validation_candidates": (
                candidates or configured.max_validation_candidates
            ),
            "strict_generation_targets": strict_targets,
        }
    )
    run_id = str(uuid4())
    checkpoints = JsonCheckpointStore(runtime.settings.run_directory)
    executor = _live_executor(runtime, stack, runner, selected)
    flow = IdeaPipelineFlow(
        state=PipelineState(
            run_id=run_id,
            mandate=mandate,
            artifacts={"live_mvp_config": selected.model_dump(mode="json")},
        ),
        executor=executor,
        checkpoint_store=checkpoints,
    )
    try:
        flow.kickoff()
    except Exception:
        try:
            RunRepository(runtime.database).set_status(run_id, RunStatus.FAILED)
        except Exception as status_error:  # noqa: BLE001
            typer.echo(
                f"warning: could not persist failed run status: {status_error}",
                err=True,
            )
        raise
    _emit(
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "execution_mode": "live_crewai_ollama",
            "finalist_ids": flow.state.finalist_ids,
            "dossiers": flow.state.artifacts.get("dossier_paths", []),
            "checkpoint": str(checkpoints.path_for(run_id)),
        }
    )


@app.command("resume-run")
def resume_live_run(
    run_id: Annotated[str, typer.Argument(help="Persisted run UUID")],
    preflight: Annotated[bool, typer.Option()] = True,
    config: Annotated[Path, typer.Option(exists=True)] = Path("config/default.yaml"),
) -> None:
    """Resume a live run from its last completed stage checkpoint."""
    runtime = build_runtime(str(config))
    runtime.database.initialize()
    stack, runner, configured = _live_stack(runtime)
    if preflight:
        checks = _live_preflight(runtime, stack)
        if not checks["ready"]:
            _emit({"status": "PREFLIGHT_FAILED", "checks": checks})
            raise typer.Exit(code=1)
    checkpoints = JsonCheckpointStore(runtime.settings.run_directory)
    restored_state = checkpoints.load(run_id)
    restored_config = _restored_live_config(configured, restored_state)
    flow = IdeaPipelineFlow(
        state=restored_state,
        checkpoint_store=checkpoints,
        executor=_live_executor(runtime, stack, runner, restored_config),
    )
    RunRepository(runtime.database).set_status(run_id, RunStatus.RUNNING)
    flow.kickoff()
    _emit(
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "execution_mode": "live_crewai_ollama",
            "finalist_ids": flow.state.finalist_ids,
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


@app.command("commercial-benchmark")
def commercial_benchmark_command(
    benchmark: Annotated[Path, typer.Option(exists=True)] = Path(
        "benchmarks/commercial_opportunities_synthetic.json"
    ),
    output: Annotated[Path, typer.Option()] = Path("runs/benchmarks/commercial"),
    k: Annotated[int, typer.Option(min=1)] = 5,
) -> None:
    """Evaluate versioned historical commercial decisions offline."""
    metrics = evaluate_historical_benchmark(load_historical_benchmark(benchmark), k=k)
    paths = write_historical_report(metrics, output)
    _emit(
        {
            "benchmark_id": metrics["benchmark_id"],
            "metrics": metrics,
            "outputs": [str(path) for path in paths],
        }
    )


@app.command("forecast-report")
def forecast_report_command(
    input_file: Annotated[Path, typer.Option(exists=True)] = Path("benchmarks/forecast_observations_synthetic.json"),
    output: Annotated[Path, typer.Option()] = Path("runs/benchmarks/forecasts"),
) -> None:
    """Compare structured commercial forecasts with measured outcomes offline."""
    rows = json.loads(input_file.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise typer.BadParameter("input JSON must be a list of forecast/outcome records")
    paths = write_forecast_report(rows, output)
    _emit({"observations": len(rows), "outputs": [str(path) for path in paths]})


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
