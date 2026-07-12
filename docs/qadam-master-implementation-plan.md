# Qadam Master Implementation Plan

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

This is the control document. Read this first. The other docs are supporting appendices, not competing plans.

## 2026-05-27 Paper Growth Operating Target

Qadam's active paper mandate is no longer described to users as "Phase 7".
The current target is a 60-day paper growth trial: grow the GBP 100,000 paper
portfolio to GBP 200,000 while keeping live capital disabled. This is a
high-conviction paper simulation, not a small-trade demo. Qadam should wait for
event-driven, evidence-gated probability or pricing-mispricing setups and take
selective larger paper positions only when Strategy Lead, Signal Integrity,
Risk Agent, Q-CTRL/quant consultation, execution policy, and Alpaca Paper gates
agree.

The historical 30-day proof artifacts remain as compatibility and maturity
records, but they no longer block paper-live certification. Paper-live
certification is now the permission to operate the paper system under the
60-day growth trial, with live broker endpoints and live capital still disabled.

## 2026-05-26 Quantum And PaperOps Runtime Update

Qadam now treats Q-CTRL Fire Opal as a mandatory paper-parity provider rather
than an optional note. The PT-1 guarded provider probe authenticates
successfully for the `qadam` organization and records
`qctrl_paper_consultation_ready`, `product_access_verified=True`,
`provider_call_succeeded=True`, and `product_access_blocker=none`. The Q-CTRL
submit hold is clear.

The Fire Opal on IBM Quantum guide is captured in
`scripts/check_qctrl_fire_opal_ibm_quantum.py`. Current state:
`fire_opal_product_access_verified=True`, `fire_opal_sdk_importable=True`,
`qiskit_importable=True`, `qiskit_ibm_runtime_importable=True`,
`qctrl_organization_slug_configured=True`, and
`status=blocked_missing_ibm_quantum_credentials` because
`IBM_QUANTUM_TOKEN` and `IBM_QUANTUM_INSTANCE` are not yet configured locally.
This gate is readiness and device discovery only; hardware submission remains
separately blocked.

Update on 2026-05-28: strict `.env.local` is now an accepted local secret
fallback after `data/runtime/qadam-secrets.env`, so IBM Quantum token and
instance values can be visible to the Python runtime without being committed or
printed. The closeout gate is:

```bash
.venv/bin/python scripts/check_qadam_paper_closeout.py
```

This gate separates required paper-operation blockers from optional quality
gaps. With IBM credentials visible, Fire Opal plus IBM Quantum now records the
latest explicit read-only device probe result in the runtime artifact. A
sanitized provider-network failure remains an optional quality gap; it does not
grant hardware-job, broker, paper-order, or live-capital authority.

Telegram paper-trade notifications are also split from the general Telegram
member outbox. The general outbox stays dry-run and commandless; the
submitted-paper-order group rail can be enabled as outbound-only transport after
`TELEGRAM_GROUP_CHAT_ID` is present.

PaperOps is now `ready_for_full_paper_ops`. The safe cycle reports
`paper_cycle_full_paper_operational_ready` with 34/34 commands passing. One
Alpaca paper order was submitted and accepted, and the lifecycle poller mirrors
it as a submitted order with no fill yet. This 2026-05-26 blocker statement was
superseded on 2026-05-27 by the 60-day paper growth target above.

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
| Dashboard appendix | `docs/qadam-dashboard-implementation-plan.md` | Cockpit/system-map/trade-layer implementation path. |
| Dashboard UX overhaul appendix | `docs/qadam-dashboard-overhaul-master-implementation-plan.md` | Control plan for replacing the long cockpit page with a segmented Overview, Trades, Sources, Reasoning, Performance, Operations, and Governance experience. |
| Dashboard Stage 7 simplification appendix | `docs/qadam-dashboard-stage-7-simplification-implementation-plan.md` | Plan-only next dashboard UX pass for making the cockpit simpler without making it simplistic: operating map, system status, data sources, strategies, activity feed, trade consideration board, and paper portfolio capacity. |
| Telegram appendix | `docs/qadam-telegram-bot-implementation-plan.md` | Member communications rail, bot phases, message classes, and dashboard visibility. |
| OSS reference appendix | `docs/qadam-oss-reference-implementation-plan.md` | Implementation overlay for adopting useful patterns from external financial-agent, terminal, MCP, chat, and durable inbox repos without importing unsafe execution authority. |
| Reddit narrative proxy appendix | `docs/qadam-reddit-narrative-proxy-implementation-plan.md` | Plan for filling the Reddit API gap with a no-key ApeWisdom aggregate retail-attention bridge while keeping Reddit OAuth as a later optional upgrade. |
| Trading edge realization appendix | `docs/qadam-trading-edge-realization-plan.md` | Multi-stage plan for turning Qadam's architecture edge into fresh setup identity, candidate generation, strategy routing, market confirmation, risk sizing, exits, postmortems, and idle-state diagnosis without relaxing paper-only safety. |
| Quantum Edge hybrid-loop appendix | `docs/qadam-quantum-edge-hybrid-loop-implementation-plan.md` | Active 15-stage plan for parallel classical and quantum-assisted pattern recognition, Fire Opal on IBM evidence generation, Pattern Recognition and Quantum Edge public surfaces, validated strategy lineage, and guarded paper-only downstream integration. |
| QSASE appendix | `docs/qadam-qsase-implementation-plan.md` | Evolution plan for Qadam's Self-Aware Strategy Engine: universal source-price pattern discovery, linear and nonlinear backtesting, strategy foundry, Akber filter integration, quantum review, strategy routing, and guarded PaperOps handoff. |
| User guide | `docs/qadam-user-guide.md` | Full beginner operating manual for using Qadam, reading the cockpit, reviewing demo-proof trades, and preserving safety boundaries. |
| Live source appendix | `docs/api-source-inventory.md` | 35 live/live-adjacent feeds and source conflicts. |
| API credential appendix | `docs/api-specs.md` | Full API/provider inventory, credential placeholders, onboarding batches, and current provider decisions. |
| API key acquisition plan | `docs/qadam-api-key-acquisition-plan.md` | Practical provider-by-provider order, cost posture, official links, and validation checks for getting keys safely. |
| Pre-Phase-3 readiness appendix | `docs/qadam-pre-phase-3-implementation-plan.md` | Modular checklist for completing Phase 0, Phase 1, Agent OS, Phase 2, durable replay, safety-chain, and cockpit gates before Phase 3 resumes beyond scaffold mode. |
| Phase 3 appendix | `docs/qadam-phase-3-implementation-plan.md` | Staged provider/scheduler readiness plan for Head of Quant work after pre-Phase-3 certification. |
| Phase 6 appendix | `docs/qadam-phase-6-learning-loop-implementation-plan.md` | Staged learning-loop plan from Q6-0 re-entry through Q6-17 certification, preserving plan-only handoff boundaries until each gate passes. |
| Legacy paper-proof appendix | `docs/qadam-phase-7-demo-proof-implementation-plan.md` | Historical 30-day proof/maturity plan retained for compatibility, not the user-facing paper mandate. |
| Paper Operational appendix | `docs/qadam-paper-operational-mode-plan.md` | Control plan for making Qadam fully operational in paper mode before any live-capital path exists. |
| Resource appendix | `docs/qadam-resource-registry.md` | Papers, products, OSS stacks, frameworks, build references. |
| Private worldview appendix | `docs/how-the-world-works-integration.md` | Qadam's private world-model foundation and evidence boundary. |

Rule: update this master plan when the build sequence changes. Update appendices only when implementation detail changes.

## 3. The Three Knowledge Layers

Qadam should not mix all inputs into one bucket.

| Layer | What It Contains | What It Does |
| --- | --- | --- |
| Live Source Registry | ACLED, FIRMS, Oref, UnusualWhales, Polymarket, Kalshi/OddsPipe, Alpaca, GDELT, Telegram, RSS, TradingView alerts, etc. | Feeds the machine with observable data and heartbeat status. |
| Resource Registry | Papers, open-source tools, product references, analytical frameworks, build inspiration. | Guides architecture, signal design, UX, and research methods. |
| Private World-Model Corpus | `how-the-world-works/` | Quietly shapes Qadam's suspicion, hidden-incentive reasoning, scenario generation, and narrative analysis. Currently 4 markdown files. |

Operational boundary:

- Live sources can become evidence.
- Resources can become design inputs.
- The private world-model can become a lens and prior.
- Only corroborated, logged, auditable evidence can affect trades.

### Trading Philosophy

Qadam's trading philosophy is not chart-first. It is world-model first, evidence-gated second, and risk-authorized last.

The `how-the-world-works/` corpus powers the questions Qadam asks before a trade exists. It pushes Qadam to inspect power hierarchy, energy and security dependencies, monetary plumbing, institutional self-preservation, narrative asymmetry, US-China strategic bargaining, and hidden coordination risk. This is the private philosophical foundation behind Qadam's suspicion, scenario generation, and market-channel watchlists.

That foundation is not allowed to become proof by itself. In the trading chain, the worldview creates hypotheses and observable signatures; live sources must corroborate them; the Akber 6-stage filter must structure them; the Signal Integrity Gate must validate them; and the Risk Agent must authorize sizing before the paper rail can act. The dashboard must therefore show the worldview lens beside each decision while clearly labelling it as a private prior, not evidence or execution authority.

### Trading Edge Realization Roadmap

The next quality-throughput layer is defined in `docs/qadam-trading-edge-realization-plan.md`. Its purpose is to make Qadam better at converting observations into fresh, distinct, evidence-backed paper candidates without weakening any safety gate. The plan covers Fresh Setup Identity v2, a Trade Candidate Factory, Strategy Router, second-order AI infrastructure universe, market confirmation layer, dynamic risk sizing, exit intelligence, postmortem-driven weight proposals, durable replay watchdog, idle-state diagnosis, and final paper-autonomy certification refresh.

This roadmap does not grant new live-capital authority. It preserves the rule that Qadam may submit multiple Alpaca paper trades per day only when distinct qualified setups pass source quorum, market confirmation, Signal Integrity, Strategy Lead review, Head of Quant shadow annotation where applicable, Risk Agent sizing, Execution Policy, kill-switch, idempotency, Event Log, broker-readiness, and reconciliation gates.

### QSASE Evolution Roadmap

The next metamorphosis layer is defined in `docs/qadam-qsase-implementation-plan.md`. QSASE turns Qadam's existing strategy, learning, source, model, quantum, and PaperOps machinery into a self-reflective strategy operating system. It first searches the entire data universe against the entire trading universe, then uses linear backtesting, nonlinear and quantum pattern review, Akber's filter, shadow replay, and guarded strategy routing to decide which strategies should be studied, rejected, shadow-tested, or sent to PaperOps paper review.

QSASE does not grant execution authority. It cannot bypass source quorum, Signal Integrity, Strategy Lead review, Head of Quant review, Risk Agent sizing, Execution Policy, idempotency, the guarded Alpaca Paper route, proof-ledger rules, or the live-capital boundary.

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
| TradingView MCP / Alerts | Read-only technical-analysis MCP tooling now; paid TradingView account alert webhooks later. |
| Yahoo Finance / yfinance Market Data | Supplemental read-only market confirmation from the local `yahoo-finance-api/` reference checkout: OHLCV, volume, options chains, market status, quote search, news, sectors, and screeners. Not a broker, not an execution venue, and not canonical source number 36 unless the registry is deliberately changed. |
| Knowledge Graph | Resolved catalyst memory and nearest-neighbour recall. |
| Cockpit | `qadam.trade` login, dashboard, system map, signal review, comments forum, postmortems. |
| Fund Manager Forum | Private suggestions and governance comments from Ramin, Troy, Akber, Anas, and Ion. |
| Telegram Bot Communications And Intake | Outbound member alerts for trade lifecycle updates, insight digests, system warnings, and dashboard links; inbound read-only member research intake for world-event datapoints and strategy considerations. No execution authority. |
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
- No Telegram command can place, modify, close, approve, reject, or resize a trade.
- Telegram messages must be derived from structured Event Log/status records, not raw model text.
- Telegram inbound messages may create sanitized world-event datapoints,
  Research Analyst review packets, or Strategy Lead considerations only; they
  cannot create trade candidates, orders, broker writes, Q-CTRL jobs, or live
  capital authority.
- Never create a new order intent through retry. Live-capital POST retries are
  disallowed. Alpaca paper-submit retries are allowed only on the guarded
  paper route, only for timeout, HTTP 429, or HTTP 5xx, only with the same
  idempotency key, and only inside the configured max-attempt contract.
- Venue account/subaccount/network scope must be explicit before any order path is enabled.
- Quantum is a weekly oracle, not a real-time trading brain.
- Three proof trades per week is a Phase 7 discipline target only where
  qualified setups exist; it is not a quota.
- 100 closed trades is the maturity benchmark.

## 6. First Release Trial Mode

The first release of Qadam is a local-first autonomous trial system.

Operating constraints:

- Account: £100,000 test/paper account.
- First-month sprint: use the £100,000 paper account as the proof surface, with TradingView as the visible market/chart layer and later alert source, before any live-capital path exists.
- Execution: Qadam may submit guarded paper trades after the paper-only gates
  are met: qualified setup, Signal Integrity, Risk Agent, Execution Policy,
  kill-switch, idempotency, Event Log prewrite, broker-readiness, and
  reconciliation. Live capital remains unavailable.
- Capital boundary: no live capital in the first release.
- Access boundary: first-release login is limited to Ramin, Troy, Akber, Ion, Dan, and pending Anas.
- Current allowlist emails: Ramin `raminhoodeh@gmail.com`, Troy `troycookecareer@gmail.com`, Akber `akber.ali@hotmail.co.uk`, Ion `isioras@yahoo.co.uk`, Dan `danmerdad@hotmail.co.uk`.
- Pending allowlist emails: Anas.
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
- The cockpit must show the full trade lifecycle: signal, risk check, trade candidate, paper order, open position, exit/invalidation, and postmortem.

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
- API Specs appendix covering all 35 canonical World Monitor sources, model providers, quantum providers, broker rails, notification services, and optional `world-monitor/` reference providers, with placeholders only.
- Resource Registry from `qadam-general-context.md`.
- Private World-Model Corpus registry from the 4 markdown files in `how-the-world-works/`.
- Disabled Execution Venue Registry shaped by PriveX Starter lessons: read-only first, explicit account/subaccount/network scope, auth errors separated from transient errors, and no automatic POST retries.
- FastMCP tools: `ticker_echo`, `source_registry`, `source_detail`, `resource_registry`, `world_model_claim`, `system_health`, `module_map`.
- Agent/skill manifest plan shaped by Anthropic's `financial-services` reference: named workflow agents, reusable skill bundles, explicit connector grants, manifest validation, and secret scanning.
- Local Next.js cockpit shell with public `/`, protected `/dashboard`, System Map, and settings route retained as the richer server-rendered cockpit target.
- Live static cockpit workaround deployed through `landing-page-repo`: `/login/`, `/sign-up/`, and `/dashboard/` are real static routes on `qadam.trade`.
- Supabase Auth login/sign-up is live through the browser client, with founding Fund Manager allowlist enforcement before opening `/dashboard/`.
- Vercel is linked to the existing `qadam.trade` project; both `qadam.trade` and `www.qadam.trade` are explicitly aliased to the live static deployment.
- Dashboard Plan D0 is frozen: the current live shell is the baseline and should not gain more hardcoded claims.
- Dashboard Plan D1 status contract exists through `orchestrator/cockpit_status.py`, `scripts/export_cockpit_status.py`, and `scripts/check_cockpit_status.py`.
- The D1 exporter writes `data/runtime/cockpit-status.json` locally and `landing-page-repo/status/cockpit-status.json` as the static-safe site snapshot.
- Dashboard Plan D2 renderer exists in `landing-page-repo/dashboard.js`; the static dashboard now reads `status/cockpit-status.json` after Supabase allowlist login and renders modules, sources, cognition, forbidden actions, trade state, capital fields, and process console from the contract.
- Dashboard Plan D3 Watching View exists locally: the contract and static dashboard show all 35 registered sources under 5 pipeline groups with readiness, credential state, adapter state, degraded reason, trust placeholder, and heartbeat time; D7 appends TradingView paid alerts as an observed market alert source.
- Dashboard Plan D4 Cognition View exists locally: the contract and static dashboard show current focus, model activity, shadow packets, hypotheses, evidence packets, missing corroboration, analysis timeline, and blocked-by-reason state.
- Dashboard Plan D5 Trade Intent Board exists locally: `orchestrator/trade_intent.py` stores local trade intent records, `scripts/check_trade_intent.py` validates one candidate and one blocked test intent, and the static dashboard renders those records without broker authority.
- Dashboard Plan D6 Paper Account Mirror exists locally: `orchestrator/paper_account.py` stores the read-only paper-account mirror, `scripts/check_paper_account.py` validates no live capital and no write authority, `scripts/check_alpaca_paper_mirror.py --live` refreshes Alpaca balance, positions, orders, and P&L through GET-only calls, and the static dashboard renders the sanitized account state from the public-safe status contract.
- Dashboard Plan D7 TradingView Alert Source exists locally as an intake contract: `orchestrator/tradingview_alerts.py` stores observed TradingView chart alerts, deduplicates them, writes safe Event Log entries, and exports them to the cockpit as observed signals only.
- Dashboard worldview integration exists locally: `orchestrator/cockpit_status.py` exports `decision_philosophy` from the 4-file `how-the-world-works/` corpus, and the static cockpit renders the worldview lens in the system map, Private Edge panel, hypothesis cards, and each observed-signal/trade decision card.
- Telegram Bot communications plan exists: `docs/qadam-telegram-bot-implementation-plan.md` defines outbound-only member alerts, local bot token storage, local chat-ID registry, dry-run outbox, message templates, dashboard Communications panel, and no trade execution authority.
- Protected User Guide exists locally: `docs/qadam-user-guide.md` is the source guide, and `landing-page-repo/guide/index.html` is linked from the dashboard with Supabase allowlist protection.
- Founding Fund Manager access list: Ramin, Troy, Akber, Ion, Dan, Anas pending.
- Initial email allowlist: `raminhoodeh@gmail.com`, `troycookecareer@gmail.com`, `akber.ali@hotmail.co.uk`, `isioras@yahoo.co.uk`, `danmerdad@hotmail.co.uk`; Anas pending.
- Local comments/forum schema for signal, module, strategy, and postmortem suggestions.
- Foundation check script expanded as the build grows.

Exit gate:

- Local startup verifies registries, health, config, and storage.
- Event Log writes and replays a test event through the local fallback.
- Timescale migration exists for the durable Postgres Event Log target.
- Local storage paths are created and permission-checked.
- Source Registry, Resource Registry, and World-Model Corpus are distinct.
- Execution venues are visible but disabled/read-only; no venue can place orders.
- Live static cockpit renders the System Map after Supabase login.
- The live cockpit clearly marks itself as a static web shell while the local MacBook orchestrator remains private and not exposed to Vercel.
- The D1 cockpit status contract validates in paper mode, blocks live capital, exports modules/sources/forbidden actions, and strips secrets, emails, local paths, raw payloads, and broker authority.
- The D2 dashboard renderer populates key cockpit panels from the D1 snapshot and keeps empty trade/P&L states explicit.
- The D3 Watching View renders all registered sources from the public-safe snapshot without exposing secret names or local paths.
- The D4 Cognition View renders shadow-only reasoning state from the public-safe snapshot without exposing raw references or implying execution authority.
- The D5 Trade Intent Board renders candidate and blocked trade-intent records from the local store, with `execution_allowed=false`, `paper_order_allowed=false`, and no staged/submitted/open paper-trade state.
- The D6 Paper Account Mirror renders the £100,000 paper account state from local read-only data, with `write_authority=false`, `live_capital_enabled=false`, and 0/100 maturity until closed paper trades exist.
- The D7 TradingView alert contract renders alert-derived observed signals with duplicate protection, receiver-key fail-closed behavior, `execution_allowed=false`, `paper_order_allowed=false`, and `trade_candidate_created=false`.
- The cockpit renders Qadam's private worldview as decision context for hypotheses, observed signals, candidates, and blocked trades, while preserving the boundary that world-model claims are private priors and not factual evidence or trade triggers.
- Telegram communications are represented as notify-only: bot status, queue state, delivery state, verified/pending member counts, and last message status can appear in the cockpit, but no Telegram route can trigger broker action or hidden approval.
- The protected guide explains Qadam from first principles, including access, cockpit panels, status labels, trade states, demo-proof rules, member permissions, local operator checks, troubleshooting, and red flags without exposing secrets or implying execution authority.
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
- `scripts/check_phase1_data_spine.py` is the Phase 1 acceptance gate tying the source registry, heartbeat map, promoted adapter set, and full 35-source deterministic ingestion run into one read-only contract check.
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
- `scripts/start_postgres_timescale_ingestion.sh` now exists as the dedicated Postgres/Timescale durable-ingestion bootstrap. It starts only the Timescale-backed Postgres service, waits for connectivity, applies migrations, seeds durable reference/world-model data, writes all 35 deterministic source observations, runs the live-required ingestion contract, and verifies replay coverage.
- `scripts/check_postgres_timescale_replay.py --require-full-source-coverage` verifies that durable observations can be replayed across the full 35-source registry without writing new rows.
- Current local state as of 2026-05-21: OrbStack provides the Docker-compatible runtime, `qadam-postgres` is running locally, `scripts/start_postgres_timescale_ingestion.sh` completes with `postgres_timescale_durable_ingestion=ok`, and strict replay verification sees all 35 canonical sources in `source_observation`.
- A read-only Phase 1 live adapter promotion layer now exists for ACLED, STOCK Act via the Apify Capitol Trades Scraper, Polymarket, Kalshi/OddsPipe, Alpaca, AIS, Space-Track/CelesTrak, Wingbits, BLS, ECB, USGS, UN Comtrade, SEC EDGAR, Reddit, X, and Telegram. UnusualWhales remains intentionally disabled unless re-selected.
- These 17 adapter contracts join the already promoted GDELT, Oref, NASA FIRMS, FRED, and RSS adapters, taking promoted adapter coverage to 22 sources.
- The new adapter layer has sample mode, masked credential status, raw payload archival, normalized events, degraded-state handling, and fail-closed live fetches.
- `scripts/check_phase1_live_source_hardening.py` is now the Phase 1 live-source hardening gate. It validates each of the 22 promoted sources one by one, writes `data/runtime/phase1_live_source_validation.json`, appends a local history file, and classifies every source as `live`, `degraded`, `missing_credentials`, or `sample_ready`.
- `scripts/check_source_registry_blockers.py` is the explicit regression gate for the former eight stale source blockers. It requires zero legacy `needs_*` unresolved sources, confirms STOCK Act/USGS/Space-Track/AIS provider decisions, and confirms the clear market adapters are promoted read-only contracts.
- `scripts/check_supplied_credentials.py` is now the supplied-credential validation gate for NASA FIRMS, FRED, ACLED, Alpaca paper, Telegram, Gemini, LM Studio, plus explicit Kalshi deferred and UnusualWhales missing states.
- `scripts/refresh_acled_token.py --write --validate-read` is now the ACLED token refresh automation. It uses the refresh-token grant first, falls back to local email/password only when needed, atomically updates `data/runtime/qadam-secrets.env`, and writes a redacted local refresh report.
- `scripts/check_alpaca_paper_mirror.py --live` is now the Alpaca paper-account mirror gate. It calls only GET endpoints for account, positions, orders, and portfolio history, writes sanitized local mirror files, exposes balance/P&L/positions/orders to the cockpit, and preserves `write_authority=false`, `live_capital_enabled=false`, and `paper_order_allowed=false`.
- Current live read-only validation on 2026-05-18: live sources are NASA FIRMS, FRED, RSS, Polymarket, Alpaca paper account mirror, BLS public sample, ECB public exchange-rate series, SEC EDGAR public filing metadata, and Telegram bot status. Degraded but explicit sources are GDELT, Oref, and ACLED. Missing/deferred credential sources are UnusualWhales, Kalshi, AIS Maritime, Wingbits, UN Comtrade, Reddit, and X/Twitter.
- Current supplied-credential validation on 2026-05-21: NASA FIRMS, FRED, Alpaca paper, Telegram, Gemini, and LM Studio are live when network/localhost access is available; ACLED token refresh succeeds but the provider read remains degraded with HTTP 403; Kalshi is intentionally deferred due to location/account availability; UnusualWhales remains the useful missing Batch A key. The Alpaca mirror currently reads paper equity from Alpaca, while Qadam's first-release paper account is GBP 100,000; any GBP 1,000 value is a separate single-order/notional risk cap.
- ACLED now uses the current documented endpoint pattern `https://acleddata.com/api/acled/read` rather than the legacy `api.acleddata.com` hostname. Token freshness is automated and a 2026-05-21 refresh run succeeded with the refresh-token grant, updating the ignored local secret file. The post-refresh ACLED read validation still returned HTTP 403, so the remaining blocker is entitlement or account scope, not local token plumbing.
- ECB now validates against a concrete public data-series endpoint instead of an incomplete base URL.
- Live fetch success is not claimed until each provider credential, account scope, rate limit, and provider terms are configured locally.
- Historical backfill planning and a local sample-runner now exist for 12 priority sources, distinguishing ready read-only jobs from blocked missing-credential jobs before any large provider pull is attempted.
- Trust Score seed now covers all 35 sources, with 22 sources above 0.5 and three physical/logistics sources passing the current seed threshold; these are still priors until backtests/live observations replace them.
- Postgres/Timescale durable ingestion is now live on the Mac through OrbStack. `scripts/check_postgres_timescale_ingestion.py --require-live` and `scripts/check_postgres_timescale_replay.py --require-full-source-coverage` pass with full 35-source replay coverage. The checks still degrade safely when Postgres is offline, but the current baseline is `durable_replay_ready`, not `ready_waiting_for_local_service`.
- The public-safe cockpit status now exports a `durable_ingestion` contract and Mission Control `durable_spine` summary. Fund Managers can see whether the replayable observation spine is online, offline, partial, or complete; how many of the 35 canonical sources are replayable from Postgres/Timescale; the next bootstrap step; and the explicit boundary that durable observations cannot create signals, trade candidates, orders, broker writes, or live-capital authority.
- API onboarding is now an explicit Phase 1 workstream: `docs/api-specs.md` defines Batch A-D credential placeholders, canonical 35-source requirements, platform/model/broker/notification keys, optional upstream `world-monitor/` providers, and open source-provider decisions.
- As of 2026-05-18, the local ignored secret file has credentials for NASA FIRMS, Alpaca paper, ACLED, FRED, Q-CTRL, Telegram bot token/username/private target/group target, Gemini/Google model keys, and LM Studio settings. Kalshi, UnusualWhales, UN Comtrade, Reddit, X, AIS/Wingbits/logistics providers, SEC user agent, IBM Quantum, and AWS Braket remain pending or deferred; BLS and ECB currently work in public read-only mode but should still receive explicit provider configuration where available.
- ACLED now has access-token and refresh-token material stored locally plus automatic token renewal. Entitlement/read-scope verification still needs to pass before ACLED counts as durable live infrastructure.
- Telegram bot credentials and private/group delivery targets are local, but member delivery remains dry-run and send-disabled until explicit send-test approval exists.
- GDELT is promoted to the first real read-only adapter path; Oref is promoted as the second, higher-trust conflict alert adapter; NASA FIRMS is promoted as the first physical anomaly adapter; FRED is promoted as the first macro regime adapter; RSS is promoted as the first narrative feed adapter.
- No promoted adapter is allowed to influence signal confidence without corroboration and Signal Integrity Gate approval.
- TradingView note: a paid TradingView account does not provide a normal retail data API key. Treat TradingView MCP as read-only market/technical-analysis tooling that does not require a TradingView login, and treat the paid TradingView account as useful later for webhook alerts once Qadam has a secure receiver.
- Yahoo Finance note: the local `yahoo-finance-api/` checkout is a useful `yfinance` capability for read-only market price, volume, options-chain, market-status, quote-search, sector, screener, and news context. It should backfill the current market-confirmation gap before Phase 3 depends on price context, but only through a Qadam wrapper with sample mode, rate limits, caching, raw archive, degraded-state handling, and public-safe status. It is not a broker, not an order source, not a fill/reconciliation source, and not automatically counted as a 36th canonical source.
- OddsPipe note: direct Kalshi remains deferred because signup/account eligibility is region/identity gated for Ramin. OddsPipe is now the selected Stage 0 read-only coverage path for normalized Kalshi/Polymarket markets, OHLCV context, and cross-platform spreads. It fills the existing prediction-market monitoring slot; it does not create source 36, does not provide venue execution authority, and cannot approve or submit paper trades.
- Reddit narrative note: Reddit OAuth remains an optional future upgrade because API approval is not yet available. The selected first-release bridge is the `Reddit Narrative Proxy` in `docs/qadam-reddit-narrative-proxy-implementation-plan.md`, using ApeWisdom-style aggregate retail-attention data for stocks, crypto, and 4Chan /biz. It fills the practical Reddit/social gap for narrative pressure and crowding checks without adding source 36, raw Reddit scraping, credentials, or execution authority.

Objective: make Qadam observe the world.

Build:

- Shared async source adapter interface.
- Raw payload archive.
- Normalized event schema.
- Heartbeat and SLA monitor.
- Tier 1 adapters: ACLED, Oref, NASA FIRMS, UnusualWhales, Polymarket, Kalshi, Alpaca.
- Tier 2 adapters: FRED, AIS, Wingbits, GDELT, RSS, X, TradingView webhook alerts.
- Tier 3 adapters: BLS, ECB, UN Comtrade, BIS, USGS, Reddit, Telegram, SEC, STOCK Act.
- Tier 4 adapters or deferred stubs.
- Supplemental market-confirmation capability: Yahoo Finance / yfinance via `yahoo-finance-api/`, now accepted as `accepted_supplemental_pending_live_dependencies` with a dormant read-only Qadam wrapper before any Phase 2 or Phase 3 module consumes it.
- Registered supplemental multi-source data plane: Preference/PREF MCP via `https://pref.trade/mcp`, now planned in `docs/qadam-preference-mcp-integration-plan.md` as status/catalog-first, read-only, quota-governed, provenance-gated, and not automatically a canonical source.
- Credential onboarding ledger driven by `docs/api-specs.md`, where every source is marked as `keyless`, `configured`, `missing`, `deferred`, `needs_provider_choice`, or `blocked_by_license`.
- Batch A credentials first: NASA FIRMS, ACLED, UnusualWhales, Kalshi, Alpaca paper, Gemini, Supabase, and Telegram bot.
- Batch B credentials second: FRED, BLS, UN Comtrade, X, Reddit, Telegram MTProto, AIS provider, and Wingbits.
- Batch C credentials third: Space-Track, Coinglass, Chainlink/RPC, RapidAPI, GitHub, EPO OPS, ArcGIS, and SEC EDGAR user agent.
- Batch D credentials later: LM Studio status config, Q-CTRL, IBM Quantum, AWS Braket, TradingView alert receiver, Polymarket/Polyrouter, Hyperliquid, and IBKR.
- Initial Trust Score table.
- `data_environment_map.json`.
- Cockpit degraded-state banners.
- Local retention policy for raw payloads, normalized events, and derived features.

Exit gate:

- Every one of the 35 sources is `live`, `degraded`, `unavailable`, or `deferred`.
- Tier 1 sources are ingesting or blocked for explicit credential/licensing reasons.
- API credentials are represented only by placeholders and masked status; no raw key appears in docs, Event Log, source heartbeat output, cockpit status, or committed files.
- Every credential-gated source has a visible blocked reason until the key, rate limit, account scope, and provider terms are configured.
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
- Agent output schemas now require explicit `execution_allowed=false`, `paper_order_allowed=false`, `broker_write_allowed=false`, and a boundary statement in every sample output.
- `scripts/check_agent_manifests.py` is wired into `start_qadam.sh`.
- `scripts/check_agent_runtime.py` is wired into `start_qadam.sh`.
- `scripts/check_phase1_agent_os.py` is the Phase 1E/1F acceptance gate tying manifests, skills, runtime grants, authority flags, broker-write blocking, undeclared-tool blocking, and required per-agent tool grants into one check.
- System health, FastMCP-style tools, and the cockpit expose Agent OS and Agent Runtime status.

Why now:

- Anthropic's `financial-services` repo is a useful reference pattern for financial workflow agents: named agents, vertical skill bundles, MCP-style data connectors, managed-agent deployment cookbooks, validation scripts, and secret-scan discipline.
- The OSS reference overlay in `docs/qadam-oss-reference-implementation-plan.md` adds five adoption patterns to this phase: stricter role contracts, research-goal lifecycle, financial-terminal data taxonomy, Fund Manager operator/chat UX, and durable human-in-the-loop inbox workflows.
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
- Qadam's £100,000 first-release paper account is different: guarded paper trades are allowed after the paper-only policy gates, Risk Agent checks, execution venue checks, kill-switches, idempotency, Event Log writes, broker-readiness, and reconciliation checks exist. The PaperOps route may submit multiple Alpaca paper trades per day when distinct qualified setups exist and risk limits allow it. Live capital remains unavailable.
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
- The runtime summary includes full broker-write and undeclared-tool fail-closed matrix counts across all 8 agents.

Exit gate:

- Allowed tool calls pass only for agents with explicit grants.
- Undeclared or missing-grant tool calls block.
- Broker-write tools block for every agent.
- Undeclared tools block for every agent.
- Every agent sample output carries explicit non-execution authority flags.
- Shadow triage queue writes local-only packets with no signal, risk, or execution authority.

## 9. Phase 2 - Intelligence Stack

Objective: make Qadam think in shadow mode.

Current implementation start:

- Evidence Trail and Proposed Signal contracts exist in `orchestrator/intelligence.py`.
- Deterministic keyword/anomaly triage can produce shadow-only signals from sample evidence.
- Gemini and LM Studio provider status report configured/missing without model calls.
- Provider-safe probes exist: LM Studio `/models` can be checked after LM Studio is running, and Gemini can be checked through a model-list credential probe without text generation.
- The Research Analyst shadow triage runner consumes queued packets and writes non-executable shadow signals.
- Local Research Analyst inference contract exists: `scripts/check_local_research_analyst.py` validates a dry shadow assessment by default, and `--live` calls LM Studio `/chat/completions` only when the local server is reachable.
- Local Research Analyst outputs are stored in `data/runtime/local_research_assessments.jsonl` as shadow-only compression records with `execution_allowed=false` and `paper_order_allowed=false`.
- The OR-2 Research Goal lifecycle is now implemented as the pre-hypothesis layer in `orchestrator/research_goal.py`: source observations create/update durable JSONL goals with hypothesis, market channel, watched instruments, required sources, minimum source quorum, worldview lens, Akber stage, missing corroboration, owner agent, next handoff, and explicit zero authority for trade candidates, risk, paper orders, broker writes, quantum hardware submission, and live capital.
- RS-2 Research Goal hardening is implemented: each goal now carries source quorum, market confirmation, worldview relevance, Akber-stage, contradiction, latency/freshness, risk-readiness, priority, aging, expiry, stale/expired, close reason, and candidate-ready blocker fields. `candidate_ready` requires a clean evidence/scoring path; stale goals can close as `closed_no_trade`; and candidate/blocked trade intents must carry Research Goal lineage without giving Research Goals execution authority.
- `scripts/check_research_goal_lifecycle.py` validates the Research Goal lifecycle, sample seeding, source-quorum requirements, public-safe summaries, RS-2 scoring/aging fields, candidate-ready/closed-no-trade rules, and zero authority counters.
- `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` now runs the first deeper Phase 2 loop: live read-only observations from available sources are queued into Research Analyst shadow packets, deterministic shadow triage writes non-executable signals, local Gemma compresses the queue, the read-only Alpaca paper-account mirror is attached as account context, and a Strategy Lead shadow handoff packet is written with broker/risk execution blocked.
- `scripts/run_phase2_shadow_cycle.py --durable-replay` now runs the durable Phase 2 bridge: recent read-only `source_observation` rows from local Postgres/Timescale are replayed into hardened Research Goal records, Research Analyst packets, and the same shadow intelligence, Signal Integrity, Risk Agent, Execution Policy, disabled staged order, broker reconciliation, dry-run receipt, paper-account context, and Strategy Lead handoff chain with all authority counters locked at zero.
- `scripts/check_phase2_durable_replay_cycle.py` validates that the durable Phase 2 bridge is replayable, public-safe, source-complete for the default Phase 2 source set, and non-executable: durable observations can create/update Research Goals but cannot create trade candidates, paper orders, broker writes, or live-capital access.
- Strategy Lead shadow packets now carry sanitized source/replay context, Research Goal lifecycle context, and a challenge-only strategy review: replay mode, source posture, evidence pressure, queued packet count, research-goal count, required challenge questions, paper context status, and explicit zero authority for risk handoff, trade-candidate creation, orders, broker writes, and live capital.
- `scripts/check_strategy_lead_durable_context.py` validates that the Strategy Lead consumes durable replay context from Timescale and remains non-executable.
- `scripts/check_phase2_paper_context.py` validates the paper-account context bridge in dry mode: the context reaches the Strategy Lead packet, stays sanitized, and keeps `execution_allowed=false`, `paper_order_allowed=false`, `write_authority=false`, and `live_capital_enabled=false`.
- `orchestrator/signal_integrity.py` now implements the first Signal Integrity Gate contract. It audits recent shadow signals against source count, evidence count, trust score, missing corroboration, signal confidence, and Akber 6-stage filter state; it can return `blocked`, `hold_for_corroboration`, or `passed_to_risk_shadow`.
- `scripts/check_signal_integrity_gate.py` validates that Signal Integrity reviews are replayable, public-safe, and non-executable: the gate cannot approve risk, create trade candidates, create paper orders, or access broker-write routes.
- `orchestrator/risk_agent.py` now implements the first Risk Agent policy-router contract as read-only validation. It reviews Signal Integrity outputs and Trade Intent records against account mode, broker-write state, paper-order authority, kill-switch state, execution policy, source quality, Trust Score, invalidation, entry, and max-risk constraints; it can return `blocked_before_risk`, `policy_hold`, or `risk_shadow_ready`.
- `scripts/check_risk_agent_policy_router.py` validates that Risk Agent reviews are replayable, public-safe, and non-executable: the router cannot approve risk, create orders, create paper orders, or write to brokers.
- `orchestrator/execution_policy.py` now implements the first Execution Policy and kill-switch contract as read-only validation. It reviews Risk Agent outputs against venue mode, broker-order route state, staged-paper-order contract availability, global/strategy/venue/model/data kill switches, and live-capital boundaries; it can return `blocked_by_policy`, `kill_switch_hold`, or `paper_order_shadow_ready`.
- `scripts/check_execution_policy_router.py` validates that Execution Policy reviews are replayable, public-safe, and non-executable: the layer cannot stage orders, create orders, enable live capital, or write to brokers.
- `orchestrator/staged_paper_order.py` now implements the disabled staged paper-order contract as read-only validation. It consumes Execution Policy reviews, describes the hypothetical order that is not created, records reconciliation checks, and keeps staged order creation, paper-order submission, broker writes, and live capital disabled.
- `scripts/check_staged_paper_order_contract.py` validates that staged paper-order reviews are replayable, public-safe, and non-executable: the layer cannot create staged orders, mark paper orders submittable, enable live capital, or write to brokers.
- `orchestrator/broker_reconciliation.py` now implements the read-only broker reconciliation contract. It consumes disabled staged paper-order reviews, exposes broker echo and reconciliation prerequisites, and keeps idempotency allocation, Event Log prewrite, duplicate-order readiness, broker echo verification, paper-order submission, broker writes, and live capital disabled.
- `scripts/check_broker_reconciliation_contract.py` validates that broker reconciliation reviews are replayable, public-safe, and non-executable: the layer cannot allocate order IDs, create broker echoes, prewrite order events, submit paper orders, enable live capital, or write to brokers.
- `orchestrator/paper_submit_receipt.py` now implements the dry-run paper-submit receipt contract. It consumes broker reconciliation reviews, exposes simulated receipt prerequisites, deterministic idempotency-preview design, Event Log prewrite schema, pre-trade snapshot schema, and duplicate-order guard schema, while keeping broker POST calls, paper-order submission, broker writes, and live capital disabled.
- `scripts/check_paper_submit_receipt_contract.py` validates that paper-submit receipt reviews are replayable, public-safe, and non-executable: the layer cannot call Alpaca POST routes, submit paper orders, enable live capital, write to brokers, allocate broker-usable client IDs, write pre-order events, capture order snapshots, or execute duplicate-order guard writes.
- Current 2026-05-21 live Phase 2 cycle result: live read-only observations from NASA FIRMS, FRED, RSS, Polymarket, Alpaca, and Telegram produced 11 queued Research Analyst packets, 4 shadow signals, live local Gemma assessments when LM Studio was reachable, Signal Integrity reviews, Risk Agent policy reviews, Execution Policy / kill-switch reviews, disabled staged paper-order reviews, read-only broker reconciliation reviews, dry-run paper-submit receipt reviews, and a Strategy Lead shadow handoff packet. NASA FIRMS was live but had zero current events in the queried window. The Strategy Lead packet included read-only paper-account context: Alpaca paper mirror connected, current broker paper balance visible, zero open positions, zero mirrored orders, no write authority, and live capital disabled. The durable replay variant now replays the default Phase 2 source set from Timescale into the same chain: 6/6 sources replayed, 0 missing, 0 degraded, 6 queued Research Analyst packets, Strategy Lead handoff non-executable, and every Signal Integrity, Risk Agent, Execution Policy, staged paper-order, broker reconciliation, and paper-submit authority count held at zero. The Signal Integrity Gate returned blocked/hold reviews only, zero trade candidates, zero paper orders, and zero execution approvals. Risk Agent, Execution Policy, disabled staged paper-order, broker reconciliation, and paper-submit receipt authority counts remained zero for execution, staged paper orders, paper-order submission, broker POST calls, broker writes, and live capital.
- The public-safe cockpit status contract can expose sanitized Phase 2 durable replay cycle state, Research Goal lifecycle state, local Research Analyst assessment summaries, Strategy Lead challenge-only replay context, read-only paper-account context, Signal Integrity review state, Risk Agent policy-review state, Execution Policy / kill-switch review state, disabled staged paper-order review state, broker reconciliation review state, and dry-run paper-submit receipt review state without prompts, raw model text, local paths, broker IDs, or secrets. Current 2026-06-02 note: cockpit export and cockpit validation pass with the truthful PaperOps state exposed as safe-idle/no-current-qualified-setup. The remaining PaperOps constraint is operational, not infrastructural: Qadam must wait for a real qualified setup before the PT-4/PT-5/PT-6/PT-7/30-day chain can advance, and it must not force a trade just to satisfy a validator.
- Current-state clarification: the Phase 2 chain remains non-executable by
  design because it is an intelligence layer. Guarded paper submission authority
  lives later in PaperOps and may submit Alpaca paper orders only when the
  paper-only gates pass. Old Phase 2 zero-authority statements should not be
  read as a global ban on guarded paper trading.
- `scripts/check_shadow_intelligence.py` is wired into `start_qadam.sh`.
- `scripts/check_local_research_analyst.py` is wired into `start_qadam.sh` in dry-contract mode.
- `scripts/check_signal_integrity_gate.py` is wired into `start_qadam.sh`.
- `scripts/check_risk_agent_policy_router.py` is wired into `start_qadam.sh`.
- `scripts/check_execution_policy_router.py` is wired into `start_qadam.sh`.
- System health, FastMCP-style tools, and cockpit registry cards expose Shadow Intelligence status.
- Every Phase 2 output remains non-executable.

Build:

- Proposed Signal schema.
- Catalyst Evidence Trail schema.
- Research Goal lifecycle schema before trade candidates: each shadow idea should carry a goal id, hypothesis, watched instruments, required evidence, source quorum, contradictions, invalidation conditions, world-model lens, Akber stage, owner agent, next handoff, and explicit zero execution authority.
- Gemma local triage.
- Local Research Analyst shadow assessment store and live LM Studio inference runner.
- Gemini research packets.
- Strategy Lead shadow handoff packet store.
- Akber 6-Step Filter.
- Prediction-market probability gap.
- Options / Black-Scholes gap report.
- Swarm simulation starter.
- World-model lens applied to candidates as private prior and red-team prompt.
- Signal Integrity Gate.
- Read-only Risk Agent policy router.
- Read-only Execution Policy and kill-switch router.
- Disabled staged paper-order contract.
- Read-only broker reconciliation contract.
- Shadow signal store.

Exit gate:

- Layer A produces Proposed Signals.
- Local Research Analyst can compress queued packets through LM Studio in shadow mode when the local server is running.
- Strategy Lead can receive queued shadow handoff packets, but cannot call broker-write tools or approve risk.
- Signal Integrity Gate can block, hold, or mark a signal ready for future risk-shadow review, but cannot create candidates, orders, or approvals.
- Risk Agent can block or hold a reviewed shadow signal or trade intent, but cannot approve risk, create a paper order, create a broker order, or enable broker writes.
- Execution Policy can block or hold a Risk Agent-reviewed record, but cannot stage paper orders, create paper orders, create broker orders, enable live capital, or enable broker writes.
- Staged paper-order contract can describe hypothetical staging and reconciliation, but cannot create staged orders, mark paper orders submittable, create broker orders, enable live capital, or enable broker writes.
- Broker reconciliation contract can describe broker echo, idempotency, Event Log prewrite, duplicate-order guard, post-submit reconciliation, and postmortem requirements, but cannot allocate order IDs, write order events, submit paper orders, create broker orders, enable live capital, or enable broker writes.
- Every signal has evidence, assumptions, invalidation, transaction-cost assumptions, source Trust Scores, and pricing gap.
- World-model lens is present as private reasoning provenance, not factual evidence.
- No execution is possible.

## 10. Phase 3 - Quantum Integration

Objective: connect the weekly oracle without making the system dependent on it.

Detailed staged plan: `docs/qadam-phase-3-implementation-plan.md`.

Current implementation start:

- `orchestrator/quantum.py` now defines the Phase 3 quantum/classical oracle contract: provider readiness, `QuantumOracleJob`, `QuantumOracleResult`, local validation, deterministic classical fallback, and a JSONL result store.
- `scripts/check_quantum_oracle.py` validates two bounded oracle jobs: Pattern Recognition and Strategy Collapse / Ambiguity Score.
- The 2026-05-21 Phase 3 scaffold check produced two oracle results through `classical_fallback` because optional `qiskit-aer` is not installed. This is acceptable: the output schema is live and the hardware path remains closed.
- The 2026-05-21 Phase 3 hardening pass added the `QuantumBackend` interface, deterministic `ClassicalFallbackBackend`, optional `QiskitAerBackend`, local circuit blueprint, measurement-count output, stable input fingerprint, validation checks, and weekly cadence metadata. If `qiskit` and `qiskit-aer` are absent or fail locally, the backend degrades to the same classical fallback schema.
- The Head of Quant can now produce a shadow-only `upgrade`, `downgrade`, or `hold` recommendation after Signal Integrity review context exists. It cannot originate signals, create trade candidates, approve risk, create paper orders, call broker routes, submit hardware jobs, or bypass any gate.
- The public-safe cockpit status now exposes the quantum oracle summary and Mission Control system stack shows the oracle backend, local simulation mode, latest recommendation, cadence, fingerprint, and validation-check state without leaking credentials or local paths.
- The 2026-05-23 Phase 3A certification is recorded in `docs/qadam-phase-3-q3-10-phase-3a-certification-audit-2026-05-23.md`: provider/scheduler readiness is certified locally with Q-CTRL configured, IBM/AWS missing-secret stubs, local `classical_fallback`, `quantum_oracle.result_count=46`, durable replay `35/35`, dashboard/cockpit checks green, and all hardware, scheduler, execution, paper-order, trade-candidate, provider-call, secret-exposure, raw-response, local-path, and cloud-job counters at zero.
- The 2026-05-23 Q3-11 hardware enablement proposal is recorded in `docs/qadam-phase-3-q3-11-hardware-enablement-proposal-2026-05-23.md`. It is documentation only: Phase 3B hardware implementation remains blocked until a separate future certification explicitly authorizes a live provider call or hardware job.

