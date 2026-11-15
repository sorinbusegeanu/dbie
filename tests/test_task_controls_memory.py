import json
from pathlib import Path

import httpx

from dbie.config import ModelProfile, ModelRoleConfig, ModelsConfig, OllamaSettings
from dbie.crews.catalog import ActorSpec, CrewCatalog, task_class_for_actor, task_class_for_request
from dbie.crews.outputs import RunPlan
from dbie.crews.router_llm import RouterLLM
from dbie.crews.skills import skills_for_task
from dbie.crews.stage_runner import CrewAIStageRunner, CrewTaskRequest
from dbie.domain.enums import CandidateState
from dbie.domain.memory import BusinessLesson
from dbie.models.ollama_provider import OllamaProvider
from dbie.models.performance import ModelExecutionContext
from dbie.models.roles import ModelRole
from dbie.models.task_roles import TaskClass
from dbie.models.router import ModelRouter
from dbie.persistence.db import Database
from dbie.persistence.repositories import BusinessLessonRepository, CandidateRepository
from dbie.persistence.vector import DeterministicEmbeddingService, SemanticMemoryRepository
from dbie.services.live_mvp import _compare_idea_dimensions, _explicit_reconsideration, _may_reconsider
from dbie.tools.crewai_tools import CrewAIToolContext
from tests.conftest import make_idea


