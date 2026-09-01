from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from dbie.crews.outputs import (
    BusinessModelBatch,
    BusinessModelDraft,
    DiscoveryBatch,
    DossierBatch,
    DossierNarrative,
    EligibilityAssessment,
    EligibilityBatch,
    EvidenceBatch,
    EvidenceClaim,
    ExperimentBatch,
    IdeaBatch,
    IdeaDraft,
    ObservationDecisionBatch,
    ObservationDecisionDraft,
    PairwiseBatch,
    RedTeamBatch,
    RedTeamDraft,
    RunConclusion,
    RunPlan,
    SignalDraft,
    ValidationBatch,
)
from dbie.domain.enums import EvidenceDirection
from dbie.domain.enums import DecisionType
from dbie.domain.models import AutonomousScalability, DigitalEligibility
from dbie.flows.state import STAGE_ORDER, PipelineState, StageName
from dbie.persistence.db import Database
from dbie.persistence.repositories import AssumptionRepository, CandidateRepository
from dbie.persistence.vector import (
    DeterministicEmbeddingService,
    SemanticMemoryRepository,
)
from dbie.services.live_mvp import (
    _EVIDENCE_REQUIRED_TOOLS,
    _FINALIZATION_REQUIRED_TOOLS,
    LiveMVPConfig,
    LiveMVPExecutor,
)
from dbie.tools.adapters.registry import AdapterRegistry
from dbie.tools.audit import InMemoryAuditSink, ToolAuditRecord
from dbie.tools.contracts import (
    SourceProvenance,
    ToolCallEnvelope,
    ToolName,
    ToolResult,
)
from dbie.tools.gateway import ToolGateway
from dbie.tools.permissions import ToolPermissionPolicy


def test_evidence_contract_requires_a_fetched_source_not_every_specialist_tool() -> None:
    assert _EVIDENCE_REQUIRED_TOOLS == (
        ToolName.DATABASE_QUERY,
        ToolName.WEB_SEARCH,
        ToolName.FETCH_PAGE,
    )
    assert ToolName.SEARCH_GITHUB not in _EVIDENCE_REQUIRED_TOOLS


def test_finalization_contract_requires_context_tools_but_not_python() -> None:
    assert _FINALIZATION_REQUIRED_TOOLS == (
        ToolName.DATABASE_QUERY,
        ToolName.SEMANTIC_MEMORY_SEARCH,
    )
    assert ToolName.PYTHON_EXECUTE not in _FINALIZATION_REQUIRED_TOOLS


