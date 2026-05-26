#!/usr/bin/env python3
"""Run one operational pass of the Phase 7 30-day demo-proof harness."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase7_demo_proof_run import (  # noqa: E402
    build_phase7_demo_proof_run,
    phase7_demo_proof_run_paths,
    write_phase7_demo_proof_run,
)


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def main() -> int:
    settings = Settings.from_env()
    start_date = _arg_value("--start-date=")
    reset = "--reset" in sys.argv
    _output_path, _history_path, event_log_path = phase7_demo_proof_run_paths(settings)

    artifact = build_phase7_demo_proof_run(
        settings=settings,
        start_date=start_date,
        reset=reset,
    )
    output_path, history_path, event_path, written = write_phase7_demo_proof_run(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )

    print(f"phase7_demo_run_status={written['status']}")
    print(f"phase7_demo_run_state={written['run_state']}")
    print(f"phase7_demo_run_id={written['run_id']}")
    print(f"phase7_demo_run_timezone={written['timezone']}")
    print(f"phase7_demo_run_start_date={written['start_date']}")
    print(f"phase7_demo_run_end_date={written['end_date']}")
    print(f"phase7_demo_run_local_observation_date={written['local_observation_date']}")
    print(f"phase7_demo_run_active_day_number={written['active_day_number']}")
    print(
        "phase7_demo_run_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
    )
    print(
        "phase7_demo_run_calendar_days_remaining="
        f"{written['calendar_days_remaining']}"
    )
    print(
        "phase7_demo_run_phase7_30_day_run_complete="
        f"{written['phase7_30_day_run_complete']}"
    )
    print(
        "phase7_demo_run_qualified_setups_exist="
        f"{written['qualified_setups_exist']}"
    )
    print(f"phase7_demo_run_qualified_setup_count={written['qualified_setup_count']}")
    print(
        "phase7_demo_run_auto_approved_setup_count="
        f"{written['auto_approved_setup_count']}"
    )
    print(f"phase7_demo_run_staged_order_count={written['staged_order_count']}")
    print(
        "phase7_demo_run_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "phase7_demo_run_closed_proof_trade_count="
        f"{written['closed_proof_trade_count']}"
    )
    print(f"phase7_demo_run_collection_state={written['collection_state']}")
    print(
        "phase7_demo_run_proof_trade_collection_attempted="
        f"{written['proof_trade_collection_attempted']}"
    )
    print(
        "phase7_demo_run_proof_trade_collection_blocker_count="
        f"{written['proof_trade_collection_blocker_count']}"
    )
    print(
        "phase7_demo_run_proof_trade_collection_blockers="
        f"{','.join(written['proof_trade_collection_blockers'])}"
    )
    print(f"phase7_demo_run_no_trade_rationale={written['no_trade_rationale']}")
    print(
        "phase7_demo_run_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase7_demo_run_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase7_demo_run_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_demo_run_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(f"phase7_demo_run_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_demo_run_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_demo_run_certification_status={written['certification_status']}")
    print(f"phase7_demo_run_live_promotion_status={written['live_promotion_status']}")
    print(f"phase7_demo_run_blocker_count={written['blocker_count']}")
    print(f"phase7_demo_run_artifact_path={output_path}")
    print(f"phase7_demo_run_history_path={history_path}")
    print(f"phase7_demo_run_event_log_path={event_path}")
    print(f"phase7_demo_run_validation_errors={written['validation_errors']}")
    if written["validation_errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
