"""Offline reproducible full-pipeline fixture used for acceptance and demos."""

from __future__ import annotations

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
from dbie.reporting.dossier import AssumptionSummary, Dossier, write_dossier
from dbie.services.assumption_pipeline import decompose_idea, validate_assumption
from dbie.services.candidate_service import CandidateService
from dbie.services.run_workspace import RunWorkspaceManager
from dbie.services.tournament import rank_matches
from dbie.services.validation import RedTeamFinding, validation_decision


class FixtureMVPExecutor:
    """Exercises every deterministic MVP stage without network/model calls."""

    def __init__(self, database: Database, output_directory: Path) -> None:
        self.database = database
        self.output_directory = output_directory
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
            decisions[identifier] = decision.model_dump(mode="json")
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

    def _produce_dossier(self, state: PipelineState) -> dict[str, Any]:
        ranking_by_id = {
            item["idea_id"]: item for item in state.artifacts.get("rankings", [])
        }
        paths = []
        for identifier in state.finalist_ids:
            idea = self.candidates.get(identifier)
            assumptions = self.assumptions.for_idea(identifier)
            dossier = Dossier(
                run_id=state.run_id,
                candidate_id=identifier,
                title=idea.title,
                thesis=idea.one_sentence_thesis,
                why_now=idea.why_now,
                customer=idea.target_customer,
                buyer=idea.buyer,
                assumptions=[
                    AssumptionSummary(
                        statement=item.statement,
                        status=item.status.value,
                        evidence_for=item.evidence_for_ids,
                        evidence_against=item.evidence_against_ids,
                        independent_lineages=2,
                    )
                    for item in assumptions
                ],
                unknowns=[],
                competitors=["Manual workflow", "Horizontal GRC suite"],
                business_model_variants=["Subscription", "Usage-based API"],
                economics={"gross_margin_base": 0.8, "source": "fixture"},
                automation_ratio=idea.autonomous_scalability.target_automation_ratio,
                human_minutes_per_customer_at_10x=idea.autonomous_scalability.human_minutes_per_customer_at_10x,
                red_team_findings=["Resolved market-skeptic challenge"],
                ranking=ranking_by_id.get(identifier, {"rank": 1, "stability": 1}),
                recommended_experiments=["Preregistered price-choice test"],
                decision=DecisionType.BUILD,
                reason_codes=["HARD_GATES_PASSED"],
            )
            markdown, structured = write_dossier(
                dossier, self.output_directory / state.run_id / "deliverables"
            )
            paths.extend((str(markdown), str(structured)))
        return {"artifacts": {"dossier_paths": paths}}

    def _finalize_run(self, state: PipelineState) -> dict[str, Any]:
        self.runs.set_status(state.run_id, RunStatus.COMPLETED)
        return {}

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
        )
