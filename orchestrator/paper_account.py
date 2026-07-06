"""Read-only paper account mirror for the first-release cockpit.

D6 creates a local account mirror contract before any broker integration. It is
the place where balance, P&L, drawdown, positions, closed trades, and maturity
progress appear once read-only broker data is connected.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.release_contract import (
    PAPER_ACCOUNT_CAPITAL_POLICY,
    PAPER_ACCOUNT_SCOPE,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
)
from orchestrator.secrets import secret_status, secret_value

PAPER_ACCOUNT_SCHEMA_VERSION = 1
MATURITY_CLOSED_TRADE_TARGET = PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
POSTMORTEM_PENDING_MARKER_STATUS = "postmortem_pending_marker"
POSTMORTEM_STATUSES = frozenset(
    {
        POSTMORTEM_PENDING_MARKER_STATUS,
        "postmortem_due",
        "postmortem_complete",
    }
)
ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_READONLY_PATHS = frozenset(
    {
        "/account",
        "/positions",
        "/orders",
        "/account/portfolio/history",
        "/clock",
    }
)
OPEN_ORDER_STATUSES = frozenset({"new", "accepted", "pending_new", "partially_filled"})
PAPER_TRIAL_RESET_SCHEMA_VERSION = 1
PAPER_TRIAL_RESET_RUNTIME_ARTIFACT = "paper_trial_reset_epoch.json"
PAPER_TRIAL_RESET_HISTORY = "paper_trial_reset_epoch_history.jsonl"


@dataclass(frozen=True)
class PaperAccountSnapshot:
    schema_version: int
    snapshot_id: str
    account_scope: str
    mode: str
    broker: str
    connection_status: str
    starting_balance_gbp: float
    current_balance_gbp: float
    cash_gbp: float
    equity_gbp: float
    peak_equity_gbp: float
    realized_pnl_gbp: float
    unrealized_pnl_gbp: float
    drawdown_pct: float
    max_drawdown_pct: float
    live_capital_enabled: bool
    write_authority: bool
    open_position_count: int
    closed_trade_count: int
    postmortem_due_count: int
    postmortem_complete_count: int
    maturity_closed_trade_target: int
    maturity_closed_trade_count: int
    timeline_status: str
    observed_at: str
    boundary: str
    account_currency: str = "GBP"
    display_currency: str = "GBP"
    fx_to_gbp_rate: float = 1.0
    source_current_balance: float | None = None
    source_cash: float | None = None
    source_equity: float | None = None
    broker_portfolio_history_latest_equity: float | None = None
    broker_portfolio_history_latest_profit_loss: float | None = None
    broker_reconciliation_status: str = "not_available"
    broker_reconciliation_delta: float | None = None
    broker_reconciliation_tolerance: float = 1.0
    broker_reconciliation_detail: str = "No broker portfolio history reconciliation was run."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperPosition:
    schema_version: int
    position_id: str
    status: str
    instrument: str
    direction: str
    quantity: float
    entry_price: float | None
    current_price: float | None
    unrealized_pnl_gbp: float
    risk_size_gbp: float
    opened_at: str | None
    invalidation: str
    source_intent_id: str | None
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClosedPaperTrade:
    schema_version: int
    trade_id: str
    instrument: str
    direction: str
    entry_price: float | None
    exit_price: float | None
    realized_pnl_gbp: float
    r_multiple: float | None
    close_reason: str
    opened_at: str | None
    closed_at: str | None
    postmortem_status: str
    source_intent_id: str | None
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperOrder:
    schema_version: int
    order_id: str
    status: str
    instrument: str
    direction: str
    quantity: float | None
    notional_gbp: float | None
    order_type: str | None
    limit_price: float | None
    submitted_at: str | None
    filled_at: str | None
    filled_quantity: float | None
    filled_avg_price: float | None
    execution_allowed: bool
    paper_order_allowed: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def paper_trial_reset_epoch_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    runtime = Path((settings or Settings.from_env()).runtime_dir)
    return (
        runtime / PAPER_TRIAL_RESET_RUNTIME_ARTIFACT,
        runtime / PAPER_TRIAL_RESET_HISTORY,
    )


def read_paper_trial_reset_epoch(settings: Settings | None = None) -> dict[str, Any]:
    path, _ = paper_trial_reset_epoch_paths(settings)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_paper_trial_reset_epoch(
    epoch: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    path, history_path = paper_trial_reset_epoch_paths(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = dict(epoch)
    output["schema_version"] = PAPER_TRIAL_RESET_SCHEMA_VERSION
    output["artifact_type"] = "paper_trial_reset_epoch"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(output, sort_keys=True) + "\n")
    return path, history_path


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return _float(value)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_id(prefix: str, value: Any) -> str:
    text = str(value or "").strip()
    return text if text else f"{prefix}:{uuid4()}"


def validate_snapshot(snapshot: PaperAccountSnapshot) -> None:
    if snapshot.schema_version != PAPER_ACCOUNT_SCHEMA_VERSION:
        raise ValueError("paper account snapshot schema version mismatch")
    if snapshot.mode != "paper":
        raise ValueError("paper account mirror can only export paper mode")
    if snapshot.live_capital_enabled:
        raise ValueError("paper account mirror cannot enable live capital")
    if snapshot.write_authority:
        raise ValueError("paper account mirror cannot expose write authority")
    if snapshot.starting_balance_gbp < 0 or snapshot.current_balance_gbp < 0:
        raise ValueError("paper account balances cannot be negative")
    if snapshot.drawdown_pct < 0 or snapshot.max_drawdown_pct < 0:
        raise ValueError("paper account drawdown cannot be negative")
    if snapshot.maturity_closed_trade_target != MATURITY_CLOSED_TRADE_TARGET:
        raise ValueError("paper account maturity target must stay at 100 closed trades")


def validate_position(position: PaperPosition) -> None:
    if position.schema_version != PAPER_ACCOUNT_SCHEMA_VERSION:
        raise ValueError("paper position schema version mismatch")
    if position.status not in {"open_position", "exit_planned"}:
        raise ValueError(f"invalid paper position status: {position.status}")
    if position.quantity < 0:
        raise ValueError("paper position quantity cannot be negative")


def validate_closed_trade(trade: ClosedPaperTrade) -> None:
    if trade.schema_version != PAPER_ACCOUNT_SCHEMA_VERSION:
        raise ValueError("closed paper trade schema version mismatch")
    if trade.postmortem_status not in POSTMORTEM_STATUSES:
        raise ValueError(f"invalid postmortem status: {trade.postmortem_status}")


def validate_order(order: PaperOrder) -> None:
    if order.schema_version != PAPER_ACCOUNT_SCHEMA_VERSION:
        raise ValueError("paper order schema version mismatch")
    if order.execution_allowed:
        raise ValueError("paper order mirror cannot expose execution authority")
    if order.paper_order_allowed:
        raise ValueError("paper order mirror cannot expose paper order authority")


class PaperAccountMirrorStore:
    def __init__(self, root: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        base = Path(root or self.settings.runtime_dir)
        self.snapshots_path = base / "paper_account_snapshots.jsonl"
        self.positions_path = base / "paper_positions.jsonl"
        self.closed_trades_path = base / "paper_closed_trades.jsonl"
        self.orders_path = base / "paper_orders.jsonl"
        base.mkdir(parents=True, exist_ok=True)

    def write_snapshot(self, snapshot: PaperAccountSnapshot, *, log_event: bool = True) -> PaperAccountSnapshot:
        validate_snapshot(snapshot)
        with self.snapshots_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot.to_dict(), sort_keys=True) + "\n")
        if log_event:
            EventLog(echo=False).write(
                event_type="paper_account_snapshot_recorded",
                component="paper_account",
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "mode": snapshot.mode,
                    "connection_status": snapshot.connection_status,
                    "current_balance_gbp": snapshot.current_balance_gbp,
                    "drawdown_pct": snapshot.drawdown_pct,
                    "live_capital_enabled": snapshot.live_capital_enabled,
                    "write_authority": snapshot.write_authority,
                },
            )
        return snapshot

    def read_snapshots(self, limit: int | None = None) -> tuple[PaperAccountSnapshot, ...]:
        snapshots = self._read_jsonl(self.snapshots_path, PaperAccountSnapshot)
        for snapshot in snapshots:
            validate_snapshot(snapshot)
        if limit is not None:
            snapshots = snapshots[-limit:]
        return tuple(snapshots)

    def read_positions(self) -> tuple[PaperPosition, ...]:
        positions = self._read_jsonl(self.positions_path, PaperPosition)
        for position in positions:
            validate_position(position)
        return tuple(positions)

    def read_closed_trades(self) -> tuple[ClosedPaperTrade, ...]:
        trades = self._read_jsonl(self.closed_trades_path, ClosedPaperTrade)
        for trade in trades:
            validate_closed_trade(trade)
        return tuple(trades)

    def read_orders(self) -> tuple[PaperOrder, ...]:
        orders = self._read_jsonl(self.orders_path, PaperOrder)
        for order in orders:
            validate_order(order)
        return tuple(orders)

    def replace_positions(self, positions: tuple[PaperPosition, ...]) -> None:
        for position in positions:
            validate_position(position)
        self._replace_jsonl(self.positions_path, tuple(position.to_dict() for position in positions))

    def replace_closed_trades(self, trades: tuple[ClosedPaperTrade, ...]) -> None:
        for trade in trades:
            validate_closed_trade(trade)
        self._replace_jsonl(self.closed_trades_path, tuple(trade.to_dict() for trade in trades))

    def replace_orders(self, orders: tuple[PaperOrder, ...]) -> None:
        for order in orders:
            validate_order(order)
        self._replace_jsonl(self.orders_path, tuple(order.to_dict() for order in orders))

    def latest_snapshot(self) -> PaperAccountSnapshot | None:
        snapshots = self.read_snapshots()
        return snapshots[-1] if snapshots else None

    def health(self) -> dict[str, Any]:
        try:
            snapshots = self.read_snapshots()
            positions = self.read_positions()
            closed_trades = self.read_closed_trades()
            orders = self.read_orders()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {
                "status": "degraded",
                "schema_version": PAPER_ACCOUNT_SCHEMA_VERSION,
                "error": str(exc),
            }
        return {
            "status": "ok" if snapshots else "not_initialized",
            "schema_version": PAPER_ACCOUNT_SCHEMA_VERSION,
            "snapshot_count": len(snapshots),
            "open_position_count": len(positions),
            "closed_trade_count": len(closed_trades),
            "order_count": len(orders),
            "open_order_count": sum(1 for order in orders if order.status in OPEN_ORDER_STATUSES),
            "postmortem_due_count": sum(
                1 for trade in closed_trades if trade.postmortem_status == "postmortem_due"
            ),
            "postmortem_complete_count": sum(
                1 for trade in closed_trades if trade.postmortem_status == "postmortem_complete"
            ),
            "latest_observed_at": snapshots[-1].observed_at if snapshots else None,
            "boundary": "Read-only local paper account mirror. No broker write path exists in D6.",
        }

    def _read_jsonl(self, path: Path, record_type: type[Any]) -> list[Any]:
        if not path.exists():
            return []
        records: list[Any] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(record_type(**json.loads(stripped)))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid paper account line {line_number} in {path.name}") from exc
        return records

    def _replace_jsonl(self, path: Path, records: tuple[dict[str, Any], ...]) -> None:
        tmp_path = path.with_name(f".{path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        os.replace(tmp_path, path)


def initial_paper_account_snapshot(settings: Settings | None = None) -> PaperAccountSnapshot:
    settings = settings or Settings.from_env()
    now = _now()
    starting_balance = float(settings.trial_balance_gbp)
    return PaperAccountSnapshot(
        schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
        snapshot_id=str(uuid4()),
        account_scope=PAPER_ACCOUNT_SCOPE,
        mode="paper",
        broker="local_mirror_pending_alpaca_readonly",
        connection_status="local_mirror_not_broker_connected",
        starting_balance_gbp=starting_balance,
        current_balance_gbp=starting_balance,
        cash_gbp=starting_balance,
        equity_gbp=starting_balance,
        peak_equity_gbp=starting_balance,
        realized_pnl_gbp=0,
        unrealized_pnl_gbp=0,
        drawdown_pct=0,
        max_drawdown_pct=0,
        live_capital_enabled=False,
        write_authority=False,
        open_position_count=0,
        closed_trade_count=0,
        postmortem_due_count=0,
        postmortem_complete_count=0,
        maturity_closed_trade_target=MATURITY_CLOSED_TRADE_TARGET,
        maturity_closed_trade_count=0,
        timeline_status="initialized_no_trades",
        observed_at=now,
        boundary="D6 local mirror only. No broker connection, no orders, no live capital.",
    )


def ensure_d6_paper_account_mirror(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = PaperAccountMirrorStore(settings=settings)
    snapshots = store.read_snapshots()
    created = False
    if not snapshots:
        store.write_snapshot(initial_paper_account_snapshot(settings))
        created = True
    health = store.health()
    latest = store.latest_snapshot()
    return {
        "status": "ok",
        "created_snapshot": created,
        "snapshot_count": health["snapshot_count"],
        "open_position_count": health["open_position_count"],
        "closed_trade_count": health["closed_trade_count"],
        "order_count": health.get("order_count", 0),
        "current_balance_gbp": latest.current_balance_gbp if latest else None,
        "realized_pnl_gbp": latest.realized_pnl_gbp if latest else None,
        "unrealized_pnl_gbp": latest.unrealized_pnl_gbp if latest else None,
        "drawdown_pct": latest.drawdown_pct if latest else None,
        "live_capital_enabled": latest.live_capital_enabled if latest else None,
        "write_authority": latest.write_authority if latest else None,
        "boundary": health["boundary"],
    }


def paper_account_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = PaperAccountMirrorStore(settings=settings)
    health = store.health()
    latest = store.latest_snapshot()
    return {
        "status": health["status"],
        "schema_version": PAPER_ACCOUNT_SCHEMA_VERSION,
        "snapshot_count": health.get("snapshot_count", 0),
        "open_position_count": health.get("open_position_count", 0),
        "closed_trade_count": health.get("closed_trade_count", 0),
        "order_count": health.get("order_count", 0),
        "open_order_count": health.get("open_order_count", 0),
        "postmortem_due_count": health.get("postmortem_due_count", 0),
        "postmortem_complete_count": health.get("postmortem_complete_count", 0),
        "current_balance_gbp": latest.current_balance_gbp if latest else settings.trial_balance_gbp,
        "account_currency": latest.account_currency if latest else "GBP",
        "display_currency": latest.display_currency if latest else "GBP",
        "broker_reconciliation_status": latest.broker_reconciliation_status if latest else "not_available",
        "drawdown_pct": latest.drawdown_pct if latest else 0,
        "live_capital_enabled": latest.live_capital_enabled if latest else False,
        "write_authority": latest.write_authority if latest else False,
        "boundary": health.get("boundary", "No paper account mirror snapshot is available."),
    }


def paper_account_shadow_context(settings: Settings | None = None) -> dict[str, Any]:
    """Return a public-safe account context for shadow intelligence only.

    This deliberately excludes broker IDs and local file locations. It is safe
    to feed into Research Analyst and Strategy Lead prompts because it carries
    state, not authority.
    """

    settings = settings or Settings.from_env()
    store = PaperAccountMirrorStore(settings=settings)
    health = store.health()
    latest = store.latest_snapshot()
    positions = store.read_positions()
    orders = store.read_orders()
    closed_trades = store.read_closed_trades()
    current_balance = latest.current_balance_gbp if latest else float(settings.trial_balance_gbp)
    drawdown = latest.drawdown_pct if latest else 0.0
    open_orders = tuple(order for order in orders if order.status in OPEN_ORDER_STATUSES)
    return {
        "status": health.get("status", "not_initialized"),
        "schema_version": PAPER_ACCOUNT_SCHEMA_VERSION,
        "account_scope": latest.account_scope if latest else PAPER_ACCOUNT_SCOPE,
        "mode": latest.mode if latest else "paper",
        "broker": latest.broker if latest else "local_mirror_pending_alpaca_readonly",
        "connection_status": latest.connection_status if latest else "local_mirror_not_broker_connected",
        "account_currency": latest.account_currency if latest else "GBP",
        "display_currency": latest.display_currency if latest else "GBP",
        "fx_to_gbp_rate": latest.fx_to_gbp_rate if latest else 1.0,
        "trial_allocation_gbp": float(settings.trial_balance_gbp),
        "current_balance_gbp": current_balance,
        "cash_gbp": latest.cash_gbp if latest else float(settings.trial_balance_gbp),
        "equity_gbp": latest.equity_gbp if latest else current_balance,
        "realized_pnl_gbp": latest.realized_pnl_gbp if latest else 0.0,
        "unrealized_pnl_gbp": latest.unrealized_pnl_gbp if latest else 0.0,
        "drawdown_pct": drawdown,
        "open_position_count": len(positions),
        "order_count": len(orders),
        "open_order_count": len(open_orders),
        "closed_trade_count": len(closed_trades),
        "maturity_closed_trade_target": MATURITY_CLOSED_TRADE_TARGET,
        "maturity_closed_trade_count": latest.maturity_closed_trade_count if latest else len(closed_trades),
        "timeline_status": latest.timeline_status if latest else "initialized_no_trades",
        "observed_at": latest.observed_at if latest else None,
        "broker_reconciliation_status": latest.broker_reconciliation_status if latest else "not_available",
        "broker_reconciliation_delta": latest.broker_reconciliation_delta if latest else None,
        "broker_reconciliation_detail": latest.broker_reconciliation_detail if latest else "No mirror snapshot yet.",
        "position_summaries": [
            {
                "instrument": position.instrument,
                "direction": position.direction,
                "quantity": position.quantity,
                "unrealized_pnl_gbp": position.unrealized_pnl_gbp,
                "risk_size_gbp": position.risk_size_gbp,
                "status": position.status,
            }
            for position in positions[:5]
        ],
        "order_summaries": [
            {
                "instrument": order.instrument,
                "direction": order.direction,
                "status": order.status,
                "order_type": order.order_type,
                "quantity": order.quantity,
                "notional_gbp": order.notional_gbp,
                "filled_quantity": order.filled_quantity,
            }
            for order in orders[:5]
        ],
        "execution_allowed": False,
        "paper_order_allowed": False,
        "write_authority": False,
        "live_capital_enabled": False,
        "capital_policy": PAPER_ACCOUNT_CAPITAL_POLICY,
        "boundary": (
            "Paper account context is read-only state for shadow intelligence. It cannot "
            "approve, create, cancel, replace, close, resize, or fund orders."
        ),
    }


def alpaca_paper_mirror_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    key_ready = secret_status("ALPACA_API_KEY", settings).configured
    secret_ready = secret_status("ALPACA_API_SECRET", settings).configured
    paper_flag = (secret_value("ALPACA_PAPER", settings) or "true").strip().lower()
    return {
        "status": "configured" if key_ready and secret_ready else "missing_credentials",
        "api_key_configured": key_ready,
        "api_secret_configured": secret_ready,
        "paper_mode": paper_flag != "false",
        "base_url": secret_value("ALPACA_ENDPOINT", settings)
        or secret_value("ALPACA_BASE_URL", settings)
        or ALPACA_PAPER_BASE_URL,
        "readonly_paths": sorted(ALPACA_READONLY_PATHS),
        "write_authority": False,
        "boundary": "Alpaca paper mirror is GET-only. No broker-write route exists.",
    }


class AlpacaReadOnlyPaperMirror:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        store: PaperAccountMirrorStore | None = None,
        event_log: EventLog | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.store = store or PaperAccountMirrorStore(settings=self.settings)
        self.event_log = event_log or EventLog(echo=False)
        self.base_url = (
            secret_value("ALPACA_ENDPOINT", self.settings)
            or secret_value("ALPACA_BASE_URL", self.settings)
            or ALPACA_PAPER_BASE_URL
        ).rstrip("/")
        self.fx_to_gbp = _float(os.getenv("ALPACA_TO_GBP_RATE"), 1.0)

    def _headers(self) -> dict[str, str]:
        api_key = secret_value("ALPACA_API_KEY", self.settings)
        api_secret = secret_value("ALPACA_API_SECRET", self.settings)
        if not api_key or not api_secret:
            raise PermissionError("missing Alpaca paper credentials")
        return {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "User-Agent": "Qadam/0.1 alpaca-readonly-paper-mirror",
            "Accept": "application/json",
        }

    def _get(self, path: str, *, params: dict[str, Any] | None = None, timeout_seconds: float = 12.0) -> Any:
        if path not in ALPACA_READONLY_PATHS:
            raise PermissionError(f"Alpaca mirror refuses non-readonly path: {path}")
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is required for Alpaca paper mirror") from exc
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(f"{self.base_url}{path}", headers=self._headers(), params=params or {})
            response.raise_for_status()
            return response.json()

    def fetch(self) -> dict[str, Any]:
        account = self._get("/account")
        positions = self._get("/positions")
        orders = self._get("/orders", params={"status": "all", "limit": 100, "direction": "desc", "nested": "true"})
        clock = self._get("/clock")
        history = self._get(
            "/account/portfolio/history",
            params={"period": "1M", "timeframe": "1D", "intraday_reporting": "market_hours"},
        )
        return {
            "account": account if isinstance(account, dict) else {},
            "positions": positions if isinstance(positions, list) else [],
            "orders": orders if isinstance(orders, list) else [],
            "clock": clock if isinstance(clock, dict) else {},
            "portfolio_history": history if isinstance(history, dict) else {},
        }

    def _order_timestamp(self, item: dict[str, Any]) -> datetime | None:
        for key in ("submitted_at", "filled_at", "created_at", "updated_at"):
            parsed = _parse_timestamp(item.get(key))
            if parsed is not None:
                return parsed
        return None

    def _epoch_order_payloads(
        self,
        orders_payload: list[Any],
        reset_epoch: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        if not reset_epoch:
            return [item for item in orders_payload if isinstance(item, dict)], 0
        reset_at = _parse_timestamp(reset_epoch.get("reset_at"))
        if reset_at is None:
            return [item for item in orders_payload if isinstance(item, dict)], 0
        kept: list[dict[str, Any]] = []
        excluded_count = 0
        for item in orders_payload:
            if not isinstance(item, dict):
                continue
            timestamp = self._order_timestamp(item)
            if timestamp is not None and timestamp >= reset_at:
                kept.append(item)
            else:
                excluded_count += 1
        return kept, excluded_count

    def _epoch_position_payloads(
        self,
        positions_payload: list[Any],
        reset_epoch: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        items = [item for item in positions_payload if isinstance(item, dict)]
        if not reset_epoch:
            return items, 0
        excluded_symbols = {
            str(symbol).upper()
            for symbol in reset_epoch.get("broker_open_position_symbols_at_reset", [])
            if str(symbol).strip()
        }
        if not excluded_symbols:
            return items, 0
        kept: list[dict[str, Any]] = []
        excluded_count = 0
        for item in items:
            symbol = str(item.get("symbol") or "").upper()
            if symbol and symbol in excluded_symbols:
                excluded_count += 1
            else:
                kept.append(item)
        return kept, excluded_count

    def sync(self) -> dict[str, Any]:
        payload = self.fetch()
        account = payload["account"]
        raw_positions_payload = payload["positions"]
        raw_orders_payload = payload["orders"]
        clock = payload["clock"]
        history = payload["portfolio_history"]
        reset_epoch = read_paper_trial_reset_epoch(self.settings)
        positions_payload, pre_reset_position_count = self._epoch_position_payloads(
            raw_positions_payload,
            reset_epoch,
        )
        orders_payload, pre_reset_order_count = self._epoch_order_payloads(
            raw_orders_payload,
            reset_epoch,
        )

        positions = tuple(self._position_from_alpaca(item) for item in positions_payload if isinstance(item, dict))
        orders = tuple(self._order_from_alpaca(item) for item in orders_payload if isinstance(item, dict))
        closed_trades = tuple(
            self._closed_trade_from_order(item)
            for item in orders_payload
            if isinstance(item, dict) and item.get("status") == "filled"
        )
        latest_profit_loss = self._latest_profit_loss(history)
        latest_history_equity = self._latest_history_money(history, "equity")
        unrealized = round(sum(position.unrealized_pnl_gbp for position in positions), 2)
        account_currency = self._account_currency(account)
        display_currency = self._display_currency(account_currency)
        equity = self._money(account.get("equity") or account.get("portfolio_value"))
        cash = self._money(account.get("cash"))
        last_equity = self._money(account.get("last_equity") or equity)
        starting_balance = float(reset_epoch.get("trial_balance_gbp") or self.settings.trial_balance_gbp)
        broker_equity_baseline = _optional_float(reset_epoch.get("broker_equity_baseline_gbp"))
        broker_cash_baseline = _optional_float(reset_epoch.get("broker_cash_baseline_gbp"))
        if broker_equity_baseline is not None:
            current_balance = round(starting_balance + (equity - broker_equity_baseline), 2)
        else:
            current_balance = equity
        if broker_cash_baseline is not None:
            effective_cash = round(starting_balance + (cash - broker_cash_baseline), 2)
        else:
            effective_cash = cash
        peak_equity = max(current_balance, starting_balance)
        drawdown_pct = round(max(0.0, (peak_equity - current_balance) / peak_equity * 100), 3) if peak_equity else 0.0
        realized = (
            round(current_balance - starting_balance - unrealized, 2)
            if broker_equity_baseline is not None
            else round(latest_profit_loss - unrealized, 2)
            if latest_profit_loss is not None
            else 0.0
        )
        reconciliation = self._reconcile_account_to_history(equity, latest_history_equity)
        snapshot = PaperAccountSnapshot(
            schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
            snapshot_id=str(uuid4()),
            account_scope=PAPER_ACCOUNT_SCOPE,
            mode="paper",
            broker="alpaca_paper_readonly",
            connection_status="alpaca_paper_readonly_connected",
            starting_balance_gbp=starting_balance,
            current_balance_gbp=current_balance,
            cash_gbp=effective_cash,
            equity_gbp=current_balance,
            peak_equity_gbp=round(peak_equity, 2),
            realized_pnl_gbp=realized,
            unrealized_pnl_gbp=unrealized,
            drawdown_pct=drawdown_pct,
            max_drawdown_pct=drawdown_pct,
            live_capital_enabled=False,
            write_authority=False,
            open_position_count=len(positions),
            closed_trade_count=len(closed_trades),
            postmortem_due_count=len(closed_trades),
            postmortem_complete_count=0,
            maturity_closed_trade_target=MATURITY_CLOSED_TRADE_TARGET,
            maturity_closed_trade_count=len(closed_trades),
            timeline_status=(
                "alpaca_paper_readonly_epoch_rebased"
                if reset_epoch
                else "alpaca_paper_readonly_mirrored"
            ),
            observed_at=_now(),
            boundary=(
                "Alpaca paper mirror is read-only. When a Qadam paper-trial reset "
                "epoch exists, pre-reset broker orders are excluded from the active "
                "trial view and account value is rebased to the reset balance. No "
                "broker write path, no live capital, no order placement."
            ),
            account_currency=account_currency,
            display_currency=display_currency,
            fx_to_gbp_rate=self.fx_to_gbp,
            source_current_balance=_optional_float(account.get("equity") or account.get("portfolio_value")),
            source_cash=_optional_float(account.get("cash")),
            source_equity=_optional_float(account.get("equity") or account.get("portfolio_value")),
            broker_portfolio_history_latest_equity=latest_history_equity,
            broker_portfolio_history_latest_profit_loss=latest_profit_loss,
            broker_reconciliation_status=reconciliation["status"],
            broker_reconciliation_delta=reconciliation["delta"],
            broker_reconciliation_tolerance=reconciliation["tolerance"],
            broker_reconciliation_detail=reconciliation["detail"],
        )
        self.store.replace_positions(positions)
        self.store.replace_orders(orders)
        self.store.replace_closed_trades(closed_trades)
        self.store.write_snapshot(snapshot)
        self.event_log.write(
            "alpaca_paper_account_mirror_synced",
            "paper_account",
            {
                "snapshot_id": snapshot.snapshot_id,
                "connection_status": snapshot.connection_status,
                "open_position_count": len(positions),
                "order_count": len(orders),
                "closed_trade_count": len(closed_trades),
                "write_authority": snapshot.write_authority,
                "live_capital_enabled": snapshot.live_capital_enabled,
                "execution_allowed": False,
                "account_currency": snapshot.account_currency,
                "display_currency": snapshot.display_currency,
                "broker_reconciliation_status": snapshot.broker_reconciliation_status,
            },
        )
        report = {
            "status": "ok",
            "schema_version": PAPER_ACCOUNT_SCHEMA_VERSION,
            "snapshot": snapshot.to_dict(),
            "position_count": len(positions),
            "order_count": len(orders),
            "closed_trade_count": len(closed_trades),
            "write_authority": False,
            "live_capital_enabled": False,
            "readonly_paths": sorted(ALPACA_READONLY_PATHS),
            "account_currency": snapshot.account_currency,
            "display_currency": snapshot.display_currency,
            "broker_reconciliation_status": snapshot.broker_reconciliation_status,
            "broker_reconciliation_delta": snapshot.broker_reconciliation_delta,
            "market_clock": self._sanitize_clock(clock),
            "reset_epoch": reset_epoch,
            "pre_reset_order_count": pre_reset_order_count,
            "pre_reset_position_count": pre_reset_position_count,
            "boundary": snapshot.boundary,
        }
        self._write_report(report)
        return report

    def _sanitize_clock(self, clock: dict[str, Any]) -> dict[str, Any]:
        if not clock:
            return {
                "status": "unavailable",
                "is_open": None,
                "next_open": None,
                "next_close": None,
                "timestamp": None,
                "boundary": "Read-only Alpaca clock unavailable; no execution authority is granted.",
            }
        is_open = clock.get("is_open")
        return {
            "status": "open" if is_open is True else "closed" if is_open is False else "unknown",
            "is_open": is_open if isinstance(is_open, bool) else None,
            "next_open": clock.get("next_open"),
            "next_close": clock.get("next_close"),
            "timestamp": clock.get("timestamp"),
            "boundary": "Read-only Alpaca market clock. It cannot place, cancel, replace, or close orders.",
        }

    def _money(self, value: Any) -> float:
        return round(_float(value) * self.fx_to_gbp, 2)

    def _account_currency(self, account: dict[str, Any]) -> str:
        return str(account.get("currency") or os.getenv("ALPACA_ACCOUNT_CURRENCY") or "USD").upper()

    def _display_currency(self, account_currency: str) -> str:
        if account_currency == "GBP" or self.fx_to_gbp != 1.0:
            return "GBP"
        return account_currency or "USD"

    def _position_from_alpaca(self, item: dict[str, Any]) -> PaperPosition:
        qty = _float(item.get("qty"))
        return PaperPosition(
            schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
            position_id=_safe_id("alpaca_position", item.get("asset_id") or item.get("symbol")),
            status="open_position",
            instrument=str(item.get("symbol") or "unknown"),
            direction="long" if qty >= 0 else "short",
            quantity=abs(qty),
            entry_price=_optional_float(item.get("avg_entry_price")),
            current_price=_optional_float(item.get("current_price")),
            unrealized_pnl_gbp=self._money(item.get("unrealized_pl")),
            risk_size_gbp=self._money(item.get("market_value")),
            opened_at=None,
            invalidation="Read-only broker mirror; invalidation belongs to a future approved trade intent.",
            source_intent_id=None,
            boundary="Mirrored Alpaca paper position only. Qadam cannot modify or close it.",
        )

    def _order_from_alpaca(self, item: dict[str, Any]) -> PaperOrder:
        return PaperOrder(
            schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
            order_id=_safe_id("alpaca_order", item.get("id") or item.get("client_order_id")),
            status=str(item.get("status") or "unknown"),
            instrument=str(item.get("symbol") or "unknown"),
            direction=str(item.get("side") or "unknown"),
            quantity=_optional_float(item.get("qty")),
            notional_gbp=self._money(item.get("notional")) if item.get("notional") is not None else None,
            order_type=item.get("type"),
            limit_price=_optional_float(item.get("limit_price")),
            submitted_at=item.get("submitted_at"),
            filled_at=item.get("filled_at"),
            filled_quantity=_optional_float(item.get("filled_qty")),
            filled_avg_price=_optional_float(item.get("filled_avg_price")),
            execution_allowed=False,
            paper_order_allowed=False,
            boundary="Mirrored Alpaca paper order only. No order create, cancel, replace, or close route exists.",
        )

    def _closed_trade_from_order(self, item: dict[str, Any]) -> ClosedPaperTrade:
        return ClosedPaperTrade(
            schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
            trade_id=_safe_id("alpaca_filled_order", item.get("id") or item.get("client_order_id")),
            instrument=str(item.get("symbol") or "unknown"),
            direction=str(item.get("side") or "unknown"),
            entry_price=_optional_float(item.get("filled_avg_price")),
            exit_price=None,
            realized_pnl_gbp=0.0,
            r_multiple=None,
            close_reason="alpaca_filled_order_mirrored",
            opened_at=item.get("submitted_at"),
            closed_at=item.get("filled_at"),
            postmortem_status="postmortem_due",
            source_intent_id=None,
            boundary="Filled Alpaca paper order mirrored for postmortem only. Qadam did not place this order.",
        )

    def _latest_profit_loss(self, history: dict[str, Any]) -> float | None:
        return self._latest_history_money(history, "profit_loss")

    def _latest_history_money(self, history: dict[str, Any], key: str) -> float | None:
        values = history.get(key)
        if not isinstance(values, list) or not values:
            return None
        for value in reversed(values):
            if value is not None and value != "":
                return self._money(value)
        return None

    def _reconcile_account_to_history(self, account_equity: float, history_equity: float | None) -> dict[str, Any]:
        tolerance = max(1.0, abs(account_equity) * 0.0025)
        if history_equity is None:
            return {
                "status": "history_unavailable",
                "delta": None,
                "tolerance": round(tolerance, 2),
                "detail": "Alpaca account equity is mirrored, but portfolio history did not return a comparable latest equity point.",
            }
        delta = round(account_equity - history_equity, 2)
        if abs(delta) <= tolerance:
            return {
                "status": "ok",
                "delta": delta,
                "tolerance": round(tolerance, 2),
                "detail": "Alpaca account equity reconciles with the latest portfolio history point inside tolerance.",
            }
        return {
            "status": "drift",
            "delta": delta,
            "tolerance": round(tolerance, 2),
            "detail": "Alpaca account equity and latest portfolio history differ beyond tolerance; use the live account equity as source of truth and treat the chart as lagging.",
        }

    def _write_report(self, report: dict[str, Any]) -> Path:
        output_path = Path(self.settings.runtime_dir) / "alpaca_paper_mirror.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        history_path = Path(self.settings.runtime_dir) / "alpaca_paper_mirror.jsonl"
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(report, sort_keys=True) + "\n")
        return output_path


def sync_alpaca_paper_account_readonly(settings: Settings | None = None) -> dict[str, Any]:
    return AlpacaReadOnlyPaperMirror(settings=settings).sync()
