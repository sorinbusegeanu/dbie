"""In-process metrics plus optional local GPU telemetry."""

from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable
from time import monotonic
from typing import Any

from pydantic import BaseModel, Field


class MetricsSnapshot(BaseModel):
    counters: dict[str, int]
    latency_seconds: dict[str, float]
    gauges: dict[str, float]
    gpu: dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self.counters: Counter[str] = Counter()
        self.latencies: dict[str, float] = defaultdict(float)
        self.gauges: dict[str, float] = {}

    def increment(self, metric: str, value: int = 1, **labels: str) -> None:
        self.counters[_key(metric, labels)] += value

    def observe_latency(self, metric: str, seconds: float, **labels: str) -> None:
        self.latencies[_key(metric, labels)] += seconds

    def set_gauge(self, metric: str, value: float, **labels: str) -> None:
        self.gauges[_key(metric, labels)] = value

    def timed(self, metric: str, **labels: str) -> Callable[[], None]:
        started = monotonic()

        def finish() -> None:
            self.observe_latency(metric, monotonic() - started, **labels)

        return finish

    def snapshot(self, include_gpu: bool = False) -> MetricsSnapshot:
        return MetricsSnapshot(
            counters=dict(self.counters),
            latency_seconds=dict(self.latencies),
            gauges=dict(self.gauges),
            gpu=gpu_snapshot() if include_gpu else {},
        )


def _key(metric: str, labels: dict[str, str]) -> str:
    suffix = ",".join(f"{name}={labels[name]}" for name in sorted(labels))
    return f"{metric}{{{suffix}}}" if suffix else metric


def gpu_snapshot(
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    try:
        result = runner(
            [
                "nvidia-smi",
                "--query-gpu=index,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc)}
    if result.returncode != 0:
        return {"available": False, "error": result.stderr.strip()}
    devices = []
    for line in result.stdout.splitlines():
        index, used, total, utilization = [part.strip() for part in line.split(",")]
        devices.append(
            {
                "index": int(index),
                "memory_used_mb": int(used),
                "memory_total_mb": int(total),
                "utilization_percent": int(utilization),
            }
        )
    return {"available": True, "devices": devices}
