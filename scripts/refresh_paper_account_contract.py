#!/usr/bin/env python3
"""Append a local paper-account snapshot under the active release contract."""

from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    MATURITY_CLOSED_TRADE_TARGET,
    PAPER_ACCOUNT_SCHEMA_VERSION,
    PaperAccountMirrorStore,
    PaperAccountSnapshot,
    _now,
)
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    positions = store.read_positions()
    closed_trades = store.read_closed_trades()
    orders = store.read_orders()

    starting_balance = float(settings.trial_balance_gbp)
    equity = float(getattr(latest, "equity_gbp", starting_balance))
    cash = float(getattr(latest, "cash_gbp", equity))
    current_balance = float(getattr(latest, "current_balance_gbp", equity))
    peak_equity = max(float(getattr(latest, "peak_equity_gbp", equity)), starting_balance, equity)
    drawdown_pct = round(max(0.0, (peak_equity - equity) / peak_equity * 100), 3) if peak_equity else 0.0

    snapshot = PaperAccountSnapshot(
        schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
        snapshot_id=str(uuid4()),
        account_scope=PAPER_ACCOUNT_SCOPE,
        mode="paper",
        broker=str(getattr(latest, "broker", "local_mirror_pending_alpaca_readonly")),
        connection_status=str(
            getattr(latest, "connection_status", "local_mirror_not_broker_connected")
        ),
        starting_balance_gbp=starting_balance,
        current_balance_gbp=current_balance,
        cash_gbp=cash,
        equity_gbp=equity,
        peak_equity_gbp=round(peak_equity, 2),
        realized_pnl_gbp=float(getattr(latest, "realized_pnl_gbp", 0.0)),
        unrealized_pnl_gbp=float(getattr(latest, "unrealized_pnl_gbp", 0.0)),
        drawdown_pct=drawdown_pct,
        max_drawdown_pct=max(float(getattr(latest, "max_drawdown_pct", 0.0)), drawdown_pct),
        live_capital_enabled=False,
        write_authority=False,
        open_position_count=len(positions),
        closed_trade_count=len(closed_trades),
        postmortem_due_count=sum(
            1 for trade in closed_trades if trade.postmortem_status == "postmortem_due"
        ),
        postmortem_complete_count=sum(
            1 for trade in closed_trades if trade.postmortem_status == "postmortem_complete"
        ),
        maturity_closed_trade_target=MATURITY_CLOSED_TRADE_TARGET,
        maturity_closed_trade_count=len(closed_trades),
        timeline_status=str(getattr(latest, "timeline_status", "contract_refreshed")),
        observed_at=_now(),
        boundary=str(
            getattr(
                latest,
                "boundary",
                "Read-only local paper account mirror. No broker write path exists.",
            )
        ),
    )
    store.write_snapshot(snapshot)
    print("paper_account_contract_refresh=ok")
    print(f"paper_account_scope={snapshot.account_scope}")
    print(f"paper_account_starting_balance_gbp={snapshot.starting_balance_gbp}")
    print(f"paper_account_current_balance_gbp={snapshot.current_balance_gbp}")
    print(f"paper_account_live_capital_enabled={snapshot.live_capital_enabled}")
    print(f"paper_account_write_authority={snapshot.write_authority}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
