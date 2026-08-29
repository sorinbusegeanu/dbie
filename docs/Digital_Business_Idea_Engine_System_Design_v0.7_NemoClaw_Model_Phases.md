\*\*\
DIGITAL BUSINESS IDEA ENGINE\*\*

CrewAI-Based System for Generating, Validating, Ranking, and Learning
from Fully Digital Business Ideas

System Design v0.7\
29 August 2026

v0.7 revision focus: venture lifecycle, autonomous MVP factory, dual
human/agent product contracts, capability reuse, and portfolio
intelligence.

v0.6 retained focus: free/open-source internal adapter stack behind the
ten stable DBIE tool contracts; SearXNG for metasearch; Crawl4AI,
Trafilatura, and Playwright for layered page acquisition; Docling and
PyMuPDF for document parsing; PRAW for Reddit; PyGithub/GitHub APIs for
software ecosystem research; official regulator adapters including
EUR-Lex; isolated Docker-based Python execution; PostgreSQL/SQLAlchemy;
pgvector plus a local BGE/E5-family embedding model; and explicit
adapter-selection, fallback, provenance, resource, and security
policies.

v0.5 retained focus: explicit runtime and harness architecture; CrewAI
as the sole agent harness; custom deterministic domain/control code;
provider-neutral model routing; vLLM and Ollama as interchangeable
serving backends; Ministral 3 14B as a lower-VRAM primary-model option
alongside gpt-oss-20b; and a strict separation between agent
orchestration, domain decisions, inference serving, and tools.

v0.4 retained focus: explicit MVP tool architecture for ten core digital
tools; actor-level tool ownership; CrewAI/MCP integration; typed call
contracts; invocation rules; provenance; and execution guardrails.

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

500 observed problems / signals\
↓\
250--500 raw business ideas\
↓\
50--100 digital-only + evidence-qualified candidates\
↓\
15--25 assumption-validated candidates\
↓\
5--10 red-team survivors\
↓\
3--5 experiment candidates\
↓\
observed market behavior / prototype evidence\
↓\
ranked build / kill / iterate recommendations

# 2. Goals and Non-Goals

## 2.1 Goals

-   Generate novel business ideas from observed problems and market
    changes rather than from unconstrained brainstorming.

-   Allow only businesses that can be built, sold, delivered, operated,
    supported, and scaled using digital tools.

-   Ground important conclusions in traceable external evidence.

-   Use independent and adversarial evaluators to reduce confirmation
    bias.

-   Rank ideas using both structured scoring and pairwise tournament
    comparison.

-   Persist opportunity, evidence, competitor, assumption, and
    evaluation knowledge across runs.

-   Preserve novelty by explicitly searching beyond already-visible SaaS
    categories and saturated market narratives.

-   Validate finalists with real digital experiments whenever market
    behavior can be observed cheaply.

-   Separate measured facts, inferred estimates, model judgments, and
    unknowns in every decision.

-   Treat assumptions---not prose reports or aggregate idea scores---as
    the primary unit of uncertainty reduction.

-   Learn which classes of ideas repeatedly succeed or fail the
    evaluation criteria.

-   Run primarily on a shared local gpt-oss-20b endpoint with bounded
    parallelism, escalating only when evidence quality or decision risk
    requires stronger independence.

-   Produce auditable artifacts suitable for human review before capital
    or implementation decisions.

## 2.2 Non-Goals

-   Automatically incorporating companies, opening bank accounts,
    signing contracts, or moving money.

-   Autonomously launching businesses without an explicit approval gate.

-   Treating simulated LLM customers, personas, or judges as substitutes
    for observed customer behavior.

-   Treating LLM confidence as market evidence.

-   Optimizing for businesses that require physical goods, inventory,
    facilities, field service, or proprietary hardware.

# 3. Digital-Only Eligibility Contract

Digital-only feasibility is a hard eligibility contract. Failure of any
mandatory criterion terminates the candidate before full validation.

  ---------------------------------------------------------------------------------
  **Dimension**    **Mandatory requirement**               **Examples of
                                                           rejection**
  ---------------- --------------------------------------- ------------------------
  Product /        Core customer value is delivered as     Physical goods,
  service          software, data, API, digital content,   manufacturing, hardware
                   or remotely executed digital work.      appliance.

  Acquisition      Customers can be reached through        Depends on physical
                   digital or remote channels.             retail footfall or local
                                                           field sales.

  Sales            Transaction can complete remotely or    Requires on-site demo or
                   self-service.                           physical inspection as
                                                           an inherent step.

  Fulfilment       Fulfilment is                           Shipping, warehousing,
                   software/API/agent/remote-service       installation, physical
                   based.                                  logistics.

  Operations       Normal operations can be run remotely   Local facilities or a
                   with software tooling.                  field workforce required
                                                           for normal delivery.

  Infrastructure   Cloud, SaaS, APIs, commodity compute,   Custom proprietary
                   or downloadable software are            hardware required.
                   sufficient.                             

  Payments         Billing and settlement can be           Cash/local physical
                   electronic.                             collection is intrinsic
                                                           to the model.

  Support          Support can be delivered remotely and   On-site maintenance
                   increasingly automated.                 intrinsic to customer
                                                           value.

  Scaling          Marginal revenue does not require       Every incremental
                   proportional physical resources.        customer requires a new
                                                           physical asset.

  Geography        Expansion does not require a new        New facilities required
                   physical deployment footprint.          country by country.
  ---------------------------------------------------------------------------------

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

  -----------------------------------------------------------------------------
  **Principle**        **Design consequence**
  -------------------- --------------------------------------------------------
  Evidence before      Claims require sources, timestamps, provenance, and
  narrative            counter-evidence.

  Generation ≠         Independent agents/crews perform ideation, validation,
  evaluation           red-team, and ranking.

  Cheap filters first  Deterministic and low-cost gates run before deep
                       research.

  Structured outputs   All inter-stage contracts use typed schemas; prose is a
                       presentation layer.

  Bounded autonomy     Agents receive least-privilege tools, budgets,
                       deadlines, and explicit task boundaries.

  Deterministic outer  CrewAI Flow owns routing, retries, state, checkpoints,
  control              approvals, and failure handling.

  Agentic inner work   Crews handle open-ended research, synthesis, debate, and
                       hypothesis generation.

  Persistent learning  Facts and evaluations are stored as reusable graph
                       entities, not discarded after a report.

  Reproducibility      Model, prompt/config version, source set, score version,
                       and execution metadata are recorded.

  Human control at     Human approval is required before spending material
  consequential        money, launching, contacting prospects at scale, or
  boundaries           deploying production systems.

  Assumption-centric   Ideas are decomposed into falsifiable assumptions;
  reasoning            progress means reducing uncertainty, not increasing
                       narrative detail.

  Outcome over model   Observed behavior and deterministic measurements outrank
  opinion              LLM judgments, synthetic personas, and repeated-agent
                       consensus.

  Independence, not    Evidence and evaluators must be meaningfully
  agent count          independent; many agents using the same model/context do
                       not count as independent validation.

  Novelty preservation Search explicitly includes capability inversion,
                       cross-industry analogy, non-obvious combinations, and
                       neglected problems rather than only visible market
                       categories.

  Learning from        Historical predictions are stored separately from later
  outcomes             outcomes; future priors are updated only from calibrated
                       evidence and observed results.
  -----------------------------------------------------------------------------

# 5. Logical Architecture

┌──────────────────────────────────────────────────────────────────────┐\
│ CONTROL PLANE │\
│ CrewAI Flow • state • routing • budgets • approvals • experiments │\
└───────────────┬──────────────────────────────────────────────────────┘\
│\
┌───────────▼──────────┐ ┌────────────────────────────────┐\
│ Opportunity Discovery│─────▶│ Evidence / Assumption Store │\
└───────────┬──────────┘ │ source lineage • outcomes │\
▼ └──────────────┬─────────────────┘\
┌──────────────────────┐ │\
│ Diverse Idea Search │ │\
└───────────┬──────────┘ │\
▼ │\
┌──────────────────────┐ │\
│ Digital + Autonomous │ │\
│ Scalability Gates │ │\
└───────────┬──────────┘ │\
▼ │\
┌──────────────────────┐◀────────────────────┘\
│ Assumption Decomposer│\
└───────────┬──────────┘\
▼\
┌──────────────────────┐\
│ Evidence Validation │\
│ + Independent RedTeam│\
└───────────┬──────────┘\
▼\
┌──────────────────────┐\
│ Uncertainty + Pairwise│\
│ Portfolio Selection │\
└───────────┬──────────┘\
▼\
┌──────────────────────┐\
│ Digital Experiment │\
│ Design + Approval │\
└───────────┬──────────┘\
▼\
┌──────────────────────┐\
│ Observe Real Outcomes│\
└───────────┬──────────┘\
▼\
BUILD / ITERATE / KILL\
│\
└──────────────▶ calibrated learning loop

# 6. CrewAI Execution Model

Current CrewAI documentation distinguishes Crews for autonomous
collaboration from Flows for structured event-driven orchestration,
state, persistence, branching, and resumability. This system uses both:
the Flow is authoritative for lifecycle and state; Crews are invoked as
bounded capabilities inside the Flow.

## 6.1 Top-Level Flow

1.  initialize_run --- load mandate, policy, scoring version, budgets,
    and prior knowledge.

2.  discover_signals --- invoke discovery crew and deduplicate against
    persistent knowledge.

3.  generate_ideas --- create deliberately diverse business formulations
    using multiple search mechanisms, including cross-industry analogy
    and capability inversion.

4.  eligibility_gate --- deterministic digital-only,
    autonomous-scalability, and structural rejection.

5.  decompose_assumptions --- convert each survivor into explicit
    demand, buyer, pricing, distribution, automation, feasibility,
    defensibility, and economics assumptions.

6.  validate --- seek evidence for and against each critical assumption;
    classify evidence as measured, observed, inferred, model-judged, or
    unknown.

7.  model_business --- generate and compare viable digital business
    models while preserving their distinct assumptions and economics.

8.  red_team --- independently attempt to falsify critical assumptions
    and detect correlated evidence or evaluator agreement.

9.  prioritize_uncertainty --- rank candidates using hard evidence
    gates, uncertainty, pairwise comparison, and expected value of
    further information; avoid false precision.

10. design_experiments --- design the cheapest digital experiment
    capable of falsifying each unresolved critical assumption.

11. observe_and_decide --- after approved experiments, ingest measured
    outcomes and recommend BUILD, ITERATE, KILL, or MORE_EVIDENCE.

12. finalize_and_learn --- produce memos, uncertainty maps, experiment
    results, decision rationale, and calibrated learning updates.

13. checkpoint --- persist run state so interrupted work can resume.

# 7. Agent and Crew Design

## 7.1 Opportunity Discovery Crew

  --------------------------------------------------------------------------------
  **Agent**    **Objective**                      **Primary tools**  **Output**
  ------------ ---------------------------------- ------------------ -------------
  Trend Scout  Find meaningful technological,     Web/news/search,   Signal
               economic, regulatory, and          research sources   records
               behavioral changes.                                   

  Pain-Point   Find expensive, frequent, or risky Forums, reviews,   Problem
  Miner        customer problems.                 job posts,         records
                                                  communities        

  Industry     Identify inefficient workflows and Web, company data, Opportunity
  Analyst      value-chain friction.              industry sources   maps

  Regulatory   Find obligations that create       Regulatory         Regulatory
  Scout        mandatory spend or new workflows.  portals, legal     triggers
                                                  search             

  Technology   Find capabilities that newly       GitHub, model/tool Technology
  Scout        reduce cost or enable new          docs, papers       enablers
               products.                                             

  Contrarian   Search for neglected niches and    Same sources,      Contrarian
  Scout        reasons conventional views may be  different          hypotheses
               wrong.                             objective          
  --------------------------------------------------------------------------------

## 7.2 Idea Generation Crew

Generation is diversified by mechanism. Multiple agents receive the same
qualified problem but are instructed to create ideas through different
business-design lenses. This produces genuine search diversity rather
than many copies of the same prompt.

  ---------------------------------------------------------------------------
  **Generator lens**    **Question**
  --------------------- -----------------------------------------------------
  AI-native automation  Can the workflow be largely executed by autonomous
                        software agents?

  Vertical SaaS         Can this become a focused system of record/workflow
                        for one industry?

  API / infrastructure  Can the capability be sold as a programmable
                        primitive?

  Data product          Can unique aggregation, transformation, or inference
                        become the product?

  Compliance /          Does regulation or risk create recurring mandatory
  assurance             demand?

  Developer tool        Can the problem be solved inside software delivery or
                        operations?

  Service-to-software   Can a remote expert workflow be productized and
                        progressively automated?

  Marketplace / network Can digital participants create a reinforcing
                        two-sided network?

  Business-model        Can pricing/distribution change make an existing
  innovation            solution substantially better?

  Newly possible        What has become feasible because of a recent
                        cost/capability discontinuity?
  ---------------------------------------------------------------------------

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

  --------------------------------------------------------------------------------
  **Agent**        **Mandate**                            **Must not do**
  ---------------- -------------------------------------- ------------------------
  Demand Analyst   Find evidence that the problem exists, Treat idea description
                   is frequent, urgent, and budgeted.     as evidence.

  Skeptic          Find evidence that demand is weak or   Optimize for agreement.
                   the problem is tolerable.              

  Competitive      Map direct, adjacent, internal-build,  Only search for exact
  Analyst          and status-quo alternatives.           product-name
                                                          competitors.

  Buyer Analyst    Identify buyer, user, budget owner,    Invent
                   procurement constraints, and buying    willingness-to-pay.
                   triggers.                              

  Economics        Model plausible price, gross margin,   Hide uncertain
  Analyst          CAC range, support burden, and         assumptions.
                   payback.                               

  Technical        Assess whether available digital tools Assume proprietary
  Analyst          can implement the product.             breakthroughs.

  Distribution     Identify credible acquisition channels Equate market size with
  Analyst          and bottlenecks.                       reachable demand.

  Assumption       Decompose the candidate into           Collapse several
  Auditor          falsifiable assumptions; identify      assumptions into one
                   which assumptions can independently    vague "market
                   kill the business.                     attractiveness" score.

  Source-Lineage   Detect derivative, syndicated, copied, Count URLs as
  Analyst          or common-origin sources and calculate independent evidence
                   effective evidence independence.       simply because they are
                                                          different pages.

  Calibration      Compare prior model predictions with   Treat evaluator
  Judge            later observed outcomes and estimate   confidence as calibrated
                   evaluator calibration by task type.    without historical
                                                          evidence.
  --------------------------------------------------------------------------------

## 7.5 Red-Team Crew

The red team has a deliberately asymmetric objective: kill the idea if
credible evidence supports rejection. Its score cannot be overwritten by
the original generator.

-   Market too small or not reachable

-   Problem lacks urgency

-   Incumbent response

-   AI/software commoditization

-   Customer inertia and switching costs

-   Poor unit economics

-   Weak distribution

-   Technical dependency or platform risk

-   Regulatory/legal constraints

-   Easy replication / weak defensibility

-   Hidden human-service burden

-   Data-access or licensing risk

# 8. Tool Architecture

