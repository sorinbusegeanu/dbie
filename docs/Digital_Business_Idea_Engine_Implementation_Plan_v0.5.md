# DIGITAL BUSINESS IDEA ENGINE

## Implementation Plan v0.5

29 August 2026

Companion to: `Digital_Business_Idea_Engine_System_Design_v0.5.md`

## 1. Implementation Objective

Build DBIE as a local-first Python application in which CrewAI is the only agent harness, authoritative business rules are deterministic custom code, local models are interchangeable through a Model Router, and all external capabilities are accessed through a permissioned Tool Gateway.

The first usable release must be able to discover a problem, generate a digital-only business idea, decompose it into falsifiable assumptions, collect traceable evidence through the ten MVP tools, apply deterministic eligibility/evidence gates, perform adversarial evaluation, and persist a resumable decision dossier.

Real-world experiments and autonomous learning come after the evidence pipeline is demonstrably reliable.

## 2. Non-Negotiable Implementation Constraints

1. CrewAI is the only general-purpose agent harness.
2. Do not introduce LangChain, LangGraph, AutoGen, or a second orchestration framework in the MVP.
3. Hard gates, scoring, evidence thresholds, permissions, budgets, and decision transitions must be deterministic Python functions.
4. Agents may propose facts or decisions, but may not mutate canonical state except through validated application services.
5. vLLM and Ollama must be adapters behind one provider-neutral interface.
6. Model choice must be configuration, never embedded in CrewAI agent definitions.
7. The ten MVP tools must be accessed through one Tool Gateway and emit common provenance/audit metadata.
8. PostgreSQL + pgvector is the target persistent store. SQLite may be used only for early local scaffolding.
9. Model agreement is not evidence. Source independence and observed outcomes remain separate concepts.
10. External spend, public deployment, outbound contact, paid acquisition, publication, and other consequential actions remain approval-gated.
11. Markdown is the canonical human-readable report format.
12. The 16 GB GPU profile must reserve material VRAM for KV cache and runtime overhead rather than maximizing model weight size.

## 3. Target Repository Structure

`dbie/`

- `pyproject.toml`
- `config/`
  - `default.yaml`
  - `models.yaml`
  - `tools.yaml`
  - `policies.yaml`
- `src/dbie/`
  - `domain/`
    - `models.py`
    - `enums.py`
    - `assumptions.py`
    - `evidence.py`
    - `experiments.py`
    - `decisions.py`
    - `eligibility.py`
    - `scoring.py`
  - `services/`
    - `candidate_service.py`
    - `evidence_service.py`
    - `decision_service.py`
    - `experiment_service.py`
  - `models/`
    - `base.py`
    - `router.py`
    - `vllm_provider.py`
    - `ollama_provider.py`
    - `external_provider.py`
    - `capabilities.py`
    - `scheduler.py`
  - `tools/`
    - `gateway.py`
    - `contracts.py`
    - `permissions.py`
    - `provenance.py`
    - `web_search.py`
    - `fetch_page.py`
    - `search_reddit.py`
    - `search_companies.py`
    - `search_github.py`
    - `search_regulations.py`
    - `read_document.py`
    - `python_execute.py`
    - `database_query.py`
    - `semantic_memory_search.py`
    - `mcp/`
  - `persistence/`
    - `db.py`
    - `repositories.py`
    - `migrations/`
    - `vector.py`
  - `crews/`
    - `discovery.py`
    - `ideation.py`
    - `validation.py`
    - `red_team.py`
    - `diligence.py`
  - `flows/`
    - `idea_pipeline.py`
    - `states.py`
    - `events.py`
  - `evaluation/`
    - `pairwise.py`
    - `calibration.py`
    - `independence.py`
  - `experiments/`
    - `registry.py`
    - `runner.py`
    - `metrics.py`
    - `approvals.py`
  - `observability/`
    - `logging.py`
    - `metrics.py`
    - `tracing.py`
  - `reports/`
    - `markdown.py`
  - `cli.py`
- `tests/`
  - deterministic unit tests
  - provider contract tests
  - tool contract tests
  - golden workflow fixtures
  - runtime smoke fixtures
