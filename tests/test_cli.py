import json
from pathlib import Path

from typer.testing import CliRunner

from dbie.cli import _restored_live_config, app
from dbie.flows.state import PipelineState
from dbie.services.live_mvp import LiveMVPConfig


def test_smoke_command_round_trips_without_llm(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "DBIE_DATABASE_URL", f"sqlite:///{tmp_path / 'cli-smoke.sqlite3'}"
    )
    monkeypatch.setenv("DBIE_RUN_DIRECTORY", str(tmp_path / "runs"))

    result = CliRunner().invoke(app, ["smoke"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["eligible"] is True
    assert payload["reloaded_identically"] is True
    assert payload["state"] == "ELIGIBLE"


def test_dashboard_command_starts_configured_read_only_app(
    monkeypatch, tmp_path: Path
) -> None:
    received = {}

    def fake_run(application, **kwargs) -> None:
        received["application"] = application
        received.update(kwargs)

    monkeypatch.setattr("uvicorn.run", fake_run)
    result = CliRunner().invoke(
        app,
        [
            "dashboard",
            "--runs-dir",
            str(tmp_path),
            "--host",
            "127.0.0.2",
            "--port",
            "9876",
            "--refresh",
            "0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert received["host"] == "127.0.0.2"
    assert received["port"] == 9876
    assert received["application"].title == "DBIE Run Dashboard"


def test_resume_restores_original_live_run_targets() -> None:
    original = LiveMVPConfig(
        target_signals=50,
        target_raw_ideas=25,
        max_validation_candidates=5,
        strict_generation_targets=False,
    )
    state = PipelineState(
        run_id="run-1",
        mandate="Find digital opportunities",
        artifacts={"live_mvp_config": original.model_dump(mode="json")},
    )

    restored = _restored_live_config(LiveMVPConfig(), state)

    assert restored == original
