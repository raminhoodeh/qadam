# Qadam Implementation Plan

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

Source of truth: `specs/qadam-specs.md`.
Companion inventory: `docs/api-source-inventory.md`.
Companion resource registry: `docs/qadam-resource-registry.md`.
Modular build guide: `docs/qadam-modular-implementation-plan.md`.
World-model integration note: `docs/how-the-world-works-integration.md`.
Master control document: `docs/qadam-master-implementation-plan.md`.

This is the detailed roadmap appendix. For day-to-day sequencing, use `docs/qadam-master-implementation-plan.md`.

## 0. Operating Doctrine

Qadam is an autonomous intelligence engine with a transparent recommendation interface. The engine can observe, reason, size risk, paper/live trade under guardrails, log outcomes, and run postmortems. The cockpit lets the founding Fund Managers, Ramin, Troy, Akber, Anas, and Ion, see what it is doing, why it matters, what evidence supports it, and how similar signals performed historically.

Non-negotiable principles:

- Layer A surfaces; Layer B acts.
- Demo before live, always.
- Human gates are policy-based.
- Quantum is a weekly oracle, not a real-time trading brain.
- AI and Quantum are leverage, not authority.
- Fail closed, never open.
- Everything is logged and replayable.
- Telegram is the primary human-in-the-loop communications channel, but it is outbound-only until a later explicitly approved command design exists.

Product boundaries:

- Not HFT.
- Not copy trading.
- Not a general stock screener.
- Not a financial advisor.
- Not lagging-indicator driven.
- Not a black-box bot.
- Not a frequency machine.

Rare Edge Doctrine:

- Qadam should never trade to fill a calendar.
- Three proof trades per week is a Phase 7 discipline target only where
  qualified setups exist; it is not a quota.
- Rare high-conviction opportunities are expected roughly 4-6 times per year.
- Forcing trades corrupts the Knowledge Graph.
- Quality of thesis beats quantity of trades.

## 1. Current Build State

Already scaffolded:

- API source inventory: `docs/api-source-inventory.md`
- Qadam resource registry from `specs/qadam-general-context.md`: `docs/qadam-resource-registry.md`
- How The World Works private world-model foundation: 4 markdown files in `how-the-world-works/`
- 35-source registry: `world_monitor/source_registry.py`
- Orchestrator shell: `orchestrator/main.py`
- Health endpoint scaffold: `orchestrator/health_server.py`
- FastMCP-style scaffold: `orchestrator/mcp_server.py`
- Postgres/Timescale and Chroma services: `docker-compose.yml`
- Cockpit shell: `cockpit/`
- Vercel project link for `qadam.trade`: `cockpit/.vercel/project.json`
- Vercel helper scripts: `scripts/inspect_vercel_project.sh`, `scripts/deploy_cockpit_vercel.sh`
- Startup check: `start_qadam.sh`

Known scaffold limitations:

- Event Log has local JSONL fallbacks and Postgres/Timescale migration/write helpers, but durable live Postgres requires the local database service to be running.
- Cockpit now has local Supabase Auth routes, a protected `/dashboard`, and founding Fund Manager allowlist enforcement.
- Live `qadam.trade` production routing still needs a deliberate deploy before the Login entrypoint is public.
- The remote Vercel project is currently configured as a generic project with root directory `.`; production deploys should be deliberate while the existing landing page is live.
- The resource registry is documentary only; it does not yet have a database table, cockpit view, or module-to-resource tracking workflow.
- The How The World Works corpus is accepted as a private foundational prior, but is not yet structured into claim cards, observable signatures, or falsification tests.
- Health port smoke test was blocked by the sandbox, not by code.
- The source registry is real and Phase 1 now has 19 promoted read-only adapter contracts. Full live ingestion still depends on provider credentials, local Postgres/Timescale availability, rate-limit configuration, and historical backfill runs.

## 2. Core Architecture To Preserve

Layer A - Intelligence Engine:

- Live ingress data pipelines, canonically called World Monitor in the spec.
- Resource registry from `qadam-general-context.md` for non-live build/research references.
- Private world-model foundation from `how-the-world-works/` for esoteric edge hypotheses, power maps, narrative lenses, and adversarial scenario generation.
- Gemma 4 local triage on MLX.
- Gemini 3.1 Pro cloud research and 100-persona swarm simulation.
- Quantum Engine weekly oracle for Pattern Recognition and Strategy Collapse.
- Signal Assembly with evidence trail and Black-Scholes Gap report.

Layer B - Orchestration Layer:

- Approval Policy Router.
- Risk Agent with deterministic guardrails.
- Broker adapters.
- Kill-switches.
- Position monitoring and exits.
- Postmortem Agent.

Cross-cutting:

- Event Log in PostgreSQL + TimescaleDB.
- Knowledge Graph in ChromaDB.
- Architect Agent.
- Web cockpit at `qadam.trade`.
- Telegram Bot notification channel for member alerts, trade lifecycle updates, insight digests, and system warnings.

