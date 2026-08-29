"""Atomic application checkpoint storage independent of CrewAI internals."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from dbie.flows.state import PipelineState


class JsonCheckpointStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path_for(self, run_id: str) -> Path:
        return self.directory / run_id / "pipeline-state.json"

    def save(self, state: PipelineState) -> Path:
        path = self.path_for(state.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = state.model_dump_json(indent=2)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
        return path

    def load(self, run_id: str) -> PipelineState:
        return PipelineState.model_validate_json(
            self.path_for(run_id).read_text(encoding="utf-8")
        )
