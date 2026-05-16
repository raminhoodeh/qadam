# Qadam Master Implementation Plan

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

This is the control document. Read this first. The other docs are supporting appendices, not competing plans.

## 1. What This Document Solves

Qadam now has several useful documents, but too many of them feel like plans. This master plan turns them into one build path:

- One source for what to build next.
- One phase sequence.
- One module map.
- One acceptance gate per phase.
- One document hierarchy so the supporting docs stop competing with each other.

This does not dilute Qadam. It reduces cognitive load. The project remains deep, but the daily build path becomes simple.

## 2. Document Hierarchy

| Role | Document | How To Use |
| --- | --- | --- |
| Canonical spec | `specs/qadam-specs.md` | Product truth, roadmap, doctrine, full system requirements. |
| Build control | `docs/qadam-master-implementation-plan.md` | The only day-to-day implementation plan. |
| Detailed roadmap appendix | `docs/qadam-implementation-plan.md` | Longer detail behind the master plan. |
| Modular appendix | `docs/qadam-modular-implementation-plan.md` | Module contracts and phase decomposition. |
| Foundation appendix | `docs/qadam-foundational-architecture-plan.md` | Phase 0 technical detail. |
| Live source appendix | `docs/api-source-inventory.md` | 35 live/live-adjacent feeds and source conflicts. |
| Resource appendix | `docs/qadam-resource-registry.md` | Papers, products, OSS stacks, frameworks, build references. |
| Private worldview appendix | `docs/how-the-world-works-integration.md` | Qadam's private world-model foundation and evidence boundary. |

Rule: update this master plan when the build sequence changes. Update appendices only when implementation detail changes.

## 3. The Three Knowledge Layers

Qadam should not mix all inputs into one bucket.

| Layer | What It Contains | What It Does |
| --- | --- | --- |
| Live Source Registry | ACLED, FIRMS, Oref, UnusualWhales, Polymarket, Kalshi, Alpaca, GDELT, Telegram, RSS, etc. | Feeds the machine with observable data and heartbeat status. |
| Resource Registry | Papers, open-source tools, product references, analytical frameworks, build inspiration. | Guides architecture, signal design, UX, and research methods. |
| Private World-Model Corpus | `how-the-world-works/` | Quietly shapes Qadam's suspicion, hidden-incentive reasoning, scenario generation, and narrative analysis. Currently 4 markdown files. |

Operational boundary:

- Live sources can become evidence.
- Resources can become design inputs.
- The private world-model can become a lens and prior.
- Only corroborated, logged, auditable evidence can affect trades.

## 4. System Shape

Qadam is built as three planes:

- **Layer A - Intelligence Engine:** watches, triages, researches, models probabilities, and proposes signals.
- **Layer B - Orchestration Layer:** applies risk, policy, kill-switches, paper/live execution, monitoring, exits, and postmortems.
- **Cockpit - Founding Fund Manager Surface:** gives Ramin, Troy, Akber, Anas, and Ion login access to the system map, health, signals, evidence, trades, postmortems, settings, and internal comments forum.

Core modules:

| Module | Purpose |
| --- | --- |
| Python COO / Orchestrator | Routes calls, schedules jobs, supervises modules, emits health. |
| Event Log | Append-only truth and replayable audit trail. |
| Source Registry | Live data feed registry, status, heartbeat, Trust Score. |
| Resource Registry | Non-live build and research references. |
| World-Model Corpus | Private foundational worldview and adversarial hypothesis layer. |
| Agent Operating System | File-based agent manifests, skill bundles, tool grants, and connector permissions. |
| FastMCP Tools | Typed interface for source, resource, health, and module access. |
| Local LLM | Gemma triage and compression on the laptop. |
| Frontier LLM | Gemini research, synthesis, debate, and strategy reasoning. |
| Quantum Engine | Weekly oracle using local simulation, Q-CTRL as an optional optimization/error-suppression provider, IBM Quantum, AWS Braket, and classical fallback. |
| Risk Agent | Position size, caps, drawdown, stale-data checks, kill-switch enforcement. |
| Execution Venue Registry | Disabled/read-only venue map covering credential status, account/subaccount scope, network/chain scope, mode, reconciliation, and kill-switch state. |
| Broker / Venue Adapters | Alpaca paper/live, prediction-market adapters, and later optional venues such as PriveX-style perps rails. |
| Knowledge Graph | Resolved catalyst memory and nearest-neighbour recall. |
| Cockpit | `qadam.trade` login, dashboard, system map, signal review, comments forum, postmortems. |
| Fund Manager Forum | Private suggestions and governance comments from Ramin, Troy, Akber, Anas, and Ion. |
| Future Compute Sharing | Optional later layer where Fund Managers can contribute local RAM/compute/storage safely. |