- `benchmarks/`
  - `tool_use/`
  - `structured_output/`
  - `evidence_quality/`
  - `multi_step_recovery/`
  - `model_profiles/`
- `runs/`

## 4. Core Interfaces to Freeze Early

### 4.1 Canonical domain entities

Freeze typed schemas for:

- OpportunitySignal
- BusinessIdea
- Assumption
- EvidenceItem
- EvidenceLineageGroup
- Competitor
- ToolCallRecord
- ModelCallRecord
- Evaluation
- PairwiseMatch
- Experiment
- ExperimentPrediction
- ExperimentOutcome
- CandidateDecision
- Run

Each canonical record has stable ID, creation timestamp, schema version, run provenance, and immutable source references where applicable.

### 4.2 LLM provider contract

Required operations:

- `generate(request)`
- `structured_generate(request, schema)`
- `tool_call(request, available_tools)`
- `capabilities()`
- `health()`
- `usage()`

Required response metadata:

- provider
- model
- model/version identifier if available
- latency
- prompt tokens
- completion tokens
- finish reason
- structured-output validation result
- tool-call parse result
- retry count

### 4.3 Tool contract

Every tool receives a common envelope containing:

- run_id
- task_id
- actor_id
- candidate_id when applicable
- assumption_id when applicable
- purpose
- requested operation
- typed arguments
- tool budget

Every tool returns:

- result payload
- provenance records
- source timestamps
- confidence/type metadata where applicable
- cost/usage
- cache status
- error category
- elapsed time

### 4.4 Decision service contract

Only the Decision Service may move a candidate between authoritative states such as:

`DISCOVERED → GENERATED → ELIGIBLE → VALIDATING → RED_TEAM → FINALIST → EXPERIMENTING → BUILD | ITERATE | KILL | MORE_EVIDENCE`

CrewAI agents return recommendations; the Decision Service validates preconditions and commits state.

## 5. Phase 0 — Repository and Runtime Foundation

### Scope

Create the package structure, configuration loader, typed logging, run IDs, exception hierarchy, CLI shell, and persistence connection.

### Deliverables

- Installable Python package.
- `dbie doctor` command validating Python, database, GPU/model endpoints, configured tools, and required credentials.
- Config profiles for local development and 16 GB GPU runtime.
- Structured JSON logs plus human-readable console summaries.
- Run directory and durable run record.

### Acceptance

- Fresh checkout can initialize DBIE with one command.
- `doctor` clearly distinguishes unavailable optional services from fatal dependencies.
- A run can be created, persisted, resumed, and closed without CrewAI or an LLM.

### Exit test

Run deterministic smoke command that creates a run, writes one synthetic candidate, reloads it, and verifies identical state.

## 6. Phase 1 — Deterministic Domain Engine

### Scope

Implement the system semantics before adding agents.

### Implement

- Digital-only eligibility contract.
- Autonomous-scalability hard gate.
- Assumption severity and status model.
- Evidence tiers.
- Evidence independence/lineage accounting.
- Candidate state machine.
- Fatal-assumption logic.
- Deterministic scoring/uncertainty calculations.
- Decision precedence: observed outcomes > primary evidence > derived evidence > model judgment.
- Approval states.

### Required tests

Golden fixtures for:

- physical business is rejected regardless of attractive score;
- remote labor-linear consultancy fails autonomous scalability unless transition assumptions exist;
- duplicated/syndicated sources count as one lineage group;
- unresolved fatal assumption prevents finalist promotion;
- model consensus cannot validate demand;
- L5 experiment outcome overrides earlier LLM confidence;
- prediction record cannot be modified after experiment starts.

### Exit criteria

All candidate-state and evidence decisions can be exercised with synthetic fixtures without loading an LLM.

## 7. Phase 2 — Persistence and Memory Substrate

### Scope

Implement PostgreSQL schema, repositories, pgvector retrieval, content hashes, source lineage, and immutable event records.

### Implement

- Canonical relational tables.
- Append-only experiment prediction/outcome events.
- Evidence-source tables and lineage groups.
- Semantic embeddings for opportunity/idea/evidence retrieval.
- Deduplication service.
- Query APIs used by agents through controlled services rather than raw DB access.

### Deliberate simplification

Do not introduce Neo4j or another graph database. Represent graph edges relationally first. Add a graph engine only after real queries demonstrate a need.

