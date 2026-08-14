# Qadam Canonical Tradeability Compiler And Agent Gauntlet Implementation Plan

Date: 2026-08-15

Status: Planned, not implemented

Purpose: Permanently remove recurring evidence-contract drift between Qadam's
research producers and decision consumers, then make local and frontier model
work reproducible, critic-reviewed, bounded, and compilable into one canonical
paper-tradeability contract.

Primary outcome: A complete current setup must either compile into one typed
`TradeabilityEnvelope` and progress through Akber, shadow, risk, Router, and
canonical PaperOps, or stop with one accurate blocker attributed to its real
source. No setup may be lost because two modules encode the same evidence in
different JSON shapes.

This plan is an evolution of the existing Qadam system. It does not create a
second execution route, replace the dashboard, weaken hard risk limits, enable
live capital, or turn model agreement into trade authority.

## 1. Executive Decision

Qadam must stop behaving like a loose collection of agents and JSON artifacts
and start behaving like a compiler.

The compiler model is:

1. Qadam receives provider-backed observations and current market evidence.
2. Python creates an immutable, role-bounded agent task packet.
3. One worker performs one declared research job.
4. Independent critics evaluate schema, provenance, temporal safety, economic
   reasoning, alternative explanations, and authority boundaries.
5. Python accepts only critic-approved structured outputs.
6. Python deterministically compiles accepted research into one canonical
   `TradeabilityEnvelope`.
7. Akber consumes that envelope rather than rediscovering fields across several
   artifacts.
8. Shadow, portfolio risk, Router, and PaperOps consume the same generation and
   lineage.
9. Every result, rejection, hold, and compilation defect becomes durable
   experiment memory.

The important distinction is:

- agents may improve the quality of research evidence;
- critics may accept or reject agent work against explicit criteria;
- only deterministic Python may validate contracts and advance workflow state;
- only canonical PaperOps may submit an Alpaca paper order;
- no model, critic, graph, dashboard, Telegram message, or compiler output has
  broker authority.

## 2. Why This Work Is Necessary

The recurring Akber/Foundry failure is a failure class, not one missing field.

The current codebase contains:

- a canonical Foundry V3 and Akber V3 path;
- a separate Foundry V4 and QEG hypothesis path;
- canonical and QEG-specific hypothesis, packet, and Akber artifacts;
- adapters that translate one nested shape into another;
- tests that can prove modules using hand-completed fixtures without proving the
  scheduled producer chain emitted the same fields;
- health checks that can pass when zero hypotheses entered Akber;
- active runtime modules that are currently dirty or untracked;
- agent output schemas that allow undeclared extra properties;
- prompt text embedded directly in Python rather than a versioned prompt
  registry;
- duplicate agent directories whose authority and use must be audited;
- operational health and tradeability reachability presented as related but
  insufficiently separated states.

Earlier evidence-fit repairs were valid for the path they changed. Later
features created another contract surface and reopened the same failure class.
The permanent repair is therefore consolidation, not another adapter.

### 2.1 Ten-Fix Traceability Matrix

The original ten RCA fixes remain the mandatory spine of this plan. The
prompting and agent-compilation work extends them; it does not replace them.

| RCA fix | Owning phases | Completion proof |
| --- | --- | --- |
| 1. Replace parallel hypothesis shapes with one typed tradeability contract | CTC-2, CTC-7 | One generated `TradeabilityEnvelope.v1` schema and no competing downstream hypothesis contract |
| 2. Give that contract exactly one canonical producer | CTC-0, CTC-7 | Producer inventory and migration checker report one active writer |
| 3. Generate the JSON Schema from the executable Python model | CTC-2 | Pydantic and JSON Schema hashes match; unknown fields fail |
| 4. Prove that required evidence can actually be collected | CTC-3 | Every hard field maps to a real provider or deterministic producer; impossible requirements fail before Akber |
| 5. Keep all decision inputs in one atomic generation | CTC-8 | Source, score, agent, critic, envelope, Akber, shadow, risk, and Router artifacts share one generation and input hashes |
| 6. Test the real producer-to-PaperOps journey from disk | CTC-10 | Real modules create every internal artifact and a valid fixture reaches a broker-disabled handoff |
| 7. Run a safe reachability canary on every build | CTC-11, CTC-14 | Signed test-namespace canary reaches handoff validation without an order |
| 8. Stop empty checks from masquerading as tradeability proof | CTC-11 | Certification distinguishes `not_exercised`, `reachable`, `blocked_contract`, and `blocked_operational` |
| 9. Classify contract breakage as an engineering defect | CTC-12 | Structural mismatches open a circuit and deduplicated repair request rather than an ordinary market hold |
| 10. Ship only a clean, restart-reproducible release | CTC-14 | Running build equals a committed release, active untracked runtime code is zero, and the soak passes |

Additional recommendations introduced by this plan are:

- versioned task packets and prompt compilation rather than prompts embedded in
  Python;
- strict task-specific agent schemas rather than permissive generic outputs;
- independent, bounded critics with objective predicate receipts;
- accepted and rejected research memory with immutable evidence lineage;
- source-content prompt-injection isolation;
- one same-generation decision DAG rather than cadence-based artifact joins;
- explicit separation of operational health, tradeability reachability, and
  current market opportunity;
- protected dashboard enrichment without changing the current route structure
  or creating authority.

## 3. Prompting Guidance Applied To Qadam

The attached Prompting Gauntlet recommends shared context, one worker per
slice, independent critics, countable end conditions, bounded autonomous loops,
artifact verification, persistent rejection memory, and staged autonomy.

