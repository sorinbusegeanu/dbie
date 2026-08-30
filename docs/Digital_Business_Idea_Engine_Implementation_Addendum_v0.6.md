# DIGITAL BUSINESS IDEA ENGINE

## Implementation Addendum v0.6 — Changes Only

29 August 2026

Applies to: `Digital_Business_Idea_Engine_Implementation_Plan_v0.5.md`  
Companion design: `Digital_Business_Idea_Engine_System_Design_v0.6.md`

This addendum contains **only implementation changes introduced by v0.6**. All v0.5 phases, acceptance gates, domain semantics, CrewAI-only harness decision, model routing, and ten logical tool contracts remain in force unless explicitly amended below.

> **Operational amendment, 30 August 2026:** Section 6 and the T03 adapter are
> superseded by the credential-free `search_community` implementation described
> in [Community_Search_Adapter.md](Community_Search_Adapter.md). It uses official
> Stack Exchange, Hacker News, and GitHub interfaces; SearXNG Reddit results are
> discovery leads only; PRAW is optional and is not a readiness dependency.

# 1. Architectural Delta

Do **not** add new CrewAI-visible tools. Keep the existing ten logical contracts exactly as the agent-facing surface. Add an internal adapter layer owned by `ToolGateway`.

New rule:

```text
CrewAI actor → logical DBIE tool → ToolGateway → adapter selector → OSS adapter(s)
```

CrewAI must never directly choose SearXNG, Crawl4AI, Trafilatura, Playwright, Docling, PyMuPDF, PRAW, PyGithub, pgvector, or the embedding model.

# 2. Repository Changes

Extend the v0.5 structure with:

```text
src/dbie/tools/
├── adapters/
│   ├── base.py
│   ├── registry.py
│   ├── health.py
│   ├── searxng.py
│   ├── trafilatura.py
│   ├── crawl4ai.py
│   ├── playwright.py
│   ├── praw_reddit.py
│   ├── company_public_sources.py
│   ├── pygithub.py
│   ├── regulations/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── eurlex.py
│   │   ├── finma.py
│   │   ├── eba.py
│   │   ├── ecb.py
│   │   ├── esma.py
│   │   └── sec.py
│   ├── docling.py
│   ├── pymupdf.py
│   ├── docker_python.py
│   ├── sqlalchemy_db.py
│   ├── pgvector.py
│   └── embeddings.py
├── routing/
│   ├── fetch_page_router.py
│   ├── document_router.py
│   └── fallback.py
└── normalization/
    ├── web.py
    ├── documents.py
    ├── companies.py
    ├── regulations.py
    └── github.py
```

Add configuration sections:

```text
config/tools.yaml
  adapters
  routing
  timeouts
  concurrency
  cache
  sandbox
  regulator_registry
  embedding_profile
```

# 3. Common Adapter Interface

Add an internal adapter protocol. At minimum each adapter exposes equivalent semantics to:

- `name`
- `capabilities`
- `health()`
- `execute(request)`
- `normalize(raw_result)` where normalization is not embedded in execution

Every adapter result adds:

- adapter name/version;
- start/end timestamps and latency;
- cache hit/miss;
- error category and retry/fallback count;
- resource usage where measurable;
- raw source identifiers/URLs;
- parser/extraction warnings;
- content hash for retrieved documents/pages where practical.

The existing logical-tool response contract remains authoritative; adapter metadata is nested provenance, not a new agent-facing schema.

# 4. `web_search` Delta — SearXNG

Implement SearXNG as the default OSS search adapter.

### Changes

1. Deploy or configure a self-hosted SearXNG endpoint.
2. Add `SearXNGAdapter` returning normalized result records: URL, canonical URL, title, snippet, engines, rank/score when supplied, published date when available, query, retrieval time.
3. Preserve the existing rule that snippets are discovery evidence only.
4. Keep the provider abstraction so commercial search APIs can be enabled as fallback or benchmark adapters without changing CrewAI.
5. Add result URL canonicalization and duplicate collapsing before returning to the agent.

### Acceptance additions

- `web_search` succeeds using only SearXNG in an OSS-only profile.
- Switching to another provider changes configuration only.
- Search snippets cannot be committed as primary evidence without a source-fetch step except for explicitly typed structured-source results.

# 5. `fetch_page` Delta — Trafilatura → Crawl4AI → Playwright

Implement deterministic adapter escalation.

### Routing order

1. **Trafilatura** — first attempt for ordinary static/readable HTML.
2. **Crawl4AI** — use for complex extraction, schema extraction, multi-page/site crawling, richer link discovery, or when Trafilatura quality is inadequate.
3. **Playwright** — use only when browser rendering/JS execution is required or the prior adapters cannot obtain meaningful content.

### Router inputs

