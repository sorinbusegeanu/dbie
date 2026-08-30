from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdapterCapabilities(BaseModel):
    operations: set[str] = Field(default_factory=set)
    media_types: set[str] = Field(default_factory=set)
    side_effect_free: bool = True


class AdapterHealth(BaseModel):
    name: str
    available: bool
    version: str | None = None
    detail: str | None = None


class AdapterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    arguments: dict[str, Any]
    timeout_seconds: float = Field(gt=0)


class AdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] = Field(default_factory=dict)
    raw_sources: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resource_usage: dict[str, float] = Field(default_factory=dict)
    cost: float = Field(default=0, ge=0)
    executed_adapter: str | None = None
    retry_count: int = Field(default=0, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    error_category: str | None = None
    attempts: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    adapter_version: str | None = None


class ToolAdapter(ABC):
    name: str
    capabilities: AdapterCapabilities

    @abstractmethod
    def health(self) -> AdapterHealth:
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: AdapterRequest) -> AdapterResult:
        raise NotImplementedError