Those ideas are useful for Qadam when translated into financial-system terms.

| Prompting principle | Qadam implementation |
| --- | --- |
| Shared brief before work | Immutable task packet with evidence refs, objective, output schema, constraints, and generation ID |
| One worker per slice | One agent role performs one bounded transformation |
| Separate critic | Independent schema, evidence, economic, adversarial, and safety critics |
| Concrete quality bar | Machine-checkable acceptance predicates, not subjective approval |
| Countable end condition | Required critic receipts, zero schema errors, bounded retry count, and one final task state |
| Verify the artifact | Validate output JSON, evidence refs, provider timestamps, and hashes rather than trusting an agent summary |
| Persist memory | Store accepted, rejected, superseded, and inconclusive task results with reasons |
| Stop on roadblock | Emit a typed blocker and repair request; never lower the bar silently |
| Staged autonomy | Research recommendation first, deterministic paper progression only after earned evidence |
| Use telemetry as judge | Measure forward outcomes, net-of-cost results, and gate attribution rather than model confidence alone |

Qadam must deliberately reject these generic gauntlet practices:

- no subjective "utterly wowed" gate for financial evidence;
- no unbounded worker/critic loop;
- no agent grading its own work;
- no majority vote that can override missing evidence;
- no automatic prompt, code, risk-envelope, or live-capital mutation;
- no hidden chain-of-thought requirement or storage;
- no uncontrolled fan-out across expensive providers;
- no agent-generated field accepted without deterministic provenance checks;
- no synthetic or fixture evidence in a current paper decision;
- no success claim based only on the agent's narrative report.

## 4. Constitutional Boundaries

Every phase must preserve all of the following:

- Alpaca Paper only;
- canonical `scripts/run_paperops_autonomous_pass.py` remains the only broker
  write route;
- live-capital authority remains false;
- agents never receive broker credentials;
- dashboard and Telegram remain command-disabled and review-only;
- research score remains neither profit probability nor execution authority;
- agent confidence remains neither evidence quality nor execution authority;
- critic approval remains neither Akber pass nor risk approval;
- Akber pass remains research eligibility, not order approval;
- shadow success remains non-order evidence and grants no proof credit;
- backtests, fixtures, simulations, and quantum jobs cannot advance the real
  paper calendar or the paper proof ledger;
- no forced trade and no daily quota;
- duplicate exposure, idempotency, current spread, liquidity, daily loss,
  drawdown, route, and broker reconciliation controls remain hard gates;
- the US$5,000 paper-order ceiling cannot expand automatically;
- self-healing may retry safe reads and deterministic compilation but cannot edit
  code, prompts, policies, secrets, authority, or risk limits;
- raw source content is untrusted data and cannot issue instructions to an
  agent;
- all unavailable evidence stays explicitly typed rather than fabricated.

## 5. Target Architecture

### 5.1 Canonical Flow

```text
Provider observations
  -> canonical evidence records
  -> AgentTaskPacket
  -> role-bounded worker output
  -> independent critic receipts
  -> AcceptedResearchPacket
  -> deterministic TradeabilityEnvelope compiler
  -> Akber's 6-Stage Filter
  -> decision-time forward shadow
  -> portfolio risk
  -> single-state Router
  -> canonical PaperOps handoff
  -> Alpaca Paper lifecycle
  -> outcome attribution and improvement proposal
```

### 5.2 Compiler Layers

| Layer | Responsibility | Authority |
| --- | --- | --- |
| Source loader | Selects immutable provider-backed records available by decision time | Read-only |
| Task compiler | Produces one bounded task packet for one agent role | No trade authority |
| Worker | Extracts, compares, challenges, or summarizes evidence | Proposal-only |
| Critics | Independently test explicit acceptance criteria | Reject/accept research output only |
| Research packet compiler | Normalizes accepted output and citations | No trade authority |
| Tradeability compiler | Builds one typed envelope from deterministic and accepted research fields | Workflow compilation only |
| Akber | Tests practical current tradeability | Eligibility only |
| Shadow | Records counterfactual current outcome | No-order observation |
| Risk | Applies sizing and portfolio constraints | Paper-risk decision only |
| Router | Assigns exactly one final state | Handoff eligibility only |
| PaperOps | Owns guarded Alpaca Paper submission | Sole paper broker-write actor |

### 5.3 One Canonical Tradeability Envelope

Create `TradeabilityEnvelope.v1` with the following required sections.

| Section | Required content |
| --- | --- |
| Identity | Envelope ID, candidate identity, research goal, strategy version, schema version |
| Generation | Decision generation ID, generated time, decision time, input hashes |
| Authority | Paper-only flags, all model/broker/live authority false |
| Provenance | Source event IDs, provider, observed time, available time, parser version, trust state |
| Pattern | Pattern ID, score ID, method, research score, directionality state, horizon |
| Strategy | Core refinement or emerging family, mechanism, falsifier, entry concept, exit concept |
| Direction | Long, short, or unresolved; resolution method and evidence references |
| Evidence profile | Event catalyst, regime state, market dislocation, or future reviewed profile |
| Current trigger | Trigger value, freshness, source independence, instrument relevance, expiry |
| Market context | Price, volatility, volume/flow, spread, liquidity, session, provider timestamps |
| Economics | Gross estimate, costs, net estimate, uncertainty, source method, validated/provisional label |
| Invalidation | Numeric or deterministic invalidation conditions and lifecycle response |
| Risk preconditions | Reward-to-risk, loss derivation inputs, cluster, notional ceiling, basis risk |
| Agent contributions | Accepted worker packet IDs and model/prompt/version hashes |
| Critic receipts | Required critic IDs, verdicts, rejection reasons, evaluated criteria |
| Completeness | Required fields, present fields, missing fields, unavailable fields, substitutions |
| Routing | Non-authoritative next stage, current blocker class, no-order state |

