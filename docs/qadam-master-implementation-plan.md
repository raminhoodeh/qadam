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
| Dashboard appendix | `docs/qadam-dashboard-implementation-plan.md` | Cockpit/system-map/trade-layer implementation path. |
| Telegram appendix | `docs/qadam-telegram-bot-implementation-plan.md` | Member communications rail, bot phases, message classes, and dashboard visibility. |
| User guide | `docs/qadam-user-guide.md` | Plain-English cockpit guide for founding members. |
| Live source appendix | `docs/api-source-inventory.md` | 35 live/live-adjacent feeds and source conflicts. |
| API credential appendix | `docs/api-specs.md` | Full API/provider inventory, credential placeholders, onboarding batches, and unresolved provider decisions. |
| API key acquisition plan | `docs/qadam-api-key-acquisition-plan.md` | Practical provider-by-provider order, cost posture, official links, and validation checks for getting keys safely. |
| Resource appendix | `docs/qadam-resource-registry.md` | Papers, products, OSS stacks, frameworks, build references. |
| Private worldview appendix | `docs/how-the-world-works-integration.md` | Qadam's private world-model foundation and evidence boundary. |

Rule: update this master plan when the build sequence changes. Update appendices only when implementation detail changes.

## 3. The Three Knowledge Layers

Qadam should not mix all inputs into one bucket.

| Layer | What It Contains | What It Does |
| --- | --- | --- |
| Live Source Registry | ACLED, FIRMS, Oref, UnusualWhales, Polymarket, Kalshi, Alpaca, GDELT, Telegram, RSS, TradingView alerts, etc. | Feeds the machine with observable data and heartbeat status. |
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
| Knowledge Graph | Resolved catalyst memory and nearest-neighbour recall. |
| Cockpit | `qadam.trade` login, dashboard, system map, signal review, comments forum, postmortems. |
| Fund Manager Forum | Private suggestions and governance comments from Ramin, Troy, Akber, Anas, and Ion. |
| Telegram Bot Communications | Outbound-only member alerts for trade lifecycle updates, insight digests, system warnings, and dashboard links. No execution authority. |
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
- Never retry order-creating POST requests automatically.
- Venue account/subaccount/network scope must be explicit before any order path is enabled.
- Quantum is a weekly oracle, not a real-time trading brain.
- Two proof trades per week is a discipline target, not a quota.
- 100 closed trades is the maturity benchmark.

## 6. First Release Trial Mode

The first release of Qadam is a local-first autonomous trial system.

Operating constraints:

- Account: £1000 test/paper account.
- First-month sprint: use the £1000 test account as the proof surface, with TradingView as the visible market/chart layer and later alert source, before any live-capital path exists.
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
- Live static cockpit renders the System Map after Supabase login.
- The live cockpit clearly marks itself as a static web shell while the local MacBook orchestrator remains private and not exposed to Vercel.
- The D1 cockpit status contract validates in paper mode, blocks live capital, exports modules/sources/forbidden actions, and strips secrets, emails, local paths, raw payloads, and broker authority.
- The D2 dashboard renderer populates key cockpit panels from the D1 snapshot and keeps empty trade/P&L states explicit.
- The D3 Watching View renders all registered sources from the public-safe snapshot without exposing secret names or local paths.
- The D4 Cognition View renders shadow-only reasoning state from the public-safe snapshot without exposing raw references or implying execution authority.
- The D5 Trade Intent Board renders candidate and blocked trade-intent records from the local store, with `execution_allowed=false`, `paper_order_allowed=false`, and no staged/submitted/open paper-trade state.
- The D6 Paper Account Mirror renders the £1000 trial account state from local read-only data, with `write_authority=false`, `live_capital_enabled=false`, and 0/100 maturity until closed paper trades exist.
- The D7 TradingView alert contract renders alert-derived observed signals with duplicate protection, receiver-key fail-closed behavior, `execution_allowed=false`, `paper_order_allowed=false`, and `trade_candidate_created=false`.
- The cockpit renders Qadam's private worldview as decision context for hypotheses, observed signals, candidates, and blocked trades, while preserving the boundary that world-model claims are private priors and not factual evidence or trade triggers.
- Telegram communications are represented as notify-only: bot status, queue state, delivery state, verified/pending member counts, and last message status can appear in the cockpit, but no Telegram route can trigger broker action or hidden approval.
- The protected guide explains every major cockpit panel, status label, trade state, member permission, daily review routine, and red flag without exposing secrets or implying execution authority.
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
- Current local blocker as of 2026-05-19: no Docker-compatible CLI is available on the Mac, so the bootstrap exits explicitly with `postgres_timescale_runtime_status=missing` instead of falsely claiming durable ingestion is live.
- A read-only Phase 1 live adapter promotion layer now exists for ACLED, UnusualWhales, Polymarket, Kalshi, Alpaca, AIS, Wingbits, BLS, ECB, UN Comtrade, SEC EDGAR, Reddit, X, and Telegram.
- These 14 adapter contracts join the already promoted GDELT, Oref, NASA FIRMS, FRED, and RSS adapters, taking promoted adapter coverage to 19 sources.
- The new adapter layer has sample mode, masked credential status, raw payload archival, normalized events, degraded-state handling, and fail-closed live fetches.
- `scripts/check_phase1_live_source_hardening.py` is now the Phase 1 live-source hardening gate. It validates each of the 19 promoted sources one by one, writes `data/runtime/phase1_live_source_validation.json`, appends a local history file, and classifies every source as `live`, `degraded`, `missing_credentials`, or `sample_ready`.
- `scripts/check_supplied_credentials.py` is now the supplied-credential validation gate for NASA FIRMS, FRED, ACLED, Alpaca paper, Telegram, Gemini, LM Studio, plus explicit Kalshi deferred and UnusualWhales missing states.
- `scripts/refresh_acled_token.py --write --validate-read` is now the ACLED token refresh automation. It uses the refresh-token grant first, falls back to local email/password only when needed, atomically updates `data/runtime/qadam-secrets.env`, and writes a redacted local refresh report.
- `scripts/check_alpaca_paper_mirror.py --live` is now the Alpaca paper-account mirror gate. It calls only GET endpoints for account, positions, orders, and portfolio history, writes sanitized local mirror files, exposes balance/P&L/positions/orders to the cockpit, and preserves `write_authority=false`, `live_capital_enabled=false`, and `paper_order_allowed=false`.
- Current live read-only validation on 2026-05-18: live sources are NASA FIRMS, FRED, RSS, Polymarket, Alpaca paper account mirror, BLS public sample, ECB public exchange-rate series, SEC EDGAR public filing metadata, and Telegram bot status. Degraded but explicit sources are GDELT, Oref, and ACLED. Missing/deferred credential sources are UnusualWhales, Kalshi, AIS Maritime, Wingbits, UN Comtrade, Reddit, and X/Twitter.
- Current supplied-credential validation on 2026-05-19: NASA FIRMS, FRED, Alpaca paper, Telegram, Gemini, and LM Studio are live; ACLED is configured but degraded with provider HTTP 403; Kalshi is intentionally deferred due to location/account availability; UnusualWhales remains the useful missing Batch A key. The Alpaca mirror currently reads paper equity from Alpaca, while Qadam's first-release trial allocation remains capped by policy at £1000 until later risk/execution gates exist.
- ACLED now uses the current documented endpoint pattern `https://acleddata.com/api/acled/read` rather than the legacy `api.acleddata.com` hostname. Token freshness is automated and a 2026-05-19 refresh run succeeded with the refresh-token grant, updating the ignored local secret file. The post-refresh ACLED read validation still returned HTTP 403, so the remaining blocker is entitlement or account scope, not local token plumbing.
- ECB now validates against a concrete public data-series endpoint instead of an incomplete base URL.
- Live fetch success is not claimed until each provider credential, account scope, rate limit, and provider terms are configured locally.
- Historical backfill planning and a local sample-runner now exist for 12 priority sources, distinguishing ready read-only jobs from blocked missing-credential jobs before any large provider pull is attempted.
- Trust Score seed now covers all 35 sources, with 22 sources above 0.5 and three physical/logistics sources passing the current seed threshold; these are still priors until backtests/live observations replace them.
- Postgres/Timescale durable ingestion has a contract check that passes as `ready_waiting_for_local_service` when local Postgres is offline and can be tightened with `--require-live` once Docker/OrbStack/Podman/Colima is running. The dedicated bootstrap is now implemented; the remaining action is installing/opening a compatible runtime and rerunning it.
- API onboarding is now an explicit Phase 1 workstream: `docs/api-specs.md` defines Batch A-D credential placeholders, canonical 35-source requirements, platform/model/broker/notification keys, optional upstream `world-monitor/` providers, and open source-provider decisions.
- As of 2026-05-18, the local ignored secret file has credentials for NASA FIRMS, Alpaca paper, ACLED, FRED, Q-CTRL, Telegram bot token/username/private target/group target, Gemini/Google model keys, and LM Studio settings. Kalshi, UnusualWhales, UN Comtrade, Reddit, X, AIS/Wingbits/logistics providers, SEC user agent, IBM Quantum, and AWS Braket remain pending or deferred; BLS and ECB currently work in public read-only mode but should still receive explicit provider configuration where available.
- ACLED now has access-token and refresh-token material stored locally plus automatic token renewal. Entitlement/read-scope verification still needs to pass before ACLED counts as durable live infrastructure.
- Telegram bot credentials and private/group delivery targets are local, but member delivery remains dry-run and send-disabled until explicit send-test approval exists.
- GDELT is promoted to the first real read-only adapter path; Oref is promoted as the second, higher-trust conflict alert adapter; NASA FIRMS is promoted as the first physical anomaly adapter; FRED is promoted as the first macro regime adapter; RSS is promoted as the first narrative feed adapter.
- No promoted adapter is allowed to influence signal confidence without corroboration and Signal Integrity Gate approval.
- TradingView note: a paid TradingView account does not provide a normal retail data API key. Treat TradingView MCP as read-only market/technical-analysis tooling that does not require a TradingView login, and treat the paid TradingView account as useful later for webhook alerts once Qadam has a secure receiver.

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
- `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` now runs the first deeper Phase 2 loop: live read-only observations from available sources are queued into Research Analyst shadow packets, deterministic shadow triage writes non-executable signals, local Gemma compresses the queue, the read-only Alpaca paper-account mirror is attached as account context, and a Strategy Lead shadow handoff packet is written with broker/risk execution blocked.
- `scripts/check_phase2_paper_context.py` validates the paper-account context bridge in dry mode: the context reaches the Strategy Lead packet, stays sanitized, and keeps `execution_allowed=false`, `paper_order_allowed=false`, `write_authority=false`, and `live_capital_enabled=false`.
- Current 2026-05-19 live Phase 2 cycle result: live read-only observations from FRED, RSS, Polymarket, Alpaca, and Telegram produced eleven queued Research Analyst packets, four shadow signals, one live local Gemma assessment, and one Strategy Lead shadow handoff packet. NASA FIRMS was live but had zero current events in the queried window. The Strategy Lead packet included read-only paper-account context: Alpaca paper mirror connected, current broker paper balance visible, zero open positions, zero mirrored orders, no write authority, and live capital disabled. All outputs remained `execution_allowed=false` and `paper_order_allowed=false`.
- The public-safe cockpit status contract can expose sanitized local Research Analyst assessment summaries and read-only paper-account context without prompts, raw model text, local paths, broker IDs, or secrets.
- `scripts/check_shadow_intelligence.py` is wired into `start_qadam.sh`.
- `scripts/check_local_research_analyst.py` is wired into `start_qadam.sh` in dry-contract mode.
- System health, FastMCP-style tools, and cockpit registry cards expose Shadow Intelligence status.
- Every Phase 2 output remains non-executable.

