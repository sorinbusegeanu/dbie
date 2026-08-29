import os
from pathlib import Path

import pytest

from dbie.services.run_workspace import RunWorkspaceManager
from dbie.web.filesystem import DashboardFilesystem, DashboardPathError


def test_lists_runs_current_and_nested_artifacts(tmp_path: Path) -> None:
    manager = RunWorkspaceManager(tmp_path)
    older = manager.ensure("older", make_current=False)
    newer = manager.ensure("newer")
    nested = newer.deliverables / "reports"
    nested.mkdir()
    (nested / "idea.md").write_text("# Idea", encoding="utf-8")
    (newer.conversations / "crew.log").write_text("hello", encoding="utf-8")
    os.utime(older.root, (1, 1))

    filesystem = DashboardFilesystem(tmp_path)

    assert filesystem.current_run_id() == "newer"
    assert [item.run_id for item in filesystem.list_runs()] == ["newer", "older"]
    assert filesystem.list_runs()[0].is_current is True
    assert [item.relative_path for item in filesystem.list_files("newer", "deliverables")] == [
        "reports/idea.md"
    ]


def test_newest_run_is_used_when_current_alias_is_missing(tmp_path: Path) -> None:
    manager = RunWorkspaceManager(tmp_path)
    first = manager.ensure("first", make_current=False)
    second = manager.ensure("second", make_current=False)
    os.utime(first.root, (1, 1))
    os.utime(second.root, (2, 2))

    assert DashboardFilesystem(tmp_path).current_run_id() == "second"


@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", "nested/../../x"])
def test_rejects_traversal(tmp_path: Path, path: str) -> None:
    RunWorkspaceManager(tmp_path).ensure("safe")

    with pytest.raises(DashboardPathError):
        DashboardFilesystem(tmp_path).resolve_file("safe", "deliverables", path)


def test_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = RunWorkspaceManager(tmp_path / "runs").ensure("safe")
    secret = tmp_path / "secret.txt"
    secret.write_text("not public", encoding="utf-8")
    (workspace.deliverables / "escape.txt").symlink_to(secret)
    filesystem = DashboardFilesystem(tmp_path / "runs")

    assert filesystem.list_files("safe", "deliverables") == []
    with pytest.raises(DashboardPathError):
        filesystem.read_text("safe", "deliverables", "escape.txt")


def test_enforces_text_rendering_size_limit(tmp_path: Path) -> None:
    workspace = RunWorkspaceManager(tmp_path).ensure("safe")
    (workspace.conversations / "large.log").write_text("12345", encoding="utf-8")

    with pytest.raises(DashboardPathError, match="too large"):
        DashboardFilesystem(tmp_path, max_text_bytes=4).read_text(
            "safe", "conversations", "large.log"
        )
