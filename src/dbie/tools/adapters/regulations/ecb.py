from dbie.tools.adapters.base import ToolAdapter
from dbie.tools.adapters.regulations.official_site import OfficialSiteRegulatorAdapter


def build_ecb_adapter(
    search_adapter: ToolAdapter | None = None,
) -> OfficialSiteRegulatorAdapter:
    return OfficialSiteRegulatorAdapter(
        name="ecb",
        authority="ECB",
        jurisdiction="ECB",
        official_domain="ecb.europa.eu",
        search_adapter=search_adapter,
    )
