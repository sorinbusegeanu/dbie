**  
DIGITAL BUSINESS IDEA ENGINE**

CrewAI-Based System for Generating, Validating, Ranking, and Learning
from Fully Digital Business Ideas

System Design v0.5  
29 August 2026

v0.5 revision focus: explicit runtime and harness architecture; CrewAI as the sole agent harness; custom deterministic domain/control code; provider-neutral model routing; vLLM and Ollama as interchangeable serving backends; Ministral 3 14B as a lower-VRAM primary-model option alongside gpt-oss-20b; and a strict separation between agent orchestration, domain decisions, inference serving, and tools.

v0.4 retained focus: explicit MVP tool architecture for ten core digital tools; actor-level tool ownership; CrewAI/MCP integration; typed call contracts; invocation rules; provenance; and execution guardrails.

v0.3 retained focus: gpt-oss-20b as the primary local agent model;
explicit model-independence levels; evidence-first escalation;
heterogeneous judge routing; and real-market experiments as the
highest-trust validation layer.

**Primary design principle: only businesses whose complete value chain
can be implemented and operated using digital tools are eligible.**

# 1. Executive Summary

The Digital Business Idea Engine (DBIE) is an autonomous,
evidence-driven multi-agent system that continuously discovers market
problems, generates digital-only business concepts, decomposes each
concept into falsifiable assumptions, validates those assumptions
against external evidence, red-teams them, designs low-cost real-world
experiments, observes outcomes, and updates its beliefs. The purpose is
not to produce persuasive business plans; it is to reduce uncertainty
until an opportunity is sufficiently supported to justify a human build
or investment decision.

CrewAI Flows provide the deterministic outer workflow and state
transitions; specialized Crews provide bounded autonomy for research,
ideation, validation, debate, and diligence. The architecture
intentionally separates idea generation from evaluation so that the same
agent that creates an idea cannot validate it. The default inference
architecture uses one shared local gpt-oss-20b server for most agent
work, with bounded concurrency and selective escalation rather than a
separate model instance per agent.

The system is explicitly designed against a common failure mode of
LLM-based ideation: multiple agents creating mutually reinforcing
narratives. Important judgments are represented as assumptions and
claims linked to supporting evidence, counter-evidence, unknowns, source
lineage, measured outcomes, and confidence. External observations and
deterministic calculations outrank model opinion; LLM-generated
estimates cannot silently become facts. Model diversity is treated as a
validation resource: repeated calls to the same model are not considered
independent evidence, and stronger or different-family models are
invoked only when escalation criteria justify the cost.

## 1.1 Target Outcome

Given a broad search mandate, the system produces a ranked portfolio of
digital opportunities with investment-style memos, uncertainty maps,
falsifiable assumptions, and recommended experiments. It processes
hundreds of raw opportunities cheaply, reserves expensive research for
survivors, and reserves real-world experiments for a small number of
finalists.

500 observed problems / signals  
↓  
250–500 raw business ideas  
↓  
50–100 digital-only + evidence-qualified candidates  
↓  
15–25 assumption-validated candidates  
↓  
5–10 red-team survivors  
↓  
3–5 experiment candidates  
↓  
observed market behavior / prototype evidence  
↓  
ranked build / kill / iterate recommendations

# 2. Goals and Non-Goals

## 2.1 Goals

- Generate novel business ideas from observed problems and market
  changes rather than from unconstrained brainstorming.

- Allow only businesses that can be built, sold, delivered, operated,
  supported, and scaled using digital tools.

- Ground important conclusions in traceable external evidence.

- Use independent and adversarial evaluators to reduce confirmation
  bias.

- Rank ideas using both structured scoring and pairwise tournament
  comparison.

- Persist opportunity, evidence, competitor, assumption, and evaluation
  knowledge across runs.

- Preserve novelty by explicitly searching beyond already-visible SaaS
  categories and saturated market narratives.

- Validate finalists with real digital experiments whenever market
  behavior can be observed cheaply.

- Separate measured facts, inferred estimates, model judgments, and
  unknowns in every decision.

- Treat assumptions—not prose reports or aggregate idea scores—as the
  primary unit of uncertainty reduction.

- Learn which classes of ideas repeatedly succeed or fail the evaluation
  criteria.

- Run primarily on a shared local gpt-oss-20b endpoint with bounded
  parallelism, escalating only when evidence quality or decision risk
  requires stronger independence.

- Produce auditable artifacts suitable for human review before capital
  or implementation decisions.

## 2.2 Non-Goals

- Automatically incorporating companies, opening bank accounts, signing
  contracts, or moving money.

- Autonomously launching businesses without an explicit approval gate.

- Treating simulated LLM customers, personas, or judges as substitutes
  for observed customer behavior.

- Treating LLM confidence as market evidence.

- Optimizing for businesses that require physical goods, inventory,
  facilities, field service, or proprietary hardware.

# 3. Digital-Only Eligibility Contract

Digital-only feasibility is a hard eligibility contract. Failure of any
mandatory criterion terminates the candidate before full validation.

| **Dimension**     | **Mandatory requirement**                                                                                    | **Examples of rejection**                                           |
|-------------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| Product / service | Core customer value is delivered as software, data, API, digital content, or remotely executed digital work. | Physical goods, manufacturing, hardware appliance.                  |
| Acquisition       | Customers can be reached through digital or remote channels.                                                 | Depends on physical retail footfall or local field sales.           |
| Sales             | Transaction can complete remotely or self-service.                                                           | Requires on-site demo or physical inspection as an inherent step.   |
| Fulfilment        | Fulfilment is software/API/agent/remote-service based.                                                       | Shipping, warehousing, installation, physical logistics.            |
| Operations        | Normal operations can be run remotely with software tooling.                                                 | Local facilities or a field workforce required for normal delivery. |
| Infrastructure    | Cloud, SaaS, APIs, commodity compute, or downloadable software are sufficient.                               | Custom proprietary hardware required.                               |
| Payments          | Billing and settlement can be electronic.                                                                    | Cash/local physical collection is intrinsic to the model.           |
| Support           | Support can be delivered remotely and increasingly automated.                                                | On-site maintenance intrinsic to customer value.                    |
| Scaling           | Marginal revenue does not require proportional physical resources.                                           | Every incremental customer requires a new physical asset.           |
| Geography         | Expansion does not require a new physical deployment footprint.                                              | New facilities required country by country.                         |

A digital professional service may pass the digital-delivery gate but
still fail the system mandate. Therefore DBIE applies a second hard
gate: autonomous scalability. A candidate must have a plausible path to
increasing revenue substantially faster than required human operating
hours. Remote consulting, manual AI agencies, or labor-linear services
are rejected unless the proposed design contains a credible measurable
transition to software/agent execution.

Autonomous-scalability gate: the design must define target automation
ratio, human minutes per customer or transaction, expected marginal
human burden at 10× scale, and the operational tasks that remain
human-only. These quantities may initially be hypotheses, but they must
be testable.

# 4. Architectural Principles

| **Principle**                             | **Design consequence**                                                                                                                                                |
|-------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Evidence before narrative                 | Claims require sources, timestamps, provenance, and counter-evidence.                                                                                                 |
| Generation ≠ evaluation                   | Independent agents/crews perform ideation, validation, red-team, and ranking.                                                                                         |
| Cheap filters first                       | Deterministic and low-cost gates run before deep research.                                                                                                            |
| Structured outputs                        | All inter-stage contracts use typed schemas; prose is a presentation layer.                                                                                           |
| Bounded autonomy                          | Agents receive least-privilege tools, budgets, deadlines, and explicit task boundaries.                                                                               |
| Deterministic outer control               | CrewAI Flow owns routing, retries, state, checkpoints, approvals, and failure handling.                                                                               |
| Agentic inner work                        | Crews handle open-ended research, synthesis, debate, and hypothesis generation.                                                                                       |
| Persistent learning                       | Facts and evaluations are stored as reusable graph entities, not discarded after a report.                                                                            |
| Reproducibility                           | Model, prompt/config version, source set, score version, and execution metadata are recorded.                                                                         |
| Human control at consequential boundaries | Human approval is required before spending material money, launching, contacting prospects at scale, or deploying production systems.                                 |
| Assumption-centric reasoning              | Ideas are decomposed into falsifiable assumptions; progress means reducing uncertainty, not increasing narrative detail.                                              |
| Outcome over model opinion                | Observed behavior and deterministic measurements outrank LLM judgments, synthetic personas, and repeated-agent consensus.                                             |
| Independence, not agent count             | Evidence and evaluators must be meaningfully independent; many agents using the same model/context do not count as independent validation.                            |
| Novelty preservation                      | Search explicitly includes capability inversion, cross-industry analogy, non-obvious combinations, and neglected problems rather than only visible market categories. |
| Learning from outcomes                    | Historical predictions are stored separately from later outcomes; future priors are updated only from calibrated evidence and observed results.                       |

# 5. Logical Architecture

┌──────────────────────────────────────────────────────────────────────┐  
│ CONTROL PLANE │  
│ CrewAI Flow • state • routing • budgets • approvals • experiments │  
└───────────────┬──────────────────────────────────────────────────────┘  
│  
┌───────────▼──────────┐ ┌────────────────────────────────┐  
│ Opportunity Discovery│─────▶│ Evidence / Assumption Store │  
└───────────┬──────────┘ │ source lineage • outcomes │  
▼ └──────────────┬─────────────────┘  
┌──────────────────────┐ │  
│ Diverse Idea Search │ │  
└───────────┬──────────┘ │  
▼ │  
┌──────────────────────┐ │  
│ Digital + Autonomous │ │  
│ Scalability Gates │ │  
└───────────┬──────────┘ │  
▼ │  
┌──────────────────────┐◀────────────────────┘  
│ Assumption Decomposer│  
└───────────┬──────────┘  
▼  
┌──────────────────────┐  
│ Evidence Validation │  
│ + Independent RedTeam│  
└───────────┬──────────┘  
▼  
┌──────────────────────┐  
│ Uncertainty + Pairwise│  
│ Portfolio Selection │  
└───────────┬──────────┘  
▼  
┌──────────────────────┐  
│ Digital Experiment │  
│ Design + Approval │  
└───────────┬──────────┘  
▼  
┌──────────────────────┐  
│ Observe Real Outcomes│  
└───────────┬──────────┘  
▼  
BUILD / ITERATE / KILL  
│  
└──────────────▶ calibrated learning loop

# 6. CrewAI Execution Model

Current CrewAI documentation distinguishes Crews for autonomous
collaboration from Flows for structured event-driven orchestration,
state, persistence, branching, and resumability. This system uses both:
the Flow is authoritative for lifecycle and state; Crews are invoked as
bounded capabilities inside the Flow.

## 6.1 Top-Level Flow

1.  initialize_run — load mandate, policy, scoring version, budgets, and
    prior knowledge.

2.  discover_signals — invoke discovery crew and deduplicate against
    persistent knowledge.

