from dbie.tools.contracts import ToolName
from dbie.tools.crewai_tools import CrewAIToolContext, crewai_tools_for
from tests.test_tool_gateway import FakeAdapter, gateway


def test_crewai_receives_logical_tool_not_adapter_name() -> None:
    value = gateway(FakeAdapter())
    context = CrewAIToolContext(
        run_id="run",
        stage_id="discover",
        task_id="task",
        actor_id="Scout",
    )

    tools = crewai_tools_for(value, context, [ToolName.WEB_SEARCH])

    assert [tool.name for tool in tools] == ["web_search"]
    assert "fake_search" not in tools[0].description


def test_crewai_wrapper_calls_gateway_with_typed_arguments() -> None:
    value = gateway(FakeAdapter())
    context = CrewAIToolContext(
        run_id="run",
        stage_id="discover",
        task_id="task",
        actor_id="Scout",
    )
    tool = crewai_tools_for(value, context, [ToolName.WEB_SEARCH])[0]

    serialized = tool._run(query="pain", intent="DISCOVERY", max_results=3)

    assert '"web_search"' in serialized
    assert value.audit.records[-1].envelope.arguments["query"] == "pain"