Build:

- Proposed Signal schema.
- Catalyst Evidence Trail schema.
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
- Shadow signal store.

Exit gate:

- Layer A produces Proposed Signals.
- Local Research Analyst can compress queued packets through LM Studio in shadow mode when the local server is running.
- Strategy Lead can receive queued shadow handoff packets, but cannot call broker-write tools or approve risk.
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
- Telegram alerts match dashboard state exactly and never imply execution before backend state reaches `staged_paper_order`, `submitted_paper_order`, `open_position`, or `closed_trade`.
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
- The live dashboard now needs to prioritize a diagrammatic operating map, a read-only process console, a first-month trade layer, Fund Manager comments, a cognition view, a money/timeline view, and explicit forbidden-action status.
- The first-month trade layer should explicitly show the £1000 paper/test account, TradingView-assisted market view, live-capital block, and the full reasoning chain from catalyst to postmortem.
- Immediate design decision: the dashboard is not a generic SaaS card grid. The main view is the system map; every node must show status; the secondary views are process console, Fund Manager view, trade layer, and comments.
- Dashboard language must separate observation, hypothesis, trade candidate, blocked trade, staged paper order, submitted paper order, open position, closed trade, and postmortem. It must not imply Qadam is about to make a trade unless the backend state is `staged_paper_order` or `submitted_paper_order`.
- The richer Next.js cockpit remains in `cockpit/` as the local/server-rendered target for later health, settings, and API-backed views.
- Supabase URL Configuration must keep `https://qadam.trade` as Site URL and allow redirects for both `qadam.trade` and `www.qadam.trade`.