3.  generate_ideas — create deliberately diverse business formulations
    using multiple search mechanisms, including cross-industry analogy
    and capability inversion.

4.  eligibility_gate — deterministic digital-only,
    autonomous-scalability, and structural rejection.

5.  decompose_assumptions — convert each survivor into explicit demand,
    buyer, pricing, distribution, automation, feasibility,
    defensibility, and economics assumptions.

6.  validate — seek evidence for and against each critical assumption;
    classify evidence as measured, observed, inferred, model-judged, or
    unknown.

7.  model_business — generate and compare viable digital business models
    while preserving their distinct assumptions and economics.

8.  red_team — independently attempt to falsify critical assumptions and
    detect correlated evidence or evaluator agreement.

9.  prioritize_uncertainty — rank candidates using hard evidence gates,
    uncertainty, pairwise comparison, and expected value of further
    information; avoid false precision.

10. design_experiments — design the cheapest digital experiment capable
    of falsifying each unresolved critical assumption.

11. observe_and_decide — after approved experiments, ingest measured
    outcomes and recommend BUILD, ITERATE, KILL, or MORE_EVIDENCE.

12. finalize_and_learn — produce memos, uncertainty maps, experiment
    results, decision rationale, and calibrated learning updates.

13. checkpoint — persist run state so interrupted work can resume.

# 7. Agent and Crew Design

## 7.1 Opportunity Discovery Crew

| **Agent**        | **Objective**                                                                | **Primary tools**                       | **Output**            |
|------------------|------------------------------------------------------------------------------|-----------------------------------------|-----------------------|
| Trend Scout      | Find meaningful technological, economic, regulatory, and behavioral changes. | Web/news/search, research sources       | Signal records        |
| Pain-Point Miner | Find expensive, frequent, or risky customer problems.                        | Forums, reviews, job posts, communities | Problem records       |
| Industry Analyst | Identify inefficient workflows and value-chain friction.                     | Web, company data, industry sources     | Opportunity maps      |
| Regulatory Scout | Find obligations that create mandatory spend or new workflows.               | Regulatory portals, legal search        | Regulatory triggers   |
| Technology Scout | Find capabilities that newly reduce cost or enable new products.             | GitHub, model/tool docs, papers         | Technology enablers   |
| Contrarian Scout | Search for neglected niches and reasons conventional views may be wrong.     | Same sources, different objective       | Contrarian hypotheses |

## 7.2 Idea Generation Crew

Generation is diversified by mechanism. Multiple agents receive the same
qualified problem but are instructed to create ideas through different
business-design lenses. This produces genuine search diversity rather
than many copies of the same prompt.

| **Generator lens**        | **Question**                                                                    |
|---------------------------|---------------------------------------------------------------------------------|
| AI-native automation      | Can the workflow be largely executed by autonomous software agents?             |
| Vertical SaaS             | Can this become a focused system of record/workflow for one industry?           |
| API / infrastructure      | Can the capability be sold as a programmable primitive?                         |
| Data product              | Can unique aggregation, transformation, or inference become the product?        |
| Compliance / assurance    | Does regulation or risk create recurring mandatory demand?                      |
| Developer tool            | Can the problem be solved inside software delivery or operations?               |
| Service-to-software       | Can a remote expert workflow be productized and progressively automated?        |
| Marketplace / network     | Can digital participants create a reinforcing two-sided network?                |
| Business-model innovation | Can pricing/distribution change make an existing solution substantially better? |
| Newly possible            | What has become feasible because of a recent cost/capability discontinuity?     |

## 7.3 Novelty Search and Search-Space Diversity

Novelty is a controlled search objective, not a synonym for obscurity.
Before validation, the system measures similarity against the persistent
opportunity graph and asks dedicated agents to search through capability
inversion, cross-industry transfer, unusual buyer/problem pairings,
neglected workflows, and combinations of independently validated
primitives. Novel wording does not count as novelty.

A candidate receives a novelty bonus only when it is both meaningfully
distinct from known alternatives and supported by a credible problem.
Highly novel but unevidenced concepts remain hypotheses and cannot
outrank evidence-backed opportunities solely on originality.

## 7.4 Validation Crew

| **Agent**              | **Mandate**                                                                                                           | **Must not do**                                                             |
|------------------------|-----------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| Demand Analyst         | Find evidence that the problem exists, is frequent, urgent, and budgeted.                                             | Treat idea description as evidence.                                         |
| Skeptic                | Find evidence that demand is weak or the problem is tolerable.                                                        | Optimize for agreement.                                                     |
| Competitive Analyst    | Map direct, adjacent, internal-build, and status-quo alternatives.                                                    | Only search for exact product-name competitors.                             |
| Buyer Analyst          | Identify buyer, user, budget owner, procurement constraints, and buying triggers.                                     | Invent willingness-to-pay.                                                  |
| Economics Analyst      | Model plausible price, gross margin, CAC range, support burden, and payback.                                          | Hide uncertain assumptions.                                                 |
| Technical Analyst      | Assess whether available digital tools can implement the product.                                                     | Assume proprietary breakthroughs.                                           |
| Distribution Analyst   | Identify credible acquisition channels and bottlenecks.                                                               | Equate market size with reachable demand.                                   |
| Assumption Auditor     | Decompose the candidate into falsifiable assumptions; identify which assumptions can independently kill the business. | Collapse several assumptions into one vague “market attractiveness” score.  |
| Source-Lineage Analyst | Detect derivative, syndicated, copied, or common-origin sources and calculate effective evidence independence.        | Count URLs as independent evidence simply because they are different pages. |
| Calibration Judge      | Compare prior model predictions with later observed outcomes and estimate evaluator calibration by task type.         | Treat evaluator confidence as calibrated without historical evidence.       |

## 7.5 Red-Team Crew

The red team has a deliberately asymmetric objective: kill the idea if
credible evidence supports rejection. Its score cannot be overwritten by
the original generator.

- Market too small or not reachable

- Problem lacks urgency

- Incumbent response

- AI/software commoditization

- Customer inertia and switching costs

- Poor unit economics

- Weak distribution

- Technical dependency or platform risk

- Regulatory/legal constraints

- Easy replication / weak defensibility

- Hidden human-service burden

- Data-access or licensing risk

# 8. Tool Architecture

Agents do not receive unrestricted access to all tools. A Tool Gateway
provides least-privilege capabilities, quotas, audit logs, domain
restrictions, caching, and approval requirements. CrewAI supports custom
tools/APIs and current documentation includes web scraping/browser tools
and structured research integrations; MCP can be used as an
interoperability boundary for external tools.

| **Tool class**                      | **Purpose**                                                       | **Typical implementations**                                           | **Risk class**                           |
|-------------------------------------|-------------------------------------------------------------------|-----------------------------------------------------------------------|------------------------------------------|
| Search / research                   | Discover sources and market evidence.                             | Search API, Tavily-style research, curated feeds                      | Low                                      |
| Web fetch / browser                 | Read pages and interact with dynamic sites.                       | HTTP fetch, Playwright/Selenium, managed browser                      | Medium                                   |
| Company intelligence                | Competitors, pricing, positioning, financial/public data.         | Public APIs, datasets, search                                         | Low–Medium                               |
| Regulatory                          | Official rules, guidance, consultations, changes.                 | Government/EU/industry sources                                        | Low                                      |
| Community evidence                  | Pain points and practitioner language.                            | Forums, Reddit, reviews, communities                                  | Medium                                   |
| GitHub / software ecosystem         | Assess technical feasibility and ecosystem saturation.            | GitHub API/search                                                     | Low                                      |
| Financial model                     | Unit economics, scenarios, sensitivity.                           | Deterministic Python functions                                        | Low                                      |
| Database / knowledge graph          | Store and query persistent entities/evidence.                     | PostgreSQL + vector/graph extension                                   | Low                                      |
| Code sandbox                        | Prototype calculations or proof-of-concept logic.                 | Isolated container                                                    | Medium                                   |
| Outbound communication              | Optional later-stage interviews/outreach.                         | Email/CRM APIs                                                        | High; human approval required            |
| Experiment instrumentation          | Measure real behavior in approved digital experiments.            | Analytics, event tracking, form/waitlist metrics, experiment database | Medium                                   |
| Prototype / landing-page deployment | Create isolated digital prototypes for demand or usability tests. | Static hosting, sandbox app platform, feature flag/test environment   | High; approval for public exposure/spend |
| Advertising / acquisition test      | Test channel response, CTR, CPC, signup or lead conversion.       | Ad platform APIs or managed campaign tool                             | High; explicit spend approval            |
| Interview / outreach capture        | Record structured customer/prospect responses.                    | CRM, forms, approved email/calendar connectors                        | High; human approval                     |

## 8.1 Tool Safety Policy

- Research agents are read-only by default.

- All external requests are logged with agent, task, query, timestamp,
  and source.

- Browser actions that submit forms, create accounts, purchase, post, or
  send messages require a separate permission.

- Code execution occurs in a sandbox without production credentials.

- Outbound contact, financial spend, or public publication requires
  human approval.

- Per-run and per-agent quotas cap search volume, browser time, tokens,
  and external API spend.

## 8.2 MVP Tool Set: Required Ten Tools

The first production-capable implementation MUST expose exactly the following ten logical tools to CrewAI. A logical tool may wrap more than one provider internally, but agents call the stable DBIE contract rather than provider-specific SDKs. This prevents Crew code from depending on Tavily, Serper, Reddit, GitHub, PostgreSQL, or another vendor directly.

