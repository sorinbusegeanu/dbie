"""Stable typed payload contracts for the ten logical tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dbie.tools.contracts import ToolName


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


class WebSearchOutput(ToolOutput):
    results: list[dict[str, Any]]
    snippets_are_evidence: Literal[False] = False


class FetchPageOutput(ToolOutput):
    content: str
    url: str | None = None
    links: list[Any] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)


class CommunityOutput(ToolOutput):
    signals: list[dict[str, Any]]
    discovery_leads: list[dict[str, Any]]
    evidence_type: str
    reddit_content_automatically_fetched: Literal[False] = False


class CompaniesOutput(ToolOutput):
    companies: list[dict[str, Any]]
    merge_threshold: float = Field(ge=0, le=1)


class GitHubOutput(ToolOutput):
    repositories: list[dict[str, Any]]
    popularity_is_demand_evidence: Literal[False] = False


class RegulationsOutput(ToolOutput):
    documents: list[dict[str, Any]]
    legal_advice: Literal[False] = False


class DocumentOutput(ToolOutput):
    model_config = ConfigDict(extra="ignore")

    source: str
    content: str
    file_hash: str


class PythonOutput(ToolOutput):
    stdout: str
    stderr: str
    exit_code: int
    image: str
    network: Literal[False]


class DatabaseOutput(ToolOutput):
    operation: str
    result: Any


class SemanticMemoryOutput(ToolOutput):
    hits: list[dict[str, Any]]
    memory_is_evidence: Literal[False] = False


LOGICAL_TOOL_OUTPUTS: dict[ToolName, type[ToolOutput]] = {
    ToolName.WEB_SEARCH: WebSearchOutput,
    ToolName.FETCH_PAGE: FetchPageOutput,
    ToolName.SEARCH_COMMUNITY: CommunityOutput,
    ToolName.SEARCH_COMPANIES: CompaniesOutput,
    ToolName.SEARCH_GITHUB: GitHubOutput,
    ToolName.SEARCH_REGULATIONS: RegulationsOutput,
    ToolName.READ_DOCUMENT: DocumentOutput,
    ToolName.PYTHON_EXECUTE: PythonOutput,
    ToolName.DATABASE_QUERY: DatabaseOutput,
    ToolName.SEMANTIC_MEMORY_SEARCH: SemanticMemoryOutput,
}
