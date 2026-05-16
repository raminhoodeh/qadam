# Qadam Modular Implementation Plan

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

This is the modular appendix for contracts and module boundaries. For day-to-day sequencing, use `docs/qadam-master-implementation-plan.md`.

## Source Documents

This plan is based on four planning inputs:

- `specs/qadam-specs.md` - canonical product, architecture, roadmap, cockpit, metrics, and operating doctrine.
- `specs/qadam-general-context.md` - strategy philosophy, build principles, resource references, analytical frameworks, product positioning, and proof-of-concept inspiration.
- `docs/api-source-inventory.md` - live/source-adjacent API feed inventory and known source conflicts.
- `docs/qadam-resource-registry.md` - non-live resources, papers, open-source stacks, product benchmarks, and module-mapping references.
- `how-the-world-works/` - private foundational world-model corpus for Qadam's esoteric edge, hidden-incentive maps, narrative frames, and adversarial scenario generation. Currently 4 markdown files.

Supporting technical specs:

- `specs/Qadam — World Monitor Integration Reference.md`
- `specs/Qadam — Quantum Circuit Technical Spec.md`
- `specs/Qadam — Glossary.md`

## Modular Build Doctrine

Build Qadam as replaceable modules around stable contracts.

- First release is local-first: canonical saved state stays on Ramin's MacBook.
- First release trades autonomously only in a £1000 paper/test account after gates are met.
- Event Log first: every module emits events before it is considered real.
- Health first: every module exposes status, heartbeat, latency, and degraded-state.
- Read-only first: every data, LLM, quantum, and market module starts without execution authority.
- Contracts before intelligence: schemas, adapters, and replay tests come before model output.
- Registry separation: live data feeds stay in the source registry; strategy/build references stay in the resource registry.
- Private worldview prior: `how-the-world-works/` quietly shapes Qadam's suspicion, scenario generation, and hidden-incentive reasoning.
- Layer A surfaces; Layer B acts.
- Fail closed: stale data, missing secrets, model failure, quantum delay, or broker uncertainty should degrade or block, not silently continue.
- No direct UI-to-broker path: cockpit actions go through Orchestrator policy gates and Event Log writes.
- No LLM-to-broker path: LLMs propose, summarize, and challenge; deterministic policy code decides whether anything can act.
- Agent manifests before agent autonomy: every agent declares role, tool grants, data access, output schema, and forbidden actions before it can run.
- No venue writes before read-only proof: health, permissions, positions, balances, market metadata, and venue limits must be observable before `place_order()` can exist.
- No automatic retry for order-creating POST calls.

## Module Map

| Module Group | Primary Owner | Purpose | First Build Phase |
| --- | --- | --- | --- |
| Control Plane | Python COO / Orchestrator | Routing, health, scheduling, module state, process supervision | Phase 0 |
| Audit Plane | Event Log | Append-only truth, replay, trade/system audit | Phase 0 |
| Knowledge Plane | ChromaDB Knowledge Graph | Catalyst memory, embeddings, nearest-neighbour recall | Phase 0 shell, Phase 6 live |
| Cockpit Plane | Next.js + Clerk | Login, System Map, health, signals, postmortems, settings | Phase 0 shell, Phase 5 functional |
| Fund Manager Forum | Cockpit + Event Log | Private suggestions and governance comments from Ramin, Troy, Akber, Anas, and Ion | Phase 0 stub, Phase 5 functional |
| Live Ingress Plane | World Monitor source adapters | 35 live/live-adjacent feeds across 5 pipelines | Phase 1 |
| Resource Plane | Resource Registry | Strategy references, papers, OSS stacks, product benchmarks, provenance | Phase 0 |
| World-Model Plane | How The World Works corpus | Private foundational lens, esoteric edge, hidden-incentive hypotheses, narrative lenses, scenario trees | Phase 0 seed, Phase 2 reasoning |
| Agent OS Plane | Agent manifests + skill bundles | Named Qadam roles, reusable skills, explicit tool/data permissions, validation, and sync | Phase 1E |
| Tool Plane | FastMCP-style tools | Uniform tool interface for sources, health, modules, and later actions | Phase 0 |
| Intelligence Plane | Gemma + Gemini + swarm | Triage, research, evidence trails, proposed signals | Phase 2 |
| Quant Plane | Classical + Qiskit + Q-CTRL + IBM/Braket | Weekly oracle, pattern recognition, strategy collapse, optional optimization/error suppression | Phase 3 |
| Strategy Plane | Manifestation process | Audits, data environment map, approved strategy document | Phase 4 |
| Risk Plane | Risk Agent + policy router | Position sizing, guardrails, kill-switches, approval policy | Phase 5 |
| Execution Registry | Python COO / Risk Agent | Disabled/read-only venue map, credential state, account/subaccount scope, network/chain scope, venue mode, kill-switch state | Phase 0 |
| Execution Plane | Broker/exchange adapters | Alpaca paper/live, prediction-market routing, later PriveX-style perps rails if approved | Phase 5 |
| Learning Plane | Postmortems + Bayesian updates + Architect Agent | Learning loop, Trust Score updates, strategy review | Phase 6 |
| Proof Plane | Demo proof harness | 90-day autonomous paper run and 100-trade maturity benchmark | Phase 7 |

