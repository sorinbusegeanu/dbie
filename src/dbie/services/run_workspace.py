"""Filesystem contract shared by run producers and the read-only dashboard."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CONVERSATION_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.log$")


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    conversations: Path
    deliverables: Path


class RunWorkspaceManager:
    """Creates the only filesystem surface consumed by the dashboard."""

    def __init__(self, runs_directory: Path) -> None:
        self.runs_directory = Path(runs_directory)

    def ensure(self, run_id: str, *, make_current: bool = True) -> RunWorkspace:
        if not _RUN_ID.fullmatch(run_id) or run_id in {".", "..", "current"}:
            raise ValueError("run_id must be a safe filesystem name")
        root = self.runs_directory / run_id
        conversations = root / "conversations"
        deliverables = root / "deliverables"
        conversations.mkdir(parents=True, exist_ok=True)
        deliverables.mkdir(parents=True, exist_ok=True)
        if make_current:
            self._point_current_to(run_id)
        return RunWorkspace(root, conversations, deliverables)

    def append_activity(self, run_id: str, message: str) -> Path:
        """Append a visible runtime event; never accepts hidden model reasoning."""
        return self.append_visible_output(run_id, "activity.log", message)

    def append_visible_output(
        self, run_id: str, filename: str, message: str
    ) -> Path:
        """Persist only explicitly supplied, CrewAI-visible execution output."""
        if not _CONVERSATION_FILE.fullmatch(filename):
            raise ValueError("conversation filename must be a safe .log basename")
        workspace = self.ensure(run_id)
        path = workspace.conversations / filename
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        with path.open("a", encoding="utf-8") as stream:
            for line in message.rstrip().splitlines() or [""]:
                stream.write(f"[{timestamp}] {line}\n")
        return path

    def _point_current_to(self, run_id: str) -> None:
        self.runs_directory.mkdir(parents=True, exist_ok=True)
        current = self.runs_directory / "current"
        if current.exists() and not current.is_symlink():
            return
        temporary = self.runs_directory / f".current-{uuid4().hex}"
        temporary.symlink_to(run_id, target_is_directory=True)
        try:
            os.replace(temporary, current)
        finally:
            temporary.unlink(missing_ok=True)
