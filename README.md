# Qadam

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

Primary spec: `specs/qadam-specs.md`.

Planning docs:

- `docs/qadam-master-implementation-plan.md` - start here; this is the day-to-day control document.
- `docs/qadam-dashboard-implementation-plan.md` - cockpit, system map, cognition view, trade layer, money/timeline, and phased dashboard build path.
- `docs/qadam-telegram-bot-implementation-plan.md` - Telegram bot communications rail for member alerts, insights, trade lifecycle updates, and dashboard visibility.
- `docs/qadam-user-guide.md` - founding-member user guide for reading and using the Qadam cockpit.
- `docs/api-key-setup.md`
- `docs/qadam-api-key-acquisition-plan.md`
- `docs/api-specs.md` - full API/provider inventory, credential placeholders, source onboarding batches, and unresolved provider decisions.
- `docs/qadam-for-fund-managers.md` - trader-facing explanation for Ramin, Troy, Akber, Anas, and Ion.
- `docs/api-source-inventory.md`
- `docs/qadam-resource-registry.md`
- `docs/how-the-world-works-integration.md`
- `docs/qadam-modular-implementation-plan.md`
- `docs/qadam-foundational-architecture-plan.md`
- `docs/qadam-implementation-plan.md`

## Product Identity

Qadam is an autonomous intelligence engine with a transparent recommendation interface.

- Autonomous underneath: observe, reason, size risk, paper/live trade under guardrails, log outcomes, and run postmortems.
- Advisory on top: the cockpit at `qadam.trade` shows the founding Fund Managers what Qadam is watching, why a recommendation exists, the evidence behind it, how the autonomous engine would act, and how similar signals historically performed.
- Internal first: no public community tier, no external broker-connected autopilot, and no signal publishing in v1.

First-release cockpit access is limited to Ramin, Troy, Akber, Anas, and Ion. The cockpit includes a private comments/forum area where the founding Fund Managers can suggest improvements, debate signals, flag issues, and leave governance notes.

## Operating Doctrine

- Layer A surfaces; Layer B acts.
- Demo before live, always.
- Human gates are policy-based.
- Quantum is a weekly oracle, not a real-time trading brain.
- AI and Quantum are leverage, not authority.
- Fail closed, never open.
- Everything is logged and replayable.
- Telegram is the primary human-in-the-loop channel.

Qadam is not HFT, copy trading, a general stock screener, a financial advisor, a black-box bot, or a frequency machine. Two proof trades per week is a discipline target, not a quota. Rare high-conviction opportunities are expected to be scarce.

## First Release Trial Mode

The first release is a local-first autonomous trial on a £1000 paper/test account. Qadam may trade autonomously in that test account once the paper-trading gates are built, but no live capital is in scope.

- Hardware target: Ramin's MacBook with 1TB SSD and 24GB unified memory.
- Storage: saved Qadam state stays local by default.
- Local stores: PostgreSQL + TimescaleDB Event Log, ChromaDB Knowledge Graph, raw payload archive, runtime/config files, and model/cache data.
- Cloud calls: APIs, Gemini, quantum backends, Vercel, and paper-broker APIs are allowed, but canonical saved state remains local.
- Human controls: the founding Fund Managers can review, comment, and use allowed kill-switches or strategy toggles; individual test trades are autonomous so the proof sample stays clean.
- Cockpit must clearly show `TEST ACCOUNT` / `PAPER MODE` before autonomous test trading.

## Architecture

Layer A - Intelligence Engine:

- Live ingress pipelines across 35 World Monitor sources.
- Qadam resource registry for strategy wisdom, reference products, open-source stacks, papers, and analytical frameworks.
- How The World Works private world-model foundation for esoteric edge hypotheses, power maps, narrative lenses, and adversarial scenario generation.
- Gemma 4 local triage on MLX.
- Gemini 3.1 Pro cloud research and 100-persona swarm simulation.
- Quantum Engine weekly oracle for Pattern Recognition and Strategy Collapse.
- Q-CTRL credential registered locally for future quantum optimization/error-suppression experiments; no Phase 0 API calls.
- Signal Assembly with evidence trail and Black-Scholes Gap report.

Layer B - Orchestration Layer:

- Approval Policy Router.
- Risk Agent with hard caps and Kelly sizing.
- Disabled/read-only Execution Venue Registry before any order path is allowed.
- Broker adapters for Alpaca, pmxt/Polyrouter, and later CCXT/IBKR or PriveX-style perps rails if separately approved.
- Global, Strategy, and Venue kill-switches.
- Trade monitoring, exits, postmortems, and Bayesian weight updates.

