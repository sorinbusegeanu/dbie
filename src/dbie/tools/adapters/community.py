"""Credential-free community discovery with explicit evidence semantics.

Reddit search-index results are leads only.  This module never fetches Reddit
pages or its unofficial JSON endpoints.  Full qualitative signals come from
official Hacker News, Stack Exchange, and GitHub interfaces.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import UTC, datetime
from math import ceil
from typing import Any

import httpx

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.adapters.pygithub import PyGithubAdapter
from dbie.tools.adapters.searxng import SearXNGAdapter
from dbie.tools.normalization.documents import document_hash


_TAG_RE = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class StackExchangeCommunityAdapter(ToolAdapter):
    name = "stackexchange_community"
    platform = "STACK_EXCHANGE"
    capabilities = AdapterCapabilities(operations={"search_community"})

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        site: str = "stackoverflow",
    ) -> None:
        self.client = client or httpx.Client(
            base_url="https://api.stackexchange.com", timeout=30
        )
        self.site = site

    def health(self) -> AdapterHealth:
        try:
            response = self.client.get("/2.3/info", params={"site": self.site})
            response.raise_for_status()
            return AdapterHealth(name=self.name, available=True, version="2.3")
        except httpx.HTTPError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        arguments = request.arguments
        limit = int(arguments.get("max_results", 20))
        params: dict[str, Any] = {
            "site": self.site,
            "q": arguments["query"],
            "pagesize": limit,
            "order": "desc",
            "sort": {
                "RELEVANCE": "relevance",
                "NEW": "creation",
                "TOP": "votes",
            }.get(str(arguments.get("sort", "RELEVANCE")), "relevance"),
            "filter": "withbody",
        }
        if arguments.get("date_from"):
            params["fromdate"] = _date_timestamp(arguments["date_from"])
        response = self.client.get(
            "/2.3/search/advanced",
            params=params,
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        questions = raw.get("items", [])
        question_ids = [str(item["question_id"]) for item in questions]
        replies: dict[int, list[dict[str, Any]]] = defaultdict(list)
        sources: list[dict[str, Any]] = []
        if question_ids and arguments.get("include_replies", True):
            joined = ";".join(question_ids)
            for suffix, source_type in (
                ("answers", "stackexchange_answer"),
                ("comments", "stackexchange_comment"),
            ):
                child_response = self.client.get(
                    f"/2.3/questions/{joined}/{suffix}",
                    params={
                        "site": self.site,
                        "pagesize": min(100, limit * 5),
                        "order": "desc",
                        "sort": "votes" if suffix == "answers" else "creation",
                        "filter": "withbody",
                    },
                    timeout=request.timeout_seconds,
                )
                child_response.raise_for_status()
                for item in child_response.json().get("items", []):
                    question_id = int(item.get("question_id") or item.get("post_id"))
                    reply_id = str(item.get("answer_id") or item.get("comment_id"))
                    reply_url = item.get("link")
                    reply = {
                        "id": reply_id,
                        "type": suffix.removesuffix("s").upper(),
                        "body": _plain_text(item.get("body", "")),
                        "score": item.get("score"),
                        "created_at": _iso_timestamp(item.get("creation_date")),
                        "url": reply_url,
                    }
                    replies[question_id].append(reply)
                    sources.append(
                        _source(
                            f"stackexchange:{reply_id}",
                            reply_url,
                            source_type,
                            reply["body"],
                        )
                    )
        signals: list[dict[str, Any]] = []
        for item in questions:
            question_id = int(item["question_id"])
            title = _plain_text(item.get("title", ""))
            body = _plain_text(item.get("body", ""))
            url = item.get("link")
            signals.append(
                {
                    "id": f"stackexchange:{question_id}",
                    "platform": self.platform,
                    "title": title,
                    "body": body,
                    "score": item.get("score"),
                    "created_at": _iso_timestamp(item.get("creation_date")),
                    "url": url,
                    "tags": item.get("tags", []),
                    "replies": replies[question_id],
                    "evidence_strength": "OBSERVED_QUALITATIVE",
                }
            )
            sources.append(
                _source(
                    f"stackexchange:{question_id}",
                    url,
                    "stackexchange_question",
                    f"{title}\n{body}",
                )
            )
        warnings = ["STACKEXCHANGE_BACKOFF"] if raw.get("backoff") else []
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"signals": signals, "discovery_leads": []},
            raw_sources=sources,
            warnings=warnings,
            resource_usage={"quota_remaining": float(raw.get("quota_remaining", 0))},
            started_at=started,
            ended_at=ended,
            adapter_version="2.3",
        )


class HackerNewsCommunityAdapter(ToolAdapter):
    name = "hackernews_community"
    platform = "HACKER_NEWS"
    capabilities = AdapterCapabilities(operations={"search_community"})

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            base_url="https://hacker-news.firebaseio.com", timeout=30
        )

    def health(self) -> AdapterHealth:
        try:
            response = self.client.get("/v0/maxitem.json")
            response.raise_for_status()
            return AdapterHealth(name=self.name, available=True, version="v0")
        except httpx.HTTPError as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        arguments = request.arguments
        limit = int(arguments.get("max_results", 20))
        timeout = min(float(request.timeout_seconds), 15.0)
        feed_names = (
            ["newstories"]
            if str(arguments.get("sort", "RELEVANCE")) == "NEW"
            else ["askstories", "newstories"]
        )
        item_ids: list[int] = []
        for feed_name in feed_names:
            response = self.client.get(f"/v0/{feed_name}.json", timeout=timeout)
            response.raise_for_status()
            item_ids.extend(response.json() or [])
        scan_limit = min(100, max(40, limit * 10))
        seen: set[int] = set()
        signals: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        for item_id in item_ids:
            if item_id in seen or len(seen) >= scan_limit or len(signals) >= limit:
                continue
            seen.add(item_id)
            response = self.client.get(f"/v0/item/{item_id}.json", timeout=timeout)
            response.raise_for_status()
            item = response.json() or {}
            title = _plain_text(item.get("title", ""))
            body = _plain_text(item.get("text", ""))
            if not _query_matches(str(arguments["query"]), f"{title} {body}"):
                continue
            url = f"https://news.ycombinator.com/item?id={item_id}"
            replies: list[dict[str, Any]] = []
            if arguments.get("include_replies", True):
                for child_id in (item.get("kids") or [])[:10]:
                    child_response = self.client.get(
                        f"/v0/item/{child_id}.json", timeout=timeout
                    )
                    child_response.raise_for_status()
                    child = child_response.json() or {}
                    if child.get("deleted") or child.get("dead"):
                        continue
                    child_body = _plain_text(child.get("text", ""))
                    child_url = (
                        f"https://news.ycombinator.com/item?id={child_id}"
                    )
                    replies.append(
                        {
                            "id": f"hn:{child_id}",
                            "type": "COMMENT",
                            "body": child_body,
                            "created_at": _iso_timestamp(child.get("time")),
                            "url": child_url,
                        }
                    )
                    sources.append(
                        _source(
                            f"hn:{child_id}",
                            child_url,
                            "hackernews_comment",
                            child_body,
                        )
                    )
            signals.append(
                {
                    "id": f"hn:{item_id}",
                    "platform": self.platform,
                    "title": title,
                    "body": body,
                    "score": item.get("score"),
                    "created_at": _iso_timestamp(item.get("time")),
                    "url": url,
                    "external_url": item.get("url"),
                    "replies": replies,
                    "evidence_strength": "OBSERVED_QUALITATIVE",
                }
            )
            sources.append(
                _source(
                    f"hn:{item_id}",
                    url,
                    "hackernews_thread",
                    f"{title}\n{body}",
                )
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"signals": signals, "discovery_leads": []},
            raw_sources=sources,
            resource_usage={"items_scanned": float(len(seen))},
            started_at=started,
            ended_at=ended,
            adapter_version="v0",
        )


class GitHubCommunityAdapter(ToolAdapter):
    name = "github_community"
    platform = "GITHUB"
    capabilities = AdapterCapabilities(operations={"search_community"})

    def __init__(self, github: PyGithubAdapter) -> None:
        self.github = github

    def health(self) -> AdapterHealth:
        status = self.github.health()
        return AdapterHealth(
            name=self.name,
            available=status.available,
            version=status.version,
            detail=status.detail,
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        raw = self.github.execute(
            AdapterRequest(
                operation="search_github",
                arguments={
                    "query": request.arguments["query"],
                    "mode": "ISSUES",
                    "max_results": request.arguments.get("max_results", 20),
                    "include_comments": request.arguments.get(
                        "include_replies", True
                    ),
                },
                timeout_seconds=request.timeout_seconds,
            )
        )
        signals = []
        for item in raw.payload.get("issues", []):
            created_at = item.get("created_at")
            if request.arguments.get("date_from") and created_at:
                if created_at[:10] < str(request.arguments["date_from"]):
                    continue
            signals.append(
                {
                    "id": f"github:{item['id']}",
                    "platform": self.platform,
                    "title": item.get("title", ""),
                    "body": item.get("body", ""),
                    "score": item.get("reactions", 0),
                    "created_at": created_at,
                    "url": item.get("url"),
                    "repository_url": item.get("repository_url"),
                    "replies": item.get("replies", []),
                    "kind": item.get("kind", "ISSUE"),
                    "evidence_strength": "OBSERVED_QUALITATIVE",
                }
            )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"signals": signals, "discovery_leads": []},
            raw_sources=raw.raw_sources,
            warnings=raw.warnings,
            resource_usage=raw.resource_usage,
            started_at=started,
            ended_at=ended,
            adapter_version=raw.adapter_version,
        )


class SearchIndexLeadAdapter(ToolAdapter):
    """Find Reddit and GitHub Discussion URLs without fetching their pages."""

    name = "community_search_index"
    platform = "REDDIT_INDEX"
    capabilities = AdapterCapabilities(operations={"search_community"})

    def __init__(self, search: SearXNGAdapter) -> None:
        self.search = search

    def health(self) -> AdapterHealth:
        status = self.search.health()
        return AdapterHealth(
            name=self.name,
            available=status.available,
            version=status.version,
            detail=(
                "discovery-only; Reddit pages are never automatically fetched"
                if status.available
                else status.detail
            ),
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        limit = int(request.arguments.get("max_results", 20))
        leads: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        selected = set(request.arguments.get("platforms") or [])
        queries = []
        if not selected or "REDDIT_INDEX" in selected:
            queries.append(
                ("REDDIT_INDEX", f"site:reddit.com {request.arguments['query']}")
            )
        if not selected or "GITHUB" in selected:
            queries.append(
                (
                    "GITHUB_DISCUSSION_INDEX",
                    f"site:github.com inurl:discussions {request.arguments['query']}",
                )
            )
        per_query = max(1, ceil(limit / max(1, len(queries))))
        for platform, query in queries:
            raw = self.search.execute(
                AdapterRequest(
                    operation="web_search",
                    arguments={"query": query, "max_results": per_query},
                    timeout_seconds=request.timeout_seconds,
                )
            )
            for item in raw.payload.get("results", []):
                url = item.get("canonical_url") or item.get("url")
                lead = {
                    "id": f"search-index:{document_hash(str(url).encode())[:16]}",
                    "platform": platform,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": url,
                    "evidence_strength": "DISCOVERY_LEAD",
                    "requires_corroboration": True,
                    "automatically_fetched": False,
                }
                leads.append(lead)
                sources.append(
                    _source(
                        lead["id"],
                        url,
                        "search_index_lead",
                        f"{lead['title']}\n{lead['snippet']}",
                    )
                )
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"signals": [], "discovery_leads": leads[:limit]},
            raw_sources=sources[:limit],
            warnings=["SEARCH_INDEX_SNIPPETS_ARE_NOT_EVIDENCE"],
            started_at=started,
            ended_at=ended,
        )


class CommunitySearchAdapter(ToolAdapter):
    name = "community_search"
    capabilities = AdapterCapabilities(operations={"search_community"})

    def __init__(self, providers: list[ToolAdapter]) -> None:
        self.providers = providers

    def health(self) -> AdapterHealth:
        statuses = [provider.health() for provider in self.providers]
        evidence_names = {
            "stackexchange_community",
            "hackernews_community",
            "github_community",
        }
        available_evidence = sum(
            status.available and status.name in evidence_names for status in statuses
        )
        detail = ", ".join(
            f"{status.name}={'up' if status.available else 'down'}"
            for status in statuses
        )
        return AdapterHealth(
            name=self.name,
            available=available_evidence >= 2,
            detail=f"{detail}; Reddit index is discovery-only",
        )

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        requested = set(request.arguments.get("platforms") or [])
        limit = int(request.arguments.get("max_results", 20))
        selected = [
            provider
            for provider in self.providers
            if not requested
            or getattr(provider, "platform", None) in requested
            or (
                isinstance(provider, SearchIndexLeadAdapter)
                and bool(requested & {"REDDIT_INDEX", "GITHUB"})
            )
        ]
        per_provider = max(1, ceil(limit / max(1, len(selected))))
        signals: list[dict[str, Any]] = []
        leads: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        warnings: list[str] = []
        attempts: list[str] = []
        for provider in selected:
            status = provider.health()
            if not status.available:
                warnings.append(f"{provider.name.upper()}_UNAVAILABLE")
                attempts.append(f"{provider.name}:UNAVAILABLE")
                continue
            provider_request = request.model_copy(
                update={
                    "arguments": {
                        **request.arguments,
                        "max_results": per_provider,
                    }
                }
            )
            try:
                result = provider.execute(provider_request)
            except Exception:  # noqa: BLE001 - degrade one source, preserve others
                warnings.append(f"{provider.name.upper()}_FAILED")
                attempts.append(f"{provider.name}:ERROR")
                continue
            signals.extend(result.payload.get("signals", []))
            leads.extend(result.payload.get("discovery_leads", []))
            sources.extend(result.raw_sources)
            warnings.extend(result.warnings)
            attempts.append(f"{provider.name}:USED")
        if not signals and not leads:
            raise RuntimeError(f"all community providers failed: {attempts}")
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "signals": signals[:limit],
                "discovery_leads": leads[:limit],
                "evidence_type": "MIXED_COMMUNITY_SIGNALS",
                "reddit_content_automatically_fetched": False,
            },
            raw_sources=sources,
            warnings=sorted(set(warnings)),
            attempts=attempts,
            started_at=started,
            ended_at=ended,
        )


def _plain_text(value: Any) -> str:
    decoded = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", decoded)).strip()


def _date_timestamp(value: Any) -> int:
    return int(datetime.fromisoformat(str(value)).replace(tzinfo=UTC).timestamp())


def _iso_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), UTC).isoformat()


def _query_matches(query: str, text: str) -> bool:
    needles = {token for token in _TOKEN_RE.findall(query.lower()) if len(token) > 2}
    if not needles:
        return query.lower() in text.lower()
    haystack = set(_TOKEN_RE.findall(text.lower()))
    return bool(needles & haystack)


def _source(
    identifier: str,
    url: str | None,
    source_type: str,
    content: str,
) -> dict[str, Any]:
    return {
        "source_identifier": identifier,
        "source_url": url,
        "source_type": source_type,
        "content_hash": document_hash(content.encode()),
    }
