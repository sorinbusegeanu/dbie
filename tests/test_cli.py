import json
from pathlib import Path

from typer.testing import CliRunner

from dbie.cli import app


def test_smoke_command_round_trips_without_llm(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "DBIE_DATABASE_URL", f"sqlite:///{tmp_path / 'cli-smoke.sqlite3'}"
    )

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
