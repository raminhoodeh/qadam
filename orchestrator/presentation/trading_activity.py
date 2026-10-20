"""Bounded read-only activity counts; orders, fills and experiments stay distinct."""

from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3


def activity_report(runtime, *, as_of):
    result = {"available": False, "as_of": as_of, "paper_only": True,
              "window_basis": "trailing_seven_calendar_days_not_a_five_session_soak",
              "trade_quota_enforced": False, "account_scope": "current_canonical_ledger",
              "paper_order_allowed": False, "broker_write_count": 0}
    database = Path(runtime) / "qadam-control-plane.sqlite3"
    if not database.is_file():
        return result
    cutoff = (datetime.fromisoformat(as_of.replace("Z", "+00:00")) - timedelta(days=7)).isoformat()
    try:
        with sqlite3.connect(database.resolve().as_uri()+"?mode=ro", uri=True, timeout=1) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            orders = list(conn.execute(
                "SELECT o.state,o.payload_json,d.payload_json AS decision FROM canonical_orders o "
                "LEFT JOIN decision_transactions d ON d.decision_id=o.decision_id "
                "WHERE o.created_at>=? AND o.created_at<=? ORDER BY o.created_at DESC LIMIT 5001", (cutoff, as_of)))
            counts, events = Counter(), set()
            for row in orders[:5000]:
                payload = json.loads(row["payload_json"])
                purpose = payload.get("purpose")
                entry = purpose == "canonical_position_entry"
                exit_order = purpose == "canonical_position_exit"
                counts["entry_intents"] += int(entry)
                counts["exit_intents"] += int(exit_order)
                counts["unclassified_legacy_orders"] += int(not entry and not exit_order)
                confirmed = row["state"] in {"accepted", "filled", "partially_filled", "closed"}
                counts["broker_acknowledged_entries"] += int(entry and confirmed)
                counts["filled_entry_orders"] += int(entry and row["state"] in {"filled", "closed", "partially_filled"})
                counts["filled_exit_orders"] += int(exit_order and row["state"] in {"filled", "closed", "partially_filled"})
                if entry and confirmed and row["decision"]:
                    event = json.loads(row["decision"]).get("economic_signal_identity_id")
                    if event:
                        events.add(event)
            counts["fill_records"] = conn.execute("SELECT COUNT(*) FROM fills WHERE occurred_at>=? AND occurred_at<=?",
                                                   (cutoff, as_of)).fetchone()[0]
            dispositions = dict(conn.execute(
                "SELECT terminal_state,COUNT(*) FROM decision_transactions WHERE created_at>=? AND created_at<=? "
                "GROUP BY terminal_state", (cutoff, as_of)))
            last = conn.execute("SELECT payload_json FROM liveness_cycles ORDER BY created_at DESC LIMIT 1").fetchone()
            return {**result, "available": True, "window_start": cutoff,
                    "counts": dict(counts), "independent_acknowledged_entry_events": len(events),
                    "decision_dispositions": dispositions, "order_rows_truncated": len(orders)>5000,
                    "latest_progress": json.loads(last[0]) if last else None,
                    "independent_outcomes_are_not_fill_count": True}
    except (sqlite3.Error, ValueError, TypeError):
        return {**result, "reason": "activity_ledger_read_unavailable"}