Build:

- `QuantumBackend` interface. Implemented.
- Qiskit Aer local simulator. Optional backend path implemented; active only when local `qiskit` and `qiskit-aer` packages are installed.
- Classical fallback with the same output schema. Implemented.
- Q-CTRL optional provider path after local circuit validation. Current local status: credential configured, no API calls by default, Phase 3A certified metadata-only.
- IBM Quantum / Qiskit Runtime backend. Future provider stub/readiness work only until separately certified.
- AWS Braket secondary backend. Future provider stub/readiness work only until separately certified.
- Job 1: Pattern Recognition.
- Job 2: Strategy Collapse / Ambiguity Score.
- Weekly scheduler. Cadence metadata implemented; actual automation remains deferred.
- Cockpit quantum status.
- Phase 3A local certification. Implemented on 2026-05-23; release publication still requires a clean commit/push/deploy record.
- Hardware enablement proposal. Documented only; no implementation authority granted.

Exit gate:

- Every quantum job validates locally before hardware submission.
- Hardware failure produces `classical-fallback`.
- Quantum can upgrade, downgrade, or hold a signal.
- Under `docs/qadam-quantum-edge-hybrid-loop-implementation-plan.md`, the
  future quantum discovery lane may originate a research-only candidate
  relationship. It cannot self-validate, create a validated edge or strategy,
  create a trade candidate, approve risk or execution, place an order, grant
  proof credit, or bypass any downstream gate.

## 11. Phase 4 - Strategy Manifestation

Objective: turn observed system behaviour into an approved strategy document.

Staged implementation plan: `docs/qadam-phase-4-implementation-plan.md`. Q4-0 Re-Entry Baseline and Safety Contract is complete in `docs/qadam-phase-4-q4-0-re-entry-baseline-audit-2026-05-23.md`; Q4-1 Phase 4 Artifact Schema is complete in `docs/qadam-phase-4-q4-1-artifact-schema-audit-2026-05-23.md`; Q4-2 Triple-Mirror Audit is complete in `docs/qadam-phase-4-q4-2-triple-mirror-audit-2026-05-23.md`; Q4-3 Data Veracity Audit is complete in `docs/qadam-phase-4-q4-3-data-veracity-audit-2026-05-23.md`; Q4-4 Trust Score Recalculation is complete in `docs/qadam-phase-4-q4-4-trust-score-recalculation-audit-2026-05-23.md`; Q4-5 Resource Registry Validation is complete in `docs/qadam-phase-4-q4-5-resource-registry-validation-audit-2026-05-23.md`; Q4-6 World-Model Lens Validation is complete in `docs/qadam-phase-4-q4-6-world-model-lens-validation-audit-2026-05-23.md`; Q4-7 Candidate Strategy Universe is complete in `docs/qadam-phase-4-q4-7-candidate-strategy-universe-audit-2026-05-23.md`; Q4-8 Manifested Strategy Draft is complete in `docs/qadam-phase-4-q4-8-manifested-strategy-draft-audit-2026-05-23.md`; Q4-9 Strategy Toggle Contract is complete in `docs/qadam-phase-4-q4-9-strategy-toggle-contract-audit-2026-05-23.md`; Q4-10 Fund Manager Approval Record is complete in `docs/qadam-phase-4-q4-10-fund-manager-approval-record-audit-2026-05-23.md`; Q4-11 Cockpit Strategy Visibility is complete in `docs/qadam-phase-4-q4-11-cockpit-strategy-visibility-audit-2026-05-23.md`; Q4-12 Phase 4 Certification is evaluated in `docs/qadam-phase-4-q4-12-phase-4-certification-audit-2026-05-23.md` and amended for Yahoo Finance plus Preference/PREF MCP source-promotion closeout in `docs/qadam-phase-4-data-source-closeout-audit-2026-05-24.md`. Q5-0 later logged explicit Fund Manager approval and certified Q4-12 in `docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`. Phase 4 can approve strategy, but it cannot create trade candidates, approve risk, stage/submit paper orders, write to brokers, enable quantum hardware calls, or enable live capital.

Build:

- Triple-Mirror Audit.
- Data Veracity Audit.
- Trust Score recalculation.
- Resource Registry validation.
- World-model lens validation against observed outcomes.
- Candidate Strategy Universe.
- Manifested Strategy Document.
- Strategy toggles.
- Ramin approval logged in Event Log.

Exit gate:

- Approved strategy document exists.
- Active instruments, catalyst classes, source weights, model weights, quantum role, and risk assumptions are explicit.
- Private world-model frames used by active strategies are marked as validated, provisional, rejected, or untestable.
- No execution occurs before approval.

## 12. Phase 5 - Layer B Orchestration

Objective: wire risk, policy, paper execution, alerts, and cockpit actions.

Pre-handoff readiness: `docs/qadam-phase-5-layer-b-readiness-audit-2026-05-24.md`.
The readiness gate writes `data/runtime/phase5_layer_b_readiness.json` and
now reports `ready_for_phase5_layer_b_implementation` after explicit Fund
Manager approval and Q4-12 certification. Phase 5 implementation may begin one
stage at a time, but Layer B orchestration start remains false until the later
Q5 contracts explicitly create and verify paper-order, broker, notification,
and position-monitor gates.

Dedicated staged plan:
`docs/qadam-phase-5-layer-b-implementation-plan.md`. The plan splits Phase 5
into Q5-0 through Q5-15. Q5-0 is complete in
`docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`; Q5-1 is complete
in `docs/qadam-phase-5-q5-1-artifact-schema-authority-ledger-audit-2026-05-24.md`;
Q5-2 is complete in
`docs/qadam-phase-5-q5-2-approval-policy-router-audit-2026-05-24.md`;
Q5-3 is complete in
`docs/qadam-phase-5-q5-3-risk-agent-paper-sizing-audit-2026-05-24.md`.
Q5-4 is complete in
`docs/qadam-phase-5-q5-4-kill-switch-ledger-audit-2026-05-24.md`.
Q5-5 is complete in
`docs/qadam-phase-5-q5-5-execution-adapter-status-audit-2026-05-24.md`.
Q5-6 is complete in
`docs/qadam-phase-5-q5-6-paper-order-staging-gate-audit-2026-05-24.md`.
Q5-7 is complete in
`docs/qadam-phase-5-q5-7-alpaca-paper-dry-run-audit-2026-05-24.md`.
Q5-8 is complete in
`docs/qadam-phase-5-q5-8-paper-submit-enablement-gate-audit-2026-05-24.md`.
Q5-9 is complete in
`docs/qadam-phase-5-q5-9-prediction-market-adapter-audit-2026-05-24.md`.
Q5-10 is complete in
`docs/qadam-phase-5-q5-10-telegram-notifier-audit-2026-05-24.md`.
Q5-11 is complete in
`docs/qadam-phase-5-q5-11-position-monitor-audit-2026-05-24.md`.
Q5-12 is complete in
`docs/qadam-phase-5-q5-12-signal-review-governance-actions-audit-2026-05-24.md`.
Q5-13 is complete in
`docs/qadam-phase-5-q5-13-functional-system-map-dashboard-audit-2026-05-24.md`.
Q5-14 implementation harness is complete in
`docs/qadam-phase-5-q5-14-end-to-end-paper-trade-drill-audit-2026-05-24.md`;
its paper-submit approval unblock is recorded in
`docs/qadam-phase-5-q5-14-exit-unblock-approval-audit-2026-05-24.md`, and its
lifecycle exit gate is now passed after Q5E-9 in
`docs/qadam-phase-5-q5e-9-execution-adapter-readiness-audit-2026-05-24.md`.
Q5-15 certification evaluation is complete in
`docs/qadam-phase-5-q5-15-phase-5-certification-audit-2026-05-24.md`, and it
now reports `phase5_certified=True`, `phase5_exit_gate=True`,
`phase6_handoff_allowed=True`, `phase7_planning_allowed=True`, and
`phase7_proof_credit_allowed=False`. Phase 5 is complete for the handoff to
Phase 6 - Learning Loop. Q5E-10 formalizes that closeout in
`docs/qadam-phase-5-q5e-10-phase-6-handoff-closeout-audit-2026-05-24.md` and
reports `phase6_learning_loop_plan_allowed=True` while
`phase6_learning_loop_implementation_allowed=False`. Q5E-11 exposes that handoff
in cockpit, Mission Control, and dashboard checks through
`docs/qadam-phase-5-q5e-11-phase-6-handoff-visibility-audit-2026-05-24.md`.
Broker POST calls, Alpaca POST calls, live endpoints, prediction-market writes,
crypto-perps writes, live capital, autonomous execution, Phase 6 learning
writes, knowledge-graph writes, and Phase 7 proof credit remain disabled.

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
- Telegram alerts match dashboard state exactly and never imply execution before backend state reaches `staged_paper_order`, `submitted_paper_order`, `open_position`, or `closed_trade`.
- Phase 5 test trades do not count toward Phase 7 proof.
- No live endpoint or live credential can be used in first-release mode.
- PriveX or any crypto-perps venue remains disabled in the first-release £100,000 paper-account proof run unless a separate paper/sandbox account is explicitly approved.

## 13. Phase 6 - Learning Loop

Objective: make Qadam improve from paper outcomes without rewriting history,
silently changing policy, or treating Phase 5 test lifecycle evidence as Phase
7 proof.

Dedicated staged plan: `docs/qadam-phase-6-learning-loop-implementation-plan.md`.
The plan splits Phase 6 into Q6-0 through Q6-17, beginning with a re-entry gate
that must keep implementation and learning-write authority closed before any
Phase 6 module starts.

Current handoff state after Q6-17:

- Q5E-11 exposes the Q5E-10 handoff through cockpit, Mission Control, and the
  dashboard.
- Q6-0 is complete in
  `docs/qadam-phase-6-q6-0-re-entry-gate-audit-2026-05-24.md` and writes
  `data/runtime/phase6_readiness.json`.
- Q6-1 is complete in
  `docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-2026-05-24.md`
  and defines the shared Phase 6 schema, authority ledger, event contracts,
  source posture, provenance rules, and dishonest-payload probes.
- Q6-2 is complete in
  `docs/qadam-phase-6-q6-2-learning-source-intake-audit-2026-05-24.md`
  and writes `data/runtime/phase6_learning_source_intake.json`.
- Q6-3 is complete in
  `docs/qadam-phase-6-q6-3-closed-trade-outcome-schema-audit-2026-05-25.md`
  and writes `data/runtime/phase6_closed_trade_outcome.json`.
- Q6-4 is complete in
  `docs/qadam-phase-6-q6-4-postmortem-packet-contract-audit-2026-05-25.md`
  and writes `data/runtime/phase6_postmortem_packet_contract.json`.
- Q6-5 is complete in
  `docs/qadam-phase-6-q6-5-postmortem-agent-draft-audit-2026-05-25.md`
  and writes `data/runtime/phase6_postmortem_draft.json`.
- Q6-6 is complete in
  `docs/qadam-phase-6-q6-6-analysis-packets-audit-2026-05-25.md`
  and writes `data/runtime/phase6_postmortem_analysis_packets.json`.
- Q6-7 is complete in
  `docs/qadam-phase-6-q6-7-reducer-review-gate-audit-2026-05-25.md`
  and writes `data/runtime/phase6_postmortem_reduced_review.json`.
- Q6-8 is complete in
  `docs/qadam-phase-6-q6-8-outcome-linker-audit-2026-05-25.md`
  and writes `data/runtime/phase6_outcome_links.json`.
- Q6-9 is complete in
  `docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-2026-05-25.md`
  and writes `data/runtime/phase6_learning_approval_ledger.json`.
- Q6-10 is complete in
  `docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-2026-05-25.md`
  and writes `data/runtime/phase6_knowledge_graph_staged_writes.json`.
- Q6-11 is complete in
  `docs/qadam-phase-6-q6-11-knowledge-graph-read-path-audit-2026-05-25.md`
  and writes `data/runtime/phase6_knowledge_graph_read_view.json`.
- Q6-12 is complete in
  `docs/qadam-phase-6-q6-12-model-weight-update-proposals-audit-2026-05-25.md`
  and writes `data/runtime/phase6_model_weight_update_proposals.json`.
- Q6-13 is complete in
  `docs/qadam-phase-6-q6-13-trust-score-update-proposals-audit-2026-05-25.md`
  and writes `data/runtime/phase6_trust_score_update_proposals.json`.
- Q6-14 is complete in
  `docs/qadam-phase-6-q6-14-shadow-strategy-runner-audit-2026-05-25.md`
  and writes `data/runtime/phase6_shadow_strategy_replay.json`.
- Q6-15 is complete in
  `docs/qadam-phase-6-q6-15-architect-learning-summary-audit-2026-05-25.md`
  and writes `data/runtime/phase6_architect_learning_summary.json`.
- Q6-16 is complete in
  `docs/qadam-phase-6-q6-16-journal-cockpit-visibility-audit-2026-05-25.md`
  and writes `data/runtime/phase6_cockpit_learning_visibility.json`.
- Q6-17 is complete in
  `docs/qadam-phase-6-q6-17-phase-6-certification-audit-2026-05-25.md`
  and writes `data/runtime/phase6_certification.json`.
- Q5-14 is complete with `paper_trade_drill_complete=True`,
  `phase5_paper_trade_drill_exit_gate_passed=True`, and `blocker_count=0`.
- Q5-15 is certified with `phase5_certified=True`, `phase5_exit_gate=True`,
  `phase6_handoff_allowed=True`, `phase7_planning_allowed=True`, and
  `phase7_proof_credit_allowed=False`.
- Q5E-10/Q5E-11 allows only Phase 6 planning:
  `phase6_learning_loop_plan_allowed=True`,
  `phase6_learning_loop_implementation_allowed=False`,
  `phase6_learning_write_allowed=False`,
  `phase6_knowledge_graph_write_allowed=False`, and
  `live_capital_enabled_count=0`.
- Q6-0 reports `phase6_re_entry_gate_passed=True`,
  `q6_1_artifact_schema_stage_allowed=True`, and
  `unsafe_write_counter_total=0`, while keeping
  `phase6_learning_loop_implementation_allowed=False`,
  `phase6_postmortem_ingestion_allowed=False`,
  `phase6_learning_write_allowed=False`,
  `phase6_knowledge_graph_write_allowed=False`, and
  `phase7_proof_credit_allowed=False`.
- Q6-1 reports `phase6_artifact_schema_status=ok`,
  `phase6_artifact_contract_count=17`, `phase6_authority_field_count=20`,
  `phase6_unsafe_counter_field_count=15`, `phase6_event_contract_count=6`,
  `phase6_sample_authority_enabled_count=0`, and
  `phase6_sample_unsafe_counter_total=0`.
- Q6-2 reports `phase6_learning_source_intake_status=read_only`,
  `postmortem_due_count=1`, `source_ref_count=20`,
  `required_source_present_count=11`, `optional_source_present_count=9`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `phase5_hash_mutation_count=0`, `phase7_proof_credit_allowed=False`, and
  `unsafe_write_counter_total=0`.
