"""Independent, durable fill reporting and sustained-failure alerts. No broker writes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import urllib.error
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic
from orchestrator.secrets import secret_value
from orchestrator.telegram_trade_notifications import _telegram_send

STATUS_ARTIFACT = "qadam_trade_delivery_status.json"
DB_ARTIFACT = "qadam-trade-delivery.sqlite3"
MAX_ATTEMPTS = 5


def _hash(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def _time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def confirmed_receipt(response, target):
    result = response.get("result") or {}
    message_id = result.get("message_id")
    return bool(
        response.get("ok") is True
        and isinstance(message_id, int)
        and not isinstance(message_id, bool)
        and message_id > 0
        and str((result.get("chat") or {}).get("id")) == str(target)
    )


def _connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
        event_key TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL,
        state TEXT NOT NULL, created_at REAL NOT NULL, next_at REAL NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, message_id INTEGER,
        target_hash TEXT, error TEXT)""")
    db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
    return db


def _meta(db, key, default=None):
    row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _set_meta(db, key, value):
    db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, str(value)))


def _enqueue(db, key, kind, body, timestamp):
    db.execute(
        "INSERT OR IGNORE INTO deliveries(event_key,kind,body,state,created_at,next_at) "
        "VALUES (?,?,?,'pending',?,?)",
        (key, kind, body, timestamp, timestamp),
    )


def _collect_fills(db, runtime, now):
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    snapshot = mirror.get("snapshot") or {}
    observed = _time(snapshot.get("observed_at"))
    if (
        mirror.get("status") != "ok"
        or not observed
        or not 0 <= (now - observed).total_seconds() <= 1800
    ):
        return ["broker_mirror_not_current"]
    epoch = snapshot.get("paper_epoch_id")
    if not epoch or snapshot.get("mode") != "paper":
        return ["paper_epoch_missing"]
    since = _meta(db, "fills_since")
    if since is None:
        # Initial installation reports the last day, never the archived account history.
        since = (now - timedelta(days=1)).timestamp()
        _set_meta(db, "fills_since", since)
    try:
        orders = [
            json.loads(line)
            for line in (runtime / "paper_orders.jsonl").read_text().splitlines()
            if line.strip()
        ]
        if any(not isinstance(order, dict) for order in orders):
            raise ValueError("invalid_order")
    except (OSError, ValueError):
        return ["broker_order_mirror_unreadable"]
    errors = []
    for order in orders:
        filled = _time(order.get("filled_at"))
        if (
            order.get("paper_epoch_id") != epoch
            or order.get("record_origin") != "broker_mirror"
            or order.get("status") != "filled"
            or not filled
            or not float(since) <= filled.timestamp() <= now.timestamp()
        ):
            continue
        symbol = str(order.get("instrument") or "")
        identity = order.get("broker_order_id_hash")
        try:
            qty, price = float(order["filled_quantity"]), float(order["filled_avg_price"])
            valid = all(math.isfinite(v) and v > 0 for v in (qty, price))
        except (ValueError, TypeError, KeyError):
            valid = False
        currency = str(order.get("account_currency") or snapshot.get("account_currency") or "")
        if (
            not valid
            or not identity
            or not re.fullmatch(r"[A-Z0-9.\-/]{1,20}", symbol)
            or not re.fullmatch(r"[A-Z]{3}", currency)
        ):
            errors.append("invalid_fill_record")
            continue
        intent = order.get("position_intent")
        action = {
            "sell_to_open": "opened a short",
            "buy_to_open": "opened a long",
            "buy_to_close": "bought to close a short",
            "sell_to_close": "sold to close a long",
        }.get(intent)
        if not action:
            action = (
                "bought"
                if order.get("direction") == "buy"
                else "sold"
                if order.get("direction") == "sell"
                else None
            )
        if action is None:
            errors.append("fill_direction_missing")
            continue
        clock = filled.astimezone(ZoneInfo("Asia/Dubai")).strftime("%d %b, %H:%M Dubai")
        body = (
            f"Confirmed paper fill: {action}, {qty:g} {symbol} at {currency} {price:,.2f} "
            f"per share ({currency} {qty * price:,.2f} notional). Filled {clock}.\n\n"
            "This is a completed Alpaca Paper fill, not a pending order or a new trade recommendation."
        )
        _enqueue(db, _hash(f"{epoch}:{identity}:filled"), "paper_fill", body, now.timestamp())
    return sorted(set(errors))


def _collect_health(db, runtime, now):
    operator = read_json(runtime / "qadam_operator_service_status.json")
    observed = _time(operator.get("generated_at"))
    if not observed or not 0 <= (now - observed).total_seconds() <= 300:
        issues = ["operator heartbeat missing or stale"]
    else:
        issues = [
            str(row.get("service_id"))
            for row in operator.get("services", [])
            if (row.get("circuit_breaker") or {}).get("state") in {"open", "half_open"}
            or (row.get("freshness") or {}).get("state") in {"stale", "not_run"}
        ]
        if not issues and operator.get("operational_ready") is not True:
            issues = ["operator readiness not confirmed"]
    team = read_json(runtime / "qadam_hedge_fund_team_health.json")
    team_at = _time(team.get("generated_at"))
    if not team_at or not 0 <= (now - team_at).total_seconds() <= 4 * 60 * 60:
        issues.append("hedge-fund team assessment missing or stale")
    elif team.get("status") != "passed":
        issues.append("hedge-fund team assessment failed")
    signature = ", ".join(sorted(set(issues))) if issues else "healthy"
    if signature != _meta(db, "health_observed"):
        _set_meta(db, "health_observed", signature)
        _set_meta(db, "health_since", now.timestamp())
        return
    since = float(_meta(db, "health_since", now.timestamp()))
    if now.timestamp() - since < 120 or signature == _meta(db, "health_notified"):
        return
    if signature == "healthy" and _meta(db, "health_notified") is None:
        _set_meta(db, "health_notified", signature)
        return
    body = (
        "Qadam operational checks recovered on two consecutive observations. "
        "This confirms current service health, not a guarantee of future uptime or returns."
        if signature == "healthy"
        else f"Qadam needs attention: {signature}. This condition persisted across checks. "
        "The operator's bounded recovery remains responsible for safe repairs; "
        "unresolved failures are not being reported as healthy."
    )
    _enqueue(db, _hash(f"health:{signature}:{since}"), "service_health", body, now.timestamp())
    _set_meta(db, "health_notified", signature)


