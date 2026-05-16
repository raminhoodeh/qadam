# Qadam Foundational Architecture Plan

Appendix for Phase 0 technical detail. For day-to-day sequencing, use `docs/qadam-master-implementation-plan.md`.

A hedge fund team that fits inside your laptop.
Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].

This plan covers only the foundational architecture and tech stack. It deliberately excludes real data ingestion, model inference, signal generation, broker execution, and trading logic.

## Foundation Goal

By the end of this foundation pass, Qadam should boot as a coherent system:

- `qadam.trade` login works.
- The local cockpit is linked to the existing Vercel `qadam` project without overwriting the live landing page.
- The authenticated dashboard shows a system map of all modules.
- The authenticated dashboard includes a private comments/forum area for founding Fund Manager suggestions.
- The Python COO starts, exposes health, and reports process status.
- Postgres/Timescale stores append-only events.
- ChromaDB is initialized as the empty Knowledge Graph.
- FastMCP-style tools expose the source registry and health.
- Qadam's non-live resource registry from `qadam-general-context.md` is tracked separately from the live data-source registry.
- The `how-the-world-works/` corpus is tracked as Qadam's private foundational world-model layer, with an evidence boundary before signals or execution.
- Execution venue architecture is defined as a disabled/read-only contract before any broker or exchange can trade.
- First-release storage is local-first on Ramin's MacBook: Event Log, Knowledge Graph, raw payloads, runtime state, and proof data remain local by default.
- The system is clearly configured for a £1000 paper/test account before any autonomous test trading is possible.
- Secrets are loaded safely.
- Startup and verification are one-command.

## Non-Goals

- No source polling beyond registry/heartbeat stubs.
- No Gemma/Gemini inference.
- No quantum hardware calls.
- No broker orders.
- No PriveX live integration or crypto-perps order submission.
- No strategy logic.
- No public community surface.
- No external user accounts beyond the five founding Fund Manager logins: Ramin, Troy, Akber, Anas, and Ion.

## Architecture Slice

| Area | Foundation Choice | Purpose |
| --- | --- | --- |
| Cockpit | Next.js App Router + Clerk | Allowlisted login and system-map dashboard at `qadam.trade`. |
| Deployment | Existing Vercel project `qadam` | Host the landing page and future authenticated cockpit deliberately. |
| Orchestrator | Python 3.12, asyncio, uvloop | The COO process coordinating health, logs, tools, and later adapters. |
| Tool layer | FastMCP-style tools | Uniform interface for source registry and future modules. |
| Event Log | PostgreSQL + TimescaleDB | Append-only audit trail and deterministic replay. |
| Knowledge Graph | ChromaDB | Empty local vector store, ready for resolved catalyst memory. |
| Local storage | MacBook 1TB SSD | Canonical saved state: raw payloads, Event Log data, Chroma persistence, runtime files, proof records. |
| Resource registry | Markdown now, database table later | Strategy references, papers, product benchmarks, OSS stacks, and analytical frameworks. |
| World-model corpus | Markdown now, claim cards later | Private foundational worldview, esoteric edge hypotheses, power maps, narrative lenses, and falsification tests. |
| Execution rail contracts | Disabled `ExecutionVenue` + `BrokerAdapter` registry | Define safe venue boundaries before any venue can place orders. PriveX Starter informs this contract as an optional later execution rail, not a first-release dependency. |
| Secrets | macOS Keychain or strict local secret file | Runtime-only credentials, split research, quantum, and execution keys. |
| Quantum provider registry | Local simulator now, Q-CTRL/IBM/Braket later | Show credential readiness without submitting Phase 0 quantum jobs. |
| Supervision | launchd | Keep orchestrator, cockpit, storage, and future local LLM alive. |
| Observability | JSON logs, health endpoint, Sentry hook, uptime monitor | Make status visible before the system trades. |

## Build Slice 1 - Runtime And Repository Contract

Deliverables:

