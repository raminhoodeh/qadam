# Qadam Pre-Phase-3 Implementation Plan

This document defines the staged work that must be complete before Qadam treats Phase 3 quantum integration as an active build track.

The current repo already contains an early Phase 3 oracle scaffold. For planning discipline, this document treats that scaffold as parked behind the pre-Phase-3 gate until the foundation, data spine, shadow intelligence, safety contracts, and cockpit status surfaces are green in a repeatable local run.

This version also accounts for the local `yahoo-finance-api/` checkout. That checkout is a `yfinance` reference implementation that can shift Qadam's pre-Phase-3 work by providing read-only market price, volume, options-chain, market-status, quote-search, news, sector, and screener data. It is accepted as a supplemental capability pending live dependencies, not as an execution rail and not as an automatic expansion of the canonical 35-source registry.

## 1. Scope

Pre-Phase-3 means:

- Qadam can boot locally with observable health.
- Qadam can ingest or classify all canonical sources without leaking secrets.
- Qadam can replay durable observations from local Postgres/Timescale when the local service is running.
- Qadam can run Phase 2 shadow intelligence from live read-only sources and durable replay.
- Qadam can run Signal Integrity, Risk Agent, Execution Policy, staged-paper-order, broker reconciliation, and dry-run receipt checks without creating execution authority.
- Qadam's cockpit can show a public-safe, read-only view of all of the above.
- Qadam can prove no broker write, paper-order submission, live-capital route, or quantum hardware submission is enabled.

Pre-Phase-3 does not include:

- IBM Quantum, AWS Braket, or Q-CTRL hardware submissions.
- Quantum scheduler enablement.
- Quantum-originated signals.
- Paper-order creation.
- Broker POST calls.
- Live-capital configuration.
- Phase 4 strategy approval.

## 2. Stage Map

| Stage | Module | Purpose | Can Be Done Alone | Exit Gate |
| --- | --- | --- | --- | --- |
| P3-0 | Baseline audit | Freeze current repo/runtime state before changing behavior. | Yes | Current branch, dirty files, local service state, and known blockers are recorded. |
| P3-1 | Foundation health | Prove Phase 0 still boots as a coherent local system. | Yes | Startup, registry, storage, cockpit status, and secret hygiene checks pass. |
| P3-2 | Source and credential ledger | Make every source explicit: live, degraded, missing, deferred, or blocked. | Yes | All 35 sources have classified status and no raw credentials appear in outputs. |
| P3-2A | Yahoo Finance capability review | Decide how `yahoo-finance-api/` should be used as a read-only market-data capability. | Yes | Yahoo Finance is accepted, deferred, or rejected with clear adapter boundaries. |
| P3-3 | Durable observation spine | Keep Postgres/Timescale ingestion and replay green. | Mostly | Full 35-source durable replay works when OrbStack/Postgres is running. |
| P3-4 | Agent OS enforcement | Prove every agent remains permissioned and non-executable. | Yes | Agent manifests, tool grants, sample outputs, and broker-write blocks pass. |
| P3-5 | Phase 2 shadow cycle | Run intelligence from live and replay sources without authority. | Depends on P3-2/P3-3 | Shadow packets, signals, Strategy Lead handoff, and account context are created with zero execution authority. |
| P3-6 | Safety chain | Harden Signal Integrity through dry-run receipt as one non-executing chain. | Depends on P3-5 | Every safety layer blocks or holds correctly and authority counters stay zero. |
| P3-7 | Cockpit status and public-safe export | Show the complete state without exposing local secrets or implying execution. | Depends on P3-1/P3-6 | Static/live cockpit snapshot passes public-safe checks. |
| P3-8 | Operational runbook | Make the repeatable local routine boring. | Yes | One command sequence can refresh sources, replay, shadow intelligence, and cockpit export. |
| P3-9 | Pre-Phase-3 certification | Decide whether Phase 3 can resume beyond scaffold mode. | Depends on all prior stages | A signed-off checklist says what is green, degraded, deferred, and blocked. |

