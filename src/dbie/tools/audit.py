from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from dbie.tools.contracts import ToolCallEnvelope, ToolResult


class ToolAuditRecord(BaseModel):
    envelope: ToolCallEnvelope
    result: ToolResult | None = None
    allowed: bool
    reason: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.records: list[ToolAuditRecord] = []

    def write(self, record: ToolAuditRecord) -> None:
        self.records.append(record.model_copy(deep=True))


class ToolAuditSink(Protocol):
    def write(self, record: ToolAuditRecord) -> None: ...


class JsonlToolAuditSink:
    """Append complete tool attribution records to a run-local JSONL file."""

    def __init__(self, runs_directory: Path) -> None:
        self.runs_directory = Path(runs_directory)

    def write(self, record: ToolAuditRecord) -> None:
        run_id = record.envelope.run_id
        directory = self.runs_directory / run_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "tool-audit.jsonl"
        line = record.model_dump_json() + "\n"
        # A single append is atomic for the small records DBIE writes here.
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, line.encode("utf-8"))
        finally:
            os.close(descriptor)


class CompositeAuditSink:
    def __init__(self, sinks: Iterable[ToolAuditSink]) -> None:
        self.sinks = list(sinks)
        self.records: list[ToolAuditRecord] = []

    def write(self, record: ToolAuditRecord) -> None:
        copied = record.model_copy(deep=True)
        self.records.append(copied)
        for sink in self.sinks:
            sink.write(copied)
