"""Typed arguments for exactly ten logical CrewAI-visible tools."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from dbie.tools.contracts import ToolName


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WebSearchInput(ToolInput):
    query: str = Field(min_length=1)
    intent: Literal[
        "DISCOVERY",
        "SUPPORT",
        "CONTRADICT",
        "COMPETITOR",
        "MARKET_SIZE",
        "PRICING",
        "DISTRIBUTION",
    ] = "DISCOVERY"
    date_from: date | None = None
    date_to: date | None = None
    domains_allow: list[str] = Field(default_factory=list)
    domains_deny: list[str] = Field(default_factory=list)
    max_results: int = Field(default=10, ge=1, le=50)


class FetchPageInput(ToolInput):
    url: HttpUrl
    mode: Literal["READ", "EXTRACT"] = "READ"
    extract_fields: list[str] = Field(default_factory=list)
    extract_schema: dict[str, Any] | None = None
    render_js: Literal["AUTO", "NO", "YES"] = "AUTO"
    max_chars: int = Field(default=50_000, ge=100, le=1_000_000)
    site_traversal: bool = False


class SearchCommunityInput(ToolInput):
    query: str = Field(min_length=1)
    platforms: list[
        Literal["STACK_EXCHANGE", "HACKER_NEWS", "GITHUB", "REDDIT_INDEX"]
    ] = Field(default_factory=list)
    date_from: date | None = None
    sort: Literal["RELEVANCE", "NEW", "TOP"] = "RELEVANCE"
    max_results: int = Field(default=20, ge=1, le=100)
    include_replies: bool = True


class SearchCompaniesInput(ToolInput):
    query: str = Field(min_length=1)
    mode: Literal[
        "COMPETITORS", "COMPANY_LOOKUP", "CATEGORY", "FUNDING", "POSITIONING"
    ] = "COMPETITORS"
    geography: list[str] = Field(default_factory=list)
    max_results: int = Field(default=25, ge=1, le=100)


class SearchGitHubInput(ToolInput):
    query: str = Field(min_length=1)
    mode: Literal["REPOSITORIES", "CODE", "ISSUES", "TOPICS"] = "REPOSITORIES"
    language: str | None = None
    updated_after: date | None = None
    max_results: int = Field(default=20, ge=1, le=100)


class SearchRegulationsInput(ToolInput):
    query: str = Field(min_length=1)
    jurisdictions: list[str] = Field(min_length=1)
    authorities: list[str] = Field(default_factory=list)
    status: Literal["IN_FORCE", "PROPOSED", "CONSULTATION", "ANY"] = "ANY"
    date_from: date | None = None
    max_results: int = Field(default=20, ge=1, le=50)


class ReadDocumentInput(ToolInput):
    source: str = Field(min_length=1)
    query: str = Field(min_length=1)
    sections: list[str] = Field(default_factory=list)
    tables: bool = True
    require_structure: bool = True
    max_pages: int = Field(default=100, ge=1, le=1000)


class PythonExecuteInput(ToolInput):
    code: str = Field(min_length=1, max_length=100_000)
    input_artifacts: list[str] = Field(default_factory=list)
    purpose: Literal[
        "CALCULATION",
        "STATISTICS",
        "SIMULATION",
        "CLUSTERING",
        "CALIBRATION",
        "MICRO_TEST",
    ]
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    memory_mb: int = Field(default=512, ge=64, le=2048)
    network: Literal[False] = False


class DatabaseQueryInput(ToolInput):
    operation: Literal[
        "GET_ASSUMPTION",
        "UPSERT_EVIDENCE",
        "LINK_EVIDENCE",
        "GET_IDEA",
        "SAVE_EVALUATION",
        "GET_OUTCOMES",
        "GET_SOURCE_LINEAGE",
        "LIST_IDEAS",
        "LIST_ASSUMPTIONS",
        "LIST_EVIDENCE",
    ]
    parameters: dict[str, Any] = Field(default_factory=dict)


class SemanticMemorySearchInput(ToolInput):
    query: str = Field(min_length=1)
    entity_types: list[
        Literal[
            "PROBLEM",
            "IDEA",
            "ASSUMPTION",
            "EVIDENCE",
            "COMPETITOR",
            "EXPERIMENT",
            "OUTCOME",
            "LESSON",
        ]
    ]
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=100)
    exclude_current_run: bool = False
    exclude_run_id: str | None = None


LOGICAL_TOOL_INPUTS: dict[ToolName, type[ToolInput]] = {
    ToolName.WEB_SEARCH: WebSearchInput,
    ToolName.FETCH_PAGE: FetchPageInput,
    ToolName.SEARCH_COMMUNITY: SearchCommunityInput,
    ToolName.SEARCH_COMPANIES: SearchCompaniesInput,
    ToolName.SEARCH_GITHUB: SearchGitHubInput,
    ToolName.SEARCH_REGULATIONS: SearchRegulationsInput,
    ToolName.READ_DOCUMENT: ReadDocumentInput,
    ToolName.PYTHON_EXECUTE: PythonExecuteInput,
    ToolName.DATABASE_QUERY: DatabaseQueryInput,
    ToolName.SEMANTIC_MEMORY_SEARCH: SemanticMemorySearchInput,
}
