"""Model-resident batching above ModelRouter for single-GPU execution."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from time import monotonic
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dbie.models.performance import ModelPerformanceSink, ModelPhasePerformanceRecord
from dbie.models.roles import ModelRole, ModelSelection
from dbie.models.router import ModelRouter
from dbie.models.task_roles import TaskClass, role_for_task


class ModelPhaseTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    run_id: str
    task_class: TaskClass
    dependency_barrier: int = Field(default=0, ge=0)
    priority: int = 0
    venture_id: str | None = None
    venture_batch: str = "default"
    crew_id: str
    agent_id: str
    context_tokens: int | None = Field(default=None, gt=0)
    execution_mode: str = "default"
    escalation_required: bool = False
    selection: ModelSelection | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def model_role(self) -> ModelRole:
        return role_for_task(self.task_class)

    @model_validator(mode="after")
    def judge_is_explicitly_escalated(self) -> ModelPhaseTask:
        if self.model_role is ModelRole.JUDGE and not self.escalation_required:
            raise ValueError("JUDGE tasks require an explicit escalation decision")
        return self


class ModelPhase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase_id: str
    dependency_barrier: int
    model_role: ModelRole
    selection: ModelSelection
    resolved_profile: str
    resolved_model_id: str
    context_tokens: int
    execution_mode: str
    venture_batch: str
    active_inference_limit: int = Field(ge=1)
    tasks: list[ModelPhaseTask] = Field(min_length=1)


class PhaseRunResult(BaseModel):
    phase_ids: list[str]
    task_outputs: dict[str, Any]
    switch_count: int
    tasks_per_residency: dict[str, int]


class ModelPhaseScheduler:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    def plan(self, tasks: list[ModelPhaseTask]) -> list[ModelPhase]:
        groups: dict[
            tuple[int, ModelRole, ModelSelection, str, int, str, str],
            list[ModelPhaseTask],
        ] = {}
        for task in tasks:
            selection = task.selection or self.router.selection_for_task(
                task.model_role, task.task_id
            )
            resolution = self.router.resolve_role(task.model_role, selection=selection)
            context_tokens = task.context_tokens or resolution.context_tokens
            maximum = self.router.config.profiles[
                resolution.profile_name
            ].maximum_context_tokens
            if context_tokens > maximum:
                raise ValueError(
                    f"task {task.task_id} context {context_tokens} exceeds "
                    f"{resolution.profile_name} maximum {maximum}"
                )
            key = (
                task.dependency_barrier,
                task.model_role,
                selection,
                resolution.profile_name,
                context_tokens,
                task.execution_mode,
                task.venture_batch,
            )
            groups.setdefault(key, []).append(task)

        phases = []
        role_order = {
            ModelRole.THINKER: 0,
            ModelRole.DOER: 1,
            ModelRole.BUILDER: 2,
            ModelRole.JUDGE: 3,
        }
        for key, grouped_tasks in groups.items():
            barrier, role, selection, profile_name, context, mode, venture_batch = key
            profile = self.router.config.profiles[profile_name]
            ordered_tasks = sorted(
                grouped_tasks, key=lambda item: (-item.priority, item.task_id)
            )
            phase_key = "|".join(
                (
                    str(barrier),
                    role.value,
                    selection.value,
                    profile_name,
                    str(context),
                    mode,
                    venture_batch,
                )
            )
            phases.append(
                ModelPhase(
                    phase_id=sha256(phase_key.encode()).hexdigest()[:16],
                    dependency_barrier=barrier,
                    model_role=role,
                    selection=selection,
                    resolved_profile=profile_name,
                    resolved_model_id=profile.model,
                    context_tokens=context,
                    execution_mode=mode,
                    venture_batch=venture_batch,
                    active_inference_limit=profile.active_concurrency,
                    tasks=ordered_tasks,
                )
            )
        return sorted(
            phases,
            key=lambda item: (
                item.dependency_barrier,
                role_order[item.model_role],
                item.resolved_profile,
                item.phase_id,
            ),
        )

    def execute(
        self,
        phases: list[ModelPhase],
        *,
        execute_task: Callable[[ModelPhaseTask, ModelPhase], Any],
        checkpoint_barrier: Callable[[ModelPhase], None],
        release_model: Callable[[ModelPhase], None] | None = None,
        performance_sink: ModelPerformanceSink | None = None,
    ) -> PhaseRunResult:
        outputs: dict[str, Any] = {}
        phase_ids: list[str] = []
        residencies: dict[str, int] = {}
        prior_model: str | None = None
        switches = 0
        for phase in phases:
            phase_started = monotonic()
            switched = (
                prior_model is not None and phase.resolved_model_id != prior_model
            )
            if switched:
                switches += 1
            prior_model = phase.resolved_model_id
            for task in phase.tasks:
                outputs[task.task_id] = execute_task(task, phase)
            checkpoint_barrier(phase)
            phase_ids.append(phase.phase_id)
            residencies[phase.phase_id] = len(phase.tasks)
            if release_model is not None:
                release_model(phase)
            if performance_sink is not None:
                performance_sink.record_phase(
                    ModelPhasePerformanceRecord(
                        run_id=phase.tasks[0].run_id,
                        phase_id=phase.phase_id,
                        model_role=phase.model_role,
                        resolved_profile=phase.resolved_profile,
                        model_id=phase.resolved_model_id,
                        dependency_barrier=phase.dependency_barrier,
                        switch_count=int(switched),
                        tasks_per_model_residency=len(phase.tasks),
                        phase_duration_ms=(monotonic() - phase_started) * 1000,
                        metadata={
                            "execution_mode": phase.execution_mode,
                            "venture_batch": phase.venture_batch,
                            "context_tokens": phase.context_tokens,
                        },
                    )
                )
        return PhaseRunResult(
            phase_ids=phase_ids,
            task_outputs=outputs,
            switch_count=switches,
            tasks_per_residency=residencies,
        )
