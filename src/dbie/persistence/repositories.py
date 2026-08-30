"""Typed repositories and append-only event recording."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import insert, select, update

from dbie.domain.enums import CandidateState, RunStatus
from dbie.domain.models import (
    Assumption,
    BusinessIdea,
    Evaluation,
    EvidenceItem,
    Experiment,
    ExperimentOutcome,
    ExperimentPrediction,
    PairwiseMatch,
    Run,
)
from dbie.exceptions import PersistenceError
from dbie.persistence.db import Database
from dbie.persistence.schema import (
    assumptions,
    evaluations,
    events,
    evidence,
    experiment_outcomes,
    experiment_predictions,
    experiments,
    ideas,
    pairwise_matches,
    runs,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _payload(record: object) -> dict[str, object]:
    return record.model_dump(mode="json")  # type: ignore[attr-defined, no-any-return]


class EventRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def append(
        self,
        *,
        run_id: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload: dict[str, object],
        connection: object | None = None,
    ) -> None:
        values = {
            "event_id": str(uuid4()),
            "run_id": run_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            "created_at": _now(),
            "payload": payload,
        }
        if connection is not None:
            connection.execute(insert(events).values(**values))  # type: ignore[attr-defined]
            return
        with self.database.engine.begin() as active:
            active.execute(insert(events).values(**values))

    def for_entity(self, entity_type: str, entity_id: str) -> list[dict[str, object]]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(events)
                .where(
                    events.c.entity_type == entity_type,
                    events.c.entity_id == entity_id,
                )
                .order_by(events.c.sequence)
            ).mappings()
            return [dict(row) for row in rows]


class RunRepository:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.events = EventRepository(database)

    def create(self, run: Run) -> Run:
        now = _now()
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(runs).values(
                    id=run.id,
                    status=run.status.value,
                    mandate=run.mandate,
                    schema_version=run.schema_version,
                    created_at=run.created_at,
                    updated_at=now,
                    payload=_payload(run),
                )
            )
            self.events.append(
                run_id=run.id,
                entity_type="Run",
                entity_id=run.id,
                event_type="RUN_CREATED",
                payload={"status": run.status.value},
                connection=connection,
            )
        return run

    def get(self, run_id: str) -> Run:
        with self.database.engine.connect() as connection:
            row = connection.execute(
                select(runs.c.payload).where(runs.c.id == run_id)
            ).scalar_one_or_none()
        if row is None:
            raise PersistenceError(f"run not found: {run_id}")
        return Run.model_validate(row)

    def set_status(self, run_id: str, status: RunStatus) -> Run:
        run = self.get(run_id)
        run.status = status
        if status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            run.closed_at = _now()
        with self.database.engine.begin() as connection:
            result = connection.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(status=status.value, updated_at=_now(), payload=_payload(run))
            )
            if result.rowcount != 1:
                raise PersistenceError(f"run not found during status update: {run_id}")
            self.events.append(
                run_id=run_id,
                entity_type="Run",
                entity_id=run_id,
                event_type="RUN_STATUS_CHANGED",
                payload={"status": status.value},
                connection=connection,
            )
        return run


class CandidateRepository:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.events = EventRepository(database)

    def create(self, idea: BusinessIdea) -> BusinessIdea:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(ideas).values(
                    id=idea.id,
                    run_id=idea.run_id,
                    problem_id=idea.problem_id,
                    state=idea.lifecycle_state.value,
                    schema_version=idea.schema_version,
                    created_at=idea.created_at,
                    updated_at=_now(),
                    payload=_payload(idea),
                )
            )
            self.events.append(
                run_id=idea.run_id,
                entity_type="BusinessIdea",
                entity_id=idea.id,
                event_type="IDEA_CREATED",
                payload={"state": idea.lifecycle_state.value},
                connection=connection,
            )
        return idea

    def get(self, idea_id: str) -> BusinessIdea:
        with self.database.engine.connect() as connection:
            row = connection.execute(
                select(ideas.c.payload).where(ideas.c.id == idea_id)
            ).scalar_one_or_none()
        if row is None:
            raise PersistenceError(f"idea not found: {idea_id}")
        return BusinessIdea.model_validate(row)

    def for_run(self, run_id: str) -> list[BusinessIdea]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(ideas.c.payload).where(ideas.c.run_id == run_id)
            ).scalars()
            return [BusinessIdea.model_validate(row) for row in rows]

    def set_state(self, idea_id: str, state: CandidateState) -> BusinessIdea:
        idea = self.get(idea_id)
        idea.lifecycle_state = state
        with self.database.engine.begin() as connection:
            result = connection.execute(
                update(ideas)
                .where(ideas.c.id == idea_id)
                .values(state=state.value, updated_at=_now(), payload=_payload(idea))
            )
            if result.rowcount != 1:
                raise PersistenceError(f"idea not found during state update: {idea_id}")
            self.events.append(
                run_id=idea.run_id,
                entity_type="BusinessIdea",
                entity_id=idea.id,
                event_type="IDEA_STATE_CHANGED",
                payload={"state": state.value},
                connection=connection,
            )
        return idea


class AssumptionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, assumption: Assumption) -> Assumption:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(assumptions).values(
                    id=assumption.id,
                    run_id=assumption.run_id,
                    idea_id=assumption.idea_id,
                    category=assumption.category.value,
                    criticality=assumption.criticality.value,
                    status=assumption.status.value,
                    schema_version=assumption.schema_version,
                    created_at=assumption.created_at,
                    updated_at=_now(),
                    payload=_payload(assumption),
                )
            )
        return assumption

    def for_idea(self, idea_id: str) -> list[Assumption]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(assumptions.c.payload).where(assumptions.c.idea_id == idea_id)
            ).scalars()
            return [Assumption.model_validate(row) for row in rows]

    def get(self, assumption_id: str) -> Assumption:
        with self.database.engine.connect() as connection:
            row = connection.execute(
                select(assumptions.c.payload).where(assumptions.c.id == assumption_id)
            ).scalar_one_or_none()
        if row is None:
            raise PersistenceError(f"assumption not found: {assumption_id}")
        return Assumption.model_validate(row)

    def for_run(self, run_id: str) -> list[Assumption]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(assumptions.c.payload).where(assumptions.c.run_id == run_id)
            ).scalars()
            return [Assumption.model_validate(row) for row in rows]

    def save(self, assumption: Assumption) -> Assumption:
        with self.database.engine.begin() as connection:
            result = connection.execute(
                update(assumptions)
                .where(assumptions.c.id == assumption.id)
                .values(
                    status=assumption.status.value,
                    updated_at=_now(),
                    payload=_payload(assumption),
                )
            )
        if result.rowcount != 1:
            raise PersistenceError(f"assumption not found: {assumption.id}")
        return assumption


class EvidenceRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: EvidenceItem) -> EvidenceItem:
        with self.database.engine.begin() as connection:
            existing = connection.execute(
                select(evidence.c.payload).where(
                    evidence.c.content_hash == item.content_hash,
                    evidence.c.lineage_group_id == item.lineage_group_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return EvidenceItem.model_validate(existing)
            connection.execute(
                insert(evidence).values(
                    id=item.id,
                    run_id=item.run_id,
                    lineage_group_id=item.lineage_group_id,
                    content_hash=item.content_hash,
                    tier=item.tier.value,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def get(self, evidence_id: str) -> EvidenceItem:
        with self.database.engine.connect() as connection:
            row = connection.execute(
                select(evidence.c.payload).where(evidence.c.id == evidence_id)
            ).scalar_one_or_none()
        if row is None:
            raise PersistenceError(f"evidence not found: {evidence_id}")
        return EvidenceItem.model_validate(row)

    def for_run(self, run_id: str) -> list[EvidenceItem]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(evidence.c.payload).where(evidence.c.run_id == run_id)
            ).scalars()
            return [EvidenceItem.model_validate(row) for row in rows]


class EvaluationRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: Evaluation) -> Evaluation:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(evaluations).values(
                    id=item.id,
                    run_id=item.run_id,
                    idea_id=item.idea_id,
                    evaluator_actor_id=item.evaluator_actor_id,
                    recommendation=item.recommendation.value,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def for_idea(self, idea_id: str) -> list[Evaluation]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(evaluations.c.payload).where(evaluations.c.idea_id == idea_id)
            ).scalars()
            return [Evaluation.model_validate(row) for row in rows]


class PairwiseMatchRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: PairwiseMatch) -> PairwiseMatch:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(pairwise_matches).values(
                    id=item.id,
                    run_id=item.run_id,
                    left_idea_id=item.left_idea_id,
                    right_idea_id=item.right_idea_id,
                    winner_idea_id=item.winner_idea_id,
                    judge_model=item.judge_model,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def for_run(self, run_id: str) -> list[PairwiseMatch]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(pairwise_matches.c.payload).where(
                    pairwise_matches.c.run_id == run_id
                )
            ).scalars()
            return [PairwiseMatch.model_validate(row) for row in rows]


class ExperimentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: Experiment) -> Experiment:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(experiments).values(
                    id=item.id,
                    run_id=item.run_id,
                    idea_id=item.idea_id,
                    assumption_id=item.assumption_id,
                    approval_status=item.approval_status.value,
                    protocol_version=item.protocol_version,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def for_run(self, run_id: str) -> list[Experiment]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(experiments.c.payload).where(experiments.c.run_id == run_id)
            ).scalars()
            return [Experiment.model_validate(row) for row in rows]


class ExperimentPredictionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: ExperimentPrediction) -> ExperimentPrediction:
        if item.locked_at is None:
            item = item.model_copy(update={"locked_at": _now()})
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(experiment_predictions).values(
                    id=item.id,
                    run_id=item.run_id,
                    experiment_id=item.experiment_id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def for_run(self, run_id: str) -> list[ExperimentPrediction]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(experiment_predictions.c.payload).where(
                    experiment_predictions.c.run_id == run_id
                )
            ).scalars()
            return [ExperimentPrediction.model_validate(row) for row in rows]


class ExperimentOutcomeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: ExperimentOutcome) -> ExperimentOutcome:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(experiment_outcomes).values(
                    id=item.id,
                    run_id=item.run_id,
                    experiment_id=item.experiment_id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    payload=_payload(item),
                )
            )
        return item

    def for_run(self, run_id: str) -> list[ExperimentOutcome]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(experiment_outcomes.c.payload).where(
                    experiment_outcomes.c.run_id == run_id
                )
            ).scalars()
            return [ExperimentOutcome.model_validate(row) for row in rows]
