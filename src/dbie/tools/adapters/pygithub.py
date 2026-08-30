from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from itertools import islice
from typing import Any

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash
from dbie.tools.normalization.github import repository_record


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
        query = str(arguments["query"])
        if arguments.get("language"):
            query += f" language:{arguments['language']}"
        repositories: list[dict[str, object]] = []
        issues: list[dict[str, object]] = []
        code_results: list[dict[str, object]] = []
        limit = int(arguments.get("max_results", 20))
        if mode in {"REPOSITORIES", "TOPICS"}:
            if mode == "TOPICS":
                query = f"topic:{query}"
            for repository in islice(
                self.client.search_repositories(query=query), limit
            ):
                record = repository_record(repository)
                releases = []
                get_releases = getattr(repository, "get_releases", None)
                if callable(get_releases):
                    for release in islice(get_releases(), 5):
                        releases.append(
                            {
                                "tag": release.tag_name,
                                "name": release.title,
                                "url": release.html_url,
                                "published_at": release.published_at.isoformat()
                                if release.published_at
                                else None,
                                "draft": release.draft,
                                "prerelease": release.prerelease,
                            }
                        )
                record["releases"] = releases
                repositories.append(record)
        elif mode == "ISSUES":
            for issue in islice(self.client.search_issues(query=query), limit):
                replies = []
                get_comments = getattr(issue, "get_comments", None)
                if arguments.get("include_comments", True) and callable(get_comments):
                    for comment in islice(get_comments(), 20):
                        replies.append(
                            {
                                "id": str(comment.id),
                                "type": "COMMENT",
                                "body": getattr(comment, "body", "") or "",
                                "created_at": comment.created_at.isoformat()
                                if getattr(comment, "created_at", None)
                                else None,
                                "url": getattr(comment, "html_url", None),
                            }
                        )
                raw_data = getattr(issue, "raw_data", {}) or {}
                issues.append(
                    {
                        "id": issue.id,
                        "number": issue.number,
                        "title": issue.title,
                        "body": getattr(issue, "body", "") or "",
                        "url": issue.html_url,
                        "state": issue.state,
                        "comments": issue.comments,
                        "replies": replies,
                        "reactions": (
                            raw_data.get("reactions", {}).get("total_count", 0)
                        ),
                        "kind": (
                            "PULL_REQUEST"
                            if getattr(issue, "pull_request", None)
                            else "ISSUE"
                        ),
                        "created_at": issue.created_at.isoformat(),
                        "updated_at": issue.updated_at.isoformat(),
                        "repository_url": getattr(issue, "repository_url", None),
                    }
                )
        elif mode == "CODE":
            for item in islice(self.client.search_code(query=query), limit):
                code_results.append(
                    {
                        "name": item.name,
                        "path": item.path,
                        "url": item.html_url,
                        "repository": item.repository.full_name,
                        "sha": item.sha,
                    }
                )
        else:
            raise ValueError(f"unsupported PyGithub mode: {mode}")
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "repositories": repositories,
                "issues": issues,
                "code_results": code_results,
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
            ]
            + [
                {
                    "source_identifier": str(item["id"]),
                    "source_url": item["url"],
                    "source_type": "github_issue",
                    "content_hash": document_hash(
                        f"{item['title']}\n{item['updated_at']}".encode()
                    ),
                }
                for item in issues
            ]
            + [
                {
                    "source_identifier": f"{item['repository']}:{item['path']}",
                    "source_url": item["url"],
                    "source_type": "github_code",
                    "content_hash": document_hash(
                        f"{item['repository']}\n{item['path']}\n{item['sha']}".encode()
                    ),
                }
                for item in code_results
            ],
            started_at=started,
            ended_at=ended,
            adapter_version=version("PyGithub"),
        )