| ID | CrewAI logical tool | Recommended implementation | Primary actors | Call only when | Must not be used for |
|---|---|---|---|---|---|
| T01 | `web_search` | Search API adapter; preferred: Tavily or Serper, with provider fallback | Trend Scout, Pain-Point Miner, Market Analyst, Competitor Analyst, Red Team | Discovery of candidate sources, competitors, statistics, market changes, terminology, or corroborating/contradicting evidence | Treating snippets as evidence; final factual extraction without opening the source |
| T02 | `fetch_page` | HTTP reader first; Playwright/managed browser fallback for JS pages | Evidence Researcher, Market Analyst, Competitor Analyst, Source-Lineage Analyst, Red Team | A URL has been selected and its primary content must be read, quoted, structured, or lineage-checked | Broad discovery; autonomous form submission; login/paywall circumvention |
| T03 | `search_reddit` | Reddit API/search adapter with post/comment retrieval and metadata | Pain-Point Miner, Customer-Pain Analyst, Distribution Analyst, Red Team | Looking for recurring practitioner pain, workarounds, buying language, switching behavior, complaints, or counterevidence | Establishing market size, legal facts, or treating anecdotes as representative statistics |
| T04 | `search_companies` | Company-intelligence adapter over public web plus optional Crunchbase/Dealroom/Tracxn connectors | Competitor Analyst, Market Analyst, Distribution Analyst, Red Team | Identifying competitors, entrants, positioning, funding, customer segments, company density, or comparable vendors | Inventing revenue/employee/funding data when unavailable; silently merging similarly named companies |
| T05 | `search_github` | GitHub API/search; optionally repository metadata/code search | Technology Scout, Technical Analyst, Prototype/Feasibility Agent, Red Team | Assessing whether enabling technology exists, ecosystem maturity, OSS alternatives, developer activity, integration feasibility, or commoditization | Executing arbitrary repository code; treating stars alone as demand evidence |
| T06 | `search_regulations` | Curated official-source search over EUR-Lex, EU Commission, FINMA, EBA, ECB, ESMA, SEC and configured authorities | Regulatory Scout, Regulatory Analyst, Red Team | A business opportunity depends on a regulation, mandate, compliance obligation, deadline, license, restriction, or regulatory change | Legal advice; reliance on blogs when an authoritative primary source exists |
| T07 | `read_document` | PDF/HTML/Office/text extraction service with metadata and page/section references | Evidence Researcher, Regulatory Analyst, Market Analyst, Technical Analyst | A report, filing, paper, policy, PDF, spreadsheet, or document contains relevant primary evidence | Summarizing an unseen document from a search snippet or title |
| T08 | `python_execute` | Isolated Python container with no production credentials and bounded CPU/RAM/time | Economics Analyst, Calibration Judge, Technical Analyst, Scoring Service caller | Deterministic calculations, sensitivity analysis, statistics, deduplication, simulations, evidence clustering, calibration, or prototype micro-tests are required | Network access by default; arbitrary production changes; replacing a deterministic service with prose arithmetic |
| T09 | `database_query` | PostgreSQL through a DBIE data-access service; parameterized reads and constrained writes | Flow Controller, Evidence Researcher, Assumption Auditor, Source-Lineage Analyst, Calibration Judge | Reading/writing canonical ideas, assumptions, claims, evidence, source lineage, outcomes, run metadata, and evaluation records | Raw unrestricted SQL from agents; schema changes; destructive operations |
| T10 | `semantic_memory_search` | PostgreSQL + pgvector initially; separate vector DB only if justified later | All research/validation actors; especially Discovery, Ideation, Assumption Auditor, Red Team | Retrieving prior related ideas, problems, assumptions, evidence, competitors, experiments, or lessons before duplicate research is performed | Treating remembered judgments as fresh evidence; allowing prior rankings to bias independent validation without provenance |

The MVP SHOULD NOT add advertising, outbound email, public deployment, CRM mutation, payments, or production cloud-management tools. Those belong to a later experiment-execution tier because they create external side effects.

## 8.3 CrewAI Integration Pattern

CrewAI agents MUST receive DBIE logical tools through their `tools` configuration. Provider credentials and provider-specific SDK objects remain below the Tool Gateway. A tool is implemented either as a CrewAI custom `BaseTool`/decorated tool or as an MCP-exposed capability wrapped by the same logical contract. The preferred boundary is:

```text
CrewAI Flow
   |
   +-- invokes bounded Crew / Agent
           |
           +-- tool name + typed arguments
                   |
              DBIE Tool Gateway
                   |
          policy / quota / cache / audit
                   |
        provider adapter or MCP client
                   |
          external service / sandbox
```

The CrewAI layer sees only stable names such as `web_search` or `search_github`. It MUST NOT know API keys or provider-specific endpoints. Provider switching is therefore a Tool Gateway concern, not an agent prompt change.

Each agent has an explicit allowlist. A tool call not on that actor's allowlist is rejected by the gateway even if the model attempts to call it. The Flow owns stage-level budgets and may further restrict an agent's normal allowlist for a specific task.

## 8.4 Common Tool Call Envelope

Every tool invocation MUST be represented internally by a common envelope before execution:

```json
{
  "run_id": "...",
  "stage_id": "...",
  "task_id": "...",
  "agent_id": "...",
  "idea_id": "optional",
  "assumption_id": "optional",
  "tool": "web_search",
  "arguments": {},
  "purpose": "one-sentence reason for this call",
  "expected_evidence": "what result would support or contradict the current assumption",
  "independence_requirement": "NONE|NEW_SOURCE_FAMILY|PRIMARY_SOURCE",
  "max_cost": 0.0,
  "timeout_seconds": 30
}
```

The gateway adds provider, start/end timestamps, cache status, cost, response hash, error state, and provenance before persisting the call. The LLM does not choose or modify `run_id`, credentials, quotas, or policy fields.

## 8.5 Tool-Specific Call Contracts and Invocation Rules

### T01 — `web_search`

**Actors:** Trend Scout, Pain-Point Miner, Market Analyst, Competitor Analyst, Distribution Analyst, Red Team.

**Call when:** the actor needs to discover candidate sources or test whether an assertion has external support or contradiction. Discovery actors may use it broadly; validation actors MUST tie each call to an assumption or claim.

**Input contract:**

```json
{
  "query": "string",
  "intent": "DISCOVERY|SUPPORT|CONTRADICT|COMPETITOR|MARKET_SIZE|PRICING|DISTRIBUTION",
  "date_from": "optional ISO date",
  "date_to": "optional ISO date",
  "domains_allow": ["optional"],
  "domains_deny": ["optional"],
  "max_results": 10
}
```

**Output:** ranked URLs with title, snippet, source domain, publication date when available, result type, and provider metadata.

**Required follow-up:** snippets are discovery material only. Any result used as evidence MUST normally be opened with `fetch_page` or `read_document`, unless the source is a structured API whose returned field is itself the primary data.

**Call discipline:** one focused query per uncertainty. Avoid query floods that merely paraphrase the same proposition. Cache identical normalized queries within a run.

### T02 — `fetch_page`

**Actors:** Evidence Researcher, Market Analyst, Competitor Analyst, Source-Lineage Analyst, Red Team.

**Call when:** a specific public URL discovered by search, memory, or another document contains potentially decision-relevant evidence.

**Input contract:**

```json
{
  "url": "https://...",
  "mode": "READ|EXTRACT",
  "extract_fields": ["optional typed fields"],
  "render_js": "AUTO|NO|YES",
  "max_chars": 50000
}
```

**Output:** canonical URL, page title, publication/update date when detectable, author/publisher, extracted text, structured fields, HTTP metadata, content hash, and links to likely primary sources.

**Rules:** use simple HTTP retrieval first; browser rendering is fallback. Never submit forms, authenticate, purchase, post, or bypass access controls in the MVP. Source-Lineage Analyst uses canonical URL, content hashes, citations, and publication relationships to identify derivative sources.

### T03 — `search_reddit`

**Actors:** Pain-Point Miner, Customer-Pain Analyst, Distribution Analyst, Red Team.

**Call when:** the system needs qualitative evidence about recurring pain, current workarounds, willingness language, switching friction, practitioner terminology, or reasons existing tools fail.

**Input contract:**

```json
{
  "query": "string",
  "subreddits": ["optional"],
  "date_from": "optional ISO date",
  "sort": "RELEVANCE|NEW|TOP",
  "max_threads": 20,
  "include_comments": true
}
```

**Output:** thread/comment text, permalink, subreddit, timestamps, scores, author pseudonym/hash where policy permits, and engagement metadata.

**Rules:** Reddit observations are `OBSERVED_QUALITATIVE`, not market-size measurements. Multiple comments in one thread are one source family for independence scoring unless there is evidence of genuinely independent observations. Personally identifying information is not persisted unless required and permitted.

### T04 — `search_companies`

**Actors:** Competitor Analyst, Market Analyst, Distribution Analyst, Red Team.

**Call when:** evaluating market structure, competitor density, comparable products, funding, positioning, buyer segments, or likely distribution channels.

**Input contract:**

```json
{
  "query": "string",
  "mode": "COMPETITORS|COMPANY_LOOKUP|CATEGORY|FUNDING|POSITIONING",
  "geography": ["optional"],
  "max_results": 25
}
```

**Output:** normalized company records with aliases, URLs, product/category description, geography, founded date, funding/public financial fields when sourced, evidence URLs, and confidence in entity resolution.

**Rules:** every numeric company field must carry its source and observation date. The tool returns `UNKNOWN`, not an LLM estimate, for unavailable revenue, headcount, funding, or customers. Entity resolution must preserve source records so similarly named companies cannot be silently merged.

### T05 — `search_github`

**Actors:** Technology Scout, Technical Analyst, Prototype/Feasibility Agent, Red Team.

**Call when:** the opportunity depends on existing software capabilities, APIs, open-source projects, developer ecosystems, implementation complexity, commoditization, or integration availability.

**Input contract:**

```json
{
  "query": "string",
  "mode": "REPOSITORIES|CODE|ISSUES|TOPICS",
  "language": "optional",
  "updated_after": "optional ISO date",
  "max_results": 20
}
```

**Output:** repository identifiers, description, license, last update, stars/forks/watchers when available, contributors/activity indicators, topics, relevant files/issues, and canonical GitHub URLs.

**Rules:** popularity metrics are ecosystem signals, not demand proof. Repository code is never executed automatically. If a feasibility test requires execution, the Flow must explicitly pass selected code or a minimal reimplementation into the isolated `python_execute`/prototype sandbox after policy checks.

### T06 — `search_regulations`

**Actors:** Regulatory Scout, Regulatory Analyst, Red Team.

**Call when:** an idea depends on a legal/regulatory obligation, compliance deadline, regulator guidance, required control, reporting requirement, license, prohibition, or rule change.

**Input contract:**

```json
{
  "query": "string",
  "jurisdictions": ["EU", "CH"],
  "authorities": ["optional configured authorities"],
  "status": "IN_FORCE|PROPOSED|CONSULTATION|ANY",
  "date_from": "optional ISO date",
  "max_results": 20
}
```

**Output:** official instrument/guidance title, authority, jurisdiction, status, relevant dates, official URL, affected entities where extractable, and text excerpts/references.

**Rules:** official primary sources rank above summaries. Secondary commentary may aid discovery but cannot establish the controlling regulatory claim when a primary source is available. The tool produces research evidence, not legal advice. Material ambiguity is escalated to human/legal review rather than resolved by model voting.

### T07 — `read_document`

**Actors:** Evidence Researcher, Regulatory Analyst, Market Analyst, Technical Analyst, Economics Analyst.

**Call when:** decision-relevant evidence resides in a PDF, report, filing, spreadsheet, paper, policy, or long-form document.

**Input contract:**

```json
{
  "source": "URL or stored document_id",
  "query": "what information is needed",
  "sections": ["optional"],
  "tables": true,
  "max_pages": 100
}
```

**Output:** document metadata, matched passages with page/section coordinates, extracted tables where possible, dates/authors/publisher, and content hash.

**Rules:** downstream claims must retain page/section references. The system must not cite a document that was only mentioned by a search result. For large documents, retrieval may be staged, but evidence must point to the actual source range used.

### T08 — `python_execute`