First release operating mode:

- Qadam runs as a local-first autonomous trial system on Ramin's MacBook with 1TB SSD and 24GB unified memory.
- Saved canonical state remains local by default: Event Log, Knowledge Graph, raw payload archive, source heartbeats, postmortems, paper trades, and model/runtime artifacts.
- External APIs, Gemini, IBM Quantum/AWS Braket, Vercel, and broker/paper-trading APIs are allowed as services, but they do not become the canonical storage layer.
- The first release may route guarded paper trades only in the £100,000 test/paper account after the required gates are built.
- Cockpit login is limited to the five founding Fund Managers: Ramin, Troy, Akber, Anas, and Ion.
- The cockpit includes a small private comments/forum area for improvement suggestions, signal debates, module notes, and postmortem concerns.
- Future compute-sharing is allowed as a later concept: Fund Managers may eventually rent or contribute local RAM/compute/storage to Qadam after the system is understood, secured, and permissioned.
- No live capital is in scope for the first release.
- Cockpit must make `TEST ACCOUNT` / `PAPER MODE` unmistakable.

## 3. Quantum Backend Policy

Qadam uses Google for Gemini only, not for quantum hardware in v1. Google Quantum hardware access is not public self-serve, so it is not a default backend.

Backend order:

1. Local classical and quantum simulation: Qiskit Aer plus scipy/cvxpy/scikit-learn.
2. Primary real quantum backend: IBM Quantum via Qiskit Runtime.
3. Secondary real quantum backend: AWS Braket.
4. Optional error-suppression layer: Q-CTRL Fire Opal.
5. Optional later adapters: Azure Quantum, IonQ direct, D-Wave Leap, qBraid.

Implementation rules:

- Every quantum job validates locally before hardware submission.
- Every hardware backend must implement the same `QuantumBackend` interface.
- Every job must have a `classical-fallback` output with the same schema.
- Queue delays or quota failures degrade the job; they do not halt Qadam.
- Quantum cannot originate a signal, bypass the 6-Step Filter, bypass the Risk Agent, or self-promote a strategy.

Secrets to reserve:

- `IBM_QUANTUM_TOKEN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `QCTRL_TOKEN`
- `QCTRL_ORGANIZATION`

## 4. Instrument Priority

Phase 7 demo strategy generation should focus on Ranks 1-3, with Ranks 4-5 opportunistic.

| Rank | Instrument | Role |
| --- | --- | --- |
| 1 | Prediction Markets, Polymarket / Kalshi | Primary. Best cadence fit and binary feedback loop. |
| 2 | Crude Oil, USO / XLE options | Primary. Strongest physical-to-paper catalyst fit. |
| 3 | Defence Equities, LMT / RTX / XAR options | Primary-secondary. Natural conflict escalation exposure. |
| 4 | Silver, SLV options | Opportunistic. Strong when physical catalyst fires, not forced. |
| 5 | Semiconductors, SOXX / NVDA / AMD options | Opportunistic. Best for Taiwan Strait / supply-chain catalysts. |
| 6 | Agricultural Commodities | Watchlist during demo. Longer resolution windows. |
| 7 | Politician Trade Plays | Conviction multiplier only. Never standalone signal origin. |

## 5. Signal Integrity Gate

Before any signal reaches the 6-Step Filter, it must have:

- Clear trigger and invalidation rule.
- Evidence trail with source Trust Scores.
- Historical or out-of-sample reference.
- Transaction-cost assumptions.
- Markov regime context.
- Defined risk per trade.
- Kill-switch clause.
- Kelly-based sizing rule.
- Probability estimate and pricing gap.

Auto-block or downgrade if:

- "Guaranteed" or "free money" framing.
- No sample size.
- No costs/slippage/spread assumptions.
- Unverified social media claim without corroboration.
- Catalyst is already mainstream consensus.
- No explainable evidence trail.

## 6. Source Ingestion Foundation

The 35-source World Monitor registry covers live and live-adjacent machine-readable ingress feeds only. It does not replace the broader Qadam resource registry in `qadam-general-context.md`.

All 35 live ingress sources are registry entries. Each source must expose:

- `source`
- `pipeline`
- `tier`
- `tool_name`
- auth requirements
- endpoint(s)
- cadence
- rate limit
- heartbeat SLA
- failure mode
- degraded status

Unified Event schema must include:

- `event_id`
- `source`
- `trust_score_at_ingestion`
- `event_type`
- `raw_payload`
- `normalised_summary`
- `coordinates`
- `ingested_at`
- `linked_catalyst_id`

Trust Score rules:

- Initial score is seeded from backtesting.
- Scores update monthly.
- Source < 0.3 is quarantined from triage.
- Source 0.3-0.6 requires corroboration.
- Source > 0.6 can pass to Gemini if strategy criteria match.

Degraded mode:

- Never silently continue with stale data.
- Every degraded state is logged and shown in cockpit.
- AIS dark switches to Wingbits + FIRMS triangulation.
- FIRMS delayed > 6 hours pauses thermal anomaly detection.
- Gemini failures create `pending-research`.
- Quantum failures mark outputs `classical-fallback`.

## 6A. Resource And Reference Registry Foundation

`specs/qadam-general-context.md` contains Qadam's broader build resources. These are not all live APIs, so they should not be forced into the World Monitor source registry.

Resource categories:

- Strategy wisdom and guardrails.
- Signal and intelligence product benchmarks.
- AI architecture and proof-of-concept references.
- Prediction-market open-source stack.
- Geopolitical and OSINT references.
- APIs and technical infrastructure candidates.
- Institutional analytical frameworks.
- Product and positioning references.
- Prediction-market papers.

Build requirements:

- Maintain `docs/qadam-resource-registry.md` as the planning companion to `docs/api-source-inventory.md`.
- Add a future `resources` or `reference_registry` table with fields for name, category, URL/source, module mapping, status, validation notes, and decision outcome.
- Link resources to modules such as Research Analyst, Strategy Lead, Prediction Market Adapter, Risk Agent, Signal Review, Cockpit, and Postmortem Agents.
- Treat resources as hypotheses or implementation references until they pass Qadam's validation process.
- Keep live feed health in the source registry; keep research/reference provenance in the resource registry.

Foundation exit criteria:

- Resource registry exists and is linked from README and implementation plan.
- Every major resource category from `qadam-general-context.md` is represented.
- The cockpit plan distinguishes live data feeds from research/build references.
- No resource is promoted into execution logic without a validation note and explicit module mapping.

## 6B. Private World-Model / Esoteric Edge Corpus

`how-the-world-works/` is Qadam's private world-model foundation. Qadam quietly believes this corpus captures something important about how surface narratives, institutional power, finance, media, war, psychology, and hidden incentives interact. It is fundamentally useful because Qadam's intelligence needs more than feeds; it needs causal maps, hidden-incentive hypotheses, narrative awareness, and red-team scenario generation.

This belief is internal and operational, not public-facing positioning. It can shape what Qadam looks for, what questions it asks, and which scenarios it stress-tests. It must still pass through evidence gates before it can affect signal confidence, sizing, execution, or user-facing factual claims.

Build requirements:

- Register `how-the-world-works/` as a private `world_model`, `esoteric_edge`, and `foundational_prior` corpus.
- Extract structured claim cards from each file.
- Classify each claim as factual, causal, predictive, metaphysical, symbolic, narrative, or strategic.
- Map each claim to actors, mechanisms, observable signatures, live sources to check, and market channels.
- Keep trade-evidence confidence low until corroborated by live sources, even when the internal worldview prior is strong.
- Store useful frames in the Knowledge Graph only with provenance and status.
- Make the cockpit display `world-model lens` separately from evidence.

Guardrails:

- World-model claims cannot originate trades.
- Metaphysical or symbolic claims cannot appear as factual evidence.
- The Signal Integrity Gate must block uncorroborated, unfalsifiable, or overconfident use.
- Postmortems must score whether each world-model lens helped, harmed, or had no effect.

Foundation exit criteria:

- `docs/how-the-world-works-integration.md` exists.
- The corpus is linked from the Resource Registry and modular implementation plan.
- A future `world_model_claim` schema is reserved.
- The cockpit plan distinguishes factual evidence, resource provenance, and private world-model lenses.

## 7. Phase 0 - Foundations

Objective: build the substrate. No ingestion, no inference, no trading.

Build order:

1. Real Event Log schema v1 in Postgres.
2. Timescale hypertables for time-indexed events.
3. Migration runner and replay test.
4. ChromaDB initialization.
5. Local data directory contract for raw payloads, runtime files, Chroma persistence, model cache, and local backups.
6. Supabase founding Fund Manager auth allowlist.
7. Secret loading via macOS Keychain or strict local file permissions.
8. FastMCP tools: `ticker_echo`, `source_registry`, `source_detail`.
9. Orchestrator health endpoint.
10. Static cockpit content shell with kill-switch buttons always visible.
11. Local comments/forum schema.
12. `COCKPIT.md` data-contract template.
13. `launchd` process supervision.
14. Sentry and uptime monitor hooks with local no-op fallback.

Exit criteria:

- Clean browser login works.
- Test event writes to Postgres and replays identically.
- FastMCP-style tools return typed responses.
- Signal schema v1.0.0 exists and is versioned.
- No secret appears in committed files.
- Local storage paths are created and permission-checked.
- Startup script verifies registry, storage, and health.
- Dashboard shell renders kill-switch controls before data fetches.

## 8. Phase 1 - Data Spine & Ingestion

Objective: populate the canonical store with live and historical data.

Build order:

1. Shared adapter interface.
2. Raw payload archive and normalized event writer.
3. Heartbeat monitor and source SLA table.
4. Tier 1 adapters.
5. Tier 2 adapters.
6. Tier 3 adapters.
7. Tier 4 adapters.
8. Historical backfill where licensing allows.
9. Trust Score initialization from 12 months of backtesting.
10. `data_environment_map.json`.
11. Cockpit degraded-mode banners.

Current implementation note: the Phase 1 foundation can already emit deterministic test observations for all 35 registered sources. GDELT, Oref, NASA FIRMS, FRED, and RSS have dedicated promoted read-only adapter paths with local raw archives and degraded-state handling. A generic Phase 1 read-only adapter promotion layer now covers ACLED, UnusualWhales, Polymarket, Kalshi, Alpaca, AIS, Wingbits, BLS, ECB, UN Comtrade, SEC EDGAR, Reddit, X, and Telegram, taking promoted adapter coverage to 19 sources. The new layer provides sample events, masked credential status, raw archive writes, normalized events, fail-closed live fetches, and no signal/order authority. Historical backfill planning and a local sample-runner exist for 12 priority sources; Trust Score seed exists for all 35 sources, with 22 above 0.5 and three physical/logistics sources meeting the current seed threshold. Postgres/Timescale durable ingestion has a non-destructive status check and remains `ready_waiting_for_local_service` until local Postgres is running. `scripts/check_phase1_data_spine.py` is now the acceptance gate for registry count, 5-pipeline coverage, promoted adapter coverage, heartbeat-map consistency, safe credential-status shape, and a full 35-source deterministic ingestion run.

TradingView decision: a paid TradingView account does not provide a standard retail market-data API key for Qadam to pull bars, prices, indicators, or watchlists. Use TradingView MCP as read-only market/technical-analysis tooling through Codex/MCP without a TradingView login. Use the paid TradingView account later for webhook alerts, but only after Qadam has a secure authenticated webhook receiver that writes to the Event Log and cannot trigger execution.

Tier 1 order:

- ACLED.
- NASA FIRMS.
- Oref/Tzeva Adom.
- Polymarket.
- Kalshi.
- UnusualWhales.
- Alpaca.

Tier 2 order:

- FRED.
- GDELT.
- RSS feeds.
- AIS Maritime, using AISStream as MVP if Spire/MarineTraffic is unavailable.
- Wingbits.
- X API.
- TradingView alert path: D7 local observed-alert contract now; public webhook only after secure receiver exists.

Tier 3 order:

- BLS with FRED fallback.
- ECB.
- UN Comtrade.
- BIS.
- Reddit.
- Telegram.
- SEC EDGAR.
- STOCK Act / politician filings.
- USGS after scope decision.

Exit criteria:

- All 35 sources have adapter status: live, degraded, unavailable, or intentionally deferred.
- Tier 1 and Tier 2 sources write normalized events to Postgres.
- Historical backfills complete for ACLED, FRED, Alpaca, and other allowed sources.
- Initial Trust Score matrix exists.
- At least 20 sources score > 0.5.
- At least two physical/logistics sources pass trust and latency thresholds.

## 8A. Phase 1E - Agent And Skill Manifests

Objective: formalize the agent architecture before giving the local LLM, frontier LLM, quantum module, or execution adapters more authority.

Current implementation note: Phase 1E now has 8 validated agent manifests, 7 validated reusable skill bundles, 130 declared tool grants, 13 secret-name grants, and zero broker-write authority. Every agent sample output now carries explicit `execution_allowed=false`, `paper_order_allowed=false`, `broker_write_allowed=false`, and a boundary statement. The validation checks are wired into startup, and system health/cockpit expose Agent OS status.

New reference input:

- Anthropic's `financial-services` repo is a useful architecture reference for named financial workflow agents, reusable skill bundles, connector grants, managed-agent cookbooks, validation scripts, and secret-scan discipline.
- Qadam should adopt the modular file structure and permission model, not the licensed connector set.

Build:

1. Add an `agents/` manifest contract.
2. Create initial manifests for COO, Research Analyst, Strategy Lead, Head of Quant, Risk Agent, Signal Auditor, Execution Auditor, and Fund Manager Interface.
3. Add reusable `skills/` bundles for macro intelligence, prediction markets, physical anomaly monitoring, options and volatility flow, Akber 6-stage filter, private edge / world-model priors, and risk/postmortems.
4. Add a manifest checker that validates role, scope, source access, MCP tool grants, secret names, forbidden actions, and output schemas.
5. Add a deterministic skill-sync step so each agent gets only approved skills.
6. Add cockpit visibility for agent ownership and permission boundaries.

Operating rule:

- Live-capital work follows the Anthropic-style posture: agents draft, humans approve.
- First-release paper-mode trading remains different: Qadam may route guarded paper trades in the £100,000 paper account only after deterministic Risk Agent, execution venue, kill-switch, Q-CTRL/proof holds, and Event Log gates are built.
- No LLM agent ever receives direct broker write authority.

Exit criteria:

- Every named agent has a validated manifest.
- Every skill bundle is reusable and traceable to a single source.
- Every agent has explicit allowed and forbidden tools.
- Secret scanning covers agent and skill files.
- Paper execution authority is reserved for the future execution policy path, not the LLM prompt layer.

## 8B. Phase 1F - Agent Runtime Enforcement

Objective: enforce the manifest permissions at runtime before Qadam starts Phase 2 shadow intelligence.

Current implementation note: Phase 1F now has runtime tool authorization, broker-write hard blocks, undeclared-tool hard blocks, sample output fixtures for all 8 agents, and a local Research Analyst shadow triage queue. `scripts/check_phase1_agent_os.py` is now the acceptance gate for manifests, skills, runtime grants, authority flags, required per-agent tools, and fail-closed behavior. The check is wired into startup, and system health/cockpit expose Agent Runtime status.

Build:

1. Runtime authorization wrapper.
2. Tool-grant checks before tool use.
3. Sample output fixtures for every agent schema.
4. Local shadow triage queue.
5. MCP-style status and authorization tools.
6. Cockpit runtime permission status.

Exit criteria:

- Allowed tool calls pass only when explicitly granted.
- Missing-grant calls block.
- Broker-write tools block for every agent.
- Shadow triage packets remain local-only and non-executable.

## 9. Phase 2 - Intelligence Stack

Objective: run Gemma and Gemini end-to-end in shadow mode.

Current implementation note: Phase 2 has started with Evidence Trail and Proposed Signal contracts, deterministic keyword/anomaly triage, local Shadow Signal storage, optional model-list provider probes for Gemini and LM Studio, a Research Analyst queue runner, a live LM Studio/Gemma local Research Analyst assessment path, read-only paper-account context, the first Signal Integrity Gate, the first read-only Risk Agent policy router, and the first read-only Execution Policy / kill-switch router. `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` now feeds available read-only observations through the Research Analyst queue, runs local Gemma in shadow mode, reviews recent shadow signals through `orchestrator/signal_integrity.py`, reviews Signal Integrity and Trade Intent records through `orchestrator/risk_agent.py`, reviews Risk Agent outputs through `orchestrator/execution_policy.py`, and queues a Strategy Lead shadow handoff packet. Every shadow signal, local assessment, Signal Integrity review, Risk Agent policy review, Execution Policy review, and Strategy Lead handoff remains non-executable.

Build order:

1. Triage packet schema.
2. Keyword-filter fallback.
3. Gemma-compatible MLX runner.
4. Gemma profile: 50/100/200/300/450 stream latency curve.
5. Gemini async research queue with backpressure.
6. 100-persona swarm simulation.
7. Evidence-trail assembly.
8. Cognitive Conflict detection.
9. Shadow signal writer.
10. Intelligence Feed page.

Gemma rules:

- Trust Score > 0.6 and anomaly match passes to Gemini.
- Trust Score 0.3-0.6 requires corroboration within 2 hours.
- Trust Score < 0.3 is quarantined.
- MLX crash activates `degraded-triage`.

Gemini rules:

- Tail-mass gap >= 15 percentage points queues candidate for Quantum.
- Swarm dissent > 60% downgrades to watchlist.
- Low domain confidence raises evidence bar.
- Gemini failures retry 3 times, then hold in `pending-research` up to 6 hours.

Exit criteria:

- 100+ concurrent stream test passes within Gemma profile limits.
- Gemini produces probability distributions and dissent scores for at least 10 catalysts.
- Cognitive Conflict event can be manually injected and logged.
- Shadow signals are written with required fields.
- No shadow signal can place an order.

## 10. Phase 3 - Quantum Integration

Objective: connect weekly quantum jobs while preserving classical fallback.

Build order:

1. Classical Strategy Collapse fallback first.
2. Qiskit Aer validation.
3. QAOA Pattern Recognition job.
4. VQE Strategy Collapse job.
5. IBM Quantum / Qiskit Runtime backend.
6. AWS Braket backend.
7. Optional Q-CTRL Fire Opal integration.
8. Weekly APScheduler batch.
9. `quantum_profile.json`.
10. Quantum status in cockpit.

Quantum rules:

- Weekly oracle, not real-time dependency.
- Standard proof trades do not wait for Quantum unless strategy marks them Quantum-gated.
- Quantum can upgrade, downgrade, or hold a signal.
- Quantum cannot originate a signal or bypass risk gates.
- Google Quantum is not a v1 backend unless Google grants approved hardware access later.

Exit criteria:

- At least one Job 1 real-hardware run completes.
- At least one Job 2 real-hardware run completes.
- AWS Braket backend can run the same job contract or cleanly return `backend-unavailable`.
- Classical fallback emits structurally identical output.
- Malformed circuit is blocked before submission.
- `Q_threshold` is calibrated.

## 11. Phase 4 - Phase 1 Manifestation

Objective: produce the approved Manifested Strategy Document.

Build order:

1. Triple-Mirror Audit.
2. Gemma profile.
3. Gemini cognitive heatmap.
4. Quantum profile.
5. Data Veracity Audit.
6. RBI: Read, Backtest, Implement.
7. Candidate strategy generation.
8. Backtesting with costs, slippage, spread, and regime splits.
9. Manifested Strategy Document.
10. 6-Step Filter configuration.
11. Markov Regime Engine.
12. Ramin approval logged in Event Log.

Manifested Strategy must define:

- Target catalyst types.
- Source weighting per catalyst.
- Entry rules.
- Exit rules.
- Stop and invalidation rules.
- Option structure preferences.
- Kelly cap policy.
- Regime suppression rules.

Exit criteria:

- All three profiles are complete.
- `data_environment_map.json` is final.
- At least two candidate strategies are backtested.
- Selected strategy has positive expectancy after costs.
- Parameter sensitivity does not collapse under +/-10% threshold shifts.
- Strategy approval is logged.

## 12. Phase 5 - Layer B Orchestration

Objective: wire risk, execution, notifications, and kill-switches.

Build order:

1. Signal object state machine.
2. Signal schema integrity validator.
3. Risk Agent hard-cap table.
4. Kelly calculator.
5. Pre-trade gate.
6. Alpaca paper adapter.
7. Prediction-market adapter experiments behind hard wrappers.
8. Kill-switch panel and event model.
9. Telegram Bot communications rail: dry-run outbox, safe templates, cockpit Communications panel, then one private test send.
10. Signal Review page for policy-required approval.
11. First paper execution drill.

6-Step Filter:

| Layer | Gate | Pass criterion |
| --- | --- | --- |
| 1 | Low Volatility / IV Suppression | IV percentile < 20th and catalyst window < 90 days |
| 2 | Options Distribution Gap | Tail mass diff >= 15pp |
| 3 | Catalyst Identification | Specific, dated, novel, dissent < 60% |
| 4 | Technical Setup | Structural entry, R:R >= 1:3, supportive/neutral regime |
| 5 | OBV / Volume Intelligence | Confirmatory or neutral |
| 6 | Approval Policy Router | Test auto-approval or live policy/human approval |

Risk caps:

| Scope | Cap |
| --- | --- |
| Defined-risk options | 2% standard; 5% absolute max for rare high-conviction setups |
| Prediction markets | 1% of bankroll |
| Other instruments | 2% of bankroll |
| Strategy daily loss | 3% |
| Strategy weekly loss | 7% |
| Portfolio daily loss | 5% |
| Portfolio max drawdown | 20% |
| Open exposure | 30% |
| Single instrument | 10% |

Pre-trade gate:

1. Valid approval state.
2. Quantum Ambiguity Score below threshold when required.
3. Hard caps satisfied post-fill.
4. Regime is not `risk_off`, unless explicitly allowed.
5. Broker heartbeat healthy.
6. Event Log write within last 60 seconds.
7. No active kill-switch.
8. Agent-accessible CLI orders pass through wrappers.

Kill-switches:

- Global.
- Strategy.
- Venue.

Auto-resume is never allowed.

Exit criteria:

- Risk Agent blocks cap violations.
- All three kill-switches fire, log, and alert.
- Paper order opens, fills, closes, and logs every transition.
- Telegram alerting works for drawdown, broker failure, kill-switch, Event Log silence, trade lifecycle updates, and insight digests.
- Telegram has no command path for placing, approving, rejecting, modifying, closing, or resizing trades.
- Telegram delivery, retry, failure, and suppression are logged.

## 13. Phase 6 - Postmortem & Learning Loop

Objective: every closed trade becomes learning input.

Build order:

1. Postmortem packet schema.
2. Catalyst Analysis sub-agent.
3. Pricing Analysis sub-agent.
4. Regime Analysis sub-agent.
5. Execution Analysis sub-agent.
6. Override Analysis sub-agent.
7. Reducer.
8. Bayesian weight updater.
9. Knowledge Graph write path.
10. Shadow Strategy runner.
11. Architect Agent metrics.
12. Monthly Reflective Manifestation workflow.

Knowledge Graph entries include:

- catalyst details
- physical signals
- market signals
- Gemini swarm output
- Quantum pattern clusters
- actual outcome
- trade outcome
- regime at detection
- lead time before mainstream consensus

High-Correlation Cluster rule:

- If a catalyst type has at least 20 resolved instances and > 80% thesis-direction resolution, Risk Agent may raise Kelly ceiling up to the hard cap.
- If win rate decays below 70% over the next 20 trades, demote the cluster.

Exit criteria:

- Every closed paper trade gets a Postmortem Packet within 24 hours.
- Knowledge Graph contains resolved catalyst entries.
- Bayesian weight changes are visible in System Health.
- Shadow Strategy comparison is visible.
- Architect Entropy gauge reacts to degraded-source injections.

## 14. Phase 7 - Demo Proof And Maturity Benchmark

Objective: prove the system before live capital.

Clean proof rules:

- Layer A watches 24/7.
- Test-mode Approval Policy Router auto-approves qualifying signals after Layers 1-5.
- The founding Fund Managers observe but do not approve, reject, defer, modify, close, or adjust individual demo trades.
- Layer B executes sizing, order placement, monitoring, exit, and postmortem.
- Kill-switches, strategy toggles, and comments/forum suggestions are allowed and logged.
- Manual trade-level intervention voids the clean proof sample.

Evaluation:

- 30 consecutive calendar days of autonomous operation.
- £100,000 starting paper/test account.
- 3 proof trades per week where qualified setups exist.
- The weekly proof target is `min(3, qualified_setup_count)` so Qadam never
  forces trades to hit a quota.
- 100 closed trades is the mature statistical benchmark.
- If 30 days pass with fewer than 100 closed trades, do not force trades; mark
  the run statistically immature and continue paper until the mature benchmark
  exists.
- At least two contributing strategies.
- Expectancy > 0 after costs.
- Max drawdown <= 20%.
- Zero manual trade-level overrides.

Live promotion:

- Full meta-review.
- Seven-day cooling-off period.
- Ramin structured approval logged.
- Live credentials loaded after approval only.
- First 30 live days run half-size.
- Material live/paper divergence returns system to paper mode.

## 15. Cockpit Build Requirements

`qadam.trade` is the login surface and command cockpit for the founding Fund Managers: Ramin, Troy, Akber, Anas, and Ion. It starts as a landing page, but the authenticated experience is a system-map dashboard showing how the entire hybrid fund is wired together: Python COO, local LLM Research Analyst, frontier LLM Strategy Lead, quantum Head of Quant, data pipelines, Event Log, Knowledge Graph, Risk Agent, broker adapters, notifications, kill-switches, and internal comments/forum notes.

Immediate dashboard design decision: the cockpit's main view is a diagrammatic system map, not a generic card grid. Every node must show status. The supporting views are a read-only process console, Fund Manager view, trade layer, and comments/forum area. The first-month trade layer must show the £100,000 paper/test account, TradingView-assisted market view, live-capital block, and the full trade reasoning chain from catalyst to postmortem.

Current deployment anchor:

- Vercel project: `qadam`, ID `prj_apm3Zfd9fpWq4wsJiSunkVmxdCVQ`.
- Team/org ID: `team_Qv7iJDGRobHFyiyUsMUbVxyy`.
- Local link file: `cockpit/.vercel/project.json`.
- Read-only verification command: `./scripts/inspect_vercel_project.sh`.
- Deploy command when approved: `./scripts/deploy_cockpit_vercel.sh`.

Deployment policy:

- Do not overwrite the live landing page accidentally.
- Keep the unauthenticated landing page and authenticated cockpit as separate experiences until the routing plan is explicit.
- Preferred production shape: `qadam.trade` remains the landing page, while logged-in users enter the cockpit through Supabase Auth and land on the System Map.
- Local cockpit route shape now exists: `/` public entry, `/login`, `/sign-in` alias, `/sign-up`, `/dashboard`, and `/settings`.
- The live top-right navigation must change from only `Read Whitepaper` to include `Login`.
- `Login` must route to Supabase Auth, then redirect authenticated users to the System Map dashboard.
- Supabase Auth access must be allowlisted to Ramin, Troy, Akber, Anas, and Ion for the first release.
- `/dashboard` must be protected; unauthenticated users redirect to login.
- `/login` or `/sign-in` must exist as the canonical auth entrypoint.
- Before production deployment, update the Vercel project framework/root settings to match the chosen app layout.
- Keep Vercel tokens local only; use strict local secret files or the platform secret store, never committed config.

Pages:

- Dashboard / System Map.
- Signal Review.
- Trade Journal.
- Strategies.
- Postmortems.
- Intelligence Feed.
- System Health.
- Settings.
- Internal Comments / Suggestions.

Design and safety requirements:

- Information density over aesthetics.
- All data comes from Event Log or signal store through Orchestrator API.
- Kill-switches are always one click away.
- Degraded states are loud.
- The first authenticated page is a system map, not a marketing page.
- The system map shows module connectivity, health, uptime, last heartbeat, current process state, and degraded/fallback state.
- Modules represented on the map: Python COO, local LLM, frontier LLM, quantum backend, Architect Agent, Event Log, Knowledge Graph, Trust Score service, Risk Agent, broker adapters, Telegram Bot notifier, all five live World Monitor pipelines, and the Qadam Resource Registry / reference-provenance layer.
- Data sources can be expanded from each pipeline node to show live/degraded/unavailable status and last successful ingestion.
- Resource Registry entries can be expanded separately to show which strategy reference, paper, product benchmark, or open-source stack informed a module.
- Dashboard LCP target <= 500ms locally.
- Dashboard and Signal Review use server-side rendering.
- No cockpit page fetches data outside its contract.
- No public community, Discord layer, or external API in v1. The only discussion surface is the private founding Fund Manager comments/forum area.

Phase 0 cockpit requirements:

- Static content shell.
- System-map layout stub with module nodes and pipeline groups.
- Live landing page top-right Login entrypoint.
- Supabase login route.
- Authenticated redirect to Dashboard / System Map.
- Protected `/dashboard` route.
- Founding Fund Manager allowlist.
- Internal comments/forum stub.
- Nav with kill-switch buttons.
- `COCKPIT.md` data-contract template.
- Web vitals endpoint writing to Event Log.

Phase 5 cockpit requirements:

- Functional Dashboard / System Map connected to Orchestrator health, heartbeat, source registry, process status, and uptime data.
- Functional Signal Review.
- Functional internal comments/forum linked to modules, signals, strategies, and postmortems.
- Kill-switch panel first in DOM tree.
- Telegram Communications panel showing bot status, dry-run/live-send mode, verified/pending members, pending messages, failed sends, suppressed sends, and last delivered trade/insight update.
- Telegram deep-link prewarming without execution authority.

## 16. Metrics And Review Cadence

Primary metric:

- Expectancy = win rate x average R-win minus loss rate x average R-loss.

Trade-level:

- Expectancy.
- R-multiple distribution.
- Win rate with R context.
- Catalyst-Correct Rate.
- Brier Score.

Portfolio-level:

- Max drawdown.
- Sharpe.
- Sortino.
- Rolling 30-day Expectancy.

System intelligence:

- Alignment Score.
- Cognitive Drift Rate.
- Signal Funnel Conversion.
- Trust Score Distribution.
- Knowledge Graph Growth Rate.
- Quantum Job Success Rate.

Override analytics:

- Override Rate.
- Override-Reason Hit Rate.
- Regret Metric.

Review cadence:

- Daily: 5-minute cockpit review.
- Weekly: funnel, overrides, Trust Scores, Quantum success, rolling expectancy.
- Monthly: full metric set, Reflective Manifestation, Shadow Strategy, Knowledge Graph, Brier Score.
- 30-day: full demo proof review and live decision-readiness review.

## 17. Markdown-First Agent And Skill Structure

The repository must move toward the canonical structure in `qadam-specs.md`, sharpened by the Anthropic `financial-services` reference pattern.

Every agent folder contains:

- `agent.md` for role, scope, operating doctrine, escalation, and forbidden actions.
- `permissions.json` for allowed sources, resources, tools, secrets-by-name, and connector grants.
- `skills/` references to approved reusable bundles.
- `schemas/` for typed outputs.
- Optional `commands/` only when command capability is explicitly safe and declared.
- Fallback instructions for degraded mode.

Critical rule:

- No agent logic lives in Orchestrator Python. Orchestrator Python is plumbing. Markdown files are the routing and reasoning layer.
- No agent can call an undeclared connector, shell command, web fetch, broker endpoint, or secret.
- Broker writes are never exposed directly to an LLM agent; they pass through deterministic policy and execution adapters.

Required agent docs:

- `ORCHESTRATOR.md`
- `WORLD_MONITOR.md`
- `TRIAGE.md`
- `RESEARCH.md`
- `QUANTUM.md`
- `RISK.md`
- `EXECUTION.md`
- `POSTMORTEM.md`
- `ARCHITECT.md`
- `STRATEGY.md`
- `KNOWLEDGE_GRAPH.md`
- `COCKPIT.md`

Required reusable skill bundles:

- `MACRO_INTELLIGENCE.md`
- `PREDICTION_MARKETS.md`
- `PHYSICAL_ANOMALY_MONITORING.md`
- `OPTIONS_VOLATILITY_FLOW.md`
- `AKBER_6_STAGE_FILTER.md`
- `PRIVATE_EDGE_WORLD_MODEL.md`
- `RISK_AND_POSTMORTEMS.md`

Required checks:

- Manifest validation.
- Skill-reference validation.
- Tool-grant validation.
- Secret scan over agent and skill files.
- Cockpit-visible agent ownership map.

## 18. Non-Blocking Decisions

These are decisions to resolve before production-grade adapters, but they do not block foundation work:

1. AIS: accept AISStream as v1 maritime MVP, or require Spire/MarineTraffic first?
2. Oref: formalize Tzeva Adom primary plus Oref fallback, or strict Oref polling?
3. USGS: earthquake, commodity/minerals, or both?
4. STOCK Act: choose canonical politician-trade data source.
5. Licensing: reimplement World Monitor behavior rather than copy AGPL code unless Qadam is AGPL-compatible.

Default assumptions:

- Use AISStream as maritime MVP.
- Use Tzeva Adom/Oref practical fallback path.
- Implement USGS as a source family if low-friction.
- Reimplement World Monitor behavior.
- Missing paid credentials degrade source status during local development.
