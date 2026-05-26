# Qadam Strategy Research Intake Audit

Date: 2026-05-25

## Scope

Integrate the rough trading strategy notes into Qadam's decision-making engine
as structured research context.

This does not approve any strategy, create a signal, create a trade candidate,
approve risk, stage a paper order, call a broker, call Q-CTRL, or enable live
capital.

## Implemented

- Added `orchestrator/strategy_research_intake.py`.
- Added `scripts/check_strategy_research_intake.py`.
- Strategy Lead now receives strategy-research challenge context during the
  Phase 2 shadow cycle.
- The Phase 4 candidate strategy universe now annotates strategy families with
  matching research candidates and review questions.
- PaperOps readiness now requires the strategy-research intake to be present.
- The PaperOps cycle runner now executes the strategy-research intake check.
- `docs/qadam-trading-strategy-research-notes.md` now records the runtime
  integration path.

## Research Candidates

1. `pead_long_only_concordant`
2. `opening_range_breakout_vol_target`
3. `trend_following_baseline_control`
4. `volume_delta_dislocation`

The intake marks PEAD as the best initial research candidate and the simple
trend-following candidate as the benchmark control.

## Verification

Commands run:

- `.venv/bin/python -m ruff check ...`
- `.venv/bin/python -m compileall ...`
- `.venv/bin/python scripts/check_strategy_research_intake.py`
- `.venv/bin/python scripts/check_phase4_candidate_strategy_universe.py`
- `.venv/bin/python scripts/check_strategy_lead_durable_context.py`
- `.venv/bin/python scripts/run_phase2_shadow_cycle.py --durable-replay --events-per-source 2 --research-limit 8`
- `.venv/bin/python scripts/check_paper_operational_readiness.py`
- `.venv/bin/python scripts/run_paper_operational_cycle.py`

Key results:

- Strategy research intake status: `ready_for_strategy_review`.
- Strategy research candidates: `4`.
- Strategy Lead challenge count from the intake: `10`.
- Phase 4 research family coverage: `4` of `5` strategy families.
- Phase 4 research challenge count: `28`.
- Phase 2 durable replay status: `ok`.
- Strategy Lead consumed the research context with `4` candidates and `8`
  retained sanitized challenges.
- PaperOps cycle result: `paper_cycle_safe_blocked_pending_enablement`.
- PaperOps runner command result: `17/17`.
- Broker POST count: `0`.
- Alpaca POST count: `0`.
- Hard safety failures: `0`.

## Remaining Blockers

This integration does not remove the existing PaperOps blockers:

- `paper_operational_flag_disabled`
- `qctrl_paper_consultation_connected_not_ready`
- `external_alpaca_paper_post_enabled_not_ready`

Those remain separate PaperOps enablement stages.

