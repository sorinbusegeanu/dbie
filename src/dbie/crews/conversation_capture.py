"""Persistence of native, visible CrewAI dialogue without model reasoning traces."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from crewai.agents.parser import AgentAction, AgentFinish
from crewai.events.event_bus import CrewAIEventsBus, crewai_event_bus
from crewai.events.types.logging_events import (
    AgentLogsExecutionEvent,
    AgentLogsStartedEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)

from dbie.services.run_workspace import RunWorkspaceManager

_SECRET_KEY = re.compile(
    r"token|password|secret|api[_-]?key|authorization", re.IGNORECASE
)


class CrewAIConversationCapture:
    """Capture exactly the task, final answer, and visible tool dialogue CrewAI emits."""

    def __init__(
        self,
        runs_directory: Path,
        run_id: str,
        crew_name: str,
        *,
        event_bus: CrewAIEventsBus = crewai_event_bus,
    ) -> None:
        self.workspace = RunWorkspaceManager(runs_directory)
        self.run_id = run_id
        slug = re.sub(r"[^a-z0-9]+", "_", crew_name.casefold()).strip("_")
        self.filename = f"{slug}_dialogue.log"
        self.event_bus = event_bus
        self._handlers = (
            (AgentLogsStartedEvent, self._agent_started),
            (AgentLogsExecutionEvent, self._agent_output),
            (ToolUsageStartedEvent, self._tool_started),
            (ToolUsageFinishedEvent, self._tool_finished),
            (ToolUsageErrorEvent, self._tool_error),
        )

    def __enter__(self) -> Self:
        for event_type, handler in self._handlers:
            self.event_bus.on(event_type)(handler)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for event_type, handler in self._handlers:
            self.event_bus.off(event_type, handler)

    def _append(self, text: str) -> None:
        self.workspace.append_visible_output(self.run_id, self.filename, text)

    def _agent_started(self, _source: Any, event: AgentLogsStartedEvent) -> None:
        task = event.task_description or "Task description unavailable"
        self._append(f"AGENT: {event.agent_role}\nTASK\n{task}")

    def _agent_output(self, _source: Any, event: AgentLogsExecutionEvent) -> None:
        answer = event.formatted_answer
        if isinstance(answer, AgentFinish):
            self._append(f"AGENT: {event.agent_role}\nANSWER\n{answer.output}")
        elif isinstance(answer, AgentAction):
            self._append(
                f"AGENT: {event.agent_role}\nTOOL RESULT\n{answer.result}"
            )

    def _tool_started(self, _source: Any, event: ToolUsageStartedEvent) -> None:
        arguments = json.dumps(_redact(event.tool_args), indent=2, default=str)
        role = event.agent_role or "CrewAI agent"
        self._append(
            f"AGENT: {role}\nTOOL REQUEST: {event.tool_name}\n{arguments}"
        )

    def _tool_finished(self, _source: Any, event: ToolUsageFinishedEvent) -> None:
        output = json.dumps(_redact(event.output), indent=2, default=str)
        self._append(f"TOOL RESPONSE: {event.tool_name}\n{output}")

    def _tool_error(self, _source: Any, event: ToolUsageErrorEvent) -> None:
        self._append(f"TOOL ERROR: {event.tool_name}\n{event.error}")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
