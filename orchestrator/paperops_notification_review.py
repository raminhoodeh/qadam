"""PaperOps-5 notification and review contract.

This stage turns PaperOps lifecycle state into public-safe notification review
records. It does not send Telegram messages, handle Telegram commands, approve
trades, submit orders, close positions, or enable live capital.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.phase5_telegram_notifier import telegram_send_test_approval_path
from orchestrator.telegram_comms import (
    FORBIDDEN_TELEGRAM_TEXT,
    TELEGRAM_MESSAGE_CLASSES,
    TelegramCommunicationsStore,
    render_telegram_message,
)
from orchestrator.telegram_message_quality import telegram_human_message_style


PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION = 1
PAPEROPS_NOTIFICATION_REVIEW_RUNTIME_ARTIFACT = "paperops_notification_review.json"
PAPEROPS_NOTIFICATION_REVIEW_HISTORY = "paperops_notification_review_history.jsonl"
PAPEROPS_NOTIFICATION_REVIEW_EVENT_LOG = "paperops_notification_review_events.jsonl"
PAPEROPS_NOTIFICATION_REVIEW_EVENT_TYPE = "paperops_notification_review_recorded"
PAPEROPS_NOTIFICATION_REVIEW_COMPONENT = "paperops_notification_review"

PAPEROPS_NOTIFICATION_TYPES: tuple[str, ...] = (
    "paperops_readiness_review",
    "paperops_30_day_operations",
    "active_paper_automation",
    "qctrl_consultation_hold",
    "submitted_paper_order",
    "broker_receipt",
    "open_position",
    "paper_exit_path",
    "closed_trade",
    "postmortem_due",
)

PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES = frozenset(
    {
        "submitted_paper_order",
        "broker_receipt",
        "open_position",
        "paper_exit_path",
        "closed_trade",
        "postmortem_due",
    }
)

NOTIFICATION_MESSAGE_CLASSES: dict[str, str] = {
    "paperops_readiness_review": "insight_digest",
    "paperops_30_day_operations": "insight_digest",
    "active_paper_automation": "insight_digest",
    "qctrl_consultation_hold": "insight_digest",
    "submitted_paper_order": "submitted_paper_order",
    "broker_receipt": "submitted_paper_order",
    "open_position": "open_position",
    "paper_exit_path": "insight_digest",
    "closed_trade": "closed_trade",
    "postmortem_due": "postmortem_due",
}

NOTIFICATION_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_place_trade_command_enabled",
    "telegram_approve_trade_command_enabled",
    "telegram_reject_trade_command_enabled",
    "telegram_modify_trade_command_enabled",
    "telegram_resize_trade_command_enabled",
    "telegram_close_trade_command_enabled",
    "telegram_cancel_trade_command_enabled",
    "telegram_live_notifications_allowed",
    "normal_live_notification_allowed",
    "live_send_allowed",
    "trade_candidate_created",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "secret_value_exposed",
    "raw_payload_exposed",
    "raw_broker_payload_exposed",
    "authorization_header_exposed",
    "chat_id_exposed",
    "bot_token_exposed",
    "telegram_handle_exposed",
    "broker_order_identifier_exposed",
)

NOTIFICATION_COUNT_FIELDS: tuple[str, ...] = (
    "telegram_command_path_enabled_count",
    "telegram_trade_command_enabled_count",
    "telegram_place_trade_command_enabled_count",
    "telegram_approve_trade_command_enabled_count",
    "telegram_reject_trade_command_enabled_count",
    "telegram_modify_trade_command_enabled_count",
    "telegram_resize_trade_command_enabled_count",
    "telegram_close_trade_command_enabled_count",
    "telegram_cancel_trade_command_enabled_count",
    "telegram_live_notifications_allowed_count",
    "normal_live_notification_allowed_count",
    "live_send_allowed_count",
    "broker_write_allowed_count",
    "broker_post_allowed_count",
    "alpaca_post_allowed_count",
    "paper_order_allowed_count",
    "paper_order_submission_allowed_count",
    "execution_allowed_count",
    "position_close_allowed_count",
    "position_resize_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "authorization_header_exposed_count",
    "chat_id_exposed_count",
    "bot_token_exposed_count",
)

PAPEROPS_NOTIFICATION_BOUNDARY = (
    "PaperOps-5 converts PaperOps paper lifecycle state into notification and "
    "review records. Telegram remains notify-only: it cannot approve, reject, "
    "modify, close, resize, cancel, or place trades; it cannot submit paper "
    "orders, write brokers, call live endpoints, expose secrets or chat ids, "
    "grant Phase 7 proof credit, or enable live capital. Live-send for paper "
    "lifecycle notifications requires a separate explicit send-test approval "
    "and is not used by the default PaperOps cycle."
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


def paperops_notification_review_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_NOTIFICATION_REVIEW_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_NOTIFICATION_REVIEW_HISTORY,
        runtime / PAPEROPS_NOTIFICATION_REVIEW_EVENT_LOG,
    )


def read_latest_paperops_notification_review(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_notification_review_paths(settings)
    return _read_json(output_path)


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "paper_operational_mode": _read_json(runtime / "paper_operational_mode.json"),
        "readiness": _read_json(runtime / "paper_operational_readiness.json"),
        "qctrl": _read_json(runtime / "paperops_qctrl_paper_consultation.json"),
        "alpaca_post": _read_json(runtime / "paperops_alpaca_paper_post.json"),
        "lifecycle_poller": _read_json(runtime / "paperops_paper_lifecycle_poller.json"),
        "exit_path": _read_json(runtime / "paperops_paper_exit_path.json"),
        "paperops_30_day_operations": _read_json(
            runtime / "paperops_30_day_operations.json"
        ),
        "active_paper_automation": _read_json(
            runtime / "paperops_active_paper_trading_automation.json"
        ),
        "paper_live_qctrl_product_access": _read_json(
            runtime / "paper_live_qctrl_product_access.json"
        ),
        "phase7_lifecycle": _read_json(runtime / "phase7_proof_lifecycle_monitor.json"),
        "phase7_postmortem": _read_json(runtime / "phase7_proof_postmortem_contract.json"),
    }


def _derived_blockers(settings: Settings, source: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    paper_operational_mode = source["paper_operational_mode"]
    qctrl = source["qctrl"]
    alpaca_post = source["alpaca_post"]
    exit_path = source["exit_path"]
    paper_operational_mode_effective = (
        paper_operational_mode.get("status") == "enabled_pending_downstream_gates"
        and paper_operational_mode.get("paper_operational_mode_effective") is True
        and paper_operational_mode.get("paper_order_submission_allowed") is False
        and paper_operational_mode.get("broker_post_allowed") is False
        and paper_operational_mode.get("live_capital_enabled") is False
        and paper_operational_mode.get("phase7_proof_credit_allowed") is False
    )
    if not settings.paper_operational_enabled and not paper_operational_mode_effective:
        blockers.append("paper_operational_flag_disabled")
    if (
        settings.quantum_paper_parity_required
        and (
            not settings.qctrl_paper_consultation_enabled
            or qctrl.get("status") != "consultation_recorded"
            or qctrl.get("provider_call_recorded") is not True
        )
    ):
        blockers.append("qctrl_paper_consultation_connected_not_ready")
    if (
        not settings.alpaca_paper_submit_enabled
        or alpaca_post.get("status")
        not in {
            "ready_no_eligible_order",
            "ready_pending_explicit_execute",
            "submitted_to_alpaca_paper",
        }
    ):
        blockers.append("external_alpaca_paper_post_enabled_not_ready")
    if (
        not settings.alpaca_paper_exit_enabled
        or exit_path.get("status")
        not in {
            "ready_no_exit_candidate",
            "ready_pending_explicit_execute",
            "paper_exit_close_recorded",
        }
    ):
        blockers.append("paper_exit_path_connected_not_ready")
    return blockers


def _send_test_gate(settings: Settings) -> dict[str, Any]:
    approval = _read_json(telegram_send_test_approval_path(settings))
    if not approval:
        return {
            "approval_present": False,
            "approval_logged": False,
            "approval_state": "missing",
            "approval_scope": "paper_lifecycle_notifications_only",
            "explicit_send_test_approval": False,
            "paper_lifecycle_live_send_test_allowed": False,
            "live_send_allowed": False,
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "position_close_allowed": False,
            "position_resize_allowed": False,
            "live_capital_enabled": False,
            "boundary": (
                "No explicit PaperOps-5 send-test approval is present; live "
                "Telegram delivery remains blocked."
            ),
        }
    scope = str(approval.get("approval_scope") or approval.get("scope") or "")
    state = str(approval.get("approval_state") or approval.get("state") or "unknown")
    explicit = (
        state == "approved"
        and scope
        in {
            "paper_lifecycle_notifications_only",
            "private_send_test_only",
        }
        and approval.get("approval_logged") is True
        and approval.get("telegram_command_path_enabled") is not True
        and approval.get("broker_write_allowed") is not True
        and approval.get("paper_order_allowed") is not True
        and approval.get("position_close_allowed") is not True
        and approval.get("position_resize_allowed") is not True
        and approval.get("live_capital_enabled") is not True
    )
    return {
        "approval_present": True,
        "approval_logged": approval.get("approval_logged") is True,
        "approval_state": state,
        "approval_scope": scope or "unknown",
        "explicit_send_test_approval": explicit,
        "paper_lifecycle_live_send_test_allowed": explicit,
        "live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "live_capital_enabled": False,
        "boundary": (
            "The approval can allow a separate PaperOps notification send test "
            "only. It does not enable commands, trade approval, broker writes, "
            "position mutation, normal live notifications, or live capital."
        ),
    }


def _source_count(
    notification_type: str,
    *,
    source: dict[str, dict[str, Any]],
    blockers: list[str],
) -> tuple[int, str, str]:
    alpaca_post = source["alpaca_post"]
    lifecycle = source["lifecycle_poller"]
    exit_path = source["exit_path"]
    operations = source["paperops_30_day_operations"]
    active_automation = source["active_paper_automation"]
    product_access = source["paper_live_qctrl_product_access"]
    phase7_lifecycle = source["phase7_lifecycle"]
    postmortem = source["phase7_postmortem"]
    if notification_type == "paperops_readiness_review":
        return max(1, len(blockers)), "paper_operational_readiness", "PaperOps readiness"
    if notification_type == "paperops_30_day_operations":
        count = 1 if operations.get("status") == "operations_active" else 0
        return count, "paperops_30_day_operations", "30-day paper run"
    if notification_type == "active_paper_automation":
        count = 1 if str(active_automation.get("status") or "").startswith(
            "active_automation_"
        ) else 0
        return count, "paperops_active_paper_trading_automation", "active paper automation"
    if notification_type == "qctrl_consultation_hold":
        count = 1 if (
            active_automation.get("qctrl_consultation_hold_active") is True
            or product_access.get("status")
            in {
                "blocked_qctrl_product_access_or_subscription",
                "blocked_missing_qctrl_sdk",
            }
        ) else 0
        return count, "paper_live_qctrl_product_access", "Q-CTRL paper consultation hold"
    if notification_type == "submitted_paper_order":
        count = max(
            _int(alpaca_post.get("alpaca_paper_post_succeeded_count")),
            _int(lifecycle.get("source_submitted_paper_order_count")),
            _int(phase7_lifecycle.get("paper_order_submitted_count")),
        )
        return count, "paperops_alpaca_paper_post", "submitted paper order"
    if notification_type == "broker_receipt":
        count = max(
            _int(alpaca_post.get("broker_submit_receipt_created_count")),
            _int(phase7_lifecycle.get("broker_submit_receipt_created_count")),
        )
        return count, "paperops_alpaca_paper_post", "broker receipt"
    if notification_type == "open_position":
        count = max(
            _int(lifecycle.get("open_position_count")),
            _int(phase7_lifecycle.get("open_position_count")),
        )
        return count, "paperops_paper_lifecycle_poller", "open paper position"
    if notification_type == "paper_exit_path":
        count = 1 if exit_path.get("status") else 0
        return count, "paperops_paper_exit_path", "paper exit path"
    if notification_type == "closed_trade":
        count = max(
            _int(lifecycle.get("closed_trade_count")),
            _int(phase7_lifecycle.get("closed_proof_trade_count")),
        )
        return count, "phase7_proof_lifecycle_monitor", "closed proof trade"
    if notification_type == "postmortem_due":
        count = max(
            _int(postmortem.get("postmortem_due_count")),
            _int(phase7_lifecycle.get("postmortem_due_count")),
            _int(phase7_lifecycle.get("postmortem_due_marker_created_count")),
        )
        return count, "phase7_proof_postmortem_contract", "postmortem due"
    return 0, "unknown", "unknown"


def _message_context(
    notification_type: str,
    *,
    source_count: int,
    source_ref: str,
    source_label: str,
    blockers: list[str],
    source: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if notification_type == "paperops_readiness_review":
        readiness = source["readiness"]
        blocker_text = ", ".join(blockers[:4]) or "no blockers"
        return {
            "title": "PaperOps review: current operating state",
            "theme": "PaperOps notification review",
            "why_it_matters": (
                f"safe_to_continue={readiness.get('safe_to_continue_paper_only', True)}"
            ),
            "evidence": f"blocker_count={len(blockers)}; {blocker_text}",
            "block": "full paper operation remains blocked until explicit gates clear",
        }
    if notification_type == "paperops_30_day_operations":
        operations = source["paperops_30_day_operations"]
        return {
            "title": "PaperOps review: 30-day run operations",
            "theme": "30-day paper run operations",
            "why_it_matters": (
                f"run={operations.get('run_id', 'missing')}; "
                f"day={operations.get('active_day_number', 'unknown')}; "
                f"remaining={operations.get('calendar_days_remaining', 'unknown')}"
            ),
            "evidence": (
                f"cycle={operations.get('paper_operational_cycle_status', 'missing')}; "
                f"commands={operations.get('paper_operational_cycle_command_count', 0)}; "
                f"qualified={operations.get('qualified_setup_count', 0)}"
            ),
            "block": "paper run stays calendar-true; trades occur only where qualified setups exist",
        }
    if notification_type == "active_paper_automation":
        active_automation = source["active_paper_automation"]
        return {
            "title": "PaperOps review: active paper automation",
            "theme": "guarded active paper automation",
            "why_it_matters": (
                f"status={active_automation.get('status', 'missing')}; "
                f"enabled={active_automation.get('active_paper_trading_automation_enabled')}"
            ),
            "evidence": (
                f"submit_allowed={active_automation.get('paper_submit_step_allowed')}; "
                f"poll_allowed={active_automation.get('paper_poll_step_allowed')}; "
                f"exit_allowed={active_automation.get('paper_exit_step_allowed')}"
            ),
            "block": "active runner can only delegate to recorded PaperOps paper gates",
        }
    if notification_type == "qctrl_consultation_hold":
        active_automation = source["active_paper_automation"]
        product_access = source["paper_live_qctrl_product_access"]
        return {
            "title": "PaperOps review: Q-CTRL paper consultation hold",
            "theme": "Head of Quant paper parity hold",
            "why_it_matters": (
                f"product_access={product_access.get('status', 'missing')}; "
                f"hold={active_automation.get('qctrl_consultation_hold_active')}"
            ),
            "evidence": (
                f"provider_calls={product_access.get('provider_call_count', 0)}; "
                f"submit_allowed={active_automation.get('paper_submit_step_allowed')}"
            ),
            "block": "paper submit remains held until Q-CTRL consultation access is ready",
        }
    if notification_type == "paper_exit_path":
        exit_path = source["exit_path"]
        return {
            "title": "PaperOps review: paper exit path",
            "theme": "guarded paper exit path",
            "why_it_matters": f"exit_status={exit_path.get('status', 'missing')}",
            "evidence": (
                "open_position_readbacks="
                f"{_int(exit_path.get('open_position_readback_count'))}; "
                f"close_calls={_int(exit_path.get('paper_position_close_called_count'))}"
            ),
            "block": "paper exits require explicit flag and remain notify-only here",
        }
    if notification_type == "submitted_paper_order":
        return {
            "instrument": "Alpaca paper proof order",
            "catalyst": f"{source_count} submitted paper order state(s) observed",
            "evidence_summary": f"source={source_ref}",
        }
    if notification_type == "broker_receipt":
        return {
            "instrument": "Alpaca paper broker receipt",
            "catalyst": f"{source_count} sanitized broker receipt(s) observed",
            "evidence_summary": f"source={source_ref}; identifiers remain hashed",
        }
    if notification_type == "open_position":
        return {
            "subject": "paper position lifecycle",
            "title": "PaperOps: open paper position",
            "catalyst": f"{source_count} open paper position state(s) observed",
            "evidence_summary": f"source={source_ref}",
        }
    if notification_type == "closed_trade":
        return {
            "subject": "closed paper trade",
            "title": "PaperOps: closed proof trade",
            "catalyst": f"{source_count} closed proof trade state(s) observed",
            "evidence_summary": f"source={source_ref}",
        }
    if notification_type == "postmortem_due":
        return {
            "subject": "postmortem due marker",
            "title": "PaperOps: postmortem due",
            "catalyst": f"{source_count} postmortem due marker(s) observed",
            "evidence_summary": f"source={source_ref}",
        }
    return {
        "title": f"PaperOps: {source_label}",
        "subject": source_label,
        "why_it_matters": "paper lifecycle state changed",
        "evidence": f"source={source_ref}",
        "block": "notification only",
    }


def _safe_preview(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def _notification_record(
    notification_type: str,
    *,
    generated_at: str,
    source: dict[str, dict[str, Any]],
    blockers: list[str],
    send_test_gate: dict[str, Any],
) -> dict[str, Any]:
    source_count, source_ref, source_label = _source_count(
        notification_type,
        source=source,
        blockers=blockers,
    )
    message_class = NOTIFICATION_MESSAGE_CLASSES[notification_type]
    context = _message_context(
        notification_type,
        source_count=source_count,
        source_ref=source_ref,
        source_label=source_label,
        blockers=blockers,
        source=source,
    )
    title, body = render_telegram_message(message_class, context)
    eligible = source_count > 0
    record = {
        "schema_version": PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION,
        "artifact_type": "paperops_notification_review_record",
        "artifact_id": f"paperops:notification-review:{notification_type}",
        "phase": "PaperOps",
        "stage": "PaperOps-5",
        "status": "eligible_for_review" if eligible else "suppressed_no_matching_backend_state",
        "generated_at": generated_at,
        "public_safe": True,
        "notification_type": notification_type,
        "message_class": message_class,
        "is_lifecycle_notification": notification_type in PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES,
        "source_ref": source_ref,
        "source_label": source_label,
        "source_state_count": source_count,
        "backend_state_matched": eligible,
        "message_preview": {
            "title": title,
            "body": body,
            "dashboard_link": "qadam.trade/dashboard/",
        },
        "message_preview_redacted": _safe_preview(title, body),
        "send_test_required_before_live": True,
        "send_test_gate": send_test_gate,
        "paper_lifecycle_live_send_test_allowed": (
            send_test_gate.get("paper_lifecycle_live_send_test_allowed") is True
        ),
        "normal_live_notification_allowed": False,
        "live_send_allowed": False,
        "delivery_mode": "review_only",
        "outbox_message_written": False,
        "outbox_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "telegram_place_trade_command_enabled": False,
        "telegram_approve_trade_command_enabled": False,
        "telegram_reject_trade_command_enabled": False,
        "telegram_modify_trade_command_enabled": False,
        "telegram_resize_trade_command_enabled": False,
        "telegram_close_trade_command_enabled": False,
        "telegram_cancel_trade_command_enabled": False,
        "telegram_live_notifications_allowed": False,
        "trade_candidate_created": False,
        "risk_approval_allowed": False,
        "execution_allowed": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_write_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "order_cancel_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "chat_id_exposed": False,
        "bot_token_exposed": False,
        "telegram_handle_exposed": False,
        "broker_order_identifier_exposed": False,
        "boundary": PAPEROPS_NOTIFICATION_BOUNDARY,
    }
    record["validation_errors"] = validate_paperops_notification_record(record)
    return record


def build_paperops_notification_review(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    source = _source_snapshot(settings)
    blockers = _derived_blockers(settings, source)
    send_test_gate = _send_test_gate(settings)
    telegram_status = TelegramCommunicationsStore(settings=settings).public_status()
    records = [
        _notification_record(
            notification_type,
            generated_at=generated_at,
            source=source,
            blockers=blockers,
            send_test_gate=send_test_gate,
        )
        for notification_type in PAPEROPS_NOTIFICATION_TYPES
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    source_counts = {
        record["notification_type"]: record["source_state_count"] for record in records
    }
    artifact = {
        "schema_version": PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION,
        "artifact_type": "paperops_notification_review",
        "artifact_id": "paperops:notification-review:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-5",
        "status": "review_ready",
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
        "paper_operational_enabled": (
            settings.paper_operational_enabled
            or source["paper_operational_mode"].get("paper_operational_mode_effective")
            is True
        ),
        "settings_paper_operational_enabled": settings.paper_operational_enabled,
        "paper_operational_mode_status": source["paper_operational_mode"].get(
            "status",
            "missing",
        ),
        "paper_operational_mode_effective": (
            source["paper_operational_mode"].get("paper_operational_mode_effective")
            is True
        ),
        "live_capital_enabled": settings.live_capital_enabled,
        "telegram_status": telegram_status.get("status", "unknown"),
        "telegram_mode": telegram_status.get("mode", "unknown"),
        "telegram_send_gate": telegram_status.get("send_gate", "unknown"),
        "telegram_bot_configured": telegram_status.get("bot_configured") is True,
        "telegram_delivery_target_count": _int(telegram_status.get("delivery_target_count")),
        "send_test_gate_state": send_test_gate.get("approval_state", "missing"),
        "send_test_approval_present": send_test_gate.get("approval_present") is True,
        "send_test_approval_logged": send_test_gate.get("approval_logged") is True,
        "private_send_test_allowed": (
            send_test_gate.get("paper_lifecycle_live_send_test_allowed") is True
        ),
        "paper_lifecycle_live_send_test_allowed": (
            send_test_gate.get("paper_lifecycle_live_send_test_allowed") is True
        ),
        "normal_live_notification_allowed": False,
        "notification_type_count": len(PAPEROPS_NOTIFICATION_TYPES),
        "lifecycle_notification_type_count": len(PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES),
        "notification_record_count": len(records),
        "eligible_review_count": status_counts.get("eligible_for_review", 0),
        "suppressed_notification_count": status_counts.get(
            "suppressed_no_matching_backend_state",
            0,
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "source_state_counts": source_counts,
        "source_paperops_30_day_operations_count": source_counts[
            "paperops_30_day_operations"
        ],
        "source_active_paper_automation_count": source_counts[
            "active_paper_automation"
        ],
        "source_qctrl_consultation_hold_count": source_counts[
            "qctrl_consultation_hold"
        ],
        "paperops_blocker_count": len(blockers),
        "paperops_blockers": blockers,
        "safe_to_continue_paper_only": (
            source["readiness"].get("safe_to_continue_paper_only") is not False
        ),
        "readiness_status": source["readiness"].get("status", "missing"),
        "alpaca_paper_post_status": source["alpaca_post"].get("status", "missing"),
        "lifecycle_poller_status": source["lifecycle_poller"].get("status", "missing"),
        "exit_path_status": source["exit_path"].get("status", "missing"),
        "source_submitted_paper_order_count": source_counts["submitted_paper_order"],
        "source_broker_receipt_count": source_counts["broker_receipt"],
        "source_open_position_count": source_counts["open_position"],
        "source_closed_trade_count": source_counts["closed_trade"],
        "source_postmortem_due_count": source_counts["postmortem_due"],
        "source_exit_path_state_count": source_counts["paper_exit_path"],
        "records": records,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "telegram_live_notifications_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "live_send_allowed": False,
        "live_endpoint_allowed": False,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "authorization_header_exposed": False,
        "chat_id_exposed": False,
        "bot_token_exposed": False,
        "broker_order_identifier_exposed": False,
        "boundary": PAPEROPS_NOTIFICATION_BOUNDARY,
    }
    for field in NOTIFICATION_AUTHORITY_FALSE_FIELDS:
        artifact.setdefault(field, False)
    for field in NOTIFICATION_COUNT_FIELDS:
        source_field = field.removesuffix("_count")
        artifact[field] = sum(1 for record in records if record.get(source_field) is True)
    artifact["validation_errors"] = validate_paperops_notification_review(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_notification_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "backend_state_matched",
        "boundary",
        "delivery_mode",
        "is_lifecycle_notification",
        "live_send_allowed",
        "message_class",
        "message_preview",
        "message_preview_redacted",
        "notification_type",
        "outbox_message_written",
        "phase",
        "public_safe",
        "send_test_required_before_live",
        "source_ref",
        "source_state_count",
        "stage",
        "status",
    }
    missing = sorted(required - set(record))
    if missing:
        errors.append("paperops_notification_record_missing_fields:" + ",".join(missing))
    if record.get("artifact_type") != "paperops_notification_review_record":
        errors.append("paperops_notification_record_type_mismatch")
    if record.get("phase") != "PaperOps" or record.get("stage") != "PaperOps-5":
        errors.append("paperops_notification_record_phase_stage_mismatch")
    if record.get("public_safe") is not True:
        errors.append("paperops_notification_record_not_public_safe")
    notification_type = str(record.get("notification_type") or "")
    if notification_type not in PAPEROPS_NOTIFICATION_TYPES:
        errors.append("paperops_notification_type_invalid")
    if record.get("message_class") != NOTIFICATION_MESSAGE_CLASSES.get(notification_type):
        errors.append("paperops_notification_message_class_mismatch")
    if record.get("message_class") not in TELEGRAM_MESSAGE_CLASSES:
        errors.append("paperops_notification_message_class_invalid")
    if record.get("is_lifecycle_notification") != (
        notification_type in PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES
    ):
        errors.append("paperops_notification_lifecycle_flag_mismatch")
    source_count = _int(record.get("source_state_count"))
    if record.get("status") == "eligible_for_review":
        if source_count <= 0:
            errors.append("paperops_notification_eligible_without_source_state")
        if record.get("backend_state_matched") is not True:
            errors.append("paperops_notification_eligible_backend_not_matched")
    elif record.get("status") == "suppressed_no_matching_backend_state":
        if source_count != 0:
            errors.append("paperops_notification_suppressed_with_source_state")
    else:
        errors.append("paperops_notification_status_invalid")
    if record.get("delivery_mode") != "review_only":
        errors.append("paperops_notification_delivery_mode_not_review_only")
    if record.get("send_test_required_before_live") is not True:
        errors.append("paperops_notification_send_test_not_required")
    if record.get("outbox_message_written") is not False:
        errors.append("paperops_notification_outbox_written")
    if record.get("outbox_send_allowed") is not False:
        errors.append("paperops_notification_outbox_send_allowed")
    preview = record.get("message_preview", {})
    if not isinstance(preview, dict):
        errors.append("paperops_notification_preview_missing")
    else:
        title = str(preview.get("title") or "")
        body = str(preview.get("body") or "")
        if not title.strip() or not body.strip():
            errors.append("paperops_notification_preview_empty")
        style = telegram_human_message_style(title, body)
        if style["status"] != "human":
            errors.append("paperops_notification_preview_not_human:" + ",".join(style["errors"]))
        for phrase in ("Dashboard:", "Evidence:", "Status:", "Mode:", "What changed:"):
            if phrase in body:
                errors.append("paperops_notification_preview_too_verbose:" + phrase)
        if not _safe_preview(title, body):
            errors.append("paperops_notification_preview_forbidden_text")
    if record.get("message_preview_redacted") is not True:
        errors.append("paperops_notification_preview_not_redacted")
    gate = record.get("send_test_gate", {})
    if not isinstance(gate, dict):
        errors.append("paperops_notification_send_test_gate_missing")
    else:
        for field in (
            "live_send_allowed",
            "telegram_command_path_enabled",
            "broker_write_allowed",
            "paper_order_allowed",
            "position_close_allowed",
            "position_resize_allowed",
            "live_capital_enabled",
        ):
            if gate.get(field) is not False:
                errors.append(f"paperops_notification_send_gate_authority:{field}")
    for field in NOTIFICATION_AUTHORITY_FALSE_FIELDS:
        if record.get(field) is not False:
            errors.append(f"paperops_notification_authority_enabled:{field}")
    if "Telegram remains notify-only" not in str(record.get("boundary") or ""):
        errors.append("paperops_notification_record_boundary_weak")
    return sorted(set(errors))


def validate_paperops_notification_review(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "boundary",
        "event_log_required",
        "event_log_written",
        "live_capital_enabled",
        "mode",
        "notification_record_count",
        "notification_type_count",
        "paperops_blocker_count",
        "phase",
        "public_safe",
        "records",
        "recorded",
        "schema_version",
        "send_test_gate_state",
        "stage",
        "status",
        "telegram_mode",
        "telegram_send_gate",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_notification_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION:
        errors.append("paperops_notification_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_notification_review":
        errors.append("paperops_notification_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-5":
        errors.append("paperops_notification_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_notification_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_notification_not_public_safe")
    if artifact.get("status") not in {"review_ready", "invalid"}:
        errors.append("paperops_notification_status_invalid")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_notification_live_capital_enabled")
    if artifact.get("telegram_mode") != "dry_run":
        errors.append("paperops_notification_telegram_mode_not_dry_run")
    if artifact.get("telegram_send_gate") != "disabled":
        errors.append("paperops_notification_telegram_send_gate_not_disabled")
    records = artifact.get("records", [])
    if not isinstance(records, list):
        errors.append("paperops_notification_records_not_list")
        records = []
    if artifact.get("notification_type_count") != len(PAPEROPS_NOTIFICATION_TYPES):
        errors.append("paperops_notification_type_count_mismatch")
    if artifact.get("lifecycle_notification_type_count") != len(
        PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES
    ):
        errors.append("paperops_notification_lifecycle_type_count_mismatch")
    if artifact.get("notification_record_count") != len(records):
        errors.append("paperops_notification_record_count_mismatch")
    record_types = {
        str(record.get("notification_type") or "")
        for record in records
        if isinstance(record, dict)
    }
    missing_types = sorted(set(PAPEROPS_NOTIFICATION_TYPES) - record_types)
    if missing_types:
        errors.append("paperops_notification_missing_types:" + ",".join(missing_types))
    status_counts = Counter(
        str(record.get("status") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    if artifact.get("eligible_review_count") != status_counts.get("eligible_for_review", 0):
        errors.append("paperops_notification_eligible_count_mismatch")
    if artifact.get("suppressed_notification_count") != status_counts.get(
        "suppressed_no_matching_backend_state",
        0,
    ):
        errors.append("paperops_notification_suppressed_count_mismatch")
    if _int(artifact.get("eligible_review_count")) < 1:
        errors.append("paperops_notification_expected_review_missing")
    if artifact.get("recorded") is True:
        if artifact.get("event_log_written") is not True:
            errors.append("paperops_notification_event_log_missing")
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("paperops_notification_event_log_count_mismatch")
    for field in NOTIFICATION_AUTHORITY_FALSE_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"paperops_notification_authority_enabled:{field}")
    for field in NOTIFICATION_COUNT_FIELDS:
        if _int(artifact.get(field)) != 0:
            errors.append(f"paperops_notification_unsafe_count_nonzero:{field}")
    if artifact.get("private_send_test_allowed") is True and artifact.get(
        "send_test_approval_logged"
    ) is not True:
        errors.append("paperops_notification_send_test_allowed_without_logged_approval")
    if (
        "cannot approve, reject, modify, close, resize, cancel, or place trades"
        not in str(artifact.get("boundary") or "")
    ):
        errors.append("paperops_notification_boundary_weak")
    for record in records:
        if isinstance(record, dict):
            errors.extend(validate_paperops_notification_record(record))
        else:
            errors.append("paperops_notification_record_invalid")
    return sorted(set(errors))


def write_paperops_notification_review(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_notification_review_paths(
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
            PAPEROPS_NOTIFICATION_REVIEW_EVENT_TYPE,
            PAPEROPS_NOTIFICATION_REVIEW_COMPONENT,
            payload={
                "status": written["status"],
                "notification_record_count": written["notification_record_count"],
                "eligible_review_count": written["eligible_review_count"],
                "suppressed_notification_count": written["suppressed_notification_count"],
                "paperops_blocker_count": written["paperops_blocker_count"],
                "telegram_send_gate": written["telegram_send_gate"],
                "live_send_allowed_count": written["live_send_allowed_count"],
                "telegram_command_path_enabled_count": written[
                    "telegram_command_path_enabled_count"
                ],
                "broker_write_allowed_count": written["broker_write_allowed_count"],
                "paper_order_allowed_count": written["paper_order_allowed_count"],
                "live_capital_enabled": written["live_capital_enabled"],
                "boundary": written["boundary"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_notification_review(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "notification_record_count": written.get("notification_record_count"),
        "eligible_review_count": written.get("eligible_review_count"),
        "suppressed_notification_count": written.get("suppressed_notification_count"),
        "paperops_blocker_count": written.get("paperops_blocker_count"),
        "live_send_allowed_count": written.get("live_send_allowed_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_notification_review_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_notification_review(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-5",
            "public_safe": True,
            "recorded": False,
            "notification_record_count": 0,
            "eligible_review_count": 0,
            "suppressed_notification_count": 0,
            "paperops_blocker_count": 0,
            "telegram_mode": "dry_run",
            "telegram_send_gate": "disabled",
            "send_test_gate_state": "missing",
            "private_send_test_allowed": False,
            "normal_live_notification_allowed": False,
            "live_send_allowed_count": 0,
            "telegram_command_path_enabled_count": 0,
            "broker_write_allowed_count": 0,
            "paper_order_allowed_count": 0,
            "live_endpoint_allowed_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "secret_value_exposed": False,
            "raw_payload_exposed": False,
            "authorization_header_exposed": False,
            "chat_id_exposed": False,
            "bot_token_exposed": False,
            "boundary": PAPEROPS_NOTIFICATION_BOUNDARY,
        }
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "stage": artifact.get("stage"),
        "public_safe": artifact.get("public_safe") is True,
        "recorded": artifact.get("recorded") is True,
        "event_log_written": artifact.get("event_log_written") is True,
        "event_log_event_count": artifact.get("event_log_event_count", 0),
        "validation_error_count": len(artifact.get("validation_errors", [])),
        "notification_type_count": artifact.get("notification_type_count", 0),
        "lifecycle_notification_type_count": artifact.get(
            "lifecycle_notification_type_count",
            0,
        ),
        "notification_record_count": artifact.get("notification_record_count", 0),
        "eligible_review_count": artifact.get("eligible_review_count", 0),
        "suppressed_notification_count": artifact.get("suppressed_notification_count", 0),
        "paperops_blocker_count": artifact.get("paperops_blocker_count", 0),
        "paperops_blockers": artifact.get("paperops_blockers", []),
        "source_submitted_paper_order_count": artifact.get(
            "source_submitted_paper_order_count",
            0,
        ),
        "source_broker_receipt_count": artifact.get("source_broker_receipt_count", 0),
        "source_paperops_30_day_operations_count": artifact.get(
            "source_paperops_30_day_operations_count",
            0,
        ),
        "source_active_paper_automation_count": artifact.get(
            "source_active_paper_automation_count",
            0,
        ),
        "source_qctrl_consultation_hold_count": artifact.get(
            "source_qctrl_consultation_hold_count",
            0,
        ),
        "source_open_position_count": artifact.get("source_open_position_count", 0),
        "source_closed_trade_count": artifact.get("source_closed_trade_count", 0),
        "source_postmortem_due_count": artifact.get("source_postmortem_due_count", 0),
        "source_exit_path_state_count": artifact.get("source_exit_path_state_count", 0),
        "telegram_status": artifact.get("telegram_status", "unknown"),
        "telegram_mode": artifact.get("telegram_mode", "unknown"),
        "telegram_send_gate": artifact.get("telegram_send_gate", "unknown"),
        "send_test_gate_state": artifact.get("send_test_gate_state", "missing"),
        "send_test_approval_present": artifact.get("send_test_approval_present") is True,
        "send_test_approval_logged": artifact.get("send_test_approval_logged") is True,
        "private_send_test_allowed": artifact.get("private_send_test_allowed") is True,
        "paper_lifecycle_live_send_test_allowed": (
            artifact.get("paper_lifecycle_live_send_test_allowed") is True
        ),
        "normal_live_notification_allowed": False,
        "live_send_allowed_count": artifact.get("live_send_allowed_count", 0),
        "telegram_command_path_enabled_count": artifact.get(
            "telegram_command_path_enabled_count",
            0,
        ),
        "telegram_trade_command_enabled_count": artifact.get(
            "telegram_trade_command_enabled_count",
            0,
        ),
        "telegram_approve_trade_command_enabled_count": artifact.get(
            "telegram_approve_trade_command_enabled_count",
            0,
        ),
        "telegram_reject_trade_command_enabled_count": artifact.get(
            "telegram_reject_trade_command_enabled_count",
            0,
        ),
        "telegram_modify_trade_command_enabled_count": artifact.get(
            "telegram_modify_trade_command_enabled_count",
            0,
        ),
        "telegram_resize_trade_command_enabled_count": artifact.get(
            "telegram_resize_trade_command_enabled_count",
            0,
        ),
        "telegram_close_trade_command_enabled_count": artifact.get(
            "telegram_close_trade_command_enabled_count",
            0,
        ),
        "telegram_cancel_trade_command_enabled_count": artifact.get(
            "telegram_cancel_trade_command_enabled_count",
            0,
        ),
        "broker_write_allowed_count": artifact.get("broker_write_allowed_count", 0),
        "broker_post_allowed_count": artifact.get("broker_post_allowed_count", 0),
        "paper_order_allowed_count": artifact.get("paper_order_allowed_count", 0),
        "paper_order_submission_allowed_count": artifact.get(
            "paper_order_submission_allowed_count",
            0,
        ),
        "position_close_allowed_count": artifact.get("position_close_allowed_count", 0),
        "position_resize_allowed_count": artifact.get("position_resize_allowed_count", 0),
        "prediction_market_write_allowed_count": artifact.get(
            "prediction_market_write_allowed_count",
            0,
        ),
        "crypto_perps_write_allowed_count": artifact.get(
            "crypto_perps_write_allowed_count",
            0,
        ),
        "live_endpoint_allowed_count": artifact.get("live_endpoint_allowed_count", 0),
        "live_capital_enabled_count": artifact.get("live_capital_enabled_count", 0),
        "live_capital_enabled": artifact.get("live_capital_enabled") is True,
        "phase7_proof_credit_allowed": artifact.get("phase7_proof_credit_allowed") is True,
        "secret_value_exposed": artifact.get("secret_value_exposed") is True,
        "raw_payload_exposed": artifact.get("raw_payload_exposed") is True,
        "authorization_header_exposed": artifact.get("authorization_header_exposed") is True,
        "chat_id_exposed": artifact.get("chat_id_exposed") is True,
        "bot_token_exposed": artifact.get("bot_token_exposed") is True,
        "boundary": artifact.get("boundary", PAPEROPS_NOTIFICATION_BOUNDARY),
    }
