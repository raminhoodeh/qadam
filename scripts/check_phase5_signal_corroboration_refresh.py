#!/usr/bin/env python3
"""Validate second-source corroboration refresh for shadow signals."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_signal_corroboration_refresh import (  # noqa: E402
    PHASE5_SIGNAL_CORROBORATION_REFRESH_SCHEMA_VERSION,
    build_phase5_signal_corroboration_refresh,
    validate_phase5_signal_corroboration_refresh,
    write_phase5_signal_corroboration_refresh,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_phase5_signal_corroboration_refresh(settings=settings)
    output_path, history_path, event_log_path, written = write_phase5_signal_corroboration_refresh(
        artifact,
        settings=settings,
    )
    validation_errors = validate_phase5_signal_corroboration_refresh(written)
    event_replay = EventLog(event_log_path, echo=False).replay()

    print("phase5_signal_corroboration_refresh_status=" + written["status"])
    print(
        "phase5_signal_corroboration_refresh_schema_version="
        f"{PHASE5_SIGNAL_CORROBORATION_REFRESH_SCHEMA_VERSION}"
    )
    print(f"phase5_signal_corroboration_refresh_artifact_path={output_path}")
    print(f"phase5_signal_corroboration_refresh_history_path={history_path}")
    print(f"phase5_signal_corroboration_refresh_event_log_path={event_log_path}")
    print(f"phase5_signal_corroboration_refresh_candidate_count={written['candidate_count']}")
    print(
        "phase5_signal_corroboration_refresh_refreshed_signal_count="
        f"{written['refreshed_signal_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_signal_written_count="
        f"{written['signal_written_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_review_written_count="
        f"{written['review_written_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_passed_to_risk_shadow_count="
        f"{written['passed_to_risk_shadow_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_signals_with_market_confirmation_count="
        f"{written['signals_with_market_confirmation_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_signals_passed_to_risk_count="
        f"{written['signals_passed_to_risk_count']}"
    )
    print(
        "phase5_signal_corroboration_refresh_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_signal_corroboration_refresh_validation_error_count="
        f"{len(validation_errors)}"
    )
    print("phase5_signal_corroboration_refresh_boundary=" + written["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "ok":
        errors.append("signal_corroboration_refresh_not_ok")
    if written["signals_with_market_confirmation_count"] < 5:
        errors.append("signals_with_market_confirmation_count_below_floor")
    if written["signals_passed_to_risk_count"] < 2:
        errors.append("signals_passed_to_risk_count_below_floor")
    if written["execution_allowed_count"] != 0:
        errors.append("execution_allowed_count_nonzero")
    if written["paper_order_allowed_count"] != 0:
        errors.append("paper_order_allowed_count_nonzero")
    if written["trade_candidate_created_count"] != 0:
        errors.append("trade_candidate_created_count_nonzero")

    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
