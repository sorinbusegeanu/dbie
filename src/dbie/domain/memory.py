"""Versioned structured business-research lessons."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class BusinessLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: int = Field(default=1, ge=1)
    category: str = Field(min_length=1)
    opportunity_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    attempted_or_assumed: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    observed_result: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_behavior: str = Field(min_length=1)
    applicability_conditions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    validation_status: Literal["OBSERVED", "HYPOTHESIS", "VALIDATED"] = "HYPOTHESIS"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revised_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

