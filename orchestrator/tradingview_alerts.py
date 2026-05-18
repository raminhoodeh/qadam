"""TradingView alert intake contract.

D7 treats paid-account TradingView alerts as observed source events only. The
local contract proves validation, deduplication, Event Log writes, and cockpit
visibility before any public webhook or broker path exists.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

TRADINGVIEW_ALERT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TradingViewAlert:
    schema_version: int
    alert_id: str
    dedupe_key: str
    status: str
    source_type: str
    symbol: str
    timeframe: str
    setup_type: str
    direction: str
    trigger: str
    price: float | None
    indicator_state: dict[str, str]
    chart_context: str
    received_at: str
    observed_at: str
    execution_allowed: bool
    paper_order_allowed: bool
    trade_candidate_created: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, fallback: str = "unknown") -> str:
    text = str(value or fallback).strip()
    return text[:500]


def _safe_indicator_state(payload: dict[str, Any]) -> dict[str, str]:
    raw_state = payload.get("indicator_state", {})
    if not isinstance(raw_state, dict):
        return {}
    safe: dict[str, str] = {}
    for key, value in list(raw_state.items())[:12]:
        safe[_safe_text(key, "indicator")[:80]] = _safe_text(value, "unknown")[:160]
    return safe


def _dedupe_key(payload: dict[str, Any]) -> str:
    identity = {
        "symbol": _safe_text(payload.get("symbol")),
        "timeframe": _safe_text(payload.get("timeframe")),
        "setup_type": _safe_text(payload.get("setup_type")),
        "direction": _safe_text(payload.get("direction"), "watch"),
        "trigger": _safe_text(payload.get("trigger")),
        "price": payload.get("price"),
        "observed_at": _safe_text(payload.get("observed_at"), "no_observed_time"),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_tradingview_alert(alert: TradingViewAlert) -> None:
    if alert.schema_version != TRADINGVIEW_ALERT_SCHEMA_VERSION:
        raise ValueError("TradingView alert schema version mismatch")
    if alert.status != "observed_signal":
        raise ValueError("TradingView alerts can only enter as observed_signal")
    if alert.source_type != "tradingview_paid_alert":
        raise ValueError("TradingView alert source_type mismatch")
    for field_name in ("alert_id", "dedupe_key", "symbol", "timeframe", "setup_type", "trigger", "boundary"):
        if not str(getattr(alert, field_name)).strip():
            raise ValueError(f"TradingView alert missing required field: {field_name}")
    if alert.execution_allowed:
        raise ValueError("TradingView alerts cannot allow execution")
    if alert.paper_order_allowed:
        raise ValueError("TradingView alerts cannot allow paper orders")
    if alert.trade_candidate_created:
        raise ValueError("D7 TradingView alerts cannot create trade candidates")


def build_tradingview_alert_from_payload(
    payload: dict[str, Any],
    *,
    expected_receiver_key: str | None = None,
) -> TradingViewAlert:
    """Build a sanitized alert from a TradingView-style webhook payload.

    The receiver key is checked and discarded. It is never persisted.
    """

    if expected_receiver_key is not None and payload.get("qadam_receiver_key") != expected_receiver_key:
        raise ValueError("TradingView alert receiver authentication failed")

    dedupe_key = _dedupe_key(payload)
    observed_at = _safe_text(payload.get("observed_at"), _now())
    price_value = payload.get("price")
    price = None if price_value in {None, ""} else float(price_value)
    alert = TradingViewAlert(
        schema_version=TRADINGVIEW_ALERT_SCHEMA_VERSION,
        alert_id=_safe_text(payload.get("alert_id"), f"tv-{dedupe_key[:16]}")[:120],
        dedupe_key=dedupe_key,
        status="observed_signal",
        source_type="tradingview_paid_alert",
        symbol=_safe_text(payload.get("symbol")),
        timeframe=_safe_text(payload.get("timeframe")),
        setup_type=_safe_text(payload.get("setup_type")),
        direction=_safe_text(payload.get("direction"), "watch"),
        trigger=_safe_text(payload.get("trigger")),
        price=price,
        indicator_state=_safe_indicator_state(payload),
        chart_context=_safe_text(payload.get("chart_context"), "No chart context supplied."),
        received_at=_now(),
        observed_at=observed_at,
        execution_allowed=False,
        paper_order_allowed=False,
        trade_candidate_created=False,
        boundary=(
            "D7 observed TradingView alert only. It can enter the Event Log, "
            "but it cannot create a trade candidate, paper order, or broker action."
        ),
    )
    validate_tradingview_alert(alert)
    return alert


class TradingViewAlertStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "tradingview_alerts.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add_alert(self, alert: TradingViewAlert, *, log_event: bool = True) -> dict[str, Any]:
        validate_tradingview_alert(alert)
        existing = {record.dedupe_key for record in self.read_alerts()}
        if alert.dedupe_key in existing:
            return {
                "status": "duplicate_ignored",
                "alert_id": alert.alert_id,
                "dedupe_key": alert.dedupe_key,
                "created": False,
            }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(alert.to_dict(), sort_keys=True) + "\n")
        if log_event:
            EventLog(echo=False).write(
                event_type="tradingview_alert_observed",
                component="tradingview_alerts",
                payload={
                    "alert_id": alert.alert_id,
                    "symbol": alert.symbol,
                    "timeframe": alert.timeframe,
                    "setup_type": alert.setup_type,
                    "status": alert.status,
                    "execution_allowed": alert.execution_allowed,
                    "paper_order_allowed": alert.paper_order_allowed,
                    "trade_candidate_created": alert.trade_candidate_created,
                    "boundary": alert.boundary,
                },
            )
        return {
            "status": "created",
            "alert_id": alert.alert_id,
            "dedupe_key": alert.dedupe_key,
            "created": True,
        }

    def read_alerts(self, limit: int | None = None) -> tuple[TradingViewAlert, ...]:
        if not self.path.exists():
            return ()
        alerts: list[TradingViewAlert] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    alerts.append(TradingViewAlert(**json.loads(stripped)))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid TradingView alert line {line_number} in {self.path.name}") from exc
        if limit is not None:
            alerts = alerts[-limit:]
        for alert in alerts:
            validate_tradingview_alert(alert)
        return tuple(alerts)

    def health(self) -> dict[str, Any]:
        try:
            alerts = self.read_alerts()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {
                "status": "degraded",
                "schema_version": TRADINGVIEW_ALERT_SCHEMA_VERSION,
                "error": str(exc),
            }
        return {
            "status": "ok" if alerts else "not_initialized",
            "schema_version": TRADINGVIEW_ALERT_SCHEMA_VERSION,
            "alert_count": len(alerts),
            "latest_observed_at": alerts[-1].observed_at if alerts else None,
            "execution_allowed_count": sum(1 for alert in alerts if alert.execution_allowed),
            "paper_order_allowed_count": sum(1 for alert in alerts if alert.paper_order_allowed),
            "trade_candidate_created_count": sum(1 for alert in alerts if alert.trade_candidate_created),
            "boundary": "TradingView alerts are observed signals only. D7 has no execution route.",
        }


def d7_sample_tradingview_payload() -> dict[str, Any]:
    return {
        "alert_id": "d7-sample-tradingview-crude-volatility",
        "symbol": "TVC:USOIL",
        "timeframe": "1D",
        "setup_type": "volatility_compression_watch",
        "direction": "watch_long_volatility",
        "trigger": "Daily close near prior-week range with crude volatility compression.",
        "price": 82.5,
        "indicator_state": {
            "rsi": "recovering",
            "macd": "pending_cross",
            "volume": "needs_confirmation",
            "akber_stage": "technical_confirmation_only",
        },
        "chart_context": (
            "D7 local fixture for TradingView paid-account alert ingestion. "
            "It is an observed chart event, not a trade candidate."
        ),
        "observed_at": "2026-05-16T00:00:00+00:00",
    }


def ensure_d7_tradingview_alert_source(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TradingViewAlertStore(settings=settings)
    alert = build_tradingview_alert_from_payload(d7_sample_tradingview_payload())
    first_result = store.add_alert(alert)
    duplicate_result = store.add_alert(alert)
    health = store.health()
    return {
        "status": "ok",
        "created": bool(first_result["created"]),
        "duplicate_protection": duplicate_result["status"],
        "alert_count": health["alert_count"],
        "execution_allowed_count": health["execution_allowed_count"],
        "paper_order_allowed_count": health["paper_order_allowed_count"],
        "trade_candidate_created_count": health["trade_candidate_created_count"],
        "boundary": health["boundary"],
    }


def tradingview_alert_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TradingViewAlertStore(settings=settings)
    health = store.health()
    return {
        "status": health["status"],
        "schema_version": TRADINGVIEW_ALERT_SCHEMA_VERSION,
        "alert_count": health.get("alert_count", 0),
        "latest_observed_at": health.get("latest_observed_at"),
        "execution_allowed_count": health.get("execution_allowed_count", 0),
        "paper_order_allowed_count": health.get("paper_order_allowed_count", 0),
        "trade_candidate_created_count": health.get("trade_candidate_created_count", 0),
        "receiver_status": "local_contract_only",
        "duplicate_protection": "dedupe_key_sha256",
        "boundary": health.get("boundary", "TradingView alert store is not initialized."),
    }
