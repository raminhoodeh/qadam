# Qadam Phase 5 Q5-3 Risk Agent Paper Sizing Audit - 2026-05-24

## Scope

Q5-3 implements the Risk Agent paper-sizing contract for Phase 5 Layer B. It
consumes Q5-2 approval-policy decisions, Phase 4 candidate strategy families,
Signal Integrity evidence, paper-account state, Yahoo Finance market
confirmation policy, and Preference/PREF MCP source posture.

The contract can block, hold, or mark a strategy family as paper-size eligible
for later Q5-4 kill-switch checks. It cannot create trade candidates, hand off
to Execution Policy, create execution intents, stage or submit paper orders,
write brokers, create receipts, create positions, or enable live capital.

## Implemented Artifacts

- `orchestrator/phase5_risk_sizing.py`
- `scripts/check_phase5_risk_agent_paper_sizing.py`
- `data/runtime/phase5_risk_sizing_reviews.json`
- `data/runtime/phase5_risk_sizing_events.jsonl`
- `data/runtime/phase5_risk_sizing_reviews_history.jsonl`

## Runtime Result

`scripts/check_phase5_risk_agent_paper_sizing.py` reports:

```text
phase5_risk_sizing_status=ok
phase5_risk_sizing_review_count=5
phase5_risk_sizing_eligible_count=0
phase5_risk_sizing_hold_count=0
phase5_risk_sizing_blocked_count=5
phase5_risk_sizing_paper_size_eligible_count=0
phase5_risk_sizing_approval_policy_eligible_count=5
phase5_risk_sizing_event_log_written=True
phase5_risk_sizing_event_log_total_events=5
phase5_risk_sizing_validation_error_count=0
phase5_risk_sizing_global_error_count=0
phase5_risk_sizing_risk_approval_allowed_count=0
phase5_risk_sizing_trade_candidate_created_count=0
phase5_risk_sizing_execution_allowed_count=0
phase5_risk_sizing_paper_order_allowed_count=0
phase5_risk_sizing_broker_write_allowed_count=0
phase5_risk_sizing_position_created_count=0
phase5_risk_sizing_yahoo_role=supplemental_market_confirmation_only
phase5_risk_sizing_preference_source36=False
phase5_risk_sizing_check=ok
```

The five strategy families have Q5-2 policy eligibility but fail Q5-3 risk
sizing under current evidence:

- `prediction_market_geopolitical_dislocation`
- `crude_oil_energy_security_disruption`
- `defence_repricing_geopolitical_watch`
- `silver_macro_liquidity_stress`
- `semiconductor_policy_options_asymmetry`

All five currently produce `risk_decision=blocked_risk_gate_failed` and
`proposed_risk_gbp=0.0`. The sizing cap is 1% of the GBP 1000 first-release
policy balance, so `max_risk_gbp=10.0`.

The primary blockers are Signal Integrity not yet passing to risk shadow,
missing or insufficient market confirmation, and unconfirmed pricing-gap
evidence. The semiconductor family has current market corroboration available,
but still blocks because pricing-gap evidence is not confirmed and Signal
Integrity remains hold-only.

## Source Policy

Q5-3 enforces:

- Yahoo Finance is supplemental market confirmation only.
- Yahoo-only confirmation is not allowed.
- Preference/PREF MCP remains supplemental context.
- Preference/PREF MCP is not source 36.
- Preference/PREF MCP paid tools remain disabled.
- Preference/PREF MCP source-quorum credit remains false.
- Preference-only confirmation remains false.
- Canonical source count remains 35.

Preference quota degradation is retained as caution-only supplemental context.
It does not become a source-quorum blocker by itself, and it does not grant any
risk, execution, order, broker, or live-capital authority.

## Safety Probes

The checker rejects dishonest risk-sizing payloads for:

- proposed risk above cap
- paper-size eligibility without Signal Integrity pass
- paper-size eligibility without Q5-2 policy eligibility
- paper-size eligibility without invalidation conditions
- paper-size eligibility while drawdown exceeds cap
- broker-write enablement
- staged-order creation
- paper-order authority
- Yahoo Finance promoted to canonical source
- Preference/PREF MCP source-quorum credit

## Verification

Commands run successfully:

```bash
.venv/bin/python -m compileall orchestrator/phase5_risk_sizing.py scripts/check_phase5_risk_agent_paper_sizing.py
.venv/bin/ruff check orchestrator/phase5_risk_sizing.py scripts/check_phase5_risk_agent_paper_sizing.py
.venv/bin/python scripts/check_phase5_risk_agent_paper_sizing.py
.venv/bin/python scripts/check_phase5_approval_policy_router.py
.venv/bin/python scripts/check_risk_agent_policy_router.py
```

## Exit State

Q5-3 is complete. Qadam may proceed to Q5-4 - Kill-Switch Ledger.

Layer B orchestration start remains false. Risk approval, execution handoff,
execution intents, paper order staging, paper order submission, broker writes,
live Telegram execution alerts, prediction-market writes, position mutation,
and live capital remain disabled.
