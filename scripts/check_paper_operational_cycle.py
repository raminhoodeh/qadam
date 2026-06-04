#!/usr/bin/env python3
"""Validate the PaperOps-1 operational cycle runner."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from scripts.run_paper_operational_cycle import (  # noqa: E402
    COMMANDS,
    PAPER_OPS_CYCLE_SCHEMA_VERSION,
    build_paper_operational_cycle,
    validate_paper_operational_cycle,
    write_paper_operational_cycle,
)

ACCEPTED_CYCLE_STATUSES = {
    "paper_cycle_safe_blocked_pending_enablement",
    "paper_cycle_full_paper_operational_ready",
}
ACCEPTED_PAPER_LIVE_CERTIFICATION_STATUSES = {
    "blocked_pending_qctrl_and_phase7_proof",
    "blocked_pending_qctrl",
    "blocked_pending_phase7_proof",
    "blocked_pending_certification_gates",
    "paper_live_certified",
}
FULL_READY_NEXT_STAGES = {
    "PaperOps-4 paper exit path",
    "Phase 7 proof run certification",
}


def _expected_next_stage_for_blockers(blockers: list[str]) -> str:
    if not blockers:
        return "PaperOps-4 paper exit path"
    if "source_spine_available_not_ready" in blockers:
        return "Refresh Phase 1 data spine and durable source mirror"
    if "paper_live_activation_approved_not_ready" in blockers:
        return "PT-0 paper-live activation charter"
    if (
        "global_paper_operational_mode_enabled_not_ready" in blockers
        or "paper_operational_flag_disabled" in blockers
    ):
        return "PT-2 global PaperOps runtime mode enablement"
    if "paperops_30_day_operations_active_not_ready" in blockers:
        return "PaperOps-6 30-day paper operations scheduler binding"
    if "active_paper_trading_automation_connected_not_ready" in blockers:
        return "PT-8 active paper-trading automation binding"
    if "cockpit_notification_upgrade_connected_not_ready" in blockers:
        return "PT-9 cockpit and notification upgrade"
    if "paper_live_certification_gate_connected_not_ready" in blockers:
        return "PT-10 paper-live certification gate"
    if "paperops_auto_approval_staged_order_connected_not_ready" in blockers:
        return "PT-4 auto-approval and staged paper-order handoff"
    if "alpaca_paper_submit_runtime_enablement_connected_not_ready" in blockers:
        return "PT-5 Alpaca paper-submit runtime enablement"
    if "paper_lifecycle_polling_runtime_enablement_connected_not_ready" in blockers:
        return "PT-6 active paper lifecycle polling enablement"
    if "guarded_paper_exit_runtime_enablement_connected_not_ready" in blockers:
        return "PT-7 guarded paper-exit runtime enablement"
    if "qctrl_paper_consultation_connected_not_ready" in blockers:
        return "Resolve PaperOps-Q Q-CTRL product access for successful paper consultation"
    if "external_alpaca_paper_post_enabled_not_ready" in blockers:
        return "PaperOps-2 explicit Alpaca paper POST gate"
    return "PaperOps-4 paper exit path"


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_paper_operational_cycle(settings)
    output_path, history_path, event_path, written = write_paper_operational_cycle(
        artifact,
        settings,
    )
    validation_errors = validate_paper_operational_cycle(written)
    replay = EventLog(event_path, echo=False).replay()
    idle_bridge = written.get("rs10_idle_wait_bridge_applied") is True

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paper_operational_cycle(live_capital_probe)

    paper_live_submit_probe = deepcopy(written)
    paper_live_submit_probe["paper_live_activation_paper_order_submission_allowed"] = True
    paper_live_submit_errors = validate_paper_operational_cycle(paper_live_submit_probe)

    paper_live_broker_probe = deepcopy(written)
    paper_live_broker_probe["paper_live_activation_broker_post_called_count"] = 1
    paper_live_broker_probe["unsafe_write_counter_total"] = 1
    paper_live_broker_errors = validate_paper_operational_cycle(paper_live_broker_probe)

    paper_live_qctrl_probe = deepcopy(written)
    paper_live_qctrl_probe["paper_live_activation_qctrl_direct_execution_allowed"] = True
    paper_live_qctrl_errors = validate_paper_operational_cycle(paper_live_qctrl_probe)

    pt1_qctrl_authority_probe = deepcopy(written)
    pt1_qctrl_authority_probe["paper_live_qctrl_execution_allowed"] = True
    pt1_qctrl_authority_probe["paper_live_qctrl_broker_post_allowed"] = True
    pt1_qctrl_authority_errors = validate_paper_operational_cycle(
        pt1_qctrl_authority_probe
    )

    pt1_qctrl_counter_probe = deepcopy(written)
    pt1_qctrl_counter_probe["paper_live_qctrl_broker_post_called_count"] = 1
    pt1_qctrl_counter_probe["unsafe_write_counter_total"] = 1
    pt1_qctrl_counter_errors = validate_paper_operational_cycle(pt1_qctrl_counter_probe)

    pt2_mode_probe = deepcopy(written)
    pt2_mode_probe["paper_operational_mode_effective"] = False
    pt2_mode_errors = validate_paper_operational_cycle(pt2_mode_probe)

    pt2_broker_probe = deepcopy(written)
    pt2_broker_probe["paper_operational_mode_broker_post_called_count"] = 1
    pt2_broker_probe["unsafe_write_counter_total"] = 1
    pt2_broker_errors = validate_paper_operational_cycle(pt2_broker_probe)

    pt2_submit_probe = deepcopy(written)
    pt2_submit_probe["paper_operational_mode_paper_order_submission_allowed"] = True
    pt2_submit_errors = validate_paper_operational_cycle(pt2_submit_probe)

    qualified_setup_broker_probe = deepcopy(written)
    qualified_setup_broker_probe["qualified_setup_production_broker_post_called_count"] = 1
    qualified_setup_broker_probe["unsafe_write_counter_total"] = 1
    qualified_setup_broker_errors = validate_paper_operational_cycle(
        qualified_setup_broker_probe
    )

    qualified_setup_missing_probe = deepcopy(written)
    qualified_setup_missing_probe["qualified_setup_production_path_ready"] = False
    qualified_setup_missing_errors = validate_paper_operational_cycle(
        qualified_setup_missing_probe
    )

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["alpaca_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 2
    broker_errors = validate_paper_operational_cycle(broker_probe)

    alpaca_live_endpoint_probe = deepcopy(written)
    alpaca_live_endpoint_probe["alpaca_paper_post_live_endpoint_called_count"] = 1
    alpaca_live_endpoint_probe["unsafe_write_counter_total"] = 1
    alpaca_live_endpoint_errors = validate_paper_operational_cycle(alpaca_live_endpoint_probe)

    lifecycle_poller_probe = deepcopy(written)
    lifecycle_poller_probe["paper_lifecycle_poller_live_endpoint_called_count"] = 1
    lifecycle_poller_probe["paper_lifecycle_poller_broker_post_called_count"] = 1
    lifecycle_poller_probe["unsafe_write_counter_total"] = 2
    lifecycle_poller_errors = validate_paper_operational_cycle(lifecycle_poller_probe)

    lifecycle_polling_enablement_probe = deepcopy(written)
    lifecycle_polling_enablement_probe[
        "lifecycle_polling_enablement_live_endpoint_called_count"
    ] = 1
    lifecycle_polling_enablement_probe["unsafe_write_counter_total"] = 1
    lifecycle_polling_enablement_errors = validate_paper_operational_cycle(
        lifecycle_polling_enablement_probe
    )

    guarded_exit_enablement_probe = deepcopy(written)
    guarded_exit_enablement_probe["guarded_exit_enablement_close_called_count"] = 1
    guarded_exit_enablement_probe["guarded_exit_enablement_live_endpoint_called_count"] = 1
    guarded_exit_enablement_probe["unsafe_write_counter_total"] = 2
    guarded_exit_enablement_errors = validate_paper_operational_cycle(
        guarded_exit_enablement_probe
    )

    active_automation_probe = deepcopy(written)
    active_automation_probe["active_paper_automation_live_endpoint_called_count"] = 1
    active_automation_probe["active_paper_automation_unsafe_write_counter_total"] = 1
    active_automation_probe["unsafe_write_counter_total"] = 2
    active_automation_errors = validate_paper_operational_cycle(
        active_automation_probe
    )

    active_automation_qctrl_probe = deepcopy(written)
    active_automation_qctrl_probe["active_paper_automation_qctrl_hold"] = True
    active_automation_qctrl_probe["active_paper_automation_submit_step_allowed"] = True
    active_automation_qctrl_errors = validate_paper_operational_cycle(
        active_automation_qctrl_probe
    )

    exit_path_probe = deepcopy(written)
    exit_path_probe["paper_exit_path_live_endpoint_called_count"] = 1
    exit_path_probe["paper_exit_path_broker_post_called_count"] = 1
    exit_path_probe["paper_exit_path_order_cancel_called_count"] = 1
    exit_path_probe["unsafe_write_counter_total"] = 3
    exit_path_errors = validate_paper_operational_cycle(exit_path_probe)

    notification_probe = deepcopy(written)
    notification_probe["notification_review_live_send_allowed_count"] = 1
    notification_probe["notification_review_command_path_enabled_count"] = 1
    notification_probe["notification_review_broker_write_allowed_count"] = 1
    notification_probe["unsafe_write_counter_total"] = 3
    notification_errors = validate_paper_operational_cycle(notification_probe)

    cockpit_notification_probe = deepcopy(written)
    cockpit_notification_probe["cockpit_notification_upgrade_live_send_allowed_count"] = 1
    cockpit_notification_probe["cockpit_notification_upgrade_unsafe_write_counter_total"] = 1
    cockpit_notification_probe["unsafe_write_counter_total"] = 2
    cockpit_notification_errors = validate_paper_operational_cycle(
        cockpit_notification_probe
    )

    cockpit_notification_qctrl_probe = deepcopy(written)
    cockpit_notification_qctrl_probe[
        "cockpit_notification_upgrade_qctrl_hold_visible"
    ] = True
    cockpit_notification_qctrl_probe[
        "cockpit_notification_upgrade_submit_visible_as_held"
    ] = False
    cockpit_notification_qctrl_errors = validate_paper_operational_cycle(
        cockpit_notification_qctrl_probe
    )

    paper_live_certification_probe = deepcopy(written)
    paper_live_certification_probe[
        "paper_live_certification_unsafe_write_counter_total"
    ] = 1
    paper_live_certification_probe["unsafe_write_counter_total"] = 1
    paper_live_certification_errors = validate_paper_operational_cycle(
        paper_live_certification_probe
    )

    paper_live_certification_false_probe = deepcopy(written)
    paper_live_certification_false_probe[
        "paper_live_certification_paper_live_certified"
    ] = True
    paper_live_certification_false_probe[
        "paper_live_certification_operation_allowed"
    ] = True
    paper_live_certification_false_probe[
        "paper_live_certification_unattended_delegation_enabled"
    ] = True
    paper_live_certification_false_probe[
        "paper_live_certification_blocker_count"
    ] = 1
    paper_live_certification_false_errors = validate_paper_operational_cycle(
        paper_live_certification_false_probe
    )

    operations_probe = deepcopy(written)
    operations_probe["paperops_30_day_operations_unsafe_write_counter_total"] = 1
    operations_probe["unsafe_write_counter_total"] = 1
    operations_errors = validate_paper_operational_cycle(operations_probe)

    qctrl_probe = deepcopy(written)
    qctrl_probe["qctrl_provider_call_count"] = 1
    qctrl_probe["qctrl_paper_consultation_provider_call_recorded"] = False
    qctrl_errors = validate_paper_operational_cycle(qctrl_probe)

    failed_command_probe = deepcopy(written)
    failed_command_probe["command_failed_count"] = 1
    failed_command_probe["command_passed_count"] = max(0, written["command_passed_count"] - 1)
    failed_command_probe["failed_commands"] = ["probe_failed_command"]
    failed_command_errors = validate_paper_operational_cycle(failed_command_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paper_operational_cycle(event_probe)

    print(f"paper_ops_cycle_check_status={written['status']}")
    print(f"paper_ops_cycle_check_schema_version={PAPER_OPS_CYCLE_SCHEMA_VERSION}")
    print(f"paper_ops_cycle_check_artifact_path={output_path}")
    print(f"paper_ops_cycle_check_history_path={history_path}")
    print(f"paper_ops_cycle_check_event_log_path={event_path}")
    print(f"paper_ops_cycle_check_stage={written['stage']}")
    print(f"paper_ops_cycle_check_command_count={written['command_count']}")
    print(f"paper_ops_cycle_check_command_passed_count={written['command_passed_count']}")
    print(f"paper_ops_cycle_check_command_failed_count={written['command_failed_count']}")
    print(
        "paper_ops_cycle_check_paper_live_activation_status="
        f"{written['paper_live_activation_status']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_activation_approved="
        f"{written['paper_live_activation_approved']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_activation_system_approval_logged="
        f"{written['paper_live_activation_system_approval_logged']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_activation_submit_allowed="
        f"{written['paper_live_activation_paper_order_submission_allowed']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_product_access_status="
        f"{written['paper_live_qctrl_product_access_status']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_product_access_verified="
        f"{written['paper_live_qctrl_product_access_verified']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_provider_call_attempted="
        f"{written['paper_live_qctrl_provider_call_attempted']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_provider_call_succeeded="
        f"{written['paper_live_qctrl_provider_call_succeeded']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_provider_call_count="
        f"{written['paper_live_qctrl_provider_call_count']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_qctrl_product_access_blocker="
        f"{written['paper_live_qctrl_product_access_blocker']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_status="
        f"{written['paper_operational_mode_status']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_enabled="
        f"{written['paper_operational_mode_enabled']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_effective="
        f"{written['paper_operational_mode_effective']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_settings_flag="
        f"{written['paper_operational_mode_settings_flag']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_runtime_artifact_override_enabled="
        f"{written['paper_operational_mode_runtime_artifact_override_enabled']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_flag_disabled="
        f"{written['paper_operational_mode_flag_disabled']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_paper_order_submission_allowed="
        f"{written['paper_operational_mode_paper_order_submission_allowed']}"
    )
    print(
        "paper_ops_cycle_check_paper_operational_mode_broker_post_called_count="
        f"{written['paper_operational_mode_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_status="
        f"{written['qualified_setup_production_status']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_path_ready="
        f"{written['qualified_setup_production_path_ready']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_candidate_count="
        f"{written['qualified_setup_production_candidate_count']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_qualified_setup_count="
        f"{written['qualified_setup_production_qualified_setup_count']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_ready_to_stage_q7_order="
        f"{written['qualified_setup_production_ready_to_stage_q7_order']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_qctrl_status="
        f"{written['qualified_setup_production_qctrl_status']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_broker_post_called_count="
        f"{written['qualified_setup_production_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_check_qualified_setup_production_unsafe_write_counter_total="
        f"{written['qualified_setup_production_unsafe_write_counter_total']}"
    )
    print(f"paper_ops_cycle_check_safe_to_continue_paper_only={written['safe_to_continue_paper_only']}")
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_status="
        f"{written['lifecycle_polling_enablement_status']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_active="
        f"{written['lifecycle_polling_enablement_active']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_path_available="
        f"{written['lifecycle_polling_enablement_path_available']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_submitted_order_count="
        f"{written['lifecycle_polling_enablement_paperops2_submitted_order_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_poller_order_poll_called_count="
        f"{written['lifecycle_polling_enablement_poller_order_poll_called_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_polling_enablement_live_endpoint_called_count="
        f"{written['lifecycle_polling_enablement_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_status="
        f"{written['guarded_exit_enablement_status']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_enabled="
        f"{written['guarded_exit_enablement_enabled']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_effective="
        f"{written['guarded_exit_enablement_effective']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_path_available="
        f"{written['guarded_exit_enablement_path_available']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_open_position_count="
        f"{written['guarded_exit_enablement_open_position_count']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_close_called_count="
        f"{written['guarded_exit_enablement_close_called_count']}"
    )
    print(
        "paper_ops_cycle_check_guarded_exit_enablement_live_endpoint_called_count="
        f"{written['guarded_exit_enablement_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_status="
        f"{written['active_paper_automation_status']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_enabled="
        f"{written['active_paper_automation_enabled']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_prompt_bound="
        f"{written['active_paper_automation_prompt_bound']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_qctrl_hold="
        f"{written['active_paper_automation_qctrl_hold']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_submit_step_allowed="
        f"{written['active_paper_automation_submit_step_allowed']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_poll_step_allowed="
        f"{written['active_paper_automation_poll_step_allowed']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_exit_step_allowed="
        f"{written['active_paper_automation_exit_step_allowed']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_live_endpoint_called_count="
        f"{written['active_paper_automation_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_active_paper_automation_unsafe_write_counter_total="
        f"{written['active_paper_automation_unsafe_write_counter_total']}"
    )
    print(f"paper_ops_cycle_check_full_paper_operational_ready={written['full_paper_operational_ready']}")
    print(f"paper_ops_cycle_check_blocker_count={written['blocker_count']}")
    print(f"paper_ops_cycle_check_blockers={','.join(written['blockers'])}")
    print(f"paper_ops_cycle_check_hard_safety_failure_count={written['hard_safety_failure_count']}")
    print(f"paper_ops_cycle_check_qualified_setup_count={written['qualified_setup_count']}")
    print(f"paper_ops_cycle_check_submitted_paper_order_count={written['submitted_paper_order_count']}")
    print(f"paper_ops_cycle_check_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"paper_ops_cycle_check_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paper_ops_cycle_check_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(
        "paper_ops_cycle_check_alpaca_paper_post_gate_status="
        f"{written['alpaca_paper_post_gate_status']}"
    )
    print(
        "paper_ops_cycle_check_alpaca_paper_post_called_count="
        f"{written['alpaca_paper_post_called_count']}"
    )
    print(
        "paper_ops_cycle_check_alpaca_paper_post_live_endpoint_called_count="
        f"{written['alpaca_paper_post_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_status="
        f"{written['paper_lifecycle_poller_status']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_source_submitted_order_count="
        f"{written['paper_lifecycle_poller_source_submitted_paper_order_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_order_poll_called_count="
        f"{written['paper_lifecycle_poller_order_poll_called_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_broker_get_called_count="
        f"{written['paper_lifecycle_poller_broker_get_called_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_broker_post_called_count="
        f"{written['paper_lifecycle_poller_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_check_lifecycle_poller_live_endpoint_called_count="
        f"{written['paper_lifecycle_poller_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_status="
        f"{written['paper_exit_path_status']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_open_position_readback_count="
        f"{written['paper_exit_path_open_position_readback_count']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_close_called_count="
        f"{written['paper_exit_path_close_called_count']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_broker_write_called_count="
        f"{written['paper_exit_path_broker_write_called_count']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_broker_post_called_count="
        f"{written['paper_exit_path_broker_post_called_count']}"
    )
    print(
        "paper_ops_cycle_check_exit_path_live_endpoint_called_count="
        f"{written['paper_exit_path_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_cycle_check_notification_review_status="
        f"{written['notification_review_status']}"
    )
    print(
        "paper_ops_cycle_check_notification_review_record_count="
        f"{written['notification_review_record_count']}"
    )
    print(
        "paper_ops_cycle_check_notification_review_live_send_allowed_count="
        f"{written['notification_review_live_send_allowed_count']}"
    )
    print(
        "paper_ops_cycle_check_notification_review_command_path_enabled_count="
        f"{written['notification_review_command_path_enabled_count']}"
    )
    print(
        "paper_ops_cycle_check_notification_review_broker_write_allowed_count="
        f"{written['notification_review_broker_write_allowed_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_status="
        f"{written['cockpit_notification_upgrade_status']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_ready="
        f"{written['cockpit_notification_upgrade_ready']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_notification_ready="
        f"{written['cockpit_notification_upgrade_notification_ready']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_readout_count="
        f"{written['cockpit_notification_upgrade_readout_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_notification_record_count="
        f"{written['cockpit_notification_upgrade_notification_record_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_qctrl_hold_visible="
        f"{written['cockpit_notification_upgrade_qctrl_hold_visible']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_submit_visible_as_held="
        f"{written['cockpit_notification_upgrade_submit_visible_as_held']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_live_send_allowed_count="
        f"{written['cockpit_notification_upgrade_live_send_allowed_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_command_path_enabled_count="
        f"{written['cockpit_notification_upgrade_command_path_enabled_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_broker_write_allowed_count="
        f"{written['cockpit_notification_upgrade_broker_write_allowed_count']}"
    )
    print(
        "paper_ops_cycle_check_cockpit_notification_upgrade_unsafe_write_counter_total="
        f"{written['cockpit_notification_upgrade_unsafe_write_counter_total']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_status="
        f"{written['paper_live_certification_status']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_control_plane_certified="
        f"{written['paper_live_certification_control_plane_certified']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_paper_live_certified="
        f"{written['paper_live_certification_paper_live_certified']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_operation_allowed="
        f"{written['paper_live_certification_operation_allowed']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_unattended_delegation_enabled="
        f"{written['paper_live_certification_unattended_delegation_enabled']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_unattended_delegation_reason="
        f"{written['paper_live_certification_unattended_delegation_reason']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_blocker_count="
        f"{written['paper_live_certification_blocker_count']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_qctrl_hold_visible="
        f"{written['paper_live_certification_qctrl_hold_visible']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_submit_visible_as_held="
        f"{written['paper_live_certification_submit_visible_as_held']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_phase7_30_day_run_complete="
        f"{written['paper_live_certification_phase7_30_day_run_complete']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_phase7_demo_proof_certified="
        f"{written['paper_live_certification_phase7_demo_proof_certified']}"
    )
    print(
        "paper_ops_cycle_check_paper_live_certification_unsafe_write_counter_total="
        f"{written['paper_live_certification_unsafe_write_counter_total']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_status="
        f"{written['paperops_30_day_operations_status']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_scheduler_status="
        f"{written['paperops_30_day_operations_scheduler_status']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_automation_active="
        f"{written['paperops_30_day_operations_automation_active']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_automation_prompt_paperops_bound="
        f"{written['paperops_30_day_operations_automation_prompt_paperops_bound']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_cycle_command_count="
        f"{written['paperops_30_day_operations_cycle_command_count']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_dashboard_mirror_public_safe="
        f"{written['paperops_30_day_operations_dashboard_mirror_public_safe']}"
    )
    print(
        "paper_ops_cycle_check_paperops_30_day_operations_unsafe_write_counter_total="
        f"{written['paperops_30_day_operations_unsafe_write_counter_total']}"
    )
    print(
        "paper_ops_cycle_check_qctrl_paper_consultation_status="
        f"{written['qctrl_paper_consultation_status']}"
    )
    print(
        "paper_ops_cycle_check_qctrl_paper_consultation_provider_call_recorded="
        f"{written['qctrl_paper_consultation_provider_call_recorded']}"
    )
    print(f"paper_ops_cycle_check_qctrl_provider_call_count={written['qctrl_provider_call_count']}")
    print(f"paper_ops_cycle_check_recommended_next_stage={written['recommended_next_stage']}")
    print(f"paper_ops_cycle_check_rs10_idle_wait_bridge_applied={idle_bridge}")
    print(
        "paper_ops_cycle_check_rs10_final_paper_autonomy_status="
        f"{written.get('rs10_final_paper_autonomy_status')}"
    )
    print(f"paper_ops_cycle_check_event_log_events={replay['total_events']}")
    print(f"paper_ops_cycle_check_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"cycle validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("cycle event log did not record exactly one event")
    if written["status"] not in ACCEPTED_CYCLE_STATUSES:
        errors.append("unexpected current PaperOps-1 status")
    if written["full_paper_operational_ready"] is True:
        if written["status"] != "paper_cycle_full_paper_operational_ready":
            errors.append("PaperOps-1 full readiness did not use the full-ready status")
        if written["blocker_count"] != 0:
            errors.append("PaperOps-1 full readiness still has blockers")
    elif written["status"] != "paper_cycle_safe_blocked_pending_enablement":
        errors.append("PaperOps-1 is neither full-ready nor safely blocked")
    if written["command_count"] != len(COMMANDS) or written["command_passed_count"] != len(
        COMMANDS
    ):
        errors.append(f"PaperOps-1 runner did not pass all {len(COMMANDS)} commands")
    if written["safe_to_continue_paper_only"] is not True:
        errors.append("PaperOps-1 is not safe to continue in paper-only mode")
    if written["paper_live_activation_approved"] is not True:
        errors.append("PaperOps-1 did not record PT-0 paper-live approval")
    if written["paper_live_activation_system_approval_logged"] is not True:
        errors.append("PaperOps-1 did not log PT-0 system approval")
    if written["paper_live_activation_paper_order_submission_allowed"] is not False:
        errors.append("PaperOps-1 opened paper submit through PT-0")
    if written["paper_live_activation_qctrl_direct_execution_allowed"] is not False:
        errors.append("PaperOps-1 gave Q-CTRL execution authority through PT-0")
    if written["paper_live_qctrl_provider_call_attempted"] is not True:
        errors.append("PaperOps-1 did not include PT-1 provider-call attempt")
    if written["paper_live_qctrl_provider_call_count"] < 1:
        errors.append("PaperOps-1 did not include PT-1 provider-call count")
    if written["paper_live_qctrl_execution_allowed"] is not False:
        errors.append("PaperOps-1 gave execution authority through PT-1")
    if written["paper_live_qctrl_broker_post_allowed"] is not False:
        errors.append("PaperOps-1 gave broker authority through PT-1")
    if written["paper_live_qctrl_phase7_proof_credit_allowed"] is not False:
        errors.append("PaperOps-1 granted proof credit through PT-1")
    if written["paper_operational_mode_status"] != "enabled_pending_downstream_gates":
        errors.append("PaperOps-1 did not include PT-2 operational mode")
    if written["paper_operational_mode_effective"] is not True:
        errors.append("PaperOps-1 did not make PT-2 mode effective")
    if written["paper_operational_mode_flag_disabled"] is not False:
        errors.append("PaperOps-1 still sees disabled PT-2 mode")
    if written["paper_operational_mode_paper_order_submission_allowed"] is not False:
        errors.append("PaperOps-1 opened paper submit through PT-2")
    if written["paper_operational_mode_broker_post_called_count"] != 0:
        errors.append("PaperOps-1 called broker POST through PT-2")
    if written["qualified_setup_production_status"] not in {
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
    }:
        errors.append("PaperOps-1 did not include ready PT-3 production path")
    if written["qualified_setup_production_path_ready"] is not True:
        errors.append("PaperOps-1 did not see PT-3 production path ready")
    if written["qualified_setup_production_candidate_count"] < 1:
        errors.append("PaperOps-1 did not see PT-3 candidates")
    if written["qualified_setup_production_phase7_demo_qualified_setup_count"] != 0:
        errors.append("PaperOps-1 saw PT-3 mutate Phase 7 demo setup count")
    if written["qualified_setup_production_q7_ledger_count"] != 0:
        errors.append("PaperOps-1 saw PT-3 mutate Q7 ledger")
    if written["qualified_setup_production_broker_post_called_count"] != 0:
        errors.append("PaperOps-1 called broker POST through PT-3")
    lifecycle_statuses = {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }
    if idle_bridge:
        lifecycle_statuses.add("blocked_pending_prerequisites")
    if written["lifecycle_polling_enablement_status"] not in lifecycle_statuses:
        errors.append("PaperOps-1 did not include PT-6 lifecycle polling enablement")
    if written["lifecycle_polling_enablement_active"] is not True and not idle_bridge:
        errors.append("PaperOps-1 did not activate PT-6 lifecycle polling")
    if written["lifecycle_polling_enablement_effective"] is not True and not idle_bridge:
        errors.append("PaperOps-1 did not make PT-6 lifecycle polling effective")
    if (
        written["lifecycle_polling_enablement_paperops2_submitted_order_count"] == 0
        and written["lifecycle_polling_enablement_path_available"] is not False
    ):
        errors.append("PaperOps-1 exposed PT-6 poll path with no submitted paper order")
    if written["lifecycle_polling_enablement_broker_get_called_count"] != 0:
        errors.append("PaperOps-1 called broker GET directly through PT-6 enablement")
    if written["lifecycle_polling_enablement_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called live endpoint through PT-6")
    exit_statuses = {
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
    }
    if idle_bridge:
        exit_statuses.add("blocked_lifecycle_polling_enablement_not_ready")
    if written["guarded_exit_enablement_status"] not in exit_statuses:
        errors.append("PaperOps-1 did not include PT-7 guarded exit enablement")
    if written["guarded_exit_enablement_enabled"] is not True and not idle_bridge:
        errors.append("PaperOps-1 did not activate PT-7 guarded exit enablement")
    if written["guarded_exit_enablement_effective"] is not True and not idle_bridge:
        errors.append("PaperOps-1 did not make PT-7 guarded exit effective")
    if (
        written["guarded_exit_enablement_open_position_count"] == 0
        and written["guarded_exit_enablement_path_available"] is not False
    ):
        errors.append("PaperOps-1 exposed PT-7 exit path with no open position")
    if written["guarded_exit_enablement_close_called_count"] != 0:
        errors.append("PaperOps-1 closed a paper position through PT-7 enablement")
    if written["guarded_exit_enablement_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called live endpoint through PT-7")
    if written["active_paper_automation_status"] not in {
        "active_automation_enabled_idle",
        "active_automation_enabled_qctrl_hold",
        "active_automation_ready_to_submit",
        "active_automation_ready_to_poll",
        "active_automation_ready_to_exit",
    }:
        errors.append("PaperOps-1 did not include PT-8 active automation")
    if written["active_paper_automation_enabled"] is not True:
        errors.append("PaperOps-1 did not enable PT-8 active paper automation")
    if written["active_paper_automation_prompt_bound"] is not True:
        errors.append("PaperOps-1 saw PT-8 automation prompt unbound")
    if (
        written["active_paper_automation_qctrl_hold"] is True
        and written["active_paper_automation_submit_step_allowed"] is True
    ):
        errors.append("PaperOps-1 allowed PT-8 submit under Q-CTRL hold")
    if written["active_paper_automation_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called live endpoint through PT-8")
    if written["active_paper_automation_unsafe_write_counter_total"] != 0:
        errors.append("PaperOps-1 saw nonzero PT-8 unsafe counter")
    if (
        written["full_paper_operational_ready"] is False
        and written["blocker_count"] == 0
    ):
        errors.append("PaperOps-1 is not full-ready but has no blockers")
    if written["broker_post_called_count"] != 0 or written["alpaca_post_called_count"] != 0:
        errors.append("PaperOps-1 called broker/Alpaca POST")
    if written["alpaca_paper_post_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called a live endpoint through PaperOps-2")
    if written["paper_lifecycle_poller_broker_post_called_count"] != 0:
        errors.append("PaperOps-1 called broker POST through PaperOps-3")
    if written["paper_lifecycle_poller_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called live endpoint through PaperOps-3")
    if written["paper_exit_path_close_called_count"] != 0:
        errors.append("PaperOps-1 closed a paper position through PaperOps-4")
    if written["paper_exit_path_broker_post_called_count"] != 0:
        errors.append("PaperOps-1 called broker POST through PaperOps-4")
    if written["paper_exit_path_live_endpoint_called_count"] != 0:
        errors.append("PaperOps-1 called live endpoint through PaperOps-4")
    if written["notification_review_live_send_allowed_count"] != 0:
        errors.append("PaperOps-1 allowed live Telegram send through PaperOps-5")
    if written["notification_review_command_path_enabled_count"] != 0:
        errors.append("PaperOps-1 enabled Telegram command path through PaperOps-5")
    if written["notification_review_broker_write_allowed_count"] != 0:
        errors.append("PaperOps-1 allowed broker write through PaperOps-5")
    if written["cockpit_notification_upgrade_status"] != "cockpit_notification_upgrade_ready":
        errors.append("PaperOps-1 did not include ready PT-9 cockpit notification upgrade")
    if written["cockpit_notification_upgrade_ready"] is not True:
        errors.append("PaperOps-1 saw PT-9 cockpit upgrade not ready")
    if written["cockpit_notification_upgrade_notification_ready"] is not True:
        errors.append("PaperOps-1 saw PT-9 notification upgrade not ready")
    if written["cockpit_notification_upgrade_readout_count"] < 5:
        errors.append("PaperOps-1 saw PT-9 readouts missing")
    if (
        written["cockpit_notification_upgrade_qctrl_hold_visible"] is True
        and written["cockpit_notification_upgrade_submit_visible_as_held"] is not True
    ):
        errors.append("PaperOps-1 saw PT-9 hide the Q-CTRL submit hold")
    if written["cockpit_notification_upgrade_unsafe_write_counter_total"] != 0:
        errors.append("PaperOps-1 saw nonzero PT-9 unsafe counter")
    if written["paper_live_certification_status"] not in (
        ACCEPTED_PAPER_LIVE_CERTIFICATION_STATUSES
    ):
        errors.append("PaperOps-1 did not include evaluated PT-10 certification")
    if written["paper_live_certification_control_plane_certified"] is not True:
        errors.append("PaperOps-1 saw PT-10 control plane not certified")
    if written["paper_live_certification_paper_live_certified"] is True:
        if written["paper_live_certification_operation_allowed"] is not True:
            errors.append("PaperOps-1 saw PT-10 certify without paper operation")
        if written["paper_live_certification_unattended_delegation_enabled"] is not True:
            errors.append("PaperOps-1 saw PT-10 certify without unattended delegation")
        if written["paper_live_certification_blocker_count"] != 0:
            errors.append("PaperOps-1 saw PT-10 certify with blockers")
    else:
        if written["paper_live_certification_operation_allowed"] is not False:
            errors.append("PaperOps-1 saw PT-10 allow operation while blocked")
        if written["paper_live_certification_unattended_delegation_enabled"] is not False:
            errors.append("PaperOps-1 saw PT-10 arm unattended delegation while blocked")
        if written["paper_live_certification_blocker_count"] < 1:
            errors.append("PaperOps-1 saw PT-10 blockers missing")
    if (
        written["paper_live_certification_qctrl_hold_visible"] is True
        and written["paper_live_certification_submit_visible_as_held"] is not True
    ):
        errors.append("PaperOps-1 saw PT-10 hide the Q-CTRL submit hold")
    if written["paper_live_certification_unsafe_write_counter_total"] != 0:
        errors.append("PaperOps-1 saw nonzero PT-10 unsafe counter")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "paper_live_certification_unsafe_write_counter_total"
        not in paper_live_certification_errors
    ):
        errors.append("PaperOps-1 PT-10 unsafe probe was not rejected")
    if (
        "paper_ops_cycle_paper_live_certified_with_blockers"
        not in paper_live_certification_false_errors
    ):
        errors.append("PaperOps-1 PT-10 certified-with-blockers probe was not rejected")
    if (
        written["paperops_30_day_operations_status"] != "operations_active"
        and not (
            idle_bridge
            and written["paperops_30_day_operations_status"] == "invalid"
        )
    ):
        errors.append("PaperOps-1 did not include active PaperOps-6 operations")
    if written["paperops_30_day_operations_automation_active"] is not True:
        errors.append("PaperOps-1 saw inactive PaperOps-6 automation")
    if written["paperops_30_day_operations_automation_prompt_paperops_bound"] is not True:
        errors.append("PaperOps-1 saw unbound PaperOps-6 automation prompt")
    if written["paperops_30_day_operations_dashboard_mirror_public_safe"] is not True:
        errors.append("PaperOps-1 saw unsafe PaperOps-6 dashboard mirror")
    if written["paperops_30_day_operations_unsafe_write_counter_total"] != 0:
        errors.append("PaperOps-1 saw nonzero PaperOps-6 unsafe counter")
    if written["qctrl_provider_call_count"] and not written[
        "qctrl_paper_consultation_provider_call_recorded"
    ]:
        errors.append("PaperOps-1 has an unrecorded Q-CTRL provider call")
    if written["full_paper_operational_ready"] is True:
        if written["recommended_next_stage"] not in FULL_READY_NEXT_STAGES:
            errors.append("PaperOps-1 full-ready next step is not a paper exit/proof step")
    elif written["recommended_next_stage"] != _expected_next_stage_for_blockers(
        written["blockers"]
    ):
        errors.append("PaperOps-1 did not route next unblock to the current blocker")
    if written["hard_safety_failure_count"] != 0:
        errors.append("PaperOps-1 has hard safety failures")
    if "paper_ops_cycle_live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if (
        "paper_ops_cycle_paper_live_activation_submit_authority"
        not in paper_live_submit_errors
    ):
        errors.append("paper-live submit-authority probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "paper_live_activation_broker_post_called_count"
        not in paper_live_broker_errors
    ):
        errors.append("paper-live broker-POST probe was not rejected")
    if (
        "paper_ops_cycle_paper_live_activation_qctrl_execution_authority"
        not in paper_live_qctrl_errors
    ):
        errors.append("paper-live Q-CTRL execution probe was not rejected")
    if (
        "paper_ops_cycle_paper_live_qctrl_forbidden:"
        "paper_live_qctrl_execution_allowed"
        not in pt1_qctrl_authority_errors
    ):
        errors.append("PT-1 Q-CTRL execution-authority probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "paper_live_qctrl_broker_post_called_count"
        not in pt1_qctrl_counter_errors
    ):
        errors.append("PT-1 Q-CTRL broker-counter probe was not rejected")
    if (
        "paper_ops_cycle_paper_operational_mode_not_effective"
        not in pt2_mode_errors
    ):
        errors.append("PT-2 mode-disabled probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "paper_operational_mode_broker_post_called_count"
        not in pt2_broker_errors
    ):
        errors.append("PT-2 broker-counter probe was not rejected")
    if (
        "paper_ops_cycle_paper_operational_mode_forbidden:"
        "paper_operational_mode_paper_order_submission_allowed"
        not in pt2_submit_errors
    ):
        errors.append("PT-2 submit-authority probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "qualified_setup_production_broker_post_called_count"
        not in qualified_setup_broker_errors
    ):
        errors.append("PT-3 broker-counter probe was not rejected")
    if (
        "paper_ops_cycle_qualified_setup_production_path_not_ready"
        not in qualified_setup_missing_errors
    ):
        errors.append("PT-3 missing-path probe was not rejected")
    if "paper_ops_cycle_unsafe_counter_nonzero:broker_post_called_count" not in broker_errors:
        errors.append("broker POST probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:alpaca_paper_post_live_endpoint_called_count"
        not in alpaca_live_endpoint_errors
    ):
        errors.append("Alpaca live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:paper_lifecycle_poller_live_endpoint_called_count"
        not in lifecycle_poller_errors
    ):
        errors.append("PaperOps lifecycle poller live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:paper_lifecycle_poller_broker_post_called_count"
        not in lifecycle_poller_errors
    ):
        errors.append("PaperOps lifecycle poller broker-POST probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "lifecycle_polling_enablement_live_endpoint_called_count"
        not in lifecycle_polling_enablement_errors
    ):
        errors.append("PT-6 lifecycle polling live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "guarded_exit_enablement_close_called_count"
        not in guarded_exit_enablement_errors
    ):
        errors.append("PT-7 guarded exit close-counter probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "guarded_exit_enablement_live_endpoint_called_count"
        not in guarded_exit_enablement_errors
    ):
        errors.append("PT-7 guarded exit live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "active_paper_automation_live_endpoint_called_count"
        not in active_automation_errors
    ):
        errors.append("PT-8 active automation live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_active_paper_automation_submit_bypassed_qctrl"
        not in active_automation_qctrl_errors
    ):
        errors.append("PT-8 Q-CTRL hold probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:paper_exit_path_live_endpoint_called_count"
        not in exit_path_errors
    ):
        errors.append("PaperOps exit path live-endpoint probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:paper_exit_path_broker_post_called_count"
        not in exit_path_errors
    ):
        errors.append("PaperOps exit path broker-POST probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:paper_exit_path_order_cancel_called_count"
        not in exit_path_errors
    ):
        errors.append("PaperOps exit path order-cancel probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:notification_review_live_send_allowed_count"
        not in notification_errors
    ):
        errors.append("PaperOps notification live-send probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "notification_review_command_path_enabled_count"
        not in notification_errors
    ):
        errors.append("PaperOps notification command-path probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "notification_review_broker_write_allowed_count"
        not in notification_errors
    ):
        errors.append("PaperOps notification broker-write probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "cockpit_notification_upgrade_live_send_allowed_count"
        not in cockpit_notification_errors
    ):
        errors.append("PT-9 live-send probe was not rejected")
    if (
        "paper_ops_cycle_cockpit_notification_upgrade_qctrl_not_visible"
        not in cockpit_notification_qctrl_errors
    ):
        errors.append("PT-9 Q-CTRL visibility probe was not rejected")
    if (
        "paper_ops_cycle_unsafe_counter_nonzero:"
        "paperops_30_day_operations_unsafe_write_counter_total"
        not in operations_errors
    ):
        errors.append("PaperOps-6 unsafe-counter probe was not rejected")
    if "paper_ops_cycle_qctrl_provider_call_unrecorded_by_paperops_q" not in qctrl_errors:
        errors.append("Q-CTRL provider-call probe was not rejected")
    if "paper_ops_cycle_failed_commands_present" not in failed_command_errors:
        errors.append("failed-command probe was not rejected")
    if "paper_ops_cycle_event_log_missing" not in event_errors:
        errors.append("missing-event-log probe was not rejected")

    if errors:
        print("paper_operational_cycle_contract_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_operational_cycle_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