The envelope must use Pydantic v2 as its executable Python model and generate a
JSON Schema artifact. There must not be a hand-maintained schema and a separate
Python interpretation that can drift.

## 6. Agent Compilation Contract

### 6.1 AgentTaskPacket

Every agent call must begin from a typed task packet containing:

- task ID and task type;
- decision generation ID;
- objective and non-objectives;
- role and model capability class;
- immutable evidence references and hashes;
- explicit distinction between provider facts, Qadam inference, external claim,
  and prior hypothesis;
- allowed tools and source groups;
- required output schema and schema digest;
- quality predicates;
- required critics;
- retry and token budget;
- deadline and freshness deadline;
- stop conditions;
- forbidden actions;
- authority flags;
- prompt template version;
- compiler version;
- parent task and prior rejection references.

### 6.2 Compiled Prompt Package

Python must compile the task packet into a model-specific prompt package rather
than embedding free-form prompts throughout application code.

The compiled package must include:

1. role definition;
2. exact task;
3. trusted context manifest;
4. untrusted source-content boundary;
5. output schema;
6. acceptance predicates;
7. forbidden actions;
8. retry budget;
9. failure and escalation behavior;
10. authority statement.

Store prompt template hashes and compilation receipts, not hidden reasoning or
raw credentials. Public dashboard projections may show role, task, status, and
critic outcome but never raw private prompts or source payloads.

### 6.3 Role Specialization

| Role | Primary compiled job | Prohibited substitution |
| --- | --- | --- |
| Python COO | Select evidence, compile tasks, validate outputs, publish generations | Cannot invent evidence or override risk |
| Local Gemma Research Analyst | Extract entities, events, claims, uncertainty, and candidate relationships at volume | Cannot decide tradeability or size |
| Gemini Strategy Lead | Challenge mechanism, alternatives, falsifiers, and strategy mapping | Cannot fill missing provider fields |
| Head of Quant | Run declared classical, nonlinear, and quantum comparisons | Cannot turn method novelty into edge proof |
| Signal Auditor | Critique evidence independence, direction, timing, and invalidation | Cannot approve execution |
| Risk Agent | Deterministically evaluate policy and sizing inputs | LLM prose cannot override policy |
| Execution Auditor | Verify paper route, session, spread, liquidity, and reconciliation | Cannot submit an order |
| Fund Manager Interface | Explain outcomes and material escalations | Cannot create commands or authority |

## 7. Critic Gauntlet Design

Every agent output must be reviewed by critics selected from a typed registry.
The worker cannot serve as its own critic.

### 7.1 Required Critics

| Critic | Deterministic or model-assisted | Question |
| --- | --- | --- |
| Schema critic | Deterministic | Does the output exactly satisfy its declared schema? |
| Provenance critic | Deterministic | Do all factual fields resolve to immutable evidence available by decision time? |
| Temporal critic | Deterministic | Is there leakage, revised-data substitution, stale evidence, or generation mixing? |
| Capability critic | Deterministic | Could Qadam genuinely collect every required downstream field? |
| Evidence critic | Model-assisted plus deterministic checks | Are sources independent, relevant, and represented honestly? |
| Economic critic | Frontier model-assisted | Is there a plausible mechanism, horizon, falsifier, and alternative explanation? |
| Adversarial critic | Separate frontier call or deterministic challenger | What would make the relationship spurious, crowded, reversed, or non-tradeable? |
| Quant critic | Deterministic/classical/quantum as declared | Did the method outperform its fair baseline without leakage or false-discovery abuse? |
| Safety critic | Deterministic | Did the output request authority, credentials, orders, policy changes, or proof? |
| Integration critic | Deterministic | Can the accepted output compile into the canonical envelope without adapters guessing? |

### 7.2 Critic Rules

- Critics receive the output artifact, source references, schema, and acceptance
  predicates, not the worker's hidden reasoning.
- Every verdict is structured as `accept`, `revise`, `reject`, or
  `operator_action_required`.
- Every non-accept verdict names failed predicate IDs.
- No critic may add missing evidence on behalf of the worker.
- A model critic can identify a concern but deterministic critics decide schema,
  freshness, authority, and lineage validity.
- Maximum worker revisions default to two.
- Maximum model critic calls, tokens, latency, and cost are configured per task.
- Repeated identical failure ends the loop with a typed blocker.
- A provider outage pauses the task; it does not trigger speculative completion.
- A disagreement between model critics is preserved, not averaged away.
- The final accepted research packet records every critic receipt.

## 8. Evidence Capability Matrix

Create a machine-readable matrix joining every strategy evidence profile to the
fields required by the compiler and downstream gates.

Each row must contain:

- field ID;
- semantic definition;
- strategy/evidence profiles that require it;
- hard, soft, optional, or substitutable status;
- canonical producer;
- actual provider or deterministic calculation;
- current versus historical eligibility;
- freshness policy;
- market-session policy;
- accepted fallback;
- unavailable-state behavior;
- sample/fixture admissibility;
- provenance requirements;
- consumer stages;
- test fixture;
- current implementation status.