Cross-cutting:

- PostgreSQL + TimescaleDB Event Log.
- Local JSONL Event Log fallback for Phase 0 replay before Postgres is running.
- ChromaDB Knowledge Graph.
- Architect Agent.
- Next.js cockpit.
- Telegram notification path.

## qadam.trade Cockpit

`qadam.trade` is the login surface and command cockpit. After Supabase login, the first view is a system map showing how the fund is wired together:

- Python script [COO]
- Local LLM [Research Analyst]
- Frontier LLM [Strategy Lead]
- Quantum computer [Head of Quant]
- World Monitor intelligence pipelines and active data sources
- Event Log, Knowledge Graph, Risk Agent, broker adapters, notifications, and kill-switches
- Telegram Bot communications rail for founding-member alerts, trade lifecycle updates, insight digests, and system warnings

The dashboard should show health, uptime, heartbeat, degraded-state, and process status for every major module. It is a map of the system first, and a trading dashboard second. The detailed dashboard build path lives in `docs/qadam-dashboard-implementation-plan.md`.

The dashboard must eventually answer, from real status data:

- What Qadam is watching.
- Which modules are alive, pending, blocked, degraded, or local-only.
- What Qadam is thinking about and how it is analyzing sources and news.
- Which trades are candidates, blocked, staged, submitted, open, closed, or ready for postmortem.
- What Qadam is forbidden from doing.
- How the £1000 paper account is performing over time.
- What Telegram communications were sent, queued, failed, suppressed, or pending delivery to founding members.

Current local cockpit state:

- The live production `qadam.trade` cockpit currently uses a static Supabase-authenticated workaround in `landing-page-repo`.
- `/` renders a public cockpit entry page with a Login action.
- `/login` renders Supabase email/password login.
- `/sign-in` redirects to `/login`; `/sign-up` creates allowlisted Supabase Auth accounts.
- `/dashboard` renders the health-driven System Map and is protected by Supabase session cookies plus Qadam's founding-manager allowlist.
- `/guide` renders the protected Qadam User Guide and is linked from the dashboard.
- `/dashboard` and `/settings` enforce Qadam's founding Fund Manager email allowlist after sign-in.
- `/api/health` proxies the Python COO health payload when `QADAM_ORCHESTRATOR_URL` is set.
- If the COO is offline, the cockpit falls back to a degraded local shell instead of crashing.
- Promoted adapters, source counts, unresolved sources, local-store status, execution venues, and Fund Manager access are rendered from the health contract.

The dashboard should also include a small private comments/forum area for Ramin, Troy, Akber, Anas, and Ion. Comments are saved locally and linked to the relevant signal, module, strategy, or postmortem.

Future extension: once the founding Fund Managers understand Qadam better, they may optionally contribute local compute capacity such as RAM, processing time, storage, or model runtime. This is deferred until after the first release and must be explicit, permissioned, and measurable.

## Quantum Backend Plan

Qadam uses Google for Gemini only, not for quantum hardware in v1. Google Quantum hardware access is not public self-serve, so it is not a default backend.

- Primary quantum backend: IBM Quantum via Qiskit Runtime.
- Secondary backend: AWS Braket for hardware diversity and failover.
- Optional error-suppression layer: Q-CTRL Fire Opal.
- Local validation: Qiskit Aer before any hardware submission.
- Required fallback: classical scipy/cvxpy/scikit-learn output marked `classical-fallback`.

Quantum remains a weekly oracle. It can upgrade, downgrade, or hold a signal, but it cannot originate a trade, bypass the 6-Step Filter, or bypass the Risk Agent.

## Current Foundation