- Confirm Python 3.12 runtime path. The current macOS default Python can run checks, but production runtime should be 3.12.
- Confirm Node runtime for the cockpit.
- Keep `pyproject.toml` as the Python dependency contract.
- Keep `cockpit/package.json` as the web dependency contract.
- Maintain `.env.example` with all planned secrets but no real values.
- Define local data directories for raw payloads, Event Log persistence, Chroma persistence, model/cache data, runtime files, and backups.
- Add first-release mode config for `paper` / `test` trading with £1000 starting balance.
- Add local verification commands to `start_qadam.sh`.

Exit checks:

- `./start_qadam.sh` passes from a fresh terminal.
- `python3 scripts/check_foundation.py` reports 35 sources.
- Local storage paths exist and are permission-checked.
- Test/live mode config is explicit.
- No committed file contains a secret-looking value.

## Build Slice 2 - Event Log Foundation

Deliverables:

- Add SQL migrations.
- Add migration runner.
- Create append-only `event_log` table.
- Create Timescale hypertable on event timestamp.
- Add schema version field.
- Add `event_type`, `component`, `severity`, `payload`, `created_at`, `correlation_id`.
- Add replay function that reconstructs current system state from events.
- Replace in-memory `orchestrator/event_log.py` with a local JSONL fallback now and a Postgres-backed writer later.

Exit checks:

- Test event writes to local JSONL before Docker is running.
- Timescale migration exists for Postgres replay storage.
- Replay returns the same derived state on repeated runs.
- Event Log write failure causes health status `degraded`.
- Event Log silence > 60 seconds is representable as an alert condition.

## Build Slice 2A - Local Store Health

Deliverables:

- Add a local-store health layer for Postgres/Timescale and Chroma.
- Report missing storage directories as failure.
- Report offline Postgres/Chroma services as degraded while Phase 0 fallbacks are active.
- Surface the Postgres fallback as `local_jsonl_event_log`.
- Surface the Chroma fallback as `empty_knowledge_graph_shell`.

Exit checks:

- `scripts/check_local_stores.py` passes when directories exist.
- `scripts/check_local_stores.py --require-running` can be used later to force Postgres/Chroma to be live.
- Orchestrator health includes `local_stores.status`.
- System Map can distinguish `registered`, `jsonl_fallback`, and `not_running`.

Implemented state:

- Python dependencies install into `.venv` through `scripts/bootstrap_runtime.sh`.
- Embedded Chroma Knowledge Graph initializes through `scripts/check_chroma_store.py`.
- Postgres/Timescale migration and seed scripts are ready, but require Docker Desktop, OrbStack, Podman, or Colima.

## Build Slice 3C - First Read-Only Source Adapter Paths

Deliverables:

- Add a reusable adapter response envelope matching the World Monitor Integration Reference.
- Add local raw payload archive writes before normalization.
- Add normalized event schema.
- Add first public read-only source adapter.
- Ensure live network/API failures produce degraded state instead of crashing.

Implemented state:

- `orchestrator/adapters.py` implements the shared envelope plus GDELT, Oref, FRED, and RSS adapters.
- `scripts/check_gdelt_adapter.py` checks sample mode and optional live read-only mode.
- GDELT output writes to the raw archive and Event Log.
- Live GDELT timeout is represented as a degraded source check with archived request metadata.
- Oref is implemented as the second read-only adapter.
- `scripts/check_oref_adapter.py` checks sample mode and optional live read-only mode.
- Empty active Oref alerts are treated as a healthy zero-event result.
- Oref timeout, HTML, or parse failure is represented as degraded source state with archived request metadata.
- FRED is implemented as the first macro read-only adapter.
- `scripts/check_fred_adapter.py` checks sample mode and optional live read-only mode with sigma filtering.
- FRED uses `FRED_API_KEY` when configured and the official public FRED CSV fallback when no key is present; series failures are represented as degraded or partial source state.
- RSS is implemented as the first narrative read-only adapter.
- `scripts/check_rss_adapter.py` checks sample mode and optional live read-only mode with keyword filtering.
- RSS feed failures, HTML responses, or XML parse failures are represented as degraded or partial source state with archived request metadata.

## Build Slice 3 - Source Registry And Heartbeats

Deliverables:

- Keep `world_monitor/source_registry.py` as the static registry of 35 live ingress sources.
- Add database table for source heartbeat snapshots.
- Add source statuses: `registered`, `live`, `degraded`, `unavailable`, `deferred`.
- Add heartbeat API response grouped by pipeline.
- Add expandable source groups for the system map.

