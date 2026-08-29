from __future__ import annotations

from datetime import UTC, datetime

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