Compilation must fail before Akber when a hard field is structurally
uncollectable. That failure must be reported as a design defect, not a market
hold. A field that is temporarily unavailable from an otherwise supported
provider must remain a market/context hold.

## 9. Implementation Phases

The phases are intentionally modular. Each phase must update
`data/runtime/qadam_canonical_tradeability_compiler_plan_status.json` and append
to `docs/qadam-canonical-tradeability-compiler-implementation-log.md`. Later
phases must not start until the current phase's checker passes.

## CTC-0 - Freeze, Inventory, And Reproducible Baseline

### Objective

Freeze contract expansion and establish exactly which modules, artifacts,
agents, prompts, and schedulers are currently active.

### Build

- Freeze new Foundry, hypothesis, Akber, risk, Router, and PaperOps artifact
  variants until migration completes.
- Inventory every producer and consumer of strategy hypotheses and Akber fields.
- Inventory canonical, compatibility, QEG, QSASE, and legacy artifacts.
- Audit the duplicate `agents/* 2` directories and remove them only after proving
  they are redundant and unreferenced.
- Record all prompts embedded in Python and all prompt/agent files.
- Record active untracked runtime modules and scripts.
- Generate a producer-consumer graph and field-level contract-drift report.
- Snapshot current runtime truth without changing decisions or orders.
- Establish a clean implementation branch while preserving unrelated user work.

### Artifacts

- `data/runtime/qadam_tradeability_contract_inventory.json`
- `data/runtime/qadam_agent_prompt_inventory.json`
- `data/runtime/qadam_parallel_pipeline_audit.json`
- `data/runtime/qadam_release_reproducibility_baseline.json`
- `data/runtime/qadam_contract_field_drift_report.json`

### Checker

- `scripts/check_qadam_ctc0_baseline.py`

### Acceptance

- Every active artifact has exactly one declared producer.
- Every active consumer and field lookup is listed.
- Every untracked runtime module is identified.
- Duplicate agent directories are classified.
- No policy, prompt, threshold, order, or authority changes occur.

## CTC-1 - Constitutional Contract Hierarchy

### Objective

Create one hierarchy that agents and deterministic modules cannot reinterpret.

### Build

- Define precedence: constitutional safety -> canonical data contract -> agent
  task contract -> strategy profile -> prompt template -> runtime task.
- Extend the agent registry with task types, input schemas, output schemas,
  critic requirements, budgets, and escalation states.
- Mark source documents as normative, informative, historical, or deprecated.
- Define trusted instruction sources separately from untrusted market content.
- Fail compilation when instructions conflict with a higher-level contract.
- Preserve prompt and policy mutation as proposal-only.

### Artifacts

- `config/qadam_contract_hierarchy.json`
- `config/qadam_agent_task_registry.json`
- `data/runtime/qadam_contract_hierarchy_checks.json`
- `data/runtime/qadam_instruction_precedence_audit.json`

### Checker

- `scripts/check_qadam_contract_hierarchy.py`

### Acceptance

- Every task type resolves one role, schema, critic set, and authority boundary.
- Untrusted source text cannot override system instructions.
- A prompt cannot relax a constitutional or risk rule.
- Conflicts fail closed with exact source locations.

## CTC-2 - Canonical TradeabilityEnvelope V1

### Objective

Implement the one intermediate representation used from strategy formation to
PaperOps handoff.

### Build

- Add `orchestrator/qadam_tradeability_envelope.py` using Pydantic v2.
- Generate `schemas/qadam.tradeability-envelope.v1.schema.json` from the model.
- Use `extra="forbid"` so undeclared fields cannot silently enter the contract.
- Add typed enums for evidence state, direction, freshness, source independence,
  expectancy class, and blocker class.
- Require generation ID and input hashes.
- Require all authority flags and validate forbidden true states.
- Separate missing, unavailable, stale, adverse, not-applicable, and structurally
  uncollectable states.
- Add exact compatibility adapters for existing artifacts, but prevent adapters
  from inventing values.
- Register one canonical owner and canonical artifact.

### Artifacts

- `data/runtime/qadam_tradeability_envelopes.jsonl`
- `data/runtime/qadam_tradeability_envelope_registry.json`
- `data/runtime/qadam_tradeability_envelope_compatibility_audit.json`
- `data/runtime/qadam_tradeability_envelope_checks.json`

### Checker

- `scripts/check_qadam_tradeability_envelope.py`

### Acceptance

- Schema and Python model hashes match.
- Unknown fields are rejected.
- Missing and adverse evidence are not conflated.
- Fixture, future, stale, and live-capital probes fail.
- No envelope can create a trade, approval, handoff, or proof credit.

## CTC-3 - Provider And Strategy Capability Matrix

### Objective

Prove at compile time that each strategy asks only for evidence Qadam can
genuinely collect or explicitly classify.

### Build

- Generate the evidence capability matrix for all 41 registered sources, 19
  watched instruments, configured strategy families, emerging power sleeve, and
  future pattern-sourced strategies.
- Map every Akber, risk, and execution field to a producer and provider.
- Distinguish live, delayed, historical-only, forward-only, supplemental,
  unavailable, sample-only, and excluded capabilities.
- Encode profile-specific substitutions and their haircuts.
- Reject any strategy profile whose hard requirements are structurally
  impossible.
- Generate design-repair proposals rather than permanent market holds for
  impossible requirements.

### Artifacts

- `data/runtime/qadam_tradeability_capability_matrix.json`
- `data/runtime/qadam_strategy_collectability_audit.json`
- `data/runtime/qadam_uncollectable_requirement_repairs.jsonl`
- `data/runtime/qadam_capability_matrix_checks.json`