Exit checks:

- Registry count remains 35.
- Pipeline counts remain conflict 5, physical 7, macro 6, market 9, social 8.
- Cockpit can show all pipeline groups from the Orchestrator API.
- A simulated degraded source appears as degraded in health output.

## Build Slice 3A - Resource Registry

Deliverables:

- Keep `docs/qadam-resource-registry.md` as the registry for resources from `specs/qadam-general-context.md`.
- Do not mix non-live references into the live source heartbeat registry.
- Represent categories:
  - strategy wisdom and guardrails
  - signal/intelligence benchmarks
  - AI architecture references
  - prediction-market open-source stack
  - OSINT references
  - APIs and technical infrastructure candidates
  - analytical frameworks
  - product and positioning references
  - prediction-market papers
- Add a future database design for `reference_registry` with name, category, source URL/path, mapped Qadam module, validation status, and decision notes.
- Add a future cockpit area that shows which resources informed each module without treating them as live feeds.

Exit checks:

- README links to the resource registry.
- Implementation plan references both the API source inventory and the resource registry.
- Cockpit plan distinguishes live data-source health from resource/reference provenance.
- No resource is marked production-active without validation notes.

Implemented state:

- `orchestrator/resource_registry.py` stores the non-live registry as typed entries.
- `resource_registry` and `resource_detail` are exposed through the FastMCP-style scaffold.
- `scripts/check_registries.py` fails if a resource is marked production-active without validation.

## Build Slice 3B - Private World-Model Corpus

Deliverables:

- Register `how-the-world-works/` as Qadam's private foundational world-model corpus.
- Add `docs/how-the-world-works-integration.md`.
- Do not mix this corpus into live source health.
- Mark extracted claims as `foundational_prior` until corroborated.
- Define a future `world_model_claim` schema with:
  - claim
  - claim type
  - actors
  - mechanism
  - observable signatures
  - live sources to check
  - market channels
  - corroboration status
  - postmortem score
- Reserve a cockpit `world-model lens` provenance area that is visually separate from factual evidence.

Exit checks:

- Corpus is linked from the implementation plan and modular plan.
- Claims are treated as private priors and hypotheses, not factual evidence.
- Signal Integrity Gate rules explicitly prevent uncorroborated world-model claims from affecting trade decisions.

Implemented state:

- `orchestrator/world_model.py` registers 5 claim cards across the 4 corpus files.
- Every claim starts as `foundational_prior`.
- `world_model_claims` and `world_model_claim_detail` are exposed through the FastMCP-style scaffold.

## Build Slice 4 - Orchestrator Health API

Deliverables:

- Health endpoint with:
  - system status
  - uptime
  - process id
  - module status
  - source registry summary
  - heartbeat summary
  - storage status
  - degraded/fallback states
- Add process registry for foundation modules:
  - Python COO
  - cockpit
  - Postgres
  - ChromaDB
  - Event Log writer
  - FastMCP tool server
  - future local LLM placeholder
  - future quantum backend placeholder
- Add typed health response model.

Exit checks:

- Health endpoint responds locally outside sandbox restrictions.
- Health output is valid JSON.
- Cockpit can render health data server-side.
- If Postgres or Chroma is down, status becomes degraded, not falsely healthy.

## Build Slice 5 - FastMCP Tool Scaffold

Deliverables:

- Keep `ticker_echo`.
- Add `source_registry`.
- Add `source_detail`.
- Add `system_health`.
- Add `module_map`.
- Define typed input/output schemas.
- Ensure tools read from Orchestrator state, not duplicated data.

Exit checks:

- Each tool can be called locally.
- Tool responses match typed schemas.
- Tool failures log events.

## Build Slice 5A - Execution Venue Contract Stub

This slice defines the shape of future execution without enabling trading. It exists because Qadam should not discover execution safety rules for the first time while connected to a broker.

PriveX Starter learning to adopt:

