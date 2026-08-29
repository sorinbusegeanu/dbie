from dbie.tools.adapters.base import ToolAdapter
from dbie.tools.adapters.regulations.official_site import OfficialSiteRegulatorAdapter


def build_sec_adapter(
    search_adapter: ToolAdapter | None = None,
) -> OfficialSiteRegulatorAdapter:
    return OfficialSiteRegulatorAdapter(
        name="sec",
        authority="SEC",
        jurisdiction="US",
        official_domain="sec.gov",
        search_adapter=search_adapter,
    )
