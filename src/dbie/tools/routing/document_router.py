from __future__ import annotations

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)


class DocumentRouter(ToolAdapter):
    name = "document_router"
    capabilities = AdapterCapabilities(operations={"read_document"})

    def __init__(self, docling: ToolAdapter, pymupdf: ToolAdapter) -> None:
        self.docling = docling
        self.pymupdf = pymupdf

    def health(self) -> AdapterHealth:
        states = [self.docling.health(), self.pymupdf.health()]
        return AdapterHealth(
            name=self.name,
            available=any(item.available for item in states),
            detail=", ".join(
                f"{item.name}={'up' if item.available else 'down'}" for item in states
            ),
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        source = str(request.arguments["source"]).lower()
        simple_pdf = source.endswith(".pdf") and not (
            request.arguments.get("tables")
            or request.arguments.get("require_structure", True)
        )
        order = (
            [self.pymupdf, self.docling] if simple_pdf else [self.docling, self.pymupdf]
        )
        attempts: list[str] = []
        last_error: Exception | None = None
        for adapter in order:
            if not adapter.health().available:
                attempts.append(f"{adapter.name}:UNAVAILABLE")
                continue
            try:
                result = adapter.execute(request)
                result.payload["adapter_attempts"] = [*attempts, f"{adapter.name}:USED"]
                result.executed_adapter = adapter.name
                result.fallback_count = len(attempts)
                result.attempts = [*attempts, f"{adapter.name}:USED"]
                return result
            except Exception as exc:  # noqa: BLE001 - fallback isolates adapters
                attempts.append(f"{adapter.name}:ERROR")
                last_error = exc
        raise RuntimeError(f"document adapters failed: {attempts}") from last_error
