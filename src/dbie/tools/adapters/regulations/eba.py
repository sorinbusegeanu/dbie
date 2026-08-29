from dbie.tools.adapters.base import ToolAdapter
from dbie.tools.adapters.regulations.official_site import OfficialSiteRegulatorAdapter


def build_eba_adapter(
    search_adapter: ToolAdapter | None = None,
) -> OfficialSiteRegulatorAdapter:
    return OfficialSiteRegulatorAdapter(
        name="eba",
        authority="EBA",
        jurisdiction="EBA",
        official_domain="eba.europa.eu",
        search_adapter=search_adapter,
    )
