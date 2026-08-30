"""Aggregate adapter readiness without exposing provider details to agents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from dbie.tools.adapters.base import AdapterHealth
from dbie.tools.adapters.registry import AdapterRegistry


class AdapterHealthReport(BaseModel):
    ready: bool
    required: dict[str, AdapterHealth]
    optional: dict[str, AdapterHealth] = Field(default_factory=dict)


def adapter_health_report(
    registry: AdapterRegistry,
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> AdapterHealthReport:
    optional = optional or set()
    required_status = {name: registry.get(name).health() for name in sorted(required)}
    optional_status = {name: registry.get(name).health() for name in sorted(optional)}
    return AdapterHealthReport(
        ready=all(item.available for item in required_status.values()),
        required=required_status,
        optional=optional_status,
    )
