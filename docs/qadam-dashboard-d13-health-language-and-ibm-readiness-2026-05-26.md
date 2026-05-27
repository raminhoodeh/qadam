# Qadam Dashboard D13 Health Language And IBM Readiness

Date: 2026-05-26

## Scope

D13 aligns the dashboard health language with the current paper-operational
state. The goal is not to force every subsystem to say `OK`; it is to separate
healthy core systems from waiting states, optional integrations, missing required
configuration, and deliberate safety blocks.

## Changes

- Updated canonical dashboard labels to `OK`, `Waiting`, `Optional`,
  `Not configured`, `Needs attention`, `Review only`, `Blocked`, and `Fault`.
- Treated optional feeds as non-blocking for the paper-trading core.
- Added a core source allowlist for the current paper mode.
- Rebuilt source metrics around `Core OK`, `Required not configured`,
  `Optional`, and `Optional not configured`.
- Updated PaperOps cycle acceptance so
  `paper_cycle_full_paper_operational_ready` is valid when blockers are zero.
- Updated IBM Quantum readiness acceptance so configured IBM credentials no
  longer look like the old missing-secret state.

## IBM Quantum Runtime Secret

The local `.env.local` file now carries the IBM Quantum runtime variables:

- `IBM_QUANTUM_TOKEN`
- `IBM_QUANTUM_INSTANCE`
- `QCTRL_ORGANIZATION_SLUG`

The file is Git-ignored and permissioned `600`. Public snapshots expose only
configured/not-configured state, never the token, CRN, or raw provider response.

## Current Result

- PaperOps cycle: `paper_cycle_full_paper_operational_ready`
- Q-CTRL paper consultation: ready, provider call recorded
- IBM Quantum readiness: `ready_for_explicit_device_probe`
- IBM readiness blocker: `explicit_device_probe_not_run`
- Hardware job submission: disabled
- Hardware scheduler: disabled
- Execution authority: disabled
- Paper order authority from quantum: disabled

## Remaining User-Controlled Step

Run the explicit device probe only when ready to make a provider discovery call:

```bash
set -a
source .env.local
set +a
.venv/bin/python scripts/check_qctrl_fire_opal_ibm_quantum.py --probe-devices
```

That probe discovers available IBM devices through Fire Opal but still cannot
submit a hardware job or create trade authority.

## Verification

- `.venv/bin/python scripts/check_paper_operational_cycle.py`
- `.venv/bin/python scripts/check_qctrl_fire_opal_ibm_quantum.py`
- `.venv/bin/python scripts/check_cockpit_status.py`
- `node scripts/check_dashboard_d11c_canonical_status_language.js`
- `node scripts/check_dashboard_d13_health_language.js`
- `node scripts/check_dashboard_acceptance.js`
