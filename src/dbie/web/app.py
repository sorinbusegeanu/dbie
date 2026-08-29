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
                "refresh_seconds": auto_refresh_seconds,
            }
        selected = selected_run(run_id)
        return {
            "request": request,
            "runs": runs,
            "run_id": selected,
            "conversations": filesystem.list_files(selected, "conversations"),
            "deliverables": filesystem.list_files(selected, "deliverables"),
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
                raw = filesystem.read_text(selected, "deliverables", artifact_path)
                rendered = _render_markdown(raw)
                mode = "markdown"
                content = rendered
            elif path.suffix.lower() in _TEXT_SUFFIXES:
                raw = filesystem.read_text(selected, "deliverables", artifact_path)
                if path.suffix.lower() == ".json":
                    try:
                        raw = json.dumps(json.loads(raw), indent=2, sort_keys=True)
                    except json.JSONDecodeError:
                        pass
                mode = "text"
                content = raw
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
