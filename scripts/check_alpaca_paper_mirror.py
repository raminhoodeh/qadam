#!/usr/bin/env python3
"""Validate the Alpaca read-only paper-account mirror.

This check can run without network access to verify the local contract. With
`--live`, it calls Alpaca GET endpoints for account, positions, orders, and
portfolio history, then writes only sanitized mirror state into local runtime
files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    ALPACA_READONLY_PATHS,
    ALPACA_PAPER_BASE_URL,
    PaperAccountMirrorStore,
    alpaca_paper_mirror_status,
    ensure_d6_paper_account_mirror,
    sync_alpaca_paper_account_readonly,
)

MUTATING_PATH_HINTS = (
    "/orders/",
    "/positions/",
    "/account/configurations",
    "/watchlists",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Alpaca read-only paper endpoints and refresh the local mirror.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    ensure_d6_paper_account_mirror(settings)
    status = alpaca_paper_mirror_status(settings)

    print("alpaca_paper_mirror_status=" + status["status"])
    print(f"alpaca_paper_mirror_base_url={status['base_url']}")
    print(f"alpaca_paper_mirror_paper_mode={status['paper_mode']}")
    print(f"alpaca_paper_mirror_write_authority={status['write_authority']}")
    print("alpaca_paper_mirror_readonly_paths=" + ",".join(status["readonly_paths"]))

    if status["write_authority"]:
        print("alpaca_paper_mirror_write_authority_enabled=true")
        return 1
    if not status["paper_mode"]:
        print("alpaca_paper_mirror_paper_mode_disabled=true")
        return 1
    if not str(status["base_url"]).rstrip("/").startswith(ALPACA_PAPER_BASE_URL):
        print("alpaca_paper_mirror_not_paper_endpoint=true")
        return 1
    if any(any(hint in path for hint in MUTATING_PATH_HINTS) for path in ALPACA_READONLY_PATHS):
        print("alpaca_paper_mirror_mutating_path_allowed=true")
        return 1

    if args.live:
        if status["status"] != "configured":
            print("alpaca_paper_mirror_missing_credentials=true")
            return 1
        try:
            report = sync_alpaca_paper_account_readonly(settings)
        except Exception as exc:  # noqa: BLE001 - live validation must fail closed.
            print(f"alpaca_paper_mirror_live_error={exc.__class__.__name__}")
            return 1
        print("alpaca_paper_mirror_live_sync_status=" + report["status"])
        print(f"alpaca_paper_mirror_position_count={report['position_count']}")
        print(f"alpaca_paper_mirror_order_count={report['order_count']}")
        print(f"alpaca_paper_mirror_closed_trade_count={report['closed_trade_count']}")
        print(f"alpaca_paper_mirror_read_retry_count={report.get('read_retry_count', 0)}")
        market_clock = report.get("market_clock", {})
        print("alpaca_paper_mirror_market_clock_status=" + str(market_clock.get("status", "missing")))
        print("alpaca_paper_mirror_market_clock_is_open=" + str(market_clock.get("is_open")))
        print("alpaca_paper_mirror_market_clock_next_open=" + str(market_clock.get("next_open")))
        print("alpaca_paper_mirror_market_clock_next_close=" + str(market_clock.get("next_close")))
        print(f"alpaca_paper_mirror_live_capital_enabled={report['live_capital_enabled']}")
        print(f"alpaca_paper_mirror_write_authority={report['write_authority']}")
        if report["live_capital_enabled"] or report["write_authority"]:
            print("alpaca_paper_mirror_authority_enabled=true")
            return 1

    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    orders = store.read_orders()
    positions = store.read_positions()
    closed_trades = store.read_closed_trades()
    if latest is None:
        print("alpaca_paper_mirror_latest_snapshot_missing=true")
        return 1

    print("alpaca_paper_mirror_connection_status=" + latest.connection_status)
    print("alpaca_paper_mirror_account_currency=" + latest.account_currency)
    print("alpaca_paper_mirror_display_currency=" + latest.display_currency)
    print(f"alpaca_paper_mirror_fx_to_gbp_rate={latest.fx_to_gbp_rate}")
    print("alpaca_paper_mirror_broker_reconciliation_status=" + latest.broker_reconciliation_status)
    print(f"alpaca_paper_mirror_broker_reconciliation_delta={latest.broker_reconciliation_delta}")
    print(f"alpaca_paper_mirror_current_balance_gbp={latest.current_balance_gbp}")
    print(f"alpaca_paper_mirror_cash_gbp={latest.cash_gbp}")
    print(f"alpaca_paper_mirror_equity_gbp={latest.equity_gbp}")
    print(f"alpaca_paper_mirror_realized_pnl_gbp={latest.realized_pnl_gbp}")
    print(f"alpaca_paper_mirror_unrealized_pnl_gbp={latest.unrealized_pnl_gbp}")
    print(f"alpaca_paper_mirror_open_position_count={len(positions)}")
    print(f"alpaca_paper_mirror_order_count={len(orders)}")
    print(
        "alpaca_paper_mirror_open_order_count="
        f"{sum(1 for order in orders if order.status in {'new', 'accepted', 'pending_new', 'partially_filled', 'held'})}"
    )
    print(f"alpaca_paper_mirror_closed_trade_count={len(closed_trades)}")
    print("alpaca_paper_mirror_report_path=data/runtime/alpaca_paper_mirror.json")
    print("alpaca_paper_mirror_boundary=" + latest.boundary)

    if latest.live_capital_enabled or latest.write_authority:
        print("alpaca_paper_mirror_snapshot_authority_enabled=true")
        return 1
    if any(order.execution_allowed or order.paper_order_allowed for order in orders):
        print("alpaca_paper_mirror_order_authority_enabled=true")
        return 1
    if latest.open_position_count != len(positions):
        print("alpaca_paper_mirror_position_count_mismatch=true")
        return 1
    if latest.closed_trade_count != len(closed_trades):
        print("alpaca_paper_mirror_closed_trade_count_mismatch=true")
        return 1
    if not latest.account_currency or not latest.display_currency:
        print("alpaca_paper_mirror_currency_missing=true")
        return 1
    if latest.broker == "alpaca_paper_readonly" and latest.broker_reconciliation_status not in {
        "ok",
        "drift",
        "history_unavailable",
        "not_available",
    }:
        print("alpaca_paper_mirror_reconciliation_status_invalid=true")
        return 1

    print("alpaca_paper_mirror_check=ok")
    from orchestrator.runtime.command import report_work_result
    report_work_result({"status": "mirror_validated", "generated_at": latest.observed_at})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