### Checker

- `scripts/check_qadam_tradeability_capability_matrix.py`

### Acceptance

- Every hard downstream field has one verified producer.
- Every unavailable field has one typed policy outcome.
- No strategy can be admitted with an impossible hard requirement.
- No provider availability is misrepresented as a market trigger.

## CTC-4 - Agent Task And Prompt Compiler

### Objective

Compile reproducible model tasks instead of maintaining ad hoc prompt strings.

### Build

- Add `orchestrator/qadam_agent_task_packet.py`.
- Add `orchestrator/qadam_agent_prompt_compiler.py`.
- Move active model prompts into versioned role/task templates under `agents/`.
- Extend each agent manifest with supported task types and output contracts.
- Replace generic `output.schema.json` use with task-specific schemas.
- Set `additionalProperties: false` unless a reviewed extension point is needed.
- Compile model-specific packages for Gemma and Gemini without changing their
  authority.
- Hash role, task, prompt, schema, evidence manifest, model, and compiler version.
- Store bounded receipts and parsed output, not raw secrets or chain of thought.
- Add deterministic fallback only when the task explicitly defines one.
- Treat parse fallback as degraded evidence, never equivalent live model output.

### Artifacts

- `data/runtime/qadam_agent_task_packets.jsonl`
- `data/runtime/qadam_compiled_prompt_receipts.jsonl`
- `data/runtime/qadam_agent_output_records.jsonl`
- `data/runtime/qadam_agent_compiler_checks.json`

### Checker

- `scripts/check_qadam_agent_prompt_compiler.py`

### Acceptance

- Identical task inputs produce identical prompt and schema hashes.
- Every output validates against the exact task schema.
- Unknown tools, sources, fields, and authority requests are rejected.
- Agent output cannot fill provider-owned fields without evidence references.
- Provider failure or parse failure remains visible and non-authoritative.

## CTC-5 - Independent Critic Gauntlet

### Objective

Apply the useful worker/critic loop without self-grading, unbounded cost, or
subjective financial conclusions.

### Build

- Add `orchestrator/qadam_agent_critic_gauntlet.py`.
- Register critic types and objective predicate IDs.
- Require deterministic critics for schema, provenance, temporal safety,
  capability, integration, and authority.
- Use separate model calls for economic and adversarial critique where useful.
- Prevent workers from seeing critic identity or modifying acceptance criteria.
- Cap revisions, tokens, provider calls, latency, and monetary cost.
- Persist all rejections and revisions.
- Stop repeated identical failures and emit one repair request.
- Separate critic acceptance from tradeability compilation and Akber state.

### Artifacts

- `data/runtime/qadam_agent_critic_receipts.jsonl`
- `data/runtime/qadam_agent_revision_ledger.jsonl`
- `data/runtime/qadam_agent_gauntlet_failures.jsonl`
- `data/runtime/qadam_agent_gauntlet_summary.json`
- `data/runtime/qadam_agent_gauntlet_checks.json`

### Checker

- `scripts/check_qadam_agent_critic_gauntlet.py`

### Acceptance

- A worker can never approve itself.
- Every accepted packet has all required critic receipts.
- Critics cannot invent evidence or authority.
- Retry and cost ceilings are enforced.
- Identical rejection loops terminate with a typed blocker.
- Negative and inconclusive results remain durable memory.

## CTC-6 - AcceptedResearchPacket Compiler

### Objective

Normalize accepted agent contributions before they can influence a strategy
hypothesis.

### Build

- Add a strict `AcceptedResearchPacket` model.
- Separate provider facts, extracted claims, Qadam inference, counterargument,
  falsifier, and uncertainty.
- Require evidence refs for every factual claim.
- Attach worker and critic receipts.
- Deduplicate semantically equivalent packets using evidence and task hashes.
- Preserve dissent rather than manufacturing consensus.
- Exclude rejected and degraded packets from tradeability compilation while
  retaining them for experiment memory.

### Artifacts

- `data/runtime/qadam_accepted_research_packets.jsonl`
- `data/runtime/qadam_rejected_research_packets.jsonl`
- `data/runtime/qadam_research_packet_deduplication.json`
- `data/runtime/qadam_research_packet_checks.json`

### Checker

- `scripts/check_qadam_accepted_research_packets.py`

### Acceptance

- Every accepted factual claim resolves to evidence.
- Every accepted inference is labelled as inference.
- Rejected packets cannot enter the envelope compiler.
- Duplicate packets do not amplify source quorum or confidence.

## CTC-7 - Producer Migration And Pipeline Consolidation

### Objective

Eliminate Foundry V3/V4 and canonical/QEG contract competition.

### Build

- Make Foundry and QEG produce canonical strategy drafts, not downstream-ready
  hypothesis variants.
- Make the tradeability compiler the sole envelope producer.
- Convert QEG graph records into evidence and memory inputs, not a second Akber
  lane.
- Run old and new readers in comparison-only mode.
- Generate field-by-field parity and semantic-difference reports.
- Prevent compatibility adapters from writing canonical artifacts.
- Deprecate QEG-specific hypothesis, packet, and Akber artifacts after parity.
- Remove legacy producers only after all consumers migrate.

### Artifacts

- `data/runtime/qadam_tradeability_migration_status.json`
- `data/runtime/qadam_legacy_contract_parity.json`
- `data/runtime/qadam_consumer_migration_audit.json`
- `data/runtime/qadam_deprecation_registry.json`

