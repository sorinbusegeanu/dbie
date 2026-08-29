from pathlib import Path

import pytest

from dbie.flows.checkpoints import JsonCheckpointStore
from dbie.flows.idea_pipeline import IdeaPipelineFlow
from dbie.flows.state import STAGE_ORDER, PipelineState, StageName


class RecordingExecutor:
    def __init__(self, fail_at: StageName | None = None) -> None:
        self.calls: list[StageName] = []
        self.fail_at = fail_at

    def execute(self, stage, state):
        self.calls.append(stage)
        if stage is self.fail_at:
            raise RuntimeError("dependency unavailable")
        if stage is StageName.GENERATE_IDEAS:
            return {
                "candidate_ids": ["good", "bad"],
                "candidate_failures": [
                    {
                        "candidate_id": "bad",
                        "stage": stage,
                        "error_category": "SCHEMA_INVALID",
                        "detail": "isolated",
                    }
                ],
            }
        return {}


def state() -> PipelineState:
    return PipelineState(run_id="run-1", mandate="Find a digital business")


def test_crewai_flow_executes_all_typed_stages_and_isolates_candidate(
    tmp_path: Path,
) -> None:
    executor = RecordingExecutor()
    store = JsonCheckpointStore(tmp_path)
    flow = IdeaPipelineFlow(state=state(), executor=executor, checkpoint_store=store)

    flow.kickoff()

    assert executor.calls == STAGE_ORDER
    assert flow.state.completed_stages == STAGE_ORDER
    assert flow.state.candidate_failures[0].candidate_id == "bad"
    assert store.load("run-1") == flow.state


def test_flow_checkpoints_dependency_failure_and_resumes_without_repeating(
    tmp_path: Path,
) -> None:
    store = JsonCheckpointStore(tmp_path)
    failing = RecordingExecutor(fail_at=StageName.COLLECT_EVIDENCE)
    flow = IdeaPipelineFlow(state=state(), executor=failing, checkpoint_store=store)

    with pytest.raises(RuntimeError, match="dependency unavailable"):
        flow.kickoff()

    saved = store.load("run-1")
    assert saved.completed_stages[-1] is StageName.DECOMPOSE_ASSUMPTIONS
    resumed_executor = RecordingExecutor()
    resumed = IdeaPipelineFlow.resume(
        "run-1", checkpoint_store=store, executor=resumed_executor
    )
    resumed.kickoff()
    assert resumed_executor.calls == STAGE_ORDER[5:]
    assert resumed.state.run_error is None
    assert resumed.state.completed_stages == STAGE_ORDER
