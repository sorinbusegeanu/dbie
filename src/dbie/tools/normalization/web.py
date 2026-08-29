from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_NAMES = {"fbclid", "gclid", "ref", "source"}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if name.lower() not in TRACKING_QUERY_NAMES
        and not name.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(sorted(query)),
            "",
        )
    )


def deduplicate_results(results: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for result in results:
        url = str(result.get("url", ""))
        canonical = canonicalize_url(url)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        output.append({**result, "canonical_url": canonical})
    return output
