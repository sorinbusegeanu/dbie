from pathlib import Path

import pytest

from dbie.config import Settings
from dbie.persistence.db import Database
from dbie.persistence.repositories import RunRepository
from dbie.services.run_service import RunService
from dbie.services.run_workspace import RunWorkspaceManager


def test_workspace_creates_public_contract_and_current_alias(tmp_path: Path) -> None:
    manager = RunWorkspaceManager(tmp_path / "runs")

    first = manager.ensure("run-one")
    second = manager.ensure("run-two")
    log = manager.append_activity("run-two", "crew visible output")
    crew_log = manager.append_visible_output(
        "run-two", "market_research_crew.log", "signal found\nevidence collected"
    )

    assert first.conversations.is_dir()
    assert second.deliverables.is_dir()
    assert (tmp_path / "runs" / "current").resolve() == second.root.resolve()
    assert "crew visible output" in log.read_text(encoding="utf-8")
    assert "signal found" in crew_log.read_text(encoding="utf-8")
    assert "evidence collected" in crew_log.read_text(encoding="utf-8")


def test_workspace_rejects_unsafe_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safe filesystem name"):
        RunWorkspaceManager(tmp_path).ensure("../escape")

    with pytest.raises(ValueError, match="safe .log basename"):
        RunWorkspaceManager(tmp_path).append_visible_output(
            "safe", "../conversation.log", "no"
        )


def test_run_service_creates_dashboard_workspace(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'db.sqlite3'}")
    database.initialize()
    settings = Settings(run_directory=tmp_path / "runs")

    run = RunService(RunRepository(database), settings).create("test mandate")

    assert (tmp_path / "runs" / run.id / "conversations").is_dir()
    assert (tmp_path / "runs" / run.id / "deliverables").is_dir()
    assert (tmp_path / "runs" / "current").resolve().name == run.id
