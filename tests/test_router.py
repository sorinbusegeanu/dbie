from dbie.config import ModelProfile, ModelRoleConfig, ModelsConfig, OllamaSettings
from dbie.exceptions import ModelUnavailableError
from dbie.models.base import (
    ChatMessage,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    UsageSnapshot,
)
from dbie.models.capabilities import ModelCapabilities, ProviderHealth
from dbie.models.roles import ModelRole, ModelSelection
from dbie.models.router import ModelRouter


class FakeProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.called: list[str] = []
        self.requests: list[GenerationRequest] = []

    def generate(self, model, request):
        self.called.append(model)
        self.requests.append(request)
        if model == "gpt-oss:20b-64k":
            raise ModelUnavailableError("not installed")
        return GenerationResponse(
            provider="ollama", model=model, content="fallback", latency_seconds=0
        )

    def structured_generate(self, model, request, schema):
        raise NotImplementedError

    def tool_call(self, model, request):
        raise NotImplementedError

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


def profile(model: str, family: str) -> ModelProfile:
    return ModelProfile(
        provider="ollama",
        model=model,
        family=family,
        maximum_context_tokens=64000,
        request_context_tokens=16384,
        reasoning=True,
        tools=True,
        structured_output=True,
    )


def test_router_falls_back_to_requested_ministral_profile() -> None:
    config = ModelsConfig(
        active_provider="ollama",
        default_profile="gpt",
        fallback_profiles=["ministral"],
        providers={"ollama": OllamaSettings()},
        profiles={
            "gpt": profile("gpt-oss:20b-64k", "gpt-oss"),
            "ministral": profile("ministral-3:14b-64k", "ministral-3"),
        },
    )
    provider = FakeProvider()
    router = ModelRouter(config, {"ollama": provider})
    request = GenerationRequest(messages=[ChatMessage(role="user", content="go")])

    response = router.generate(request)

    assert response.content == "fallback"
    assert provider.called == ["gpt-oss:20b-64k", "ministral-3:14b-64k"]


def test_role_router_applies_context_thinking_and_role_fallback() -> None:
    config = ModelsConfig(
        active_provider="ollama",
        default_profile="gpt",
        fallback_profiles=["ministral"],
        providers={"ollama": OllamaSettings()},
        profiles={
            "gpt": profile("gpt-oss:20b-64k", "gpt-oss"),
            "ministral": profile("ministral-3:14b-64k", "ministral-3"),
        },
        roles={
            ModelRole.DOER: ModelRoleConfig(
                primary_profile="gpt",
                fallback_profiles=["ministral"],
                context_tokens=8192,
                thinking_mode="off",
            )
        },
    )
    provider = FakeProvider()
    router = ModelRouter(config, {"ollama": provider})

    response = router.generate_for_role(
        GenerationRequest(messages=[ChatMessage(role="user", content="research")]),
        role=ModelRole.DOER,
    )

    assert response.model == "ministral-3:14b-64k"
    assert provider.requests[0].context_tokens == 8192
    assert provider.requests[0].thinking is False


def test_challenger_selection_is_stable_for_same_task() -> None:
    config = ModelsConfig(
        active_provider="ollama",
        default_profile="gpt",
        providers={"ollama": OllamaSettings()},
        profiles={
            "gpt": profile("gpt-oss:20b-64k", "gpt-oss"),
            "ministral": profile("ministral-3:14b-64k", "ministral-3"),
        },
        roles={
            ModelRole.JUDGE: ModelRoleConfig(
                primary_profile="gpt",
                challenger_profile="ministral",
                context_tokens=8192,
                challenger_fraction=0.5,
            )
        },
    )
    router = ModelRouter(config, {"ollama": FakeProvider()})
    selections = [
        router.selection_for_task(ModelRole.JUDGE, "task-42") for _ in range(3)
    ]
    assert len(set(selections)) == 1
    assert selections[0] in {ModelSelection.PRIMARY, ModelSelection.CHALLENGER}