**Actors:** Economics Analyst, Calibration Judge, Technical Analyst, Source-Lineage Analyst, Scoring/Portfolio service caller.

**Call when:** a result is better produced deterministically than linguistically: TAM/SAM/SOM arithmetic, unit economics, sensitivity analysis, Monte Carlo simulation, confidence intervals, deduplication, clustering, calibration, ranking diagnostics, or a bounded feasibility micro-test.

**Input contract:**

```json
{
  "code": "Python source",
  "input_artifacts": ["optional stored artifact ids"],
  "purpose": "CALCULATION|STATISTICS|SIMULATION|CLUSTERING|CALIBRATION|MICRO_TEST",
  "timeout_seconds": 60,
  "memory_mb": 2048,
  "network": false
}
```

**Output:** stdout/stderr, structured result payload, generated artifact references, runtime, exit status, and source-code hash.

**Rules:** network disabled by default; no production credentials; no host filesystem beyond mounted task inputs; fixed CPU/RAM/time limits. Important numeric results are reproducible from persisted code, inputs, and environment version. LLM prose arithmetic MUST NOT override deterministic results.

### T09 — `database_query`

**Actors:** Flow Controller plus all stateful research/evaluation actors through constrained operations.

**Call when:** canonical DBIE state must be persisted or retrieved.

**Input contract:** agents do not submit arbitrary SQL. They call named operations such as:

```json
{
  "operation": "GET_ASSUMPTION|UPSERT_EVIDENCE|LINK_EVIDENCE|GET_IDEA|SAVE_EVALUATION|GET_OUTCOMES|GET_SOURCE_LINEAGE",
  "parameters": {}
}
```

**Output:** typed DBIE entities with IDs, versions, timestamps, and provenance.

**Rules:** schema changes and destructive deletes are never exposed to agents. Writes use optimistic versioning/idempotency keys. Flow Controller owns lifecycle transitions. Evidence records are append-oriented; corrections create new versions rather than silently rewriting historical observations.

### T10 — `semantic_memory_search`

**Actors:** Discovery, Ideation, Assumption Auditor, Evidence Researcher, Competitor Analyst, Red Team, Calibration Judge.

**Call when:** before researching or generating around a problem, the actor needs to know what DBIE already learned that is semantically related.

**Input contract:**

```json
{
  "query": "string",
  "entity_types": ["PROBLEM", "IDEA", "ASSUMPTION", "EVIDENCE", "COMPETITOR", "EXPERIMENT", "OUTCOME", "LESSON"],
  "filters": {"optional": "typed filters"},
  "top_k": 10,
  "exclude_current_run": false
}
```

**Output:** entity IDs, short canonical text, similarity score, entity type, source/evidence status, creation/update dates, and links to canonical database records.

**Rules:** memory is a retrieval hint, not independent evidence. A prior conclusion can inform search queries or priors but MUST NOT be counted as new support for an assumption. Validation agents can request `exclude_current_run=true` or hide prior verdicts when independence is required.

## 8.6 Actor-to-Tool Permission Matrix

`R` = read/research use; `W` = constrained canonical-state write; `C` = deterministic compute; blank = not granted by default.

| Actor | T01 Web | T02 Page | T03 Reddit | T04 Companies | T05 GitHub | T06 Regulations | T07 Docs | T08 Python | T09 DB | T10 Memory |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Flow Controller |  |  |  |  |  |  |  |  | W | R |
| Trend Scout | R | R |  | R | R | R | R |  | W | R |
| Pain-Point Miner | R | R | R |  |  |  | R |  | W | R |
| Technology Scout | R | R |  |  | R |  | R |  | W | R |
| Regulatory Scout | R | R |  |  |  | R | R |  | W | R |
| Idea Generator |  |  |  |  |  |  |  |  | W | R |
| Assumption Auditor |  |  |  |  |  |  |  |  | W | R |
| Evidence Researcher | R | R | R | R | R | R | R |  | W | R |
| Market Analyst | R | R | R | R |  |  | R | C | W | R |
| Competitor Analyst | R | R | R | R | R |  | R |  | W | R |
| Regulatory Analyst | R | R |  |  |  | R | R |  | W | R |
| Technical Analyst | R | R |  |  | R |  | R | C | W | R |
| Economics Analyst | R | R |  | R |  |  | R | C | W | R |
| Distribution Analyst | R | R | R | R |  |  | R |  | W | R |
| Source-Lineage Analyst | R | R |  |  |  |  | R | C | W | R |
| Calibration Judge |  |  |  |  |  |  |  | C | W | R |
| Red Team | R | R | R | R | R | R | R | C | W | R |

Idea-generation actors intentionally receive little or no live external research access once the discovery package has been assembled. This preserves separation between evidence collection and creative recombination and reduces the tendency to copy already-visible products. The Flow can authorize an exception when the generator explicitly requests evidence for a missing prerequisite, but that request is logged and handled by a research actor rather than granting the generator unrestricted search.

## 8.7 Stage-by-Stage Tool Calling Policy

| Flow stage | Required calls | Conditional calls | Prohibited/default-off calls |
|---|---|---|---|
| `initialize_run` | T09, T10 | none | T01–T08 |
| `discover_signals` | T01, T02, T09, T10 | T03, T04, T05, T06, T07 | T08 unless needed for dedup/statistics |
| `generate_ideas` | T10, T09 | none normally | unrestricted T01–T08 |
| `eligibility_gate` | T09 | T08 for deterministic thresholds | external research unless a required fact is missing |
| `decompose_assumptions` | T09, T10 | none | external research normally |
| `validate` | T01, T02, T07, T09, T10 | T03–T06 by assumption type; T08 for calculations | side-effecting external tools |
| `red_team` | T01, T02, T09, T10 | T03–T08 as attack vector requires | side-effecting external tools |
| `rank_portfolio` | T09, T10, T08 | external model judge via Model Gateway, not an MVP tool | new evidence collection unless rank is blocked by an explicit gap |
| `design_experiment` | T09, T10, T08 | T01/T02 for benchmark design | public deployment/spend in MVP |
| `learn_from_outcome` | T09, T10, T08 | none | reinterpreting outcomes via fresh web evidence before storing the raw result |

## 8.8 Evidence Routing by Assumption Type

The Assumption Auditor assigns a category, and the Flow routes the validation task to the actor/tool combination below.

| Assumption category | Primary actor | First tools | Escalation tools |
|---|---|---|---|
| DEMAND / PAIN | Pain-Point Miner or Market Analyst | T01, T02, T03 | T04, T07 |
| BUYER | Market Analyst | T01, T02, T04 | T03, T07 |
| WILLINGNESS TO PAY | Market/Economics Analyst | T01, T02, T04, T07 | later real experiment; do not infer from LLM persona |
| DISTRIBUTION | Distribution Analyst | T01, T02, T03, T04 | T07, later channel experiment |
| FEASIBILITY | Technical Analyst | T05, T02, T07 | T08 micro-test |
| AUTOMATION | Technical Analyst | T05, T07 | T08 micro-test/prototype benchmark |
| ECONOMICS | Economics Analyst | T04, T07, T09 | T08 deterministic model |
| DEFENSIBILITY | Competitor Analyst + Red Team | T01, T02, T04, T05 | T07 |
| REGULATORY | Regulatory Analyst | T06, T02, T07 | human/legal review on ambiguity |

## 8.9 Tool-Call Stopping Rules

Research agents MUST stop calling tools when one of the following becomes true:

1. The assumption reaches its configured evidence threshold with at least the required number of independent source families.
2. A fatal contradiction is established from sufficiently authoritative evidence.
3. Additional calls are returning only derivative or duplicate sources.
4. The remaining uncertainty cannot be resolved by research and requires an experiment.
5. Stage search/cost/time budget is exhausted.
6. An authoritative primary source directly resolves the factual question.

The Flow, not the agent, decides whether the stage advances after a stopping condition. This prevents agents from extending research simply because the model can continue searching.

## 8.10 CrewAI Agent Configuration Rule

Each CrewAI agent definition MUST declare four tool-related fields in addition to role/goal/backstory:

```yaml
tool_policy:
  allow: [web_search, fetch_page]
  max_calls_per_task: 12
  max_parallel_calls: 2
  require_assumption_id: true
  primary_source_required_for: [REGULATORY, MATERIAL_NUMERIC_CLAIM]
```

The Tool Gateway is authoritative. Prompt-level instructions are defense in depth only; they are not considered an access-control mechanism.

## 8.11 MCP Boundary

Where feasible, provider adapters SHOULD be exposed through MCP so the same ten logical capabilities can be reused by another harness later. CrewAI-specific wrappers translate CrewAI tool calls to DBIE contracts; MCP clients translate DBIE contracts to provider/server calls. The canonical schemas, evidence semantics, quotas, and audit model remain owned by DBIE.

This means replacing CrewAI does not require rewriting `web_search`, `search_github`, `search_regulations`, memory, or database integrations. Conversely, replacing Tavily with another search provider does not change CrewAI agents.

## 8.12 MVP Tool Acceptance Criteria

The ten-tool MVP is complete only when:

- every tool has a typed input/output schema and unit/smoke tests;
- every call is attributable to run, stage, task, actor, idea, and assumption where applicable;
- every external result records source/provider, timestamp, and content/result hash where meaningful;
- provider credentials never enter LLM context;
- actor allowlists are enforced outside prompts;
- search snippets cannot be promoted directly to evidence without an explicit permitted exception;
- T08 execution is isolated and reproducible;
- T09 does not expose arbitrary destructive SQL;
- T10 marks remembered material distinctly from newly collected evidence;
- duplicate/derivative source families are detectable;
- per-task call, time, and cost budgets are enforced;
- tool errors degrade to explicit evidence gaps rather than fabricated answers;
- no MVP tool can spend money, send communication, publish externally, create accounts, or modify production systems.

# 9. Evidence Model

The core unit of validation is the falsifiable assumption. Claims and
evidence exist to update an assumption; reports are generated from these
structured objects. Every assumption identifies what observation would
increase confidence, what observation would falsify it, and whether the
current status is UNKNOWN, RESEARCH_SUPPORTED, RESEARCH_CONTRADICTED,
EXPERIMENT_SUPPORTED, EXPERIMENT_CONTRADICTED, or INCONCLUSIVE.

Assumption {  
assumption_id  
idea_id  
category: DEMAND \| BUYER \| WTP \| DISTRIBUTION \| AUTOMATION \|  
ECONOMICS \| FEASIBILITY \| DEFENSIBILITY \| REGULATORY  
statement  
criticality: FATAL \| MATERIAL \| SECONDARY  
falsification_condition  
validation_condition  
prior_confidence  
current_confidence  
evidence_for_ids\[\]  
evidence_against_ids\[\]  
experiment_ids\[\]  
status  
uncertainty  
created_at  
updated_at  
}  
  