Agents do not receive unrestricted access to all tools. A Tool Gateway
provides least-privilege capabilities, quotas, audit logs, domain
restrictions, caching, and approval requirements. CrewAI supports custom
tools/APIs and current documentation includes web scraping/browser tools
and structured research integrations; MCP can be used as an
interoperability boundary for external tools.

  ----------------------------------------------------------------------------------
  **Tool class**    **Purpose**            **Typical                **Risk class**
                                           implementations**        
  ----------------- ---------------------- ------------------------ ----------------
  Search / research Discover sources and   Search API, Tavily-style Low
                    market evidence.       research, curated feeds  

  Web fetch /       Read pages and         HTTP fetch,              Medium
  browser           interact with dynamic  Playwright/Selenium,     
                    sites.                 managed browser          

  Company           Competitors, pricing,  Public APIs, datasets,   Low--Medium
  intelligence      positioning,           search                   
                    financial/public data.                          

  Regulatory        Official rules,        Government/EU/industry   Low
                    guidance,              sources                  
                    consultations,                                  
                    changes.                                        

  Community         Pain points and        Forums, Reddit, reviews, Medium
  evidence          practitioner language. communities              

  GitHub / software Assess technical       GitHub API/search        Low
  ecosystem         feasibility and                                 
                    ecosystem saturation.                           

  Financial model   Unit economics,        Deterministic Python     Low
                    scenarios,             functions                
                    sensitivity.                                    

  Database /        Store and query        PostgreSQL +             Low
  knowledge graph   persistent             vector/graph extension   
                    entities/evidence.                              

  Code sandbox      Prototype calculations Isolated container       Medium
                    or proof-of-concept                             
                    logic.                                          

  Outbound          Optional later-stage   Email/CRM APIs           High; human
  communication     interviews/outreach.                            approval
                                                                    required

  Experiment        Measure real behavior  Analytics, event         Medium
  instrumentation   in approved digital    tracking, form/waitlist  
                    experiments.           metrics, experiment      
                                           database                 

  Prototype /       Create isolated        Static hosting, sandbox  High; approval
  landing-page      digital prototypes for app platform, feature    for public
  deployment        demand or usability    flag/test environment    exposure/spend
                    tests.                                          

  Advertising /     Test channel response, Ad platform APIs or      High; explicit
  acquisition test  CTR, CPC, signup or    managed campaign tool    spend approval
                    lead conversion.                                

  Interview /       Record structured      CRM, forms, approved     High; human
  outreach capture  customer/prospect      email/calendar           approval
                    responses.             connectors               
  ----------------------------------------------------------------------------------

## 8.1 Tool Safety Policy

-   Research agents are read-only by default.

-   All external requests are logged with agent, task, query, timestamp,
    and source.

-   Browser actions that submit forms, create accounts, purchase, post,
    or send messages require a separate permission.

-   Code execution occurs in a sandbox without production credentials.

-   Outbound contact, financial spend, or public publication requires
    human approval.

-   Per-run and per-agent quotas cap search volume, browser time,
    tokens, and external API spend.

## 8.2 MVP Tool Set: Required Ten Tools

The first production-capable implementation MUST expose exactly the
following ten logical tools to CrewAI. A logical tool may wrap more than
one provider internally, but agents call the stable DBIE contract rather
than provider-specific SDKs. This prevents Crew code from depending on
Tavily, Serper, Reddit, GitHub, PostgreSQL, or another vendor directly.

  --------------------------------------------------------------------------------------------------------------------------------------------------------
  ID          CrewAI logical tool        Recommended implementation       Primary actors          Call only when                Must not be used for
  ----------- -------------------------- -------------------------------- ----------------------- ----------------------------- --------------------------
  T01         `web_search`               **SearXNG** self-hosted          Trend Scout, Pain-Point Discovery of candidate        Treating snippets as
                                         metasearch as default; optional  Miner, Market Analyst,  sources, competitors,         evidence; final factual
                                         paid/search-provider fallback    Competitor Analyst, Red statistics, market changes,   extraction without opening
                                                                          Team                    terminology, or               the source
                                                                                                  corroborating/contradicting   
                                                                                                  evidence                      

  T02         `fetch_page`               **Trafilatura** for lightweight  Evidence Researcher,    A URL has been selected and   Broad discovery;
                                         static extraction → **Crawl4AI** Market Analyst,         its primary content must be   autonomous form
                                         for structured/complex crawling  Competitor Analyst,     read, quoted, structured, or  submission; login/paywall
                                         → **Playwright** only when       Source-Lineage Analyst, lineage-checked               circumvention
                                         browser rendering/interaction is Red Team                                              
                                         required                                                                               

  T03         `search_reddit`            **PRAW** over the Reddit API,    Pain-Point Miner,       Looking for recurring         Establishing market size,
                                         normalized by the Tool Gateway   Customer-Pain Analyst,  practitioner pain,            legal facts, or treating
                                                                          Distribution Analyst,   workarounds, buying language, anecdotes as
                                                                          Red Team                switching behavior,           representative statistics
                                                                                                  complaints, or                
                                                                                                  counterevidence               

  T04         `search_companies`         OSS-first aggregation using      Competitor Analyst,     Identifying competitors,      Inventing
                                         **SearXNG +                      Market Analyst,         entrants, positioning,        revenue/employee/funding
                                         Crawl4AI/Trafilatura +           Distribution Analyst,   funding, customer segments,   data when unavailable;
                                         Wikidata/OpenCorporates/public   Red Team                company density, or           silently merging similarly
                                         company sites**; optional                                comparable vendors            named companies
                                         commercial company-data                                                                
                                         connectors remain pluggable                                                            

  T05         `search_github`            **PyGithub** over GitHub         Technology Scout,       Assessing whether enabling    Executing arbitrary
                                         REST/GraphQL/search APIs; direct Technical Analyst,      technology exists, ecosystem  repository code; treating
                                         API calls allowed where PyGithub Prototype/Feasibility   maturity, OSS alternatives,   stars alone as demand
                                         lacks coverage                   Agent, Red Team         developer activity,           evidence
                                                                                                  integration feasibility, or   
                                                                                                  commoditization               

  T06         `search_regulations`       Official-source adapters:        Regulatory Scout,       A business opportunity        Legal advice; reliance on
                                         **EUR-Lex APIs/SPARQL** plus EU  Regulatory Analyst, Red depends on a regulation,      blogs when an
                                         Commission, FINMA, EBA, ECB,     Team                    mandate, compliance           authoritative primary
                                         ESMA, SEC and configured                                 obligation, deadline,         source exists
                                         authorities; SearXNG only for                            license, restriction, or      
                                         discovery fallback                                       regulatory change             

  T07         `read_document`            **Docling** as primary           Evidence Researcher,    A report, filing, paper,      Summarizing an unseen
                                         multi-format parser; **PyMuPDF** Regulatory Analyst,     policy, PDF, spreadsheet, or  document from a search
                                         as fast PDF/fallback extractor;  Market Analyst,         document contains relevant    snippet or title
                                         page/section/table provenance    Technical Analyst       primary evidence              
                                         preserved                                                                              

  T08         `python_execute`           **Ephemeral Docker sandbox**     Economics Analyst,      Deterministic calculations,   Network access by default;
                                         with no production               Calibration Judge,      sensitivity analysis,         arbitrary production
                                         credentials/network by default;  Technical Analyst,      statistics, deduplication,    changes; replacing a
                                         Onyx Python Sandbox may be used  Scoring Service caller  simulations, evidence         deterministic service with
                                         as the implementation package                            clustering, calibration, or   prose arithmetic
                                         where suitable                                           prototype micro-tests are     
                                                                                                  required                      

  T09         `database_query`           **PostgreSQL + SQLAlchemy**      Flow Controller,        Reading/writing canonical     Raw unrestricted SQL from
                                         through a DBIE data-access       Evidence Researcher,    ideas, assumptions, claims,   agents; schema changes;
                                         service; parameterized reads and Assumption Auditor,     evidence, source lineage,     destructive operations
                                         constrained writes               Source-Lineage Analyst, outcomes, run metadata, and   
                                                                          Calibration Judge       evaluation records            

  T10         `semantic_memory_search`   **PostgreSQL + pgvector** with a All research/validation Retrieving prior related      Treating remembered
                                         small local **BGE- or E5-family  actors; especially      ideas, problems, assumptions, judgments as fresh
                                         embedding model**, preferably    Discovery, Ideation,    evidence, competitors,        evidence; allowing prior
                                         CPU-served; separate vector DB   Assumption Auditor, Red experiments, or lessons       rankings to bias
                                         only if later justified          Team                    before duplicate research is  independent validation
                                                                                                  performed                     without provenance
  --------------------------------------------------------------------------------------------------------------------------------------------------------

The MVP SHOULD NOT add advertising, outbound email, public deployment,
CRM mutation, payments, or production cloud-management tools. Those
belong to a later experiment-execution tier because they create external
side effects.

## 8.2.1 v0.6 Open-Source Adapter Stack

The ten names above are the **only capabilities exposed to CrewAI**. The
libraries and services below are implementation details owned by the
Tool Gateway. Agents MUST NOT receive separate tools named `crawl4ai`,
`playwright`, `docling`, `searxng`, `pgvector`, etc.; overlapping
choices materially increase small-model tool-selection errors and couple
prompts to infrastructure.

  -------------------------------------------------------------------------------------
  Logical tool               Internal adapter chain           Selection policy
  -------------------------- -------------------------------- -------------------------
  `web_search`               **SearXNG**                      Default discovery
                                                              adapter. Normalize URL,
                                                              title, snippet, engine
                                                              provenance, rank and
                                                              timestamp. A commercial
                                                              provider may be
                                                              configured only as
                                                              fallback/benchmark,
                                                              without changing the
                                                              CrewAI schema.

  `fetch_page`               **Trafilatura → Crawl4AI →       Start with the cheapest
                             Playwright**                     extractor. Promote to
                                                              Crawl4AI when structure,
                                                              links, repeated pages,
                                                              JS-aware crawling, or
                                                              schema extraction is
                                                              needed. Launch Playwright
                                                              only when content cannot
                                                              be obtained without
                                                              browser
                                                              rendering/interactions.

  `search_reddit`            **PRAW / Reddit API**            Fetch posts/comments and
                                                              native metadata. Cache
                                                              aggressively and preserve
                                                              subreddit/post/comment
                                                              IDs, dates and
                                                              permalinks.

  `search_companies`         **SearXNG +                      Merge only after entity
                             Crawl4AI/Trafilatura +           resolution. Keep each
                             Wikidata/OpenCorporates/public   provider field separately
                             registries/company sites**       until confidence in
                                                              company identity is
                                                              sufficient. Optional
                                                              commercial adapters may
                                                              enrich but are never
                                                              assumed available.

  `search_github`            **PyGithub + GitHub              Prefer structured API
                             REST/GraphQL/search APIs**       data for repositories,
                                                              issues, discussions,
                                                              releases and activity.
                                                              Use page crawling only
                                                              when API-visible content
                                                              is insufficient.

  `search_regulations`       **EUR-Lex APIs/SPARQL +          Primary legal/regulatory
                             regulator-specific official      evidence must come from
                             adapters**                       authoritative sources.
                                                              General search is a
                                                              locator, not the evidence
                                                              authority.

  `read_document`            **Docling → PyMuPDF fallback**   Docling handles
                                                              structured multi-format
                                                              parsing. PyMuPDF is
                                                              preferred for fast/simple
                                                              PDF extraction or
                                                              fallback when Docling
                                                              fails. Both return
                                                              page/section/table
                                                              provenance.

  `python_execute`           **Ephemeral Docker sandbox**;    New container per
                             optionally **Onyx Python         execution/session policy;
                             Sandbox** implementation         CPU/RAM/time/output
                                                              limits; no host mounts
                                                              except explicit read-only
                                                              inputs; no production
                                                              secrets; network disabled
                                                              by default.

  `database_query`           **PostgreSQL + SQLAlchemy**      Agents never receive raw
                                                              unrestricted credentials.
                                                              Reads/writes pass
                                                              application services,
                                                              schemas and row/action
                                                              permissions.

  `semantic_memory_search`   **pgvector + local BGE/E5        Embeddings are generated
                             embedding service**              outside the primary LLM.
                                                              Prefer CPU serving so the
                                                              16 GB inference GPU
                                                              remains available for
                                                              generation and KV cache.
  -------------------------------------------------------------------------------------

### Adapter selection for `fetch_page`

``` text
fetch_page(url, purpose, extraction_schema?)
        |
        +-- static/readable HTML? ----------> Trafilatura
        |                                      |
        |                                      +--> normalized Markdown + metadata
        |
        +-- complex/site crawl/structured? --> Crawl4AI
        |                                      |
        |                                      +--> Markdown/records/links + metadata
        |
        +-- JS/render/browser required? ----> Playwright
                                               |
                                               +--> rendered DOM/content
```

Escalation is deterministic. A CrewAI agent asks only for `fetch_page`;
it does **not** choose the adapter. The gateway records every escalation
and why it occurred. This both reduces token/tool confusion and allows
later performance tuning without agent-prompt changes.

### Document adapter selection

`read_document` first detects media type. Docling is the standard path
for PDF/DOCX/PPTX/XLSX/HTML/image-rich documents requiring layout, table
or section structure. PyMuPDF is used for fast text-oriented PDFs, page
rendering, targeted extraction, or recovery when Docling cannot parse
reliably. The normalized response MUST preserve source file hash, page
numbers, section/table identity where available, extraction
adapter/version, and any parser warnings.

### Local embedding service

Semantic memory uses a dedicated small embedding model rather than the
primary agent model. The embedding adapter exposes only
`embed(texts, profile)` internally and stores the model identifier and
dimensionality with each vector. The initial profile SHOULD use a
compact BGE- or E5-family model that can run acceptably on CPU.
Re-embedding is a migration operation, not an implicit side effect of
retrieval.

### Search-company composition

There is no single free/open source equivalent of commercial
private-company intelligence. `search_companies` therefore composes
evidence from public sources. Entity resolution is mandatory before
merging observations. Funding, employee count, revenue, ownership, and
customer claims must retain field-level provenance; absence of a public
value is `UNKNOWN`, never an inferred fact.

### Regulatory adapter policy

`search_regulations` maintains a registry of jurisdiction adapters. Each
adapter translates a common query (`jurisdiction`, `topic`,
`effective_date_window`, `entity_type`, `status`) to the official
authority. EUR-Lex API/SPARQL is the first EU implementation.
FINMA/EBA/ECB/ESMA/SEC adapters may use their official APIs, feeds,
search endpoints, or targeted crawling as appropriate. Regulatory text
is stored with authority, document identifier, status,
publication/effective dates and exact source URL.

### Sandbox policy

The Python adapter is an execution service, not a shell-access tool.
Default limits include:

-   no outbound network;
-   no Docker socket;
-   no host home-directory mount;
-   no cloud/database/tool credentials;
-   explicit CPU, RAM, wall-clock and output limits;
-   read-only mounted inputs only when authorized;
-   ephemeral filesystem unless the Flow explicitly captures declared
    outputs;
-   package installation disabled by default or restricted to a curated
    cache/allowlist.

The Tool Gateway validates the requested operation before creating a
sandbox and captures code, inputs, environment profile, stdout/stderr,
exit status, resource use and output hashes.

### Why adapters remain below CrewAI

This v0.6 boundary is normative:

``` text
CrewAI actor
   |
   +--> one of 10 stable DBIE tools
            |
            v
       Tool Gateway
       /    |     \
 policy   routing   audit
            |
            +--> SearXNG / Crawl4AI / Trafilatura / Playwright
            +--> PRAW / PyGithub / official regulatory adapters
            +--> Docling / PyMuPDF
            +--> Docker sandbox
            +--> PostgreSQL / SQLAlchemy / pgvector / embeddings
```

Changing or adding an internal adapter MUST NOT require changing CrewAI
agent definitions unless the **logical capability itself** changes.

## 8.2.2 Adapter fallback and health rules

Every adapter implements internal `health`, `execute`, and capability
metadata. The Tool Gateway owns fallbacks. A failed adapter may be
retried or escalated only if the alternative preserves the original
logical-tool semantics. Fallback results are tagged so evaluation can
detect systematic source/provider differences.

For each adapter the system records latency, success/failure category,
bytes/documents returned, cache hit, parser quality warnings, and
resource consumption. Adapter choice SHOULD eventually be optimized by
measured reliability/cost, but deterministic routing rules are preferred
for the MVP.

## 8.2.3 OSS deployment topology

The MVP can run these adapters as local services/processes:

``` text
Host
├── DBIE Python + CrewAI
├── PostgreSQL + pgvector
├── SearXNG
├── Crawl4AI service/worker
├── Playwright browser worker
├── local embedding service (CPU preferred)
├── Docker sandbox workers
└── vLLM or Ollama inference server
```

