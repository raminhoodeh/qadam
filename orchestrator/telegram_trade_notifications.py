"""Telegram group notifications for paper trade decisions.

This module sends outbound-only Telegram group alerts after Qadam has already
submitted an Alpaca paper order. It does not create, approve, modify, submit,
cancel, or close trades.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_message_quality import telegram_message_specificity


TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION = 1
TELEGRAM_TRADE_NOTIFICATIONS_RUNTIME_ARTIFACT = "telegram_trade_notifications.json"
TELEGRAM_TRADE_NOTIFICATIONS_HISTORY = "telegram_trade_notifications_history.jsonl"
TELEGRAM_TRADE_NOTIFICATIONS_EVENT_LOG = "telegram_trade_notifications_events.jsonl"
TELEGRAM_TRADE_NOTIFICATIONS_EVENT_TYPE = "telegram_trade_notification_recorded"
TELEGRAM_TRADE_NOTIFICATIONS_COMPONENT = "telegram_trade_notifications"

TELEGRAM_TRADE_NOTIFICATION_BOUNDARY = (
    "Telegram trade notifications are outbound group alerts for already-submitted "
    "Alpaca paper orders only. They cannot create trade candidates, approve risk, "
    "approve execution, submit or close broker orders, handle Telegram commands, "
    "call live broker endpoints, expose secrets or chat ids, grant Phase 7 proof "
    "credit, or enable live capital."
)

TELEGRAM_TRADE_NOTIFICATION_FALSE_FIELDS = (
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_place_trade_command_enabled",
    "telegram_approve_trade_command_enabled",
    "telegram_reject_trade_command_enabled",
    "telegram_modify_trade_command_enabled",
    "telegram_resize_trade_command_enabled",
    "telegram_close_trade_command_enabled",
    "telegram_cancel_trade_command_enabled",
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
    "raw_provider_response_persisted",
    "authorization_header_exposed",
    "chat_id_exposed",
    "bot_token_exposed",
    "telegram_handle_exposed",
    "broker_order_identifier_exposed",
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_money(value: Any) -> str:
    return f"GBP {_float(value):,.2f}"


def _format_pct(value: Any) -> str:
    number = _float(value)
    return f"{number:+.2f}%"


def _format_qty(value: Any) -> str:
    text = str(value or "unknown").strip()
    if text == "unknown":
        return text
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:g}"


def telegram_trade_notifications_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / TELEGRAM_TRADE_NOTIFICATIONS_RUNTIME_ARTIFACT,
        runtime / TELEGRAM_TRADE_NOTIFICATIONS_HISTORY,
        runtime / TELEGRAM_TRADE_NOTIFICATIONS_EVENT_LOG,
    )


def _delivery_path(settings: Settings) -> Path:
    path = _runtime_dir(settings) / "telegram-deliveries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _sent_delivery_keys(settings: Settings) -> set[str]:
    path = _delivery_path(settings)
    if not path.exists():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(payload, dict)
                and payload.get("message_class") == "submitted_paper_order"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "submitted_paper_order",
        "delivery_key": payload.get("delivery_key"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": TELEGRAM_TRADE_NOTIFICATION_BOUNDARY,
    }
    with _delivery_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_payload, sort_keys=True) + "\n")


def _telegram_send(token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _paperops_source(settings: Settings) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / "paperops_alpaca_paper_post.json")


def _selected_records(source: dict[str, Any]) -> list[dict[str, Any]]:
    records = source.get("selected_post_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _record_key(record: dict[str, Any]) -> str:
    preview = record.get("request_preview", {})
    client_order_id = ""
    if isinstance(preview, dict):
        client_order_id = str(preview.get("client_order_id") or "")
    client_order_id = client_order_id or str(record.get("idempotency_key") or "")
    receipt = record.get("broker_receipt", {})
    broker_hash = ""
    if isinstance(receipt, dict):
        broker_hash = str(receipt.get("broker_order_id_hash") or "")
    raw = f"{client_order_id}:{broker_hash}:telegram_group_trade_notification"
    return sha256(raw.encode("utf-8")).hexdigest()


def _trade_details(record: dict[str, Any]) -> dict[str, Any]:
    preview = record.get("request_preview", {})
    if not isinstance(preview, dict):
        preview = {}
    receipt = record.get("broker_receipt", {})
    if not isinstance(receipt, dict):
        receipt = {}
    symbol = str(preview.get("symbol") or record.get("alpaca_symbol") or "paper order")
    side = str(preview.get("side") or "unknown")
    qty = str(preview.get("qty") or "unknown")
    order_type = str(preview.get("type") or "market")
    time_in_force = str(preview.get("time_in_force") or "day")
    broker_status = str(receipt.get("broker_order_status") or "submitted")
    instrument = str(preview.get("instrument") or record.get("instrument") or symbol)
    return {
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "quantity_display": _format_qty(qty),
        "order_type": order_type,
        "time_in_force": time_in_force,
        "broker_status": broker_status,
        "instrument": instrument,
        "summary": f"{side.upper()} {_format_qty(qty)} {symbol}",
    }


def _trade_decision_context(record: dict[str, Any]) -> dict[str, Any]:
    preview = record.get("request_preview", {})
    if not isinstance(preview, dict):
        preview = {}
    receipt = record.get("broker_receipt", {})
    if not isinstance(receipt, dict):
        receipt = {}
    symbol_source = str(record.get("alpaca_symbol_source") or preview.get("symbol_source") or "request_preview")
    source_status = str(record.get("status") or "unknown")
    receipt_status = str(receipt.get("broker_order_status") or "submitted")
    return {
        "why_submitted": (
            f"PaperOps recorded {source_status} after the guarded paper-post path selected "
            f"the {symbol_source} symbol route."
        ),
        "evidence": (
            f"source_status={source_status}; broker_status={receipt_status}; "
            f"idempotency_key_present={bool(record.get('idempotency_key'))}"
        ),
    }


def _portfolio_snapshot(settings: Settings) -> dict[str, Any]:
    context = paper_account_shadow_context(settings=settings)
    starting_balance = _float(context.get("trial_allocation_gbp"), _float(settings.trial_balance_gbp))
    equity = _float(context.get("equity_gbp"), starting_balance)
    current_balance = _float(context.get("current_balance_gbp"), equity)
    realized = _float(context.get("realized_pnl_gbp"))
    unrealized = _float(context.get("unrealized_pnl_gbp"))
    total_pnl = round(realized + unrealized, 2)
    performance_pct = round(((equity - starting_balance) / starting_balance * 100), 4) if starting_balance else 0.0
    return {
        "status": str(context.get("status") or "unknown"),
        "trial_allocation_gbp": round(starting_balance, 2),
        "portfolio_value_gbp": round(equity, 2),
        "current_balance_gbp": round(current_balance, 2),
        "cash_gbp": round(_float(context.get("cash_gbp"), current_balance), 2),
        "realized_pnl_gbp": round(realized, 2),
        "unrealized_pnl_gbp": round(unrealized, 2),
        "total_pnl_gbp": total_pnl,
        "performance_pct": performance_pct,
        "drawdown_pct": round(_float(context.get("drawdown_pct")), 4),
        "open_position_count": _int(context.get("open_position_count")),
        "order_count": _int(context.get("order_count")),
        "closed_trade_count": _int(context.get("closed_trade_count")),
        "observed_at": context.get("observed_at"),
    }


def _render_trade_message(
    trade: dict[str, Any],
    portfolio: dict[str, Any],
    decision_context: dict[str, Any],
) -> tuple[str, str]:
    title = f"Paper Trade: {trade['summary']}"
    body = "\n".join(
        [
            "Qadam: submitted Alpaca paper order",
            (
                "Trade: "
                f"{trade['side'].upper()} {trade['quantity_display']} {trade['symbol']} "
                f"({trade['order_type']}, {trade['time_in_force']})"
            ),
            f"Instrument: {trade['instrument']}",
            f"Why this trade was sent: {decision_context['why_submitted']}",
            f"Evidence: {decision_context['evidence']}",
            f"Broker status: {trade['broker_status']}",
            f"Portfolio: {_format_money(portfolio['portfolio_value_gbp'])}",
            (
                "Performance: "
                f"{_format_money(portfolio['total_pnl_gbp'])} "
                f"({_format_pct(portfolio['performance_pct'])})"
            ),
            f"Cash: {_format_money(portfolio['cash_gbp'])}",
            (
                "Open positions: "
                f"{portfolio['open_position_count']} | Orders: {portfolio['order_count']} | "
                f"Closed trades: {portfolio['closed_trade_count']}"
            ),
            (
                "Current impact: "
                f"paper equity is {_format_pct(portfolio['performance_pct'])} versus the "
                f"{_format_money(portfolio['trial_allocation_gbp'])} allocation."
            ),
            "Safety: broker identifiers are hashed and Telegram cannot approve or modify orders.",
            "Mode: paper only; live capital remains blocked.",
            "Dashboard: qadam.trade/dashboard/",
        ]
    )
    return title, body


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def _notification_record(
    record: dict[str, Any],
    *,
    settings: Settings,
    source_status: str,
    send_requested: bool,
    sent_keys: set[str],
    generated_at: str,
) -> dict[str, Any]:
    trade = _trade_details(record)
    portfolio = _portfolio_snapshot(settings)
    decision_context = _trade_decision_context(record)
    title, body = _render_trade_message(trade, portfolio, decision_context)
    text = f"{title}\n\n{body}"
    delivery_key = _record_key(record)
    message_specificity = telegram_message_specificity(title, body)
    eligible = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and source_status == "submitted_to_alpaca_paper"
        and record.get("status") == "submitted_to_alpaca_paper"
        and _safe_text(title, body)
        and message_specificity["status"] == "specific"
    )
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    enabled = settings.telegram_trade_group_notifications_enabled
    dry_run = settings.telegram_trade_group_notifications_dry_run
    already_sent = delivery_key in sent_keys

    blockers: list[str] = []
    if not eligible:
        blockers.append("no_submitted_paper_order_state")
    if message_specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if not enabled:
        blockers.append("trade_group_notifications_disabled")
    if dry_run:
        blockers.append("trade_group_notifications_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    if already_sent:
        blockers.append("telegram_trade_notification_already_sent")

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    status = "dry_run_ready" if eligible else "suppressed_not_eligible"
    if eligible and enabled and not dry_run:
        status = "ready_to_send"
    if already_sent:
        status = "already_sent"

    if (
        send_requested
        and eligible
        and enabled
        and not dry_run
        and bot_configured
        and group_chat_configured
        and not already_sent
    ):
        live_send_attempted = True
        try:
            assert token is not None
            assert chat_id is not None
            response = _telegram_send(token, chat_id, text)
            if response.get("ok") is True:
                live_send_succeeded = True
                result = response.get("result", {})
                if isinstance(result, dict) and result.get("message_id") is not None:
                    telegram_message_id = int(result["message_id"])
                status = "sent"
            else:
                status = "failed"
                failure_category = "telegram_api_rejected"
        except Exception as exc:  # noqa: BLE001 - keep persisted failure sanitized.
            status = "failed"
            failure_category = type(exc).__name__

        _archive_delivery(
            settings,
            {
                "created_at": _now(),
                "status": status,
                "delivery_key": delivery_key,
                "telegram_message_id": telegram_message_id,
                "failure_category": failure_category,
                "send_requested": send_requested,
                "live_send_attempted": live_send_attempted,
            },
        )

    output = {
        "schema_version": TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION,
        "artifact_type": "telegram_trade_notification_record",
        "artifact_id": f"telegram:trade-notification:{delivery_key[:16]}",
        "phase": "PaperOps",
        "stage": "Telegram-Trade-Notify",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "target": "group",
        "recipient_scope": "fund_manager_group",
        "message_class": "submitted_paper_order",
        "delivery_key": delivery_key,
        "source_status": source_status,
        "source_record_status": record.get("status"),
        "eligible_for_trade_notification": eligible,
        "trade_group_notifications_enabled": enabled,
        "trade_group_notifications_dry_run": dry_run,
        "send_requested": send_requested,
        "already_sent": already_sent,
        "bot_configured": bot_configured,
        "group_chat_configured": group_chat_configured,
        "message_preview": {"title": title, "body": body, "dashboard_link": "qadam.trade/dashboard/"},
        "message_preview_redacted": _safe_text(title, body),
        "message_specificity": message_specificity,
        "message_specificity_status": message_specificity["status"],
        "message_specificity_score": message_specificity["score"],
        "message_fingerprint": message_specificity["fingerprint"],
        "trade_decision_context": decision_context,
        "trade_summary": trade["summary"],
        "trade_symbol": trade["symbol"],
        "trade_side": trade["side"],
        "trade_quantity": trade["quantity"],
        "trade_order_type": trade["order_type"],
        "trade_broker_status": trade["broker_status"],
        "portfolio_snapshot": portfolio,
        "portfolio_value_gbp": portfolio["portfolio_value_gbp"],
        "portfolio_total_pnl_gbp": portfolio["total_pnl_gbp"],
        "portfolio_performance_pct": portfolio["performance_pct"],
        "portfolio_cash_gbp": portfolio["cash_gbp"],
        "live_send_attempted": live_send_attempted,
        "live_send_succeeded": live_send_succeeded,
        "telegram_message_id_present": telegram_message_id is not None,
        "delivery_failure_category": failure_category,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "telegram_place_trade_command_enabled": False,
        "telegram_approve_trade_command_enabled": False,
        "telegram_reject_trade_command_enabled": False,
        "telegram_modify_trade_command_enabled": False,
        "telegram_resize_trade_command_enabled": False,
        "telegram_close_trade_command_enabled": False,
        "telegram_cancel_trade_command_enabled": False,
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
        "raw_provider_response_persisted": False,
        "authorization_header_exposed": False,
        "chat_id_exposed": False,
        "bot_token_exposed": False,
        "telegram_handle_exposed": False,
        "broker_order_identifier_exposed": False,
        "boundary": TELEGRAM_TRADE_NOTIFICATION_BOUNDARY,
    }
    output["validation_errors"] = validate_telegram_trade_notification_record(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    return output


def build_telegram_trade_notifications(
    settings: Settings | None = None,
    *,
    send_requested: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    source = _paperops_source(settings)
    records = [
        _notification_record(
            record,
            settings=settings,
            source_status=str(source.get("status") or "missing"),
            send_requested=send_requested,
            sent_keys=_sent_delivery_keys(settings),
            generated_at=generated_at,
        )
        for record in _selected_records(source)
    ]
    eligible_count = sum(1 for record in records if record["eligible_for_trade_notification"])
    sent_count = sum(1 for record in records if record["status"] == "sent")
    live_attempt_count = sum(1 for record in records if record["live_send_attempted"])
    artifact = {
        "schema_version": TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION,
        "artifact_type": "telegram_trade_notifications",
        "artifact_id": "telegram:trade-notifications:latest",
        "phase": "PaperOps",
        "stage": "Telegram-Trade-Notify",
        "status": "ready" if eligible_count else "idle_no_submitted_paper_orders",
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "source_status": source.get("status", "missing"),
        "source_selected_record_count": len(_selected_records(source)),
        "eligible_notification_count": eligible_count,
        "live_send_attempted_count": live_attempt_count,
        "live_send_succeeded_count": sent_count,
        "failed_delivery_count": sum(1 for record in records if record["status"] == "failed"),
        "already_sent_count": sum(1 for record in records if record["status"] == "already_sent"),
        "trade_group_notifications_enabled": settings.telegram_trade_group_notifications_enabled,
        "trade_group_notifications_dry_run": settings.telegram_trade_group_notifications_dry_run,
        "send_requested": send_requested,
        "bot_configured": secret_status("TELEGRAM_BOT_TOKEN", settings).configured,
        "group_chat_configured": secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured,
        "records": records,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "telegram_place_trade_command_enabled": False,
        "telegram_approve_trade_command_enabled": False,
        "telegram_reject_trade_command_enabled": False,
        "telegram_modify_trade_command_enabled": False,
        "telegram_resize_trade_command_enabled": False,
        "telegram_close_trade_command_enabled": False,
        "telegram_cancel_trade_command_enabled": False,
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
        "raw_provider_response_persisted": False,
        "authorization_header_exposed": False,
        "chat_id_exposed": False,
        "bot_token_exposed": False,
        "telegram_handle_exposed": False,
        "broker_order_identifier_exposed": False,
        "boundary": TELEGRAM_TRADE_NOTIFICATION_BOUNDARY,
    }
    if artifact["failed_delivery_count"]:
        artifact["status"] = "delivery_failed"
    elif sent_count:
        artifact["status"] = "sent"
    elif artifact["already_sent_count"] and eligible_count:
        artifact["status"] = "already_sent"
    elif eligible_count and artifact["trade_group_notifications_dry_run"]:
        artifact["status"] = "dry_run_ready"
    elif eligible_count and not artifact["trade_group_notifications_enabled"]:
        artifact["status"] = "blocked_pending_enablement"
    artifact["validation_errors"] = validate_telegram_trade_notifications(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_telegram_trade_notification_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "boundary",
        "bot_configured",
        "delivery_key",
        "eligible_for_trade_notification",
        "group_chat_configured",
        "live_send_attempted",
        "live_send_succeeded",
        "message_class",
        "message_fingerprint",
        "message_preview",
        "message_preview_redacted",
        "message_specificity",
        "message_specificity_score",
        "message_specificity_status",
        "portfolio_cash_gbp",
        "portfolio_performance_pct",
        "portfolio_snapshot",
        "portfolio_total_pnl_gbp",
        "portfolio_value_gbp",
        "public_safe",
        "send_requested",
        "status",
        "target",
        "trade_decision_context",
        "trade_broker_status",
        "trade_order_type",
        "trade_quantity",
        "trade_side",
        "trade_summary",
        "trade_symbol",
    }
    missing = sorted(required - set(record))
    if missing:
        errors.append("telegram_trade_notification_record_missing_fields:" + ",".join(missing))
    if record.get("artifact_type") != "telegram_trade_notification_record":
        errors.append("telegram_trade_notification_record_type_mismatch")
    if record.get("public_safe") is not True:
        errors.append("telegram_trade_notification_record_not_public_safe")
    if record.get("target") != "group":
        errors.append("telegram_trade_notification_target_not_group")
    if record.get("message_class") != "submitted_paper_order":
        errors.append("telegram_trade_notification_message_class_invalid")
    if record.get("status") not in {
        "already_sent",
        "dry_run_ready",
        "failed",
        "invalid",
        "ready_to_send",
        "sent",
        "suppressed_not_eligible",
    }:
        errors.append("telegram_trade_notification_status_invalid")
    preview = record.get("message_preview", {})
    if not isinstance(preview, dict):
        errors.append("telegram_trade_notification_preview_missing")
    else:
        title = str(preview.get("title") or "")
        body = str(preview.get("body") or "")
        if not title.strip() or not body.strip():
            errors.append("telegram_trade_notification_preview_empty")
        if "Dashboard: qadam.trade/dashboard/" not in body:
            errors.append("telegram_trade_notification_dashboard_missing")
        if "Trade:" not in body:
            errors.append("telegram_trade_notification_trade_line_missing")
        if "Why this trade was sent:" not in body:
            errors.append("telegram_trade_notification_why_line_missing")
        if "Evidence:" not in body:
            errors.append("telegram_trade_notification_evidence_line_missing")
        if "Portfolio:" not in body:
            errors.append("telegram_trade_notification_portfolio_line_missing")
        if "Performance:" not in body or "%" not in body:
            errors.append("telegram_trade_notification_performance_line_missing")
        if "Current impact:" not in body:
            errors.append("telegram_trade_notification_current_impact_missing")
        if "Mode: paper only; live capital remains blocked." not in body:
            errors.append("telegram_trade_notification_paper_mode_line_missing")
        if not _safe_text(title, body):
            errors.append("telegram_trade_notification_forbidden_text")
    specificity = record.get("message_specificity", {})
    if not isinstance(specificity, dict):
        errors.append("telegram_trade_notification_specificity_missing")
    else:
        if specificity.get("status") != "specific":
            errors.append("telegram_trade_notification_message_not_specific")
        if _int(specificity.get("score")) < _int(specificity.get("minimum_score", 70)):
            errors.append("telegram_trade_notification_specificity_score_low")
    if record.get("message_specificity_status") != "specific":
        errors.append("telegram_trade_notification_specificity_status_not_specific")
    if _int(record.get("message_specificity_score")) < 70:
        errors.append("telegram_trade_notification_specificity_score_low")
    if not str(record.get("message_fingerprint") or "").strip():
        errors.append("telegram_trade_notification_message_fingerprint_missing")
    if not isinstance(record.get("trade_decision_context"), dict):
        errors.append("telegram_trade_notification_decision_context_missing")
    portfolio = record.get("portfolio_snapshot", {})
    if not isinstance(portfolio, dict):
        errors.append("telegram_trade_notification_portfolio_snapshot_missing")
    else:
        if _float(record.get("portfolio_value_gbp")) != _float(portfolio.get("portfolio_value_gbp")):
            errors.append("telegram_trade_notification_portfolio_value_mismatch")
        if _float(record.get("portfolio_total_pnl_gbp")) != _float(portfolio.get("total_pnl_gbp")):
            errors.append("telegram_trade_notification_portfolio_pnl_mismatch")
        if _float(record.get("portfolio_performance_pct")) != _float(portfolio.get("performance_pct")):
            errors.append("telegram_trade_notification_portfolio_performance_mismatch")
    if not str(record.get("trade_summary") or "").strip():
        errors.append("telegram_trade_notification_trade_summary_missing")
    if record.get("message_preview_redacted") is not True:
        errors.append("telegram_trade_notification_preview_not_redacted")
    if record.get("live_send_attempted") is True:
        if record.get("send_requested") is not True:
            errors.append("telegram_trade_notification_live_attempt_without_request")
        if record.get("trade_group_notifications_enabled") is not True:
            errors.append("telegram_trade_notification_live_attempt_without_gate")
        if record.get("trade_group_notifications_dry_run") is not False:
            errors.append("telegram_trade_notification_live_attempt_in_dry_run")
        if record.get("bot_configured") is not True:
            errors.append("telegram_trade_notification_live_attempt_without_bot")
        if record.get("group_chat_configured") is not True:
            errors.append("telegram_trade_notification_live_attempt_without_group")
    if record.get("live_send_succeeded") is True and record.get("status") != "sent":
        errors.append("telegram_trade_notification_succeeded_status_mismatch")
    for field in TELEGRAM_TRADE_NOTIFICATION_FALSE_FIELDS:
        if record.get(field) is not False:
            errors.append(f"telegram_trade_notification_authority_enabled:{field}")
    if "cannot create trade candidates" not in str(record.get("boundary") or ""):
        errors.append("telegram_trade_notification_boundary_weak")
    return sorted(set(errors))


def validate_telegram_trade_notifications(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "boundary",
        "bot_configured",
        "eligible_notification_count",
        "group_chat_configured",
        "live_send_attempted_count",
        "live_send_succeeded_count",
        "mode",
        "public_safe",
        "records",
        "schema_version",
        "send_requested",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("telegram_trade_notifications_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION:
        errors.append("telegram_trade_notifications_schema_version_mismatch")
    if artifact.get("artifact_type") != "telegram_trade_notifications":
        errors.append("telegram_trade_notifications_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("telegram_trade_notifications_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("telegram_trade_notifications_mode_not_paper")
    if artifact.get("status") not in {
        "already_sent",
        "blocked_pending_enablement",
        "delivery_failed",
        "dry_run_ready",
        "idle_no_submitted_paper_orders",
        "invalid",
        "ready",
        "sent",
    }:
        errors.append("telegram_trade_notifications_status_invalid")
    records = artifact.get("records", [])
    if not isinstance(records, list):
        errors.append("telegram_trade_notifications_records_not_list")
        records = []
    if _int(artifact.get("source_selected_record_count")) != len(records):
        errors.append("telegram_trade_notifications_source_count_mismatch")
    if _int(artifact.get("eligible_notification_count")) != sum(
        1
        for record in records
        if isinstance(record, dict) and record.get("eligible_for_trade_notification") is True
    ):
        errors.append("telegram_trade_notifications_eligible_count_mismatch")
    if _int(artifact.get("live_send_attempted_count")) != sum(
        1 for record in records if isinstance(record, dict) and record.get("live_send_attempted") is True
    ):
        errors.append("telegram_trade_notifications_attempt_count_mismatch")
    if _int(artifact.get("live_send_succeeded_count")) != sum(
        1 for record in records if isinstance(record, dict) and record.get("live_send_succeeded") is True
    ):
        errors.append("telegram_trade_notifications_success_count_mismatch")
    for field in TELEGRAM_TRADE_NOTIFICATION_FALSE_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"telegram_trade_notifications_authority_enabled:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("telegram_trade_notification_record_invalid")
            continue
        errors.extend(validate_telegram_trade_notification_record(record))
    if artifact.get("recorded") is True:
        if artifact.get("event_log_written") is not True:
            errors.append("telegram_trade_notifications_event_log_missing")
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("telegram_trade_notifications_event_count_mismatch")
    if "cannot create trade candidates" not in str(artifact.get("boundary") or ""):
        errors.append("telegram_trade_notifications_boundary_weak")
    return sorted(set(errors))


def write_telegram_trade_notifications(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = telegram_trade_notifications_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            TELEGRAM_TRADE_NOTIFICATIONS_EVENT_TYPE,
            TELEGRAM_TRADE_NOTIFICATIONS_COMPONENT,
            {
                "status": written.get("status"),
                "eligible_notification_count": written.get("eligible_notification_count"),
                "live_send_attempted_count": written.get("live_send_attempted_count"),
                "live_send_succeeded_count": written.get("live_send_succeeded_count"),
                "trade_group_notifications_enabled": written.get(
                    "trade_group_notifications_enabled"
                ),
                "trade_group_notifications_dry_run": written.get(
                    "trade_group_notifications_dry_run"
                ),
                "telegram_command_path_enabled": written.get(
                    "telegram_command_path_enabled"
                ),
                "broker_write_allowed": written.get("broker_write_allowed"),
                "paper_order_allowed": written.get("paper_order_allowed"),
                "live_capital_enabled": written.get("live_capital_enabled"),
                "secret_value_exposed": written.get("secret_value_exposed"),
                "chat_id_exposed": written.get("chat_id_exposed"),
                "bot_token_exposed": written.get("bot_token_exposed"),
                "boundary": written.get("boundary"),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_telegram_trade_notifications(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "eligible_notification_count": written.get("eligible_notification_count"),
        "live_send_attempted_count": written.get("live_send_attempted_count"),
        "live_send_succeeded_count": written.get("live_send_succeeded_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written
