from uuid import uuid4

from dbie.flows.checkpoints import JsonCheckpointStore
from dbie.flows.idea_pipeline import IdeaPipelineFlow
from dbie.flows.state import STAGE_ORDER, PipelineState
from dbie.persistence.db import Database
from dbie.persistence.repositories import RunRepository
from dbie.services.fixture_mvp import FixtureMVPExecutor


def test_full_mvp_fixture_runs_without_manual_intermediate_edits(tmp_path) -> None:
    run_id = str(uuid4())
    database = Database(f"sqlite:///{tmp_path / 'mvp.sqlite3'}")
    checkpoints = JsonCheckpointStore(tmp_path / "runs")
    state = PipelineState(run_id=run_id, mandate="Find digital compliance products")
    flow = IdeaPipelineFlow(
        state=state,
        executor=FixtureMVPExecutor(database, tmp_path / "artifacts"),
        checkpoint_store=checkpoints,
    )

    flow.kickoff()

    assert flow.state.completed_stages == STAGE_ORDER
    assert len(flow.state.finalist_ids) == 2
    assert len(flow.state.artifacts["dossier_paths"]) == 4
    assert RunRepository(database).get(run_id).status.value == "COMPLETED"
    assert checkpoints.load(run_id).artifacts["raw_idea_count"] == 50