Claim {  
claim_id  
assumption_id  
statement  
direction: SUPPORTS \| CONTRADICTS \| NEUTRAL  
evidence_ids\[\]  
inference_type: MEASURED \| OBSERVED \| INFERRED \| MODEL_JUDGMENT  
confidence  
created_by_agent  
model_version  
prompt_version  
created_at  
}

Evidence {  
evidence_id  
source_url / source_identifier  
source_type  
publisher / author  
observed_at  
published_at  
extracted_fact  
quote_or_excerpt_pointer  
evidence_tier: OBSERVED_BEHAVIOR \| PRIMARY \| SECONDARY \| MODEL_ONLY  
reliability_score  
freshness_score  
lineage_root_id  
independence_group  
content_hash  
}  
  
ExperimentResult {  
experiment_id  
assumption_id  
hypothesis  
protocol_version  
metric  
threshold  
sample_definition  
observed_value  
sample_size  
cost  
started_at  
ended_at  
interpretation  
raw_artifact_refs\[\]  
}

Evidence independence is explicit. Ten pages derived from one press
release, analyst note, survey, or vendor dataset count as one lineage
family until independent provenance is demonstrated. Source quantity
never substitutes for source independence. Observed behavior from a
controlled experiment is stored separately and receives a higher trust
tier than model-generated judgments.

# 10. Candidate Data Model

BusinessIdea {  
idea_id  
problem_id  
title  
one_sentence_thesis  
target_customer  
buyer  
user  
value_proposition  
product_form  
delivery_model  
why_now  
digital_eligibility  
autonomous_scalability  
assumption_ids\[\]  
competitor_ids\[\]  
risk_ids\[\]  
experiment_ids\[\]  
evidence_coverage  
unresolved_fatal_assumptions  
tournament_rating  
decision: BUILD \| ITERATE \| KILL \| MORE_EVIDENCE  
lifecycle_state  
lineage{}  
}

The idea record intentionally does not contain a single authoritative
“truth score.” Decision-relevant values live on assumptions, evidence,
experiments, and deterministic economics. Aggregate portfolio metrics
are projections over those objects and must retain their uncertainty.

# 11. Fast Rejection, Uncertainty, and Decision Metrics

## 11.1 Deterministic Rejection

- Fails any mandatory digital-only criterion.

- No identifiable customer and economic buyer.

- No evidence that the stated problem exists.

- No credible “why now” mechanism.

- Implementation requires unavailable proprietary technology or physical
  infrastructure.

- Business is structurally dependent on linear human labor with no
  plausible automation path.

- Known legal/regulatory constraint makes the proposed operation
  infeasible.

- Duplicate of an existing candidate above a configured similarity
  threshold without meaningful differentiation.

## 11.2 Evidence-Typed Decision Metrics

The system may compute normalized portfolio metrics for triage, but
every dimension must declare its evidence type: MEASURED, OBSERVED,
INFERRED, MODEL_JUDGMENT, or UNKNOWN. UNKNOWN does not become 5/10; it
remains unknown. MODEL_JUDGMENT cannot by itself satisfy a critical
assumption. Measured and observed values retain sample size, date,
protocol, and uncertainty.

| **Dimension**                | Triage weight | Required evidence / interpretation                                                                                                                             |
|------------------------------|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Problem severity / urgency   | 12%           | Economic pain, risk, frequency, deadline pressure. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                          |
| Willingness to pay           | 12%           | Evidence that a budget owner will pay enough. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                               |
| Reachable market             | 9%            | Serviceable and realistically reachable demand, not headline TAM. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.           |
| Growth / why now             | 8%            | Structural tailwinds and timing. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                                            |
| Digital automation potential | 12%           | Share of delivery/operations that software/agents can perform. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.              |
| Gross margin potential       | 8%            | Economics at scale. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                                                         |
| Distribution feasibility     | 10%           | Credible path to customers at acceptable CAC. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                               |
| Differentiation              | 7%            | Clear superiority for a specific segment/use case. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                          |
| Defensibility                | 7%            | Data, workflow embedding, network effects, switching costs, learning loops. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption. |
| Technical feasibility        | 6%            | Can be built from available digital technologies. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                           |
| Capital efficiency           | 5%            | Low external capital before validation/revenue. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                             |
| Low human marginal burden    | 4%            | Revenue can scale faster than operator headcount. Unknowns remain explicit; model judgment alone cannot validate a fatal assumption.                           |

Portfolio triage uses a versioned multi-criteria view rather than
false-precision arithmetic. A candidate cannot receive a definitive
overall score while fatal assumptions remain unknown. When a scalar is
required for queue prioritization, the system reports a range (for
example, expected-value interval or lower/base/upper scenario) together
with evidence coverage and uncertainty. The scalar is never treated as a
probability of business success.

# 12. Pairwise Tournament Ranking

Pairwise comparison is retained because relative judgments can be more
stable than absolute LLM scores, but it is not evidence. Judges compare
candidates only after hard assumption/evidence gates and receive
normalized dossiers rather than persuasive generated prose. A pairwise
win can order two eligible candidates; it cannot rescue a candidate with
unresolved fatal assumptions.

Pairing emphasizes candidates with similar evidence status or uncertain
ordering. Judge independence is measured, not assumed: repeated calls to
the same model family are treated as correlated unless calibration
demonstrates otherwise. Where feasible, generator and judge use
different model families or deterministic evaluators. The portfolio view
shows tournament rating beside evidence coverage, unresolved
assumptions, red-team severity, and experiment outcomes.

# 13. Business Model Exploration

The system distinguishes the opportunity from the business model. For
one validated problem, a Business Model Crew may generate several
digital implementations and compare them before selecting one.

| **Model**                     | **Typical strength**                              | **Typical weakness**                       |
|-------------------------------|---------------------------------------------------|--------------------------------------------|
| Subscription SaaS             | Recurring revenue, high margins.                  | Long enterprise sales/procurement.         |
| Usage-based API               | Scales with customer usage; developer-friendly.   | Price compression and platform dependency. |
| AI agent / managed automation | High value capture from replacing workflow labor. | Reliability, oversight, trust.             |
| Data / intelligence product   | Reusable differentiated information asset.        | Data rights, freshness, reproducibility.   |
| Marketplace                   | Network effects if liquidity emerges.             | Cold-start and two-sided acquisition.      |
| Digital service → software    | Fast early revenue and learning.                  | Risk of remaining labor-linear.            |
| Open-source + enterprise      | Distribution and ecosystem leverage.              | Monetization and free-rider risk.          |

# 14. Persistent Opportunity Graph and Learning

A persistent graph prevents each run from starting from zero. It stores
reusable knowledge and the lineage from market signal to final decision.

Signal ──indicates──▶ Problem ──affects──▶ Customer  
│ │ │  
│ ├──solved_by──────▶ ExistingSolution  
│ └──supports───────▶ BusinessIdea  
│  
BusinessIdea ──has────▶ Assumption ──tested_by────▶ Experiment  
│ │ │  
│ ├──supported_by───────▶ Evidence  
│ ├──contradicted_by────▶ Evidence  
│ └──predicted_status───▶ Prediction  
│ │  
├──variant_of────▶ BusinessIdea ▼  
└──evaluated_by──▶ Evaluation ObservedOutcome  
│  
└──calibrates──▶ Model/Judge/Prior

Learning is outcome-grounded. The graph stores what the system predicted
before an experiment separately from what happened afterward. Priors,
search allocation, and evaluator trust may be updated from
prediction-versus-outcome calibration, but historical LLM judgments
never become positive market evidence merely through repetition.
Rejected ideas are periodically sampled for re-evaluation to detect
self-reinforcing blind spots.

A learning update records: prior prediction, evidence available at
prediction time, later observed outcome, calibration error, affected
assumption types, and the exact model/prompt/scoring version. This
permits regression testing when models or policies change.

# 15. Memory and Retrieval Strategy

| **Store**               | **Content**                                                            | **Retrieval**                  |
|-------------------------|------------------------------------------------------------------------|--------------------------------|
| Relational store        | Canonical entities, run state, scores, policies, provenance.           | Exact queries and analytics.   |
| Document/evidence store | Fetched pages, extracts, reports, normalized source text.              | Source-id and metadata lookup. |
| Vector index            | Semantic similarity for deduplication and related prior work.          | Embedding nearest neighbors.   |
| Graph layer             | Relationships among problems, ideas, companies, evidence, assumptions. | Neighborhood and path queries. |
| Cache                   | Search/fetch/tool results and repeated LLM subcalls.                   | Content hashes / request keys. |

Vector similarity is used for retrieval, deduplication, and search-space
coverage—not as truth. Canonical evidence, assumptions, experiments,
predictions, and outcomes remain in structured storage with provenance.
Retrieval policies deliberately reserve a fraction of search budget for
dissimilar or underexplored regions so historical memory does not
collapse future ideation onto past winners.

# 16. Runtime, Harness, and LLM Serving Architecture

DBIE deliberately uses **one agent harness: CrewAI**. No LangChain, LangGraph, AutoGen, or second general-purpose agent framework is required in the initial architecture. Adding overlapping orchestration frameworks would duplicate state, retry, tool, and execution semantics and make failures harder to reproduce. A second harness may be introduced only if a measured capability gap cannot be solved cleanly in CrewAI Flow or custom deterministic code.

The runtime is divided into five explicit layers:

```text
Python DBIE application
│
├── CrewAI orchestration layer
│   ├── Flows: lifecycle, routing, stage transitions
│   └── Crews/Agents: bounded open-ended reasoning
│
├── Custom Domain Engine
│   ├── ideas / opportunities
│   ├── assumptions
│   ├── evidence / provenance
│   ├── experiments / outcomes
│   ├── deterministic gates
│   ├── scoring / uncertainty
│   └── decision state machine
│
├── Model Router
│   ├── VLLMProvider
│   ├── OllamaProvider
│   └── optional ExternalProvider
│
├── Tool Gateway
│   ├── MCP adapters where appropriate
│   └── custom typed tool adapters
│
└── Persistence / telemetry
    ├── PostgreSQL + pgvector
    ├── evidence/document cache
    └── logs, traces, metrics
```

## 16.1 Responsibility Boundary

| Layer | Owns | Must not own |
|---|---|---|
| CrewAI Flow | Stage orchestration, bounded retries, task dependencies, crew invocation, checkpoints, approval transitions | Canonical business rules hidden in prompts |
| CrewAI Crews/Agents | Research, hypothesis generation, synthesis, critique, red-team, experiment proposal | Final authoritative hard gates, money movement, unrestricted tools |
| Custom Domain Engine | Canonical objects, deterministic policy, assumption lifecycle, evidence rules, scoring, promotion/rejection, experiment state | Open-ended research behavior |
| Model Router | Provider selection, model selection, reasoning tier, context limits, concurrency, fallback, escalation metadata | Business decisions |
| vLLM/Ollama | Model serving and generation | Agent lifecycle or business state |
| Tool Gateway | Authentication, authorization, call validation, provenance, rate limits, budgets, audit | Deciding business viability |
| Persistence | Durable state, immutable predictions/outcomes, source lineage, retrieval | Generating conclusions |

