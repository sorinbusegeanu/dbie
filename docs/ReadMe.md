# DBIE MVP

The Digital Business Idea Engine is a local-first system that discovers,
evaluates, ranks, and documents fully digital business opportunities. The MVP
stores each run under `runs/<run-id>/`; its read-only dashboard displays visible
run activity and generated Markdown/JSON deliverables.

From the repository root, run these commands in two separate terminals:

```bash
CREWAI_TRACING_ENABLED=false uv run dbie acceptance-run
```

```bash
uv run dbie dashboard
```

Dashboard: <http://127.0.0.1:8080>
