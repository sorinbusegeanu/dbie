"""Safe, read-only access to dashboard-visible run artifacts."""

from __future__ import annotations

import json
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
    display_name: str
    artifact_type: str
    detail: str
    preview: str | None = None


@dataclass(frozen=True)
class DashboardFunnelStage:
    key: str
    label: str
    target: str
    actual: int | None


_FUNNEL_STAGES = (
    ("observed_signals", "Observed problems / signals", "500"),
    ("raw_ideas", "Raw business ideas", "250–500"),
    (
        "evidence_qualified",
        "Digital-only + evidence-qualified candidates",
        "50–100",
    ),
    ("assumption_validated", "Assumption-validated candidates", "15–25"),
    ("red_team_survivors", "Red-team survivors", "5–10"),
    ("experiment_candidates", "Experiment candidates", "3–5"),
    (
        "observed_market_evidence",
        "Observed market behavior / prototype evidence",
        "Required",
    ),
    (
        "ranked_recommendations",
        "Ranked BUILD / KILL / ITERATE recommendations",
        "3–5",
    ),
)

_CONVERSATION_LABELS = {
    "activity.log": "Run activity",
    "market_research_crew.log": "Market research crew",
    "market_research_summary.log": "Market research",
    "market_research_dialogue.log": "Market research crew",
    "ideation_crew.log": "Ideation crew",
    "ideation_summary.log": "Ideation",
    "ideation_dialogue.log": "Ideation crew",
    "evidence_validation_crew.log": "Evidence & validation crew",
    "evidence_validation_summary.log": "Evidence & validation",
    "evidence_validation_dialogue.log": "Evidence & validation crew",
    "red_team_crew.log": "Red-team crew",
    "red_team_summary.log": "Red-team",
    "red_team_dialogue.log": "Red-team crew",
    "portfolio_crew.log": "Portfolio decision crew",
    "portfolio_summary.log": "Portfolio decision",
    "portfolio_dialogue.log": "Portfolio decision crew",
}


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
            display_name, artifact_type, detail, preview = self._describe_file(
                resolved, kind
            )
            files.append(
                DashboardFile(
                    relative_path=relative,
                    name=candidate.name,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, UTC),
                    suffix=candidate.suffix.lower(),
                    display_name=display_name,
                    artifact_type=artifact_type,
                    detail=detail,
                    preview=preview,
                )
            )
        return sorted(files, key=lambda item: (item.relative_path.lower()))

    def read_funnel(self, run_id: str) -> list[DashboardFunnelStage]:
        actual: dict[str, int] = {}
        try:
            raw = self.read_text(run_id, "deliverables", "run-overview.json")
            payload = json.loads(raw)
            values = payload.get("funnel", {}) if isinstance(payload, dict) else {}
            if isinstance(values, dict):
                actual = {
                    key: value
                    for key, value in values.items()
                    if isinstance(key, str)
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                    and value >= 0
                }
        except (DashboardPathError, json.JSONDecodeError):
            pass
        return [
            DashboardFunnelStage(key, label, target, actual.get(key))
            for key, label, target in _FUNNEL_STAGES
        ]

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

    def _describe_file(
        self, path: Path, kind: str
    ) -> tuple[str, str, str, str | None]:
        if kind == "conversations":
            lines = self._read_display_lines(path)
            label = _CONVERSATION_LABELS.get(
                path.name, path.stem.replace("_", " ").replace("-", " ").title()
            )
            preview = next((line.strip() for line in reversed(lines) if line.strip()), None)
            if path.name.endswith("_dialogue.log"):
                artifact_type = "Actual CrewAI dialogue"
                detail = "Open the complete visible task, agent answer, and tool exchange"
            elif path.name == "activity.log":
                artifact_type = "Runtime activity"
                detail = "Stage lifecycle events"
            else:
                artifact_type = "Deterministic stage summary"
                detail = "No CrewAI dialogue was executed for this fixture"
            return (
                label,
                artifact_type,
                detail,
                preview,
            )

        if path.suffix.lower() == ".json":
            payload = self._read_json_object(path)
            title = payload.get("title") if payload else None
            decision = payload.get("decision") if payload else None
            artifact_marker = payload.get("artifact_type") if payload else None
            if artifact_marker == "run_overview":
                return "Run funnel and outcomes", "Run overview", "Current run counts", None
            if isinstance(title, str) and title.strip():
                detail = f"Recommendation: {decision}" if isinstance(decision, str) else "Structured dossier"
                return title.strip(), "Decision record", detail, None
            return path.stem.replace("_", " ").title(), "Structured data", "JSON", None

        if path.suffix.lower() == ".md":
            lines = self._read_display_lines(path)
            title = next(
                (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
                path.stem.replace("_", " ").title(),
            )
            decision = next(
                (
                    line.split("**", 2)[1]
                    for line in lines
                    if line.startswith("- Decision: **") and line.count("**") >= 2
                ),
                None,
            )
            detail = f"Recommendation: {decision}" if decision else "Human-readable analysis"
            return title, "Business case", detail, None

        return path.stem.replace("_", " ").title(), "File", path.suffix[1:].upper() or "Artifact", None

    def _read_display_lines(self, path: Path) -> list[str]:
        if path.stat().st_size > self.max_text_bytes:
            return []
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            return []

    def _read_json_object(self, path: Path) -> dict[str, object]:
        lines = self._read_display_lines(path)
        if not lines:
            return {}
        try:
            value = json.loads("\n".join(lines))
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _is_within(candidate: Path, parent: Path) -> bool:
        try:
            candidate.relative_to(parent)
            return True
        except ValueError:
            return False
