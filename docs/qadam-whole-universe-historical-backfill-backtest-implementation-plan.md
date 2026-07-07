# Qadam Whole-Universe Historical Backfill And Backtest Implementation Plan

Date: 2026-07-06

Purpose: turn Qadam's existing QSASE backtesting infrastructure into a durable,
resumable, multi-day baseline backfill and backtest runner across the full
current data source universe and full current trading universe.

This is not a new trading feature. It is the evidence foundation Qadam needs
before it can honestly call itself backtest-first and self-refining.

## 1. Current State

Current local state, verified before this plan:

| Item | Current value |
| --- | --- |
| Active Qadam autonomous runner process | Not running after targeted process stop |
| Current source rows | 41 |
| Current source categories | 6 |
| Current watched instruments | 19 |
| Current source-price matrix records | 6,232 |
| Current complete forward windows | 82 |
| Current missing forward windows | 6,150 |
| Current complete forward-window ratio | 0.0132 |
| Current local data/runtime footprint | About 2.6 GB |
| Current PaperOps route | Guarded paper-only route remains separate |

Existing useful modules:

- `orchestrator/historical_backfill.py`
- `orchestrator/qsase_universal_source_price_matrix.py`
- `orchestrator/qsase_historical_source_price_memory.py`
- `orchestrator/qsase_linear_pattern_lab.py`
- `orchestrator/qsase_full_universe_pattern_search.py`
- `orchestrator/qsase_nonlinear_quantum_pattern_lab.py`
- `orchestrator/qsase_shadow_strategy_simulator.py`
- `orchestrator/qsase_learning_attribution_ledger.py`

Current gap:

`orchestrator/historical_backfill.py` is only a sample-contract runner. It
plans historical backfills and records local sample observations, but it does
not yet execute provider-specific multi-day historical pulls, full price
history collection, full source event history collection, or complete
source-price forward-window repair.

## 2. Target Outcome

Build a long-running command that can safely run for up to five days on the
local laptop:

```bash
caffeinate -dimsu .venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --max-runtime-hours 120
```

The runner should:

- Inventory every current data source and watched instrument.
- Backfill historical source events where provider history is available.
- Backfill historical price windows for every watched instrument and proxy.
- Align source events and price history point-in-time.
- Complete missing forward windows where data exists.
- Run whole-universe baseline backtests.
- Run linear, analog, state-matrix, nonlinear, and quantum/classical review
  where input coverage is sufficient.
- Produce a baseline evidence map showing which source categories historically
  led which markets.
- Keep all output research-only, paper-only, proposal-first, and fail-closed.

## 3. Non-Negotiable Boundaries

The whole-universe backfill and backtest runner must not:

- Edit secrets, `.env` files, live credentials, or live-capital settings.
- Submit paper orders.
- Submit live orders.
- Call broker live endpoints.
- Grant paper proof ledger credit.
- Advance the 30-day paper growth trial calendar.
- Simulate elapsed paper-trial time.
- Create trade candidates directly.
- Create risk approvals.
- Create execution approvals.
- Let Telegram or the dashboard create commands.
- Treat a backtest as proof.

Every artifact must expose authority flags:

```json
{
  "read_only": true,
  "paper_only": true,
  "proposal_first": true,
  "trade_candidate_creation_allowed": false,
  "risk_approval_allowed": false,
  "execution_allowed": false,
  "paper_order_allowed": false,
  "broker_write_allowed": false,
  "live_capital_enabled": false,
  "proof_credit_allowed": false,
  "paper_growth_trial_calendar_advance_allowed": false
}
```

## 4. Architecture

### 4.1 New Orchestrator Module

Create:

```text
orchestrator/qsase_whole_universe_backfill_backtest.py
```

Responsibilities:

- Build the full job manifest.
- Maintain the checkpoint state.
- Run provider-specific backfill batches.
- Normalize historical source and price records.
- Repair source-price forward windows.
- Run whole-universe baseline tests.
- Update dashboard-safe summaries.
- Fail closed on any authority drift.

### 4.2 New Runner Script

Create:

