from __future__ import annotations

from hashlib import sha256


def document_hash(content: bytes) -> str:
    return sha256(content).hexdigest()


def extraction_quality(text: str, *, minimum_chars: int = 200) -> dict[str, object]:
    stripped = text.strip()
    warnings: list[str] = []
    if not stripped:
        warnings.append("EMPTY_CONTENT")
    elif len(stripped) < minimum_chars:
        warnings.append("NEAR_EMPTY_CONTENT")
    lowered = stripped.lower()
    if "enable javascript" in lowered or "javascript required" in lowered:
        warnings.append("DYNAMIC_RENDER_REQUIRED")
    if "sign in" in lowered and len(stripped) < 1000:
        warnings.append("SUSPECTED_LOGIN_OR_PAYWALL")
    return {"meaningful": not warnings, "warnings": warnings, "chars": len(stripped)}