- Python orchestrator shell.
- World Monitor 35-source registry.
- API Specs appendix covering the 35 canonical data sources, model providers, quantum providers, broker rails, notification services, TradingView alert boundary, and optional providers discovered in the pasted `world-monitor/` reference codebase.
- Qadam resource registry from `specs/qadam-general-context.md`.
- How The World Works integration note for the private esoteric edge corpus.
- Structured world-model claim cards, all marked as private foundational priors.
- Local founding Fund Manager governance comment store.
- Phase 1 test-data ingestion spine for typed source observations without live API calls.
- Phase 1 data-spine acceptance gate for all 35 sources, all 5 pipelines, promoted adapter coverage, heartbeat consistency, and full deterministic ingestion.
- Phase 1 read-only live adapter promotion layer for ACLED, UnusualWhales, Polymarket, Kalshi, Alpaca, AIS, Wingbits, BLS, ECB, UN Comtrade, SEC EDGAR, Reddit, X, and Telegram.
- Alpaca paper-account mirror with GET-only balance, positions, orders, and P&L refresh through `scripts/check_alpaca_paper_mirror.py --live`.
- Historical backfill planning and local sample-run contract for 12 priority sources, with credential-aware blocked/ready states.
- Trust Score seed contract across all 35 sources: 22 sources currently score above 0.5 from priors/promoted adapters; real-data scoring remains pending.
- Postgres/Timescale durable ingestion contract and status check; it passes as `ready_waiting_for_local_service` until local Postgres is running.
- FastMCP-style tool scaffold.
- Postgres/Timescale and Chroma service definitions.
- Local store health checks for Postgres/Timescale and Chroma, with degraded status until the services are running.
- Next.js cockpit shell wired to the local health contract.
- API source inventory.
- API key setup guide for the credential-gated adapters.
- API specs and placeholder ledger in `docs/api-specs.md`; real keys still belong only in `data/runtime/qadam-secrets.env`.
- Agent/skill manifest plan shaped by Anthropic's financial-services reference: named workflow agents, reusable skill bundles, explicit tool grants, validation, and secret scanning.
- Phase 1E Agent OS manifests for 8 named Qadam agents and 7 reusable skill bundles.
- Phase 1E/1F Agent OS acceptance gate for manifests, skills, runtime grants, broker-write blocks, undeclared-tool blocks, and explicit non-execution output flags.
- Frozen D0 cockpit shell and D1 public-safe cockpit status contract.
- D6 read-only paper account mirror for the £1000 trial allocation, Alpaca paper balance/P&L/positions/orders, closed trades, postmortem counts, and 100-closed-trade maturity benchmark. The mirror cannot create, modify, cancel, close, or approve orders.
- D7 local TradingView alert intake contract for observed chart signals, duplicate protection, Event Log writes, and cockpit visibility with no trade-candidate or order authority.
- Read-only broker reconciliation contract after the disabled staged paper-order layer: broker echo, idempotency, Event Log prewrite, duplicate-order guard, post-submit reconciliation, and postmortem requirements are visible without creating any submit route.
- Startup and foundation checks.

## Source Pipelines

These are live or live-adjacent data feeds, not the full set of Qadam research/build resources.

- Conflict: ACLED, UCDP, GDELT, Oref, Conflict Tracker.
- Physical: NASA FIRMS, Wingbits, AIS, ArcGIS/USACE, Space-Track/CelesTrak, GPS Jamming, Internet Outage.
- Macro: FRED, BLS, BIS, ECB, UN Comtrade, USGS.
- Market: UnusualWhales, Polymarket, Kalshi, Hyperliquid, Alpaca, RapidAPI, Coinglass, Chainlink, Bookmap.
- Social: RSS, Telegram, X, Reddit, SEC EDGAR, STOCK Act, Patents, GitHub.

The detailed source credential list lives in `docs/api-specs.md`. Qadam should onboard providers in batches: first NASA FIRMS, ACLED, UnusualWhales, Kalshi, Alpaca paper, Gemini, Supabase, and Telegram bot; then FRED, BLS, UN Comtrade, X, Reddit, Telegram MTProto, AIS, and Wingbits; then the lower-frequency physical, crypto, patent, GitHub, and quantum providers.

TradingView boundary:

- A paid TradingView account does not provide a standard retail data API key for Qadam to pull market data directly.
- TradingView MCP is useful as read-only market and technical-analysis tooling through Codex/MCP, and does not require a TradingView login.
- TradingView paid-account alerts now have a local D7 intake contract: Qadam can represent an alert as an observed signal, deduplicate it, write a safe Event Log entry, and show it in the cockpit.
- The public TradingView webhook URL remains later work. It requires a secure authenticated receiver and still cannot trigger execution.

## Resource Registry

`specs/qadam-general-context.md` also defines Qadam's broader resource base: strategy guardrails, signal benchmarks, AI architecture references, prediction-market open-source tools, OSINT references, technical infrastructure candidates, institutional analyst frameworks, product references, and prediction-market papers. These live in `docs/qadam-resource-registry.md`.

PriveX Starter is now treated as an execution-adapter reference: useful for read-only venue health, delegated subaccounts, network/chain scoping, auth error handling, and the rule that order-creating POST calls are never automatically retried. It is not a first-release dependency.

## World-Model Corpus

`how-the-world-works/` is Qadam's private esoteric edge and world-model foundation. It currently contains 4 markdown files. It quietly shapes how Qadam thinks about power, incentives, narrative, and hidden coordination. In the actual trading system, it becomes a hypothesis generator, power-map source, narrative lens, and red-team scenario engine. It is not public-facing positioning and it cannot replace live evidence. The integration rules live in `docs/how-the-world-works-integration.md`.

