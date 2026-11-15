"""Typed, model-produced records accepted by the live MVP crews."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dbie.domain.enums import (
    AssumptionCategory,
    AssumptionCriticality,
    AssumptionStatus,
    CommercialEvidenceClass,
    DecisionType,
    EvidenceDirection,
    EvidenceScope,
)
from dbie.domain.models import (
    AutonomousScalability,
    CommercialForecastMetrics,
    DigitalEligibility,
    ForecastIntervals,
)


class CrewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalDraft(CrewOutput):
    title: str = Field(min_length=3)
    description: str = Field(min_length=20)
    affected_customer: str = Field(min_length=2)
    source_urls: list[str] = Field(default_factory=list)
    problem_frequency: str | None = None
    problem_cost_or_risk: str | None = None


class DiscoveryBatch(CrewOutput):
    signals: list[SignalDraft] = Field(default_factory=list)
    search_gaps: list[str] = Field(default_factory=list)


class RunPlan(CrewOutput):
    mandate_interpretation: str = Field(min_length=20)
    research_questions: list[str] = Field(min_length=1)
    explicit_exclusions: list[str] = Field(default_factory=list)


class IdeaDraft(CrewOutput):
    problem_title: str = Field(min_length=3)
    title: str = Field(min_length=3)
    one_sentence_thesis: str = Field(min_length=10)
    target_customer: str = Field(min_length=2)
    buyer: str | None = None
    user: str | None = None
    value_proposition: str = Field(min_length=10)
    product_form: str = Field(min_length=2)
    delivery_model: str = Field(min_length=2)
    why_now: str | None = None
    novelty_lineage: str = Field(min_length=5)
    signal_titles: list[str] = Field(min_length=1)
    digital_eligibility: DigitalEligibility
    autonomous_scalability: AutonomousScalability


class IdeaBatch(CrewOutput):
    ideas: list[IdeaDraft] = Field(default_factory=list)


class EligibilityAssessment(CrewOutput):
    candidate_id: str
    recommended_eligible: bool
    concerns: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)


class EligibilityBatch(CrewOutput):
    assessments: list[EligibilityAssessment] = Field(default_factory=list)


class AssumptionDraft(CrewOutput):
    candidate_id: str
    category: AssumptionCategory
    statement: str = Field(min_length=8)
    criticality: AssumptionCriticality
    falsification_condition: str = Field(min_length=8)
    validation_condition: str = Field(min_length=8)


class AssumptionBatch(CrewOutput):
    assumptions: list[AssumptionDraft] = Field(default_factory=list)


class EvidenceClaim(CrewOutput):
    candidate_id: str
    assumption_id: str
    source_url: str = Field(min_length=4)
    source_title: str = Field(min_length=2)
    publisher: str | None = None
    extracted_fact: str = Field(min_length=10)
    excerpt_pointer: str | None = None
    direction: EvidenceDirection
    reliability_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    commercial_classification: CommercialEvidenceClass = CommercialEvidenceClass.UNKNOWN
    commercial_scope: EvidenceScope = EvidenceScope.UNKNOWN


class EvidenceBatch(CrewOutput):
    claims: list[EvidenceClaim] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)


class AssumptionRecommendation(CrewOutput):
    assumption_id: str
    recommended_status: AssumptionStatus
    rationale: str = Field(min_length=8)
    evidence_ids: list[str] = Field(default_factory=list)


class ValidationBatch(CrewOutput):
    recommendations: list[AssumptionRecommendation] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class BusinessModelDraft(CrewOutput):
    candidate_id: str
    name: str = Field(min_length=3)
    buyer: str = Field(min_length=2)
    pricing_model: str = Field(min_length=3)
    acquisition_channel: str = Field(min_length=3)
    delivery_mechanism: str = Field(min_length=3)
    key_cost_drivers: list[str] = Field(default_factory=list)
    distinct_assumptions: list[str] = Field(default_factory=list)


class BusinessModelBatch(CrewOutput):
    models: list[BusinessModelDraft] = Field(default_factory=list)


class RedTeamDraft(CrewOutput):
    candidate_id: str
    attack: str = Field(min_length=10)
    severity: int = Field(ge=1, le=5)
    evidence_urls: list[str] = Field(default_factory=list)
    unresolved: bool = True


class RedTeamBatch(CrewOutput):
    findings: list[RedTeamDraft] = Field(default_factory=list)


class PairwiseJudgment(CrewOutput):
    left_candidate_id: str
    right_candidate_id: str
    winner_candidate_id: str | None
    rationale: str = Field(min_length=8)

    @model_validator(mode="after")
    def winner_is_a_participant(self) -> PairwiseJudgment:
        if self.winner_candidate_id not in {
            None,
            self.left_candidate_id,
            self.right_candidate_id,
        }:
            raise ValueError("pairwise winner must be one of the supplied candidates")
        return self


class PairwiseBatch(CrewOutput):
    judgments: list[PairwiseJudgment] = Field(default_factory=list)
    portfolio_observations: list[str] = Field(default_factory=list)


class ExperimentProtocolDraft(CrewOutput):
    candidate_id: str
    assumption_id: str
    hypothesis: str = Field(min_length=10)
    metric: str = Field(min_length=3)
    threshold: str = Field(min_length=3)
    sample_definition: str = Field(min_length=5)
    budget: float = Field(default=0, ge=0)
    stop_condition: str = Field(min_length=5)
    predicted_value: str = Field(min_length=3)
    prediction_rationale: str = Field(min_length=8)
    predicted_metrics: CommercialForecastMetrics = Field(default_factory=CommercialForecastMetrics)
    scenario_intervals: ForecastIntervals = Field(default_factory=ForecastIntervals)


class ExperimentBatch(CrewOutput):
    experiments: list[ExperimentProtocolDraft] = Field(default_factory=list)


class ObservationDecisionDraft(CrewOutput):
    candidate_id: str
    recommendation: DecisionType
    reason_codes: list[str] = Field(min_length=1)
    observed_outcome_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=10)


class ObservationDecisionBatch(CrewOutput):
    decisions: list[ObservationDecisionDraft] = Field(default_factory=list)
    unexecuted_experiment_ids: list[str] = Field(default_factory=list)


class DossierNarrative(CrewOutput):
    candidate_id: str
    description: str
    competitors: list[str] = Field(default_factory=list)
    business_model_variants: list[str] = Field(default_factory=list)
    monthly_price: float | None = Field(default=None, gt=0)
    variable_cost_per_customer: float | None = Field(default=None, ge=0)
    unknowns: list[str] = Field(default_factory=list)
    recommended_experiments: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def description_is_substantial(cls, value: str) -> str:
        if len(re.findall(r"\b[\w'-]+\b", value)) < 100:
            raise ValueError("business opportunity description requires 100 words")
        return value


class DossierBatch(CrewOutput):
    dossiers: list[DossierNarrative] = Field(default_factory=list)


class RunConclusion(CrewOutput):
    summary: str = Field(min_length=20)
    recommended_actions: list[str] = Field(default_factory=list)
    decision_counts: dict[DecisionType, int] = Field(default_factory=dict)