Target state:

- Landing page remains public.
- Top-right includes Login.
- Login routes to Supabase Auth.
- Successful sign-in routes to protected `/dashboard`.
- Login allowlist is limited to Ramin, Troy, Akber, Anas, and Ion in the first release.
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
- Next target is Dashboard Plan D10: choose whether the secure bridge should first support public TradingView webhook ingestion, read-only broker mirroring, or both, without adding broker-write authority.

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

Phase 1E/1F are implemented at the manifest and runtime-enforcement level. Phase 2 shadow-intelligence contracts, provider-safe probes, live Local Research Analyst runs, Strategy Lead shadow handoffs, and read-only paper-account context are active. Dashboard Plan D0-D9 is implemented locally, with the protected D8B User Guide now added. The next practical batch is to keep durable Postgres/Timescale green, keep live credential validation fresh, and start the Signal Integrity Gate / Risk Agent design without creating any order route:

1. Install or open a Docker-compatible runtime on the Mac: Docker Desktop, OrbStack, Podman, or Colima.
2. Run `scripts/start_postgres_timescale_ingestion.sh` and require `postgres_timescale_durable_ingestion=ok`.
3. Run `scripts/check_postgres_timescale_replay.py --require-full-source-coverage` and require all 35 sources to be replayable from `source_observation`.
4. Keep the D6 paper mirror read-only: £1000 starting/current balance, zero P&L until read-only broker data exists, no live capital, and no write authority.
5. Keep the D7 TradingView alert source observed-only: duplicate protected, Event Log backed, and unable to create trade candidates or orders.
6. Register TradingView MCP as read-only market/technical-analysis tooling when Codex CLI access is available; no TradingView retail data API key is expected.
7. Use `docs/api-specs.md` as the credential onboarding ledger; add keys gradually to `data/runtime/qadam-secrets.env`, never to Git.
8. Run `scripts/refresh_acled_token.py --write --validate-read`, then rerun `scripts/check_supplied_credentials.py` after starting LM Studio or refreshing ACLED. Keep Kalshi deferred and UnusualWhales missing until those external conditions change.
9. Keep `scripts/check_phase1_data_spine.py` and `scripts/check_phase1_agent_os.py` green before adding new intelligence, source, broker, or notification behavior.
10. Build D8 Fund Manager comments around module, source, signal, trade candidate, and postmortem references.
11. Build D8A Telegram Bot Communications in dry-run mode: local member registry, outbox, message templates, cockpit status, and dashboard Communications panel.
12. Start the LM Studio local server and run the local `/models` readiness check against `gemma-4-e4b`.
13. Run `scripts/check_local_research_analyst.py --live` once LM Studio is reachable to record the first true local Research Analyst assessment.
13A. Run `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` whenever LM Studio is running to feed available live read-only observations and paper-account context through Research Analyst and Strategy Lead shadow workflows.
14. Run the Gemini model-list credential probe without text generation.
15. Keep all outputs non-executable and hidden/debug-only until Signal Integrity Gate exists.

This gets Qadam ready to think without letting prompts, tools, or future model calls accumulate hidden authority.
