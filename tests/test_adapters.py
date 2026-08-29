import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from dbie.persistence.db import Database
from dbie.persistence.vector import DeterministicEmbeddingService
from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.adapters.crawl4ai import Crawl4AIAdapter
from dbie.tools.adapters.docker_python import DockerPythonAdapter
from dbie.tools.adapters.docling import DoclingAdapter
from dbie.tools.adapters.embeddings import FastEmbedBGEEmbeddingService
from dbie.tools.adapters.playwright import PlaywrightAdapter
from dbie.tools.adapters.praw_reddit import PrawRedditAdapter
from dbie.tools.adapters.pygithub import PyGithubAdapter
from dbie.tools.adapters.pymupdf import PyMuPDFAdapter
from dbie.tools.adapters.regulations.eurlex import EurLexAdapter
from dbie.tools.adapters.searxng import SearXNGAdapter
from dbie.tools.adapters.sqlalchemy_db import SQLAlchemyDatabaseAdapter
from dbie.tools.adapters.trafilatura import TrafilaturaAdapter
from dbie.tools.contracts import ToolName
from dbie.tools.normalization.companies import identity, resolve_company_identity
from dbie.tools.normalization.web import canonicalize_url
from dbie.tools.oss_local import build_oss_gateway
from dbie.tools.routing.fetch_page_router import FetchPageRouter


def adapter_request(operation: str, arguments: dict[str, object]) -> AdapterRequest:
    return AdapterRequest(operation=operation, arguments=arguments, timeout_seconds=5)


def test_searxng_normalizes_and_deduplicates_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "json"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://Example.test/article?utm_source=x",
                        "title": "First",
                        "content": "snippet",
                        "engines": ["duckduckgo"],
                    },
                    {
                        "url": "https://example.test/article",
                        "title": "Duplicate",
                        "content": "same",
                    },
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://searxng.test"
    )
    adapter = SearXNGAdapter("http://searxng.test", client)

    result = adapter.execute(adapter_request("web_search", {"query": "pain"}))

    assert len(result.payload["results"]) == 1
    assert result.payload["results"][0]["canonical_url"] == (
        "https://example.test/article"
    )
    assert result.payload["snippets_are_evidence"] is False


def test_trafilatura_static_extraction_does_not_need_browser() -> None:
    html = "<html><body>" + ("useful article text " * 30) + "</body></html>"
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=html)),
    )
    adapter = TrafilaturaAdapter(client=client, extractor=lambda html, **kwargs: html)

    result = adapter.execute(
        adapter_request("fetch_page", {"url": "https://example.test/article"})
    )

    assert result.payload["quality"]["meaningful"] is True
    assert result.resource_usage["bytes"] > 0


def test_crawl4ai_service_contract_extracts_markdown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/crawl"
        return httpx.Response(
            200,
            json={"results": [{"markdown": "useful text " * 30, "links": []}]},
        )

    adapter = Crawl4AIAdapter(
        "http://crawl.test",
        httpx.Client(
            transport=httpx.MockTransport(handler), base_url="http://crawl.test"
        ),
    )
    result = adapter.execute(
        adapter_request("fetch_page", {"url": "https://example.test"})
    )
    assert result.payload["quality"]["meaningful"] is True


class RoutingAdapter(ToolAdapter):
    capabilities = AdapterCapabilities(operations={"fetch_page"})

    def __init__(self, name: str, meaningful: bool) -> None:
        self.name = name
        self.meaningful = meaningful
        self.calls = 0

    def health(self) -> AdapterHealth:
        return AdapterHealth(name=self.name, available=True)

    def execute(self, request: AdapterRequest) -> AdapterResult:
        self.calls += 1
        return AdapterResult(
            payload={
                "content": "content" if self.meaningful else "",
                "quality": {"meaningful": self.meaningful, "warnings": []},
            }
        )


def test_fetch_router_uses_static_adapter_without_escalation() -> None:
    static = RoutingAdapter("trafilatura", True)
    crawl = RoutingAdapter("crawl4ai", True)
    browser = RoutingAdapter("playwright", True)
    router = FetchPageRouter([static, crawl, browser])

    result = router.execute(
        adapter_request("fetch_page", {"url": "https://example.test"})
    )

    assert result.payload["adapter_attempts"] == ["trafilatura:USED"]
    assert (static.calls, crawl.calls, browser.calls) == (1, 0, 0)


def test_fetch_router_escalates_low_quality_to_browser() -> None:
    static = RoutingAdapter("trafilatura", False)
    crawl = RoutingAdapter("crawl4ai", False)
    browser = RoutingAdapter("playwright", True)
    router = FetchPageRouter([static, crawl, browser])

    result = router.execute(
        adapter_request("fetch_page", {"url": "https://example.test/js"})
    )

    assert result.payload["adapter_attempts"] == [
        "trafilatura:LOW_QUALITY",
        "crawl4ai:LOW_QUALITY",
        "playwright:USED",
    ]


def test_company_resolution_requires_deterministic_threshold() -> None:
    left = identity("Acme AG", "https://acme.example", jurisdiction="CH")
    same = identity("ACME", "acme.example", jurisdiction="CH")
    ambiguous = identity("Acme Consulting", "other.example", jurisdiction="CH")

    assert resolve_company_identity(left, same).matched is True
    assert resolve_company_identity(left, ambiguous).matched is False


