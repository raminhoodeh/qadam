# Qadam Active Edge Research Runbook

## Purpose

Qadam now has a mechanism-first research lane for testing whether California
electricity scarcity, renewable shortfalls, and grid congestion precede moves
in listed power-market assets. The lane is designed to increase the chance of
finding a defensible edge by adding genuinely different information rather
than rerunning the same market-price features.

The initial strategy family is `power_scarcity_congestion`. Its evidence comes
from read-only CAISO OASIS data and Alpaca IEX market data. The core instruments
are CEG, VST, NRG, and TLN; XLU, GRID, and UNG are secondary comparison proxies.

## Autonomous Progression

The frozen progression is:

1. Acquire provider-backed CAISO and Alpaca history with resumable partitions.
2. Align day-ahead evidence to later proxy returns without using future data.
3. Test scarcity, congestion, renewable-shortfall, and day-ahead-price methods.
4. Fit thresholds on training data, then evaluate validation and untouched
   holdout periods after a conservative 15-basis-point round-trip cost.
5. Apply deterministic permutation controls and Benjamini-Hochberg correction.
6. Keep weak results in research or reject them.
7. If a positive provisional result and a frozen current trigger coexist,
   automatically create a bounded pattern-sourced strategy hypothesis.
8. Pass that hypothesis through Strategy Foundry, Akber's 6-Stage Filter,
   forward shadowing, portfolio risk, Router, and guarded PaperOps.
9. Permit an Alpaca Paper order only if every current gate passes under the
   existing US$5,000 absolute experimental ceiling and 0.5 risk multiplier.
10. Attribute the real paper outcome without granting validated-edge or proof
    credit automatically.

Automatic strategy admission is not automatic risk expansion. The engine
cannot edit its policy, create live-capital authority, call a broker directly,
or bypass the canonical PaperOps wrapper.

## Operating States

- `historical_evidence_collecting`: provider acquisition is healthy but fewer
  than 90 overlapping evidence days are available.
- `hypotheses_tested_no_current_signal`: historical tests have run but no
  current setup satisfies both empirical and trigger requirements.
- `current_strategy_signal_active`: a bounded pattern score can enter Foundry
  and Akber review.
- `operational`: acquisition, testing, downstream contracts, operator service,
  dashboard projection, and authority boundaries all pass certification.
- `blocked`: at least one provider, lineage, downstream, operator, dashboard,
  storage, or authority check failed.

These states describe machinery and evidence, not expected profit. A healthy
no-trade result is still possible when the tested relationship does not survive
costs or when current tradeability evidence is incomplete.

## Canonical Commands

Run one bounded provider-backed pass:

```bash
.venv/bin/python scripts/run_qadam_power_market_edge_engine.py \
  --once --allow-network --max-partitions 8
```

Validate the research sleeve:

```bash
.venv/bin/python scripts/check_qadam_power_market_edge_engine.py
```

Validate end-to-end autonomous progression:

```bash
.venv/bin/python scripts/check_qadam_active_edge_research.py
```

The long-running operator invokes the same commands on a 30-minute cadence.
Provider retries use pending-first scheduling and bounded exponential backoff,
so one slow partition cannot starve untouched evidence.

## Canonical Artifacts

- `data/runtime/qadam_power_market_edge_engine.json`
- `data/runtime/qadam_power_market_acquisition_manifest.json`
- `data/runtime/qadam_power_market_backtest.json`
- `data/runtime/qadam_power_market_strategy_registry.json`
- `data/runtime/qadam_power_market_pattern_scores.jsonl`
- `data/runtime/qadam_power_market_context.json`
- `data/runtime/qadam_power_market_dashboard_summary.json`
- `data/runtime/qadam_power_market_edge_engine_checks.json`
- `data/runtime/qadam_active_edge_research_certification.json`
- `data/runtime/qadam_active_edge_research_checks.json`

Bulk raw and normalized provider data remains under
`data/research/power_market/`, which is Git-ignored and guarded by an 8 GiB
research-sleeve ceiling.
