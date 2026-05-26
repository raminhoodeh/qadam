"""PT-9 cockpit and notification upgrade contract.

PT-9 proves that the active PaperOps state is visible to the Fund Manager in a
public-safe cockpit shape and in review-only notification records. It does not
send Telegram messages, create outbox entries, approve trades, call brokers, or
grant paper execution authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_active_paper_trading_automation import (
    PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES,
)
from orchestrator.paperops_notification_review import (
    PAPEROPS_NOTIFICATION_TYPES,
)


PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION = 1
PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_RUNTIME_ARTIFACT = (
    "paperops_cockpit_notification_upgrade.json"
)
PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_HISTORY = (
    "paperops_cockpit_notification_upgrade_history.jsonl"
)
PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_EVENT_LOG = (
    "paperops_cockpit_notification_upgrade_events.jsonl"
)
PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_EVENT_TYPE = (
    "paperops_cockpit_notification_upgrade_recorded"
)
PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_COMPONENT = (
    "paperops_cockpit_notification_upgrade"
)

PT9_REQUIRED_NOTIFICATION_TYPES: tuple[str, ...] = (
    "paperops_readiness_review",
    "paperops_30_day_operations",
    "active_paper_automation",
    "qctrl_consultation_hold",
    "paper_exit_path",
)

PT9_BOUNDARY = (
    "PT-9 upgrades the cockpit and notification review surface for active "
    "PaperOps. It may expose public-safe Fund Manager readouts, PT-8 active "
    "automation state, the Q-CTRL paper consultation hold, the 30-day run, and "
    "review-only notification previews. It cannot send Telegram messages, "
    "cannot write outbox messages, cannot enable Telegram commands, cannot "
    "submit paper orders, cannot call live endpoints, cannot bypass Q-CTRL, "
    "cannot grant Phase 7 proof credit, cannot enable live capital, and cannot "
    "call brokers."
)

PT9_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_written",
    "event_log_event_count",
    "mode",
    "cockpit_upgrade_ready",
    "notification_upgrade_ready",
    "fund_manager_readout_count",
    "fund_manager_readouts",
    "operator_next_action",
    "paperops_30_day_operations_status",
    "paperops_30_day_operations_run_state",
    "paperops_30_day_operations_active_day_number",
    "paperops_30_day_operations_calendar_days_remaining",
    "paperops_30_day_operations_command_count",
    "paperops_30_day_operations_dashboard_public_safe",
    "active_paper_automation_status",
    "active_paper_automation_enabled",
    "active_paper_automation_qctrl_hold",
    "active_paper_automation_submit_step_allowed",
    "active_paper_automation_poll_step_allowed",
    "active_paper_automation_exit_step_allowed",
    "active_paper_automation_live_endpoint_called_count",
    "notification_status",
    "notification_record_count",
    "notification_eligible_review_count",
    "notification_required_type_count",
    "notification_required_types_present_count",
    "notification_missing_required_types",
    "notification_live_send_allowed_count",
    "notification_command_path_enabled_count",
    "notification_broker_write_allowed_count",
    "notification_paper_order_allowed_count",
    "notification_phase7_proof_credit_allowed",
    "telegram_mode",
    "telegram_send_gate",
    "qctrl_hold_visible",
    "qctrl_hold_reason",
    "paper_submit_visible_as_held",
    "live_capital_enabled",
    "live_endpoint_called_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "outbox_message_written_count",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
    "blockers",
    "blocker_count",
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


def paperops_cockpit_notification_upgrade_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_HISTORY,
        runtime / PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_EVENT_LOG,
    )


def read_latest_paperops_cockpit_notification_upgrade(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_cockpit_notification_upgrade_paths(settings)
    return _read_json(output_path)


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "operations": _read_json(runtime / "paperops_30_day_operations.json"),
        "active_automation": _read_json(
            runtime / "paperops_active_paper_trading_automation.json"
        ),
        "notification": _read_json(runtime / "paperops_notification_review.json"),
        "readiness": _read_json(runtime / "paper_operational_readiness.json"),
    }


def _notification_types(notification: dict[str, Any]) -> set[str]:
    records = notification.get("records", [])
    if not isinstance(records, list):
        return set()
    return {
        str(record.get("notification_type") or "")
        for record in records
        if isinstance(record, dict)
    }


def _operations_observable(operations: dict[str, Any]) -> bool:
    status = operations.get("status")
    return (
        status == "operations_active"
        or (
            status == "invalid"
            and operations.get("run_state") == "active"
            and operations.get("dashboard_mirror_public_safe") is True
            and _int(operations.get("unsafe_write_counter_total")) == 0
        )
    )


def _blockers(
    *,
    operations: dict[str, Any],
    active_automation: dict[str, Any],
    notification: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not _operations_observable(operations):
        blockers.append("paperops_30_day_operations_not_active")
    if operations.get("dashboard_mirror_public_safe") is not True:
        blockers.append("cockpit_dashboard_mirror_not_public_safe")
    if _int(operations.get("paper_operational_cycle_command_count")) < 32:
        blockers.append("paperops_cycle_not_pt9_current")
    if active_automation.get("status") not in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES:
        blockers.append("active_paper_automation_not_ready")
    if active_automation.get("active_paper_trading_automation_enabled") is not True:
        blockers.append("active_paper_automation_not_enabled")
    if (
        active_automation.get("qctrl_consultation_hold_active") is True
        and active_automation.get("paper_submit_step_allowed") is True
    ):
        blockers.append("active_paper_automation_qctrl_hold_bypassed")
    if notification.get("status") != "review_ready":
        blockers.append("notification_review_not_ready")
    missing_types = sorted(
        set(PT9_REQUIRED_NOTIFICATION_TYPES) - _notification_types(notification)
    )
    if missing_types:
        blockers.append("notification_required_types_missing")
    if _int(notification.get("live_send_allowed_count")) != 0:
        blockers.append("notification_live_send_allowed")
    if _int(notification.get("telegram_command_path_enabled_count")) != 0:
        blockers.append("notification_command_path_enabled")
    if _int(notification.get("broker_write_allowed_count")) != 0:
        blockers.append("notification_broker_write_allowed")
    if _int(notification.get("paper_order_allowed_count")) != 0:
        blockers.append("notification_paper_order_allowed")
    if notification.get("phase7_proof_credit_allowed") is True:
        blockers.append("notification_phase7_proof_credit_allowed")
    return sorted(set(blockers))


def _readouts(
    *,
    operations: dict[str, Any],
    active_automation: dict[str, Any],
    notification: dict[str, Any],
    readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "key": "paperops_run",
            "label": "30-day paper run",
            "status": str(operations.get("status") or "missing"),
            "value": (
                f"day {operations.get('active_day_number', 'unknown')} of 30; "
                f"{operations.get('calendar_days_remaining', 'unknown')} days remaining"
            ),
        },
        {
            "key": "active_runner",
            "label": "Active paper runner",
            "status": str(active_automation.get("status") or "missing"),
            "value": (
                f"submit={active_automation.get('paper_submit_step_allowed')}; "
                f"poll={active_automation.get('paper_poll_step_allowed')}; "
                f"exit={active_automation.get('paper_exit_step_allowed')}"
            ),
        },
        {
            "key": "qctrl_hold",
            "label": "Q-CTRL hold",
            "status": "held"
            if active_automation.get("qctrl_consultation_hold_active") is True
            else "clear",
            "value": str(
                active_automation.get("submit_hold_reason")
                or "no submit hold reason exported"
            ),
        },
        {
            "key": "notification_review",
            "label": "Notification review",
            "status": str(notification.get("status") or "missing"),
            "value": (
                f"{notification.get('eligible_review_count', 0)} eligible; "
                f"{notification.get('notification_record_count', 0)} records"
            ),
        },
        {
            "key": "paperops_readiness",
            "label": "PaperOps readiness",
            "status": str(readiness.get("status") or "missing"),
            "value": (
                f"safe={readiness.get('safe_to_continue_paper_only')}; "
                f"blockers={readiness.get('blocker_count', 0)}"
            ),
        },
    ]


def build_paperops_cockpit_notification_upgrade(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    operations = snapshot["operations"]
    active_automation = snapshot["active_automation"]
    notification = snapshot["notification"]
    readiness = snapshot["readiness"]
    notification_types = _notification_types(notification)
    missing_required_types = sorted(
        set(PT9_REQUIRED_NOTIFICATION_TYPES) - notification_types
    )
    blockers = _blockers(
        operations=operations,
        active_automation=active_automation,
        notification=notification,
    )
    unsafe_total = sum(
        _int(value)
        for value in (
            operations.get("unsafe_write_counter_total"),
            active_automation.get("live_endpoint_called_count"),
            active_automation.get("unsafe_write_counter_total"),
            notification.get("live_send_allowed_count"),
            notification.get("telegram_command_path_enabled_count"),
            notification.get("broker_write_allowed_count"),
            notification.get("paper_order_allowed_count"),
            notification.get("live_endpoint_allowed_count"),
            notification.get("live_capital_enabled_count"),
        )
    )
    qctrl_hold = active_automation.get("qctrl_consultation_hold_active") is True
    submit_allowed = active_automation.get("paper_submit_step_allowed") is True
    status = (
        "cockpit_notification_upgrade_ready"
        if not blockers and unsafe_total == 0
        else "blocked_cockpit_notification_upgrade"
    )
    readouts = _readouts(
        operations=operations,
        active_automation=active_automation,
        notification=notification,
        readiness=readiness,
    )
    artifact = {
        "schema_version": PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION,
        "artifact_type": "paperops_cockpit_notification_upgrade",
        "artifact_id": "paperops:pt-9:cockpit-notification-upgrade",
        "phase": "PaperOps",
        "stage": "PT-9",
        "status": status,
        "generated_at": generated_at,
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
        "cockpit_upgrade_ready": status == "cockpit_notification_upgrade_ready",
        "notification_upgrade_ready": notification.get("status") == "review_ready"
        and not missing_required_types,
        "fund_manager_readout_count": len(readouts),
        "fund_manager_readouts": readouts,
        "operator_next_action": (
            "Resolve Q-CTRL product access before PT-8 can delegate paper submit."
            if qctrl_hold
            else "Keep the PaperOps runner active and monitor qualified setups."
        ),
        "paperops_30_day_operations_status": operations.get("status", "missing"),
        "paperops_30_day_operations_run_state": operations.get("run_state", "missing"),
        "paperops_30_day_operations_active_day_number": _int(
            operations.get("active_day_number")
        ),
        "paperops_30_day_operations_calendar_days_remaining": _int(
            operations.get("calendar_days_remaining")
        ),
        "paperops_30_day_operations_command_count": _int(
            operations.get("paper_operational_cycle_command_count")
        ),
        "paperops_30_day_operations_dashboard_public_safe": (
            operations.get("dashboard_mirror_public_safe") is True
        ),
        "active_paper_automation_status": active_automation.get("status", "missing"),
        "active_paper_automation_enabled": (
            active_automation.get("active_paper_trading_automation_enabled") is True
        ),
        "active_paper_automation_qctrl_hold": qctrl_hold,
        "active_paper_automation_submit_step_allowed": submit_allowed,
        "active_paper_automation_poll_step_allowed": (
            active_automation.get("paper_poll_step_allowed") is True
        ),
        "active_paper_automation_exit_step_allowed": (
            active_automation.get("paper_exit_step_allowed") is True
        ),
        "active_paper_automation_live_endpoint_called_count": _int(
            active_automation.get("live_endpoint_called_count")
        ),
        "notification_status": notification.get("status", "missing"),
        "notification_record_count": _int(notification.get("notification_record_count")),
        "notification_eligible_review_count": _int(
            notification.get("eligible_review_count")
        ),
        "notification_required_type_count": len(PT9_REQUIRED_NOTIFICATION_TYPES),
        "notification_required_types_present_count": len(
            set(PT9_REQUIRED_NOTIFICATION_TYPES) & notification_types
        ),
        "notification_missing_required_types": missing_required_types,
        "notification_live_send_allowed_count": _int(
            notification.get("live_send_allowed_count")
        ),
        "notification_command_path_enabled_count": _int(
            notification.get("telegram_command_path_enabled_count")
        ),
        "notification_broker_write_allowed_count": _int(
            notification.get("broker_write_allowed_count")
        ),
        "notification_paper_order_allowed_count": _int(
            notification.get("paper_order_allowed_count")
        ),
        "notification_phase7_proof_credit_allowed": (
            notification.get("phase7_proof_credit_allowed") is True
        ),
        "telegram_mode": notification.get("telegram_mode", "missing"),
        "telegram_send_gate": notification.get("telegram_send_gate", "missing"),
        "qctrl_hold_visible": qctrl_hold,
        "qctrl_hold_reason": str(
            active_automation.get("submit_hold_reason") or "missing"
        ),
        "paper_submit_visible_as_held": qctrl_hold and not submit_allowed,
        "live_capital_enabled": settings.live_capital_enabled,
        "live_endpoint_called_count": _int(active_automation.get("live_endpoint_called_count")),
        "broker_post_called_count": _int(operations.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(operations.get("alpaca_post_called_count")),
        "outbox_message_written_count": 0,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": unsafe_total,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "boundary": PT9_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paperops_cockpit_notification_upgrade(
        artifact
    )
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
        artifact["cockpit_upgrade_ready"] = False
    return artifact


def validate_paperops_cockpit_notification_upgrade(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PT9_PUBLIC_FIELDS) - set(artifact))
    if missing:
        errors.append("paperops_pt9_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION:
        errors.append("paperops_pt9_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_cockpit_notification_upgrade":
        errors.append("paperops_pt9_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-9":
        errors.append("paperops_pt9_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_pt9_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_pt9_not_public_safe")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_pt9_live_capital_enabled")
    if artifact.get("status") not in {
        "cockpit_notification_upgrade_ready",
        "blocked_cockpit_notification_upgrade",
        "invalid",
    }:
        errors.append("paperops_pt9_status_invalid")
    if artifact.get("status") == "cockpit_notification_upgrade_ready":
        if artifact.get("cockpit_upgrade_ready") is not True:
            errors.append("paperops_pt9_cockpit_upgrade_not_ready")
        if artifact.get("notification_upgrade_ready") is not True:
            errors.append("paperops_pt9_notification_upgrade_not_ready")
    operations_observable = artifact.get("paperops_30_day_operations_status") == (
        "operations_active"
    ) or (
        artifact.get("paperops_30_day_operations_status") == "invalid"
        and artifact.get("paperops_30_day_operations_run_state") == "active"
        and artifact.get("paperops_30_day_operations_dashboard_public_safe") is True
        and _int(artifact.get("unsafe_write_counter_total")) == 0
    )
    if not operations_observable:
        errors.append("paperops_pt9_operations_not_active")
    if artifact.get("paperops_30_day_operations_dashboard_public_safe") is not True:
        errors.append("paperops_pt9_dashboard_not_public_safe")
    if _int(artifact.get("paperops_30_day_operations_command_count")) < 32:
        errors.append("paperops_pt9_cycle_command_count_stale")
    if artifact.get("active_paper_automation_status") not in (
        PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES
    ):
        errors.append("paperops_pt9_active_automation_status_invalid")
    if artifact.get("active_paper_automation_enabled") is not True:
        errors.append("paperops_pt9_active_automation_not_enabled")
    if (
        artifact.get("active_paper_automation_qctrl_hold") is True
        and artifact.get("active_paper_automation_submit_step_allowed") is True
    ):
        errors.append("paperops_pt9_qctrl_hold_bypassed")
    if artifact.get("qctrl_hold_visible") is True and artifact.get(
        "paper_submit_visible_as_held"
    ) is not True:
        errors.append("paperops_pt9_submit_hold_not_visible")
    if artifact.get("notification_status") != "review_ready":
        errors.append("paperops_pt9_notification_not_ready")
    if artifact.get("notification_required_types_present_count") != artifact.get(
        "notification_required_type_count"
    ):
        errors.append("paperops_pt9_notification_required_types_missing")
    if artifact.get("notification_missing_required_types"):
        errors.append("paperops_pt9_notification_missing_required_types")
    for key in (
        "active_paper_automation_live_endpoint_called_count",
        "notification_live_send_allowed_count",
        "notification_command_path_enabled_count",
        "notification_broker_write_allowed_count",
        "notification_paper_order_allowed_count",
        "live_endpoint_called_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "outbox_message_written_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_pt9_unsafe_counter_nonzero:{key}")
    if artifact.get("notification_phase7_proof_credit_allowed") is not False:
        errors.append("paperops_pt9_notification_proof_credit_allowed")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("paperops_pt9_proof_credit_allowed")
    if artifact.get("recorded") is True:
        if artifact.get("event_log_written") is not True:
            errors.append("paperops_pt9_event_log_missing")
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("paperops_pt9_event_count_mismatch")
    readouts = artifact.get("fund_manager_readouts", [])
    if not isinstance(readouts, list) or len(readouts) < 5:
        errors.append("paperops_pt9_readouts_missing")
    if _int(artifact.get("fund_manager_readout_count")) != len(readouts):
        errors.append("paperops_pt9_readout_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-9 upgrades the cockpit and notification review surface",
        "review-only notification previews",
        "cannot send Telegram messages",
        "cannot write outbox messages",
        "cannot enable Telegram commands",
        "cannot submit paper orders",
        "cannot call brokers",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_pt9_boundary_weak")
            break
    if artifact.get("validation_error_count") not in {
        None,
        len(artifact.get("validation_errors", [])),
    }:
        errors.append("paperops_pt9_validation_count_mismatch")
    return sorted(set(errors))


def write_paperops_cockpit_notification_upgrade(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = (
        paperops_cockpit_notification_upgrade_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_EVENT_TYPE,
            PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_COMPONENT,
            payload={
                "status": written.get("status"),
                "cockpit_upgrade_ready": written.get("cockpit_upgrade_ready"),
                "notification_upgrade_ready": written.get(
                    "notification_upgrade_ready"
                ),
                "active_paper_automation_status": written.get(
                    "active_paper_automation_status"
                ),
                "qctrl_hold_visible": written.get("qctrl_hold_visible"),
                "notification_record_count": written.get("notification_record_count"),
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
    written["validation_errors"] = validate_paperops_cockpit_notification_upgrade(
        written
    )
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
        written["cockpit_upgrade_ready"] = False
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "cockpit_upgrade_ready": written.get("cockpit_upgrade_ready"),
        "notification_upgrade_ready": written.get("notification_upgrade_ready"),
        "notification_record_count": written.get("notification_record_count"),
        "qctrl_hold_visible": written.get("qctrl_hold_visible"),
        "unsafe_write_counter_total": written.get("unsafe_write_counter_total"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_cockpit_notification_upgrade_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_cockpit_notification_upgrade(settings)
    if not artifact:
        defaults = {field: None for field in PT9_PUBLIC_FIELDS}
        defaults.update(
            {
            "schema_version": PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION,
            "artifact_type": "paperops_cockpit_notification_upgrade",
            "artifact_id": "paperops:pt-9:cockpit-notification-upgrade",
            "phase": "PaperOps",
            "stage": "PT-9",
            "status": "not_run",
            "generated_at": None,
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "cockpit_upgrade_ready": False,
            "notification_upgrade_ready": False,
            "fund_manager_readout_count": 0,
            "fund_manager_readouts": [],
            "operator_next_action": "Run PT-9 cockpit and notification upgrade.",
            "paperops_30_day_operations_status": "not_run",
            "paperops_30_day_operations_run_state": "missing",
            "paperops_30_day_operations_active_day_number": 0,
            "paperops_30_day_operations_calendar_days_remaining": 30,
            "paperops_30_day_operations_command_count": 0,
            "paperops_30_day_operations_dashboard_public_safe": False,
            "active_paper_automation_status": "not_run",
            "active_paper_automation_enabled": False,
            "active_paper_automation_qctrl_hold": False,
            "active_paper_automation_submit_step_allowed": False,
            "active_paper_automation_poll_step_allowed": False,
            "active_paper_automation_exit_step_allowed": False,
            "active_paper_automation_live_endpoint_called_count": 0,
            "notification_status": "not_run",
            "notification_record_count": 0,
            "notification_eligible_review_count": 0,
            "notification_required_type_count": len(PT9_REQUIRED_NOTIFICATION_TYPES),
            "notification_required_types_present_count": 0,
            "notification_missing_required_types": list(PT9_REQUIRED_NOTIFICATION_TYPES),
            "notification_live_send_allowed_count": 0,
            "notification_command_path_enabled_count": 0,
            "notification_broker_write_allowed_count": 0,
            "notification_paper_order_allowed_count": 0,
            "notification_phase7_proof_credit_allowed": False,
            "telegram_mode": "missing",
            "telegram_send_gate": "missing",
            "qctrl_hold_visible": False,
            "qctrl_hold_reason": "missing",
            "paper_submit_visible_as_held": False,
            "live_capital_enabled": False,
            "live_endpoint_called_count": 0,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "outbox_message_written_count": 0,
            "phase7_proof_credit_allowed": False,
            "unsafe_write_counter_total": 0,
            "blockers": ["pt9_not_run"],
            "blocker_count": 1,
            "validation_error_count": 0,
            "boundary": PT9_BOUNDARY,
            }
        )
        return defaults
    public = {field: artifact.get(field) for field in PT9_PUBLIC_FIELDS}
    public["blockers"] = list(public.get("blockers") or [])
    public["fund_manager_readouts"] = list(public.get("fund_manager_readouts") or [])
    public["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return public
