"""PT-10 paper-live certification gate.

PT-10 aggregates the paper-live activation path through PT-9 and records whether
Qadam can be certified for active paper-live operation. It is intentionally
fail-closed: the control plane can be certified as safe and visible while full
paper-live certification remains blocked by any mandatory Q-CTRL or PaperOps
control-plane gate.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog


PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION = 1
PAPER_LIVE_CERTIFICATION_RUNTIME_ARTIFACT = "paper_live_certification.json"
PAPER_LIVE_CERTIFICATION_HISTORY = "paper_live_certification_history.jsonl"
PAPER_LIVE_CERTIFICATION_EVENT_LOG = "paper_live_certification_events.jsonl"
PAPER_LIVE_CERTIFICATION_EVENT_TYPE = "paper_live_certification_evaluated"
PAPER_LIVE_CERTIFICATION_COMPONENT = "paper_live_certification"
PAPER_GROWTH_TRIAL_NAME = "60-day paper growth trial"
PAPER_GROWTH_TRIAL_STARTING_VALUE_GBP = 100_000
PAPER_GROWTH_TRIAL_TARGET_VALUE_GBP = 200_000
PAPER_GROWTH_TRIAL_TARGET_MULTIPLE = 2.0
PAPER_GROWTH_TRIAL_HORIZON_DAYS = 60
PAPER_GROWTH_TRIAL_MINDSET = (
    "Event-driven, evidence-gated, probability/pricing-mispricing trading "
    "with selective larger paper positions when the strategy, risk, Q-CTRL, "
    "and Alpaca Paper gates agree."
)

PAPER_LIVE_CERTIFICATION_BOUNDARY = (
    "PT-10 is a paper-live certification gate only. It can certify that the "
    "paper-live control plane is safe, public-safe, scheduler-bound, and visible "
    "to the Fund Manager, but it cannot bypass Q-CTRL product access, cannot "
    "bypass the Q-CTRL paper consultation hold, cannot submit paper orders, "
    "cannot call brokers, cannot call live endpoints, cannot send Telegram "
    "messages, cannot enable Telegram commands, cannot force trades, cannot "
    "grant paper growth proof credit, cannot mark paper performance as mature "
    "without verified records, and cannot enable live capital."
)

PT10_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "certification_state",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_written",
    "event_log_event_count",
    "mode",
    "paper_live_certification_gate_evaluated",
    "paper_live_control_plane_certified",
    "paper_live_certified",
    "paper_live_operation_allowed",
    "paper_live_submission_delegation_allowed",
    "paper_live_certification_blocked",
    "paper_growth_trial_name",
    "paper_growth_trial_starting_value_gbp",
    "paper_growth_trial_target_value_gbp",
    "paper_growth_trial_target_multiple",
    "paper_growth_trial_horizon_days",
    "paper_growth_trial_mindset",
    "paper_growth_trial_target_active",
    "input_gate_count",
    "input_gate_passed_count",
    "input_gate_blocked_count",
    "control_plane_gate_count",
    "control_plane_gate_passed_count",
    "control_plane_gate_blocked_count",
    "control_plane_blockers",
    "control_plane_blocker_count",
    "certification_blockers",
    "certification_blocker_count",
    "gate_records",
    "safe_to_continue_paper_only",
    "full_paper_operational_ready",
    "paper_operational_readiness_status",
    "paper_operational_readiness_blockers",
    "paper_operational_readiness_blocker_count",
    "paper_live_activation_status",
    "paper_live_activation_approved",
    "paper_live_qctrl_product_access_status",
    "qctrl_product_access_verified",
    "qctrl_paper_consultation_ready",
    "qctrl_product_access_blocker",
    "qctrl_hold_active",
    "qctrl_hold_visible",
    "paper_submit_step_allowed",
    "paper_submit_visible_as_held",
    "active_paper_automation_status",
    "paperops_cockpit_notification_status",
    "paperops_cockpit_notification_readout_count",
    "paperops_notification_review_status",
    "paperops_notification_record_count",
    "paperops_30_day_operations_status",
    "paperops_30_day_operations_run_state",
    "paperops_30_day_operations_active_day_number",
    "paperops_30_day_operations_calendar_days_remaining",
    "paperops_30_day_operations_cycle_command_count",
    "paper_operational_cycle_status",
    "paper_operational_cycle_command_count",
    "paper_operational_cycle_command_passed_count",
    "paper_operational_cycle_command_failed_count",
    "phase7_run_id",
    "phase7_run_state",
    "phase7_active_day_number",
    "phase7_30_day_run_complete",
    "phase7_demo_proof_certified",
    "phase7_live_promotion_allowed",
    "qualified_setup_count",
    "submitted_paper_order_count",
    "closed_proof_trade_count",
    "live_capital_enabled",
    "live_credentials_loaded",
    "live_endpoint_called_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "notification_live_send_allowed_count",
    "telegram_command_path_enabled_count",
    "outbox_message_written_count",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
    "paper_growth_trial_unblocks_paper_operation",
    "recommended_next_action",
    "boundary",
    "validation_error_count",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _gate(
    *,
    key: str,
    stage: str,
    passed: bool,
    status: str,
    detail: str,
    required_for_control_plane: bool = True,
    required_for_paper_live_certification: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "stage": stage,
        "passed": passed,
        "backend_status": status,
        "display_status": status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "detail": detail,
        "required_for_control_plane": required_for_control_plane,
        "required_for_paper_live_certification": required_for_paper_live_certification,
    }


def paper_live_certification_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_LIVE_CERTIFICATION_RUNTIME_ARTIFACT,
        runtime / PAPER_LIVE_CERTIFICATION_HISTORY,
        runtime / PAPER_LIVE_CERTIFICATION_EVENT_LOG,
    )


def read_latest_paper_live_certification(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paper_live_certification_paths(settings)
    return _read_json(output_path)


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "paper_live_activation": _read_json(runtime / "paper_live_activation.json"),
        "paper_live_qctrl_product_access": _read_json(
            runtime / "paper_live_qctrl_product_access.json"
        ),
        "paper_operational_mode": _read_json(runtime / "paper_operational_mode.json"),
        "qualified_setup_production": _read_json(
            runtime / "paperops_qualified_setup_production.json"
        ),
        "auto_approval_staged_order": _read_json(
            runtime / "paperops_auto_approval_staged_order.json"
        ),
        "alpaca_submit_enablement": _read_json(
            runtime / "paperops_alpaca_paper_submit_enablement.json"
        ),
        "lifecycle_polling_enablement": _read_json(
            runtime / "paperops_paper_lifecycle_polling_enablement.json"
        ),
        "guarded_exit_enablement": _read_json(
            runtime / "paperops_guarded_paper_exit_enablement.json"
        ),
        "active_automation": _read_json(
            runtime / "paperops_active_paper_trading_automation.json"
        ),
        "notification_review": _read_json(runtime / "paperops_notification_review.json"),
        "operations": _read_json(runtime / "paperops_30_day_operations.json"),
        "cockpit_notification": _read_json(
            runtime / "paperops_cockpit_notification_upgrade.json"
        ),
        "cycle": _read_json(runtime / "paper_operational_cycle.json"),
        "readiness": _read_json(runtime / "paper_operational_readiness.json"),
        "demo_run": _read_json(runtime / "phase7_demo_proof_run.json"),
        "phase7_certification": _read_json(runtime / "phase7_certification.json"),
        "live_promotion": _read_json(runtime / "phase7_live_promotion_review.json"),
    }


def _gate_records(settings: Settings, snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    activation = snapshot["paper_live_activation"]
    qctrl_access = snapshot["paper_live_qctrl_product_access"]
    paper_mode = snapshot["paper_operational_mode"]
    setup = snapshot["qualified_setup_production"]
    staged = snapshot["auto_approval_staged_order"]
    submit_enablement = snapshot["alpaca_submit_enablement"]
    lifecycle_enablement = snapshot["lifecycle_polling_enablement"]
    exit_enablement = snapshot["guarded_exit_enablement"]
    active = snapshot["active_automation"]
    notification = snapshot["notification_review"]
    operations = snapshot["operations"]
    cockpit_notification = snapshot["cockpit_notification"]
    cycle = snapshot["cycle"]
    readiness = snapshot["readiness"]
    demo_run = snapshot["demo_run"]
    phase7_certification = snapshot["phase7_certification"]
    live_promotion = snapshot["live_promotion"]

    qctrl_checked = (
        qctrl_access.get("status")
        in {
            "blocked_qctrl_product_access_or_subscription",
            "blocked_missing_qctrl_sdk",
            "qctrl_paper_consultation_ready",
        }
        and qctrl_access.get("provider_call_attempted") is True
        and _int(qctrl_access.get("provider_call_count")) >= 1
    )
    qctrl_ready = (
        qctrl_access.get("status") == "qctrl_paper_consultation_ready"
        and qctrl_access.get("product_access_verified") is True
        and qctrl_access.get("paper_consultation_ready") is True
    )
    qctrl_hold = active.get("qctrl_consultation_hold_active") is True
    submit_allowed = active.get("paper_submit_step_allowed") is True
    cycle_safe = (
        cycle.get("safe_to_continue_paper_only") is True
        and _int(cycle.get("command_failed_count")) == 0
        and _int(cycle.get("hard_safety_failure_count")) == 0
        and _int(cycle.get("unsafe_write_counter_total")) == 0
    )
    return [
        _gate(
            key="paper_mode_enforced",
            stage="PaperOps",
            passed=settings.mode == "paper" and settings.live_capital_enabled is False,
            status=f"mode={settings.mode}",
            detail="Qadam must remain in paper mode with live capital disabled.",
        ),
        _gate(
            key="pt0_activation_approved",
            stage="PT-0",
            passed=activation.get("approval_state") == "approved"
            and activation.get("paper_trading_system_approval_logged") is True
            and activation.get("paper_live_activation_approved") is True,
            status=str(activation.get("status") or "missing"),
            detail="Fund Manager system-level paper-live approval must be logged.",
        ),
        _gate(
            key="pt1_qctrl_access_checked",
            stage="PT-1",
            passed=qctrl_checked,
            status=str(qctrl_access.get("status") or "missing"),
            detail="Q-CTRL product-access state must be explicitly checked.",
        ),
        _gate(
            key="qctrl_product_access_ready",
            stage="PT-1",
            passed=qctrl_ready,
            status=str(qctrl_access.get("status") or "missing"),
            detail="Full paper-live certification requires Q-CTRL consultation readiness.",
            required_for_control_plane=False,
            required_for_paper_live_certification=True,
        ),
        _gate(
            key="pt2_global_paper_mode_effective",
            stage="PT-2",
            passed=paper_mode.get("paper_operational_mode_effective") is True
            and paper_mode.get("paper_operational_enabled") is True,
            status=str(paper_mode.get("status") or "missing"),
            detail="Runtime PaperOps mode must be effective without env edits.",
        ),
        _gate(
            key="pt3_qualified_setup_path_ready",
            stage="PT-3",
            passed=setup.get("qualified_setup_production_path_ready") is True
            and setup.get("recorded") is True,
            status=str(setup.get("status") or "missing"),
            detail="Qualified setup production path must be connected without forcing trades.",
        ),
        _gate(
            key="pt4_staged_paper_order_ready",
            stage="PT-4",
            passed=staged.get("recorded") is True
            and _int(staged.get("staged_order_count")) >= 1
            and staged.get("paper_order_submission_allowed") is False,
            status=str(staged.get("status") or "missing"),
            detail="Auto-approval may stage paper orders but not submit them by itself.",
        ),
        _gate(
            key="pt5_paper_submit_path_enabled",
            stage="PT-5",
            passed=submit_enablement.get("alpaca_paper_submit_effective") is True
            and submit_enablement.get("paper_post_path_available") is True,
            status=str(submit_enablement.get("status") or "missing"),
            detail="Alpaca paper-submit path must be runtime-enabled and guarded.",
        ),
        _gate(
            key="pt6_lifecycle_polling_enabled",
            stage="PT-6",
            passed=lifecycle_enablement.get("paper_lifecycle_polling_effective") is True,
            status=str(lifecycle_enablement.get("status") or "missing"),
            detail="Paper lifecycle polling must be runtime-enabled and idle until submitted orders exist.",
        ),
        _gate(
            key="pt7_guarded_exit_enabled",
            stage="PT-7",
            passed=exit_enablement.get("alpaca_paper_exit_effective") is True,
            status=str(exit_enablement.get("status") or "missing"),
            detail="Guarded paper-exit path must be runtime-enabled and idle until open positions exist.",
        ),
        _gate(
            key="pt8_active_automation_safe",
            stage="PT-8",
            passed=active.get("active_paper_trading_automation_enabled") is True
            and active.get("automation_prompt_active_trade_bound") is True
            and not (qctrl_hold and submit_allowed),
            status=str(active.get("status") or "missing"),
            detail="Active runner must be bound to guarded PaperOps gates and cannot bypass Q-CTRL.",
        ),
        _gate(
            key="qctrl_hold_cleared_for_submit",
            stage="PT-8",
            passed=qctrl_hold is False,
            status="held" if qctrl_hold else "clear",
            detail="Full paper-live certification requires the Q-CTRL submit hold to clear.",
            required_for_control_plane=False,
            required_for_paper_live_certification=True,
        ),
        _gate(
            key="pt9_cockpit_notification_ready",
            stage="PT-9",
            passed=cockpit_notification.get("status") == "cockpit_notification_upgrade_ready"
            and cockpit_notification.get("cockpit_upgrade_ready") is True
            and cockpit_notification.get("notification_upgrade_ready") is True,
            status=str(cockpit_notification.get("status") or "missing"),
            detail="Fund Manager cockpit and notification readouts must be public-safe and review-only.",
        ),
        _gate(
            key="paperops5_notification_review_ready",
            stage="PaperOps-5",
            passed=notification.get("status") == "review_ready"
            and _int(notification.get("live_send_allowed_count")) == 0
            and _int(notification.get("telegram_command_path_enabled_count")) == 0,
            status=str(notification.get("status") or "missing"),
            detail="Notification review must remain command-disabled and live-send disabled.",
        ),
        _gate(
            key="paperops6_30_day_operations_active",
            stage="PaperOps-6",
            passed=operations.get("status") in {"operations_active", "operations_complete_pending_certification"}
            and operations.get("automation_active") is True
            and operations.get("dashboard_mirror_public_safe") is True,
            status=str(operations.get("status") or "missing"),
            detail="30-day operations must be active and mirrored through public-safe cockpit state.",
        ),
        _gate(
            key="paperops1_cycle_safe",
            stage="PaperOps-1",
            passed=cycle_safe,
            status=str(cycle.get("status") or "missing"),
            detail="The operational cycle must pass without hard safety failures.",
        ),
        _gate(
            key="paperops_readiness_safe",
            stage="PaperOps-0",
            passed=readiness.get("safe_to_continue_paper_only") is True,
            status=str(readiness.get("status") or "missing"),
            detail="PaperOps readiness must be safe to continue in paper mode.",
        ),
        _gate(
            key="paperops_full_readiness",
            stage="PaperOps-0",
            passed=readiness.get("full_paper_operational_ready") is True,
            status=str(readiness.get("status") or "missing"),
            detail="Full paper-live certification requires all required PaperOps capabilities ready.",
            required_for_control_plane=False,
            required_for_paper_live_certification=True,
        ),
        _gate(
            key="phase7_demo_run_active",
            stage="Paper Growth Trial",
            passed=demo_run.get("run_state") in {"active", "complete_pending_certification"},
            status=str(demo_run.get("run_state") or "missing"),
            detail="The paper growth trial observation run must be active or complete.",
        ),
        _gate(
            key="phase7_30_day_run_complete",
            stage="Paper Growth Trial",
            passed=demo_run.get("phase7_30_day_run_complete") is True,
            status=str(demo_run.get("run_state") or "missing"),
            detail=(
                "Legacy 30-day proof completion is tracked for performance "
                "history, but no longer blocks paper-mode operation."
            ),
            required_for_control_plane=False,
            required_for_paper_live_certification=False,
        ),
        _gate(
            key="phase7_demo_proof_certified",
            stage="Paper Growth Trial",
            passed=phase7_certification.get("phase7_demo_proof_certified") is True,
            status=str(phase7_certification.get("status") or "missing"),
            detail=(
                "Legacy proof certification is a performance-readiness metric, "
                "not a prerequisite for Alpaca paper operation."
            ),
            required_for_control_plane=False,
            required_for_paper_live_certification=False,
        ),
        _gate(
            key="live_promotion_still_blocked",
            stage="Paper Growth Trial",
            passed=live_promotion.get("live_capital_enabled") is not True
            and live_promotion.get("live_promotion_live_capital_enabled") is not True,
            status=str(live_promotion.get("status") or "missing"),
            detail="PT-10 cannot promote Qadam to live capital.",
        ),
    ]


def _recommended_next_action(blockers: list[str]) -> str:
    if "qctrl_product_access_ready" in blockers or "qctrl_hold_cleared_for_submit" in blockers:
        return "Resolve Q-CTRL product access so PT-8 can clear the paper-submit hold."
    if blockers:
        return "Resolve PT-10 certification blockers before treating paper-live as certified."
    return (
        "Keep the 60-day paper growth trial active: target GBP 200,000 from "
        "GBP 100,000 in 60 days, using Alpaca Paper only."
    )


def _blocked_certification_status(
    *,
    control_plane_certified: bool,
    certification_blockers: list[str],
    paper_live_certified: bool,
) -> str:
    if paper_live_certified:
        return "paper_live_certified"
    if not control_plane_certified:
        return "blocked_paper_live_control_plane"

    qctrl_blockers = {
        "qctrl_product_access_ready",
        "qctrl_hold_cleared_for_submit",
    }
    phase7_blockers = {
        "phase7_30_day_run_complete",
        "phase7_demo_proof_certified",
    }
    has_qctrl_blocker = any(blocker in qctrl_blockers for blocker in certification_blockers)
    has_phase7_blocker = any(blocker in phase7_blockers for blocker in certification_blockers)
    if has_qctrl_blocker and has_phase7_blocker:
        return "blocked_pending_qctrl_and_phase7_proof"
    if has_qctrl_blocker:
        return "blocked_pending_qctrl"
    if has_phase7_blocker:
        return "blocked_pending_phase7_proof"
    return "blocked_pending_certification_gates"


def build_paper_live_certification(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    snapshot = _source_snapshot(settings)
    gate_records = _gate_records(settings, snapshot)
    control_blockers = [
        gate["key"]
        for gate in gate_records
        if gate["required_for_control_plane"] and not gate["passed"]
    ]
    certification_blockers = [
        gate["key"]
        for gate in gate_records
        if gate["required_for_paper_live_certification"] and not gate["passed"]
    ]
    readiness = snapshot["readiness"]
    activation = snapshot["paper_live_activation"]
    qctrl_access = snapshot["paper_live_qctrl_product_access"]
    active = snapshot["active_automation"]
    notification = snapshot["notification_review"]
    operations = snapshot["operations"]
    cockpit_notification = snapshot["cockpit_notification"]
    cycle = snapshot["cycle"]
    demo_run = snapshot["demo_run"]
    phase7_certification = snapshot["phase7_certification"]
    live_promotion = snapshot["live_promotion"]

    qctrl_hold = active.get("qctrl_consultation_hold_active") is True
    submit_allowed = active.get("paper_submit_step_allowed") is True
    unsafe_total = sum(
        _int(value)
        for value in (
            readiness.get("broker_post_called_count"),
            readiness.get("alpaca_post_called_count"),
            active.get("live_endpoint_called_count"),
            active.get("unsafe_write_counter_total"),
            notification.get("live_send_allowed_count"),
            notification.get("telegram_command_path_enabled_count"),
            notification.get("broker_write_allowed_count"),
            cockpit_notification.get("notification_live_send_allowed_count"),
            cockpit_notification.get("notification_command_path_enabled_count"),
            cockpit_notification.get("notification_broker_write_allowed_count"),
            cockpit_notification.get("unsafe_write_counter_total"),
            operations.get("unsafe_write_counter_total"),
            cycle.get("unsafe_write_counter_total"),
            demo_run.get("live_endpoint_allowed_count"),
        )
    )
    if settings.live_capital_enabled:
        unsafe_total += 1
    control_plane_certified = not control_blockers and unsafe_total == 0
    paper_live_certified = control_plane_certified and not certification_blockers
    status = _blocked_certification_status(
        control_plane_certified=control_plane_certified,
        certification_blockers=certification_blockers,
        paper_live_certified=paper_live_certified,
    )
    artifact = {
        "schema_version": PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "paper_live_certification",
        "artifact_id": "paperops:pt-10:paper-live-certification",
        "phase": "PaperOps",
        "stage": "PT-10",
        "status": status,
        "stage_status": "paper_live_certified"
        if paper_live_certified
        else "paper_live_certification_blocked",
        "certification_state": "certified" if paper_live_certified else "blocked",
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "paper_live_certification_gate_evaluated": True,
        "paper_live_control_plane_certified": control_plane_certified,
        "paper_live_certified": paper_live_certified,
        "paper_live_operation_allowed": paper_live_certified,
        "paper_live_submission_delegation_allowed": paper_live_certified
        and submit_allowed
        and not qctrl_hold,
        "paper_live_certification_blocked": not paper_live_certified,
        "paper_growth_trial_name": PAPER_GROWTH_TRIAL_NAME,
        "paper_growth_trial_starting_value_gbp": PAPER_GROWTH_TRIAL_STARTING_VALUE_GBP,
        "paper_growth_trial_target_value_gbp": PAPER_GROWTH_TRIAL_TARGET_VALUE_GBP,
        "paper_growth_trial_target_multiple": PAPER_GROWTH_TRIAL_TARGET_MULTIPLE,
        "paper_growth_trial_horizon_days": PAPER_GROWTH_TRIAL_HORIZON_DAYS,
        "paper_growth_trial_mindset": PAPER_GROWTH_TRIAL_MINDSET,
        "paper_growth_trial_target_active": True,
        "input_gate_count": len(gate_records),
        "input_gate_passed_count": sum(1 for gate in gate_records if gate["passed"]),
        "input_gate_blocked_count": sum(1 for gate in gate_records if not gate["passed"]),
        "control_plane_gate_count": sum(
            1 for gate in gate_records if gate["required_for_control_plane"]
        ),
        "control_plane_gate_passed_count": sum(
            1
            for gate in gate_records
            if gate["required_for_control_plane"] and gate["passed"]
        ),
        "control_plane_gate_blocked_count": len(control_blockers),
        "control_plane_blockers": control_blockers,
        "control_plane_blocker_count": len(control_blockers),
        "certification_blockers": certification_blockers,
        "certification_blocker_count": len(certification_blockers),
        "gate_records": gate_records,
        "safe_to_continue_paper_only": readiness.get("safe_to_continue_paper_only") is True,
        "full_paper_operational_ready": readiness.get("full_paper_operational_ready") is True,
        "paper_operational_readiness_status": readiness.get("status", "missing"),
        "paper_operational_readiness_blockers": list(readiness.get("blockers") or []),
        "paper_operational_readiness_blocker_count": _int(readiness.get("blocker_count")),
        "paper_live_activation_status": activation.get("status", "missing"),
        "paper_live_activation_approved": activation.get("paper_live_activation_approved")
        is True,
        "paper_live_qctrl_product_access_status": qctrl_access.get("status", "missing"),
        "qctrl_product_access_verified": qctrl_access.get("product_access_verified")
        is True,
        "qctrl_paper_consultation_ready": qctrl_access.get("paper_consultation_ready")
        is True,
        "qctrl_product_access_blocker": qctrl_access.get("product_access_blocker"),
        "qctrl_hold_active": qctrl_hold,
        "qctrl_hold_visible": cockpit_notification.get("qctrl_hold_visible") is True,
        "paper_submit_step_allowed": submit_allowed,
        "paper_submit_visible_as_held": (
            cockpit_notification.get("paper_submit_visible_as_held") is True
        ),
        "active_paper_automation_status": active.get("status", "missing"),
        "paperops_cockpit_notification_status": cockpit_notification.get(
            "status",
            "missing",
        ),
        "paperops_cockpit_notification_readout_count": _int(
            cockpit_notification.get("fund_manager_readout_count")
        ),
        "paperops_notification_review_status": notification.get("status", "missing"),
        "paperops_notification_record_count": _int(
            notification.get("notification_record_count")
        ),
        "paperops_30_day_operations_status": operations.get("status", "missing"),
        "paperops_30_day_operations_run_state": operations.get("run_state", "missing"),
        "paperops_30_day_operations_active_day_number": operations.get(
            "active_day_number"
        ),
        "paperops_30_day_operations_calendar_days_remaining": _int(
            operations.get("calendar_days_remaining")
        ),
        "paperops_30_day_operations_cycle_command_count": _int(
            operations.get("paper_operational_cycle_command_count")
        ),
        "paper_operational_cycle_status": cycle.get("status", "missing"),
        "paper_operational_cycle_command_count": _int(cycle.get("command_count")),
        "paper_operational_cycle_command_passed_count": _int(
            cycle.get("command_passed_count")
        ),
        "paper_operational_cycle_command_failed_count": _int(
            cycle.get("command_failed_count")
        ),
        "phase7_run_id": demo_run.get("run_id"),
        "phase7_run_state": demo_run.get("run_state", "missing"),
        "phase7_active_day_number": demo_run.get("active_day_number"),
        "phase7_30_day_run_complete": demo_run.get("phase7_30_day_run_complete")
        is True,
        "phase7_demo_proof_certified": phase7_certification.get(
            "phase7_demo_proof_certified"
        )
        is True,
        "phase7_live_promotion_allowed": live_promotion.get(
            "live_promotion_allowed"
        )
        is True,
        "qualified_setup_count": _int(demo_run.get("qualified_setup_count")),
        "submitted_paper_order_count": _int(
            demo_run.get("submitted_paper_order_count")
        ),
        "closed_proof_trade_count": _int(demo_run.get("closed_proof_trade_count")),
        "live_capital_enabled": settings.live_capital_enabled,
        "live_credentials_loaded": False,
        "live_endpoint_called_count": _int(demo_run.get("live_endpoint_allowed_count")),
        "broker_post_called_count": _int(readiness.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(readiness.get("alpaca_post_called_count")),
        "broker_write_allowed_count": _int(notification.get("broker_write_allowed_count")),
        "notification_live_send_allowed_count": _int(
            notification.get("live_send_allowed_count")
        ),
        "telegram_command_path_enabled_count": _int(
            notification.get("telegram_command_path_enabled_count")
        ),
        "outbox_message_written_count": 0,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": unsafe_total,
        "paper_growth_trial_unblocks_paper_operation": paper_live_certified,
        "recommended_next_action": _recommended_next_action(certification_blockers),
        "boundary": PAPER_LIVE_CERTIFICATION_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paper_live_certification(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
        artifact["stage_status"] = "invalid"
        artifact["paper_live_certified"] = False
        artifact["paper_live_operation_allowed"] = False
        artifact["paper_live_submission_delegation_allowed"] = False
    return artifact


def validate_paper_live_certification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PT10_PUBLIC_FIELDS) - set(artifact))
    if missing:
        errors.append("paper_live_certification_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION:
        errors.append("paper_live_certification_schema_mismatch")
    if artifact.get("artifact_type") != "paper_live_certification":
        errors.append("paper_live_certification_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-10":
        errors.append("paper_live_certification_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paper_live_certification_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paper_live_certification_not_public_safe")
    if artifact.get("status") not in {
        "paper_live_certified",
        "blocked_pending_qctrl_and_phase7_proof",
        "blocked_pending_qctrl",
        "blocked_pending_phase7_proof",
        "blocked_pending_certification_gates",
        "blocked_paper_live_control_plane",
        "invalid",
    }:
        errors.append("paper_live_certification_status_invalid")
    gates = artifact.get("gate_records", [])
    if not isinstance(gates, list) or not gates:
        errors.append("paper_live_certification_gate_records_missing")
    else:
        if artifact.get("input_gate_count") != len(gates):
            errors.append("paper_live_certification_gate_count_mismatch")
        passed_count = sum(1 for gate in gates if gate.get("passed") is True)
        blocked_count = sum(1 for gate in gates if gate.get("passed") is not True)
        if artifact.get("input_gate_passed_count") != passed_count:
            errors.append("paper_live_certification_passed_count_mismatch")
        if artifact.get("input_gate_blocked_count") != blocked_count:
            errors.append("paper_live_certification_blocked_count_mismatch")
        for gate in gates:
            if gate.get("display_status") != gate.get("backend_status"):
                errors.append("paper_live_certification_gate_display_mismatch")
            if gate.get("display_derived_from_backend") is not True:
                errors.append("paper_live_certification_gate_not_backend_derived")
            if gate.get("ui_inferred_readiness") is not False:
                errors.append("paper_live_certification_gate_ui_inferred")
    control_blockers = list(artifact.get("control_plane_blockers") or [])
    certification_blockers = list(artifact.get("certification_blockers") or [])
    if artifact.get("control_plane_blocker_count") != len(control_blockers):
        errors.append("paper_live_certification_control_blocker_count_mismatch")
    if artifact.get("certification_blocker_count") != len(certification_blockers):
        errors.append("paper_live_certification_blocker_count_mismatch")
    if artifact.get("paper_live_control_plane_certified") is True and control_blockers:
        errors.append("paper_live_certification_control_plane_with_blockers")
    if artifact.get("paper_live_control_plane_certified") is False and not control_blockers:
        errors.append("paper_live_certification_control_plane_false_without_blockers")
    if artifact.get("paper_live_certified") is True:
        if artifact.get("status") != "paper_live_certified":
            errors.append("paper_live_certification_status_not_certified")
        if certification_blockers:
            errors.append("paper_live_certified_with_blockers")
        if artifact.get("paper_live_operation_allowed") is not True:
            errors.append("paper_live_certified_without_operation_allowed")
        if artifact.get("qctrl_product_access_verified") is not True:
            errors.append("paper_live_certified_without_qctrl_access")
        if artifact.get("qctrl_hold_active") is not False:
            errors.append("paper_live_certified_with_qctrl_hold")
        if artifact.get("full_paper_operational_ready") is not True:
            errors.append("paper_live_certified_without_full_readiness")
    else:
        if artifact.get("status") == "paper_live_certified":
            errors.append("paper_live_uncertified_with_certified_status")
        if not certification_blockers and artifact.get("status") != "invalid":
            errors.append("paper_live_blocked_without_blockers")
        if artifact.get("paper_live_operation_allowed") is not False:
            errors.append("paper_live_operation_allowed_while_blocked")
        if artifact.get("paper_live_submission_delegation_allowed") is not False:
            errors.append("paper_live_submission_allowed_while_blocked")
    if (
        artifact.get("qctrl_hold_active") is True
        and artifact.get("paper_submit_step_allowed") is True
    ):
        errors.append("paper_live_certification_qctrl_hold_bypassed")
    if artifact.get("qctrl_hold_active") is True and artifact.get(
        "paper_submit_visible_as_held"
    ) is not True:
        errors.append("paper_live_certification_qctrl_hold_not_visible")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("paper_live_certification_phase7_proof_credit_allowed")
    if artifact.get("paper_growth_trial_target_active") is not True:
        errors.append("paper_live_certification_growth_trial_not_active")
    if _int(artifact.get("paper_growth_trial_starting_value_gbp")) != PAPER_GROWTH_TRIAL_STARTING_VALUE_GBP:
        errors.append("paper_live_certification_growth_trial_start_mismatch")
    if _int(artifact.get("paper_growth_trial_target_value_gbp")) != PAPER_GROWTH_TRIAL_TARGET_VALUE_GBP:
        errors.append("paper_live_certification_growth_trial_target_mismatch")
    if _int(artifact.get("paper_growth_trial_horizon_days")) != PAPER_GROWTH_TRIAL_HORIZON_DAYS:
        errors.append("paper_live_certification_growth_trial_horizon_mismatch")
    for key in (
        "live_capital_enabled",
        "live_credentials_loaded",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_live_certification_forbidden:{key}")
    for key in (
        "live_endpoint_called_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "notification_live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "outbox_message_written_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_live_certification_unsafe_counter_nonzero:{key}")
    if artifact.get("recorded") is True:
        if artifact.get("event_log_written") is not True:
            errors.append("paper_live_certification_event_log_missing")
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("paper_live_certification_event_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-10 is a paper-live certification gate only",
        "cannot bypass Q-CTRL product access",
        "cannot submit paper orders",
        "cannot call brokers",
        "cannot call live endpoints",
        "cannot send Telegram messages",
        "cannot grant paper growth proof credit",
        "cannot mark paper performance as mature without verified records",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paper_live_certification_boundary_weak")
            break
    if artifact.get("validation_error_count") not in {
        None,
        len(artifact.get("validation_errors", []) or []),
    }:
        errors.append("paper_live_certification_validation_count_mismatch")
    return sorted(set(errors))


def write_paper_live_certification(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paper_live_certification_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPER_LIVE_CERTIFICATION_EVENT_TYPE,
            PAPER_LIVE_CERTIFICATION_COMPONENT,
            payload={
                "status": written.get("status"),
                "paper_live_control_plane_certified": written.get(
                    "paper_live_control_plane_certified"
                ),
                "paper_live_certified": written.get("paper_live_certified"),
                "certification_blocker_count": written.get(
                    "certification_blocker_count"
                ),
                "qctrl_product_access_verified": written.get(
                    "qctrl_product_access_verified"
                ),
                "phase7_30_day_run_complete": written.get(
                    "phase7_30_day_run_complete"
                ),
                "unsafe_write_counter_total": written.get(
                    "unsafe_write_counter_total"
                ),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paper_live_certification(written)
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
        written["stage_status"] = "invalid"
        written["paper_live_certified"] = False
        written["paper_live_operation_allowed"] = False
        written["paper_live_submission_delegation_allowed"] = False
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "paper_live_control_plane_certified": written.get(
            "paper_live_control_plane_certified"
        ),
        "paper_live_certified": written.get("paper_live_certified"),
        "certification_blocker_count": written.get("certification_blocker_count"),
        "qctrl_product_access_verified": written.get("qctrl_product_access_verified"),
        "phase7_30_day_run_complete": written.get("phase7_30_day_run_complete"),
        "unsafe_write_counter_total": written.get("unsafe_write_counter_total"),
        "validation_error_count": written.get("validation_error_count"),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paper_live_certification_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paper_live_certification(settings)
    if not artifact:
        defaults = {field: None for field in PT10_PUBLIC_FIELDS}
        defaults.update(
            {
                "schema_version": PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION,
                "artifact_type": "paper_live_certification",
                "artifact_id": "paperops:pt-10:paper-live-certification",
                "phase": "PaperOps",
                "stage": "PT-10",
                "status": "not_run",
                "stage_status": "not_run",
                "certification_state": "not_run",
                "generated_at": None,
                "public_safe": True,
                "recorded": False,
                "event_log_written": False,
                "event_log_event_count": 0,
                "mode": "paper",
                "paper_live_certification_gate_evaluated": False,
                "paper_live_control_plane_certified": False,
                "paper_live_certified": False,
                "paper_live_operation_allowed": False,
                "paper_live_submission_delegation_allowed": False,
                "paper_live_certification_blocked": True,
                "input_gate_count": 0,
                "input_gate_passed_count": 0,
                "input_gate_blocked_count": 0,
                "control_plane_gate_count": 0,
                "control_plane_gate_passed_count": 0,
                "control_plane_gate_blocked_count": 0,
                "control_plane_blockers": ["pt10_not_run"],
                "control_plane_blocker_count": 1,
                "certification_blockers": ["pt10_not_run"],
                "certification_blocker_count": 1,
                "gate_records": [],
                "safe_to_continue_paper_only": False,
                "full_paper_operational_ready": False,
                "paper_growth_trial_name": PAPER_GROWTH_TRIAL_NAME,
                "paper_growth_trial_starting_value_gbp": PAPER_GROWTH_TRIAL_STARTING_VALUE_GBP,
                "paper_growth_trial_target_value_gbp": PAPER_GROWTH_TRIAL_TARGET_VALUE_GBP,
                "paper_growth_trial_target_multiple": PAPER_GROWTH_TRIAL_TARGET_MULTIPLE,
                "paper_growth_trial_horizon_days": PAPER_GROWTH_TRIAL_HORIZON_DAYS,
                "paper_growth_trial_mindset": PAPER_GROWTH_TRIAL_MINDSET,
                "paper_growth_trial_target_active": True,
                "phase7_proof_credit_allowed": False,
                "live_capital_enabled": False,
                "unsafe_write_counter_total": 0,
                "paper_growth_trial_unblocks_paper_operation": False,
                "validation_error_count": 0,
                "recommended_next_action": "Run PT-10 paper-live certification.",
                "boundary": PAPER_LIVE_CERTIFICATION_BOUNDARY,
            }
        )
        return defaults
    public = {field: deepcopy(artifact.get(field)) for field in PT10_PUBLIC_FIELDS}
    public["control_plane_blockers"] = list(public.get("control_plane_blockers") or [])
    public["certification_blockers"] = list(public.get("certification_blockers") or [])
    public["gate_records"] = list(public.get("gate_records") or [])
    public["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return public
