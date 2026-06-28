#!/usr/bin/env python3
"""Validate the actual Phase 7 paper-operation run ledger."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_demo_proof_run import (  # noqa: E402
    PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION,
    build_phase7_demo_proof_run,
    phase7_demo_proof_run_paths,
    validate_phase7_demo_proof_run,
    write_phase7_demo_proof_run,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _expected_calendar_state(artifact: dict[str, object]) -> dict[str, object]:
    start = date.fromisoformat(str(artifact["start_date"]))
    end = date.fromisoformat(str(artifact["end_date"]))
    current = date.fromisoformat(str(artifact["local_observation_date"]))
    scheduled_days = int(artifact["scheduled_calendar_day_count"])

    if current < start:
        run_state = "scheduled_not_started"
        active_day_number = None
        actual_elapsed_days = 0
        completed_days = 0
    else:
        run_state = "active"
        active_day_number = (current - start).days + 1
        actual_elapsed_days = max(0, (current - start).days)
        completed_days = min(actual_elapsed_days, scheduled_days)

    return {
        "run_state": run_state,
        "active_day_number": active_day_number,
        "actual_elapsed_calendar_day_count": actual_elapsed_days,
        "paper_operation_day_number": active_day_number,
        "completed_calendar_day_count": completed_days,
        "calendar_days_remaining": max(0, scheduled_days - completed_days),
        "phase7_30_day_run_complete": completed_days >= scheduled_days,
        "legacy_30_day_milestone_complete": completed_days >= scheduled_days,
        "operation_horizon": "indefinite",
    }


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_demo_proof_run_paths(settings)

    artifact = build_phase7_demo_proof_run(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_demo_proof_run(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_demo_proof_run(written)
    runtime_copy = _read_json(output_path)
    replay = EventLog(event_log_path, echo=False).replay()

    missing_day_probe = deepcopy(written)
    missing_day_probe["calendar_day_records"] = missing_day_probe[
        "calendar_day_records"
    ][:-1]
    missing_day_errors = validate_phase7_demo_proof_run(missing_day_probe)

    backfill_probe = deepcopy(written)
    backfill_probe["backfill_used"] = True
    backfill_errors = validate_phase7_demo_proof_run(backfill_probe)

    simulated_time_probe = deepcopy(written)
    simulated_time_probe["simulated_time_used"] = True
    simulated_time_errors = validate_phase7_demo_proof_run(simulated_time_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["no_forced_trades"] = False
    forced_trade_probe["calendar_day_records"][0]["forced_trade_allowed"] = True
    forced_trade_errors = validate_phase7_demo_proof_run(forced_trade_probe)

    no_setup_trade_probe = deepcopy(written)
    no_setup_trade_probe["submitted_paper_order_count"] = 1
    no_setup_trade_probe["closed_proof_trade_count"] = 1
    no_setup_trade_probe["calendar_day_records"][0]["proof_trade_count"] = 1
    no_setup_trade_errors = validate_phase7_demo_proof_run(no_setup_trade_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_demo_proof_run(proof_credit_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_demo_proof_run(live_capital_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["alpaca_post_called_count"] = 1
    broker_errors = validate_phase7_demo_proof_run(broker_probe)

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_demo_proof_run(phase5_reuse_probe)

    print(f"phase7_demo_run_status={written['status']}")
    print(f"phase7_demo_run_state={written['run_state']}")
    print(f"phase7_demo_run_schema_version={PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION}")
    print(f"phase7_demo_run_artifact_path={output_path}")
    print(f"phase7_demo_run_history_path={history_path}")
    print(f"phase7_demo_run_event_log_path={event_log_path}")
    print(f"phase7_demo_run_id={written['run_id']}")
    print(f"phase7_demo_run_start_date={written['start_date']}")
    print(f"phase7_demo_run_end_date={written['end_date']}")
    print(f"phase7_demo_run_active_day_number={written['active_day_number']}")
    print(
        "phase7_demo_run_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
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
        "phase7_demo_run_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "phase7_demo_run_closed_proof_trade_count="
        f"{written['closed_proof_trade_count']}"
    )
    print(f"phase7_demo_run_collection_state={written['collection_state']}")
    print(
        "phase7_demo_run_collection_blockers="
        f"{','.join(written['proof_trade_collection_blockers'])}"
    )
    print(
        "phase7_demo_run_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_demo_run_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_demo_run_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_demo_run_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_demo_run_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_demo_run_event_log_events={replay['total_events']}")
    print(f"phase7_demo_run_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"demo-proof run validation failed: {validation_errors}")
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime artifact did not persist demo-proof run")
    if replay["total_events"] < 1:
        errors.append("demo-proof run event log did not record an event")
    expected_calendar = _expected_calendar_state(written)
    for field, expected_value in expected_calendar.items():
        if written.get(field) != expected_value:
            errors.append(
                "demo-proof run calendar mismatch: "
                f"{field} expected {expected_value} got {written.get(field)}"
            )
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("demo-proof run grants proof credit")
    if written["live_capital_enabled"] is not False:
        errors.append("demo-proof run enables live capital")
    for label, probe_errors in (
        ("missing day", missing_day_errors),
        ("backfill", backfill_errors),
        ("simulated time", simulated_time_errors),
        ("forced trade", forced_trade_errors),
        ("trade without setup", no_setup_trade_errors),
        ("proof credit", proof_credit_errors),
        ("live capital", live_capital_errors),
        ("broker post", broker_errors),
        ("phase5 reuse", phase5_reuse_errors),
    ):
        if not probe_errors:
            errors.append(f"{label} probe was not rejected")

    if errors:
        print("phase7_demo_run_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("phase7_demo_run_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
