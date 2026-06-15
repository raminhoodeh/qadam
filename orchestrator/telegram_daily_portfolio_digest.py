"""Daily Telegram group portfolio digest for Qadam paper mode.

This module is outbound-only. It reports mirrored paper-account state and the
day's trade events to the configured Telegram group. It does not create,
approve, submit, close, cancel, or resize trades.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paper_account import PaperAccountMirrorStore, paper_account_shadow_context
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_specificity,
)


TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION = 1
TELEGRAM_DAILY_PORTFOLIO_DIGEST_RUNTIME_ARTIFACT = "telegram_daily_portfolio_digest.json"
TELEGRAM_DAILY_PORTFOLIO_DIGEST_HISTORY = "telegram_daily_portfolio_digest_history.jsonl"
TELEGRAM_DAILY_PORTFOLIO_DIGEST_EVENT_LOG = "telegram_daily_portfolio_digest_events.jsonl"
TELEGRAM_DAILY_PORTFOLIO_DIGEST_EVENT_TYPE = "telegram_daily_portfolio_digest_recorded"
TELEGRAM_DAILY_PORTFOLIO_DIGEST_COMPONENT = "telegram_daily_portfolio_digest"

TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY = (
    "Daily Telegram portfolio digests are outbound group status reports for "
    "mirrored Alpaca paper-account state only. They cannot create trade "
    "candidates, approve risk, approve execution, submit or close broker "
    "orders, handle Telegram commands, call live broker endpoints, expose "
    "secrets or chat ids, grant Phase 7 proof credit, or enable live capital."
)

TELEGRAM_DAILY_PORTFOLIO_DIGEST_FALSE_FIELDS = (
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_money(value: Any) -> str:
    return f"GBP {_float(value):,.2f}"


def _format_pct(value: Any) -> str:
    return f"{_float(value):+.2f}%"


def _format_qty(value: Any) -> str:
    if value is None or value == "":
        return "unknown"
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _configured_timezone(settings: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(settings.telegram_daily_portfolio_digest_timezone)
    except Exception:  # noqa: BLE001 - configuration should fail closed to UTC.
        return ZoneInfo("UTC")


def _parse_local_cutoff(settings: Settings) -> time:
    text = settings.telegram_daily_portfolio_digest_after_local_time.strip()
    try:
        hour_text, minute_text, *_ = text.split(":")
        return time(hour=max(0, min(23, int(hour_text))), minute=max(0, min(59, int(minute_text))))
    except (TypeError, ValueError):
        return time(hour=17, minute=0)


def _local_context(settings: Settings, generated_at: str) -> dict[str, Any]:
    tz = _configured_timezone(settings)
    generated = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    local_now = generated.astimezone(tz)
    cutoff = _parse_local_cutoff(settings)
    return {
        "timezone": getattr(tz, "key", settings.telegram_daily_portfolio_digest_timezone),
        "local_date": local_now.date().isoformat(),
        "local_time": local_now.strftime("%H:%M"),
        "delivery_after_local_time": cutoff.strftime("%H:%M"),
        "due_for_delivery": local_now.time() >= cutoff,
        "local_now": local_now,
    }


def telegram_daily_portfolio_digest_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / TELEGRAM_DAILY_PORTFOLIO_DIGEST_RUNTIME_ARTIFACT,
        runtime / TELEGRAM_DAILY_PORTFOLIO_DIGEST_HISTORY,
        runtime / TELEGRAM_DAILY_PORTFOLIO_DIGEST_EVENT_LOG,
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
                and payload.get("message_class") == "daily_portfolio_digest"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "daily_portfolio_digest",
        "delivery_key": payload.get("delivery_key"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
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


def _portfolio_snapshot(settings: Settings) -> dict[str, Any]:
    context = paper_account_shadow_context(settings=settings)
    starting_balance = _float(context.get("trial_allocation_gbp"), _float(settings.trial_balance_gbp))
    equity = _float(context.get("equity_gbp"), _float(context.get("current_balance_gbp"), starting_balance))
    cash = _float(context.get("cash_gbp"), equity)
    realized = _float(context.get("realized_pnl_gbp"))
    unrealized = _float(context.get("unrealized_pnl_gbp"))
    total_pnl = round(equity - starting_balance, 2)
    performance_pct = round((total_pnl / starting_balance * 100), 4) if starting_balance else 0.0
    return {
        "status": str(context.get("status") or "unknown"),
        "trial_allocation_gbp": round(starting_balance, 2),
        "portfolio_value_gbp": round(equity, 2),
        "current_balance_gbp": round(_float(context.get("current_balance_gbp"), equity), 2),
        "cash_gbp": round(cash, 2),
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


def _same_local_date(timestamp: Any, local_date: str, tz: ZoneInfo) -> bool:
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False
    return parsed.astimezone(tz).date().isoformat() == local_date


def _safe_event_time(*values: Any) -> str | None:
    for value in values:
        parsed = _parse_timestamp(value)
        if parsed is not None:
            return parsed.isoformat()
    return None


def _daily_trade_events(settings: Settings, local_date: str, tz: ZoneInfo) -> list[dict[str, Any]]:
    store = PaperAccountMirrorStore(settings=settings)
    events: list[dict[str, Any]] = []

    for order in store.read_orders():
        event_at = _safe_event_time(order.filled_at, order.submitted_at)
        if not _same_local_date(event_at, local_date, tz):
            continue
        status = str(order.status or "mirrored_order")
        summary = (
            f"{str(order.direction or 'unknown').upper()} {_format_qty(order.filled_quantity or order.quantity)} "
            f"{order.instrument} ({status})"
        )
        events.append(
            {
                "event_type": "paper_order",
                "instrument": order.instrument,
                "direction": order.direction,
                "quantity": order.filled_quantity or order.quantity,
                "status": status,
                "event_at": event_at,
                "summary": summary,
            }
        )

    for trade in store.read_closed_trades():
        event_at = _safe_event_time(trade.closed_at, trade.opened_at)
        if not _same_local_date(event_at, local_date, tz):
            continue
        summary = (
            f"CLOSED {trade.instrument} "
            f"{_format_money(trade.realized_pnl_gbp)} realized ({trade.postmortem_status})"
        )
        events.append(
            {
                "event_type": "closed_paper_trade",
                "instrument": trade.instrument,
                "direction": trade.direction,
                "quantity": None,
                "status": trade.postmortem_status,
                "event_at": event_at,
                "realized_pnl_gbp": trade.realized_pnl_gbp,
                "summary": summary,
            }
        )

    for position in store.read_positions():
        event_at = _safe_event_time(position.opened_at)
        if not _same_local_date(event_at, local_date, tz):
            continue
        summary = (
            f"OPEN {str(position.direction or 'unknown').upper()} "
            f"{_format_qty(position.quantity)} {position.instrument}"
        )
        events.append(
            {
                "event_type": "open_paper_position",
                "instrument": position.instrument,
                "direction": position.direction,
                "quantity": position.quantity,
                "status": position.status,
                "event_at": event_at,
                "summary": summary,
            }
        )

    return sorted(events, key=lambda event: str(event.get("event_at") or ""))


def _paperops_daily_context(settings: Settings) -> dict[str, Any]:
    summary = _read_json(_runtime_dir(settings) / "paperops_autonomous_pass_summary.json")
    active = _read_json(_runtime_dir(settings) / "paperops_active_paper_trading_automation.json")
    states = summary.get("states", {}) if isinstance(summary.get("states"), dict) else {}
    paper_growth = (
        summary.get("paper_growth_trial", {})
        if isinstance(summary.get("paper_growth_trial"), dict)
        else {}
    )
    paper_runtime = (
        summary.get("paper_runtime", {})
        if isinstance(summary.get("paper_runtime"), dict)
        else {}
    )
    qualified_count = _int(
        states.get("qualified_setup_count")
        or paper_growth.get("qualified_setup_count")
        or active.get("qualified_setup_count")
    )
    submitted_count = _int(
        states.get("submitted_paper_order_count")
        or paper_runtime.get("submitted_paper_order_count")
        or active.get("submitted_paper_order_count")
    )
    idle_reason = str(
        states.get("idle_reason")
        or summary.get("idle_reason")
        or active.get("idle_reason")
        or ""
    ).strip()
    if not idle_reason:
        if qualified_count <= 0:
            idle_reason = "no qualified setup cleared the paper sizing and evidence gates"
        elif submitted_count <= 0:
            idle_reason = "qualified setup review did not reach the guarded submit path"
        else:
            idle_reason = "submitted paper-order state is already recorded"
    return {
        "autonomous_pass_status": summary.get("status", "not_run"),
        "active_automation_status": active.get("status", "not_run"),
        "run_day": summary.get("run_day") or states.get("run_day"),
        "actual_calendar_run": summary.get("actual_calendar_run") is True,
        "qualified_setup_count": qualified_count,
        "submitted_paper_order_count": submitted_count,
        "idle_reason": idle_reason,
    }


def _delivery_key(local_date: str) -> str:
    raw = f"qadam:telegram_daily_portfolio_digest:{local_date}:group"
    return sha256(raw.encode("utf-8")).hexdigest()


def _render_digest_message(
    *,
    local_date: str,
    timezone_name: str,
    portfolio: dict[str, Any],
    daily_trades: list[dict[str, Any]],
    paperops_context: dict[str, Any],
) -> tuple[str, str]:
    trade_lines = [str(trade.get("summary") or "").strip() for trade in daily_trades[:8]]
    if not trade_lines:
        trade_summary = "none recorded"
    else:
        trade_summary = "; ".join(line for line in trade_lines if line)
    if len(daily_trades) > 8:
        trade_summary = f"{trade_summary}; +{len(daily_trades) - 8} more"

    title = "Qadam"
    body = (
        f"Qadam's paper portfolio update for {local_date} is ready. The portfolio is now "
        f"{_format_money(portfolio['portfolio_value_gbp'])}, which is "
        f"{_format_money(portfolio['total_pnl_gbp'])} ({_format_pct(portfolio['performance_pct'])}) "
        f"against the {_format_money(portfolio['trial_allocation_gbp'])} paper allocation. "
        f"Today it has {portfolio['open_position_count']} open positions, {portfolio['order_count']} orders "
        f"on record, and {portfolio['closed_trade_count']} closed paper trades."
        "\n\n"
        f"Trades made today were {trade_summary}. For now, the reason Qadam is waiting or moving slowly is: "
        f"{paperops_context['idle_reason']}. This is only a paper-trading update; Telegram is explaining "
        "what happened and cannot approve, place, change, or close trades, and live capital remains off."
    )
    return title, body


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def build_daily_portfolio_digest(
    settings: Settings | None = None,
    *,
    send_requested: bool = False,
    force: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    local = _local_context(settings, generated_at)
    tz = _configured_timezone(settings)
    local_date = str(local["local_date"])
    delivery_key = _delivery_key(local_date)
    portfolio = _portfolio_snapshot(settings)
    daily_trades = _daily_trade_events(settings, local_date, tz)
    paperops_context = _paperops_daily_context(settings)
    title, body = _render_digest_message(
        local_date=local_date,
        timezone_name=str(local["timezone"]),
        portfolio=portfolio,
        daily_trades=daily_trades,
        paperops_context=paperops_context,
    )
    message_preview_redacted = _safe_text(title, body)
    message_specificity = telegram_message_specificity(title, body)
    message_style = telegram_human_message_style(title, body)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    enabled = settings.telegram_daily_portfolio_digest_enabled
    dry_run = settings.telegram_daily_portfolio_digest_dry_run
    due_for_delivery = bool(local["due_for_delivery"] or force)
    already_sent = delivery_key in _sent_delivery_keys(settings)
    eligible = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and message_preview_redacted
        and message_specificity["status"] == "specific"
        and message_style["status"] == "human"
    )

    blockers: list[str] = []
    if not eligible:
        blockers.append("daily_digest_not_eligible")
    if message_specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if message_style["status"] != "human":
        blockers.append("telegram_message_not_human")
    if not due_for_delivery:
        blockers.append("daily_digest_not_due_until_end_of_day")
    if not enabled:
        blockers.append("daily_portfolio_digest_disabled")
    if dry_run:
        blockers.append("daily_portfolio_digest_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    if already_sent:
        blockers.append("daily_portfolio_digest_already_sent")

    status = "not_due"
    if due_for_delivery and eligible:
        status = "dry_run_ready" if dry_run else "ready_to_send"
    if due_for_delivery and eligible and not enabled:
        status = "blocked_pending_enablement"
    if already_sent:
        status = "already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    text = body

    if (
        send_requested
        and due_for_delivery
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
        except Exception as exc:  # noqa: BLE001 - persist sanitized failure only.
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

    artifact = {
        "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
        "artifact_type": "telegram_daily_portfolio_digest",
        "artifact_id": f"telegram:daily-portfolio-digest:{local_date}",
        "phase": "PaperOps",
        "stage": "Daily-Portfolio-Digest",
        "status": status,
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
        "target": "group",
        "recipient_scope": "fund_manager_group",
        "delivery_key": delivery_key,
        "local_date": local_date,
        "timezone": local["timezone"],
        "local_time": local["local_time"],
        "delivery_after_local_time": local["delivery_after_local_time"],
        "due_for_delivery": due_for_delivery,
        "force_delivery_window": force,
        "already_sent": already_sent,
        "daily_portfolio_digest_enabled": enabled,
        "daily_portfolio_digest_dry_run": dry_run,
        "send_requested": send_requested,
        "bot_configured": bot_configured,
        "group_chat_configured": group_chat_configured,
        "message_class": "daily_portfolio_digest",
        "message_preview": {"title": title, "body": body, "dashboard_link": "qadam.trade/dashboard/"},
        "message_preview_redacted": message_preview_redacted,
        "message_specificity": message_specificity,
        "message_specificity_status": message_specificity["status"],
        "message_specificity_score": message_specificity["score"],
        "message_fingerprint": message_specificity["fingerprint"],
        "message_human_style": message_style,
        "message_human_style_status": message_style["status"],
        "portfolio_snapshot": portfolio,
        "portfolio_balance_gbp": portfolio["portfolio_value_gbp"],
        "portfolio_total_pnl_gbp": portfolio["total_pnl_gbp"],
        "portfolio_performance_pct": portfolio["performance_pct"],
        "portfolio_cash_gbp": portfolio["cash_gbp"],
        "daily_trade_count": len(daily_trades),
        "daily_trade_summaries": [str(trade.get("summary") or "") for trade in daily_trades],
        "daily_trades": daily_trades,
        "paperops_context": paperops_context,
        "paperops_idle_reason": paperops_context["idle_reason"],
        "paperops_qualified_setup_count": paperops_context["qualified_setup_count"],
        "paperops_submitted_paper_order_count": paperops_context["submitted_paper_order_count"],
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
        "boundary": TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
    }
    artifact["validation_errors"] = validate_daily_portfolio_digest(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_daily_portfolio_digest(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "bot_configured",
        "boundary",
        "daily_portfolio_digest_dry_run",
        "daily_portfolio_digest_enabled",
        "daily_trade_count",
        "daily_trade_summaries",
        "delivery_after_local_time",
        "delivery_key",
        "due_for_delivery",
        "group_chat_configured",
        "live_send_attempted",
        "live_send_succeeded",
        "local_date",
        "message_class",
        "message_preview",
        "message_preview_redacted",
        "message_specificity",
        "message_specificity_score",
        "message_specificity_status",
        "message_fingerprint",
        "message_human_style",
        "message_human_style_status",
        "mode",
        "paperops_context",
        "paperops_idle_reason",
        "portfolio_balance_gbp",
        "portfolio_performance_pct",
        "portfolio_snapshot",
        "portfolio_total_pnl_gbp",
        "public_safe",
        "schema_version",
        "send_requested",
        "status",
        "target",
        "timezone",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("telegram_daily_portfolio_digest_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION:
        errors.append("telegram_daily_portfolio_digest_schema_version_mismatch")
    if artifact.get("artifact_type") != "telegram_daily_portfolio_digest":
        errors.append("telegram_daily_portfolio_digest_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("telegram_daily_portfolio_digest_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("telegram_daily_portfolio_digest_mode_not_paper")
    if artifact.get("target") != "group":
        errors.append("telegram_daily_portfolio_digest_target_not_group")
    if artifact.get("message_class") != "daily_portfolio_digest":
        errors.append("telegram_daily_portfolio_digest_message_class_invalid")
    if artifact.get("status") not in {
        "already_sent",
        "blocked_pending_enablement",
        "dry_run_ready",
        "failed",
        "invalid",
        "not_due",
        "ready_to_send",
        "sent",
    }:
        errors.append("telegram_daily_portfolio_digest_status_invalid")
    preview = artifact.get("message_preview", {})
    if not isinstance(preview, dict):
        errors.append("telegram_daily_portfolio_digest_preview_missing")
    else:
        title = str(preview.get("title") or "")
        body = str(preview.get("body") or "")
        if not title.strip() or not body.strip():
            errors.append("telegram_daily_portfolio_digest_preview_empty")
        style = telegram_human_message_style(title, body)
        if style["status"] != "human":
            errors.append("telegram_daily_portfolio_digest_message_not_human:" + ",".join(style["errors"]))
        for phrase in (
            "Portfolio balance:",
            "Performance:",
            "Trades made today:",
            "Why no/next trade:",
            "PaperOps context:",
            "Current impact:",
            "Dashboard: qadam.trade/dashboard/",
            "Mode: paper only; live capital remains blocked.",
        ):
            if phrase in body:
                errors.append("telegram_daily_portfolio_digest_message_too_verbose:" + phrase)
        if not _safe_text(title, body):
            errors.append("telegram_daily_portfolio_digest_forbidden_text")
    if artifact.get("message_human_style_status") != "human":
        errors.append("telegram_daily_portfolio_digest_human_style_status_not_human")
    specificity = artifact.get("message_specificity", {})
    if not isinstance(specificity, dict):
        errors.append("telegram_daily_portfolio_digest_specificity_missing")
    else:
        if specificity.get("status") != "specific":
            errors.append("telegram_daily_portfolio_digest_message_not_specific")
        if _int(specificity.get("score")) < _int(specificity.get("minimum_score", 70)):
            errors.append("telegram_daily_portfolio_digest_specificity_score_low")
    if artifact.get("message_specificity_status") != "specific":
        errors.append("telegram_daily_portfolio_digest_specificity_status_not_specific")
    if _int(artifact.get("message_specificity_score")) < 70:
        errors.append("telegram_daily_portfolio_digest_specificity_score_low")
    if not str(artifact.get("message_fingerprint") or "").strip():
        errors.append("telegram_daily_portfolio_digest_message_fingerprint_missing")
    if not isinstance(artifact.get("paperops_context"), dict):
        errors.append("telegram_daily_portfolio_digest_paperops_context_missing")
    if not str(artifact.get("paperops_idle_reason") or "").strip():
        errors.append("telegram_daily_portfolio_digest_idle_reason_missing")
    if artifact.get("message_preview_redacted") is not True:
        errors.append("telegram_daily_portfolio_digest_preview_not_redacted")
    portfolio = artifact.get("portfolio_snapshot", {})
    if not isinstance(portfolio, dict):
        errors.append("telegram_daily_portfolio_digest_portfolio_missing")
    else:
        if _float(artifact.get("portfolio_balance_gbp")) != _float(portfolio.get("portfolio_value_gbp")):
            errors.append("telegram_daily_portfolio_digest_balance_mismatch")
        if _float(artifact.get("portfolio_total_pnl_gbp")) != _float(portfolio.get("total_pnl_gbp")):
            errors.append("telegram_daily_portfolio_digest_pnl_mismatch")
        if _float(artifact.get("portfolio_performance_pct")) != _float(portfolio.get("performance_pct")):
            errors.append("telegram_daily_portfolio_digest_performance_mismatch")
    daily_trades = artifact.get("daily_trades", [])
    summaries = artifact.get("daily_trade_summaries", [])
    if not isinstance(daily_trades, list):
        errors.append("telegram_daily_portfolio_digest_trades_not_list")
        daily_trades = []
    if not isinstance(summaries, list):
        errors.append("telegram_daily_portfolio_digest_trade_summaries_not_list")
        summaries = []
    if _int(artifact.get("daily_trade_count")) != len(daily_trades):
        errors.append("telegram_daily_portfolio_digest_trade_count_mismatch")
    if len(summaries) != len(daily_trades):
        errors.append("telegram_daily_portfolio_digest_trade_summary_count_mismatch")
    if artifact.get("live_send_attempted") is True:
        if artifact.get("send_requested") is not True:
            errors.append("telegram_daily_portfolio_digest_live_attempt_without_request")
        if artifact.get("due_for_delivery") is not True:
            errors.append("telegram_daily_portfolio_digest_live_attempt_before_due")
        if artifact.get("daily_portfolio_digest_enabled") is not True:
            errors.append("telegram_daily_portfolio_digest_live_attempt_without_gate")
        if artifact.get("daily_portfolio_digest_dry_run") is not False:
            errors.append("telegram_daily_portfolio_digest_live_attempt_in_dry_run")
        if artifact.get("bot_configured") is not True:
            errors.append("telegram_daily_portfolio_digest_live_attempt_without_bot")
        if artifact.get("group_chat_configured") is not True:
            errors.append("telegram_daily_portfolio_digest_live_attempt_without_group")
    if artifact.get("live_send_succeeded") is True and artifact.get("status") != "sent":
        errors.append("telegram_daily_portfolio_digest_succeeded_status_mismatch")
    for field in TELEGRAM_DAILY_PORTFOLIO_DIGEST_FALSE_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"telegram_daily_portfolio_digest_authority_enabled:{field}")
    if "cannot create trade candidates" not in str(artifact.get("boundary") or ""):
        errors.append("telegram_daily_portfolio_digest_boundary_weak")
    if artifact.get("recorded") is True:
        if artifact.get("event_log_written") is not True:
            errors.append("telegram_daily_portfolio_digest_event_log_missing")
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("telegram_daily_portfolio_digest_event_count_mismatch")
    return sorted(set(errors))


def write_daily_portfolio_digest(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = telegram_daily_portfolio_digest_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            TELEGRAM_DAILY_PORTFOLIO_DIGEST_EVENT_TYPE,
            TELEGRAM_DAILY_PORTFOLIO_DIGEST_COMPONENT,
            {
                "status": written.get("status"),
                "local_date": written.get("local_date"),
                "due_for_delivery": written.get("due_for_delivery"),
                "daily_trade_count": written.get("daily_trade_count"),
                "portfolio_balance_gbp": written.get("portfolio_balance_gbp"),
                "portfolio_performance_pct": written.get("portfolio_performance_pct"),
                "live_send_attempted": written.get("live_send_attempted"),
                "live_send_succeeded": written.get("live_send_succeeded"),
                "telegram_command_path_enabled": written.get("telegram_command_path_enabled"),
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
    written["validation_errors"] = validate_daily_portfolio_digest(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "local_date": written.get("local_date"),
        "due_for_delivery": written.get("due_for_delivery"),
        "daily_trade_count": written.get("daily_trade_count"),
        "portfolio_balance_gbp": written.get("portfolio_balance_gbp"),
        "portfolio_performance_pct": written.get("portfolio_performance_pct"),
        "live_send_attempted": written.get("live_send_attempted"),
        "live_send_succeeded": written.get("live_send_succeeded"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "invalid_json"}
    return payload if isinstance(payload, dict) else {}


def telegram_daily_portfolio_digest_public_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    output_path, _, _ = telegram_daily_portfolio_digest_paths(settings)
    artifact = _read_json(output_path)
    if not artifact:
        return {
            "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
            "status": "not_run",
            "enabled": settings.telegram_daily_portfolio_digest_enabled,
            "dry_run": settings.telegram_daily_portfolio_digest_dry_run,
            "target": "group",
            "local_date": None,
            "timezone": settings.telegram_daily_portfolio_digest_timezone,
            "delivery_after_local_time": settings.telegram_daily_portfolio_digest_after_local_time,
            "due_for_delivery": False,
            "already_sent": False,
            "portfolio_balance_gbp": None,
            "portfolio_total_pnl_gbp": None,
            "portfolio_performance_pct": None,
            "daily_trade_count": 0,
            "daily_trade_summaries": [],
            "paperops_idle_reason": None,
            "paperops_qualified_setup_count": 0,
            "paperops_submitted_paper_order_count": 0,
            "message_specificity_status": "not_run",
            "message_specificity_score": 0,
            "message_fingerprint": None,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "telegram_message_id_present": False,
            "last_delivery_failure_category": None,
            "blocker_count": 0,
            "blockers": [],
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
        }
    return {
        "schema_version": TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
        "status": artifact.get("status", "unknown"),
        "enabled": artifact.get("daily_portfolio_digest_enabled") is True,
        "dry_run": artifact.get("daily_portfolio_digest_dry_run") is True,
        "target": "group",
        "local_date": artifact.get("local_date"),
        "timezone": artifact.get("timezone"),
        "delivery_after_local_time": artifact.get("delivery_after_local_time"),
        "due_for_delivery": artifact.get("due_for_delivery") is True,
        "already_sent": artifact.get("already_sent") is True,
        "portfolio_balance_gbp": artifact.get("portfolio_balance_gbp"),
        "portfolio_total_pnl_gbp": artifact.get("portfolio_total_pnl_gbp"),
        "portfolio_performance_pct": artifact.get("portfolio_performance_pct"),
        "daily_trade_count": _int(artifact.get("daily_trade_count")),
        "daily_trade_summaries": [
            str(item) for item in artifact.get("daily_trade_summaries", []) if str(item).strip()
        ][:8],
        "paperops_idle_reason": artifact.get("paperops_idle_reason"),
        "paperops_qualified_setup_count": _int(artifact.get("paperops_qualified_setup_count")),
        "paperops_submitted_paper_order_count": _int(
            artifact.get("paperops_submitted_paper_order_count")
        ),
        "message_specificity_status": artifact.get("message_specificity_status"),
        "message_specificity_score": _int(artifact.get("message_specificity_score")),
        "message_fingerprint": artifact.get("message_fingerprint"),
        "live_send_attempted": artifact.get("live_send_attempted") is True,
        "live_send_succeeded": artifact.get("live_send_succeeded") is True,
        "telegram_message_id_present": artifact.get("telegram_message_id_present") is True,
        "last_delivery_failure_category": artifact.get("delivery_failure_category"),
        "blocker_count": _int(artifact.get("blocker_count")),
        "blockers": [str(item) for item in artifact.get("blockers", [])],
        "telegram_command_path_enabled": False,
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "live_capital_enabled": False,
        "boundary": TELEGRAM_DAILY_PORTFOLIO_DIGEST_BOUNDARY,
    }
