#!/usr/bin/env python3
"""Validate D6 read-only paper account mirror."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    MATURITY_CLOSED_TRADE_TARGET,
    PAPER_ACCOUNT_SCHEMA_VERSION,
    PaperAccountMirrorStore,
    ensure_d6_paper_account_mirror,
    paper_account_summary,
)

SNAPSHOT_REQUIRED_FIELDS = {
    "account_scope",
    "boundary",
    "broker",
    "cash_gbp",
    "closed_trade_count",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "equity_gbp",
    "live_capital_enabled",
    "maturity_closed_trade_count",
    "maturity_closed_trade_target",
    "max_drawdown_pct",
    "mode",
    "observed_at",
    "open_position_count",
    "peak_equity_gbp",
    "postmortem_complete_count",
    "postmortem_due_count",
    "realized_pnl_gbp",
    "schema_version",
    "snapshot_id",
    "starting_balance_gbp",
    "timeline_status",
    "unrealized_pnl_gbp",
    "write_authority",
}


def main() -> int:
    settings = Settings.from_env()
    result = ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    snapshots = store.read_snapshots()
    positions = store.read_positions()
    closed_trades = store.read_closed_trades()
    summary = paper_account_summary(settings)

    print("paper_account_status=" + summary["status"])
    print(f"paper_account_created_snapshot={result['created_snapshot']}")
    print(f"paper_account_snapshot_count={summary['snapshot_count']}")
    print(f"paper_account_current_balance_gbp={summary['current_balance_gbp']}")
    print(f"paper_account_realized_pnl_gbp={latest.realized_pnl_gbp if latest else 'missing'}")
    print(f"paper_account_unrealized_pnl_gbp={latest.unrealized_pnl_gbp if latest else 'missing'}")
    print(f"paper_account_drawdown_pct={summary['drawdown_pct']}")
    print(f"paper_account_open_position_count={summary['open_position_count']}")
    print(f"paper_account_closed_trade_count={summary['closed_trade_count']}")
    print(f"paper_account_postmortem_due_count={summary['postmortem_due_count']}")
    print(f"paper_account_live_capital_enabled={summary['live_capital_enabled']}")
    print(f"paper_account_write_authority={summary['write_authority']}")
    print("paper_account_boundary=" + summary["boundary"])

    if summary["status"] != "ok":
        print("paper_account_not_ok=true")
        return 1
    if latest is None:
        print("paper_account_latest_snapshot_missing=true")
        return 1
    latest_payload = latest.to_dict()
    missing_fields = sorted(SNAPSHOT_REQUIRED_FIELDS - set(latest_payload))
    if missing_fields:
        print("paper_account_snapshot_fields_missing=" + ",".join(missing_fields))
        return 1
    if latest.schema_version != PAPER_ACCOUNT_SCHEMA_VERSION:
        print("paper_account_schema_version_mismatch=true")
        return 1
    if latest.mode != "paper":
        print("paper_account_mode_not_paper=true")
        return 1
    if latest.account_scope != "first_release_gbp_1000_trial":
        print("paper_account_scope_mismatch=true")
        return 1
    if latest.connection_status != "local_mirror_not_broker_connected":
        print("paper_account_connection_status_mismatch=true")
        return 1
    if "No broker connection" not in latest.boundary:
        print("paper_account_snapshot_boundary_weak=true")
        return 1
    if "No broker write path exists" not in summary["boundary"]:
        print("paper_account_summary_boundary_weak=true")
        return 1
    if latest.live_capital_enabled:
        print("paper_account_live_capital_enabled_true=true")
        return 1
    if latest.write_authority:
        print("paper_account_write_authority_true=true")
        return 1
    if latest.starting_balance_gbp != settings.trial_balance_gbp:
        print("paper_account_starting_balance_mismatch=true")
        return 1
    if latest.maturity_closed_trade_target != MATURITY_CLOSED_TRADE_TARGET:
        print("paper_account_maturity_target_mismatch=true")
        return 1
    if latest.current_balance_gbp != latest.starting_balance_gbp:
        print("paper_account_current_balance_not_initial=true")
        return 1
    if latest.cash_gbp != latest.current_balance_gbp or latest.equity_gbp != latest.current_balance_gbp:
        print("paper_account_cash_equity_mismatch=true")
        return 1
    if latest.realized_pnl_gbp != 0 or latest.unrealized_pnl_gbp != 0:
        print("paper_account_pnl_not_zero=true")
        return 1
    if latest.drawdown_pct != 0 or latest.max_drawdown_pct != 0:
        print("paper_account_drawdown_not_zero=true")
        return 1
    if latest.open_position_count != len(positions):
        print("paper_account_open_position_count_mismatch=true")
        return 1
    if latest.closed_trade_count != len(closed_trades):
        print("paper_account_closed_trade_count_mismatch=true")
        return 1
    if latest.maturity_closed_trade_count != len(closed_trades):
        print("paper_account_maturity_count_mismatch=true")
        return 1
    if summary["snapshot_count"] != len(snapshots):
        print("paper_account_snapshot_count_mismatch=true")
        return 1

    print("paper_account_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
