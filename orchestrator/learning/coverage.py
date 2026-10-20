"""Account-scoped attribution coverage from the existing canonical ledger."""

from collections import Counter
import json
import math
from pathlib import Path
import sqlite3


def attribution_coverage(runtime, *, epoch_id):
    database = Path(runtime) / "qadam-control-plane.sqlite3"
    result = {"available": False, "paper_epoch_id": epoch_id,
              "gross_accounting_is_net_performance": False,
              "historical_gaps_block_new_discovery": False}
    if not database.is_file() or not epoch_id:
        return result
    try:
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=2) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            rows = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload_json FROM outcomes WHERE state='closed' "
                "AND json_extract(payload_json, '$.paper_epoch_id')=?", (epoch_id,))]
            counts = Counter()
            gross = []
            for row in rows:
                if row.get("accounting_status") == "gross_reconstructed":
                    counts["gross_reconstructed"] += 1
                    if (type(row.get("realized_pnl")) in (int, float)
                            and math.isfinite(row["realized_pnl"])):
                        gross.append(row["realized_pnl"])
                lots = row.get("attributed_lots") or [row]
                for lot in lots:
                    exact = lot.get("attribution_status") == "exact_entry_decision"
                    versioned = lot.get("strategy_version") not in (
                        None, "", "unversioned", "strategy-version-unclassified")
                    counts["exact_decision_lots"] += int(exact)
                    counts["versioned_lots"] += int(exact and versioned)
                    counts["costed_lots"] += int(exact and versioned and lot.get("net_return") is not None)
                    counts["benchmark_matched_lots"] += int(lot.get("benchmark_comparison_available") is True)
                    if not exact:
                        counts["missing_exact_entry_decision"] += 1
                    elif not versioned:
                        counts["missing_registered_strategy_version"] += 1
                    elif lot.get("net_return") is None:
                        counts["missing_prospective_cost_model"] += 1
            return {**result, "available": True, "closed_broker_outcomes": len(rows),
                    "counts": dict(counts),
                    "reconstructed_gross_pnl": round(sum(gross), 8) if gross else None,
                    "gross_pnl_coverage": len(gross),
                    "unknown_costs_are_zero": False}
    except (sqlite3.Error, ValueError, TypeError):
        return {**result, "reason": "canonical_attribution_read_failed"}
