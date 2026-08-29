from dbie.config import ModelRoleConfig, ModelsConfig, OllamaSettings
from dbie.crews.router_llm import RouterLLM
from dbie.models.base import (
    GenerationResponse,
    LLMProvider,
    UsageSnapshot,
)
from dbie.models.capabilities import ModelCapabilities, ProviderHealth
from dbie.models.performance import (
    ModelExecutionContext,
    ModelPerformanceRecord,
    ModelPhasePerformanceRecord,
)
from dbie.models.roles import ModelRole
from dbie.models.router import ModelRouter
from dbie.models.task_roles import TaskClass
from dbie.persistence.db import Database
from dbie.persistence.model_performance import ModelPerformanceRepository


class RecordingProvider(LLMProvider):
    name = "ollama"

    def generate(self, model, request):
        return GenerationResponse(
            provider="ollama",
            model=model,
            content="done",
            latency_seconds=0.01,
            prompt_tokens=12,
            completion_tokens=3,
        )

    def structured_generate(self, model, request, schema):
        raise NotImplementedError

    def tool_call(self, model, request):
        return self.generate(model, request)

    def capabilities(self, model):
        return ModelCapabilities(
            model=model,
            context_tokens=64000,
            reasoning=True,
            tools=True,
            structured_output=True,
        )

    def health(self):
        return ProviderHealth(provider="ollama", reachable=True)

    def usage(self):
        return UsageSnapshot()


def test_model_performance_and_phase_residency_are_directly_queryable(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'model-ledger.sqlite3'}")
    database.initialize()
    repository = ModelPerformanceRepository(database)
    repository.record(
        ModelPerformanceRecord(
            run_id="run",
            venture_id="venture",
            crew_id="research",
            agent_id="market",
            task_id="task",
            task_class=TaskClass.MARKET_EVIDENCE,
            model_role=ModelRole.DOER,
            model_id="qwen3:14b-64k",
            runtime="ollama",
            thinking_mode="off",
            context_limit=16384,
            input_tokens=100,
            output_tokens=25,
            wall_clock_ms=500,
            tokens_per_second=50,
            tool_calls=2,
            schema_valid=True,
            task_success=True,
        )
    )
    repository.record_phase(
        ModelPhasePerformanceRecord(
            run_id="run",
            phase_id="phase",
            model_role=ModelRole.DOER,
            resolved_profile="qwen",
            model_id="qwen3:14b-64k",
            dependency_barrier=1,
            tasks_per_model_residency=4,
            phase_duration_ms=1000,
        )
    )

    record = repository.for_task("task")[0]
    assert record.model_role is ModelRole.DOER
    assert record.tokens_per_second == 50
    assert repository.for_role("run", ModelRole.DOER) == [record]
    assert repository.phases_for_run("run")[0].tasks_per_model_residency == 4


def test_crewai_role_bridge_records_every_contextualized_model_call(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'bridge-ledger.sqlite3'}")
    database.initialize()
    repository = ModelPerformanceRepository(database)
    profile = {
        "provider": "ollama",
        "model": "qwen3:14b-64k",
        "family": "qwen3",
        "maximum_context_tokens": 64000,
        "request_context_tokens": 16384,
        "reasoning": True,
        "tools": True,
        "structured_output": True,
    }
    config = ModelsConfig(
        active_provider="ollama",
        default_profile="qwen",
        providers={"ollama": OllamaSettings()},
        profiles={"qwen": profile},
        roles={
            ModelRole.DOER: ModelRoleConfig(
                primary_profile="qwen",
                context_tokens=16384,
                thinking_mode="off",
            )
        },
    )
    router = ModelRouter(config, {"ollama": RecordingProvider()})
    llm = RouterLLM(router, performance_sink=repository).for_execution(
        ModelRole.DOER,
        ModelExecutionContext(
            run_id="run",
            crew_id="market",
            agent_id="researcher",
            task_id="task-call",
            task_class=TaskClass.MARKET_EVIDENCE,
        ),
    )

    assert llm.call([{"role": "user", "content": "research"}]) == "done"
    record = repository.for_task("task-call")[0]
    assert record.model_id == "qwen3:14b-64k"
    assert record.model_role is ModelRole.DOER
    assert record.input_tokens == 12
    assert record.output_tokens == 3
    assert record.task_success is True
