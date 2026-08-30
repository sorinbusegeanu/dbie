from types import SimpleNamespace

import pytest

from dbie.config import ModelRoleConfig
from dbie.crews.catalog import ActorSpec
from dbie.crews.outputs import RunPlan
from dbie.crews.stage_runner import CrewAIStageRunner, CrewTaskRequest
from dbie.models.roles import ModelRole, ModelSelection
from dbie.tools.audit import ToolAuditRecord
from dbie.tools.contracts import ToolCallEnvelope, ToolName, ToolResult


def _request(*required: ToolName) -> CrewTaskRequest[RunPlan]:
    return CrewTaskRequest(
        task_id="task-1",
        stage_id="stage-1",
        crew_name="Test Crew",
        spec=ActorSpec(
            role="Research Planner",
            group="test",
            goal="Test required tools",
            tools=required,
            model_role=ModelRole.THINKER,
        ),
        description="Use required tools and return a plan.",
        expected_output="A RunPlan",
        output_model=RunPlan,
        required_tools=required,
    )


def _runner(records: list[ToolAuditRecord]) -> CrewAIStageRunner:
    runner = object.__new__(CrewAIStageRunner)
    runner.catalog = SimpleNamespace(
        gateway=SimpleNamespace(audit=SimpleNamespace(records=records)),
        llm=SimpleNamespace(
            router=SimpleNamespace(
                config=SimpleNamespace(
                    roles={
                        ModelRole.THINKER: ModelRoleConfig(
                            primary_profile="deepseek",
                            challenger_profile="qwen",
                            context_tokens=32768,
                        )
                    }
                )
            )
        ),
    )
    return runner


def test_live_stage_rejects_model_only_completion_when_tool_is_required() -> None:
    with pytest.raises(ValueError, match="omitted required real tools: web_search"):
        _runner([])._verify_required_tools(_request(ToolName.WEB_SEARCH))


def test_live_stage_accepts_successful_attributed_required_tool_call() -> None:
    record = ToolAuditRecord(
        envelope=ToolCallEnvelope(
            run_id="run-1",
            stage_id="stage-1",
            task_id="task-1",
            actor_id="ResearchPlanner",
            tool=ToolName.WEB_SEARCH,
            arguments={"query": "workflow pain"},
            purpose="ground the plan",
        ),
        result=ToolResult(tool=ToolName.WEB_SEARCH),
        allowed=True,
    )

    _runner([record])._verify_required_tools(_request(ToolName.WEB_SEARCH))


def test_initial_task_prompt_discloses_every_required_tool() -> None:
    description = _runner([])._task_description(
        _request(ToolName.WEB_SEARCH, ToolName.SEARCH_COMMUNITY),
        attempt=0,
    )

    assert "MANDATORY TOOL CONTRACT" in description
    assert "web_search, search_community" in description
    assert "arguments declared in each tool's schema" in description


def test_retry_prompt_preserves_mandatory_tool_contract() -> None:
    description = _runner([])._task_description(
        _request(ToolName.SEARCH_COMMUNITY),
        attempt=1,
    )

    assert "search_community" in description
    assert "RECOVERY ATTEMPT" in description


def test_contract_retry_switches_from_primary_to_role_challenger() -> None:
    runner = _runner([])

    assert runner._selection_for_attempt(
        ModelRole.THINKER, ModelSelection.PRIMARY, attempt=0
    ) is ModelSelection.PRIMARY
    assert runner._selection_for_attempt(
        ModelRole.THINKER, ModelSelection.PRIMARY, attempt=1
    ) is ModelSelection.CHALLENGER


def test_challenger_retry_switches_back_to_primary() -> None:
    runner = _runner([])

    assert runner._selection_for_attempt(
        ModelRole.THINKER, ModelSelection.CHALLENGER, attempt=1
    ) is ModelSelection.PRIMARY
