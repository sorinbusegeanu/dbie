from datetime import UTC, datetime
from types import SimpleNamespace

import httpx

from dbie.persistence.db import Database
from dbie.persistence.vector import DeterministicEmbeddingService
from dbie.tools.adapters.base import AdapterRequest
from dbie.tools.adapters.community import (
    CommunitySearchAdapter,
    GitHubCommunityAdapter,
    HackerNewsCommunityAdapter,
    SearchIndexLeadAdapter,
    StackExchangeCommunityAdapter,
)
from dbie.tools.adapters.pygithub import PyGithubAdapter
from dbie.tools.adapters.searxng import SearXNGAdapter
from dbie.tools.contracts import ToolName
from dbie.tools.oss_local import build_oss_gateway


def request(**arguments) -> AdapterRequest:
    return AdapterRequest(
        operation="search_community",
        arguments={"query": "automation", **arguments},
        timeout_seconds=10,
    )


def test_stackexchange_returns_questions_replies_and_primary_provenance() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        path = http_request.url.path
        if path == "/2.3/search/advanced":
            return httpx.Response(
                200,
                json={
                    "quota_remaining": 299,
                    "items": [
                        {
                            "question_id": 11,
                            "title": "&lt;b&gt;Automation&lt;/b&gt; problem",
                            "body": "<p>A repeated manual workflow</p>",
                            "score": 4,
                            "creation_date": 1,
                            "link": "https://stackoverflow.com/q/11",
                            "tags": ["automation"],
                        }
                    ],
                },
            )
        if path.endswith("/answers"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "question_id": 11,
                            "answer_id": 12,
                            "body": "<p>Automate it safely</p>",
                            "score": 2,
                            "creation_date": 2,
                            "link": "https://stackoverflow.com/a/12",
                        }
                    ]
                },
            )
        if path.endswith("/comments"):
            return httpx.Response(200, json={"items": []})
        raise AssertionError(path)

    adapter = StackExchangeCommunityAdapter(
        httpx.Client(
            base_url="https://api.stackexchange.test",
            transport=httpx.MockTransport(handler),
        )
    )

    result = adapter.execute(request())

    signal = result.payload["signals"][0]
    assert signal["title"] == "Automation problem"
    assert signal["body"] == "A repeated manual workflow"
    assert signal["replies"][0]["body"] == "Automate it safely"
    assert signal["evidence_strength"] == "OBSERVED_QUALITATIVE"
    assert {source["source_type"] for source in result.raw_sources} == {
        "stackexchange_question",
        "stackexchange_answer",
    }


def test_hackernews_filters_official_feed_and_preserves_comment_lineage() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        path = http_request.url.path
        values = {
            "/v0/askstories.json": [1],
            "/v0/newstories.json": [1, 2],
            "/v0/item/1.json": {
                "id": 1,
                "title": "Ask HN: automation is painful",
                "text": "We repeat this workflow daily",
                "score": 9,
                "time": 1,
                "kids": [3],
            },
            "/v0/item/3.json": {
                "id": 3,
                "text": "The workaround takes two hours",
                "time": 2,
            },
        }
        if path not in values:
            raise AssertionError(path)
        return httpx.Response(200, json=values[path])

    adapter = HackerNewsCommunityAdapter(
        httpx.Client(
            base_url="https://hacker-news.test",
            transport=httpx.MockTransport(handler),
        )
    )

    result = adapter.execute(request(max_results=1))

    signal = result.payload["signals"][0]
    assert signal["platform"] == "HACKER_NEWS"
    assert signal["replies"][0]["id"] == "hn:3"
    assert {source["source_type"] for source in result.raw_sources} == {
        "hackernews_thread",
        "hackernews_comment",
    }


def test_github_issues_are_normalized_as_qualitative_community_signals() -> None:
    comment = SimpleNamespace(
        id=8,
        body="We also hit this limitation",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        html_url="https://github.com/acme/project/issues/7#issuecomment-8",
    )
    issue = SimpleNamespace(
        id=7,
        number=7,
        title="Manual automation setup",
        body="Every customer needs the same workaround",
        html_url="https://github.com/acme/project/issues/7",
        state="open",
        comments=1,
        get_comments=lambda: [comment],
        raw_data={"reactions": {"total_count": 3}},
        pull_request=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        repository_url="https://api.github.com/repos/acme/project",
    )
    github = PyGithubAdapter(
        SimpleNamespace(search_issues=lambda **kwargs: [issue])
    )

    result = GitHubCommunityAdapter(github).execute(request())

    signal = result.payload["signals"][0]
    assert signal["platform"] == "GITHUB"
    assert signal["body"] == "Every customer needs the same workaround"
    assert signal["replies"][0]["id"] == "8"
    assert signal["score"] == 3


def test_reddit_search_results_are_leads_and_are_never_fetched() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url.path == "/search"
        assert "site:reddit.com" in http_request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://www.reddit.com/r/ops/comments/abc/pain/",
                        "title": "Repeated operator pain",
                        "content": "Search-index snippet only",
                        "engines": ["example"],
                    }
                ]
            },
        )

    searxng = SearXNGAdapter(
        "http://searx.test",
        httpx.Client(
            base_url="http://searx.test",
            transport=httpx.MockTransport(handler),
        ),
    )
    adapter = SearchIndexLeadAdapter(searxng)

    result = adapter.execute(request(platforms=["REDDIT_INDEX"]))

    lead = result.payload["discovery_leads"][0]
    assert lead["evidence_strength"] == "DISCOVERY_LEAD"
    assert lead["requires_corroboration"] is True
    assert lead["automatically_fetched"] is False
    assert result.payload["signals"] == []
    assert "SEARCH_INDEX_SNIPPETS_ARE_NOT_EVIDENCE" in result.warnings


def test_oss_gateway_exposes_community_search_in_the_ten_tool_surface(
    tmp_path,
) -> None:
    database = Database(f"sqlite:///{tmp_path / 'community.sqlite3'}")
    database.initialize()
    gateway = build_oss_gateway(
        database=database,
        embeddings=DeterministicEmbeddingService(),
        tools_config={
            "actor_permissions": {},
            "adapter_endpoints": {
                "searxng": "http://127.0.0.1:1",
                "crawl4ai": "http://127.0.0.1:1",
            },
        },
    )

    assert len(gateway.routes) == 10
    assert ToolName.SEARCH_COMMUNITY in gateway.routes
    assert gateway.routes[ToolName.SEARCH_COMMUNITY] == CommunitySearchAdapter.name
