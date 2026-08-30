# DBIE Community Search Adapter

## Operational amendment — 30 August 2026

Reddit Data API access is not available for this deployment. DBIE therefore
replaces the CrewAI-visible `search_reddit` contract with `search_community`
while retaining exactly ten agent-visible tools. PRAW remains an optional,
unregistered future adapter and is not required by `doctor` or `live-run`.

## Sources and evidence treatment

| Source | Acquisition | Returned classification | Use |
|---|---|---|---|
| Stack Exchange | Official API v2.3 search, questions, answers, comments | `OBSERVED_QUALITATIVE` | Repeated technical and operational problems, workarounds, practitioner language |
| Hacker News | Official Firebase v0 Ask/new feeds and comment items | `OBSERVED_QUALITATIVE` | Founder, operator, developer, and buyer discussions |
| GitHub | PyGithub issue search and issue comments | `OBSERVED_QUALITATIVE` | Product limitations, missing workflows, implementation pain, repeated workarounds |
| GitHub Discussions | SearXNG discovery | `DISCOVERY_LEAD` | Locate potentially relevant discussions for corroboration |
| Reddit | SearXNG `site:reddit.com` discovery only | `DISCOVERY_LEAD` | Locate public thread URLs and snippets for independent corroboration |

Search-index snippets are never treated as observed market evidence. DBIE does
not automatically fetch Reddit pages, use Reddit JSON endpoints, replay browser
cookies, use proxies to bypass restrictions, or ingest unofficial Reddit
archives. A Reddit lead must be corroborated by an accessible independent
source before it can support an assumption.

## Logical contract

`search_community` accepts:

- `query`;
- optional `platforms`: `STACK_EXCHANGE`, `HACKER_NEWS`, `GITHUB`, or
  `REDDIT_INDEX`;
- optional `date_from`;
- `sort`: `RELEVANCE`, `NEW`, or `TOP`;
- `max_results`;
- `include_replies`.

It returns two separate collections:

- `signals`: source content that may be assessed as qualitative evidence;
- `discovery_leads`: search-index metadata that requires corroboration.

Every item includes its platform, canonical source URL, stable identifier,
evidence strength, and available timestamps. Retrieved content receives a hash
in Tool Gateway provenance. The output always declares
`reddit_content_automatically_fetched: false`.

## Availability and degradation

The aggregate adapter is ready when at least two of the three qualitative
providers—Stack Exchange, Hacker News, and GitHub—are healthy. Failure of one
provider degrades the result and produces an adapter warning without discarding
successful results from the other providers. SearXNG Reddit/GitHub Discussion
discovery does not count toward the qualitative-provider readiness threshold.

The strict doctor therefore no longer requires Reddit or PRAW credentials.
PRAW can be introduced later only after authorized Reddit Data API access is
approved; doing so must not weaken the evidence classifications above.
