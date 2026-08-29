from dbie.tools.adapters.base import ToolAdapter
from dbie.tools.adapters.regulations.official_site import OfficialSiteRegulatorAdapter


def build_finma_adapter(
    search_adapter: ToolAdapter | None = None,
) -> OfficialSiteRegulatorAdapter:
    return OfficialSiteRegulatorAdapter(
        name="finma",
        authority="FINMA",
        jurisdiction="CH",
        official_domain="finma.ch",
        search_adapter=search_adapter,
    )
