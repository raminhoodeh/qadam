# Qadam Five-Market-Day Active Discovery Trial

## Purpose

This is a frozen five-real-market-session test of Qadam's current autonomous
research-to-paper pipeline. It measures whether the system can review its full
watched universe, form bounded setups, apply its practical and portfolio gates,
and reach the guarded Alpaca Paper route when the evidence supports doing so.

The trial does not impose a trade quota. A session with no paper order is a valid
result when every setup has a recorded blocker. The trial does not advance the
30-day paper growth trial, create proof credit, enable live capital, or allow a
direct broker call.

## Frozen Seven Stages

1. **Unattended reliability:** require a healthy operator cycle with no open
   circuit or unresolved repair request.
2. **Whole-universe evaluation:** score all 19 watched instruments from the
   point-in-time evidence available during each real US market session.
3. **Setup formation:** shortlist five distinct high-value reviews and either
   form a directional hypothesis or preserve a typed rejection.
4. **Akber review:** record one pass, hold, or veto with current context,
   catalyst, confirmation, risk, execution, and learning evidence.
5. **Shadow and portfolio risk:** preserve the decision-time shadow record and
   create either a bounded size proposal or an explicit risk rejection.
6. **Router and guarded PaperOps:** assign exactly one Router state. Only a clean
   paper-review candidate can continue through the canonical guarded Alpaca
   Paper wrapper.
7. **Outcome and learning:** preserve the real session, order origin, lifecycle
   outcome, and proposal-only learning record for later comparison.

## Risk Envelope

- Paper account reference: US$100,000.
- Discovery allocation target: US$500 to US$1,000. The lower value is a target,
  not a forced floor; risk sizing may produce a smaller amount or no trade.
- Absolute per-trade ceiling: US$5,000.
- Maximum simultaneous canonical discovery positions: three.
- Maximum canonical discovery positions per correlated market cluster: one.
- Existing exploratory or manual paper exposure does not consume a canonical
  discovery slot, but it still counts toward gross exposure, correlation,
  drawdown, liquidity, and duplicate-exposure controls.

## Calendar Contract

Only a real session observed while the Alpaca market clock reports the US market
open can count. Weekends, closed-market refreshes, historical rows, backfills,
and simulated elapsed time cannot advance the five-session counter.

## Interpretation

The implementation is successful when the seven-stage machinery runs
generation-consistently and records five real sessions. The result is reported
as one of:

- `complete_autonomous_paper_conversion_observed`
- `complete_no_tradeable_setup_observed`
- `complete_with_operational_reliability_gaps`

The second state is not a software failure and does not justify forcing a trade.
It means no setup completed every current evidence, Akber, portfolio-risk, and
Router gate during the frozen observation window.

## Canonical Artifacts

- `data/runtime/qadam_active_discovery_trial_contract.json`
- `data/runtime/qadam_active_discovery_trial_status.json`
- `data/runtime/qadam_active_discovery_trial_evaluations.jsonl`
- `data/runtime/qadam_active_discovery_trial_sessions.jsonl`
- `data/runtime/qadam_active_discovery_trial_dashboard_summary.json`
- `data/runtime/qadam_active_discovery_trial_checks.json`

The Decision Room mirrors the dashboard-safe summary. That surface remains
read-only and command-disabled.
