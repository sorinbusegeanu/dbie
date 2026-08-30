"""The Phase 7 CrewAI Flow; business truth remains in domain services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from crewai.flow.flow import Flow, listen, start
from pydantic import PrivateAttr

from dbie.flows.checkpoints import JsonCheckpointStore
from dbie.flows.state import CandidateFailure, PipelineState, StageName


class StageExecutor(Protocol):
    def execute(self, stage: StageName, state: PipelineState) -> dict[str, Any]: ...


class NoOpStageExecutor:
    def execute(self, stage: StageName, state: PipelineState) -> dict[str, Any]:
        return {}


class IdeaPipelineFlow(Flow[PipelineState]):
    """Resumable stage graph with candidate isolation and clean checkpoints."""

    _executor: StageExecutor = PrivateAttr()
    _checkpoint_store: JsonCheckpointStore | None = PrivateAttr(default=None)
    _checkpoint_callback: Callable[[PipelineState], None] | None = PrivateAttr(
        default=None
    )

    def __init__(
        self,
        *,
        state: PipelineState,
        executor: StageExecutor | None = None,
        checkpoint_store: JsonCheckpointStore | None = None,
        checkpoint_callback: Callable[[PipelineState], None] | None = None,
    ) -> None:
        super().__init__(initial_state=state, tracing=False)
        self._executor = executor or NoOpStageExecutor()
        self._checkpoint_store = checkpoint_store
        self._checkpoint_callback = checkpoint_callback

    @classmethod
    def resume(
        cls,
        run_id: str,
        *,
        checkpoint_store: JsonCheckpointStore,
        executor: StageExecutor | None = None,
    ) -> IdeaPipelineFlow:
        return cls(
            state=checkpoint_store.load(run_id),
            executor=executor,
            checkpoint_store=checkpoint_store,
        )

    def _apply(self, stage: StageName) -> str:
        if stage in self.state.completed_stages:
            return stage.value
        self.state.current_stage = stage
        self.state.run_error = None
        try:
            changes = self._executor.execute(stage, self.state)
            failures = changes.pop("candidate_failures", [])
            self.state.candidate_failures.extend(
                CandidateFailure.model_validate(item) for item in failures
            )
            for field, value in changes.items():
                if field == "artifacts":
                    self.state.artifacts.update(value)
                else:
                    setattr(self.state, field, value)
            self.state.completed_stages.append(stage)
        except Exception as exc:
            self.state.run_error = f"{type(exc).__name__}: {exc}"
            self._save()
            raise
        self._save()
        return stage.value

    def _save(self) -> None:
        if self._checkpoint_store:
            self._checkpoint_store.save(self.state)
        if self._checkpoint_callback:
            self._checkpoint_callback(self.state.model_copy(deep=True))

    @start()
    def initialize_run(self) -> str:
        return self._apply(StageName.INITIALIZE_RUN)

    @listen(initialize_run)
    def discover_signals(self) -> str:
        return self._apply(StageName.DISCOVER_SIGNALS)

    @listen(discover_signals)
    def generate_ideas(self) -> str:
        return self._apply(StageName.GENERATE_IDEAS)

    @listen(generate_ideas)
    def eligibility_gate(self) -> str:
        return self._apply(StageName.ELIGIBILITY_GATE)

    @listen(eligibility_gate)
    def decompose_assumptions(self) -> str:
        return self._apply(StageName.DECOMPOSE_ASSUMPTIONS)

    @listen(decompose_assumptions)
    def collect_evidence(self) -> str:
        return self._apply(StageName.COLLECT_EVIDENCE)

    @listen(collect_evidence)
    def validate_assumptions(self) -> str:
        return self._apply(StageName.VALIDATE_ASSUMPTIONS)

    @listen(validate_assumptions)
    def model_business(self) -> str:
        return self._apply(StageName.MODEL_BUSINESS)

    @listen(model_business)
    def red_team(self) -> str:
        return self._apply(StageName.RED_TEAM)

    @listen(red_team)
    def rank_portfolio(self) -> str:
        return self._apply(StageName.RANK_PORTFOLIO)

    @listen(rank_portfolio)
    def design_experiments(self) -> str:
        return self._apply(StageName.DESIGN_EXPERIMENTS)

    @listen(design_experiments)
    def observe_and_decide(self) -> str:
        return self._apply(StageName.OBSERVE_AND_DECIDE)

    @listen(observe_and_decide)
    def produce_dossier(self) -> str:
        return self._apply(StageName.PRODUCE_DOSSIER)

    @listen(produce_dossier)
    def finalize_run(self) -> str:
        return self._apply(StageName.FINALIZE_RUN)
