# Digital Business Idea Engine

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

`acceptance-run` is deliberately offline and deterministic. It executes all 11
MVP Flow stages, persists 50 raw-idea fixture provenance, exercises the hard
eligibility/evidence/red-team gates, creates a pairwise portfolio result, and
writes resumable state and dossiers under `runs/<run-id>/`. It is the
reproducibility acceptance path, not a claim of newly collected market evidence.

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
- PRAW, public company-source resolution, and PyGithub
- EUR-Lex plus official FINMA/EBA/ECB/ESMA/SEC registry adapters
- Docling then PyMuPDF document routing
- network-disabled, read-only, capability-free, non-root Docker Python execution
- named-operation-only SQLAlchemy access
- PostgreSQL/pgvector in production, with SQLite exact-vector fallback in tests
- local CPU BGE embeddings through FastEmbed

External services are optional for unit tests. Production endpoints and actor
allowlists are configured in `config/tools.yaml`; credentials are read only by
adapter construction and are never included in model context.

The default development database is `runs/dbie.sqlite3`. Override any setting
with environment variables prefixed by `DBIE_`; for example,
`DBIE_DATABASE_URL=postgresql+psycopg://...`.

## Ollama models

`gpt-oss:20b-64k` is the default profile. The Ollama registry publishes the
Ministral base as `ministral-3:14b`, so the configured fallback tag is created
locally with the requested 64k context:

```bash
ollama pull ministral-3:14b
ollama create ministral-3:14b-64k \
  -f config/ollama/Ministral-3-14B-64K.Modelfile
uv run dbie doctor
```

## Specialized model phases

The v0.7 NemoClaw model-phase design is implemented above the provider router.
Crews declare a logical role rather than a model name:

- `THINKER` → `deepseek-r1:14b-48k` for synthesis, assumptions, reconciliation,
  experiment design, and portfolio reasoning
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