- URL/domain;
- purpose;
- requested extraction schema;
- whether links/site traversal are requested;
- prior adapter error/quality signal;
- stage budget.

### Required output quality flags

- empty/near-empty content;
- boilerplate ratio where measurable;
- suspected login/paywall/challenge;
- parser warning;
- dynamic-render requirement;
- truncation.

### Acceptance additions

Golden fixtures must prove:

- static article uses Trafilatura without launching a browser;
- complex structured page can escalate to Crawl4AI;
- JS-only fixture escalates to Playwright;
- CrewAI receives the same `fetch_page` result schema in all cases;
- adapter escalation is recorded in provenance.

# 6. `search_community` Delta — Credential-Free Community Evidence

Implement `CommunitySearchAdapter` behind `search_community`. Aggregate official
Stack Exchange questions/answers/comments, official Hacker News feeds/comments,
and GitHub issues/comments. Preserve source IDs, thread/reply relations,
timestamps, canonical URLs, scores where supplied, and content hashes.

Use SearXNG `site:reddit.com` and GitHub Discussion results only as
`DISCOVERY_LEAD` records. Search snippets are not observed evidence. The adapter
must not automatically fetch Reddit pages or unofficial JSON endpoints. PRAW is
an optional future adapter after approved Reddit Data API access and is not a
health or readiness dependency.

# 7. `search_companies` Delta — Public-Source Composition

Replace any implied commercial dependency with an OSS/public-source baseline.

Initial adapters:

- SearXNG discovery;
- company website fetch via Trafilatura/Crawl4AI;
- Wikidata;
- OpenCorporates/public registries where usable;
- regulator/filing sources where relevant.

Commercial connectors remain optional enrichers only.

### New mandatory component: entity resolution

Implement canonical-company matching using normalized name, domain, jurisdiction, registry identifiers, website and known aliases. Do not merge fields until identity confidence passes a deterministic threshold or a human/evidence-review path resolves ambiguity.

Each company attribute retains field-level provenance. Unknown values remain `UNKNOWN`; no LLM-filled funding/revenue/headcount facts.

# 8. `search_github` Delta — PyGithub + Direct APIs

Implement `PyGithubAdapter` and allow direct GitHub REST/GraphQL/search calls underneath when needed.

Normalize at least:

- repository metadata;
- releases;
- issues;
- discussions where API-accessible;
- stars/forks/watchers;
- contributor/activity signals;
- timestamps;
- license;
- archived status.

Prioritize issues/discussions and release/activity patterns for evidence; never convert stars directly into demand.

Repository code execution remains prohibited. Any feasibility execution must be copied/reimplemented into the Python sandbox under a separate authorized call.

# 9. `search_regulations` Delta — Official Adapter Registry

Create a regulator adapter registry. Implement **EUR-Lex** first using official APIs/SPARQL where appropriate, then adapters for FINMA, EBA, ECB, ESMA and SEC using their authoritative interfaces or targeted official-site extraction.

Common request fields:

- jurisdiction;
- authority optional;
- topic/query;
- entity type;
- publication/effective-date window;
- status.

Common normalized output:

- authority;
- jurisdiction;
- document identifier;
- title;
- legal/status type;
- publication date;
- effective/applicability date when available;
- affected entity scope when directly supported;
- canonical official URL;
- retrieved text/section references.

General web search may locate a document but must not outrank the official source.

# 10. `read_document` Delta — Docling + PyMuPDF

Implement:

- `DoclingAdapter` as the default structured multi-format parser;
- `PyMuPDFAdapter` as fast PDF path/fallback and page-rendering/extraction utility.

The document router uses media type, size, requested structure, and previous parse quality to choose an adapter.

Normalized output must retain:

- file/source hash;
- page number;
- section heading/path where available;
- table identity/cells where available;
- parser adapter/version;
- extraction warnings;
- source URL/path provenance.

Add fixtures for text PDF, table-heavy PDF, scanned/image-rich or difficult PDF where supported, DOCX, PPTX and XLSX/HTML as appropriate to Docling coverage.

# 11. `python_execute` Delta — Isolated Docker Sandbox

Implement a dedicated execution adapter. Onyx Python Sandbox may be used as the package/service, but DBIE's `python_execute` contract remains stable.

Default sandbox policy:

- ephemeral container;
- no outbound network;
- no Docker socket;
- no production/database/cloud credentials;
- CPU/RAM/wall-clock/output quotas;
- no host-home mount;
- explicit read-only input mounts only;
- package installation off by default or restricted to an allowlist/cache;
- declared outputs copied out and hashed only after completion.

Record code, inputs, environment image/version, output, stderr, exit code, limits and observed resource use.

Add hostile fixtures attempting filesystem escape, network access, excessive CPU/RAM/output and prohibited mounts. They must fail closed.

