from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

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

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        *,
        api_token: str | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=120,
            headers=(
                {"Authorization": f"Bearer {api_token}"} if api_token else None
            ),
        )

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
        content = _markdown_text(item.get("markdown"))
        if not content:
            content = str(item.get("content") or item.get("cleaned_html") or "")
        quality = extraction_quality(content)
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "url": request.arguments["url"],
                "content": content,
                "links": _links(item.get("links")),
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


def _markdown_text(markdown: Any) -> str:
    if isinstance(markdown, str):
        return markdown
    if not isinstance(markdown, dict):
        return ""
    for key in ("raw_markdown", "markdown_with_citations", "fit_markdown"):
        value = markdown.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _links(links: Any) -> list[dict[str, Any]]:
    if isinstance(links, list):
        return [item for item in links if isinstance(item, dict)]
    if not isinstance(links, dict):
        return []
    normalized: list[dict[str, Any]] = []
    for relationship in ("internal", "external"):
        values = links.get(relationship, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict):
                normalized.append({**item, "relationship": relationship})
    return normalized