## 5. Non-Negotiable Build Rules

- Event Log first. If it is not logged, it did not happen.
- Health first. Every module needs status, heartbeat, latency, and degraded reason.
- Read-only first. No module gets execution authority until it has proved itself in observation mode.
- Evidence before action. World-model priors and LLM reasoning never bypass live corroboration.
- Fail closed. Missing data, stale heartbeats, missing secrets, broker ambiguity, or model failure blocks or degrades.
- Layer A surfaces; Layer B acts.
- No direct UI-to-broker path.
- No LLM-to-broker path.
- No agent can call an undeclared tool, connector, shell command, or execution endpoint.
- Every agent must declare its role, allowed data, allowed tools, output schema, and escalation path before it can run.
- No venue can write orders until it has passed read-only health, permission, position, and reconciliation checks.
- Never retry order-creating POST requests automatically.
- Venue account/subaccount/network scope must be explicit before any order path is enabled.
- Quantum is a weekly oracle, not a real-time trading brain.
- Two proof trades per week is a discipline target, not a quota.
- 100 closed trades is the maturity benchmark.

## 6. First Release Trial Mode

The first release of Qadam is a local-first autonomous trial system.

Operating constraints:

- Account: £1000 test/paper account.
- Execution: Qadam may trade autonomously in the test account after Phase 5/7 gates are met.
- Capital boundary: no live capital in the first release.
- Access boundary: first-release login is limited to Ramin, Troy, Akber, Anas, and Ion.
- Current allowlist emails: Ramin `raminhoodeh@gmail.com`, Troy `troycookecareer@gmail.com`, Ion `isioras@yahoo.co.uk`.
- Pending allowlist emails: Akber and Anas.
- Approval boundary: test-mode trades do not require individual Fund Manager approval, because the point is to test whether Qadam's rules work cleanly without emotional interference.
- Human controls: Fund Managers can review, comment, suggest improvements, and use allowed kill-switches, strategy toggles, and system-level approval gates; these are logged.
- Storage: all saved Qadam data remains local on Ramin's MacBook unless a later explicit cloud-sync decision is made.
- Hardware target: MacBook with 1TB SSD and 24GB unified memory.
- Local stores: PostgreSQL + TimescaleDB for Event Log, ChromaDB for Knowledge Graph, local raw payload archive, local model/config/runtime files.
- Cloud calls allowed: external APIs, Gemini, Q-CTRL, IBM Quantum/AWS Braket, Vercel cockpit hosting, and broker/paper-trading APIs can be accessed, but Qadam's canonical saved state remains local.
- Q-CTRL credential is stored locally for future quantum optimization/error-suppression experiments, but Q-CTRL is not active in Phase 0.
- Cloud backup: optional and deferred; no Pinecone/cloud data sync in first release unless explicitly approved.

Design implications:

- Use local paths and retention policies from day one.
- Keep storage schemas compact and replayable.
- Avoid architectures that require Redis/Railway/cloud databases for correctness.
- Build offline/degraded modes for missing APIs.
- Never store broker credentials, API keys, or Vercel tokens in committed files.
- Make test/live environment separation impossible to miss in config and cockpit.
- The cockpit must clearly show `TEST ACCOUNT` / `PAPER MODE` status during autonomous trading.

## 7. Phase 0 - Foundation

Objective: make Qadam boot as a coherent, observable system. No ingestion, no inference, no trading.

Build:

- Postgres + Timescale Event Log schema v1.
- Local JSONL Event Log fallback and replay check for Phase 0 operation before Docker/Postgres is running.
- Migration runner for applying SQL migrations when Postgres is available.
- Replay test for a sample event.
- ChromaDB initialized as empty Knowledge Graph.
- Local data directory contract for raw payloads, runtime files, event storage, Chroma persistence, model cache, and backups.
- Config and secrets loader with strict local secret-file support.
- Masked secret status for quantum providers, including Q-CTRL.
- Orchestrator health endpoint and module map.
- Static Source Registry for 35 live ingress feeds.
- Resource Registry from `qadam-general-context.md`.
- Private World-Model Corpus registry from the 4 markdown files in `how-the-world-works/`.
- Disabled Execution Venue Registry shaped by PriveX Starter lessons: read-only first, explicit account/subaccount/network scope, auth errors separated from transient errors, and no automatic POST retries.
- FastMCP tools: `ticker_echo`, `source_registry`, `source_detail`, `resource_registry`, `world_model_claim`, `system_health`, `module_map`.
- Agent/skill manifest plan shaped by Anthropic's `financial-services` reference: named workflow agents, reusable skill bundles, explicit connector grants, manifest validation, and secret scanning.
- Next.js cockpit shell with System Map.
- Clerk route plan: top-right Login, `/login` or `/sign-in`, protected `/dashboard`.
- Vercel linked read-only to existing `qadam.trade` project.
- Founding Fund Manager access list: Ramin, Troy, Akber, Anas, Ion.
- Initial email allowlist: `raminhoodeh@gmail.com`, `troycookecareer@gmail.com`, `isioras@yahoo.co.uk`; Akber and Anas pending.
- Local comments/forum schema for signal, module, strategy, and postmortem suggestions.
- Foundation check script expanded as the build grows.

Exit gate:

- Local startup verifies registries, health, config, and storage.
- Event Log writes and replays a test event through the local fallback.
- Timescale migration exists for the durable Postgres Event Log target.
- Local storage paths are created and permission-checked.
- Source Registry, Resource Registry, and World-Model Corpus are distinct.
- Execution venues are visible but disabled/read-only; no venue can place orders.
- Cockpit shell renders the System Map.
- Cockpit access model is limited to the five founding Fund Managers.
- Comment/forum entries can be saved locally and linked to a module or signal.
- No secret appears in committed files.
- No market action is possible.

## 8. Phase 1 - Data Spine And Ingestion

Current implementation start:

- Test-data ingestion spine exists in `orchestrator/ingestion.py`.
- Shared adapter envelope, raw archive, and normalized event schema exist in `orchestrator/adapters.py`.
- First read-only public adapters exist for GDELT, Oref, NASA FIRMS, FRED, and RSS.
- Source heartbeat and `data_environment_map.json` generation exist in `orchestrator/source_health.py`.
- `scripts/check_test_ingestion.py` proves typed source observations and Event Log writes without live API calls.
- `scripts/check_source_heartbeat.py` proves all 35 sources are classified by readiness, missing credentials, promoted adapter state, and deferred reasons.
- `scripts/check_gdelt_adapter.py` proves GDELT sample normalization and graceful degraded handling for live network/API failure.
- `scripts/check_oref_adapter.py` proves Oref sample normalization and graceful degraded handling for live network/API failure.
- `scripts/check_nasa_firms_adapter.py` proves NASA FIRMS sample normalization, bbox-first area requests, credential-gated live mode, raw archive writes, and graceful degraded handling when the key is missing.
- `scripts/check_fred_adapter.py` proves FRED macro normalization, sigma/pct-change calculation, public CSV fallback, raw archive writes, and graceful degraded handling for live feed failure.
- `scripts/check_rss_adapter.py` proves RSS feed normalization, keyword filtering, raw archive writes, and graceful degraded handling for live feed failure.
- `migrations/0003_source_observation.sql` defines durable observation storage for Postgres/Timescale.
- Local Python 3.12 `.venv` bootstrap exists in `scripts/bootstrap_runtime.sh`.
- Embedded Chroma Knowledge Graph initialization exists in `orchestrator/chroma_store.py`.
- Durable Postgres seed/write helpers exist in `orchestrator/postgres_store.py`.
- `scripts/start_local_stores.sh` is ready to start services, migrate, and seed once Docker/OrbStack/Podman/Colima is available.
- Remaining live adapters stay unimplemented until each source is promoted from test data to real API mode.
- GDELT is promoted to the first real read-only adapter path; Oref is promoted as the second, higher-trust conflict alert adapter; NASA FIRMS is promoted as the first physical anomaly adapter; FRED is promoted as the first macro regime adapter; RSS is promoted as the first narrative feed adapter.
- No promoted adapter is allowed to influence signal confidence without corroboration and Signal Integrity Gate approval.

