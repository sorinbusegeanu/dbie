from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash, extraction_quality


class TrafilaturaAdapter(ToolAdapter):
    name = "trafilatura"
    capabilities = AdapterCapabilities(
        operations={"fetch_page"}, media_types={"text/html"}
    )

    def __init__(
        self,
        client: httpx.Client | None = None,
        extractor: Callable[..., str | None] | None = None,
    ) -> None:
        self.client = client or httpx.Client(follow_redirects=True, timeout=30)
        self.extractor = extractor

    def health(self) -> AdapterHealth:
        try:
            import trafilatura

            return AdapterHealth(
                name=self.name, available=True, version=trafilatura.__version__
            )
        except ImportError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        response = self.client.get(
            str(request.arguments["url"]), timeout=request.timeout_seconds
        )
        response.raise_for_status()
        extractor = self.extractor
        if extractor is None:
            from trafilatura import extract

            extractor = extract
        text = (
            extractor(
                response.text,
                output_format="markdown",
                include_links=True,
                include_tables=True,
            )
            or ""
        )
        quality = extraction_quality(text)
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "url": str(response.url),
                "content": text,
                "content_type": response.headers.get("content-type"),
                "quality": quality,
                "links": [],
            },
            raw_sources=[
                {
                    "source_identifier": str(response.url),
                    "source_url": str(response.url),
                    "source_type": "web_page",
                    "content_hash": document_hash(response.content),
                }
            ],
            warnings=list(quality["warnings"]),
            resource_usage={"bytes": float(len(response.content))},
            started_at=started,
            ended_at=ended,
            adapter_version=_version(),
        )


def _version() -> str | None:
    try:
        return version("trafilatura")
    except PackageNotFoundError:
        return None