## Contract-First Interfaces

Each module should be replaceable if it obeys its contract.

| Contract | Minimum Interface | Must Emit |
| --- | --- | --- |
| `EventWriter` | `append_event(event)`, `replay(query)` | write success/failure, schema version |
| `HealthProvider` | `status()`, `heartbeat()`, `degraded_reason()` | uptime, latency, last heartbeat |
| `SourceAdapter` | `fetch()`, `normalize()`, `heartbeat()` | raw payload, normalized event, source SLA |
| `ResourceRegistry` | `list_resources()`, `map_to_module()` | provenance mapping, validation status |
| `WorldModelCorpus` | `extract_claims()`, `map_claim_to_observables()`, `score_after_outcome()` | claim card, corroboration status, falsification result |
| `AgentManifest` | `role`, `scope`, `allowed_tools`, `allowed_sources`, `allowed_skills`, `forbidden_actions`, `output_schema` | manifest validation result, permission map, escalation boundary |
| `SkillBundle` | reusable markdown instructions plus tests/examples | source bundle, synced agent copies, dependency map |
| `MCPTool` | typed request/response | call started, call completed, call failed |
| `TriageModel` | `triage(event_batch)` | confidence, uncertainty, dropped reason |
| `ResearchModel` | `research(candidate)` | evidence trail, assumptions, citations, risk flags |
| `QuantumBackend` | `simulate(job)`, `submit(job)`, `fallback(job)` | job status, fidelity, queue delay, fallback status |
| `SecretProvider` | `status(key)`, `value(key)` for runtime-only callers | configured/missing only in health; never raw values |
| `SignalAssembler` | `assemble(candidate)` | proposed signal, invalidation, pricing gap |
| `RiskAgent` | `evaluate(signal, portfolio)` | allow/block, size, cap reason, kill-switch state |
| `ExecutionVenue` | `health()`, `status()`, `permissions()`, `positions()`, `limits()` | venue mode, credential state, account/subaccount scope, chain/network, reconciliation status |
| `BrokerAdapter` | `quote()`, `place_order()`, `cancel()`, `positions()` | order state, fill state, broker error; POST writes are never auto-retried |
| `PostmortemAgent` | `analyze(closed_trade)` | outcome, attribution, lessons, updates |

## Phase 0 - Foundations

Objective: build the nervous system. No real ingestion, no inference, no trading.

Trading state: none.

