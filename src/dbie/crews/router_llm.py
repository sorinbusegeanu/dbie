"""CrewAI BaseLLM implementation backed only by DBIE's Model Router."""

from __future__ import annotations

import json
from time import monotonic
from typing import Any

from crewai.llms.base_llm import BaseLLM

from dbie.models.base import ChatMessage, GenerationRequest
from dbie.models.performance import (
    ModelExecutionContext,
    ModelPerformanceRecord,
    ModelPerformanceSink,
)
from dbie.models.roles import ModelRole, ModelSelection
from dbie.models.router import ModelRouter


class RouterLLM(BaseLLM):
    router: ModelRouter
    profile_name: str | None
    model_role: ModelRole | None
    selection: ModelSelection
    execution_context: ModelExecutionContext | None
    performance_sink: ModelPerformanceSink | None

    def __init__(
        self,
        router: ModelRouter,
        *,
        model: str = "dbie-router",
        profile_name: str | None = None,
        model_role: ModelRole | None = None,
        selection: ModelSelection = ModelSelection.PRIMARY,
        execution_context: ModelExecutionContext | None = None,
        performance_sink: ModelPerformanceSink | None = None,
        temperature: float | None = None,
    ) -> None:
        if profile_name is not None and model_role is not None:
            raise ValueError("select either a profile or a model role, not both")
        super().__init__(
            model=model,
            provider="dbie",
            temperature=temperature,
            router=router,
            profile_name=profile_name,
            model_role=model_role,
            selection=selection,
            execution_context=execution_context,
            performance_sink=performance_sink,
        )

    def for_role(
        self,
        role: ModelRole,
        *,
        selection: ModelSelection = ModelSelection.PRIMARY,
    ) -> RouterLLM:
        return RouterLLM(
            self.router,
            model=f"dbie-{role.value.lower()}",
            model_role=role,
            selection=selection,
            performance_sink=self.performance_sink,
            temperature=self.temperature,
        )

    def for_execution(
        self,
        role: ModelRole,
        context: ModelExecutionContext,
        *,
        selection: ModelSelection = ModelSelection.PRIMARY,
    ) -> RouterLLM:
        value = self.for_role(role, selection=selection)
        value.execution_context = context
        return value

    def call(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[Any] | None = None,
    ) -> str | Any:
        del callbacks, from_task, from_agent
        normalized = (
            [ChatMessage(role="user", content=messages)]
            if isinstance(messages, str)
            else [
                ChatMessage(
                    role=item.get("role", "user"),
                    content=(
                        None
                        if item.get("content") is None
                        else str(item.get("content", ""))
                    ),
                    tool_calls=list(item.get("tool_calls") or []),
                    tool_call_id=item.get("tool_call_id"),
                    name=item.get("name"),
                )
                for item in messages
                if item.get("role") in {"system", "user", "assistant", "tool"}
            ]
        )
        effective_temperature = self.temperature
        if effective_temperature is None and self.execution_context is not None:
            effective_temperature = self.router.config.task_temperatures.get(
                self.execution_context.task_class, 0.1
            )
        request = GenerationRequest(
            messages=normalized,
            temperature=effective_temperature,
            tools=tools or [],
        )
        started = monotonic()
        try:
            if response_model is not None:
                if self.model_role is not None:
                    value = self.router.structured_generate_for_role(
                        request,
                        response_model,
                        role=self.model_role,
                        selection=self.selection,
                    )
                else:
                    value = self.router.structured_generate(
                        request, response_model, profile_name=self.profile_name
                    )
                self._record(
                    request=request,
                    started=started,
                    response=None,
                    schema_valid=True,
                )
                return value
            if self.model_role is not None:
                response = (
                    self.router.tool_call_for_role(
                        request, role=self.model_role, selection=self.selection
                    )
                    if tools
                    else self.router.generate_for_role(
                        request, role=self.model_role, selection=self.selection
                    )
                )
            else:
                response = (
                    self.router.tool_call(request, profile_name=self.profile_name)
                    if tools
                    else self.router.generate(request, profile_name=self.profile_name)
                )
            self._record(
                request=request,
                started=started,
                response=response,
                schema_valid=response.structured_output_valid,
            )
            if response.tool_calls:
                if available_functions:
                    return self._execute_first_tool(
                        response.tool_calls, available_functions
                    )
                # CrewAI's native-tool executor deliberately calls BaseLLM with
                # ``available_functions=None`` and expects the provider-native
                # tool-call list back.  Returning JSON text here makes CrewAI
                # treat the call as a final answer, so the logical DBIE tool is
                # never executed.
                return response.tool_calls
            return response.content
        except Exception as exc:
            self._record(
                request=request,
                started=started,
                response=None,
                schema_valid=False if response_model is not None else None,
                error_category=type(exc).__name__,
            )
            raise

    def _record(
        self,
        *,
        request: GenerationRequest,
        started: float,
        response: Any | None,
        schema_valid: bool | None,
        error_category: str | None = None,
    ) -> None:
        if self.performance_sink is None or self.execution_context is None:
            return
        context = self.execution_context
        if self.model_role is not None:
            resolution = self.router.resolve_role(
                self.model_role, selection=self.selection
            )
            role = self.model_role
            model_id = response.model if response is not None else resolution.model_id
            thinking_mode = resolution.thinking_mode
            context_limit = request.context_tokens or resolution.context_tokens
            runtime = response.provider if response is not None else "ollama"
        else:
            profile_name = self.profile_name or self.router.config.default_profile
            profile = self.router.config.profiles[profile_name]
            role = role_for_unclassified_context(context.task_class)
            model_id = response.model if response is not None else profile.model
            thinking_mode = "adaptive"
            context_limit = request.context_tokens or profile.request_context_tokens
            runtime = response.provider if response is not None else profile.provider
        elapsed = monotonic() - started
        output_tokens = response.completion_tokens if response is not None else None
        tokens_per_second = (
            output_tokens / elapsed
            if output_tokens is not None and elapsed > 0
            else None
        )
        self.performance_sink.record(
            ModelPerformanceRecord(
                run_id=context.run_id,
                venture_id=context.venture_id,
                crew_id=context.crew_id,
                agent_id=context.agent_id,
                task_id=context.task_id,
                task_class=context.task_class,
                model_role=role,
                model_id=model_id,
                effective_temperature=request.temperature,
                skill_ids=context.skill_ids,
                runtime=runtime,
                thinking_mode=thinking_mode,
                context_limit=context_limit,
                input_tokens=response.prompt_tokens if response is not None else None,
                output_tokens=output_tokens,
                wall_clock_ms=elapsed * 1000,
                tokens_per_second=tokens_per_second,
                tool_calls=len(response.tool_calls) if response is not None else 0,
                schema_valid=schema_valid,
                task_success=error_category is None,
                escalated=role is ModelRole.JUDGE,
                error_category=error_category,
            )
        )

    @staticmethod
    def _execute_first_tool(
        tool_calls: list[dict[str, Any]], functions: dict[str, Any]
    ) -> Any:
        function = tool_calls[0].get("function", {})
        name = function.get("name")
        if name not in functions:
            return json.dumps({"error": "tool unavailable", "tool": name})
        arguments = function.get("arguments") or {}
        return functions[name](**arguments)

    def supports_function_calling(self) -> bool:
        return True

    def supports_stop_words(self) -> bool:
        return True


def role_for_unclassified_context(task_class: Any) -> ModelRole:
    from dbie.models.task_roles import role_for_task

    return role_for_task(task_class)