- Q6-3 reports `phase6_closed_trade_outcome_status=read_only`,
  `outcome_status=closed_trade_outcome_normalized`, `outcome_record_count=1`,
  `closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`,
  `broker_truth_separated=True`, `unknown_field_count=5`,
  `deferred_field_count=6`, `source_hash_mutation_count=0`,
  `learning_write_allowed=False`, `knowledge_graph_write_created=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-4 reports `phase6_postmortem_packet_contract_status=schema_only`,
  `packet_section_count=13`, `assertion_source_refs_required=True`,
  `uncited_conclusion_allowed=False`, `narrative_only_allowed=False`,
  `postmortem_draft_created=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`, `source_hash_mutation_count=0`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-5 reports `phase6_postmortem_agent_status=draft`,
  `postmortem_draft_created=True`, `postmortem_approved=False`,
  `approval_state=not_requested`, `packet_section_count=13`,
  `source_assertion_count=20`, `unknown_marker_count=5`,
  `deferred_marker_count=6`, `missing_ref_count=3`, `llm_used=False`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `model_weight_update_created=False`, `trust_score_update_created=False`,
  `policy_mutation_created=False`, `strategy_mutation_created=False`,
  `source_hash_mutation_count=0`, `phase7_proof_credit_allowed=False`, and
  `unsafe_write_counter_total=0`.
- Q6-6 reports `phase6_postmortem_analysis_status=draft`,
  `analysis_state=deterministic_analysis_packets_created`,
  `analysis_packet_count=5`, catalyst/pricing/regime/execution/override packet
  coverage, `claim_count=10`, `all_claims_cited=True`,
  `confidence_packet_count=5`, `uncertainty_count=5`,
  `missing_evidence_count=9`, `postmortem_approved=False`,
  `approval_state=not_requested`, `llm_used=False`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `model_weight_update_created=False`, `trust_score_update_created=False`,
  `policy_mutation_created=False`, `strategy_mutation_created=False`,
  `source_hash_mutation_count=0`, `phase7_proof_credit_allowed=False`, and
  `unsafe_write_counter_total=0`.
- Q6-7 reports `phase6_postmortem_reducer_status=pending_review`,
  `review_state=review_required`, `governance_state=review_required`,
  `reduced_postmortem_created=True`, `classification_record_count=5`,
  useful=2, harmful=0, neutral=1, untestable=2, `review_queue_count=5`,
  `postmortem_approved=False`, `approval_state=not_requested`,
  `approval_logged=False`, `reviewer_label=None`, `write_allowed=False`,
  `learning_action_count=0`, `learning_action_approved_count=0`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `model_weight_update_created=False`, `trust_score_update_created=False`,
  `policy_mutation_created=False`, `strategy_mutation_created=False`,
  `source_hash_mutation_count=0`, `phase7_proof_credit_allowed=False`, and
  `unsafe_write_counter_total=0`.
- Q6-8 reports `phase6_outcome_linker_status=linked`,
  `source_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`,
  `source_review_state=review_required`,
  `complete_outcome_link_created=True`, `linked_ref_count=21`,
  `required_link_present_count=12`, `missing_required_link_count=0`,
  `optional_link_present_count=9`, `missing_optional_link_count=0`,
  `reference_only_link_count=21`, `raw_payload_copied_count=0`,
  `private_payload_copied_count=0`, `local_path_exposed_count=0`,
  `secret_ref_exposed_count=0`, `source_hash_mutation_count=0`,
  `link_write_allowed=False`, `postmortem_approved=False`,
  `approval_state=not_requested`, `approval_logged=False`,
  `learning_action_count=0`, `learning_action_approved_count=0`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `model_weight_update_created=False`, `trust_score_update_created=False`,
  `policy_mutation_created=False`, `strategy_mutation_created=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-9 reports `phase6_learning_approval_status=deferred`,
  `approval_state=deferred`, `approval_logged=True`,
  `reviewer_label=fund_manager_ramin`,
  `approval_event_log_ref=data/runtime/phase6_learning_approval_ledger_events.jsonl`,
  `default_approval_exists=False`,
  `missing_approval_blocks_downstream=True`, `source_review_state=review_required`,
  `source_outcome_link_status=linked`, `proposed_action_count=5`,
  `approved_action_count=0`, `rejected_action_count=0`,
  `deferred_action_count=5`, `pending_review_action_count=0`,
  `learning_action_count=0`, `learning_action_approved_count=0`,
  `downstream_advance_allowed=False`, `downstream_blocked_gate_count=4`,
  `knowledge_graph_staged_write_allowed=False`,
  `model_weight_update_proposal_allowed=False`,
  `trust_score_update_proposal_allowed=False`,
  `strategy_learning_proposal_allowed=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`, `model_weight_update_created=False`,
  `trust_score_update_created=False`, `policy_mutation_created=False`,
  `strategy_mutation_created=False`, `source_hash_mutation_count=0`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-10 reports `phase6_knowledge_graph_staging_status=blocked`,
  `kg_write_state=blocked_pending_learning_approval`,
  `source_approval_state=deferred`, `source_approved_action_count=0`,
  `candidate_action_count=5`, `blocked_action_count=5`,
  `staged_entry_count=0`, `staged_write_allowed=False`,
  `knowledge_graph_staged_write_allowed=False`,
  `missing_approval_blocks_staging=True`,
  `knowledge_graph_commit_allowed=False`, `chroma_write_allowed=False`,
  `graph_backend_write_allowed=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`, `actual_graph_commit_created=False`,
  `chroma_write_created=False`, `graph_backend_write_created=False`,
  `destructive_overwrite_allowed=False`, `supersession_required=True`,
  `rollback_available=True`, `source_hash_mutation_count=0`,
  `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-11 reports `phase6_knowledge_graph_read_path_status=read_only`,
  `read_view_state=read_only_seed_context_available`,
  `source_staging_status=blocked`, `source_approval_state=deferred`,
  `source_staged_entry_count=0`, `source_blocked_action_count=5`,
  `result_count=1`, `seed_result_count=1`, `staged_result_count=0`,
  `approved_learning_entry_count=0`, `search_enabled=True`,
  `crude_oil_search_result_count=1`, `paper_lifecycle_search_result_count=1`,
  `write_allowed=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`,
  `chroma_write_created=False`, `graph_backend_write_created=False`,
  `raw_payload_copied_count=0`, `private_payload_copied_count=0`,
  `local_path_exposed_count=0`, `secret_ref_exposed_count=0`,
  `source_hash_mutation_count=0`, `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-12 reports `phase6_model_weight_updates_status=blocked`,
  `proposal_state=blocked_pending_learning_approval`,
  `source_read_path_status=read_only`, `source_approval_state=deferred`,
  `source_approved_learning_entry_count=0`, `source_staged_result_count=0`,
  `source_seed_result_count=1`, `proposal_record_count=1`,
  `active_proposal_count=0`, `blocked_proposal_count=1`,
  `approved_evidence_count=0`, `bayesian_update_count=0`,
  `before_weight_count=7`, `after_weight_count=7`, `before_weight_sum=1.0`,
  `after_weight_sum=1.0`, `weight_delta_total_abs=0.0`,
  `weights_normalized=True`, `model_weight_update_proposal_allowed=False`,
  `model_weight_update_proposed=False`, `apply_allowed=False`,
  `model_weight_update_allowed=False`, `model_weight_update_applied=False`,
  `active_model_weight_mutated=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`,
  `chroma_write_created=False`, `graph_backend_write_created=False`,
  `model_weight_update_created=False`, `trust_score_update_created=False`,
  `policy_mutation_created=False`, `strategy_mutation_created=False`,
  `source_hash_mutation_count=0`, `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-13 reports `phase6_trust_score_updates_status=blocked`,
  `proposal_state=blocked_pending_learning_approval`,
  `source_model_weight_status=blocked`, `source_approval_state=deferred`,
  `source_approved_evidence_count=0`, `canonical_source_score_count=35`,
  `supplemental_policy_record_count=2`, `proposal_record_count=35`,
  `active_proposal_count=0`, `blocked_proposal_count=35`,
  `approved_evidence_count=0`, `trust_score_update_count=0`,
  `before_score=0.539143`, `after_score=0.539143`,
  `score_delta_total_abs=0.0`, `trust_score_update_proposal_allowed=False`,
  `trust_score_update_proposed=False`, `apply_allowed=False`,
  `trust_score_update_allowed=False`, `trust_score_update_applied=False`,
  `active_trust_score_mutated=False`, `canonical_rank_mutated=False`,
  `source_quorum_credit_granted=False`, `single_source_verdict_rejected=True`,
  `supplemental_only_verdict_rejected=True`,
  `yahoo_finance_score_included=False`,
  `preference_mcp_source_quorum_credit_allowed=False`,
  `learning_write_created=False`, `knowledge_graph_write_created=False`,
  `knowledge_graph_commit_created=False`, `chroma_write_created=False`,
  `graph_backend_write_created=False`, `model_weight_update_created=False`,
  `trust_score_update_created=False`, `policy_mutation_created=False`,
  `strategy_mutation_created=False`, `source_hash_mutation_count=0`,
  `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-14 reports `phase6_shadow_strategy_runner_status=blocked`,
  `replay_state=blocked_pending_learning_approval`,
  `source_trust_score_status=blocked`,
  `source_approval_state=deferred`,
  `source_approved_evidence_count=0`, `approved_fact_count=0`,
  `variant_record_count=3`, `active_replay_count=0`,
  `blocked_replay_count=3`, `evaluated_variant_count=0`,
  `actual_vs_hypothetical_comparison_count=3`,
  `evaluated_comparison_count=0`, `replay_output_exists=True`,
  `shadow_strategy_replay_allowed=False`,
  `shadow_strategy_replay_created=False`,
  `trade_candidate_creation_allowed=False`,
  `trade_candidate_created=False`, `trade_candidate_created_count=0`,
  `order_creation_allowed=False`, `paper_order_allowed=False`,
  `paper_order_allowed_count=0`, `paper_order_created=False`,
  `paper_order_created_count=0`, `execution_allowed=False`,
  `execution_allowed_count=0`, `execution_intent_created=False`,
  `execution_intent_created_count=0`, `broker_post_allowed=False`,
  `alpaca_post_allowed=False`, `broker_post_called_count=0`,
  `alpaca_post_called_count=0`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`,
  `knowledge_graph_commit_created=False`, `chroma_write_created=False`,
  `graph_backend_write_created=False`, `model_weight_update_created=False`,
  `trust_score_update_created=False`, `policy_mutation_created=False`,
  `strategy_mutation_created=False`, `source_hash_mutation_count=0`,
  `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-15 reports `phase6_architect_learning_status=blocked`,
  `summary_state=blocked_pending_learning_approval`,
  `source_shadow_replay_status=blocked`,
  `source_approval_state=deferred`, `source_approved_fact_count=0`,
  `approved_fact_count=0`, `architect_summary_created=True`,
  `recommendation_count=4`, `recommendation_record_count=4`,
  `active_recommendation_count=0`, `blocked_recommendation_count=4`,
  `governance_pending_count=4`, `policy_recommendation_count=1`,
  `strategy_recommendation_count=1`, `risk_limit_recommendation_count=1`,
  `source_model_trust_recommendation_count=1`,
  `recommendation_apply_allowed=False`, `policy_mutation_allowed=False`,
  `policy_mutation_created=False`, `strategy_mutation_allowed=False`,
  `strategy_mutation_created=False`, `risk_limit_update_allowed=False`,
  `risk_limit_update_created=False`, `source_weight_update_allowed=False`,
  `source_weight_update_created=False`, `model_weight_update_allowed=False`,
  `model_weight_update_created=False`, `trust_score_update_allowed=False`,
  `trust_score_update_created=False`, `learning_write_created=False`,
  `knowledge_graph_write_created=False`,
  `knowledge_graph_commit_created=False`, `chroma_write_created=False`,
  `graph_backend_write_created=False`, `source_hash_mutation_count=0`,
  `phase5_source_artifacts_mutated=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.
- Q6-16 reports `phase6_cockpit_visibility_status=visible`,
  `visibility_state=backend_derived_deferred_learning_visible`,
  `learning_state=deferred_learning_visible`,
  `backend_derived=True`, `display_derived_from_backend=True`,
  `dashboard_uses_backend_status=True`, `ui_inferred_readiness_count=0`,
  `backend_parity_error_count=0`, `postmortem_due_count=1`,
  `postmortem_resolved_count=0`, `approval_state=deferred`,
  `pending_review_action_count=0`, `deferred_action_count=5`,
  `explicitly_deferred_action_count=5`,
  `learning_actions_review_satisfied=True`,
  `staged_graph_entry_count=0`, `knowledge_graph_read_result_count=1`,
  `model_weight_proposal_count=1`, `trust_score_proposal_count=35`,
  `shadow_replay_variant_count=3`, `architect_recommendation_count=4`,
  `blocked_authority_count=20`, `raw_payload_exposed_count=0`,
  `private_payload_exposed_count=0`, `local_path_exposed_count=0`,
  `secret_ref_exposed_count=0`, `broker_identifier_exposed_count=0`,
  `phase6_learning_write_allowed=False`,
  `phase6_knowledge_graph_write_allowed=False`,
  `phase6_model_weight_update_allowed=False`,
  `phase6_trust_score_update_allowed=False`,
  `phase6_architect_policy_mutation_allowed=False`,
  `phase7_proof_credit_allowed=False`, `live_capital_enabled=False`, and
  `unsafe_write_counter_total=0`.
- Q6-17 reports `phase6_certification_status=certified`,
  `stage_status=phase6_certified`,
  `phase6_certified=True`, `phase6_exit_gate=True`,
  `phase7_demo_proof_planning_allowed=True`,
  `phase7_proof_credit_allowed=False`,
  `phase5_test_trades_count_for_phase7=False`, `input_gate_count=17`,
  `input_gate_passed_count=17`, `input_gate_blocked_count=0`,
  `certification_blocker_count=0`,
  `postmortem_due_count=1`, `postmortem_resolved_count=0`,
  `postmortem_explicitly_deferred_count=1`, `unresolved_postmortem_count=0`,
  `reviewed_postmortem_coverage_satisfied=True`,
  `approval_state=deferred`, `proposed_action_count=5`,
  `approved_action_count=0`, `explicitly_deferred_action_count=5`,
  `pending_review_action_count=0`, `learning_actions_review_satisfied=True`,
  `knowledge_graph_requirement_satisfied=True`,
  `knowledge_graph_read_result_count=1`, `model_weight_proposal_count=1`,
  `trust_score_proposal_count=35`, `shadow_replay_variant_count=3`,
  `architect_recommendation_count=4`, `cockpit_visibility_status=visible`,
  `blocking_unsafe_count=0`, and `unsafe_write_counter_total=0`.
- The first learning seed is a guarded local paper lifecycle for
  `crude_oil_energy_security_disruption`: staged order, dry-run preview,
  guarded local submitted paper order, local broker receipt, mirrored submitted
  order, guarded local closed trade, and postmortem-due marker. This is Phase 5
  test data and must not count toward Phase 7 proof.

Entry rule:

- Q6-0 must pass before Q6-1 begins. It is now passed, but it allows only Q6-1
  schema and authority-ledger work; it does not enable learning writes.
- Phase 6 may read Phase 5 artifacts, Event Log records, cockpit status,
  postmortem-due markers, Strategy Lead reviews, Signal Integrity reviews,
  Risk Agent reviews, Execution Policy decisions, Position Monitor records, and
  source provenance, but it must not mutate those Phase 5 source records.
- Any new learning output must be append-only, Event Log backed, provenance
  linked, public-safe in cockpit, and reversible by superseding record rather
  than destructive rewrite.
- The first implementation stages must keep broker POST, Alpaca POST, live
  endpoints, prediction-market writes, crypto-perps writes, live capital,
  autonomous execution, Phase 7 proof credit, policy mutation, and hidden model
  weight changes disabled.

Build:

- Q6-0 modular implementation plan and Phase 6 re-entry gate.
- Phase 6 artifact schema, authority ledger, source refs, and audit/event
  contract.
- Postmortem Agent that consumes `postmortem_due` markers and drafts
  postmortem packets without changing scores or policy.
- Closed-trade and outcome schema covering realized outcome, expected thesis,
  catalyst path, risk decision, sizing, execution path, slippage/receipt data,
  source evidence, and invalidation.
- Outcome linker that connects the closed trade to Signal Integrity, Strategy
  Lead, Risk Agent, Execution Policy, paper order, position monitor,
  postmortem-due, Yahoo Finance market-confirmation context, Preference/PREF
  MCP provenance context, and optional Head of Quant shadow annotations.
- Human/governance review gate for postmortem approval before any Knowledge
  Graph, model-weight, trust-score, or strategy-learning write is allowed.
- Knowledge Graph write/read path for approved resolved catalyst entries,
  using append-only records with source refs and no destructive overwrite.
- Bayesian model-weight update proposals in shadow mode first, with before/after
  deltas, confidence, replay evidence, and approval state.
- Trust Score monthly update proposals based on resolved source usefulness,
  error, staleness, provenance quality, and corroboration history.
- Shadow Strategy runner that can replay "what would have happened" variants
  and propose adjustments, but cannot create trade candidates or orders.
- Architect Agent learning summaries that recommend policy or strategy changes
  but cannot silently mutate policy, source weights, model weights, trust
  scores, or risk limits.
- Trade Journal and Postmortems cockpit pages that are backend-derived and show
  learning state, review state, unresolved postmortems, proposed updates, and
  rejected/approved changes without implying live execution.
- Phase 6 certification and Phase 7 handoff gate.

Data-source rules:

- Yahoo Finance remains supplemental market-confirmation context only. It can
  help evaluate price/volume context around a trade, but cannot become fill
  truth, broker echo, receipt evidence, reconciliation truth, or a single-source
  learning verdict.
- Preference/PREF MCP remains a supplemental multi-source data plane. Polymarket,
  Kalshi, SEC, vessel, weather, wallet, or other PREF-derived context can enrich
  postmortems only with tool/source provenance and only under the existing
  source-promotion policy; it does not create source-quorum credit by itself.
- Q-CTRL/quantum outputs remain shadow annotations unless a later hardware gate
  explicitly changes that role; they cannot become execution proof or learning
  truth on their own.
- Learning must distinguish execution evidence, market context, source
  provenance, model interpretation, and governance approval as separate fields.

Exit gate:

- Every closed paper trade in Phase 6 scope has a reviewed postmortem, and
  every `postmortem_due` marker is either resolved or explicitly deferred with
  reason and next-review date.
- Knowledge Graph contains approved resolved catalyst entries with source refs,
  timestamps, provenance, linked trade/outcome ids, and supersession semantics.
- Trust Score and model-weight update proposals have before/after audit trails,
  replay evidence, reviewer state, Event Log entries, and rollback/supersession
  paths.
- World-model frames are scored as helpful, harmful, neutral, or untestable
  only when tied to resolved evidence; private priors remain context, not proof.
- Shadow Strategy runner outputs are replay/proposal only and cannot create
  trade candidates, approvals, paper orders, broker writes, or live actions.
- Architect Agent recommends; it does not silently change policy.
- Cockpit and dashboard expose Phase 6 learning state from backend artifacts
  only, with zero UI-inferred readiness.
- Phase 5 test trades remain excluded from Phase 7 proof credit.
- Phase 6 certification may allow Phase 7 demo-proof planning, but does not by
  itself enable live capital, broker writes, prediction-market writes,
  crypto-perps writes, or Phase 7 proof credit.

## 14. Phase 7 - Demo Proof

Objective: prove the autonomous paper system before live capital.

Dedicated staged plan: `docs/qadam-phase-7-demo-proof-implementation-plan.md`.
The plan updates the old 90-day/two-trade cadence into a 30-consecutive-day
demo proof harness with three proof trades per proof week where qualified
setups exist. No trade may be forced to satisfy the cadence target.

Paper operational target: `docs/qadam-paper-operational-mode-plan.md` defines
the next control track. The goal is a full end-to-end autonomous paper loop:
source observations, reasoning, Head-of-Quant/Q-CTRL consultation, evidence
gates, risk, staging, Alpaca paper submit, lifecycle monitoring, Telegram
notification, postmortem, performance, and learning review. Paper mode is the
high-fidelity simulation of the intended Qadam reality: the decision/provider
stack should match live mode, while the venue and capital boundary stay paper
only. Live capital, live endpoints, live credentials, prediction-market writes,
crypto-perps writes, UI-to-broker shortcuts, LLM-to-broker shortcuts, and live
promotion remain disabled.

Current PaperOps status:

- PaperOps-0 readiness gate is implemented in
  `orchestrator/paper_operational_readiness.py` and
  `scripts/check_paper_operational_readiness.py`.
- PaperOps-1 cycle runner is implemented in
  `scripts/run_paper_operational_cycle.py`.
- PT-0 paper-live activation charter is implemented in
  `orchestrator/paper_live_activation.py` and
  `scripts/check_paper_live_activation.py`. It records explicit Fund Manager
  system-level approval for Alpaca paper-only operation after later PT gates
  pass: `approval_state=approved`, `approval_logged=True`,
  `paper_live_activation_approved=True`, and
  `paper_trading_system_approval_logged=True`. It also keeps
  `per_trade_manual_approval_required=False`,
  `paper_order_submission_allowed=False`, `live_capital_enabled=False`,
  `forced_trades_allowed=False`, `qctrl_direct_execution_allowed=False`, and
  all broker/Alpaca/live endpoint counters at zero.
- PT-1 Q-CTRL product access and paper consultation is implemented in
  `orchestrator/paper_live_qctrl_product_access.py` and
  `scripts/check_paper_live_qctrl_product_access.py`. The explicit guarded
  provider probe was run through PaperOps-Q for the `qadam` organization and
  reports `status=qctrl_paper_consultation_ready`,
  `product_access_verified=True`, `paper_consultation_ready=True`,
  `provider_call_attempted=True`, `provider_call_succeeded=True`,
  `provider_call_count=1`, and `product_access_blocker=none`.
  It exposes this state in PaperOps readiness, PaperOps cycle, PaperOps-6, and
  cockpit Mission Control while keeping Q-CTRL advisory-only with no execution,
  paper-order, broker, live endpoint, live capital, forced-trade, hardware, raw
  response, secret, or Phase 7 proof-credit authority.
- PT-2 global PaperOps runtime mode is implemented in
  `orchestrator/paper_operational_mode.py` and
  `scripts/check_paper_operational_mode.py`. It records
  `status=enabled_pending_downstream_gates`,
  `paper_operational_mode_enabled=True`,
  `paper_operational_mode_effective=True`,
  `settings_paper_operational_enabled=False`,
  `runtime_artifact_override_enabled=True`, and
  `paper_operational_flag_disabled=False` without editing `.env`, submitting
  orders, calling brokers/live endpoints, enabling live capital, giving Q-CTRL
  execution authority, forcing trades, or granting Phase 7 proof credit.
- PT-3 qualified setup production path is implemented in
  `orchestrator/paperops_qualified_setup_production.py` and
  `scripts/check_paperops_qualified_setup_production.py`. It reads existing
  Phase 5, Phase 7, Signal Integrity, Risk Agent, execution-adapter, and
  paper-staging evidence and currently reports
  `status=production_path_ready_with_qualified_setup`,
  `production_candidate_count=5`, `qualified_setup_count=1`,
  `blocked_candidate_count=4`, `paper_size_eligible_count=1`,
  `staged_order_count=1`, and `ready_to_stage_q7_order=True`. This is a
  production handoff classification only: `phase7_demo_qualified_setup_count=0`
  and `source_qualified_setup_ledger_count=0` remain unchanged, and PT-3 keeps
  broker POST, Alpaca POST, live endpoint, forced-trade, Q-CTRL broker, live
  capital, and Phase 7 proof-credit counters at zero.
- PT-4 auto-approval and staged paper-order handoff is implemented in
  `orchestrator/paperops_auto_approval_staged_order.py` and
  `scripts/check_paperops_auto_approval_staged_order.py`. It consumes the PT-3
  production-qualified setup and currently reports
  `status=staged_paper_order_ready`, `auto_approved_setup_count=1`,
  `staged_order_count=1`, `ready_for_paperops2_submit=True`,
  `idempotency_key_count=1`, `duplicate_idempotency_key_count=0`,
  `event_log_prewrite_written_count=1`, and
  `pre_trade_snapshot_present_count=1`. This is a PaperOps/PT-4 handoff only:
  Q7 source ledger, Q7 auto-approval, and Q7 staging artifacts remain
  unmutated, and broker POST, Alpaca POST, live endpoint, forced-trade, live
  capital, and Phase 7 proof-credit counters remain zero.
- PaperOps-Q Q-CTRL paper consultation gate is implemented in
  `orchestrator/paperops_qctrl_consultation.py` and
  `scripts/check_paperops_qctrl_consultation.py`. Fire Opal is installed and
  SDK importability is true; the explicit flagged provider probe records a
  sanitized provider-call attempt, but successful consultation remains blocked
  by Q-CTRL account/product subscription access.
- PT-5 Alpaca paper-submit runtime enablement is implemented in
  `orchestrator/paperops_alpaca_paper_submit_enablement.py` and
  `scripts/check_paperops_alpaca_paper_submit_enablement.py`. It records
  `status=enabled_pending_explicit_submit`,
  `alpaca_paper_submit_effective=True`,
  `settings_alpaca_paper_submit_enabled=False`,
  `runtime_artifact_override_enabled=True`, and
  `paper_post_path_available=True` without editing `.env`, submitting orders,
  calling Alpaca, enabling live capital, forcing trades, exposing credentials,
  or granting Phase 7 proof credit.
- PaperOps-2 explicit Alpaca paper POST gate is implemented in
  `orchestrator/paperops_alpaca_paper_post.py` and
  `scripts/check_paperops_alpaca_paper_post.py`. The default path is
  non-submit; a real Alpaca paper POST requires paper mode, live capital
  disabled, `QADAM_ALPACA_PAPER_SUBMIT_ENABLED=true` or PT-5 runtime
  enablement, paper endpoint classification, paper credentials, an eligible
  PT-4 staged PaperOps paper order or Q7 guarded submit record, source Event
  Log prewrite, pre-trade snapshot, Phase 7 idempotency, and the explicit
  `--submit-paper-order` CLI flag. The current default check reports
  `ready_pending_explicit_execute`, `eligible_submit_record_count=1`,
  `selected_source_family=paperops_pt4_staged_order`, and zero Alpaca POST
  calls.
- PaperOps-3 paper lifecycle poller is implemented in
  `orchestrator/paperops_paper_lifecycle_poller.py` and
  `scripts/check_paperops_paper_lifecycle_poller.py`. It consumes only
  successful PaperOps-2 submitted paper orders, writes a sanitized read-only
  lifecycle readback artifact, and requires PT-6 active lifecycle polling
  enablement plus an explicit active-poll handoff before any Alpaca paper GET.
- PT-6 active paper lifecycle polling enablement is implemented in
  `orchestrator/paperops_paper_lifecycle_polling_enablement.py` and
  `scripts/check_paperops_paper_lifecycle_polling_enablement.py`. It records
  `status=enabled_pending_submitted_paper_orders`,
  `active_lifecycle_polling_enabled=True`,
  `paper_lifecycle_polling_effective=True`, and
  `paper_poll_path_available=False` because PaperOps-2 has zero successful
  submitted paper orders. It does not edit `.env`, submit orders, call Alpaca
  by itself, call broker POST routes, call live endpoints, close positions,
  force trades, grant Phase 7 proof credit, expose credentials, or enable live
  capital.
- PT-7 guarded paper-exit runtime enablement is implemented in
  `orchestrator/paperops_guarded_paper_exit_enablement.py` and
  `scripts/check_paperops_guarded_paper_exit_enablement.py`. It records
  `status=enabled_pending_open_position_readback`,
  `guarded_paper_exit_enabled=True`, `alpaca_paper_exit_effective=True`,
  `runtime_artifact_override_enabled=True`, and
  `paper_exit_path_available=False` because PaperOps-3 has zero open-position
  readbacks. It does not edit `.env`, request an exit, close positions, call
  Alpaca, call broker POST routes, call live endpoints, force trades, grant
  Phase 7 proof credit, expose credentials, or enable live capital.
- PaperOps-4 guarded paper exit path is implemented in
  `orchestrator/paperops_paper_exit_path.py` and
  `scripts/check_paperops_paper_exit_path.py`. It consumes only PaperOps-3
  open-position readbacks, writes a sanitized paper-exit artifact, and now
  consumes PT-7 runtime enablement while keeping
  `QADAM_ALPACA_PAPER_EXIT_ENABLED=false`. It reports
  `ready_no_exit_candidate` until PaperOps-3 has an open-position readback, and
  still requires paper endpoint classification, paper credentials, Event Log
  prewrite, and the explicit `--execute-paper-exit` CLI flag before any Alpaca
  paper position close.
- PaperOps-5 notification and review is implemented in
  `orchestrator/paperops_notification_review.py` and
  `scripts/check_paperops_notification_review.py`. It renders ten public-safe
  review records for PaperOps readiness, 30-day operations, active paper
  automation, Q-CTRL consultation hold, submitted paper orders, broker receipts,
  open positions, paper exit-path state, closed trades, and postmortem due
  markers. Telegram remains notify-only, dry-run by default, and
  command-disabled; live-send requires a separate send-test approval and is not
  used by the default PaperOps cycle.
- PaperOps-6 30-day paper run operations is implemented in
  `orchestrator/paperops_30_day_operations.py` and
  `scripts/check_paperops_30_day_operations.py`. It binds the active Phase 7
  30-day paper window to the existing hourly Codex automation, validates the
  scheduler prompt, records PaperOps cycle state, keeps the cockpit as the
  public-safe operating mirror, and rejects backfill, simulated time, forced
  trades, broker writes, live endpoints, live credentials, live capital,
  Telegram command paths, live notification sends, and Phase 7 proof credit.
- PaperOps opportunity scan cadence is implemented in
  `orchestrator/paperops_opportunity_scan_cadence.py` and
  `scripts/check_paperops_opportunity_scan_cadence.py`. This splits
  opportunity discovery from execution: Qadam can refresh candidate state every
  20 minutes, while model review remains hourly or event-gated and guarded
  paper submission remains on the existing hourly PaperOps runner. The scan
  contract is read-only and cannot submit orders, close positions, force trades,
  bypass Signal Integrity/Risk/Execution/Q-CTRL/idempotency gates, call live
  endpoints, enable live capital, or grant Phase 7 proof credit.
- PT-8 active paper trading automation is implemented in
  `orchestrator/paperops_active_paper_trading_automation.py`,
  `scripts/check_paperops_active_paper_trading_automation.py`, and
  `scripts/run_active_paper_trading_automation.py`. It binds the hourly
  PaperOps runner to the existing PaperOps-2 submit, PaperOps-3 poll, and
  PaperOps-4 exit gates without creating a direct broker shortcut. The active
  runner is now explicitly armed for unattended paper execution via
  `unattended_paper_execution_delegation_enabled=True`, but it only submits when
  PaperOps-2 reports a fresh eligible order. Already-submitted staged orders are
  held by the PaperOps-2 idempotency ledger and surface as
  `ready_no_fresh_eligible_order`, not as repeat submit opportunities.
- PT-9 cockpit and notification upgrade is implemented in
  `orchestrator/paperops_cockpit_notification_upgrade.py` and
  `scripts/check_paperops_cockpit_notification_upgrade.py`. It exposes
  public-safe Fund Manager readouts for 30-day operations, active automation,
  notification review, Q-CTRL hold visibility, and paper-submit hold visibility
  in cockpit and Mission Control. It records
  `cockpit_notification_upgrade_ready`, five Fund Manager readouts, ten
  notification review records, zero Telegram live sends, zero Telegram command
  paths, zero outbox writes, zero broker writes, zero broker/live calls, zero
  live capital, and zero Phase 7 proof credit.
- PT-10 paper-live certification is implemented in
  `orchestrator/paper_live_certification.py` and
  `scripts/check_paper_live_certification.py`. It now records
  `status=paper_live_certified`,
  `paper_live_certification_gate_evaluated=True`,
  `paper_live_control_plane_certified=True`,
  `paper_live_certified=True`, `paper_live_operation_allowed=True`, and
  `paper_live_unattended_execution_delegation_enabled=True`. The narrower
  `paper_live_submission_delegation_allowed` flag remains `False` until a fresh
  eligible paper submit action exists. It is wired into PaperOps
  readiness, the PaperOps cycle, PaperOps-6, cockpit status, Mission Control,
  and the hourly automation prompt. The historical 30-day proof artifacts no
  longer block paper-live certification; all unsafe write, broker, notification,
  live capital, and false performance-maturity counters remain zero. Q-CTRL
  remains mandatory, but its current product-access and
  submit-hold gates are clear for the `qadam` organization.
- External trading strategy notes are now integrated as decision context through
  `orchestrator/strategy_research_intake.py`, Strategy Lead shadow review, the
  Phase 4 candidate strategy universe, and PaperOps readiness. This gives Qadam
  four structured research candidates without granting trade, broker, Q-CTRL, or
  live-capital authority.
- Current cycle result is `paper_cycle_full_paper_operational_ready` with 34/34
  commands passing: paper mode is safe to continue, PT-0 approval is logged,
  PT-1 has verified Q-CTRL product access for `qadam`, PT-2 makes the global
  PaperOps runtime mode effective, PT-3 finds one production-qualified setup
  candidate ready for guarded paper handoff, PT-4 auto-approves and stages one
  PaperOps paper order, PT-5 runtime-enables the Alpaca paper-submit path,
  PT-6 runtime-enables active read-only lifecycle polling, PT-7 runtime-enables
  the guarded paper-exit path, PT-8 binds active paper automation with the
  Q-CTRL hold clear, the paper growth run is active, the Head-of-Quant oracle can run
  in its current guarded mode, one Alpaca paper order has been submitted and
  accepted, PaperOps-3 has mirrored the submitted order, PaperOps-4 reports
  `ready_no_exit_candidate`, PaperOps-5 reports `review_ready`, PaperOps-6
  reports `operations_active`, PT-9 reports
  `cockpit_notification_upgrade_ready`, PT-10 reports
  `paper_live_certified`, with the paper-live control plane certified and
  operation allowed for the 60-day paper growth trial.
- The active legacy run id remains `phase7-demo-proof-2026-05-25`, but the
  user-facing operating mandate is the 60-day paper growth trial: GBP 100,000
  to GBP 200,000 under paper-only, evidence-gated, risk-governed trading.
- The existing hourly automation is now `Qadam Paper Growth Runner`, remains
  `ACTIVE` on `FREQ=HOURLY;INTERVAL=1`, and runs the PaperOps cycle, PT-8
  active automation check, guarded PT-8 active runner, PT-9 cockpit
  notification check, PT-10 paper-live certification check, PaperOps-6
  operations check, paper growth run check, certification check,
  live-promotion review, and cockpit status export. Do not convert this
  transport into a 20-minute broker-submit loop; the 20-minute cadence belongs
  to the separate read-only opportunity scanner.
- The next operational step is to keep the PaperOps runner active through the
  60-day paper growth trial, keep the Q-CTRL/Fire Opal paper consultation gate
  clear, and let PT-8 delegate only to PaperOps-2/PaperOps-3/PaperOps-4 when
  their explicit paper-only gates and source prerequisites exist.

Build:

- 60-day paper growth trial.
- Test-mode auto-approval after gates pass.
- Qualified setup ledger.
- Weekly proof cadence tracker.
- Performance evaluator.
- Override detector.
- Verified performance maturity tracker.
- Live promotion review flow.

Operating rules:

- 30 consecutive calendar days.
- £100,000 Alpaca paper account.
- Three proof trades per week where qualified setups exist.
- No forced trades.
- The weekly target is `min(3, qualified_setup_count)`, with policy/risk/venue
  blocks and no-trade rationale recorded explicitly.
- Max drawdown <= 20%.
- Zero manual trade-level overrides.
- 100 closed trades remains the mature statistical benchmark.
- A completed 30-day run with fewer than 100 closed proof trades must be marked
  statistically immature.
- Phase 5 test trades and Q6 deferred-learning artifacts do not count as Phase
  7 proof.
- All saved proof data remains local on the MacBook.

Exit gate:

- 30-day run complete.
- Weekly qualified-setup cadence satisfied or explicitly explained without
  forced trades.
- Expectancy positive after costs.
- Drawdown within cap.
- No manual trade-level overrides.
- Postmortems exist for all closed trades.
- 100-trade benchmark met, or result marked statistically immature.
- Ramin completes structured live-promotion review.

Current handoff state after Q7-12:

- Q7-0 is complete in
  `docs/qadam-phase-7-q7-0-re-entry-operating-rules-audit-2026-05-25.md`
  and writes `data/runtime/phase7_readiness.json`.
- Q7-0 reports `phase7_re_entry_gate_passed=True`,
  `phase7_harness_day_count=30`,
  `phase7_consecutive_calendar_days_required=True`,
  `phase7_weekly_proof_trade_target=3`,
  `phase7_weekly_target_where_qualified_setups_exist=True`,
  `phase7_no_forced_trades=True`,
  `phase7_mature_closed_trade_benchmark=100`,
  `phase7_statistical_immaturity_allowed=True`,
  `phase7_proof_credit_allowed=False`,
  `phase5_test_trades_count_for_phase7=False`,
  `phase7_harness_started=False`,
  `phase7_demo_proof_implementation_allowed=False`,
  `phase7_proof_trade_execution_allowed=False`,
  `live_capital_enabled=False`,
  `manual_trade_level_override_allowed=False`,
  `unsafe_write_counter_total=0`, and `blocker_count=0`.
- Q7-1 is complete in
  `docs/qadam-phase-7-q7-1-artifact-schema-authority-ledger-audit-2026-05-25.md`.
- Q7-1 defines 19 Phase 7 proof artifact contracts, 19 statuses, 20
  authority flags, 14 unsafe counters, and 18 Event Log categories.
- Q7-1 reports `phase7_artifact_schema_status=ok`,
  `phase7_sample_error_count=0`,
  `phase7_sample_authority_enabled_count=0`,
  `phase7_sample_unsafe_counter_total=0`,
  `phase7_sample_proof_contract_status=validated`,
  `phase7_sample_source_posture_status=validated`,
  `phase7_sample_provenance_status=validated`, and
  `phase7_sample_event_contract_status=validated`.
- Yahoo Finance and Preference/PREF MCP remain supplemental-only for Phase 7
  proof; Q-CTRL remains shadow annotation only; Phase 5 lifecycle records and
  Q6 deferred-learning artifacts remain excluded from Phase 7 proof credit.
- Q7-1 grants no proof trade, proof credit, broker POST, live endpoint,
  manual trade-level override, or live capital authority.
- Q7-2 is complete in
  `docs/qadam-phase-7-q7-2-calendar-harness-audit-2026-05-25.md` and writes
  `data/runtime/phase7_calendar_harness.json`.
- Q7-2 reports `phase7_calendar_status=scheduled`,
  `phase7_calendar_stage_status=phase7_calendar_harness_scheduled`,
  `phase7_calendar_day_record_count=30`,
  `phase7_calendar_record_present_count=30`,
  `phase7_calendar_consecutive_calendar_days_validated=True`,
  `phase7_calendar_proof_week_count=5`,
  `phase7_calendar_full_proof_week_count=4`,
  `phase7_calendar_partial_proof_week_count=1`,
  `phase7_calendar_partial_week_trade_pressure_allowed=False`,
  `phase7_calendar_weekly_proof_trade_target=3`,
  `phase7_calendar_no_forced_trades=True`,
  `phase7_calendar_harness_started=False`,
  `phase7_calendar_phase7_demo_day_count=0`,
  `phase7_calendar_qualified_setup_count=0`,
  `phase7_calendar_proof_trade_count=0`,
  `phase7_calendar_closed_proof_trade_count=0`,
  `phase7_calendar_phase7_proof_credit_allowed=False`,
  `phase7_calendar_live_capital_enabled=False`,
  `phase7_calendar_unsafe_write_counter_total=0`, and
  `phase7_calendar_blocker_count=0`.
- Q7-2 grants no proof trade, proof credit, broker POST, live endpoint,
  manual trade-level override, or live capital authority.
- Q7-3 is complete in
  `docs/qadam-phase-7-q7-3-qualified-setup-ledger-audit-2026-05-25.md` and
  writes `data/runtime/phase7_qualified_setup_ledger.json`.
- Q7-3 reports `phase7_setup_ledger_status=read_only_no_q7_setups`,
  `phase7_setup_ledger_stage_status=qualified_setup_ledger_recorded_no_q7_setup_window`,
  `phase7_setup_ledger_calendar_day_record_count=30`,
  `phase7_setup_ledger_daily_setup_decision_count=30`,
  `phase7_setup_ledger_weekly_setup_summary_count=5`,
  `phase7_setup_ledger_candidate_setup_record_count=1`,
  `phase7_setup_ledger_qualified_setup_record_count=0`,
  `phase7_setup_ledger_eligible_setup_count=0`,
  `phase7_setup_ledger_qualified_setup_count=0`,
  `phase7_setup_ledger_blocked_setup_count=0`,
  `phase7_setup_ledger_expired_setup_count=0`,
  `phase7_setup_ledger_no_trade_day_explanation_count=30`,
  `phase7_setup_ledger_no_trade_week_explanation_count=5`,
  `phase7_setup_ledger_rejected_phase5_lifecycle_count=1`,
  `phase7_setup_ledger_supplemental_only_qualification_allowed=False`,
  `phase7_setup_ledger_phase5_test_trades_count_for_phase7=False`,
  `phase7_setup_ledger_proof_trade_count=0`,
  `phase7_setup_ledger_phase7_proof_credit_allowed=False`,
  `phase7_setup_ledger_live_capital_enabled=False`,
  `phase7_setup_ledger_unsafe_write_counter_total=0`, and
  `phase7_setup_ledger_blocker_count=0`.
- Q7-3 grants no qualified setup creation, auto-approval, proof order, proof
  trade, proof credit, broker POST, live endpoint, manual trade-level override,
  or live capital authority.
- Q7-4 is complete in
  `docs/qadam-phase-7-q7-4-weekly-cadence-tracker-audit-2026-05-25.md` and
  writes `data/runtime/phase7_weekly_cadence_tracker.json`.
- Q7-4 reports `phase7_weekly_cadence_status=cadence_satisfied_no_q7_setups`,
  `phase7_weekly_cadence_stage_status=weekly_cadence_recorded_no_qualified_setups`,
  `phase7_weekly_cadence_record_count=5`,
  `phase7_weekly_cadence_satisfied_count=5`,
  `phase7_weekly_cadence_failed_count=0`,
  `phase7_weekly_cadence_weekly_target_total=0`,
  `phase7_weekly_cadence_weekly_target_formula=min(3, qualified_setup_count)`,
  `phase7_weekly_cadence_weekly_proof_trade_target=3`,
  `phase7_weekly_cadence_qualified_setup_count=0`,
  `phase7_weekly_cadence_target_proof_trade_count=0`,
  `phase7_weekly_cadence_proof_trade_count=0`,
  `phase7_weekly_cadence_missed_qualified_setup_count=0`,
  `phase7_weekly_cadence_no_forced_trade_exception_count=5`,
  `phase7_weekly_cadence_no_trade_week_explanation_count=5`,
  `phase7_weekly_cadence_partial_week_trade_pressure_allowed=False`,
  `phase7_weekly_cadence_phase7_proof_credit_allowed=False`,
  `phase7_weekly_cadence_live_capital_enabled=False`,
  `phase7_weekly_cadence_unsafe_write_counter_total=0`, and
  `phase7_weekly_cadence_blocker_count=0`.
- Q7-4 grants no auto-approval, proof order, proof trade, proof credit, broker
  POST, live endpoint, manual trade-level override, or live capital authority.
- Q7-5 is complete in
  `docs/qadam-phase-7-q7-5-test-mode-auto-approval-router-audit-2026-05-25.md`
  and writes `data/runtime/phase7_test_mode_auto_approval_router.json`.
- Q7-5 reports `phase7_auto_approval_status=ready_no_auto_approved_setups`,
  `phase7_auto_approval_stage_status=test_mode_auto_approval_router_ready_no_q7_setups`,
  `phase7_auto_approval_test_mode_auto_approval_allowed=True`,
  `phase7_auto_approval_phase7_test_mode_auto_approval_allowed=True`,
  `phase7_auto_approval_q7_6_proof_order_staging_stage_allowed=True`,
  `phase7_auto_approval_decision_record_count=1`,
  `phase7_auto_approval_qualified_setup_count=0`,
  `phase7_auto_approval_qualified_setup_decision_count=0`,
  `phase7_auto_approval_auto_approved_setup_count=0`,
  `phase7_auto_approval_rejected_setup_decision_count=1`,
  `phase7_auto_approval_phase5_candidate_rejected_count=1`,
  `phase7_auto_approval_fund_manager_trade_level_approval_count=0`,
  `phase7_auto_approval_manual_trade_level_override_attempt_count=0`,
  `phase7_auto_approval_sample_contaminated=False`,
  `phase7_auto_approval_risk_or_kill_switch_bypass_count=0`,
  `phase7_auto_approval_proof_order_staged_count=0`,
  `phase7_auto_approval_proof_trade_count=0`,
  `phase7_auto_approval_phase7_proof_order_staging_allowed=False`,
  `phase7_auto_approval_phase7_proof_credit_allowed=False`,
  `phase7_auto_approval_live_capital_enabled=False`,
  `phase7_auto_approval_unsafe_write_counter_total=0`, and
  `phase7_auto_approval_blocker_count=0`.
- Q7-5 grants no proof order staging, proof trade submission, proof trade
  execution, proof credit, broker POST, live endpoint, manual trade-level
  override, or live capital authority.
- Q7-6 is complete in
  `docs/qadam-phase-7-q7-6-proof-order-staging-audit-2026-05-25.md` and writes
  `data/runtime/phase7_proof_order_staging.json`.
- Q7-6 reports `phase7_proof_order_staging_status=ready_no_staged_orders`,
  `phase7_proof_order_staging_stage_status=proof_order_staging_ready_no_auto_approved_setups`,
  `phase7_proof_order_staging_allowed=True`,
  `phase7_proof_order_staging_phase7_proof_order_staging_allowed=True`,
  `phase7_proof_order_staging_q7_7_guarded_alpaca_stage_allowed=True`,
  `phase7_proof_order_staging_decision_record_count=1`,
  `phase7_proof_order_staging_staged_order_count=0`,
  `phase7_proof_order_staging_blocked_decision_count=1`,
  `phase7_proof_order_staging_auto_approved_setup_count=0`,
  `phase7_proof_order_staging_idempotency_key_count=0`,
  `phase7_proof_order_staging_duplicate_idempotency_key_count=0`,
  `phase7_proof_order_staging_phase5_order_id_reuse_count=0`,
  `phase7_proof_order_staging_event_log_prewrite_ready_count=0`,
  `phase7_proof_order_staging_event_log_prewrite_written_count=0`,
  `phase7_proof_order_staging_pre_trade_snapshot_present_count=0`,
  `phase7_proof_order_staging_proof_trade_count=0`,
  `phase7_proof_order_staging_phase7_proof_credit_allowed=False`,
  `phase7_proof_order_staging_broker_post_allowed=False`,
  `phase7_proof_order_staging_live_capital_enabled=False`,
  `phase7_proof_order_staging_unsafe_write_counter_total=0`, and
  `phase7_proof_order_staging_blocker_count=0`.
- Q7-6 grants no proof trade submission, proof trade execution, proof credit,
  broker POST, Alpaca POST, prediction-market write, crypto-perps write, live
  endpoint, manual trade-level override, or live capital authority.
- Q7-7 is complete in
  `docs/qadam-phase-7-q7-7-guarded-alpaca-paper-submit-audit-2026-05-25.md`
  and writes `data/runtime/phase7_guarded_alpaca_paper_submit_path.json`.
- Q7-7 reports `phase7_guarded_submit_status=ready_no_submit_candidates`,
  `phase7_guarded_submit_stage_status=guarded_alpaca_submit_path_ready_no_staged_orders`,
  `phase7_guarded_submit_source_proof_order_staging_status=ready_no_staged_orders`,
  `phase7_guarded_submit_path_available=True`,
  `phase7_guarded_submit_phase7_proof_trade_submission_allowed=True`,
  `phase7_guarded_submit_q7_8_lifecycle_stage_allowed=True`,
  `phase7_guarded_submit_source_staged_order_count=0`,
  `phase7_guarded_submit_submit_record_count=0`,
  `phase7_guarded_submit_submitted_paper_order_count=0`,
  `phase7_guarded_submit_broker_receipt_record_count=0`,
  `phase7_guarded_submit_idempotency_key_count=0`,
  `phase7_guarded_submit_duplicate_idempotency_key_count=0`,
  `phase7_guarded_submit_phase5_order_id_reuse_count=0`,
  `phase7_guarded_submit_broker_post_called_count=0`,
  `phase7_guarded_submit_alpaca_post_called_count=0`,
  `phase7_guarded_submit_paper_order_submitted_count=0`,
  `phase7_guarded_submit_broker_receipt_created_count=0`,
  `phase7_guarded_submit_proof_trade_count=0`,
  `phase7_guarded_submit_phase7_proof_credit_allowed=False`,
  `phase7_guarded_submit_live_capital_enabled=False`,
  `phase7_guarded_submit_unsafe_write_counter_total=0`, and
  `phase7_guarded_submit_blocker_count=0`.
- Q7-7 grants narrow guarded paper-submit-path authority only for future
  eligible Phase 7 staged proof orders. Broker POST, Alpaca POST, proof trade
  execution, proof lifecycle writes, proof credit, prediction-market write,
  crypto-perps write, live endpoint, manual trade-level override, and live
  capital authority remain disabled.
- Q7-8 is complete in
  `docs/qadam-phase-7-q7-8-proof-lifecycle-monitor-audit-2026-05-25.md` and
  writes `data/runtime/phase7_proof_lifecycle_monitor.json`.
- Q7-8 reports `phase7_lifecycle_status=ready_no_lifecycle_events`,
  `phase7_lifecycle_stage_status=proof_lifecycle_monitor_ready_no_submitted_orders`,
  `phase7_lifecycle_source_guarded_submit_status=ready_no_submit_candidates`,
  `phase7_lifecycle_q7_9_postmortem_stage_allowed=True`,
  `phase7_lifecycle_write_allowed=True`,
  `phase7_lifecycle_source_submitted_paper_order_count=0`,
  `phase7_lifecycle_event_count=0`,
  `phase7_lifecycle_mirrored_submitted_order_count=0`,
  `phase7_lifecycle_open_position_count=0`,
  `phase7_lifecycle_exit_intent_count=0`,
  `phase7_lifecycle_closed_proof_trade_count=0`,
  `phase7_lifecycle_proof_trade_count=0`,
  `phase7_lifecycle_postmortem_due_count=0`,
  `phase7_lifecycle_missing_broker_echo_count=0`,
  `phase7_lifecycle_duplicate_fill_count=0`,
  `phase7_lifecycle_stale_position_count=0`,
  `phase7_lifecycle_failed_reconciliation_count=0`,
  `phase7_lifecycle_phase7_proof_credit_allowed=False`,
  `phase7_lifecycle_live_capital_enabled=False`,
  `phase7_lifecycle_broker_post_called_count=0`,
  `phase7_lifecycle_alpaca_post_called_count=0`,
  `phase7_lifecycle_unsafe_write_counter_total=0`, and
  `phase7_lifecycle_blocker_count=0`.
- Q7-8 grants narrow local proof lifecycle write authority only for lifecycle
  records derived from Q7-7 guarded paper-submit receipts. Broker POST, Alpaca
  POST, proof trade execution authority, postmortem writes, proof credit,
  prediction-market write, crypto-perps write, live endpoint, manual
  trade-level override, and live capital authority remain disabled.
- Q7-9 is complete in
  `docs/qadam-phase-7-q7-9-proof-postmortem-contract-audit-2026-05-25.md`
  and writes `data/runtime/phase7_proof_postmortem_contract.json`.
- Q7-9 reports `phase7_postmortem_status=ready_no_closed_trades`,
  `phase7_postmortem_stage_status=proof_postmortem_contract_ready_no_closed_trades`,
  `phase7_postmortem_source_lifecycle_status=ready_no_lifecycle_events`,
  `phase7_postmortem_q7_10_performance_stage_allowed=True`,
  `phase7_postmortem_write_allowed=True`,
  `phase7_postmortem_source_closed_proof_trade_count=0`,
  `phase7_postmortem_record_count=0`,
  `phase7_postmortem_due_count=0`,
  `phase7_postmortem_due_marker_created_count=0`,
  `phase7_postmortem_packet_required_count=0`,
  `phase7_postmortem_packet_template_count=0`,
  `phase7_postmortem_packet_submitted_count=0`,
  `phase7_postmortem_reviewed_count=0`,
  `phase7_postmortem_explicitly_deferred_count=0`,
  `phase7_postmortem_late_count=0`,
  `phase7_postmortem_missing_count=0`,
  `phase7_postmortem_missing_coverage_count=0`,
  `phase7_postmortem_phase7_proof_credit_allowed=False`,
  `phase7_postmortem_live_capital_enabled=False`,
  `phase7_postmortem_broker_post_called_count=0`,
  `phase7_postmortem_alpaca_post_called_count=0`,
  `phase7_postmortem_unsafe_write_counter_total=0`, and
  `phase7_postmortem_blocker_count=0`.
- Q7-9 grants narrow local postmortem write authority only for due markers and
  packet templates derived from Q7-8 closed proof trades. Postmortem approval,
  learning writes, Knowledge Graph writes, model/trust updates,
  policy/strategy mutation, proof credit, broker POST, Alpaca POST,
  prediction-market write, crypto-perps write, live endpoint, manual
  trade-level override, and live capital authority remain disabled.
- Q7-10 is complete in
  `docs/qadam-phase-7-q7-10-performance-evaluator-audit-2026-05-25.md`
  and writes `data/runtime/phase7_performance_evaluator.json`.
- Q7-10 reports `phase7_performance_status=ready_no_closed_trades`,
  `phase7_performance_stage_status=performance_evaluator_ready_no_closed_trades`,
  `phase7_performance_source_postmortem_status=ready_no_closed_trades`,
  `phase7_performance_q7_11_drawdown_stage_allowed=True`,
  `phase7_performance_write_allowed=True`,
  `phase7_performance_closed_proof_trade_count=0`,
  `phase7_performance_evaluated_trade_count=0`,
  `phase7_performance_metric_record_count=0`,
  `phase7_performance_expectancy_after_costs_gbp=None`,
  `phase7_performance_expectancy_after_costs_positive=False`,
  `phase7_performance_win_rate=None`,
  `phase7_performance_loss_rate=None`,
  `phase7_performance_max_drawdown_fraction_observed=0.0`,
  `phase7_performance_drawdown_within_cap=True`,
  `phase7_performance_statistical_maturity_state=no_sample`,
  `phase7_performance_phase7_proof_credit_allowed=False`,
  `phase7_performance_live_capital_enabled=False`,
  `phase7_performance_broker_post_called_count=0`,
  `phase7_performance_alpaca_post_called_count=0`,
  `phase7_performance_unsafe_write_counter_total=0`, and
  `phase7_performance_blocker_count=0`.
- Q7-10 grants narrow local performance-evaluation write authority only for
  metrics derived from Q7-9 postmortem-covered Q7 proof trades. It does not
  certify Phase 7, grant proof credit, call broker POST, call Alpaca POST,
  write market orders, mutate policy/strategy, permit manual trade-level
  overrides, or enable live capital.
- Q7-11 is complete in
  `docs/qadam-phase-7-q7-11-drawdown-risk-sentinel-audit-2026-05-25.md`
  and writes `data/runtime/phase7_drawdown_risk_sentinel.json`.
- Q7-11 reports `phase7_drawdown_status=ready_no_drawdown_sample`,
  `phase7_drawdown_stage_status=drawdown_sentinel_ready_no_closed_trades`,
  `phase7_drawdown_source_performance_status=ready_no_closed_trades`,
  `phase7_drawdown_q7_12_override_stage_allowed=True`,
  `phase7_drawdown_risk_halt_write_allowed=True`,
  `phase7_drawdown_risk_halt_active=False`,
  `phase7_drawdown_new_proof_trades_frozen=False`,
  `phase7_drawdown_new_proof_order_staging_allowed=True`,
  `phase7_drawdown_new_proof_trade_submission_allowed=True`,
  `phase7_drawdown_source_closed_proof_trade_count=0`,
  `phase7_drawdown_source_evaluated_trade_count=0`,
  `phase7_drawdown_current_equity_gbp=100000.0`,
  `phase7_drawdown_peak_equity_gbp=100000.0`,
  `phase7_drawdown_realized_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_unrealized_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_max_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_drawdown_within_cap=True`,
  `phase7_drawdown_drawdown_state=no_sample_within_cap`,
  `phase7_drawdown_phase7_certification_blocked_by_drawdown=False`,
  `phase7_drawdown_phase7_proof_credit_allowed=False`,
  `phase7_drawdown_live_capital_enabled=False`,
  `phase7_drawdown_broker_post_called_count=0`,
  `phase7_drawdown_alpaca_post_called_count=0`,
  `phase7_drawdown_unsafe_write_counter_total=0`, and
  `phase7_drawdown_blocker_count=0`.
- Q7-11 grants narrow local risk-halt write authority only for drawdown
  sentinel state. It enforces that a drawdown breach above 20 percent freezes
  new Phase 7 proof-order staging and proof-trade submission while preserving
  lifecycle/postmortem/performance closeout authority. It does not certify
  Phase 7, grant proof credit, create proof trades, call broker POST, call
  Alpaca POST, write market orders, mutate policy/strategy, permit manual
  trade-level overrides, or enable live capital.
- Q7-12 is complete in
  `docs/qadam-phase-7-q7-12-override-detector-audit-2026-05-25.md`
  and writes `data/runtime/phase7_override_detector.json`.
- Q7-12 reports `phase7_override_status=clean_no_overrides`,
  `phase7_override_stage_status=override_detector_clean_no_interventions`,
  `phase7_override_source_drawdown_status=ready_no_drawdown_sample`,
  `phase7_override_source_drawdown_new_proof_trades_frozen=False`,
  `phase7_override_q7_13_signal_stage_allowed=True`,
  `phase7_override_detection_write_allowed=True`,
  `phase7_override_sample_contaminated=False`,
  `phase7_override_clean_sample=True`,
  `phase7_override_count=0`,
  `phase7_override_record_count=0`,
  `phase7_override_manual_trade_level_override_count=0`,
  `phase7_override_broker_side_intervention_count=0`,
  `phase7_override_unlinked_lifecycle_record_count=0`,
  `phase7_override_governance_feedback_record_count=3`,
  `phase7_override_governance_feedback_trade_level_intervention_count=0`,
  `phase7_override_new_proof_trades_frozen=False`,
  `phase7_override_new_proof_order_staging_allowed=True`,
  `phase7_override_new_proof_trade_submission_allowed=True`,
  `phase7_override_phase7_certification_blocked_by_override=False`,
  `phase7_override_run_restart_required=False`,
  `phase7_override_phase7_proof_credit_allowed=False`,
  `phase7_override_live_capital_enabled=False`,
  `phase7_override_broker_post_called_count=0`,
  `phase7_override_alpaca_post_called_count=0`,
  `phase7_override_unsafe_write_counter_total=0`, and
  `phase7_override_blocker_count=0`.
- Q7-12 grants narrow local override-detection write authority only for
  clean-sample and contamination evidence. It separates governance feedback
  from trade-level intervention and enforces that manual approvals, rejects,
  edits, exits, broker-side intervention, or unlinked lifecycle records
  contaminate the proof sample, block Phase 7 certification, freeze new proof
  trades, and require restart. It does not certify Phase 7, grant proof credit,
  create proof trades, call broker POST, call Alpaca POST, write market orders,
  mutate policy/strategy, permit manual trade-level override authority, or
  enable live capital.
- Q7-13 is complete in
  `docs/qadam-phase-7-q7-13-source-signal-funnel-evidence-audit-2026-05-25.md`.
  Q7-13 adds `orchestrator/phase7_signal_funnel_evidence.py` and
  `scripts/check_phase7_signal_funnel_evidence.py`, writes
  `data/runtime/phase7_signal_funnel_evidence.json`, and reports
  `phase7_signal_evidence_status=ready_no_proof_trades`,
  `phase7_signal_evidence_stage_status=signal_funnel_evidence_ready_no_proof_trades`,
  `phase7_signal_evidence_source_override_status=clean_no_overrides`,
  `phase7_signal_evidence_source_override_sample_contaminated=False`,
  `phase7_signal_evidence_q7_14_maturity_stage_allowed=True`,
  `phase7_signal_evidence_write_allowed=True`,
  `phase7_signal_evidence_record_count=0`,
  `phase7_signal_evidence_complete_decision_chain_count=0`,
  `phase7_signal_evidence_missing_decision_chain_count=0`,
  `phase7_signal_evidence_private_priors_only_proof_trade_count=0`,
  `phase7_signal_evidence_phase7_certification_blocked_by_signal_evidence=False`,
  `phase7_signal_evidence_phase7_proof_credit_allowed=False`,
  `phase7_signal_evidence_live_capital_enabled=False`, and
  `phase7_signal_evidence_unsafe_write_counter_total=0`. It enforces that
  each proof trade must carry source quorum, source trust, Akber filter, Signal
  Integrity, Risk Agent, Execution Policy, kill-switch state, paper sizing, and
  broker readiness evidence; private priors cannot certify a proof trade; and
  Preference/PREF, Yahoo Finance, and Q-CTRL remain challenge-only,
  supplemental-only, and shadow-only respectively.
- Q7-14 is complete in
  `docs/qadam-phase-7-q7-14-maturity-tracker-audit-2026-05-25.md`. Q7-14
  adds `orchestrator/phase7_maturity_tracker.py` and
  `scripts/check_phase7_maturity_tracker.py`, writes
  `data/runtime/phase7_maturity_tracker.json`, and reports
  `phase7_maturity_status=ready_no_closed_trades`,
  `phase7_maturity_stage_status=maturity_tracker_ready_no_closed_trades`,
  `phase7_maturity_source_signal_status=ready_no_proof_trades`,
  `phase7_maturity_q7_15_cockpit_visibility_stage_allowed=True`,
  `phase7_maturity_write_allowed=True`,
  `phase7_maturity_closed_proof_trade_count=0`,
  `phase7_maturity_mature_benchmark=100`,
  `phase7_maturity_progress_fraction=0.0`,
  `phase7_maturity_closed_trades_remaining_to_mature=100`,
  `phase7_maturity_phase7_mature_benchmark_met=False`,
  `phase7_maturity_phase7_mature_status_blocked=True`,
  `phase7_maturity_phase7_statistically_immature=False`,
  `phase7_maturity_phase7_statistical_immaturity_hidden=False`,
  `phase7_maturity_phase7_30_day_run_complete=False`,
  `phase7_maturity_completed_calendar_day_count=0`,
  `phase7_maturity_phase7_30_day_operational_result_erased_by_immaturity=False`,
  `phase7_maturity_phase7_certification_blocked_by_maturity=True`,
  `phase7_maturity_phase7_proof_credit_allowed=False`,
  `phase7_maturity_live_capital_enabled=False`, and
  `phase7_maturity_unsafe_write_counter_total=0`. It keeps the 100 closed
  proof-trade benchmark visible, blocks mature status below 100 closed proof
  trades, prevents hidden statistical immaturity, and preserves the 30-day
  operational result separately from mature-sample status. It does not certify
  Phase 7, force trades, grant proof credit, call broker routes, write market
  orders, mutate policy/strategy, permit manual trade-level override authority,
  or enable live capital.
- Q7-15 is complete in
  `docs/qadam-phase-7-q7-15-cockpit-mission-control-visibility-audit-2026-05-25.md`.
  Q7-15 adds `orchestrator/phase7_cockpit_visibility.py`,
  `scripts/check_phase7_cockpit_visibility.py`, and
  `scripts/check_dashboard_phase7_demo_proof.js`, wires
  `phase7_demo_proof` into `orchestrator/cockpit_status.py`,
  `landing-page-repo/dashboard.js`, and `scripts/check_dashboard_renderer.js`,
  writes `data/runtime/phase7_cockpit_visibility.json`, and exports a
  backend-derived public Phase 7 demo-proof readout. Current state is
  `phase7_cockpit_visibility_status=visible`,
  `phase7_cockpit_visibility_stage_status=phase7_demo_proof_visible`,
  `phase7_cockpit_visibility_backend_derived=True`,
  `phase7_cockpit_visibility_ui_inferred_readiness_count=0`,
  `phase7_cockpit_visibility_source_artifact_count=14`,
  `phase7_cockpit_visibility_source_missing_count=0`,
  `phase7_cockpit_visibility_source_validation_error_count=0`,
  `phase7_cockpit_visibility_completed_calendar_day_count=0`,
  `phase7_cockpit_visibility_phase7_harness_day_count=30`,
  `phase7_cockpit_visibility_proof_week_count=5`,
  `phase7_cockpit_visibility_qualified_setup_count=0`,
  `phase7_cockpit_visibility_submitted_paper_order_count=0`,
  `phase7_cockpit_visibility_broker_receipt_count=0`,
  `phase7_cockpit_visibility_closed_proof_trade_count=0`,
  `phase7_cockpit_visibility_mature_benchmark=100`,
  `phase7_cockpit_visibility_maturity_progress_fraction=0.0`,
  `phase7_cockpit_visibility_phase7_mature_benchmark_met=False`,
  `phase7_cockpit_visibility_phase7_mature_status_blocked=True`,
  `phase7_cockpit_visibility_phase7_statistical_immaturity_hidden=False`,
  `phase7_cockpit_visibility_phase5_test_trades_count_for_phase7=False`,
  `phase7_cockpit_visibility_phase7_proof_credit_allowed=False`,
  `phase7_cockpit_visibility_live_capital_enabled=False`,
  `phase7_cockpit_visibility_unsafe_write_counter_total=0`, and
  `phase7_cockpit_visibility_q7_16_weekly_review_pack_stage_allowed=True`.
  It exposes day count, proof week, qualified/missed setups, staged/submitted
  paper-order state, broker receipts, proof lifecycle, postmortems,
  expectancy, drawdown, overrides, source/signal evidence, and 100-trade
  maturity from backend artifacts only; it rejects UI-inferred readiness,
  public payload leakage, local paths, hidden statistical immaturity, Phase 5
  proof reuse, proof credit, and live capital.
- Q7-16 is complete in
  `docs/qadam-phase-7-q7-16-weekly-review-pack-audit-2026-05-25.md`.
  Q7-16 adds `orchestrator/phase7_weekly_review_pack.py` and
  `scripts/check_phase7_weekly_review_pack.py`, then writes
  `data/runtime/phase7_weekly_review_pack.json` with one read-only review
  packet for each of the five proof weeks. Current state is
  `phase7_weekly_review_status=read_only`,
  `phase7_weekly_review_stage_status=weekly_review_pack_created`,
  `phase7_weekly_review_packet_created_count=5`,
  `phase7_weekly_review_all_proof_weeks_have_review_packet=True`,
  `phase7_weekly_review_future_policy_comment_allowed=True`,
  `phase7_weekly_review_trade_level_intervention_allowed=False`,
  `phase7_weekly_review_trade_level_intervention_count=0`,
  `phase7_weekly_review_phase7_proof_credit_allowed=False`,
  `phase7_weekly_review_live_capital_enabled=False`,
  `phase7_weekly_review_unsafe_write_counter_total=0`, and
  `phase7_weekly_review_q7_17_certification_stage_allowed=True`. Fund Manager
  comments are limited to future-policy review; current-trade comments,
  trade-level intervention, proof credit, live capital, broker/market writes,
  UI-inferred readiness, and raw/private payload exposure are rejected.
- Q7-17 is complete in
  `docs/qadam-phase-7-q7-17-demo-proof-certification-audit-2026-05-25.md`.
  Q7-17 adds `orchestrator/phase7_certification.py` and
  `scripts/check_phase7_certification.py`, then writes
  `data/runtime/phase7_certification.json`. Current state is
  `phase7_certification_status=blocked`,
  `phase7_certification_stage_status=phase7_certification_blocked_run_incomplete`,
  `phase7_certification_phase7_demo_proof_certified=False`,
  `phase7_certification_phase7_demo_proof_exit_gate=False`,
  `phase7_certification_30_day_operational_result_clean=False`,
  `phase7_certification_30_day_operational_result_preserved=True`,
  `phase7_certification_phase7_30_day_run_complete=False`,
  `phase7_certification_completed_calendar_day_count=0`,
  `phase7_certification_weekly_cadence_satisfied_count=5`,
  `phase7_certification_weekly_review_packet_created_count=5`,
  `phase7_certification_evaluated_trade_count=0`,
  `phase7_certification_expectancy_after_costs_positive=False`,
  `phase7_certification_phase7_mature_benchmark_met=False`,
  `phase7_certification_phase7_proof_credit_allowed=False`,
  `phase7_certification_live_capital_enabled=False`,
  `phase7_certification_unsafe_write_counter_total=0`,
  `phase7_certification_gate_passed_count=6`,
  `phase7_certification_gate_blocked_count=3`, and
  `phase7_certification_q7_18_live_promotion_review_stage_allowed=False`.
  Current blockers are `phase7_30_day_run_incomplete`,
  `positive_expectancy_after_costs_missing`, and
  `phase7_maturity_benchmark_not_met`. Q7-17 preserves a future clean 30-day
  operational result separately from 100-trade maturity, rejects hidden
  statistical immaturity and false mature claims, and keeps proof credit, live
  capital, broker/market writes, Phase 5 proof reuse, and Q7-18 handoff
  closed until certification is real.
- Q7-18 is complete in
  `docs/qadam-phase-7-q7-18-live-promotion-review-flow-audit-2026-05-25.md`.
  Q7-18 adds `orchestrator/phase7_live_promotion_review.py` and
  `scripts/check_phase7_live_promotion_review.py`, then writes
  `data/runtime/phase7_live_promotion_review.json`. Current state is
  `phase7_live_promotion_status=blocked`,
  `phase7_live_promotion_stage_status=live_promotion_review_blocked_phase7_not_certified`,
  `phase7_live_promotion_source_certification_status=blocked`,
  `phase7_live_promotion_phase7_demo_proof_certified=False`,
  `phase7_live_promotion_q7_18_live_promotion_review_stage_allowed=False`,
  `phase7_live_promotion_review_packet_draft_allowed=False`,
  `phase7_live_promotion_review_packet_created=False`,
  `phase7_live_promotion_cooling_off_required=True`,
  `phase7_live_promotion_cooling_off_complete=False`,
  `phase7_live_promotion_live_promotion_approval_state=not_requested`,
  `phase7_live_promotion_live_credentials_enabled=False`,
  `phase7_live_promotion_live_credentials_loaded=False`,
  `phase7_live_promotion_live_capital_enabled=False`,
  `phase7_live_promotion_phase7_proof_credit_allowed=False`,
  `phase7_live_promotion_broker_post_called_count=0`,
  `phase7_live_promotion_alpaca_post_called_count=0`, and
  `phase7_live_promotion_unsafe_write_counter_total=0`. Q7-18 validates the
  future post-certification read-only packet path and rejects early handoff,
  blocked packet creation, live credentials, live capital, broker/market
  writes, proof credit, cooling-off bypass, premature approval, public payload
  leakage, and source display drift.
- Phase 7 staged implementation through Q7-18 is structurally complete. The
  current explicit operational target is the actual 30-day demo-proof run and
  evidence collection needed to unblock Q7-17 and then Q7-18. Phase 8 or live
  capital remains blocked until Q7-17 certifies and Q7-18 can produce the
  read-only live-promotion review packet.
- Operational update after demo-proof run start: the actual Phase 7 run ledger
  is active in `data/runtime/phase7_demo_proof_run.json` through
  `orchestrator/phase7_demo_proof_run.py`,
  `scripts/run_phase7_demo_proof_harness.py`, and
  `scripts/check_phase7_demo_proof_run.py`. The run starts on 2026-05-25
  America/Chicago and ends after 2026-06-23. Q7-17 certification now treats
  `data/runtime/phase7_demo_proof_run.json` as authoritative for the actual
  completed-day count and 30-day completion flag. Current state is
  `phase7_demo_run_status=running`, `phase7_demo_run_state=active`,
  `phase7_demo_run_active_day_number=1`,
  `phase7_demo_run_completed_calendar_day_count=0`,
  `phase7_demo_run_phase7_30_day_run_complete=False`,
  `phase7_demo_run_qualified_setups_exist=False`,
  `phase7_demo_run_submitted_paper_order_count=0`,
  `phase7_demo_run_closed_proof_trade_count=0`,
  `phase7_demo_run_collection_state=active_no_qualified_setups`,
  `phase7_demo_run_phase7_proof_credit_allowed=False`,
  `phase7_demo_run_live_capital_enabled=False`,
  `phase7_demo_run_broker_post_called_count=0`,
  `phase7_demo_run_alpaca_post_called_count=0`, and
  `phase7_demo_run_unsafe_write_counter_total=0`. The first operational pass
  found no Q7-qualified setups and recorded the no-trade rationale instead of
  forcing a trade.

## 15. qadam.trade Route Plan

Current repository state:

- `qadam.trade` and `www.qadam.trade` are both explicitly aliased to the active Vercel production deployment.
- Public landing page exists in `landing-page-repo`.
- Top-right includes `Read Whitepaper` and `Login`.
- Live production cockpit currently uses a static workaround in `landing-page-repo`, not the Next.js cockpit app.
- Live static routes are `/login/`, `/sign-up/`, and `/dashboard/`.
- `/login/` and `/sign-up/` use Supabase JS browser auth with project `eipijgublkypksygsyet`.
- `/dashboard/` checks the Supabase browser session and Qadam founding Fund Manager allowlist before showing the System Map.
- The live System Map is a static founding-release map and clearly says the local MacBook orchestrator is not exposed to Vercel.
- The dedicated dashboard build path is `docs/qadam-dashboard-implementation-plan.md`.
- The live dashboard now prioritizes a top Mission Control surface before the detailed panels and includes a sticky cockpit navigation rail. After login, a Fund Manager should first see which data sources are configured/connected, whether durable Postgres/Timescale replay is ready, what trading philosophy Qadam is currently telling itself, how the API spine, Python COO, local LLM, frontier LLM, quantum oracle, risk gates, and paper account fit together, which trades Qadam is considering or blocking, what positions/orders it holds, current P&L, and the hard safety boundaries.
- Mission Control must include a plain-English trading-strategy narrative that explains Qadam's current strategy posture, why it is choosing that posture, how live sources are informing it, how the posture is evolving through evidence/hypotheses/candidates/orders/positions, and how Akber's 6-stage method remains the practical decision filter.
- Mission Control must also expose the second-order AI infrastructure beneficiary lens as structured strategy context: obvious AI leaders such as Nvidia are reference assets, while Qadam asks whether the better paper setup is in power generation, grid hardware, data-centre electrical infrastructure, semiconductor fabrication capacity, memory, connectivity, or networking. This lens may shape research goals, evidence packets, Strategy Lead challenges, and candidate comparison, but it cannot create a trade, approve risk, stage an order, submit to Alpaca, or enable live capital.
- Mission Control is exported as a public-safe `mission_control` status-contract object and rendered in the static cockpit by `renderMissionControl(status, source)`. It is read-only and cannot promote hypotheses, create trade candidates, submit paper orders, call broker POST routes, write to brokers, or enable live capital.
- The first-month trade layer should explicitly show the £100,000 paper/test account, TradingView-assisted market view, live-capital block, and the full reasoning chain from catalyst to postmortem.
- Immediate design decision: the dashboard is not a generic SaaS card grid and must not force endless scrolling. The main view starts with Mission Control, then the system map; the navigation rail jumps to Mission, Map, Sources, Cognition, Trades, Money, Safety, Runtime, and Governance; every node must show status; the secondary views are source detail, cognition, trade layer, paper-account mirror, safety, communications, Fund Manager comments, and process console.
- Dashboard language must separate observation, hypothesis, trade candidate, blocked trade, staged paper order, submitted paper order, open position, closed trade, and postmortem. It must not imply Qadam is about to make a trade unless the backend state is `staged_paper_order` or `submitted_paper_order`.
- The richer Next.js cockpit remains in `cockpit/` as the local/server-rendered target for later health, settings, and API-backed views.
- Supabase URL Configuration must keep `https://qadam.trade` as Site URL and allow redirects for both `qadam.trade` and `www.qadam.trade`.