### Phase 0 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Repository contract | Runtime versions, folder layout, `.env.example`, startup script | Fresh start command verifies foundation |
| Event Log | Postgres/Timescale schema v1, migration runner, local JSONL fallback, append-only events, replay test | Test event writes and replays identically without Docker |
| Local storage contract | Data directories for raw payloads, Event Log persistence, Chroma, runtime files, model/cache data | Paths exist and permissions are checked |
| Config and secrets | Strict local file and future Keychain abstraction | Secret files with weak permissions are rejected |
| Quantum provider registry | Local simulator, Q-CTRL, IBM, Braket credential status | Q-CTRL can be configured without Phase 0 API calls |
| Health API | Orchestrator health JSON with module states | Health reports uptime and degraded reasons |
| FastMCP scaffold | `ticker_echo`, `source_registry`, `source_detail`, `system_health`, `module_map` | Tools return typed responses |
| Source registry | 35 live ingress sources, tiers, SLA placeholders | Registry count and pipeline counts pass |
| Resource registry | Strategy/resource references from `qadam-general-context.md` | Resources are mapped to future modules |
| World-model corpus | Register `how-the-world-works/` as Qadam's private esoteric edge foundation | Claims become structured priors, not direct evidence |
| Execution registry | Disabled/read-only venue map shaped by PriveX Starter lessons | All venues visible; no order path exists |
| Chroma shell | Empty Knowledge Graph initialization | Chroma starts and reports healthy |
| Cockpit shell | Landing/auth/dashboard route plan, System Map shell | Login path and protected dashboard are defined |
| Fund Manager allowlist | Ramin, Troy, Akber, Anas, Ion only | Non-allowlisted users cannot access cockpit |
| Comments/forum stub | Local governance notes linked to modules/signals/strategies | Notes can be saved locally |
| Vercel link | Existing `qadam.trade` project linked read-only | Project inspection succeeds without deploy |
| Observability shell | Structured logs, Sentry no-op, web-vitals endpoint placeholder | Missing optional observability keys do not crash |

### Phase 0 Build Order

1. Event Log schema, local fallback, and replay contract.
2. Local storage contract for 1TB SSD operation.
3. Local store health for Postgres/Timescale and Chroma degraded states.
4. Config/secrets loader.
5. Orchestrator health and module registry.
6. Source registry and resource registry endpoints.
7. World-model corpus registry and claim-card schema.
8. Execution registry with disabled Alpaca paper and optional PriveX-style venue placeholders.
9. FastMCP tools over those endpoints.
10. Cockpit System Map shell.
11. Clerk route plan: top-right Login, `/login` or `/sign-in`, protected `/dashboard`, founding Fund Manager allowlist.
12. Comments/forum stub.
13. Vercel deployment guardrails.
14. One-command foundation verification.

### Phase 0 Gate

Phase 0 is done when:

- `qadam.trade` production routing plan is explicit and does not accidentally overwrite the landing page.
- Local cockpit has a System Map shell with module placeholders.
- Event Log accepts and replays a test event through the local fallback.
- Timescale migration exists for durable Postgres storage.
- Local storage paths are created for all canonical saved state.
- Source registry and Resource Registry are separate and visible in docs.
- How The World Works is registered as Qadam's private world-model foundation, with a hard evidence boundary before trading.
- Cockpit access is limited to the five founding Fund Managers.
- Comments/forum notes can be saved locally.
- Health API reports module status and degraded states.
- No real secret is committed.
- No source ingestion, LLM inference, quantum call, or trade exists yet.

Current implementation note:

- Resource Registry, world-model claim cards, and local governance comments now have Python modules, local checks, migration stubs, MCP-style tools, and cockpit visibility.

## Phase 1 - Data Spine And Ingestion

Current implementation start:

- The Phase 1 spine can emit deterministic test observations for registered sources without live network calls.
- Test observations are local-only and write Event Log entries.
- This proves the adapter contract before API credentials and live rate limits are introduced.
- Source heartbeat now classifies all 35 sources into promoted, derived, deferred, missing credentials, local bridge, fallback-only, ready-to-build, or ready-to-port states.
- `data/runtime/data_environment_map.json` is generated locally and remains ignored by Git.
- GDELT now has the first real read-only adapter path with raw archive, normalized events, Event Log entries, and degraded-state handling.
- Oref now has the second read-only adapter path, including healthy empty-alert handling and degraded-state handling for timeout, HTML, or parse failure.
- NASA FIRMS now has the first physical read-only adapter path, including bbox-first area requests, credential-gated live mode, high-confidence thermal anomaly filtering, raw archive, and degraded-state handling.
- FRED now has the first macro read-only adapter path, including rate/dollar/volatility/credit/crude series, public CSV fallback, sigma calculation, raw archive, and degraded-state handling.
- RSS now has the first narrative read-only adapter path, including feed validation, keyword filtering, raw archive, normalized headline events, and degraded-state handling.
- Local Python 3.12 dependencies are bootstrapped in `.venv`.
- Embedded Chroma initializes the empty Knowledge Graph locally.
- Postgres/Timescale durable writes are coded and waiting on a Docker-compatible runtime.

Objective: populate the canonical store with live and historical data.

Trading state: none.

### Phase 1 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Adapter base | Shared async `SourceAdapter` interface | Fake adapter writes normalized event |
| Raw archive | Store raw payloads before normalization | Raw payload can be replayed |
| Normalized event writer | Unified event schema for all sources | Event validates against schema |
| Heartbeat monitor | Source SLA, last success, latency, degraded status | Simulated stale source appears degraded |
| Tier 1 adapters | ACLED, Oref, NASA FIRMS, UnusualWhales, Polymarket, Kalshi, Alpaca | Each writes sample event or intentional unavailable state |
| Tier 2 adapters | FRED, AIS, Wingbits, GDELT, RSS, X | Each has heartbeat and rate-limit behavior |
| Tier 3 adapters | BLS, ECB, UN Comtrade, BIS, USGS, Reddit, Telegram, SEC, STOCK Act | Conflicts are resolved or marked deferred |
| Tier 4 adapters | UCDP, ArcGIS/USACE, Space-Track/CelesTrak, GPSJam, IODA, Coinglass, Bookmap, Chainlink, Hyperliquid, GitHub, Patents, RapidAPI | Later feeds can be added without schema changes |
| Trust seed | Initial Trust Score structure | Source < 0.3 quarantine path exists |
| Data environment map | Human-readable source status and tiering | Ramin can review source quality before Phase 2 |
| Local retention policy | Storage sizing, compaction, and backup rules for 1TB SSD | Saved data stays local and bounded |

### Phase 1 Build Order

1. Adapter interface and schema tests.
2. Raw payload archive.
3. Normalized event writer.
4. Heartbeat and SLA monitor.
5. Tier 1 adapters in read-only mode.
6. Tier 2 adapters.
7. Tier 3 and conflict-resolution adapters.
8. Tier 4 deferred/fallback adapters.
9. Historical backfill where licensing allows.
10. Initial Trust Score table.
11. `data_environment_map.json`.

### Phase 1 Gate

Phase 1 is done when:

- All 35 sources have `live`, `degraded`, `unavailable`, or `deferred` status.
- Tier 1 sources are ingesting or intentionally blocked with clear credential/licensing reasons.
- Every source has heartbeat visibility in the cockpit plan.
- Raw and normalized data can be replayed.
- Trust Score seed data exists.
- Degraded mode is visible and logged.
- Canonical saved data remains local.

## Phase 1E - Agent And Skill Manifests

Objective: formalize Qadam's named agents before model autonomy expands.

Current implementation start:

- Agent registry, skill bundles, manifest validation, explicit tool grants, and cockpit/system-health status exist.
- Eight named agents validate locally.
- Seven reusable skill bundles validate locally.
- Current validation reports 85 tool grants and 13 secret-name grants, all names only.

Reference pattern:

- Anthropic's `financial-services` repo is a useful architecture reference because it separates named financial agents, reusable vertical skills, connector grants, managed-agent cookbooks, manifest checks, and secret scanning.
- Qadam adopts the structure and safety pattern, not Anthropic's licensed data connectors or human-signoff-only operating model.