- Treat every venue as an explicit adapter with `health()`, `status()`, `positions()`, `quote()`, `place_order()`, `cancel()`, and `close_position()` capabilities.
- Start every venue in read-only mode: health, permissions, portfolio, market metadata, prices, solver/venue limits, and open positions before any write endpoint exists.
- Scope credentials to account, subaccount, network, chain, and permission set where the venue supports it.
- Separate auth/permission failures from transient API failures so the Risk Agent can choose re-auth, pause, or backoff.
- Retry only idempotent read calls. Never automatically retry order-creating POST requests.
- Validate order payloads locally before a venue receives them.
- Make `live` or real-money smoke tests require an explicit risk flag and a separate command path. Qadam first release should not run those paths.

Foundation deliverables:

- Add future `ExecutionVenue` registry schema:
  - venue key
  - mode: `disabled`, `read_only`, `paper`, `live_blocked`, `live`
  - account/subaccount identifier
  - network/chain identifier if relevant
  - credential status
  - permissions status
  - read health
  - write health
  - last reconciliation timestamp
  - kill-switch status
  - first-release allowed flag
- Define `BrokerAdapter` / `ExecutionAdapter` interface but implement only disabled stubs.
- Add Alpaca paper as the first intended first-release venue.
- Add PriveX as an optional later venue reference with `Base` / `COTI` network awareness, delegated subaccount awareness, and hard `live_blocked` default.
- Add cockpit placeholders for execution status, credential status, venue mode, and kill-switch state.

Exit checks:

- No adapter can submit an order in the foundation phase.
- Missing execution credentials result in `execution_disabled`, not a startup crash.
- Venue state appears in health output and cockpit System Map.
- A fake venue can move from `disabled` to `read_only` and back through logged config changes.
- Any attempted write action in foundation mode is blocked and logged.

## Build Slice 6 - qadam.trade Cockpit Shell

Deliverables:

- Preserve the live unauthenticated landing page until the production routing plan is approved.
- Add a top-right Login entrypoint to the live landing page navigation.
- Add canonical `/login` or `/sign-in` Clerk route.
- Add protected `/dashboard` route for the authenticated System Map.
- Redirect successful Clerk sign-in to `/dashboard`.
- Redirect unauthenticated `/dashboard` visits back to login.
- Restrict cockpit access to Ramin, Troy, Akber, Anas, and Ion.
- Initial allowlisted emails are Ramin `raminhoodeh@gmail.com`, Troy `troycookecareer@gmail.com`, and Ion `isioras@yahoo.co.uk`; Akber and Anas remain pending until their emails are known.
- Keep the local cockpit linked to Vercel project `prj_apm3Zfd9fpWq4wsJiSunkVmxdCVQ` through `cockpit/.vercel/project.json`.
- Keep Vercel credentials runtime-only through `data/runtime/vercel.env` or an external secret store.
- Use `scripts/inspect_vercel_project.sh` for read-only project verification.
- Use `scripts/deploy_cockpit_vercel.sh` only when a cockpit deploy is intended.
- Wire Clerk auth with a founding Fund Manager allowlist.
- Make the first authenticated route the System Map.
- Keep unauthenticated landing page separate from authenticated cockpit.
- Add private comments/forum stub for improvement suggestions.
- Add content shell with:
  - always-visible kill-switch area
  - top system health bar
  - degraded-state banner area
  - module map
  - pipeline/source groups
- Add `COCKPIT.md` with page data contracts.
- Add web-vitals endpoint and log LCP/CLS to Event Log.

Implemented state:

- `/` renders a dynamic System Map from the cockpit health contract.
- `/api/health` fetches the Python COO health endpoint when configured.
- Cockpit fallback renders a degraded local state when the COO is offline.
- Promoted adapters, local-store degradation, unresolved sources, execution venues, and Fund Manager access are visible in the System Map.
- `COCKPIT.md` documents the cockpit data contract and current route surface.

System Map nodes:

- Python script [COO]
- Local LLM [Research Analyst]
- Frontier LLM [Strategy Lead]
- Quantum backend [Head of Quant]
- World Monitor pipelines
- Event Log
- Knowledge Graph
- Trust Score service
- Risk Agent
- Broker adapters
- Telegram notifier
- Kill-switches
- Resource registry / reference provenance
- Private world-model lens / hypothesis provenance
- Fund Manager comments/forum

