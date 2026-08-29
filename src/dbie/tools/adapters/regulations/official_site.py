from __future__ import annotations

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.adapters.regulations.base import RegulatoryAdapter
from dbie.tools.normalization.regulations import is_official_regulatory_url


class OfficialSiteRegulatorAdapter(RegulatoryAdapter):
    capabilities = AdapterCapabilities(operations={"search_regulations"})

    def __init__(
        self,
        *,
        name: str,
        authority: str,
        jurisdiction: str,
        official_domain: str,
        search_adapter: ToolAdapter | None = None,
    ) -> None:
        self.name = name
        self.authority = authority
        self.jurisdiction = jurisdiction
        self.official_domain = official_domain
        self.search_adapter = search_adapter

    def health(self) -> AdapterHealth:
        return AdapterHealth(
            name=self.name,
            available=self.search_adapter is not None,
            detail="official-site targeted adapter",
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        if self.search_adapter is None:
            raise RuntimeError(f"{self.authority} adapter transport not configured")
        scoped = request.model_copy(deep=True)
        scoped.arguments["query"] = (
            f"site:{self.official_domain} {request.arguments['query']}"
        )
        result = self.search_adapter.execute(scoped)
        documents = []
        sources = []
        for hit in result.payload.get("results", []):
            url = str(hit.get("canonical_url") or hit.get("url") or "")
            if not is_official_regulatory_url(self.jurisdiction, url):
                continue
            document = {
                "authority": self.authority,
                "jurisdiction": self.jurisdiction,
                "document_identifier": url,
                "title": hit.get("title"),
                "legal_status": request.arguments.get("status", "ANY"),
                "publication_date": hit.get("published_at"),
                "effective_date": None,
                "affected_entities": None,
                "canonical_official_url": url,
                "official_source": True,
            }
            documents.append(document)
            sources.append(
                {
                    "source_identifier": url,
                    "source_url": url,
                    "source_type": "official_regulation",
                }
            )
        return AdapterResult(
            payload={"documents": documents, "legal_advice": False},
            raw_sources=sources,
            warnings=result.warnings,
        )