## Demo Proof

Qadam proves itself on a £1000 Alpaca paper account before live capital.

- 90 consecutive calendar days of autonomous operation.
- Two proof trades per week where qualified setups exist.
- No forced trades.
- 100 closed trades is the mature statistical benchmark.
- Max drawdown must stay at or below 20%.
- No manual trade-level overrides during the clean proof sample.

Current founding access list:

- Ramin: `raminhoodeh@gmail.com`
- Troy: `troycookecareer@gmail.com`
- Akber: `akber.ali@hotmail.co.uk`
- Ion: `isioras@yahoo.co.uk`
- Anas: email pending

## Local Start

1. Copy `.env.example` to `.env` and fill only the keys you have.
2. Start storage with Docker Compose when Docker is available.
3. Run `./start_qadam.sh` to verify the foundation.
4. Set `QADAM_START_ORCHESTRATOR=1` when you want the local health endpoint to run.
5. For cockpit login, set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in the cockpit environment, then open `/login`.

Supabase cockpit auth:

- Project ref: `eipijgublkypksygsyet`.
- Public URL: `https://eipijgublkypksygsyet.supabase.co`.
- Use the Supabase public anon/publishable key for `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- Keep the Supabase secret key server-only as `SUPABASE_SECRET_KEY`.
- Never put a Supabase secret or service-role key in a `NEXT_PUBLIC_` variable.

Optional Codex Supabase MCP access:

```bash
codex mcp add supabase --url https://mcp.supabase.com/mcp?project_ref=eipijgublkypksygsyet
```

Then enable remote MCP client support in `~/.codex/config.toml`:

```toml
[mcp]
remote_mcp_client_enabled = true
```

Finally run:

```bash
codex mcp login supabase
```

Current Event Log state:

- `migrations/0001_event_log.sql` defines the durable Timescale/Postgres table.
- `scripts/apply_migrations.py` applies SQL migrations once Postgres is running.
- `orchestrator/event_log.py` writes append-only local JSONL during Phase 0.
- `scripts/check_event_log.py` verifies write and replay without requiring Docker.

Current local store state:

- `docker-compose.yml` defines local Postgres/Timescale and Chroma services.
- `orchestrator/local_store.py` reports whether those services are reachable.
- `scripts/check_local_stores.py` treats missing directories as failure and offline services as a degraded but acceptable foundation state.
- Until Docker is running, Postgres falls back to local JSONL Event Log and Chroma remains an empty Knowledge Graph shell.
- `scripts/bootstrap_runtime.sh` creates a local `.venv` using Python 3.12 and installs Qadam dependencies.
- `scripts/start_local_stores.sh` starts local container services, applies migrations, and seeds durable registry tables when Docker/OrbStack/Podman/Colima is available.
- `scripts/start_postgres_timescale_ingestion.sh` is the Postgres-only durable-ingestion bootstrap: it starts the Timescale service, waits for readiness, applies migrations, seeds reference/world-model data, writes all 35 deterministic source observations, and verifies replay coverage.
- `orchestrator/chroma_store.py` initializes an embedded local Chroma Knowledge Graph even before the Chroma server container is running.
- `scripts/check_chroma_store.py` verifies the embedded Knowledge Graph.
- Postgres/Timescale is the only remaining durable-store service that requires a Docker-compatible runtime on this Mac.

Current registry and governance state:

- `orchestrator/resource_registry.py` tracks Qadam's non-live strategy, product, AI, OSINT, infrastructure, and paper references separately from live data feeds.
- `orchestrator/world_model.py` converts the 4-file `how-the-world-works/` corpus into private claim cards with observable signatures and live sources to check.
- All world-model claims begin as `foundational_prior` and cannot affect signal confidence without corroboration.
- `orchestrator/governance.py` saves local founding Fund Manager comments linked to modules, sources, resources, strategies, signals, postmortems, or the overall system.
- `scripts/check_registries.py` verifies the resource boundary, world-model corpus count, claim status, and governance store.

Current ingestion state:

- `orchestrator/ingestion.py` creates deterministic test observations from the 35-source registry.
- `orchestrator/adapters.py` defines the reusable source-adapter envelope, raw archive, normalized event schema, and the first read-only public adapters.
- `orchestrator/source_health.py` builds the source heartbeat run and `data/runtime/data_environment_map.json`.
- `scripts/check_test_ingestion.py` verifies the adapter contract without calling live APIs.
- `scripts/check_source_heartbeat.py` verifies all 35 source readiness states, promoted adapter count, missing credential map, and local heartbeat store.
- `scripts/check_phase1_data_spine.py` verifies the whole Phase 1 source contract: 35 sources, 5 pipelines, promoted adapters, heartbeat-map consistency, safe credential-status shape, and full deterministic ingestion.
- `scripts/check_supplied_credentials.py` validates the currently supplied credentials and local model settings in one read-only pass: NASA FIRMS, FRED, ACLED, Alpaca paper, Telegram, Gemini, LM Studio, plus Kalshi deferred and UnusualWhales missing.
- `scripts/check_alpaca_paper_mirror.py --live` refreshes the Alpaca paper-account mirror in read-only mode: account, positions, orders, and portfolio history only; no broker-write route exists.
- `scripts/refresh_acled_token.py --write --validate-read` refreshes ACLED OAuth tokens into the ignored local secret file and writes a redacted local report; it cannot create signals or orders.
- `scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm` feeds read-only observations into the Research Analyst queue, runs the local Gemma Research Analyst, and queues a Strategy Lead shadow handoff with no execution authority.
- `scripts/check_phase2_paper_context.py` validates that Phase 2 receives the paper-account mirror as read-only context and that neither the Research Analyst nor Strategy Lead can approve execution or paper orders.
- `scripts/check_gdelt_adapter.py` verifies the GDELT sample path and can run a live read-only check with `--live`.
- `scripts/check_oref_adapter.py` verifies the Oref sample path and can run a live read-only check with `--live`.
- `scripts/check_nasa_firms_adapter.py` verifies the NASA FIRMS sample path and can run a live read-only area CSV check with `--live` when `NASA_FIRMS_API_KEY` is configured.
- `scripts/check_fred_adapter.py` verifies the FRED macro sample path and can run a live read-only check with `--live`.
- `scripts/check_rss_adapter.py` verifies the RSS sample path and can run a live read-only check with `--live`.
- Test observations write to local JSONL and emit Event Log entries.
- `migrations/0003_source_observation.sql` defines the future durable Timescale table.
- `orchestrator/postgres_store.py` can seed durable reference/world-model tables and write test observations into Postgres once the database is running.
- `scripts/run_test_ingestion_durable.py --all` writes all 35 deterministic observations into Timescale once migrations are applied.
- `scripts/check_postgres_timescale_replay.py --require-full-source-coverage` verifies replay coverage from durable observations without writing new rows.
- Individual live adapters should replace test observations one at a time after their credentials, rate limits, and failure modes are clear.
- The data environment map currently distinguishes promoted adapters, derived sources, deferred sources, missing-credential sources, local bridges, fallback-only sources, and ready-to-build/ready-to-port sources.
- The GDELT live path is read-only and degrades cleanly on network/API failure while preserving the raw attempt locally.
- The Oref live path is read-only, treats empty active alerts as valid, and degrades cleanly on timeout, HTML, or parse failure.
- The NASA FIRMS live path is read-only, credential-gated, bbox-first, and turns high-confidence thermal anomalies into physical observations.
- The FRED live path is read-only, uses `FRED_API_KEY` when configured, and falls back to official public FRED CSV when no key is present.
- The RSS live path is read-only, rejects HTML/non-feed responses, archives raw feed attempts, and turns headlines into narrative observations.

Current Agent OS state:

- `agents/` contains manifests for COO, Research Analyst, Strategy Lead, Head of Quant, Risk Agent, Signal Auditor, Execution Auditor, and Fund Manager Interface.
- `skills/` contains reusable Qadam bundles for macro intelligence, prediction markets, physical anomaly monitoring, options/volatility flow, Akber's 6-stage filter, private world-model priors, and risk/postmortems.
- `scripts/check_agent_manifests.py` verifies role files, tool grants, skill references, output schemas, forbidden actions, and secret-pattern hygiene.
- `scripts/check_agent_runtime.py` verifies runtime tool authorization, blocked broker-write tools, sample outputs, and the Research Analyst shadow triage queue.
- `scripts/check_phase1_agent_os.py` verifies the combined Agent OS gate: 8 agents, 7 skills, 130 tool grants, broker-write blocking, undeclared-tool blocking, required per-agent tools, and explicit `execution_allowed=false` / `paper_order_allowed=false` / `broker_write_allowed=false` sample outputs.
- System health and the cockpit expose `agent_os` and `agent_runtime` status with agent count, skill count, tool-grant count, enforced block count, and shadow queue state.

Current shadow intelligence state:

- `orchestrator/intelligence.py` defines Evidence Trail and Proposed Signal contracts.
- `scripts/check_shadow_intelligence.py` runs deterministic keyword/anomaly triage without calling Gemini or LM Studio.
- Gemini and LM Studio provider readiness are reported as configured/missing, with optional safe probes that list models only and do not generate content.
- `scripts/check_llm_provider_probes.py` can run dry status checks by default, `--local-live` after LM Studio is running, and `--gemini-live` for the Gemini model-list credential probe. The live probe timeouts are explicit so slow local model servers degrade cleanly instead of creating false authority.
- The Research Analyst shadow triage runner consumes queued packets and converts them into non-executable shadow signals.
- `scripts/check_local_research_analyst.py` validates the local Research Analyst assessment contract in dry mode by default, and `--live` calls LM Studio only after the local server is running.
- Local Research Analyst assessments are stored in `data/runtime/local_research_assessments.jsonl` as shadow-only compression records with no execution authority.
- Phase 2 now feeds a sanitized paper-account context into the Local Research Analyst and Strategy Lead shadow workflow: Alpaca paper balance, P&L, positions, order counts, drawdown, maturity progress, and the £1000 policy allocation are visible as context only, with `execution_allowed=false`, `paper_order_allowed=false`, `write_authority=false`, and `live_capital_enabled=false`.
- `orchestrator/signal_integrity.py` implements the first Signal Integrity Gate. It reviews shadow signals through evidence count, source count, trust scores, missing corroboration, signal confidence, and Akber's 6-stage filter, then marks each signal as `blocked`, `hold_for_corroboration`, or `passed_to_risk_shadow`.
- `scripts/check_signal_integrity_gate.py` validates that Signal Integrity reviews are durable, public-safe, and non-executable. The gate cannot approve risk, create trade candidates, create paper orders, or access broker-write routes.
- `orchestrator/risk_agent.py` now implements the first read-only Risk Agent policy router. It reviews Signal Integrity outputs and Trade Intent records against account mode, live-capital flags, broker-write flags, paper-order authority, kill-switch state, execution policy, source quality, Trust Score, invalidation, entry, and max-risk constraints.
- `scripts/check_risk_agent_policy_router.py` validates that Risk Agent reviews are durable, public-safe, and non-executable. The router can block or hold, but it cannot approve risk, create orders, create paper orders, or write to brokers.
- `orchestrator/execution_policy.py` now implements the first read-only Execution Policy and kill-switch layer. It reviews Risk Agent outputs against venue mode, broker-order route state, staged-paper-order contract availability, global/strategy/venue/model/data kill switches, and live-capital boundaries.
- `scripts/check_execution_policy_router.py` validates that Execution Policy reviews are durable, public-safe, and non-executable. The layer can explain policy blocks and kill-switch holds, but it cannot stage orders, create orders, enable live capital, or write to brokers.
- `orchestrator/staged_paper_order.py` now implements the disabled staged paper-order contract. It sits after Execution Policy, describes the hypothetical order and reconciliation checks that would be needed later, and keeps `execution_allowed=false`, `staged_paper_order_created=false`, `paper_order_submittable=false`, `broker_write_allowed=false`, and `live_capital_enabled=false`.
- `scripts/check_staged_paper_order_contract.py` validates that staged paper-order reviews are durable, public-safe, and unable to create staged orders, submit paper orders, enable live capital, or write to brokers.
- `orchestrator/broker_reconciliation.py` now implements the read-only broker reconciliation contract. It sits after the disabled staged paper-order contract and checks broker echo, idempotency, Event Log prewrite, duplicate-order guard, post-submit reconciliation, and postmortem requirements while keeping `paper_order_submit_allowed=false`, `broker_write_allowed=false`, and `live_capital_enabled=false`.
- `scripts/check_broker_reconciliation_contract.py` validates that broker reconciliation reviews are durable, public-safe, and unable to allocate order IDs, create broker echoes, prewrite Event Log order records, submit paper orders, enable live capital, or write to brokers.
- `orchestrator/paper_submit_receipt.py` now implements the dry-run paper-submit receipt contract. It sits after broker reconciliation and can describe a simulated receipt only after reconciliation prerequisites pass, with deterministic idempotency-preview design, Event Log prewrite schema, pre-trade snapshot schema, and duplicate-order guard schema, while keeping `paper_order_submitted=false`, `broker_post_called=false`, `broker_write_allowed=false`, and `live_capital_enabled=false`.
- `scripts/check_paper_submit_receipt_contract.py` validates that dry-run receipt reviews are durable, public-safe, and unable to call Alpaca POST routes, submit paper orders, enable live capital, write to brokers, allocate broker-usable client IDs, write pre-order events, capture order snapshots, or execute duplicate-order guard writes.
- `orchestrator/quantum.py` now starts Phase 3 with a Head of Quant quantum/classical oracle scaffold. It defines provider readiness, `QuantumOracleJob`, `QuantumOracleResult`, deterministic classical fallback, local validation, and a JSONL result store.
- `scripts/check_quantum_oracle.py` validates Pattern Recognition and Strategy Collapse / Ambiguity Score jobs. The current scaffold uses `classical_fallback` when optional `qiskit-aer` is not installed, and keeps hardware submissions, execution approvals, paper-order approvals, broker writes, and trade-candidate creation at zero.
- All shadow signals are marked non-executable with `execution_allowed=false`.

Current dashboard status-contract state:

- `orchestrator/cockpit_status.py` builds the public-safe cockpit status contract and includes the D9 Secure Live Bridge status.
- `scripts/export_cockpit_status.py` writes `data/runtime/cockpit-status.json`, `cockpit-status.signature.json`, and, when the static site repo exists, matching files in `landing-page-repo/status/`.
- `scripts/check_cockpit_status.py` validates that D0 is frozen, Qadam is in paper mode, live capital is disabled, module/source status exists, and the public snapshot contains no raw token-like values, allowlist emails, local absolute paths, secret lists, or broker authority.
- `landing-page-repo/dashboard.js` now tries the authenticated `/api/cockpit-status` live bridge first, then falls back to `/status/cockpit-status.json`, and renders a top Mission Control surface before the detailed panels: connected/configured sources, durable replay readiness, Qadam's current trading philosophy, API/model/quant stack, current thinking, trade intent, paper holdings, P&L, safety boundaries, modules, source groups, cognition, forbidden actions, trade state, communications, comments, and process console from the contract.
- Mission Control now includes a public-safe durable spine readout from `durable_ingestion`: Postgres/Timescale service state, replay status, replayed source count versus the 35-source target, next step, and explicit zero authority for source observations to create signals, candidates, orders, broker writes, or live-capital access.
- Dashboard Plan D3 is implemented locally: the Watching panel renders all 35 registered sources under 5 pipeline groups with readiness, credential state, adapter state, degraded reason, trust placeholder, and heartbeat time; D7 appends TradingView paid alerts as an observed market alert source.
- Dashboard Plan D4 is implemented locally: the Cognition panel renders current focus, read-only paper-account context, Signal Integrity Gate state, recent Signal Integrity reviews, Head of Quant oracle state, model activity, shadow packets, hypotheses, evidence packets, missing corroboration, analysis timeline, and blocked-by-reason state from the public-safe snapshot.
- Dashboard Plan D5 is implemented locally: `orchestrator/trade_intent.py`, `orchestrator/risk_agent.py`, `orchestrator/execution_policy.py`, `orchestrator/staged_paper_order.py`, `orchestrator/broker_reconciliation.py`, `orchestrator/paper_submit_receipt.py`, `scripts/check_trade_intent.py`, `scripts/check_risk_agent_policy_router.py`, `scripts/check_execution_policy_router.py`, `scripts/check_staged_paper_order_contract.py`, `scripts/check_broker_reconciliation_contract.py`, and `scripts/check_paper_submit_receipt_contract.py` create a local Trade Intent Store plus read-only Risk Agent, Execution Policy, disabled staged paper-order, read-only broker reconciliation, and dry-run paper-submit receipt review layers. The cockpit renders one candidate, one blocked D5 test intent, current Risk Agent policy reviews, current Execution Policy / kill-switch reviews, disabled staged paper-order reviews, broker reconciliation reviews, and dry-run paper-submit receipt reviews from those stores.
- Trade intent remains non-executing: `execution_allowed=false`, `paper_order_allowed=false`, no broker order path, no live capital, and no staged paper orders.
- Dashboard Plan D6 is implemented locally: `orchestrator/paper_account.py`, `scripts/check_paper_account.py`, and `scripts/check_alpaca_paper_mirror.py --live` maintain a read-only paper account mirror. It shows the £1000 trial allocation alongside Alpaca paper balance/P&L/positions/orders, while keeping `write_authority=false`, `live_capital_enabled=false`, and `paper_order_allowed=false`.
- The cockpit money panel now renders those D6 mirror fields from the public-safe snapshot; it still has no broker write path, no live capital, and no ability to place orders.
- Dashboard Plan D7 is implemented locally: `orchestrator/tradingview_alerts.py` and `scripts/check_tradingview_alerts.py` validate a TradingView paid-alert intake contract, block duplicate alerts, fail closed on receiver-key mismatch, and export observed signals to the cockpit with `execution_allowed=false`, `paper_order_allowed=false`, and `trade_candidate_created=false`.
- The cockpit now shows TradingView alerts under Watching and as observed signals in the Trade Layer; they are not candidates, staged orders, submitted orders, or positions.
- The cockpit now exports `decision_philosophy` from the private `how-the-world-works/` corpus and renders Qadam's worldview lens in the system map, Private Edge panel, hypothesis cards, and each observed-signal/trade decision card while labelling it as a private prior, not evidence.
- Dashboard Plan D8/D8A/D8B is implemented locally: the cockpit shows Fund Manager comments, Telegram dry-run Communications, and the protected User Guide.
- Dashboard Plan D9 is implemented locally: the Secure Live Bridge contract, signed snapshot manifest, read-only authenticated API route, rate-limit boundary, write-method blocks, and static fallback are in place.
- The cockpit cognition contract can now include sanitized local Research Analyst assessments, read-only paper-account context, and Signal Integrity review state: summary, watch focus, missing correlations, next questions, confidence, paper mirror state, integrity score, Akber filter output, failure reasons, required next steps, and shadow-only authority flags.
- The cockpit trade contract now includes sanitized Risk Agent policy-review state: review status, policy score, blocked reasons, required next steps, account context, risk cap, Signal Integrity reference, and explicit zero-authority flags for execution, paper orders, order creation, and broker writes.
- The cockpit trade contract now also includes sanitized Execution Policy state: selected venue, venue mode, kill-switch status, execution checks, blocked reasons, required next steps, and explicit zero-authority flags for staged paper orders, paper-order creation, broker writes, and live capital.
- The cockpit trade contract now includes sanitized disabled staged paper-order state: hypothetical order, reconciliation checks, blocked reasons, required next steps, and explicit zero-authority flags for staged order creation, paper-order submission, broker writes, and live capital.
- The cockpit trade contract now includes sanitized broker reconciliation state: broker echo status, reconciliation checks, blocked reasons, required next steps, and explicit zero-authority flags for idempotency allocation, Event Log prewrite, duplicate-order readiness, paper-order submission, broker writes, and live capital.
- The cockpit trade contract now includes sanitized dry-run paper-submit receipt state: simulated receipt status, idempotency preview, prewrite schema, pre-trade snapshot schema, duplicate-order guard schema, receipt checks, blocked reasons, required next steps, and explicit zero-authority flags for broker POST calls, paper-order submission, broker writes, and live capital.
- The cockpit status contract now includes sanitized Head of Quant oracle state: backend, latest recommendation, result count, optional `qiskit-aer` availability, hardware-submission counts, and zero-authority flags for execution, paper orders, trade-candidate creation, and hardware jobs.
- Telegram Bot planning now treats Telegram as an outbound-only member communications rail: trade lifecycle updates, insight digests, health warnings, delivery status, and dashboard visibility, with no execution authority.
- The protected static cockpit now links to `/guide/`, a user guide explaining the dashboard panels, status labels, trade states, member permissions, daily operating routine, and red flags.

Durable-mode commands:

1. Run `scripts/bootstrap_runtime.sh`.
2. Install or open a Docker-compatible runtime: Docker Desktop, OrbStack, Podman, or Colima.
3. Run `scripts/start_postgres_timescale_ingestion.sh`.
4. Run `scripts/check_postgres_timescale_replay.py --require-full-source-coverage`.
5. Use `scripts/start_local_stores.sh` later when Chroma server mode is needed as well.

Current quantum credential state:

- Real quantum keys belong in `data/runtime/qadam-secrets.env` or a future macOS Keychain provider.
- Q-CTRL is configured locally as a future provider.
- IBM Quantum and AWS Braket remain optional future credentials.
- Phase 3 has started with local validation and classical fallback only. No quantum hardware jobs are submitted.

## Vercel Project

The local cockpit is linked to the existing Vercel project for `qadam.trade` through `cockpit/.vercel/project.json`.

- Project ID: `prj_apm3Zfd9fpWq4wsJiSunkVmxdCVQ`
- Team ID: `team_Qv7iJDGRobHFyiyUsMUbVxyy`
- Verified status: the Vercel CLI can retrieve the `qadam` project.
- Current remote setup: generic framework preset with root directory `.`. Keep production deploys intentional while the existing landing page is live.

The Vercel token must stay local. Export `VERCEL_TOKEN` in your shell or load it from your local secret store, then use:

```bash
./scripts/inspect_vercel_project.sh
./scripts/deploy_cockpit_vercel.sh
```

This workspace supports a local, gitignored secret file at `data/runtime/vercel.env` with strict `600` permissions.