Trading state: none. This phase creates permissions and manifests; it does not create execution.

### Phase 1E Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Agent registry | `agents/` folders for COO, Research Analyst, Strategy Lead, Head of Quant, Risk Agent, Signal Auditor, Execution Auditor, Fund Manager Interface | Registry count and ownership map validate |
| Skill bundles | `skills/` folders for macro, prediction markets, physical anomalies, options/volatility, Akber filter, private edge, risk/postmortems | Skill references resolve deterministically |
| Tool grants | Per-agent allowed MCP tools, source groups, resources, and secrets-by-name | No agent has undeclared tool access |
| Output schemas | Typed outputs for triage, research packet, signal audit, risk decision, execution audit, forum response | Sample outputs validate |
| Manifest checker | Local script validates manifests, bundle references, forbidden actions, and secret leakage | Check fails on undeclared connector or raw key |
| Cockpit ownership map | System Map can show which agent owns each module and permission boundary | Agent/module map renders from health contract |

### Phase 1E Build Order

1. Define manifest schema.
2. Add the eight initial agent manifests.
3. Add reusable skill bundle folders.
4. Add sync/check scripts.
5. Map existing MCP tools to explicit agent grants.
6. Add forbidden-action checks: no shell, no web fetch, no broker write, no undeclared connector unless explicitly granted.
7. Add cockpit health surface for agent ownership and permission status.

### Phase 1E Gate

Phase 1E is done when:

- Every named agent has a validated manifest.
- Every reusable skill has one source of truth and synced agent references.
- Every tool grant is explicit.
- Live-capital action requires future human signoff.
- Paper-account autonomy remains possible only through deterministic Risk Agent and execution-policy gates, not direct LLM authority.

## Phase 2 - Intelligence Stack In Shadow Mode

Objective: generate proposed signals without showing them as trade recommendations and without execution.

Trading state: Layer A shadow only.

### Phase 2 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Gemma local triage | Local event compression, ranking, discard reasons | Batch triage completes under latency budget |
| Gemini research | Frontier LLM research packet generation | Research packets include evidence and assumptions |
| Evidence Trail | Structured evidence object linked to source events | Evidence can be traced back to raw payloads |
| Swarm simulation | 100-persona or smaller starter simulation | Output includes disagreement and uncertainty |
| Prediction-market probability layer | Compare estimated probability vs Polymarket/Kalshi pricing | Pricing gap report generated read-only |
| Options mispricing layer | Black-Scholes gap report for options candidates | IV/tail-mass assumptions logged |
| Signal assembler | Proposed Signal schema v1 | Proposed signal writes to store but does not execute |
| Signal integrity gate | Akber 6-Step Filter and anti-hype checks | Bad signals are blocked with explicit reason |
| Resource provenance | Link analytical frameworks to signal packet | Signal shows which frameworks informed analysis |
| World-model lens | Convert private esoteric frames into falsifiable scenario prompts | Lens output is marked worldview/prior until corroborated |

### Phase 2 Build Order

1. Proposed Signal schema.
2. Evidence Trail schema.
3. Gemma triage over Phase 1 events.
4. Gemini research packets.
5. Signal integrity gate.
6. Prediction-market pricing-gap module.
7. Options mispricing module.
8. Swarm simulation starter.
9. World-model lens over candidates.
10. Shadow signal store.
11. Cockpit-hidden review page for debugging only.

### Phase 2 Gate

Phase 2 is done when:

- Full Layer A flow produces Proposed Signal objects.
- Every Proposed Signal has evidence, assumptions, invalidation, costs/slippage, source Trust Scores, and pricing gap.
- Signals are not executable.
- LLM failures create `pending-research` or `degraded`, not fake confidence.
- Resource Registry provenance appears in signal metadata.
- World-model lens is foundational to how Qadam asks questions, but never counts as factual evidence without live-source corroboration.

## Phase 3 - Quantum Integration

Objective: connect the weekly quantum oracle with simulation, hardware, and classical fallback.