The most important rule is: **core business logic is code, not prompt text**. For example, digital-only rejection, fatal-assumption policy, minimum evidence independence, experiment precedence, budget limits, and escalation triggers are deterministic functions over stored state. Agents propose or extract inputs; the Domain Engine decides whether the rule is satisfied.

## 16.2 Model Provider Interface

CrewAI must not depend directly on a specific runtime. DBIE exposes an internal provider-neutral model contract such as:

```text
LLMProvider
  generate(request) -> response
  structured_generate(request, schema) -> typed_response
  tool_call(request, tool_schema) -> tool_intent
  health() -> provider_status
  capabilities() -> model_capabilities
```

Initial adapters:

- `VLLMProvider` — preferred for production-like local concurrency, continuous batching, explicit GPU-memory controls, and OpenAI-compatible serving.
- `OllamaProvider` — preferred for simple local setup, development, model swapping, and fallback operation.
- `ExternalProvider` — optional, disabled by default; used only for L4 escalation or explicitly configured evaluation.

Provider choice is configuration, not agent logic. The same CrewAI agent/task definition must run against either vLLM or Ollama without changing its business behavior.

## 16.3 Supported Primary Models

DBIE v0.5 defines two local primary-model profiles rather than assuming a single model:

| Profile | Intended runtime | Role | Hardware rationale |
|---|---|---|---|
| `gpt-oss-20b` | Ollama or vLLM where memory permits | Baseline/reference primary model | Strong agent/tool behavior; larger VRAM footprint leaves less KV-cache headroom on 16 GB GPUs |
| `ministral-3-14b-reasoning` quantized | Prefer vLLM; Ollama-compatible packaging where available | Low-VRAM primary option | Target roughly <10 GB weights so a 16 GB GPU retains substantial KV/cache/runtime headroom |

The architecture does not encode either model as intrinsically superior. DBIE benchmarks them on its own tool-use and business-evaluation workload. Configuration selects the default.

Recommended 16 GB strategy: target **8–10 GB model-weight occupancy**, cap context per request, and reserve the remaining VRAM for KV cache, batching, CUDA/runtime overhead, and concurrency. Full advertised context windows must not be enabled by default simply because a model supports them. Start with 16k–32k maximum context and retrieve only relevant evidence.

## 16.4 Concurrency

Many logical agents may exist while only a small number generate simultaneously:

```text
30–100 logical CrewAI tasks/agents
             │
             ▼
      ModelRouter queue
 priorities • quotas • cancellation
             │
             ▼
      4–8 initial active requests
             │
        vLLM / Ollama
             │
        one loaded model
```

The initial 4–8 active-request target is a tuning starting point, not a guarantee. The runtime automatically reduces concurrency when KV-cache pressure, OOM risk, p95 latency, or throughput degradation crosses configured thresholds. Tool I/O concurrency is governed separately so slow web/database calls do not occupy inference slots.

## 16.5 Why No Additional Harness

DBIE explicitly rejects an initial stack such as `CrewAI + LangChain + LangGraph`. CrewAI already supplies agent/crew orchestration and Flow-level control. Deterministic behavior belongs in the custom Domain Engine rather than in a second orchestration abstraction.

A second harness is justified only if all of the following are true:

1. A required capability is missing from CrewAI Flow/Crews.
2. The capability cannot be implemented simply in custom deterministic code.
3. The measured benefit outweighs duplicated state/tool/retry abstractions.
4. An integration contract and failure semantics are defined before adoption.

# 17. Model Routing and Independence

The Model Router is provider- and model-agnostic. A configured local primary model handles discovery, ideation, query formulation, structured extraction, assumption decomposition, evidence synthesis, experiment design, ordinary red-team work, pairwise comparison, and reporting. Deterministic code performs calculations and hard gates. A different model family or stronger external model is reserved for disputes, critical assumptions, high-value finalists, low evaluator agreement, or unusually consequential decisions.

Model routing inputs include: task type, required structured-output/tool capabilities, context size, configured independence level, queue depth, VRAM budget, latency budget, historical task accuracy, and escalation policy. Agents do not select providers themselves.

## 17.1 Model-Independence Levels

- L0 — Primary-model judgment: configured primary model alone. Suitable for generation, routing, drafting, and low-risk internal judgments; never sufficient by itself to validate a fatal market assumption.
- L1 — Deterministic evidence: primary model plus externally sourced evidence, provenance, deterministic calculations, schema checks, and hard gates. This is the normal validation baseline.
- L2 — Repeated independent contexts: multiple primary-model evaluations with clean role-specific contexts and randomized ordering. Useful for stability measurement, but not independent market evidence because the underlying model is shared.
- L3 — Heterogeneous local judge: a different local model family evaluates the disputed claim or candidate.
- L4 — Strong external judge: a substantially stronger or otherwise independent external model evaluates only escalated cases. Its judgment is advisory unless grounded in evidence.
- L5 — Observed market experiment: measured customer or market behavior from a pre-registered digital experiment. Highest-trust validation level for demand, pricing, conversion, and related behavioral assumptions.

## 17.2 Escalation Policy

Use the cheapest independence level capable of resolving current uncertainty. Escalate on a high-value finalist, low evaluator agreement, FATAL assumption, conflicting high-quality evidence, material legal/regulatory interpretation, large proposed commitment, unstable ranking, or demonstrated primary-model failure on the relevant task class. Escalation stops when additional model opinion has lower expected information value than collecting evidence or running an experiment.

| Task | Default execution / escalation |
|---|---|
| Extraction / classification | Primary local model, low reasoning effort, schema-constrained; deterministic validators |
| Deduplication / tagging | Embeddings + deterministic similarity; model only for ambiguity |
| Idea generation | Primary local model with diversified lenses; novelty measured against memory |
| Validation synthesis | Primary + evidence graph (L1); disputed critical assumptions to L3/L4 |
| Red team | Primary with isolated context; heterogeneous judge for high-impact disagreement |
| Pairwise ranking | Primary initially; repeat for stability; escalate unstable/high-value matchups |
| Financial analysis | Deterministic Python from explicit assumptions; model explains only |
| Legal/regulatory | Primary may triage; material conclusions require authoritative sources and possibly external expert/human review |
| Demand / WTP | LLM judgment cannot validate alone; prefer L5 observed experiments |
| Final synthesis | Primary composes dossier; high-value finalists may receive L4 review before human approval |

# 18. Observability and Evaluation

Every run is observable at system, crew, agent, task, tool, model, and
candidate levels. Current CrewAI exposes observability-oriented
concepts; this design additionally requires application-level metrics
tied to business-idea quality.

| **Metric group**       | **Examples**                                                                                                                |
|------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Pipeline               | Ideas generated, rejection rate by gate, survivors per stage, stage latency.                                                |
| Evidence               | Sources per claim, independent-source count, evidence coverage, stale-source fraction.                                      |
| Agent quality          | Schema failures, unsupported-claim rate, judge disagreement, hallucination incidents.                                       |
| Economics              | Tokens/run, external API cost/run, cost/finalist, cost/rejected candidate.                                                  |
| Ranking stability      | Pairwise upset rate, rank correlation across repeated judging, score variance.                                              |
| Novelty                | Duplicate rate vs prior graph, new-problem rate, new-business-model rate.                                                   |
| Learning               | Recurring rejection reasons, prediction accuracy of early gates, later validation outcomes.                                 |
| Assumptions            | Fatal assumptions per candidate, unresolved-fatal rate, falsification rate, evidence transitions by tier.                   |
| Experiments            | Experiments designed/run, cost per resolved assumption, conversion/usage metrics, inconclusive rate, time to falsification. |
| Calibration            | Brier/log-style calibration where applicable, prediction-vs-outcome error, judge reliability by model/prompt/task.          |
| Evidence independence  | Effective independent-source count, lineage-family concentration, derivative-source inflation prevented.                    |
| Automation scalability | Human minutes per customer/transaction, automation ratio, estimated burden at 10× and 100× volume.                          |

# 19. Quality Controls

- Pydantic/JSON-schema validation for every inter-stage output.

- No score can cite the candidate’s own generated description as
  evidence.

- Important market claims require at least two independent sources where
  feasible.

- Each evaluator receives a clean role-specific context, avoiding
  contamination by prior persuasive prose.

- Judges receive both supporting and contradictory evidence.

- Low evidence coverage caps candidate ranking irrespective of narrative
  quality.

- Source freshness thresholds vary by claim type; current pricing and
  competition require recent evidence.

- All automatic decisions record reason codes and score/config versions.

- Randomized re-evaluation of a sample of rejected ideas detects
  over-aggressive gates.

- Aggregate rankings expose uncertainty and evidence tier; UNKNOWN is
  never silently imputed as an average score.

- At least a configured fraction of ideation/search budget explores
  areas dissimilar to historical winners.

- Source-lineage clustering reduces copied/syndicated evidence to its
  effective independent roots.

- Predictions are immutable once an experiment starts; outcomes are
  appended separately.

- Observed experiment results are evaluated against predeclared
  metrics/thresholds to reduce post-hoc rationalization.

- Critical assumptions must state falsification criteria before the
  evaluator sees the final recommendation.

- LLM-to-LLM agreement is never counted as independent evidence.

# 20. Human Approval Gates

| **Boundary**                                                        | **Default**                                                                         |
|---------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Web research / public read-only data                                | Automatic within quotas.                                                            |
| Paid research/API spend above run budget                            | Approval required.                                                                  |
| Contacting a real customer/prospect                                 | Approval required unless a dedicated campaign is explicitly enabled.                |
| Publishing content publicly                                         | Approval required.                                                                  |
| Deploying a prototype to production                                 | Approval required.                                                                  |
| Purchasing domains/services or committing funds                     | Approval required.                                                                  |
| Selecting finalists for automated deeper research                   | Automatic within configured budget.                                                 |
| Final build/investment decision                                     | Human decision.                                                                     |
| Creating a private/local prototype with no external exposure        | Automatic inside sandbox and resource quotas.                                       |
| Publishing a landing page or collecting external signups            | Approval required; privacy/terms/instrumentation reviewed.                          |
| Running paid acquisition experiments                                | Approval required with explicit spend ceiling and campaign scope.                   |
| Changing an active experiment protocol after data collection starts | New experiment version required; original prediction and protocol remain immutable. |

# 21. Failure Handling

