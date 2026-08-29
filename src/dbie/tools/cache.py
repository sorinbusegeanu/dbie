from __future__ import annotations

import json
from hashlib import sha256

from dbie.tools.contracts import ToolCallEnvelope, ToolResult


class InMemoryToolCache:
    def __init__(self) -> None:
        self._values: dict[str, ToolResult] = {}

    def key(self, envelope: ToolCallEnvelope) -> str:
        stable = {
            "tool": envelope.tool.value,
            "arguments": envelope.arguments,
            "independence": envelope.independence_requirement.value,
        }
        return sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()

    def get(self, envelope: ToolCallEnvelope) -> ToolResult | None:
        value = self._values.get(self.key(envelope))
        return value.model_copy(deep=True) if value else None

    def put(self, envelope: ToolCallEnvelope, result: ToolResult) -> None:
        self._values[self.key(envelope)] = result.model_copy(deep=True)