### Exit criteria

- Semantic lookup can find related prior ideas.
- Exact state reconstruction is deterministic.
- All evidence references can be traced to their source and lineage group.
- Repeated run does not create duplicate canonical evidence when content hashes match.

## 8. Phase 3 — Model Router and Local Serving

### Scope

Implement model/provider independence before integrating CrewAI.

### Providers

1. `OllamaProvider`
2. `VLLMProvider`
3. `ExternalProvider` stub/optional adapter for later L4 escalation

### Model profiles

At minimum:

- GPT-OSS-20B baseline profile.
- Quantized Ministral 3 14B Reasoning low-VRAM profile.

### Router behavior

Route based on:

- task class;
- provider health;
- required tool/structured-output capability;
- required context;
- independence level;
- queue depth;
- VRAM/context policy;
- configured fallback;
- historical benchmark score.

### 16 GB GPU policy

Initial target:

- prefer model weight occupancy around 8–10 GB where possible;
- reserve remaining VRAM for KV cache/runtime/batching;
- start max model context at 16k–32k;
- start active inference concurrency at 4, test toward 8;
- reduce context or concurrency on memory-pressure thresholds before OOM;
- never load one model instance per agent.

### Acceptance

Run identical structured-generation fixtures through Ollama and vLLM. Both must return the same application-level schema and error categories even if model text differs.

## 9. Phase 4 — DBIE-Specific Model Benchmark

### Purpose

Do not choose the primary model from generic benchmark reputation alone.

### Benchmark categories

1. Tool selection accuracy.
2. Tool argument/schema accuracy.
3. Structured-output validity.
4. Multi-step tool recovery after an intentionally failed call.
5. Evidence extraction accuracy.
6. Unsupported-claim/hallucination rate.
7. Assumption decomposition quality.
8. Adversarial critique quality.
9. Pairwise ranking stability.
10. Latency, tokens/s, peak VRAM, KV pressure, and effective concurrency.

### Candidate models

- GPT-OSS-20B.
- Ministral 3 14B Reasoning quantized profile.
- Additional local models only when they meet the configured VRAM envelope.

### Output

One machine-readable benchmark report per model/provider combination plus Markdown comparison.

### Decision

Select primary model by weighted DBIE benchmark score subject to the hard VRAM/headroom constraint. Keep the other model as alternative or L3 heterogeneous judge if practical.

## 10. Phase 5 — Tool Gateway Foundation

### Scope

Implement the common gateway before individual tools.

### Gateway responsibilities

- actor authorization;
- tool allowlist;
- typed input validation;
- rate limits;
- per-run/per-candidate budget;
- retries with bounded policy;
- caching;
- provenance capture;
- audit record;
- timeout/cancellation;
- normalization of provider errors;
- approval check for consequential actions.

### CrewAI integration

CrewAI receives narrow tool wrappers. The wrapper calls Tool Gateway; agents never receive raw API credentials or direct unrestricted Python/SQL/browser capabilities.

### Exit criteria

A synthetic agent cannot invoke a tool outside its permission set and every denied/allowed call is auditable.

## 11. Phase 6 — Ten MVP Tools

Implement in this order because later tools depend on earlier provenance and storage.

### T01 `web_search`

Actors: Trend Scout, Pain-Point Miner, Industry Analyst, Competitor Analyst, Validation Analyst, Red Team.

Call when: broad external discovery is needed or a claim lacks candidate sources.

Return: ranked result metadata, snippets only as discovery hints, source IDs, timestamps.

Do not treat search snippets as validated evidence.

### T02 `fetch_page`

Actors: Evidence Analyst, Validation Analyst, Regulatory Scout, Competitor Analyst, Red Team.

Call when: a search result or known URL must be inspected as primary page content.

Return: normalized content, metadata, content hash, source lineage hints.

### T03 `search_reddit`

Actors: Pain-Point Miner, Customer/Market Analyst, Red Team.

Call when: repeated user/customer complaints, workarounds, language, or community sentiment could illuminate an assumption.

Return: thread/post references and normalized excerpts with dates. Community evidence is observational, not authoritative market sizing.

### T04 `search_companies`

