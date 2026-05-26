# Qadam Phase 7 Q7-18 Live Promotion Review Flow Audit

Date: 2026-05-25

## Scope

Q7-18 implements the read-only live-promotion review flow for Phase 7. The
stage prepares the contract for Ramin's structured review packet, cooling-off
requirements, and later explicit approval gates without executing promotion or
opening live authority.

## Implementation

- Added `orchestrator/phase7_live_promotion_review.py`.
- Added `scripts/check_phase7_live_promotion_review.py`.
- Added runtime output at `data/runtime/phase7_live_promotion_review.json`.
- Added history output at
  `data/runtime/phase7_live_promotion_review_history.jsonl`.
- Added Event Log output at
  `data/runtime/phase7_live_promotion_review_events.jsonl`.
- Updated `docs/qadam-phase-7-demo-proof-implementation-plan.md`.
- Updated `docs/qadam-master-implementation-plan.md`.

## Current Runtime State

The current runtime is correctly blocked because Q7-17 has not certified the
30-day proof run:

```text
phase7_live_promotion_status=blocked
phase7_live_promotion_stage_status=live_promotion_review_blocked_phase7_not_certified
phase7_live_promotion_source_certification_status=blocked
phase7_live_promotion_source_certification_stage_status=phase7_certification_blocked_run_incomplete
phase7_live_promotion_phase7_demo_proof_certified=False
phase7_live_promotion_q7_18_live_promotion_review_stage_allowed=False
phase7_live_promotion_review_packet_draft_allowed=False
phase7_live_promotion_review_packet_created=False
phase7_live_promotion_review_state=blocked_pending_phase7_certification
phase7_live_promotion_cooling_off_required=True
phase7_live_promotion_cooling_off_complete=False
phase7_live_promotion_live_promotion_approval_state=not_requested
phase7_live_promotion_live_credentials_enabled=False
phase7_live_promotion_live_credentials_loaded=False
phase7_live_promotion_live_capital_enabled=False
phase7_live_promotion_live_broker_write_allowed=False
phase7_live_promotion_phase7_proof_credit_allowed=False
phase7_live_promotion_broker_post_called_count=0
phase7_live_promotion_alpaca_post_called_count=0
phase7_live_promotion_unsafe_write_counter_total=0
phase7_live_promotion_blocker_count=2
phase7_live_promotion_blockers=phase7_certification_not_certified,q7_18_live_promotion_review_not_allowed
phase7_live_promotion_event_log_events=1
phase7_live_promotion_validation_errors=[]
phase7_live_promotion_check=ok
```

## Review Packet Contract

When Q7-17 eventually certifies, Q7-18 can create a read-only packet with these
sections:

- `phase7_certification_summary`
- `thirty_day_operational_result`
- `maturity_and_sample_size`
- `drawdown_and_risk`
- `override_and_clean_sample`
- `postmortems`
- `source_signal_chain`
- `weekly_review_notes`
- `operational_incidents`
- `cooling_off_and_approval_requirements`
- `live_credential_and_capital_lockout`

The packet remains review-only. Cooling off is required for 72 hours, approval
state stays `not_requested`, and a later explicit gate must record any live
approval.

## Safety Boundaries

Q7-18 does not:

- approve live promotion
- load live credentials
- enable live capital
- call broker POST or Alpaca POST routes
- write prediction-market or crypto-perps orders
- bypass the cooling-off period
- grant Phase 7 proof credit
- count Phase 5 test trades toward Phase 7 proof
- infer readiness from the UI
- expose raw payloads, local paths, secrets, broker identifiers, request
  bodies, receipts, or source payloads

## Validation Probes

The checker validates:

- current blocked runtime state before Q7-17 certification
- valid post-certification read-only review packet probe
- rejection of early Q7-18 handoff
- rejection of packet creation while blocked
- rejection of live credential enabling or loading
- rejection of live capital
- rejection of broker, Alpaca, prediction-market, and crypto-perps write
  authority
- rejection of Phase 7 proof credit
- rejection of cooling-off bypass
- rejection of premature approval
- rejection of raw public payload leakage
- rejection of source display/backend mismatch

## Verification

```bash
.venv/bin/python scripts/check_phase7_live_promotion_review.py
.venv/bin/python -m ruff check orchestrator/phase7_live_promotion_review.py scripts/check_phase7_live_promotion_review.py
```

Both commands passed on 2026-05-25.
