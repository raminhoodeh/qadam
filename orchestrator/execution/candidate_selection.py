"""Conservative entry suppression from one verified, read-only ledger snapshot."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3


def defer_held_entries(candidates, runtime, *, now=None):
    """Skip existing exposure, never grant entry authority from preview data."""
    now = now or datetime.now(timezone.utc)
    connection = None
    try:
        connection = sqlite3.connect(
            f"file:{Path(runtime) / 'qadam-control-plane.sqlite3'}?mode=ro",
            uri=True, timeout=5,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        row = connection.execute(
            "SELECT * FROM reconciliation_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row or sha256(row["payload_json"].encode()).hexdigest() != row["payload_sha256"]:
            return
        check = json.loads(row["payload_json"])
        observed = check.get("observed") or {}
        timestamp = datetime.fromisoformat(observed["mirror_observed_at"].replace("Z", "+00:00"))
        if (row["status"] != "passed" or check.get("status") != "passed"
                or check.get("paper_only") is not True
                or check.get("live_capital_enabled") is not False
                or check.get("blockers") != []
                or not observed.get("position_protection_digest")
                or not 0 <= (now - timestamp).total_seconds() <= 180):
            return
        positions = connection.execute("SELECT * FROM positions WHERE state='open'").fetchall()
        if observed.get("position_count") != len(positions):
            return
        held = set()
        for position in positions:
            if sha256(position["payload_json"].encode()).hexdigest() != position["payload_sha256"]:
                return
            payload = json.loads(position["payload_json"])
            quantity = float(position["quantity"])
            if (not math.isfinite(quantity) or quantity == 0
                    or payload.get("instrument") != position["instrument"]
                    or float(payload["quantity"]) != quantity):
                return
            held.add(position["instrument"])
        for candidate in candidates:
            symbol = (candidate.get("request_preview") or {}).get("symbol") or candidate.get("instrument")
            if (symbol in held and candidate.get("fresh_for_paper_post") is True
                    and candidate.get("previously_submitted_to_alpaca_paper") is False):
                candidate.update(fresh_for_paper_post=False, status="held_existing_open_position",
                                 entry_hold_reason="duplicate_open_position_in_ledger",
                                 entry_hold_reconciliation_id=check["reconciliation_id"])
    except (sqlite3.Error, ValueError, TypeError, KeyError, AttributeError):
        # Missing preview truth leaves the fenced immediate prewrite in charge.
        return
    finally:
        if connection is not None:
            connection.close()
