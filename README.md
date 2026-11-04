# Digital Business Idea Engine

## At a glance

**Type:** Local-first multi-agent AI application  
**Stack:** Python, CrewAI, Ollama, PostgreSQL/pgvector, FastEmbed, Docker, configurable research tools

**Purpose:** Discover, assess and compare digital business opportunities using evidence collected from external sources.

- **Agent workflow:** Specialised discovery, ideation, validation, synthesis, red-team and evaluation roles coordinated through a resumable 14-stage CrewAI Flow.
- **Model orchestration:** Role-based routing for local models, with scheduled phases, checkpoint barriers and recorded performance metrics.
- **Tools and evidence:** Permissioned research and document tools, provenance-aware evidence, semantic retrieval and deterministic evaluation gates.
- **Outputs:** Ranked opportunities, decision dossiers (Markdown/JSON), persisted records and a local read-only dashboard.
- **Implementation status:** MVP code, acceptance and test workflows are present; real live runs depend on the configured local models, database and optional external services.

**Inspect the code:** [Flow](src/dbie/flows/idea_pipeline.py) · [Agents](src/dbie/crews/catalog.py) · [Model scheduling](src/dbie/models/phase_scheduler.py) · [Tool gateway](src/dbie/tools/gateway.py) · [Tests](tests/).



DBIE is a local-first, evidence-driven engine for discovering and evaluating
fully digital, autonomously scalable business opportunities.

The MVP now includes the deterministic domain engine, durable relational and
semantic memory, the Ollama-backed provider-neutral model router, a resumable
CrewAI Flow, separated discovery/ideation/validation/red-team actor catalogs,
the ten permissioned tools backed by the v0.6 OSS adapter stack, pairwise
portfolio ranking, observability, and Markdown plus JSON decision dossiers.

## Development

```bash
uv sync --extra dev
uv run dbie doctor
uv run dbie smoke
CREWAI_TRACING_ENABLED=false uv run dbie acceptance-run
uv run dbie benchmark --profile gpt_oss_20b_64k
uv run pytest
```

`live-run` executes all 14 MVP Flow stages with CrewAI, the configured Ollama
role models, and the real logical tools. It defaults to the v0.6 funnel targets
of 500 grounded signals, 250 raw ideas, and up to 25 validation candidates.
Use `--signals`, `--ideas`, and `--candidates` for a bounded first run. Every
stage checkpoint can be resumed with `uv run dbie resume-run <run-id>`.

A recommended first all-crews execution is:

```bash
DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' \
CREWAI_TRACING_ENABLED=false \
uv run dbie live-run \
  --mandate "Find fully digital, autonomously scalable business opportunities" \
  --signals 50 \
  --ideas 25 \
  --candidates 5 \
  --no-strict-targets
```

Omitting the four bounded-target options runs the complete strict
500-signal/250-idea/25-candidate funnel.

`acceptance-run` remains the fast offline regression path for deterministic
domain gates and dashboard artifacts.

## Run dashboard

The dashboard is a read-only filesystem viewer for persisted crew-visible output
and deliverables. Start it locally and open <http://127.0.0.1:8080>:

```bash
uv run dbie dashboard
```

It follows `runs/current`, falls back to the newest run, and refreshes active
conversation views every three seconds. The documented default binds all local
interfaces; use `--host 127.0.0.1` to restrict it to the host. No mutation
routes, database coupling, model calls, or hidden model reasoning are exposed.

## v0.6 OSS stack

CrewAI sees exactly ten stable logical tools. Their implementations remain
hidden behind the Tool Gateway:

- SearXNG; Trafilatura then Crawl4AI then Playwright page routing
- credential-free community search across Stack Exchange, Hacker News, GitHub
  issues, and search-index discovery leads; public company-source resolution;
  and PyGithub
- EUR-Lex plus official FINMA/EBA/ECB/ESMA/SEC registry adapters
- Docling then PyMuPDF document routing
- network-disabled, read-only, capability-free, non-root Docker Python execution
- named-operation-only SQLAlchemy access
- PostgreSQL/pgvector in production, with SQLite exact-vector fallback in tests
- local CPU BGE embeddings through FastEmbed

External services are optional for unit tests. Live-run endpoints and actor
allowlists are configured in `config/tools.yaml`; credentials are read only by
adapter construction and are never included in model context.

Start already-installed container images without downloading replacements:

```bash
docker compose -f deploy/compose.yaml up -d
```

Then run `DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' uv run dbie doctor`. The strict doctor checks Ollama, every configured
model, all ten logical adapter routes, and the local BGE embedding cache before
a live run starts.

The default development database is `runs/dbie.sqlite3`. Override any setting
with environment variables prefixed by `DBIE_`; for example,
`DBIE_DATABASE_URL=postgresql+psycopg://...`.

Compose uses a localhost-only Crawl4AI development token. Set
`DBIE_CRAWL4AI_API_TOKEN` to the same custom value for both Compose and DBIE in
non-local deployments.

### Community evidence without Reddit credentials

The ten-tool surface now exposes `search_community` instead of
`search_reddit`. It collects qualitative signals from official Stack Exchange,
Hacker News, and GitHub interfaces. SearXNG may return Reddit and GitHub
Discussion URLs only as `DISCOVERY_LEAD` records; DBIE never automatically
fetches Reddit content. PRAW is optional and does not block strict readiness.
See [the community adapter amendment](docs/Community_Search_Adapter.md).

## Ollama models

`qwen3:14b-64k`, `gpt-oss:20b-64k`, and `ministral-3:14b-64k` are configured
local profiles.
DBIE never pulls models during doctor or live execution. Verify the existing
local tags with:

```bash
ollama list
uv run dbie doctor
```

## Specialized model phases

The v0.7 NemoClaw model-phase design is implemented above the provider router.
Crews declare a logical role rather than a model name:

- `THINKER` → `qwen3:14b-64k` in thinking mode for synthesis, assumptions,
  reconciliation, experiment design, and portfolio reasoning because current
  THINKER tasks also execute tools; `ministral-3:14b-64k` is the challenger
- `DOER` → `qwen3:14b-64k` for high-volume research, extraction, and tool use;
  `ministral-3:14b-64k` is the challenger/fallback
- `BUILDER` → `qwen3:14b-64k` for later governed MVP implementation/test loops
- `JUDGE` → `gpt-oss:20b-64k` for explicitly escalated independent review

`ModelPhaseScheduler` batches runnable work by barrier, role, resolved model,
context requirement, execution mode, and venture batch. Every barrier is
checkpointed before the model residency changes. Model/task performance and
phase-switch metrics are stored separately from venture evidence, so model
agreement or operational quality can never become market evidence.

All mappings are configuration in `config/models.yaml`; Crew definitions contain
only the stable logical role. The GPT-OSS 64k tag can be recreated without a
download from an installed 96k tag:

```bash
ollama create gpt-oss:20b-64k -f config/ollama/GPT-OSS-20B-64K.Modelfile
```
