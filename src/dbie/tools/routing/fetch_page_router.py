from __future__ import annotations

from datetime import UTC, datetime

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)


class FetchPageRouter(ToolAdapter):
    name = "fetch_page_router"
    capabilities = AdapterCapabilities(operations={"fetch_page"})

    def __init__(self, adapters: list[ToolAdapter]) -> None:
        if not adapters:
            raise ValueError("fetch page router requires adapters")
        self.adapters = adapters

    def health(self) -> AdapterHealth:
        health = [adapter.health() for adapter in self.adapters]
        available = any(item.available for item in health)
        detail = ", ".join(
            f"{item.name}={'up' if item.available else 'down'}" for item in health
        )
        return AdapterHealth(name=self.name, available=available, detail=detail)

    def execute(self, request: AdapterRequest) -> AdapterResult:
        attempts: list[str] = []
        warnings: list[str] = []
        started = datetime.now(UTC)
        last_error: Exception | None = None
        force_complex = bool(
            request.arguments.get("extract_schema")
            or request.arguments.get("site_traversal")
        )
        for index, adapter in enumerate(self.adapters):
            if force_complex and index == 0:
                attempts.append(f"{adapter.name}:SKIPPED_COMPLEX_REQUEST")
                continue
            health = adapter.health()
            if not health.available:
                attempts.append(f"{adapter.name}:UNAVAILABLE")
                continue
            try:
                result = adapter.execute(request)
            except Exception as exc:  # noqa: BLE001 - fallback isolates adapters
                attempts.append(f"{adapter.name}:ERROR")
                last_error = exc
                continue
            quality = result.payload.get("quality", {})
            if quality.get("meaningful"):
                result.payload["adapter_attempts"] = [*attempts, f"{adapter.name}:USED"]
                result.warnings = [*warnings, *result.warnings]
                return result
            attempts.append(f"{adapter.name}:LOW_QUALITY")
            warnings.extend(result.warnings)
        if last_error:
            raise RuntimeError("all fetch adapters failed") from last_error
        return AdapterResult(
            payload={
                "url": request.arguments["url"],
                "content": "",
                "links": [],
                "quality": {"meaningful": False, "warnings": warnings},
                "adapter_attempts": attempts,
            },
            warnings=[*warnings, "NO_ADAPTER_PRODUCED_MEANINGFUL_CONTENT"],
            started_at=started,
            ended_at=datetime.now(UTC),
        )
