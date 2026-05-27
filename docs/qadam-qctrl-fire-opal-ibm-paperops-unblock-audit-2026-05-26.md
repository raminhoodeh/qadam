# Q-CTRL Fire Opal And PaperOps Unblock Audit

Date: 2026-05-26

## Summary

Q-CTRL Fire Opal product access is now verified for the `qadam` organization.
Q-CTRL is no longer a PaperOps submit blocker.

The Fire Opal on IBM Quantum notebook has been converted into a local readiness
contract. Fire Opal is verified first, then IBM Quantum token/instance and
Qiskit Runtime package readiness are checked before an explicit device probe.
The gate never submits hardware jobs or grants trade authority.

## Runtime Evidence

- `paper_live_qctrl_product_access_status=qctrl_paper_consultation_ready`
- `paper_live_qctrl_product_access_verified=True`
- `paper_live_qctrl_product_access_provider_call_succeeded=True`
- `paper_live_qctrl_product_access_blocker=none`
- `paper_ops_status=ready_for_full_paper_ops`
- `paper_ops_blocker_count=0`
- `paper_ops_cycle_status=paper_cycle_full_paper_operational_ready`
- `paper_ops_cycle_command_passed_count=34`
- `paper_ops_cycle_command_failed_count=0`
- `paperops_alpaca_post_status=submitted_to_alpaca_paper`
- `paperops_alpaca_post_called_count=1`
- `paperops_alpaca_post_succeeded_count=1`
- `paperops_lifecycle_poller_status=paper_lifecycle_poll_recorded`
- `paperops_lifecycle_poller_source_submitted_order_count=1`
- `paperops_lifecycle_poller_order_poll_succeeded_count=1`
- `paperops_lifecycle_poller_open_position_count=0`
- `paper_live_certification_blockers=phase7_30_day_run_complete,phase7_demo_proof_certified`

## Fire Opal IBM Readiness

- `fire_opal_ibm_readiness_status=blocked_missing_ibm_quantum_credentials`
- `fire_opal_ibm_fire_opal_product_access_verified=True`
- `fire_opal_ibm_qctrl_product_access_status=qctrl_paper_consultation_ready`
- `fire_opal_ibm_fire_opal_sdk_importable=True`
- `fire_opal_ibm_ibm_quantum_token_configured=False`
- `fire_opal_ibm_ibm_quantum_instance_configured=False`
- `fire_opal_ibm_qiskit_ibm_runtime_importable=True`
- `fire_opal_ibm_qiskit_importable=True`
- `fire_opal_ibm_hardware_submission_allowed=False`

## Code Changes

- Added `qctrl_organization_slug` runtime config with `qadam` as the non-secret
  default organization slug.
- Added `scripts/check_qctrl_fire_opal_ibm_quantum.py`.
- Added Fire Opal IBM readiness functions in `orchestrator/quantum.py`.
- Added `IBM_QUANTUM_INSTANCE` docs and optional `quantum-ibm` dependencies.
- Installed `qiskit`, `qiskit-ibm-runtime`, `qctrl-visualizer`, and
  `matplotlib` in the local project virtualenv, leaving IBM token/instance as
  the remaining Fire Opal IBM readiness blocker.
- Added Fire Opal IBM readiness to cockpit status and the dashboard Head of
  Quant annotation so the Fund Manager can see Q-CTRL access, IBM runtime
  readiness, IBM credential state, and the hardware-submission block separately.
- Split PT-10 status into dynamic states so a cleared Q-CTRL hold now reports
  `blocked_pending_phase7_proof` instead of the stale combined Q-CTRL/Phase 7
  blocker.
- Updated PaperOps-Q, PaperOps-2, PaperOps-3, and PT-6 checks so normal safe
  cycles preserve verified provider, submitted paper order, and lifecycle
  readback artifacts instead of overwriting them with placeholders.

## Remaining Blockers

- IBM Quantum hardware device discovery needs local `IBM_QUANTUM_TOKEN` and
  `IBM_QUANTUM_INSTANCE`.
- PT-10 full paper-live certification still waits for the actual Phase 7
  30-day proof run and Phase 7 certification.
- The submitted Alpaca paper order is currently accepted with no fill, so no
  open position or exit candidate exists yet.