Trafilatura, Docling, PyMuPDF, PRAW, PyGithub and SQLAlchemy may
initially run in the DBIE application/worker process if resource
isolation is acceptable. Crawl/browser/sandbox workloads SHOULD have
separate worker concurrency limits so web extraction cannot starve LLM
inference or the control plane.

## 8.3 CrewAI Integration Pattern

CrewAI agents MUST receive DBIE logical tools through their `tools`
configuration. Provider credentials and provider-specific SDK objects
remain below the Tool Gateway. A tool is implemented either as a CrewAI
custom `BaseTool`/decorated tool or as an MCP-exposed capability wrapped
by the same logical contract. The preferred boundary is:

``` text
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

The CrewAI layer sees only stable names such as `web_search` or
`search_github`. It MUST NOT know API keys or provider-specific
endpoints. Provider switching is therefore a Tool Gateway concern, not
an agent prompt change.

Each agent has an explicit allowlist. A tool call not on that actor's
allowlist is rejected by the gateway even if the model attempts to call
it. The Flow owns stage-level budgets and may further restrict an
agent's normal allowlist for a specific task.

## 8.4 Common Tool Call Envelope

Every tool invocation MUST be represented internally by a common
envelope before execution:

``` json
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

The gateway adds provider, start/end timestamps, cache status, cost,
response hash, error state, and provenance before persisting the call.
The LLM does not choose or modify `run_id`, credentials, quotas, or
policy fields.

## 8.5 Tool-Specific Call Contracts and Invocation Rules

### T01 --- `web_search`

**Actors:** Trend Scout, Pain-Point Miner, Market Analyst, Competitor
Analyst, Distribution Analyst, Red Team.

**Call when:** the actor needs to discover candidate sources or test
whether an assertion has external support or contradiction. Discovery
actors may use it broadly; validation actors MUST tie each call to an
assumption or claim.

**Input contract:**

``` json
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

**Output:** ranked URLs with title, snippet, source domain, publication
date when available, result type, and provider metadata.

**Required follow-up:** snippets are discovery material only. Any result
used as evidence MUST normally be opened with `fetch_page` or
`read_document`, unless the source is a structured API whose returned
field is itself the primary data.

**Call discipline:** one focused query per uncertainty. Avoid query
floods that merely paraphrase the same proposition. Cache identical
normalized queries within a run.

### T02 --- `fetch_page`

**Actors:** Evidence Researcher, Market Analyst, Competitor Analyst,
Source-Lineage Analyst, Red Team.

**Call when:** a specific public URL discovered by search, memory, or
another document contains potentially decision-relevant evidence.

**Input contract:**

``` json
{
  "url": "https://...",
  "mode": "READ|EXTRACT",
  "extract_fields": ["optional typed fields"],
  "render_js": "AUTO|NO|YES",
  "max_chars": 50000
}
```

**Output:** canonical URL, page title, publication/update date when
detectable, author/publisher, extracted text, structured fields, HTTP
metadata, content hash, and links to likely primary sources.

**Rules:** use simple HTTP retrieval first; browser rendering is
fallback. Never submit forms, authenticate, purchase, post, or bypass
access controls in the MVP. Source-Lineage Analyst uses canonical URL,
content hashes, citations, and publication relationships to identify
derivative sources.

### T03 --- `search_reddit`

**Actors:** Pain-Point Miner, Customer-Pain Analyst, Distribution
Analyst, Red Team.

**Call when:** the system needs qualitative evidence about recurring
pain, current workarounds, willingness language, switching friction,
practitioner terminology, or reasons existing tools fail.

**Input contract:**

``` json
{
  "query": "string",
  "subreddits": ["optional"],
  "date_from": "optional ISO date",
  "sort": "RELEVANCE|NEW|TOP",
  "max_threads": 20,
  "include_comments": true
}
```

**Output:** thread/comment text, permalink, subreddit, timestamps,
scores, author pseudonym/hash where policy permits, and engagement
metadata.

**Rules:** Reddit observations are `OBSERVED_QUALITATIVE`, not
market-size measurements. Multiple comments in one thread are one source
family for independence scoring unless there is evidence of genuinely
independent observations. Personally identifying information is not
persisted unless required and permitted.

### T04 --- `search_companies`

**Actors:** Competitor Analyst, Market Analyst, Distribution Analyst,
Red Team.

**Call when:** evaluating market structure, competitor density,
comparable products, funding, positioning, buyer segments, or likely
distribution channels.

**Input contract:**

``` json
{
  "query": "string",
  "mode": "COMPETITORS|COMPANY_LOOKUP|CATEGORY|FUNDING|POSITIONING",
  "geography": ["optional"],
  "max_results": 25
}
```

**Output:** normalized company records with aliases, URLs,
product/category description, geography, founded date, funding/public
financial fields when sourced, evidence URLs, and confidence in entity
resolution.

**Rules:** every numeric company field must carry its source and
observation date. The tool returns `UNKNOWN`, not an LLM estimate, for
unavailable revenue, headcount, funding, or customers. Entity resolution
must preserve source records so similarly named companies cannot be
silently merged.

### T05 --- `search_github`

**Actors:** Technology Scout, Technical Analyst, Prototype/Feasibility
Agent, Red Team.

**Call when:** the opportunity depends on existing software
capabilities, APIs, open-source projects, developer ecosystems,
implementation complexity, commoditization, or integration availability.

**Input contract:**

``` json
{
  "query": "string",
  "mode": "REPOSITORIES|CODE|ISSUES|TOPICS",
  "language": "optional",
  "updated_after": "optional ISO date",
  "max_results": 20
}
```

**Output:** repository identifiers, description, license, last update,
stars/forks/watchers when available, contributors/activity indicators,
topics, relevant files/issues, and canonical GitHub URLs.

**Rules:** popularity metrics are ecosystem signals, not demand proof.
Repository code is never executed automatically. If a feasibility test
requires execution, the Flow must explicitly pass selected code or a
minimal reimplementation into the isolated `python_execute`/prototype
sandbox after policy checks.

### T06 --- `search_regulations`

**Actors:** Regulatory Scout, Regulatory Analyst, Red Team.

**Call when:** an idea depends on a legal/regulatory obligation,
compliance deadline, regulator guidance, required control, reporting
requirement, license, prohibition, or rule change.

**Input contract:**

``` json
{
  "query": "string",
  "jurisdictions": ["EU", "CH"],
  "authorities": ["optional configured authorities"],
  "status": "IN_FORCE|PROPOSED|CONSULTATION|ANY",
  "date_from": "optional ISO date",
  "max_results": 20
}
```

**Output:** official instrument/guidance title, authority, jurisdiction,
status, relevant dates, official URL, affected entities where
extractable, and text excerpts/references.

**Rules:** official primary sources rank above summaries. Secondary
commentary may aid discovery but cannot establish the controlling
regulatory claim when a primary source is available. The tool produces
research evidence, not legal advice. Material ambiguity is escalated to
human/legal review rather than resolved by model voting.

### T07 --- `read_document`

**Actors:** Evidence Researcher, Regulatory Analyst, Market Analyst,
Technical Analyst, Economics Analyst.

**Call when:** decision-relevant evidence resides in a PDF, report,
filing, spreadsheet, paper, policy, or long-form document.

**Input contract:**

``` json
{
  "source": "URL or stored document_id",
  "query": "what information is needed",
  "sections": ["optional"],
  "tables": true,
  "max_pages": 100
}
```

**Output:** document metadata, matched passages with page/section
coordinates, extracted tables where possible, dates/authors/publisher,
and content hash.

**Rules:** downstream claims must retain page/section references. The
system must not cite a document that was only mentioned by a search
result. For large documents, retrieval may be staged, but evidence must
point to the actual source range used.

### T08 --- `python_execute`

**Actors:** Economics Analyst, Calibration Judge, Technical Analyst,
Source-Lineage Analyst, Scoring/Portfolio service caller.

**Call when:** a result is better produced deterministically than
linguistically: TAM/SAM/SOM arithmetic, unit economics, sensitivity
analysis, Monte Carlo simulation, confidence intervals, deduplication,
clustering, calibration, ranking diagnostics, or a bounded feasibility
micro-test.

**Input contract:**

``` json
{
  "code": "Python source",
  "input_artifacts": ["optional stored artifact ids"],
  "purpose": "CALCULATION|STATISTICS|SIMULATION|CLUSTERING|CALIBRATION|MICRO_TEST",
  "timeout_seconds": 60,
  "memory_mb": 2048,
  "network": false
}
```

**Output:** stdout/stderr, structured result payload, generated artifact
references, runtime, exit status, and source-code hash.

**Rules:** network disabled by default; no production credentials; no
host filesystem beyond mounted task inputs; fixed CPU/RAM/time limits.
Important numeric results are reproducible from persisted code, inputs,
and environment version. LLM prose arithmetic MUST NOT override
deterministic results.

### T09 --- `database_query`

**Actors:** Flow Controller plus all stateful research/evaluation actors
through constrained operations.

**Call when:** canonical DBIE state must be persisted or retrieved.

**Input contract:** agents do not submit arbitrary SQL. They call named
operations such as:

``` json
{
  "operation": "GET_ASSUMPTION|UPSERT_EVIDENCE|LINK_EVIDENCE|GET_IDEA|SAVE_EVALUATION|GET_OUTCOMES|GET_SOURCE_LINEAGE",
  "parameters": {}
}
```

**Output:** typed DBIE entities with IDs, versions, timestamps, and
provenance.

**Rules:** schema changes and destructive deletes are never exposed to
agents. Writes use optimistic versioning/idempotency keys. Flow
Controller owns lifecycle transitions. Evidence records are
append-oriented; corrections create new versions rather than silently
rewriting historical observations.

### T10 --- `semantic_memory_search`

**Actors:** Discovery, Ideation, Assumption Auditor, Evidence
Researcher, Competitor Analyst, Red Team, Calibration Judge.

**Call when:** before researching or generating around a problem, the
actor needs to know what DBIE already learned that is semantically
related.

**Input contract:**

``` json
{
  "query": "string",
  "entity_types": ["PROBLEM", "IDEA", "ASSUMPTION", "EVIDENCE", "COMPETITOR", "EXPERIMENT", "OUTCOME", "LESSON"],
  "filters": {"optional": "typed filters"},
  "top_k": 10,
  "exclude_current_run": false
}
```

**Output:** entity IDs, short canonical text, similarity score, entity
type, source/evidence status, creation/update dates, and links to
canonical database records.

**Rules:** memory is a retrieval hint, not independent evidence. A prior
conclusion can inform search queries or priors but MUST NOT be counted
as new support for an assumption. Validation agents can request
`exclude_current_run=true` or hide prior verdicts when independence is
required.

## 8.6 Actor-to-Tool Permission Matrix

`R` = read/research use; `W` = constrained canonical-state write; `C` =
deterministic compute; blank = not granted by default.

  ----------------------------------------------------------------------------------------------------------
  Actor               T01    T02      T03         T04      T05           T06    T07      T08 T09 DB      T10
                      Web   Page   Reddit   Companies   GitHub   Regulations   Docs   Python          Memory
  ---------------- ------ ------ -------- ----------- -------- ------------- ------ -------- ------ --------
  Flow Controller                                                                                 W        R

  Trend Scout           R      R                    R        R             R      R               W        R

  Pain-Point Miner      R      R        R                                         R               W        R

  Technology Scout      R      R                             R                    R               W        R

  Regulatory Scout      R      R                                           R      R               W        R

  Idea Generator                                                                                  W        R

  Assumption                                                                                      W        R
  Auditor                                                                                           

  Evidence              R      R        R           R        R             R      R               W        R
  Researcher                                                                                        

  Market Analyst        R      R        R           R                             R        C      W        R

  Competitor            R      R        R           R        R                    R               W        R
  Analyst                                                                                           

  Regulatory            R      R                                           R      R               W        R
  Analyst                                                                                           

  Technical             R      R                             R                    R        C      W        R
  Analyst                                                                                           

  Economics             R      R                    R                             R        C      W        R
  Analyst                                                                                           

  Distribution          R      R        R           R                             R               W        R
  Analyst                                                                                           

  Source-Lineage        R      R                                                  R        C      W        R
  Analyst                                                                                           

  Calibration                                                                              C      W        R
  Judge                                                                                             

  Red Team              R      R        R           R        R             R      R        C      W        R
  ----------------------------------------------------------------------------------------------------------

Idea-generation actors intentionally receive little or no live external
research access once the discovery package has been assembled. This
preserves separation between evidence collection and creative
recombination and reduces the tendency to copy already-visible products.
The Flow can authorize an exception when the generator explicitly
requests evidence for a missing prerequisite, but that request is logged
and handled by a research actor rather than granting the generator
unrestricted search.

## 8.7 Stage-by-Stage Tool Calling Policy

  --------------------------------------------------------------------------------------
  Flow stage                Required calls    Conditional calls Prohibited/default-off
                                                                calls
  ------------------------- ----------------- ----------------- ------------------------
  `initialize_run`          T09, T10          none              T01--T08

  `discover_signals`        T01, T02, T09,    T03, T04, T05,    T08 unless needed for
                            T10               T06, T07          dedup/statistics

  `generate_ideas`          T10, T09          none normally     unrestricted T01--T08

  `eligibility_gate`        T09               T08 for           external research unless
                                              deterministic     a required fact is
                                              thresholds        missing

  `decompose_assumptions`   T09, T10          none              external research
                                                                normally

  `validate`                T01, T02, T07,    T03--T06 by       side-effecting external
                            T09, T10          assumption type;  tools
                                              T08 for           
                                              calculations      

  `red_team`                T01, T02, T09,    T03--T08 as       side-effecting external
                            T10               attack vector     tools
                                              requires          

  `rank_portfolio`          T09, T10, T08     external model    new evidence collection
                                              judge via Model   unless rank is blocked
                                              Gateway, not an   by an explicit gap
                                              MVP tool          

  `design_experiment`       T09, T10, T08     T01/T02 for       public deployment/spend
                                              benchmark design  in MVP

  `learn_from_outcome`      T09, T10, T08     none              reinterpreting outcomes
                                                                via fresh web evidence
                                                                before storing the raw
                                                                result
  --------------------------------------------------------------------------------------

## 8.8 Evidence Routing by Assumption Type

The Assumption Auditor assigns a category, and the Flow routes the
validation task to the actor/tool combination below.

  -----------------------------------------------------------------------------
  Assumption        Primary actor      First tools       Escalation tools
  category                                               
  ----------------- ------------------ ----------------- ----------------------
  DEMAND / PAIN     Pain-Point Miner   T01, T02, T03     T04, T07
                    or Market Analyst                    

  BUYER             Market Analyst     T01, T02, T04     T03, T07

  WILLINGNESS TO    Market/Economics   T01, T02, T04,    later real experiment;
  PAY               Analyst            T07               do not infer from LLM
                                                         persona

  DISTRIBUTION      Distribution       T01, T02, T03,    T07, later channel
                    Analyst            T04               experiment

  FEASIBILITY       Technical Analyst  T05, T02, T07     T08 micro-test

  AUTOMATION        Technical Analyst  T05, T07          T08
                                                         micro-test/prototype
                                                         benchmark

  ECONOMICS         Economics Analyst  T04, T07, T09     T08 deterministic
                                                         model

  DEFENSIBILITY     Competitor         T01, T02, T04,    T07
                    Analyst + Red Team T05               

  REGULATORY        Regulatory Analyst T06, T02, T07     human/legal review on
                                                         ambiguity
  -----------------------------------------------------------------------------

## 8.9 Tool-Call Stopping Rules

Research agents MUST stop calling tools when one of the following
becomes true:

1.  The assumption reaches its configured evidence threshold with at
    least the required number of independent source families.
2.  A fatal contradiction is established from sufficiently authoritative
    evidence.
3.  Additional calls are returning only derivative or duplicate sources.
4.  The remaining uncertainty cannot be resolved by research and
    requires an experiment.
5.  Stage search/cost/time budget is exhausted.
6.  An authoritative primary source directly resolves the factual
    question.

The Flow, not the agent, decides whether the stage advances after a
stopping condition. This prevents agents from extending research simply
because the model can continue searching.

## 8.10 CrewAI Agent Configuration Rule

Each CrewAI agent definition MUST declare four tool-related fields in
addition to role/goal/backstory:

``` yaml
tool_policy:
  allow: [web_search, fetch_page]
  max_calls_per_task: 12
  max_parallel_calls: 2
  require_assumption_id: true
  primary_source_required_for: [REGULATORY, MATERIAL_NUMERIC_CLAIM]