Trading state: Layer A shadow.

### Phase 3 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Quantum job schema | Versioned input/output schemas | Jobs validate before simulation |
| Local simulator | Qiskit Aer validation | Failed simulation blocks hardware submission |
| Classical fallback | scipy/cvxpy/scikit-learn equivalent output | Same schema as quantum output |
| IBM backend | Qiskit Runtime adapter | Job can submit or report quota/queue degraded |
| AWS Braket backend | Secondary adapter | Same `QuantumBackend` interface |
| Job 1 Pattern Recognition | Co-occurrence across 3+ sources | Pattern clusters written to Event Log |
| Job 2 Strategy Collapse | Options/strategy ambiguity scoring | Quantum Ambiguity Score produced |
| Cockpit status | Last run, next run, backend, fallback state | Quantum status visible in System Health |

### Phase 3 Build Order

1. `QuantumBackend` interface.
2. Job schema and fixtures.
3. Local Qiskit Aer validation.
4. Classical fallback implementation.
5. IBM Qiskit Runtime adapter.
6. AWS Braket adapter.
7. Job 1 and Job 2 runners.
8. Weekly scheduler.
9. Quantum cockpit status.

### Phase 3 Gate

Phase 3 is done when:

- Every quantum job runs locally before hardware.
- Hardware failures produce `classical-fallback`.
- Quantum output can upgrade, downgrade, or hold a signal.
- Quantum cannot originate a signal, bypass the 6-Step Filter, or bypass the Risk Agent.
- Google is recorded as Gemini-only unless public hardware access changes.

## Phase 4 - Phase 1 Manifestation

Objective: convert observed data quality, model behavior, and strategy hypotheses into an approved Manifested Strategy Document.

Trading state: shadow.

### Phase 4 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Triple-Mirror Audit | Compare spec, context resources, and observed system behavior | Drift report generated |
| Data Veracity Audit | Backtest source reliability and latency | Trust Score matrix updated |
| Strategy Manifestation | Formal strategy document | Ramin approval logged |
| Resource validation | Promote/demote references from Resource Registry | Each promoted resource has module mapping |
| Strategy toggles | Configurable active/inactive strategy states | Toggles write Event Log entries |
| Approval record | Human approval captured as audit event | Phase 5 cannot start without approval |

### Phase 4 Build Order

1. Data Veracity Audit over Phase 1/2 events.
2. Source Trust Score recalculation.
3. Resource Registry validation pass.
4. Candidate catalyst class review.
5. Strategy Manifestation draft.
6. Ramin review and written approval.
7. Strategy toggles and config snapshot.

### Phase 4 Gate

Phase 4 is done when:

- Manifested Strategy Document exists.
- Approved instruments, catalyst types, sources, model weights, quantum role, and risk assumptions are explicit.
- Resource Registry references used by active strategies are validated or marked provisional.
- Approval is logged in Event Log.
- No execution has occurred yet.

## Phase 5 - Layer B Orchestration

Objective: wire risk, policy, paper brokers, kill-switches, and cockpit action flows.

Trading state: paper integration testing.

### Phase 5 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Approval Policy Router | Test/live approval rules | Policy decision logged |
| Risk Agent | Sizing, Kelly, caps, drawdown checks | Bad trade blocked deterministically |
| Kill-switches | Global, strategy, venue | Switch writes event before acknowledgement |
| Execution adapter status | Read-only venue health, permission, position, balance, and limit checks | Venue cannot write until read-only checks pass |
| Broker adapters | Alpaca paper, pmxt/Polyrouter read-only then guarded; PriveX-style perps remain `live_blocked` unless separately approved | Paper order lifecycle logged |
| Position monitor | Open position state and exits | State transitions are replayable |
| Telegram notifier | Human-in-loop alerts | Delivery/retry/fallback logged |
| Signal Review UI | Review proposed signals with evidence | No direct broker action from UI |
| Cockpit dashboard | Functional System Map, health, uptime, source status | Kill-switch panel renders first |