Actors: Industry Analyst, Competitor Analyst, Distribution Analyst, Market Analyst.

Call when: competitor density, target-company population, funding/employee/company signals, or market structure must be examined.

Return: structured company records with provider/source provenance.

### T05 `search_github`

Actors: Technology Scout, Technical Analyst, Prototype Analyst, Red Team.

Call when: feasibility, OSS substitutes, implementation maturity, developer adoption, or competing technical approaches matter.

Return: repositories/issues/releases metadata and source references.

### T06 `search_regulations`

Actors: Regulatory Scout, Validation Analyst, Red Team.

Call when: a business depends on compliance obligations, regulatory timing, allowed/prohibited activity, or mandatory process changes.

Prefer authoritative regulator/legislative sources. Material legal conclusions remain escalation/human-review candidates.

### T07 `read_document`

Actors: Evidence Analyst, Market Analyst, Regulatory Scout, Technical Analyst.

Call when: a PDF/report/CSV/Markdown/document contains evidence that cannot be reliably evaluated from snippets.

Return: page/section-addressable extracted content and document metadata.

### T08 `python_execute`

Actors: Economics Analyst, Data Analyst, Technical/Prototype Analyst under restricted profile.

Call when: deterministic calculations, statistics, simulations, parsing, or controlled technical tests are required.

Never use conversational arithmetic as authoritative financial output when this tool can calculate it reproducibly.

### T09 `database_query`

Actors: Flow services and read-authorized analysts. Write operations remain application-service controlled.

Call when: exact canonical state, historical outcomes, prior evidence, or aggregate analytics are needed.

Agents do not receive arbitrary database write access.

### T10 `semantic_memory_search`

Actors: Discovery, Ideation, Validation, Red Team, Diligence.

Call when: related prior problems, ideas, assumptions, evidence, failures, or experiments may prevent duplication or inform search.

Semantic similarity is retrieval evidence, not truth and not a decision signal by itself.

### Phase 6 acceptance

Each tool passes:

- contract validation;
- permission checks;
- timeout/error normalization;
- provenance completeness;
- deterministic fixture/replay where feasible;
- cache behavior;
- explicit actor allowlist tests.

## 12. Phase 7 — CrewAI Flow Skeleton

### Scope

Build orchestration only after Domain Engine, Router, Persistence, and Gateway exist.

### Initial Flow stages

1. initialize_run
2. discover_signals
3. generate_ideas
4. eligibility_gate
5. decompose_assumptions
6. collect_evidence
7. validate_assumptions
8. red_team
9. rank_portfolio
10. produce_dossier
11. finalize_run

Every stage receives and returns typed application state. CrewAI output is parsed/validated before persistence.

### Required failure semantics

- tool timeout → bounded retry or alternate source;
- malformed structured output → one schema repair attempt, then fail task;
- model unavailable → Router fallback;
- insufficient evidence → `MORE_EVIDENCE`, not fabricated confidence;
- candidate-specific failure → isolate candidate, continue run;
- run-level dependency failure → persist checkpoint and exit cleanly.

## 13. Phase 8 — Discovery and Ideation Crews

### Implement actors

Discovery:

- Trend Scout
- Pain-Point Miner
- Industry Analyst
- Regulatory Scout
- Technology Scout
- Contrarian/Neglected-Problem Scout

Ideation:

- Automation Lens
- AI-Native Lens
- Regulatory Lens
- Vertical SaaS Lens
- API/Data Lens
- Services-to-Software Lens
- Capability-Inversion Lens
- Cross-Industry Analogy Lens

### Requirements

- Generator cannot validate its own candidate.
- 15–25% exploration budget reserved for deliberately dissimilar search.
- Every generated idea links back to observed signal(s).
- Digital-only and autonomous-scalability gates run immediately after generation.

### Exit criteria

A controlled run can generate 50+ raw ideas, deduplicate them, reject scope violations deterministically, and persist survivors with provenance.

## 14. Phase 9 — Assumption and Evidence Pipeline

### Implement

For each eligible idea create atomic assumptions across:

- problem existence/severity;
- identifiable buyer;
- willingness to pay;
- reachable distribution;
- technical feasibility;
- automation ratio;
- marginal human burden;
- economics;
- competition/substitution;
- defensibility;
- regulatory feasibility;
- timing/why-now.