### Checker

- `scripts/check_qadam_tradeability_migration.py`

### Acceptance

- Exactly one active canonical envelope producer exists.
- QEG cannot create a second hypothesis or Akber source of truth.
- Every active consumer reads the envelope or a declared read-only projection.
- No legacy producer writes a canonical artifact.
- Parity differences are explained before cutover.

## CTC-8 - Atomic Same-Generation Decision DAG

### Objective

Make one transaction cover the complete evidence-to-Router decision path.

### Build

- Replace overlapping cadence joins with one explicit decision DAG.
- Require source, price, score, task, critic, envelope, Akber, shadow, risk, and
  Router artifacts to share one decision generation ID.
- Publish through a staging directory and atomic manifest swap.
- Prevent partial generations from becoming current.
- Make open-market conversion depend on the completed current research
  generation rather than an independent stale artifact set.
- Record every input hash and command receipt.
- Resume deterministically after interruption.
- Preserve canonical PaperOps as a separately guarded final action.

### Artifacts

- `data/runtime/qadam_decision_generation_manifest.json`
- `data/runtime/qadam_decision_generation_receipts.jsonl`
- `data/runtime/qadam_decision_generation_failures.jsonl`
- `data/runtime/qadam_decision_dag_checks.json`

### Checker

- `scripts/check_qadam_decision_generation.py`

### Acceptance

- Mixed-generation join count is zero.
- Partial generations are never current.
- Restarting the same generation is idempotent.
- A changed input creates a new generation.
- PaperOps sees only a completed Router generation.

## CTC-9 - Akber, Shadow, Risk, And Router Consumer Cutover

### Objective

Make every downstream gate consume one envelope without rediscovering fields.

### Build

- Refactor Akber to read typed envelope sections.
- Remove undocumented nested-field lookup fallbacks after migration.
- Make Akber missing-context reasons reference envelope field IDs.
- Create decision-time shadow directly from the accepted envelope and Akber
  receipt.
- Make risk consume envelope economics, invalidation, execution, and exposure
  fields without translating QEG variants.
- Make Router consume one Akber state, one shadow state, and one risk state.
- Preserve all current hard portfolio and route controls.
- Emit exactly one root blocker and separate propagated consequences.

### Artifacts

- `data/runtime/qadam_envelope_akber_decisions.jsonl`
- `data/runtime/qadam_envelope_shadow_decisions.jsonl`
- `data/runtime/qadam_envelope_risk_decisions.jsonl`
- `data/runtime/qadam_envelope_router_decisions.jsonl`
- `data/runtime/qadam_downstream_consumer_checks.json`

### Checker

- `scripts/check_qadam_tradeability_consumers.py`

### Acceptance

- No downstream consumer reads a legacy hypothesis directly.
- Every hold references a real field and state.
- Structurally uncollectable fields are code/design defects, not market holds.
- Missing evidence does not become adverse evidence.
- Router assigns exactly one final state.

## CTC-10 - Disk-Backed Golden Journeys

### Objective

Prove the scheduled producer chain, not isolated helper functions.

### Build

- Create disposable test state roots using the real scripts and artifact names.
- Add a valid-pass journey that reaches a broker-disabled PaperOps handoff.
- Add missing-context hold, inactive-trigger watchlist, adverse-evidence veto,
  duplicate-exposure rejection, closed-market hold, stale-provider hold,
  direction-unresolved hold, parse-failure rejection, and mixed-generation
  rejection journeys.
- Use provider-shaped fixtures only at the external boundary.
- Require all internal artifacts to be produced by real modules.
- Assert every generation ID, source ref, receipt, and final state.

### Artifacts

- `tests/fixtures/qadam_tradeability_journeys/`
- `data/runtime/qadam_tradeability_golden_journeys.json`
- `data/runtime/qadam_tradeability_golden_journey_checks.json`

### Checker

- `scripts/check_qadam_tradeability_golden_journeys.py`

### Acceptance

- The pass journey reaches an accepted broker-disabled handoff.
- Every negative journey fails at its intended stage.
- Tests do not hand-author internal downstream artifacts.
- No journey creates an order, broker write, proof credit, or live authority.

## CTC-11 - Tradeability Reachability Canary And Honest Empty States

### Objective

Separate operational health from proof that the full tradeability path works.

### Build

- Add a signed, test-namespace, broker-disabled canary envelope.
- Run it through Akber, shadow, risk, Router, and PaperOps handoff validation.
- Prevent canary records from entering production ledgers, orders, proof, or the
  paper calendar.
- Report `not_exercised`, `reachable`, `blocked_contract`, or
  `blocked_operational` separately.
- Prevent a checker from claiming tradeability passed when zero hypotheses were
  exercised.
- Keep legitimate `no_current_trigger` as healthy idle, but label reachability
  separately.

### Artifacts

- `data/runtime/qadam_tradeability_reachability_canary.json`
- `data/runtime/qadam_tradeability_reachability_history.jsonl`
- `data/runtime/qadam_tradeability_reachability_checks.json`

### Checker

- `scripts/check_qadam_tradeability_reachability.py`

### Acceptance

- `ready_idle` cannot imply reachability by itself.
- A zero-input run is explicitly `not_exercised`.
- A canary reaches a handoff without creating an order.
- Canary lineage cannot collide with real candidate identity or idempotency.

## CTC-12 - Defect Classification And Bounded Self-Healing

### Objective

Make contract failures visible engineering incidents instead of recurring market
holds.

### Build

