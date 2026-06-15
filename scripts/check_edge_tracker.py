#!/usr/bin/env python3
"""Validate Qadam's public edge-tracker status contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.cockpit_status import build_cockpit_status
from orchestrator.edge_tracker import validate_edge_tracker_status

REPORT_PATH = ROOT / "data/runtime/edge_tracker_check.json"


def main() -> None:
    settings = Settings.from_env()
    payload = build_cockpit_status(settings)
    edge = payload["edge_tracker"]
    validate_edge_tracker_status(edge)

    sleeves = edge["sleeves"]
    symbols = edge["market_price_watch"]["symbols"]
    required_symbols = {
        "CL=F",
        "BZ=F",
        "USO",
        "XLE",
        "SI=F",
        "SLV",
        "SMH",
        "SOXX",
        "NVDA",
        "AMD",
        "Polymarket CLOB",
        "Kalshi events",
        "ITA",
        "XAR",
        "LMT",
        "RTX",
        "NOC",
    }
    missing_symbols = sorted(required_symbols - set(symbols))
    authority_leaks = [
        key
        for key, value in edge.items()
        if key.endswith("_allowed") or key.endswith("_enabled") or key.endswith("_authority")
        if value is not False
    ]
    sleeve_authority_leaks = [
        sleeve["key"]
        for sleeve in sleeves
        if int(sleeve.get("order_authority_source_count", 0) or 0) != 0
    ]
    errors: list[str] = []
    if missing_symbols:
        errors.append(f"missing_symbols={','.join(missing_symbols)}")
    if authority_leaks:
        errors.append(f"authority_leaks={','.join(authority_leaks)}")
    if sleeve_authority_leaks:
        errors.append(f"sleeve_authority_leaks={','.join(sleeve_authority_leaks)}")
    if edge["weekly_thesis"].get("cadence") != "weekly":
        errors.append("weekly_thesis_cadence_not_weekly")
    if edge["quantum_pattern_review"].get("paper_order_allowed_count") != 0:
        errors.append("quantum_pattern_review_paper_order_allowed")

    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": "ok" if not errors else "failed",
                "errors": errors,
                "sleeve_count": edge["sleeve_count"],
                "watched_instrument_count": edge["watched_instrument_count"],
                "weekly_thesis": edge["weekly_thesis"],
                "quantum_pattern_review": edge["quantum_pattern_review"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("; ".join(errors))

    print("edge_tracker_check=ok")
    print(f"edge_tracker_sleeve_count={edge['sleeve_count']}")
    print(f"edge_tracker_watched_instrument_count={edge['watched_instrument_count']}")
    print(f"edge_tracker_weekly_thesis_cadence={edge['weekly_thesis']['cadence']}")
    print(f"edge_tracker_quantum_mode={edge['quantum_pattern_review']['mode']}")
    print("edge_tracker_order_authority=false")


if __name__ == "__main__":
    main()
