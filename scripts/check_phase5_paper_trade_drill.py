#!/usr/bin/env python3
"""Validate the Q5-14 guarded paper trade drill contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    PAPER_TRADE_DRILL_REQUIRED_STEPS,
    PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION,
    build_phase5_paper_trade_drill,
    paper_trade_drill_paths,
    validate_phase5_paper_trade_drill_bundle,
    validate_phase5_paper_trade_drill_step,
    write_phase5_paper_trade_drill,
)


def _first_step(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("no Q5-14 drill step records produced")
    return records[0]


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_trade_drill_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_paper_trade_drill(settings=settings)
    output_path, history_path, event_log_path, written = write_phase5_paper_trade_drill(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_paper_trade_drill_bundle(written)
    replay = EventLog(event_log_path, echo=False).replay()

    first_step = _first_step(written)
    display_mismatch_probe = deepcopy(first_step)
    display_mismatch_probe["display_status"] = "ready"
    display_mismatch_errors = validate_phase5_paper_trade_drill_step(display_mismatch_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase5_paper_trade_drill_bundle(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase5_paper_trade_drill_bundle(live_capital_probe)

    phase7_probe = deepcopy(written)
    phase7_probe["phase7_proof_credit_allowed"] = True
    phase7_errors = validate_phase5_paper_trade_drill_bundle(phase7_probe)

    false_exit_probe = deepcopy(written)
    false_exit_probe["phase5_paper_trade_drill_exit_gate_passed"] = True
    false_exit_errors = validate_phase5_paper_trade_drill_bundle(false_exit_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "ok":
        errors.append("status_not_ok")
    if written["schema_version"] != PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != len(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("event_log_count_not_required_step_count")
    if replay["total_events"] != written["event_log_event_count"]:
        errors.append("event_log_replay_count_mismatch")
    if written["required_step_count"] != len(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("required_step_count_mismatch")
    if written["step_count"] != len(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("step_count_mismatch")
    if written["phase5_paper_trade_drill_implementation_ready"] is not True:
        errors.append("implementation_not_ready")
    if written["paper_submit_approval_present"] is not True:
        if written["phase5_paper_trade_drill_exit_gate_passed"] is not False:
            errors.append("exit_gate_open_without_paper_submit_approval")
        if "paper_submit_approval_missing" not in written["blockers"]:
            errors.append("missing_approval_not_reported")
    if written["paper_submit_path_available_count"] <= 0:
        if "paper_submit_path_unavailable" not in written["blockers"]:
            errors.append("missing_submit_path_not_reported")
    if written["paper_trade_drill_complete"] is True:
        for count_key in (
            "submitted_paper_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(written.get(count_key, 0) or 0) <= 0:
                errors.append(f"complete_drill_missing_{count_key}")
        if written.get("position_open_lifecycle_satisfied") is not True:
            errors.append("complete_drill_missing_position_open_lifecycle")
    else:
        if written["phase5_paper_trade_drill_exit_gate_passed"] is not False:
            errors.append("blocked_drill_exit_gate_open")
    for count_key in (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_monitor_write_authority_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "order_cancel_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if int(written.get(count_key, 0) or 0) != 0:
            errors.append(f"unsafe_count_nonzero:{count_key}")
    if "step_display_backend_mismatch" not in display_mismatch_errors:
        errors.append("display_mismatch_probe_not_rejected")
    if (
        "bundle_unsafe_count_nonzero:broker_post_called_count" not in broker_post_errors
        and "broker_post_before_exit_gate" not in broker_post_errors
    ):
        errors.append("broker_post_probe_not_rejected")
    if "bundle_unsafe_count_nonzero:live_capital_enabled_count" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if "phase7_credit_allowed" not in phase7_errors:
        errors.append("phase7_credit_probe_not_rejected")
    if (
        "exit_gate_without_paper_submit_approval" not in false_exit_errors
        and written["paper_submit_approval_present"] is not True
    ):
        errors.append("false_exit_probe_not_rejected")

    print(f"phase5_paper_trade_drill_status={written['status']}")
    print(
        "phase5_paper_trade_drill_schema_version="
        f"{PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION}"
    )
    print(f"phase5_paper_trade_drill_artifact_path={output_path}")
    print(f"phase5_paper_trade_drill_history_path={history_path}")
    print(f"phase5_paper_trade_drill_event_log_path={event_log_path}")
    print(f"phase5_paper_trade_drill_state={written['paper_trade_drill_state']}")
    print(
        "phase5_paper_trade_drill_complete="
        f"{written['paper_trade_drill_complete']}"
    )
    print(
        "phase5_paper_trade_drill_exit_gate_passed="
        f"{written['phase5_paper_trade_drill_exit_gate_passed']}"
    )
    print(
        "phase5_paper_trade_drill_implementation_ready="
        f"{written['phase5_paper_trade_drill_implementation_ready']}"
    )
    print(f"phase5_paper_trade_drill_step_count={written['step_count']}")
    print(f"phase5_paper_trade_drill_blocker_count={written['blocker_count']}")
    print(
        "phase5_paper_trade_drill_paper_submit_approval_state="
        f"{written['paper_submit_approval_state']}"
    )
    print(
        "phase5_paper_trade_drill_paper_submit_approval_present="
        f"{written['paper_submit_approval_present']}"
    )
    print(
        "phase5_paper_trade_drill_paper_submit_path_available_count="
        f"{written['paper_submit_path_available_count']}"
    )
    print(
        "phase5_paper_trade_drill_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "phase5_paper_trade_drill_open_position_count="
        f"{written['open_position_count']}"
    )
    print(
        "phase5_paper_trade_drill_closed_trade_count="
        f"{written['closed_trade_count']}"
    )
    print(
        "phase5_paper_trade_drill_postmortem_due_count="
        f"{written['postmortem_due_count']}"
    )
    print(
        "phase5_paper_trade_drill_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase5_paper_trade_drill_live_capital_enabled_count="
        f"{written['live_capital_enabled_count']}"
    )
    print(
        "phase5_paper_trade_drill_event_log_written="
        f"{written['event_log_written']}"
    )
    print(
        "phase5_paper_trade_drill_event_log_event_count="
        f"{written['event_log_event_count']}"
    )
    print(
        "phase5_paper_trade_drill_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    if errors:
        for error in sorted(set(errors)):
            print(f"phase5_paper_trade_drill_error={error}")
        return 1
    print("phase5_paper_trade_drill_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
