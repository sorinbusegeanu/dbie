"""Real Ollama/CrewAI executor for every phase inside the v0.6 MVP cut line."""

from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from dbie.crews.catalog import (
    DISCOVERY_SPECS,
    IDEATION_SPECS,
    RED_TEAM_SPECS,
    SYNTHESIS_SPECS,
    VALIDATION_SPECS,
    ActorSpec,
)
from dbie.crews.outputs import (
    AssumptionBatch,
    BusinessModelBatch,
    DiscoveryBatch,
    DossierBatch,
    EligibilityBatch,
    EvidenceBatch,
    ExperimentBatch,
    IdeaBatch,
    ObservationDecisionBatch,
    PairwiseBatch,
    RedTeamBatch,
    RunConclusion,
    RunPlan,
    ValidationBatch,
)
from dbie.crews.stage_runner import CrewTaskRequest, StageTaskRunner
from dbie.domain.enums import (
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
from dbie.domain.evidence import independent_lineage_count
from dbie.domain.commercial import (
    calculate_economics,
    estimated_business_model_inputs,
    grade_commercial_evidence,
)
from dbie.domain.decisions import ReadinessPolicy, assess_decision_readiness
from dbie.domain.models import (
    Assumption,
    BusinessIdea,
    Evaluation,
    EvidenceItem,
    Experiment,
    ExperimentPrediction,
    OpportunitySignal,
    PairwiseMatch,
    Run,
)
from dbie.domain.memory import BusinessLesson
from dbie.flows.state import PipelineState, StageName
from dbie.models.roles import ModelRole
from dbie.persistence.db import Database
from dbie.persistence.repositories import (
    AssumptionRepository,
    BusinessLessonRepository,
    CandidateRepository,
    EvaluationRepository,
    EvidenceRepository,
    ExperimentOutcomeRepository,
    ExperimentPredictionRepository,
    ExperimentRepository,
    PairwiseMatchRepository,
    RunRepository,
)
from dbie.reporting.dossier import (
    AssumptionSummary,
    Dossier,
    EvidenceReference,
    write_dossier,
)
from dbie.services.assumption_pipeline import decompose_idea, validate_assumption
from dbie.services.candidate_service import CandidateService
from dbie.services.run_workspace import RunWorkspaceManager
from dbie.services.tournament import RankedCandidate, rank_matches
from dbie.services.validation import RedTeamFinding, validation_decision
from dbie.tools.audit import ToolAuditRecord
from dbie.tools.contracts import SourceProvenance, ToolName
from dbie.tools.gateway import ToolGateway
from dbie.tools.normalization.web import canonicalize_url


_EVIDENCE_REQUIRED_TOOLS = (
    ToolName.DATABASE_QUERY,
    ToolName.WEB_SEARCH,
    ToolName.FETCH_PAGE,
)

_FINALIZATION_REQUIRED_TOOLS = (
    ToolName.DATABASE_QUERY,
    ToolName.SEMANTIC_MEMORY_SEARCH,
)


class LiveMVPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_signals: int = Field(default=500, ge=1, le=500)
    target_raw_ideas: int = Field(default=250, ge=1, le=500)
    max_validation_candidates: int = Field(default=25, ge=1, le=25)
    strict_generation_targets: bool = True
    duplicate_similarity_threshold: float = Field(default=0.55, ge=0.1, le=1)
    minimum_memory_similarity: float = Field(default=0.15, ge=-1, le=1)
    memory_retrieval_limit: int = Field(default=5, ge=1, le=100)


class LiveMVPExecutor:
    """Keep domain truth deterministic while agents perform bounded open work."""

    def __init__(
        self,
        database: Database,
        output_directory: Path,
        gateway: ToolGateway,
        task_runner: StageTaskRunner,
        memory: Any,
        *,
        config: LiveMVPConfig | None = None,
        readiness_policy: ReadinessPolicy | None = None,
        configuration_hash: str = "live-v06",
    ) -> None:
        self.database = database
        self.output_directory = Path(output_directory)
        self.gateway = gateway
        self.task_runner = task_runner
        self.memory = memory
        self.config = config or LiveMVPConfig()
        self.readiness_policy = readiness_policy or ReadinessPolicy()
        self.configuration_hash = configuration_hash
        self.runs = RunRepository(database)
        self.candidates = CandidateRepository(database)
        self.lessons = BusinessLessonRepository(database)
        self.assumptions = AssumptionRepository(database)
        self.evidence = EvidenceRepository(database)
        self.experiments = ExperimentRepository(database)
        self.experiment_predictions = ExperimentPredictionRepository(database)
        self.experiment_outcomes = ExperimentOutcomeRepository(database)
        self.evaluations = EvaluationRepository(database)
        self.matches = PairwiseMatchRepository(database)
        self.workspaces = RunWorkspaceManager(self.output_directory)

    def execute(self, stage: StageName, state: PipelineState) -> dict[str, Any]:
        self.workspaces.append_activity(state.run_id, f"stage {stage.value}: started")
        try:
            result = getattr(self, f"_{stage.value}")(state)
        except Exception:
            self.workspaces.append_activity(state.run_id, f"stage {stage.value}: failed")
            raise
        self.workspaces.append_activity(state.run_id, f"stage {stage.value}: completed")
        return result

    def _initialize_run(self, state: PipelineState) -> dict[str, Any]:
        self.database.initialize()
        self.workspaces.ensure(state.run_id)
        self.runs.create(
            Run(
                id=state.run_id,
                run_id=state.run_id,
                mandate=state.mandate,
                configuration_hash=self.configuration_hash,
            )
        )
        self.runs.set_status(state.run_id, RunStatus.RUNNING)
        spec = _spec("Research Planner", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="initialize-research-plan",
            stage_id=StageName.INITIALIZE_RUN.value,
            crew_name="Run Planning Crew",
            spec=spec,
            description=(
                f"Interpret this DBIE mandate: {state.mandate!r}. Use "
                "semantic_memory_search to identify related prior learning. The run "
                "record has already been created and verified deterministically; do not "
                "query unrelated database entities to confirm it. Define the central "
                "research questions and explicitly exclude physical, labor-linear, and "
                "consequential external actions from this MVP run."
            ),
            expected_output="A typed RunPlan with research questions and exclusions.",
            output_model=RunPlan,
            dependency_barrier=0,
            required_tools=(ToolName.SEMANTIC_MEMORY_SEARCH,),
        )
        plan = RunPlan.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        return {
            "artifacts": {
                "execution_mode": "live_crewai_ollama",
                "mvp_version": "v0.6",
                "configuration_hash": self.configuration_hash,
                "run_plan": plan.model_dump(mode="json"),
            }
        }

    def _discover_signals(self, state: PipelineState) -> dict[str, Any]:
        per_agent = math.ceil(self.config.target_signals / len(DISCOVERY_SPECS))
        requests = [
            CrewTaskRequest(
                task_id=f"discovery-{index}-{_slug(spec.role)}",
                stage_id=StageName.DISCOVER_SIGNALS.value,
                crew_name="Opportunity Discovery Crew",
                spec=spec,
                description=(
                    f"Research the mandate: {state.mandate!r}. Use your configured "
                    "DBIE tools before answering. When web_search returns candidate "
                    "pages, use fetch_page where available before treating page text "
                    "as evidence. Return at least "
                    f"{per_agent} distinct costly/frequent/risky problem signals. "
                    "Every source URL must come from a tool result; list unresolved "
                    "search gaps instead of inventing support."
                ),
                expected_output="A typed DiscoveryBatch with grounded signal records.",
                output_model=DiscoveryBatch,
                dependency_barrier=1,
                required_tools=(ToolName.SEARCH_REGULATIONS,)
                if spec.role == "Regulatory Scout"
                else spec.tools,
            )
            for index, spec in enumerate(DISCOVERY_SPECS)
        ]
        outputs = self.task_runner.run_tasks(state.run_id, requests)
        signals: list[OpportunitySignal] = []
        seen: set[str] = set()
        search_gaps: list[str] = []
        for request in requests:
            batch = DiscoveryBatch.model_validate(outputs[request.task_id])
            permitted_urls = self._source_urls_for_task(request.task_id)
            search_gaps.extend(batch.search_gaps)
            for draft in batch.signals:
                source_urls = [
                    url
                    for url in draft.source_urls
                    if url in permitted_urls or canonicalize_url(url) in permitted_urls
                ]
                if not source_urls:
                    search_gaps.append(
                        f"Ungrounded signal omitted: {draft.title} ({request.spec.role})"
                    )
                    continue
                key = _normalize_key(draft.title)
                if key in seen:
                    continue
                seen.add(key)
                signal = OpportunitySignal(
                    run_id=state.run_id,
                    title=draft.title,
                    description=draft.description,
                    source_ids=source_urls,
                )
                signals.append(signal)
        if self.config.strict_generation_targets and len(signals) < self.config.target_signals:
            raise ValueError(
                f"live discovery returned {len(signals)} grounded signals; "
                f"target is {self.config.target_signals}"
            )
        retained = signals[: self.config.target_signals]
        for signal in retained:
            self._index(state.run_id, "PROBLEM", signal.id, f"{signal.title}. {signal.description}")
        return {
            "signal_ids": [item.id for item in retained],
            "artifacts": {
                "signals": [item.model_dump(mode="json") for item in retained],
                "discovery_search_gaps": search_gaps,
                "observed_signal_count": len(retained),
                "excluded_signal_count": max(0, len(signals) - len(retained)),
            },
        }

    def _generate_ideas(self, state: PipelineState) -> dict[str, Any]:
        signals = state.artifacts.get("signals", [])
        prior_ideas = self.candidates.all()
        prior_context = [
            {
                "candidate_id": item.id,
                "run_id": item.run_id,
                "title": item.title,
                "problem": item.problem_id,
                "customer": item.target_customer,
                "buyer": item.buyer,
                "value": item.value_proposition,
                "solution": item.product_form,
                "lifecycle": item.lifecycle_state.value,
                "decision_reasons": next((event["payload"].get("reason_codes", []) for event in reversed(self.candidates.events.for_entity("BusinessIdea", item.id)) if event["event_type"] == "INVESTMENT_DECISION_RECORDED"), []),
            }
            for item in prior_ideas[-30:]
        ]
        per_agent = math.ceil(self.config.target_raw_ideas / len(IDEATION_SPECS))
        signal_context = json.dumps(signals, ensure_ascii=False)
        requests = [
            CrewTaskRequest(
                task_id=f"ideation-{index}-{_slug(spec.role)}",
                stage_id=StageName.GENERATE_IDEAS.value,
                crew_name="Idea Generation Crew",
                spec=spec,
                description=(
                    "First use semantic_memory_search to check for related prior ideas. "
                    "The following persisted candidate history is context: avoid duplicates, "
                    "but retain materially different products for the same problem. A prior "
                    "rejection can be reconsidered only with explicit new evidence or a "
                    "materially changed circumstance; explain that in novelty_lineage. "
                    "Prior candidates:\n" + json.dumps(prior_context, ensure_ascii=False) + "\n"
                    f"Then generate at least {per_agent} materially distinct business "
                    f"ideas through the {spec.role} lens for mandate {state.mandate!r}. "
                    "Every idea must cite one or more supplied signal titles and provide "
                    "all digital-only and autonomous-scalability fields. For the hard "
                    "eligibility schema, every digital_eligibility field must describe "
                    "whether that function is fully digital: set payments=true when "
                    "payments are digitally fulfilled (it does not mean the product moves "
                    "money), and do not propose an idea if any dimension cannot be fully "
                    "digital. human_minutes_per_customer_at_10x must be strictly lower "
                    "than human_minutes_per_customer and must reflect improving marginal "
                    "human burden at scale. Do not validate the ideas. Signals:\n"
                    + signal_context
                ),
                expected_output="A typed IdeaBatch containing distinct complete ideas.",
                output_model=IdeaBatch,
                dependency_barrier=2,
                required_tools=(ToolName.SEMANTIC_MEMORY_SEARCH,),
            )
            for index, spec in enumerate(IDEATION_SPECS)
        ]
        outputs = self.task_runner.run_tasks(state.run_id, requests)
        unique: list[Any] = []
        seen: set[str] = set()
        duplicate_decisions: list[dict[str, Any]] = []
        signal_titles = {
            _normalize_key(str(item.get("title", ""))) for item in signals
        }
        for request in requests:
            batch = IdeaBatch.model_validate(outputs[request.task_id])
            for draft in batch.ideas:
                key = _normalize_key(draft.one_sentence_thesis)
                if key in seen:
                    duplicate_id = str(uuid4())
                    duplicate_decisions.append({"candidate_id": duplicate_id, "title": draft.title, "status": "REJECTED", "reason": "SAME_RUN_EXACT_THESIS"})
                    self.candidates.events.append(
                        run_id=state.run_id, entity_type="OpportunityDeduplication",
                        entity_id=duplicate_id, event_type="CANDIDATE_REJECTED_AS_DUPLICATE",
                        payload={"title": draft.title, "reason": "SAME_RUN_EXACT_THESIS"},
                    )
                    continue
                if not any(
                    _normalize_key(title) in signal_titles for title in draft.signal_titles
                ):
                    continue
                seen.add(key)
                unique.append(draft)
        if self.config.strict_generation_targets and len(unique) < self.config.target_raw_ideas:
            raise ValueError(
                f"live ideation returned {len(unique)} valid unique ideas; "
                f"target is {self.config.target_raw_ideas}"
            )
        ideas: list[BusinessIdea] = []
        memory_retrieval_failures: list[str] = []
        for draft in unique[: self.config.target_raw_ideas]:
            candidate_pool = [*prior_ideas, *ideas]
            semantic_ids: set[str] = set()
            try:
                semantic_hits = self.memory.search(
                    f"{draft.problem_title}. {draft.one_sentence_thesis}. {draft.target_customer}. "
                    f"{draft.buyer or ''}. {draft.value_proposition}. {draft.product_form}. {draft.delivery_model}",
                    top_k=self.config.memory_retrieval_limit,
                    entity_types={"IDEA"},
                    min_similarity=self.config.minimum_memory_similarity,
                )
                semantic_ids = {item.entity_id for item in semantic_hits}
            except Exception as exc:
                semantic_ids = set()
                memory_retrieval_failures.append(f"{draft.title}: {type(exc).__name__}")
            comparisons = []
            for historical in candidate_pool:
                score = _compare_idea_dimensions(draft, historical)
                if historical.id in semantic_ids or score["similarity"] >= self.config.duplicate_similarity_threshold:
                    comparisons.append((historical, score))
            duplicate = next(
                ((historical, score) for historical, score in comparisons
                 if score["duplicate"] and score["similarity"] >= self.config.duplicate_similarity_threshold),
                None,
            )
            signal_by_title = {_normalize_key(str(item.get("title", ""))): item for item in signals}
            new_signal_sources = list(dict.fromkeys(
                str(source_id)
                for title in draft.signal_titles
                for source_id in signal_by_title.get(_normalize_key(title), {}).get("source_ids", [])
            ))
            new_signal_ids = list(dict.fromkeys(
                str(signal_by_title.get(_normalize_key(title), {}).get("id"))
                for title in draft.signal_titles
                if signal_by_title.get(_normalize_key(title), {}).get("id")
            ))
            reconsidered = _may_reconsider(duplicate[0], draft, new_signal_sources) if duplicate else False
            if duplicate and not reconsidered:
                duplicate_id = str(uuid4())
                duplicate_reason = (
                    "SEMANTIC_DUPLICATE"
                    if duplicate[0].lifecycle_state not in {CandidateState.KILL, CandidateState.ITERATE, CandidateState.MORE_EVIDENCE}
                    else "RECONSIDERATION_REQUIRES_EXPLICIT_RATIONALE_AND_NEW_SOURCES"
                )
                duplicate_decisions.append({
                    "candidate_id": duplicate_id,
                    "title": draft.title, "status": "LINKED", "reason": duplicate_reason,
                    "linked_candidate_id": duplicate[0].id, "prior_run_id": duplicate[0].run_id,
                    "similarity": duplicate[1]["similarity"], "dimensions": duplicate[1],
                    "retrieval_method": "semantic_shortlist_and_dimension_check" if duplicate[0].id in semantic_ids else "deterministic_dimension_fallback",
                })
                self.candidates.events.append(
                    run_id=state.run_id, entity_type="OpportunityDeduplication",
                    entity_id=duplicate_id, event_type="CANDIDATE_LINKED_AS_DUPLICATE",
                    payload={"title": draft.title, "candidate_id": duplicate_id, "linked_candidate_id": duplicate[0].id, "reason": duplicate_reason},
                )
                continue
            idea = BusinessIdea(
                run_id=state.run_id,
                problem_id=sha256(draft.problem_title.encode()).hexdigest()[:24],
                canonical_identity=sha256(_canonical_opportunity_identity(draft).encode()).hexdigest(),
                title=draft.title,
                one_sentence_thesis=draft.one_sentence_thesis,
                target_customer=draft.target_customer,
                buyer=draft.buyer,
                user=draft.user,
                value_proposition=draft.value_proposition,
                product_form=draft.product_form,
                delivery_model=draft.delivery_model,
                why_now=draft.why_now,
                novelty_lineage=draft.novelty_lineage,
                source_signal_ids=new_signal_ids,
                source_urls=new_signal_sources,
                duplicate_of_ids=[duplicate[0].id] if reconsidered else [],
                digital_eligibility=draft.digital_eligibility,
                autonomous_scalability=draft.autonomous_scalability,
            )
            self.candidates.create(idea)
            self._index(
                state.run_id,
                "IDEA",
                idea.id,
                f"{idea.title}. {idea.one_sentence_thesis}. {idea.target_customer}",
            )
            ideas.append(idea)
            duplicate_decisions.append({
                "title": draft.title,
                "status": "RECONSIDERED" if reconsidered else ("RELATED_ACCEPTED" if any(score["related"] for _, score in comparisons) else "ACCEPTED"),
                "reason": "EXPLICIT_NEW_EVIDENCE_OR_CHANGED_CIRCUMSTANCE" if reconsidered else "NO_MATERIAL_DUPLICATE",
                "linked_candidate_id": duplicate[0].id if duplicate else None,
            })
            if reconsidered:
                self.candidates.events.append(
                    run_id=state.run_id, entity_type="BusinessIdea", entity_id=idea.id,
                    event_type="OPPORTUNITY_RECONSIDERED",
                    payload={"prior_candidate_id": duplicate[0].id, "reason": "EXPLICIT_NEW_EVIDENCE_AND_NEW_SOURCE_IDS", "new_source_ids": sorted(set(new_signal_sources) - set(duplicate[0].source_urls)), "novelty_lineage": draft.novelty_lineage},
                )
        return {
            "candidate_ids": [item.id for item in ideas],
            "artifacts": {
                "raw_idea_count": len(unique),
                "deduplicated_idea_count": len(ideas),
                "idea_records": [item.model_dump(mode="json") for item in ideas],
                "duplicate_decisions": duplicate_decisions,
                "duplicate_count": sum(item["status"] in {"REJECTED", "LINKED"} for item in duplicate_decisions),
                "memory_retrieval_failures": memory_retrieval_failures,
            },
        }

    def _eligibility_gate(self, state: PipelineState) -> dict[str, Any]:
        ideas = [self.candidates.get(identifier) for identifier in state.candidate_ids]
        spec = _spec("Opportunity Synthesizer", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="eligibility-review",
            stage_id=StageName.ELIGIBILITY_GATE.value,
            crew_name="Digital Eligibility Crew",
            spec=spec,
            description=(
                "Review the supplied candidates for digital-only delivery and "
                "autonomous scalability. Use database_query LIST_IDEAS and "
                "semantic_memory_search. Your recommendation is advisory; report "
                "missing facts and concerns without changing any hard gate. Candidates:\n"
                + json.dumps([item.model_dump(mode="json") for item in ideas])
            ),
            expected_output="A typed EligibilityBatch with one advisory assessment per candidate.",
            output_model=EligibilityBatch,
            dependency_barrier=3,
            required_tools=spec.tools,
        )
        output = EligibilityBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        advisory = {item.candidate_id: item for item in output.assessments}
        service = CandidateService(self.candidates)
        eligible: list[str] = []
        hard_results: dict[str, Any] = {}
        for idea in ideas:
            result = service.apply_eligibility(idea.id)
            hard_results[idea.id] = {
                "eligible": result.eligible,
                "reason_codes": result.reason_codes,
                "agent_assessment": advisory.get(idea.id).model_dump(mode="json")
                if idea.id in advisory
                else None,
            }
            if result.eligible:
                eligible.append(idea.id)
            else:
                rejected_idea = self.candidates.set_decision(
                    idea.id, list(result.reason_codes),
                    ["Change the delivery or product model to satisfy every hard eligibility criterion."],
                    DecisionType.KILL,
                )
                reason_codes = list(result.reason_codes)
                self._index(
                    state.run_id, "IDEA", idea.id,
                    f"{rejected_idea.title}. {rejected_idea.one_sentence_thesis}. "
                    f"Lifecycle KILL after eligibility. Reasons: {', '.join(reason_codes)}",
                )
                lesson = self.lessons.create(BusinessLesson(
                    category="hard_eligibility",
                    opportunity_id=idea.id,
                    run_id=state.run_id,
                    task_id="eligibility-gate",
                    attempted_or_assumed="Opportunity can be delivered digitally and scale autonomously.",
                    expected_result="All deterministic digital eligibility and scalability checks pass.",
                    observed_result="Candidate failed the deterministic eligibility gate.",
                    root_cause="; ".join(reason_codes) or "Eligibility requirements not met",
                    recommended_behavior="Do not revive without materially changing the product or delivery model and rechecking every hard eligibility criterion.",
                    applicability_conditions=["same product and delivery model"],
                    confidence=1,
                    validation_status="VALIDATED",
                ))
                self._index(state.run_id, "LESSON", lesson.id, _lesson_memory_text(lesson))
        selected = eligible[: self.config.max_validation_candidates]
        if not selected:
            raise ValueError(
                "live eligibility produced no candidates that passed the deterministic "
                "digital-only and autonomous-scalability gates"
            )
        return {
            "eligible_candidate_ids": selected,
            "artifacts": {
                "eligibility_results": hard_results,
                "all_eligible_candidate_ids": eligible,
                "validation_capacity_deferred_ids": eligible[len(selected) :],
            },
        }

    def _decompose_assumptions(self, state: PipelineState) -> dict[str, Any]:
        ideas = [
            self.candidates.get(identifier) for identifier in state.eligible_candidate_ids
        ]
        spec = _spec("Assumption Decomposer", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="assumption-decomposition",
            stage_id=StageName.DECOMPOSE_ASSUMPTIONS.value,
            crew_name="Assumption Crew",
            spec=spec,
            description=(
                "Use database_query LIST_IDEAS and semantic_memory_search. Decompose "
                "every supplied idea into atomic, falsifiable assumptions covering "
                "DEMAND, BUYER, WTP, DISTRIBUTION, FEASIBILITY, AUTOMATION, ECONOMICS, "
                "DEFENSIBILITY, REGULATORY, and TIMING. Include two distinct automation "
                "assumptions: automation ratio and marginal human burden. Candidates:\n"
                + json.dumps([item.model_dump(mode="json") for item in ideas])
            ),
            expected_output="A typed AssumptionBatch with candidate IDs and falsification tests.",
            output_model=AssumptionBatch,
            dependency_barrier=4,
            required_tools=spec.tools,
        )
        output = AssumptionBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        drafts: dict[tuple[str, AssumptionCategory], list[Any]] = defaultdict(list)
        for draft in output.assumptions:
            drafts[(draft.candidate_id, draft.category)].append(draft)
        records: list[Assumption] = []
        for idea in ideas:
            for canonical in decompose_idea(idea):
                candidates = drafts[(idea.id, canonical.category)]
                if candidates:
                    draft = candidates.pop(0)
                    canonical.statement = draft.statement
                    canonical.falsification_condition = draft.falsification_condition
                    canonical.validation_condition = draft.validation_condition
                self.assumptions.create(canonical)
                self._index(
                    state.run_id,
                    "ASSUMPTION",
                    canonical.id,
                    f"{canonical.category.value}: {canonical.statement}",
                )
                records.append(canonical)
            self.candidates.set_state(idea.id, CandidateState.VALIDATING)
        return {
            "artifacts": {
                "assumptions": [item.model_dump(mode="json") for item in records]
            }
        }

    def _collect_evidence(self, state: PipelineState) -> dict[str, Any]:
        focus = {
            "Demand Validator": {
                AssumptionCategory.DEMAND,
                AssumptionCategory.BUYER,
                AssumptionCategory.WTP,
            },
            "Economics Analyst": {AssumptionCategory.ECONOMICS},
            "Distribution Analyst": {AssumptionCategory.DISTRIBUTION},
            "Technical Analyst": {
                AssumptionCategory.FEASIBILITY,
                AssumptionCategory.AUTOMATION,
            },
            "Competitive Analyst": {AssumptionCategory.DEFENSIBILITY},
            "Regulatory Validator": {
                AssumptionCategory.REGULATORY,
                AssumptionCategory.TIMING,
            },
        }
        assumptions = [
            item
            for candidate_id in state.eligible_candidate_ids
            for item in self.assumptions.for_idea(candidate_id)
        ]
        ideas = {
            identifier: self.candidates.get(identifier)
            for identifier in state.eligible_candidate_ids
        }
        requests: list[CrewTaskRequest[Any]] = []
        for index, spec in enumerate(VALIDATION_SPECS):
            selected = [item for item in assumptions if item.category in focus[spec.role]]
            requests.append(
                CrewTaskRequest(
                    task_id=f"evidence-{index}-{_slug(spec.role)}",
                    stage_id=StageName.COLLECT_EVIDENCE.value,
                    crew_name="Market and Evidence Research Crew",
                    spec=spec,
                    description=(
                        "Collect real, source-grounded evidence for the supplied atomic "
                        "assumptions. First call database_query LIST_ASSUMPTIONS. Use the "
                        "external research tools configured for your role. For ordinary "
                        "web results, call fetch_page before returning an evidence claim; "
                        "search snippets are not evidence. Use official regulatory sources "
                        "for legal claims and python_execute for deterministic economics or "
                        "technical calculations. Return exact source URLs from tool results, "
                        "both support and contradiction, and explicit gaps. For each claim, "
                        "classify commercial evidence only when directly supported by the "
                        "source as MARKET_SIGNAL, EXISTING_MARKET, CUSTOMER_VALIDATION, "
                        "PURCHASE_INTENT, or OBSERVED_TRANSACTION; otherwise return UNKNOWN. "
                        "Mark scope MARKET for category-wide or competitor evidence and PRODUCT "
                        "only for evidence about this proposed product. Never treat a competitor "
                        "or market signal as product-specific purchase evidence. Ideas:\n"
                        + json.dumps(
                            [item.model_dump(mode="json") for item in ideas.values()]
                        )
                        + "\nAssumptions assigned to you:\n"
                        + json.dumps([item.model_dump(mode="json") for item in selected])
                    ),
                    expected_output="A typed EvidenceBatch containing only tool-grounded claims.",
                    output_model=EvidenceBatch,
                    dependency_barrier=5,
                    required_tools=_EVIDENCE_REQUIRED_TOOLS,
                )
            )
        outputs = self.task_runner.run_tasks(state.run_id, requests)
        assumptions_by_id = {item.id: item for item in assumptions}
        evidence_by_assumption: dict[str, list[dict[str, Any]]] = defaultdict(list)
        rejected: list[dict[str, str]] = []
        gaps: list[str] = []
        for request in requests:
            batch = EvidenceBatch.model_validate(outputs[request.task_id])
            gaps.extend(batch.unresolved_gaps)
            sources = self._sources_for_task(request.task_id)
            for claim in batch.claims:
                assumption = assumptions_by_id.get(claim.assumption_id)
                if assumption is None or assumption.idea_id != claim.candidate_id:
                    rejected.append(
                        {"source": claim.source_url, "reason": "UNKNOWN_ASSUMPTION"}
                    )
                    continue
                provenance = sources.get(claim.source_url) or sources.get(
                    canonicalize_url(claim.source_url)
                )
                if provenance is None:
                    rejected.append(
                        {"source": claim.source_url, "reason": "NOT_IN_TOOL_RESULT"}
                    )
                    continue
                source, tool = provenance
                if source.source_type == "search_result" or tool is ToolName.WEB_SEARCH:
                    rejected.append(
                        {"source": claim.source_url, "reason": "SEARCH_SNIPPET_ONLY"}
                    )
                    continue
                item = self._evidence_from_claim(state.run_id, claim, source)
                persisted = self.evidence.create(item)
                evidence_by_assumption[assumption.id].append(
                    persisted.model_dump(mode="json")
                )
                self._index(
                    state.run_id,
                    "EVIDENCE",
                    persisted.id,
                    f"{persisted.publisher or persisted.source_type}: {persisted.extracted_fact}",
                )
        for assumption in assumptions:
            evidence_by_assumption.setdefault(assumption.id, [])
        return {
            "artifacts": {
                "evidence_by_assumption": dict(evidence_by_assumption),
                "rejected_evidence_claims": rejected,
                "evidence_gaps": gaps,
                "evidence_item_count": sum(
                    len(items) for items in evidence_by_assumption.values()
                ),
            }
        }

    def _validate_assumptions(self, state: PipelineState) -> dict[str, Any]:
        assumptions = [
            item
            for candidate_id in state.eligible_candidate_ids
            for item in self.assumptions.for_idea(candidate_id)
        ]
        evidence_by_assumption = state.artifacts.get("evidence_by_assumption", {})
        spec = _spec("Evidence Reconciler", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="evidence-reconciliation",
            stage_id=StageName.VALIDATE_ASSUMPTIONS.value,
            crew_name="Evidence Validation Crew",
            spec=spec,
            description=(
                "First call database_query with LIST_ASSUMPTIONS, then call it with "
                "LIST_EVIDENCE, and call semantic_memory_search for related prior "
                "learning. Use those tool results as the only research context. "
                "Independently reconcile every returned assumption for the supplied "
                "candidate IDs. Recommend a status and identify contradictions, but "
                "never count model agreement as evidence. The deterministic decision "
                "service will enforce evidence tiers and independent lineages. "
                "Candidate IDs:\n"
                + json.dumps(state.eligible_candidate_ids)
            ),
            expected_output="A typed ValidationBatch with advisory recommendations.",
            output_model=ValidationBatch,
            dependency_barrier=6,
            required_tools=spec.tools,
        )
        advisory = ValidationBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        advisory_by_id = {item.assumption_id: item for item in advisory.recommendations}
        validated: list[dict[str, Any]] = []
        for assumption in assumptions:
            items = [
                EvidenceItem.model_validate(item)
                for item in evidence_by_assumption.get(assumption.id, [])
            ]
            result = validate_assumption(assumption, items)
            self.assumptions.save(result)
            if result.status in {AssumptionStatus.RESEARCH_CONTRADICTED, AssumptionStatus.EXPERIMENT_CONTRADICTED}:
                lesson = self.lessons.create(BusinessLesson(
                    category="contradicted_assumption",
                    opportunity_id=result.idea_id,
                    run_id=state.run_id,
                    task_id="validate-assumptions",
                    attempted_or_assumed=result.statement,
                    expected_result=result.validation_condition,
                    observed_result=result.status.value,
                    root_cause="Recorded contrary evidence contradicts the assumption.",
                    evidence_ids=result.evidence_against_ids,
                    recommended_behavior="Do not reuse this assumption as supported; test a revised claim against independent sources.",
                    applicability_conditions=[result.category.value, "same buyer and product context"],
                    confidence=result.current_confidence or 0.7,
                    validation_status="VALIDATED" if result.evidence_against_ids else "HYPOTHESIS",
                ))
                self._index(state.run_id, "LESSON", lesson.id, _lesson_memory_text(lesson))
            value = result.model_dump(mode="json")
            value["agent_recommendation"] = (
                advisory_by_id[assumption.id].model_dump(mode="json")
                if assumption.id in advisory_by_id
                else None
            )
            validated.append(value)
        return {
            "artifacts": {
                "validated_assumptions": validated,
                "validation_contradictions": advisory.contradictions,
                "lessons_created": [item.model_dump(mode="json") for item in self.lessons.all() if item.run_id == state.run_id],
            }
        }

    def _model_business(self, state: PipelineState) -> dict[str, Any]:
        spec = _spec("Opportunity Synthesizer", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="business-model-comparison",
            stage_id=StageName.MODEL_BUSINESS.value,
            crew_name="Digital Business Model Crew",
            spec=spec,
            description=(
                "First call database_query with LIST_IDEAS, LIST_ASSUMPTIONS, and "
                "LIST_EVIDENCE, then call semantic_memory_search for related prior "
                "learning. Use those tool results as the only research context. For "
                "every supplied candidate ID, formulate at least one concrete fully "
                "digital business model. Keep buyer, pricing, acquisition, delivery, "
                "costs, and the assumptions unique to that model explicit. Do not "
                "convert estimates into evidence and do not merge materially different "
                "models. Candidate IDs:\n"
                + json.dumps(state.eligible_candidate_ids)
            ),
            expected_output=(
                "A typed BusinessModelBatch with one or more distinct models per candidate."
            ),
            output_model=BusinessModelBatch,
            dependency_barrier=7,
            required_tools=spec.tools,
        )
        output = BusinessModelBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        valid_ids = set(state.eligible_candidate_ids)
        models = [
            item for item in output.models if item.candidate_id in valid_ids
        ]
        represented = {item.candidate_id for item in models}
        missing = valid_ids - represented
        if missing:
            raise ValueError(
                "business-model stage omitted candidates: " + ", ".join(sorted(missing))
            )
        return {
            "artifacts": {
                "business_models": [item.model_dump(mode="json") for item in models]
            }
        }

    def _red_team(self, state: PipelineState) -> dict[str, Any]:
        requests = [
            CrewTaskRequest(
                task_id=f"red-team-{index}-{_slug(spec.role)}",
                stage_id=StageName.RED_TEAM.value,
                crew_name="Independent Red Team Crew",
                spec=spec,
                description=(
                    f"Act as {spec.role}. This is an explicit L3 heterogeneous local "
                    "review. First call database_query with LIST_IDEAS, "
                    "LIST_ASSUMPTIONS, and LIST_EVIDENCE, then call "
                    "semantic_memory_search for related prior learning. Use live external "
                    "tools when a factual attack requires new support. Attack the "
                    "candidate IDs without relying on generator persuasion. Return exact "
                    "source URLs from tool results and mark each attack resolved or "
                    "unresolved. Candidate IDs:\n"
                    + json.dumps(state.eligible_candidate_ids)
                ),
                expected_output="A typed RedTeamBatch with candidate-specific attacks.",
                output_model=RedTeamBatch,
                dependency_barrier=8,
                escalation_required=True,
                required_tools=(
                    ToolName.DATABASE_QUERY,
                    ToolName.SEMANTIC_MEMORY_SEARCH,
                ),
            )
            for index, spec in enumerate(RED_TEAM_SPECS)
        ]
        outputs = self.task_runner.run_tasks(state.run_id, requests)
        findings: list[RedTeamFinding] = []
        valid_candidates = set(state.eligible_candidate_ids)
        for request in requests:
            batch = RedTeamBatch.model_validate(outputs[request.task_id])
            tool_sources = self._sources_for_task(request.task_id)
            for draft in batch.findings:
                if draft.candidate_id not in valid_candidates:
                    continue
                evidence_ids = []
                for url in draft.evidence_urls:
                    provenance = tool_sources.get(url) or tool_sources.get(
                        canonicalize_url(url)
                    )
                    if provenance is None:
                        continue
                    source, tool = provenance
                    if source.source_type == "search_result" or tool is ToolName.WEB_SEARCH:
                        continue
                    evidence_item = self.evidence.create(
                        self._red_team_evidence(state.run_id, draft.attack, source)
                    )
                    evidence_ids.append(evidence_item.id)
                finding = RedTeamFinding(
                    candidate_id=draft.candidate_id,
                    actor=request.spec.role,
                    attack=draft.attack,
                    severity=draft.severity,
                    evidence_ids=evidence_ids,
                    unresolved=draft.unresolved,
                )
                findings.append(finding)
                if evidence_ids:
                    lesson = self.lessons.create(BusinessLesson(
                        category="evidence_confirmed_red_team_finding",
                        opportunity_id=draft.candidate_id,
                        run_id=state.run_id,
                        task_id=request.task_id,
                        attempted_or_assumed=draft.attack,
                        expected_result="The proposed opportunity withstands evidence-backed adversarial review.",
                        observed_result="Red-team attack supported by cited source records.",
                        root_cause="Evidence-supported adversarial finding; see linked source records.",
                        evidence_ids=evidence_ids,
                        recommended_behavior="Check this failure mode early in future opportunities with the same buyer, product, or operating condition.",
                        applicability_conditions=["same underlying failure mode"],
                        confidence=min(0.9, 0.5 + 0.1 * len(evidence_ids)),
                        validation_status="VALIDATED",
                    ))
                    self._index(state.run_id, "LESSON", lesson.id, _lesson_memory_text(lesson))
                self.evaluations.create(
                    Evaluation(
                        run_id=state.run_id,
                        idea_id=draft.candidate_id,
                        evaluator_actor_id=_slug(request.spec.role),
                        evaluator_model="JUDGE",
                        recommendation=(
                            DecisionType.MORE_EVIDENCE
                            if draft.unresolved and draft.severity >= 4
                            else DecisionType.BUILD
                        ),
                        reason_codes=[
                            "UNRESOLVED_RED_TEAM_FINDING"
                            if draft.unresolved
                            else "RED_TEAM_ATTACK_RESOLVED"
                        ],
                        evidence_ids=evidence_ids,
                    )
                )
        finalist_ids: list[str] = []
        decisions: dict[str, Any] = {}
        service = CandidateService(self.candidates)
        for candidate_id in state.eligible_candidate_ids:
            service.transition(candidate_id, CandidateState.RED_TEAM)
            decision = validation_decision(
                self.assumptions.for_idea(candidate_id),
                [item for item in findings if item.candidate_id == candidate_id],
                heterogeneous_review=True,
            )
            idea = self.candidates.get(candidate_id)
            assumptions = self.assumptions.for_idea(candidate_id)
            evidence_by_id = {item.id: item for item in self.evidence.for_run(state.run_id)}
            candidate_evidence = [
                evidence_by_id[evidence_id]
                for assumption in assumptions
                for evidence_id in assumption.evidence_for_ids + assumption.evidence_against_ids
                if evidence_id in evidence_by_id
            ]
            grades = grade_commercial_evidence([a.id for a in assumptions], candidate_evidence)
            readiness = assess_decision_readiness(
                idea, assumptions, grades, policy=self.readiness_policy
            )
            if readiness.recommendation is DecisionType.KILL:
                decision = decision.model_copy(update={
                    "decision": DecisionType.KILL,
                    "reason_codes": readiness.reason_codes,
                })
            decisions[candidate_id] = decision.model_dump(mode="json")
            decisions[candidate_id]["readiness_assessment"] = readiness.model_dump(mode="json")
            decisions[candidate_id]["readiness_assessment"]["pipeline_validation_decision"] = decision.decision.value
            decisions[candidate_id]["readiness_assessment"]["pipeline_validation_reason_codes"] = decision.reason_codes
            decisions[candidate_id]["commercial_evidence_grades"] = [item.model_dump(mode="json") for item in grades]
            if decision.decision is DecisionType.BUILD:
                service.transition(
                    candidate_id,
                    CandidateState.FINALIST,
                    self.assumptions.for_idea(candidate_id),
                )
                finalist_ids.append(candidate_id)
            else:
                service.transition(candidate_id, CandidateState(decision.decision.value))
            reconsider_conditions = (
                ["Provide independent customer or purchase evidence addressing the failed assumptions."]
                if decision.decision in {DecisionType.KILL, DecisionType.MORE_EVIDENCE}
                else ["Demonstrate a material change in buyer, product, or delivery model."]
            )
            final_idea = self.candidates.set_decision(candidate_id, decision.reason_codes, reconsider_conditions, decision.decision)
            final_state = final_idea.lifecycle_state.value
            self._index(
                state.run_id,
                "IDEA",
                candidate_id,
                f"{final_idea.title}. {final_idea.one_sentence_thesis}. "
                f"Customer: {final_idea.target_customer}. Decision: {decision.decision.value}. "
                f"Reasons: {', '.join(decision.reason_codes)}",
            )
            if decision.decision is not DecisionType.BUILD:
                lesson = self.lessons.create(BusinessLesson(
                    category="opportunity_decision",
                    opportunity_id=candidate_id,
                    run_id=state.run_id,
                    task_id="red-team",
                    attempted_or_assumed="; ".join(item.statement for item in assumptions[:5]) or final_idea.one_sentence_thesis,
                    expected_result="Critical assumptions are supported sufficiently for a build recommendation.",
                    observed_result=f"Decision {decision.decision.value}; reasons: {', '.join(decision.reason_codes)}",
                    root_cause="Evidence-linked decision rationale" if any(item.evidence_for_ids or item.evidence_against_ids for item in assumptions) else "Unverified model or policy hypothesis; not established as an observed market failure",
                    evidence_ids=list(dict.fromkeys(eid for item in assumptions for eid in item.evidence_for_ids + item.evidence_against_ids)),
                    recommended_behavior="Retrieve this decision and retest the changed or contradicted assumption before proposing this opportunity again.",
                    applicability_conditions=["same or materially similar buyer and product"],
                    confidence=0.75 if any(item.evidence_for_ids or item.evidence_against_ids for item in assumptions) else 0.35,
                    validation_status="VALIDATED" if any(item.evidence_for_ids or item.evidence_against_ids for item in assumptions) else "HYPOTHESIS",
                ))
                self._index(
                    state.run_id, "LESSON", lesson.id,
                    _lesson_memory_text(lesson),
                )
        return {
            "finalist_ids": finalist_ids,
            "artifacts": {
                "red_team_findings": [item.model_dump(mode="json") for item in findings],
                "validation_decisions": decisions,
                "lessons_created": [item.model_dump(mode="json") for item in self.lessons.all() if item.run_id == state.run_id],
            },
        }

    def _rank_portfolio(self, state: PipelineState) -> dict[str, Any]:
        if not state.finalist_ids:
            return {
                "artifacts": {
                    "matches": [],
                    "rankings": [],
                    "portfolio_observations": [
                        "No candidates passed deterministic validation and red-team gates."
                    ],
                }
            }
        judge = ActorSpec(
            role="Portfolio Judge",
            group="portfolio",
            goal="Compare normalized finalists without overriding hard gates",
            tools=(
                ToolName.DATABASE_QUERY,
                ToolName.SEMANTIC_MEMORY_SEARCH,
                ToolName.PYTHON_EXECUTE,
            ),
            model_role=ModelRole.JUDGE,
        )
        pairs = list(combinations(sorted(state.finalist_ids), 2))
        request = CrewTaskRequest(
            task_id="portfolio-tournament",
            stage_id=StageName.RANK_PORTFOLIO.value,
            crew_name="Portfolio Tournament Crew",
            spec=judge,
            description=(
                "This is an explicitly authorized independent portfolio judgment. "
                "Use database_query, semantic_memory_search, and python_execute for a "
                "reproducible comparison check. Judge every supplied pair using only "
                "normalized evidence, unresolved risk, automation, economics, and "
                "distribution plus the deterministic decision_readiness.readiness_score "
                "as a ranking input. That score never overrides an eligibility or "
                "decision gate. Return a tie when evidence does not distinguish a pair. "
                "Do not override hard gates. Pairs:\n"
                + json.dumps(pairs)
                + "\nCandidates:\n"
                + json.dumps(self._normalized_candidate_context(state.finalist_ids))
            ),
            expected_output="A typed PairwiseBatch containing exactly the supplied pairs.",
            output_model=PairwiseBatch,
            dependency_barrier=9,
            escalation_required=True,
            required_tools=judge.tools,
        )
        output = PairwiseBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        judgments = {
            tuple(sorted((item.left_candidate_id, item.right_candidate_id))): item
            for item in output.judgments
        }
        model_id = "JUDGE:" + _spec_model_name(self.task_runner, ModelRole.JUDGE)
        matches: list[PairwiseMatch] = []
        for left, right in pairs:
            judgment = judgments.get(tuple(sorted((left, right))))
            match = PairwiseMatch(
                run_id=state.run_id,
                left_idea_id=left,
                right_idea_id=right,
                winner_idea_id=judgment.winner_candidate_id if judgment else None,
                judge_model=model_id,
                rationale=(
                    judgment.rationale
                    if judgment
                    else "Judge returned no valid comparison; recorded as a tie."
                ),
            )
            self.matches.create(match)
            matches.append(match)
        if len(state.finalist_ids) == 1:
            rankings = [
                RankedCandidate(
                    idea_id=state.finalist_ids[0],
                    rating=1500,
                    rank=1,
                    match_count=0,
                    stability=1,
                )
            ]
        else:
            rankings = rank_matches(matches)
        return {
            "artifacts": {
                "matches": [item.model_dump(mode="json") for item in matches],
                "rankings": [item.model_dump(mode="json") for item in rankings],
                "portfolio_observations": output.portfolio_observations,
            }
        }

    def _design_experiments(self, state: PipelineState) -> dict[str, Any]:
        spec = _spec("Experiment Designer", SYNTHESIS_SPECS)
        decisions = state.artifacts.get("validation_decisions", {})
        decision_candidate_ids = [
            candidate_id
            for candidate_id in state.eligible_candidate_ids
            if decisions.get(candidate_id, {}).get("decision")
            == DecisionType.MORE_EVIDENCE.value
        ]
        unresolved = [
            assumption
            for candidate_id in decision_candidate_ids
            for assumption in self.assumptions.for_idea(candidate_id)
            if assumption.criticality
            in {AssumptionCriticality.FATAL, AssumptionCriticality.MATERIAL}
            and assumption.status
            not in {
                AssumptionStatus.RESEARCH_SUPPORTED,
                AssumptionStatus.EXPERIMENT_SUPPORTED,
            }
        ]
        experiment_candidate_ids = sorted({item.idea_id for item in unresolved})
        request = CrewTaskRequest(
            task_id="experiment-design",
            stage_id=StageName.DESIGN_EXPERIMENTS.value,
            crew_name="Experiment Design Crew",
            spec=spec,
            description=(
                "Use database_query and semantic_memory_search, then python_execute "
                "for any sample, threshold, or budget calculation. Design the cheapest "
                "falsifying digital experiment for each candidate's highest-priority "
                "unresolved assumption. Every protocol must preregister a metric, "
                "threshold, sample, zero-or-bounded budget, stop condition, and locked "
                "prediction. When measurable, also provide numeric structured predictions "
                "for demand, conversion, revenue, CAC, margins, implementation cost, and "
                "launch/first-revenue timing, plus lower/upper scenario intervals. Leave "
                "unsupported values unknown rather than inventing them. Do not launch, "
                "publish, contact anyone, or spend money; all "
                "protocols require human approval. Unresolved assumptions:\n"
                + json.dumps([item.model_dump(mode="json") for item in unresolved])
            ),
            expected_output="A typed ExperimentBatch containing preregistered protocols.",
            output_model=ExperimentBatch,
            dependency_barrier=10,
            required_tools=spec.tools,
        )
        output = ExperimentBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        assumptions = {item.id: item for item in unresolved}
        experiments: list[Experiment] = []
        predictions: list[ExperimentPrediction] = []
        represented: set[str] = set()
        for draft in output.experiments:
            assumption = assumptions.get(draft.assumption_id)
            if assumption is None or assumption.idea_id != draft.candidate_id:
                continue
            experiment = self.experiments.create(
                Experiment(
                    run_id=state.run_id,
                    idea_id=draft.candidate_id,
                    assumption_id=draft.assumption_id,
                    hypothesis=draft.hypothesis,
                    metric=draft.metric,
                    threshold=draft.threshold,
                    sample_definition=draft.sample_definition,
                    budget=draft.budget,
                    stop_condition=draft.stop_condition,
                )
            )
            prediction = self.experiment_predictions.create(
                ExperimentPrediction(
                    run_id=state.run_id,
                    experiment_id=experiment.id,
                    predicted_value=draft.predicted_value,
                    rationale=draft.prediction_rationale,
                    predicted_metrics=draft.predicted_metrics,
                    scenario_intervals=draft.scenario_intervals,
                )
            )
            experiments.append(experiment)
            predictions.append(prediction)
            represented.add(draft.candidate_id)
        missing = set(experiment_candidate_ids) - represented
        if missing:
            raise ValueError(
                "experiment-design stage omitted candidates: "
                + ", ".join(sorted(missing))
            )
        return {
            "artifacts": {
                "experiment_candidate_ids": experiment_candidate_ids,
                "experiments": [item.model_dump(mode="json") for item in experiments],
                "experiment_predictions": [
                    item.model_dump(mode="json") for item in predictions
                ],
            }
        }

    def _observe_and_decide(self, state: PipelineState) -> dict[str, Any]:
        spec = _spec("Portfolio Reasoner", SYNTHESIS_SPECS)
        outcomes = self.experiment_outcomes.for_run(state.run_id)
        experiments = self.experiments.for_run(state.run_id)
        request = CrewTaskRequest(
            task_id="observed-outcome-decision",
            stage_id=StageName.OBSERVE_AND_DECIDE.value,
            crew_name="Observed Outcome Decision Crew",
            spec=spec,
            description=(
                "Use database_query and semantic_memory_search, then python_execute "
                "to check any reported rates. Recommend BUILD, ITERATE, KILL, or "
                "MORE_EVIDENCE for each candidate. Only the supplied immutable outcome "
                "records count as observed behavior. If an experiment has no outcome, "
                "say it is awaiting approval/execution and never invent a measurement. "
                "Existing research decisions:\n"
                + json.dumps(state.artifacts.get("validation_decisions", {}))
                + "\nPreregistered experiments:\n"
                + json.dumps([item.model_dump(mode="json") for item in experiments])
                + "\nObserved outcomes:\n"
                + json.dumps([item.model_dump(mode="json") for item in outcomes])
            ),
            expected_output=(
                "A typed ObservationDecisionBatch that distinguishes missing outcomes."
            ),
            output_model=ObservationDecisionBatch,
            dependency_barrier=11,
            required_tools=spec.tools,
        )
        advisory = ObservationDecisionBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        actual_outcome_ids = {item.id for item in outcomes}
        valid_candidates = set(state.eligible_candidate_ids)
        base_decisions = state.artifacts.get("validation_decisions", {})
        decisions: dict[str, Any] = {}
        advisory_by_id = {
            item.candidate_id: item
            for item in advisory.decisions
            if item.candidate_id in valid_candidates
        }
        for candidate_id in state.eligible_candidate_ids:
            item = advisory_by_id.get(candidate_id)
            used_outcomes = (
                [value for value in item.observed_outcome_ids if value in actual_outcome_ids]
                if item
                else []
            )
            base = DecisionType(
                base_decisions.get(candidate_id, {}).get(
                    "decision", DecisionType.MORE_EVIDENCE.value
                )
            )
            recommendation = item.recommendation if item else base
            if not used_outcomes and base is not DecisionType.BUILD:
                recommendation = base
            decisions[candidate_id] = {
                "recommendation": recommendation.value,
                "reason_codes": list(
                    dict.fromkeys(
                        (item.reason_codes if item else [])
                        + ([] if used_outcomes else ["NO_OBSERVED_OUTCOME"])
                    )
                ),
                "rationale": item.rationale if item else "No observed outcome exists.",
                "observed_outcome_ids": used_outcomes,
                "observed_market_evidence": bool(used_outcomes),
            }
        forecast_lessons: list[BusinessLesson] = []
        predictions_by_experiment = {item.experiment_id: item for item in self.experiment_predictions.for_run(state.run_id)}
        experiments_by_id = {item.id: item for item in experiments}
        for outcome in outcomes:
            prediction = predictions_by_experiment.get(outcome.experiment_id)
            experiment = experiments_by_id.get(outcome.experiment_id)
            if prediction is None or experiment is None:
                continue
            interpretation = outcome.interpretation.casefold()
            if any(term in interpretation for term in ("failed", "failure", "contradicted", "below threshold", "threshold not met")):
                failed_lesson = self.lessons.create(BusinessLesson(
                    category="failed_validation_experiment",
                    opportunity_id=experiment.idea_id,
                    run_id=state.run_id,
                    task_id="observe-and-decide",
                    attempted_or_assumed=experiment.hypothesis,
                    expected_result=experiment.threshold,
                    observed_result=outcome.interpretation,
                    root_cause="Measured experiment interpretation reports failure; see outcome and evidence sources.",
                    evidence_ids=outcome.evidence_source_ids,
                    recommended_behavior="Use the measured failure to revise or retire the tested assumption; do not generalize beyond its sample and conditions.",
                    applicability_conditions=[experiment.assumption_id, experiment.sample_definition],
                    confidence=0.8 if outcome.evidence_source_ids else 0.4,
                    validation_status="VALIDATED" if outcome.evidence_source_ids else "HYPOTHESIS",
                ))
                self._index(state.run_id, "LESSON", failed_lesson.id, _lesson_memory_text(failed_lesson))
            predicted = prediction.predicted_metrics.model_dump(exclude_none=True, exclude={"currency", "period_months"})
            observed = outcome.observed_metrics.model_dump(exclude_none=True, exclude={"currency", "period_months"})
            discrepancies = [
                f"{name}: predicted {predicted[name]}, observed {value} ({abs(float(value)-float(predicted[name]))/max(abs(float(predicted[name])), 1e-9):.0%} error)"
                for name, value in observed.items()
                if name in predicted and abs(float(value)-float(predicted[name])) / max(abs(float(predicted[name])), 1e-9) > 0.5
            ]
            if discrepancies:
                lesson = self.lessons.create(BusinessLesson(
                    category="forecast_discrepancy",
                    opportunity_id=experiment.idea_id,
                    run_id=state.run_id,
                    task_id="observe-and-decide",
                    attempted_or_assumed=prediction.rationale,
                    expected_result="; ".join(f"{key}={value}" for key, value in predicted.items()),
                    observed_result="; ".join(discrepancies),
                    root_cause="Forecast discrepancy recorded; root cause requires validation and is not inferred from error alone.",
                    evidence_ids=outcome.evidence_source_ids,
                    recommended_behavior="Revisit the forecast drivers and recalibrate only after identifying which assumption changed.",
                    applicability_conditions=[experiment.assumption_id, "same metric definition and period"],
                    confidence=0.8,
                    validation_status="OBSERVED",
                ))
                forecast_lessons.append(lesson)
                self._index(state.run_id, "LESSON", lesson.id, _lesson_memory_text(lesson))
        return {
            "artifacts": {
                "observed_decisions": decisions,
                "observed_outcome_count": len(outcomes),
                "forecast_lessons": [item.model_dump(mode="json") for item in forecast_lessons],
                "unexecuted_experiment_ids": [
                    item.id
                    for item in experiments
                    if not any(outcome.experiment_id == item.id for outcome in outcomes)
                ],
            }
        }

    def _produce_dossier(self, state: PipelineState) -> dict[str, Any]:
        candidate_ids = state.eligible_candidate_ids
        spec = _spec("Opportunity Synthesizer", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="dossier-synthesis",
            stage_id=StageName.PRODUCE_DOSSIER.value,
            crew_name="Diligence and Dossier Crew",
            spec=spec,
            description=(
                "First call database_query with LIST_IDEAS, LIST_ASSUMPTIONS, and "
                "LIST_EVIDENCE, then call semantic_memory_search for related prior "
                "learning. Use those tool results as the only research context. Produce "
                "one grounded business dossier narrative for every supplied candidate "
                "ID. Each description must contain at least 150 words. Include named "
                "competitors, plausible digital business models, explicit unknowns, and "
                "cheap falsifying experiments. Provide monthly price and variable cost "
                "estimates only when supportable; they will be calculated "
                "deterministically outside the model. Never call model agreement "
                "evidence. Candidate IDs:\n"
                + json.dumps(candidate_ids)
            ),
            expected_output="A typed DossierBatch with one substantial narrative per candidate.",
            output_model=DossierBatch,
            dependency_barrier=12,
            required_tools=spec.tools,
        )
        output = DossierBatch.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        narratives = {item.candidate_id: item for item in output.dossiers}
        missing = [identifier for identifier in candidate_ids if identifier not in narratives]
        if missing:
            raise ValueError(f"dossier synthesis omitted candidates: {', '.join(missing)}")
        evidence_by_id = {item.id: item for item in self.evidence.for_run(state.run_id)}
        rankings = {
            item["idea_id"]: item for item in state.artifacts.get("rankings", [])
        }
        decisions = state.artifacts.get("validation_decisions", {})
        red_findings = state.artifacts.get("red_team_findings", [])
        paths: list[str] = []
        for candidate_id in candidate_ids:
            idea = self.candidates.get(candidate_id)
            narrative = narratives[candidate_id]
            assumptions = self.assumptions.for_idea(candidate_id)
            candidate_evidence = [
                evidence_by_id[evidence_id]
                for assumption in assumptions
                for evidence_id in assumption.evidence_for_ids + assumption.evidence_against_ids
                if evidence_id in evidence_by_id
            ]
            grades = grade_commercial_evidence([item.id for item in assumptions], candidate_evidence)
            economics = calculate_economics(
                estimated_business_model_inputs(
                    narrative.monthly_price,
                    narrative.variable_cost_per_customer,
                )
            )
            readiness = assess_decision_readiness(idea, assumptions, grades, economics, policy=self.readiness_policy)
            decision_value = decisions.get(candidate_id, {}).get(
                "decision", DecisionType.MORE_EVIDENCE.value
            )
            readiness_payload = readiness.model_dump(mode="json") | {
                "pipeline_validation_decision": decision_value,
                "pipeline_validation_reason_codes": decisions.get(candidate_id, {}).get("reason_codes", []),
            }
            dossier = Dossier(
                run_id=state.run_id,
                candidate_id=candidate_id,
                title=idea.title,
                thesis=idea.one_sentence_thesis,
                description=narrative.description,
                why_now=idea.why_now,
                customer=idea.target_customer,
                buyer=idea.buyer,
                assumptions=[
                    AssumptionSummary(
                        statement=item.statement,
                        status=item.status.value,
                        evidence_for=self._evidence_references(
                            item.evidence_for_ids, evidence_by_id
                        ),
                        evidence_against=self._evidence_references(
                            item.evidence_against_ids, evidence_by_id
                        ),
                        independent_lineages=independent_lineage_count(
                            [
                                evidence_by_id[evidence_id]
                                for evidence_id in (
                                    item.evidence_for_ids + item.evidence_against_ids
                                )
                                if evidence_id in evidence_by_id
                            ]
                        ),
                    )
                    for item in assumptions
                ],
                unknowns=sorted(set(narrative.unknowns) | {reason for item in economics.scenarios.values() for reason in item.unknowns.values()}),
                competitors=narrative.competitors,
                business_model_variants=narrative.business_model_variants,
                economics={
                    "gross_margin_base": _gross_margin(
                        narrative.monthly_price,
                        narrative.variable_cost_per_customer,
                    ),
                    "currency": economics.currency,
                    "period_months": economics.period_months,
                    "assumptions": economics.assumptions.model_dump(mode="json"),
                    "scenarios": {key: value.model_dump(mode="json") for key, value in economics.scenarios.items()},
                },
                readiness=readiness_payload,
                opportunity_investment_thesis=idea.one_sentence_thesis,
                critical_assumptions=[item.model_dump(mode="json") for item in assumptions if item.criticality.value == "FATAL"],
                recommended_experiment={"description": narrative.recommended_experiments[0] if narrative.recommended_experiments else "Validate willingness to pay", "estimated_cost": {"value": None, "basis": "UNKNOWN", "reason": "No experiment budget is recorded."}, "success_criteria": "Preregister a measurable product-specific purchase-intent threshold."},
                addressable_market={"value": None, "basis": "UNKNOWN", "reason": "No sourced market sizing is recorded."},
                reachable_market={"value": None, "basis": "UNKNOWN", "reason": "No distribution reach or serviceable-market estimate is recorded."},
                willingness_to_pay_evidence=[
                    item.id for item in candidate_evidence
                    if any(a.id in item.supported_assumption_ids and a.category.value == "WTP" for a in assumptions)
                    and item.commercial_scope.value == "PRODUCT"
                    and item.commercial_classification.value in {"CUSTOMER_VALIDATION", "PURCHASE_INTENT", "OBSERVED_TRANSACTION"}
                ],
                commercial_evidence_grades=[item.model_dump(mode="json") for item in grades],
                automation_ratio=(
                    idea.autonomous_scalability.target_automation_ratio
                    if idea.autonomous_scalability
                    else None
                ),
                human_minutes_per_customer_at_10x=(
                    idea.autonomous_scalability.human_minutes_per_customer_at_10x
                    if idea.autonomous_scalability
                    else None
                ),
                red_team_findings=[
                    str(item["attack"])
                    for item in red_findings
                    if item.get("candidate_id") == candidate_id
                ],
                ranking=(
                    rankings.get(candidate_id, {"rank": 0, "stability": 0})
                    | {"portfolio_size": len(state.finalist_ids)}
                ),
                recommended_experiments=narrative.recommended_experiments,
                decision=readiness.recommendation,
                reason_codes=readiness.reason_codes,
            )
            markdown, structured = write_dossier(
                dossier,
                self.output_directory / state.run_id / "deliverables",
            )
            paths.extend((str(markdown), str(structured)))
        return {"artifacts": {"dossier_paths": paths}}

    def _finalize_run(self, state: PipelineState) -> dict[str, Any]:
        spec = _spec("Portfolio Reasoner", SYNTHESIS_SPECS)
        request = CrewTaskRequest(
            task_id="run-conclusion",
            stage_id=StageName.FINALIZE_RUN.value,
            crew_name="Portfolio Decision Crew",
            spec=spec,
            description=(
                "Use database_query and semantic_memory_search. Summarize this completed "
                "research run, its actual funnel, evidence gaps, and ranked BUILD/KILL/"
                "ITERATE/MORE_EVIDENCE recommendations. Do not describe research as "
                "observed market behavior. Pipeline state:\n"
                + state.model_dump_json()
            ),
            expected_output="A typed RunConclusion with concrete next actions.",
            output_model=RunConclusion,
            dependency_barrier=13,
            required_tools=_FINALIZATION_REQUIRED_TOOLS,
        )
        conclusion = RunConclusion.model_validate(
            self.task_runner.run_tasks(state.run_id, [request])[request.task_id]
        )
        workspace = self.workspaces.ensure(state.run_id)
        conclusion_path = workspace.deliverables / "run-conclusion.json"
        conclusion_path.write_text(conclusion.model_dump_json(indent=2), encoding="utf-8")
        overview_path = self._write_run_overview(state)
        self.runs.set_status(state.run_id, RunStatus.COMPLETED)
        return {
            "artifacts": {
                "run_conclusion_path": str(conclusion_path),
                "run_overview_path": str(overview_path),
            }
        }

    def _write_run_overview(self, state: PipelineState) -> Path:
        validated = state.artifacts.get("validated_assumptions", [])
        validated_candidates = {
            item.get("idea_id")
            for item in validated
            if item.get("status")
            in {"RESEARCH_SUPPORTED", "EXPERIMENT_SUPPORTED"}
        }
        overview = {
            "artifact_type": "run_overview",
            "run_id": state.run_id,
            "execution_mode": "live_crewai_ollama",
            "funnel": {
                "observed_signals": len(state.signal_ids),
                "raw_ideas": int(state.artifacts.get("raw_idea_count", 0)),
                "evidence_qualified": len(state.eligible_candidate_ids),
                "assumption_validated": len(validated_candidates),
                "red_team_survivors": len(state.finalist_ids),
                "experiment_candidates": len(
                    state.artifacts.get("experiment_candidate_ids", [])
                ),
                "observed_market_evidence": int(
                    state.artifacts.get("observed_outcome_count", 0)
                ),
                "ranked_recommendations": len(
                    state.artifacts.get("rankings", [])
                ),
            },
            "evidence_items": int(state.artifacts.get("evidence_item_count", 0)),
            "rejected_ungrounded_claims": len(
                state.artifacts.get("rejected_evidence_claims", [])
            ),
                "duplicate_candidates": int(state.artifacts.get("duplicate_count", 0)),
        }
        path = self.workspaces.ensure(state.run_id).deliverables / "run-overview.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(overview, indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return path

    def _normalized_candidate_context(self, candidate_ids: list[str]) -> list[dict[str, Any]]:
        context = []
        for candidate_id in candidate_ids:
            assumptions = self.assumptions.for_idea(candidate_id)
            evidence_by_assumption = {}
            candidate_evidence = []
            for assumption in assumptions:
                evidence = [
                    self.evidence.get(identifier)
                    for identifier in assumption.evidence_for_ids + assumption.evidence_against_ids
                ]
                candidate_evidence.extend(evidence)
                evidence_by_assumption[assumption.id] = [item.model_dump(mode="json") for item in evidence]
            grades = grade_commercial_evidence([item.id for item in assumptions], candidate_evidence)
            economics = calculate_economics(estimated_business_model_inputs(None, None))
            readiness = assess_decision_readiness(
                self.candidates.get(candidate_id), assumptions, grades, economics,
                policy=self.readiness_policy,
            )
            context.append({
                "idea": self.candidates.get(candidate_id).model_dump(mode="json"),
                "assumptions": [item.model_dump(mode="json") for item in assumptions],
                "evidence_by_assumption": evidence_by_assumption,
                "commercial_evidence_grades": [item.model_dump(mode="json") for item in grades],
                "decision_readiness": readiness.model_dump(mode="json"),
            })
        return context

    def _source_urls_for_task(self, task_id: str) -> set[str]:
        return set(self._sources_for_task(task_id))

    def _sources_for_task(
        self, task_id: str
    ) -> dict[str, tuple[SourceProvenance, ToolName]]:
        values: dict[str, tuple[SourceProvenance, ToolName]] = {}
        for record in self._audit_records():
            if record.envelope.task_id != task_id or record.result is None:
                continue
            for source in record.result.sources:
                if source.source_url:
                    url = str(source.source_url)
                    values[url] = (source, record.envelope.tool)
                    values[canonicalize_url(url)] = (source, record.envelope.tool)
        return values

    def _audit_records(self) -> list[ToolAuditRecord]:
        records = getattr(self.gateway.audit, "records", None)
        if not isinstance(records, list):
            raise TypeError("live gateway audit sink must retain in-process records")
        return [ToolAuditRecord.model_validate(item) for item in records]

    def _index(
        self,
        run_id: str,
        entity_type: str,
        entity_id: str,
        text: str,
    ) -> None:
        self.memory.index(
            run_id=run_id,
            entity_type=entity_type,
            entity_id=entity_id,
            text=text,
        )

    @staticmethod
    def _evidence_from_claim(
        run_id: str, claim: Any, source: SourceProvenance
    ) -> EvidenceItem:
        source_url = str(source.source_url or claim.source_url)
        source_type = source.source_type or "external_source"
        tier = (
            EvidenceTier.PRIMARY
            if source_type
            in {
                "official_regulation",
                "web_page",
                "rendered_web_page",
                "document",
                "github_repository",
            }
            else EvidenceTier.SECONDARY
        )
        content_hash = source.content_hash or sha256(
            f"{source_url}\n{claim.extracted_fact}".encode()
        ).hexdigest()
        return EvidenceItem(
            run_id=run_id,
            source_identifier=source.source_identifier,
            source_url=source_url if source_url.startswith(("http://", "https://")) else None,
            source_type=source_type,
            publisher=claim.publisher or _publisher_from_url(source_url),
            extracted_fact=claim.extracted_fact,
            excerpt_pointer=claim.excerpt_pointer,
            tier=tier,
            evidence_type=EvidenceType.OBSERVED,
            direction=claim.direction,
            reliability_score=min(claim.reliability_score, 0.95 if tier is EvidenceTier.PRIMARY else 0.75),
            freshness_score=claim.freshness_score,
            lineage_group_id=_lineage_id(source_url, source.source_identifier),
            content_hash=content_hash,
            commercial_classification=claim.commercial_classification,
            commercial_scope=claim.commercial_scope,
            supported_assumption_ids=[claim.assumption_id],
        )

    @staticmethod
    def _red_team_evidence(
        run_id: str, attack: str, source: SourceProvenance
    ) -> EvidenceItem:
        source_url = str(source.source_url or source.source_identifier)
        return EvidenceItem(
            run_id=run_id,
            source_identifier=source.source_identifier,
            source_url=source_url if source_url.startswith(("http://", "https://")) else None,
            source_type=source.source_type or "external_source",
            publisher=_publisher_from_url(source_url),
            extracted_fact=attack,
            tier=EvidenceTier.SECONDARY,
            evidence_type=EvidenceType.OBSERVED,
            direction=EvidenceDirection.CONTRADICTS,
            reliability_score=0.65,
            freshness_score=1,
            lineage_group_id=_lineage_id(source_url, source.source_identifier),
            content_hash=source.content_hash
            or sha256(f"{source_url}\n{attack}".encode()).hexdigest(),
        )

    @staticmethod
    def _evidence_references(
        identifiers: list[str], evidence_by_id: dict[str, EvidenceItem]
    ) -> list[EvidenceReference]:
        values = []
        for identifier in identifiers:
            item = evidence_by_id.get(identifier)
            if item is None:
                continue
            publisher = item.publisher or _publisher_from_url(str(item.source_url or ""))
            values.append(
                EvidenceReference(
                    title=f"{publisher} — {item.source_type.replace('_', ' ').title()}",
                    summary=item.extracted_fact,
                    url=str(item.source_url) if item.source_url else None,
                    publisher=item.publisher,
                    tier=item.tier.value,
                )
            )
        return values


def _spec(role: str, values: tuple[ActorSpec, ...]) -> ActorSpec:
    return next(item for item in values if item.role == role)


def _slug(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _normalize_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> set[str]:
    synonyms = {
        "automated": "automate", "automation": "automate", "automating": "automate",
        "regulatory": "compliance", "regulation": "compliance", "regulations": "compliance",
        "checks": "review", "check": "review", "inspections": "review",
        "recurring": "repetitive", "repeated": "repetitive", "manual": "repetitive",
        "departments": "team", "department": "team", "teams": "team",
        "webapp": "web", "application": "web", "applications": "web",
        "streamlines": "automate", "streamline": "automate", "replaces": "automate",
        "software": "product", "platform": "product", "tool": "product",
    }
    return {synonyms.get(token, token) for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2}


def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _compare_idea_dimensions(draft: Any, prior: BusinessIdea) -> dict[str, Any]:
    problem = _similarity(draft.problem_title + " " + draft.one_sentence_thesis,
                          prior.title + " " + prior.one_sentence_thesis)
    customer = _similarity(draft.target_customer + " " + (draft.buyer or ""),
                           prior.target_customer + " " + (prior.buyer or ""))
    value = _similarity(draft.value_proposition, prior.value_proposition)
    solution = _similarity(draft.product_form + " " + draft.delivery_model,
                           prior.product_form + " " + prior.delivery_model)
    total = 0.30 * problem + 0.20 * customer + 0.25 * value + 0.25 * solution
    duplicate = problem >= 0.35 and customer >= 0.30 and solution >= 0.30 and total >= 0.35
    related = problem >= 0.25 and not duplicate
    return {
        "problem_similarity": round(problem, 4),
        "customer_similarity": round(customer, 4),
        "value_similarity": round(value, 4),
        "solution_similarity": round(solution, 4),
        "similarity": round(total, 4),
        "duplicate": duplicate,
        "related": related,
    }


def _explicit_reconsideration(novelty_lineage: str) -> bool:
    value = novelty_lineage.casefold()
    return any(term in value for term in (
        "reconsider", "new evidence", "materially changed", "changed circumstance",
        "new condition", "since rejection",
    ))


def _may_reconsider(prior: BusinessIdea, draft: Any, new_source_ids: list[str]) -> bool:
    return bool(
        prior.lifecycle_state in {CandidateState.KILL, CandidateState.ITERATE, CandidateState.MORE_EVIDENCE}
        and _explicit_reconsideration(draft.novelty_lineage)
        and set(new_source_ids) - set(prior.source_urls)
    )


def _canonical_opportunity_identity(draft: Any) -> str:
    dimensions = (
        draft.problem_title, draft.target_customer, draft.buyer or "",
        draft.value_proposition, draft.product_form, draft.delivery_model,
    )
    return " | ".join(_normalize_key(item) for item in dimensions)


def _lesson_memory_text(lesson: BusinessLesson) -> str:
    return (
        f"{lesson.category} [{lesson.validation_status}, confidence={lesson.confidence:.2f}]. "
        f"Attempted: {lesson.attempted_or_assumed}. Expected: {lesson.expected_result}. "
        f"Observed: {lesson.observed_result}. Cause: {lesson.root_cause}. "
        f"Evidence IDs: {', '.join(lesson.evidence_ids) or 'none'}. "
        f"Recommended: {lesson.recommended_behavior}. "
        f"Conditions: {'; '.join(lesson.applicability_conditions)}. "
        f"Opportunity={lesson.opportunity_id}; run={lesson.run_id}; task={lesson.task_id}."
    )


def _publisher_from_url(url: str) -> str:
    host = urlparse(url).hostname or "Source"
    return host.removeprefix("www.")


def _lineage_id(url: str, source_identifier: str) -> str:
    host = urlparse(url).hostname or source_identifier
    return sha256(host.casefold().encode()).hexdigest()[:32]


def _gross_margin(price: float | None, variable_cost: float | None) -> float | str:
    if price is None or variable_cost is None:
        return "UNKNOWN"
    return round((price - variable_cost) / price, 4)


def _spec_model_name(task_runner: StageTaskRunner, role: ModelRole) -> str:
    catalog = getattr(task_runner, "catalog", None)
    if catalog is None:
        return role.value
    return catalog.llm.router.resolve_role(role).model_id
