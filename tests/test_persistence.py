from pathlib import Path

from dbie.config import Settings
from dbie.domain.enums import (
    CandidateState,
    EvidenceDirection,
    EvidenceTier,
    EvidenceType,
    RunStatus,
)
from dbie.domain.models import EvidenceItem
from dbie.persistence.db import Database
from dbie.persistence.repositories import (
    CandidateRepository,
    EventRepository,
    EvidenceRepository,
    RunRepository,
)
from dbie.services.candidate_service import CandidateService
from dbie.services.run_service import RunService
from tests.conftest import make_idea


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'dbie.sqlite3'}",
        models_config=Path("config/models.yaml"),
        tools_config=Path("config/tools.yaml"),
        policies_config=Path("config/policies.yaml"),
    )


def test_run_and_candidate_round_trip(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    database = Database(settings.database_url)
    database.initialize()
    runs = RunService(RunRepository(database), settings)
    candidates = CandidateService(CandidateRepository(database))

    run = runs.create("Find a bounded digital opportunity")
    resumed = runs.resume(run.id)
    idea = make_idea(run_id=run.id)
    candidates.register(idea)
    eligibility = candidates.apply_eligibility(idea.id)
    reloaded = candidates.repository.get(idea.id)
    closed = runs.close(run.id)

    assert resumed.status is RunStatus.RUNNING
    assert eligibility.eligible is True
    assert reloaded.id == idea.id
    assert reloaded.lifecycle_state is CandidateState.ELIGIBLE
    assert closed.status is RunStatus.COMPLETED
    assert RunRepository(database).get(run.id).closed_at is not None


def test_duplicate_evidence_reuses_canonical_record(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'dbie.sqlite3'}")
    database.initialize()
    repository = EvidenceRepository(database)
    first = EvidenceItem(
        run_id="run-1",
        source_identifier="official-report",
        source_type="report",
        extracted_fact="Measured result",
        tier=EvidenceTier.PRIMARY,
        evidence_type=EvidenceType.MEASURED,
        direction=EvidenceDirection.SUPPORTS,
        reliability_score=1,
        freshness_score=1,
        lineage_group_id="lineage-1",
        content_hash="0123456789abcdef",
    )
    duplicate = first.model_copy(update={"id": "different-id"})

    stored = repository.create(first)
    reused = repository.create(duplicate)

    assert reused.id == stored.id


def test_state_changes_are_reconstructable_from_ordered_events(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    database = Database(settings.database_url)
    database.initialize()
    runs = RunService(RunRepository(database), settings)
    candidates = CandidateService(CandidateRepository(database))
    run = runs.create("Event reconstruction")
    idea = make_idea(run_id=run.id)
    candidates.register(idea)
    candidates.apply_eligibility(idea.id)

    history = EventRepository(database).for_entity("BusinessIdea", idea.id)

    assert [event["event_type"] for event in history] == [
        "IDEA_CREATED",
        "IDEA_STATE_CHANGED",
    ]
    assert history[-1]["payload"] == {"state": "ELIGIBLE"}
