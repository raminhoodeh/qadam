# Qadam PaperOps-Q Q-CTRL Paper Consultation Audit

Date: 2026-05-26

## Scope

PaperOps-Q implements the Q-CTRL paper-mode advisory gate required for
high-fidelity Paper Operational Mode. The gate may only attempt a provider
auth/status probe when Qadam is in paper mode, live capital is disabled, the
Q-CTRL credential is configured, the SDK is importable, and
`QADAM_QCTRL_PAPER_CONSULTATION_ENABLED=true` is explicitly set for that run.

Q-CTRL remains advisory only. It cannot create trade candidates, approve risk,
approve execution, create staged paper orders, submit broker orders, call live
endpoints, submit hardware jobs, expose secrets, persist raw provider responses,
or promote live capital.

## Implemented

- Added `orchestrator/paperops_qctrl_consultation.py`.
- Added `scripts/check_paperops_qctrl_consultation.py`.
- Added the `qctrl-paper` optional dependency group with `fire-opal`.
- Updated Q-CTRL SDK detection to check `fireopal`, `qctrl`, and `boulderopal`.
- Installed Fire Opal into the local virtualenv.
- Wired PaperOps readiness to read the PaperOps-Q consultation artifact instead
  of treating default Q-CTRL readiness as a provider-call source.
- Added the PaperOps-Q check to the PaperOps operational cycle.
- Added PaperOps-Q public-safe status into cockpit status.
- Attached the PaperOps-Q Head of Quant note into Q7 signal-funnel quantum
  shadow annotation context.

## Verification

Commands run:

```bash
.venv/bin/python -m pip install fire-opal
.venv/bin/python scripts/check_qctrl_readiness.py
.venv/bin/python scripts/check_quantum_provider_readiness.py
.venv/bin/python scripts/check_paperops_qctrl_consultation.py
env QADAM_QCTRL_PAPER_CONSULTATION_ENABLED=true .venv/bin/python scripts/check_paperops_qctrl_consultation.py
.venv/bin/python scripts/run_paper_operational_cycle.py
.venv/bin/python scripts/check_paper_operational_cycle.py
.venv/bin/python scripts/check_paper_operational_readiness.py
.venv/bin/python scripts/check_cockpit_status.py
.venv/bin/python scripts/check_phase7_signal_funnel_evidence.py
```

Observed safe default:

- `qctrl_readiness_status=configured_package_importable`
- `qctrl_credential_configured=True`
- `qctrl_sdk_package_importable=True`
- `qctrl_provider_call_count=0`
- `paperops_qctrl_status=disabled_pending_enablement`
- `paperops_qctrl_provider_call_count=0`
- `paperops_qctrl_execution_allowed=False`
- `paperops_qctrl_paper_order_allowed=False`
- `paperops_qctrl_broker_post_allowed=False`
- `paperops_qctrl_secret_value_exposed=False`
- `paperops_qctrl_raw_response_exposed=False`

Observed explicit flagged probe:

- `paperops_qctrl_enabled=True`
- `paperops_qctrl_provider_call_allowed=True`
- `paperops_qctrl_provider_call_attempted=True`
- `paperops_qctrl_provider_call_count=1`
- `paperops_qctrl_provider_call_succeeded=False`
- `paperops_qctrl_auth_status=provider_call_failed_sanitized`

The sanitized diagnostic for the failed provider call indicates that the
configured Q-CTRL identity does not currently have an active organization or
valid subscription for the Fire Opal product. The provider failure message
itself is not persisted in runtime artifacts.

Observed PaperOps cycle:

- `paper_ops_cycle_command_count=18`
- `paper_ops_cycle_command_passed_count=18`
- `paper_ops_cycle_command_failed_count=0`
- `paper_ops_cycle_status=paper_cycle_safe_blocked_pending_enablement`
- `paper_ops_cycle_qctrl_readiness_status=configured_package_importable`
- `paper_ops_cycle_qctrl_paper_consultation_status=disabled_pending_enablement`
- `paper_ops_cycle_qctrl_provider_call_count=0`
- `paper_ops_cycle_broker_post_called_count=0`
- `paper_ops_cycle_alpaca_post_called_count=0`
- `paper_ops_cycle_hard_safety_failure_count=0`

## Current State

PaperOps-Q implementation is complete, but full Q-CTRL paper consultation is not
operationally successful yet because product access is blocked at the Q-CTRL
account/subscription layer.

PaperOps remains safe to continue in paper-only mode. Full Paper Operational
Mode remains blocked by:

- `paper_operational_flag_disabled`
- `qctrl_paper_consultation_connected_not_ready`
- `external_alpaca_paper_post_enabled_not_ready`

The next code stage can proceed to PaperOps-2, while the Q-CTRL product-access
blocker remains an external/account setup item.
