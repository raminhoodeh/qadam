# Qadam Phase 5 Q5-2 Approval Policy Router Audit - 2026-05-24

## Scope

Q5-2 implements the first active Layer B contract after the Q5-1 schema work:
a deterministic Approval Policy Router that consumes certified Phase 4 strategy
approval, approved-shadow strategy toggles, candidate strategy families, Phase 5
readiness, Yahoo Finance market-confirmation policy, and Preference/PREF MCP
source posture.

The router is policy-only. It cannot create trade candidates, hand off to Risk
Agent, create execution intents, stage or submit paper orders, call broker
write endpoints, create broker receipts, create positions, send execution
alerts, or enable live capital.

## Implemented Artifacts

- `orchestrator/phase5_approval_policy.py`
- `scripts/check_phase5_approval_policy_router.py`
- `data/runtime/phase5_approval_policy_decisions.json`
- `data/runtime/phase5_approval_policy_events.jsonl`
- `data/runtime/phase5_approval_policy_decisions_history.jsonl`

Q5-2 also extends `orchestrator/phase5_artifacts.py` so the shared Phase 5
artifact validator can validate later-stage artifacts by explicit stage while
keeping Q5-1 as the default.

## Runtime Result

`scripts/check_phase5_approval_policy_router.py` reports:

```text
phase5_approval_policy_status=ok
phase5_approval_policy_decision_count=5
phase5_approval_policy_eligible_count=5
phase5_approval_policy_hold_count=0
phase5_approval_policy_blocked_count=0
phase5_approval_policy_approved_shadow_toggle_count=5
phase5_approval_policy_phase5_implementation_allowed=True
phase5_approval_policy_orchestration_start_allowed=False
phase5_approval_policy_phase4_certified=True
phase5_approval_policy_phase5_handoff_allowed=True
phase5_approval_policy_event_log_written=True
phase5_approval_policy_event_log_total_events=5
phase5_approval_policy_validation_error_count=0
phase5_approval_policy_global_error_count=0
phase5_approval_policy_trade_candidate_created_count=0
phase5_approval_policy_risk_handoff_allowed_count=0
phase5_approval_policy_execution_allowed_count=0
phase5_approval_policy_paper_order_allowed_count=0
phase5_approval_policy_broker_write_allowed_count=0
phase5_approval_policy_position_created_count=0
phase5_approval_policy_preference_source36=False
phase5_approval_policy_yahoo_role=supplemental_market_confirmation_only
phase5_approval_policy_check=ok
```

The five strategy families are eligible only for the next Q5-3 risk-sizing
contract:

- `prediction_market_geopolitical_dislocation`
- `crude_oil_energy_security_disruption`
- `defence_repricing_geopolitical_watch`
- `silver_macro_liquidity_stress`
- `semiconductor_policy_options_asymmetry`

Each decision has `policy_decision=eligible_for_q5_3_risk_sizing_contract`,
`approved_strategy_toggle_state=approved_shadow`, `policy_blocker_count=0`, and
Event Log correlation. Preference/PREF MCP quota degradation is preserved as a
caution-only supplemental context. It does not create a hold or authority grant
because canonical source quorum remains intact and Preference remains
supplemental.

## Source Policy

Q5-2 enforces:

- Yahoo Finance role is `supplemental_market_confirmation_only`.
- Yahoo-only confirmation is not allowed.
- Preference/PREF MCP role is `supplemental_multi_source_data_plane`.
- Preference/PREF MCP is not source 36.
- Preference/PREF MCP paid tools remain disabled.
- Preference/PREF MCP source-quorum credit remains false.
- Preference-only confirmation remains false.
- Canonical source count remains 35.

## Safety Probes

The checker rejects dishonest policy-decision payloads for:

- eligible decision without an `approved_shadow` toggle
- broker-write enablement
- staged-order creation
- broker POST / receipt creation
- position creation
- Yahoo Finance promoted to canonical source
- Preference/PREF MCP promoted to source 36
- Preference/PREF MCP source-quorum credit

## Verification

Commands run successfully:

```bash
.venv/bin/python -m compileall orchestrator/phase5_artifacts.py orchestrator/phase5_approval_policy.py scripts/check_phase5_artifact_schema.py scripts/check_phase5_approval_policy_router.py
.venv/bin/ruff check orchestrator/phase5_artifacts.py orchestrator/phase5_approval_policy.py scripts/check_phase5_artifact_schema.py scripts/check_phase5_approval_policy_router.py
.venv/bin/python scripts/check_phase5_artifact_schema.py
.venv/bin/python scripts/check_phase5_readiness.py
.venv/bin/python scripts/check_phase5_approval_policy_router.py
.venv/bin/python scripts/check_phase4_strategy_toggles.py
```

## Exit State

Q5-2 is complete. Qadam may proceed to Q5-3 - Risk Agent Paper Sizing Contract.

Layer B orchestration start remains false. Paper order staging, paper order
submission, broker writes, live Telegram execution alerts, prediction-market
writes, position mutation, and live capital remain disabled.