Each assumption has falsification criteria before validation begins.

### Evidence collection policy

Route tool calls by assumption type. Stop research when:

- configured evidence threshold is met;
- evidence is irreducibly conflicting and escalation is warranted;
- source diversity has saturated;
- remaining queries have low expected information gain;
- budget is exhausted.

### Exit criteria

Every finalist candidate has an assumption map in which every material claim is evidence-linked, contradicted, unknown, or explicitly unvalidated.

## 15. Phase 10 — Validation, Red Team, and Independence Ladder

### Implement

Validation actors:

- Demand Validator
- Economics Analyst
- Distribution Analyst
- Technical Analyst
- Competitive Analyst
- Regulatory Validator

Red-team actors:

- Market Skeptic
- Incumbent Response Analyst
- Commoditization Analyst
- Distribution Skeptic
- Economics Skeptic
- Automation/Operations Skeptic

### Independence policy

- L0 primary model judgment.
- L1 evidence + deterministic checks.
- L2 repeated isolated primary-model contexts for stability only.
- L3 heterogeneous local model where available.
- L4 optional stronger/external review.
- L5 observed market experiment.

### Exit criteria

No candidate reaches FINALIST without adversarial evaluation and no demand/pricing assumption is marked validated solely from model agreement.

## 16. Phase 11 — Pairwise Tournament and Portfolio Selection

### Implement

- deterministic pre-filter;
- pairwise match scheduler;
- randomized presentation order;
- repeated matches for unstable comparisons;
- Elo/Bradley-Terry-style ranking or equivalent;
- ranking confidence/stability metric;
- escalation for consequential unstable matchups.

Pairwise ranking is advisory and cannot override hard gates.

### Exit criteria

A portfolio can be ranked reproducibly from stored match records and rerun under a different model without losing original results.

## 17. Phase 12 — Markdown Dossier and Observability

### Dossier contents

- idea summary;
- why now;
- customer/buyer;
- assumption map;
- evidence for/against;
- source independence;
- unknowns;
- competitors;
- business model variants;
- deterministic economics;
- automation/marginal-human-burden estimate;
- red-team findings;
- ranking results;
- recommended next experiments;
- BUILD / ITERATE / KILL / MORE_EVIDENCE state.

### Observability

Measure per run/candidate/agent/tool/model:

- calls;
- latency;
- tokens;
- failures/retries;
- tool selection correctness;
- malformed calls;
- evidence yield;
- source diversity;
- model disagreement;
- GPU memory;
- queue depth;
- inference throughput;
- cost where applicable.

## 18. Phase 13 — Digital Experiment Engine

Do not build this before the research/evaluation pipeline is stable.

### Implement

- experiment proposal;
- pre-registration;
- immutable prediction;
- approval request;
- bounded execution adapter;
- metric ingestion;
- stop rules;
- outcome record;
- assumption update.

Initial experiments should be digital, cheap, reversible, and minimally consequential: prototype benchmarks, landing-page interest tests, pricing-choice tests, waitlist conversion, or controlled usability tests.

Paid ads, outreach, publication, domains, or customer contact require explicit approval.

## 19. Phase 14 — Calibration and Learning

Only observed outcomes should materially update historical priors.

### Implement

- predicted probability vs observed outcome calibration;
- evaluator reliability by task/model;
- tool/source yield statistics;
- experiment information gain;
- false-rejection audit sampling;
- novelty/coverage metrics;
- holdout evaluation preventing historical winners from collapsing exploration.

### Guardrail

Never train future priors directly from previous LLM scores as though they were outcomes.

## 20. Implementation Sequence and Dependency Graph

Recommended order:

Phase 0 foundation
→ Phase 1 deterministic domain engine
→ Phase 2 persistence
→ Phase 3 model router
→ Phase 4 DBIE model benchmark
→ Phase 5 tool gateway
→ Phase 6 ten tools
→ Phase 7 CrewAI Flow
→ Phase 8 discovery/ideation
→ Phase 9 assumptions/evidence
→ Phase 10 validation/red team
→ Phase 11 ranking
→ Phase 12 reporting/observability
→ Phase 13 experiments
→ Phase 14 calibration/learning