| **Failure**               | **System behavior**                                                                   |
|---------------------------|---------------------------------------------------------------------------------------|
| Tool timeout              | Retry with bounded backoff; then mark evidence gap and continue if non-critical.      |
| Search unavailable        | Use alternate provider/cache; never fabricate evidence.                               |
| Schema-invalid LLM output | Repair once with schema-only retry; then fail task and record.                        |
| Agent disagreement        | Preserve disagreement; invoke adjudicator only where decision is required.            |
| Insufficient evidence     | Mark INSUFFICIENT_EVIDENCE; do not convert uncertainty into a neutral/positive score. |
| Budget exhausted          | Checkpoint; stop lower-priority candidates first.                                     |
| Model server overloaded   | Queue requests; reduce active concurrency; preserve logical agents.                   |
| Interrupted run           | Resume from persisted Flow state and idempotent stage checkpoints.                    |

# 22. Security and Data Governance

- Credentials are held by the Tool Gateway or secret manager, not
  inserted into agent prompts.

- Per-tool allowlists and scopes enforce least privilege.

- External content is treated as untrusted input; prompt-injection
  defenses separate tool content from instructions.

- Fetched evidence is hashed and provenance-stamped for traceability.

- PII collection is minimized and isolated from general research
  context.

- Retention policies apply to raw web content, logs, generated
  artifacts, and contact data independently.

- Agents cannot grant themselves additional permissions or alter
  scoring/governance configuration.

# 23. Suggested Repository Structure

digital_business_idea_engine/  
├── app/  
│ ├── flows/  
│ │ └── idea_pipeline.py  
│ ├── crews/  
│ │ ├── discovery/  
│ │ ├── ideation/  
│ │ ├── validation/  
│ │ ├── business_model/  
│ │ ├── red_team/  
│ │ └── diligence/  
│ ├── agents/  
│ ├── tasks/  
│ ├── tools/  
│ │ ├── gateway/  
│ │ ├── search/  
│ │ ├── browser/  
│ │ ├── company/  
│ │ ├── regulatory/  
│ │ ├── github/  
│ │ └── finance/  
│ ├── models/ \# typed domain schemas  
│ ├── scoring/  
│ │ ├── rubric.py  
│ │ ├── evidence.py  
│ │ └── tournament.py  
│ ├── knowledge/  
│ │ ├── repository.py  
│ │ ├── graph.py  
│ │ └── retrieval.py  
│ ├── llm/  
│ │ ├── gateway.py  
│ │ └── scheduler.py  
│ ├── policies/  
│ ├── observability/  
│ └── reports/  
├── config/  
│ ├── agents.yaml  
│ ├── tasks.yaml  
│ ├── scoring.yaml  
│ ├── budgets.yaml  
│ └── tool_policy.yaml  
├── migrations/  
├── tests/  
└── data/

# 24. Stage Contracts

| **Stage**            | **Input**                                              | **Output**                                                       | **Gate**                                                                                             |
|----------------------|--------------------------------------------------------|------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| Discovery            | Search mandate + prior graph                           | Signals + problems + evidence                                    | Problem has identifiable affected customer.                                                          |
| Ideation             | Qualified problem + search diversity target            | Idea variants + novelty lineage                                  | Structured schema + meaningful difference from prior candidates.                                     |
| Digital eligibility  | Idea                                                   | Digital + autonomous-scalability pass/fail + reason codes        | All mandatory criteria pass.                                                                         |
| Fast scoring         | Eligible idea + initial evidence                       | Assumption set + evidence gaps + triage range                    | No unresolved schema/identity defects; fatal assumptions identified.                                 |
| Validation           | Candidate + assumptions + evidence gaps                | Evidence-for/against + lineage + confidence transitions          | Fatal assumptions cannot be validated by model judgment alone.                                       |
| Business model       | Validated problem + assumption set                     | Model variants + deterministic economics + changed assumptions   | At least one digital, autonomously scalable model remains plausible.                                 |
| Red team             | Candidate dossier without generator persuasive prose   | Falsification attempts + correlated-evidence warnings + severity | No fatal contradiction ignored.                                                                      |
| Tournament           | Eligible survivors with normalized dossiers            | Pairwise ordering + judge disagreement                           | Ordering only; cannot override hard gates.                                                           |
| Diligence            | Top candidates + unresolved assumptions                | Experiment-ready dossier                                         | Each unresolved fatal/material assumption has a falsifiable test or explicit research gap.           |
| Learning             | Immutable predictions + evidence + experiment outcomes | Calibration updates + search-prior statistics                    | Outcomes stored separately from predictions; no self-confirming evidence creation.                   |
| Experiment design    | Diligence dossier + unresolved assumptions             | Pre-registered digital experiment protocol                       | Metric, threshold, sample, budget, stop condition and falsification criterion defined before launch. |
| Experiment execution | Approved protocol                                      | Observed raw metrics + artifacts                                 | No protocol mutation without a new version; outcome may be positive, negative, or inconclusive.      |
| Decision             | Research + red team + experiment outcomes              | BUILD / ITERATE / KILL / MORE_EVIDENCE                           | Decision cites resolved/unresolved assumptions and evidence tiers.                                   |

# 25. Implementation Phases

## Phase 1 — MVP: deterministic pipeline + evidence

- Define typed schemas for ideas, atomic assumptions, claims, evidence
  lineage, experiments, predictions, outcomes, and lifecycle states.

- Implement CrewAI Flow with discovery → diverse ideation →
  digital/autonomous gate → assumption decomposition → evidence
  validation → uncertainty view → report.

- Implement search/web tools behind a simple gateway.

- Use one shared LLM endpoint.

- Store runs, ideas, assumptions, claims, source lineage, evidence,
  predictions, and triage metrics in PostgreSQL/SQLite initially.

- Generate one final markdown/HTML memo per finalist containing an
  uncertainty map and explicit falsification tests.

Exit criterion: system runs end-to-end and produces finalists whose
critical assumptions, evidence tiers, source lineage, contradictions,
and unknowns are traceable.

## Phase 2 — adversarial quality

- Add Skeptic, Red-Team, Assumption Auditor, and Source-Lineage roles.

- Add source-lineage clustering, independence/freshness measurement, and
  evidence-tier rules.

- Add pairwise tournament ranking with normalized dossiers and explicit
  judge correlation tracking.

- Add evaluator calibration, repeated-judge stability tests, and a
  prohibition on treating agent agreement as evidence.

- Implement structured reason codes for all rejections.

Exit criterion: unsupported-claim rate, effective evidence independence,
judge disagreement, and calibration error are measurable; rankings never
override fatal-assumption gates.

## Phase 3 — persistent opportunity graph

- Add semantic deduplication and related-idea retrieval.

- Add problem → idea → assumption → evidence → prediction → experiment →
  observed-outcome graph.

- Reuse prior evidence subject to freshness rules.

- Track historical rejection patterns, calibration outcomes, and
  search-space coverage while reserving exploration budget for
  dissimilar opportunities.

Exit criterion: later runs reuse evidence without converting historical
judgments into truth and maintain measurable exploration outside prior
winner clusters.

## Phase 4 — scale and model routing

- Deploy one shared gpt-oss-20b inference server behind an async
  scheduler; begin with 4–8 active requests and many queued logical
  agents.

- Implement L0–L5 independence levels and escalation rules in the Model
  Gateway.

- Add caching, prioritization, reasoning-effort selection, and per-stage
  token/tool budgets.

- Parallelize independent candidate evaluations while tracking
  same-model correlation and evaluator stability.

- Add run dashboard/observability.

Exit criterion: hundreds of candidates can be processed without
multiplying model instances; at least 90% of ordinary inference can
remain on the primary local model, and L3/L4 escalations are measurable,
budgeted, and triggered only by explicit policy.

## Phase 5 — pre-registered digital experimentation

- Generate pre-registered falsifiable digital experiments for unresolved
  critical assumptions.

- With explicit approval, support landing pages, prototype usage tests,
  pricing/waitlist tests, acquisition experiments, interviews, or other
  digital-only tests.

- Record immutable protocol versions, raw measurements, sample
  definitions, costs, and observed experiment results as a higher-trust
  evidence tier.

- Update assumptions and portfolio decisions from observed behavior; do
  not retroactively alter the pre-experiment prediction.

Exit criterion: the engine distinguishes research attractiveness from
observed market response and can produce BUILD / ITERATE / KILL /
MORE_EVIDENCE decisions from explicit assumption resolution.

## Phase 6 — outcome calibration and autonomous learning

- Compare stored predictions with later observed outcomes and calculate
  calibration by assumption category, model, prompt, judge, and evidence
  tier.

- Update search allocation and evaluator trust from measured
  calibration, not from repeated internal consensus.

- Periodically re-sample rejected ideas and underexplored search regions
  to detect path dependence and premature convergence.

- Use experiment cost and information gain to learn which validation
  actions resolve uncertainty most efficiently.

Exit criterion: historical outcomes measurably improve prioritization
while holdout tests show that novelty and rejected-candidate recall do
not collapse.

# 26. MVP Recommended Configuration

| Area | Initial recommendation |
|---|---|
| Application | Python package with explicit domain, orchestration, model, tools, persistence, experiments, and observability modules |
| Agent harness | **CrewAI only**: Flow for authoritative lifecycle; Crews/Agents for bounded open-ended work |
| Additional harnesses | None initially; do not add LangChain/LangGraph unless a measured capability gap satisfies §16.5 |
| Domain logic | Custom deterministic Python; no hard business rules hidden exclusively in prompts |
| Model API | Internal `LLMProvider`/`ModelRouter` abstraction |
| Serving backends | `VLLMProvider` and `OllamaProvider`; same CrewAI tasks must work through either |
| Primary model option A | `gpt-oss-20b` as baseline/reference where VRAM/context budget is acceptable |
| Primary model option B | Quantized `Ministral 3 14B Reasoning` as preferred lower-VRAM option for a 16 GB GPU when substantial KV-cache headroom is required |
| GPU memory policy | Prefer ~8–10 GB model weights on a 16 GB GPU; reserve remaining memory for KV cache, batching, runtime overhead; enforce memory guardrails |
| Context policy | Start 16k–32k max model context; retrieve evidence rather than stuffing global state into prompts |
| Active LLM concurrency | Start 4–8; adapt to measured KV pressure, p95 latency, tokens/s and OOM margin |
| Logical agents | 30–100 acceptable; instantiate tasks/roles on demand and queue inference |
| Tools | Ten MVP tools from §8 behind Tool Gateway; MCP where useful, custom typed adapters otherwise |
| Persistence | PostgreSQL + pgvector preferred; predictions/outcomes stored separately and immutably |
| Graph | Relational edges first; dedicated graph DB only when measured queries justify it |
| Output | Structured JSON + Markdown reports |
| Approval | No public experiment, outbound contact, paid acquisition, spend, publication, or production deployment without explicit approval |
| Independence | L0 → L5 ladder retained; model family diversity counts as reasoning independence, not market evidence |
| Benchmarking | Primary-model choice based on DBIE-specific tool/evidence benchmark, not generic model benchmark alone |

# 27. Acceptance Criteria

- 100% of finalists pass the digital-only eligibility contract.

- Every scored market claim links to evidence or is explicitly labeled
  assumption/unknown.