def _router(monkeypatch, requested: list[dict[str, object]]) -> ModelRouter:
    profile = ModelProfile(
        provider="ollama", model="local-model", family="test",
        maximum_context_tokens=4096, request_context_tokens=2048,
        reasoning=True, tools=True, structured_output=True,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "local-model", "message": {"content": "ok"}, "done": True})

    provider = OllamaProvider(OllamaSettings(base_url="http://ollama.test"), {"local": profile}, httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test"))
    config = ModelsConfig(
        active_provider="ollama", default_profile="local", providers={"ollama": OllamaSettings()},
        profiles={"local": profile},
        roles={ModelRole.THINKER: ModelRoleConfig(primary_profile="local", context_tokens=2048)},
        task_temperatures={TaskClass.DISCOVERY_IDEATION: 0.8, TaskClass.FINANCIAL_ANALYSIS: 0.0},
    )
    return ModelRouter(config, {"ollama": provider})


def _call(router: ModelRouter, task_class: TaskClass, *, temperature=None):
    llm = RouterLLM(router, temperature=temperature).for_execution(
        ModelRole.THINKER,
        ModelExecutionContext(run_id="run", crew_id="crew", agent_id="agent", task_id="task", task_class=task_class, skill_ids=["financial-modeling@1.0"]),
    )
    return llm.call("Use this context")


class _Sink:
    def __init__(self):
        self.records = []

    def record(self, item):
        self.records.append(item)

    def record_phase(self, item):
        del item


def test_task_class_temperature_reaches_ollama_and_explicit_override_wins() -> None:
    bodies: list[dict[str, object]] = []
    router = _router(None, bodies)

    _call(router, TaskClass.DISCOVERY_IDEATION)
    _call(router, TaskClass.FINANCIAL_ANALYSIS)
    _call(router, TaskClass.DISCOVERY_IDEATION, temperature=0.35)

    assert [body["options"]["temperature"] for body in bodies] == [0.8, 0.0, 0.35]


def test_execution_metrics_record_resolved_temperature_and_skill_versions() -> None:
    bodies: list[dict[str, object]] = []
    router = _router(None, bodies)
    sink = _Sink()
    llm = RouterLLM(router, performance_sink=sink).for_execution(
        ModelRole.THINKER,
        ModelExecutionContext(
            run_id="run", crew_id="crew", agent_id="agent", task_id="idea",
            task_class=TaskClass.DISCOVERY_IDEATION,
            skill_ids=["opportunity-discovery@1.0"],
        ),
    )

    llm.call("Generate ideas")

    assert sink.records[0].effective_temperature == 0.8
    assert sink.records[0].skill_ids == ["opportunity-discovery@1.0"]


def test_skills_are_versioned_loaded_and_task_classified() -> None:
    skills = skills_for_task(TaskClass.DISCOVERY_IDEATION)
    assert skills[0].identifier == "opportunity-discovery@1.0"
    assert "prior opportunities" in skills[0].instructions

    spec = ActorSpec("Automation Lens", "ideation", "Generate ideas", (), ModelRole.THINKER)
    assert task_class_for_actor(spec) is TaskClass.DISCOVERY_IDEATION
    assert task_class_for_request(type("Req", (), {"task_id": "business-model-comparison", "spec": spec})()) is TaskClass.FINANCIAL_ANALYSIS
    assert task_class_for_request(type("Req", (), {"task_id": "portfolio-tournament", "spec": spec})()) is TaskClass.JUDGE_INVESTMENT_DECISION

    request = CrewTaskRequest(
        task_id="ideas", stage_id="generate_ideas", crew_name="Idea Crew", spec=spec,
        description="Generate distinct opportunities", expected_output="A plan",
        output_model=RunPlan,
    )
    injected = CrewAIStageRunner._task_description(
        request, 0, skills, "IDEA old-id run=prior: rejected because no buyer budget",
    )
    assert "opportunity-discovery@1.0" in injected
    assert "prior buyer budget" not in skills[0].instructions
    assert "no buyer budget" in injected
    assert "not current evidence" in injected

    role_spec = ActorSpec("Opportunity Synthesizer", "synthesis", "Synthesize", (), ModelRole.THINKER)
    agent = CrewCatalog(object(), RouterLLM(_router(None, []))).build_agent(
        role_spec,
        CrewAIToolContext(run_id="run", stage_id="business", task_id="business-model-comparison", actor_id="OpportunitySynthesizer"),
        task_class=TaskClass.FINANCIAL_ANALYSIS,
        skill_ids=["financial-modeling@1.0"],
    )
    assert agent.llm.execution_context.task_class is TaskClass.FINANCIAL_ANALYSIS
    assert agent.llm.execution_context.skill_ids == ["financial-modeling@1.0"]


def test_lesson_and_semantic_memory_survive_repository_restart_and_filter_irrelevant(tmp_path: Path) -> None:
    db_path = tmp_path / "persistent.sqlite"
    database = Database(f"sqlite:///{db_path}")
    database.initialize()
    lesson = BusinessLesson(
        category="demand", opportunity_id="idea-1", run_id="old-run", task_id="validation",
        attempted_or_assumed="Buyers will pay", expected_result="Preorders", observed_result="No purchase intent",
        root_cause="Observed interview evidence", evidence_ids=["ev-1"], recommended_behavior="Test budget ownership",
        applicability_conditions=["similar buyer"], confidence=0.9, validation_status="VALIDATED",
    )
    assert BusinessLessonRepository(database).create(lesson).id == lesson.id
    memory = SemanticMemoryRepository(database, DeterministicEmbeddingService())
    memory.index(run_id="old-run", entity_type="LESSON", entity_id=lesson.id, text="No buyer budget and no purchase intent")
    memory.index(run_id="other-run", entity_type="IDEA", entity_id="idea-2", text="No buyer budget and no purchase intent")
    assert BusinessLessonRepository(database).create(lesson).id == lesson.id
    database.dispose()

    reopened = Database(f"sqlite:///{db_path}")
    hits = SemanticMemoryRepository(reopened, DeterministicEmbeddingService()).search(
        "buyer has no budget", entity_types={"LESSON"}, min_similarity=-0.01,
    )
    assert hits and hits[0].entity_id == lesson.id
    assert SemanticMemoryRepository(reopened, DeterministicEmbeddingService()).search(
        "totally unrelated quantum spacecraft", min_similarity=0.99,
    ) == []


def test_semantic_index_updates_lifecycle_text_idempotently(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'index.sqlite'}")
    database.initialize()
    ideas = CandidateRepository(database)
    idea = make_idea(run_id="run")
    ideas.create(idea)
    memory = SemanticMemoryRepository(database, DeterministicEmbeddingService())
    initial = memory.index(run_id="run", entity_type="IDEA", entity_id=idea.id, text=idea.title)
    ideas.set_state(idea.id, CandidateState.KILL)
    updated = memory.index(run_id="run", entity_type="IDEA", entity_id=idea.id, text=f"{idea.title} KILL: no buyer")
    again = memory.index(run_id="run", entity_type="IDEA", entity_id=idea.id, text=f"{idea.title} KILL: no buyer")
    assert updated.id == initial.id == again.id
    assert again.canonical_text.endswith("KILL: no buyer")


def test_duplicate_comparison_preserves_related_products_and_requires_evidence_for_reconsideration() -> None:
    prior = make_idea(run_id="old")
    exact = type("Draft", (), {
        "problem_title": prior.title,
        "one_sentence_thesis": prior.one_sentence_thesis,
        "target_customer": prior.target_customer,
        "buyer": prior.buyer,
        "value_proposition": prior.value_proposition,
        "product_form": prior.product_form,
        "delivery_model": prior.delivery_model,
    })()
    score = _compare_idea_dimensions(exact, prior)
    assert score["duplicate"] and score["similarity"] > 0.6
    assert _explicit_reconsideration("Reconsider with new evidence from new interviews")
    assert not _explicit_reconsideration("A fresh creative angle")


def test_duplicate_comparison_recognizes_synonymous_problem_and_same_product() -> None:
    prior = make_idea(
        run_id="old", title="Compliance workflow automation",
        one_sentence_thesis="Automates repetitive regulatory review for compliance teams.",
        target_customer="Compliance teams", buyer="Chief compliance officer",
        value_proposition="Reduce repetitive regulatory review",
        product_form="Regulatory review automation SaaS",
        delivery_model="Self-service compliance web application",
    )
    draft = type("Draft", (), {
        "problem_title": "Automated compliance checks",
        "one_sentence_thesis": "Software streamlines recurring regulation review for compliance departments.",
        "target_customer": "Compliance departments",
        "buyer": "Compliance director",
        "value_proposition": "Streamline recurring compliance checks",
        "product_form": "Compliance checklist automation software",
        "delivery_model": "Self-service compliance web app",
    })()

    score = _compare_idea_dimensions(draft, prior)
    assert score["duplicate"]
    assert score["similarity"] >= 0.55

    rejected = prior.model_copy(update={
        "lifecycle_state": CandidateState.KILL,
        "source_urls": ["source-old"],
    })
    draft.novelty_lineage = "Reconsider with new evidence from new interviews"
    assert not _may_reconsider(rejected, draft, ["source-old"])
    assert _may_reconsider(rejected, draft, ["source-new"])
