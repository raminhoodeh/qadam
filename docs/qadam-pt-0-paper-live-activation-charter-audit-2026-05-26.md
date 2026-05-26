# Qadam PT-0 Paper-Live Activation Charter Audit

Date: 2026-05-26

## Scope

PT-0 records explicit Fund Manager approval for Qadam to operate against the
Alpaca paper account after later guarded PT gates pass.

This is not live-capital approval, not live-endpoint approval, and not an
immediate broker-submit instruction.

## Implementation

Implemented files:

- `orchestrator/paper_live_activation.py`
- `scripts/check_paper_live_activation.py`

Integrated surfaces:

- `orchestrator/paper_operational_readiness.py`
- `scripts/check_paper_operational_readiness.py`
- `scripts/run_paper_operational_cycle.py`
- `scripts/check_paper_operational_cycle.py`
- `orchestrator/cockpit_status.py`
- `scripts/check_cockpit_status.py`
- `docs/qadam-paper-operational-mode-plan.md`
- `docs/qadam-master-implementation-plan.md`

Runtime artifacts:

- `data/runtime/paper_live_activation.json`
- `data/runtime/paper_live_activation_history.jsonl`
- `data/runtime/paper_live_activation_events.jsonl`

## Recorded State

- `status=approved_pending_later_enablement`
- `approval_state=approved`
- `approval_scope=system_level_alpaca_paper_trading_only`
- `approval_logged=True`
- `paper_live_activation_approved=True`
- `paper_trading_system_approval_logged=True`
- `per_trade_manual_approval_required=False`
- `manual_trade_level_approval_required=False`
- `paper_live_mode=alpaca_paper_only`
- `broker_scope=alpaca_paper_account_only`
- `qctrl_consultation_required=True`

## Boundaries

PT-0 keeps these authorities false:

- `paper_order_submission_allowed=False`
- `live_capital_enabled=False`
- `live_endpoint_allowed=False`
- `live_credentials_loaded=False`
- `env_file_edited=False`
- `forced_trades_allowed=False`
- `phase7_proof_credit_allowed=False`
- `qctrl_direct_execution_allowed=False`
- `qctrl_broker_post_allowed=False`

Unsafe counters remain zero:

- `broker_post_called_count=0`
- `alpaca_post_called_count=0`
- `live_endpoint_called_count=0`

## Verification

Commands run:

```bash
.venv/bin/python scripts/check_paper_live_activation.py
.venv/bin/python scripts/check_paper_operational_readiness.py
.venv/bin/python scripts/check_paper_operational_cycle.py
.venv/bin/python scripts/check_paperops_30_day_operations.py
.venv/bin/python scripts/check_cockpit_status.py
.venv/bin/python -m compileall orchestrator/paper_live_activation.py orchestrator/paper_operational_readiness.py orchestrator/cockpit_status.py scripts/check_paper_live_activation.py scripts/check_paper_operational_readiness.py scripts/run_paper_operational_cycle.py scripts/check_paper_operational_cycle.py scripts/check_cockpit_status.py
.venv/bin/ruff check orchestrator/paper_live_activation.py orchestrator/paper_operational_readiness.py orchestrator/cockpit_status.py scripts/check_paper_live_activation.py scripts/check_paper_operational_readiness.py scripts/run_paper_operational_cycle.py scripts/check_paper_operational_cycle.py scripts/check_cockpit_status.py
```

Observed results:

- `paper_live_activation_check=ok`
- `paper_operational_readiness_check=ok`
- `paper_operational_cycle_contract_check=ok`
- `paperops_30_day_operations_check=ok`
- `cockpit_status_check=ok`
- PaperOps cycle command count is now `24/24`.
- PaperOps remains safe but blocked from full operation by
  `paper_operational_flag_disabled`,
  `qctrl_paper_consultation_connected_not_ready`,
  `external_alpaca_paper_post_enabled_not_ready`, and
  `paper_exit_path_connected_not_ready`.

## Next Stage

The next operational unblock is Q-CTRL product access for PaperOps-Q, followed
by explicit PaperOps-2 and PaperOps-4 enablement only after their guarded
prerequisites exist.