## 3. Stage P3-0 - Baseline Audit

Objective: know exactly what state the repo and local runtime are in before changing any module.

Latest audit record: `docs/qadam-pre-phase-3-baseline-audit-2026-05-22.md`.

Work:

- Check main repo status.
- Check nested `landing-page-repo` status before touching public cockpit files.
- Check whether `yahoo-finance-api/` is an intentionally retained local reference checkout, a future vendored dependency, or accidental untracked material.
- Record whether OrbStack/Postgres is running.
- Record whether LM Studio is running.
- Record current missing/deferred source count.
- Record current non-execution authority counters for broker, paper order, live capital, and quantum hardware jobs.
- Identify unrelated local checkouts such as research/reference repos that should not be committed accidentally.

Acceptance gate:

- Dirty files are understood.
- Untracked reference checkouts are ignored unless intentionally adopted.
- No secret-containing file is staged.
- Runtime blockers are written down before deeper work starts.

Verification:

```bash
git status --short
git -C landing-page-repo status --short
./scripts/check_phase1_data_spine.py
./scripts/check_phase1_agent_os.py
./scripts/check_quantum_oracle.py
```

## 4. Stage P3-1 - Foundation Health

Objective: keep Phase 0 boring, observable, and non-trading.

Latest audit record: `docs/qadam-pre-phase-3-foundation-health-audit-2026-05-22.md`.

Work:

- Verify config loading and local runtime paths.
- Verify Source Registry, Resource Registry, and World-Model Corpus are distinct.
- Verify Event Log fallback writes and replays.
- Verify disabled execution venue registry remains read-only.
- Verify cockpit status contract strips secrets, emails, absolute local paths, broker IDs, raw payloads, and write authority.
- Verify startup checks still run the expected contract suite.

Acceptance gate:

- Qadam starts locally without implying a trade route.
- Foundation status can be exported to the cockpit.
- Every execution venue remains disabled/read-only.
- No market action is possible.

Verification:

```bash
./start_qadam.sh
./scripts/check_cockpit_status.py
```

## 5. Stage P3-2 - Source And Credential Ledger

Objective: make the data universe explicit before quantum or higher-level reasoning can depend on it.

Latest audit record: `docs/qadam-pre-phase-3-source-credential-ledger-audit-2026-05-22.md`.

Work:

- Keep the 35-source registry stable unless the master plan changes.
- Keep all 5 source pipelines represented.
- Keep all 19 promoted adapter contracts passing sample/read-only checks.
- Classify every source as `live`, `degraded`, `missing_credentials`, `deferred`, `unavailable`, or `blocked_by_license`.
- Refresh ACLED tokens without committing token material.
- Keep Kalshi deferred until eligibility/account access changes.
- Keep UnusualWhales marked as the useful missing Batch A key until obtained.
- Keep live-source checks read-only and fail-closed.
- Update `docs/api-specs.md` and `docs/qadam-api-key-acquisition-plan.md` when provider requirements change.

Acceptance gate:

- Every source has a visible status and blocked reason.
- Credential state is masked.
- No source can raise signal confidence by itself.
- No raw provider key appears in docs, logs intended for Git, or cockpit output.

Verification:

```bash
./scripts/check_phase1_data_spine.py
./scripts/check_phase1_live_source_hardening.py --live
./scripts/check_supplied_credentials.py
./scripts/refresh_acled_token.py --write --validate-read
```

## 6. Stage P3-2A - Yahoo Finance Capability Review

Objective: decide how the local `yahoo-finance-api/` checkout changes Qadam's data-source and market-confirmation plan before Phase 3 consumes any market-context output.

Latest audit record: `docs/qadam-pre-phase-3-yahoo-finance-capability-review-audit-2026-05-22.md`.

### Local Codebase Findings

