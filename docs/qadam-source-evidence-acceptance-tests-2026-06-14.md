# Qadam Source/Evidence Acceptance Tests - 2026-06-14

Status: implemented

## Scope

This acceptance stage validates the non-dashboard source and evidence work:

- source registry cleanup;
- credential-bound read-only adapters;
- provider decisions;
- Bookmap local bridge;
- TradingView MCP read-only technical context;
- evidence packet normalization;
- durable evidence packet runtime;
- cockpit export integration.

It explicitly excludes Stage 7 Dashboard Simplification. The Stage 7
simplification plan remains plan-only and has no acceptance implementation in
this pass.

## Acceptance Gate

Run:

```bash
.venv/bin/python scripts/check_source_evidence_acceptance.py
```

The checker composes the existing focused checks:

- `scripts/check_source_registry_blockers.py`
- `scripts/check_phase1_data_spine.py`
- `scripts/check_phase1_live_source_hardening.py`
- `scripts/check_credential_bound_adapters.py`
- `scripts/check_provider_decision_pass.py`
- `scripts/check_tradingview_mcp_adapter.py`
- `scripts/check_bookmap_local_bridge.py`
- `scripts/check_evidence_packet_normalization.py`
- `scripts/check_evidence_packet_runtime.py`
- `scripts/check_cockpit_status.py`

It writes a local public-safe report to:

```text
data/runtime/source_evidence_acceptance.json
```

## Required Result

The acceptance gate must print:

```text
source_evidence_acceptance_status=ok
source_evidence_acceptance_check=ok
source_evidence_acceptance_dashboard_simplification_skipped=True
```

## Contract Assertions

The acceptance gate proves:

- all 35 canonical source records are still present;
- legacy source-registry blockers are zero;
- Phase 1 deterministic source observations cover all 35 sources;
- selected optional credential gaps remain explicit and non-blocking;
- Reddit, Kalshi/OddsPipe, and Capitol Trades/STOCK Act remain credential-bound,
  read-only adapters; OddsPipe satisfies first-release Kalshi/Polymarket
  monitoring while direct Kalshi remains deferred;
- RapidAPI, Coinglass, Chainlink, GitHub, and Bookmap provider decisions do not
  create credential pressure or trading authority;
- TradingView MCP observes and analyzes only;
- Bookmap local bridge observes order flow only;
- normalized evidence packets strip raw references;
- durable evidence runtime writes replayable local JSON/JSONL state;
- cockpit status exports evidence normalization and runtime status as `ok`;
- source gaps are not trade-blocking or silent;
- live capital remains disabled.

## Authority Boundary

This stage cannot approve signals, create source quorum, create trade
candidates, submit Alpaca Paper orders, call brokers, run quantum jobs, grant
proof credit, send Telegram commands, or enable live capital.
