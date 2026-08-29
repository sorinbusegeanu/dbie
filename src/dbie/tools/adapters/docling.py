from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash


class DoclingAdapter(ToolAdapter):
    name = "docling"
    capabilities = AdapterCapabilities(
        operations={"read_document"},
        media_types={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/html",
        },
    )

    def __init__(self, converter: Any | None = None) -> None:
        self.converter = converter

    def health(self) -> AdapterHealth:
        try:
            package_version = version("docling")
        except PackageNotFoundError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))
        return AdapterHealth(name=self.name, available=True, version=package_version)

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        converter = self.converter
        if converter is None:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
        conversion = converter.convert(request.arguments["source"])
        document = conversion.document
        markdown = document.export_to_markdown()
        structure = document.export_to_dict()
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "source": request.arguments["source"],
                "content": markdown,
                "pages": structure.get("pages", {}),
                "sections": structure.get("texts", []),
                "tables": structure.get("tables", []),
                "file_hash": document_hash(markdown.encode()),
                "parser": self.name,
            },
            raw_sources=[
                {
                    "source_identifier": str(request.arguments["source"]),
                    "source_url": str(request.arguments["source"]),
                    "source_type": "document",
                    "content_hash": document_hash(markdown.encode()),
                }
            ],
            started_at=started,
            ended_at=ended,
            adapter_version=version("docling"),
        )