```text
scripts/run_qsase_whole_universe_backfill_backtest.py
```

Required CLI:

```bash
.venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --dry-run
.venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --max-runtime-hours 120
.venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --batch-limit 100
.venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --sources all --instruments all
```

Optional CLI:

```bash
--source acled
--source gdelt
--instrument USO
--instrument SMH
--from-date YYYY-MM-DD
--to-date YYYY-MM-DD
--max-provider-calls N
--sleep-between-calls SECONDS
--network-disabled
--paperops-paused-required
```

### 4.3 Runtime Artifacts

Create these canonical artifacts:

```text
data/runtime/qsase_whole_universe_backfill_backtest_manifest.json
data/runtime/qsase_whole_universe_backfill_backtest_state.json
data/runtime/qsase_whole_universe_backfill_backtest_progress.jsonl
data/runtime/qsase_whole_universe_backfill_backtest_errors.jsonl
data/runtime/qsase_whole_universe_backfill_backtest_summary.json
data/runtime/qsase_whole_universe_backfill_backtest_dashboard_summary.json
data/runtime/qsase_backfill_source_history_manifest.json
data/runtime/qsase_backfill_price_history_manifest.json
data/runtime/qsase_backfill_forward_window_completion.json
data/runtime/qsase_baseline_backtest_results.jsonl
data/runtime/qsase_baseline_backtest_rejections.jsonl
data/runtime/qsase_baseline_backtest_evidence_map.json
data/runtime/qsase_baseline_strategy_evidence_map.json
```

Large raw records should be written append-only and chunked, not repeatedly
rewritten as one massive JSON file.

Suggested raw-history layout:

```text
data/runtime/backfill/source_history/<source_key>/<yyyy>/<chunk>.jsonl
data/runtime/backfill/price_history/<symbol>/<timeframe>/<yyyy>/<chunk>.jsonl
data/runtime/backfill/alignment/<source_key>/<symbol>/<window>.jsonl
```

## 5. Phase 0 - Quiescence And Pause Contract

Before the five-day job starts, Qadam needs a local pause/lock contract to avoid
PaperOps and dashboard refresh jobs fighting over the same runtime artifacts.

Implement:

```text
data/runtime/qadam_long_backtest_lock.json
```

Fields:

```json
{
  "lock_type": "qsase_whole_universe_backfill_backtest",
  "status": "active",
  "started_at": "...",
  "max_runtime_hours": 120,
  "paperops_autonomous_runner_paused": true,
  "paper_order_creation_allowed": false,
  "broker_write_allowed": false,
  "live_capital_enabled": false,
  "reason": "long historical backfill and backtest in progress"
}
```

Required checks:

- Verify no active PaperOps autonomous process is running.
- Verify no active daily-learning live runner is running.
- Verify no dashboard deployment process is running.
- Verify PaperOps can read the lock and degrade to watch-only if invoked.
- Verify removing the lock is explicit and logged.

Acceptance:

- A check script reports `qadam_long_backtest_lock_active=true`.
- PaperOps wrapper refuses new order-producing work while the lock is active.
- Existing account state is not mutated by the backtest.

## 6. Phase 1 - Universe Freeze

Build a point-in-time manifest of the universe being tested.

Inputs:

- `data/runtime/qsase_dashboard_source_network.json`
- `data/runtime/qsase_source_universe.json`
- `data/runtime/qsase_trading_universe.json`
- `data/runtime/qsase_dashboard_strategy_universe.json`

Output:

```text
data/runtime/qsase_backtest_universe_freeze.json
```

The freeze must include:

- Source category.
- Source key.
- Provider.
- Credential requirement.
- Historical availability.
- Freshness state.
- Quorum role.
- Instrument symbol.
- Instrument family.
- Paperability.
- Strategy-family mapping.
- Core vs secondary instrument role.
- Backtest eligibility.

Acceptance:

- Every one of the current 41 source rows is classified.
- Every one of the current 19 watched instruments is classified.
- Any unavailable source or instrument is marked with a reason, not silently
  dropped.

## 7. Phase 2 - Provider Capability Audit

