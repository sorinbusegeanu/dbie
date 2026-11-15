from unittest.mock import Mock

from dbie.tools.contracts import ToolName, ToolResult
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


def test_crewai_wrapper_scopes_database_list_queries_to_context_run() -> None:
    value = gateway(FakeAdapter())
    value.invoke = Mock(return_value=ToolResult(tool=ToolName.DATABASE_QUERY))
    context = CrewAIToolContext(
        run_id="run-42",
        stage_id="eligibility_gate",
        task_id="eligibility-review",
        actor_id="OpportunitySynthesizer",
    )
    tool = crewai_tools_for(value, context, [ToolName.DATABASE_QUERY])[0]

    tool._run(operation="LIST_IDEAS")

    envelope = value.invoke.call_args.args[0]
    assert envelope.arguments["parameters"] == {
        "run_id": "run-42"
    }


def test_semantic_memory_tool_can_restrict_results_to_prior_runs() -> None:
    value = gateway(FakeAdapter())
    value.invoke = Mock(return_value=ToolResult(tool=ToolName.SEMANTIC_MEMORY_SEARCH))
    context = CrewAIToolContext(
        run_id="run-current", stage_id="generate_ideas", task_id="memory",
        actor_id="IdeaGenerator",
    )
    tool = crewai_tools_for(value, context, [ToolName.SEMANTIC_MEMORY_SEARCH])[0]

    tool._run(query="buyer demand", entity_types=["IDEA"], exclude_current_run=True)

    envelope = value.invoke.call_args.args[0]
    assert envelope.arguments["exclude_run_id"] == "run-current"
    assert "exclude_current_run" not in envelope.arguments
