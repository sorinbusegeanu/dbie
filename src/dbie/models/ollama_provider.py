"""Ollama implementation of the provider-neutral model contract."""

from __future__ import annotations

import json
from time import monotonic
from typing import Any

import httpx
from pydantic import ValidationError

from dbie.config import ModelProfile, OllamaSettings
from dbie.exceptions import (
    ModelProviderError,
    ModelUnavailableError,
    StructuredOutputError,
)
from dbie.models.base import (
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    SchemaT,
    UsageSnapshot,
)
from dbie.models.capabilities import ModelCapabilities, ProviderHealth


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        settings: OllamaSettings,
        profiles: dict[str, ModelProfile],
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._profiles_by_model = {
            profile.model: profile for profile in profiles.values()
        }
        self._client = client or httpx.Client(
            base_url=settings.base_url.rstrip("/"),
            timeout=settings.timeout_seconds,
        )
        self._usage = UsageSnapshot()

    def generate(self, model: str, request: GenerationRequest) -> GenerationResponse:
        return self._chat(model, request)

    def structured_generate(
        self, model: str, request: GenerationRequest, schema: type[SchemaT]
    ) -> SchemaT:
        response = self._chat(model, request, output_schema=schema.model_json_schema())
        try:
            return schema.model_validate_json(response.content)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"{model} returned schema-invalid JSON: {exc}"
            ) from exc

    def tool_call(self, model: str, request: GenerationRequest) -> GenerationResponse:
        if not request.tools:
            raise ModelProviderError("tool_call requires at least one tool schema")
        return self._chat(model, request)

    def capabilities(self, model: str) -> ModelCapabilities:
        try:
            profile = self._profiles_by_model[model]
        except KeyError as exc:
            raise ModelUnavailableError(f"unconfigured Ollama model: {model}") from exc
        return ModelCapabilities(
            model=model,
            context_tokens=profile.maximum_context_tokens,
            reasoning=profile.reasoning,
            tools=profile.tools,
            structured_output=profile.structured_output,
        )

    def health(self) -> ProviderHealth:
        try:
            version_response = self._client.get("/api/version")
            version_response.raise_for_status()
            tags_response = self._client.get("/api/tags")
            tags_response.raise_for_status()
            tags = tags_response.json().get("models", [])
            installed = [item["name"] for item in tags if "name" in item]
            return ProviderHealth(
                provider=self.name,
                reachable=True,
                version=version_response.json().get("version"),
                installed_models=installed,
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            return ProviderHealth(
                provider=self.name,
                reachable=False,
                error=str(exc),
            )

    def usage(self) -> UsageSnapshot:
        return self._usage.model_copy(deep=True)

    def _chat(
        self,
        model: str,
        request: GenerationRequest,
        output_schema: dict[str, Any] | None = None,
    ) -> GenerationResponse:
        profile = self._profiles_by_model.get(model)
        if profile is None:
            raise ModelUnavailableError(f"unconfigured Ollama model: {model}")
        context_tokens = request.context_tokens or profile.request_context_tokens
        if context_tokens > profile.maximum_context_tokens:
            raise ModelProviderError(
                f"requested context {context_tokens} exceeds {model} profile maximum "
                f"{profile.maximum_context_tokens}"
            )

        body: dict[str, Any] = {
            "model": model,
            "messages": [_ollama_message(message) for message in request.messages],
            "stream": False,
            "keep_alive": self.settings.keep_alive,
            "options": {
                "num_ctx": context_tokens,
                "num_predict": profile.maximum_output_tokens,
            },
        }
        if request.temperature is not None:
            body["options"]["temperature"] = request.temperature
        if request.thinking is not None:
            body["think"] = request.thinking
        elif request.reasoning_effort is not None:
            body["think"] = request.reasoning_effort
        if request.tools:
            body["tools"] = request.tools
        if output_schema is not None:
            body["format"] = output_schema

        started = monotonic()
        try:
            response = self._client.post("/api/chat", json=body)
            if response.status_code == 404 and "model" in response.text.lower():
                raise ModelUnavailableError(f"Ollama model unavailable: {model}")
            response.raise_for_status()
            data = response.json()
        except ModelUnavailableError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelProviderError(
                f"Ollama request failed for {model}: {exc}"
            ) from exc

        elapsed = monotonic() - started
        message = data.get("message") or {}
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        self._usage.prompt_tokens += int(prompt_tokens or 0)
        self._usage.completion_tokens += int(completion_tokens or 0)
        self._usage.requests += 1
        return GenerationResponse(
            provider=self.name,
            model=data.get("model", model),
            content=message.get("content", ""),
            latency_seconds=elapsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=data.get("done_reason"),
            tool_calls=message.get("tool_calls") or [],
            structured_output_valid=output_schema is not None,
            raw=data,
        )


def _ollama_message(message: Any) -> dict[str, Any]:
    """Preserve CrewAI's native tool-call history in Ollama's chat schema."""
    value: dict[str, Any] = {
        "role": message.role,
        "content": message.content or "",
    }
    if message.tool_calls:
        calls = []
        for call in message.tool_calls:
            copied = dict(call)
            function = dict(copied.get("function") or {})
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    function["arguments"] = json.loads(arguments)
                except json.JSONDecodeError:
                    function["arguments"] = {}
            copied["function"] = function
            calls.append(copied)
        value["tool_calls"] = calls
    if message.role == "tool" and message.name:
        value["tool_name"] = message.name
    return value