Exit checks:

- Vercel project inspection succeeds without deploying.
- Production deploy path is documented before changing the live domain.
- Live landing page shows a top-right Login entrypoint.
- Login reaches Clerk sign-in.
- Successful sign-in reaches the System Map.
- Unauthenticated `/dashboard` access redirects to login.
- Non-allowlisted accounts cannot access the cockpit.
- Comment/forum entries can be saved locally as governance notes.
- System Map renders before non-critical data loads.
- Module health, uptime, heartbeat, and degraded state have visible places in the UI.
- Dashboard shell LCP target is <= 500ms locally once running outside sandbox.

## Build Slice 7 - Secrets And Configuration

Deliverables:

- Add secret provider abstraction.
- Support macOS Keychain.
- Support strict local secrets file with `600` permissions for dev.
- Split secrets into:
  - research/data keys
  - quantum keys, including Q-CTRL
  - execution/broker keys
  - notification keys
  - auth keys
- Add config validation at startup.
- Add masked secret status for configured/missing keys; never expose actual secret values.

Exit checks:

- Missing optional source keys mark sources unavailable, not failed.
- Missing required foundation keys produce clear startup errors.
- Execution keys are never loaded by research-only code paths.
- Secret files with weak permissions are rejected.

## Build Slice 8 - Process Supervision

Deliverables:

- Add `launchd` plist templates for:
  - orchestrator
  - cockpit
  - Postgres/Chroma startup wrapper if needed
  - future local LLM service
- Add `scripts/status_qadam.sh`.
- Add `scripts/stop_qadam.sh`.
- Add process heartbeat events.

Exit checks:

- Orchestrator restarts after a crash.
- Status script reports each process.
- Stop script stops local Qadam processes cleanly.
- Restart events write to Event Log.

## Build Slice 9 - Observability

Deliverables:

- Structured JSON logging everywhere.
- Sentry hook with no-op when key absent.
- UptimeRobot-compatible health URL.
- Event Log alerts for:
  - process restart
  - health degradation
  - Event Log silence
  - secret/config validation failure
  - storage unavailable
- Daily summary placeholder.

Exit checks:

- Local logs are machine-readable JSON.
- Simulated degraded module appears in health, cockpit, and Event Log.
- Sentry absence does not crash local dev.

## Build Slice 10 - Foundation Acceptance Test

The foundation is complete when:

1. Vercel project inspection succeeds for the existing `qadam.trade` project without deploying.
2. `qadam.trade` shows a top-right Login entrypoint.
3. Login reaches Clerk sign-in.
4. Successful allowlisted login redirects to the cockpit System Map.
5. Unauthenticated `/dashboard` access redirects to login.
6. Non-allowlisted accounts cannot access the cockpit.
7. System Map shows all major modules and five pipeline groups.
8. Comments/forum stub saves local governance notes.
9. Orchestrator health reports uptime, module health, and source registry status.
10. Postgres Event Log accepts and replays a test event.
11. ChromaDB initializes and reports healthy.
12. FastMCP-style tools return typed responses.
13. Startup script validates registry, storage, config, and health.
14. Secrets are runtime-only and pass permission checks.
15. Promoted source adapters appear in the cockpit and Event Log, with degraded states visible when live checks fail.
16. Resource registry is linked and distinguished from the live source registry.
17. How The World Works corpus is linked as Qadam's private world-model foundation and distinguished from factual evidence.
18. Execution venue registry exists in disabled/read-only form, with no order submission path.
19. No trading, model inference, or source ingestion is required for the foundation to pass.

## Recommended Implementation Order

1. Runtime and repository contract.
2. Postgres Event Log schema.
3. Orchestrator health API.
4. Source heartbeat model.
5. Resource registry and module-mapping schema.
6. World-model claim schema and guardrails.
7. Execution venue contract stub and disabled venue registry.
8. Cockpit System Map connected to health API.
9. Clerk auth.
10. Secrets provider.
11. FastMCP tools.
12. launchd supervision.
13. Observability and acceptance test.

This order gets the nervous system visible early, then makes it durable.
