"""Safe, read-only access to dashboard-visible run artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_KINDS = frozenset({"conversations", "deliverables"})


class DashboardPathError(ValueError):
    """The requested path is outside the dashboard's public filesystem."""


@dataclass(frozen=True)
class DashboardRun:
    run_id: str
    modified_at: datetime
    is_current: bool


@dataclass(frozen=True)
class DashboardFile:
    relative_path: str
    name: str
    size: int
    modified_at: datetime
    suffix: str


class DashboardFilesystem:
    def __init__(
        self,
        runs_directory: Path,
        *,
        current_name: str = "current",
        max_text_bytes: int = 5_000_000,
    ) -> None:
        self.runs_directory = Path(runs_directory)
        self.current_name = current_name
        self.max_text_bytes = max_text_bytes

    def list_runs(self) -> list[DashboardRun]:
        if not self.runs_directory.is_dir():
            return []
        current = self.current_run_id()
        runs: list[DashboardRun] = []
        for candidate in self.runs_directory.iterdir():
            if candidate.name == self.current_name or candidate.is_symlink():
                continue
            if not candidate.is_dir() or not _RUN_ID.fullmatch(candidate.name):
                continue
            resolved = candidate.resolve()
            if not self._is_within(resolved, self.runs_directory.resolve()):
                continue
            stat = resolved.stat()
            runs.append(
                DashboardRun(
                    run_id=candidate.name,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, UTC),
                    is_current=candidate.name == current,
                )
            )
        return sorted(runs, key=lambda item: item.modified_at, reverse=True)

    def current_run_id(self) -> str | None:
        current = self.runs_directory / self.current_name
        if current.exists() or current.is_symlink():
            try:
                resolved = current.resolve(strict=True)
            except (OSError, RuntimeError):
                resolved = None
            if (
                resolved is not None
                and resolved.is_dir()
                and self._is_within(resolved, self.runs_directory.resolve())
                and resolved.parent == self.runs_directory.resolve()
                and _RUN_ID.fullmatch(resolved.name)
            ):
                return resolved.name
        newest = self.list_runs_without_current()
        return newest[0].run_id if newest else None

    def list_runs_without_current(self) -> list[DashboardRun]:
        """List runs without recursively resolving the current alias."""
        if not self.runs_directory.is_dir():
            return []
        runs: list[DashboardRun] = []
        root = self.runs_directory.resolve()
        for candidate in self.runs_directory.iterdir():
            if (
                candidate.name == self.current_name
                or candidate.is_symlink()
                or not candidate.is_dir()
                or not _RUN_ID.fullmatch(candidate.name)
            ):
                continue
            resolved = candidate.resolve()
            if not self._is_within(resolved, root):
                continue
            stat = resolved.stat()
            runs.append(
                DashboardRun(
                    candidate.name,
                    datetime.fromtimestamp(stat.st_mtime, UTC),
                    False,
                )
            )
        return sorted(runs, key=lambda item: item.modified_at, reverse=True)

    def resolve_run(self, run_id: str) -> Path:
        if not _RUN_ID.fullmatch(run_id) or run_id in {".", "..", self.current_name}:
            raise DashboardPathError("unknown run")
        root = self.runs_directory.resolve()
        candidate = self.runs_directory / run_id
        if candidate.is_symlink():
            raise DashboardPathError("unknown run")
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DashboardPathError("unknown run") from exc
        if (
            not resolved.is_dir()
            or resolved.parent != root
            or not self._is_within(resolved, root)
        ):
            raise DashboardPathError("unknown run")
        return resolved

    def list_files(self, run_id: str, kind: str) -> list[DashboardFile]:
        directory = self._kind_directory(run_id, kind)
        if not directory.is_dir():
            return []
        files: list[DashboardFile] = []
        for candidate in directory.rglob("*"):
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if (
                not resolved.is_file()
                or not self._is_within(resolved, directory.resolve())
            ):
                continue
            stat = resolved.stat()
            relative = candidate.relative_to(directory).as_posix()
            files.append(
                DashboardFile(
                    relative_path=relative,
                    name=candidate.name,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, UTC),
                    suffix=candidate.suffix.lower(),
                )
            )
        return sorted(files, key=lambda item: (item.relative_path.lower()))

    def resolve_file(self, run_id: str, kind: str, relative_path: str) -> Path:
        directory = self._kind_directory(run_id, kind)
        logical = PurePosixPath(relative_path)
        if (
            not relative_path
            or logical.is_absolute()
            or any(part in {"", ".", ".."} for part in logical.parts)
        ):
            raise DashboardPathError("unknown file")
        candidate = directory.joinpath(*logical.parts)
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DashboardPathError("unknown file") from exc
        if not resolved.is_file() or not self._is_within(resolved, directory.resolve()):
            raise DashboardPathError("unknown file")
        return resolved

    def read_text(self, run_id: str, kind: str, relative_path: str) -> str:
        path = self.resolve_file(run_id, kind, relative_path)
        if path.stat().st_size > self.max_text_bytes:
            raise DashboardPathError("file is too large to render")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DashboardPathError("file is not UTF-8 text") from exc

    def _kind_directory(self, run_id: str, kind: str) -> Path:
        if kind not in _KINDS:
            raise DashboardPathError("unknown artifact kind")
        run = self.resolve_run(run_id)
        directory = run / kind
        if directory.exists():
            resolved = directory.resolve()
            if not self._is_within(resolved, run):
                raise DashboardPathError("unknown artifact kind")
            return resolved
        return directory

    @staticmethod
    def _is_within(candidate: Path, parent: Path) -> bool:
        try:
            candidate.relative_to(parent)
            return True
        except ValueError:
            return False