The local `yahoo-finance-api/` folder is a `yfinance` reference checkout. Its README describes a Pythonic interface for Yahoo Finance data and exposes these useful components:

- `Ticker`: single-symbol data.
- `Tickers` and `download`: multi-symbol historical market data.
- `Market`: market status and summary.
- `WebSocket` and `AsyncWebSocket`: live streaming data.
- `Search`: quote, news, and research search.
- `Sector` and `Industry`: sector and industry context.
- `EquityQuery`, `FundQuery`, `ETFQuery`, and `screen`: market screening.

The implementation can fetch:

- OHLCV bars through `Ticker.history()` and `download()`.
- Options chains through `Ticker.option_chain()`.
- Financial statements and balance sheet data.
- Earnings calendar and corporate event dates.
- Analyst price targets, recommendations, and upgrades/downgrades.
- Market status summaries.
- Quotes, news, and related research search results.
- WebSocket ticks for supported symbols.

The dependency footprint is meaningful: pandas, numpy, requests/curl_cffi, multitasking, platformdirs, pytz, frozendict, peewee, BeautifulSoup, protobuf, and websockets. Optional caching/rate-limit helpers are present through `requests_cache` and `requests_ratelimiter`.

The legal and operating boundary matters. The local README says `yfinance` is not affiliated with, endorsed by, or vetted by Yahoo, uses publicly available Yahoo APIs, and is intended for research and educational/personal use. Qadam must therefore treat it as a research-grade, read-only market confirmation source unless a later legal/commercial review says otherwise.

### How This Shifts The Approach

Yahoo Finance should slightly backtrack the pre-Phase-3 source plan in five ways:

1. Market price confirmation should no longer wait only on Alpaca market data, TradingView alerts, UnusualWhales, or prediction markets. A Yahoo Finance adapter can provide read-only OHLCV and volume context for liquid public instruments.
2. Signal Integrity currently asks for `market_price_confirmation` and the Akber filter asks for pricing-gap, volatility, technical, and volume confirmation. Yahoo Finance can become the first practical source for those confirmation fields, especially when TradingView remains alert-only and UnusualWhales is still missing.
3. Yahoo Finance should not silently become canonical source number 36. The first implementation should be a supplemental `market.yahoo_finance` capability and only become canonical after the master plan explicitly changes the 35-source registry.
4. The Phase 2 shadow cycle should be able to attach Yahoo Finance context to candidate-shaped evidence once a wrapper passes acceptance: last close, percent move, volume ratio, rolling volatility, option-chain availability, and instrument metadata.
5. Phase 3 should not consume quantum/classical oracle input that lacks market-confirmation context when Yahoo Finance could provide a cheap read-only check for the instrument.

### Recommended Treatment

Implemented status: accepted as a supplemental read-only market-data capability with classification `accepted_supplemental_pending_live_dependencies`.

The first Qadam wrapper now exists in `orchestrator/yahoo_finance_adapter.py`, with deterministic sample mode and guarded live mode. Live Yahoo Finance reads are not certified yet because the active `.venv` cannot import the local checkout until pandas and the rest of the yfinance dependency set are installed. The wrapper is not wired into Phase 2, Phase 3, Signal Integrity, cockpit status, or the canonical source registry.

Do not directly import `yfinance` inside intelligence, risk, cockpit, or strategy modules. Wrap it behind a Qadam adapter module first, with the same adapter envelope used by other sources:

- Sample mode from deterministic fixtures.
- Live mode behind `YFINANCE_ENABLED=true` or an equivalent config flag.
- No API key by default.
- Local cache directory under `data/runtime/`.
- Per-run symbol allowlist and request budget.
- Explicit stale-data handling.
- Explicit provider/rate-limit degradation.
- Local raw archive.
- Normalized `UnifiedEvent` output.
- Event Log entry for every fetch attempt.
- Public-safe cockpit status.

The initial symbol universe should be small and tied to Qadam's first trading universe:

- Crude/energy: `CL=F`, `BZ=F`, `USO`, `XLE`.
- Silver/metals: `SI=F`, `SLV`, `SIL`, `PAAS`.
- Defence: `ITA`, `XAR`, `LMT`, `RTX`, `NOC`.
- Semiconductors: `SMH`, `SOXX`, `NVDA`, `TSM`, `ASML`, `AMD`.
- Macro proxies: `SPY`, `QQQ`, `DXY` proxy where available, `TLT`, `HYG`, `VIX` proxy where available.

The first adapter should avoid WebSocket streaming. Start with daily or 1-hour OHLCV snapshots, options-chain metadata for a small equity/ETF allowlist, and market status. Streaming can be a later local bridge only after rate limits, reconnect behavior, and snapshot fallback are proven.

### Boundaries

- Yahoo Finance is not a broker.
- Yahoo Finance cannot provide execution authority.
- Yahoo Finance data cannot be used as a fill price, broker echo, order receipt, or post-trade reconciliation source.
- Yahoo Finance should not be the sole source that moves a signal to risk review.
- Yahoo Finance news/search results are narrative context, not high-trust evidence.
- Yahoo Finance terms and personal-use boundaries must remain visible before production or public-member use.
- If Yahoo Finance is unavailable, Qadam should degrade to `market_confirmation_unavailable`, not fabricate technical confirmation.

### Work

- Record `yahoo-finance-api/` as a local reference checkout in the baseline audit.
- Decide whether to keep it untracked as a reference repo, install it into `.venv`, or vendor it deliberately. Do not accidentally commit it as bulk material.
- Add a Qadam adapter design note for `market.yahoo_finance`.
- Add optional runtime controls to the credential/config ledger: `YFINANCE_ENABLED`, `YFINANCE_CACHE_DIR`, and `YFINANCE_REQUEST_BUDGET_PER_RUN`.
- Build `orchestrator/yahoo_finance_adapter.py` only after this plan is accepted. Completed for dormant sample/guarded-live mode.
- Build `scripts/check_yahoo_finance_adapter.py` with dry fixture mode first and live mode second. Completed.
- Add a small source observation type for `market_price_confirmation`.
- Add Yahoo Finance context to Phase 2 only after the adapter check passes.
- Add cockpit status fields only after the adapter output is public-safe.

### Acceptance Gate

- Yahoo Finance is explicitly classified as `accepted_supplemental`, `deferred`, or `rejected`.
- If accepted, it has a Qadam wrapper before any intelligence module consumes it.
- The adapter can fetch sample market confirmation without network access.
- Live fetches are read-only, rate-limited, cached, and gracefully degraded.
- Outputs contain no cookies, crumb tokens, local cache paths, raw HTML, or full unfiltered provider payloads in public-safe status.
- Yahoo Finance can satisfy `market_price_confirmation` only as corroboration, never as sole signal authority.
- No broker write, paper order, live capital, or quantum hardware authority is added.

Verification:

```bash
./scripts/check_yahoo_finance_adapter.py
./scripts/check_yahoo_finance_adapter.py --live
./scripts/check_phase1_data_spine.py
./scripts/check_signal_integrity_gate.py
./scripts/check_cockpit_status.py
```

Until live dependencies, public-safe cockpit status, and Phase 2 wiring are separately completed, pre-Phase-3 certification must record Yahoo Finance as `accepted_supplemental_pending_live_dependencies`, not as an active canonical source.

## 7. Stage P3-3 - Durable Observation Spine

Objective: make local replay reliable before Phase 3 depends on prior observations.

Latest audit record: `docs/qadam-pre-phase-3-durable-observation-spine-audit-2026-05-22.md`.

Work:

- Keep OrbStack or another Docker-compatible runtime available during local work.
- Start the Timescale-backed Postgres service after machine restarts.
- Apply migrations.
- Seed durable reference and world-model tables.
- Write deterministic source observations for all 35 canonical sources.
- Verify strict replay coverage without writing new rows.
- Ensure offline Postgres degrades to `ready_waiting_for_local_service` rather than producing false readiness.