- Add `contract_schema_drift`, `producer_field_omission`,
  `consumer_undocumented_requirement`, `mixed_generation`,
  `prompt_compile_failure`, `critic_contract_failure`, and
  `capability_matrix_mismatch` defect classes.
- Open the relevant service circuit on structural contract defects.
- Generate one deduplicated repair request containing producer, consumer, field,
  schema versions, and generation IDs.
- Permit automatic retry only for transient provider reads, lock contention, and
  deterministic incomplete writes.
- Prohibit self-healing from changing schemas, prompts, code, thresholds, or
  authority.
- Close a circuit only after the real integration probe passes on the same build.

### Artifacts

- `data/runtime/qadam_contract_defects.jsonl`
- `data/runtime/qadam_contract_repair_requests.jsonl`
- `data/runtime/qadam_contract_defect_summary.json`
- `data/runtime/qadam_contract_self_healing_checks.json`

### Checker

- `scripts/check_qadam_contract_defect_handling.py`

### Acceptance

- Contract defects cannot appear as ordinary Akber market holds.
- Repeated identical defects create one repair request.
- Unsafe mutation probes fail.
- Circuit closure requires real same-build revalidation.

## CTC-13 - Observability, Dashboard, And Communications

### Objective

Explain the compiler and conversion funnel without changing protected dashboard
structure or creating authority.

### Build

- Preserve all existing dashboard routes, sidebar order, and established UX.
- Add read-only enrichment to existing Pattern Recognition, Trading Strategies,
  Decision Room, Order Monitor, and System surfaces.
- Show operational health separately from tradeability reachability.
- Show task status, worker role, critic verdicts, envelope completeness, first
  blocker, next action, and generation freshness.
- Show the funnel: observations -> tasks -> accepted research packets ->
  envelopes -> Akber entries -> passes -> shadows -> risk proposals -> handoffs
  -> orders.
- Explain `no current setup`, `contract defect`, `market hold`, and `risk veto`
  in distinct language.
- Never expose raw prompts, chain of thought, private source payloads, local
  paths, credentials, or canary records.
- Telegram may mention a materially changed hypothesis or blocker but cannot
  create tasks, approvals, envelopes, candidates, or orders.

### Artifacts

- `data/runtime/qadam_tradeability_compiler_dashboard_summary.json`
- `data/runtime/qadam_agent_gauntlet_dashboard_summary.json`
- `data/runtime/qadam_tradeability_funnel.json`
- `data/runtime/qadam_tradeability_public_safety_audit.json`

### Checkers

- `scripts/check_dashboard_tradeability_compiler.js`
- `scripts/check_qadam_tradeability_public_safety.py`

### Acceptance

- Existing dashboard structure is unchanged.
- Operational health and tradeability reachability are visibly distinct.
- Counts reconcile with canonical artifacts.
- No private prompt or authority-bearing control is exposed.
- Telegram remains concise, material-change-only, and command-disabled.

## CTC-14 - Clean Release, Soak, And Legacy Removal

### Objective

Make the repaired architecture reproducible and prove it survives real runtime
conditions.

### Build

- Commit every active runtime module, script, schema, prompt template, and test.
- Exclude mutable bulk runtime data from Git while retaining canonical schemas
  and fixtures.
- Require a clean release worktree and certified commit.
- Restart the installed operator from that commit.
- Verify running and current build identities match.
- Run all unit, contract, golden-journey, negative-safety, operator, dashboard,
  and PaperOps checks.
- Complete five consecutive real market sessions without contract-shape defects.
- Require at least one successful broker-disabled reachability canary per build.
- Compare real setups against legacy outputs during the soak.
- Remove deprecated producers and artifacts only after parity and rollback
  readiness are proven.
- Preserve a rollback tag and migration manifest.

### Artifacts

- `data/runtime/qadam_canonical_tradeability_compiler_certification.json`
- `data/runtime/qadam_tradeability_soak_status.json`
- `data/runtime/qadam_tradeability_release_manifest.json`
- `data/runtime/qadam_legacy_removal_audit.json`

### Checker

- `scripts/check_qadam_canonical_tradeability_compiler.py`

### Acceptance

- Running build equals one clean committed release.
- Active untracked runtime-code count is zero.
- Exactly one canonical envelope producer exists.
- Golden journeys and reachability canary pass.
- Five real market sessions have zero contract-shape defects.
- No safety, authority, proof, or live-capital probe succeeds.
- Legacy producers are removed or explicitly read-only with expiry dates.

## 10. Testing Strategy

### 10.1 Unit Tests

- Pydantic model and JSON Schema parity.
- Unknown-field rejection.
- Enum and state-transition validation.
- Prompt compilation determinism.
- Agent tool/source allowlists.
- Critic independence and retry limits.
- Capability matrix resolution.
- Evidence state semantics.
- Input hash and generation ID stability.

### 10.2 Contract Tests

- Every producer emits a valid declared contract.
- Every consumer accepts the canonical envelope and rejects legacy variants.
- Every required field has a capability-matrix row.
- Every agent output is task-schema-specific.
- Every accepted packet has required critics.
- No compatibility adapter invents values.

### 10.3 Integration Tests

- Real script-to-script disk-backed journeys.
- Same-generation atomic publication.
- Interrupted compile resume.
- Provider timeout and stale evidence.
- Model unavailable and parse failure.
- Critic disagreement.
- Market closed and session transition.
- Router and PaperOps broker-disabled handoff.

### 10.4 Negative Safety Tests

