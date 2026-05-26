# Qadam Pre-Phase-3 Operational Runbook

This runbook is the Stage P3-8 operator path for `docs/qadam-pre-phase-3-implementation-plan.md`.

Use it when starting a new local session, adding credentials, refreshing source state, rerunning durable replay, or exporting the cockpit before Phase 3 work resumes.

## One-Command Routine

Run the full local routine from the repository root:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage all
```

Preview the routine without running commands:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage all --dry-run
```

Run a single stage:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage local-startup
./scripts/run_pre_phase3_operational_routine.sh --stage source-refresh
./scripts/run_pre_phase3_operational_routine.sh --stage durable-replay
./scripts/run_pre_phase3_operational_routine.sh --stage shadow-intelligence
./scripts/run_pre_phase3_operational_routine.sh --stage safety-chain
./scripts/run_pre_phase3_operational_routine.sh --stage cockpit-export
./scripts/run_pre_phase3_operational_routine.sh --stage dashboard
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

## Normal Local Startup

Run this after opening the repo in a fresh terminal:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage local-startup
```

This verifies:

- repository foundation
- local Event Log path
- local store health contracts
- source registry shape
- Agent OS manifests and runtime grants
- Phase 1 data spine
- Yahoo Finance wrapper in sample/live-degraded mode

Expected posture:

- missing live credentials degrade as missing credentials
- Yahoo Finance can remain deferred when `YFINANCE_ENABLED=false`
- no broker-write route is opened
- no Telegram send route is opened
- no quantum hardware route is opened

## Source Refresh

Run this after adding or rotating source credentials:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage source-refresh
```

This refreshes the source heartbeat and validates the read-only adapter posture. It keeps TradingView as observed-only and Yahoo Finance as supplemental market confirmation.

Use provider-specific live checks only when deliberately testing a credential. Examples:

```bash
.venv/bin/python scripts/check_nasa_firms_adapter.py --live
.venv/bin/python scripts/check_alpaca_paper_mirror.py --live
.venv/bin/python scripts/check_fred_adapter.py --live
```

Do not paste real keys into docs, chat, screenshots, or committed files. Real secrets belong only in `data/runtime/qadam-secrets.env` with mode `600`.

## Durable Replay

Run this when local Docker/OrbStack is available:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage durable-replay
```

This starts local Postgres/Timescale, applies migrations, seeds deterministic durable observations, verifies live ingestion, verifies full-source replay coverage, and checks the Phase 2 durable replay bridge.

Expected success posture:

- 35 canonical sources replay from `source_observation`
- replayed observations remain read-only
- replay cannot create signals, candidates, paper orders, broker writes, or live-capital authority

If Docker/OrbStack is closed, do not certify durable replay. Run the non-live visibility checks instead:

```bash
.venv/bin/python scripts/check_postgres_timescale_ingestion.py
.venv/bin/python scripts/check_postgres_timescale_replay.py
.venv/bin/python scripts/check_phase2_durable_replay_cycle.py
```

The cockpit should degrade clearly rather than imply replay is live.

## Shadow Intelligence

Run this after durable replay is green:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage shadow-intelligence
```

This verifies shadow intelligence and runs the durable Phase 2 shadow cycle:

- durable observations become local Research Analyst packets
- Strategy Lead receives non-executable shadow context
- safety-chain packets remain blocked or held until downstream policy allows them

Boundary:

- Research Analyst cannot create orders
- Strategy Lead cannot bypass Signal Integrity
- durable replay cannot become execution authority

## Safety Chain

Run this before every cockpit export and before any later Phase 3 continuation:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage safety-chain
```

This validates:

- Signal Integrity
- Risk Agent
- Execution Policy
- disabled staged paper-order contract
- read-only broker reconciliation contract
- dry-run paper-submit receipt contract

Required state:

- zero paper orders created
- zero broker POST calls
- zero broker writes
- zero live-capital authority
- Yahoo Finance cannot move a signal forward alone

## Cockpit Export

Run this after source, durable, shadow, and safety stages:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage cockpit-export
```

This writes:

- `data/runtime/cockpit-status.json`
- `data/runtime/cockpit-status.signature.json`
- `landing-page-repo/status/cockpit-status.json`
- `landing-page-repo/status/cockpit-status.signature.json`

Then run the dashboard checks:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage dashboard
```

Do not deploy `landing-page-repo` until local checks pass and `git -C landing-page-repo status --short` is understood.

## Secret Scan

Run this before committing or sharing output:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Expected result:

```text
pre_phase3_secret_scan=ok
```

No output from the underlying `rg` scan means no obvious secret value was found. Secret names and empty placeholders are allowed; secret values are not.

## Safety Locks

These locks remain in force during P3-8:

- Telegram: `QADAM_TELEGRAM_ENABLED=false` unless explicit send testing is approved; keep `QADAM_TELEGRAM_DRY_RUN=true` by default.
- TradingView: observed alert intake only; no execution path.
- Yahoo Finance: read-only supplemental market confirmation; not canonical source authority.
- Alpaca: paper mirror is GET-only until later execution stages deliberately add order paths.
- Quantum: classical/local scaffold only; no hardware scheduler or hardware submissions.
- Browser/cockpit: public-safe status only; no secret, raw payload, raw prompt, broker ID, or allowlist email exposure.

## When To Stop

Stop and fix before proceeding to P3-9 if any of these appear:

- `cockpit_status_check` is not `ok`
- durable replay is required but Postgres/Timescale is offline
- a safety-chain authority counter is non-zero
- `paper_order_created_count` or broker-write count is non-zero
- dashboard wording implies execution readiness that backend state does not support
- secret scan prints any match
- `landing-page-repo` has unexpected changes unrelated to the cockpit status export

