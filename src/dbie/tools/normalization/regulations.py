from __future__ import annotations

from urllib.parse import urlsplit

OFFICIAL_DOMAINS = {
    "EU": {
        "eur-lex.europa.eu",
        "data.europa.eu",
        "publications.europa.eu",
    },
    "CH": {"finma.ch", "www.finma.ch"},
    "EBA": {"eba.europa.eu", "www.eba.europa.eu"},
    "ECB": {"ecb.europa.eu", "www.ecb.europa.eu"},
    "ESMA": {"esma.europa.eu", "www.esma.europa.eu"},
    "US": {"sec.gov", "www.sec.gov"},
}


def is_official_regulatory_url(jurisdiction: str, url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host in OFFICIAL_DOMAINS.get(jurisdiction.upper(), set())
