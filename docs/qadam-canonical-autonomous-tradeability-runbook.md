# Qadam Canonical Autonomous Tradeability Runbook

Date: 2026-08-19

## Operating Contract

Qadam runs one paper-only decision path:

`trigger -> evidence envelope -> execution context -> Akber -> shadow -> risk -> Router -> PaperOps handoff -> guarded Alpaca Paper -> lifecycle -> learning`

Only `scripts/run_paperops_autonomous_pass.py` may reach the guarded Alpaca
Paper write route. Models, dashboard, Telegram, research jobs, quantum jobs and
compatibility readers have no broker-write authority. Live capital remains
disabled.

## Start And Stop

Use the version-bound service installer rather than launching duplicate workers:

```bash
scripts/restart_qadam_operator_safely.sh
```

The operator must run with the paper release effective, the research lock
released, and one active lease. The exit manager may continue independently for
open-position protection.

To quiesce the main operator without cancelling broker orders, use the existing
safe stop procedure in `scripts/restart_qadam_operator_safely.sh`. Never delete
the control-plane database to clear a status.

## Verify

Run the single release checker:

```bash
.venv/bin/python scripts/check_qadam_canonical_autonomous_tradeability.py
```

Interpret the result precisely:

- `blocked`: a safety, authority, integrity or implementation check failed.
- `implementation_ready`: code and migration checks pass; five real sessions
  have not yet accrued.
- `observation_ready`: the installed build passed five distinct real US market
  sessions without simulated or backfilled time.
- `ready_idle`: the operating path is healthy but no accepted handoff exists.

`ready_idle` is not a failure and must not be converted into a forced order.

## Current Truth

The authoritative local state is the ignored SQLite/WAL control plane at
`data/runtime/qadam-control-plane.sqlite3`. JSON and JSONL files are rebuildable
read-only projections. An empty Router generation must never erase an earlier
handoff, receipt, broker event or lifecycle event.

The source capability registry separates:

- 41 catalogue sources;
- currently provider-backed and fresh confirmation sources;
- quorum-eligible current sources;
- historically scored alpha signals;
- forward-only, unavailable and excluded sources.

Never use the catalogue count as a claim of 41 independent tested signals.

## No-Trade Diagnosis

Every setup receives one Router terminal state and one primary blocker. Check:

1. `data/runtime/qadam_router_v3_why_not_trading_now.json` for the investment
   decision.
2. `data/runtime/qadam_execution_context_summary.json` for market session,
   quote and provider state.
3. `data/runtime/qadam_trigger_proxy_compiler_checks.json` for internal
   conversion or mapping defects.
4. `data/runtime/qadam_canonical_autonomous_tradeability_dashboard_summary.json`
   for the public-safe operating summary.

Missing soft evidence may reduce size under the reviewed profile policy.
Missing current price/spread, paper route, risk budget, idempotency, drawdown or
other hard safety evidence remains fail-closed.

## PaperOps And Exactly Once

An accepted Router decision creates an immutable handoff and an outbox event.
The canonical wrapper consumes it using the same candidate identity and
idempotency key. Ambiguous broker responses are reconciled read-only and are
never retried blindly. Multiple distinct qualified setups may be submitted,
but duplicate exposure and duplicate identity remain blocked.

## Lifecycle And Learning

Lifecycle polling records submitted, accepted, partial-fill, fill, cancel,
reject, expire, open and closed states append-only. Learning can consume a
closed outcome only after broker reconciliation. Historical records with
missing lineage remain explicitly incomplete and cannot receive paper proof
ledger credit.

Strategy improvements are versioned proposals. Bounded paper-version promotion
may occur only inside the frozen paper risk envelope after preregistered
criteria pass. Qadam cannot silently expand risk or enable live capital.

## Real-Market Soak

`scripts/check_qadam_catc_real_market_soak.py` records a session only after a
real US market close when all execution services ran on the same committed
build, circuits were closed, and conversion, mapping, lineage, duplicate-write
and starvation defects were zero. Five sessions are required. Sessions are
never simulated or backfilled.

## Incident Response

- Provider failure: isolate the affected provider/instruments and keep other
  domains healthy.
- Dashboard or Telegram failure: repair the projection domain; do not block
  execution.
- Quantum dependency failure: degrade research only.
- Schema, conversion or mapping defect: create an engineering repair request;
  do not report it as an Akber investment hold.
- Disk pressure: stop write services safely, preserve lifecycle polling, and
  run the reviewed storage-maintenance path.
- Uncertain broker write: reconcile by broker/client order identity before any
  further action.

## Rollback

Rollback code and database schema together. Preserve the pre-CATC baseline,
database backups and imported source checksums. After rollback, reconcile
Alpaca Paper read-only before restoring PaperOps. Never run old and new writers
at the same time.