```

The Tool Gateway is authoritative. Prompt-level instructions are defense
in depth only; they are not considered an access-control mechanism.

## 8.11 MCP Boundary

Where feasible, provider adapters SHOULD be exposed through MCP so the
same ten logical capabilities can be reused by another harness later.
CrewAI-specific wrappers translate CrewAI tool calls to DBIE contracts;
MCP clients translate DBIE contracts to provider/server calls. The
canonical schemas, evidence semantics, quotas, and audit model remain
owned by DBIE.

This means replacing CrewAI does not require rewriting `web_search`,
`search_github`, `search_regulations`, memory, or database integrations.
Conversely, replacing Tavily with another search provider does not
change CrewAI agents.

## 8.12 MVP Tool Acceptance Criteria

The ten-tool MVP is complete only when:

-   every tool has a typed input/output schema and unit/smoke tests;
-   every call is attributable to run, stage, task, actor, idea, and
    assumption where applicable;
-   every external result records source/provider, timestamp, and
    content/result hash where meaningful;
-   provider credentials never enter LLM context;
-   actor allowlists are enforced outside prompts;
-   search snippets cannot be promoted directly to evidence without an
    explicit permitted exception;
-   T08 execution is isolated and reproducible;
-   T09 does not expose arbitrary destructive SQL;
-   T10 marks remembered material distinctly from newly collected
    evidence;
-   duplicate/derivative source families are detectable;
-   per-task call, time, and cost budgets are enforced;
-   tool errors degrade to explicit evidence gaps rather than fabricated
    answers;
-   no MVP tool can spend money, send communication, publish externally,
    create accounts, or modify production systems.

# 9. Evidence Model

The core unit of validation is the falsifiable assumption. Claims and
evidence exist to update an assumption; reports are generated from these
structured objects. Every assumption identifies what observation would
increase confidence, what observation would falsify it, and whether the
current status is UNKNOWN, RESEARCH_SUPPORTED, RESEARCH_CONTRADICTED,
EXPERIMENT_SUPPORTED, EXPERIMENT_CONTRADICTED, or INCONCLUSIVE.

Assumption {\
assumption_id\
idea_id\
category: DEMAND \| BUYER \| WTP \| DISTRIBUTION \| AUTOMATION \|\
ECONOMICS \| FEASIBILITY \| DEFENSIBILITY \| REGULATORY\
statement\
criticality: FATAL \| MATERIAL \| SECONDARY\
falsification_condition\
validation_condition\
prior_confidence\
current_confidence\
evidence_for_ids\[\]\
evidence_against_ids\[\]\
experiment_ids\[\]\
status\
uncertainty\
created_at\
updated_at\
}

Claim {\
claim_id\
assumption_id\
statement\
direction: SUPPORTS \| CONTRADICTS \| NEUTRAL\
evidence_ids\[\]\
inference_type: MEASURED \| OBSERVED \| INFERRED \| MODEL_JUDGMENT\
confidence\
created_by_agent\
model_version\
prompt_version\
created_at\
}

Evidence {\
evidence_id\
source_url / source_identifier\
source_type\
publisher / author\
observed_at\
published_at\
extracted_fact\
quote_or_excerpt_pointer\
evidence_tier: OBSERVED_BEHAVIOR \| PRIMARY \| SECONDARY \| MODEL_ONLY\
reliability_score\
freshness_score\
lineage_root_id\
independence_group\
content_hash\
}

ExperimentResult {\
experiment_id\
assumption_id\
hypothesis\
protocol_version\
metric\
threshold\
sample_definition\
observed_value\
sample_size\
cost\
started_at\
ended_at\
interpretation\
raw_artifact_refs\[\]\
}

Evidence independence is explicit. Ten pages derived from one press
release, analyst note, survey, or vendor dataset count as one lineage
family until independent provenance is demonstrated. Source quantity
never substitutes for source independence. Observed behavior from a
controlled experiment is stored separately and receives a higher trust
tier than model-generated judgments.

# 10. Candidate Data Model

BusinessIdea {\
idea_id\
problem_id\
title\
one_sentence_thesis\
target_customer\
buyer\
user\
value_proposition\
product_form\
delivery_model\
why_now\
digital_eligibility\
autonomous_scalability\
assumption_ids\[\]\
competitor_ids\[\]\
risk_ids\[\]\
experiment_ids\[\]\
evidence_coverage\
unresolved_fatal_assumptions\
tournament_rating\
decision: BUILD \| ITERATE \| KILL \| MORE_EVIDENCE\
lifecycle_state\
lineage{}\
}

The idea record intentionally does not contain a single authoritative
"truth score." Decision-relevant values live on assumptions, evidence,
experiments, and deterministic economics. Aggregate portfolio metrics
are projections over those objects and must retain their uncertainty.

# 11. Fast Rejection, Uncertainty, and Decision Metrics

## 11.1 Deterministic Rejection

-   Fails any mandatory digital-only criterion.

-   No identifiable customer and economic buyer.

-   No evidence that the stated problem exists.

-   No credible "why now" mechanism.

-   Implementation requires unavailable proprietary technology or
    physical infrastructure.

-   Business is structurally dependent on linear human labor with no
    plausible automation path.

-   Known legal/regulatory constraint makes the proposed operation
    infeasible.

-   Duplicate of an existing candidate above a configured similarity
    threshold without meaningful differentiation.

## 11.2 Evidence-Typed Decision Metrics

The system may compute normalized portfolio metrics for triage, but
every dimension must declare its evidence type: MEASURED, OBSERVED,
INFERRED, MODEL_JUDGMENT, or UNKNOWN. UNKNOWN does not become 5/10; it
remains unknown. MODEL_JUDGMENT cannot by itself satisfy a critical
assumption. Measured and observed values retain sample size, date,
protocol, and uncertainty.

  ----------------------------------------------------------------------------------
  **Dimension**     Triage   Required evidence / interpretation
                    weight   
  ----------------- -------- -------------------------------------------------------
  Problem severity  12%      Economic pain, risk, frequency, deadline pressure.
  / urgency                  Unknowns remain explicit; model judgment alone cannot
                             validate a fatal assumption.

  Willingness to    12%      Evidence that a budget owner will pay enough. Unknowns
  pay                        remain explicit; model judgment alone cannot validate a
                             fatal assumption.

  Reachable market  9%       Serviceable and realistically reachable demand, not
                             headline TAM. Unknowns remain explicit; model judgment
                             alone cannot validate a fatal assumption.

  Growth / why now  8%       Structural tailwinds and timing. Unknowns remain
                             explicit; model judgment alone cannot validate a fatal
                             assumption.

  Digital           12%      Share of delivery/operations that software/agents can
  automation                 perform. Unknowns remain explicit; model judgment alone
  potential                  cannot validate a fatal assumption.

  Gross margin      8%       Economics at scale. Unknowns remain explicit; model
  potential                  judgment alone cannot validate a fatal assumption.

  Distribution      10%      Credible path to customers at acceptable CAC. Unknowns
  feasibility                remain explicit; model judgment alone cannot validate a
                             fatal assumption.

  Differentiation   7%       Clear superiority for a specific segment/use case.
                             Unknowns remain explicit; model judgment alone cannot
                             validate a fatal assumption.

  Defensibility     7%       Data, workflow embedding, network effects, switching
                             costs, learning loops. Unknowns remain explicit; model
                             judgment alone cannot validate a fatal assumption.

  Technical         6%       Can be built from available digital technologies.
  feasibility                Unknowns remain explicit; model judgment alone cannot
                             validate a fatal assumption.

  Capital           5%       Low external capital before validation/revenue.
  efficiency                 Unknowns remain explicit; model judgment alone cannot
                             validate a fatal assumption.

  Low human         4%       Revenue can scale faster than operator headcount.
  marginal burden            Unknowns remain explicit; model judgment alone cannot
                             validate a fatal assumption.
  ----------------------------------------------------------------------------------

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

  -----------------------------------------------------------------------
  **Model**         **Typical strength**         **Typical weakness**
  ----------------- ---------------------------- ------------------------
  Subscription SaaS Recurring revenue, high      Long enterprise
                    margins.                     sales/procurement.

  Usage-based API   Scales with customer usage;  Price compression and
                    developer-friendly.          platform dependency.

  AI agent /        High value capture from      Reliability, oversight,
  managed           replacing workflow labor.    trust.
  automation                                     

  Data /            Reusable differentiated      Data rights, freshness,
  intelligence      information asset.           reproducibility.
  product                                        

  Marketplace       Network effects if liquidity Cold-start and two-sided
                    emerges.                     acquisition.

  Digital service → Fast early revenue and       Risk of remaining
  software          learning.                    labor-linear.

  Open-source +     Distribution and ecosystem   Monetization and
  enterprise        leverage.                    free-rider risk.
  -----------------------------------------------------------------------

# 14. Persistent Opportunity Graph and Learning

A persistent graph prevents each run from starting from zero. It stores
reusable knowledge and the lineage from market signal to final decision.

Signal ──indicates──▶ Problem ──affects──▶ Customer\
│ │ │\
│ ├──solved_by──────▶ ExistingSolution\
│ └──supports───────▶ BusinessIdea\
│\
BusinessIdea ──has────▶ Assumption ──tested_by────▶ Experiment\
│ │ │\
│ ├──supported_by───────▶ Evidence\
│ ├──contradicted_by────▶ Evidence\
│ └──predicted_status───▶ Prediction\
│ │\
├──variant_of────▶ BusinessIdea ▼\
└──evaluated_by──▶ Evaluation ObservedOutcome\
│\
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

  -----------------------------------------------------------------------------
  **Store**           **Content**                             **Retrieval**
  ------------------- --------------------------------------- -----------------
  Relational store    Canonical entities, run state, scores,  Exact queries and
                      policies, provenance.                   analytics.

  Document/evidence   Fetched pages, extracts, reports,       Source-id and
  store               normalized source text.                 metadata lookup.

  Vector index        Semantic similarity for deduplication   Embedding nearest
                      and related prior work.                 neighbors.

  Graph layer         Relationships among problems, ideas,    Neighborhood and
                      companies, evidence, assumptions.       path queries.

  Cache               Search/fetch/tool results and repeated  Content hashes /
                      LLM subcalls.                           request keys.
  -----------------------------------------------------------------------------

Vector similarity is used for retrieval, deduplication, and search-space
coverage---not as truth. Canonical evidence, assumptions, experiments,
predictions, and outcomes remain in structured storage with provenance.
Retrieval policies deliberately reserve a fraction of search budget for
dissimilar or underexplored regions so historical memory does not
collapse future ideation onto past winners.

# 16. Runtime, Harness, and LLM Serving Architecture

DBIE deliberately uses **one agent harness: CrewAI**. No LangChain,
LangGraph, AutoGen, or second general-purpose agent framework is
required in the initial architecture. Adding overlapping orchestration
frameworks would duplicate state, retry, tool, and execution semantics
and make failures harder to reproduce. A second harness may be
introduced only if a measured capability gap cannot be solved cleanly in
CrewAI Flow or custom deterministic code.

The runtime is divided into five explicit layers:

``` text
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

  -----------------------------------------------------------------------
  Layer                   Owns                    Must not own
  ----------------------- ----------------------- -----------------------
  CrewAI Flow             Stage orchestration,    Canonical business
                          bounded retries, task   rules hidden in prompts
                          dependencies, crew      
                          invocation,             
                          checkpoints, approval   
                          transitions             

  CrewAI Crews/Agents     Research, hypothesis    Final authoritative
                          generation, synthesis,  hard gates, money
                          critique, red-team,     movement, unrestricted
                          experiment proposal     tools

  Custom Domain Engine    Canonical objects,      Open-ended research
                          deterministic policy,   behavior
                          assumption lifecycle,   
                          evidence rules,         
                          scoring,                
                          promotion/rejection,    
                          experiment state        

  Model Router            Provider selection,     Business decisions
                          model selection,        
                          reasoning tier, context 
                          limits, concurrency,    
                          fallback, escalation    
                          metadata                

  vLLM/Ollama             Model serving and       Agent lifecycle or
                          generation              business state

  Tool Gateway            Authentication,         Deciding business
                          authorization, call     viability
                          validation, provenance, 
                          rate limits, budgets,   
                          audit                   

  Persistence             Durable state,          Generating conclusions
                          immutable               
                          predictions/outcomes,   
                          source lineage,         
                          retrieval               
  -----------------------------------------------------------------------

The most important rule is: **core business logic is code, not prompt
text**. For example, digital-only rejection, fatal-assumption policy,
minimum evidence independence, experiment precedence, budget limits, and
escalation triggers are deterministic functions over stored state.
Agents propose or extract inputs; the Domain Engine decides whether the
rule is satisfied.

## 16.2 Model Provider Interface

CrewAI must not depend directly on a specific runtime. DBIE exposes an
internal provider-neutral model contract such as:

``` text
LLMProvider
  generate(request) -> response
  structured_generate(request, schema) -> typed_response
  tool_call(request, tool_schema) -> tool_intent
  health() -> provider_status
  capabilities() -> model_capabilities
```

Initial adapters:

-   `VLLMProvider` --- preferred for production-like local concurrency,
    continuous batching, explicit GPU-memory controls, and
    OpenAI-compatible serving.
-   `OllamaProvider` --- preferred for simple local setup, development,
    model swapping, and fallback operation.
-   `ExternalProvider` --- optional, disabled by default; used only for
    L4 escalation or explicitly configured evaluation.

Provider choice is configuration, not agent logic. The same CrewAI
agent/task definition must run against either vLLM or Ollama without
changing its business behavior.

## 16.3 Supported Primary Models

DBIE v0.5 defines two local primary-model profiles rather than assuming
a single model:

  -----------------------------------------------------------------------------------------
  Profile                       Intended runtime    Role                 Hardware rationale
  ----------------------------- ------------------- -------------------- ------------------
  `gpt-oss-20b`                 Ollama or vLLM      Baseline/reference   Strong agent/tool
                                where memory        primary model        behavior; larger
                                permits                                  VRAM footprint
                                                                         leaves less
                                                                         KV-cache headroom
                                                                         on 16 GB GPUs

  `ministral-3-14b-reasoning`   Prefer vLLM;        Low-VRAM primary     Target roughly
  quantized                     Ollama-compatible   option               \<10 GB weights so
                                packaging where                          a 16 GB GPU
                                available                                retains
                                                                         substantial
                                                                         KV/cache/runtime
                                                                         headroom
  -----------------------------------------------------------------------------------------

The architecture does not encode either model as intrinsically superior.
DBIE benchmarks them on its own tool-use and business-evaluation
workload. Configuration selects the default.

Recommended 16 GB strategy: target **8--10 GB model-weight occupancy**,
cap context per request, and reserve the remaining VRAM for KV cache,
batching, CUDA/runtime overhead, and concurrency. Full advertised
context windows must not be enabled by default simply because a model
supports them. Start with 16k--32k maximum context and retrieve only
relevant evidence.

## 16.4 Concurrency

Many logical agents may exist while only a small number generate
simultaneously:

``` text
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

The initial 4--8 active-request target is a tuning starting point, not a
guarantee. The runtime automatically reduces concurrency when KV-cache
pressure, OOM risk, p95 latency, or throughput degradation crosses
configured thresholds. Tool I/O concurrency is governed separately so
slow web/database calls do not occupy inference slots.

## 16.5 Why No Additional Harness

DBIE explicitly rejects an initial stack such as
`CrewAI + LangChain + LangGraph`. CrewAI already supplies agent/crew
orchestration and Flow-level control. Deterministic behavior belongs in
the custom Domain Engine rather than in a second orchestration
abstraction.

A second harness is justified only if all of the following are true:

1.  A required capability is missing from CrewAI Flow/Crews.
2.  The capability cannot be implemented simply in custom deterministic
    code.
3.  The measured benefit outweighs duplicated state/tool/retry
    abstractions.
4.  An integration contract and failure semantics are defined before
    adoption.

# 17. Model Routing and Independence

The Model Router is provider- and model-agnostic. A configured local
primary model handles discovery, ideation, query formulation, structured
extraction, assumption decomposition, evidence synthesis, experiment
design, ordinary red-team work, pairwise comparison, and reporting.
Deterministic code performs calculations and hard gates. A different
model family or stronger external model is reserved for disputes,
critical assumptions, high-value finalists, low evaluator agreement, or
unusually consequential decisions.

Model routing inputs include: task type, required structured-output/tool
capabilities, context size, configured independence level, queue depth,
VRAM budget, latency budget, historical task accuracy, and escalation
policy. Agents do not select providers themselves.

## 17.1 Model-Independence Levels

-   L0 --- Primary-model judgment: configured primary model alone.
    Suitable for generation, routing, drafting, and low-risk internal
    judgments; never sufficient by itself to validate a fatal market
    assumption.
-   L1 --- Deterministic evidence: primary model plus externally sourced
    evidence, provenance, deterministic calculations, schema checks, and
    hard gates. This is the normal validation baseline.
-   L2 --- Repeated independent contexts: multiple primary-model
    evaluations with clean role-specific contexts and randomized
    ordering. Useful for stability measurement, but not independent
    market evidence because the underlying model is shared.
-   L3 --- Heterogeneous local judge: a different local model family
    evaluates the disputed claim or candidate.
-   L4 --- Strong external judge: a substantially stronger or otherwise
    independent external model evaluates only escalated cases. Its
    judgment is advisory unless grounded in evidence.
-   L5 --- Observed market experiment: measured customer or market
    behavior from a pre-registered digital experiment. Highest-trust
    validation level for demand, pricing, conversion, and related
    behavioral assumptions.

## 17.2 Escalation Policy

Use the cheapest independence level capable of resolving current
uncertainty. Escalate on a high-value finalist, low evaluator agreement,
FATAL assumption, conflicting high-quality evidence, material
legal/regulatory interpretation, large proposed commitment, unstable
ranking, or demonstrated primary-model failure on the relevant task
class. Escalation stops when additional model opinion has lower expected
information value than collecting evidence or running an experiment.

  -----------------------------------------------------------------------
  Task                                Default execution / escalation
  ----------------------------------- -----------------------------------
  Extraction / classification         Primary local model, low reasoning
                                      effort, schema-constrained;
                                      deterministic validators

  Deduplication / tagging             Embeddings + deterministic
                                      similarity; model only for
                                      ambiguity

  Idea generation                     Primary local model with
                                      diversified lenses; novelty
                                      measured against memory

  Validation synthesis                Primary + evidence graph (L1);
                                      disputed critical assumptions to
                                      L3/L4

  Red team                            Primary with isolated context;
                                      heterogeneous judge for high-impact
                                      disagreement

  Pairwise ranking                    Primary initially; repeat for
                                      stability; escalate
                                      unstable/high-value matchups

  Financial analysis                  Deterministic Python from explicit
                                      assumptions; model explains only

  Legal/regulatory                    Primary may triage; material
                                      conclusions require authoritative
                                      sources and possibly external
                                      expert/human review

  Demand / WTP                        LLM judgment cannot validate alone;
                                      prefer L5 observed experiments

  Final synthesis                     Primary composes dossier;
                                      high-value finalists may receive L4
                                      review before human approval
  -----------------------------------------------------------------------

# 18. Observability and Evaluation

Every run is observable at system, crew, agent, task, tool, model, and
candidate levels. Current CrewAI exposes observability-oriented
concepts; this design additionally requires application-level metrics
tied to business-idea quality.

  --------------------------------------------------------------------------
  **Metric       **Examples**
  group**        
  -------------- -----------------------------------------------------------
  Pipeline       Ideas generated, rejection rate by gate, survivors per
                 stage, stage latency.

  Evidence       Sources per claim, independent-source count, evidence
                 coverage, stale-source fraction.

  Agent quality  Schema failures, unsupported-claim rate, judge
                 disagreement, hallucination incidents.

  Economics      Tokens/run, external API cost/run, cost/finalist,
                 cost/rejected candidate.

  Ranking        Pairwise upset rate, rank correlation across repeated
  stability      judging, score variance.

  Novelty        Duplicate rate vs prior graph, new-problem rate,
                 new-business-model rate.

  Learning       Recurring rejection reasons, prediction accuracy of early
                 gates, later validation outcomes.

  Assumptions    Fatal assumptions per candidate, unresolved-fatal rate,
                 falsification rate, evidence transitions by tier.

  Experiments    Experiments designed/run, cost per resolved assumption,
                 conversion/usage metrics, inconclusive rate, time to
                 falsification.

  Calibration    Brier/log-style calibration where applicable,
                 prediction-vs-outcome error, judge reliability by
                 model/prompt/task.

  Evidence       Effective independent-source count, lineage-family
  independence   concentration, derivative-source inflation prevented.

  Automation     Human minutes per customer/transaction, automation ratio,
  scalability    estimated burden at 10× and 100× volume.
  --------------------------------------------------------------------------

# 19. Quality Controls

-   Pydantic/JSON-schema validation for every inter-stage output.

-   No score can cite the candidate's own generated description as
    evidence.

-   Important market claims require at least two independent sources
    where feasible.

-   Each evaluator receives a clean role-specific context, avoiding
    contamination by prior persuasive prose.

-   Judges receive both supporting and contradictory evidence.

-   Low evidence coverage caps candidate ranking irrespective of
    narrative quality.

-   Source freshness thresholds vary by claim type; current pricing and
    competition require recent evidence.

-   All automatic decisions record reason codes and score/config
    versions.

-   Randomized re-evaluation of a sample of rejected ideas detects
    over-aggressive gates.

-   Aggregate rankings expose uncertainty and evidence tier; UNKNOWN is
    never silently imputed as an average score.

-   At least a configured fraction of ideation/search budget explores
    areas dissimilar to historical winners.

-   Source-lineage clustering reduces copied/syndicated evidence to its
    effective independent roots.

-   Predictions are immutable once an experiment starts; outcomes are
    appended separately.

-   Observed experiment results are evaluated against predeclared
    metrics/thresholds to reduce post-hoc rationalization.

-   Critical assumptions must state falsification criteria before the
    evaluator sees the final recommendation.

-   LLM-to-LLM agreement is never counted as independent evidence.

# 20. Human Approval Gates

  -----------------------------------------------------------------------
  **Boundary**                    **Default**
  ------------------------------- ---------------------------------------
  Web research / public read-only Automatic within quotas.
  data                            

  Paid research/API spend above   Approval required.
  run budget                      

  Contacting a real               Approval required unless a dedicated
  customer/prospect               campaign is explicitly enabled.

  Publishing content publicly     Approval required.

  Deploying a prototype to        Approval required.
  production                      

  Purchasing domains/services or  Approval required.
  committing funds                

  Selecting finalists for         Automatic within configured budget.
  automated deeper research       

  Final build/investment decision Human decision.

  Creating a private/local        Automatic inside sandbox and resource
  prototype with no external      quotas.
  exposure                        

  Publishing a landing page or    Approval required;
  collecting external signups     privacy/terms/instrumentation reviewed.

  Running paid acquisition        Approval required with explicit spend
  experiments                     ceiling and campaign scope.

  Changing an active experiment   New experiment version required;
  protocol after data collection  original prediction and protocol remain
  starts                          immutable.
  -----------------------------------------------------------------------

# 21. Failure Handling

  -----------------------------------------------------------------------
  **Failure**      **System behavior**
  ---------------- ------------------------------------------------------
  Tool timeout     Retry with bounded backoff; then mark evidence gap and
                   continue if non-critical.

  Search           Use alternate provider/cache; never fabricate
  unavailable      evidence.

  Schema-invalid   Repair once with schema-only retry; then fail task and
  LLM output       record.

  Agent            Preserve disagreement; invoke adjudicator only where
  disagreement     decision is required.

  Insufficient     Mark INSUFFICIENT_EVIDENCE; do not convert uncertainty
  evidence         into a neutral/positive score.

  Budget exhausted Checkpoint; stop lower-priority candidates first.

  Model server     Queue requests; reduce active concurrency; preserve
  overloaded       logical agents.

  Interrupted run  Resume from persisted Flow state and idempotent stage
                   checkpoints.
  -----------------------------------------------------------------------

# 22. Security and Data Governance

-   Credentials are held by the Tool Gateway or secret manager, not
    inserted into agent prompts.

-   Per-tool allowlists and scopes enforce least privilege.

-   External content is treated as untrusted input; prompt-injection
    defenses separate tool content from instructions.

-   Fetched evidence is hashed and provenance-stamped for traceability.

-   PII collection is minimized and isolated from general research
    context.

-   Retention policies apply to raw web content, logs, generated
    artifacts, and contact data independently.

-   Agents cannot grant themselves additional permissions or alter
    scoring/governance configuration.

# 23. Suggested Repository Structure

digital_business_idea_engine/\
├── app/\
│ ├── flows/\
│ │ └── idea_pipeline.py\
│ ├── crews/\
│ │ ├── discovery/\
│ │ ├── ideation/\
│ │ ├── validation/\
│ │ ├── business_model/\
│ │ ├── red_team/\
│ │ └── diligence/\
│ ├── agents/\
│ ├── tasks/\
│ ├── tools/\
│ │ ├── gateway/\
│ │ ├── search/\
│ │ ├── browser/\
│ │ ├── company/\
│ │ ├── regulatory/\
│ │ ├── github/\
│ │ └── finance/\
│ ├── models/ \# typed domain schemas\
│ ├── scoring/\
│ │ ├── rubric.py\
│ │ ├── evidence.py\
│ │ └── tournament.py\
│ ├── knowledge/\
│ │ ├── repository.py\
│ │ ├── graph.py\
│ │ └── retrieval.py\
│ ├── llm/\
│ │ ├── gateway.py\
│ │ └── scheduler.py\
│ ├── policies/\
│ ├── observability/\
│ └── reports/\
├── config/\
│ ├── agents.yaml\
│ ├── tasks.yaml\
│ ├── scoring.yaml\
│ ├── budgets.yaml\
│ └── tool_policy.yaml\
├── migrations/\
├── tests/\
└── data/

# 24. Stage Contracts

  -------------------------------------------------------------------------------------
  **Stage**     **Input**        **Output**               **Gate**
  ------------- ---------------- ------------------------ -----------------------------
  Discovery     Search mandate + Signals + problems +     Problem has identifiable
                prior graph      evidence                 affected customer.

  Ideation      Qualified        Idea variants + novelty  Structured schema +
                problem + search lineage                  meaningful difference from
                diversity target                          prior candidates.

  Digital       Idea             Digital +                All mandatory criteria pass.
  eligibility                    autonomous-scalability   
                                 pass/fail + reason codes 

  Fast scoring  Eligible idea +  Assumption set +         No unresolved schema/identity
                initial evidence evidence gaps + triage   defects; fatal assumptions
                                 range                    identified.

  Validation    Candidate +      Evidence-for/against +   Fatal assumptions cannot be
                assumptions +    lineage + confidence     validated by model judgment
                evidence gaps    transitions              alone.

  Business      Validated        Model variants +         At least one digital,
  model         problem +        deterministic            autonomously scalable model
                assumption set   economics + changed      remains plausible.
                                 assumptions              

  Red team      Candidate        Falsification attempts + No fatal contradiction
                dossier without  correlated-evidence      ignored.
                generator        warnings + severity      
                persuasive prose                          

  Tournament    Eligible         Pairwise ordering +      Ordering only; cannot
                survivors with   judge disagreement       override hard gates.
                normalized                                
                dossiers                                  

  Diligence     Top candidates + Experiment-ready dossier Each unresolved
                unresolved                                fatal/material assumption has
                assumptions                               a falsifiable test or
                                                          explicit research gap.

  Learning      Immutable        Calibration updates +    Outcomes stored separately
                predictions +    search-prior statistics  from predictions; no
                evidence +                                self-confirming evidence
                experiment                                creation.
                outcomes                                  

  Experiment    Diligence        Pre-registered digital   Metric, threshold, sample,
  design        dossier +        experiment protocol      budget, stop condition and
                unresolved                                falsification criterion
                assumptions                               defined before launch.

  Experiment    Approved         Observed raw metrics +   No protocol mutation without
  execution     protocol         artifacts                a new version; outcome may be
                                                          positive, negative, or
                                                          inconclusive.

  Decision      Research + red   BUILD / ITERATE / KILL / Decision cites
                team +           MORE_EVIDENCE            resolved/unresolved
                experiment                                assumptions and evidence
                outcomes                                  tiers.
  -------------------------------------------------------------------------------------

# 25. Implementation Phases

## Phase 1 --- MVP: deterministic pipeline + evidence

-   Define typed schemas for ideas, atomic assumptions, claims, evidence
    lineage, experiments, predictions, outcomes, and lifecycle states.

-   Implement CrewAI Flow with discovery → diverse ideation →
    digital/autonomous gate → assumption decomposition → evidence
    validation → uncertainty view → report.

-   Implement search/web tools behind a simple gateway.

-   Use one shared LLM endpoint.

-   Store runs, ideas, assumptions, claims, source lineage, evidence,
    predictions, and triage metrics in PostgreSQL/SQLite initially.

-   Generate one final markdown/HTML memo per finalist containing an
    uncertainty map and explicit falsification tests.

Exit criterion: system runs end-to-end and produces finalists whose
critical assumptions, evidence tiers, source lineage, contradictions,
and unknowns are traceable.

## Phase 2 --- adversarial quality

-   Add Skeptic, Red-Team, Assumption Auditor, and Source-Lineage roles.

-   Add source-lineage clustering, independence/freshness measurement,
    and evidence-tier rules.

-   Add pairwise tournament ranking with normalized dossiers and
    explicit judge correlation tracking.

-   Add evaluator calibration, repeated-judge stability tests, and a
    prohibition on treating agent agreement as evidence.

-   Implement structured reason codes for all rejections.

Exit criterion: unsupported-claim rate, effective evidence independence,
judge disagreement, and calibration error are measurable; rankings never
override fatal-assumption gates.

## Phase 3 --- persistent opportunity graph

-   Add semantic deduplication and related-idea retrieval.

-   Add problem → idea → assumption → evidence → prediction → experiment
    → observed-outcome graph.

-   Reuse prior evidence subject to freshness rules.

-   Track historical rejection patterns, calibration outcomes, and
    search-space coverage while reserving exploration budget for
    dissimilar opportunities.

Exit criterion: later runs reuse evidence without converting historical
judgments into truth and maintain measurable exploration outside prior
winner clusters.

## Phase 4 --- scale and model routing

-   Deploy one shared gpt-oss-20b inference server behind an async
    scheduler; begin with 4--8 active requests and many queued logical
    agents.

-   Implement L0--L5 independence levels and escalation rules in the
    Model Gateway.

-   Add caching, prioritization, reasoning-effort selection, and
    per-stage token/tool budgets.

-   Parallelize independent candidate evaluations while tracking
    same-model correlation and evaluator stability.

-   Add run dashboard/observability.

Exit criterion: hundreds of candidates can be processed without
multiplying model instances; at least 90% of ordinary inference can
remain on the primary local model, and L3/L4 escalations are measurable,
budgeted, and triggered only by explicit policy.

## Phase 5 --- pre-registered digital experimentation

-   Generate pre-registered falsifiable digital experiments for
    unresolved critical assumptions.

-   With explicit approval, support landing pages, prototype usage
    tests, pricing/waitlist tests, acquisition experiments, interviews,
    or other digital-only tests.

-   Record immutable protocol versions, raw measurements, sample
    definitions, costs, and observed experiment results as a
    higher-trust evidence tier.

-   Update assumptions and portfolio decisions from observed behavior;
    do not retroactively alter the pre-experiment prediction.

Exit criterion: the engine distinguishes research attractiveness from
observed market response and can produce BUILD / ITERATE / KILL /
MORE_EVIDENCE decisions from explicit assumption resolution.

## Phase 6 --- outcome calibration and autonomous learning

-   Compare stored predictions with later observed outcomes and
    calculate calibration by assumption category, model, prompt, judge,
    and evidence tier.

-   Update search allocation and evaluator trust from measured
    calibration, not from repeated internal consensus.

-   Periodically re-sample rejected ideas and underexplored search
    regions to detect path dependence and premature convergence.

-   Use experiment cost and information gain to learn which validation
    actions resolve uncertainty most efficiently.

Exit criterion: historical outcomes measurably improve prioritization
while holdout tests show that novelty and rejected-candidate recall do
not collapse.

# 26. MVP Recommended Configuration

  -----------------------------------------------------------------------
  Area                                Initial recommendation
  ----------------------------------- -----------------------------------
  Application                         Python package with explicit
                                      domain, orchestration, model,
                                      tools, persistence, experiments,
                                      and observability modules

  Agent harness                       **CrewAI only**: Flow for
                                      authoritative lifecycle;
                                      Crews/Agents for bounded open-ended
                                      work

  Additional harnesses                None initially; do not add
                                      LangChain/LangGraph unless a
                                      measured capability gap satisfies
                                      §16.5

  Domain logic                        Custom deterministic Python; no
                                      hard business rules hidden
                                      exclusively in prompts

  Model API                           Internal
                                      `LLMProvider`/`ModelRouter`
                                      abstraction

  Serving backends                    `VLLMProvider` and
                                      `OllamaProvider`; same CrewAI tasks
                                      must work through either

  Primary model option A              `gpt-oss-20b` as baseline/reference
                                      where VRAM/context budget is
                                      acceptable

  Primary model option B              Quantized
                                      `Ministral 3 14B Reasoning` as
                                      preferred lower-VRAM option for a
                                      16 GB GPU when substantial KV-cache
                                      headroom is required

  GPU memory policy                   Prefer \~8--10 GB model weights on
                                      a 16 GB GPU; reserve remaining
                                      memory for KV cache, batching,
                                      runtime overhead; enforce memory
                                      guardrails

  Context policy                      Start 16k--32k max model context;
                                      retrieve evidence rather than
                                      stuffing global state into prompts

  Active LLM concurrency              Start 4--8; adapt to measured KV
                                      pressure, p95 latency, tokens/s and
                                      OOM margin

  Logical agents                      30--100 acceptable; instantiate
                                      tasks/roles on demand and queue
                                      inference

  Tools                               Ten MVP tools from §8 behind Tool
                                      Gateway; MCP where useful, custom
                                      typed adapters otherwise

  Persistence                         PostgreSQL + pgvector preferred;
                                      predictions/outcomes stored
                                      separately and immutably

  Graph                               Relational edges first; dedicated
                                      graph DB only when measured queries
                                      justify it

  Output                              Structured JSON + Markdown reports

  Approval                            No public experiment, outbound
                                      contact, paid acquisition, spend,
                                      publication, or production
                                      deployment without explicit
                                      approval

  Independence                        L0 → L5 ladder retained; model
                                      family diversity counts as
                                      reasoning independence, not market
                                      evidence

  Benchmarking                        Primary-model choice based on
                                      DBIE-specific tool/evidence
                                      benchmark, not generic model
                                      benchmark alone
  -----------------------------------------------------------------------

# 27. Acceptance Criteria

-   100% of finalists pass the digital-only eligibility contract.

-   Every scored market claim links to evidence or is explicitly labeled
    assumption/unknown.

-   Rejected candidates retain machine-readable rejection reasons.

-   Generator agents cannot be assigned as the sole evaluator of their
    own ideas.

-   At least one adversarial evaluation occurs before a candidate can
    become a finalist.

-   Finalists are ranked through both structured scoring and pairwise
    comparison.

-   Runs are resumable from persisted checkpoints.

-   Tool calls and LLM calls are attributable to run, stage, task,
    agent, and candidate.

-   Prior ideas/evidence can be retrieved to prevent unnecessary
    duplication.

-   No individual agent can bypass tool permissions, budget limits, or
    human approval gates.

-   Pairwise ranking cannot override digital-only,
    autonomous-scalability, evidence, or fatal-assumption gates.

-   A configured exploration budget prevents the opportunity graph from
    collapsing ideation onto historical winners.

-   The system reports human marginal burden and automation ratio for
    every finalist.

-   Observed experiment outcomes are stored separately from predictions
    and can be used for later calibration.

-   Every externally executed experiment has a predeclared protocol,
    metric, threshold, budget, and immutable pre-experiment prediction.

-   LLM agreement is never counted as market evidence.

-   At least 90% of normal pipeline inference is executable on the
    configured primary gpt-oss-20b endpoint without requiring a stronger
    model.

-   Every L3/L4 escalation records its trigger, model family, cost,
    decision impact, and whether it changed the outcome.

-   Repeated gpt-oss-20b judgments (L2) are reported as stability
    evidence, never as independent market evidence.

-   Fatal demand, pricing, or behavioral assumptions cannot be marked
    validated by L0--L4 model judgment alone when a feasible L5
    experiment is required by policy.

-   Deterministic calculations and hard gates are implemented outside
    the LLM and remain reproducible from stored inputs.

-   Every evidence source belongs to a lineage/independence group;
    effective independent evidence is reported separately from raw
    source count.

-   No unresolved FATAL assumption can be silently converted into an
    average numeric score.

-   100% of finalists have explicit atomic assumptions with
    falsification conditions.

-   CrewAI is the only general-purpose agent harness in the MVP
    dependency graph.

-   All hard eligibility, evidence, budget, escalation, and decision
    gates execute in deterministic application code and are testable
    without an LLM.

-   The same representative CrewAI task suite can run through both
    `VLLMProvider` and `OllamaProvider` without changing domain behavior
    or schemas.

-   Model/provider selection is performed by `ModelRouter`; individual
    agents cannot bypass routing policy.

-   A 16 GB deployment can enforce a configured GPU-memory headroom
    target and reduce context/concurrency before OOM.

-   Primary-model evaluation includes DBIE-specific tool-selection,
    tool-argument, structured-output, multi-step recovery,
    evidence-quality, latency, and VRAM measurements.

# 28. Key Design Decisions

  -----------------------------------------------------------------------
  **Decision**         **Rationale**
  -------------------- --------------------------------------------------
  Flow outside, Crews  Preserves deterministic control while using
  inside               autonomy only where it adds value.

  Digital-only as hard Prevents scoring from compensating for a
  gate                 fundamental scope violation.

  Evidence graph as    Makes reasoning auditable and reusable across
  core substrate       runs.

  Adversarial          Counteracts self-confirming LLM reasoning.
  evaluation           

  Tournament + score   Reduces dependence on poorly calibrated absolute
                       LLM scores.

  One shared model     Efficiently supports many logical agents with
  service              bounded concurrent inference.

  Least-privilege tool Limits accidental or unauthorized external
  gateway              actions.

  Human approval at    Keeps the research engine autonomous while
  consequential        retaining control over real-world commitments.
  boundaries           

  Assumption as        Turns business evaluation into falsifiable
  primary validation   uncertainty reduction rather than narrative
  object               scoring.

  Observed outcomes    Prevents many correlated LLM agents from
  outrank agent        manufacturing confidence.
  consensus            

  Predictions          Makes calibration possible and prevents hindsight
  separated from       rewriting.
  outcomes             

  Source-lineage       Stops copied/syndicated material from inflating
  independence         evidence strength.

  Pre-registered       Tests demand, pricing, acquisition, usability, and
  digital experiments  automation with real behavior before build
                       decisions.

  Exploration reserve  Protects novelty and reduces path dependence
                       caused by persistent memory and prior rankings.

  Autonomous           Excludes digital businesses whose revenue remains
  scalability as hard  structurally tied to proportional human labor.
  gate                 
  -----------------------------------------------------------------------

## v0.5 Architecture Decisions

-   CrewAI is the sole agent harness; no LangChain/LangGraph layer in
    the initial system.
-   Custom Python owns canonical domain state and every authoritative
    deterministic decision rule.
-   CrewAI owns Flow orchestration and bounded agentic reasoning, not
    business-policy truth.
-   Model serving is isolated behind `ModelRouter` and `LLMProvider`.
-   vLLM and Ollama are interchangeable provider adapters, not
    architectural dependencies of agents.
-   `gpt-oss-20b` remains a supported baseline/reference primary model.
-   Quantized Ministral 3 14B Reasoning is added as a lower-VRAM
    primary-model option when a 16 GB GPU must reserve substantial
    KV-cache headroom.
-   Default context is deliberately capped at 16k--32k and extended only
    from evidence.
-   The ten MVP tools remain behind one permissioned Tool Gateway,
    exposed via MCP where useful and typed custom adapters otherwise.
-   Model choice is validated using a DBIE-specific benchmark rather
    than generic benchmark scores alone.

# 29. v0.3 Design Changes

-   Defined gpt-oss-20b as the primary local model for most CrewAI agent
    tasks while preserving a model-agnostic gateway.

-   Added L0--L5 model-independence levels separating same-model
    judgment, deterministic evidence, heterogeneous-model review, and
    observed market experiments.

-   Added explicit escalation triggers so stronger/external models are
    used selectively rather than as the default execution path.

-   Clarified that repeated calls to one model measure stability but do
    not create independent evidence.

-   Made deterministic calculations, schema validation, hard gates, and
    evidence provenance authoritative outside the LLM.

-   Added local-first concurrency guidance: one shared gpt-oss-20b
    server, 4--8 active requests initially, and many queued logical
    agents.

## v0.2 changes retained

-   Replaced idea-centric aggregate scoring with assumption-centric
    uncertainty reduction.

-   Added immutable prediction → experiment → observed-outcome loop for
    calibration.

-   Added evidence tiers and source-lineage independence to prevent
    correlated-source inflation.

-   Added explicit safeguards against LLM-to-LLM consensus being treated
    as independent validation.

-   Added novelty-search mechanisms and exploration budget to reduce
    memory-induced convergence.

-   Elevated autonomous scalability from a soft score to a hard
    eligibility constraint.

-   Made real-world digital experiments a first-class system stage with
    pre-registration and human approval.

-   Changed final decisions to BUILD / ITERATE / KILL / MORE_EVIDENCE
    with explicit semantics.

# 29.1 v0.6 Revision Summary

v0.6 keeps the ten-tool CrewAI surface unchanged and standardizes an
OSS-first implementation beneath it. SearXNG, Crawl4AI, Trafilatura,
Playwright, PRAW, PyGithub, official regulator adapters, Docling,
PyMuPDF, Docker sandboxing, PostgreSQL/SQLAlchemy, pgvector, and a local
BGE/E5 embedding service are internal adapters. This preserves tool-call
reliability for 14--20B local models, allows provider replacement
without prompt changes, reduces external API cost, and makes
provenance/security/resource controls enforceable at one gateway.

# 30. References / Framework Alignment

CrewAI framework concepts used in this design were checked against the
current CrewAI documentation as of August 2026: Crews for collaborative
autonomous work; Flows for structured orchestration, state, branching,
and resumability; agents with tools and structured outputs; and
extensible/custom tools including web research and browser integrations.

-   CrewAI Documentation --- https://docs.crewai.com/

-   CrewAI Introduction / Crews vs. Flows ---
    https://docs.crewai.com/core-concepts/Agents

-   CrewAI annotation/configuration documentation ---
    https://docs.crewai.com/learn/using-annotations

-   CrewAI web scraping/browser tool overview ---
    https://docs.crewai.com/tools/web-scraping/overview

-   OpenAI gpt-oss-20b model documentation ---
    https://developers.openai.com/api/docs/models/gpt-oss-20b

-   OpenAI gpt-oss architecture / release notes ---
    https://openai.com/index/introducing-gpt-oss/

-   SearXNG Documentation --- https://docs.searxng.org/

-   Crawl4AI Documentation --- https://docs.crawl4ai.com/

-   Trafilatura Documentation --- https://trafilatura.readthedocs.io/

-   Playwright Python Documentation --- https://playwright.dev/python/

-   Docling --- https://github.com/docling-project/docling

-   PyMuPDF Documentation --- https://pymupdf.readthedocs.io/

-   PRAW Documentation --- https://praw.readthedocs.io/

-   PyGithub Documentation --- https://pygithub.readthedocs.io/

-   pgvector --- https://github.com/pgvector/pgvector

-   SQLAlchemy Documentation --- https://docs.sqlalchemy.org/

-   EUR-Lex Web Services ---
    https://eur-lex.europa.eu/content/help/data-reuse/webservice.html

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
limitations---not to average the result with model opinion.

# 32. Final Architecture Summary

Runtime strategy: one shared local gpt-oss-20b endpoint performs the
bulk of agent reasoning. The scheduler bounds active inference, the
Model Gateway enforces L0--L5 independence policy, deterministic
services own calculations and hard gates, and costly
heterogeneous/external model review is reserved for explicit escalation.
Real digital experiments remain the final authority for observable
market behavior.

The system is not primarily an idea-generating crew. It is a controlled
digital opportunity discovery, falsification, and experimentation
engine. Generation is cheap and broad; each surviving idea is decomposed
into falsifiable assumptions; evidence and independent red-team work
reduce uncertainty; pairwise ranking orders only eligible candidates;
and pre-registered digital experiments test the remaining critical
assumptions against real behavior. Persistent memory improves efficiency
without allowing remembered judgments to masquerade as new evidence.

The v0.6 core architecture is deterministic CrewAI Flow + specialized
Crews + least-privilege digital tools + an assumption/evidence/outcome
substrate + digital-only and autonomous-scalability hard gates + novelty
search + source-lineage independence + adversarial validation +
uncertainty-aware portfolio metrics + pairwise ordering + pre-registered
digital experiments + outcome-calibrated learning + explicit human
approval for consequential external actions.

# 33. v0.5 Runtime Reference Architecture

``` text
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