- Rejected candidates retain machine-readable rejection reasons.

- Generator agents cannot be assigned as the sole evaluator of their own
  ideas.

- At least one adversarial evaluation occurs before a candidate can
  become a finalist.

- Finalists are ranked through both structured scoring and pairwise
  comparison.

- Runs are resumable from persisted checkpoints.

- Tool calls and LLM calls are attributable to run, stage, task, agent,
  and candidate.

- Prior ideas/evidence can be retrieved to prevent unnecessary
  duplication.

- No individual agent can bypass tool permissions, budget limits, or
  human approval gates.

- Pairwise ranking cannot override digital-only, autonomous-scalability,
  evidence, or fatal-assumption gates.

- A configured exploration budget prevents the opportunity graph from
  collapsing ideation onto historical winners.

- The system reports human marginal burden and automation ratio for
  every finalist.

- Observed experiment outcomes are stored separately from predictions
  and can be used for later calibration.

- Every externally executed experiment has a predeclared protocol,
  metric, threshold, budget, and immutable pre-experiment prediction.

- LLM agreement is never counted as market evidence.

- At least 90% of normal pipeline inference is executable on the
  configured primary gpt-oss-20b endpoint without requiring a stronger
  model.

- Every L3/L4 escalation records its trigger, model family, cost,
  decision impact, and whether it changed the outcome.

- Repeated gpt-oss-20b judgments (L2) are reported as stability
  evidence, never as independent market evidence.

- Fatal demand, pricing, or behavioral assumptions cannot be marked
  validated by L0–L4 model judgment alone when a feasible L5 experiment
  is required by policy.

- Deterministic calculations and hard gates are implemented outside the
  LLM and remain reproducible from stored inputs.

- Every evidence source belongs to a lineage/independence group;
  effective independent evidence is reported separately from raw source
  count.

- No unresolved FATAL assumption can be silently converted into an
  average numeric score.

- 100% of finalists have explicit atomic assumptions with falsification
  conditions.

- CrewAI is the only general-purpose agent harness in the MVP dependency graph.

- All hard eligibility, evidence, budget, escalation, and decision gates execute in deterministic application code and are testable without an LLM.

- The same representative CrewAI task suite can run through both `VLLMProvider` and `OllamaProvider` without changing domain behavior or schemas.

- Model/provider selection is performed by `ModelRouter`; individual agents cannot bypass routing policy.

- A 16 GB deployment can enforce a configured GPU-memory headroom target and reduce context/concurrency before OOM.

- Primary-model evaluation includes DBIE-specific tool-selection, tool-argument, structured-output, multi-step recovery, evidence-quality, latency, and VRAM measurements.

# 28. Key Design Decisions

| **Decision**                               | **Rationale**                                                                                            |
|--------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Flow outside, Crews inside                 | Preserves deterministic control while using autonomy only where it adds value.                           |
| Digital-only as hard gate                  | Prevents scoring from compensating for a fundamental scope violation.                                    |
| Evidence graph as core substrate           | Makes reasoning auditable and reusable across runs.                                                      |
| Adversarial evaluation                     | Counteracts self-confirming LLM reasoning.                                                               |
| Tournament + score                         | Reduces dependence on poorly calibrated absolute LLM scores.                                             |
| One shared model service                   | Efficiently supports many logical agents with bounded concurrent inference.                              |
| Least-privilege tool gateway               | Limits accidental or unauthorized external actions.                                                      |
| Human approval at consequential boundaries | Keeps the research engine autonomous while retaining control over real-world commitments.                |
| Assumption as primary validation object    | Turns business evaluation into falsifiable uncertainty reduction rather than narrative scoring.          |
| Observed outcomes outrank agent consensus  | Prevents many correlated LLM agents from manufacturing confidence.                                       |
| Predictions separated from outcomes        | Makes calibration possible and prevents hindsight rewriting.                                             |
| Source-lineage independence                | Stops copied/syndicated material from inflating evidence strength.                                       |
| Pre-registered digital experiments         | Tests demand, pricing, acquisition, usability, and automation with real behavior before build decisions. |
| Exploration reserve                        | Protects novelty and reduces path dependence caused by persistent memory and prior rankings.             |
| Autonomous scalability as hard gate        | Excludes digital businesses whose revenue remains structurally tied to proportional human labor.         |


## v0.5 Architecture Decisions

- CrewAI is the sole agent harness; no LangChain/LangGraph layer in the initial system.
- Custom Python owns canonical domain state and every authoritative deterministic decision rule.
- CrewAI owns Flow orchestration and bounded agentic reasoning, not business-policy truth.
- Model serving is isolated behind `ModelRouter` and `LLMProvider`.
- vLLM and Ollama are interchangeable provider adapters, not architectural dependencies of agents.
- `gpt-oss-20b` remains a supported baseline/reference primary model.
- Quantized Ministral 3 14B Reasoning is added as a lower-VRAM primary-model option when a 16 GB GPU must reserve substantial KV-cache headroom.
- Default context is deliberately capped at 16k–32k and extended only from evidence.
- The ten MVP tools remain behind one permissioned Tool Gateway, exposed via MCP where useful and typed custom adapters otherwise.
- Model choice is validated using a DBIE-specific benchmark rather than generic benchmark scores alone.

# 29. v0.3 Design Changes

- Defined gpt-oss-20b as the primary local model for most CrewAI agent
  tasks while preserving a model-agnostic gateway.

- Added L0–L5 model-independence levels separating same-model judgment,
  deterministic evidence, heterogeneous-model review, and observed
  market experiments.

- Added explicit escalation triggers so stronger/external models are
  used selectively rather than as the default execution path.

- Clarified that repeated calls to one model measure stability but do
  not create independent evidence.

- Made deterministic calculations, schema validation, hard gates, and
  evidence provenance authoritative outside the LLM.

- Added local-first concurrency guidance: one shared gpt-oss-20b server,
  4–8 active requests initially, and many queued logical agents.

## v0.2 changes retained

- Replaced idea-centric aggregate scoring with assumption-centric
  uncertainty reduction.

- Added immutable prediction → experiment → observed-outcome loop for
  calibration.

- Added evidence tiers and source-lineage independence to prevent
  correlated-source inflation.

- Added explicit safeguards against LLM-to-LLM consensus being treated
  as independent validation.

- Added novelty-search mechanisms and exploration budget to reduce
  memory-induced convergence.

- Elevated autonomous scalability from a soft score to a hard
  eligibility constraint.

- Made real-world digital experiments a first-class system stage with
  pre-registration and human approval.

- Changed final decisions to BUILD / ITERATE / KILL / MORE_EVIDENCE with
  explicit semantics.

# 30. References / Framework Alignment

CrewAI framework concepts used in this design were checked against the
current CrewAI documentation as of August 2026: Crews for collaborative
autonomous work; Flows for structured orchestration, state, branching,
and resumability; agents with tools and structured outputs; and
extensible/custom tools including web research and browser integrations.

- CrewAI Documentation — https://docs.crewai.com/

- CrewAI Introduction / Crews vs. Flows —
  https://docs.crewai.com/core-concepts/Agents

- CrewAI annotation/configuration documentation —
  https://docs.crewai.com/learn/using-annotations

- CrewAI web scraping/browser tool overview —
  https://docs.crewai.com/tools/web-scraping/overview

- OpenAI gpt-oss-20b model documentation —
  https://developers.openai.com/api/docs/models/gpt-oss-20b

- OpenAI gpt-oss architecture / release notes —
  https://openai.com/index/introducing-gpt-oss/

v0.3 uses official gpt-oss-20b specifications: approximately 21B total
parameters, 3.6B active parameters per token, native context up to 128k,
and agentic/tool-oriented capabilities.

# 31. Decision Semantics

A candidate decision is not inferred from prose sentiment. BUILD means
all fatal assumptions are resolved to the configured evidence threshold,
no fatal red-team contradiction remains, autonomous scalability is
plausible, and experiment results meet predeclared criteria where an
experiment is required. ITERATE means evidence supports the problem but
the current product/business formulation failed or remains materially
uncertain. KILL means at least one fatal assumption is contradicted or
the candidate violates a hard gate. MORE_EVIDENCE means the decision is
blocked by unresolved assumptions for which additional evidence has
positive expected value.

The system should additionally calculate Expected Value of Information
(EVI) for unresolved material assumptions where inputs are available:
approximate decision impact × probability that new information changes
the decision − validation cost. EVI is used for choosing the next
experiment, not as a claim of precise financial truth.

## 31.1 Experiment precedence

When a credible real-world observation conflicts with an LLM assessment,
the observed result controls the assumption update unless the experiment
itself is invalid. The correct response to a surprising experiment is to
inspect protocol quality, segmentation, instrumentation, and sample
limitations—not to average the result with model opinion.

# 32. Final Architecture Summary

Runtime strategy: one shared local gpt-oss-20b endpoint performs the
bulk of agent reasoning. The scheduler bounds active inference, the
Model Gateway enforces L0–L5 independence policy, deterministic services
own calculations and hard gates, and costly heterogeneous/external model
review is reserved for explicit escalation. Real digital experiments
remain the final authority for observable market behavior.

The system is not primarily an idea-generating crew. It is a controlled
digital opportunity discovery, falsification, and experimentation
engine. Generation is cheap and broad; each surviving idea is decomposed
into falsifiable assumptions; evidence and independent red-team work
reduce uncertainty; pairwise ranking orders only eligible candidates;
and pre-registered digital experiments test the remaining critical
assumptions against real behavior. Persistent memory improves efficiency
without allowing remembered judgments to masquerade as new evidence.

The v0.4 core architecture is deterministic CrewAI Flow + specialized
Crews + least-privilege digital tools + an assumption/evidence/outcome
substrate + digital-only and autonomous-scalability hard gates + novelty
search + source-lineage independence + adversarial validation +
uncertainty-aware portfolio metrics + pairwise ordering + pre-registered
digital experiments + outcome-calibrated learning + explicit human
approval for consequential external actions.


# 33. v0.5 Runtime Reference Architecture

```text
                        DBIE Python Application
                                │
        ┌───────────────────────┼────────────────────────┐
        │                       │                        │
   CrewAI Flow             Domain Engine           Persistence
        │                 deterministic                │
   bounded Crews            policies/state       PostgreSQL+pgvector
        │                       │                        │
        └───────────────┬───────┴───────────────┬────────┘
                        │                       │
                  Model Router             Tool Gateway
                        │                       │
                 ┌──────┴──────┐          MCP/custom tools
                 │             │                 │
               vLLM          Ollama          10 MVP tools
                 │             │
           Ministral 14B   GPT-OSS-20B
            or GPT-OSS      or other
```

This boundary is intentional: CrewAI may be replaced later without rewriting the Domain Engine or tool implementations; vLLM/Ollama may be exchanged without rewriting agents; and models may be benchmarked/swapped without changing canonical business state.