Do not begin CrewAI prompt tuning before Phases 0–6 are sufficiently stable. Otherwise framework behavior will hide defects in schemas, permissions, evidence semantics, and model contracts.

## 21. MVP Cut Line

The first production-worthy MVP ends after Phase 12.

It must support:

- one local model endpoint;
- both provider adapters implemented even if only one is active;
- ten MVP tools;
- discovery → idea → eligibility → assumptions → evidence → red-team → ranking → dossier;
- persistent resumable runs;
- 100% traceable evidence;
- deterministic hard gates;
- no real-world autonomous experiment execution yet.

Phase 13+ turns the evaluator into a real business-discovery system through observed outcomes.

## 22. First Model Deployment Recommendation

For a 16 GB GPU, implement both profiles but begin runtime benchmarking with:

1. Quantized Ministral 3 14B Reasoning through vLLM as the low-VRAM profile.
2. GPT-OSS-20B through Ollama as the baseline/reference profile.

If GPT-OSS-20B leaves insufficient KV/cache headroom under the target workload, it remains a benchmark or low-concurrency alternative rather than the production default.

The production model must be selected only after Phase 4 measures DBIE-specific tool and reasoning behavior.

## 23. Definition of Done for v1 MVP

DBIE v1 MVP is complete only when all of the following are true:

- A fresh run can execute end-to-end without manual editing of intermediate state.
- The Flow is resumable after controlled interruption.
- No hard domain decision depends only on prompt wording.
- Both Ollama and vLLM satisfy the same provider contract.
- All ten tools satisfy actor permissions and provenance contracts.
- Every finalist is digital-only and autonomously scalable by policy.
- Every material assumption is traceable to evidence, counter-evidence, unknown status, or explicit experiment requirement.
- Correlated sources do not inflate effective evidence counts.
- Generator and evaluator responsibilities are separated.
- Red-team evaluation is mandatory before finalist state.
- Model consensus is never labeled market evidence.
- Primary-model performance has been measured on the DBIE-specific benchmark.
- GPU headroom, context length, and active concurrency are observable and bounded.
- Final output is a reproducible Markdown dossier plus machine-readable structured state.
- No agent can bypass Tool Gateway permissions or approval rules.
- An end-to-end benchmark run can be reproduced from saved configuration, model profile, tool fixtures/source references, and schema versions.

## 24. Deferred Until After MVP

Do not implement initially:

- second general-purpose agent harness;
- dedicated graph database;
- autonomous paid advertising;
- autonomous mass outreach;
- automatic company formation/payment movement;
- fine-tuning the primary model;
- large-scale multi-GPU scheduler;
- self-modifying agent prompts without evaluation gates;
- learning directly from historical LLM rankings;
- complex UI before the CLI/reports and observability are stable.

## 25. Main Implementation Risks

| Risk | Mitigation |
|---|---|
| CrewAI logic leaks into domain truth | Keep state transitions and gates in Domain Engine |
| Local model produces malformed tools/JSON | schema-constrained generation, repair limit, benchmark before adoption |
| 16 GB GPU OOM under concurrency | low-VRAM model option, context caps, adaptive concurrency, telemetry |
| Search volume creates fake evidence | fetch primary sources, lineage grouping, evidence tiers |
| Too many tools become difficult for model | actor-specific allowlists; only expose relevant tools per task |
| Agent loops consume tokens without information gain | Flow budgets, stopping rules, tool-result cache |
| Persistence biases future ideation | explicit novelty budget and dissimilar retrieval |
| Same-model validators agree spuriously | L2 labeled stability only; L3/L4/L5 escalation |
| Framework churn | provider/tool/domain interfaces isolate CrewAI and runtimes |
| Premature experiment automation | defer until evidence pipeline passes acceptance suite |

## 26. Recommended First Build Increment

Implement only Phases 0–3 first. At the end of that increment, DBIE should have no meaningful autonomous agents yet, but it should already possess the most important architecture:

- canonical domain objects;
- deterministic gates;
- durable state;
- provider-neutral model calls;
- vLLM/Ollama switching;
- GPU/context/concurrency telemetry.

That foundation makes every later CrewAI and tool feature replaceable and testable rather than entangled with prompts.