Acceptance gate:

- `source_observation` can replay all 35 canonical sources.
- Replay is read-only.
- Durable observations cannot create signals, candidates, orders, broker writes, or live-capital authority.
- Cockpit Mission Control reports durable spine state accurately.

Verification:

```bash
./scripts/start_postgres_timescale_ingestion.sh
./scripts/check_postgres_timescale_ingestion.py --require-live
./scripts/check_postgres_timescale_replay.py --require-full-source-coverage
```

## 8. Stage P3-4 - Agent OS Enforcement

Objective: prove that agents and tools cannot accumulate hidden authority before deeper model workflows.

Latest audit record: `docs/qadam-pre-phase-3-agent-os-enforcement-audit-2026-05-22.md`.

Work:

- Validate all 8 agent manifests.
- Validate all 7 reusable skill bundles.
- Check required tool grants.
- Check forbidden broker-write tools.
- Check undeclared-tool failure.
- Validate sample output schemas.
- Keep `execution_allowed=false`, `paper_order_allowed=false`, and `broker_write_allowed=false` explicit in every sample output.
- Keep Research Analyst queue writes local-only and shadow-only.

Acceptance gate:

- Every allowed tool call is explicitly granted.
- Every undeclared tool call blocks.
- Every broker-write tool blocks for every agent.
- No LLM agent can approve risk, create paper orders, write to brokers, or enable live capital.

Verification:

```bash
./scripts/check_agent_manifests.py
./scripts/check_agent_runtime.py
./scripts/check_phase1_agent_os.py
```

## 9. Stage P3-5 - Phase 2 Shadow Cycle

Objective: make Qadam think from evidence without allowing it to act.

Work:

- Run deterministic shadow intelligence.
- Run local Research Analyst dry checks.
- Run LM Studio live local Research Analyst checks only after the local server is reachable.
- Run durable replay shadow cycle after P3-3 is green.
- Run live-source shadow cycle after P3-2 live checks are current.
- Attach Yahoo Finance market-confirmation context only after P3-2A accepts the capability and a Qadam adapter check exists.
- Attach read-only Alpaca paper-account context.
- Write Strategy Lead handoff packets as challenge-only analysis.
- Keep Gemini probes to model-list/status checks unless a later research packet gate is explicitly approved.

Acceptance gate:

- Shadow packets and shadow signals are created.
- Strategy Lead can receive handoff context.
- Paper-account context is sanitized and read-only.
- All outputs remain non-executable.
- Missing or stale data results in degraded or hold state, not false confidence.
- Yahoo Finance context, if present, is tagged as supplemental market confirmation and cannot create signal authority by itself.

Verification:

```bash
./scripts/check_shadow_intelligence.py
./scripts/check_local_research_analyst.py
./scripts/check_phase2_paper_context.py
./scripts/check_phase2_durable_replay_cycle.py
./scripts/check_strategy_lead_durable_context.py
./scripts/run_phase2_shadow_cycle.py --durable-replay
./scripts/run_phase2_shadow_cycle.py --live-sources --live-local-llm
```

Latest audit record: `docs/qadam-pre-phase-3-phase-2-shadow-cycle-audit-2026-05-22.md`.

## 10. Stage P3-6 - Safety Chain

Objective: prove the complete pre-execution safety chain before Phase 3 advice can enter it.

Work:

- Run Signal Integrity reviews on recent shadow signals.
- Run Risk Agent policy reviews on Signal Integrity outputs and trade-intent records.
- Run Execution Policy / kill-switch reviews on Risk Agent outputs.
- Run disabled staged-paper-order review.
- Run read-only broker reconciliation review.
- Run dry-run paper-submit receipt review.
- Require a pricing-gap and market-price-confirmation policy that can use Yahoo Finance once accepted, but still holds when that context is stale, unavailable, or single-source.
- Confirm the safety chain handles both candidate-shaped records and blocked records.
- Confirm every layer exposes required next steps without creating authority.

