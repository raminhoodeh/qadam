#!/usr/bin/env python3
"""Validate the PT-9 cockpit and notification upgrade contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_cockpit_notification_upgrade import (  # noqa: E402
    PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION,
    PT9_REQUIRED_NOTIFICATION_TYPES,
    build_paperops_cockpit_notification_upgrade,
    paperops_cockpit_notification_upgrade_paths,
    validate_paperops_cockpit_notification_upgrade,
    write_paperops_cockpit_notification_upgrade,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = (
        paperops_cockpit_notification_upgrade_paths(settings)
    )
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_cockpit_notification_upgrade(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_paperops_cockpit_notification_upgrade(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_paperops_cockpit_notification_upgrade(written)
    replay = EventLog(event_log_path, echo=False).replay()

    missing_type_probe = deepcopy(written)
    missing_type_probe["notification_required_types_present_count"] = max(
        0,
        int(written["notification_required_types_present_count"]) - 1,
    )
    missing_type_probe["notification_missing_required_types"] = [
        PT9_REQUIRED_NOTIFICATION_TYPES[0]
    ]
    missing_type_errors = validate_paperops_cockpit_notification_upgrade(
        missing_type_probe
    )

    live_send_probe = deepcopy(written)
    live_send_probe["notification_live_send_allowed_count"] = 1
    live_send_probe["unsafe_write_counter_total"] = 1
    live_send_errors = validate_paperops_cockpit_notification_upgrade(live_send_probe)

    command_probe = deepcopy(written)
    command_probe["notification_command_path_enabled_count"] = 1
    command_probe["unsafe_write_counter_total"] = 1
    command_errors = validate_paperops_cockpit_notification_upgrade(command_probe)

    broker_probe = deepcopy(written)
    broker_probe["notification_broker_write_allowed_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_paperops_cockpit_notification_upgrade(broker_probe)

    qctrl_probe = deepcopy(written)
    qctrl_probe["active_paper_automation_qctrl_hold"] = True
    qctrl_probe["active_paper_automation_submit_step_allowed"] = True
    qctrl_probe["paper_submit_visible_as_held"] = False
    qctrl_errors = validate_paperops_cockpit_notification_upgrade(qctrl_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_cockpit_notification_upgrade(
        live_capital_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_cockpit_notification_upgrade(proof_probe)

    outbox_probe = deepcopy(written)
    outbox_probe["outbox_message_written_count"] = 1
    outbox_probe["unsafe_write_counter_total"] = 1
    outbox_errors = validate_paperops_cockpit_notification_upgrade(outbox_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_cockpit_notification_upgrade(event_probe)

    print(f"paperops_cockpit_notification_upgrade_status={written['status']}")
    print(
        "paperops_cockpit_notification_upgrade_schema_version="
        f"{PAPEROPS_COCKPIT_NOTIFICATION_UPGRADE_SCHEMA_VERSION}"
    )
    print(f"paperops_cockpit_notification_upgrade_artifact_path={output_path}")
    print(f"paperops_cockpit_notification_upgrade_history_path={history_path}")
    print(f"paperops_cockpit_notification_upgrade_event_log_path={event_log_path}")
    print(
        "paperops_cockpit_notification_upgrade_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_cockpit_ready="
        f"{written['cockpit_upgrade_ready']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_ready="
        f"{written['notification_upgrade_ready']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_readout_count="
        f"{written['fund_manager_readout_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_operations_status="
        f"{written['paperops_30_day_operations_status']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_operations_run_state="
        f"{written['paperops_30_day_operations_run_state']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_operations_command_count="
        f"{written['paperops_30_day_operations_command_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_dashboard_public_safe="
        f"{written['paperops_30_day_operations_dashboard_public_safe']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_active_automation_status="
        f"{written['active_paper_automation_status']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_active_automation_enabled="
        f"{written['active_paper_automation_enabled']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_qctrl_hold_visible="
        f"{written['qctrl_hold_visible']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_submit_visible_as_held="
        f"{written['paper_submit_visible_as_held']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_status="
        f"{written['notification_status']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_record_count="
        f"{written['notification_record_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_required_type_count="
        f"{written['notification_required_type_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_present_type_count="
        f"{written['notification_required_types_present_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_missing_types="
        f"{','.join(written['notification_missing_required_types'])}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_live_send_allowed_count="
        f"{written['notification_live_send_allowed_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_command_path_enabled_count="
        f"{written['notification_command_path_enabled_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_broker_write_allowed_count="
        f"{written['notification_broker_write_allowed_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_notification_paper_order_allowed_count="
        f"{written['notification_paper_order_allowed_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_outbox_message_written_count="
        f"{written['outbox_message_written_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_blocker_count="
        f"{written['blocker_count']}"
    )
    print(
        "paperops_cockpit_notification_upgrade_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(f"paperops_cockpit_notification_upgrade_validation_errors={validation_errors}")
    print(
        "paperops_cockpit_notification_upgrade_missing_type_probe_error_count="
        f"{len(missing_type_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_live_send_probe_error_count="
        f"{len(live_send_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_command_probe_error_count="
        f"{len(command_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_broker_probe_error_count="
        f"{len(broker_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_qctrl_probe_error_count="
        f"{len(qctrl_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_proof_probe_error_count="
        f"{len(proof_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_outbox_probe_error_count="
        f"{len(outbox_errors)}"
    )
    print(
        "paperops_cockpit_notification_upgrade_event_probe_error_count="
        f"{len(event_errors)}"
    )

    if validation_errors:
        errors.extend(validation_errors)
    if replay["total_events"] != 1:
        errors.append("PT-9 event log did not record exactly one event")
    if written["status"] != "cockpit_notification_upgrade_ready":
        errors.append("PT-9 is not cockpit_notification_upgrade_ready")
    if written["cockpit_upgrade_ready"] is not True:
        errors.append("PT-9 cockpit upgrade flag is false")
    if written["notification_upgrade_ready"] is not True:
        errors.append("PT-9 notification upgrade flag is false")
    if written["fund_manager_readout_count"] < 5:
        errors.append("PT-9 readout count is too low")
    if written["notification_required_types_present_count"] != written[
        "notification_required_type_count"
    ]:
        errors.append("PT-9 missing required notification types")
    if written["paperops_30_day_operations_status"] not in {
        "operations_active",
        "invalid",
    }:
        errors.append("PT-9 did not see an active PaperOps-6 operations mirror")
    if written["paperops_30_day_operations_status"] == "invalid" and written[
        "paperops_30_day_operations_run_state"
    ] != "active":
        errors.append("PT-9 self-observer recovery did not see active run state")
    if written["paperops_30_day_operations_dashboard_public_safe"] is not True:
        errors.append("PT-9 did not see public-safe cockpit mirror")
    if written["active_paper_automation_enabled"] is not True:
        errors.append("PT-9 did not see enabled active automation")
    if written["qctrl_hold_visible"] is True and written[
        "paper_submit_visible_as_held"
    ] is not True:
        errors.append("PT-9 did not surface the Q-CTRL submit hold")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("PT-9 unsafe counter is nonzero")
    if "paperops_pt9_notification_required_types_missing" not in missing_type_errors:
        errors.append("missing notification type probe was not rejected")
    if (
        "paperops_pt9_unsafe_counter_nonzero:notification_live_send_allowed_count"
        not in live_send_errors
    ):
        errors.append("live-send probe was not rejected")
    if (
        "paperops_pt9_unsafe_counter_nonzero:notification_command_path_enabled_count"
        not in command_errors
    ):
        errors.append("command probe was not rejected")
    if (
        "paperops_pt9_unsafe_counter_nonzero:notification_broker_write_allowed_count"
        not in broker_errors
    ):
        errors.append("broker-write probe was not rejected")
    if "paperops_pt9_qctrl_hold_bypassed" not in qctrl_errors:
        errors.append("Q-CTRL hold probe was not rejected")
    if "paperops_pt9_live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_pt9_proof_credit_allowed" not in proof_errors:
        errors.append("proof-credit probe was not rejected")
    if (
        "paperops_pt9_unsafe_counter_nonzero:outbox_message_written_count"
        not in outbox_errors
    ):
        errors.append("outbox-write probe was not rejected")
    if "paperops_pt9_event_log_missing" not in event_errors:
        errors.append("event-log probe was not rejected")

    if errors:
        print("paperops_cockpit_notification_upgrade_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_cockpit_notification_upgrade_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
