#!/usr/bin/env python3
"""Quarantine pending Alpaca Paper orders from an explicitly bounded incident."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_pending_order_quarantine import (  # noqa: E402
    quarantine_pending_paper_orders,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--incident-started-at", required=True)
    parser.add_argument("--execute-paper-cancel", action="store_true")
    args = parser.parse_args()
    result = quarantine_pending_paper_orders(
        Settings.from_env(),
        incident_id=args.incident_id,
        incident_started_at=args.incident_started_at,
        execute=args.execute_paper_cancel,
    )
    print(f"qadam_pending_order_quarantine_status={result['status']}")
    print(
        "qadam_pending_order_quarantine_selected_open_order_count="
        f"{result['selected_open_order_count']}"
    )
    print(
        "qadam_pending_order_quarantine_cancel_requested_count="
        f"{result['cancel_requested_count']}"
    )
    print(
        "qadam_pending_order_quarantine_cancel_failed_count="
        f"{result['cancel_failed_count']}"
    )
    return 1 if result["cancel_failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
