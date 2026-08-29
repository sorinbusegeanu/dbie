from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash


class PyGithubAdapter(ToolAdapter):
    name = "pygithub"
    capabilities = AdapterCapabilities(operations={"search_github"})

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def health(self) -> AdapterHealth:
        try:
            package_version = version("PyGithub")
        except PackageNotFoundError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))
        return AdapterHealth(
            name=self.name,
            available=self.client is not None,
            version=package_version,
            detail=None if self.client else "GitHub client not configured",
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        if self.client is None:
            raise RuntimeError("GitHub client not configured")
        started = datetime.now(UTC)
        arguments = request.arguments
        mode = arguments.get("mode", "REPOSITORIES")
        if mode != "REPOSITORIES":
            raise ValueError(f"unsupported PyGithub mode: {mode}")
        query = str(arguments["query"])
        if arguments.get("language"):
            query += f" language:{arguments['language']}"
        repositories: list[dict[str, object]] = []
        for repository in self.client.search_repositories(query=query)[
            : int(arguments.get("max_results", 20))
        ]:
            license_name = None
            if getattr(repository, "license", None):
                license_name = getattr(repository.license, "spdx_id", None)
            repositories.append(
                {
                    "full_name": repository.full_name,
                    "url": repository.html_url,
                    "description": repository.description,
                    "stars": repository.stargazers_count,
                    "forks": repository.forks_count,
                    "watchers": repository.watchers_count,
                    "open_issues": repository.open_issues_count,
                    "archived": repository.archived,
                    "license": license_name,
                    "updated_at": repository.updated_at.isoformat()
                    if repository.updated_at
                    else None,
                }
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "repositories": repositories,
                "popularity_is_demand_evidence": False,
            },
            raw_sources=[
                {
                    "source_identifier": item["full_name"],
                    "source_url": item["url"],
                    "source_type": "github_repository",
                    "content_hash": document_hash(
                        f"{item['full_name']}\n{item['description'] or ''}\n"
                        f"{item['updated_at'] or ''}".encode()
                    ),
                }
                for item in repositories
            ],
            started_at=started,
            ended_at=ended,
            adapter_version=version("PyGithub"),
        )
