from dbie.tools.adapters.base import ToolAdapter
from dbie.tools.adapters.regulations.official_site import OfficialSiteRegulatorAdapter


def build_esma_adapter(
    search_adapter: ToolAdapter | None = None,
) -> OfficialSiteRegulatorAdapter:
    return OfficialSiteRegulatorAdapter(
        name="esma",
        authority="ESMA",
        jurisdiction="ESMA",
        official_domain="esma.europa.eu",
        search_adapter=search_adapter,
    )
