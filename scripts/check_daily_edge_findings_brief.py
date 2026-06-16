#!/usr/bin/env python3
"""Validate and write Qadam's Daily Edge Findings brief."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.daily_edge_findings import (  # noqa: E402
    EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    build_daily_edge_findings_brief,
    validate_daily_edge_findings_brief,
    write_daily_edge_findings_brief,
)

REPORT_PATH = ROOT / "data/runtime/daily_edge_findings_brief_check.json"


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    brief = build_daily_edge_findings_brief(cockpit_status=cockpit_status)
    validate_daily_edge_findings_brief(brief)
    paths = write_daily_edge_findings_brief(brief, settings=settings)

    authority_leaks = [
        field for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if brief.get(field) is not False
    ]
    pattern_authority_leaks = [
        pattern.get("pattern_id", pattern.get("sleeve_key", "unknown"))
        for pattern in brief["patterns_observed"]
        if any(pattern.get(field) is not False for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS)
    ]
    strategy_authority_leaks = [
        update.get("update_id", update.get("sleeve_key", "unknown"))
        for update in brief["strategy_updates"]
        if any(update.get(field) is not False for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS)
    ]
    errors: list[str] = []
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    if pattern_authority_leaks:
        errors.append("pattern_authority_leaks=" + ",".join(map(str, pattern_authority_leaks)))
    if strategy_authority_leaks:
        errors.append("strategy_authority_leaks=" + ",".join(map(str, strategy_authority_leaks)))
    if brief["source_count"] < 30:
        errors.append("source_count_below_30")
    if brief["watched_instrument_count"] < 20:
        errors.append("watched_instrument_count_below_20")
    if brief["candidate_pattern_count"] != len(brief["patterns_observed"]):
        errors.append("candidate_pattern_count_mismatch")
    if brief["candidate_pattern_count"] < 5:
        errors.append("candidate_pattern_count_below_5")
    if brief["quantum_review"].get("core_gate") is not True:
        errors.append("quantum_not_core_gate")
    if brief["telegram_message"].get("telegram_command_path_enabled") is not False:
        errors.append("telegram_command_path_enabled")
    if brief["telegram_message"].get("telegram_live_send_allowed") is not False:
        errors.append("telegram_live_send_allowed")
    if "quantum" not in str(brief["telegram_message"].get("body", "")).lower():
        errors.append("telegram_message_missing_quantum")

    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": "ok" if not errors else "failed",
                "errors": errors,
                "brief_status": brief["status"],
                "brief_date": brief["brief_date"],
                "source_count": brief["source_count"],
                "watched_instrument_count": brief["watched_instrument_count"],
                "candidate_pattern_count": brief["candidate_pattern_count"],
                "validated_edge_count": brief["validated_edge_count"],
                "quantum_review_status": brief["quantum_review_status"],
                "quantum_backend": brief["quantum_backend"],
                "quantum_core_gate": brief["quantum_review"].get("core_gate") is True,
                "patterns_observed_count": len(brief["patterns_observed"]),
                "patterns_rejected_count": len(brief["patterns_rejected"]),
                "strategy_update_count": len(brief["strategy_updates"]),
                "telegram_message_status": brief["telegram_message"]["status"],
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("; ".join(errors))

    print("daily_edge_findings_brief_check=ok")
    print(f"daily_edge_findings_brief_status={brief['status']}")
    print(f"daily_edge_findings_brief_date={brief['brief_date']}")
    print(f"daily_edge_findings_source_count={brief['source_count']}")
    print(f"daily_edge_findings_watched_instrument_count={brief['watched_instrument_count']}")
    print(f"daily_edge_findings_candidate_pattern_count={brief['candidate_pattern_count']}")
    print(f"daily_edge_findings_validated_edge_count={brief['validated_edge_count']}")
    print(f"daily_edge_findings_quantum_status={brief['quantum_review_status']}")
    print(f"daily_edge_findings_quantum_backend={brief['quantum_backend']}")
    print(f"daily_edge_findings_quantum_core_gate={brief['quantum_review']['core_gate']}")
    print(f"daily_edge_findings_patterns_observed_count={len(brief['patterns_observed'])}")
    print(f"daily_edge_findings_patterns_rejected_count={len(brief['patterns_rejected'])}")
    print(f"daily_edge_findings_strategy_update_count={len(brief['strategy_updates'])}")
    print(f"daily_edge_findings_telegram_message_status={brief['telegram_message']['status']}")
    print(f"daily_edge_findings_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
