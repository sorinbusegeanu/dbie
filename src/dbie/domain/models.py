"""Canonical, versioned DBIE entities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from dbie.domain.enums import (
    ApprovalStatus,
    AssumptionCategory,
    AssumptionCriticality,
    AssumptionStatus,
    CandidateState,
    DecisionType,
    EvidenceDirection,
    EvidenceTier,
    EvidenceType,
    RunStatus,
)


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class CanonicalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: int = Field(default=1, ge=1)
    run_id: str


class OpportunitySignal(CanonicalRecord):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class DigitalEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_service: bool
    acquisition: bool
    sales: bool
    fulfilment: bool
    operations: bool
    infrastructure: bool
    payments: bool
    support: bool
    scaling: bool
    geography: bool


class AutonomousScalability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_automation_ratio: float = Field(ge=0, le=1)
    human_minutes_per_customer: float = Field(ge=0)
    human_minutes_per_customer_at_10x: float = Field(ge=0)
    human_only_tasks: list[str] = Field(default_factory=list)
    credible_transition_plan: bool


class BusinessIdea(CanonicalRecord):
    problem_id: str
    title: str = Field(min_length=1)
    one_sentence_thesis: str = Field(min_length=1)
    target_customer: str = Field(min_length=1)
    buyer: str | None = None
    user: str | None = None
    value_proposition: str = Field(min_length=1)
    product_form: str = Field(min_length=1)
    delivery_model: str = Field(min_length=1)
    why_now: str | None = None
    digital_eligibility: DigitalEligibility | None = None
    autonomous_scalability: AutonomousScalability | None = None
    assumption_ids: list[str] = Field(default_factory=list)
    competitor_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    lifecycle_state: CandidateState = CandidateState.GENERATED


class Assumption(CanonicalRecord):
    idea_id: str
    category: AssumptionCategory
    statement: str = Field(min_length=1)
    criticality: AssumptionCriticality
    falsification_condition: str = Field(min_length=1)
    validation_condition: str = Field(min_length=1)
    prior_confidence: float | None = Field(default=None, ge=0, le=1)
    current_confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_for_ids: list[str] = Field(default_factory=list)
    evidence_against_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    status: AssumptionStatus = AssumptionStatus.UNKNOWN
    uncertainty: float = Field(default=1.0, ge=0, le=1)


class EvidenceLineageGroup(CanonicalRecord):
    root_source_identifier: str
    member_evidence_ids: list[str] = Field(default_factory=list)


class EvidenceItem(CanonicalRecord):
    source_identifier: str
    source_url: HttpUrl | None = None
    source_type: str
    publisher: str | None = None
    author: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = None
    extracted_fact: str = Field(min_length=1)
    excerpt_pointer: str | None = None
    tier: EvidenceTier
    evidence_type: EvidenceType
    direction: EvidenceDirection
    reliability_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    lineage_group_id: str
    content_hash: str = Field(min_length=16)


class Competitor(CanonicalRecord):
    idea_id: str
    name: str
    canonical_url: HttpUrl | None = None
    positioning: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class ToolCallRecord(CanonicalRecord):
    task_id: str
    actor_id: str
    candidate_id: str | None = None
    assumption_id: str | None = None
    tool: str
    purpose: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0)
    cache_hit: bool = False
    error_category: str | None = None


class ModelCallRecord(CanonicalRecord):
    task_id: str
    actor_id: str
    provider: str
    model: str
    latency_seconds: float = Field(ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None
    structured_output_valid: bool | None = None
    retry_count: int = Field(default=0, ge=0)


class Evaluation(CanonicalRecord):
    idea_id: str
    evaluator_actor_id: str
    evaluator_model: str
    recommendation: DecisionType
    reason_codes: list[str]
    evidence_ids: list[str] = Field(default_factory=list)


class PairwiseMatch(CanonicalRecord):
    left_idea_id: str
    right_idea_id: str
    winner_idea_id: str | None = None
    judge_model: str
    presentation_order_randomized: bool = True
    rationale: str | None = None

    @model_validator(mode="after")
    def winner_is_participant(self) -> PairwiseMatch:
        if self.winner_idea_id not in {None, self.left_idea_id, self.right_idea_id}:
            raise ValueError("winner must be one of the matched ideas")
        return self


class Experiment(CanonicalRecord):
    idea_id: str
    assumption_id: str
    hypothesis: str
    protocol_version: int = Field(default=1, ge=1)
    metric: str
    threshold: str
    sample_definition: str
    budget: float = Field(default=0, ge=0)
    stop_condition: str
    approval_status: ApprovalStatus = ApprovalStatus.REQUIRED


class ExperimentPrediction(CanonicalRecord):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    experiment_id: str
    predicted_value: str
    rationale: str
    locked_at: datetime | None = None


class ExperimentOutcome(CanonicalRecord):
    experiment_id: str
    observed_value: str
    sample_size: int = Field(ge=0)
    raw_artifact_refs: list[str] = Field(default_factory=list)
    interpretation: str


class CandidateDecision(CanonicalRecord):
    idea_id: str
    decision: DecisionType
    reason_codes: list[str]
    resolved_assumption_ids: list[str] = Field(default_factory=list)
    unresolved_assumption_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Run(CanonicalRecord):
    mandate: str = Field(min_length=1)
    status: RunStatus = RunStatus.CREATED
    configuration_hash: str
    closed_at: datetime | None = None

    @model_validator(mode="after")
    def identifier_matches_run_provenance(self) -> Run:
        if self.id != self.run_id:
            raise ValueError("a Run id must match its run_id provenance field")
        return self
