import json

import httpx
from pydantic import BaseModel

from dbie.config import ModelProfile, OllamaSettings
from dbie.models.base import ChatMessage, GenerationRequest
from dbie.models.ollama_provider import OllamaProvider


def profiles() -> dict[str, ModelProfile]:
    return {
        "gpt": ModelProfile(
            provider="ollama",
            model="gpt-oss:20b-64k",
            family="gpt-oss",
            maximum_context_tokens=64000,
            request_context_tokens=16384,
            reasoning=True,
            tools=True,
            structured_output=True,
        )
    }


def request() -> GenerationRequest:
    return GenerationRequest(messages=[ChatMessage(role="user", content="Answer")])


def test_health_reports_exact_installed_models() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test"})
        return httpx.Response(
            200,
            json={"models": [{"name": "gpt-oss:20b-64k"}]},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    provider = OllamaProvider(OllamaSettings(), profiles(), client)

    health = provider.health()

    assert health.reachable is True
    assert health.installed_models == ["gpt-oss:20b-64k"]


def test_generate_uses_conservative_profile_context() -> None:
    seen: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "gpt-oss:20b-64k",
                "message": {"role": "assistant", "content": "result"},
                "done_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 4,
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    provider = OllamaProvider(OllamaSettings(), profiles(), client)

    response = provider.generate("gpt-oss:20b-64k", request())

    assert response.content == "result"
    assert seen["options"] == {"num_ctx": 16384, "num_predict": 8192}
    assert provider.usage().completion_tokens == 4


def test_structured_generate_uses_json_schema() -> None:
    class Answer(BaseModel):
        accepted: bool

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        assert body["format"]["properties"]["accepted"]["type"] == "boolean"
        return httpx.Response(
            200,
            json={"message": {"content": '{"accepted": true}'}, "done": True},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    provider = OllamaProvider(OllamaSettings(), profiles(), client)

    answer = provider.structured_generate("gpt-oss:20b-64k", request(), Answer)

    assert answer.accepted is True


def test_generate_preserves_native_tool_call_history_for_ollama() -> None:
    seen: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={"message": {"content": "https://example.test"}, "done": True},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    provider = OllamaProvider(OllamaSettings(), profiles(), client)
    tool_history = GenerationRequest(
        messages=[
            ChatMessage(role="user", content="Search"),
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
                content='{"sources":["https://example.test"]}',
                tool_call_id="call-1",
                name="web_search",
            ),
        ]
    )

    provider.generate("gpt-oss:20b-64k", tool_history)

    messages = seen["messages"]
    assert messages[1]["tool_calls"][0]["function"]["arguments"] == {
        "query": "pain"
    }
    assert messages[2]["tool_name"] == "web_search"