- Prompt injection in source text.
- Agent requests broker tools.
- Critic requests policy mutation.
- Unknown schema field.
- Future evidence timestamp.
- Fixture presented as current evidence.
- Duplicate source presented as independent quorum.
- Canary presented as a real setup.
- QEG tries to write a second canonical hypothesis.
- Dashboard or Telegram tries to create authority.
- Live broker endpoint or live-capital flag.
- Proof credit from backtest, shadow, or canary.

### 10.5 Mutation Tests

Deliberately remove or rename each critical field in turn and prove that:

- the producer test fails;
- the integration critic fails;
- the defect is classified as code/schema drift;
- the service circuit opens;
- the failure is not reported as a market hold;
- no downstream handoff is produced.

## 11. Operational Metrics And Service-Level Objectives

Track at minimum:

- task compilation success rate;
- output schema failure rate;
- critic rejection and revision rates;
- identical-loop termination count;
- model/provider cost and latency per accepted packet;
- envelope compilation success rate;
- structurally uncollectable field count;
- mixed-generation count;
- contract-defect count;
- current market-hold count;
- Akber entry and pass rates;
- shadow creation rate;
- risk proposal rate;
- Router handoff rate;
- broker-disabled reachability result;
- real PaperOps order count;
- outcome maturation and attribution rate.

Initial SLOs:

- 100% of active agent tasks have versioned task and output schemas;
- 100% of accepted research packets have complete critic receipts;
- 100% of envelopes have generation and input hashes;
- 0 mixed-generation joins;
- 0 active unknown contract fields;
- 0 contract defects misclassified as market holds;
- 0 active untracked runtime modules in a release;
- 100% broker-disabled reachability success on certified builds;
- 0 unauthorized broker writes, live-capital flags, or proof credits.

Trade frequency is deliberately not an SLO. The correct conversion SLO is that
every complete, distinct, current, low-risk setup is evaluated within one market
decision cycle and is not lost to infrastructure mismatch.

## 12. Migration And Rollback Policy

Migration order:

1. Inventory without behavior change.
2. Add canonical models and validators.
3. Add capability matrix.
4. Add agent compiler and critics in shadow mode.
5. Compile envelopes in comparison-only mode.
6. Compare canonical and legacy outputs.
7. Cut Akber to canonical envelope input.
8. Cut shadow, risk, and Router to canonical input.
9. Enable broker-disabled canary.
10. Complete soak.
11. Remove legacy writers.

Rollback must restore the previous certified paper-only release and preserve all
new records as non-authoritative audit history. Rollback cannot reactivate a
legacy producer that writes the new canonical artifact.

## 13. Definition Of Done

The implementation is complete only when all of the following are true:

1. One typed `TradeabilityEnvelope` is the sole contract between strategy
   formation and downstream decision gates.
2. Exactly one canonical producer owns that envelope.
3. Foundry V3/V4 and QEG no longer create competing downstream hypothesis or
   Akber sources of truth.
4. Every hard envelope field maps to a verified producer and provider policy.
5. Every active agent task is compiled from a versioned manifest and schema.
6. Every accepted agent output has independent required critic receipts.
7. Prompt injection, undeclared tools, unknown fields, and authority requests
   fail closed.
8. All decision artifacts in one cycle share one generation ID and input hashes.
9. A disk-backed valid journey reaches a broker-disabled PaperOps handoff.
10. Hold, watchlist, veto, duplicate, stale, closed-market, and mixed-generation
    journeys fail at the correct stages.
11. A zero-setup run cannot be reported as proof of tradeability reachability.
12. Contract mismatch opens an engineering circuit and repair request rather
    than appearing as an ordinary Akber hold.
13. Operational health, tradeability reachability, and current setup state are
    reported separately.
14. The dashboard retains its current structure and remains read-only.
15. Telegram remains material-change-only, concise, and command-disabled.
16. All live-capital, broker-bypass, proof-credit, prompt-mutation, and
    policy-mutation probes fail.
17. The installed operator runs from a clean committed release.
18. Active untracked runtime-code count is zero.
19. Five consecutive real market sessions complete with zero contract-shape
    defects.
20. The canonical certification checker passes without waivers.

## 14. Recommended Execution Sequence

Implement in these bounded waves:

| Wave | Phases | Outcome |
| --- | --- | --- |
| 1 | CTC-0 to CTC-2 | Frozen baseline and canonical envelope |
| 2 | CTC-3 to CTC-6 | Capability-aware agent compiler and critics |
| 3 | CTC-7 to CTC-9 | One producer and one downstream decision path |
| 4 | CTC-10 to CTC-12 | Real-artifact proof, reachability, and defect handling |
| 5 | CTC-13 to CTC-14 | Public visibility, clean release, soak, and legacy removal |

Each wave must stop if its end checker fails. A blocker report must name the
failed artifact, producer, consumer, field, schema version, and safe next action.
The implementation must never lower acceptance criteria merely to complete the
roadmap.

## 15. Final Thesis

Qadam's models should not pass loosely worded opinions from one agent to another.
They should produce bounded, critic-reviewed research artifacts that Python can
compile into one explicit intermediate representation.

This is the durable lesson from the recurring Akber/Foundry failures:

> Reliable autonomy comes from making every handoff typed, attributable,
> generation-consistent, independently tested, and reproducible. Better prompts
> improve the research inside the handoff; they do not replace the contract.

When this plan is complete, a future model, pattern engine, quantum method, or
strategy family can be added without silently reopening the same failure class.
It must either compile against the contract, declare a reviewed extension, or be
rejected before it can distort Qadam's tradeability state.
