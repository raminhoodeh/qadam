# Qadam PT-5 Alpaca Paper Submit Enablement Audit - 2026-05-26

## Scope

PT-5 enables the Alpaca paper-submit path for PaperOps through a recorded
runtime artifact. It does not edit `.env`, call Alpaca, submit paper orders,
enable live capital, force trades, expose credentials, or grant Phase 7 proof
credit.

## Implementation

- Added `orchestrator/paperops_alpaca_paper_submit_enablement.py`.
- Added `scripts/check_paperops_alpaca_paper_submit_enablement.py`.
- Updated PaperOps-2 so `paperops_alpaca_paper_post.py` can consume either the
  env flag or PT-5 runtime enablement.
- Updated PaperOps-2 to convert the PT-4 staged PaperOps paper order into an
  eligible Alpaca paper POST candidate. The crude-oil strategy lane maps to the
  paper-tradable proxy symbol `USO`; unmapped lanes remain blocked.
- Updated PaperOps readiness, the operational cycle, PaperOps-6, and cockpit
  public status so PT-5 is visible and counted in the PaperOps command chain.

## Current Runtime Evidence

- PT-5:
  - `status=enabled_pending_explicit_submit`
  - `alpaca_paper_submit_effective=True`
  - `settings_alpaca_paper_submit_enabled=False`
  - `runtime_artifact_override_enabled=True`
  - `paper_post_path_available=True`
  - `pt4_staged_order_count=1`
  - `broker_post_called_count=0`
  - `alpaca_post_called_count=0`
  - `live_endpoint_called_count=0`
- PaperOps-2:
  - `status=ready_pending_explicit_execute`
  - `runtime_alpaca_paper_submit_enabled=True`
  - `eligible_submit_record_count=1`
  - `selected_source_family=paperops_pt4_staged_order`
  - `alpaca_paper_post_called_count=0`
- PaperOps readiness:
  - `paper_ops_safe_to_continue_paper_only=True`
  - `paper_ops_full_paper_operational_ready=False`
  - blockers are now `qctrl_paper_consultation_connected_not_ready` and
    `paper_exit_path_connected_not_ready`.
- PaperOps cycle:
  - `paper_ops_cycle_check_command_count=29`
  - `paper_ops_cycle_check_command_passed_count=29`
  - `paper_ops_cycle_check_command_failed_count=0`
- PaperOps-6:
  - `paperops_30_day_operations_cycle_command_count=29`
  - `paperops_30_day_operations_cycle_command_failed_count=0`

## Verification Commands

```bash
.venv/bin/python scripts/check_paperops_alpaca_paper_submit_enablement.py
.venv/bin/python scripts/check_paperops_alpaca_paper_post.py
.venv/bin/python scripts/check_paper_operational_cycle.py
.venv/bin/python scripts/check_paperops_30_day_operations.py
.venv/bin/python scripts/check_paper_operational_readiness.py
.venv/bin/python scripts/check_cockpit_status.py
.venv/bin/python -m compileall orchestrator scripts
```

## Boundary

PT-5 and the default PaperOps-2 check do not submit to Alpaca. The actual broker
POST remains behind `scripts/check_paperops_alpaca_paper_post.py
--submit-paper-order`, paper endpoint classification, configured Alpaca paper
credentials, source Event Log prewrite, pre-trade snapshot, Phase 7-scoped
idempotency, and live-capital-disabled checks.
