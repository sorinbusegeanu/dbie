from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.web import deduplicate_results


class SearXNGAdapter(ToolAdapter):
    name = "searxng"
    capabilities = AdapterCapabilities(operations={"web_search"})

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(base_url=self.base_url, timeout=30)

    def health(self) -> AdapterHealth:
        try:
            response = self.client.get("/healthz")
            if response.status_code == 404:
                response = self.client.get("/")
            response.raise_for_status()
            return AdapterHealth(name=self.name, available=True)
        except httpx.HTTPError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        arguments = request.arguments
        params: dict[str, Any] = {
            "q": arguments["query"],
            "format": "json",
        }
        if arguments.get("categories"):
            params["categories"] = ",".join(arguments["categories"])
        response = self.client.get(
            "/search", params=params, timeout=request.timeout_seconds
        )
        response.raise_for_status()
        raw = response.json()
        normalized = deduplicate_results(
            [
                {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "engines": item.get("engines", []),
                    "score": item.get("score"),
                    "published_date": item.get("publishedDate"),
                    "rank": index + 1,
                    "query": arguments["query"],
                }
                for index, item in enumerate(raw.get("results", []))
            ]
        )[: int(arguments.get("max_results", 10))]
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"results": normalized, "snippets_are_evidence": False},
            raw_sources=[
                {
                    "source_identifier": item["canonical_url"],
                    "source_url": item["canonical_url"],
                    "source_type": "search_result",
                }
                for item in normalized
            ],
            started_at=started,
            ended_at=ended,
            adapter_version=_package_version("searxng"),
        )


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None
