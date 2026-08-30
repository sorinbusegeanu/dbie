"""Model-phase scheduled execution of bounded, typed CrewAI tasks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from crewai import Crew, Process, Task
from pydantic import BaseModel

from dbie.crews.catalog import (
    ActorSpec,
    CrewCatalog,
    actor_id_for,
    task_class_for_actor,
)
from dbie.crews.conversation_capture import CrewAIConversationCapture
from dbie.models.performance import ModelPerformanceSink
from dbie.models.phase_scheduler import (
    ModelPhase,
    ModelPhaseScheduler,
    ModelPhaseTask,
)
from dbie.models.roles import ModelRole
from dbie.services.run_workspace import RunWorkspaceManager
from dbie.tools.crewai_tools import CrewAIToolContext
from dbie.tools.contracts import ToolName


@dataclass(frozen=True)
class CrewTaskRequest[OutputT: BaseModel]:
    task_id: str
    stage_id: str
    crew_name: str
    spec: ActorSpec
    description: str
    expected_output: str
    output_model: type[OutputT]
    candidate_id: str | None = None
    assumption_id: str | None = None
    dependency_barrier: int = 0
    priority: int = 0
    escalation_required: bool = False
    required_tools: tuple[ToolName, ...] = ()


class StageTaskRunner(Protocol):
    def run_tasks(
        self, run_id: str, requests: list[CrewTaskRequest[Any]]
    ) -> dict[str, BaseModel]: ...


class CrewAIStageRunner:
    """Execute each typed task through CrewAI and DBIE's Ollama-only router."""

    def __init__(
        self,
        catalog: CrewCatalog,
        runs_directory: Path,
        *,
        performance_sink: ModelPerformanceSink | None = None,
        phase_callback: Callable[[ModelPhase], None] | None = None,
    ) -> None:
        self.catalog = catalog
        self.runs_directory = Path(runs_directory)
        self.performance_sink = performance_sink
        self.phase_callback = phase_callback
        self.scheduler = ModelPhaseScheduler(catalog.llm.router)
        self.workspaces = RunWorkspaceManager(self.runs_directory)

    def run_tasks(
        self, run_id: str, requests: list[CrewTaskRequest[Any]]
    ) -> dict[str, BaseModel]:
        if not requests:
            return {}
        by_id = {request.task_id: request for request in requests}
        if len(by_id) != len(requests):
            raise ValueError("CrewAI task IDs must be unique within a scheduled batch")
        phases = self.scheduler.plan(
            [
                ModelPhaseTask(
                    task_id=request.task_id,
                    run_id=run_id,
                    task_class=task_class_for_actor(request.spec),
                    dependency_barrier=request.dependency_barrier,
                    priority=request.priority,
                    venture_id=request.candidate_id,
                    venture_batch=request.stage_id,
                    crew_id=request.crew_name,
                    agent_id=actor_id_for(request.spec.role),
                    escalation_required=request.escalation_required,
                )
                for request in requests
            ]
        )

        def execute(task: ModelPhaseTask, phase: ModelPhase) -> BaseModel:
            return self._execute_one(run_id, by_id[task.task_id], phase)

        def checkpoint(phase: ModelPhase) -> None:
            self.workspaces.append_activity(
                run_id,
                (
                    f"model phase {phase.phase_id}: {phase.model_role.value} "
                    f"using {phase.resolved_model_id}; {len(phase.tasks)} task(s) complete"
                ),
            )
            if self.phase_callback is not None:
                self.phase_callback(phase)

        result = self.scheduler.execute(
            phases,
            execute_task=execute,
            checkpoint_barrier=checkpoint,
            performance_sink=self.performance_sink,
        )
        return {
            task_id: value
            for task_id, value in result.task_outputs.items()
            if isinstance(value, BaseModel)
        }

    def _execute_one(
        self,
        run_id: str,
        request: CrewTaskRequest[Any],
        phase: ModelPhase,
    ) -> BaseModel:
        if request.spec.model_role is ModelRole.JUDGE and not request.escalation_required:
            raise ValueError("JUDGE execution requires an explicit escalation record")
        context = CrewAIToolContext(
            run_id=run_id,
            stage_id=request.stage_id,
            task_id=request.task_id,
            actor_id=actor_id_for(request.spec.role),
            candidate_id=request.candidate_id,
            assumption_id=request.assumption_id,
        )
        last_error: Exception | None = None
        required_names = ", ".join(item.value for item in request.required_tools)
        for attempt in range(2):
            agent = self.catalog.build_agent(
                request.spec,
                context,
                selection=phase.selection,
            )
            recovery = ""
            if attempt:
                recovery = (
                    "\nRECOVERY ATTEMPT: the prior response failed a hard runtime "
                    "contract. Return every required typed field with non-empty valid "
                    "values. Call every mandatory tool before the final answer"
                    + (f": {required_names}." if required_names else ".")
                )
            task = Task(
                description=request.description + recovery,
                expected_output=request.expected_output,
                agent=agent,
                output_pydantic=request.output_model,
                guardrail_max_retries=1,
            )
            crew = Crew(
                name=request.crew_name,
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
                memory=False,
                cache=False,
                tracing=False,
            )
            try:
                with CrewAIConversationCapture(
                    self.runs_directory, run_id, request.crew_name
                ):
                    result = crew.kickoff()
                self._verify_required_tools(request)
                if isinstance(result.pydantic, request.output_model):
                    return result.pydantic
                return request.output_model.model_validate_json(result.raw)
            except Exception as exc:  # noqa: BLE001 - one bounded task retry
                last_error = exc
                self.workspaces.append_activity(
                    run_id,
                    f"task {request.task_id}: attempt {attempt + 1} failed "
                    f"({type(exc).__name__})",
                )
        raise ValueError(
            f"CrewAI task {request.task_id} did not return "
            f"{request.output_model.__name__} after 2 attempts"
        ) from last_error

    def _verify_required_tools(self, request: CrewTaskRequest[Any]) -> None:
        if not request.required_tools:
            return
        records = getattr(self.catalog.gateway.audit, "records", [])
        called = {
            record.envelope.tool
            for record in records
            if record.envelope.task_id == request.task_id
            and record.allowed
            and record.result is not None
        }
        missing = set(request.required_tools) - called
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(
                f"CrewAI task {request.task_id} omitted required real tools: {names}"
            )