For each provider, define what history can actually be fetched.

Provider classes:

| Provider class | Examples | Backfill role |
| --- | --- | --- |
| Market prices | Alpaca paper/read data, Yahoo-style research prices, Stooq/CSV fallback | OHLCV and forward windows |
| Macro | FRED, ECB, BIS, BLS, USGS, UN Comtrade | macro state and regime features |
| Geopolitics | ACLED, GDELT, UCDP, conflict tracker | event source signals |
| Physical world | NASA FIRMS, AIS maritime | physical disruption signals |
| Filings/policy | SEC EDGAR, Stock Act/capitol trades, patents | defence/semi/policy signals |
| Prediction markets | Kalshi, Polymarket | probability signals and event contracts |
| Social/narrative | Reddit Narrative Proxy, RSS/news, Telegram intake | narrative context, never command authority |
| Technical/order flow | TradingView, Bookmap/CVD if available | Akber confirmation inputs |

Output:

```text
data/runtime/qsase_backfill_provider_capability_audit.json
```

Acceptance:

- Every provider has `available`, `blocked_missing_credentials`,
  `blocked_missing_history`, or `not_supported_yet`.
- The runner can continue if optional providers are unavailable.
- Unavailable history reduces confidence instead of fabricating data.

## 8. Phase 3 - Historical Price Lake

Backfill historical prices for all watched instruments and secondary proxies.

Required fields:

- symbol
- provider
- timeframe
- timestamp
- open
- high
- low
- close
- adjusted_close if available
- volume if available
- currency
- source_available_at
- provider_latency_notes

Timeframes:

- Daily bars for all instruments.
- Intraday bars only where available and rate-limit safe.
- Futures symbols like `CL=F` and `SI=F` can be research-only if direct paper
  expression is not available.

Acceptance:

- Price history exists for every paperable instrument.
- Research-only instruments are mapped to paperable proxies where possible.
- Missing histories are written to a missing-history ledger.

## 9. Phase 4 - Historical Source Event Lake

Backfill source events into normalized source-event records.

Required fields:

- source_event_id
- source_key
- source_category
- event_timestamp
- source_available_at
- geography
- actor if available
- theme or mechanism
- severity or magnitude if available
- source_confidence
- raw_ref
- normalized_text
- affected_market_hints

Acceptance:

- Source histories are stored append-only.
- Every event has `source_available_at`.
- Events without point-in-time safety are quarantined.
- Narrative/social sources remain evidence only and cannot satisfy quorum alone.

## 10. Phase 5 - Point-In-Time Source-Price Alignment

For every valid source event and watched instrument, create source-price windows.

Core windows:

- event time
- same session close
- 1 day forward
- 3 days forward
- 5 days forward
- 10 days forward
- 20 days forward
- 60 days forward

Alignment must respect:

- market calendars
- weekends and holidays
- source availability delay
- provider publication delay
- no outcome leakage into features

Acceptance:

- Missing forward windows fall materially below the current 6,150.
- Every complete window has price before, price after, forward return,
  volatility context, and volume context if available.
- Leakage audit passes.

## 11. Phase 6 - Initial Whole-Universe Baseline Backtest

This is the core baseline.

It should test:

- source category to market response
- individual source to market response
- source combinations to market response
- event severity to return relationship
- lead-lag timing
- cross-asset relationships
- regime-conditioned relationships
- market-family response differences
- false-positive rate

Required metrics:

- sample count
- hit rate
- average forward return
- median forward return
- expectancy
- max adverse excursion
- max favorable excursion
- drawdown proxy
- confidence interval
- p-value or non-parametric equivalent where appropriate
- false-positive rate
- regime split
- liquidity/paperability flag
- overfit warning

Acceptance:

- Baseline results are emitted for the whole universe, not only one strategy
  family.
- Low-sample relationships are rejected or marked insufficient data.
- No backtest creates a trade candidate or proof credit.

## 12. Phase 7 - Linear Pattern Lab Expansion

Expand the existing linear lab to consume the new baseline.

Tests:

