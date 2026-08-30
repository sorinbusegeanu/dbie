from dbie.config import ModelProfile, ModelsConfig, OllamaSettings
from dbie.crews.router_llm import RouterLLM
from dbie.models.base import (
    ChatMessage,
    GenerationResponse,
    LLMProvider,
    UsageSnapshot,
)
from dbie.models.capabilities import ModelCapabilities, ProviderHealth
from dbie.models.router import ModelRouter


class ToolProvider(LLMProvider):
    name = "ollama"

    def generate(self, model, request):
        return GenerationResponse(
            provider="ollama", model=model, content="done", latency_seconds=0
        )

    def structured_generate(self, model, request, schema):
        raise NotImplementedError

    def tool_call(self, model, request):
        return GenerationResponse(
            provider="ollama",
            model=model,
            content="",
            latency_seconds=0,
            tool_calls=[
                {
                    "id": "call-1",
                    "function": {
                        "name": "web_search",
                        "arguments": {"query": "pain"},
                    },
                }
            ],
        )

    def capabilities(self, model):
        return ModelCapabilities(
            model=model,
            context_tokens=8192,
            reasoning=False,
            tools=True,
            structured_output=True,
        )

    def health(self):
        return ProviderHealth(provider="ollama", reachable=True)

    def usage(self):
        return UsageSnapshot()


def test_router_llm_returns_native_tool_calls_to_crewai_executor() -> None:
    profile = ModelProfile(
        provider="ollama",
        model="tool-model",
        family="test",
        maximum_context_tokens=8192,
        request_context_tokens=4096,
        tools=True,
        structured_output=True,
    )
    router = ModelRouter(
        ModelsConfig(
            active_provider="ollama",
            default_profile="tool",
            providers={"ollama": OllamaSettings()},
            profiles={"tool": profile},
        ),
        {"ollama": ToolProvider()},
    )
    llm = RouterLLM(router, profile_name="tool")

    result = llm.call(
        [{"role": "user", "content": "Use search"}],
        tools=[{"type": "function", "function": {"name": "web_search"}}],
    )

    assert isinstance(result, list)
    assert result[0]["function"]["name"] == "web_search"


def test_router_llm_preserves_crewai_tool_history() -> None:
    messages = [
        ChatMessage(role="user", content="Use search"),
        ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call-1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query":"pain"}',
                    },
                }
            ],
        ),
        ChatMessage(
            role="tool",
            content='{"results": []}',
            tool_call_id="call-1",
            name="web_search",
        ),
    ]

    assert messages[1].tool_calls[0]["function"]["name"] == "web_search"
    assert messages[2].name == "web_search"
