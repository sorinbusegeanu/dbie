# DBIE Dashboard --- Design and Implementation

## 1. Purpose

The DBIE Dashboard is a deliberately small, read-only web interface for
observing DBIE/CrewAI work.

It has only two responsibilities:

1.  **Read CrewAI conversations** in the native persisted CrewAI
    output/log format.
2.  **Read deliverables** produced by crews and agents, especially
    Markdown reports and specifications.

It is not an orchestration console, observability platform, event
system, workflow editor, or administration interface.

## 2. Design Principles

-   Keep the dashboard independent from DBIE business logic.
-   Do not introduce an event bus, WebSockets, Redis, Kafka, React, or
    another agent framework.
-   Do not transform CrewAI conversations into a new DBIE-specific
    conversation schema.
-   Persist CrewAI conversation output as close as possible to its
    native format.
-   Persist deliverables as ordinary files.
-   Treat the filesystem as the dashboard's read interface.
-   Keep the dashboard read-only.
-   Make it possible to delete or replace the dashboard without
    affecting DBIE execution.

## 3. Architecture

``` text
DBIE / CrewAI
     |
     +--> runs/<run_id>/conversations/
     |       crew-*.log
     |       agent-*.log
     |       ...
     |
     +--> runs/<run_id>/deliverables/
             *.md
             *.txt
             *.json
             other artifacts

                     |
                     v

              DBIE Dashboard
          FastAPI + Jinja2
                     |
                     v
                Web browser
```

There is no direct orchestration dependency between the dashboard and
CrewAI.

CrewAI and DBIE write files. The dashboard reads them.

## 4. Run Directory Contract

Each DBIE run uses a predictable directory:

``` text
runs/
  <run_id>/
    conversations/
    deliverables/
```

Optionally:

``` text
runs/
  current -> <run_id>
```

may point to the active run.

The dashboard must support browsing both the current run and previous
runs when they remain on disk.

## 5. Conversation Storage

CrewAI conversation/activity output is persisted under:

``` text
runs/<run_id>/conversations/
```

The objective is to preserve the native CrewAI representation rather
than create a second conversation model.

Example:

``` text
conversations/
  discovery_crew.log
  validation_crew.log
  market_research_crew.log
  mvp_factory_crew.log
```

If CrewAI produces separate files per agent or task, the dashboard
should display that structure directly rather than merge it
artificially.

Conversation files are displayed as preformatted text.

``` html
<pre>
CrewAI native output
</pre>
```

The dashboard does not attempt to expose hidden model chain-of-thought.
It displays only content actually emitted or persisted by CrewAI:
messages, task output, tool activity, delegated work, and other native
visible execution information.

## 6. Deliverable Storage

Crew and agent deliverables are persisted under:

``` text
runs/<run_id>/deliverables/
```

Example:

``` text
deliverables/
  opportunity_report.md
  assumptions.md
  market_research.md
  competitor_analysis.md
  evidence_summary.md
  experiment_design.md
  mvp_spec.md
  productization_review.md
```

Markdown is the preferred DBIE human-readable deliverable format.

The dashboard renders `.md` files as HTML.

Plain text and JSON may be displayed directly.

Other artifacts are shown as downloadable/openable files where
appropriate.

## 7. User Interface

The dashboard home page contains two primary sections:

``` text
DBIE
================================================

Conversations
------------------------------------------------
Discovery Crew
Market Research Crew
Validation Crew
MVP Factory Crew

Deliverables
------------------------------------------------
Opportunity Report
Market Research
Evidence Summary
MVP Specification
```

Selecting a conversation opens its native output.

Selecting a Markdown deliverable opens the rendered document.

No additional dashboard functionality is required for the initial
version.

## 8. Optional Run Selection

If multiple runs exist, the page may include a minimal run selector:

``` text
Run: [ 2026-08-29-001 v ]

Conversations
...

Deliverables
...
```

The default selection should be `current` or the newest run.

This remains filesystem-based and requires no additional database.

## 9. Refresh Behaviour

The first implementation may use ordinary browser refresh.

If automatic refresh is useful while agents are running, use simple
periodic page refresh or small JavaScript polling.

Example:

``` html
<meta http-equiv="refresh" content="3">
```

A 2--5 second interval is sufficient.

WebSockets and server-side event streaming are explicitly unnecessary
for this dashboard.

## 10. Technology

Use:

``` text
Python
FastAPI
Jinja2
Markdown renderer
filesystem
```

Do not add:

``` text
React
Next.js
Redis
Kafka
WebSocket infrastructure
separate telemetry database
event bus
```

unless a future requirement genuinely requires them.

## 11. Repository Structure

Recommended structure:

``` text
src/dbie/web/
    __init__.py
    app.py
    filesystem.py
    templates/
        base.html
        index.html
        conversation.html
        deliverable.html
    static/
        dashboard.css
```

No separate frontend build system is required.

## 12. Configuration

Example:

``` yaml
web_viewer:
  enabled: true
  host: 0.0.0.0
  port: 8080
  runs_dir: runs
  current_run: current
  auto_refresh_seconds: 3
```

The dashboard should also accept equivalent CLI/environment
configuration where consistent with the wider DBIE configuration system.

## 13. HTTP Routes

Minimum routes:

``` text
GET /
GET /runs/{run_id}
GET /runs/{run_id}/conversations/{path}
GET /runs/{run_id}/deliverables/{path}
```

Optional convenience routes:

``` text
GET /current
GET /current/conversations/{path}
GET /current/deliverables/{path}
```

`/` lists the current/newest run and its conversations and deliverables.

## 14. Filesystem Safety

All requested files must resolve underneath the configured `runs_dir`.

The implementation must reject path traversal such as:

``` text
../../etc/passwd
```

The dashboard is read-only.

It must not:

-   modify CrewAI output;
-   edit deliverables;
-   delete files;
-   start or stop crews;
-   invoke agents;
-   execute code;
-   expose secrets or unrelated host files.

If conversation logs can contain secrets, DBIE should redact them before
persistence or before dashboard rendering.

## 15. Implementation Plan

### Phase 1 --- Output Directories

Ensure every DBIE run creates:

``` text
runs/<run_id>/conversations/
runs/<run_id>/deliverables/
```

Ensure the active run is discoverable through `runs/current` or
equivalent configuration.

### Phase 2 --- CrewAI Conversation Persistence

Configure/wrap CrewAI execution so visible native conversation/activity
output is persisted to the run's `conversations/` directory.

Do not introduce a custom conversation database.

Acceptance:

-   start a CrewAI crew;
-   observe a conversation log file;
-   open the file directly and confirm it retains the expected
    CrewAI-readable format.

### Phase 3 --- Deliverable Persistence

Ensure crew/task outputs intended for human inspection are written to
`deliverables/`.

Prefer Markdown for reports and specifications.

Acceptance:

-   a completed crew creates its expected Markdown deliverable;
-   the file is usable independently of the dashboard.

### Phase 4 --- FastAPI Viewer

Implement `src/dbie/web/app.py`.

Responsibilities:

-   discover runs;
-   determine current/newest run;
-   list conversation files;
-   list deliverable files;
-   safely read selected files;
-   render templates.

Keep business logic out of this module.

### Phase 5 --- Markdown Rendering

Render Markdown deliverables into HTML.

The original Markdown file remains canonical.

The dashboard rendering is only a presentation layer.

### Phase 6 --- Conversation Rendering

Display conversation files in a `<pre>` block with readable
wrapping/scrolling.

Do not parse or reinterpret CrewAI's native conversation structure
unless minimal escaping is required for safe HTML display.

### Phase 7 --- Simple Refresh

Add configurable automatic refresh to listing/conversation pages if
desired.

Default:

``` text
3 seconds
```

This permits following a conversation file while CrewAI continues
writing to it.

### Phase 8 --- CLI Startup

Provide a simple way to start the dashboard, for example:

``` text
dbie dashboard
```

or the equivalent existing DBIE CLI convention.

It starts FastAPI on the configured host/port.

## 16. Minimal Acceptance Test

A successful end-to-end test is:

``` text
1. Start DBIE.
2. Start the dashboard.
3. CrewAI begins a Market Research Crew.
4. Browser shows its conversation file.
5. Refresh shows newly persisted CrewAI output.
6. Crew finishes.
7. Crew writes market_research.md.
8. Browser lists market_research.md.
9. Selecting it renders the Markdown.
```

Nothing more is required for v1.

## 17. Non-Goals

The dashboard is explicitly not intended to provide:

-   workflow visualization;
-   model performance charts;
-   GPU monitoring;
-   token metrics;
-   CrewAI control;
-   task editing;
-   agent chat;
-   approvals;
-   venture administration;
-   live event streaming;
-   orchestration;
-   database administration.

Those may exist elsewhere if eventually required.

## 18. Final Design

``` text
                DBIE / CrewAI
                     |
          +----------+----------+
          |                     |
          v                     v
   conversations/          deliverables/
   native CrewAI logs      Markdown/files
          |                     |
          +----------+----------+
                     |
                     v
             FastAPI + Jinja2
                     |
                     v
                 Browser
```

The implementation should remain intentionally small: **persist native
CrewAI-visible conversations and DBIE deliverables to disk, then provide
a read-only web page for browsing them.**