Target state:

- Landing page remains public.
- Top-right includes Login.
- Login routes to Supabase Auth.
- Successful sign-in routes to protected `/dashboard`.
- Login allowlist is limited to Ramin, Troy, Akber, Ion, Dan, and pending Anas in the first release.
- `/dashboard` opens the System Map.
- Dashboard includes a private comments/forum area for suggestions and improvement notes.
- Dashboard includes a trade layer that shows candidates, blocked trades, paper orders, open positions, exits, and postmortems once those backends exist.
- Unauthenticated `/dashboard` redirects to login.
- Supabase project `eipijgublkypksygsyet` is the Auth backend for the cockpit; Codex can use the Supabase MCP server after local `codex mcp login supabase` authentication.
- Production deploys remain deliberate while the landing page is live.
- Dashboard Plan D6 is now the local paper-account mirror baseline: the cockpit shows balance, P&L, drawdown, open positions, closed trades, postmortem state, and 100-trade maturity progress from sanitized read-only local data.
- Dashboard Plan D7 is now the local TradingView alert baseline: the cockpit shows TradingView paid-alert fixtures as observed signals only, with no trade-candidate or order path.
- Dashboard Plan D8/D8A/D8B is now the local governance and communications baseline: the cockpit shows Fund Manager comments, Telegram dry-run Communications, and the protected User Guide.
- Dashboard Plan D9 is now the secure live bridge baseline: the cockpit exports a read-only bridge contract and detached signature file, the API route serves only sanitized status to authenticated founding members, write methods are blocked, and the dashboard falls back to the static snapshot if the bridge is unavailable.
- Dashboard Plan D10J is now the navigation UX baseline: the protected cockpit has stable section anchors, sticky navigation, current-section state, mobile navigation behaviour, and an automated preflight check. Navigation remains read-only and cannot approve trades, create orders, write to brokers, send Telegram commands, expose local secrets, or enable live capital.

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