def test_praw_normalizes_removed_content_without_credentials_in_output() -> None:
    post = SimpleNamespace(
        id="p1",
        subreddit="workflows",
        title="Repeated pain",
        selftext="[removed]",
        author=None,
        score=7,
        created_utc=0,
        permalink="/r/workflows/p1",
    )
    subreddit = SimpleNamespace(search=lambda *args, **kwargs: [post])
    client = SimpleNamespace(subreddit=lambda names: subreddit)
    result = PrawRedditAdapter(client).execute(
        adapter_request("search_reddit", {"query": "pain"})
    )
    assert result.payload["threads"][0]["content_status"] == "REMOVED"
    assert result.payload["threads"][0]["body"] is None


def test_pygithub_marks_popularity_as_not_demand_evidence() -> None:
    repository = SimpleNamespace(
        full_name="owner/project",
        html_url="https://github.com/owner/project",
        description="fixture",
        stargazers_count=10,
        forks_count=2,
        watchers_count=3,
        open_issues_count=1,
        archived=False,
        license=SimpleNamespace(spdx_id="MIT"),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    client = SimpleNamespace(search_repositories=lambda **kwargs: [repository])
    result = PyGithubAdapter(client).execute(
        adapter_request("search_github", {"query": "automation"})
    )
    assert result.payload["repositories"][0]["license"] == "MIT"
    assert result.payload["popularity_is_demand_evidence"] is False


def test_eurlex_returns_only_normalized_official_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": {
                    "bindings": [
                        {
                            "work": {
                                "value": "http://publications.europa.eu/resource/cellar/123"
                            },
                            "title": {"value": "Digital resilience regulation"},
                            "date": {"value": "2025-01-01"},
                        }
                    ]
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = EurLexAdapter(client=client)
    result = adapter.execute(
        adapter_request(
            "search_regulations", {"query": "resilience", "status": "IN_FORCE"}
        )
    )

    document = result.payload["documents"][0]
    assert document["authority"] == "EUR-Lex"
    assert document["jurisdiction"] == "EU"
    assert document["canonical_official_url"] == (
        "http://publications.europa.eu/resource/cellar/123"
    )
    assert document["official_source"] is True


def test_docker_command_fails_closed_without_mounts_or_network() -> None:
    seen: dict[str, object] = {}

    def runner(command, **kwargs):
        seen["command"] = command
        seen.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="2\n", stderr="")

    adapter = DockerPythonAdapter(runner=runner)
    result = adapter.execute(adapter_request("python_execute", {"code": "print(1+1)"}))
    command = seen["command"]

    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert command[command.index("--user") + 1] == "65532:65532"
    assert "--cap-drop" in command
    assert not any("/home" in value for value in command)
    assert result.payload["stdout"] == "2\n"


def test_database_adapter_exposes_only_named_operations(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'adapter.sqlite3'}")
    database.initialize()
    adapter = SQLAlchemyDatabaseAdapter(
        database, {"GET_IDEA": lambda params: {"id": params["idea_id"]}}
    )

    result = adapter.execute(
        adapter_request(
            "database_query",
            {"operation": "GET_IDEA", "parameters": {"idea_id": "one"}},
        )
    )

    assert result.payload["result"] == {"id": "one"}
    with pytest.raises(ValueError, match="raw or destructive SQL"):
        adapter.execute(
            adapter_request(
                "database_query", {"operation": "RAW_SQL", "sql": "DROP TABLE x"}
            )
        )


class FakeVector(list):
    def tolist(self):
        return list(self)


class FakeEmbeddingModel:
    def embed(self, texts):
        return [FakeVector([float(len(text)), 1.0]) for text in texts]


def test_local_bge_embedding_contract_records_model_and_dimension() -> None:
    service = FastEmbedBGEEmbeddingService(model=FakeEmbeddingModel())

    batch = service.embed([" one   two "])

    assert batch.model_id == "BAAI/bge-small-en-v1.5"
    assert batch.dimension == 2
    assert batch.normalization_version == "ws-v1"


def test_docling_contract_has_structured_content_hash() -> None:
    document = SimpleNamespace(
        export_to_markdown=lambda: "# Heading\n\nEvidence",
        export_to_dict=lambda: {"pages": {"1": {}}, "texts": [], "tables": []},
    )
    converter = SimpleNamespace(
        convert=lambda source: SimpleNamespace(document=document)
    )
    result = DoclingAdapter(converter).execute(
        adapter_request("read_document", {"source": "fixture.docx"})
    )
    assert len(result.payload["file_hash"]) == 64


def test_pymupdf_reads_page_addressable_pdf(tmp_path) -> None:
    import pymupdf

    path = tmp_path / "fixture.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Traceable PDF evidence")
    document.save(path)
    document.close()

    result = PyMuPDFAdapter().execute(
        adapter_request("read_document", {"source": str(path)})
    )
    assert result.payload["pages"][0]["page"] == 1
    assert "Traceable PDF evidence" in result.payload["content"]


def test_canonical_url_removes_tracking_and_fragment() -> None:
    assert (
        canonicalize_url("HTTPS://Example.Test/path/?utm_campaign=x&b=2&a=1#section")
        == "https://example.test/path?a=1&b=2"
    )


def test_complete_oss_stack_routes_exactly_the_ten_logical_tools(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'oss-stack.sqlite3'}")
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

    assert set(gateway.routes) == set(ToolName)
    assert gateway.registry.names() >= {
        "searxng",
        "fetch_page_router",
        "praw",
        "company_public_sources",
        "pygithub",
        "regulatory_registry",
        "document_router",
        "docker_python",
        "sqlalchemy_db",
        "pgvector",
    }


def test_playwright_health_checks_browser_binary_not_only_python_package() -> None:
    health = PlaywrightAdapter().health()
    assert health.version == "1.62.0"
    assert health.available or health.detail == "Chromium binary is not installed"
