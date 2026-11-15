from pathlib import Path

from dbie.config import Settings
from dbie.domain.enums import (
    ApprovalStatus,
    CandidateState,
    EvidenceDirection,
    EvidenceTier,
    EvidenceType,
    RunStatus,
)
from dbie.domain.models import (
    EvidenceItem,
    Experiment,
    ExperimentOutcome,
    ExperimentPrediction,
)
from dbie.persistence.db import Database
from dbie.persistence.repositories import (
    CandidateRepository,
    EventRepository,
    EvidenceRepository,
    ExperimentOutcomeRepository,
    ExperimentPredictionRepository,
    ExperimentRepository,
    RunRepository,
)
from dbie.services.candidate_service import CandidateService
from dbie.services.run_service import RunService
from tests.conftest import make_idea


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'dbie.sqlite3'}",
        run_directory=tmp_path / "runs",
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


def test_experiment_protocol_prediction_and_outcome_are_separate_records(
    tmp_path: Path,
) -> None:
    database = Database(f"sqlite:///{tmp_path / 'experiments.sqlite3'}")
    database.initialize()
    experiment = ExperimentRepository(database).create(
        Experiment(
            run_id="run-1",
            idea_id="idea-1",
            assumption_id="assumption-1",
            hypothesis="At least ten percent of qualified visitors request access.",
            metric="Qualified request rate",
            threshold=">= 10%",
            sample_definition="100 unique qualified visitors",
            stop_condition="Stop after 100 qualified visitors or 30 days",
        )
    )
    prediction = ExperimentPredictionRepository(database).create(
        ExperimentPrediction(
            run_id="run-1",
            experiment_id=experiment.id,
            predicted_value="12%",
            rationale="The research evidence supports bounded buyer urgency.",
            predicted_metrics={"conversion_rate": 0.12, "revenue": 12000},
            scenario_intervals={"conversion_rate": {"lower": 0.08, "upper": 0.16}},
        )
    )
    outcome = ExperimentOutcomeRepository(database).create(
        ExperimentOutcome(
            run_id="run-1",
            experiment_id=experiment.id,
            observed_value="8%",
            sample_size=100,
            raw_artifact_refs=["artifact://events-1"],
            interpretation="The preregistered threshold was not met.",
            measured_at="2026-01-15T00:00:00Z",
            observed_metrics={"conversion_rate": 0.08, "revenue": 8000},
            evidence_source_ids=["artifact://events-1"],
        )
    )

    assert experiment.approval_status is ApprovalStatus.REQUIRED
    assert prediction.locked_at is not None
    assert ExperimentRepository(database).for_run("run-1") == [experiment]
    assert ExperimentPredictionRepository(database).for_run("run-1") == [prediction]
    assert ExperimentOutcomeRepository(database).for_run("run-1") == [outcome]
    assert ExperimentPredictionRepository(database).for_run("run-1")[0].predicted_metrics.conversion_rate == 0.12
    assert ExperimentOutcomeRepository(database).for_run("run-1")[0].evidence_source_ids == ["artifact://events-1"]
