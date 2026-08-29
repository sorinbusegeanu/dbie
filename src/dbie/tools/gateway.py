"""Authoritative permission, budget, cache, audit, and adapter boundary."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from time import monotonic

from pydantic import ValidationError

from dbie.exceptions import (
    ToolBudgetExceeded,
    ToolExecutionError,
    ToolInputValidationError,
    ToolPermissionDenied,
)
from dbie.tools.adapters.base import AdapterRequest
from dbie.tools.adapters.registry import AdapterRegistry
from dbie.tools.audit import InMemoryAuditSink, ToolAuditRecord
from dbie.tools.cache import InMemoryToolCache
from dbie.tools.contracts import (
    AdapterProvenance,
    SourceProvenance,
    ToolCallEnvelope,
    ToolName,
    ToolResult,
)
from dbie.tools.logical import LOGICAL_TOOL_INPUTS
from dbie.tools.logical_outputs import LOGICAL_TOOL_OUTPUTS
from dbie.tools.permissions import ToolPermissionPolicy


class ToolGateway:
    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        routes: dict[ToolName, str],
        permissions: ToolPermissionPolicy,
        cache: InMemoryToolCache | None = None,
        audit: InMemoryAuditSink | None = None,
    ) -> None:
        self.registry = registry
        self.routes = routes
        self.permissions = permissions
        self.cache = cache or InMemoryToolCache()
        self.audit = audit or InMemoryAuditSink()
        self._task_calls: Counter[str] = Counter()

    def invoke(self, envelope: ToolCallEnvelope) -> ToolResult:
        if not self.permissions.allowed(envelope.actor_id, envelope.tool):
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    allowed=False,
                    reason="TOOL_NOT_ALLOWED_FOR_ACTOR",
                )
            )
            raise ToolPermissionDenied(
                f"actor {envelope.actor_id} cannot use {envelope.tool.value}"
            )
        try:
            validated = LOGICAL_TOOL_INPUTS[envelope.tool].model_validate(
                envelope.arguments
            )
            envelope = envelope.model_copy(
                update={"arguments": validated.model_dump(mode="json")}
            )
        except ValidationError as exc:
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    allowed=False,
                    reason="INVALID_TOOL_ARGUMENTS",
                )
            )
            raise ToolInputValidationError(
                "logical tool arguments are invalid"
            ) from exc
        self._task_calls[envelope.task_id] += 1
        if self._task_calls[envelope.task_id] > envelope.budget.max_calls:
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    allowed=False,
                    reason="TASK_CALL_BUDGET_EXCEEDED",
                )
            )
            raise ToolBudgetExceeded(
                f"tool call budget exceeded for {envelope.task_id}"
            )

        cached = self.cache.get(envelope)
        if cached is not None:
            cached.cache_status = "HIT"
            for item in cached.adapter_provenance:
                item.cache_hit = True
            self.audit.write(
                ToolAuditRecord(envelope=envelope, result=cached, allowed=True)
            )
            return cached

        try:
            adapter_name = self.routes[envelope.tool]
            adapter = self.registry.get(adapter_name)
        except KeyError as exc:
            raise ToolExecutionError("logical tool is temporarily unavailable") from exc

        started_at = datetime.now(UTC)
        started = monotonic()
        try:
            raw = adapter.execute(
                AdapterRequest(
                    operation=envelope.tool.value,
                    arguments=envelope.arguments,
                    timeout_seconds=envelope.budget.timeout_seconds,
                )
            )
        except Exception as exc:
            result = ToolResult(
                tool=envelope.tool,
                error_category="ADAPTER_FAILURE",
                elapsed_seconds=monotonic() - started,
            )
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    result=result,
                    allowed=True,
                    reason="ADAPTER_FAILURE",
                )
            )
            raise ToolExecutionError("logical tool execution failed") from exc

        ended_at = datetime.now(UTC)
        elapsed = monotonic() - started
        if elapsed > envelope.budget.timeout_seconds:
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    result=ToolResult(
                        tool=envelope.tool,
                        error_category="TIME_BUDGET_EXCEEDED",
                        elapsed_seconds=elapsed,
                    ),
                    allowed=True,
                    reason="TIME_BUDGET_EXCEEDED",
                )
            )
            raise ToolBudgetExceeded("logical tool exceeded its time budget")
        try:
            payload = (
                LOGICAL_TOOL_OUTPUTS[envelope.tool]
                .model_validate(raw.payload)
                .model_dump(mode="json")
            )
        except ValidationError as exc:
            result = ToolResult(
                tool=envelope.tool,
                error_category="INVALID_ADAPTER_OUTPUT",
                elapsed_seconds=monotonic() - started,
            )
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    result=result,
                    allowed=True,
                    reason="INVALID_ADAPTER_OUTPUT",
                )
            )
            raise ToolExecutionError("logical tool returned an invalid result") from exc
        sources = [
            SourceProvenance.model_validate(source) for source in raw.raw_sources
        ]
        result = ToolResult(
            tool=envelope.tool,
            payload=payload,
            sources=sources,
            adapter_provenance=[
                AdapterProvenance(
                    adapter=adapter.name,
                    adapter_version=raw.adapter_version,
                    started_at=raw.started_at or started_at,
                    ended_at=raw.ended_at or ended_at,
                    latency_seconds=(raw.ended_at - raw.started_at).total_seconds(),
                    warnings=raw.warnings,
                    resource_usage=raw.resource_usage,
                )
            ],
            cost=raw.cost,
            elapsed_seconds=elapsed,
        )
        if result.cost > envelope.budget.max_cost:
            self.audit.write(
                ToolAuditRecord(
                    envelope=envelope,
                    result=result,
                    allowed=True,
                    reason="COST_BUDGET_EXCEEDED",
                )
            )
            raise ToolBudgetExceeded("adapter result exceeded cost budget")
        self.cache.put(envelope, result)
        self.audit.write(
            ToolAuditRecord(envelope=envelope, result=result, allowed=True)
        )
        return result
