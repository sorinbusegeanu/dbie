import pytest

from dbie.exceptions import ToolInputValidationError
from dbie.tools.adapters.base import AdapterCapabilities
from dbie.tools.contracts import ToolName
from dbie.tools.logical import LOGICAL_TOOL_INPUTS, PythonExecuteInput
from dbie.tools.logical_outputs import LOGICAL_TOOL_OUTPUTS
from tests.test_tool_gateway import FakeAdapter, envelope, gateway


def test_crewai_visible_surface_is_exactly_ten_tools() -> None:
    assert set(LOGICAL_TOOL_INPUTS) == set(ToolName)
    assert set(LOGICAL_TOOL_OUTPUTS) == set(ToolName)
    assert len(LOGICAL_TOOL_INPUTS) == 10


def test_python_execute_cannot_enable_network() -> None:
    with pytest.raises(ValueError):
        PythonExecuteInput(
            code="print(1)",
            purpose="CALCULATION",
            network=True,  # type: ignore[arg-type]
        )


def test_gateway_validates_logical_arguments_before_adapter() -> None:
    adapter = FakeAdapter()
    adapter.capabilities = AdapterCapabilities(operations={"web_search"})
    value = gateway(adapter)
    invalid = envelope().model_copy(update={"arguments": {"max_results": 10}})

    with pytest.raises(ToolInputValidationError):
        value.invoke(invalid)

    assert adapter.calls == 0
