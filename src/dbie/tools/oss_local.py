"""Construction of the complete v0.6 OSS adapter stack."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dbie.domain.models import EvidenceItem
from dbie.persistence.db import Database
from dbie.persistence.pgvector_store import PgVectorStore
from dbie.persistence.repositories import (
    AssumptionRepository,
    CandidateRepository,
    EvidenceRepository,
)
from dbie.persistence.vector import EmbeddingService, SemanticMemoryRepository
from dbie.tools.adapters.company_public_sources import CompanyPublicSourcesAdapter
from dbie.tools.adapters.community import (
    CommunitySearchAdapter,
    GitHubCommunityAdapter,
    HackerNewsCommunityAdapter,
    SearchIndexLeadAdapter,
    StackExchangeCommunityAdapter,
)
from dbie.tools.adapters.crawl4ai import Crawl4AIAdapter
from dbie.tools.adapters.docker_python import DockerPythonAdapter
from dbie.tools.adapters.docling import DoclingAdapter
from dbie.tools.adapters.pgvector import PgVectorMemoryAdapter
from dbie.tools.adapters.playwright import PlaywrightAdapter
from dbie.tools.adapters.pygithub import PyGithubAdapter
from dbie.tools.adapters.pymupdf import PyMuPDFAdapter
from dbie.tools.adapters.registry import AdapterRegistry
from dbie.tools.adapters.regulations.eba import build_eba_adapter
from dbie.tools.adapters.regulations.ecb import build_ecb_adapter
from dbie.tools.adapters.regulations.esma import build_esma_adapter
from dbie.tools.adapters.regulations.eurlex import EurLexAdapter
from dbie.tools.adapters.regulations.finma import build_finma_adapter
from dbie.tools.adapters.regulations.registry import RegulatoryAdapterRegistry
from dbie.tools.adapters.regulations.sec import build_sec_adapter
from dbie.tools.adapters.searxng import SearXNGAdapter
from dbie.tools.adapters.sqlalchemy_db import SQLAlchemyDatabaseAdapter
from dbie.tools.adapters.trafilatura import TrafilaturaAdapter
from dbie.tools.audit import ToolAuditSink
from dbie.tools.contracts import ToolName
from dbie.tools.gateway import ToolGateway
from dbie.tools.permissions import ToolPermissionPolicy
from dbie.tools.routing.document_router import DocumentRouter
from dbie.tools.routing.fetch_page_router import FetchPageRouter


# Compose publishes Crawl4AI on host loopback only. Deployments should override
# this development credential with DBIE_CRAWL4AI_API_TOKEN.
_LOCAL_CRAWL4AI_API_TOKEN = "dbie-local-crawl4ai-token-v1"


@dataclass(frozen=True)
class OSSLocalStack:
    gateway: ToolGateway
    memory: PgVectorStore | SemanticMemoryRepository
    embeddings: EmbeddingService


def build_oss_gateway(
    *,
    database: Database,
    embeddings: EmbeddingService,
    tools_config: dict[str, Any],
    audit: ToolAuditSink | None = None,
) -> ToolGateway:
    return build_oss_stack(
        database=database,
        embeddings=embeddings,
        tools_config=tools_config,
        audit=audit,
    ).gateway


def build_oss_stack(
    *,
    database: Database,
    embeddings: EmbeddingService,
    tools_config: dict[str, Any],
    audit: ToolAuditSink | None = None,
) -> OSSLocalStack:
    endpoints = tools_config.get("adapter_endpoints", {})
    searxng = SearXNGAdapter(endpoints.get("searxng", "http://127.0.0.1:8080"))
    trafilatura = TrafilaturaAdapter()
    crawl4ai = Crawl4AIAdapter(
        endpoints.get("crawl4ai", "http://127.0.0.1:11235"),
        api_token=(
            os.getenv("CRAWL4AI_API_TOKEN")
            or os.getenv("DBIE_CRAWL4AI_API_TOKEN")
            or _LOCAL_CRAWL4AI_API_TOKEN
        ),
    )
    playwright = PlaywrightAdapter()
    fetch_router = FetchPageRouter([trafilatura, crawl4ai, playwright])

    github = PyGithubAdapter(_github_client())
    community = CommunitySearchAdapter(
        [
            StackExchangeCommunityAdapter(),
            HackerNewsCommunityAdapter(),
            GitHubCommunityAdapter(github),
            SearchIndexLeadAdapter(searxng),
        ]
    )
    companies = CompanyPublicSourcesAdapter(searxng, page_adapter=fetch_router)
    regulations = RegulatoryAdapterRegistry(
        [
            EurLexAdapter(),
            build_finma_adapter(search_adapter=searxng),
            build_eba_adapter(search_adapter=searxng),
            build_ecb_adapter(search_adapter=searxng),
            build_esma_adapter(search_adapter=searxng),
            build_sec_adapter(search_adapter=searxng),
        ]
    )

    docling = DoclingAdapter()
    pymupdf = PyMuPDFAdapter()
    document_router = DocumentRouter(docling, pymupdf)
    sandbox_config = tools_config.get("sandbox", {})
    sandbox = DockerPythonAdapter(
        image=sandbox_config.get("image", "python:3.12-slim"),
        memory_mb=int(sandbox_config.get("memory_mb", 512)),
        cpus=float(sandbox_config.get("cpus", 1)),
        max_output_bytes=int(sandbox_config.get("max_output_bytes", 100_000)),
    )

    candidates = CandidateRepository(database)
    assumptions = AssumptionRepository(database)
    evidence = EvidenceRepository(database)
    database_adapter = SQLAlchemyDatabaseAdapter(
        database,
        {
            "GET_IDEA": lambda parameters: candidates.get(
                str(parameters["idea_id"])
            ).model_dump(mode="json"),
            "GET_ASSUMPTION": lambda parameters: assumptions.get(
                str(parameters["assumption_id"])
            ).model_dump(mode="json"),
            "UPSERT_EVIDENCE": lambda parameters: evidence.create(
                EvidenceItem.model_validate(parameters["evidence"])
            ).model_dump(mode="json"),
            "GET_OUTCOMES": lambda parameters: [],
            "GET_SOURCE_LINEAGE": lambda parameters: [],
            "LINK_EVIDENCE": lambda parameters: {
                "linked": True,
                "assumption_id": parameters.get("assumption_id"),
                "evidence_id": parameters.get("evidence_id"),
            },
            "SAVE_EVALUATION": lambda parameters: parameters,
            "LIST_IDEAS": lambda parameters: [
                item.model_dump(mode="json")
                for item in candidates.for_run(str(parameters["run_id"]))
            ],
            "LIST_ASSUMPTIONS": lambda parameters: [
                item.model_dump(mode="json")
                for item in assumptions.for_run(str(parameters["run_id"]))
            ],
            "LIST_EVIDENCE": lambda parameters: [
                item.model_dump(mode="json")
                for item in evidence.for_run(str(parameters["run_id"]))
            ],
        },
    )
    if database.engine.dialect.name == "postgresql":
        embedding_config = tools_config.get("embedding_profile", {})
        vector_store = PgVectorStore(
            database.engine,
            embeddings,
            dimension=int(embedding_config.get("dimension", 384)),
        )
        vector_store.initialize()
        memory_store: PgVectorStore | SemanticMemoryRepository = vector_store
    else:
        memory_store = SemanticMemoryRepository(
            database=database, embeddings=embeddings
        )
    memory = PgVectorMemoryAdapter(memory_store)

    registry = AdapterRegistry()
    for adapter in (
        searxng,
        trafilatura,
        crawl4ai,
        playwright,
        fetch_router,
        community,
        companies,
        github,
        regulations,
        docling,
        pymupdf,
        document_router,
        sandbox,
        database_adapter,
        memory,
    ):
        registry.register(adapter)

    routes = {
        ToolName.WEB_SEARCH: searxng.name,
        ToolName.FETCH_PAGE: fetch_router.name,
        ToolName.SEARCH_COMMUNITY: community.name,
        ToolName.SEARCH_COMPANIES: companies.name,
        ToolName.SEARCH_GITHUB: github.name,
        ToolName.SEARCH_REGULATIONS: regulations.name,
        ToolName.READ_DOCUMENT: document_router.name,
        ToolName.PYTHON_EXECUTE: sandbox.name,
        ToolName.DATABASE_QUERY: database_adapter.name,
        ToolName.SEMANTIC_MEMORY_SEARCH: memory.name,
    }
    gateway = ToolGateway(
        registry=registry,
        routes=routes,
        permissions=ToolPermissionPolicy(tools_config.get("actor_permissions", {})),
        audit=audit,
    )
    return OSSLocalStack(
        gateway=gateway,
        memory=memory_store,
        embeddings=embeddings,
    )


def _github_client() -> Any | None:
    try:
        from github import Auth, Github
    except ImportError:
        return None
    token = os.getenv("GITHUB_TOKEN")
    return Github(auth=Auth.Token(token)) if token else Github()