Acceptance gate:

- Signal Integrity may block, hold, or mark risk-shadow readiness, but cannot create trade candidates.
- Risk Agent may block or hold, but cannot approve risk or create orders.
- Execution Policy may block or hold, but cannot stage orders.
- Staged paper-order contract cannot create staged orders.
- Broker reconciliation cannot allocate broker-usable IDs, create broker echoes, prewrite order events, or submit paper orders.
- Dry-run receipt cannot call Alpaca POST routes or submit paper orders.
- Yahoo Finance cannot provide broker echo, order price, fill confirmation, receipt evidence, or reconciliation truth.
- Authority counters for execution, paper orders, broker writes, and live capital remain zero.

Verification:

```bash
./scripts/check_signal_integrity_gate.py
./scripts/check_risk_agent_policy_router.py
./scripts/check_execution_policy_router.py
./scripts/check_staged_paper_order_contract.py
./scripts/check_broker_reconciliation_contract.py
./scripts/check_paper_submit_receipt_contract.py
```

Latest audit record: `docs/qadam-pre-phase-3-safety-chain-audit-2026-05-22.md`.

## 11. Stage P3-7 - Cockpit Status And Public-Safe Export

Objective: make the cockpit show reality without exposing secrets or overstating readiness.

Work:

- Export the cockpit status snapshot after stages P3-1 through P3-6 pass.
- Include durable ingestion status and replay coverage.
- Include source classifications and degraded reasons.
- Include local Research Analyst and Strategy Lead shadow summaries without raw prompts or raw model text.
- Include Signal Integrity, Risk Agent, Execution Policy, staged order, broker reconciliation, and dry-run receipt state.
- Include paper-account mirror state as read-only context.
- Include Yahoo Finance status only after it has a public-safe wrapper: enabled/deferred, last check, symbol count, stale/degraded reason, and zero authority. Do not expose raw payloads, cookies, crumb tokens, cache paths, or scraped HTML.
- Include public-safe quantum scaffold state only as parked/non-executable if already present.
- Deploy `landing-page-repo` only after local checks pass and the nested repo status is understood.

Acceptance gate:

- Cockpit snapshot contains no secrets, local absolute paths, raw payloads, raw model prompts, raw broker IDs, allowlist emails, or broker authority.
- Dashboard language distinguishes observation, hypothesis, proposed signal, blocked/held record, staged paper order, submitted paper order, open position, closed trade, and postmortem.
- No UI element implies Qadam is about to trade unless the backend state later reaches a valid execution-stage status.

Verification:

```bash
./scripts/export_cockpit_status.py
./scripts/check_cockpit_status.py
git -C landing-page-repo status --short
```

Latest audit record: `docs/qadam-pre-phase-3-cockpit-status-public-safe-export-audit-2026-05-22.md`.

## 12. Stage P3-8 - Operational Runbook

Objective: make the pre-Phase-3 routine repeatable after restarts or new credentials.

Work:

- Add a staged operator runbook and one-command local routine.
- Define a normal local startup sequence.
- Define a source-refresh sequence.
- Define a durable-replay sequence.
- Define a shadow-intelligence sequence.
- Define a cockpit-export sequence.
- Define a pre-commit secret scan.
- Keep Telegram in dry-run/notify-only mode unless explicit send testing is approved.
- Keep TradingView observed-only until the secure receiver path is approved.
- Keep Yahoo Finance read-only and supplemental; run its adapter check only after the wrapper exists.

Acceptance gate:

- A new session can refresh the local state without rereading the whole repo.
- Failed services degrade clearly.
- Secrets remain local-only.
- No notification, broker, or quantum hardware side effect happens accidentally.

