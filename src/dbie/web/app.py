"""FastAPI application for observing filesystem-native DBIE runs."""

from __future__ import annotations

import html
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dbie.web.filesystem import DashboardFilesystem, DashboardPathError

_PACKAGE_DIRECTORY = Path(__file__).parent
_TEXT_SUFFIXES = {".txt", ".log", ".json", ".yaml", ".yml", ".csv"}
_MARKDOWN_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


class _SafeMarkdownParser(HTMLParser):
    """Allow only markup emitted by our Markdown renderer and safe link schemes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag not in _MARKDOWN_TAGS:
            return
        safe_attrs: list[str] = []
        for name, value in attrs:
            if value is None:
                continue
            if tag == "a" and name == "href":
                if urlsplit(value).scheme.lower() not in {"", "http", "https", "mailto"}:
                    continue
                safe_attrs.append(f'href="{html.escape(value, quote=True)}"')
            elif tag == "a" and name == "title":
                safe_attrs.append(f'title="{html.escape(value, quote=True)}"')
            elif tag == "code" and name == "class" and value.startswith("language-"):
                safe_attrs.append(f'class="{html.escape(value, quote=True)}"')
        suffix = f" {' '.join(safe_attrs)}" if safe_attrs else ""
        self.output.append(f"<{tag}{suffix}>")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _MARKDOWN_TAGS and tag not in {"br", "hr"}:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.output.append(html.escape(data, quote=False))


def _render_markdown(raw: str) -> str:
    generated = markdown.markdown(
        html.escape(raw),
        extensions=["fenced_code", "tables", "sane_lists"],
    )
    parser = _SafeMarkdownParser()
    parser.feed(generated)
    parser.close()
    return "".join(parser.output)


def _dossier_summary(payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    required = ("title", "thesis", "decision", "assumptions")
    if not all(key in payload for key in required):
        return None
    assumptions = [
        item for item in payload.get("assumptions", []) if isinstance(item, dict)
    ]
    assumption_details = [
        {
            "statement": item.get("statement", "Unnamed assumption"),
            "status": str(item.get("status", "UNKNOWN")).replace("_", " ").title(),
            "supporting_evidence": len(item.get("evidence_for", [])),
            "contradicting_evidence": len(item.get("evidence_against", [])),
            "independent_lineages": item.get("independent_lineages", 0),
            "supporting_sources": _evidence_display_entries(
                item.get("evidence_for", []), "Supporting evidence"
            ),
            "contradicting_sources": _evidence_display_entries(
                item.get("evidence_against", []), "Contradicting evidence"
            ),
        }
        for item in assumptions
    ]
    supported_statuses = {"RESEARCH_SUPPORTED", "EXPERIMENT_SUPPORTED"}
    supported = sum(
        item.get("status") in supported_statuses for item in assumptions
    )
    evidence_references = sum(
        len(item.get("evidence_for", [])) + len(item.get("evidence_against", []))
        for item in assumptions
    )
    contradictions = sum(len(item.get("evidence_against", [])) for item in assumptions)
    lineages = [
        item.get("independent_lineages")
        for item in assumptions
        if isinstance(item.get("independent_lineages"), int)
    ]
    economics = payload.get("economics", {})
    economics = economics if isinstance(economics, dict) else {}
    ranking = payload.get("ranking", {})
    ranking = ranking if isinstance(ranking, dict) else {}
    gross_margin = economics.get("gross_margin_base")
    if isinstance(gross_margin, (int, float)) and not isinstance(gross_margin, bool):
        gross_margin = f"{gross_margin:.0%}"
    else:
        gross_margin = None
    automation = payload.get("automation_ratio")
    if isinstance(automation, (int, float)) and not isinstance(automation, bool):
        automation = f"{automation:.0%}"
    else:
        automation = None
    description = payload.get("description")
    if not isinstance(description, str) or len(description.split()) < 100:
        description = _legacy_opportunity_description(payload)
    return {
        "title": payload.get("title"),
        "decision": payload.get("decision"),
        "thesis": payload.get("thesis"),
        "description": description,
        "why_now": payload.get("why_now"),
        "customer": payload.get("customer"),
        "buyer": payload.get("buyer"),
        "automation": automation,
        "human_minutes_at_10x": payload.get("human_minutes_per_customer_at_10x"),
        "gross_margin": gross_margin,
        "rank": ranking.get("rank"),
        "stability": ranking.get("stability"),
        "assumption_total": len(assumptions),
        "assumption_supported": supported,
        "evidence_references": evidence_references,
        "contradictions": contradictions,
        "minimum_lineages": min(lineages) if lineages else None,
        "assumptions": assumption_details,
        "unknowns": payload.get("unknowns", []),
        "competitors": payload.get("competitors", []),
        "business_models": payload.get("business_model_variants", []),
        "red_team_findings": payload.get("red_team_findings", []),
        "recommended_experiments": payload.get("recommended_experiments", []),
        "reason_codes": payload.get("reason_codes", []),
    }


def _evidence_display_entries(values: object, fallback: str) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    entries: list[dict[str, str]] = []
    for index, item in enumerate(values, start=1):
        if isinstance(item, dict):
            title = item.get("title")
            summary = item.get("summary")
            url = item.get("url")
            entries.append(
                {
                    "title": title if isinstance(title, str) else f"{fallback} {index}",
                    "summary": summary if isinstance(summary, str) else "",
                    "url": url if isinstance(url, str) else "",
                }
            )
        else:
            entries.append(
                {"title": f"{fallback} {index}", "summary": "", "url": ""}
            )
    return entries


def _legacy_opportunity_description(payload: dict[str, Any]) -> str:
    """Present older dossiers usefully without changing their canonical JSON."""

    def text_value(key: str, fallback: str) -> str:
        value = payload.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else fallback

    competitors = payload.get("competitors", [])
    competitor_text = ", ".join(str(item) for item in competitors) or "existing manual work"
    models = payload.get("business_model_variants", [])
    model_text = ", ".join(str(item) for item in models) or "a recurring digital plan"
    experiments = payload.get("recommended_experiments", [])
    experiment_text = (
        ", ".join(str(item) for item in experiments)
        or "a bounded customer-demand experiment"
    )
    return (
        f"{text_value('title', 'This opportunity')} is a fully digital business "
        f"opportunity for {text_value('customer', 'a defined customer group')}. "
        f"The core proposition is to {text_value('thesis', 'automate a costly, repeated workflow').rstrip('.')}. "
        f"The expected economic buyer is {text_value('buyer', 'the operational owner of the problem')}, "
        "with the product delivered through software rather than recurring manual "
        "services. It would turn fragmented inputs into structured, traceable "
        "outputs that users can review, integrate, and reuse in their normal "
        "workflow. The timing case is based on the following catalyst: "
        f"{text_value('why_now', 'the necessary data and technology are becoming more accessible').rstrip('.')}. "
        f"Current substitutes include {competitor_text}, so differentiation must "
        "come from accuracy, auditability, workflow integration, and lower marginal "
        f"effort. Candidate commercial models include {model_text}. The proposed "
        "service should remain digital across acquisition, onboarding, fulfilment, "
        "support, payment, and geographic scaling. Human work should be limited to "
        "consequential exceptions instead of growing linearly with customer count. "
        f"The present recommendation is {text_value('decision', 'MORE EVIDENCE')}, "
        "but that recommendation remains conditional on the recorded assumptions. "
        f"The next practical validation step is {experiment_text}. That test should "
        "measure observed customer behavior, willingness to pay, output quality, "
        "repeat usage, and integration friction before substantial product investment."
    )


def create_dashboard_app(
    runs_directory: Path = Path("runs"),
    *,
    current_run: str = "current",
    auto_refresh_seconds: int = 3,
    max_text_bytes: int = 5_000_000,
) -> FastAPI:
    """Build an independent, read-only dashboard application."""
    filesystem = DashboardFilesystem(
        runs_directory,
        current_name=current_run,
        max_text_bytes=max_text_bytes,
    )
    app = FastAPI(
        title="DBIE Run Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.dashboard_filesystem = filesystem
    app.mount(
        "/static",
        StaticFiles(directory=_PACKAGE_DIRECTORY / "static"),
        name="static",
    )
    templates = Jinja2Templates(directory=_PACKAGE_DIRECTORY / "templates")

    def selected_run(run_id: str | None) -> str:
        selected = run_id or filesystem.current_run_id()
        if selected is None:
            raise HTTPException(status_code=404, detail="No dashboard runs exist yet")
        try:
            filesystem.resolve_run(selected)
        except DashboardPathError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        return selected

    def index_context(request: Request, run_id: str | None) -> dict[str, Any]:
        runs = filesystem.list_runs()
        if not runs:
            return {
                "request": request,
                "runs": [],
                "run_id": None,
                "conversations": [],
                "deliverables": [],
                "funnel": [],
                "refresh_seconds": auto_refresh_seconds,
            }
        selected = selected_run(run_id)
        return {
            "request": request,
            "runs": runs,
            "run_id": selected,
            "conversations": filesystem.list_files(selected, "conversations"),
            "deliverables": filesystem.list_files(selected, "deliverables"),
            "funnel": filesystem.read_funnel(selected),
            "refresh_seconds": auto_refresh_seconds,
        }

    @app.get("/", name="dashboard_home")
    async def dashboard_home(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=index_context(request, None),
        )

    @app.get("/runs/{run_id}", name="dashboard_run")
    async def dashboard_run(request: Request, run_id: str) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=index_context(request, run_id),
        )

    @app.get("/current", name="dashboard_current")
    async def dashboard_current() -> RedirectResponse:
        return RedirectResponse(url=f"/runs/{selected_run(None)}", status_code=303)

    @app.get(
        "/runs/{run_id}/conversations/{artifact_path:path}",
        name="dashboard_conversation",
    )
    async def dashboard_conversation(
        request: Request, run_id: str, artifact_path: str
    ) -> Any:
        selected = selected_run(run_id)
        try:
            content = filesystem.read_text(selected, "conversations", artifact_path)
        except DashboardPathError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return templates.TemplateResponse(
            request=request,
            name="conversation.html",
            context={
                "request": request,
                "run_id": selected,
                "artifact_path": artifact_path,
                "content": content,
                "refresh_seconds": auto_refresh_seconds,
            },
        )

    @app.get(
        "/runs/{run_id}/deliverables/{artifact_path:path}",
        name="dashboard_deliverable",
    )
    async def dashboard_deliverable(
        request: Request, run_id: str, artifact_path: str
    ) -> Any:
        selected = selected_run(run_id)
        try:
            path = filesystem.resolve_file(selected, "deliverables", artifact_path)
            if path.suffix.lower() == ".md":
                sibling_json = f"{Path(artifact_path).with_suffix('.json').as_posix()}"
                try:
                    sibling_raw = filesystem.read_text(
                        selected, "deliverables", sibling_json
                    )
                    sibling_summary = _dossier_summary(json.loads(sibling_raw))
                except (DashboardPathError, json.JSONDecodeError):
                    sibling_summary = None
                if sibling_summary is not None:
                    mode = "dossier"
                    content = sibling_summary
                else:
                    raw = filesystem.read_text(selected, "deliverables", artifact_path)
                    rendered = _render_markdown(raw)
                    mode = "markdown"
                    content = rendered
            elif path.suffix.lower() in _TEXT_SUFFIXES:
                raw = filesystem.read_text(selected, "deliverables", artifact_path)
                mode = "text"
                content = raw
                if path.suffix.lower() == ".json":
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        pass
                    else:
                        summary = _dossier_summary(parsed)
                        if summary is not None:
                            mode = "dossier"
                            content = summary
                        else:
                            content = json.dumps(parsed, indent=2, sort_keys=True)
            else:
                return FileResponse(path, filename=path.name)
        except DashboardPathError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return templates.TemplateResponse(
            request=request,
            name="deliverable.html",
            context={
                "request": request,
                "run_id": selected,
                "artifact_path": artifact_path,
                "mode": mode,
                "content": content,
                "refresh_seconds": 0,
            },
        )

    @app.get(
        "/current/conversations/{artifact_path:path}",
        name="dashboard_current_conversation",
    )
    async def dashboard_current_conversation(artifact_path: str) -> RedirectResponse:
        return RedirectResponse(
            url=(
                f"/runs/{selected_run(None)}/conversations/"
                f"{quote(artifact_path, safe='/')}"
            ),
            status_code=303,
        )

    @app.get(
        "/current/deliverables/{artifact_path:path}",
        name="dashboard_current_deliverable",
    )
    async def dashboard_current_deliverable(artifact_path: str) -> RedirectResponse:
        return RedirectResponse(
            url=(
                f"/runs/{selected_run(None)}/deliverables/"
                f"{quote(artifact_path, safe='/')}"
            ),
            status_code=303,
        )

    return app
