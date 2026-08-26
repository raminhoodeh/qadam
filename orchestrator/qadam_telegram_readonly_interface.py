"""Read-only Telegram query interface for Qadam's configured group.

The interface renders deterministic answers from canonical runtime artifacts.
It never invokes an LLM and cannot mutate research, strategy, risk, execution,
broker, proof, policy, or live-capital state.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    write_json_atomic,
)
from orchestrator.secrets import secret_status, secret_value

SCHEMA_VERSION = "qadam_telegram_readonly_interface.v1"
STATUS_ARTIFACT = "qadam_telegram_readonly_interface_status.json"
CHECK_ARTIFACT = "qadam_telegram_readonly_interface_checks.json"
RESPONSE_LEDGER_ARTIFACT = "qadam_telegram_readonly_response_ledger.jsonl"
MAX_LEDGER_ROWS = 2_000
MAX_RESPONSE_CHARS = 1_800

QUERY_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "Current operating and paper-trading state"),
    ("portfolio", "Paper balance, P&L and open holdings"),
    ("trading", "Latest decision, gate and PaperOps state"),
    ("patterns", "Highest-ranked current research patterns"),
    ("health", "Operator, circuit and freshness health"),
    ("repairs", "Self-healing critic and repair queue state"),
    ("help", "Available read-only Qadam queries"),
)
QUERY_NAMES = tuple(item[0] for item in QUERY_COMMANDS)
FORBIDDEN_CONTROL_COMMANDS = {
    "approve",
    "buy",
    "cancel",
    "close",
    "execute",
    "live",
    "order",
    "paperops",
    "reject",
    "repair",
    "resize",
    "risk",
    "sell",
    "submit",
    "trade",
}

READONLY_BOUNDARY = (
    "Telegram can request a plain-English readout of canonical Qadam state. "
    "It cannot create or change research goals, evidence, patterns, strategies, "
    "candidates, approvals, risk, orders, broker state, proof credit, policy, "
    "quantum jobs, code, secrets, or live-capital authority."
)

Sender = Callable[[str, str, str, int | None], dict[str, Any]]


def _authority() -> dict[str, bool]:
    return {
        "read_only": True,
        "paper_only": True,
        "public_safe": True,
        "query_response_send_allowed": True,
        "control_commands_disabled": True,
        "telegram_command_authority": False,
        "trade_candidate_creation_allowed": False,
        "strategy_mutation_allowed": False,
        "risk_approval_allowed": False,
        "execution_approval_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "quantum_job_allowed": False,
        "code_edit_allowed": False,
        "secret_readout_allowed": False,
        "live_capital_enabled": False,
    }


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _freshness(value: Any) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return "timestamp unavailable"
    seconds = max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3_600:
        return f"{seconds // 60}m ago"
    if seconds < 86_400:
        return f"{seconds // 3_600}h ago"
    return f"{seconds // 86_400}d ago"


def _local_timestamp(value: Any) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return "unknown time"
    local = parsed.astimezone(ZoneInfo("Asia/Dubai"))
    return local.strftime("%d %b, %H:%M GST")


def _human_state(value: Any) -> str:
    text = str(value or "unknown").strip().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).capitalize()


def _money(value: Any, *, signed: bool = False) -> str:
    number = _as_float(value)
    sign = "+" if signed and number > 0 else "-" if number < 0 else ""
    return f"{sign}US${abs(number):,.2f}"


def _pattern_state(value: Any) -> str:
    return {
        "score_ready_for_tape": "ready for historical outcome tracking",
        "blocked_missing_critical_features": "waiting for required evidence",
        "score_not_ready_for_tape": "not ready for outcome tracking",
    }.get(str(value or ""), _human_state(value).lower())


def _runtime_artifacts(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = runtime_dir(settings)
    return {
        "operator": read_json(runtime / "qadam_operator_service_status.json"),
        "critic": read_json(runtime / "qadam_reliability_critic_status.json"),
        "repairs": read_json(runtime / "qadam_operator_repair_queue.json"),
        "circuits": read_json(runtime / "qadam_operator_circuit_breakers.json"),
        "paperops": read_json(runtime / "paperops_autonomous_pass_summary.json"),
        "router": read_json(runtime / "qadam_router_v3_why_not_trading_now.json"),
        "mirror": read_json(runtime / "alpaca_paper_mirror.json"),
        "cockpit": read_json(runtime / "cockpit-status.json"),
        "patterns": read_json(runtime / "qadam_pattern_score_v3.json"),
    }


def _portfolio(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cockpit = _safe_dict(artifacts.get("cockpit"))
    projected = _safe_dict(cockpit.get("dashboard_portfolio"))
    mirror = _safe_dict(artifacts.get("mirror"))
    snapshot = _safe_dict(mirror.get("snapshot"))
    positions = _safe_list(projected.get("positions"))
    if not positions:
        positions = _safe_list(projected.get("current_positions"))
    return {
        "generated_at": projected.get("generated_at") or snapshot.get("observed_at"),
        "equity": projected.get("current_balance_gbp", snapshot.get("equity")),
        "cash": projected.get("cash_gbp", snapshot.get("cash")),
        "starting_balance": projected.get(
            "starting_balance_gbp", snapshot.get("starting_balance")
        ),
        "realized_pnl": projected.get("realized_pnl_gbp", snapshot.get("realized_pnl")),
        "unrealized_pnl": projected.get(
            "unrealized_pnl_gbp", snapshot.get("unrealized_pnl")
        ),
        "open_position_count": projected.get(
            "open_position_count", snapshot.get("open_position_count")
        ),
        "closed_trade_count": projected.get(
            "closed_trade_count", snapshot.get("closed_trade_count")
        ),
        "positions": positions,
        "market_clock": _safe_dict(projected.get("market_clock")),
        "mirror_status": mirror.get("status"),
    }


def _latest_pattern_rows(settings: Settings) -> list[dict[str, Any]]:
    rows = read_jsonl(runtime_dir(settings) / "qadam_pattern_score_v3_records.jsonl", limit=1_000)
    generated_values = [str(row.get("generated_at") or "") for row in rows]
    latest_generation = max(generated_values, default="")
    current = [row for row in rows if str(row.get("generated_at") or "") == latest_generation]
    ranked = sorted(current, key=lambda row: _as_float(row.get("raw_pattern_score")), reverse=True)
    distinct: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in ranked:
        label = str(row.get("strategy_label") or row.get("market_family") or "Unlabelled pattern")
        family = str(row.get("market_family") or "")
        key = (label, family)
        if key in seen:
            continue
        seen.add(key)
        distinct.append(row)
    return distinct


def classify_readonly_query(text: str, bot_username: str | None = None) -> str | None:
    """Return a normalized read-only query without treating it as trade authority."""

    stripped = str(text or "").strip()
    if not stripped:
        return None
    first = stripped.split(maxsplit=1)[0].lower()
    normalized_username = str(bot_username or "").strip().lstrip("@").lower()
    command: str | None = None
    if first.startswith("/"):
        command = first[1:].split("@", 1)[0]
    else:
        lowered = stripped.lower()
        if lowered.startswith("qadam "):
            command = lowered.split(maxsplit=2)[1]
        elif normalized_username and lowered.startswith(f"@{normalized_username} "):
            command = lowered.split(maxsplit=2)[1]
    aliases = {
        "qadam": "status",
        "start": "help",
        "why": "trading",
        "positions": "portfolio",
        "pattern": "patterns",
        "selfheal": "repairs",
        "selfhealing": "repairs",
    }
    command = aliases.get(str(command or ""), command)
    if command in QUERY_NAMES:
        return command
    if command in FORBIDDEN_CONTROL_COMMANDS:
        return "forbidden_control"
    return None


def _help_response() -> str:
    return (
        "Qadam read-only group interface\n"
        "/status - operating summary\n"
        "/portfolio - paper balance and holdings\n"
        "/trading - current decision and PaperOps state\n"
        "/patterns - highest-ranked research patterns\n"
        "/health - services, freshness and circuits\n"
        "/repairs - self-healing and repair status\n"
        "/help - show these queries\n\n"
        "These queries only read canonical state. They cannot create or alter trades."
    )


def _forbidden_response() -> str:
    return (
        "Qadam's Telegram interface is read-only. Trading, approval, repair and "
        "capital-control instructions are not accepted here. Use /trading to inspect "
        "the current guarded paper-trade state or /repairs to inspect self-healing."
    )


def build_readonly_query_response(
    command: str,
    *,
    settings: Settings | None = None,
) -> tuple[str, dict[str, Any]]:
    """Render one concise response exclusively from local canonical artifacts."""

    active = settings or Settings.from_env()
    artifacts = _runtime_artifacts(active)
    operator = _safe_dict(artifacts["operator"])
    critic = _safe_dict(artifacts["critic"])
    repairs = _safe_dict(artifacts["repairs"])
    circuits = _safe_dict(artifacts["circuits"])
    paperops = _safe_dict(artifacts["paperops"])
    router = _safe_dict(artifacts["router"])
    portfolio = _portfolio(artifacts)
    paper_runtime = _safe_dict(paperops.get("paper_runtime"))
    handoff = _safe_dict(paperops.get("router_v3_handoff_boundary"))
    source_artifacts: list[str] = []

    if command == "help":
        text = _help_response()
    elif command == "forbidden_control":
        text = _forbidden_response()
    elif command == "status":
        source_artifacts = [
            "qadam_operator_service_status.json",
            "qadam_reliability_critic_status.json",
            "paperops_autonomous_pass_summary.json",
            "alpaca_paper_mirror.json",
        ]
        total_pnl = _as_float(portfolio["equity"]) - _as_float(portfolio["starting_balance"])
        text = (
            "Qadam status\n"
            f"Operator: {_human_state(operator.get('status'))}; "
            f"operational={str(operator.get('operational_ready') is True).lower()}, "
            f"observation={str(operator.get('observation_ready') is True).lower()}.\n"
            f"PaperOps: {_human_state(paperops.get('status'))}; "
            f"{_as_int(paper_runtime.get('fresh_eligible_submit_count'))} eligible, "
            f"{_as_int(paper_runtime.get('submitted_paper_order_count'))} submitted in the latest pass.\n"
            f"Portfolio: {_money(portfolio['equity'])} ({_money(total_pnl, signed=True)}); "
            f"{_as_int(portfolio['open_position_count'])} open, "
            f"{_as_int(portfolio['closed_trade_count'])} closed.\n"
            f"Self-healing: {_human_state(critic.get('repair_packet', {}).get('status'))}; "
            f"{_as_int(circuits.get('open_circuit_count'))} open circuits, "
            f"{_as_int(repairs.get('open_request_count'))} open repairs.\n"
            f"Updated: {_local_timestamp(operator.get('generated_at'))}."
        )
    elif command == "portfolio":
        source_artifacts = ["cockpit-status.json", "alpaca_paper_mirror.json"]
        position_lines: list[str] = []
        for row in _safe_list(portfolio["positions"])[:6]:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("instrument") or row.get("symbol") or "Unknown")
            quantity = _as_float(row.get("quantity"))
            pnl = row.get("unrealized_pnl_gbp", row.get("unrealized_pnl"))
            quantity_text = str(int(quantity)) if quantity.is_integer() else f"{quantity:g}"
            unit = "share" if quantity == 1 else "shares"
            position_lines.append(
                f"- {symbol}: {quantity_text} {unit}, {_money(pnl, signed=True)} open P&L"
            )
        holdings = "\n".join(position_lines) if position_lines else "- No open paper positions"
        total_pnl = _as_float(portfolio["equity"]) - _as_float(portfolio["starting_balance"])
        text = (
            "Qadam paper portfolio\n"
            f"Equity: {_money(portfolio['equity'])}\n"
            f"Total P&L: {_money(total_pnl, signed=True)}\n"
            f"Cash: {_money(portfolio['cash'])}\n"
            f"Realized: {_money(portfolio['realized_pnl'], signed=True)}; "
            f"unrealized: {_money(portfolio['unrealized_pnl'], signed=True)}\n"
            f"Holdings:\n{holdings}\n"
            f"Broker mirror: {_human_state(portfolio['mirror_status'])}, "
            f"updated {_freshness(portfolio['generated_at'])}."
        )
    elif command == "trading":
        source_artifacts = [
            "paperops_autonomous_pass_summary.json",
            "qadam_router_v3_why_not_trading_now.json",
            "cockpit-status.json",
        ]
        market = _safe_dict(portfolio.get("market_clock"))
        reason = str(router.get("primary_reason") or "No current router explanation is available.")
        text = (
            "Qadam trading state\n"
            f"Latest PaperOps pass: {_human_state(paperops.get('status'))}.\n"
            f"Eligible setups: {_as_int(paper_runtime.get('fresh_eligible_submit_count'))}; "
            f"accepted handoffs: {_as_int(handoff.get('accepted_handoff_count'))}; "
            f"submitted orders: {_as_int(paper_runtime.get('submitted_paper_order_count'))}; "
            f"duplicates blocked: {_as_int(paper_runtime.get('duplicate_submit_count'))}.\n"
            f"Current Router: {_human_state(router.get('current_router_state'))}. {reason}\n"
            f"Market: {_human_state(market.get('status'))}; "
            f"next open {_local_timestamp(market.get('next_open'))}.\n"
            f"PaperOps updated {_freshness(paperops.get('generated_at'))}."
        )
    elif command == "patterns":
        source_artifacts = [
            "qadam_pattern_score_v3.json",
            "qadam_pattern_score_v3_records.jsonl",
        ]
        rows = _latest_pattern_rows(active)
        pattern_lines: list[str] = []
        for index, row in enumerate(rows[:3], start=1):
            label = str(row.get("strategy_label") or row.get("market_family") or "Unlabelled")
            score = _as_float(row.get("raw_pattern_score"))
            instrument = str(row.get("instrument") or "unmapped")
            state = _pattern_state(row.get("confidence_state"))
            pattern_lines.append(
                f"{index}. {label}: research score {score:.3f} on {instrument} - {state}"
            )
        body = "\n".join(pattern_lines) if pattern_lines else "No current scored patterns are available."
        pattern_generated = rows[0].get("generated_at") if rows else artifacts["patterns"].get("generated_at")
        text = (
            "Qadam pattern research\n"
            f"{body}\n"
            "Research scores rank what deserves testing; they are not return probabilities or trade approval.\n"
            f"Updated {_freshness(pattern_generated)}."
        )
    elif command == "health":
        source_artifacts = [
            "qadam_operator_service_status.json",
            "qadam_operator_circuit_breakers.json",
            "qadam_operator_repair_queue.json",
        ]
        services = [row for row in _safe_list(operator.get("services")) if isinstance(row, dict)]
        fresh_count = sum(
            1 for row in services if _safe_dict(row.get("freshness")).get("state") == "fresh"
        )
        stale_count = sum(
            1 for row in services if _safe_dict(row.get("freshness")).get("state") == "stale"
        )
        text = (
            "Qadam operating health\n"
            f"Operator: {_human_state(operator.get('status'))}.\n"
            f"Services: {fresh_count}/{len(services)} fresh; {stale_count} stale.\n"
            f"Circuits: {_as_int(circuits.get('open_circuit_count'))} open.\n"
            f"Repair queue: {_as_int(repairs.get('open_request_count'))} open, "
            f"{_as_int(repairs.get('critical_request_count'))} critical.\n"
            f"Reliability critic: {_human_state(critic.get('status'))} - "
            f"{str(critic.get('primary_reason') or 'no explanation reported')}\n"
            f"Updated {_freshness(operator.get('generated_at'))}."
        )
    elif command == "repairs":
        source_artifacts = [
            "qadam_reliability_critic_status.json",
            "qadam_operator_repair_queue.json",
            "qadam_operator_circuit_breakers.json",
        ]
        packet = _safe_dict(critic.get("repair_packet"))
        text = (
            "Qadam self-healing\n"
            f"Critic: {_human_state(critic.get('status'))}; "
            f"state: {_human_state(critic.get('operating_state'))}.\n"
            f"Repair decision: {_human_state(packet.get('status'))}.\n"
            f"Queue: {_as_int(repairs.get('open_request_count'))} open, "
            f"{_as_int(repairs.get('critical_request_count'))} critical.\n"
            f"Circuits: {_as_int(circuits.get('open_circuit_count'))} open.\n"
            f"Reason: {str(critic.get('primary_reason') or 'No repair reason reported.')}\n"
            "Telegram can inspect this state but cannot trigger a repair."
        )
    else:
        raise ValueError(f"unsupported_readonly_query:{command}")

    response = text[:MAX_RESPONSE_CHARS]
    provenance = {
        "source_artifacts": source_artifacts,
        "response_digest": sha256_text(response),
        "response_char_count": len(response),
        "rendered_at": now_iso(),
    }
    return response, provenance


def _telegram_api_request(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        loaded = json.loads(response.read().decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Telegram returned a non-object response")
    return loaded


def send_readonly_response(
    token: str,
    target: str,
    text: str,
    reply_to_message_id: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": target,
        "text": text,
        "disable_web_page_preview": "true",
    }
    if reply_to_message_id is not None:
        payload["reply_parameters"] = json.dumps(
            {"message_id": reply_to_message_id, "allow_sending_without_reply": True}
        )
    return _telegram_api_request(token, "sendMessage", payload)


def _bounded_append(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl_durable(path, payload)
    try:
        if path.stat().st_size < 2_000_000:
            return
    except OSError:
        return
    rows = read_jsonl(path, limit=MAX_LEDGER_ROWS)
    encoded = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    from orchestrator.qadam_operator_ready_common import atomic_write_text

    atomic_write_text(path, encoded)


def _response_key(update: dict[str, Any], message: dict[str, Any], command: str) -> str:
    identity = {
        "update_id": update.get("update_id"),
        "message_id": message.get("message_id"),
        "command": command,
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _already_delivered(path: Path, response_key: str) -> bool:
    return any(
        row.get("response_key") == response_key and row.get("delivery_status") == "delivered"
        for row in read_jsonl(path, limit=MAX_LEDGER_ROWS)
    )


def handle_readonly_query_update(
    update: dict[str, Any],
    message: dict[str, Any],
    text: str,
    *,
    settings: Settings | None = None,
    token: str | None = None,
    sender: Sender | None = None,
) -> dict[str, Any]:
    """Handle one authorized group query and return retry semantics to the poller."""

    active = settings or Settings.from_env()
    username = secret_value("TELEGRAM_BOT_USERNAME", active)
    command = classify_readonly_query(text, username)
    if command is None:
        return {"handled": False, "retry_required": False}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    target = secret_value("TELEGRAM_GROUP_CHAT_ID", active)
    response_key = _response_key(update, message, command)
    runtime = runtime_dir(active)
    ledger_path = runtime / RESPONSE_LEDGER_ARTIFACT
    base_event = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_readonly_response_event",
        "generated_at": now_iso(),
        "response_key": response_key,
        "update_ref_hash": sha256_text(str(update.get("update_id") or "unknown"))[:24],
        "sender_ref_hash": sha256_text(
            str(_safe_dict(message.get("from")).get("id") or "unknown")
        )[:24],
        "target_ref_hash": sha256_text(str(chat.get("id") or "unknown"))[:24],
        "query": command,
        "authority": _authority(),
        "boundary": READONLY_BOUNDARY,
    }
    if not target or str(chat.get("id")) != str(target):
        event = {**base_event, "delivery_status": "unauthorized_group_ignored"}
        _bounded_append(ledger_path, event)
        return {
            "handled": True,
            "command": command,
            "delivery_status": "unauthorized_group_ignored",
            "retry_required": False,
        }
    if _already_delivered(ledger_path, response_key):
        return {
            "handled": True,
            "command": command,
            "delivery_status": "duplicate_suppressed",
            "retry_required": False,
        }
    response_text, provenance = build_readonly_query_response(command, settings=active)
    send = sender or send_readonly_response
    try:
        provider_result = send(
            str(token or secret_value("TELEGRAM_BOT_TOKEN", active) or ""),
            str(target),
            response_text,
            message.get("message_id") if isinstance(message.get("message_id"), int) else None,
        )
        delivered = provider_result.get("ok") is True
    except Exception as error:  # noqa: BLE001 - never persist provider URLs or secrets
        provider_result = {"ok": False, "error_class": error.__class__.__name__}
        delivered = False
    event = {
        **base_event,
        **provenance,
        "delivery_status": "delivered" if delivered else "delivery_retry_pending",
        "provider_ok": delivered,
        "provider_error_class": provider_result.get("error_class") if not delivered else None,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_created": False,
        "proof_credit_created": False,
        "live_capital_enabled": False,
    }
    _bounded_append(ledger_path, event)
    return {
        "handled": True,
        "command": command,
        "delivery_status": event["delivery_status"],
        "retry_required": not delivered,
        "response_digest": provenance["response_digest"],
    }


def register_readonly_commands(
    *,
    settings: Settings | None = None,
    request: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    token = secret_value("TELEGRAM_BOT_TOKEN", active)
    target = secret_value("TELEGRAM_GROUP_CHAT_ID", active)
    if not token or not target:
        return {"status": "missing_configuration", "registered": False}
    payload = {
        "commands": json.dumps(
            [{"command": command, "description": description} for command, description in QUERY_COMMANDS]
        ),
        "scope": json.dumps({"type": "chat", "chat_id": target}),
        "language_code": "en",
    }
    execute = request or _telegram_api_request
    try:
        result = execute(str(token), "setMyCommands", payload)
    except Exception as error:  # noqa: BLE001
        return {
            "status": "provider_error",
            "registered": False,
            "provider_error_class": error.__class__.__name__,
        }
    return {
        "status": "registered" if result.get("ok") is True else "provider_error",
        "registered": result.get("ok") is True,
        "command_count": len(QUERY_COMMANDS),
    }


def announce_readonly_interface(
    *,
    settings: Settings | None = None,
    sender: Sender | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    token = secret_value("TELEGRAM_BOT_TOKEN", active)
    target = secret_value("TELEGRAM_GROUP_CHAT_ID", active)
    if not token or not target:
        return {"status": "missing_configuration", "sent": False}
    runtime = runtime_dir(active)
    ledger_path = runtime / RESPONSE_LEDGER_ARTIFACT
    response_key = sha256_text(f"{SCHEMA_VERSION}:ready_notice")
    if _already_delivered(ledger_path, response_key):
        return {"status": "already_announced", "sent": False}
    text = (
        "Qadam's read-only group interface is ready. Use /status, /portfolio, "
        "/trading, /patterns, /health or /repairs. These queries report canonical "
        "state only and cannot create or alter trades."
    )
    send = sender or send_readonly_response
    try:
        result = send(str(token), str(target), text, None)
        delivered = result.get("ok") is True
    except Exception as error:  # noqa: BLE001
        result = {"ok": False, "error_class": error.__class__.__name__}
        delivered = False
    _bounded_append(
        ledger_path,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_telegram_readonly_response_event",
            "generated_at": now_iso(),
            "response_key": response_key,
            "update_ref_hash": "setup_announcement",
            "sender_ref_hash": "qadam_system",
            "target_ref_hash": sha256_text(str(target))[:24],
            "query": "interface_ready",
            "delivery_status": "delivered" if delivered else "delivery_retry_pending",
            "provider_ok": delivered,
            "provider_error_class": result.get("error_class") if not delivered else None,
            "response_digest": sha256_text(text),
            "response_char_count": len(text),
            "authority": _authority(),
            "boundary": READONLY_BOUNDARY,
        },
    )
    return {"status": "sent" if delivered else "provider_error", "sent": delivered}


def write_interface_status(
    poll_result: dict[str, Any],
    *,
    settings: Settings | None = None,
    registration_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    previous = read_json(runtime / STATUS_ARTIFACT)
    rows = read_jsonl(runtime / RESPONSE_LEDGER_ARTIFACT, limit=MAX_LEDGER_ROWS)
    last = rows[-1] if rows else {}
    poll_status = str(poll_result.get("status") or "unknown")
    enabled = bool(getattr(active, "telegram_inbound_intake_enabled", True))
    token_configured = secret_status("TELEGRAM_BOT_TOKEN", active).configured
    group_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", active).configured
    username_configured = secret_status("TELEGRAM_BOT_USERNAME", active).configured
    registration = registration_result or {}
    commands_registered = (
        registration.get("registered") is True
        or previous.get("commands_registered") is True
    )
    healthy_poll = poll_status in {"ok", "concurrent_poll_skipped"}
    status = (
        "ready"
        if enabled
        and token_configured
        and group_configured
        and username_configured
        and commands_registered
        and healthy_poll
        else "degraded"
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_readonly_interface_status",
        "generated_at": now_iso(),
        "status": status,
        "enabled": enabled,
        "poll_status": poll_status,
        "polling_mode": "shared_locked_getUpdates",
        "poll_interval_seconds": 30,
        "bot_configured": token_configured,
        "group_configured": group_configured,
        "bot_username_configured": username_configured,
        "commands_registered": commands_registered,
        "registered_command_count": len(QUERY_COMMANDS) if commands_registered else 0,
        "available_queries": list(QUERY_NAMES),
        "fetched_update_count": _as_int(poll_result.get("fetched_update_count")),
        "processed_update_count": _as_int(poll_result.get("processed_update_count")),
        "query_count": _as_int(poll_result.get("query_count")),
        "query_delivery_count": _as_int(poll_result.get("query_delivery_count")),
        "query_duplicate_count": _as_int(poll_result.get("query_duplicate_count")),
        "query_unauthorized_count": _as_int(poll_result.get("query_unauthorized_count")),
        "query_delivery_retry_count": _as_int(poll_result.get("query_delivery_retry_count")),
        "response_ledger_count": len(rows),
        "last_query": last.get("query"),
        "last_delivery_status": last.get("delivery_status"),
        "last_query_at": last.get("generated_at"),
        "read_only": True,
        "control_commands_disabled": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": _authority(),
        "boundary": READONLY_BOUNDARY,
    }
    errors = validate_interface_status(payload)
    payload["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    if errors:
        payload["status"] = "degraded"
    write_json_atomic(runtime / STATUS_ARTIFACT, payload)
    return payload


def validate_interface_status(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("telegram_readonly_interface_schema_invalid")
    if payload.get("artifact_type") != "qadam_telegram_readonly_interface_status":
        errors.append("telegram_readonly_interface_artifact_type_invalid")
    authority = _safe_dict(payload.get("authority"))
    if authority.get("read_only") is not True:
        errors.append("telegram_readonly_interface_not_read_only")
    if authority.get("query_response_send_allowed") is not True:
        errors.append("telegram_readonly_interface_query_reply_not_explicit")
    for field in (
        "telegram_command_authority",
        "trade_candidate_creation_allowed",
        "strategy_mutation_allowed",
        "risk_approval_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "proof_credit_allowed",
        "quantum_job_allowed",
        "code_edit_allowed",
        "secret_readout_allowed",
        "live_capital_enabled",
    ):
        if authority.get(field) is not False:
            errors.append(f"telegram_readonly_interface_unsafe_authority:{field}")
    for field in (
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if _as_int(payload.get(field)) != 0:
            errors.append(f"telegram_readonly_interface_unsafe_count:{field}")
    encoded = json.dumps(payload, sort_keys=True).lower()
    for forbidden in ("chat_id", "bot_token", "api_key", "/users/", "ghp_"):
        if forbidden in encoded:
            errors.append("telegram_readonly_interface_secret_or_identifier_exposed")
            break
    if READONLY_BOUNDARY != payload.get("boundary"):
        errors.append("telegram_readonly_interface_boundary_mismatch")
    return sorted(set(errors))


__all__ = [
    "CHECK_ARTIFACT",
    "QUERY_COMMANDS",
    "QUERY_NAMES",
    "READONLY_BOUNDARY",
    "RESPONSE_LEDGER_ARTIFACT",
    "SCHEMA_VERSION",
    "STATUS_ARTIFACT",
    "announce_readonly_interface",
    "build_readonly_query_response",
    "classify_readonly_query",
    "handle_readonly_query_update",
    "register_readonly_commands",
    "send_readonly_response",
    "validate_interface_status",
    "write_interface_status",
]
