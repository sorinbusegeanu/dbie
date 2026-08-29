from __future__ import annotations

from datetime import UTC, datetime

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.companies import identity


class CompanyPublicSourcesAdapter(ToolAdapter):
    name = "company_public_sources"
    capabilities = AdapterCapabilities(operations={"search_companies"})

    def __init__(self, search_adapter: ToolAdapter) -> None:
        self.search_adapter = search_adapter

    def health(self) -> AdapterHealth:
        health = self.search_adapter.health()
        return AdapterHealth(
            name=self.name,
            available=health.available,
            detail=f"discovery={health.name}",
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        search = self.search_adapter.execute(
            AdapterRequest(
                operation="web_search",
                arguments={
                    "query": request.arguments["query"],
                    "max_results": request.arguments.get("max_results", 25),
                },
                timeout_seconds=request.timeout_seconds,
            )
        )
        companies: list[dict[str, object]] = []
        for item in search.payload.get("results", []):
            title = str(item.get("title") or "").split("|")[0].strip()
            if not title:
                continue
            company_identity = identity(title, str(item.get("canonical_url") or ""))
            companies.append(
                {
                    "identity": company_identity.model_dump(),
                    "identity_confidence": 0.55,
                    "attributes": {
                        "positioning": {
                            "value": item.get("snippet") or "UNKNOWN",
                            "source_url": item.get("canonical_url"),
                        },
                        "revenue": {"value": "UNKNOWN", "source_url": None},
                        "funding": {"value": "UNKNOWN", "source_url": None},
                        "headcount": {"value": "UNKNOWN", "source_url": None},
                    },
                }
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "companies": companies,
                "merge_threshold": 0.8,
                "unavailable_values": "UNKNOWN",
            },
            raw_sources=search.raw_sources,
            warnings=search.warnings,
            started_at=started,
            ended_at=ended,
        )
