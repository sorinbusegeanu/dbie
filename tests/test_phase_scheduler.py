import pytest

from dbie.bootstrap import build_runtime
from dbie.models.phase_scheduler import ModelPhaseScheduler, ModelPhaseTask
from dbie.models.roles import ModelRole, ModelSelection
from dbie.models.task_roles import TaskClass
from dbie.persistence.db import Database
from dbie.persistence.model_performance import ModelPerformanceRepository


def task(
    task_id: str,
    task_class: TaskClass,
    barrier: int,
    *,
    escalation: bool = False,
) -> ModelPhaseTask:
    return ModelPhaseTask(
        task_id=task_id,
        run_id="run",
        task_class=task_class,
        dependency_barrier=barrier,
        crew_id="crew",
        agent_id="agent",
        escalation_required=escalation,
        selection=ModelSelection.PRIMARY,
    )


def test_scheduler_batches_model_affine_tasks_between_barriers() -> None:
    scheduler = ModelPhaseScheduler(build_runtime().router)
    phases = scheduler.plan(
        [
            task("think-2", TaskClass.RESEARCH_PLANNING, 0),
            task("do-2", TaskClass.REGULATORY_RESEARCH, 1),
            task("think-1", TaskClass.ASSUMPTION_DECOMPOSITION, 0),
            task("do-1", TaskClass.MARKET_EVIDENCE, 1),
            task("synthesize", TaskClass.EVIDENCE_RECONCILIATION, 2),
        ]
    )

    assert [phase.model_role for phase in phases] == [
        ModelRole.THINKER,
        ModelRole.DOER,
        ModelRole.THINKER,
    ]
    assert [len(phase.tasks) for phase in phases] == [2, 2, 1]
    assert phases[0].resolved_model_id == "qwen3:14b-64k"
    assert phases[1].resolved_model_id == "qwen3:14b-64k"


def test_judge_phase_requires_explicit_escalation() -> None:
    with pytest.raises(ValueError, match="explicit escalation"):
        task("judge", TaskClass.INDEPENDENT_RED_TEAM, 3)


def test_execution_checkpoints_every_residency_and_counts_switches(tmp_path) -> None:
    scheduler = ModelPhaseScheduler(build_runtime().router)
    database = Database(f"sqlite:///{tmp_path / 'phase-metrics.sqlite3'}")
    database.initialize()
    performance = ModelPerformanceRepository(database)
    phases = scheduler.plan(
        [
            task("think", TaskClass.RESEARCH_PLANNING, 0),
            task("do", TaskClass.MARKET_EVIDENCE, 1),
            task("judge", TaskClass.INDEPENDENT_RED_TEAM, 2, escalation=True),
        ]
    )
    checkpoints: list[str] = []
    released: list[str] = []
    result = scheduler.execute(
        phases,
        execute_task=lambda item, phase: phase.resolved_model_id,
        checkpoint_barrier=lambda phase: checkpoints.append(phase.phase_id),
        release_model=lambda phase: released.append(phase.resolved_model_id),
        performance_sink=performance,
    )

    assert checkpoints == result.phase_ids
    assert released == [phase.resolved_model_id for phase in phases]
    assert result.switch_count == 1
    assert result.task_outputs["judge"] == "gpt-oss:20b-64k"
    persisted = performance.phases_for_run("run")
    assert [item.phase_id for item in persisted] == result.phase_ids
    assert sum(item.switch_count for item in persisted) == 1
