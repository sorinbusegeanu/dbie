"""Offline reproducible full-pipeline fixture used for acceptance and demos."""

from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Any

from dbie.domain.enums import (
    CandidateState,
    DecisionType,
    EvidenceDirection,
    EvidenceTier,
    EvidenceType,
    RunStatus,
)
from dbie.domain.commercial import (
    calculate_economics,
    estimated_business_model_inputs,
    grade_commercial_evidence,
)
from dbie.domain.decisions import ReadinessPolicy, assess_decision_readiness
from dbie.domain.models import (
    AutonomousScalability,
    BusinessIdea,
    DigitalEligibility,
    EvidenceItem,
    PairwiseMatch,
    Run,
)
from dbie.flows.state import PipelineState, StageName
from dbie.persistence.db import Database
from dbie.persistence.repositories import (
    AssumptionRepository,
    CandidateRepository,
    EvidenceRepository,
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
from dbie.services.tournament import rank_matches
from dbie.services.validation import RedTeamFinding, validation_decision


class FixtureMVPExecutor:
    """Exercises every deterministic MVP stage without network/model calls."""

    def __init__(self, database: Database, output_directory: Path, readiness_policy: ReadinessPolicy | None = None) -> None:
        self.database = database
        self.output_directory = output_directory
        self.readiness_policy = readiness_policy or ReadinessPolicy()
        self.runs = RunRepository(database)
        self.candidates = CandidateRepository(database)
        self.assumptions = AssumptionRepository(database)
        self.evidence = EvidenceRepository(database)
        self.matches = PairwiseMatchRepository(database)
        self.workspaces = RunWorkspaceManager(output_directory)

    def execute(self, stage: StageName, state: PipelineState) -> dict[str, Any]:
        self.workspaces.append_activity(state.run_id, f"stage {stage.value}: started")
        handler = getattr(self, f"_{stage.value}")
        result = handler(state)
        self._record_visible_stage_output(stage, state, result)
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
                configuration_hash=sha256(b"fixture-mvp-v1").hexdigest(),
            )
        )
        self.runs.set_status(state.run_id, RunStatus.RUNNING)
        return {"artifacts": {"fixture_version": "mvp-v1"}}

    def _discover_signals(self, state: PipelineState) -> dict[str, Any]:
        signals = ["machine-readable regulation", "manual evidence review"]
        return {
            "signal_ids": ["signal-regulation", "signal-review"],
            "artifacts": {"signals": signals},
        }

    def _generate_ideas(self, state: PipelineState) -> dict[str, Any]:
        ideas = [
            self._idea(state, "Regulatory Evidence Copilot", "evidence review"),
            self._idea(state, "Control Mapping API", "control mapping"),
        ]
        for idea in ideas:
            self.candidates.create(idea)
        return {
            "candidate_ids": [item.id for item in ideas],
            "artifacts": {
                "raw_idea_count": 50,
                "deduplicated_idea_count": 2,
                "idea_records": [item.model_dump(mode="json") for item in ideas],
            },
        }

    def _eligibility_gate(self, state: PipelineState) -> dict[str, Any]:
        service = CandidateService(self.candidates)
        eligible = [
            identifier
            for identifier in state.candidate_ids
            if service.apply_eligibility(identifier).eligible
        ]
        return {"eligible_candidate_ids": eligible}

    def _decompose_assumptions(self, state: PipelineState) -> dict[str, Any]:
        records = []
        for identifier in state.eligible_candidate_ids:
            idea = self.candidates.get(identifier)
            for assumption in decompose_idea(idea):
                self.assumptions.create(assumption)
                records.append(assumption.model_dump(mode="json"))
            self.candidates.set_state(identifier, CandidateState.VALIDATING)
        return {"artifacts": {"assumptions": records}}

    def _collect_evidence(self, state: PipelineState) -> dict[str, Any]:
        links: dict[str, list[dict[str, Any]]] = {}
        for candidate_id in state.eligible_candidate_ids:
            for assumption in self.assumptions.for_idea(candidate_id):
                items = [
                    self._evidence(state.run_id, assumption.id, index)
                    for index in (1, 2)
                ]
                persisted = [self.evidence.create(item) for item in items]
                links[assumption.id] = [
                    item.model_dump(mode="json") for item in persisted
                ]
        return {"artifacts": {"evidence_by_assumption": links}}

    def _validate_assumptions(self, state: PipelineState) -> dict[str, Any]:
        validated = []
        raw = state.artifacts["evidence_by_assumption"]
        for candidate_id in state.eligible_candidate_ids:
            for assumption in self.assumptions.for_idea(candidate_id):
                items = [
                    EvidenceItem.model_validate(item) for item in raw[assumption.id]
                ]
                result = validate_assumption(assumption, items)
                self.assumptions.save(result)
                validated.append(result.model_dump(mode="json"))
        return {"artifacts": {"validated_assumptions": validated}}

    def _model_business(self, state: PipelineState) -> dict[str, Any]:
        return {
            "artifacts": {
                "business_models": [
                    {
                        "candidate_id": identifier,
                        "name": "Self-service subscription",
                        "buyer": self.candidates.get(identifier).buyer,
                        "pricing_model": "Monthly subscription",
                        "acquisition_channel": "Digital content and partnerships",
                        "delivery_mechanism": "Multi-tenant SaaS and API",
                        "key_cost_drivers": ["Document processing"],
                        "distinct_assumptions": ["Remote buyer approval"],
                    }
                    for identifier in state.eligible_candidate_ids
                ]
            }
        }

    def _red_team(self, state: PipelineState) -> dict[str, Any]:
        findings = [
            RedTeamFinding(
                candidate_id=identifier,
                actor="Market Skeptic",
                attack="Fixture challenge was resolved by independent evidence.",
                severity=3,
                unresolved=False,
            )
            for identifier in state.eligible_candidate_ids
        ]
        finalists = []
        decisions = {}
        for identifier in state.eligible_candidate_ids:
            self.candidates.set_state(identifier, CandidateState.RED_TEAM)
            decision = validation_decision(
                self.assumptions.for_idea(identifier),
                [item for item in findings if item.candidate_id == identifier],
                heterogeneous_review=True,
            )
            idea = self.candidates.get(identifier)
            assumptions = self.assumptions.for_idea(identifier)
            evidence = [
                item for assumption in assumptions
                for evidence_id in assumption.evidence_for_ids
                if (item := self.evidence.get(evidence_id)) is not None
            ]
            grades = grade_commercial_evidence([a.id for a in assumptions], evidence)
            economics = calculate_economics(estimated_business_model_inputs(49.0, 8.0))
            readiness = assess_decision_readiness(
                idea, assumptions, grades, economics, policy=self.readiness_policy
            )
            if readiness.recommendation is DecisionType.KILL:
                decision = decision.model_copy(update={
                    "decision": DecisionType.KILL,
                    "reason_codes": readiness.reason_codes,
                })
            decisions[identifier] = decision.model_dump(mode="json")
            decisions[identifier]["readiness_assessment"] = readiness.model_dump(mode="json")
            decisions[identifier]["readiness_assessment"]["pipeline_validation_decision"] = decision.decision.value
            decisions[identifier]["readiness_assessment"]["pipeline_validation_reason_codes"] = decision.reason_codes
            decisions[identifier]["commercial_evidence_grades"] = [item.model_dump(mode="json") for item in grades]
            if decision.decision is DecisionType.BUILD:
                CandidateService(self.candidates).transition(
                    identifier,
                    CandidateState.FINALIST,
                    self.assumptions.for_idea(identifier),
                )
                finalists.append(identifier)
        return {
            "finalist_ids": finalists,
            "artifacts": {
                "red_team_findings": [item.model_dump() for item in findings],
                "validation_decisions": decisions,
            },
        }

    def _rank_portfolio(self, state: PipelineState) -> dict[str, Any]:
        matches = []
        if len(state.finalist_ids) >= 2:
            match = PairwiseMatch(
                run_id=state.run_id,
                left_idea_id=state.finalist_ids[0],
                right_idea_id=state.finalist_ids[1],
                winner_idea_id=state.finalist_ids[0],
                judge_model="fixture-independent-judge",
                rationale="Deterministic acceptance fixture",
            )
            self.matches.create(match)
            matches.append(match)
        rankings = rank_matches(matches)
        return {
            "artifacts": {
                "matches": [item.model_dump(mode="json") for item in matches],
                "rankings": [item.model_dump() for item in rankings],
            }
        }

    def _design_experiments(self, state: PipelineState) -> dict[str, Any]:
        return {
            "artifacts": {
                "experiment_candidate_ids": [],
                "experiments": [],
                "experiment_predictions": [],
            }
        }

    def _observe_and_decide(self, state: PipelineState) -> dict[str, Any]:
        return {
            "artifacts": {
                "observed_decisions": {
                    identifier: {
                        "recommendation": DecisionType.BUILD.value,
                        "reason_codes": ["HARD_GATES_PASSED", "NO_OBSERVED_OUTCOME"],
                        "rationale": "Research gates passed; no market outcome was claimed.",
                        "observed_outcome_ids": [],
                        "observed_market_evidence": False,
                    }
                    for identifier in state.finalist_ids
                },
                "observed_outcome_count": 0,
                "unexecuted_experiment_ids": [],
            }
        }

    def _produce_dossier(self, state: PipelineState) -> dict[str, Any]:
        ranking_by_id = {
            item["idea_id"]: item for item in state.artifacts.get("rankings", [])
        }
        paths = []
        evidence_by_id = {
            item["id"]: EvidenceItem.model_validate(item)
            for items in state.artifacts.get("evidence_by_assumption", {}).values()
            for item in items
        }
        for identifier in state.finalist_ids:
            idea = self.candidates.get(identifier)
            assumptions = self.assumptions.for_idea(identifier)
            candidate_evidence = [
                item for assumption in assumptions
                for item in [evidence_by_id[eid] for eid in assumption.evidence_for_ids if eid in evidence_by_id]
            ]
            grades = grade_commercial_evidence([item.id for item in assumptions], candidate_evidence)
            economics = calculate_economics(estimated_business_model_inputs(49.0, 8.0))
            readiness = assess_decision_readiness(idea, assumptions, grades, economics, policy=self.readiness_policy)
            dossier = Dossier(
                run_id=state.run_id,
                candidate_id=identifier,
                title=idea.title,
                thesis=idea.one_sentence_thesis,
                description=self._opportunity_description(idea),
                why_now=idea.why_now,
                customer=idea.target_customer,
                buyer=idea.buyer,
                assumptions=[
                    AssumptionSummary(
                        statement=item.statement,
                        status=item.status.value,
                        evidence_for=self._named_evidence(
                            item.evidence_for_ids, evidence_by_id
                        ),
                        evidence_against=self._named_evidence(
                            item.evidence_against_ids, evidence_by_id
                        ),
                        independent_lineages=2,
                    )
                    for item in assumptions
                ],
                unknowns=sorted({reason for item in economics.scenarios.values() for reason in item.unknowns.values()}),
                competitors=["Manual workflow", "Horizontal GRC suite"],
                business_model_variants=["Subscription", "Usage-based API"],
                economics={
                    "gross_margin_base": 0.8,
                    "currency": economics.currency,
                    "period_months": economics.period_months,
                    "assumptions": economics.assumptions.model_dump(mode="json"),
                    "scenarios": {key: value.model_dump(mode="json") for key, value in economics.scenarios.items()},
                },
                readiness=(readiness.model_dump(mode="json") | {"pipeline_validation_decision": "BUILD", "pipeline_validation_reason_codes": ["HARD_GATES_PASSED"]}),
                opportunity_investment_thesis=idea.one_sentence_thesis,
                critical_assumptions=[item.model_dump(mode="json") for item in assumptions if item.criticality.value == "FATAL"],
                recommended_experiment={"description": "Preregistered price-choice test", "estimated_cost": {"value": 0, "basis": "ESTIMATE", "currency": "USD"}, "success_criteria": "A preregistered share of qualified buyers selects a paid tier."},
                addressable_market={"value": None, "basis": "UNKNOWN", "reason": "No sourced market sizing is recorded."},
                reachable_market={"value": None, "basis": "UNKNOWN", "reason": "No distribution reach or serviceable-market estimate is recorded."},
                willingness_to_pay_evidence=[
                    item.id for item in candidate_evidence
                    if any(a.id in item.supported_assumption_ids and a.category.value == "WTP" for a in assumptions)
                    and item.commercial_scope.value == "PRODUCT"
                    and item.commercial_classification.value in {"CUSTOMER_VALIDATION", "PURCHASE_INTENT", "OBSERVED_TRANSACTION"}
                ],
                commercial_evidence_grades=[item.model_dump(mode="json") for item in grades],
                automation_ratio=idea.autonomous_scalability.target_automation_ratio,
                human_minutes_per_customer_at_10x=idea.autonomous_scalability.human_minutes_per_customer_at_10x,
                red_team_findings=["Resolved market-skeptic challenge"],
                ranking=(
                    ranking_by_id.get(identifier, {"rank": 1, "stability": 1})
                    | {"portfolio_size": len(state.finalist_ids)}
                ),
                recommended_experiments=["Preregistered price-choice test"],
                decision=readiness.recommendation,
                reason_codes=readiness.reason_codes,
            )
            markdown, structured = write_dossier(
                dossier, self.output_directory / state.run_id / "deliverables"
            )
            paths.extend((str(markdown), str(structured)))
        return {"artifacts": {"dossier_paths": paths}}

    @staticmethod
    def _named_evidence(
        identifiers: list[str], evidence_by_id: dict[str, EvidenceItem]
    ) -> list[EvidenceReference]:
        references: list[EvidenceReference] = []
        for position, identifier in enumerate(identifiers, start=1):
            item = evidence_by_id.get(identifier)
            if item is None:
                references.append(
                    EvidenceReference(
                        title=f"Evidence source {position}",
                        summary="The source record is retained in canonical storage.",
                    )
                )
                continue
            publisher = item.publisher or item.source_type.replace("_", " ").title()
            references.append(
                EvidenceReference(
                    title=(
                        f"{publisher} — {item.evidence_type.value.title()} "
                        f"{item.tier.value.lower()} evidence"
                    ),
                    summary=item.extracted_fact,
                    url=str(item.source_url) if item.source_url else None,
                    publisher=item.publisher,
                    tier=item.tier.value,
                )
            )
        return references

    def _finalize_run(self, state: PipelineState) -> dict[str, Any]:
        self._write_run_overview(state)
        self.runs.set_status(state.run_id, RunStatus.COMPLETED)
        return {}

    def _record_visible_stage_output(
        self, stage: StageName, state: PipelineState, result: dict[str, Any]
    ) -> None:
        artifacts = result.get("artifacts", {})
        conversation, message = {
            StageName.INITIALIZE_RUN: (
                "market_research_summary.log",
                f"Run initialized for mandate: {state.mandate}",
            ),
            StageName.DISCOVER_SIGNALS: (
                "market_research_summary.log",
                "Observed signals: "
                + ", ".join(artifacts.get("signals", [])),
            ),
            StageName.GENERATE_IDEAS: (
                "ideation_summary.log",
                (
                    f"Generated {artifacts.get('raw_idea_count', 0)} raw ideas; "
                    f"deduplicated fixture retained {len(result.get('candidate_ids', []))}.\n"
                    "Retained ideas: "
                    + ", ".join(
                        item.get("title", "Untitled")
                        for item in artifacts.get("idea_records", [])
                    )
                ),
            ),
            StageName.ELIGIBILITY_GATE: (
                "ideation_summary.log",
                (
                    f"Digital/autonomous gate retained "
                    f"{len(result.get('eligible_candidate_ids', []))} candidates."
                ),
            ),
            StageName.DECOMPOSE_ASSUMPTIONS: (
                "ideation_summary.log",
                f"Decomposed {len(artifacts.get('assumptions', []))} atomic assumptions.",
            ),
            StageName.COLLECT_EVIDENCE: (
                "market_research_summary.log",
                (
                    "Collected "
                    f"{sum(len(items) for items in artifacts.get('evidence_by_assumption', {}).values())} "
                    "traceable evidence items."
                ),
            ),
            StageName.VALIDATE_ASSUMPTIONS: (
                "evidence_validation_summary.log",
                (
                    f"Validated {len(artifacts.get('validated_assumptions', []))} "
                    "assumptions against independent evidence lineages."
                ),
            ),
            StageName.MODEL_BUSINESS: (
                "portfolio_summary.log",
                f"Compared {len(artifacts.get('business_models', []))} digital business models.",
            ),
            StageName.RED_TEAM: (
                "red_team_summary.log",
                (
                    f"Completed {len(artifacts.get('red_team_findings', []))} "
                    f"adversarial reviews; {len(result.get('finalist_ids', []))} survived."
                ),
            ),
            StageName.RANK_PORTFOLIO: (
                "portfolio_summary.log",
                (
                    f"Ranked {len(artifacts.get('rankings', []))} finalists from "
                    f"{len(artifacts.get('matches', []))} stored pairwise matches."
                ),
            ),
            StageName.DESIGN_EXPERIMENTS: (
                "portfolio_summary.log",
                f"Preregistered {len(artifacts.get('experiments', []))} experiments.",
            ),
            StageName.OBSERVE_AND_DECIDE: (
                "portfolio_summary.log",
                "Checked immutable outcomes; no unobserved result was promoted to evidence.",
            ),
            StageName.PRODUCE_DOSSIER: (
                "portfolio_summary.log",
                f"Produced {len(artifacts.get('dossier_paths', []))} dossier artifacts.",
            ),
            StageName.FINALIZE_RUN: (
                "portfolio_summary.log",
                "Run completed with ranked BUILD / KILL / ITERATE recommendations.",
            ),
        }[stage]
        self.workspaces.append_visible_output(state.run_id, conversation, message)

    def _write_run_overview(self, state: PipelineState) -> Path:
        workspace = self.workspaces.ensure(state.run_id)
        overview = {
            "artifact_type": "run_overview",
            "run_id": state.run_id,
            "funnel": {
                "observed_signals": len(state.signal_ids),
                "raw_ideas": int(state.artifacts.get("raw_idea_count", 0)),
                "evidence_qualified": len(state.eligible_candidate_ids),
                "assumption_validated": len(state.eligible_candidate_ids),
                "red_team_survivors": len(state.finalist_ids),
                "experiment_candidates": len(state.finalist_ids),
                "observed_market_evidence": 0,
                "ranked_recommendations": len(state.finalist_ids),
            },
        }
        path = workspace.deliverables / "run-overview.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(overview, indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return path

    @staticmethod
    def _opportunity_description(idea: BusinessIdea) -> str:
        return (
            f"{idea.title} is a software opportunity for {idea.target_customer} "
            "that need to translate changing rules and policies into reliable "
            "operational work. The product would ingest official, machine-readable "
            "material, identify relevant obligations, map them to a customer's "
            "workflow, and produce traceable recommendations for expert review. "
            f"Its primary buyer is the {idea.buyer}, while {idea.user} teams use "
            "the service through a self-service application and API. The value "
            "comes from reducing repetitive evidence review, shortening response "
            "cycles, and preserving an auditable source trail. Subscription and "
            "usage-based pricing could support the delivery model. The system "
            "targets high automation and low marginal human effort, with people "
            "involved mainly for consequential exceptions. Initial validation "
            "should test buyer urgency, output accuracy, integration effort, "
            "repeat usage, and willingness to pay before committing resources to "
            "a production build. The proposed service remains fully digital in "
            "acquisition, delivery, support, payment, operation, and geographic "
            "scaling."
        )

    @staticmethod
    def _idea(state: PipelineState, title: str, workflow: str) -> BusinessIdea:
        return BusinessIdea(
            run_id=state.run_id,
            problem_id=f"problem-{workflow.replace(' ', '-')}",
            title=title,
            one_sentence_thesis=f"Automate costly {workflow} for regulated teams.",
            target_customer="Regulated mid-market companies",
            buyer="Chief compliance officer",
            user="Compliance analyst",
            value_proposition="Reduce review time with traceable evidence.",
            product_form="SaaS and API",
            delivery_model="Self-service digital application",
            why_now="Official rules are increasingly machine-readable.",
            digital_eligibility=DigitalEligibility(
                **{name: True for name in DigitalEligibility.model_fields}
            ),
            autonomous_scalability=AutonomousScalability(
                target_automation_ratio=0.95,
                human_minutes_per_customer=15,
                human_minutes_per_customer_at_10x=1.5,
                human_only_tasks=["exception approval"],
                credible_transition_plan=True,
            ),
        )

    @staticmethod
    def _evidence(run_id: str, assumption_id: str, index: int) -> EvidenceItem:
        source = f"fixture://{assumption_id}/{index}"
        return EvidenceItem(
            run_id=run_id,
            source_identifier=source,
            source_type="acceptance_fixture",
            publisher=f"Independent publisher {index}",
            extracted_fact="Independent fixture evidence supports the bounded claim.",
            tier=EvidenceTier.PRIMARY,
            evidence_type=EvidenceType.MEASURED,
            direction=EvidenceDirection.SUPPORTS,
            reliability_score=0.9,
            freshness_score=1.0,
            lineage_group_id=f"{assumption_id}-lineage-{index}",
            content_hash=sha256(source.encode()).hexdigest(),
            supported_assumption_ids=[assumption_id],
        )
