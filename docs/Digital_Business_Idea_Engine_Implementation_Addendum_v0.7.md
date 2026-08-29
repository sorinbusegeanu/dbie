# DIGITAL BUSINESS IDEA ENGINE

## Implementation Addendum v0.7 --- Changes Only

29 August 2026

This addendum contains only implementation changes introduced by System
Design v0.7. It assumes the v0.5 implementation plan and v0.6
OSS-adapter addendum remain in force.

# 1. Scope Delta

Extend DBIE from `Idea -> Evaluate -> Experiment` to a persistent
venture lifecycle capable of bounded autonomous MVP construction,
human/agent-facing interfaces, controlled experimentation,
productization, capability reuse and portfolio allocation. Do not add
another agent harness. CrewAI remains the only agent harness; lifecycle,
budgets, permissions and promotion decisions remain deterministic custom
Python.

# 2. Phase 16 --- Venture Domain and Lifecycle

Add `Venture`, `VentureState`, `VentureDecision`, `MVP`, `Product`, and
lifecycle transition records. Implement a transition service with
explicit allowed transitions and immutable decision history.

**Acceptance:** illegal transitions fail deterministically; `KILLED`
ventures remain queryable; every idea/assumption/experiment can be
linked to a venture; agents cannot directly update lifecycle state.

# 3. Phase 17 --- MVP Specification and Candidate Gate

Implement `MVPSpec` schema and `MVP_CANDIDATE` gate. Add deterministic
measures for estimated build time/cost, information gain, dependency
burden, technical feasibility, reversibility and capability reuse.

**Acceptance:** no build starts without a persisted spec, critical
assumption, preregistered success/failure criteria and bounded budgets;
post-start mutation of success criteria is rejected/versioned as a new
experiment.

# 4. Phase 18 --- Capability and Product Registry

Create capability registry tables/services and semantic retrieval
through existing pgvector memory. Register schemas, endpoints, quality,
cost, dependencies, versions, licensing and lifecycle. Implement
resolver classifications: `REUSE`, `ADAPT`, `OSS`, `BUY_API`, `BUILD`.

**Acceptance:** every MVP build performs registry lookup; duplicate
capability proposals are surfaced; a prior capability can be referenced
as a dependency without copying its implementation.

# 5. Phase 19 --- Privileged MVP Tool Gateway

Create a separate permission class for build tools. Add isolated Git
workspace, Docker sandbox, runtime/test adapters, dependency scanner,
static/security scanners, container packaging and contract-testing
adapters. Research actors must not receive these tools.

**Acceptance:** actor/tool ACL tests prove separation;
filesystem/network/CPU/RAM/time limits are enforced; secrets are
injected only by policy; build artifacts cannot directly trigger public
deployment.

# 6. Phase 20 --- MVP Factory Crew

Implement CrewAI actors: MVP Spec Agent, Reuse Architect, Solution
Architect, Builder, Test Agent, Security Reviewer, Deployment Agent,
Experiment Agent and Outcome Analyst. Keep build-state transitions in
custom Python.

**Acceptance:** one synthetic venture can progress from validated
assumption through spec, reuse analysis, build, tests, security review
and packaged sandbox artifact; Builder cannot approve its own output;
retries terminate at configured limits.

# 7. Phase 21 --- Dual Human/Agent Contracts

Add product interface schemas for Human UI, REST, MCP and optional SDK.
Define machine contracts with typed inputs/outputs, deterministic error
semantics, auth scopes, rate limits, versioning, provenance and cost
metadata.

**Acceptance:** a sample MVP exposes the same core capability through a
minimal human UI and either REST or MCP; contract tests verify both
routes call the same domain service.

# 8. Phase 22 --- Sandbox Deployment and Telemetry

Add isolated deployment target and telemetry event schema. Correlate
events with venture, MVP/product, version, experiment, assumption and
consumer type. Add activation, completion, repeat-use, task-success,
latency and marginal-cost metrics.

**Acceptance:** an MVP can be deployed only to the sandbox autonomously;
telemetry can reconstruct experiment outcomes; observations are
append-only and linked to the preregistered experiment.

# 9. Phase 23 --- Experiment-to-Outcome Loop

Extend experiment engine to use MVP telemetry. Freeze predictions and
success criteria at experiment start. Implement outcome comparison and
confidence/calibration update without rewriting historical beliefs.

**Acceptance:** synthetic positive and negative experiments produce
expected BUILD/ITERATE/KILL/MORE_EVIDENCE recommendations; original
predictions remain inspectable; L5 observations outrank LLM evaluations.

