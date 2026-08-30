"""Reusable fail-closed adapter fallback for stable logical-tool schemas."""

from __future__ import annotations

from dbie.tools.adapters.base import AdapterRequest, AdapterResult, ToolAdapter


def execute_with_fallback(
    request: AdapterRequest,
    adapters: list[ToolAdapter],
) -> AdapterResult:
    attempts: list[str] = []
    last_error: Exception | None = None
    for adapter in adapters:
        health = adapter.health()
        if not health.available:
            attempts.append(f"{adapter.name}:UNAVAILABLE")
            continue
        try:
            result = adapter.execute(request)
        except Exception as exc:  # noqa: BLE001 - isolates provider failures
            attempts.append(f"{adapter.name}:ERROR")
            last_error = exc
            continue
        result.executed_adapter = adapter.name
        result.fallback_count = len(attempts)
        result.attempts = [*attempts, f"{adapter.name}:USED"]
        return result
    raise RuntimeError(f"all adapters failed: {attempts}") from last_error
