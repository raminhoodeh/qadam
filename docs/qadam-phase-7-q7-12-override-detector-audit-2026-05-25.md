# Qadam Phase 7 Q7-12 Override Detector Audit - 2026-05-25

## Scope

Q7-12 implements the Phase 7 Demo Proof override detector. It consumes the
Q7-11 drawdown sentinel, Q7-5 auto-approval router, and Q7-8 lifecycle monitor
to detect manual trade-level approvals, rejections, quantity edits, price
edits, manual exits, broker-side intervention, and unlinked lifecycle records.

This stage can mark the proof sample contaminated and require restart. It
cannot approve trades, create proof trades, grant proof credit, mutate policy
or strategy, call broker or Alpaca POST routes, write prediction-market or
crypto-perps orders, permit manual trade-level overrides, or enable live
capital.

## Files

- `orchestrator/phase7_override_detector.py`
- `scripts/check_phase7_override_detector.py`
- `data/runtime/phase7_override_detector.json`
- `data/runtime/phase7_override_detector_history.jsonl`
- `data/runtime/phase7_override_detector_events.jsonl`

## Runtime Result

The Q7-12 checker writes the local runtime artifact and records one Event Log
entry.

Key outputs:

- `phase7_override_status=clean_no_overrides`
- `phase7_override_stage_status=override_detector_clean_no_interventions`
- `phase7_override_schema_version=1`
- `phase7_override_source_drawdown_status=ready_no_drawdown_sample`
- `phase7_override_source_drawdown_new_proof_trades_frozen=False`
- `phase7_override_q7_13_signal_stage_allowed=True`
- `phase7_override_detection_write_allowed=True`
- `phase7_override_sample_contaminated=False`
- `phase7_override_clean_sample=True`
- `phase7_override_count=0`
- `phase7_override_record_count=0`
- `phase7_override_manual_trade_level_override_count=0`
- `phase7_override_broker_side_intervention_count=0`
- `phase7_override_unlinked_lifecycle_record_count=0`
- `phase7_override_governance_feedback_record_count=3`
- `phase7_override_governance_feedback_trade_level_intervention_count=0`
- `phase7_override_new_proof_trades_frozen=False`
- `phase7_override_new_proof_order_staging_allowed=True`
- `phase7_override_new_proof_trade_submission_allowed=True`
- `phase7_override_phase7_certification_blocked_by_override=False`
- `phase7_override_run_restart_required=False`
- `phase7_override_phase7_proof_credit_allowed=False`
- `phase7_override_live_capital_enabled=False`
- `phase7_override_broker_post_called_count=0`
- `phase7_override_alpaca_post_called_count=0`
- `phase7_override_unsafe_write_counter_total=0`
- `phase7_override_blocker_count=0`
- `phase7_override_event_log_replay_total_events=1`

## Interpretation

Q7-12 is clean in the current runtime. There are no manual trade-level
approvals, rejects, edits, exits, broker-side interventions, or unlinked
lifecycle records. Governance feedback channels are present but are marked as
future-policy only and do not contaminate the proof sample.

The new authority added by this stage is narrow
`override_detection_write_allowed=True`. It is limited to local clean-sample
and contamination evidence. If contamination appears, Q7-12 freezes new proof
trade staging/submission and requires a Phase 7 run restart.

## Guard Probes

The checker verifies that the following override and safety conditions are
enforced:

- governance-only records are accepted without contaminating the sample
- valid manual trade-level override contamination is accepted and blocks
  certification
- valid broker-side intervention contamination is accepted and blocks
  certification
- valid unlinked-lifecycle contamination is accepted and blocks certification
- inherited drawdown freezes are preserved without marking governance feedback
  as contamination
- contaminated samples that do not block certification are rejected
- contaminated samples that do not freeze new proof trades are rejected
- governance feedback that contaminates the sample is rejected
- manual override count drift is rejected
- clean samples with override counts are rejected
- Phase 7 proof credit remains disabled
- broker POST and Alpaca POST remain disabled
- live capital remains disabled
- prediction-market and crypto-perps writes remain disabled
- manual trade-level override authority remains disabled
- Preference/PREF source-quorum credit and Q-CTRL execution truth are rejected
- local absolute path leakage is rejected
- disabled Q7-12 stage gate is rejected
- disabled Q7-13 signal-funnel handoff gate is rejected

## Verification

Commands run:

```bash
.venv/bin/python scripts/check_phase7_override_detector.py
.venv/bin/python -m ruff check orchestrator/phase7_override_detector.py scripts/check_phase7_override_detector.py
.venv/bin/python -m compileall orchestrator/phase7_override_detector.py scripts/check_phase7_override_detector.py
```

Results:

- `phase7_override_detector_check=ok`
- `All checks passed!`
- `compileall` succeeded

## Handoff

Q7-12 is complete. The next explicit build target is Q7-13 - Source And Signal
Funnel Evidence.
