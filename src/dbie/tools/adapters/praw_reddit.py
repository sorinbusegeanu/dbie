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


class PrawRedditAdapter(ToolAdapter):
    name = "praw"
    capabilities = AdapterCapabilities(operations={"search_reddit"})

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def health(self) -> AdapterHealth:
        try:
            package_version = version("praw")
        except PackageNotFoundError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))
        if self.client is None:
            return AdapterHealth(
                name=self.name,
                available=False,
                version=package_version,
                detail="Reddit credentials/client not configured",
            )
        return AdapterHealth(name=self.name, available=True, version=package_version)

    def execute(self, request: AdapterRequest) -> AdapterResult:
        if self.client is None:
            raise RuntimeError("Reddit client not configured")
        started = datetime.now(UTC)
        arguments = request.arguments
        subreddit_names = arguments.get("subreddits") or ["all"]
        subreddit = self.client.subreddit("+".join(subreddit_names))
        posts: list[dict[str, object]] = []
        for submission in subreddit.search(
            arguments["query"],
            sort=str(arguments.get("sort", "relevance")).lower(),
            limit=int(arguments.get("max_threads", 20)),
        ):
            body = getattr(submission, "selftext", None)
            removed = body in {"[deleted]", "[removed]"}
            posts.append(
                {
                    "post_id": submission.id,
                    "subreddit": str(submission.subreddit),
                    "title": submission.title,
                    "body": None if removed else body,
                    "content_status": "REMOVED" if removed else "AVAILABLE",
                    "author": str(submission.author) if submission.author else None,
                    "score": submission.score,
                    "created_at": datetime.fromtimestamp(
                        submission.created_utc, UTC
                    ).isoformat(),
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "comments": [],
                }
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"threads": posts, "evidence_type": "OBSERVED_QUALITATIVE"},
            raw_sources=[
                {
                    "source_identifier": item["post_id"],
                    "source_url": item["permalink"],
                    "source_type": "reddit_thread",
                    "content_hash": document_hash(
                        f"{item['title']}\n{item['body'] or ''}".encode()
                    ),
                }
                for item in posts
            ],
            started_at=started,
            ended_at=ended,
            adapter_version=version("praw"),
        )