### Phase 5 Build Order

1. Risk Agent contract and deterministic tests.
2. Approval Policy Router.
3. Kill-switch implementation.
4. Execution adapter status/reconciliation layer.
5. Alpaca paper adapter.
6. Prediction-market adapter in read-only mode.
7. PriveX-style adapter research note and disabled placeholder if useful.
8. Telegram alerting.
9. Signal Review UI.
10. Position monitor.
11. Paper trade drill.

### Phase 5 Gate

Phase 5 is done when:

- At least one paper trade can open and close with complete Event Log trace.
- Risk Agent blocks oversize, stale, low-evidence, and degraded-state trades.
- Kill-switches stop new actions.
- Telegram alerts work for critical events.
- Cockpit shows health, uptime, module map, source status, and resource provenance.
- Phase 5 test trades do not count toward the clean Phase 7 proof.

## Phase 6 - Postmortem And Learning Loop

Objective: make Qadam improve from outcomes without silently rewriting history.

Trading state: paper.

### Phase 6 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Postmortem Agent | Analyze every closed trade | Postmortem packet written |
| Outcome linker | Link thesis to real outcome | Catalyst correctness recorded |
| Bayesian updater | Update weights after postmortem | Weight change is auditable |
| Trust Score updater | Monthly source-score updates | Score changes have evidence |
| Knowledge Graph writer | Store resolved catalysts and embeddings | Nearest-neighbour query works |
| Shadow Strategy | Parallel strategy suggestions not executed | Shadow P/L tracked separately |
| Architect Agent | Weekly/monthly system review | Recommendations are logged, not auto-applied |
| Cockpit postmortems | Trade Journal and Postmortems pages | Ramin can inspect the learning loop |

### Phase 6 Build Order

1. Closed-trade schema.
2. Postmortem packet schema.
3. Outcome linker.
4. Knowledge Graph write/read path.
5. Bayesian weight update path.
6. Trust Score update path.
7. Shadow Strategy runner.
8. Architect Agent summaries.
9. Cockpit Postmortems and Trade Journal.

### Phase 6 Gate

Phase 6 is done when:

- Every closed paper trade produces a postmortem.
- Knowledge Graph has resolved catalyst entries.
- Trust Scores and model weights update with audit trail.
- Shadow Strategy is tracked separately from executed strategy.
- Architect Agent produces review output without changing policy by itself.

## Phase 7 - 90-Day Demo Proof And Live Decision

Objective: run the fully autonomous paper system and evaluate whether Qadam deserves live capital.

Trading state: autonomous paper, then live decision.

### Phase 7 Modules

| Module | Build In This Phase | Independent Exit Check |
| --- | --- | --- |
| Demo proof harness | 90-day clock, mode lock, proof state | Start date logged |
| Autonomous paper policy | Test-mode auto-approval after gates pass | No manual trade-level approvals |
| Performance evaluator | Expectancy, drawdown, Brier, Sharpe/Sortino | Metrics update from Event Log |
| Override detector | Detect manual interventions | Any manual override voids clean sample |
| Maturity tracker | 100 closed trade benchmark | Under-100 sample marked immature |
| Live promotion review | Structured review and cooling-off period | Approval logged separately |

### Phase 7 Operating Rules

- Layer A watches continuously.
- Layer B executes only when policy gates pass.
- Two proof trades per week is a discipline target, not a quota.
- If qualified setups do not exist, Qadam does not force trades.
- Starting balance is £1000 in a paper/test account.
- 100 closed trades is the maturity benchmark.
- If 90 days pass with fewer than 100 closed trades, continue paper until maturity exists.
- Max drawdown must stay at or below 20%.
- Zero manual trade-level overrides during the clean proof sample.

### Phase 7 Gate

Phase 7 is done when:

- 90 consecutive days of autonomous paper operation complete.
- Performance is positive after costs.
- Drawdown is within cap.
- No manual trade-level overrides occurred.
- Postmortems exist for all closed trades.
- 100-trade maturity is met or the result is explicitly marked immature.
- Ramin completes a structured live-promotion review.
- All proof data remains locally stored unless explicit cloud sync is approved later.

