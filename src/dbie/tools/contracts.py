"""The ten stable CrewAI-visible logical tool contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolName(StrEnum):
    WEB_SEARCH = "web_search"
    FETCH_PAGE = "fetch_page"
    SEARCH_COMMUNITY = "search_community"
    SEARCH_COMPANIES = "search_companies"
    SEARCH_GITHUB = "search_github"
    SEARCH_REGULATIONS = "search_regulations"
    READ_DOCUMENT = "read_document"
    PYTHON_EXECUTE = "python_execute"
    DATABASE_QUERY = "database_query"
    SEMANTIC_MEMORY_SEARCH = "semantic_memory_search"


class IndependenceRequirement(StrEnum):
    NONE = "NONE"
    NEW_SOURCE_FAMILY = "NEW_SOURCE_FAMILY"
    PRIMARY_SOURCE = "PRIMARY_SOURCE"


class ToolBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_cost: float = Field(default=0, ge=0)
    timeout_seconds: float = Field(default=30, gt=0)
    max_calls: int = Field(default=20, ge=1)
    max_retries: int = Field(default=1, ge=0, le=3)


class ToolCallEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    stage_id: str
    task_id: str
    actor_id: str
    candidate_id: str | None = None
    assumption_id: str | None = None
    tool: ToolName
    arguments: dict[str, Any]
    purpose: str = Field(min_length=1)
    expected_evidence: str | None = None
    independence_requirement: IndependenceRequirement = IndependenceRequirement.NONE
    budget: ToolBudget = Field(default_factory=ToolBudget)


class SourceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_identifier: str
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str | None = None
    source_type: str | None = None


class AdapterProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    adapter_version: str | None = None
    started_at: datetime
    ended_at: datetime
    latency_seconds: float = Field(ge=0)
    cache_hit: bool = False
    retry_count: int = Field(default=0, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    resource_usage: dict[str, float] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolName
    payload: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceProvenance] = Field(default_factory=list)
    adapter_provenance: list[AdapterProvenance] = Field(default_factory=list)
    cost: float = Field(default=0, ge=0)
    cache_status: str = "MISS"
    error_category: str | None = None
    elapsed_seconds: float = Field(default=0, ge=0)