def _deliver(db, token, target, now, sender):
    # A crash after sendMessage may have delivered. Never blindly resend it.
    db.execute(
        "UPDATE deliveries SET state='uncertain',error='interrupted_send' WHERE state='sending'"
    )
    db.commit()
    for row in db.execute(
        "SELECT * FROM deliveries WHERE state IN ('pending','retry') AND next_at<=? "
        "ORDER BY created_at LIMIT 3",
        (now.timestamp(),),
    ).fetchall():
        db.execute(
            "UPDATE deliveries SET state='sending',attempts=attempts+1,target_hash=? WHERE event_key=?",
            (_hash(target), row["event_key"]),
        )
        db.commit()
        state, error, message_id, delay = "uncertain", None, None, 60 * 2 ** row["attempts"]
        try:
            response = sender(token, target, row["body"])
            if confirmed_receipt(response, target):
                state, message_id = "delivered", response["result"]["message_id"]
            elif response.get("ok") is False:
                code = response.get("error_code")
                state = "retry" if code == 429 else "failed"
                error = f"telegram_rejected_{code}"
                delay = max(
                    delay, float((response.get("parameters") or {}).get("retry_after") or 0)
                )
            else:
                error = "unconfirmed_provider_receipt"
        except urllib.error.HTTPError as exc:
            state = (
                "retry" if exc.code == 429 else "failed" if 400 <= exc.code < 500 else "uncertain"
            )
            error = f"telegram_http_{exc.code}"
            if exc.code == 429:
                try:
                    delay = max(
                        delay,
                        float(json.loads(exc.read()).get("parameters", {}).get("retry_after") or 0),
                    )
                except (ValueError, TypeError):
                    pass
        except Exception as exc:  # Do not persist token-bearing exception text.
            error = type(exc).__name__
        if state == "retry" and row["attempts"] + 1 >= MAX_ATTEMPTS:
            state = "failed"
        db.execute(
            "UPDATE deliveries SET state=?,error=?,message_id=?,next_at=? WHERE event_key=?",
            (state, error, message_id, now.timestamp() + delay, row["event_key"]),
        )
        db.commit()


def run_trade_delivery(settings=None, *, now=None, sender=None):
    active = settings or Settings.from_env()
    runtime = Path(active.runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(timezone.utc)
    with (runtime / ".qadam-trade-delivery.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "concurrent_run_skipped"}
        db = _connect(runtime / DB_ARTIFACT)
        try:
            errors = _collect_fills(db, runtime, now)
            _collect_health(db, runtime, now)
            db.commit()
            token, target = (
                secret_value("TELEGRAM_BOT_TOKEN", active),
                secret_value("TELEGRAM_GROUP_CHAT_ID", active),
            )
            enabled = (
                active.mode == "paper"
                and not active.live_capital_enabled
                and active.telegram_trade_group_notifications_enabled
                and not active.telegram_trade_group_notifications_dry_run
                and bool(token and target)
            )
            if enabled:
                _deliver(db, token, target, now, sender or _telegram_send)
            else:
                errors.append("trade_delivery_disabled_or_unconfigured")
            counts = dict(
                db.execute("SELECT state,COUNT(*) FROM deliveries GROUP BY state").fetchall()
            )
            unresolved = sum(
                counts.get(key, 0) for key in ("pending", "retry", "uncertain", "failed", "sending")
            )
            payload = {
                "generated_at": now.isoformat(),
                "status": "needs_attention" if errors or unresolved else "healthy",
                "delivery_counts": counts,
                "unresolved_count": unresolved,
                "errors": errors,
                "target_hash": _hash(target) if target else None,
                "delivery_is_read_confirmation": False,
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "live_capital_enabled": False,
            }
            write_json_atomic(runtime / STATUS_ARTIFACT, payload)
            return payload
        finally:
            db.close()


def trade_delivery_health(runtime, now=None):
    now = now or datetime.now(timezone.utc)
    payload = read_json(Path(runtime) / STATUS_ARTIFACT)
    observed = _time(payload.get("generated_at"))
    fresh = observed and 0 <= (now - observed).total_seconds() <= 180
    healthy = bool(fresh and payload.get("status") == "healthy")
    counts = payload.get("delivery_counts") or {}
    safe_refresh = not fresh and not any(
        counts.get(key) for key in ("uncertain", "failed", "sending")
    )
    return {
        "healthy": healthy,
        "safe_refresh_allowed": bool(safe_refresh),
        "reason": "Trade-fill reporting is current."
        if healthy
        else "Trade-fill reporting needs attention; delivery or monitor freshness is not confirmed.",
    }
