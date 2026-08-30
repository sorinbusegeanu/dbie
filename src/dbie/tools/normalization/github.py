"""Provider-independent GitHub repository/activity records."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def repository_record(repository: Any) -> dict[str, object]:
    license_name = None
    if getattr(repository, "license", None):
        license_name = getattr(repository.license, "spdx_id", None)
    updated_at: datetime | None = getattr(repository, "updated_at", None)
    pushed_at: datetime | None = getattr(repository, "pushed_at", None)
    return {
        "full_name": repository.full_name,
        "url": repository.html_url,
        "description": repository.description,
        "stars": repository.stargazers_count,
        "forks": repository.forks_count,
        "watchers": repository.watchers_count,
        "open_issues": repository.open_issues_count,
        "archived": repository.archived,
        "license": license_name,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "pushed_at": pushed_at.isoformat() if pushed_at else None,
        "default_branch": getattr(repository, "default_branch", None),
    }
