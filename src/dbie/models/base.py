"""Provider-neutral generation interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from dbie.models.capabilities import ModelCapabilities, ProviderHealth


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_tokens: int | None = Field(default=None, gt=0)
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    thinking: bool | None = None
    tools: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageSnapshot(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    requests: int = 0


class GenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    content: str
    latency_seconds: float = Field(ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    structured_output_valid: bool | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, model: str, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError

    @abstractmethod
    def structured_generate(
        self, model: str, request: GenerationRequest, schema: type[SchemaT]
    ) -> SchemaT:
        raise NotImplementedError

    @abstractmethod
    def tool_call(self, model: str, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self, model: str) -> ModelCapabilities:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def usage(self) -> UsageSnapshot:
        raise NotImplementedError
