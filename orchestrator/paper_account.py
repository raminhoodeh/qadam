"""Read-only paper account mirror for the first-release cockpit.

D6 creates a local account mirror contract before any broker integration. It is
the place where balance, P&L, drawdown, positions, closed trades, and maturity
progress appear once read-only broker data is connected.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

PAPER_ACCOUNT_SCHEMA_VERSION = 1
MATURITY_CLOSED_TRADE_TARGET = 100


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    if trade.postmortem_status not in {"postmortem_due", "postmortem_complete"}:
        raise ValueError(f"invalid postmortem status: {trade.postmortem_status}")


class PaperAccountMirrorStore:
    def __init__(self, root: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        base = Path(root or self.settings.runtime_dir)
        self.snapshots_path = base / "paper_account_snapshots.jsonl"
        self.positions_path = base / "paper_positions.jsonl"
        self.closed_trades_path = base / "paper_closed_trades.jsonl"
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

    def latest_snapshot(self) -> PaperAccountSnapshot | None:
        snapshots = self.read_snapshots()
        return snapshots[-1] if snapshots else None

    def health(self) -> dict[str, Any]:
        try:
            snapshots = self.read_snapshots()
            positions = self.read_positions()
            closed_trades = self.read_closed_trades()
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


def initial_paper_account_snapshot(settings: Settings | None = None) -> PaperAccountSnapshot:
    settings = settings or Settings.from_env()
    now = _now()
    starting_balance = float(settings.trial_balance_gbp)
    return PaperAccountSnapshot(
        schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
        snapshot_id=str(uuid4()),
        account_scope="first_release_gbp_1000_trial",
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
        "postmortem_due_count": health.get("postmortem_due_count", 0),
        "postmortem_complete_count": health.get("postmortem_complete_count", 0),
        "current_balance_gbp": latest.current_balance_gbp if latest else settings.trial_balance_gbp,
        "drawdown_pct": latest.drawdown_pct if latest else 0,
        "live_capital_enabled": latest.live_capital_enabled if latest else False,
        "write_authority": latest.write_authority if latest else False,
        "boundary": health.get("boundary", "No paper account mirror snapshot is available."),
    }
