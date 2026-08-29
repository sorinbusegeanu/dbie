from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from dbie.config import Settings
from dbie.domain.enums import RunStatus
from dbie.domain.models import Run, new_id
from dbie.persistence.repositories import RunRepository
from dbie.services.run_workspace import RunWorkspaceManager


class RunService:
    def __init__(self, repository: RunRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def create(self, mandate: str) -> Run:
        identifier = new_id()
        run = Run(
            id=identifier,
            run_id=identifier,
            mandate=mandate,
            status=RunStatus.CREATED,
            configuration_hash=self._configuration_hash(),
        )
        persisted = self.repository.create(run)
        RunWorkspaceManager(self.settings.run_directory).ensure(identifier)
        return persisted

    def resume(self, run_id: str) -> Run:
        return self.repository.set_status(run_id, RunStatus.RUNNING)

    def checkpoint(self, run_id: str) -> Run:
        return self.repository.set_status(run_id, RunStatus.CHECKPOINTED)

    def close(self, run_id: str) -> Run:
        return self.repository.set_status(run_id, RunStatus.COMPLETED)

    def _configuration_hash(self) -> str:
        paths = (
            self.settings.models_config,
            self.settings.tools_config,
            self.settings.policies_config,
        )
        digest = sha256()
        for path in paths:
            value = Path(path)
            digest.update(value.as_posix().encode())
            digest.update(value.read_bytes())
        return digest.hexdigest()
