from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)
from dbie.tools.normalization.documents import document_hash, extraction_quality


class PlaywrightAdapter(ToolAdapter):
    name = "playwright"
    capabilities = AdapterCapabilities(
        operations={"fetch_page"}, media_types={"text/html"}
    )

    def health(self) -> AdapterHealth:
        try:
            installed = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if installed.returncode != 0 or "chromium-" not in installed.stdout:
                return AdapterHealth(
                    name=self.name,
                    available=False,
                    version=version("playwright"),
                    detail="Chromium binary is not installed",
                )
            return AdapterHealth(
                name=self.name, available=True, version=version("playwright")
            )
        except (
            PackageNotFoundError,
            ImportError,
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        from playwright.sync_api import sync_playwright

        started = datetime.now(UTC)
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(
                str(request.arguments["url"]),
                wait_until="networkidle",
                timeout=int(request.timeout_seconds * 1000),
            )
            content = page.locator("body").inner_text()
            final_url = page.url
            browser.close()
        quality = extraction_quality(content)
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={
                "url": final_url,
                "content": content,
                "links": [],
                "quality": quality,
            },
            raw_sources=[
                {
                    "source_identifier": final_url,
                    "source_url": final_url,
                    "source_type": "rendered_web_page",
                    "content_hash": document_hash(content.encode()),
                }
            ],
            warnings=list(quality["warnings"]),
            resource_usage={"browser_launches": 1},
            started_at=started,
            ended_at=ended,
            adapter_version=version("playwright"),
        )
