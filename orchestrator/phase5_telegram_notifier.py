"""Q5-10 Telegram notifier contract.

This module promotes the existing D8A Telegram dry-run rail into Phase 5
state-matched notification records. It remains outbound-only, dry-run by
default, and command-disabled. It does not call Telegram live APIs, approve
trades, submit orders, or enable live capital.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_account import paper_account_summary
from orchestrator.phase5_approval_policy import (
    APPROVAL_POLICY_RUNTIME_ARTIFACT,
    build_phase5_approval_policy_decisions,
    validate_phase5_approval_policy_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    build_phase5_kill_switch_ledger,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase5_paper_order_staging_gate,
    validate_phase5_paper_order_staging_bundle,
)
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_prediction_market_adapter import (
    PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_prediction_market_adapter,
    validate_phase5_prediction_market_adapter_bundle,
)
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from orchestrator.source_health import build_data_environment_map
from orchestrator.telegram_comms import (
    FORBIDDEN_TELEGRAM_TEXT,
    TELEGRAM_MESSAGE_CLASSES,
    TelegramCommunicationsStore,
    render_telegram_message,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION = 1
TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT = "phase5_telegram_notifier.json"
TELEGRAM_NOTIFIER_HISTORY = "phase5_telegram_notifier_history.jsonl"
TELEGRAM_NOTIFIER_EVENT_LOG = "phase5_telegram_notifier_events.jsonl"
TELEGRAM_NOTIFIER_EVENT_TYPE = "phase5_telegram_notification_written"
TELEGRAM_NOTIFIER_COMPONENT = "phase5_telegram_notifier"
TELEGRAM_SEND_TEST_APPROVAL_RUNTIME_ARTIFACT = "phase5_telegram_send_test_approval.json"

TELEGRAM_NOTIFIER_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{APPROVAL_POLICY_RUNTIME_ARTIFACT}",
    f"data/runtime/{RISK_SIZING_RUNTIME_ARTIFACT}",
    f"data/runtime/{KILL_SWITCH_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_ORDER_STAGING_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT}",
    f"data/runtime/{PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT}",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/paper_positions.jsonl",
    "data/runtime/paper_closed_trades.jsonl",
    "data/runtime/telegram-members.json",
    "data/runtime/telegram-outbox.jsonl",
    f"data/runtime/{TELEGRAM_SEND_TEST_APPROVAL_RUNTIME_ARTIFACT}",
)

TELEGRAM_ALERT_TYPES: tuple[str, ...] = (
    "policy_blocked",
    "risk_blocked",
    "staged_paper_order",
    "submitted_paper_order",
    "open_position",
    "closed_trade",
    "kill_switch_change",
    "degraded_source_or_venue",
    "postmortem_due",
)

ALERT_MESSAGE_CLASS: dict[str, str] = {
    "policy_blocked": "blocked_trade",
    "risk_blocked": "blocked_trade",
    "staged_paper_order": "staged_paper_order",
    "submitted_paper_order": "submitted_paper_order",
    "open_position": "open_position",
    "closed_trade": "closed_trade",
    "kill_switch_change": "kill_switch",
    "degraded_source_or_venue": "source_degraded",
    "postmortem_due": "postmortem_due",
}

TELEGRAM_REQUIRED_CHECKS: tuple[str, ...] = (
    "alert_type_registered",
    "message_class_registered",
    "backend_state_matched_before_alert",
    "backend_state_count_positive_when_eligible",
    "telegram_transport_dry_run",
    "telegram_send_gate_disabled",
    "telegram_command_path_disabled",
    "live_send_blocked",
    "explicit_private_send_test_gate_present",
    "message_preview_redacted",
    "delivery_policy_present",
    "retry_policy_present",
    "fallback_policy_present",
    "redaction_policy_present",
    "event_log_required",
    "no_trade_command_authority",
    "no_broker_write_authority",
    "no_paper_order_authority",
    "no_live_capital_authority",
    "outbox_send_not_allowed",
)

TELEGRAM_BOUNDARY_FIELDS: tuple[str, ...] = (
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
    "trade_candidate_created",
    "risk_approval_allowed",
    "execution_allowed",
    "execution_intent_created",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "paper_order_submitted",
    "broker_write_allowed",
    "broker_post_called",
    "alpaca_post_called",
    "broker_submit_receipt_created",
    "prediction_market_write_allowed",
    "position_created",
    "position_monitor_write_authority",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "source_quorum_bypass_allowed",
)

TELEGRAM_EXPOSURE_FIELDS: tuple[str, ...] = (
    "secret_value_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
    "authorization_header_exposed",
    "chat_id_exposed",
    "bot_token_exposed",
    "telegram_handle_exposed",
)

TELEGRAM_COUNT_FIELDS: tuple[str, ...] = (
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
    "live_send_allowed_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "paper_order_allowed_count",
    "paper_order_submitted_count",
    "execution_allowed_count",
    "prediction_market_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "chat_id_exposed_count",
    "bot_token_exposed_count",
)

TELEGRAM_NOTIFIER_BOUNDARY = (
    "Q5-10 Telegram notifications are state-matched outbound alerts only. "
    "An alert can be queued only after matching backend state exists, and it "
    "uses the D8A dry-run outbox until a separate private send-test approval is "
    "present. Telegram cannot place, approve, reject, modify, resize, close, "
    "or cancel trades, submit paper orders, write brokers, send live execution "
    "alerts, or enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-10"
    ledger["boundary"] = (
        "Q5-10 records Telegram notification eligibility only. Live Telegram "
        "sends, command paths, broker writes, paper orders, position mutation, "
        "and live capital stay disabled."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def telegram_notifier_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
        runtime / TELEGRAM_NOTIFIER_HISTORY,
        runtime / TELEGRAM_NOTIFIER_EVENT_LOG,
    )


def telegram_send_test_approval_path(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings) / TELEGRAM_SEND_TEST_APPROVAL_RUNTIME_ARTIFACT


def _approval_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / APPROVAL_POLICY_RUNTIME_ARTIFACT) or (
        build_phase5_approval_policy_decisions(settings=settings)
    )


def _risk_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / RISK_SIZING_RUNTIME_ARTIFACT) or (
        build_phase5_risk_sizing_reviews(settings=settings)
    )


def _kill_switch_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / KILL_SWITCH_RUNTIME_ARTIFACT) or (
        build_phase5_kill_switch_ledger(settings=settings)
    )


def _staging_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / PAPER_ORDER_STAGING_RUNTIME_ARTIFACT) or (
        build_phase5_paper_order_staging_gate(settings=settings)
    )


def _submit_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT) or (
        build_phase5_paper_submit_enablement_gate(settings=settings)
    )


def _prediction_bundle(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT) or (
        build_phase5_prediction_market_adapter(settings=settings)
    )


def _send_test_gate(settings: Settings | None = None) -> dict[str, Any]:
    path = telegram_send_test_approval_path(settings)
    approval = _read_json(path)
    if not approval:
        return {
            "approval_present": False,
            "approval_logged": False,
            "approval_state": "missing",
            "approval_scope": "private_send_test_only",
            "explicit_private_send_test_approval": False,
            "private_send_test_allowed": False,
            "live_send_allowed": False,
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "live_capital_enabled": False,
            "boundary": "No Q5-10 private send-test approval is present; live Telegram sends remain blocked.",
        }
    scope = str(approval.get("approval_scope") or approval.get("scope") or "")
    approval_state = str(approval.get("approval_state") or approval.get("state") or "unknown")
    explicit = (
        approval_state == "approved"
        and scope == "private_send_test_only"
        and approval.get("approval_logged") is True
        and approval.get("telegram_command_path_enabled") is not True
        and approval.get("broker_write_allowed") is not True
        and approval.get("paper_order_allowed") is not True
        and approval.get("live_capital_enabled") is not True
    )
    return {
        "approval_present": True,
        "approval_logged": approval.get("approval_logged") is True,
        "approval_state": approval_state,
        "approval_scope": scope or "unknown",
        "explicit_private_send_test_approval": explicit,
        "private_send_test_allowed": explicit,
        "live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "live_capital_enabled": False,
        "boundary": (
            "Private send-test approval can allow one explicit delivery test "
            "only; it does not enable command handling, trade approval, broker "
            "writes, normal live notifications, or live capital."
        ),
    }


def _source_degradation_count(settings: Settings) -> int:
    data_map = build_data_environment_map(settings=settings)
    sources = data_map.get("sources", [])
    if not isinstance(sources, list):
        return 0
    return sum(
        1
        for source in sources
        if isinstance(source, dict)
        and (
            str(source.get("runtime_status") or "") in {"degraded", "missing_secret", "deferred"}
            or bool(source.get("missing_secrets"))
        )
    )


def _backend_state(settings: Settings) -> dict[str, Any]:
    approval = _approval_bundle(settings)
    risk = _risk_bundle(settings)
    kill_switch = _kill_switch_bundle(settings)
    staging = _staging_bundle(settings)
    submit = _submit_bundle(settings)
    prediction = _prediction_bundle(settings)
    account = paper_account_summary(settings=settings)
    return {
        "approval": approval,
        "approval_errors": validate_phase5_approval_policy_bundle(approval),
        "risk": risk,
        "risk_errors": validate_phase5_risk_sizing_bundle(risk),
        "kill_switch": kill_switch,
        "kill_switch_errors": validate_phase5_kill_switch_ledger(kill_switch),
        "staging": staging,
        "staging_errors": validate_phase5_paper_order_staging_bundle(staging),
        "submit": submit,
        "submit_errors": validate_phase5_paper_submit_enablement_bundle(submit),
        "prediction": prediction,
        "prediction_errors": validate_phase5_prediction_market_adapter_bundle(prediction),
        "account": account,
        "source_degradation_count": _source_degradation_count(settings),
    }


def _backend_count(alert_type: str, backend: dict[str, Any]) -> tuple[int, str, str]:
    if alert_type == "policy_blocked":
        return (
            int(backend["approval"].get("blocked_count", 0) or 0),
            "phase5_approval_policy_decisions.blocked_count",
            "Q5-2 policy decision blocked count",
        )
    if alert_type == "risk_blocked":
        return (
            int(backend["risk"].get("blocked_count", 0) or 0),
            "phase5_risk_sizing_reviews.blocked_count",
            "Q5-3 risk sizing blocked count",
        )
    if alert_type == "staged_paper_order":
        return (
            int(backend["staging"].get("staged_order_count", 0) or 0),
            "phase5_paper_order_staging_gate.staged_order_count",
            "Q5-6 staged paper-order count",
        )
    if alert_type == "submitted_paper_order":
        return (
            int(backend["submit"].get("paper_order_submitted_count", 0) or 0),
            "phase5_paper_submit_enablement_gate.paper_order_submitted_count",
            "Q5-8 submitted paper-order count",
        )
    if alert_type == "open_position":
        return (
            int(backend["account"].get("open_position_count", 0) or 0),
            "paper_account_summary.open_position_count",
            "paper-account mirrored open-position count",
        )
    if alert_type == "closed_trade":
        return (
            int(backend["account"].get("closed_trade_count", 0) or 0),
            "paper_account_summary.closed_trade_count",
            "paper-account mirrored closed-trade count",
        )
    if alert_type == "kill_switch_change":
        return (
            int(backend["kill_switch"].get("switch_count", 0) or 0),
            "phase5_kill_switch_ledger.switch_count",
            "Q5-4 kill-switch ledger record count",
        )
    if alert_type == "degraded_source_or_venue":
        degraded_sources = int(backend.get("source_degradation_count", 0) or 0)
        live_blocked_routes = int(backend["prediction"].get("live_blocked_count", 0) or 0)
        return (
            degraded_sources + live_blocked_routes,
            "data_environment_map.degraded_or_missing_sources + phase5_prediction_market_adapter.live_blocked_count",
            "degraded source, missing credential, deferred source, or live-blocked venue count",
        )
    if alert_type == "postmortem_due":
        return (
            int(backend["account"].get("postmortem_due_count", 0) or 0),
            "paper_account_summary.postmortem_due_count",
            "paper-account postmortem-due count",
        )
    return 0, "unknown", "unknown"


def _message_context(alert_type: str, backend_count: int, backend_ref: str) -> dict[str, Any]:
    if alert_type == "policy_blocked":
        return {
            "instrument": "Phase 5 policy route",
            "catalyst": "approval policy router recorded blocked strategy state",
            "evidence_summary": f"{backend_count} blocked Q5-2 policy records",
            "blocked_reason": "policy gate blocked before risk sizing",
        }
    if alert_type == "risk_blocked":
        return {
            "instrument": "Phase 5 risk sizing",
            "catalyst": "Risk Agent paper-sizing contract blocked paper eligibility",
            "evidence_summary": f"{backend_count} blocked Q5-3 risk reviews",
            "blocked_reason": "risk sizing blocked before staging or broker handoff",
        }
    if alert_type in {"staged_paper_order", "submitted_paper_order"}:
        return {
            "instrument": "Alpaca paper route",
            "catalyst": f"{backend_count} backend records reached {alert_type}",
            "evidence_summary": backend_ref,
        }
    if alert_type == "kill_switch_change":
        return {
            "title": "Kill-switch ledger update",
            "subject": "Layer B kill-switch ledger",
            "why_it_matters": "downstream notification, staging, submit, and execution checks must respect kill-switch state",
            "evidence": f"{backend_count} Q5-4 kill-switch records logged",
            "block": "kill switches can only block; mutation and execution authority stay disabled",
        }
    if alert_type == "degraded_source_or_venue":
        return {
            "title": "Source or venue degraded",
            "subject": "source readiness and disabled venue routes",
            "why_it_matters": "evidence strength and route availability are reduced until recovered",
            "evidence": f"{backend_count} degraded, credential-gated, deferred, or live-blocked source/venue states",
            "block": "affected sources and venues cannot unlock orders",
        }
    if alert_type in {"open_position", "closed_trade", "postmortem_due"}:
        return {
            "title": alert_type.replace("_", " ").title(),
            "subject": "paper-account mirror",
            "why_it_matters": "backend paper lifecycle state changed",
            "evidence": f"{backend_count} mirrored backend records in {backend_ref}",
            "block": "Telegram has no close, resize, cancel, or broker-write command path",
        }
    return {
        "title": alert_type.replace("_", " ").title(),
        "subject": "Phase 5 backend state",
        "why_it_matters": "backend state changed",
        "evidence": backend_ref,
        "block": "notification only",
    }


def _notification_status(backend_count: int) -> tuple[str, str]:
    if backend_count > 0:
        return "eligible", "eligible_dry_run"
    return "blocked", "suppressed_no_matching_backend_state"


def _policies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    delivery = {
        "mode": "dry_run_outbox",
        "recipient_scope": "founding_fund_managers",
        "requires_matching_backend_state": True,
        "requires_private_send_test_before_live": True,
        "live_send_allowed": False,
    }
    retry = {
        "max_attempts": 3,
        "retry_backoff_seconds": [30, 120, 300],
        "live_retry_enabled": False,
        "failure_record_required": True,
    }
    fallback = {
        "primary": "telegram_dry_run_outbox",
        "fallback": "cockpit_status_and_event_log",
        "fallback_only_if_delivery_fails": True,
        "broker_action_on_failure": False,
    }
    redaction = {
        "strip_secrets": True,
        "strip_chat_ids": True,
        "strip_handles": True,
        "strip_local_paths": True,
        "strip_raw_payloads": True,
    }
    return delivery, retry, fallback, redaction


def _record_checks(
    *,
    alert_type: str,
    message_class: str,
    backend_count: int,
    status: str,
    settings: Settings,
    send_test_gate: dict[str, Any],
    message_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    preview_text = f"{message_preview.get('title', '')}\n{message_preview.get('body', '')}"
    safe_preview = all(not pattern.search(preview_text) for pattern in FORBIDDEN_TELEGRAM_TEXT)
    transport_dry_run = settings.telegram_dry_run is True
    send_gate_disabled = settings.telegram_enabled is False
    return [
        _check("alert_type_registered", alert_type in TELEGRAM_ALERT_TYPES),
        _check("message_class_registered", message_class in TELEGRAM_MESSAGE_CLASSES),
        _check("backend_state_matched_before_alert", backend_count > 0 if status == "eligible" else True),
        _check("backend_state_count_positive_when_eligible", backend_count > 0 if status == "eligible" else True),
        _check("telegram_transport_dry_run", transport_dry_run),
        _check("telegram_send_gate_disabled", send_gate_disabled),
        _check("telegram_command_path_disabled", True),
        _check("live_send_blocked", True),
        _check(
            "explicit_private_send_test_gate_present",
            send_test_gate.get("private_send_test_allowed") is True
            or send_test_gate.get("approval_present") is False,
        ),
        _check("message_preview_redacted", safe_preview),
        _check("delivery_policy_present", True),
        _check("retry_policy_present", True),
        _check("fallback_policy_present", True),
        _check("redaction_policy_present", True),
        _check("event_log_required", True),
        _check("no_trade_command_authority", True),
        _check("no_broker_write_authority", True),
        _check("no_paper_order_authority", True),
        _check("no_live_capital_authority", True),
        _check("outbox_send_not_allowed", True),
    ]


def _alert_record(
    alert_type: str,
    *,
    backend: dict[str, Any],
    settings: Settings,
    send_test_gate: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    backend_count, backend_ref, backend_label = _backend_count(alert_type, backend)
    status, notification_state = _notification_status(backend_count)
    message_class = ALERT_MESSAGE_CLASS[alert_type]
    context = _message_context(alert_type, backend_count, backend_ref)
    title, body = render_telegram_message(message_class, context)
    delivery, retry, fallback, redaction = _policies()
    message_id = f"q5-10-{alert_type.replace('_', '-')}"
    checks = _record_checks(
        alert_type=alert_type,
        message_class=message_class,
        backend_count=backend_count,
        status=status,
        settings=settings,
        send_test_gate=send_test_gate,
        message_preview={"title": title, "body": body},
    )
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "telegram_notifier_schema_version": PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION,
        "artifact_type": "telegram_notification",
        "artifact_id": f"phase5:q5-10:telegram-notifier:{_safe_key(alert_type)}",
        "phase": "Q5",
        "stage": "Q5-10",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(TELEGRAM_NOTIFIER_SOURCE_REFS),
        "boundary": TELEGRAM_NOTIFIER_BOUNDARY,
        **phase5_authority_defaults(),
        "alert_type": alert_type,
        "message_class": message_class,
        "notification_state": notification_state,
        "recipient_scope": "founding_fund_managers",
        "backend_state_ref": backend_ref,
        "backend_state_label": backend_label,
        "backend_state_count": backend_count,
        "backend_state_matched": backend_count > 0,
        "backend_state_required": True,
        "message_context": context,
        "message_preview": {"title": title, "body": body, "dashboard_link": "qadam.trade/dashboard/"},
        "delivery_policy": delivery,
        "retry_policy": retry,
        "fallback_policy": fallback,
        "redaction_policy": redaction,
        "phase5_telegram_send_test_gate": send_test_gate,
        "private_send_test_allowed": send_test_gate.get("private_send_test_allowed") is True,
        "normal_live_notification_allowed": False,
        "live_send_allowed": False,
        "outbox_message_id": message_id,
        "outbox_message_written": False,
        "outbox_write_status": "not_written",
        "outbox_message_mode": None,
        "outbox_message_status": None,
        "outbox_send_allowed": False,
        "delivery_status": "suppressed" if status == "blocked" else "eligible_for_dry_run_queue",
        "delivery_attempt_count": 0,
        "delivery_failure_reason": "",
        "required_checks": list(TELEGRAM_REQUIRED_CHECKS),
        "required_check_count": len(TELEGRAM_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
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
        "execution_intent_created": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "broker_submit_receipt_created": False,
        "prediction_market_write_allowed": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "source_quorum_bypass_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "chat_id_exposed": False,
        "bot_token_exposed": False,
        "telegram_handle_exposed": False,
    }
    record["validation_errors"] = validate_phase5_telegram_notifier_record(record)
    return record


def build_phase5_telegram_notifier(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    backend = _backend_state(settings)
    send_test_gate = _send_test_gate(settings)
    telegram = TelegramCommunicationsStore(settings=settings).public_status()
    records = [
        _alert_record(
            alert_type,
            backend=backend,
            settings=settings,
            send_test_gate=send_test_gate,
            generated_at=generated_at,
        )
        for alert_type in TELEGRAM_ALERT_TYPES
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    notification_counts = Counter(str(record.get("notification_state") or "unknown") for record in records)
    bundle = {
        "schema_version": PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION,
        "artifact_type": "phase5_telegram_notifier_bundle",
        "artifact_id": "phase5:q5-10:telegram-notifier",
        "phase": "Q5",
        "stage": "Q5-10",
        "status": "ok",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(TELEGRAM_NOTIFIER_SOURCE_REFS),
        "boundary": TELEGRAM_NOTIFIER_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "alert_type_count": len(TELEGRAM_ALERT_TYPES),
        "notification_record_count": len(records),
        "eligible_alert_count": status_counts.get("eligible", 0),
        "suppressed_alert_count": status_counts.get("blocked", 0),
        "queued_dry_run_alert_count": notification_counts.get("queued_dry_run", 0),
        "outbox_message_written_count": sum(1 for record in records if record.get("outbox_message_written") is True),
        "status_counts": dict(sorted(status_counts.items())),
        "notification_state_counts": dict(sorted(notification_counts.items())),
        "required_check_count": len(TELEGRAM_REQUIRED_CHECKS),
        "telegram_status": telegram.get("status", "unknown"),
        "telegram_mode": telegram.get("mode", "unknown"),
        "telegram_send_gate": telegram.get("send_gate", "unknown"),
        "telegram_bot_configured": telegram.get("bot_configured") is True,
        "telegram_delivery_target_count": int(telegram.get("delivery_target_count", 0) or 0),
        "send_test_gate_state": send_test_gate.get("approval_state", "missing"),
        "send_test_approval_present": send_test_gate.get("approval_present") is True,
        "send_test_approval_logged": send_test_gate.get("approval_logged") is True,
        "private_send_test_allowed": send_test_gate.get("private_send_test_allowed") is True,
        "normal_live_notification_allowed": False,
        "backend_validation_error_count": sum(
            len(backend.get(key, []))
            for key in (
                "approval_errors",
                "risk_errors",
                "kill_switch_errors",
                "staging_errors",
                "submit_errors",
                "prediction_errors",
            )
        ),
        "source_degradation_count": int(backend.get("source_degradation_count", 0) or 0),
        "records": records,
    }
    for field in TELEGRAM_COUNT_FIELDS:
        source_field = field.removesuffix("_count")
        if field == "live_send_allowed_count":
            source_field = "live_send_allowed"
        bundle[field] = sum(1 for record in records if record.get(source_field) is True)
    bundle["validation_errors"] = validate_phase5_telegram_notifier_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _required_check_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("required_check_count") != len(TELEGRAM_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        return ["checks_not_list"]
    check_names = {str(check.get("name") or "") for check in checks if isinstance(check, dict)}
    for required in TELEGRAM_REQUIRED_CHECKS:
        if required not in check_names:
            errors.append(f"required_check_missing:{required}")
    failed_checks = [check.get("name") for check in checks if isinstance(check, dict) and not check.get("passed")]
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("failed_check_count_mismatch")
    return errors


def _policy_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("delivery_policy", "retry_policy", "fallback_policy", "redaction_policy"):
        if not isinstance(record.get(field), dict):
            errors.append(f"{field}_missing_or_invalid")
    delivery = record.get("delivery_policy", {})
    if isinstance(delivery, dict):
        if delivery.get("requires_matching_backend_state") is not True:
            errors.append("delivery_policy_backend_state_not_required")
        if delivery.get("live_send_allowed") is not False:
            errors.append("delivery_policy_live_send_allowed")
    retry = record.get("retry_policy", {})
    if isinstance(retry, dict):
        if retry.get("live_retry_enabled") is not False:
            errors.append("retry_policy_live_retry_enabled")
        if retry.get("failure_record_required") is not True:
            errors.append("retry_policy_failure_record_not_required")
    fallback = record.get("fallback_policy", {})
    if isinstance(fallback, dict) and fallback.get("broker_action_on_failure") is not False:
        errors.append("fallback_policy_broker_action_enabled")
    redaction = record.get("redaction_policy", {})
    if isinstance(redaction, dict):
        for field in ("strip_secrets", "strip_chat_ids", "strip_handles", "strip_local_paths", "strip_raw_payloads"):
            if redaction.get(field) is not True:
                errors.append(f"redaction_policy_not_enforced:{field}")
    return errors


def _message_preview_errors(record: dict[str, Any]) -> list[str]:
    preview = record.get("message_preview", {})
    if not isinstance(preview, dict):
        return ["message_preview_missing_or_invalid"]
    title = str(preview.get("title") or "")
    body = str(preview.get("body") or "")
    if not title.strip() or not body.strip():
        return ["message_preview_empty"]
    if "Dashboard: qadam.trade/dashboard/" not in body:
        return ["message_preview_dashboard_link_missing"]
    errors: list[str] = []
    for pattern in FORBIDDEN_TELEGRAM_TEXT:
        if pattern.search(title) or pattern.search(body):
            errors.append("message_preview_forbidden_text")
            break
    if record.get("message_class") == "blocked_trade" and "Status: blocked" not in body:
        errors.append("blocked_trade_preview_state_missing")
    if record.get("message_class") in {"source_degraded", "kill_switch"} and (
        "No trade command is available" not in body
    ):
        errors.append("system_alert_command_boundary_missing")
    return errors


def validate_phase5_telegram_notifier_record(record: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-10"))
    if record.get("artifact_type") != "telegram_notification":
        errors.append("artifact_type_not_telegram_notification")
    if record.get("telegram_notifier_schema_version") != PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION:
        errors.append("telegram_notifier_schema_version_mismatch")
    alert_type = str(record.get("alert_type") or "")
    message_class = str(record.get("message_class") or "")
    if alert_type not in TELEGRAM_ALERT_TYPES:
        errors.append("alert_type_invalid")
    if ALERT_MESSAGE_CLASS.get(alert_type) != message_class:
        errors.append("alert_message_class_mismatch")
    if message_class not in TELEGRAM_MESSAGE_CLASSES:
        errors.append("message_class_invalid")
    backend_count = int(record.get("backend_state_count", 0) or 0)
    if record.get("status") == "eligible":
        if backend_count <= 0:
            errors.append("eligible_without_backend_state")
        if record.get("backend_state_matched") is not True:
            errors.append("eligible_backend_state_not_matched")
        if record.get("notification_state") not in {"eligible_dry_run", "queued_dry_run"}:
            errors.append("eligible_notification_state_invalid")
    if backend_count <= 0 and record.get("outbox_message_written") is True:
        errors.append("outbox_written_without_backend_state")
    if record.get("status") == "blocked" and record.get("notification_state") != "suppressed_no_matching_backend_state":
        errors.append("blocked_notification_state_invalid")
    if record.get("live_send_allowed") is not False:
        errors.append("telegram_live_send_allowed")
    if record.get("normal_live_notification_allowed") is not False:
        errors.append("normal_live_notification_allowed")
    if record.get("outbox_send_allowed") is not False:
        errors.append("outbox_send_allowed")
    if record.get("outbox_message_written") is True:
        if record.get("outbox_message_mode") != "dry_run":
            errors.append("outbox_message_not_dry_run")
        if record.get("outbox_message_status") != "queued":
            errors.append("outbox_message_not_queued")
    for field in TELEGRAM_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"telegram_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    for exposure in TELEGRAM_EXPOSURE_FIELDS:
        if record.get(exposure) is not False:
            errors.append(f"telegram_exposure_enabled:{exposure}")
    gate = record.get("phase5_telegram_send_test_gate", {})
    if not isinstance(gate, dict):
        errors.append("send_test_gate_missing_or_invalid")
    else:
        for field in (
            "live_send_allowed",
            "telegram_command_path_enabled",
            "broker_write_allowed",
            "paper_order_allowed",
            "live_capital_enabled",
        ):
            if gate.get(field) is not False:
                errors.append(f"send_test_gate_authority_enabled:{field}")
    errors.extend(_required_check_errors(record))
    errors.extend(_policy_errors(record))
    errors.extend(_message_preview_errors(record))
    return sorted(set(errors))


def validate_phase5_telegram_notifier_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "alert_type_count",
        "notification_record_count",
        "eligible_alert_count",
        "suppressed_alert_count",
        "queued_dry_run_alert_count",
        "outbox_message_written_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_telegram_notifier_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-10":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("alert_type_count") != len(TELEGRAM_ALERT_TYPES):
        errors.append("alert_type_count_mismatch")
    if bundle.get("notification_record_count") != len(records):
        errors.append("notification_record_count_mismatch")
    record_alerts = {str(record.get("alert_type") or "") for record in records if isinstance(record, dict)}
    missing_alerts = sorted(set(TELEGRAM_ALERT_TYPES) - record_alerts)
    if missing_alerts:
        errors.append("missing_alert_types:" + ",".join(missing_alerts))
    status_counts = Counter(
        str(record.get("status") or "unknown") for record in records if isinstance(record, dict)
    )
    notification_counts = Counter(
        str(record.get("notification_state") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    if bundle.get("eligible_alert_count") != status_counts.get("eligible", 0):
        errors.append("eligible_alert_count_mismatch")
    if bundle.get("suppressed_alert_count") != status_counts.get("blocked", 0):
        errors.append("suppressed_alert_count_mismatch")
    if bundle.get("queued_dry_run_alert_count") != notification_counts.get("queued_dry_run", 0):
        errors.append("queued_dry_run_alert_count_mismatch")
    if bundle.get("outbox_message_written_count") != sum(
        1 for record in records if isinstance(record, dict) and record.get("outbox_message_written") is True
    ):
        errors.append("outbox_message_written_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("telegram_mode") != "dry_run":
        errors.append("telegram_mode_not_dry_run")
    if bundle.get("telegram_send_gate") != "disabled":
        errors.append("telegram_send_gate_not_disabled")
    if bundle.get("normal_live_notification_allowed") is not False:
        errors.append("bundle_normal_live_notification_allowed")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in TELEGRAM_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("telegram_notification_record_not_dict")
            continue
        errors.extend(validate_phase5_telegram_notifier_record(record))
    if (
        "cannot place, approve, reject, modify, resize, close, or cancel trades"
        not in str(bundle.get("boundary") or "")
    ):
        errors.append("bundle_boundary_command_block_missing")
    return sorted(set(errors))


def _outbox_lookup(store: TelegramCommunicationsStore) -> dict[str, Any]:
    return {message.message_id: message for message in store.read_outbox()}


def attach_phase5_telegram_notifier_outbox_messages(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    output = deepcopy(bundle)
    store = TelegramCommunicationsStore(settings=settings)
    existing = _outbox_lookup(store)
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        if record.get("status") != "eligible":
            continue
        if settings.telegram_dry_run is not True or settings.telegram_enabled is not False:
            record["outbox_write_status"] = "blocked_transport_not_dry_run"
            record["validation_errors"] = validate_phase5_telegram_notifier_record(record)
            continue
        message_id = str(record.get("outbox_message_id") or "")
        message = existing.get(message_id)
        if message is None:
            message = store.add_outbox_message(
                message_id=message_id,
                message_class=str(record.get("message_class") or ""),
                context=record.get("message_context", {}),
                target_ref=f"phase5:q5-10:{record.get('alert_type')}",
                status="queued",
                log_event=False,
            )
            existing[message_id] = message
            record["outbox_write_status"] = "created"
        else:
            record["outbox_write_status"] = "already_present"
        record["outbox_message_written"] = True
        record["outbox_message_mode"] = message.mode
        record["outbox_message_status"] = message.status
        record["outbox_send_allowed"] = message.send_allowed
        record["notification_state"] = "queued_dry_run"
        record["delivery_status"] = "queued_dry_run"
        record["delivery_attempt_count"] = 0
        record["validation_errors"] = validate_phase5_telegram_notifier_record(record)

    notification_counts = Counter(
        str(record.get("notification_state") or "unknown")
        for record in output.get("records", [])
        if isinstance(record, dict)
    )
    output["queued_dry_run_alert_count"] = notification_counts.get("queued_dry_run", 0)
    output["notification_state_counts"] = dict(sorted(notification_counts.items()))
    output["outbox_message_written_count"] = sum(
        1
        for record in output.get("records", [])
        if isinstance(record, dict) and record.get("outbox_message_written") is True
    )
    output["validation_errors"] = validate_phase5_telegram_notifier_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output


def attach_phase5_telegram_notifier_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / TELEGRAM_NOTIFIER_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            TELEGRAM_NOTIFIER_EVENT_TYPE,
            TELEGRAM_NOTIFIER_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "alert_type": record.get("alert_type"),
                "message_class": record.get("message_class"),
                "status": record.get("status"),
                "notification_state": record.get("notification_state"),
                "backend_state_ref": record.get("backend_state_ref"),
                "backend_state_count": record.get("backend_state_count"),
                "outbox_message_id": record.get("outbox_message_id"),
                "outbox_message_written": record.get("outbox_message_written"),
                "live_send_allowed": record.get("live_send_allowed"),
                "telegram_command_path_enabled": record.get("telegram_command_path_enabled"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "paper_order_allowed": record.get("paper_order_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_telegram_notifier_record(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_telegram_notifier_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def write_phase5_telegram_notifier(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
    queue_outbox: bool = True,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = telegram_notifier_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if queue_outbox:
        output = attach_phase5_telegram_notifier_outbox_messages(output, settings=settings)
    if record_event:
        output, _ = attach_phase5_telegram_notifier_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_telegram_notifier_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_telegram_notifier_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "notification_record_count": output.get("notification_record_count"),
        "eligible_alert_count": output.get("eligible_alert_count"),
        "queued_dry_run_alert_count": output.get("queued_dry_run_alert_count"),
        "outbox_message_written_count": output.get("outbox_message_written_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