Objective: make Qadam observe the world.

Build:

- Shared async source adapter interface.
- Raw payload archive.
- Normalized event schema.
- Heartbeat and SLA monitor.
- Tier 1 adapters: ACLED, Oref, NASA FIRMS, UnusualWhales, Polymarket, Kalshi, Alpaca.
- Tier 2 adapters: FRED, AIS, Wingbits, GDELT, RSS, X.
- Tier 3 adapters: BLS, ECB, UN Comtrade, BIS, USGS, Reddit, Telegram, SEC, STOCK Act.
- Tier 4 adapters or deferred stubs.
- Initial Trust Score table.
- `data_environment_map.json`.
- Cockpit degraded-state banners.
- Local retention policy for raw payloads, normalized events, and derived features.

Exit gate:

- Every one of the 35 sources is `live`, `degraded`, `unavailable`, or `deferred`.
- Tier 1 sources are ingesting or blocked for explicit credential/licensing reasons.
- Raw and normalized events are replayable.
- Stale data appears as degraded.
- Trust Score seed exists.
- Saved data remains local.

## 8A. Phase 1E - Agent And Skill Manifests

Objective: make Qadam's agents explicit, permissioned, and inspectable before deeper intelligence or execution work begins.

Current implementation start:

- `agents/` contains 8 named role manifests: COO, Research Analyst, Strategy Lead, Head of Quant, Risk Agent, Signal Auditor, Execution Auditor, and Fund Manager Interface.
- `skills/` contains 7 reusable skill bundles: macro intelligence, prediction markets, physical anomaly monitoring, options/volatility flow, Akber 6-stage filter, private edge/world-model priors, and risk/postmortems.
- `orchestrator/agent_registry.py` validates agent folders, permissions, skill references, tool grants, output schemas, forbidden actions, and raw-secret patterns.
- `orchestrator/agent_runtime.py` enforces tool-grant checks before tool use, validates sample outputs, blocks broker-write tools, and maintains a Research Analyst shadow triage queue.
- `scripts/check_agent_manifests.py` is wired into `start_qadam.sh`.
- `scripts/check_agent_runtime.py` is wired into `start_qadam.sh`.
- System health, FastMCP-style tools, and the cockpit expose Agent OS and Agent Runtime status.

Why now:

- Anthropic's `financial-services` repo is a useful reference pattern for financial workflow agents: named agents, vertical skill bundles, MCP-style data connectors, managed-agent deployment cookbooks, validation scripts, and secret-scan discipline.
- Qadam should adopt the architecture pattern, not the vendor dependency or licensed connector set.
- This phase prevents hidden authority from accumulating inside prompts, scripts, or future LLM calls.

Build:

- Add an `agents/` directory with one manifest folder per named Qadam role: COO, Research Analyst, Strategy Lead, Head of Quant, Risk Agent, Signal Auditor, Execution Auditor, and Fund Manager Interface.
- Add a `skills/` directory for reusable bundles: macro intelligence, prediction markets, physical anomaly monitoring, options and volatility flow, Akber 6-stage filter, private edge / world-model priors, and risk/postmortems.
- Each agent manifest declares role, scope, allowed source groups, allowed Resource Registry references, allowed MCP tools, allowed secrets by name, output schema, escalation and signoff rules, and forbidden actions.
- Add `scripts/check_agent_manifests.py` to validate manifests, skill references, tool grants, and forbidden capabilities.
- Add a deterministic skill sync step only after the source skill bundle is validated.
- Extend secret scanning so agent manifests and skill bundles cannot contain raw keys.

Critical boundary:

- Anthropic's reference defaults to "agents draft, humans approve." Qadam keeps that for live capital.
- Qadam's £1000 first-release paper account is different: autonomous paper trades are allowed only after the Phase 5/7 policy gates, Risk Agent checks, execution venue checks, kill-switches, and Event Log writes exist.
- No live-capital trade can be placed without an explicit future approval model.

Exit gate:

- All agent manifests validate locally.
- Each agent has least-privilege tool grants.
- No agent has direct broker write access.
- Paper execution authority is reserved for the future execution path, not the LLM agent itself.
- The cockpit can show which agent owns each module and which tools it is allowed to use.

## 8B. Phase 1F - Agent Runtime Enforcement

Objective: make Qadam enforce agent permissions before Phase 2 intelligence begins.

Implemented state:

- `authorize_tool_call(agent_key, tool_name)` returns allow/block decisions from the manifest grants.
- Broker-write tools such as `place_order`, `cancel_order`, and `close_position` are hard-blocked.
- Sample output fixtures exist for all 8 agents and validate against each agent's output schema.
- Research Analyst can queue a local shadow triage packet, marked non-executable.
- Runtime status is exposed through system health, FastMCP-style tools, startup checks, and cockpit registry cards.

Exit gate:

- Allowed tool calls pass only for agents with explicit grants.
- Undeclared or missing-grant tool calls block.
- Broker-write tools block for every agent.
- Shadow triage queue writes local-only packets with no signal, risk, or execution authority.

## 9. Phase 2 - Intelligence Stack

Objective: make Qadam think in shadow mode.

Build:

- Proposed Signal schema.
- Catalyst Evidence Trail schema.
- Gemma local triage.
- Gemini research packets.
- Akber 6-Step Filter.
- Prediction-market probability gap.
- Options / Black-Scholes gap report.
- Swarm simulation starter.
- World-model lens applied to candidates as private prior and red-team prompt.
- Signal Integrity Gate.
- Shadow signal store.

Exit gate:

- Layer A produces Proposed Signals.
- Every signal has evidence, assumptions, invalidation, transaction-cost assumptions, source Trust Scores, and pricing gap.
- World-model lens is present as private reasoning provenance, not factual evidence.
- No execution is possible.

## 10. Phase 3 - Quantum Integration

Objective: connect the weekly oracle without making the system dependent on it.

Build:

- `QuantumBackend` interface.
- Qiskit Aer local simulator.
- Classical fallback with the same output schema.
- Q-CTRL optional provider path after local circuit validation.
- IBM Quantum / Qiskit Runtime backend.
- AWS Braket secondary backend.
- Job 1: Pattern Recognition.
- Job 2: Strategy Collapse / Ambiguity Score.
- Weekly scheduler.
- Cockpit quantum status.

Exit gate:

- Every quantum job validates locally before hardware submission.
- Hardware failure produces `classical-fallback`.
- Quantum can upgrade, downgrade, or hold a signal.
- Quantum cannot originate a signal or bypass risk gates.

## 11. Phase 4 - Strategy Manifestation

Objective: turn observed system behaviour into an approved strategy document.

Build:

- Triple-Mirror Audit.
- Data Veracity Audit.
- Trust Score recalculation.
- Resource Registry validation.
- World-model lens validation against observed outcomes.
- Manifested Strategy Document.
- Strategy toggles.
- Ramin approval logged in Event Log.

Exit gate:

- Approved strategy document exists.
- Active instruments, catalyst classes, source weights, model weights, quantum role, and risk assumptions are explicit.
- Private world-model frames used by active strategies are marked as validated, provisional, or rejected.
- No execution occurs before approval.

## 12. Phase 5 - Layer B Orchestration

Objective: wire risk, policy, paper execution, alerts, and cockpit actions.

Build:

- Approval Policy Router.
- Risk Agent.
- Global, strategy, and venue kill-switches.
- Execution adapter contract with read-only status before any write path.
- Alpaca paper adapter.
- Prediction-market adapter in read-only then guarded mode.
- PriveX-style perps adapter research note: optional later execution rail only; default `live_blocked` unless an explicit test/sandbox path is approved.
- Telegram notifier.
- Position monitor.
- Signal Review UI.
- Functional System Map dashboard.
- Test/live mode guardrail shown in cockpit and enforced in config.