This boundary is intentional: CrewAI may be replaced later without
rewriting the Domain Engine or tool implementations; vLLM/Ollama may be
exchanged without rewriting agents; and models may be
benchmarked/swapped without changing canonical business state.

# 34. Venture Evolution Platform Extension (v0.7)

## 34.1 Revised Mission

DBIE is extended from an idea discovery/evaluation engine into a
**Digital Venture Evolution Platform**. The platform continuously
discovers opportunities, reduces uncertainty, builds low-cost MVPs,
exposes them to real users or software agents, observes behavior,
evolves successful MVPs into products, and returns all outcomes to
shared portfolio memory.

The target lifecycle is:

``` text
Signal -> Idea -> Assumptions -> Evidence -> Experiment -> MVP -> Usage -> Product
                                                            |          |
                                                            v          v
                                                          Kill    Grow/Pivot/Scale
                                                                     |
                                                                     v
                                                        Portfolio knowledge/capabilities
```

The optimization target changes from "best idea" to **highest expected
information or business value from the next bounded experiment**,
subject to cost, time, risk, autonomy, and digital-only constraints.

## 34.2 First-Class Venture Model

A `Venture` becomes the aggregate above ideas and experiments. It owns:
`venture_id`, `thesis`, `ideas[]`, `assumptions[]`, `evidence[]`,
`experiments[]`, `mvp_versions[]`, `products[]`, `customer_types[]`,
`usage_metrics`, `revenue`, `costs`, `capabilities[]`, `dependencies[]`,
`lifecycle_state`, `decision_history`, and `owner/approval_policy`.

