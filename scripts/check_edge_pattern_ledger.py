#!/usr/bin/env python3
"""Validate and write Qadam's edge pattern ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.edge_pattern_ledger import (  # noqa: E402
    EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    validate_edge_pattern_ledger,
    write_edge_pattern_ledger,
)

REPORT_PATH = ROOT / "data/runtime/edge_pattern_ledger_check.json"


def main() -> None:
    settings = Settings.from_env()
    payload = build_cockpit_status(settings)
    ledger = payload["edge_pattern_ledger"]
    validate_edge_pattern_ledger(ledger)
    paths = write_edge_pattern_ledger(ledger, settings=settings)

    authority_leaks = [
        field for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if ledger.get(field) is not False
    ]
    pattern_authority_leaks = [
        pattern.get("pattern_id", pattern.get("sleeve_key", "unknown"))
        for pattern in ledger["patterns"]
        if pattern.get("paper_order_allowed") is not False
        or pattern.get("broker_write_allowed") is not False
        or pattern.get("live_capital_enabled") is not False
        or pattern.get("quantum_required") is not True
    ]
    errors: list[str] = []
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    if pattern_authority_leaks:
        errors.append("pattern_authority_leaks=" + ",".join(map(str, pattern_authority_leaks)))
    if ledger["sprint"].get("length_days") != 30:
        errors.append("sprint_not_30_days")
    if ledger["quantum_review"].get("core_gate") is not True:
        errors.append("quantum_not_core_gate")
    if ledger["source_price_scope"].get("source_mode") != "all_sources_every_sleeve":
        errors.append("source_mode_not_all_sources_every_sleeve")
    if ledger["telegram_summary"].get("telegram_command_path_enabled") is not False:
        errors.append("telegram_command_path_enabled")
    if ledger["telegram_summary"].get("telegram_live_send_allowed") is not False:
        errors.append("telegram_live_send_allowed")

    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": "ok" if not errors else "failed",
                "errors": errors,
                "ledger_status": ledger["status"],
                "sprint": ledger["sprint"],
                "candidate_pattern_count": ledger["candidate_pattern_count"],
                "validated_edge_count": ledger["validated_edge_count"],
                "passed_criterion_count": ledger["passed_criterion_count"],
                "criterion_count": ledger["criterion_count"],
                "quantum_review": ledger["quantum_review"],
                "telegram_summary_status": ledger["telegram_summary"]["status"],
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("; ".join(errors))

    print("edge_pattern_ledger_check=ok")
    print(f"edge_pattern_ledger_status={ledger['status']}")
    print(f"edge_pattern_ledger_sprint_day={ledger['sprint']['day_number']}")
    print(f"edge_pattern_ledger_sprint_days_remaining={ledger['sprint']['days_remaining']}")
    print(f"edge_pattern_ledger_candidate_pattern_count={ledger['candidate_pattern_count']}")
    print(f"edge_pattern_ledger_validated_edge_count={ledger['validated_edge_count']}")
    print(
        "edge_pattern_ledger_criteria="
        f"{ledger['passed_criterion_count']}/{ledger['criterion_count']}"
    )
    print(f"edge_pattern_ledger_quantum_mode={ledger['quantum_review']['mode']}")
    print(f"edge_pattern_ledger_quantum_core_gate={ledger['quantum_review']['core_gate']}")
    print(f"edge_pattern_ledger_source_count={ledger['source_price_scope']['source_count']}")
    print(f"edge_pattern_ledger_watched_instrument_count={ledger['source_price_scope']['watched_instrument_count']}")
    print(f"edge_pattern_ledger_telegram_summary_status={ledger['telegram_summary']['status']}")
    print(f"edge_pattern_ledger_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
