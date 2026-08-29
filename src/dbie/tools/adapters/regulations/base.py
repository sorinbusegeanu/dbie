from __future__ import annotations

from dbie.tools.adapters.base import ToolAdapter


class RegulatoryAdapter(ToolAdapter):
    authority: str
    jurisdiction: str