The live access surface is now functional through the static `qadam.trade` cockpit workaround. Treat it as the first-release founding-manager demo shell, not the final cockpit architecture. It proves login, allowlist, and System Map access, while keeping the local orchestrator private.

Phase 1E/1F are implemented at the manifest and runtime-enforcement level. Phase 2 shadow-intelligence contracts, provider-safe probes, Research Goal lifecycle, live Local Research Analyst runs, Strategy Lead shadow handoffs, read-only paper-account context, the first Signal Integrity Gate, the first read-only Risk Agent policy router, the first read-only Execution Policy / kill-switch router, the guarded staged paper-order contract, the read-only broker reconciliation contract, and the guarded paper-submit receipt contract are active. Phase 3 now has a hardened Head of Quant quantum/classical oracle path: backend interface, optional Qiskit Aer local backend, deterministic classical fallback, circuit blueprint, measurement-count output, stable fingerprint, weekly cadence metadata, provider readiness, public-safe cockpit status, hardware submission blocked, local Phase 3A certification, and a docs-only hardware enablement proposal. Dashboard Plan D0-D10J is implemented locally, with Mission Control, sticky navigation UX, Fund Manager comments, dry-run Telegram Communications, the protected D8B User Guide, and a Reasoning workspace that now has a pre-hypothesis Research Goal queue. Mission Control now exposes durable replay readiness as `durable_replay_ready` when OrbStack/Postgres is running, with 35/35 canonical sources replayable from local Timescale. The local `yahoo-finance-api/` checkout is now accepted as a supplemental read-only market-confirmation capability with a dormant Qadam wrapper, Signal Integrity market-confirmation policy, and public-safe cockpit status. Preference/PREF MCP is now implemented through PREF-12 as a supplemental multi-source data plane in `docs/qadam-preference-mcp-integration-plan.md`; it has identity, status/catalog, quota, provenance, Resource Registry, Data Veracity, Trust Score, domain-allowlist, shadow-intelligence enrichment, cockpit/Mission Control visibility, Preference-aware Phase 4 manifestation, Q4-10 approval scoping, Q4-12 certification gating, and upstream source-promotion decisions with no source-count change. PaperOps now has a distinct 20-minute read-only opportunity scan cadence contract that refreshes candidate state without changing the existing hourly guarded paper-submit runner. PREF-12 evaluates six Preference sample upstreams one at a time, maps Polymarket, Kalshi, SEC EDGAR, and vessel tracking to existing registry entries, defers NOAA-style weather and KOL wallet context, promotes zero sources, and preserves the canonical source count at 35; Q4-10 is now `approved` and Q4-12 is certified after explicit Fund Manager approval. A 2026-06-04 defragmentation pass added `docs/README.md` as the documentation index and normalized public dashboard fallback copy to the GBP 100,000 paper-account mandate; the cleanup audit is recorded in `docs/qadam-defragmentation-cleanup-2026-06-04.md`. The 2026-05-22 pre-Phase-3 certification is recorded in `docs/qadam-pre-phase-3-certification-2026-05-22.md`; the 2026-05-23 Phase 3A certification is recorded in `docs/qadam-phase-3-q3-10-phase-3a-certification-audit-2026-05-23.md`; the Q3-11 proposal is recorded in `docs/qadam-phase-3-q3-11-hardware-enablement-proposal-2026-05-23.md`. Phase 3B hardware implementation remains blocked. Live capital, quantum hardware submission, dashboard execution, Telegram execution, LLM risk approval, and unmanaged broker writes remain disabled. Guarded Alpaca paper submission is allowed only through PaperOps when paper-only gates pass. The remaining slices are organized in `docs/qadam-remaining-slices-phased-implementation-plan.md`; the next practical batch is:

1. Keep OrbStack open when working locally and rerun `scripts/start_postgres_timescale_ingestion.sh` after machine restarts or Docker runtime updates.
2. Require `scripts/check_postgres_timescale_ingestion.py --require-live`, `scripts/check_postgres_timescale_replay.py --require-full-source-coverage`, `scripts/check_phase2_durable_replay_cycle.py`, and `scripts/check_strategy_lead_durable_context.py` to remain green before deepening intelligence workflows.
3. Keep the live cockpit snapshot deployed with `durable_ingestion.status=ok`, `contract_status=durable_replay_ready`, `replay_status=ok`, `replayed_source_count=35`, and `missing_source_count=0`.
4. Keep the D6 paper mirror read-only: £100,000 starting/current balance, zero P&L until read-only broker data exists, no live capital, and no write authority.
5. Keep the D7 TradingView alert source observed-only: duplicate protected, Event Log backed, and unable to create trade candidates or orders.
6. Register TradingView MCP as read-only market/technical-analysis tooling when Codex CLI access is available; no TradingView retail data API key is expected.
6A. Keep `yahoo-finance-api/` as a supplemental read-only market-data capability. The Qadam Yahoo Finance adapter, sample check, Signal Integrity market-confirmation policy, and public-safe cockpit wrapper now exist; before relying on live Yahoo reads, install dependencies deliberately, pass live mode with `YFINANCE_ENABLED=true`, and keep no execution, fill, receipt, broker, reconciliation, or live-capital authority.
6B. Implement Preference/PREF MCP through `docs/qadam-preference-mcp-integration-plan.md`. PREF-0 capability review is complete in `docs/qadam-preference-mcp-pref-0-capability-review-audit-2026-05-24.md`; PREF-1 identity/status gating is complete in `docs/qadam-preference-mcp-pref-1-identity-status-gate-audit-2026-05-24.md`; PREF-2 catalog/schema gating is complete in `docs/qadam-preference-mcp-pref-2-tool-catalog-audit-2026-05-24.md`; PREF-3 offline sample adapter scaffolding is complete in `docs/qadam-preference-mcp-pref-3-offline-sample-adapter-audit-2026-05-24.md`; PREF-4 live read-only smoke gating is complete in `docs/qadam-preference-mcp-pref-4-live-read-only-smoke-gate-audit-2026-05-24.md` and currently blocks before network calls until a valid non-anonymous Preference identity exists; PREF-5 provenance/source-quorum policy is complete in `docs/qadam-preference-mcp-pref-5-provenance-source-quorum-audit-2026-05-24.md`; PREF-6 source inventory, Resource Registry, and trust policy is complete in `docs/qadam-preference-mcp-pref-6-source-inventory-registry-trust-policy-audit-2026-05-24.md`; PREF-7 first-trading-universe domain pack mapping is complete in `docs/qadam-preference-mcp-pref-7-first-trading-universe-domain-packs-audit-2026-05-24.md`; PREF-8 shadow intelligence enrichment is complete in `docs/qadam-preference-mcp-pref-8-shadow-intelligence-enrichment-audit-2026-05-24.md`; PREF-9 cockpit and Mission Control visibility is complete in `docs/qadam-preference-mcp-pref-9-cockpit-mission-control-visibility-audit-2026-05-24.md`; PREF-10 Phase 4 re-manifestation is complete in `docs/qadam-preference-mcp-pref-10-phase-4-re-manifestation-audit-2026-05-24.md`; PREF-11 certification and Phase 5 gate update is complete in `docs/qadam-preference-mcp-pref-11-certification-phase-5-gate-audit-2026-05-24.md`; PREF-12 source-promotion decisions are complete in `docs/qadam-preference-mcp-pref-12-source-promotion-decisions-audit-2026-05-24.md`. Treat Preference as a supplemental data plane, not source 36, until individual upstream sources are explicitly promoted through a later registry decision.
7. Use `docs/api-specs.md` as the credential onboarding ledger; add keys gradually to `data/runtime/qadam-secrets.env`, never to Git.
8. Run `scripts/refresh_acled_token.py --write --validate-read`, then rerun `scripts/check_supplied_credentials.py` after starting LM Studio or refreshing ACLED. Keep Kalshi deferred and UnusualWhales missing until those external conditions change.
9. Keep `scripts/check_phase1_data_spine.py` and `scripts/check_phase1_agent_os.py` green before adding new intelligence, source, broker, or notification behavior.
10. Keep D8 Fund Manager comments constrained to governance notes: comments can link to modules, sources, signals, trade candidates, and postmortems, but cannot approve trades.
11. Keep D8A Telegram Bot Communications in dry-run/notify-only mode until a later explicit send-test gate is approved.
12. Start the LM Studio local server and run the local `/models` readiness check against `gemma-4-e4b`.
13. Run `scripts/check_local_research_analyst.py --live` once LM Studio is reachable to record the first true local Research Analyst assessment.
13A. Run `scripts/run_phase2_shadow_cycle.py --durable-replay` after Timescale is green to feed replayable observations and paper-account context through Research Analyst and Strategy Lead shadow workflows without depending on live source availability.
13A.1. Keep `scripts/check_research_goal_lifecycle.py` green and require Phase 2 source observations to pass through Research Goals before becoming hypotheses or later trade-candidate references.
13B. Run `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` whenever LM Studio is running to refresh the live-source variant of the same shadow workflow.
14. Run the Gemini model-list credential probe without text generation.
14A. Run `scripts/run_pre_phase3_operational_routine.sh --stage phase3-readiness` before treating Phase 3A evidence as current; require provider/scheduler readiness, cockpit/dashboard export, secret scan, two local/fallback oracle jobs, local backend validation, circuit blueprint, input fingerprint, weekly cadence metadata, zero provider calls, zero hardware scheduler enablement, zero hardware submissions, zero execution approvals, zero paper-order approvals, and zero trade-candidate creation.
15. Keep all model, dashboard, Telegram, and quantum outputs non-executable after Signal Integrity, Risk Agent policy review, Execution Policy review, broker reconciliation review, paper-submit receipt review, and Head of Quant oracle review.
16. Keep the staged paper-order contract guarded: it must explain what would be staged, why it is blocked or allowed, how idempotency is allocated, and how it reconciles before any PaperOps submit attempt.
17. Keep broker reconciliation read-only except for the explicit Alpaca paper-submit transport: it must define broker echo checks, idempotency, prewrite event logging, duplicate-order guards, post-submit reconciliation, and postmortem links while keeping live capital at zero.
18. Keep the paper-submit receipt contract guarded: it can produce a simulated or real Alpaca paper receipt only after broker reconciliation prerequisites pass, with no live-capital route and no new order intent on retry.
19. Keep `scripts/check_paperops_opportunity_scan_cadence.py` green before changing the paper-trading cadence. The opportunity scan target is every 20 minutes for candidate refresh only; the existing hourly PaperOps runner remains the guarded submission transport until a later explicit local scheduler is installed and audited.
20. RS-0 authority reconciliation and blocker hygiene is implemented through
    `orchestrator/paper_authority_reconciliation.py`,
    `scripts/check_paper_authority_reconciliation.py`, cockpit status, and the
    public dashboard safety strip. The current runtime can now distinguish
    paper authority from current actionability: Qadam is authorized for guarded
    Alpaca paper trading with live capital disabled, while paused automation,
    no fresh eligible setup, or paper lifecycle gates are surfaced as
    operational/opportunity blockers instead of stale safety contradictions.
21. RS-2 Research Goal hardening is implemented. Keep
    `scripts/check_research_goal_lifecycle.py`, `scripts/run_phase2_shadow_cycle.py
    --durable-replay`, `scripts/check_phase2_durable_replay_cycle.py`, and
    `scripts/check_cockpit_status.py` green so every trade candidate keeps
    Research Goal lineage and no pre-signal object gains broker authority.
22. RS-3 Market Context Packet and Source Quality is implemented through
    `orchestrator/market_context.py`, `scripts/check_market_context_packet.py`,
    Phase 2 source-context integration, cockpit status export, and the public
    dashboard Reasoning workspace. The RS-3 packet attaches source taxonomy,
    trust/freshness/source-quality posture, Yahoo Finance supplemental
    price/volume confirmation, TradingView MCP supplemental technical context,
    Alpaca paper-account context, missing/degraded source posture, contradictory
    evidence, and source-quorum result to each Research Goal while keeping
    candidate creation, risk approval, paper orders, broker writes, source
    quorum credit, and live capital disabled.
23. RS-5 Guarded Paper Autonomy is implemented out of sequence as a safety and
    authority hardening slice. The daily paper-trade target is now explicitly a
    minimum, not a ceiling; multiple same-day Alpaca paper submits are allowed
    only through the guarded PaperOps-2 route when each setup has a distinct
    Research Goal, candidate, and idempotency key, passes risk/exposure/drawdown
    and source-quorum checks, and live capital remains disabled. The current
    runtime is armed and paper-authorized, but has no fresh distinct setup, so
    the public why-not state is `daily_target_met_and_no_additional_distinct_setup`.
    No paper order was submitted during the RS-5 implementation checks.
24. Continue the remaining-slices rollout with RS-4 or RS-6 depending on the
    immediate goal: RS-4 deepens Local Research Analyst and Strategy Lead runs
    over Research Goals plus RS-3 market context packets; RS-6 hardens lifecycle,
    portfolio, and postmortem handling after guarded paper submits occur.
25. RS-6 Lifecycle, Portfolio, And Postmortem Hardening is now implemented.
    Qadam writes `data/runtime/paper_lifecycle_portfolio_postmortem.json`,
    validates it with `scripts/check_paper_lifecycle_portfolio_postmortem.py`,
    and exports the sanitized status through `paper_lifecycle_portfolio_postmortem`
    in the cockpit contract. Current validated state: portfolio value source is
    `alpaca_paper_account_mirror`, the dashboard balance ticker is broker/account
    derived, 7 open positions, 7 mirrored orders, 7 closed paper trades, 7
    postmortem markers, 0 missing postmortem markers, 7 postmortems due, 0
    completed postmortems, 0 Phase 7 verified proof records, and 0 mirror-only
    trades counted for proof. This is audit hardening only: it adds no broker
    write route, no live-capital authority, no forced trades, and no proof credit.
26. RS-7 Operator Inbox, Telegram, And Human Oversight is now implemented.
    Qadam writes `data/runtime/operator_inbox.json`, durable history/comment/
    acknowledgement/event JSONL records, validates the contract with
    `scripts/check_operator_inbox.py`, exports a public-safe `operator_inbox`
    block through cockpit status, and renders the inbox in the dashboard
    Operations/Governance view. Current validated state: `status=ok`, 48 inbox
    items, 48 open items, 2 high-or-critical items, 1 postmortem-due item, 23
    paper-trade-related items, 48 Telegram-linked items, 8 read-only Telegram
    commands, 0 validation errors, and no public leak. Telegram can summarize
    and notify only: it cannot create signals, approve risk, approve execution,
    place paper orders, write to Alpaca, call Q-CTRL, or enable live capital.
27. RS-8 Dashboard Mission Control Completion is now implemented. Cockpit
    status exports a public-safe `mission_control.mission_brief` contract with
    seven Fund Manager question cards: what Qadam is watching, thinking about,
    forbidden from doing, considering, traded on paper, worth as a portfolio,
    and blocked or waiting on. The static dashboard renders the Mission Brief
    as the top Overview surface with visible click/tap expansion controls,
    quick links to Mission, Map, Sources, Reasoning, Trades, Portfolio, Safety,
    Inbox, and Runtime, and a single next-operator-action readout. Validation is
    enforced by `scripts/check_cockpit_status.py` and
    `scripts/check_dashboard_rs8_mission_control.js`. This is visibility and
    operator triage only: the dashboard, Telegram intake, LLMs, data sources,
    and quantum oracle still cannot approve, place, modify, close, fund, or
    grant performance credit for trades.
28. RS-9 Learning Loop And Full-Potential Review is now implemented. Qadam
    writes `data/runtime/rs9_learning_loop_review.json`, validates it with
    `scripts/check_rs9_learning_loop.py`, exports the sanitized
    `rs9_learning_loop` block through cockpit status, and renders it in the
    dashboard paper lifecycle learning area. Current contract: five learning
    proposal surfaces are visible and blocked pending Fund Manager review:
    strategy weights, source trust, risk sizing, market-context
    interpretation, and worldview lens strength. RS-9 can explain whether
    Qadam is improving, degrading, or uncertain, and can state whether guarded
    PaperOps remains unblocked. It cannot silently mutate strategy, trust,
    risk, market interpretation, worldview lens strength, policy, knowledge
    graph, model weights, trust scores, dashboard commands, Telegram commands,
    broker writes, live capital, or Phase 7 proof credit.
29. RS-10 Final Paper Autonomy Certification is now implemented. Qadam writes
    `data/runtime/rs10_final_paper_autonomy_certification.json`, validates it
    with `scripts/check_rs10_final_paper_autonomy_certification.py`, exports the
    sanitized `rs10_final_paper_autonomy_certification` cockpit block, and
    renders the state in Mission Control and the Trades view. Current contract:
    `final_paper_autonomy_certified=True`,
    `guarded_paper_autonomy_allowed=True`, and
    `multiple_paper_trades_per_day_allowed_when_gates_pass=True`. This means
    Qadam is authorized for guarded Alpaca paper trading and multiple paper
    trades per day when the PaperOps gates pass. It does not force a trade:
    `autonomy_currently_actionable=False` is valid when the current runner
    reports `paperops2_submit_gate_not_ready` or `paper_poll_gate_not_ready`.
    Live capital, dashboard execution, Telegram execution, LLM execution,
    quantum execution, unmanaged broker writes, stale blocker promotion, fake
    submit authority, and Phase 7 proof credit remain blocked.

Note: the following implementation snapshots are retained as historical context.
The latest `Update after Q6-17` note below is authoritative for the current Phase 6
target.

Historical implementation snapshot before Q5E-11: Phase 3A local provider/scheduler readiness certification passed on 2026-05-23, Q3-11 hardware enablement is documented as proposal-only, Q4-0 through Q4-12 Phase 4 implementation stages are recorded, Q5-0 through Q5-15 are implemented, Q5E-1 through Q5E-9 built and certified the guarded paper lifecycle, and Q5E-10 recorded the formal Phase 5 to Phase 6 handoff. This paragraph is retained for context only; the latest Phase 6 update below is authoritative for current Phase 6 state.

Superseding current Q6 note: Q6-0 is complete in `docs/qadam-phase-6-q6-0-re-entry-gate-audit-2026-05-24.md`, Q6-1 is complete in `docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-2026-05-24.md`, Q6-2 is complete in `docs/qadam-phase-6-q6-2-learning-source-intake-audit-2026-05-24.md`, Q6-3 is complete in `docs/qadam-phase-6-q6-3-closed-trade-outcome-schema-audit-2026-05-25.md`, Q6-4 is complete in `docs/qadam-phase-6-q6-4-postmortem-packet-contract-audit-2026-05-25.md`, Q6-5 is complete in `docs/qadam-phase-6-q6-5-postmortem-agent-draft-audit-2026-05-25.md`, Q6-6 is complete in `docs/qadam-phase-6-q6-6-analysis-packets-audit-2026-05-25.md`, Q6-7 is complete in `docs/qadam-phase-6-q6-7-reducer-review-gate-audit-2026-05-25.md`, Q6-8 is complete in `docs/qadam-phase-6-q6-8-outcome-linker-audit-2026-05-25.md`, Q6-9 is complete in `docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-2026-05-25.md`, and Q6-10 is complete in `docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-2026-05-25.md`. Q5-14 reports `paper_trade_drill_complete=True`, `phase5_paper_trade_drill_exit_gate_passed=True`, and `blocker_count=0`; Q5-15 reports `phase5_certified=True`, `phase5_exit_gate=True`, `phase6_handoff_allowed=True`, `phase7_planning_allowed=True`, and `phase7_proof_credit_allowed=False`; Q5E-10/Q5E-11 reports `phase6_learning_loop_plan_allowed=True`, `phase6_learning_loop_implementation_allowed=False`, `phase6_learning_write_allowed=False`, `phase6_knowledge_graph_write_allowed=False`, and `live_capital_enabled_count=0`. Q6-0 reports `phase6_re_entry_gate_passed=True`, `q6_1_artifact_schema_stage_allowed=True`, `phase6_learning_loop_implementation_allowed=False`, `phase6_postmortem_ingestion_allowed=False`, `phase6_learning_write_allowed=False`, `phase6_knowledge_graph_write_allowed=False`, `phase7_proof_credit_allowed=False`, `unsafe_write_counter_total=0`, and `blocker_count=0`. Q6-1 reports `phase6_artifact_schema_status=ok`, 17 artifact contracts, 20 false authority defaults, 15 zero unsafe counters, six required Event Log categories, validated source posture, validated provenance, and validated probes against hidden learning writes, policy mutation, live capital, local path leakage, and Phase 7 proof credit. Q6-2 reports one Q5E `postmortem_due` marker, 20 source refs, 11 required source refs present, nine optional source refs present, `phase5_hash_mutation_count=0`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. Q6-3 reports one normalized closed-trade outcome, `broker_truth_separated=True`, five unknown fields, six deferred fields, `source_hash_mutation_count=0`, `learning_write_allowed=False`, `knowledge_graph_write_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. Q6-4 reports 13 required packet sections, source refs or hypothesis markers required for assertions, narrative-only packets rejected, uncited conclusions rejected, `postmortem_draft_created=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. Q6-5 reports one deterministic backend-derived postmortem draft, 13 packet sections, 20 source-cited assertions, five unknown markers, six deferred markers, three missing broker-fill ref markers, `postmortem_approved=False`, `approval_state=not_requested`, `llm_used=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. Q6-6 reports five deterministic analysis packets for catalyst, pricing, regime, execution, and override readiness, `claim_count=10`, `all_claims_cited=True`, `confidence_packet_count=5`, `uncertainty_count=5`, `missing_evidence_count=9`, `postmortem_approved=False`, `approval_state=not_requested`, `llm_used=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. Q6-7 reports a review-required reduced postmortem with no approval or write authority, Q6-8 reports a complete reference-only outcome-link graph with no source mutation or copied payloads, Q6-9 reports a pending-review governance ledger with no default approval and all downstream learning advancement blocked, and Q6-10 reports a blocked Knowledge Graph staged-write gate with five blocked candidate actions, zero staged entries, no graph commits, no Chroma/backend graph writes, no destructive overwrite, and no proof credit. The current explicit build target is Q6-11: Knowledge Graph Read Path.

Update after Q6-7: `docs/qadam-phase-6-q6-7-reducer-review-gate-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-7 added a review-required reduced postmortem, five proposed classifications, five review-queue items, and Event Log replay evidence while keeping `postmortem_approved=False`, `approval_state=not_requested`, `approval_logged=False`, `learning_action_count=0`, `learning_action_approved_count=0`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-8 - Outcome Linker.

Update after Q6-8: `docs/qadam-phase-6-q6-8-outcome-linker-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-8 added a complete reference-only outcome-link artifact with 21 linked refs, all 12 required links present, all nine optional context links present, no copied raw/private payloads, no local path or secret ref exposure, no source artifact mutation, and Event Log replay evidence while keeping `link_write_allowed=False`, `postmortem_approved=False`, `approval_state=not_requested`, `approval_logged=False`, `learning_action_count=0`, `learning_action_approved_count=0`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-9 - Learning Approval Ledger.

Update after Q6-9: `docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-9 added a pending-review governance ledger with five proposed actions deferred pending explicit reviewer/Event Log approval, no default approval, and all downstream learning advancement blocked while keeping `approved_action_count=0`, `learning_action_approved_count=0`, `downstream_advance_allowed=False`, `knowledge_graph_staged_write_allowed=False`, `model_weight_update_proposal_allowed=False`, `trust_score_update_proposal_allowed=False`, `strategy_learning_proposal_allowed=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-10 - Knowledge Graph Staged Writes.