- event-study returns
- lead-lag regression
- cross-correlation
- factor-controlled regressions
- source-before-price tests
- divergence tests
- walk-forward validation
- out-of-sample validation

Acceptance:

- Accepted patterns require minimum sample count, walk-forward survival, and
  leakage safety.
- Inconclusive patterns remain under observation.
- Rejected patterns store rejection reasons.

## 13. Phase 8 - Analog, Similarity, And State Matrix Models

Implement the pattern methods most relevant to Qadam:

- pattern-agnostic vector similarity
- kNN historical analog retrieval
- correlation-based historical occurrence models
- state matrix probability models
- anchored historical scenarios

Outputs:

```text
data/runtime/qsase_analog_backtest_results.jsonl
data/runtime/qsase_state_matrix_probability_results.jsonl
data/runtime/qsase_historical_analog_library.json
```

Acceptance:

- Every analog includes historical forward outcomes.
- Similarity does not imply prediction unless outcome evidence is present.
- State probabilities are regime-labeled.

## 14. Phase 9 - Nonlinear, Entropy, And Quantum/Classical Review

Use nonlinear review where linear tests are insufficient.

Methods:

- interaction effects across source groups
- regime path dependence
- permutation/ordinal entropy
- nonlinear ambiguity scoring
- quantum/classical review labels where available
- simulator fallback labels when hardware is unavailable

Acceptance:

- Nonlinear review can upgrade, downgrade, or hold research confidence.
- Quantum review cannot approve trades.
- Classical fallback is labeled honestly.

## 15. Phase 10 - Strategy Evidence Map

Only after the baseline backtest should Qadam map evidence to strategies.

Output:

```text
data/runtime/qsase_baseline_strategy_evidence_map.json
```

For each strategy family:

- supporting source-price relationships
- unsupported assumptions
- best instruments
- weak instruments
- secondary confirmation instruments
- backtest sample count
- expectancy
- drawdown proxy
- regime dependency
- Akber confirmation requirements
- whether the strategy remains active, shadow-only, or held

Acceptance:

- Strategy Universe cards become evidence-backed.
- Strategy labels do not determine the evidence upfront.
- New strategy families can be proposed if whole-universe evidence justifies
  them.

## 16. Phase 11 - Akber Filter Backtest Calibration

Backtest Akber's six-stage filter as a practical trader, not as a decorative
gate.

Akber inputs:

- context
- catalyst
- confirmation
- volatility
- volume/flow
- technical state
- risk/reward
- invalidation
- execution feasibility

Tests:

- What happens if Akber passes?
- What happens if Akber holds?
- What happens if Akber vetoes?
- Does Akber reduce false positives?
- Does Akber over-filter good setups?

Output:

```text
data/runtime/qsase_akber_backtest_calibration.json
```

Acceptance:

- Akber thresholds are proposals only.
- No threshold mutation happens automatically.
- Router receives calibrated evidence, not direct order authority.

## 17. Phase 12 - Shadow Simulation And Router Dry Mapping

Run shadow decisions on baseline-backed hypotheses.

For each hypothesis:

- trade-now counterfactual
- wait counterfactual
- veto counterfactual
- no-order counterfactual
- alternate threshold replay

Output:

```text
data/runtime/qsase_baseline_shadow_router_map.json
```

Acceptance:

- Shadow success cannot create paper orders.
- Shadow success cannot create paper proof ledger credit.
- Router outputs remain dry/research until PaperOps receives a separate
  eligible handoff.

## 18. Phase 13 - Dashboard And Telegram Visibility

Dashboard should show:

- backfill progress
- provider coverage
- source-event coverage
- price-history coverage
- forward-window completion
- strongest source-price relationships
- rejected relationships
- strategy evidence map
- Akber calibration state
- shadow simulation state
- why no trade was created

Telegram should only send short progress notes, for example:

```text
Qadam backtest: 38% complete.
Best current evidence: maritime disruption has the strongest oil-price lead.
Blocked: forward windows still incomplete. No orders or proof credit.
```

Acceptance:

