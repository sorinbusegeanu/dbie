from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash


class PyMuPDFAdapter(ToolAdapter):
    name = "pymupdf"
    capabilities = AdapterCapabilities(
        operations={"read_document"}, media_types={"application/pdf"}
    )

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(follow_redirects=True, timeout=60)

    def health(self) -> AdapterHealth:
        try:
            return AdapterHealth(
                name=self.name, available=True, version=version("PyMuPDF")
            )
        except PackageNotFoundError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        import pymupdf

        started = datetime.now(UTC)
        source = str(request.arguments["source"])
        if source.startswith(("http://", "https://")):
            response = self.client.get(source, timeout=request.timeout_seconds)
            response.raise_for_status()
            content = response.content
            document = pymupdf.open(stream=content, filetype="pdf")
        else:
            content = Path(source).read_bytes()
            document = pymupdf.open(source)
        max_pages = int(request.arguments.get("max_pages", 100))
        pages = [
            {
                "page": index + 1,
                "text": page.get_text("text"),
            }
            for index, page in enumerate(document)
            if index < max_pages
        ]
        document.close()
        max_chars = int(request.arguments.get("max_chars", 50_000))
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "source": source,
                "content": "\n\n".join(page["text"] for page in pages)[:max_chars],
                "pages": pages,
                "sections": [],
                "tables": [],
                "file_hash": document_hash(content),
                "parser": self.name,
            },
            raw_sources=[
                {
                    "source_identifier": source,
                    "source_url": source if source.startswith("http") else None,
                    "source_type": "document",
                    "content_hash": document_hash(content),
                }
            ],
            resource_usage={"bytes": float(len(content)), "pages": float(len(pages))},
            started_at=started,
            ended_at=ended,
            adapter_version=version("PyMuPDF"),
        )