Update after Q6-10: `docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-10 added the Knowledge Graph staged-write gate and carried the five Q6-9 candidate actions forward as blocked records because the approval ledger is explicitly `deferred`. It keeps `staged_entry_count=0`, `staged_write_allowed=False`, `knowledge_graph_staged_write_allowed=False`, `missing_approval_blocks_staging=True`, `knowledge_graph_commit_allowed=False`, `chroma_write_allowed=False`, `graph_backend_write_allowed=False`, `actual_graph_commit_created=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `destructive_overwrite_allowed=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-11 - Knowledge Graph Read Path.

Update after Q6-11: `docs/qadam-phase-6-q6-11-knowledge-graph-read-path-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-11 added a read-only Knowledge Graph view over the blocked Q6-10 staging gate, returns one guarded Q5E seed-context result for `crude oil` and `paper lifecycle` searches, exposes cockpit-safe counts and states only, and keeps `approved_learning_entry_count=0`, `staged_result_count=0`, `write_allowed=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`, `chroma_write_created=False`, `graph_backend_write_created=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-12 - Model Weight Update Proposals.

Update after Q6-12: `docs/qadam-phase-6-q6-12-model-weight-update-proposals-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-12 added the model-weight update proposal gate over the blocked Q6-11 read path. Because Q6-9 approval is explicitly `deferred`, it records one blocked no-op proposal record with seven before/after model weights, zero delta, `active_proposal_count=0`, `approved_evidence_count=0`, `bayesian_update_count=0`, `model_weight_update_proposal_allowed=False`, `model_weight_update_proposed=False`, `apply_allowed=False`, `model_weight_update_applied=False`, `active_model_weight_mutated=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`, `chroma_write_created=False`, `graph_backend_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-13 - Trust Score Update Proposals.

Update after Q6-13: `docs/qadam-phase-6-q6-13-trust-score-update-proposals-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-13 added the trust-score update proposal gate over the blocked Q6-12 model-weight proposal gate. Because Q6-9 approval is explicitly `deferred`, it records 35 blocked no-op canonical source-score proposal records, two supplemental policy records for Yahoo Finance and Preference/PREF, `before_score=0.539143`, `after_score=0.539143`, zero score delta, `active_proposal_count=0`, `trust_score_update_count=0`, `trust_score_update_proposal_allowed=False`, `trust_score_update_proposed=False`, `apply_allowed=False`, `trust_score_update_applied=False`, `active_trust_score_mutated=False`, `canonical_rank_mutated=False`, `source_quorum_credit_granted=False`, `single_source_verdict_rejected=True`, `supplemental_only_verdict_rejected=True`, `yahoo_finance_score_included=False`, `preference_mcp_source_quorum_credit_allowed=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`, `chroma_write_created=False`, `graph_backend_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-14 - Shadow Strategy Runner.

Update after Q6-14: `docs/qadam-phase-6-q6-14-shadow-strategy-runner-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-14 added the shadow strategy replay gate over the blocked Q6-13 trust-score proposal gate. Because Q6-9 approval is explicitly `deferred`, it records three blocked no-op shadow replay variants, `active_replay_count=0`, `blocked_replay_count=3`, `evaluated_variant_count=0`, `actual_vs_hypothetical_comparison_count=3`, `evaluated_comparison_count=0`, `replay_output_exists=True`, `shadow_strategy_replay_allowed=False`, `shadow_strategy_replay_created=False`, `trade_candidate_creation_allowed=False`, `trade_candidate_created=False`, `trade_candidate_created_count=0`, `order_creation_allowed=False`, `paper_order_allowed=False`, `paper_order_allowed_count=0`, `paper_order_created=False`, `paper_order_created_count=0`, `execution_allowed=False`, `execution_allowed_count=0`, `execution_intent_created=False`, `execution_intent_created_count=0`, `broker_post_allowed=False`, `alpaca_post_allowed=False`, `broker_post_called_count=0`, `alpaca_post_called_count=0`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`, `chroma_write_created=False`, `graph_backend_write_created=False`, `model_weight_update_created=False`, `trust_score_update_created=False`, `policy_mutation_created=False`, `strategy_mutation_created=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-15 - Architect Learning Summary.

Update after Q6-15: `docs/qadam-phase-6-q6-15-architect-learning-summary-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-15 added the Architect learning summary over the blocked Q6-14 shadow replay gate. Because Q6-9 approval is explicitly `deferred`, it records four blocked recommendation records, `active_recommendation_count=0`, `blocked_recommendation_count=4`, `governance_pending_count=4`, one policy recommendation, one strategy recommendation, one risk-limit recommendation, one source/model/trust recommendation, `recommendation_apply_allowed=False`, `policy_mutation_allowed=False`, `policy_mutation_created=False`, `strategy_mutation_allowed=False`, `strategy_mutation_created=False`, `risk_limit_update_allowed=False`, `risk_limit_update_created=False`, `source_weight_update_allowed=False`, `source_weight_update_created=False`, `model_weight_update_allowed=False`, `model_weight_update_created=False`, `trust_score_update_allowed=False`, `trust_score_update_created=False`, `learning_write_created=False`, `knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`, `chroma_write_created=False`, `graph_backend_write_created=False`, `phase5_source_artifacts_mutated=False`, `phase5_test_trades_count_for_phase7=False`, `phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`. The current explicit build target is Q6-16 - Journal And Cockpit Visibility.

Update after Q6-16: `docs/qadam-phase-6-q6-16-journal-cockpit-visibility-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-16 added the backend-derived cockpit/dashboard visibility layer through `orchestrator/phase6_cockpit_visibility.py`, `scripts/check_phase6_cockpit_visibility.py`, `orchestrator/cockpit_status.py`, `landing-page-repo/dashboard.js`, and `scripts/check_dashboard_phase6_learning_loop.js`. It writes `data/runtime/phase6_cockpit_learning_visibility.json`, exports `phase6_learning_loop` in the public cockpit snapshot, and renders the Q6-16 Learning Loop Journal Visibility panel from backend artifacts only. Current state is `status=visible`, `visibility_state=backend_derived_deferred_learning_visible`, `learning_state=deferred_learning_visible`, `backend_derived=True`, `ui_inferred_readiness_count=0`, `backend_parity_error_count=0`, `postmortem_due_count=1`, `postmortem_resolved_count=0`, `approval_state=deferred`, `pending_review_action_count=0`, `deferred_action_count=5`, `learning_actions_review_satisfied=True`, `staged_graph_entry_count=0`, `knowledge_graph_read_result_count=1`, `model_weight_proposal_count=1`, `trust_score_proposal_count=35`, `shadow_replay_variant_count=3`, `architect_recommendation_count=4`, `blocked_authority_count=20`, `unsafe_write_counter_total=0`, `raw_payload_exposed_count=0`, `local_path_exposed_count=0`, `secret_ref_exposed_count=0`, `broker_identifier_exposed_count=0`, `phase6_learning_write_allowed=False`, `phase6_knowledge_graph_write_allowed=False`, `phase6_model_weight_update_allowed=False`, `phase6_trust_score_update_allowed=False`, `phase6_architect_policy_mutation_allowed=False`, `phase7_proof_credit_allowed=False`, and `live_capital_enabled=False`. The current explicit build target is Q6-17 - Phase 6 Certification.

Update after Q6-17: `docs/qadam-phase-6-q6-17-phase-6-certification-audit-2026-05-25.md` is now complete. This update supersedes the preceding Q6 current-target sentence. Q6-17 added the Phase 6 certification gate through `orchestrator/phase6_certification.py`, `scripts/check_phase6_certification.py`, `orchestrator/cockpit_status.py`, `landing-page-repo/dashboard.js`, and `scripts/check_dashboard_phase6_certification.js`. The follow-up unblock script `scripts/defer_phase6_learning_review_for_certification.py` records the explicit Fund Manager deferral for the pending Q6 learning approval/postmortem review, refreshes Q6-9 through Q6-17, and exports the certified cockpit snapshot. Current state is `status=certified`, `stage_status=phase6_certified`, `phase6_certified=True`, `phase6_exit_gate=True`, `phase7_demo_proof_planning_allowed=True`, `phase7_proof_credit_allowed=False`, `phase5_test_trades_count_for_phase7=False`, `input_gate_count=17`, `input_gate_passed_count=17`, `input_gate_blocked_count=0`, `certification_blocker_count=0`, `postmortem_due_count=1`, `postmortem_resolved_count=0`, `postmortem_explicitly_deferred_count=1`, `unresolved_postmortem_count=0`, `reviewed_postmortem_coverage_satisfied=True`, `approval_state=deferred`, `pending_review_action_count=0`, `explicitly_deferred_action_count=5`, `learning_actions_review_satisfied=True`, `knowledge_graph_requirement_satisfied=True`, `knowledge_graph_read_result_count=1`, `model_weight_proposal_count=1`, `trust_score_proposal_count=35`, `shadow_replay_variant_count=3`, `architect_recommendation_count=4`, `cockpit_visibility_status=visible`, `blocking_unsafe_count=0`, `unsafe_write_counter_total=0`, and `live_capital_enabled=False`. The current explicit build target is Phase 7 Demo Proof planning; Phase 7 proof credit remains blocked until a future Phase 7 gate earns it from Phase 7 evidence.

Update after Q5-9: `docs/qadam-phase-5-q5-9-prediction-market-adapter-audit-2026-05-24.md` is now complete. Q5-9 added six read-only or disabled prediction-market route records, preserved Polymarket and Kalshi Preference/PREF MCP context as policy/risk caution only, kept source-quorum credit false, exposed cockpit and Mission Control status, and left Polymarket, Kalshi, Hyperliquid, dFlow, PriveX-style perps, paper-order, broker, live-endpoint, and live-capital write authority at zero. The next explicit build target is Q5-10 - Telegram Notifier.

Update after Q5-10: `docs/qadam-phase-5-q5-10-telegram-notifier-audit-2026-05-24.md` is now complete. Q5-10 added nine state-matched Telegram notification records, writes nine Event Log entries, validates three current dry-run outbox messages for risk-blocked, kill-switch-change, and degraded-source-or-venue states, suppresses lifecycle alerts until matching backend state exists, exposes cockpit and Mission Control status, and keeps Telegram command handling, live sends, paper orders, broker writes, execution, prediction-market writes, and live capital at zero. The next explicit build target is Q5-11 - Position Monitor And Reconciliation Loop.

Update after Q5-11: `docs/qadam-phase-5-q5-11-position-monitor-audit-2026-05-24.md` is now complete. Q5-11 added read-only position lifecycle monitoring and reconciliation records, writes two Event Log entries, currently records blocked sentinels because no submitted paper orders or positions exist, exposes cockpit and Mission Control status, and keeps submit, close, resize, cancel, broker-write, Alpaca POST, position-mutation, and live capital authority at zero.

Update after Q5-12: `docs/qadam-phase-5-q5-12-signal-review-governance-actions-audit-2026-05-24.md` is now complete. Q5-12 added Signal Review UI and governance actions, records five public-safe review records, shows 45 backend-sourced decision-chain steps, writes five governance comment Event Log entries and five kill-switch action-intent Event Log entries, exposes cockpit and Mission Control status, renders in the dashboard Trade Layer, and keeps UI-inferred readiness plus approval, order, close, resize, cancel, broker-write, prediction-market-write, kill-switch-mutation, and live-capital authority at zero. The next explicit build target is Q5-13 - Functional System Map Dashboard.

Update after Q5-13: `docs/qadam-phase-5-q5-13-functional-system-map-dashboard-audit-2026-05-24.md` is now complete. Q5-13 added a backend-sourced Functional System Map Dashboard with 27 nodes, six lanes, 10 Layer B nodes, exact display/backend parity, Event Log artifact recording, source posture badges for canonical/Yahoo Finance/Preference MCP, and guardrails proving the dashboard does not say Qadam is trading without submitted/open/closed backend state. It keeps UI-inferred readiness, unsafe controls, paper-submit path availability, broker writes, prediction-market writes, and live-capital authority at zero. The next explicit build target is Q5-14 - End-To-End Paper Trade Drill.

Update after Q5-14: `docs/qadam-phase-5-q5-14-end-to-end-paper-trade-drill-audit-2026-05-24.md` is now complete for the implementation harness, and `docs/qadam-phase-5-q5-14-exit-unblock-approval-audit-2026-05-24.md` records the explicit guarded Alpaca paper-submit approval. Q5-14 added a dedicated guarded paper trade drill artifact, 13 backend-sourced lifecycle steps, 13 Event Log entries, cockpit and Mission Control visibility, dashboard rendering, display/backend parity checks, and blocker reporting across source context, Signal Integrity, approval policy, risk sizing, kill switches, execution adapter, staging, submit gate, broker receipt, position open, position close, postmortem due, and Telegram/dashboard sync. After Q5E-4, the current drill state is `blocked_prerequisites_missing`, with `paper_trade_drill_complete=False`, `phase5_paper_trade_drill_exit_gate_passed=False`, `paper_submit_approval_present=True`, `paper_submit_path_available_count=1`, `submitted_paper_order_count=0`, `open_position_count=0`, `closed_trade_count=0`, `postmortem_due_count=0`, `broker_post_called_count=0`, and `live_capital_enabled_count=0`.

Update after Q5-15: `docs/qadam-phase-5-q5-15-phase-5-certification-audit-2026-05-24.md` is now complete for the certification evaluation. Q5-15 added a Phase 5 certification artifact, one certification Event Log entry, 15 backend-sourced input gates, cockpit and Mission Control visibility, dashboard rendering, display/backend parity checks, and probes against false certification, live capital, prediction-market writes, Phase 7 proof credit, and UI-inferred readiness. It correctly reports `status=blocked`, `phase5_certified=False`, `phase5_exit_gate=False`, `phase6_handoff_allowed=False`, `phase7_planning_allowed=False`, `phase7_proof_credit_allowed=False`, `input_gate_passed_count=14`, `input_gate_blocked_count=1`, `submitted_paper_order_count=0`, `open_position_count=0`, `closed_trade_count=0`, and `live_capital_enabled_count=0`. The next explicit build target is the upstream Q5-14 lifecycle unblock after risk sizing, staged-order, dry-run, guarded submit-path, and position lifecycle prerequisites exist.

Update after Q5E-1 and Q5E-2: `docs/qadam-phase-5-q5e-1-risk-evidence-lift-audit-2026-05-24.md` and `docs/qadam-phase-5-q5e-2-paper-order-staging-audit-2026-05-24.md` are now complete. Q5E-1 added a non-executing evidence lift for `crude_oil_energy_security_disruption`: Signal Integrity reports `passed_to_risk_shadow`, non-Yahoo market confirmation is available, `pricing_gap=pass_pricing_gap_confirmed`, Yahoo Finance remains supplemental-only, and Q5-3 now reports `paper_size_eligible_count=1` with `target_proposed_risk_gbp=5.0` against `target_max_risk_gbp=10.0`. Q5E-2 then updated Q5-6 so that eligible Alpaca-paper risk review can create one staged paper-order object with `selected_venue=alpaca_paper`, `order_state=staged_ready_for_dry_run`, deterministic idempotency, `side=buy`, `quantity=1.0`, `order_type=market`, and `time_in_force=day`. Q5-6 now reports `staged_order_count=1` and `blocked_count=4`, while broker POST calls, paper-order submission, broker writes, positions, prediction-market writes, and live capital remain zero. The next explicit build target is Q5E-3: let Q5-7 create a dry-run request preview and simulated receipt from the staged paper order without submitting it.

Update after Q5E-3: `docs/qadam-phase-5-q5e-3-alpaca-paper-dry-run-audit-2026-05-24.md` is now complete. Q5-7 now consumes the staged Alpaca paper-order record and reports `source_staged_order_count=1`, `request_preview_count=1`, and `dry_run_receipt_count=1`; the target record has `request_preview_allowed=True`, `dry_run_receipt_created=True`, `receipt_state=dry_run_receipt_preview_ready`, and deterministic Q5-7 idempotency present. Broker POST calls, Alpaca POST calls, broker writes, paper-order submission, real broker receipt creation, live endpoints, positions, and live capital remain zero. This unblocked Q5E-4.

Update after Q5E-4: `docs/qadam-phase-5-q5e-4-paper-submit-path-audit-2026-05-24.md` is now complete. Q5-8 now consumes the Q5E-3 dry-run preview and explicit paper-submit approval, exposing one guarded Alpaca paper-submit path for `crude_oil_energy_security_disruption` with `submit_path_available_count=1`, `paper_submit_gate_state=ready_for_guarded_paper_submit`, `receipt_state=paper_submit_gate_ready`, `idempotency_key_allocated_for_submit=True`, `event_log_prewrite.prewrite_complete=True`, and `pre_trade_snapshot.captured=True`. This is guarded path readiness only: `broker_post_called_count=0`, `alpaca_post_called_count=0`, `paper_order_submitted_count=0`, `live_endpoint_allowed_count=0`, `prediction_market_write_allowed_count=0`, and `live_capital_enabled_count=0`. Q5-14 remains blocked because there is still no submitted paper order, broker receipt, mirrored submitted order, open position, closed trade, or postmortem due marker. Q5-15 remains blocked with `phase5_certified=False` and `phase6_handoff_allowed=False`. The next explicit build target is Q5E-5: create the guarded submitted paper-order plus broker-receipt state and mirror it into the position-monitor path without enabling live capital or Phase 7 proof credit.

Update after Q5E-5: `docs/qadam-phase-5-q5e-5-submitted-paper-order-audit-2026-05-24.md` is now complete. Q5-8 now records one guarded local submitted paper-order and one local broker receipt for `crude_oil_energy_security_disruption`: `paper_order_submitted_count=1`, `broker_submit_receipt_created_count=1`, `submitted_order_ref=q5e5-paper-order-crude_oil_energy_security_disruption`, and `broker_receipt_ref=q5e5-local-broker-receipt-crude_oil_energy_security_disruption`. This is a local lifecycle state only: `broker_post_called_count=0`, `alpaca_post_called_count=0`, `live_endpoint_allowed_count=0`, `prediction_market_write_allowed_count=0`, `live_capital_enabled_count=0`, and `phase7_proof_credit_allowed=False`. Q5-11 now reports `submitted_order_count=1` and `mirrored_order_count=1`, while `open_position_count=0`, `closed_trade_count=0`, and `postmortem_due_count=0`. Q5-14 remains blocked with `closed_trade_missing`, `execution_adapter_not_staging_ready`, `open_position_missing`, and `postmortem_due_missing`. Q5-15 remains blocked with `phase5_certified=False` and `phase6_handoff_allowed=False`. The next explicit build target is Q5E-6: create the guarded open-position lifecycle state from the mirrored submitted order without enabling broker POST, live capital, autonomous position mutation, or Phase 7 proof credit.

Update after Q5E-6: `docs/qadam-phase-5-q5e-6-open-position-audit-2026-05-24.md` is now complete. Q5E-6 records one guarded local open-position lifecycle state for `crude_oil_energy_security_disruption`: `status=open_position`, `source_order_ref=q5e5-paper-order-crude_oil_energy_security_disruption`, `position_ref=q5e6-open-position-crude_oil_energy_security_disruption`, `order_status_for_mirror=filled`, and `position_status_for_mirror=open_position`. Q5-11 now reports `submitted_order_count=1`, `mirrored_order_count=1`, and `open_position_count=1`, while `closed_trade_count=0` and `postmortem_due_count=0`. Q5-14 remains blocked with `closed_trade_missing`, `execution_adapter_not_staging_ready`, and `postmortem_due_missing`. Q5-15 remains blocked with `phase5_certified=False` and `phase6_handoff_allowed=False`. The next explicit build target is Q5E-7: create the guarded closed-trade lifecycle state from the Q5E-6 open position without enabling broker POST, live capital, autonomous position mutation, or Phase 7 proof credit.

Update after Q5E-7: `docs/qadam-phase-5-q5e-7-closed-trade-audit-2026-05-24.md` is now complete. Q5E-7 records one guarded local closed-trade lifecycle state for `crude_oil_energy_security_disruption`: `status=closed_trade`, `source_position_ref=q5e6-open-position-crude_oil_energy_security_disruption`, `closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`, and `postmortem_status=postmortem_pending_marker`. Q5-11 now reports `submitted_order_count=1`, `mirrored_order_count=1`, `open_position_count=0`, `closed_trade_count=1`, and `postmortem_due_count=0`. Q5-14 remains blocked with `execution_adapter_not_staging_ready` and `postmortem_due_missing`. Q5-15 remains blocked with `phase5_certified=False` and `phase6_handoff_allowed=False`. The next explicit build target is Q5E-8: create the guarded postmortem due marker from the Q5E-7 closed trade without enabling broker POST, live capital, autonomous position mutation, or Phase 7 proof credit.

Update after Q5E-8: `docs/qadam-phase-5-q5e-8-postmortem-due-audit-2026-05-24.md` is now complete. Q5E-8 records one guarded local postmortem-due marker for `crude_oil_energy_security_disruption`: `status=postmortem_due`, `source_closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`, `postmortem_due_ref=q5e8-postmortem-due-crude_oil_energy_security_disruption`, and `postmortem_status=postmortem_due`. Q5-11 now reports `submitted_order_count=1`, `mirrored_order_count=1`, `open_position_count=0`, `closed_trade_count=1`, and `postmortem_due_count=1`. Q5-14 remains blocked only with `execution_adapter_not_staging_ready`. Q5-15 remains blocked with `phase5_certified=False` and `phase6_handoff_allowed=False`. The next explicit build target is Q5E-9: resolve the remaining execution-adapter staging-readiness blocker without enabling broker POST, live capital, autonomous execution, or Phase 7 proof credit.

Update after Q5E-9: `docs/qadam-phase-5-q5e-9-execution-adapter-readiness-audit-2026-05-24.md` is now complete. The execution adapter now reports exactly one guarded Alpaca paper staging-readiness signal with `downstream_staging_allowed_count=1`, `staging_readiness_scope=guarded_q5e_lifecycle_readiness`, and `guarded_postmortem_due_ready=True`. This is read-only readiness only: broker POST, Alpaca POST, broker writes, paper-order staging/submission authority, prediction-market writes, crypto-perps writes, live endpoints, live capital, and Phase 7 proof credit remain disabled. Q5-14 now reports `paper_trade_drill_complete=True`, `phase5_paper_trade_drill_exit_gate_passed=True`, and `blocker_count=0`. Q5-15 now reports `status=eligible`, `phase5_certified=True`, `phase5_exit_gate=True`, `phase6_handoff_allowed=True`, `phase7_planning_allowed=True`, `phase7_proof_credit_allowed=False`, `input_gate_passed_count=15`, and `input_gate_blocked_count=0`. The next explicit build target is the Phase 6 - Learning Loop implementation plan.

Update after Q5E-10: `docs/qadam-phase-5-q5e-10-phase-6-handoff-closeout-audit-2026-05-24.md` is now complete. Q5E-10 added `orchestrator/phase5_phase6_handoff.py` and `scripts/check_phase5_phase6_handoff.py`, writes `data/runtime/phase5_phase6_handoff.json`, records one handoff Event Log entry, and reports `status=eligible`, `handoff_state=phase6_learning_loop_plan_ready`, `phase6_learning_loop_plan_allowed=True`, and `phase6_learning_loop_implementation_allowed=False`. It allows only Q6 planning: Phase 6 postmortem ingestion, learning writes, knowledge-graph writes, model-weight updates, trust-score updates, shadow-strategy runner activation, Architect policy mutation, broker POST, Alpaca POST, live endpoints, live capital, and Phase 7 proof credit remain disabled. The next explicit build target is Q6-0: the Phase 6 - Learning Loop implementation plan.

This gets Qadam ready to think without letting prompts, tools, or future model calls accumulate hidden authority.
