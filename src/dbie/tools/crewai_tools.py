"""CrewAI wrappers exposing only the ten stable logical DBIE tools."""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool
from pydantic import ConfigDict, Field

from dbie.tools.contracts import ToolBudget, ToolCallEnvelope, ToolName
from dbie.tools.gateway import ToolGateway
from dbie.tools.logical import LOGICAL_TOOL_INPUTS


class CrewAIToolContext:
    def __init__(
        self,
        *,
        run_id: str,
        stage_id: str,
        task_id: str,
        actor_id: str,
        candidate_id: str | None = None,
        assumption_id: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.stage_id = stage_id
        self.task_id = task_id
        self.actor_id = actor_id
        self.candidate_id = candidate_id
        self.assumption_id = assumption_id


class GatewayCrewAITool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    gateway: ToolGateway = Field(exclude=True)
    logical_tool: ToolName = Field(exclude=True)
    context: CrewAIToolContext = Field(exclude=True)

    def _run(self, **kwargs: Any) -> str:
        arguments = dict(kwargs)
        if self.logical_tool is ToolName.DATABASE_QUERY:
            operation = arguments.get("operation")
            if operation in {"LIST_IDEAS", "LIST_ASSUMPTIONS", "LIST_EVIDENCE"}:
                parameters = dict(arguments.get("parameters") or {})
                parameters.setdefault("run_id", self.context.run_id)
                arguments["parameters"] = parameters
        result = self.gateway.invoke(
            ToolCallEnvelope(
                run_id=self.context.run_id,
                stage_id=self.context.stage_id,
                task_id=self.context.task_id,
                actor_id=self.context.actor_id,
                candidate_id=self.context.candidate_id,
                assumption_id=self.context.assumption_id,
                tool=self.logical_tool,
                arguments=arguments,
                purpose=f"CrewAI {self.context.actor_id} invoked {self.logical_tool.value}",
                budget=ToolBudget(),
            )
        )
        return result.model_dump_json()


def crewai_tools_for(
    gateway: ToolGateway,
    context: CrewAIToolContext,
    allowed_tools: list[ToolName],
) -> list[GatewayCrewAITool]:
    return [
        GatewayCrewAITool(
            name=tool.value,
            description=f"DBIE logical tool: {tool.value}",
            args_schema=LOGICAL_TOOL_INPUTS[tool],
            gateway=gateway,
            logical_tool=tool,
            context=context,
        )
        for tool in allowed_tools
    ]