Lifecycle states are: `DISCOVERED`, `RESEARCHING`, `VALIDATING`,
`MVP_CANDIDATE`, `BUILDING`, `EXPERIMENTING`, `PRODUCT`, `GROWING`,
`PIVOTING`, `SCALING`, `MATURE`, `PAUSED`, and `KILLED`. State
transitions are deterministic domain-engine decisions; CrewAI agents may
recommend transitions but cannot mutate lifecycle state directly.

`KILLED` is an evidence-bearing terminal state, not deletion. Failed
assumptions, build results, market responses, costs, and reusable
capabilities remain searchable.

## 34.3 MVP Candidate Gate

An idea may become an MVP candidate only when it passes the existing
digital/autonomous-scalability gates and has a specific falsifiable
assumption that can be tested by a bounded digital artifact.

The gate additionally evaluates:

-   `time_to_autonomous_mvp`
-   `estimated_mvp_cost`
-   `information_gain_expected`
-   `technical_feasibility`
-   `required_external_dependencies`
-   `customer_access_feasibility`
-   `reusability_of_existing_capabilities`
-   `experiment_reversibility`

The platform prioritizes cheap, disposable experiments over polished
applications. An MVP is successful when it answers its registered
question, not when it contains many features.

## 34.4 MVP Specification Contract

Every build begins from a persisted `MVPSpec`, never directly from an
agent prompt. Required fields include:

``` yaml
mvp_id: MVP-...
venture_id: V-...
critical_assumption_id: A-...
hypothesis: "..."
customer_types: [human, agent]
value_test: "single behavior being tested"
human_interface: {required: true|false, type: web|dashboard|none}
agent_interface: {required: true|false, rest: true|false, mcp: true|false}
core_capabilities: []
existing_capabilities_to_reuse: []
new_capabilities_allowed: []
success_metrics: {}
failure_metrics: {}
build_budget: {wall_clock_hours: 4, compute_budget: "...", cash_budget: "..."}
runtime_budget: {}
security_class: sandbox
expiry_or_review_at: "..."
approval_requirements: []
```

Success/failure metrics are registered before deployment and cannot be
retroactively rewritten to make an experiment appear successful.

## 34.5 MVP Factory

The MVP Factory is a bounded subsystem invoked only after
`MVP_CANDIDATE`. It contains specialized CrewAI actors but is governed
by custom deterministic build state.

Actors and responsibilities:

  -----------------------------------------------------------------------
  Actor                   Responsibility          Primary tools
  ----------------------- ----------------------- -----------------------
  MVP Spec Agent          Convert validated       memory, database,
                          assumption into minimal documents
                          testable artifact       
                          specification           

  Reuse Architect         Search                  semantic memory,
                          capability/product      GitHub, database
                          registry before         
                          proposing new code      

  Solution Architect      Minimal architecture    GitHub, web, memory
                          and dependency plan     

  Builder Agent           Generate implementation GitHub, Python sandbox,
                          in isolated workspace   files/code execution

  Test Agent              Functional, contract    Python sandbox,
                          and hypothesis-test     browser/test adapters
                          checks                  

  Security Reviewer       Dependency, secret,     GitHub, sandbox, static
                          permission and          scanners
                          exposed-surface review  

  Deployment Agent        Package sandbox         container/deployment
                          artifact and prepare    adapter; approval-gated
                          controlled deployment   externally

  Experiment Agent        Configure telemetry and analytics/experiment
                          execute approved        adapters
                          experiment              

  Outcome Analyst         Compare preregistered   database, Python,
                          success criteria with   analytics
                          observations            
  -----------------------------------------------------------------------

The Builder cannot approve its own output. Test and security results are
deterministic gates where possible.

## 34.6 MVP Build State Machine

``` text
SPECIFIED -> REUSE_ANALYSIS -> ARCHITECTED -> BUILDING -> TESTING -> SECURITY_REVIEW
                                                               |
                                          failure <-------------+
                                                               v
                                                    SANDBOX_DEPLOYABLE
                                                               |
                                                     approval if required
                                                               v
                                                         EXPERIMENTING
                                                               |
                                                  OBSERVED -> DECIDED
```

Retries are bounded. Repeated failure returns the venture to `ITERATE`
or `KILL`; it does not create an unbounded coding loop.

## 34.7 Dual Human/Agent Product Contract

The platform treats **humans and autonomous agents as first-class
customers**. Products must declare supported consumers explicitly.

A reusable digital capability should separate its core service from
interfaces:

``` text
Human UI / Dashboard ----\
                          >---- Core Product Service ---- Telemetry/Billing/Policy
REST API ----------------/
MCP Tool ----------------/
SDK ---------------------/
```

Agent-facing contracts prioritize machine-readable schemas,
deterministic errors, idempotency where appropriate, authentication
scopes, rate limits, provenance, versioning, cost metadata, and
discoverable capability descriptions. Human-facing contracts prioritize
comprehensible workflows and explanations. Neither interface may contain
business logic unavailable to the other without an explicit reason.

## 34.8 Agent-Native Opportunity Discovery

Discovery is extended with an `agent_customer` lens. Agents explicitly
search for digital services that autonomous systems may consume:
verification, provenance, specialized search, normalization, compliance,
identity/authorization, reputation, memory, simulation, evaluation,
transaction support, workflow execution, decision validation, and
high-value proprietary data transformations.

Every idea records `customer_mode = human | agent | both`. Agent demand
cannot be inferred merely because an API can be built; it requires
evidence of a machine-consumable problem and a plausible economic
principal paying for the consumption.

## 34.9 Product and Capability Registry

Every MVP and product registers capabilities independent of product
branding. The registry stores: `capability_id`, semantic description,
input/output schemas, implementation owner, REST/MCP endpoints,
authentication, quality metrics, latency, marginal cost, dependencies,
version, lifecycle, licensing, reuse policy, and evidence of
reliability.

Before building new functionality, `Reuse Architect` must query the
registry and classify each required capability as `REUSE`, `ADAPT`,
`OSS`, `BUY_API`, or `BUILD`. New implementation requires a reason when
a reusable internal capability exists.

This enables later ventures to compose products from prior successes
rather than rebuild them.

## 34.10 Productization Gate

An MVP does not automatically become a product. `PRODUCT` requires
evidence beyond technical completion, including preregistered
market/usage success, repeatability, acceptable unit economics or a
credible path to them, operational feasibility, security review,
ownership, support policy, and a human approval gate for public
commercial operation.

Productization creates a durable service repository/package, stable
interface contracts, monitoring, release policy, data governance,
backup/recovery requirements where applicable, and an entry in the
Product Registry.

## 34.11 Portfolio Intelligence Engine

A new deterministic/analytical layer operates above ventures. It does
not autonomously spend unrestricted money. It ranks candidate actions
such as research, experiment, MVP build, iteration, capability
investment, merge, pause, or kill.

Primary portfolio objectives include:

``` text
expected_information_gain / (cash_cost * time_cost * execution_risk)
expected_business_value / constrained_resources
capability_reuse_multiplier
portfolio_diversification
```

The engine detects overlapping ventures, shared customer problems,
reusable capabilities, dependency concentration, duplicate experiments,
cross-selling opportunities, and platform-level capabilities worth
building once.

## 34.12 Venture and Capability Composition

Successful products may become tools used by later ventures. Internal
consumption is recorded like an external dependency so real reuse,
quality and cost are measurable. A venture may therefore evolve from
mostly-new implementation toward composition of existing DBIE
capabilities plus OSS components.

The platform must never count internal reuse as external market
validation. Capability usefulness and business demand remain separate
evidence dimensions.

## 34.13 Telemetry and Outcome Learning

MVP/product telemetry becomes first-class evidence. Events are linked to
`venture_id`, `mvp_id/product_id`, experiment, assumption, consumer
type, version and timestamp. Metrics may include activation, completion,
repeat use, retention, API calls, agent retries, task success, latency,
willingness-to-pay signals, paid conversion, revenue and marginal
inference/infrastructure cost.

Observed behavior outranks model predictions. Predictions are immutable
after an experiment begins; calibration compares predicted
probability/impact against actual outcomes.

## 34.14 Autonomy and Approval Policy

Default policy:

  Action                              Default autonomy
  ----------------------------------- -------------------------------------------
  Idea generation/research            Autonomous
  Local/sandbox MVP build             Autonomous within budget
  Automated tests/security scans      Autonomous
  Sandbox deployment                  Autonomous within isolated environment
  Public deployment                   Human approval
  Paid advertising/spend              Human approval or explicit bounded budget
  Unsolicited customer outreach       Human approval
  Contracts/legal commitments         Human only
  Regulated consequential decisions   Human-controlled
  Major scaling/resource commitment   Human approval

Permissions are enforced by the Tool Gateway and domain engine, not
prompt instructions alone.

## 34.15 Repository Extension

``` text
src/dbie/
  ventures/
    models.py
    lifecycle.py
    decisions.py
  mvp_factory/
    spec.py
    reuse_architect.py
    build_state.py
    workspace.py
    tests.py
    security.py
    packaging.py
  products/
    contracts.py
    registry.py
    productization.py
  capabilities/
    registry.py
    resolver.py
    composition.py
  experiments/
    telemetry.py
    outcomes.py
  portfolio/
    allocator.py
    overlap.py
    capability_investment.py
```

Existing CrewAI, domain, model-router, tool-gateway, persistence and
evidence layers remain authoritative; v0.7 extends them rather than
introducing another harness.

## 34.16 New Tooling Boundary

The original ten research/evidence tools remain stable. MVP/product
execution requires a **separate privileged build/experiment tool class**
so research agents cannot accidentally gain deployment or code-execution
authority. Candidate internal adapters include Git, isolated Docker
workspaces, language runtimes/test runners, static/security scanners,
container build tools, sandbox deployment, telemetry/analytics, and
API/MCP contract test tooling.

These are exposed only to MVP Factory actors through least-privilege
Tool Gateway policies.

## 34.17 v0.7 Acceptance Criteria

v0.7 is architecturally complete when:

1.  Venture lifecycle transitions are persisted and deterministic.
2.  Every MVP is linked to one or more explicit assumptions and a
    preregistered `MVPSpec`.
3.  An MVP can be generated, tested and packaged in an isolated
    workspace without granting research agents build privileges.
4.  Build/test loops have hard attempt, time and compute budgets.
5.  Human and agent interfaces are represented as first-class contracts.
6.  Product/capability registry search occurs before every new MVP
    build.
7.  MVP telemetry is attributable to assumptions and experiments.
8.  Observed outcomes update confidence without rewriting original
    predictions.
9.  Successful MVPs can pass a deterministic productization gate; weak
    ones can be killed while preserving learning.
10. Portfolio logic can rank next experiments/builds and identify
    reusable capabilities without directly authorizing unrestricted
    spend.
11. Public deployment, external outreach, contracts and material spend
    remain policy-gated.
12. A later venture can reuse a capability produced by an earlier
    venture and that reuse is measurable.



## 34.18 Preferred MVP Runtime: NemoClaw / OpenShell

The preferred secure execution runtime for the MVP Factory is **NemoClaw with NVIDIA OpenShell**, while DBIE remains architecturally independent of NVIDIA-specific infrastructure.

The intended separation is:

```text
DBIE Domain Engine
        |
        v
    MVP Factory
        |
        v
SecureExecutionAdapter
        |
   +----+------------------+
   |                       |
   v                       v
NemoClaw/OpenShell     Docker Sandbox
 preferred runtime       fallback
   |
   v
generated code / tools / package managers / browsers / test runners
```

NemoClaw is used because the MVP Factory is materially more dangerous than ordinary research agents. Builder agents may write and execute code, install dependencies, access approved network resources, create artifacts, run browsers, and prepare deployments. These capabilities require a stronger governed runtime than prompt-level restrictions.

NemoClaw/OpenShell should therefore provide or enforce, where supported:

- sandboxed filesystem and process execution;
- network policy and domain allowlists;
- CPU, RAM, GPU, wall-clock and output limits;
- execution lifecycle management;
- agent/process restart and recovery;
- approval-aware privileged operations;
- secret isolation and controlled injection;
- runtime observability and audit;
- immutable or externally controlled security policy;
- restricted package and dependency access;
- controlled artifact export from sandbox to DBIE.

DBIE defines policy; NemoClaw/OpenShell enforces execution policy.

```text
DBIE policy
    |
    v
NemoClaw/OpenShell
    |
    v
restricted execution
```

The MVP Factory must not rely on NemoClaw for venture semantics. NemoClaw does **not** own:

```text
Idea discovery
Assumption state
Evidence provenance
Experiment semantics
Venture lifecycle
MVP candidate selection
Productization decisions
Portfolio allocation
Capability registry
Business scoring
```

Those remain canonical DBIE domain responsibilities.

## 34.19 Agent Harness vs Secure Runtime

CrewAI remains the sole general-purpose orchestration and reasoning harness in DBIE. NemoClaw is treated primarily as a **secure agent execution substrate**, not as a replacement for CrewAI.

Conceptually:

```text
DBIE
 |
 +-- CrewAI Flow / Crews
 |       |
 |       +-- Discovery
 |       +-- Validation
 |       +-- Red Team
 |       +-- MVP Factory coordination
 |
 +-- Deterministic Domain Engine
 |
 +-- Tool Gateway
         |
         +-- normal research tools
         |
         +-- privileged execution
                 |
                 v
         NemoClaw/OpenShell
```

If future NemoClaw releases provide superior native support for another agent harness such as Hermes or OpenClaw, DBIE may add an adapter for specialized MVP execution jobs. This must not require replacing the DBIE domain engine, venture state machine, Tool Gateway contracts, or CrewAI-based orchestration elsewhere.

## 34.20 SecureExecutionAdapter

Introduce a provider-neutral interface:

```text
SecureExecutionAdapter
    create_workspace(spec, policy)
    execute(command_or_task)
    run_tests(test_plan)
    inspect_artifacts()
    export_artifact()
    get_runtime_metrics()
    terminate()
```

Initial implementations:

```text
NemoClawExecutionAdapter   # preferred
DockerExecutionAdapter     # fallback / local compatibility
```

This adapter boundary prevents DBIE from becoming dependent on a single secure-runtime vendor.

The runtime adapter receives an explicit execution policy containing:

```text
workspace_id
venture_id
mvp_id
actor_id
network_allowlist
filesystem_policy
package_policy
secret_policy
cpu_limit
ram_limit
gpu_limit
wall_clock_limit
process_limit
output_limit
artifact_export_policy
approval_scope
```

All policies are generated and persisted by DBIE before execution begins.

## 34.21 MVP Factory Runtime Topology

Preferred topology:

```text
DBIE Control Plane
        |
        v
CrewAI MVP Factory
        |
        v
Privileged Tool Gateway
        |
        v
SecureExecutionAdapter
        |
        v
NemoClaw / OpenShell
        |
        +-- isolated repository checkout
        +-- Python / Node / other runtime
        +-- test runners
        +-- static analyzers
        +-- dependency scanners
        +-- approved browser automation
        +-- approved package registries
        +-- container build tooling
        +-- local service execution
        +-- artifact staging
```

The MVP Factory receives only logical capabilities from the Tool Gateway. It must not receive raw host shell access, Docker socket access, deployment credentials, or unrestricted filesystem/network access.

## 34.22 Runtime Policy Classes

Define at least four policy classes:

```text
RESEARCH_READONLY
BUILD_ISOLATED
SANDBOX_DEPLOY
EXTERNAL_DEPLOY_APPROVED
```

`RESEARCH_READONLY`:
- no code execution beyond existing bounded deterministic tools;
- no package installation;
- no deployment;
- no unrestricted network.

`BUILD_ISOLATED`:
- code generation/execution allowed;
- limited package registries;
- no production credentials;
- outbound network restricted;
- artifact export only through DBIE.

