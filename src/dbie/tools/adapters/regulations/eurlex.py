from __future__ import annotations

from datetime import UTC, datetime

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
)
from dbie.tools.adapters.regulations.base import RegulatoryAdapter
from dbie.tools.normalization.regulations import is_official_regulatory_url


class EurLexAdapter(RegulatoryAdapter):
    name = "eurlex"
    authority = "EUR-Lex"
    jurisdiction = "EU"
    capabilities = AdapterCapabilities(operations={"search_regulations"})

    def __init__(
        self,
        endpoint: str = "https://publications.europa.eu/webapi/rdf/sparql",
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.client = client or httpx.Client(timeout=30)

    def health(self) -> AdapterHealth:
        try:
            response = self.client.get(
                self.endpoint,
                params={
                    "query": "ASK { ?s ?p ?o }",
                    "format": "application/sparql-results+json",
                },
                timeout=5,
            )
            response.raise_for_status()
            return AdapterHealth(name=self.name, available=True)
        except httpx.HTTPError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        topic = str(request.arguments["query"]).replace('"', '\\"')
        limit = min(int(request.arguments.get("max_results", 20)), 50)
        sparql = f"""
SELECT ?work ?title ?date WHERE {{
  ?work <http://purl.org/dc/terms/title> ?title .
  OPTIONAL {{ ?work <http://purl.org/dc/terms/date> ?date . }}
  FILTER(CONTAINS(LCASE(STR(?title)), LCASE(\"{topic}\")))
}} LIMIT {limit}
""".strip()
        response = self.client.get(
            self.endpoint,
            params={"query": sparql, "format": "application/sparql-results+json"},
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        bindings = response.json().get("results", {}).get("bindings", [])
        documents: list[dict[str, object]] = []
        for binding in bindings:
            url = binding.get("work", {}).get("value")
            if not url:
                continue
            # The Cellar work URI is already an official, stable identifier.  It
            # must not be rewritten into a CELEX URL because the UUID is not a
            # CELEX number.
            documents.append(
                {
                    "authority": self.authority,
                    "jurisdiction": self.jurisdiction,
                    "document_identifier": binding.get("work", {}).get("value"),
                    "title": binding.get("title", {}).get("value"),
                    "legal_status": request.arguments.get("status", "ANY"),
                    "publication_date": binding.get("date", {}).get("value"),
                    "effective_date": None,
                    "affected_entities": None,
                    "canonical_official_url": url,
                    "official_source": is_official_regulatory_url("EU", url),
                }
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"documents": documents, "legal_advice": False},
            raw_sources=[
                {
                    "source_identifier": item["document_identifier"],
                    "source_url": item["canonical_official_url"],
                    "source_type": "official_regulation",
                }
                for item in documents
            ],
            started_at=started,
            ended_at=ended,
        )
