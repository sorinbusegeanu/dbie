from __future__ import annotations

import subprocess
from collections.abc import Callable
from datetime import UTC, datetime

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


class DockerPythonAdapter(ToolAdapter):
    name = "docker_python"
    capabilities = AdapterCapabilities(
        operations={"python_execute"}, side_effect_free=True
    )

    def __init__(
        self,
        *,
        image: str = "python:3.12-slim",
        memory_mb: int = 512,
        cpus: float = 1.0,
        max_output_bytes: int = 100_000,
        runner: Runner = subprocess.run,
    ) -> None:
        self.image = image
        self.memory_mb = memory_mb
        self.cpus = cpus
        self.max_output_bytes = max_output_bytes
        self.runner = runner

    def health(self) -> AdapterHealth:
        try:
            result = self.runner(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return AdapterHealth(
                name=self.name,
                available=result.returncode == 0,
                version=result.stdout.strip() or None,
                detail=result.stderr.strip() or None,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def command(self) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--interactive",
            "--network",
            "none",
            "--read-only",
            "--user",
            "65532:65532",
            "--cap-drop",
            "ALL",
            "--memory",
            f"{self.memory_mb}m",
            "--cpus",
            str(self.cpus),
            "--pids-limit",
            "64",
            "--ulimit",
            "nofile=256:256",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            self.image,
            "python",
            "-I",
            "-",
        ]

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        result = self.runner(
            self.command(),
            input=str(request.arguments["code"]),
            capture_output=True,
            text=True,
            timeout=request.timeout_seconds,
            check=False,
        )
        stdout = result.stdout[: self.max_output_bytes]
        stderr = result.stderr[: self.max_output_bytes]
        warnings = []
        if (
            len(result.stdout) > self.max_output_bytes
            or len(result.stderr) > self.max_output_bytes
        ):
            warnings.append("OUTPUT_TRUNCATED")
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
                "image": self.image,
                "network": False,
            },
            warnings=warnings,
            started_at=started,
            ended_at=ended,
        )
