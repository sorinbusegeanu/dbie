# DBIE MVP

The Digital Business Idea Engine is a local-first system that uses specialized
CrewAI agents, local Ollama models, and ten permissioned OSS tools to discover,
validate, challenge, rank, and document fully digital business opportunities.
Each live run is resumable and visible under `runs/<run-id>/`.

Community pain signals use Stack Exchange, Hacker News, and GitHub issues.
Reddit search-index results are retained only as discovery leads and are never
automatically crawled. See [Community Search Adapter](Community_Search_Adapter.md).

The live OSS stack uses SearXNG, Crawl4AI, PostgreSQL with pgvector, local BGE
embeddings, and Ollama. PRAW credentials are not required. From the repository
root, start the services and dashboard in the first terminal:

```bash
docker compose -f deploy/compose.yaml up -d && DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' uv run dbie dashboard
```

Open the dashboard at <http://127.0.0.1:8080>.

In a second terminal, run a manageable execution that still invokes every crew
and all 14 MVP phases:

```bash
DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' CREWAI_TRACING_ENABLED=false uv run dbie live-run --mandate "Find fully digital, autonomously scalable business opportunities" --signals 50 --ideas 25 --candidates 5 --no-strict-targets
```

For the complete strict funnel of 500 signals, 250 ideas, and up to 25
validation candidates, omit the bounded target options:

```bash
DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' CREWAI_TRACING_ENABLED=false uv run dbie live-run --mandate "Find fully digital, autonomously scalable business opportunities"
```

Before a run, strict readiness can be checked with:

```bash
DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' uv run dbie doctor
```

If a run is interrupted after its UUID has been persisted, resume it with
`DBIE_DATABASE_URL='postgresql+psycopg://dbie@127.0.0.1:5432/dbie' uv run dbie resume-run <run-id>`.
