"""Queryable persistence for model/task and residency-phase performance."""

from __future__ import annotations

from sqlalchemy import insert, select

from dbie.models.performance import (
    ModelPerformanceRecord,
    ModelPhasePerformanceRecord,
)
from dbie.models.roles import ModelRole
from dbie.persistence.db import Database
from dbie.persistence.schema import (
    model_performance_records,
    model_phase_performance_records,
)


class ModelPerformanceRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record(self, item: ModelPerformanceRecord) -> None:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(model_performance_records).values(
                    model_run_id=item.model_run_id,
                    run_id=item.run_id,
                    venture_id=item.venture_id,
                    crew_id=item.crew_id,
                    agent_id=item.agent_id,
                    task_id=item.task_id,
                    task_class=item.task_class.value,
                    model_role=item.model_role.value,
                    model_id=item.model_id,
                    task_success=str(item.task_success).lower(),
                    created_at=item.created_at,
                    payload=item.model_dump(mode="json"),
                )
            )

    def record_phase(self, item: ModelPhasePerformanceRecord) -> None:
        with self.database.engine.begin() as connection:
            connection.execute(
                insert(model_phase_performance_records).values(
                    phase_run_id=item.phase_run_id,
                    run_id=item.run_id,
                    phase_id=item.phase_id,
                    model_role=item.model_role.value,
                    model_id=item.model_id,
                    dependency_barrier=item.dependency_barrier,
                    created_at=item.created_at,
                    payload=item.model_dump(mode="json"),
                )
            )

    def for_task(self, task_id: str) -> list[ModelPerformanceRecord]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(model_performance_records.c.payload)
                .where(model_performance_records.c.task_id == task_id)
                .order_by(model_performance_records.c.created_at)
            ).scalars()
            return [ModelPerformanceRecord.model_validate(row) for row in rows]

    def for_role(self, run_id: str, role: ModelRole) -> list[ModelPerformanceRecord]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(model_performance_records.c.payload)
                .where(
                    model_performance_records.c.run_id == run_id,
                    model_performance_records.c.model_role == role.value,
                )
                .order_by(model_performance_records.c.created_at)
            ).scalars()
            return [ModelPerformanceRecord.model_validate(row) for row in rows]

    def phases_for_run(self, run_id: str) -> list[ModelPhasePerformanceRecord]:
        with self.database.engine.connect() as connection:
            rows = connection.execute(
                select(model_phase_performance_records.c.payload)
                .where(model_phase_performance_records.c.run_id == run_id)
                .order_by(model_phase_performance_records.c.dependency_barrier)
            ).scalars()
            return [ModelPhasePerformanceRecord.model_validate(row) for row in rows]
