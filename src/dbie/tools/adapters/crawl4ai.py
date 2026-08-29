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
from dbie.tools.normalization.documents import document_hash, extraction_quality


class Crawl4AIAdapter(ToolAdapter):
    name = "crawl4ai"
    capabilities = AdapterCapabilities(
        operations={"fetch_page"}, media_types={"text/html"}
    )

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(base_url=base_url.rstrip("/"), timeout=120)

    def health(self) -> AdapterHealth:
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return AdapterHealth(name=self.name, available=True)
        except httpx.HTTPError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        response = self.client.post(
            "/crawl",
            json={
                "urls": [request.arguments["url"]],
                "extraction_schema": request.arguments.get("extract_schema"),
                "include_links": request.arguments.get("include_links", True),
            },
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        item = (raw.get("results") or [raw])[0]
        content = item.get("markdown") or item.get("content") or ""
        quality = extraction_quality(content)
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "url": request.arguments["url"],
                "content": content,
                "links": item.get("links", []),
                "records": item.get("extracted_content"),
                "quality": quality,
            },
            raw_sources=[
                {
                    "source_identifier": request.arguments["url"],
                    "source_url": request.arguments["url"],
                    "source_type": "web_page",
                    "content_hash": document_hash(content.encode()),
                }
            ],
            warnings=list(quality["warnings"]),
            started_at=started,
            ended_at=ended,
        )
