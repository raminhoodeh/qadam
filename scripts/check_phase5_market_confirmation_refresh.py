#!/usr/bin/env python3
"""Validate fresh market-confirmation coverage for Q5 strategy families."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_market_confirmation_refresh import (  # noqa: E402
    PHASE5_MARKET_CONFIRMATION_REFRESH_SCHEMA_VERSION,
    build_phase5_market_confirmation_refresh,
    validate_phase5_market_confirmation_refresh,
    write_phase5_market_confirmation_refresh,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_phase5_market_confirmation_refresh(settings=settings)
    output_path, history_path, event_log_path, written = write_phase5_market_confirmation_refresh(
        artifact,
        settings=settings,
    )
    validation_errors = validate_phase5_market_confirmation_refresh(written)
    event_replay = EventLog(event_log_path, echo=False).replay()

    print("phase5_market_confirmation_refresh_status=" + written["status"])
    print(
        "phase5_market_confirmation_refresh_schema_version="
        f"{PHASE5_MARKET_CONFIRMATION_REFRESH_SCHEMA_VERSION}"
    )
    print(f"phase5_market_confirmation_refresh_artifact_path={output_path}")
    print(f"phase5_market_confirmation_refresh_history_path={history_path}")
    print(f"phase5_market_confirmation_refresh_event_log_path={event_log_path}")
    print(f"phase5_market_confirmation_refresh_target_count={written['target_count']}")
    print(
        "phase5_market_confirmation_refresh_signal_written_count="
        f"{written['signal_written_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_review_written_count="
        f"{written['review_written_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_fresh_market_confirmation_count="
        f"{written['fresh_market_confirmation_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_hold_review_count="
        f"{written['hold_review_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_passed_to_risk_shadow_count="
        f"{written['passed_to_risk_shadow_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_execution_allowed_count="
        f"{written['execution_allowed_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_paper_order_allowed_count="
        f"{written['paper_order_allowed_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_trade_candidate_created_count="
        f"{written['trade_candidate_created_count']}"
    )
    print(
        "phase5_market_confirmation_refresh_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_market_confirmation_refresh_validation_error_count="
        f"{len(validation_errors)}"
    )
    print("phase5_market_confirmation_refresh_boundary=" + written["boundary"])

    if written["status"] != "ok":
        errors.append("market_confirmation_refresh_not_ok")
    if validation_errors:
        errors.extend(validation_errors)
    if written["target_count"] != 5:
        errors.append("market_confirmation_refresh_target_count_mismatch")
    if written["fresh_market_confirmation_count"] != written["target_count"]:
        errors.append("market_confirmation_refresh_fresh_count_mismatch")
    if written["execution_allowed_count"] != 0:
        errors.append("market_confirmation_refresh_execution_allowed_nonzero")
    if written["paper_order_allowed_count"] != 0:
        errors.append("market_confirmation_refresh_paper_order_allowed_nonzero")
    if written["trade_candidate_created_count"] != 0:
        errors.append("market_confirmation_refresh_trade_candidate_created_nonzero")
    if event_replay["total_events"] < 1:
        errors.append("market_confirmation_refresh_event_log_missing")

    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