# 10. Phase 24 --- Productization Gate

Implement deterministic `MVP -> PRODUCT` gate requiring market/usage
evidence, repeatability, unit economics/path, security status,
operational owner/policy and human approval for public commercial
deployment.

**Acceptance:** technically successful but demand-negative MVPs cannot
become products; approval is required before public deployment; product
registration creates stable versioned contracts and monitoring
requirements.

# 11. Phase 25 --- Agent-Native Opportunity Discovery

Extend discovery schemas/prompts with `customer_mode = human|agent|both`
and agent-native problem categories. Require evidence of a
machine-consumable problem and an economic principal; an API alone is
not evidence of agent demand.

**Acceptance:** fixtures distinguish genuine agent-native demand from
ordinary SaaS with an API; agent-facing assumptions are independently
represented and tested.

# 12. Phase 26 --- Portfolio Intelligence

Implement portfolio candidate-action ranking in deterministic Python
using configurable expected information gain, business value,
cash/time/compute cost, risk, reuse multiplier and diversification
constraints. Add overlap and shared-capability detection using
structured relations plus semantic retrieval.

**Acceptance:** portfolio engine can rank a mixed queue of research,
experiment, build and capability-investment actions; it cannot execute
spend/deployment itself; duplicate experiments and overlapping ventures
are detected.

# 13. Phase 27 --- Capability Composition

Allow a new MVPSpec to bind existing internal capabilities as
dependencies. Add dependency health, version and marginal-cost
propagation. Record internal calls as telemetry while keeping internal
reuse separate from external market evidence.

**Acceptance:** build a second synthetic MVP using a capability from the
first; demonstrate reduced new implementation; failure of the shared
dependency is visible to dependent ventures.

# 14. Phase 28 --- Controlled Externalization

Add approval workflows for public deployment, paid experiments, outbound
communication and scaling. Introduce explicit monetary and compute
budget envelopes with audit records.

**Acceptance:** sandbox actions can remain autonomous;
public/spend/outreach actions fail closed without authorization;
approved bounded actions cannot exceed their envelope.

# 15. Configuration Delta

Add configuration sections for `venture_lifecycle`, `mvp_factory`,
`build_sandbox`, `capability_registry`, `product_contracts`,
`telemetry`, `productization`, `portfolio`, and `approval_policy`.
Defaults must favor sandbox-only execution and zero autonomous external
spend.

# 16. Database Migration Delta

Add tables for ventures, venture_transitions, mvp_specs, mvp_versions,
build_runs, build_artifacts, test_runs, security_reviews, products,
product_versions, capabilities, capability_versions,
capability_dependencies, product_interfaces, telemetry_events,
portfolio_actions, approvals and budget_ledgers. Add foreign keys back
to assumptions, evidence and experiments rather than duplicating those
records.

# 17. Observability Delta

Add metrics: MVP candidate rate, autonomous build success, build
retries, median build time/cost, test/security failure rates, reuse
ratio, new-code ratio, sandbox experiment rate, activation/repeat-use,
agent-vs-human usage, MVP-to-product conversion, kill rate, capability
reuse count, portfolio allocation accuracy and prediction calibration
after observed outcomes.

# 18. Security Delta

Treat generated code as untrusted. Default deny network and host
filesystem access in build execution; enforce image/package allow
policies where practical; scan dependencies and artifacts; redact
secrets from logs; sign/hash build artifacts; preserve provenance from
MVPSpec through deployed version. Deployment credentials are
inaccessible to ordinary CrewAI research/build agents.

# 19. Recommended Build Order Delta

Implement in this order: **Venture domain -\> MVPSpec/gate -\>
capability registry -\> privileged build gateway -\> MVP Factory -\>
interface contracts -\> sandbox deployment/telemetry -\> outcome loop
-\> productization -\> agent-native discovery -\> portfolio intelligence
-\> capability composition -\> controlled externalization.**

Do not begin portfolio optimization before telemetry/outcome attribution
works; otherwise the allocator optimizes model opinions rather than
observed results.

# 20. v0.7 Exit Gate

v0.7 is complete when an end-to-end fixture can: discover/accept a
validated idea; create a venture; preregister an MVP experiment; reuse
available capabilities; autonomously build/test/security-review a
minimal artifact in isolation; expose a human and/or agent contract;
sandbox-deploy it; collect attributable telemetry; evaluate the observed
outcome; deterministically kill/iterate or nominate it for
productization; register successful capabilities; and make those
capabilities available to a later venture. All external commercial
actions remain approval-gated.
