from __future__ import annotations

from datetime import UTC, datetime

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.companies import (
    CompanyIdentity,
    identity,
    resolve_company_identity,
)


class CompanyPublicSourcesAdapter(ToolAdapter):
    name = "company_public_sources"
    capabilities = AdapterCapabilities(operations={"search_companies"})

    def __init__(
        self,
        search_adapter: ToolAdapter,
        *,
        page_adapter: ToolAdapter | None = None,
        wikidata_client: httpx.Client | None = None,
        opencorporates_client: httpx.Client | None = None,
    ) -> None:
        self.search_adapter = search_adapter
        self.page_adapter = page_adapter
        self.wikidata_client = wikidata_client or httpx.Client(
            base_url="https://www.wikidata.org", timeout=20
        )
        self.opencorporates_client = opencorporates_client or httpx.Client(
            base_url="https://api.opencorporates.com", timeout=20
        )

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
        sources = list(search.raw_sources)
        warnings = list(search.warnings)
        for item in search.payload.get("results", []):
            title = str(item.get("title") or "").split("|")[0].strip()
            if not title:
                continue
            company_identity = identity(title, str(item.get("canonical_url") or ""))
            positioning = item.get("snippet") or "UNKNOWN"
            url = str(item.get("canonical_url") or "")
            if self.page_adapter is not None and url and len(companies) < 5:
                try:
                    page = self.page_adapter.execute(
                        AdapterRequest(
                            operation="fetch_page",
                            arguments={"url": url, "max_chars": 5000},
                            timeout_seconds=request.timeout_seconds,
                        )
                    )
                    sources.extend(page.raw_sources)
                    text = str(page.payload.get("content") or "").strip()
                    if text:
                        positioning = text[:1000]
                except Exception:  # noqa: BLE001 - source composition is best effort
                    warnings.append(f"COMPANY_SITE_FETCH_FAILED:{url}")
            companies.append(
                {
                    "identity": company_identity.model_dump(),
                    "identity_confidence": 0.55,
                    "attributes": {
                        "positioning": {
                            "value": positioning,
                            "source_url": url,
                        },
                        "revenue": {"value": "UNKNOWN", "source_url": None},
                        "funding": {"value": "UNKNOWN", "source_url": None},
                        "headcount": {"value": "UNKNOWN", "source_url": None},
                    },
                }
            )
        public_records = self._wikidata(request)
        public_records.extend(self._opencorporates(request, warnings))
        companies = _merge_resolved_companies(companies, public_records)
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "companies": companies,
                "merge_threshold": 0.8,
                "unavailable_values": "UNKNOWN",
            },
            raw_sources=sources
            + [
                {
                    "source_identifier": str(item["identity"]["registry_id"]),
                    "source_url": item["source_url"],
                    "source_type": item["source_type"],
                }
                for item in public_records
            ],
            warnings=warnings,
            started_at=started,
            ended_at=ended,
        )

    def _wikidata(self, request: AdapterRequest) -> list[dict[str, object]]:
        try:
            response = self.wikidata_client.get(
                "/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": request.arguments["query"],
                    "language": "en",
                    "format": "json",
                    "limit": min(int(request.arguments.get("max_results", 25)), 10),
                },
                timeout=request.timeout_seconds,
            )
            response.raise_for_status()
            values = response.json().get("search", [])
        except (httpx.HTTPError, ValueError):
            return []
        return [
            {
                "identity": identity(
                    str(item.get("label") or item["id"]), registry_id=item["id"]
                ).model_dump(),
                "identity_confidence": 0.7,
                "attributes": {
                    "positioning": {
                        "value": item.get("description") or "UNKNOWN",
                        "source_url": item.get("concepturi"),
                    },
                    "revenue": {"value": "UNKNOWN", "source_url": None},
                    "funding": {"value": "UNKNOWN", "source_url": None},
                    "headcount": {"value": "UNKNOWN", "source_url": None},
                },
                "source_url": item.get("concepturi"),
                "source_type": "wikidata_entity",
            }
            for item in values
            if item.get("id")
        ]

    def _opencorporates(
        self, request: AdapterRequest, warnings: list[str]
    ) -> list[dict[str, object]]:
        try:
            response = self.opencorporates_client.get(
                "/v0.4/companies/search",
                params={
                    "q": request.arguments["query"],
                    "per_page": min(int(request.arguments.get("max_results", 25)), 10),
                },
                timeout=request.timeout_seconds,
            )
            response.raise_for_status()
            values = response.json().get("results", {}).get("companies", [])
        except (httpx.HTTPError, ValueError):
            warnings.append("OPENCORPORATES_UNAVAILABLE")
            return []
        records = []
        for wrapped in values:
            item = wrapped.get("company", {})
            registry_id = item.get("company_number")
            jurisdiction = item.get("jurisdiction_code")
            url = item.get("opencorporates_url")
            records.append(
                {
                    "identity": identity(
                        str(item.get("name") or registry_id or "Unknown company"),
                        item.get("registry_url"),
                        jurisdiction=jurisdiction,
                        registry_id=(
                            f"{jurisdiction}:{registry_id}" if registry_id else None
                        ),
                    ).model_dump(),
                    "identity_confidence": 0.9,
                    "attributes": {
                        "positioning": {"value": "UNKNOWN", "source_url": url},
                        "revenue": {"value": "UNKNOWN", "source_url": None},
                        "funding": {"value": "UNKNOWN", "source_url": None},
                        "headcount": {"value": "UNKNOWN", "source_url": None},
                        "status": {
                            "value": item.get("current_status") or "UNKNOWN",
                            "source_url": url,
                        },
                    },
                    "source_url": url,
                    "source_type": "public_company_registry",
                }
            )
        return records


def _merge_resolved_companies(
    discovered: list[dict[str, object]], public: list[dict[str, object]]
) -> list[dict[str, object]]:
    output = list(discovered)
    for candidate in public:
        candidate_identity = CompanyIdentity.model_validate(candidate["identity"])
        merged = False
        for existing in output:
            existing_identity = CompanyIdentity.model_validate(existing["identity"])
            match = resolve_company_identity(existing_identity, candidate_identity)
            if not match.matched:
                continue
            existing["identity_confidence"] = match.confidence
            attributes = existing["attributes"]
            for name, value in candidate["attributes"].items():
                if attributes.get(name, {}).get("value") in {None, "UNKNOWN"}:
                    attributes[name] = value
            merged = True
            break
        if not merged:
            output.append(candidate)
    return output
