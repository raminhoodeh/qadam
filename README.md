# Qadam

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence, silver, and semiconductors. Join the waitlist and be the first to install the system on your machine, tailoring it to your needs over time.

Primary spec: `specs/qadam-specs.md`.

Planning docs:

- `docs/qadam-master-implementation-plan.md` - start here; this is the day-to-day control document.
- `docs/api-key-setup.md`
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

`qadam.trade` is the login surface and command cockpit. After Clerk login, the first view is a system map showing how the fund is wired together:

- Python script [COO]
- Local LLM [Research Analyst]
- Frontier LLM [Strategy Lead]
- Quantum computer [Head of Quant]
- World Monitor intelligence pipelines and active data sources
- Event Log, Knowledge Graph, Risk Agent, broker adapters, notifications, and kill-switches

The dashboard should show health, uptime, heartbeat, degraded-state, and process status for every major module. It is a map of the system first, and a trading dashboard second.

Current local cockpit state:

- `/` renders a health-driven System Map.
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
- Qadam resource registry from `specs/qadam-general-context.md`.
- How The World Works integration note for the private esoteric edge corpus.
- Structured world-model claim cards, all marked as private foundational priors.
- Local founding Fund Manager governance comment store.
- Phase 1 test-data ingestion spine for typed source observations without live API calls.
- FastMCP-style tool scaffold.
- Postgres/Timescale and Chroma service definitions.
- Local store health checks for Postgres/Timescale and Chroma, with degraded status until the services are running.
- Next.js cockpit shell wired to the local health contract.
- API source inventory.
- API key setup guide for the credential-gated adapters.
- Agent/skill manifest plan shaped by Anthropic's financial-services reference: named workflow agents, reusable skill bundles, explicit tool grants, validation, and secret scanning.
- Phase 1E Agent OS manifests for 8 named Qadam agents and 7 reusable skill bundles.
- Startup and foundation checks.

## Source Pipelines

These are live or live-adjacent data feeds, not the full set of Qadam research/build resources.

- Conflict: ACLED, UCDP, GDELT, Oref, Conflict Tracker.
- Physical: NASA FIRMS, Wingbits, AIS, ArcGIS/USACE, Space-Track/CelesTrak, GPS Jamming, Internet Outage.
- Macro: FRED, BLS, BIS, ECB, UN Comtrade, USGS.
- Market: UnusualWhales, Polymarket, Kalshi, Hyperliquid, Alpaca, RapidAPI, Coinglass, Chainlink, Bookmap.
- Social: RSS, Telegram, X, Reddit, SEC EDGAR, STOCK Act, Patents, GitHub.

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
- Ion: `isioras@yahoo.co.uk`
- Akber: email pending
- Anas: email pending

## Local Start

1. Copy `.env.example` to `.env` and fill only the keys you have.
2. Start storage with Docker Compose when Docker is available.
3. Run `./start_qadam.sh` to verify the foundation.
4. Set `QADAM_START_ORCHESTRATOR=1` when you want the local health endpoint to run.

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
- `scripts/check_gdelt_adapter.py` verifies the GDELT sample path and can run a live read-only check with `--live`.
- `scripts/check_oref_adapter.py` verifies the Oref sample path and can run a live read-only check with `--live`.
- `scripts/check_nasa_firms_adapter.py` verifies the NASA FIRMS sample path and can run a live read-only area CSV check with `--live` when `NASA_FIRMS_API_KEY` is configured.
- `scripts/check_fred_adapter.py` verifies the FRED macro sample path and can run a live read-only check with `--live`.
- `scripts/check_rss_adapter.py` verifies the RSS sample path and can run a live read-only check with `--live`.
- Test observations write to local JSONL and emit Event Log entries.
- `migrations/0003_source_observation.sql` defines the future durable Timescale table.
- `orchestrator/postgres_store.py` can seed durable reference/world-model tables and write test observations into Postgres once the database is running.
- `scripts/run_test_ingestion_durable.py --all` writes all 35 deterministic observations into Timescale once migrations are applied.
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
- System health and the cockpit expose `agent_os` and `agent_runtime` status with agent count, skill count, tool-grant count, enforced block count, and shadow queue state.

Durable-mode commands:

1. Run `scripts/bootstrap_runtime.sh`.
2. Install or open a Docker-compatible runtime: Docker Desktop, OrbStack, Podman, or Colima.
3. Run `scripts/start_local_stores.sh`.
4. Run `scripts/check_durable_stores.py`.
5. Run `scripts/run_test_ingestion_durable.py --all`.

Current quantum credential state:

- Real quantum keys belong in `data/runtime/qadam-secrets.env` or a future macOS Keychain provider.
- Q-CTRL is configured locally as a future provider.
- IBM Quantum and AWS Braket remain optional future credentials.
- Phase 0 must not submit quantum jobs.

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