Routine:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage all
./scripts/run_pre_phase3_operational_routine.sh --stage all --dry-run
```

Secret scan:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Expected secret-scan result: `pre_phase3_secret_scan=ok`.

Detailed runbook: `docs/qadam-pre-phase-3-operational-runbook.md`.

Latest audit record: `docs/qadam-pre-phase-3-operational-runbook-audit-2026-05-22.md`.

## 13. Stage P3-9 - Pre-Phase-3 Certification

Objective: make a deliberate decision before Phase 3 resumes as a build track.

Work:

- Run every acceptance command in this document.
- Record the exact date, local service status, source counts, replay coverage, and authority counters.
- List remaining degraded sources.
- List remaining missing credentials.
- Record Yahoo Finance treatment: accepted supplemental, deferred, rejected, or active adapter.
- Confirm Phase 2 has enough replay/live context for the Head of Quant to receive shadow-only review inputs.
- Confirm any existing Phase 3 scaffold still has:
  - zero hardware submissions,
  - zero scheduler enablement,
  - zero trade-candidate creation,
  - zero execution approvals,
  - zero paper-order approvals,
  - zero broker writes.
- Decide whether Phase 3 may proceed to provider/scheduler readiness work.

Acceptance gate:

- P3-0 through P3-8 are green or explicitly deferred with a documented reason.
- Durable replay is either green or intentionally marked as blocked by local service availability.
- Phase 2 shadow cycle can produce non-executable context for Signal Integrity and Strategy Lead.
- Safety chain remains zero-authority.
- Cockpit reflects the same truth as the local checks.

Certification record template:

```text
Date:
Branch:
Commit:
OrbStack/Postgres:
LM Studio:
Source count:
Promoted adapter count:
Missing credential count:
Deferred source count:
Yahoo Finance treatment:
Yahoo Finance adapter status:
Yahoo Finance symbol universe:
Durable replay status:
Durable replay source coverage:
Phase 2 durable replay status:
Strategy Lead handoff status:
Signal Integrity status:
Risk Agent status:
Execution Policy status:
Staged paper-order status:
Broker reconciliation status:
Paper-submit receipt status:
Cockpit status check:
Execution allowed count:
Paper order allowed/submitted count:
Broker write allowed count:
Live capital enabled count:
Quantum hardware submitted count:
Decision:
```

Latest certification record: `docs/qadam-pre-phase-3-certification-2026-05-22.md`.

## 14. Recommended Stage Order

Use this order for implementation work:

1. P3-0 Baseline Audit.
2. P3-1 Foundation Health.
3. P3-2 Source And Credential Ledger.
4. P3-2A Yahoo Finance Capability Review.
5. P3-3 Durable Observation Spine.
6. P3-4 Agent OS Enforcement.
7. P3-5 Phase 2 Shadow Cycle.
8. P3-6 Safety Chain.
9. P3-7 Cockpit Status And Public-Safe Export.
10. P3-8 Operational Runbook.
11. P3-9 Pre-Phase-3 Certification.

If local Postgres/Timescale is offline, continue P3-1, P3-2, P3-2A, P3-4, P3-6 dry-contract checks, and P3-8 runbook work. Do not certify P3-3, P3-5 durable replay, P3-7 live cockpit durable status, or P3-9 until the service is running again.

## 15. Phase 3 Entry Rule

Phase 3 can resume beyond scaffold mode only when the pre-Phase-3 certification record says:

- Foundation checks are green.
- Source registry and credential ledger are current.
- Yahoo Finance has an explicit treatment decision, and if active, is wrapped as a read-only supplemental market-confirmation adapter.
- Durable replay is green or explicitly deferred by local service state.
- Agent OS and runtime enforcement are green.
- Phase 2 shadow cycle is producing non-executable context.
- The safety chain remains zero-authority.
- Cockpit status is public-safe and consistent with local checks.
- Existing quantum scaffold remains non-executable and hardware-submission blocked.

Until then, Phase 3 work is limited to documentation, local schema review, and non-executing contract checks.