`SANDBOX_DEPLOY`:
- allows execution of the generated service in an isolated environment;
- telemetry enabled;
- still no public production exposure unless separately authorized.

`EXTERNAL_DEPLOY_APPROVED`:
- created only after explicit approval;
- narrowly scoped credentials;
- explicit destination and budget;
- immutable audit record.

## 34.23 Why NemoClaw is Preferred

NemoClaw/OpenShell is preferred for the MVP Factory because DBIE would otherwise need to implement and maintain substantial low-level runtime governance itself:

```text
sandbox isolation
network enforcement
filesystem restrictions
process/resource controls
runtime lifecycle
recovery
approval boundaries
security policy enforcement
execution observability
```

These are infrastructure concerns rather than DBIE's differentiating business logic.

The preferred architectural principle is therefore:

> Build DBIE-specific venture intelligence internally; reuse a specialized governed runtime for dangerous autonomous execution.

This reduces security implementation risk while preserving DBIE's core intellectual property in venture discovery, evidence, experimentation, productization, capability reuse and portfolio intelligence.

## 34.24 Runtime Portability Requirement

NemoClaw is preferred, not mandatory.

DBIE must continue to operate with the fallback Docker execution runtime when:

- NemoClaw is unavailable;
- local hardware/runtime constraints prevent its use;
- a platform does not support the required NemoClaw deployment mode;
- benchmarking shows unacceptable latency/resource overhead;
- licensing or infrastructure constraints change.

No canonical venture, assumption, experiment, MVP, product or portfolio state may exist only inside NemoClaw.

Runtime state is ephemeral; DBIE state is canonical.

## 34.25 Model Independence

NemoClaw must not force a specific model family.

Inference remains behind the existing `ModelRouter` and may use:

```text
vLLM
Ollama
OpenAI-compatible endpoints
local Ministral-class models
GPT-OSS-class models
future compatible models
```

The secure runtime may be colocated with inference or consume it over a controlled endpoint, but inference choice remains independent of secure execution choice.

## 34.26 Observability Integration

NemoClaw/OpenShell runtime telemetry should be normalized into DBIE observability.

Capture at minimum:

```text
workspace creation/termination
commands/tasks executed
resource consumption
network attempts/blocks
package operations
test results
security violations
artifact exports
runtime failures/restarts
approval requests
execution duration
```

These records must be correlated with:

```text
run_id
venture_id
mvp_id
build_id
actor_id
tool_call_id
```

Runtime events are operational evidence, not market evidence.

## 34.27 Security Invariants

Regardless of runtime implementation:

1. Generated code is always treated as untrusted.
2. Builder agents cannot modify their own execution policy.
3. Research agents cannot obtain privileged build tools.
4. Build sandboxes cannot access host Docker sockets.
5. Production/cloud credentials are unavailable in ordinary build mode.
6. Network access is deny-by-default.
7. Artifact export is mediated by DBIE.
8. Public deployment requires explicit authorization.
9. Build/test agents cannot approve their own promotion to product.
10. Runtime replacement must not alter DBIE business semantics.


# 35. v0.7 Revision Summary

v0.7 changes DBIE from an idea engine with experimentation into a
**persistent digital venture foundry**. It adds the Venture Lifecycle
Engine, MVP Factory, dual human/agent product contract, Product and
Capability Registry, productization gates, telemetry-driven outcome
learning, capability composition, and Portfolio Intelligence. The
architecture remains custom Python domain/control code + CrewAI +
provider-neutral vLLM/Ollama inference + permissioned Tool
Gateway/MCP/custom adapters + PostgreSQL/pgvector. No additional agent
harness is introduced.

# 36. Specialized Model Roles, Crew Mapping, and Model-Phase Scheduling

## 36.1 Purpose

DBIE separates **business roles**, **CrewAI crews/tasks**, and **physical model execution**.

A Crew does not permanently own a specific model. Each Crew or task declares a required `model_role`; the `ModelRouter` maps that role to the currently configured model.

This makes model specialization explicit, reduces unnecessary model switching on a single-GPU system, and creates a stable structure for measuring model performance by task type.

```text
Business workflow
      |
      v
Crew / Task
      |
      v
model_role
      |
      v
Model Phase Scheduler
      |
      v
ModelRouter
      |
      v
Ollama / vLLM
      |
      v
single physical GPU
```

## 36.2 Model Roles

Initial model roles are:

```text
THINKER
DOER
BUILDER
JUDGE
```

### THINKER

Used for high-value reasoning:

- opportunity and venture synthesis;
- causal reasoning;
- assumption decomposition;
- research planning;
- evidence reconciliation;
- contradiction analysis;
- experiment design;
- pivot reasoning;
- portfolio reasoning;
- deciding what evidence remains missing.

Initial preferred local model:

```text
deepseek-r1:14b-48k
```

`qwen3:14b` in thinking mode is the principal challenger and fallback.

### DOER

Used for high-volume execution:

- web research;
- competitor research;
- pricing research;
- Reddit/community research;
- company research;
- GitHub research;
- regulatory retrieval;
- page/document reading;
- evidence extraction;
- schema completion;
- API/MCP/tool execution.

Initial preferred local model:

```text
qwen3:14b
```

Thinking should normally be disabled or minimized for routine tool-oriented work.

`ministral-3:14b` is the principal benchmark challenger/fallback.

### BUILDER

Used by the MVP Factory for:

- MVP architecture implementation;
- code generation;
- test generation;
- code repair;
- integration work;
- tool use inside the privileged NemoClaw/OpenShell runtime.

Initial preferred local model:

```text
qwen3:14b
```

Builder reasoning mode is task-dependent. Architecture or difficult debugging may justify thinking; routine implementation should avoid unnecessary reasoning overhead.

The Builder model remains benchmark-selected rather than permanently fixed.

### JUDGE

Used sparingly for independent challenge and arbitration:

- disputed conclusions;
- high-value BUILD/KILL decisions;
- red-team review;
- promotion/productization decisions;
- evaluation of Thinker conclusions;
- model-family independence checks.

Initial preferred local model:

```text
gpt-oss:20b-32k
```

The Judge is intentionally a different model family where practical.

## 36.3 Initial Local Model Configuration

For a 16 GB VRAM workstation, the initial configuration is:

```yaml
THINKER:
  primary: deepseek-r1:14b-48k
  alternate: qwen3:14b

DOER:
  primary: qwen3:14b
  alternate: ministral-3:14b

BUILDER:
  primary: qwen3:14b
  alternate: ministral-3:14b

JUDGE:
  primary: gpt-oss:20b-32k
  alternate: deepseek-r1:14b
```

The mapping is configuration, not domain logic.

DBIE must be able to replace any model without modifying Crew definitions or canonical venture semantics.

## 36.4 Crew-to-Model-Role Mapping

Every Crew and significant task declares its required role.

Example:

| Crew / Task | Model role | Typical mode |
|---|---|---|
| Opportunity synthesis | THINKER | reasoning |
| Assumption decomposition | THINKER | reasoning |
| Research planning | THINKER | reasoning |
| Market Evidence Crew | DOER | non-thinking/tool-oriented |
| Competitor Crew | DOER | non-thinking/tool-oriented |
| Regulatory Crew | DOER | non-thinking/tool-oriented |
| GitHub/OSS Crew | DOER | non-thinking/tool-oriented |
| Evidence extraction | DOER | non-thinking |
| Evidence reconciliation | THINKER | reasoning |
| Experiment design | THINKER | reasoning |
| MVP implementation | BUILDER | adaptive |
| Test/fix loop | BUILDER | adaptive |
| Independent red-team | JUDGE | reasoning |
| Productization challenge | JUDGE | reasoning |

This mapping must be persisted with each execution so later evaluation can compare model performance for the same role and task class.

## 36.5 Model-Resident Execution Phases

On a single 16 GB GPU, DBIE should prefer:

> **parallel execution within a model-resident phase; synchronization/checkpoint barrier; model switch; parallel execution of the next phase.**

Example venture cycle:

```text
PHASE A — THINK
model: DeepSeek-R1 14B

  Strategy Crew
  Assumption Crew
  Research Planning
  Experiment Design
        |
        v
     BARRIER
        |
  persist outputs
        |
   unload model


PHASE B — DO / RESEARCH
model: Qwen3 14B

  Market Research
  Competitor Research
  Pricing Research
  Community Research
  Regulatory Research
  GitHub Research
        |
        v
     BARRIER
        |
  persist evidence
        |
   unload model


PHASE C — THINK / SYNTHESIZE
model: DeepSeek-R1 14B

  Evidence Reconciliation
  Contradiction Analysis
  Gap Analysis
  Venture Decision
        |
        v
     BARRIER


PHASE D — BUILD
model: Qwen3 14B

  MVP Implementation
  Test Generation
  Repair
  Integration
  NemoClaw execution
        |
        v
     BARRIER


PHASE E — JUDGE, WHEN REQUIRED
model: GPT-OSS 20B

  Independent Review
  Red Team
  Promotion Arbitration
```

Phase E is conditional and should not run for every venture.

## 36.6 Model Phase Scheduler

Introduce a `ModelPhaseScheduler` above the `ModelRouter`.

```text
Workflow Scheduler
        |
        v
ModelPhaseScheduler
        |
        +-- dependency graph
        +-- model affinity
        +-- role
        +-- context requirement
        +-- priority
        +-- escalation requirement
        |
        v
ModelRouter
        |
        v
Ollama / vLLM
```

The scheduler groups runnable work by:

```text
model_role
resolved_model_id
dependency_barrier
context_requirement
priority
venture_batch
execution_mode
```

Its objective is to maximize useful GPU residency while respecting workflow dependencies.

The scheduler should avoid task-level model thrashing such as:

```text
DeepSeek -> Qwen -> DeepSeek -> Qwen -> GPT-OSS -> DeepSeek
```

when the same work can be safely reorganized as:

```text
DeepSeek batch -> checkpoint -> Qwen batch -> checkpoint -> DeepSeek batch
```

## 36.7 Logical Parallelism vs Physical Inference Parallelism

CrewAI may expose many runnable logical agents while only a small number of generations execute concurrently.

Example:

```text
logical runnable tasks: 20-50
active inference requests: initially 2-4
```

Concurrency is dynamically tuned from measured:

```text
aggregate tokens/sec
per-request tokens/sec
time-to-first-token
p50/p95 latency
VRAM usage
KV-cache pressure
context length
OOM/retry rate
CPU/RAM pressure
queue depth
```

DBIE must not equate the number of CrewAI agents with the number of simultaneous model generations.

## 36.8 Context Policy

Large configured context windows are ceilings, not targets.

Initial operating targets:

```text
DOER:    16k-32k
THINKER: 32k-48k
BUILDER: 16k-32k, expandable when required
JUDGE:   approximately 32k
```

Agents should receive retrieved and structured context:

```text
task
+ relevant assumptions
+ relevant evidence
+ required prior decisions
+ applicable capability/product context
```

rather than the complete venture history.

Supermemory/semantic retrieval and canonical PostgreSQL queries should be used to assemble task-specific context.

## 36.9 Model Performance Ledger

Every model invocation must produce a persistent performance record.

Minimum fields:

```text
model_run_id
run_id
venture_id
crew_id
agent_id
task_id
task_class
model_role
model_id
model_version_or_digest
quantization
runtime
thinking_mode
context_limit
input_tokens
output_tokens
reasoning_tokens_if_available
wall_clock_ms
time_to_first_token_ms
tokens_per_second
peak_vram_mb
queue_wait_ms
tool_calls
tool_failures
schema_valid
task_success
retry_count
escalated
estimated_cost
quality_score
judge_score
downstream_outcome_id
created_at
```

This ledger is separate from venture evidence.

A model performing well operationally is not evidence that a business hypothesis is correct.

## 36.10 Task-Class Benchmarking

Model quality must be evaluated **per task class**, not with one global model score.

Initial benchmark dimensions:

```text
opportunity synthesis
assumption decomposition
research planning
tool selection
tool argument correctness
evidence extraction
source quality
contradiction detection
evidence synthesis
experiment design
coding
test repair
red-team quality
decision calibration
structured-output validity
```

Example internal scorecard:

```text
                     DeepSeek   Qwen3   Ministral   GPT-OSS
Assumptions             ...       ...       ...        ...
Research/tool use       ...       ...       ...        ...
Evidence extraction     ...       ...       ...        ...
Synthesis               ...       ...       ...        ...
Coding                   ...       ...       ...        ...
Judging                  ...       ...       ...        ...
```

The scorecard must be derived from recorded executions and benchmark fixtures, not manually assumed.

## 36.11 Outcome-Linked Model Evaluation

Where possible, model runs should be linked to downstream outcomes.

Examples:

```text
research plan
    -> evidence discovered
    -> assumption resolution

experiment design
    -> experiment completed
    -> information gain

builder task
    -> tests passed
    -> sandbox deployment succeeded

venture recommendation
    -> observed market outcome
```

This permits analysis such as:

```text
Which THINKER produces assumptions that are resolved fastest?

Which DOER finds the highest proportion of independent primary evidence?

Which BUILDER reaches passing MVPs with the fewest repair cycles?

Which JUDGE is best calibrated against later observed outcomes?
```

Do not train routing policy directly on noisy short-term business outcomes without sufficient sample size and controls.

## 36.12 Model Challenger and Promotion Process

A configured primary model is never permanent.

For each role:

```text
PRIMARY
CHALLENGER
FALLBACK
```

A challenger can receive a bounded percentage of comparable tasks or run offline against stored fixtures.

Promotion requires evidence across:

```text
quality
reliability
tool correctness
latency
throughput
VRAM
context efficiency
retry rate
downstream effectiveness
```

Example:

```text
THINKER
primary:    DeepSeek-R1 14B
challenger: Qwen3 14B thinking

DOER
primary:    Qwen3 14B
challenger: Ministral-3 14B
```

This allows DBIE to discover that a general model is sufficient for a specialized role and eliminate unnecessary model switches.

## 36.13 Adaptive Routing and Escalation

The first implementation uses explicit phase mappings.

Later versions may route dynamically:

```text
routine task
    -> Qwen3

complex reasoning / unresolved contradiction
    -> THINKER

high uncertainty + material decision
    -> stronger THINKER or JUDGE

major promotion / investment decision
    -> independent JUDGE
```

Adaptive routing must remain deterministic from persisted routing rules and metrics. Agents cannot promote themselves to more privileged or expensive models.

## 36.14 Model Switching Metrics

Because model switching is a first-class architectural cost, DBIE must measure:

```text
model_load_ms
model_unload_ms
switch_count
GPU_idle_during_switch_ms
tasks_per_model_residency
tokens_per_model_residency
useful_work_per_residency
phase_duration
barrier_wait_ms
```

These metrics allow comparison between:

```text
fine-grained model specialization
```

and:

```text
fewer switches using Qwen3 for multiple roles
```

The architecture should prefer measured total workflow performance rather than maximum benchmark quality for each isolated task.

## 36.15 Reference Execution Record

The relationship among venture, Crew, task, role, model and runtime must be directly queryable:

```text
Venture
  |
  +-- Workflow Run
        |
        +-- Model Phase
              |
              +-- Crew
                    |
                    +-- Agent
                          |
                          +-- Task
                                |
                                +-- model_role
                                +-- resolved_model
                                +-- runtime
                                +-- performance record
                                +-- output artifact
                                +-- downstream outcome
```

This becomes the canonical structure for future model-performance reports.

## 36.16 Architectural Principle

DBIE optimizes models as a **portfolio of specialized computational resources**, not as interchangeable chat endpoints.

The default single-GPU strategy is:

> **Qwen3:14B for high-volume research and general execution/building; DeepSeek-R1:14B for specialized reasoning; GPT-OSS-20B for occasional independent judgment; parallelize tasks while a model is resident, checkpoint at barriers, and switch models only at deliberate phase boundaries.**

The exact models may change. The role, phase, measurement, and routing architecture remains stable.