## Cross-Phase Cockpit Plan

The cockpit should evolve without becoming a trading toy.

| Phase | Cockpit Capability |
| --- | --- |
| Phase 0 | Login route plan, protected dashboard shell, System Map placeholder, kill-switch placement |
| Phase 1 | Source health, heartbeat, degraded-state banners |
| Phase 1E | Agent ownership map, tool grants, skill bundle status, forbidden-action warnings |
| Phase 2 | Hidden/debug shadow signals, evidence trail previews |
| Phase 3 | Quantum job status and fallback visibility |
| Phase 4 | Manifested Strategy review and approval record |
| Phase 5 | Functional Dashboard/System Map, Signal Review, comments/forum, kill-switches, Telegram state |
| Phase 6 | Trade Journal, Postmortems, Knowledge Graph stats, Architect summaries |
| Phase 7 | Demo proof clock, maturity benchmark, live-promotion review |

Production routing requirement:

- `qadam.trade` remains the public landing page.
- Top-right Login routes to Clerk.
- Successful login routes to protected `/dashboard`.
- Login allowlist is limited to Ramin, Troy, Akber, Anas, and Ion in the first release.
- Unauthenticated `/dashboard` redirects to login.
- Cockpit includes a private comments/forum area for improvement suggestions.
- Vercel production deploys are deliberate while the landing page is live.

## Cross-Phase Data And Resource Plan

Keep these two registries separate.

| Registry | Contains | Does Not Contain |
| --- | --- | --- |
| Live ingress source registry | ACLED, FIRMS, Oref, UnusualWhales, Polymarket, Kalshi, Alpaca, GDELT, Telegram, RSS, etc. | Strategy papers, product inspirations, prompt frameworks |
| Qadam Resource Registry | Strategy wisdom, product benchmarks, open-source repos, papers, OSINT references, analytical frameworks | Live heartbeat status, raw payloads, broker/execution state |
| World-Model Corpus | How The World Works private priors, claims, power maps, narrative lenses, scenario trees, falsification tests | Verified evidence, source heartbeat status, direct trade triggers |

Future database tables:

- `source_registry`
- `source_heartbeat`
- `source_trust_score`
- `reference_registry`
- `reference_module_mapping`
- `reference_validation_note`
- `agent_manifest`
- `agent_tool_grant`
- `skill_bundle`
- `skill_bundle_reference`
- `world_model_claim`
- `world_model_observable_signature`
- `world_model_outcome_score`

## Cross-Phase Safety Gates

These apply from Phase 0 onward.

- Missing Event Log means degraded or blocked.
- Missing source heartbeat means degraded, not silently fresh.
- Missing optional API key means source unavailable, not failed.
- Missing execution key means execution disabled.
- Missing agent manifest means the agent cannot run.
- Missing or undeclared tool grant means the tool call is blocked.
- LLM uncertainty must be logged.
- Quantum delay must fall back to classical output.
- Any broker ambiguity blocks new orders until reconciled.
- Any venue with unknown account/subaccount/network scope is blocked.
- Any live or real-money venue is `live_blocked` in first-release mode unless a separate paper/sandbox approval exists.
- Any data source below Trust Score 0.3 is quarantined.
- Any signal without invalidation is blocked.
- Any signal without transaction-cost assumptions is blocked.
- Any proposed trade above cap is blocked.

## Recommended Next Implementation Batch

The Agent OS manifest layer is in place. The next batch should enforce those permissions at runtime before Qadam thinks, predicts, calculates, or trades.

1. Agent invocation wrapper.
2. Tool-grant enforcement before MCP tool calls.
3. Sample output fixtures for each agent schema.
4. Minimal Research Analyst shadow triage queue.
5. Cockpit drill-down for agent permissions and forbidden actions.
6. Keep execution authority outside the LLM layer.
