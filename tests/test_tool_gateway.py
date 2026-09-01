from datetime import UTC, datetime

import pytest

from dbie.exceptions import ToolBudgetExceeded, ToolExecutionError, ToolPermissionDenied
from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.adapters.registry import AdapterRegistry
from dbie.tools.contracts import ToolBudget, ToolCallEnvelope, ToolName
from dbie.tools.gateway import ToolGateway
from dbie.tools.permissions import ToolPermissionPolicy
from dbie.tools.logical_outputs import DocumentOutput


class FakeAdapter(ToolAdapter):
    name = "fake_search"
    capabilities = AdapterCapabilities(operations={"web_search"})

    def __init__(self, *, fail: bool = False, cost: float = 0) -> None:
        self.calls = 0
        self.fail = fail
        self.cost = cost

    def health(self) -> AdapterHealth:
        return AdapterHealth(name=self.name, available=True, version="test")

    def execute(self, request: AdapterRequest) -> AdapterResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider secret detail")
        now = datetime.now(UTC)
        return AdapterResult(
            payload={
                "results": [{"title": "Result"}],
                "snippets_are_evidence": False,
            },
            raw_sources=[
                {
                    "source_identifier": "https://example.test",
                    "source_url": "https://example.test",
                }
            ],
            started_at=now,
            ended_at=now,
            adapter_version="test",
            cost=self.cost,
        )


def envelope(actor: str = "Scout", max_calls: int = 2) -> ToolCallEnvelope:
    return ToolCallEnvelope(
        run_id="run",
        stage_id="discover",
        task_id="task",
        actor_id=actor,
        tool=ToolName.WEB_SEARCH,
        arguments={"query": "problem"},
        purpose="discover source",
        budget=ToolBudget(max_calls=max_calls),
    )


def gateway(adapter: FakeAdapter) -> ToolGateway:
    registry = AdapterRegistry()
    registry.register(adapter)
    return ToolGateway(
        registry=registry,
        routes={ToolName.WEB_SEARCH: adapter.name},
        permissions=ToolPermissionPolicy({"Scout": ["web_search"]}),
    )


def test_denied_call_is_rejected_and_audited() -> None:
    value = gateway(FakeAdapter())

    with pytest.raises(ToolPermissionDenied):
        value.invoke(envelope(actor="Generator"))

    assert value.audit.records[-1].allowed is False


def test_document_output_drops_large_internal_parser_structure() -> None:
    output = DocumentOutput.model_validate(
        {
            "source": "https://example.test/document",
            "content": "bounded",
            "file_hash": "hash",
            "pages": {"1": {"large": "internal"}},
            "tables": [{"large": "internal"}],
        }
    )

    assert output.model_dump() == {
        "source": "https://example.test/document",
        "content": "bounded",
        "file_hash": "hash",
    }


def test_allowed_call_is_normalized_cached_and_audited() -> None:
    adapter = FakeAdapter()
    value = gateway(adapter)

    first = value.invoke(envelope())
    second = value.invoke(envelope())

    assert first.payload["results"][0]["title"] == "Result"
    assert first.adapter_provenance[0].adapter == "fake_search"
    assert second.cache_status == "HIT"
    assert adapter.calls == 1
    assert len(value.audit.records) == 2


def test_task_call_budget_is_authoritative_even_for_cache_hits() -> None:
    value = gateway(FakeAdapter())
    value.invoke(envelope(max_calls=1))

    with pytest.raises(ToolBudgetExceeded):
        value.invoke(envelope(max_calls=1))


def test_zero_cost_budget_rejects_nonzero_adapter_cost() -> None:
    value = gateway(FakeAdapter(cost=0.01))
    with pytest.raises(ToolBudgetExceeded, match="cost budget"):
        value.invoke(envelope())


def test_adapter_exception_does_not_leak_provider_detail() -> None:
    value = gateway(FakeAdapter(fail=True))

    with pytest.raises(
        ToolExecutionError, match="logical tool execution failed"
    ) as caught:
        value.invoke(envelope())

    assert "secret detail" not in str(caught.value)
    assert value.audit.records[-1].result.error_category == "ADAPTER_FAILURE"


def test_gateway_retries_once_and_records_adapter_metrics() -> None:
    class FlakyAdapter(FakeAdapter):
        def execute(self, request: AdapterRequest) -> AdapterResult:
            if self.calls == 0:
                self.calls += 1
                raise RuntimeError("temporary")
            return super().execute(request)

    adapter = FlakyAdapter()
    value = gateway(adapter)

    result = value.invoke(envelope())

    assert adapter.calls == 2
    assert result.adapter_provenance[0].retry_count == 1
    assert (
        value.metrics.snapshot().counters["tool_calls{status=success,tool=web_search}"]
        == 1
    )


def test_registry_rejects_duplicate_names() -> None:
    registry = AdapterRegistry()
    registry.register(FakeAdapter())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeAdapter())
