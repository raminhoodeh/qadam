#!/usr/bin/env python3
"""Run one safe PaperOps cycle.

This is the repeatable paper-only pass. It refreshes the Phase 7 paper proof
artifacts and Head-of-Quant diagnostics that can run without broker side
effects, then records a summary. It invokes the explicit Alpaca paper POST gate
in non-submit mode and does not pass the CLI flag that can submit a paper order.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402


PAPER_OPS_CYCLE_SCHEMA_VERSION = 1
PAPER_OPS_CYCLE_RUNTIME_ARTIFACT = "paper_operational_cycle.json"
PAPER_OPS_CYCLE_HISTORY = "paper_operational_cycle_history.jsonl"
PAPER_OPS_CYCLE_EVENT_LOG = "paper_operational_cycle_events.jsonl"
PAPER_OPS_CYCLE_EVENT_TYPE = "paper_operational_cycle_recorded"
PAPER_OPS_CYCLE_COMPONENT = "paper_operational_cycle"

COMMANDS: tuple[tuple[str, str, bool], ...] = (
    ("strategy_research_intake", "scripts/check_strategy_research_intake.py", True),
    ("paper_live_activation", "scripts/check_paper_live_activation.py", True),
    (
        "paper_live_qctrl_product_access",
        "scripts/check_paper_live_qctrl_product_access.py",
        True,
    ),
    ("paper_operational_mode", "scripts/check_paper_operational_mode.py", True),
    ("quantum_provider_readiness", "scripts/check_quantum_provider_readiness.py", True),
    ("head_of_quant_oracle", "scripts/check_quantum_oracle.py", True),
    ("paperops_qctrl_consultation", "scripts/check_paperops_qctrl_consultation.py", True),
    ("phase7_demo_run", "scripts/check_phase7_demo_proof_run.py", True),
    ("phase7_qualified_setups", "scripts/check_phase7_qualified_setup_ledger.py", True),
    (
        "paperops_qualified_setup_production",
        "scripts/check_paperops_qualified_setup_production.py",
        True,
    ),
    (
        "paperops_auto_approval_staged_order",
        "scripts/check_paperops_auto_approval_staged_order.py",
        True,
    ),
    (
        "paperops_alpaca_paper_submit_enablement",
        "scripts/check_paperops_alpaca_paper_submit_enablement.py",
        True,
    ),
    ("phase7_auto_approval", "scripts/check_phase7_test_mode_auto_approval_router.py", True),
    ("phase7_order_staging", "scripts/check_phase7_proof_order_staging.py", True),
    ("phase7_guarded_paper_submit", "scripts/check_phase7_guarded_alpaca_paper_submit.py", True),
    ("paperops_alpaca_paper_post", "scripts/check_paperops_alpaca_paper_post.py", True),
    (
        "paperops_paper_lifecycle_polling_enablement",
        "scripts/check_paperops_paper_lifecycle_polling_enablement.py",
        True,
    ),
    ("paperops_paper_lifecycle_poller", "scripts/check_paperops_paper_lifecycle_poller.py", True),
    (
        "paperops_guarded_paper_exit_enablement",
        "scripts/check_paperops_guarded_paper_exit_enablement.py",
        True,
    ),
    ("paperops_paper_exit_path", "scripts/check_paperops_paper_exit_path.py", True),
    ("paperops_notification_review", "scripts/check_paperops_notification_review.py", True),
    ("phase7_lifecycle", "scripts/check_phase7_proof_lifecycle_monitor.py", True),
    ("phase7_postmortem", "scripts/check_phase7_proof_postmortem_contract.py", True),
    ("phase7_performance", "scripts/check_phase7_performance_evaluator.py", True),
    ("phase7_drawdown", "scripts/check_phase7_drawdown_risk_sentinel.py", True),
    ("phase7_override", "scripts/check_phase7_override_detector.py", True),
    ("phase7_signal_funnel", "scripts/check_phase7_signal_funnel_evidence.py", True),
    ("phase7_maturity", "scripts/check_phase7_maturity_tracker.py", True),
    ("phase7_cockpit_visibility", "scripts/check_phase7_cockpit_visibility.py", True),
    ("paperops_30_day_operations", "scripts/check_paperops_30_day_operations.py", True),
    ("paper_ops_readiness", "scripts/check_paper_operational_readiness.py", True),
)

PAPER_OPS_CYCLE_BOUNDARY = (
    "PaperOps-1 runs the current paper-only operational pass without broker "
    "side effects. It may refresh Q7 paper proof artifacts and readiness state, "
    "and it may evaluate the explicit Alpaca paper POST gate only in non-submit "
    "mode. PT-6 may invoke read-only Alpaca paper lifecycle polling only for "
    "orders PaperOps-2 has successfully submitted, while the standalone "
    "PaperOps-3 checker remains in non-poll mode. The PaperOps-4 exit path "
    "may consume PT-7 guarded paper-exit runtime enablement, but still runs "
    "only in non-exit mode. PaperOps-5 may render "
    "notification review records only; it cannot send live Telegram messages "
    "or accept Telegram commands. PaperOps-6 may verify scheduler binding for "
    "the active 30-day paper run only. The cycle cannot pass the paper-submit, "
    "paper-poll, or paper-exit CLI flags, cannot call live broker endpoints, "
    "cannot write prediction-market or crypto-perps orders, cannot enable live "
    "capital, and cannot promote the system to live money."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings) -> Path:
    return Path(settings.runtime_dir)


def _paths(settings: Settings) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_OPS_CYCLE_RUNTIME_ARTIFACT,
        runtime / PAPER_OPS_CYCLE_HISTORY,
        runtime / PAPER_OPS_CYCLE_EVENT_LOG,
    )


def _parse_output(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _run_command(label: str, script: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    parsed = _parse_output(stdout)
    return {
        "label": label,
        "script": script,
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "parsed": parsed,
        "stdout_tail": stdout.splitlines()[-12:],
        "stderr_tail": stderr.splitlines()[-12:],
    }


def recommended_next_stage(
    *,
    safe_to_continue: bool,
    blockers: list[str],
) -> str:
    if not safe_to_continue:
        return "Fix failed PaperOps command or hard safety failure"
    if (
        "global_paper_operational_mode_enabled_not_ready" in blockers
        or "paper_operational_flag_disabled" in blockers
    ):
        return "PT-2 global PaperOps runtime mode enablement"
    if "paperops_auto_approval_staged_order_connected_not_ready" in blockers:
        return "PT-4 auto-approval and staged paper-order handoff"
    if "alpaca_paper_submit_runtime_enablement_connected_not_ready" in blockers:
        return "PT-5 Alpaca paper-submit runtime enablement"
    if "qctrl_paper_consultation_connected_not_ready" in blockers:
        return "Resolve PaperOps-Q Q-CTRL product access for successful paper consultation"
    if "external_alpaca_paper_post_enabled_not_ready" in blockers:
        return "PaperOps-2 explicit Alpaca paper POST gate"
    return "PaperOps-4 paper exit path"


def build_paper_operational_cycle(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    command_records = [
        _run_command(label, script)
        for label, script, enabled in COMMANDS
        if enabled
    ]
    failed = [record for record in command_records if not record["ok"]]
    readiness = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paper_ops_readiness"
        ),
        {},
    )
    operations = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_30_day_operations"
        ),
        {},
    )
    paper_live_activation = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paper_live_activation"
        ),
        {},
    )
    paper_live_qctrl_product_access = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paper_live_qctrl_product_access"
        ),
        {},
    )
    paper_operational_mode = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paper_operational_mode"
        ),
        {},
    )
    qualified_setup_production = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_qualified_setup_production"
        ),
        {},
    )
    auto_approval_staged_order = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_auto_approval_staged_order"
        ),
        {},
    )
    alpaca_submit_enablement = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_alpaca_paper_submit_enablement"
        ),
        {},
    )
    lifecycle_polling_enablement = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_paper_lifecycle_polling_enablement"
        ),
        {},
    )
    guarded_exit_enablement = next(
        (
            record["parsed"]
            for record in command_records
            if record["label"] == "paperops_guarded_paper_exit_enablement"
        ),
        {},
    )
    unsafe_counter_total = sum(
        int(readiness.get(key, "0") or 0)
        for key in (
            "paper_ops_broker_post_called_count",
            "paper_ops_alpaca_post_called_count",
            "paper_ops_alpaca_paper_post_live_endpoint_called_count",
            "paper_ops_lifecycle_poller_broker_post_called_count",
            "paper_ops_lifecycle_poller_live_endpoint_called_count",
            "paper_ops_exit_path_broker_post_called_count",
            "paper_ops_exit_path_order_cancel_called_count",
            "paper_ops_exit_path_position_resize_called_count",
            "paper_ops_exit_path_live_endpoint_called_count",
            "paper_ops_notification_review_live_send_allowed_count",
            "paper_ops_notification_review_command_path_enabled_count",
            "paper_ops_notification_review_broker_write_allowed_count",
            "paper_ops_notification_review_paper_order_allowed_count",
            "paper_ops_notification_review_position_close_allowed_count",
            "paper_ops_notification_review_live_endpoint_allowed_count",
            "paper_ops_paper_live_activation_broker_post_called_count",
            "paper_ops_paper_live_activation_alpaca_post_called_count",
            "paper_ops_paper_live_activation_live_endpoint_called_count",
            "paper_ops_paper_live_qctrl_broker_post_called_count",
            "paper_ops_paper_live_qctrl_alpaca_post_called_count",
            "paper_ops_paper_live_qctrl_live_endpoint_called_count",
            "paper_ops_paper_operational_mode_broker_post_called_count",
            "paper_ops_qualified_setup_production_broker_post_called_count",
            "paper_ops_qualified_setup_production_unsafe_write_counter_total",
            "paper_ops_auto_approval_staged_order_broker_post_called_count",
            "paper_ops_auto_approval_staged_order_live_endpoint_called_count",
            "paper_ops_auto_approval_staged_order_unsafe_write_counter_total",
            "paper_ops_alpaca_submit_enablement_broker_post_called_count",
            "paper_ops_alpaca_submit_enablement_alpaca_post_called_count",
            "paper_ops_alpaca_submit_enablement_live_endpoint_called_count",
            "paper_ops_lifecycle_polling_enablement_broker_get_called_count",
            "paper_ops_lifecycle_polling_enablement_live_endpoint_called_count",
            "paper_ops_exit_runtime_enablement_close_called_count",
            "paper_ops_exit_runtime_enablement_live_endpoint_called_count",
        )
    ) + int(operations.get("paperops_30_day_operations_unsafe_write_counter_total", "0") or 0)
    safe_to_continue = readiness.get("paper_ops_safe_to_continue_paper_only") == "True"
    full_ready = readiness.get("paper_ops_full_paper_operational_ready") == "True"
    status = "paper_cycle_ok"
    if failed:
        status = "paper_cycle_failed"
    elif safe_to_continue and not full_ready:
        status = "paper_cycle_safe_blocked_pending_enablement"
    elif full_ready:
        status = "paper_cycle_full_paper_operational_ready"

    return {
        "schema_version": PAPER_OPS_CYCLE_SCHEMA_VERSION,
        "artifact_type": "paper_operational_cycle",
        "artifact_id": "paperops:cycle:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-1",
        "status": status,
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "paper_operational_enabled": (
            readiness.get("paper_ops_enabled") == "True"
            or settings.paper_operational_enabled
        ),
        "settings_paper_operational_enabled": settings.paper_operational_enabled,
        "paper_operational_mode_status": paper_operational_mode.get(
            "paper_operational_mode_status"
        ),
        "paper_operational_mode_enabled": (
            paper_operational_mode.get("paper_operational_mode_enabled") == "True"
        ),
        "paper_operational_mode_effective": (
            paper_operational_mode.get("paper_operational_mode_effective") == "True"
        ),
        "paper_operational_mode_settings_flag": (
            paper_operational_mode.get("paper_operational_mode_settings_flag") == "True"
        ),
        "paper_operational_mode_runtime_artifact_override_enabled": (
            paper_operational_mode.get(
                "paper_operational_mode_runtime_artifact_override_enabled"
            )
            == "True"
        ),
        "paper_operational_mode_flag_disabled": (
            paper_operational_mode.get("paper_operational_mode_flag_disabled") == "True"
        ),
        "paper_operational_mode_env_file_edited": (
            paper_operational_mode.get("paper_operational_mode_env_file_edited")
            == "True"
        ),
        "paper_operational_mode_paper_order_submission_allowed": (
            paper_operational_mode.get(
                "paper_operational_mode_paper_order_submission_allowed"
            )
            == "True"
        ),
        "paper_operational_mode_broker_post_called_count": int(
            paper_operational_mode.get(
                "paper_operational_mode_broker_post_called_count",
                "0",
            )
            or 0
        ),
        "paper_operational_mode_alpaca_post_called_count": int(
            paper_operational_mode.get(
                "paper_operational_mode_alpaca_post_called_count",
                "0",
            )
            or 0
        ),
        "paper_operational_mode_live_endpoint_called_count": int(
            paper_operational_mode.get(
                "paper_operational_mode_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "paper_operational_mode_live_capital_enabled": (
            paper_operational_mode.get("paper_operational_mode_live_capital_enabled")
            == "True"
        ),
        "paper_operational_mode_qctrl_direct_execution_allowed": (
            paper_operational_mode.get(
                "paper_operational_mode_qctrl_direct_execution_allowed"
            )
            == "True"
        ),
        "paper_operational_mode_qctrl_broker_post_allowed": (
            paper_operational_mode.get("paper_operational_mode_qctrl_broker_post_allowed")
            == "True"
        ),
        "paper_operational_mode_phase7_proof_credit_allowed": (
            paper_operational_mode.get(
                "paper_operational_mode_phase7_proof_credit_allowed"
            )
            == "True"
        ),
        "paper_operational_mode_forced_trades_allowed": (
            paper_operational_mode.get("paper_operational_mode_forced_trades_allowed")
            == "True"
        ),
        "paper_operational_mode_qctrl_product_access_blocker": (
            paper_operational_mode.get(
                "paper_operational_mode_qctrl_product_access_blocker"
            )
        ),
        "qualified_setup_production_status": qualified_setup_production.get(
            "paperops_qualified_setup_status"
        ),
        "qualified_setup_production_path_ready": (
            qualified_setup_production.get("paperops_qualified_setup_path_ready")
            == "True"
        ),
        "qualified_setup_production_candidate_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_production_candidate_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_qualified_setup_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_qualified_setup_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_ready_to_stage_q7_order": (
            qualified_setup_production.get(
                "paperops_qualified_setup_ready_to_stage_q7_order"
            )
            == "True"
        ),
        "qualified_setup_production_phase7_demo_qualified_setup_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_phase7_demo_qualified_setup_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_q7_ledger_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_q7_ledger_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_qctrl_status": qualified_setup_production.get(
            "paperops_qualified_setup_qctrl_paper_consultation_status"
        ),
        "qualified_setup_production_qctrl_connected": (
            qualified_setup_production.get(
                "paperops_qualified_setup_qctrl_paper_consultation_connected"
            )
            == "True"
        ),
        "qualified_setup_production_broker_post_called_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_broker_post_called_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_live_endpoint_called_count": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "qualified_setup_production_unsafe_write_counter_total": int(
            qualified_setup_production.get(
                "paperops_qualified_setup_unsafe_write_counter_total",
                "0",
            )
            or 0
        ),
        "auto_approval_staged_order_status": auto_approval_staged_order.get(
            "paperops_auto_approval_staged_order_status"
        ),
        "auto_approval_staged_order_source_pt3_status": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_source_pt3_status"
            )
        ),
        "auto_approval_staged_order_source_pt3_path_ready": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_source_pt3_path_ready"
            )
            == "True"
        ),
        "auto_approval_staged_order_auto_approved_setup_count": int(
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_auto_approved_setup_count",
                "0",
            )
            or 0
        ),
        "auto_approval_staged_order_staged_order_count": int(
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_staged_order_count",
                "0",
            )
            or 0
        ),
        "auto_approval_staged_order_ready_for_paperops2_submit": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_ready_for_paperops2_submit"
            )
            == "True"
        ),
        "auto_approval_staged_order_q7_source_ledger_mutation_performed": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_q7_source_ledger_mutation_performed"
            )
            == "True"
        ),
        "auto_approval_staged_order_paper_order_submission_allowed": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_paper_order_submission_allowed"
            )
            == "True"
        ),
        "auto_approval_staged_order_broker_post_called_count": int(
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_broker_post_called_count",
                "0",
            )
            or 0
        ),
        "auto_approval_staged_order_live_endpoint_called_count": int(
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "auto_approval_staged_order_phase7_proof_credit_allowed": (
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_phase7_proof_credit_allowed"
            )
            == "True"
        ),
        "auto_approval_staged_order_unsafe_write_counter_total": int(
            auto_approval_staged_order.get(
                "paperops_auto_approval_staged_order_unsafe_write_counter_total",
                "0",
            )
            or 0
        ),
        "alpaca_submit_enablement_status": alpaca_submit_enablement.get(
            "paperops_alpaca_submit_enablement_status"
        ),
        "alpaca_submit_enablement_effective": (
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_effective"
            )
            == "True"
        ),
        "alpaca_submit_enablement_path_available": (
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_path_available"
            )
            == "True"
        ),
        "alpaca_submit_enablement_pt4_staged_order_count": int(
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_pt4_staged_order_count",
                "0",
            )
            or 0
        ),
        "alpaca_submit_enablement_broker_post_called_count": int(
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_broker_post_called_count",
                "0",
            )
            or 0
        ),
        "alpaca_submit_enablement_alpaca_post_called_count": int(
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_alpaca_post_called_count",
                "0",
            )
            or 0
        ),
        "alpaca_submit_enablement_live_endpoint_called_count": int(
            alpaca_submit_enablement.get(
                "paperops_alpaca_submit_enablement_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "lifecycle_polling_enablement_status": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_status"
            )
        ),
        "lifecycle_polling_enablement_active": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_active"
            )
            == "True"
        ),
        "lifecycle_polling_enablement_effective": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_effective"
            )
            == "True"
        ),
        "lifecycle_polling_enablement_path_available": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_path_available"
            )
            == "True"
        ),
        "lifecycle_polling_enablement_idle_until_submitted_order": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_idle_until_submitted_order"
            )
            == "True"
        ),
        "lifecycle_polling_enablement_paperops2_submitted_order_count": int(
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_paperops2_submitted_order_count",
                "0",
            )
            or 0
        ),
        "lifecycle_polling_enablement_broker_get_allowed": (
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_broker_get_allowed"
            )
            == "True"
        ),
        "lifecycle_polling_enablement_broker_get_called_count": int(
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_broker_get_called_count",
                "0",
            )
            or 0
        ),
        "lifecycle_polling_enablement_poller_order_poll_called_count": int(
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_poller_order_poll_called_count",
                "0",
            )
            or 0
        ),
        "lifecycle_polling_enablement_poller_broker_get_called_count": int(
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_poller_broker_get_called_count",
                "0",
            )
            or 0
        ),
        "lifecycle_polling_enablement_live_endpoint_called_count": int(
            lifecycle_polling_enablement.get(
                "paperops_lifecycle_polling_enablement_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "guarded_exit_enablement_status": guarded_exit_enablement.get(
            "paperops_guarded_exit_enablement_status"
        ),
        "guarded_exit_enablement_enabled": (
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_enabled"
            )
            == "True"
        ),
        "guarded_exit_enablement_effective": (
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_effective"
            )
            == "True"
        ),
        "guarded_exit_enablement_runtime_override": (
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_runtime_override"
            )
            == "True"
        ),
        "guarded_exit_enablement_path_available": (
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_path_available"
            )
            == "True"
        ),
        "guarded_exit_enablement_idle_until_open_position": (
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_idle_until_open_position"
            )
            == "True"
        ),
        "guarded_exit_enablement_open_position_count": int(
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_paperops3_open_position_count",
                "0",
            )
            or 0
        ),
        "guarded_exit_enablement_close_called_count": int(
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_close_called_count",
                "0",
            )
            or 0
        ),
        "guarded_exit_enablement_live_endpoint_called_count": int(
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "guarded_exit_enablement_unsafe_write_counter_total": int(
            guarded_exit_enablement.get(
                "paperops_guarded_exit_enablement_unsafe_write_counter_total",
                "0",
            )
            or 0
        ),
        "alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "quantum_paper_parity_required": settings.quantum_paper_parity_required,
        "qctrl_paper_consultation_enabled": settings.qctrl_paper_consultation_enabled,
        "live_capital_enabled": settings.live_capital_enabled,
        "paper_live_activation_status": paper_live_activation.get(
            "paper_live_activation_status"
        ),
        "paper_live_activation_approved": (
            paper_live_activation.get("paper_live_activation_approved") == "True"
        ),
        "paper_live_activation_system_approval_logged": (
            paper_live_activation.get("paper_live_activation_system_approval_logged")
            == "True"
        ),
        "paper_live_activation_per_trade_manual_approval_required": (
            paper_live_activation.get(
                "paper_live_activation_per_trade_manual_approval_required"
            )
            == "True"
        ),
        "paper_live_activation_paper_order_submission_allowed": (
            paper_live_activation.get(
                "paper_live_activation_paper_order_submission_allowed"
            )
            == "True"
        ),
        "paper_live_activation_forced_trades_allowed": (
            paper_live_activation.get("paper_live_activation_forced_trades_allowed")
            == "True"
        ),
        "paper_live_activation_qctrl_consultation_required": (
            paper_live_activation.get(
                "paper_live_activation_qctrl_consultation_required"
            )
            == "True"
        ),
        "paper_live_activation_qctrl_direct_execution_allowed": (
            paper_live_activation.get(
                "paper_live_activation_qctrl_direct_execution_allowed"
            )
            == "True"
        ),
        "paper_live_activation_broker_post_called_count": int(
            paper_live_activation.get(
                "paper_live_activation_broker_post_called_count",
                "0",
            )
            or 0
        ),
        "paper_live_activation_alpaca_post_called_count": int(
            paper_live_activation.get(
                "paper_live_activation_alpaca_post_called_count",
                "0",
            )
            or 0
        ),
        "paper_live_activation_live_endpoint_called_count": int(
            paper_live_activation.get(
                "paper_live_activation_live_endpoint_called_count",
                "0",
            )
            or 0
        ),
        "paper_live_activation_max_order_notional_gbp": int(
            paper_live_activation.get(
                "paper_live_activation_max_order_notional_gbp",
                "0",
            )
            or 0
        ),
        "paper_live_qctrl_product_access_status": paper_live_qctrl_product_access.get(
            "paper_live_qctrl_product_access_status"
        ),
        "paper_live_qctrl_product_access_state": paper_live_qctrl_product_access.get(
            "paper_live_qctrl_product_access_product_access_state"
        ),
        "paper_live_qctrl_product_access_verified": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_verified"
            )
            == "True"
        ),
        "paper_live_qctrl_consultation_ready": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_paper_consultation_ready"
            )
            == "True"
        ),
        "paper_live_qctrl_provider_call_attempted": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_provider_call_attempted"
            )
            == "True"
        ),
        "paper_live_qctrl_provider_call_succeeded": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_provider_call_succeeded"
            )
            == "True"
        ),
        "paper_live_qctrl_provider_call_count": int(
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_provider_call_count",
                "0",
            )
            or 0
        ),
        "paper_live_qctrl_product_access_blocker": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_blocker"
            )
        ),
        "paper_live_qctrl_execution_allowed": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_execution_allowed"
            )
            == "True"
        ),
        "paper_live_qctrl_paper_order_allowed": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_paper_order_allowed"
            )
            == "True"
        ),
        "paper_live_qctrl_broker_post_allowed": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_broker_post_allowed"
            )
            == "True"
        ),
        "paper_live_qctrl_live_capital_enabled": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_live_capital_enabled"
            )
            == "True"
        ),
        "paper_live_qctrl_phase7_proof_credit_allowed": (
            paper_live_qctrl_product_access.get(
                "paper_live_qctrl_product_access_phase7_proof_credit_allowed"
            )
            == "True"
        ),
        "paper_live_qctrl_broker_post_called_count": int(
            readiness.get("paper_ops_paper_live_qctrl_broker_post_called_count", "0")
            or 0
        ),
        "paper_live_qctrl_alpaca_post_called_count": int(
            readiness.get("paper_ops_paper_live_qctrl_alpaca_post_called_count", "0")
            or 0
        ),
        "paper_live_qctrl_live_endpoint_called_count": int(
            readiness.get("paper_ops_paper_live_qctrl_live_endpoint_called_count", "0")
            or 0
        ),
        "safe_to_continue_paper_only": safe_to_continue,
        "full_paper_operational_ready": full_ready,
        "command_count": len(command_records),
        "command_passed_count": len(command_records) - len(failed),
        "command_failed_count": len(failed),
        "failed_commands": [record["label"] for record in failed],
        "command_records": command_records,
        "phase7_run_state": readiness.get("paper_ops_phase7_run_state"),
        "phase7_active_day_number": readiness.get("paper_ops_phase7_active_day_number"),
        "qualified_setup_count": int(readiness.get("paper_ops_qualified_setup_count", "0") or 0),
        "submitted_paper_order_count": int(
            readiness.get("paper_ops_submitted_paper_order_count", "0") or 0
        ),
        "closed_proof_trade_count": int(readiness.get("paper_ops_closed_proof_trade_count", "0") or 0),
        "broker_post_called_count": int(readiness.get("paper_ops_broker_post_called_count", "0") or 0),
        "alpaca_post_called_count": int(readiness.get("paper_ops_alpaca_post_called_count", "0") or 0),
        "alpaca_paper_post_gate_status": readiness.get(
            "paper_ops_alpaca_paper_post_gate_status"
        ),
        "alpaca_paper_post_path_available": (
            readiness.get("paper_ops_alpaca_paper_post_path_available") == "True"
        ),
        "alpaca_paper_post_eligible_submit_record_count": int(
            readiness.get("paper_ops_alpaca_paper_post_eligible_submit_record_count", "0")
            or 0
        ),
        "alpaca_paper_post_called_count": int(
            readiness.get("paper_ops_alpaca_paper_post_called_count", "0") or 0
        ),
        "alpaca_paper_post_succeeded_count": int(
            readiness.get("paper_ops_alpaca_paper_post_succeeded_count", "0") or 0
        ),
        "alpaca_paper_post_live_endpoint_called_count": int(
            readiness.get("paper_ops_alpaca_paper_post_live_endpoint_called_count", "0")
            or 0
        ),
        "paper_lifecycle_poller_status": readiness.get("paper_ops_lifecycle_poller_status"),
        "paper_lifecycle_poller_source_submitted_paper_order_count": int(
            readiness.get("paper_ops_lifecycle_poller_source_submitted_order_count", "0")
            or 0
        ),
        "paper_lifecycle_poller_poll_candidate_count": int(
            readiness.get("paper_ops_lifecycle_poller_poll_candidate_count", "0") or 0
        ),
        "paper_lifecycle_poller_order_poll_called_count": int(
            readiness.get("paper_ops_lifecycle_poller_order_poll_called_count", "0") or 0
        ),
        "paper_lifecycle_poller_position_poll_called_count": int(
            readiness.get("paper_ops_lifecycle_poller_position_poll_called_count", "0") or 0
        ),
        "paper_lifecycle_poller_broker_get_called_count": int(
            readiness.get("paper_ops_lifecycle_poller_broker_get_called_count", "0") or 0
        ),
        "paper_lifecycle_poller_broker_post_called_count": int(
            readiness.get("paper_ops_lifecycle_poller_broker_post_called_count", "0") or 0
        ),
        "paper_lifecycle_poller_live_endpoint_called_count": int(
            readiness.get("paper_ops_lifecycle_poller_live_endpoint_called_count", "0") or 0
        ),
        "paper_exit_path_status": readiness.get("paper_ops_exit_path_status"),
        "paper_exit_path_enabled": readiness.get("paper_ops_exit_path_enabled") == "True",
        "paper_exit_path_available": readiness.get("paper_ops_exit_path_available") == "True",
        "paper_exit_path_open_position_readback_count": int(
            readiness.get("paper_ops_exit_path_open_position_readback_count", "0") or 0
        ),
        "paper_exit_path_eligible_exit_record_count": int(
            readiness.get("paper_ops_exit_path_eligible_exit_record_count", "0") or 0
        ),
        "paper_exit_path_close_called_count": int(
            readiness.get("paper_ops_exit_path_close_called_count", "0") or 0
        ),
        "paper_exit_path_broker_write_called_count": int(
            readiness.get("paper_ops_exit_path_broker_write_called_count", "0") or 0
        ),
        "paper_exit_path_broker_post_called_count": int(
            readiness.get("paper_ops_exit_path_broker_post_called_count", "0") or 0
        ),
        "paper_exit_path_order_cancel_called_count": int(
            readiness.get("paper_ops_exit_path_order_cancel_called_count", "0") or 0
        ),
        "paper_exit_path_position_resize_called_count": int(
            readiness.get("paper_ops_exit_path_position_resize_called_count", "0") or 0
        ),
        "paper_exit_path_live_endpoint_called_count": int(
            readiness.get("paper_ops_exit_path_live_endpoint_called_count", "0") or 0
        ),
        "notification_review_status": readiness.get("paper_ops_notification_review_status"),
        "notification_review_record_count": int(
            readiness.get("paper_ops_notification_review_record_count", "0") or 0
        ),
        "notification_review_lifecycle_type_count": int(
            readiness.get("paper_ops_notification_review_lifecycle_type_count", "0") or 0
        ),
        "notification_review_eligible_review_count": int(
            readiness.get("paper_ops_notification_review_eligible_review_count", "0") or 0
        ),
        "notification_review_send_gate": readiness.get(
            "paper_ops_notification_review_send_gate"
        ),
        "notification_review_send_test_gate_state": readiness.get(
            "paper_ops_notification_review_send_test_gate_state"
        ),
        "notification_review_live_send_allowed_count": int(
            readiness.get("paper_ops_notification_review_live_send_allowed_count", "0")
            or 0
        ),
        "notification_review_command_path_enabled_count": int(
            readiness.get("paper_ops_notification_review_command_path_enabled_count", "0")
            or 0
        ),
        "notification_review_broker_write_allowed_count": int(
            readiness.get("paper_ops_notification_review_broker_write_allowed_count", "0")
            or 0
        ),
        "notification_review_paper_order_allowed_count": int(
            readiness.get("paper_ops_notification_review_paper_order_allowed_count", "0")
            or 0
        ),
        "notification_review_position_close_allowed_count": int(
            readiness.get("paper_ops_notification_review_position_close_allowed_count", "0")
            or 0
        ),
        "notification_review_live_endpoint_allowed_count": int(
            readiness.get("paper_ops_notification_review_live_endpoint_allowed_count", "0")
            or 0
        ),
        "paperops_30_day_operations_status": operations.get(
            "paperops_30_day_operations_status"
        ),
        "paperops_30_day_operations_scheduler_status": operations.get(
            "paperops_30_day_operations_scheduler_status"
        ),
        "paperops_30_day_operations_automation_active": (
            operations.get("paperops_30_day_operations_automation_active") == "True"
        ),
        "paperops_30_day_operations_automation_prompt_paperops_bound": (
            operations.get(
                "paperops_30_day_operations_automation_prompt_paperops_bound"
            )
            == "True"
        ),
        "paperops_30_day_operations_active_day_number": operations.get(
            "paperops_30_day_operations_active_day_number"
        ),
        "paperops_30_day_operations_completed_calendar_day_count": int(
            operations.get("paperops_30_day_operations_completed_calendar_day_count", "0")
            or 0
        ),
        "paperops_30_day_operations_calendar_days_remaining": int(
            operations.get("paperops_30_day_operations_calendar_days_remaining", "0") or 0
        ),
        "paperops_30_day_operations_cycle_command_count": int(
            operations.get("paperops_30_day_operations_cycle_command_count", "0") or 0
        ),
        "paperops_30_day_operations_dashboard_mirror_status": operations.get(
            "paperops_30_day_operations_dashboard_mirror_status"
        ),
        "paperops_30_day_operations_dashboard_mirror_public_safe": (
            operations.get("paperops_30_day_operations_dashboard_mirror_public_safe")
            == "True"
        ),
        "paperops_30_day_operations_unsafe_write_counter_total": int(
            operations.get("paperops_30_day_operations_unsafe_write_counter_total", "0")
            or 0
        ),
        "head_of_quant_oracle_result_count": int(
            readiness.get("paper_ops_head_of_quant_oracle_result_count", "0") or 0
        ),
        "head_of_quant_latest_backend": readiness.get("paper_ops_head_of_quant_latest_backend"),
        "qctrl_readiness_status": readiness.get("paper_ops_qctrl_readiness_status"),
        "qctrl_paper_consultation_status": readiness.get(
            "paper_ops_qctrl_paper_consultation_status"
        ),
        "qctrl_paper_consultation_provider_call_recorded": (
            readiness.get("paper_ops_qctrl_paper_consultation_provider_call_recorded") == "True"
        ),
        "qctrl_provider_call_count": int(
            readiness.get("paper_ops_qctrl_provider_call_count", "0") or 0
        ),
        "unsafe_write_counter_total": unsafe_counter_total,
        "blocker_count": int(readiness.get("paper_ops_blocker_count", "0") or 0),
        "blockers": [
            item
            for item in readiness.get("paper_ops_blockers", "").split(",")
            if item
        ],
        "hard_safety_failure_count": int(
            readiness.get("paper_ops_hard_safety_failure_count", "0") or 0
        ),
        "recommended_next_stage": recommended_next_stage(
            safe_to_continue=safe_to_continue,
            blockers=[
                item
                for item in readiness.get("paper_ops_blockers", "").split(",")
                if item
            ],
        ),
        "boundary": PAPER_OPS_CYCLE_BOUNDARY,
    }


def validate_paper_operational_cycle(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != PAPER_OPS_CYCLE_SCHEMA_VERSION:
        errors.append("paper_ops_cycle_schema_version_mismatch")
    if artifact.get("artifact_type") != "paper_operational_cycle":
        errors.append("paper_ops_cycle_artifact_type_mismatch")
    if artifact.get("stage") != "PaperOps-1":
        errors.append("paper_ops_cycle_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paper_ops_cycle_mode_not_paper")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paper_ops_cycle_live_capital_enabled")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "alpaca_paper_post_live_endpoint_called_count",
        "paper_lifecycle_poller_broker_post_called_count",
        "paper_lifecycle_poller_live_endpoint_called_count",
        "paper_exit_path_broker_post_called_count",
        "paper_exit_path_order_cancel_called_count",
        "paper_exit_path_position_resize_called_count",
        "paper_exit_path_live_endpoint_called_count",
        "notification_review_live_send_allowed_count",
        "notification_review_command_path_enabled_count",
        "notification_review_broker_write_allowed_count",
        "notification_review_paper_order_allowed_count",
        "notification_review_position_close_allowed_count",
        "notification_review_live_endpoint_allowed_count",
        "paperops_30_day_operations_unsafe_write_counter_total",
        "paper_live_activation_broker_post_called_count",
        "paper_live_activation_alpaca_post_called_count",
        "paper_live_activation_live_endpoint_called_count",
        "paper_live_qctrl_broker_post_called_count",
        "paper_live_qctrl_alpaca_post_called_count",
        "paper_live_qctrl_live_endpoint_called_count",
        "paper_operational_mode_broker_post_called_count",
        "paper_operational_mode_alpaca_post_called_count",
        "paper_operational_mode_live_endpoint_called_count",
        "qualified_setup_production_broker_post_called_count",
        "qualified_setup_production_live_endpoint_called_count",
        "qualified_setup_production_unsafe_write_counter_total",
        "auto_approval_staged_order_broker_post_called_count",
        "auto_approval_staged_order_live_endpoint_called_count",
        "auto_approval_staged_order_unsafe_write_counter_total",
        "alpaca_submit_enablement_broker_post_called_count",
        "alpaca_submit_enablement_alpaca_post_called_count",
        "alpaca_submit_enablement_live_endpoint_called_count",
        "lifecycle_polling_enablement_live_endpoint_called_count",
        "guarded_exit_enablement_close_called_count",
        "guarded_exit_enablement_live_endpoint_called_count",
        "guarded_exit_enablement_unsafe_write_counter_total",
        "unsafe_write_counter_total",
    ):
        try:
            value = int(artifact.get(key, 0) or 0)
        except (TypeError, ValueError):
            value = 1
        if value != 0:
            errors.append(f"paper_ops_cycle_unsafe_counter_nonzero:{key}")
    if artifact.get("paper_live_activation_status") != "approved_pending_later_enablement":
        errors.append("paper_ops_cycle_paper_live_activation_not_approved")
    if artifact.get("paper_live_activation_approved") is not True:
        errors.append("paper_ops_cycle_paper_live_activation_approved_false")
    if artifact.get("paper_live_activation_system_approval_logged") is not True:
        errors.append("paper_ops_cycle_paper_live_activation_system_approval_missing")
    if artifact.get("paper_live_activation_per_trade_manual_approval_required") is not False:
        errors.append("paper_ops_cycle_paper_live_activation_manual_approval_required")
    if artifact.get("paper_live_activation_paper_order_submission_allowed") is not False:
        errors.append("paper_ops_cycle_paper_live_activation_submit_authority")
    if artifact.get("paper_live_activation_forced_trades_allowed") is not False:
        errors.append("paper_ops_cycle_paper_live_activation_forced_trades_allowed")
    if artifact.get("paper_live_activation_qctrl_consultation_required") is not True:
        errors.append("paper_ops_cycle_paper_live_activation_qctrl_not_required")
    if artifact.get("paper_live_activation_qctrl_direct_execution_allowed") is not False:
        errors.append("paper_ops_cycle_paper_live_activation_qctrl_execution_authority")
    if artifact.get("paper_operational_mode_status") != "enabled_pending_downstream_gates":
        errors.append("paper_ops_cycle_paper_operational_mode_not_enabled")
    if artifact.get("paper_operational_mode_enabled") is not True:
        errors.append("paper_ops_cycle_paper_operational_mode_enabled_false")
    if artifact.get("paper_operational_mode_effective") is not True:
        errors.append("paper_ops_cycle_paper_operational_mode_not_effective")
    if artifact.get("paper_operational_mode_flag_disabled") is not False:
        errors.append("paper_ops_cycle_paper_operational_mode_flag_disabled")
    for key in (
        "paper_operational_mode_env_file_edited",
        "paper_operational_mode_paper_order_submission_allowed",
        "paper_operational_mode_live_capital_enabled",
        "paper_operational_mode_qctrl_direct_execution_allowed",
        "paper_operational_mode_qctrl_broker_post_allowed",
        "paper_operational_mode_phase7_proof_credit_allowed",
        "paper_operational_mode_forced_trades_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_ops_cycle_paper_operational_mode_forbidden:{key}")
    if artifact.get("qualified_setup_production_status") not in {
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
    }:
        errors.append("paper_ops_cycle_qualified_setup_production_not_ready")
    if artifact.get("qualified_setup_production_path_ready") is not True:
        errors.append("paper_ops_cycle_qualified_setup_production_path_not_ready")
    if int(artifact.get("qualified_setup_production_candidate_count", 0) or 0) < 1:
        errors.append("paper_ops_cycle_qualified_setup_production_candidate_missing")
    if artifact.get("qualified_setup_production_phase7_demo_qualified_setup_count") != 0:
        errors.append("paper_ops_cycle_qualified_setup_production_mutated_demo_run")
    if artifact.get("qualified_setup_production_q7_ledger_count") != 0:
        errors.append("paper_ops_cycle_qualified_setup_production_mutated_q7_ledger")
    if artifact.get("auto_approval_staged_order_status") not in {
        "staged_paper_order_ready",
        "ready_no_current_auto_approved_setup",
    }:
        errors.append("paper_ops_cycle_auto_approval_staged_order_not_ready")
    if artifact.get("auto_approval_staged_order_source_pt3_path_ready") is not True:
        errors.append("paper_ops_cycle_auto_approval_staged_order_source_not_ready")
    if (
        artifact.get("auto_approval_staged_order_status") == "staged_paper_order_ready"
        and artifact.get("auto_approval_staged_order_staged_order_count", 0) < 1
    ):
        errors.append("paper_ops_cycle_auto_approval_staged_order_missing_order")
    if (
        artifact.get("auto_approval_staged_order_status") == "staged_paper_order_ready"
        and artifact.get("auto_approval_staged_order_ready_for_paperops2_submit")
        is not True
    ):
        errors.append("paper_ops_cycle_auto_approval_staged_order_not_ready_for_paperops2")
    for key in (
        "auto_approval_staged_order_q7_source_ledger_mutation_performed",
        "auto_approval_staged_order_paper_order_submission_allowed",
        "auto_approval_staged_order_phase7_proof_credit_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_ops_cycle_auto_approval_staged_order_forbidden:{key}")
    if artifact.get("paper_live_qctrl_product_access_status") not in {
        "blocked_qctrl_product_access_or_subscription",
        "blocked_missing_qctrl_sdk",
        "qctrl_paper_consultation_ready",
    }:
        errors.append("paper_ops_cycle_paper_live_qctrl_product_access_not_checked")
    if artifact.get("paper_live_qctrl_provider_call_attempted") is not True:
        errors.append("paper_ops_cycle_paper_live_qctrl_provider_call_not_attempted")
    if int(artifact.get("paper_live_qctrl_provider_call_count", 0) or 0) < 1:
        errors.append("paper_ops_cycle_paper_live_qctrl_provider_call_count_missing")
    for key in (
        "paper_live_qctrl_execution_allowed",
        "paper_live_qctrl_paper_order_allowed",
        "paper_live_qctrl_broker_post_allowed",
        "paper_live_qctrl_live_capital_enabled",
        "paper_live_qctrl_phase7_proof_credit_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_ops_cycle_paper_live_qctrl_forbidden:{key}")
    if artifact.get("lifecycle_polling_enablement_status") not in {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_not_enabled")
    if artifact.get("lifecycle_polling_enablement_active") is not True:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_inactive")
    if artifact.get("lifecycle_polling_enablement_effective") is not True:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_not_effective")
    if artifact.get("lifecycle_polling_enablement_broker_get_allowed") is not True:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_get_not_allowed")
    if (
        artifact.get("lifecycle_polling_enablement_paperops2_submitted_order_count", 0)
        == 0
        and artifact.get("lifecycle_polling_enablement_path_available") is True
    ):
        errors.append("paper_ops_cycle_lifecycle_polling_path_without_submitted_order")
    if artifact.get("lifecycle_polling_enablement_broker_get_called_count") != 0:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_called_get_directly")
    if artifact.get("lifecycle_polling_enablement_live_endpoint_called_count") != 0:
        errors.append("paper_ops_cycle_lifecycle_polling_enablement_live_endpoint_called")
    if artifact.get("guarded_exit_enablement_status") not in {
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
    }:
        errors.append("paper_ops_cycle_guarded_exit_enablement_not_enabled")
    if artifact.get("guarded_exit_enablement_enabled") is not True:
        errors.append("paper_ops_cycle_guarded_exit_enablement_inactive")
    if artifact.get("guarded_exit_enablement_effective") is not True:
        errors.append("paper_ops_cycle_guarded_exit_enablement_not_effective")
    if artifact.get("guarded_exit_enablement_runtime_override") is not True:
        errors.append("paper_ops_cycle_guarded_exit_enablement_runtime_override_false")
    if (
        artifact.get("guarded_exit_enablement_open_position_count", 0) == 0
        and artifact.get("guarded_exit_enablement_path_available") is True
    ):
        errors.append("paper_ops_cycle_guarded_exit_path_without_open_position")
    if artifact.get("guarded_exit_enablement_close_called_count") != 0:
        errors.append("paper_ops_cycle_guarded_exit_enablement_called_close")
    if artifact.get("guarded_exit_enablement_live_endpoint_called_count") != 0:
        errors.append("paper_ops_cycle_guarded_exit_enablement_live_endpoint_called")
    qctrl_provider_call_count = int(artifact.get("qctrl_provider_call_count", 0) or 0)
    if (
        qctrl_provider_call_count
        and artifact.get("qctrl_paper_consultation_provider_call_recorded") is not True
    ):
        errors.append("paper_ops_cycle_qctrl_provider_call_unrecorded_by_paperops_q")
    if artifact.get("paperops_30_day_operations_status") not in {
        "operations_active",
        "operations_complete_pending_certification",
    }:
        errors.append("paper_ops_cycle_paperops_30_day_operations_not_active")
    if artifact.get("paperops_30_day_operations_automation_active") is not True:
        errors.append("paper_ops_cycle_paperops_30_day_operations_scheduler_inactive")
    if artifact.get("paperops_30_day_operations_automation_prompt_paperops_bound") is not True:
        errors.append("paper_ops_cycle_paperops_30_day_operations_prompt_not_bound")
    if artifact.get("paperops_30_day_operations_dashboard_mirror_public_safe") is not True:
        errors.append("paper_ops_cycle_paperops_30_day_operations_dashboard_not_safe")
    if artifact.get("command_count") != len(COMMANDS):
        errors.append("paper_ops_cycle_command_count_mismatch")
    if artifact.get("command_failed_count") != 0:
        errors.append("paper_ops_cycle_failed_commands_present")
    if artifact.get("command_passed_count") != artifact.get("command_count"):
        errors.append("paper_ops_cycle_not_all_commands_passed")
    if artifact.get("failed_commands"):
        errors.append("paper_ops_cycle_failed_command_list_not_empty")
    if any(not record.get("ok") for record in artifact.get("command_records", [])):
        errors.append("paper_ops_cycle_command_record_failed")
    if artifact.get("safe_to_continue_paper_only") is not True:
        errors.append("paper_ops_cycle_not_safe_to_continue_paper_only")
    if artifact.get("full_paper_operational_ready") is True and artifact.get("blocker_count"):
        errors.append("paper_ops_cycle_ready_with_blockers")
    if artifact.get("hard_safety_failure_count") != 0:
        errors.append("paper_ops_cycle_hard_safety_failure_count_nonzero")
    if artifact.get("event_log_written") is not True:
        errors.append("paper_ops_cycle_event_log_missing")
    if artifact.get("event_log_event_count") != 1:
        errors.append("paper_ops_cycle_event_log_count_mismatch")
    if "PaperOps-1" not in str(artifact.get("boundary", "")):
        errors.append("paper_ops_cycle_boundary_missing_stage")
    return errors


def write_paper_operational_cycle(
    artifact: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, event_path = _paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if event_path.exists():
        event_path.unlink()
    written = dict(artifact)
    event = EventLog(event_path, echo=False).write(
        PAPER_OPS_CYCLE_EVENT_TYPE,
        PAPER_OPS_CYCLE_COMPONENT,
        payload={
            "status": written["status"],
            "safe_to_continue_paper_only": written["safe_to_continue_paper_only"],
            "full_paper_operational_ready": written["full_paper_operational_ready"],
            "command_failed_count": written["command_failed_count"],
            "blocker_count": written["blocker_count"],
            "hard_safety_failure_count": written["hard_safety_failure_count"],
            "paper_live_activation_status": written["paper_live_activation_status"],
            "paper_live_activation_approved": written["paper_live_activation_approved"],
            "paper_live_activation_system_approval_logged": written[
                "paper_live_activation_system_approval_logged"
            ],
            "paper_live_qctrl_product_access_status": written[
                "paper_live_qctrl_product_access_status"
            ],
            "paper_live_qctrl_product_access_verified": written[
                "paper_live_qctrl_product_access_verified"
            ],
            "paper_live_qctrl_provider_call_count": written[
                "paper_live_qctrl_provider_call_count"
            ],
            "paper_operational_mode_status": written["paper_operational_mode_status"],
            "paper_operational_mode_effective": written[
                "paper_operational_mode_effective"
            ],
            "qualified_setup_production_status": written[
                "qualified_setup_production_status"
            ],
            "qualified_setup_production_qualified_setup_count": written[
                "qualified_setup_production_qualified_setup_count"
            ],
            "qualified_setup_production_ready_to_stage_q7_order": written[
                "qualified_setup_production_ready_to_stage_q7_order"
            ],
            "auto_approval_staged_order_status": written[
                "auto_approval_staged_order_status"
            ],
            "auto_approval_staged_order_staged_order_count": written[
                "auto_approval_staged_order_staged_order_count"
            ],
            "auto_approval_staged_order_ready_for_paperops2_submit": written[
                "auto_approval_staged_order_ready_for_paperops2_submit"
            ],
            "alpaca_paper_post_gate_status": written["alpaca_paper_post_gate_status"],
            "alpaca_paper_post_called_count": written["alpaca_paper_post_called_count"],
            "alpaca_paper_post_succeeded_count": written[
                "alpaca_paper_post_succeeded_count"
            ],
            "paper_lifecycle_poller_status": written["paper_lifecycle_poller_status"],
            "paper_lifecycle_poller_order_poll_called_count": written[
                "paper_lifecycle_poller_order_poll_called_count"
            ],
            "paper_lifecycle_poller_live_endpoint_called_count": written[
                "paper_lifecycle_poller_live_endpoint_called_count"
            ],
            "guarded_exit_enablement_status": written[
                "guarded_exit_enablement_status"
            ],
            "guarded_exit_enablement_effective": written[
                "guarded_exit_enablement_effective"
            ],
            "guarded_exit_enablement_close_called_count": written[
                "guarded_exit_enablement_close_called_count"
            ],
            "paper_exit_path_status": written["paper_exit_path_status"],
            "paper_exit_path_close_called_count": written[
                "paper_exit_path_close_called_count"
            ],
            "paper_exit_path_live_endpoint_called_count": written[
                "paper_exit_path_live_endpoint_called_count"
            ],
            "notification_review_status": written["notification_review_status"],
            "notification_review_live_send_allowed_count": written[
                "notification_review_live_send_allowed_count"
            ],
            "notification_review_command_path_enabled_count": written[
                "notification_review_command_path_enabled_count"
            ],
            "paperops_30_day_operations_status": written[
                "paperops_30_day_operations_status"
            ],
            "paperops_30_day_operations_scheduler_status": written[
                "paperops_30_day_operations_scheduler_status"
            ],
        },
    )
    written["recorded"] = True
    written["event_log_written"] = True
    written["event_log_path"] = str(event_path)
    written["event_log_event_count"] = 1
    written["event_log_correlation_id"] = event.correlation_id
    written["event_log_created_at"] = event.created_at
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(written, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def main() -> int:
    settings = Settings.from_env()
    artifact = build_paper_operational_cycle(settings)
    output_path, history_path, event_path, written = write_paper_operational_cycle(
        artifact,
        settings,
    )
    validation_errors = validate_paper_operational_cycle(written)
    print(f"paper_ops_cycle_status={written['status']}")
    print(f"paper_ops_cycle_artifact_path={output_path}")
    print(f"paper_ops_cycle_history_path={history_path}")
    print(f"paper_ops_cycle_event_log_path={event_path}")
    print(f"paper_ops_cycle_command_count={written['command_count']}")
    print(f"paper_ops_cycle_command_passed_count={written['command_passed_count']}")
    print(f"paper_ops_cycle_command_failed_count={written['command_failed_count']}")
    print(f"paper_ops_cycle_failed_commands={','.join(written['failed_commands'])}")
    print(
        "paper_ops_cycle_paper_live_activation_status="
        f"{written['paper_live_activation_status']}"
    )
    print(
        "paper_ops_cycle_paper_live_activation_approved="
        f"{written['paper_live_activation_approved']}"
    )
    print(
        "paper_ops_cycle_paper_live_activation_system_approval_logged="
        f"{written['paper_live_activation_system_approval_logged']}"
    )
    print(
        "paper_ops_cycle_paper_live_activation_paper_order_submission_allowed="
        f"{written['paper_live_activation_paper_order_submission_allowed']}"
    )
    print(
        "paper_ops_cycle_paper_live_activation_qctrl_consultation_required="
        f"{written['paper_live_activation_qctrl_consultation_required']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_product_access_status="
        f"{written['paper_live_qctrl_product_access_status']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_product_access_state="
        f"{written['paper_live_qctrl_product_access_state']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_product_access_verified="
        f"{written['paper_live_qctrl_product_access_verified']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_provider_call_attempted="
        f"{written['paper_live_qctrl_provider_call_attempted']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_provider_call_succeeded="
        f"{written['paper_live_qctrl_provider_call_succeeded']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_provider_call_count="
        f"{written['paper_live_qctrl_provider_call_count']}"
    )
    print(
        "paper_ops_cycle_paper_live_qctrl_product_access_blocker="
        f"{written['paper_live_qctrl_product_access_blocker']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_status="
        f"{written['paper_operational_mode_status']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_enabled="
        f"{written['paper_operational_mode_enabled']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_effective="
        f"{written['paper_operational_mode_effective']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_settings_flag="
        f"{written['paper_operational_mode_settings_flag']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_runtime_artifact_override_enabled="
        f"{written['paper_operational_mode_runtime_artifact_override_enabled']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_flag_disabled="
        f"{written['paper_operational_mode_flag_disabled']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_paper_order_submission_allowed="
        f"{written['paper_operational_mode_paper_order_submission_allowed']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_broker_post_called_count="
        f"{written['paper_operational_mode_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_paper_operational_mode_qctrl_product_access_blocker="
        f"{written['paper_operational_mode_qctrl_product_access_blocker']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_status="
        f"{written['qualified_setup_production_status']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_path_ready="
        f"{written['qualified_setup_production_path_ready']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_candidate_count="
        f"{written['qualified_setup_production_candidate_count']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_qualified_setup_count="
        f"{written['qualified_setup_production_qualified_setup_count']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_ready_to_stage_q7_order="
        f"{written['qualified_setup_production_ready_to_stage_q7_order']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_qctrl_status="
        f"{written['qualified_setup_production_qctrl_status']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_qctrl_connected="
        f"{written['qualified_setup_production_qctrl_connected']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_broker_post_called_count="
        f"{written['qualified_setup_production_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_qualified_setup_production_unsafe_write_counter_total="
        f"{written['qualified_setup_production_unsafe_write_counter_total']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_status="
        f"{written['auto_approval_staged_order_status']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_source_pt3_status="
        f"{written['auto_approval_staged_order_source_pt3_status']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_source_pt3_path_ready="
        f"{written['auto_approval_staged_order_source_pt3_path_ready']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_auto_approved_setup_count="
        f"{written['auto_approval_staged_order_auto_approved_setup_count']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_staged_order_count="
        f"{written['auto_approval_staged_order_staged_order_count']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_ready_for_paperops2_submit="
        f"{written['auto_approval_staged_order_ready_for_paperops2_submit']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_q7_source_ledger_mutation_performed="
        f"{written['auto_approval_staged_order_q7_source_ledger_mutation_performed']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_paper_order_submission_allowed="
        f"{written['auto_approval_staged_order_paper_order_submission_allowed']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_broker_post_called_count="
        f"{written['auto_approval_staged_order_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_live_endpoint_called_count="
        f"{written['auto_approval_staged_order_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_phase7_proof_credit_allowed="
        f"{written['auto_approval_staged_order_phase7_proof_credit_allowed']}"
    )
    print(
        "paper_ops_cycle_auto_approval_staged_order_unsafe_write_counter_total="
        f"{written['auto_approval_staged_order_unsafe_write_counter_total']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_status="
        f"{written['alpaca_submit_enablement_status']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_effective="
        f"{written['alpaca_submit_enablement_effective']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_path_available="
        f"{written['alpaca_submit_enablement_path_available']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_pt4_staged_order_count="
        f"{written['alpaca_submit_enablement_pt4_staged_order_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_broker_post_called_count="
        f"{written['alpaca_submit_enablement_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_alpaca_post_called_count="
        f"{written['alpaca_submit_enablement_alpaca_post_called_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_submit_enablement_live_endpoint_called_count="
        f"{written['alpaca_submit_enablement_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_status="
        f"{written['lifecycle_polling_enablement_status']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_active="
        f"{written['lifecycle_polling_enablement_active']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_path_available="
        f"{written['lifecycle_polling_enablement_path_available']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_submitted_order_count="
        f"{written['lifecycle_polling_enablement_paperops2_submitted_order_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_broker_get_called_count="
        f"{written['lifecycle_polling_enablement_broker_get_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_poller_order_poll_called_count="
        f"{written['lifecycle_polling_enablement_poller_order_poll_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_polling_enablement_live_endpoint_called_count="
        f"{written['lifecycle_polling_enablement_live_endpoint_called_count']}"
    )
    print(f"paper_ops_cycle_safe_to_continue_paper_only={written['safe_to_continue_paper_only']}")
    print(f"paper_ops_cycle_full_paper_operational_ready={written['full_paper_operational_ready']}")
    print(f"paper_ops_cycle_phase7_run_state={written['phase7_run_state']}")
    print(f"paper_ops_cycle_qualified_setup_count={written['qualified_setup_count']}")
    print(f"paper_ops_cycle_submitted_paper_order_count={written['submitted_paper_order_count']}")
    print(f"paper_ops_cycle_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"paper_ops_cycle_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paper_ops_cycle_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"paper_ops_cycle_alpaca_paper_post_gate_status={written['alpaca_paper_post_gate_status']}")
    print(
        "paper_ops_cycle_alpaca_paper_post_path_available="
        f"{written['alpaca_paper_post_path_available']}"
    )
    print(
        "paper_ops_cycle_alpaca_paper_post_eligible_submit_record_count="
        f"{written['alpaca_paper_post_eligible_submit_record_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_paper_post_called_count="
        f"{written['alpaca_paper_post_called_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_paper_post_succeeded_count="
        f"{written['alpaca_paper_post_succeeded_count']}"
    )
    print(
        "paper_ops_cycle_alpaca_paper_post_live_endpoint_called_count="
        f"{written['alpaca_paper_post_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_status="
        f"{written['paper_lifecycle_poller_status']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_source_submitted_order_count="
        f"{written['paper_lifecycle_poller_source_submitted_paper_order_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_order_poll_called_count="
        f"{written['paper_lifecycle_poller_order_poll_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_broker_get_called_count="
        f"{written['paper_lifecycle_poller_broker_get_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_broker_post_called_count="
        f"{written['paper_lifecycle_poller_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_lifecycle_poller_live_endpoint_called_count="
        f"{written['paper_lifecycle_poller_live_endpoint_called_count']}"
    )
    print(f"paper_ops_cycle_exit_path_status={written['paper_exit_path_status']}")
    print(f"paper_ops_cycle_exit_path_enabled={written['paper_exit_path_enabled']}")
    print(f"paper_ops_cycle_exit_path_available={written['paper_exit_path_available']}")
    print(
        "paper_ops_cycle_exit_path_open_position_readback_count="
        f"{written['paper_exit_path_open_position_readback_count']}"
    )
    print(
        "paper_ops_cycle_exit_path_eligible_exit_record_count="
        f"{written['paper_exit_path_eligible_exit_record_count']}"
    )
    print(
        "paper_ops_cycle_exit_path_close_called_count="
        f"{written['paper_exit_path_close_called_count']}"
    )
    print(
        "paper_ops_cycle_exit_path_broker_write_called_count="
        f"{written['paper_exit_path_broker_write_called_count']}"
    )
    print(
        "paper_ops_cycle_exit_path_broker_post_called_count="
        f"{written['paper_exit_path_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_exit_path_live_endpoint_called_count="
        f"{written['paper_exit_path_live_endpoint_called_count']}"
    )
    print(f"paper_ops_cycle_notification_review_status={written['notification_review_status']}")
    print(
        "paper_ops_cycle_notification_review_record_count="
        f"{written['notification_review_record_count']}"
    )
    print(
        "paper_ops_cycle_notification_review_lifecycle_type_count="
        f"{written['notification_review_lifecycle_type_count']}"
    )
    print(
        "paper_ops_cycle_notification_review_eligible_review_count="
        f"{written['notification_review_eligible_review_count']}"
    )
    print(
        "paper_ops_cycle_notification_review_send_gate="
        f"{written['notification_review_send_gate']}"
    )
    print(
        "paper_ops_cycle_notification_review_live_send_allowed_count="
        f"{written['notification_review_live_send_allowed_count']}"
    )
    print(
        "paper_ops_cycle_notification_review_command_path_enabled_count="
        f"{written['notification_review_command_path_enabled_count']}"
    )
    print(
        "paper_ops_cycle_notification_review_broker_write_allowed_count="
        f"{written['notification_review_broker_write_allowed_count']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_status="
        f"{written['paperops_30_day_operations_status']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_scheduler_status="
        f"{written['paperops_30_day_operations_scheduler_status']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_automation_active="
        f"{written['paperops_30_day_operations_automation_active']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_automation_prompt_paperops_bound="
        f"{written['paperops_30_day_operations_automation_prompt_paperops_bound']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_active_day_number="
        f"{written['paperops_30_day_operations_active_day_number']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_completed_calendar_day_count="
        f"{written['paperops_30_day_operations_completed_calendar_day_count']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_calendar_days_remaining="
        f"{written['paperops_30_day_operations_calendar_days_remaining']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_cycle_command_count="
        f"{written['paperops_30_day_operations_cycle_command_count']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_dashboard_mirror_status="
        f"{written['paperops_30_day_operations_dashboard_mirror_status']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_dashboard_mirror_public_safe="
        f"{written['paperops_30_day_operations_dashboard_mirror_public_safe']}"
    )
    print(
        "paper_ops_cycle_paperops_30_day_operations_unsafe_write_counter_total="
        f"{written['paperops_30_day_operations_unsafe_write_counter_total']}"
    )
    print(f"paper_ops_cycle_quantum_paper_parity_required={written['quantum_paper_parity_required']}")
    print(f"paper_ops_cycle_qctrl_paper_consultation_enabled={written['qctrl_paper_consultation_enabled']}")
    print(f"paper_ops_cycle_head_of_quant_oracle_result_count={written['head_of_quant_oracle_result_count']}")
    print(f"paper_ops_cycle_head_of_quant_latest_backend={written['head_of_quant_latest_backend']}")
    print(f"paper_ops_cycle_qctrl_readiness_status={written['qctrl_readiness_status']}")
    print(f"paper_ops_cycle_qctrl_paper_consultation_status={written['qctrl_paper_consultation_status']}")
    print(
        "paper_ops_cycle_qctrl_paper_consultation_provider_call_recorded="
        f"{written['qctrl_paper_consultation_provider_call_recorded']}"
    )
    print(f"paper_ops_cycle_qctrl_provider_call_count={written['qctrl_provider_call_count']}")
    print(f"paper_ops_cycle_blocker_count={written['blocker_count']}")
    print(f"paper_ops_cycle_blockers={','.join(written['blockers'])}")
    print(f"paper_ops_cycle_hard_safety_failure_count={written['hard_safety_failure_count']}")
    print(f"paper_ops_cycle_validation_errors={validation_errors}")
    if validation_errors:
        print("paper_operational_cycle_check=failed")
        return 1
    print("paper_operational_cycle_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
