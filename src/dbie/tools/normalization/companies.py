from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

LEGAL_SUFFIXES = {
    "ag",
    "corp",
    "corporation",
    "gmbh",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "sa",
}


class CompanyIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    normalized_name: str
    domain: str | None = None
    jurisdiction: str | None = None
    registry_id: str | None = None
    aliases: list[str] = Field(default_factory=list)


class EntityMatch(BaseModel):
    confidence: float = Field(ge=0, le=1)
    matched: bool
    reasons: list[str]


def normalize_company_name(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return " ".join(token for token in tokens if token not in LEGAL_SUFFIXES)


def normalize_domain(url_or_domain: str | None) -> str | None:
    if not url_or_domain:
        return None
    value = url_or_domain.strip().lower()
    if "://" not in value:
        value = f"https://{value}"
    host = urlsplit(value).hostname
    return host.removeprefix("www.") if host else None


def resolve_company_identity(
    left: CompanyIdentity,
    right: CompanyIdentity,
    *,
    threshold: float = 0.8,
) -> EntityMatch:
    score = 0.0
    reasons: list[str] = []
    if left.registry_id and right.registry_id:
        if left.registry_id == right.registry_id:
            return EntityMatch(
                confidence=1, matched=True, reasons=["REGISTRY_ID_MATCH"]
            )
        return EntityMatch(
            confidence=0, matched=False, reasons=["REGISTRY_ID_CONFLICT"]
        )
    if left.normalized_name == right.normalized_name:
        score += 0.55
        reasons.append("NORMALIZED_NAME_MATCH")
    if left.domain and right.domain and left.domain == right.domain:
        score += 0.4
        reasons.append("DOMAIN_MATCH")
    if (
        left.jurisdiction
        and right.jurisdiction
        and left.jurisdiction == right.jurisdiction
    ):
        score += 0.05
        reasons.append("JURISDICTION_MATCH")
    score = min(score, 1.0)
    return EntityMatch(confidence=score, matched=score >= threshold, reasons=reasons)


def identity(name: str, domain: str | None = None, **values: object) -> CompanyIdentity:
    return CompanyIdentity(
        name=name,
        normalized_name=normalize_company_name(name),
        domain=normalize_domain(domain),
        **values,
    )