class ScriptedStageRunner:
    def __init__(self, database: Database, audit: InMemoryAuditSink) -> None:
        self.candidates = CandidateRepository(database)
        self.assumptions = AssumptionRepository(database)
        self.audit = audit

    def run_tasks(self, run_id: str, requests: list[Any]) -> dict[str, Any]:
        return {request.task_id: self._output(run_id, request) for request in requests}

    def _output(self, run_id: str, request: Any) -> Any:
        output_model = request.output_model
        if output_model is RunPlan:
            return RunPlan(
                mandate_interpretation="Research a bounded fully digital opportunity space.",
                research_questions=["Where is repeated measurable pain?"],
                explicit_exclusions=["Physical fulfilment"],
            )
        if output_model is DiscoveryBatch:
            url = f"https://{request.task_id}.test/source"
            self._source(run_id, request, url)
            return DiscoveryBatch(
                signals=[
                    SignalDraft(
                        title=f"Signal {request.task_id}",
                        description="A repeated costly digital workflow has traceable demand.",
                        affected_customer="Compliance teams",
                        source_urls=[url],
                    )
                ]
            )
        if output_model is IdeaBatch:
            return IdeaBatch(
                ideas=[
                    IdeaDraft(
                        problem_title="Signal discovery-0-trendscout",
                        title=f"Idea {request.task_id}",
                        one_sentence_thesis=f"Automate the verified workflow via {request.task_id}.",
                        target_customer="Compliance teams",
                        buyer="Chief compliance officer",
                        user="Compliance analyst",
                        value_proposition="Reduce costly repetitive evidence review.",
                        product_form="SaaS",
                        delivery_model="Self-service web application",
                        why_now="Official data is machine-readable.",
                        novelty_lineage="A distinct workflow automation mechanism.",
                        signal_titles=["Signal discovery-0-trendscout"],
                        digital_eligibility=DigitalEligibility(
                            **{name: True for name in DigitalEligibility.model_fields}
                        ),
                        autonomous_scalability=AutonomousScalability(
                            target_automation_ratio=0.95,
                            human_minutes_per_customer=20,
                            human_minutes_per_customer_at_10x=2,
                            human_only_tasks=["exception approval"],
                            credible_transition_plan=True,
                        ),
                    )
                ]
            )
        if output_model is EligibilityBatch:
            return EligibilityBatch(
                assessments=[
                    EligibilityAssessment(
                        candidate_id=item.id,
                        recommended_eligible=True,
                    )
                    for item in self.candidates.for_run(run_id)
                ]
            )
        if output_model.__name__ == "AssumptionBatch":
            return output_model(assumptions=[])
        if output_model is EvidenceBatch:
            claims = []
            for assumption in self.assumptions.for_run(run_id):
                for source_index in (1, 2):
                    url = (
                        f"https://source-{source_index}.test/"
                        f"{request.task_id}/{assumption.id}"
                    )
                    self._source(run_id, request, url)
                    claims.append(
                        EvidenceClaim(
                            candidate_id=assumption.idea_id,
                            assumption_id=assumption.id,
                            source_url=url,
                            source_title=f"Source {source_index}",
                            publisher=f"Publisher {source_index}",
                            extracted_fact="The source directly supports the bounded assumption.",
                            direction=EvidenceDirection.SUPPORTS,
                            reliability_score=0.9,
                            freshness_score=1,
                        )
                    )
            return EvidenceBatch(claims=claims)
        if output_model is ValidationBatch:
            return ValidationBatch()
        if output_model is BusinessModelBatch:
            return BusinessModelBatch(
                models=[
                    BusinessModelDraft(
                        candidate_id=item.id,
                        name="Self-service subscription",
                        buyer=item.buyer or "Compliance leader",
                        pricing_model="Monthly subscription",
                        acquisition_channel="Digital content and partner referrals",
                        delivery_mechanism="Multi-tenant SaaS",
                        key_cost_drivers=["Inference and document processing"],
                        distinct_assumptions=["Buyer can approve remotely"],
                    )
                    for item in self.candidates.for_run(run_id)
                ]
            )
        if output_model is RedTeamBatch:
            return RedTeamBatch(
                findings=[
                    RedTeamDraft(
                        candidate_id=item.id,
                        attack="A serious substitute risk was tested and resolved by evidence.",
                        severity=3,
                        unresolved=False,
                    )
                    for item in self.candidates.for_run(run_id)
                    if item.lifecycle_state.value == "VALIDATING"
                ]
            )
        if output_model is PairwiseBatch:
            return PairwiseBatch(
                portfolio_observations=["The sole survivor passed every hard gate."]
            )
        if output_model is ExperimentBatch:
            return ExperimentBatch()
        if output_model is ObservationDecisionBatch:
            return ObservationDecisionBatch(
                decisions=[
                    ObservationDecisionDraft(
                        candidate_id=item.id,
                        recommendation=DecisionType.BUILD,
                        reason_codes=["HARD_GATES_PASSED"],
                        rationale="Research gates passed and no experiment result was claimed.",
                    )
                    for item in self.candidates.for_run(run_id)
                ]
            )
        if output_model is DossierBatch:
            description = " ".join(
                [
                    "This opportunity turns a costly repeated digital compliance workflow into traceable software automation for a clearly identified buyer."
                ]
                * 11
            )
            return DossierBatch(
                dossiers=[
                    DossierNarrative(
                        candidate_id=item.id,
                        description=description,
                        competitors=["Manual review"],
                        business_model_variants=["Subscription"],
                        monthly_price=100,
                        variable_cost_per_customer=20,
                        recommended_experiments=["Preregistered price-choice test"],
                    )
                    for item in self.candidates.for_run(run_id)
                    if item.lifecycle_state.value
                    in {"FINALIST", "MORE_EVIDENCE", "KILL"}
                ]
            )
        if output_model is RunConclusion:
            return RunConclusion(
                summary="The live-shaped unit run completed every MVP stage with traceable evidence.",
                recommended_actions=["Run a preregistered demand experiment"],
            )
        raise AssertionError(output_model)

    def _source(self, run_id: str, request: Any, url: str) -> None:
        self.audit.write(
            ToolAuditRecord(
                envelope=ToolCallEnvelope(
                    run_id=run_id,
                    stage_id=request.stage_id,
                    task_id=request.task_id,
                    actor_id="ScriptedActor",
                    tool=ToolName.FETCH_PAGE,
                    arguments={"url": url},
                    purpose="unit test source",
                ),
                result=ToolResult(
                    tool=ToolName.FETCH_PAGE,
                    sources=[
                        SourceProvenance(
                            source_identifier=url,
                            source_url=url,
                            source_type="web_page",
                            content_hash=sha256(url.encode()).hexdigest(),
                        )
                    ],
                ),
                allowed=True,
            )
        )


