from pathlib import Path

from crewai.agents.parser import AgentFinish
from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.logging_events import (
    AgentLogsExecutionEvent,
    AgentLogsStartedEvent,
)
from crewai.events.types.tool_usage_events import ToolUsageStartedEvent

from dbie.crews.conversation_capture import CrewAIConversationCapture
from dbie.web.filesystem import DashboardFilesystem


def emit(event) -> None:
    future = crewai_event_bus.emit(object(), event)
    if future is not None:
        future.result(timeout=5)


def test_captures_native_visible_dialogue_without_hidden_reasoning_or_secrets(
    tmp_path: Path,
) -> None:
    with CrewAIConversationCapture(tmp_path, "run-1", "Market Research"):
        emit(
            AgentLogsStartedEvent(
                agent_role="Trend Scout",
                task_description="Find repeated customer pain with sources.",
                verbose=True,
            )
        )
        emit(
            ToolUsageStartedEvent(
                agent_role="Trend Scout",
                tool_name="web_search",
                tool_args={"query": "compliance pain", "api_key": "secret-value"},
            )
        )
        emit(
            AgentLogsExecutionEvent(
                agent_role="Trend Scout",
                formatted_answer=AgentFinish(
                    thought="hidden model reasoning must not be persisted",
                    output="Customers repeatedly report manual control-mapping work.",
                    text="raw parser text",
                ),
                verbose=True,
            )
        )

    log = (
        tmp_path / "run-1" / "conversations" / "market_research_dialogue.log"
    ).read_text(encoding="utf-8")
    assert "AGENT: Trend Scout" in log
    assert "Find repeated customer pain with sources." in log
    assert "TOOL REQUEST: web_search" in log
    assert "compliance pain" in log
    assert "[REDACTED]" in log
    assert "secret-value" not in log
    assert "Customers repeatedly report manual control-mapping work." in log
    assert "hidden model reasoning" not in log
    assert "raw parser text" not in log

    displayed = DashboardFilesystem(tmp_path).list_files("run-1", "conversations")
    assert displayed[0].artifact_type == "Actual CrewAI dialogue"
    assert "complete visible task" in displayed[0].detail
