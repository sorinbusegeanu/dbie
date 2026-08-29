from __future__ import annotations

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.adapters.regulations.base import RegulatoryAdapter


class RegulatoryAdapterRegistry(ToolAdapter):
    name = "regulatory_registry"
    capabilities = AdapterCapabilities(operations={"search_regulations"})

    def __init__(self, adapters: list[RegulatoryAdapter]) -> None:
        self.adapters = {adapter.jurisdiction.upper(): adapter for adapter in adapters}

    def health(self) -> AdapterHealth:
        states = [adapter.health() for adapter in self.adapters.values()]
        return AdapterHealth(
            name=self.name,
            available=any(state.available for state in states),
            detail=", ".join(
                f"{state.name}={'up' if state.available else 'down'}"
                for state in states
            ),
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        jurisdictions = request.arguments.get("jurisdictions") or [
            request.arguments.get("jurisdiction", "EU")
        ]
        documents: list[dict[str, object]] = []
        sources: list[dict[str, object]] = []
        warnings: list[str] = []
        for jurisdiction in jurisdictions:
            adapter = self.adapters.get(str(jurisdiction).upper())
            if adapter is None:
                warnings.append(f"NO_OFFICIAL_ADAPTER:{jurisdiction}")
                continue
            result = adapter.execute(request)
            documents.extend(result.payload.get("documents", []))
            sources.extend(result.raw_sources)
            warnings.extend(result.warnings)
        return AdapterResult(
            payload={"documents": documents, "legal_advice": False},
            raw_sources=sources,
            warnings=warnings,
        )