@pytest.fixture(scope="module")
def live_stage_results(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("live-mvp")
    database = Database(f"sqlite:///{root / 'db.sqlite3'}")
    database.initialize()
    audit = InMemoryAuditSink()
    gateway = ToolGateway(
        registry=AdapterRegistry(),
        routes={},
        permissions=ToolPermissionPolicy({}),
        audit=audit,
    )
    memory = SemanticMemoryRepository(database, DeterministicEmbeddingService())
    executor = LiveMVPExecutor(
        database,
        root / "runs",
        gateway,
        ScriptedStageRunner(database, audit),
        memory,
        config=LiveMVPConfig(
            target_signals=1,
            target_raw_ideas=1,
            max_validation_candidates=1,
        ),
        configuration_hash="unit-test",
    )
    state = PipelineState(run_id="live-unit-run", mandate="Find compliance SaaS")
    snapshots = {}
    for stage in STAGE_ORDER:
        changes = executor.execute(stage, state)
        for field, value in changes.items():
            if field == "artifacts":
                state.artifacts.update(value)
            else:
                setattr(state, field, value)
        state.completed_stages.append(stage)
        snapshots[stage] = state.model_copy(deep=True)
    return snapshots, root


def test_phase_initialize_uses_live_execution_contract(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    assert snapshots[StageName.INITIALIZE_RUN].artifacts["execution_mode"] == (
        "live_crewai_ollama"
    )
    assert snapshots[StageName.INITIALIZE_RUN].artifacts["run_plan"]


def test_phase_discovery_retains_only_grounded_signals(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.DISCOVER_SIGNALS]
    assert len(state.signal_ids) == 1
    assert state.artifacts["signals"][0]["source_ids"]


def test_phase_ideation_generates_canonical_candidates(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.GENERATE_IDEAS]
    assert len(state.candidate_ids) == 1
    assert state.artifacts["raw_idea_count"] >= 1


def test_phase_eligibility_keeps_deterministic_gate_authoritative(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.ELIGIBILITY_GATE]
    assert len(state.eligible_candidate_ids) == 1
    result = next(iter(state.artifacts["eligibility_results"].values()))
    assert result["eligible"] is True
    assert result["agent_assessment"] is not None


def test_live_eligibility_rejects_an_empty_surviving_portfolio(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'empty.sqlite3'}")
    database.initialize()
    audit = InMemoryAuditSink()
    gateway = ToolGateway(
        registry=AdapterRegistry(),
        routes={},
        permissions=ToolPermissionPolicy({}),
        audit=audit,
    )

    class IneligibleStageRunner(ScriptedStageRunner):
        def _output(self, run_id: str, request: Any) -> Any:
            output = super()._output(run_id, request)
            if isinstance(output, IdeaBatch):
                output.ideas[0].digital_eligibility.payments = False
            return output

    executor = LiveMVPExecutor(
        database,
        tmp_path / "runs",
        gateway,
        IneligibleStageRunner(database, audit),
        SemanticMemoryRepository(database, DeterministicEmbeddingService()),
        config=LiveMVPConfig(
            target_signals=1,
            target_raw_ideas=1,
            max_validation_candidates=1,
        ),
    )
    state = PipelineState(run_id="empty-live-run", mandate="Find compliance SaaS")
    for stage in (
        StageName.INITIALIZE_RUN,
        StageName.DISCOVER_SIGNALS,
        StageName.GENERATE_IDEAS,
    ):
        changes = executor.execute(stage, state)
        for field, value in changes.items():
            if field == "artifacts":
                state.artifacts.update(value)
            else:
                setattr(state, field, value)

    with pytest.raises(ValueError, match="no candidates"):
        executor.execute(StageName.ELIGIBILITY_GATE, state)


def test_phase_assumptions_creates_complete_atomic_map(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    assert (
        len(snapshots[StageName.DECOMPOSE_ASSUMPTIONS].artifacts["assumptions"]) == 12
    )


def test_phase_evidence_rejects_ungrounded_and_persists_grounded_links(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.COLLECT_EVIDENCE]
    assert state.artifacts["evidence_item_count"] >= 24
    assert not state.artifacts["rejected_evidence_claims"]


def test_phase_validation_uses_independent_lineages(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    validated = snapshots[StageName.VALIDATE_ASSUMPTIONS].artifacts[
        "validated_assumptions"
    ]
    assert len(validated) == 12
    assert {item["status"] for item in validated} == {"RESEARCH_SUPPORTED"}


def test_phase_business_model_preserves_distinct_commercial_model(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    models = snapshots[StageName.MODEL_BUSINESS].artifacts["business_models"]
    assert len(models) == 1
    assert models[0]["pricing_model"] == "Monthly subscription"


def test_phase_red_team_is_mandatory_before_finalist(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.RED_TEAM]
    assert state.artifacts["red_team_findings"]
    assert len(state.finalist_ids) == 1


def test_phase_ranking_records_readable_portfolio_position(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    ranking = snapshots[StageName.RANK_PORTFOLIO].artifacts["rankings"][0]
    assert ranking["rank"] == 1
    assert ranking["stability"] == 1


def test_empty_finalist_portfolio_skips_a_meaningless_judge_call(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'empty-ranking.sqlite3'}")
    database.initialize()
    audit = InMemoryAuditSink()
    gateway = ToolGateway(
        registry=AdapterRegistry(),
        routes={},
        permissions=ToolPermissionPolicy({}),
        audit=audit,
    )

    class UnexpectedRunner:
        def run_tasks(self, run_id: str, requests: list[Any]) -> dict[str, Any]:
            raise AssertionError("an empty portfolio must not invoke a judge")

    executor = LiveMVPExecutor(
        database,
        tmp_path / "runs",
        gateway,
        UnexpectedRunner(),
        SemanticMemoryRepository(database, DeterministicEmbeddingService()),
    )
    result = executor.execute(
        StageName.RANK_PORTFOLIO,
        PipelineState(run_id="empty-ranking", mandate="test"),
    )

    assert result["artifacts"]["matches"] == []
    assert result["artifacts"]["rankings"] == []
    assert "No candidates" in result["artifacts"]["portfolio_observations"][0]


def test_phase_experiment_design_records_safe_preregistration_boundary(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    artifacts = snapshots[StageName.DESIGN_EXPERIMENTS].artifacts
    assert artifacts["experiments"] == []
    assert artifacts["experiment_predictions"] == []


def test_phase_observe_and_decide_never_invents_market_results(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    artifacts = snapshots[StageName.OBSERVE_AND_DECIDE].artifacts
    assert artifacts["observed_outcome_count"] == 0
    decision = next(iter(artifacts["observed_decisions"].values()))
    assert decision["observed_market_evidence"] is False
    assert "NO_OBSERVED_OUTCOME" in decision["reason_codes"]


def test_phase_dossier_contains_description_and_real_evidence_urls(
    live_stage_results,
) -> None:
    snapshots, _ = live_stage_results
    paths = snapshots[StageName.PRODUCE_DOSSIER].artifacts["dossier_paths"]
    structured_path = Path(next(path for path in paths if path.endswith(".json")))
    content = structured_path.read_text(encoding="utf-8")
    assert "https://source-1.test" in content
    assert len(content.split()) > 100


def test_phase_finalize_writes_actual_funnel_and_conclusion(live_stage_results) -> None:
    snapshots, _ = live_stage_results
    state = snapshots[StageName.FINALIZE_RUN]
    assert Path(state.artifacts["run_conclusion_path"]).exists()
    assert Path(state.artifacts["run_overview_path"]).exists()
