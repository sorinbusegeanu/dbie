"""Typed, serializable state passed between every MVP flow stage."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from crewai.flow.flow import FlowState
from pydantic import BaseModel, ConfigDict, Field


class StageName(StrEnum):
    INITIALIZE_RUN = "initialize_run"
    DISCOVER_SIGNALS = "discover_signals"
    GENERATE_IDEAS = "generate_ideas"
    ELIGIBILITY_GATE = "eligibility_gate"
    DECOMPOSE_ASSUMPTIONS = "decompose_assumptions"
    COLLECT_EVIDENCE = "collect_evidence"
    VALIDATE_ASSUMPTIONS = "validate_assumptions"
    MODEL_BUSINESS = "model_business"
    RED_TEAM = "red_team"
    RANK_PORTFOLIO = "rank_portfolio"
    DESIGN_EXPERIMENTS = "design_experiments"
    OBSERVE_AND_DECIDE = "observe_and_decide"
    PRODUCE_DOSSIER = "produce_dossier"
    FINALIZE_RUN = "finalize_run"


STAGE_ORDER = list(StageName)


class CandidateFailure(BaseModel):
    candidate_id: str
    stage: StageName
    error_category: str
    detail: str


class PipelineState(FlowState):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: str
    mandate: str = Field(min_length=1)
    current_stage: StageName | None = None
    completed_stages: list[StageName] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    eligible_candidate_ids: list[str] = Field(default_factory=list)
    finalist_ids: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    candidate_failures: list[CandidateFailure] = Field(default_factory=list)
    run_error: str | None = None
    checkpoint_version: int = 1
