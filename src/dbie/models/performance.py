"""Operational model records; explicitly not business evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from dbie.models.roles import ModelRole
from dbie.models.task_roles import TaskClass


class ModelExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    venture_id: str | None = None
    crew_id: str
    agent_id: str
    task_id: str
    task_class: TaskClass
    skill_ids: list[str] = Field(default_factory=list)


class ModelPerformanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_run_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    venture_id: str | None = None
    crew_id: str
    agent_id: str
    task_id: str
    task_class: TaskClass
    model_role: ModelRole
    model_id: str
    effective_temperature: float | None = Field(default=None, ge=0, le=2)
    skill_ids: list[str] = Field(default_factory=list)
    model_version_or_digest: str | None = None
    quantization: str | None = None
    runtime: str
    thinking_mode: str
    context_limit: int
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    wall_clock_ms: float = Field(ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    tokens_per_second: float | None = Field(default=None, ge=0)
    peak_vram_mb: float | None = Field(default=None, ge=0)
    queue_wait_ms: float = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    tool_failures: int = Field(default=0, ge=0)
    schema_valid: bool | None = None
    task_success: bool
    retry_count: int = Field(default=0, ge=0)
    escalated: bool = False
    estimated_cost: float = Field(default=0, ge=0)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    judge_score: float | None = Field(default=None, ge=0, le=1)
    downstream_outcome_id: str | None = None
    error_category: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelPhasePerformanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase_run_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    phase_id: str
    model_role: ModelRole
    resolved_profile: str
    model_id: str
    dependency_barrier: int = Field(ge=0)
    model_load_ms: float | None = Field(default=None, ge=0)
    model_unload_ms: float | None = Field(default=None, ge=0)
    switch_count: int = Field(default=0, ge=0)
    gpu_idle_during_switch_ms: float | None = Field(default=None, ge=0)
    tasks_per_model_residency: int = Field(ge=1)
    tokens_per_model_residency: int = Field(default=0, ge=0)
    useful_work_per_residency: float | None = Field(default=None, ge=0)
    phase_duration_ms: float = Field(ge=0)
    barrier_wait_ms: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class ModelPerformanceSink(Protocol):
    def record(self, item: ModelPerformanceRecord) -> None: ...

    def record_phase(self, item: ModelPhasePerformanceRecord) -> None: ...