# 12. `database_query` Delta — SQLAlchemy

Standardize PostgreSQL access through SQLAlchemy/application repositories. CrewAI never sees a database DSN or unrestricted SQL channel.

Add explicit read/query DTOs or vetted query templates for agent-originated database requests. Canonical state writes continue through domain/application services, not through free-form agent SQL.

# 13. `semantic_memory_search` Delta — pgvector + Local Embeddings

Keep pgvector in PostgreSQL. Add an `EmbeddingService` with a replaceable model adapter.

Initial profile:

- compact **BGE- or E5-family** embedding model;
- CPU preferred to preserve the 16 GB GPU for the primary LLM and KV cache;
- model identifier/dimension stored with vectors;
- batch embedding;
- deterministic text-normalization/version metadata;
- re-embedding as an explicit migration.

Implement HNSW or the pgvector index selected by measured corpus size/query behavior. Do not prematurely add Qdrant/Weaviate/Milvus.

Acceptance: semantic retrieval works with the primary LLM server stopped, proving embedding independence.

# 14. Deployment Delta

Add services/workers to the local deployment profile:

```text
DBIE + CrewAI
PostgreSQL + pgvector
SearXNG
Crawl4AI worker/service
Playwright worker/browser pool
local embedding worker/service (CPU preferred)
Docker sandbox worker pool
vLLM OR Ollama
```

Trafilatura, Docling, PyMuPDF, PRAW, PyGithub and SQLAlchemy may run in normal application workers initially.

Introduce separate concurrency pools for:

- LLM inference;
- lightweight HTTP extraction;
- Crawl4AI;
- Playwright;
- document parsing;
- Python sandboxes;
- embeddings.

Browser/crawling/document workers must not consume the LLM GPU by default.

# 15. Configuration Delta

Add an `oss_local` tool profile roughly equivalent to:

```yaml
web_search:
  primary: searxng

fetch_page:
  routing: [trafilatura, crawl4ai, playwright]

community:
  adapter: community_search
  evidence_sources: [stackexchange, hackernews, github]
  discovery_only: [reddit_index, github_discussion_index]

github:
  adapter: pygithub

read_document:
  primary: docling
  fallback: pymupdf

python_execute:
  adapter: docker
  network: false

persistence:
  engine: postgresql
  orm: sqlalchemy
  vector: pgvector

embeddings:
  provider: local
  device: cpu
  family: bge_or_e5
```

Exact model/package versions must be pinned during implementation after runtime compatibility tests; they are not hard-coded into the system semantics.

# 16. Observability Delta

Add adapter-level metrics:

- calls/success/failure;
- p50/p95 latency;
- timeout rate;
- fallback/escalation rate;
- bytes/documents/pages processed;
- extraction-quality warning rate;
- browser launches;
- sandbox CPU/RAM/time terminations;
- embedding throughput;
- cache hit rate.

Add a report comparing `fetch_page` adapter quality/cost so routing thresholds can later be tuned from measurements rather than intuition.

# 17. Build-Order Delta

Insert the following work into the v0.5 plan after the Tool Gateway contracts exist and before full CrewAI workflow integration depends on live research:

1. Adapter base/registry/health metadata.
2. PostgreSQL + SQLAlchemy + pgvector foundation.
3. Local embedding service.
4. SearXNG adapter.
5. Trafilatura adapter and fetch router.
6. Crawl4AI adapter.
7. Playwright escalation worker.
8. Docling + PyMuPDF document router.
9. Credential-free community adapter with explicit lead/evidence separation.
10. PyGithub adapter.
11. EUR-Lex adapter, then remaining regulator adapters.
12. Public company-source composition + entity resolution.
13. Docker Python sandbox.
14. Adapter observability, caching, fallback and load tests.
15. Re-run the DBIE model/tool benchmark with the **same ten CrewAI schemas** to validate GPT-OSS-20B and Ministral 3 14B tool-selection behavior.

# 18. New v0.6 Exit Gate

The OSS adapter layer is complete only when:

- all ten CrewAI-visible tool schemas are unchanged from the logical v0.5 design except backward-compatible metadata additions;
- an `oss_local` profile can run the research/evidence workflow without mandatory paid research APIs;
- static, complex and JS-only pages route correctly across Trafilatura/Crawl4AI/Playwright;
- Docling/PyMuPDF preserve page/section provenance;
- the Python sandbox passes isolation tests;
- regulator evidence resolves to authoritative sources;
- company field values retain source-level provenance and entity-resolution confidence;
- pgvector retrieval uses a dedicated local embedding model;
- adapter failures do not leak provider-specific exceptions/prompts into CrewAI;
- model benchmarking confirms that exposing only the ten stable tools remains more reliable than exposing adapter-level tools directly.