- Dashboard and Telegram remain read-only.
- Progress messages are specific and deduped.
- No command path is enabled.

## 19. Phase 14 - Certification

Create:

```text
scripts/check_qsase_whole_universe_backfill_backtest.py
```

Certification must validate:

- lock state
- universe coverage
- provider capability audit
- price history coverage
- source event coverage
- forward-window completion
- leakage checks
- baseline backtest artifacts
- rejected-pattern records
- strategy evidence map
- Akber calibration records
- shadow simulation records
- dashboard summary
- Telegram summary boundary
- proof boundary
- calendar boundary
- broker-write boundary
- live-capital boundary

Acceptance:

```text
qsase_whole_universe_backfill_backtest_check=ok
```

## 20. Runtime Strategy For A Five-Day Laptop Run

The runner should use a conservative batch loop:

1. Load manifest.
2. Pick next pending source or price job.
3. Execute a small provider-safe batch.
4. Write raw records.
5. Write normalized records.
6. Update checkpoint.
7. Sleep if rate-limit policy requires.
8. Run lightweight validation.
9. Continue until max runtime, completion, or fail-closed stop.

The runner must survive:

- laptop sleep interruption
- network failure
- provider rate limits
- malformed provider responses
- partial file writes
- Codex app restart
- Qadam process restart

Checkpoint fields:

```json
{
  "status": "running",
  "started_at": "...",
  "updated_at": "...",
  "max_runtime_hours": 120,
  "completed_job_count": 0,
  "failed_job_count": 0,
  "pending_job_count": 0,
  "last_completed_job_id": "...",
  "current_job_id": "...",
  "current_phase": "price_history_backfill",
  "safe_to_resume": true,
  "paper_order_created_count": 0,
  "broker_write_count": 0,
  "live_capital_enabled": false
}
```

## 21. Hardware Expectation

Your laptop is sufficient for the current universe if the runner is batch-based:

- 24 GB RAM is enough for the current universe if raw records are streamed and
  chunked.
- 1 TB SSD is enough for the current 2.6 GB runtime footprint plus a practical
  daily/intraday history lake, assuming raw payloads are compressed or chunked.
- The M5 chip is not the bottleneck for the current universe.
- The bottleneck is provider history availability, API rate limits, and data
  cleaning.

Expected duration:

| Run mode | Expected duration |
| --- | --- |
| Dry-run manifest | seconds to minutes |
| Current artifact rebuild | seconds to minutes |
| Initial usable baseline with available local/easy history | hours to overnight |
| Full provider-backed whole-universe baseline | 1 to 5 days |
| Intraday/order-flow-heavy expansion | several days or separate infrastructure |

## 22. Launch Procedure After Implementation

Before launch:

```bash
.venv/bin/python scripts/check_qsase_whole_universe_backfill_backtest.py --preflight
```

Start:

```bash
caffeinate -dimsu .venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --max-runtime-hours 120
```

Monitor:

```bash
tail -f data/runtime/qsase_whole_universe_backfill_backtest_progress.jsonl
```

Resume after interruption:

```bash
caffeinate -dimsu .venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --max-runtime-hours 120
```

Final certification:

```bash
.venv/bin/python scripts/check_qsase_whole_universe_backfill_backtest.py
```

## 23. Completion Definition

The backfill/backtest baseline is complete when:

- Every current source row is classified and either backfilled or explicitly
  blocked with a reason.
- Every current watched instrument is classified and either price-backfilled or
  explicitly blocked with a reason.
- Missing forward windows are materially reduced.
- Leakage checks pass.
- Baseline source-price backtest results exist.
- Rejected relationships are recorded.
- Strategy evidence map exists.
- Akber calibration exists.
- Shadow router map exists.
- Dashboard summary exists.
- No paper order, broker write, live-capital flag, or proof credit was created.

The final answer after certification should not be "Qadam can now trade".

The honest answer should be:

```text
Qadam now has a whole-universe historical evidence baseline. It can use that
baseline to refine strategy hypotheses, Akber thresholds, and shadow routing,
but paper trades still require a fresh current setup and the guarded PaperOps
route.
```