Exit gate:

- At least one paper trade opens and closes with full Event Log trace.
- Risk Agent blocks oversize, stale, low-evidence, and degraded-state trades.
- Kill-switches stop new actions.
- Telegram alerts work.
- Phase 5 test trades do not count toward Phase 7 proof.
- No live endpoint or live credential can be used in first-release mode.
- PriveX or any crypto-perps venue remains disabled in the first-release £1000 test run unless a separate paper/sandbox account is explicitly approved.

## 13. Phase 6 - Learning Loop

Objective: make Qadam improve without rewriting history.

Build:

- Postmortem Agent.
- Closed-trade schema.
- Outcome linker.
- Knowledge Graph write/read path.
- Bayesian model weight updates.
- Trust Score monthly updates.
- Shadow Strategy runner.
- Architect Agent summaries.
- Trade Journal and Postmortems cockpit pages.

Exit gate:

- Every closed paper trade has a postmortem.
- Knowledge Graph contains resolved catalyst entries.
- Trust Scores and model weights update with audit trail.
- World-model frames are scored as helpful, harmful, neutral, or untestable.
- Architect Agent recommends; it does not silently change policy.

## 14. Phase 7 - Demo Proof

Objective: prove the autonomous paper system before live capital.

Build:

- 90-day demo proof harness.
- Test-mode auto-approval after gates pass.
- Performance evaluator.
- Override detector.
- 100-trade maturity tracker.
- Live promotion review flow.

Operating rules:

- 90 consecutive calendar days.
- £1000 Alpaca paper account.
- Two proof trades per week where qualified setups exist.
- No forced trades.
- Max drawdown <= 20%.
- Zero manual trade-level overrides.
- 100 closed trades is the mature benchmark.
- All saved proof data remains local on the MacBook.

Exit gate:

- 90-day run complete.
- Expectancy positive after costs.
- Drawdown within cap.
- No manual trade-level overrides.
- Postmortems exist for all closed trades.
- 100-trade benchmark met, or result marked statistically immature.
- Ramin completes structured live-promotion review.

## 15. qadam.trade Route Plan

Current live state:

- `qadam.trade` redirects to `www.qadam.trade`.
- Public landing page exists.
- Top-right currently has `Read Whitepaper`, not Login.
- `/login`, `/sign-in`, and `/dashboard` are not live yet.

Target state:

- Landing page remains public.
- Top-right includes Login.
- Login routes to Clerk.
- Successful sign-in routes to protected `/dashboard`.
- Login allowlist is limited to Ramin, Troy, Akber, Anas, and Ion in the first release.
- `/dashboard` opens the System Map.
- Dashboard includes a private comments/forum area for suggestions and improvement notes.
- Unauthenticated `/dashboard` redirects to login.
- Production deploys remain deliberate while landing page is live.

## 16. How To Build Without Getting Overwhelmed

Use this rhythm:

1. Pick the current phase.
2. Pick one module in that phase.
3. Define its contract.
4. Implement the smallest version that emits Event Log and health.
5. Add one acceptance check.
6. Connect it to the cockpit only after the backend contract is stable.
7. Move to the next module.

Do not try to build all of Qadam at once. Qadam is created by making each module boring, observable, and replaceable.

## 17. Immediate Next Build Batch

Phase 0 foundation is substantially implemented, and Phase 1 has started with test ingestion, source heartbeat, and promoted read-only adapters for GDELT, Oref, NASA FIRMS, FRED, and RSS.

Phase 1E/1F are implemented at the manifest and runtime-enforcement level. The next practical batch is Phase 2 shadow intelligence:

1. Add Proposed Signal and Evidence Trail schemas.
2. Add a deterministic keyword/anomaly triage fallback before Gemma.
3. Add a local Research Analyst shadow triage runner that consumes queued packets.
4. Add Gemini/Gemma provider stubs that report configured/missing status without inference.
5. Keep all outputs non-executable and hidden/debug-only until Signal Integrity Gate exists.

This gets Qadam ready to think without letting prompts, tools, or future model calls accumulate hidden authority.
