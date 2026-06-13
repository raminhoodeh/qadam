#!/usr/bin/env python3
"""Validate PaperOps-6 30-day paper run operations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_30_day_operations import (  # noqa: E402
    PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION,
    build_paperops_30_day_operations,
    paperops_30_day_operations_paths,
    validate_paperops_30_day_operations,
    write_paperops_30_day_operations,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paperops_30_day_operations_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_30_day_operations(settings=settings)
    output_path, history_path, event_log_path, written = write_paperops_30_day_operations(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paperops_30_day_operations(written)
    replay = EventLog(event_log_path, echo=False).replay()

    inactive_scheduler_probe = deepcopy(written)
    inactive_scheduler_probe["automation_active"] = False
    inactive_scheduler_probe["automation_hourly"] = False
    inactive_scheduler_errors = validate_paperops_30_day_operations(
        inactive_scheduler_probe
    )

    prompt_probe = deepcopy(written)
    prompt_probe["automation_prompt_paperops_bound"] = False
    prompt_probe["automation_present_command_count"] = max(
        0,
        int(written["automation_present_command_count"]) - 1,
    )
    prompt_probe["automation_missing_commands"] = [
        "scripts/check_paperops_30_day_operations.py"
    ]
    prompt_errors = validate_paperops_30_day_operations(prompt_probe)

    backfill_probe = deepcopy(written)
    backfill_probe["backfill_used"] = True
    backfill_errors = validate_paperops_30_day_operations(backfill_probe)

    simulated_time_probe = deepcopy(written)
    simulated_time_probe["simulated_time_used"] = True
    simulated_time_errors = validate_paperops_30_day_operations(simulated_time_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["no_forced_trades"] = False
    forced_trade_errors = validate_paperops_30_day_operations(forced_trade_probe)

    no_setup_trade_probe = deepcopy(written)
    no_setup_trade_probe["qualified_setup_count"] = 0
    no_setup_trade_probe["submitted_paper_order_count"] = 1
    no_setup_trade_errors = validate_paperops_30_day_operations(no_setup_trade_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["alpaca_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 2
    broker_errors = validate_paperops_30_day_operations(broker_probe)

    live_probe = deepcopy(written)
    live_probe["live_capital_enabled"] = True
    live_probe["live_credentials_loaded"] = True
    live_probe["live_endpoint_called_count"] = 1
    live_probe["unsafe_write_counter_total"] = 1
    live_errors = validate_paperops_30_day_operations(live_probe)

    notification_probe = deepcopy(written)
    notification_probe["notification_live_send_allowed_count"] = 1
    notification_probe["telegram_command_path_enabled_count"] = 1
    notification_probe["broker_write_allowed_count"] = 1
    notification_probe["unsafe_write_counter_total"] = 3
    notification_errors = validate_paperops_30_day_operations(notification_probe)

    active_automation_probe = deepcopy(written)
    active_automation_probe["paperops_active_automation_live_endpoint_called_count"] = 1
    active_automation_probe["unsafe_write_counter_total"] = 1
    active_automation_errors = validate_paperops_30_day_operations(
        active_automation_probe
    )

    active_automation_qctrl_probe = deepcopy(written)
    active_automation_qctrl_probe["paperops_active_automation_qctrl_hold"] = True
    active_automation_qctrl_probe["paperops_active_automation_submit_step_allowed"] = True
    active_automation_qctrl_errors = validate_paperops_30_day_operations(
        active_automation_qctrl_probe
    )

    submit_regression_blocked_probe = deepcopy(written)
    submit_regression_blocked_probe[
        "paperops_submit_regression_guard_status"
    ] = "blocked_submit_regression"
    submit_regression_blocked_probe[
        "paperops_submit_regression_guard_blocker_count"
    ] = 1
    submit_regression_blocked_errors = validate_paperops_30_day_operations(
        submit_regression_blocked_probe
    )

    submit_regression_collision_probe = deepcopy(written)
    submit_regression_collision_probe[
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count"
    ] = 1
    submit_regression_collision_errors = validate_paperops_30_day_operations(
        submit_regression_collision_probe
    )

    submit_regression_misclassified_probe = deepcopy(written)
    submit_regression_misclassified_probe[
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count"
    ] = 1
    submit_regression_misclassified_errors = validate_paperops_30_day_operations(
        submit_regression_misclassified_probe
    )

    source_gap_required_probe = deepcopy(written)
    source_gap_required_probe["paperops_source_gap_visibility_required_gap_count"] = 1
    source_gap_required_errors = validate_paperops_30_day_operations(
        source_gap_required_probe
    )

    source_gap_trade_blocking_probe = deepcopy(written)
    source_gap_trade_blocking_probe[
        "paperops_source_gap_visibility_trade_blocking_gap_count"
    ] = 1
    source_gap_trade_blocking_errors = validate_paperops_30_day_operations(
        source_gap_trade_blocking_probe
    )

    source_gap_silent_blocker_probe = deepcopy(written)
    source_gap_silent_blocker_probe[
        "paperops_source_gap_visibility_silent_blocker_count"
    ] = 1
    source_gap_silent_blocker_errors = validate_paperops_30_day_operations(
        source_gap_silent_blocker_probe
    )

    source_gap_unsafe_probe = deepcopy(written)
    source_gap_unsafe_probe[
        "paperops_source_gap_visibility_live_endpoint_called_count"
    ] = 1
    source_gap_unsafe_probe[
        "paperops_source_gap_visibility_broker_post_called_count"
    ] = 1
    source_gap_unsafe_probe["unsafe_write_counter_total"] = 2
    source_gap_unsafe_errors = validate_paperops_30_day_operations(
        source_gap_unsafe_probe
    )

    source_gap_live_capital_probe = deepcopy(written)
    source_gap_live_capital_probe[
        "paperops_source_gap_visibility_live_capital_enabled"
    ] = True
    source_gap_live_capital_errors = validate_paperops_30_day_operations(
        source_gap_live_capital_probe
    )

    cockpit_notification_probe = deepcopy(written)
    cockpit_notification_probe[
        "paperops_cockpit_notification_live_send_allowed_count"
    ] = 1
    cockpit_notification_probe[
        "paperops_cockpit_notification_unsafe_write_counter_total"
    ] = 1
    cockpit_notification_probe["unsafe_write_counter_total"] = 1
    cockpit_notification_errors = validate_paperops_30_day_operations(
        cockpit_notification_probe
    )

    cockpit_notification_qctrl_probe = deepcopy(written)
    cockpit_notification_qctrl_probe[
        "paperops_cockpit_notification_qctrl_hold_visible"
    ] = True
    cockpit_notification_qctrl_probe[
        "paperops_cockpit_notification_submit_visible_as_held"
    ] = False
    cockpit_notification_qctrl_errors = validate_paperops_30_day_operations(
        cockpit_notification_qctrl_probe
    )

    paper_live_probe = deepcopy(written)
    paper_live_probe["paper_live_certification_unsafe_write_counter_total"] = 1
    paper_live_probe["unsafe_write_counter_total"] = 1
    paper_live_errors = validate_paperops_30_day_operations(paper_live_probe)

    paper_live_certified_probe = deepcopy(written)
    paper_live_certified_probe["paper_live_certification_paper_live_certified"] = True
    paper_live_certified_probe["paper_live_certification_operation_allowed"] = True
    paper_live_certified_probe[
        "paper_live_certification_unattended_delegation_enabled"
    ] = True
    paper_live_certified_probe["paper_live_certification_blocker_count"] = 1
    paper_live_certified_errors = validate_paperops_30_day_operations(
        paper_live_certified_probe
    )

    dashboard_probe = deepcopy(written)
    dashboard_probe["dashboard_mirror_public_safe"] = False
    dashboard_probe["dashboard_mirror_trigger_trading_allowed"] = True
    dashboard_errors = validate_paperops_30_day_operations(dashboard_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_30_day_operations(event_probe)

    print(f"paperops_30_day_operations_status={written['status']}")
    print(
        "paperops_30_day_operations_schema_version="
        f"{PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION}"
    )
    print(f"paperops_30_day_operations_artifact_path={output_path}")
    print(f"paperops_30_day_operations_history_path={history_path}")
    print(f"paperops_30_day_operations_event_log_path={event_log_path}")
    print(f"paperops_30_day_operations_event_log_events={replay['total_events']}")
    print(f"paperops_30_day_operations_run_id={written['run_id']}")
    print(f"paperops_30_day_operations_run_state={written['run_state']}")
    print(f"paperops_30_day_operations_start_date={written['start_date']}")
    print(f"paperops_30_day_operations_end_date={written['end_date']}")
    print(
        "paperops_30_day_operations_active_day_number="
        f"{written['active_day_number']}"
    )
    print(
        "paperops_30_day_operations_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
    )
    print(
        "paperops_30_day_operations_calendar_days_remaining="
        f"{written['calendar_days_remaining']}"
    )
    print(
        "paperops_30_day_operations_phase7_30_day_run_complete="
        f"{written['phase7_30_day_run_complete']}"
    )
    print(
        "paperops_30_day_operations_actual_calendar_run="
        f"{written['actual_calendar_run']}"
    )
    print(f"paperops_30_day_operations_backfill_used={written['backfill_used']}")
    print(
        "paperops_30_day_operations_simulated_time_used="
        f"{written['simulated_time_used']}"
    )
    print(f"paperops_30_day_operations_no_forced_trades={written['no_forced_trades']}")
    print(
        "paperops_30_day_operations_qualified_setup_count="
        f"{written['qualified_setup_count']}"
    )
    print(
        "paperops_30_day_operations_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "paperops_30_day_operations_closed_proof_trade_count="
        f"{written['closed_proof_trade_count']}"
    )
    print(
        "paperops_30_day_operations_close_to_ledger_status="
        f"{written['paperops_close_to_ledger_status']}"
    )
    print(
        "paperops_30_day_operations_close_to_ledger_closed_proof_trade_count="
        f"{written['paperops_close_to_ledger_closed_proof_trade_count']}"
    )
    print(
        "paperops_30_day_operations_close_to_ledger_postmortem_due_marker_created_count="
        f"{written['paperops_close_to_ledger_postmortem_due_marker_created_count']}"
    )
    print(
        "paperops_30_day_operations_close_to_ledger_blocker_count="
        f"{written['paperops_close_to_ledger_blocker_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_status="
        f"{written['paperops_submit_regression_guard_status']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_source_paperops2_status="
        f"{written['paperops_submit_regression_guard_source_paperops2_status']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_fresh_eligible_submit_record_count="
        f"{written['paperops_submit_regression_guard_fresh_eligible_submit_record_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_duplicate_submit_record_count="
        f"{written['paperops_submit_regression_guard_duplicate_submit_record_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_source_stale_after_post_count="
        f"{written['paperops_submit_regression_guard_source_stale_after_post_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_fresh_submitted_ledger_collision_count="
        f"{written['paperops_submit_regression_guard_fresh_submitted_ledger_collision_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_duplicate_misclassified_as_fresh_count="
        f"{written['paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_blocker_count="
        f"{written['paperops_submit_regression_guard_blocker_count']}"
    )
    print(
        "paperops_30_day_operations_submit_regression_guard_validation_error_count="
        f"{written['paperops_submit_regression_guard_validation_error_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_status="
        f"{written['paperops_source_gap_visibility_status']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_policy_status="
        f"{written['paperops_source_gap_visibility_policy_status']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_optional_gap_count="
        f"{written['paperops_source_gap_visibility_optional_gap_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_optional_gap_keys="
        f"{','.join(written['paperops_source_gap_visibility_optional_gap_keys'])}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_required_gap_count="
        f"{written['paperops_source_gap_visibility_required_gap_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_trade_blocking_gap_count="
        f"{written['paperops_source_gap_visibility_trade_blocking_gap_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_silent_blocker_count="
        f"{written['paperops_source_gap_visibility_silent_blocker_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_blocker_count="
        f"{written['paperops_source_gap_visibility_blocker_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_live_endpoint_called_count="
        f"{written['paperops_source_gap_visibility_live_endpoint_called_count']}"
    )
    print(
        "paperops_30_day_operations_source_gap_visibility_broker_post_called_count="
        f"{written['paperops_source_gap_visibility_broker_post_called_count']}"
    )
    print(
        "paperops_30_day_operations_no_trade_rationale="
        f"{written['no_trade_rationale']}"
    )
    print(f"paperops_30_day_operations_scheduler_status={written['scheduler_status']}")
    print(f"paperops_30_day_operations_automation_active={written['automation_active']}")
    print(f"paperops_30_day_operations_automation_hourly={written['automation_hourly']}")
    print(
        "paperops_30_day_operations_automation_cwd_bound="
        f"{written['automation_cwd_bound']}"
    )
    print(
        "paperops_30_day_operations_automation_prompt_paperops_bound="
        f"{written['automation_prompt_paperops_bound']}"
    )
    print(
        "paperops_30_day_operations_automation_present_command_count="
        f"{written['automation_present_command_count']}"
    )
    print(
        "paperops_30_day_operations_automation_missing_commands="
        f"{','.join(written['automation_missing_commands'])}"
    )
    print(
        "paperops_30_day_operations_automation_present_guardrail_count="
        f"{written['automation_present_guardrail_count']}"
    )
    print(
        "paperops_30_day_operations_automation_missing_guardrails="
        f"{','.join(written['automation_missing_guardrails'])}"
    )
    print(
        "paperops_30_day_operations_cycle_status="
        f"{written['paper_operational_cycle_status']}"
    )
    print(
        "paperops_30_day_operations_cycle_command_count="
        f"{written['paper_operational_cycle_command_count']}"
    )
    print(
        "paperops_30_day_operations_cycle_command_passed_count="
        f"{written['paper_operational_cycle_command_passed_count']}"
    )
    print(
        "paperops_30_day_operations_cycle_command_failed_count="
        f"{written['paper_operational_cycle_command_failed_count']}"
    )
    print(
        "paperops_30_day_operations_cycle_safe_to_continue="
        f"{written['paper_operational_cycle_safe_to_continue']}"
    )
    print(
        "paperops_30_day_operations_dashboard_mirror_status="
        f"{written['dashboard_mirror_status']}"
    )
    print(
        "paperops_30_day_operations_dashboard_mirror_public_safe="
        f"{written['dashboard_mirror_public_safe']}"
    )
    print(
        "paperops_30_day_operations_notification_live_send_allowed_count="
        f"{written['notification_live_send_allowed_count']}"
    )
    print(
        "paperops_30_day_operations_telegram_command_path_enabled_count="
        f"{written['telegram_command_path_enabled_count']}"
    )
    print(
        "paperops_30_day_operations_broker_write_allowed_count="
        f"{written['broker_write_allowed_count']}"
    )
    print(
        "paperops_30_day_operations_active_automation_status="
        f"{written['paperops_active_automation_status']}"
    )
    print(
        "paperops_30_day_operations_active_automation_enabled="
        f"{written['paperops_active_automation_enabled']}"
    )
    print(
        "paperops_30_day_operations_active_automation_qctrl_hold="
        f"{written['paperops_active_automation_qctrl_hold']}"
    )
    print(
        "paperops_30_day_operations_active_automation_submit_step_allowed="
        f"{written['paperops_active_automation_submit_step_allowed']}"
    )
    print(
        "paperops_30_day_operations_active_automation_live_endpoint_called_count="
        f"{written['paperops_active_automation_live_endpoint_called_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_status="
        f"{written['paperops_cockpit_notification_upgrade_status']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_ready="
        f"{written['paperops_cockpit_notification_upgrade_ready']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_review_ready="
        f"{written['paperops_cockpit_notification_notification_ready']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_readout_count="
        f"{written['paperops_cockpit_notification_readout_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_record_count="
        f"{written['paperops_cockpit_notification_notification_record_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_qctrl_hold_visible="
        f"{written['paperops_cockpit_notification_qctrl_hold_visible']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_submit_visible_as_held="
        f"{written['paperops_cockpit_notification_submit_visible_as_held']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_live_send_allowed_count="
        f"{written['paperops_cockpit_notification_live_send_allowed_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_command_path_enabled_count="
        f"{written['paperops_cockpit_notification_command_path_enabled_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_broker_write_allowed_count="
        f"{written['paperops_cockpit_notification_broker_write_allowed_count']}"
    )
    print(
        "paperops_30_day_operations_cockpit_notification_unsafe_write_counter_total="
        f"{written['paperops_cockpit_notification_unsafe_write_counter_total']}"
    )
    print(
        "paperops_30_day_operations_paper_live_certification_status="
        f"{written['paper_live_certification_status']}"
    )
    print(
        "paperops_30_day_operations_paper_live_control_plane_certified="
        f"{written['paper_live_certification_control_plane_certified']}"
    )
    print(
        "paperops_30_day_operations_paper_live_certified="
        f"{written['paper_live_certification_paper_live_certified']}"
    )
    print(
        "paperops_30_day_operations_paper_live_operation_allowed="
        f"{written['paper_live_certification_operation_allowed']}"
    )
    print(
        "paperops_30_day_operations_paper_live_unattended_delegation_enabled="
        f"{written['paper_live_certification_unattended_delegation_enabled']}"
    )
    print(
        "paperops_30_day_operations_paper_live_unattended_delegation_reason="
        f"{written['paper_live_certification_unattended_delegation_reason']}"
    )
    print(
        "paperops_30_day_operations_active_automation_idle_reason="
        f"{written['paperops_active_automation_idle_reason']}"
    )
    print(
        "paperops_30_day_operations_active_automation_idempotency_guard_message="
        f"{written['paperops_active_automation_idempotency_guard_message']}"
    )
    print(
        "paperops_30_day_operations_paper_live_submission_delegation_allowed="
        f"{written['paper_live_certification_submission_delegation_allowed']}"
    )
    print(
        "paperops_30_day_operations_paper_live_blocker_count="
        f"{written['paper_live_certification_blocker_count']}"
    )
    print(
        "paperops_30_day_operations_paper_live_qctrl_hold_visible="
        f"{written['paper_live_certification_qctrl_hold_visible']}"
    )
    print(
        "paperops_30_day_operations_paper_live_submit_visible_as_held="
        f"{written['paper_live_certification_submit_visible_as_held']}"
    )
    print(
        "paperops_30_day_operations_paper_live_phase7_30_day_run_complete="
        f"{written['paper_live_certification_phase7_30_day_run_complete']}"
    )
    print(
        "paperops_30_day_operations_paper_live_phase7_demo_proof_certified="
        f"{written['paper_live_certification_phase7_demo_proof_certified']}"
    )
    print(
        "paperops_30_day_operations_paper_live_unsafe_write_counter_total="
        f"{written['paper_live_certification_unsafe_write_counter_total']}"
    )
    print(f"paperops_30_day_operations_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "paperops_30_day_operations_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_30_day_operations_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_30_day_operations_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paperops_30_day_operations_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paperops_30_day_operations_blocker_count={written['blocker_count']}")
    print(f"paperops_30_day_operations_blockers={','.join(written['blockers'])}")
    print(
        "paperops_30_day_operations_recommended_next_action="
        f"{written['recommended_next_action']}"
    )
    print(f"paperops_30_day_operations_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PaperOps-6 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PaperOps-6 event log did not record exactly one event")
    if written["status"] != "operations_active":
        errors.append("PaperOps-6 is not operations_active")
    if written["automation_prompt_paperops_bound"] is not True:
        errors.append("PaperOps-6 automation prompt is not PaperOps-bound")
    if written["paper_operational_cycle_command_count"] < 22:
        errors.append("PaperOps-6 did not see an established PaperOps cycle")
    if written["paper_operational_cycle_command_failed_count"] != 0:
        errors.append("PaperOps-6 saw failed PaperOps cycle commands")
    if written["paper_operational_cycle_safe_to_continue"] is not True:
        errors.append("PaperOps-6 cycle is not safe to continue")
    if written["dashboard_mirror_public_safe"] is not True:
        errors.append("PaperOps-6 dashboard mirror is not public-safe")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("PaperOps-6 has nonzero unsafe counters")
    if written["qualified_setup_count"] == 0 and (
        written["submitted_paper_order_count"] or written["closed_proof_trade_count"]
    ):
        errors.append("PaperOps-6 trade counts advanced without qualified setup")
    if (
        "paperops_30_day_operations_scheduler_not_ready:automation_active"
        not in inactive_scheduler_errors
    ):
        errors.append("inactive scheduler probe was not rejected")
    if "paperops_30_day_operations_scheduler_command_missing" not in prompt_errors:
        errors.append("automation prompt probe was not rejected")
    if "paperops_30_day_operations_backfill_used" not in backfill_errors:
        errors.append("backfill probe was not rejected")
    if "paperops_30_day_operations_simulated_time_used" not in simulated_time_errors:
        errors.append("simulated-time probe was not rejected")
    if "paperops_30_day_operations_forced_trades_allowed" not in forced_trade_errors:
        errors.append("forced-trade probe was not rejected")
    if "paperops_30_day_operations_trade_without_qualified_setup" not in no_setup_trade_errors:
        errors.append("trade-without-setup probe was not rejected")
    if "paperops_30_day_operations_unsafe_counter_nonzero:broker_post_called_count" not in broker_errors:
        errors.append("broker POST probe was not rejected")
    if "paperops_30_day_operations_forbidden:live_capital_enabled" not in live_errors:
        errors.append("live-capital probe was not rejected")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:notification_live_send_allowed_count"
        not in notification_errors
    ):
        errors.append("notification live-send probe was not rejected")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:"
        "paperops_active_automation_live_endpoint_called_count"
        not in active_automation_errors
    ):
        errors.append("active automation live-endpoint probe was not rejected")
    if (
        "paperops_30_day_operations_active_automation_qctrl_bypass"
        not in active_automation_qctrl_errors
    ):
        errors.append("active automation Q-CTRL-hold probe was not rejected")
    if written["paperops_submit_regression_guard_status"] not in {
        "healthy_idle_idempotency_guarded",
        "healthy_idle_no_fresh_submit",
        "healthy_submitted_idempotency_recorded",
        "ready_fresh_submit_consistent",
    }:
        errors.append("submit regression guard status is not ready or healthy idle")
    if written["paperops_submit_regression_guard_blocker_count"] != 0:
        errors.append("submit regression guard blocker count is nonzero")
    if written["paperops_submit_regression_guard_validation_error_count"] != 0:
        errors.append("submit regression guard validation error count is nonzero")
    if written["paperops_submit_regression_guard_source_stale_after_post_count"] != 0:
        errors.append("submit regression guard saw stale source artifact")
    if (
        written[
            "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count"
        ]
        != 0
    ):
        errors.append("submit regression guard saw fresh ledger collision")
    if (
        written[
            "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count"
        ]
        != 0
    ):
        errors.append("submit regression guard saw duplicate misclassified as fresh")
    if (
        "paperops_30_day_operations_submit_regression_guard_not_ready"
        not in submit_regression_blocked_errors
    ):
        errors.append("submit regression blocked-status probe was not rejected")
    if (
        "paperops_30_day_operations_submit_regression_counter_nonzero:"
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count"
        not in submit_regression_collision_errors
    ):
        errors.append("submit regression fresh-ledger collision probe was not rejected")
    if (
        "paperops_30_day_operations_submit_regression_counter_nonzero:"
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count"
        not in submit_regression_misclassified_errors
    ):
        errors.append("submit regression duplicate-misclassification probe was not rejected")
    if written["paperops_source_gap_visibility_status"] not in {
        "explicit_optional_source_gaps",
        "all_optional_sources_configured",
    }:
        errors.append("source gap visibility status is not ready")
    if written["paperops_source_gap_visibility_policy_status"] != (
        "optional_gaps_explicit_non_blocking"
    ):
        errors.append("source gap policy is not explicit non-blocking")
    if written["paperops_source_gap_visibility_required_gap_count"] != 0:
        errors.append("source gap visibility has required gaps")
    if written["paperops_source_gap_visibility_trade_blocking_gap_count"] != 0:
        errors.append("source gap visibility has trade-blocking gaps")
    if written["paperops_source_gap_visibility_silent_blocker_count"] != 0:
        errors.append("source gap visibility has silent blockers")
    if written["paperops_source_gap_visibility_blocker_count"] != 0:
        errors.append("source gap visibility has blockers")
    if written["paperops_source_gap_visibility_live_endpoint_called_count"] != 0:
        errors.append("source gap visibility has live endpoint calls")
    if written["paperops_source_gap_visibility_broker_post_called_count"] != 0:
        errors.append("source gap visibility has broker POST calls")
    if written["paperops_source_gap_visibility_live_capital_enabled"] is not False:
        errors.append("source gap visibility enabled live capital")
    if (
        "paperops_30_day_operations_source_gap_counter_nonzero:"
        "paperops_source_gap_visibility_required_gap_count"
        not in source_gap_required_errors
    ):
        errors.append("source-gap required-gap probe was not rejected")
    if (
        "paperops_30_day_operations_source_gap_counter_nonzero:"
        "paperops_source_gap_visibility_trade_blocking_gap_count"
        not in source_gap_trade_blocking_errors
    ):
        errors.append("source-gap trade-blocking probe was not rejected")
    if (
        "paperops_30_day_operations_source_gap_counter_nonzero:"
        "paperops_source_gap_visibility_silent_blocker_count"
        not in source_gap_silent_blocker_errors
    ):
        errors.append("source-gap silent-blocker probe was not rejected")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:"
        "paperops_source_gap_visibility_live_endpoint_called_count"
        not in source_gap_unsafe_errors
    ):
        errors.append("source-gap live-endpoint probe was not rejected")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:"
        "paperops_source_gap_visibility_broker_post_called_count"
        not in source_gap_unsafe_errors
    ):
        errors.append("source-gap broker-POST probe was not rejected")
    if (
        "paperops_30_day_operations_source_gap_live_capital_enabled"
        not in source_gap_live_capital_errors
    ):
        errors.append("source-gap live-capital probe was not rejected")
    if written["paperops_cockpit_notification_upgrade_status"] != (
        "cockpit_notification_upgrade_ready"
    ):
        errors.append("PT-9 cockpit notification upgrade is not ready")
    if written["paperops_cockpit_notification_upgrade_ready"] is not True:
        errors.append("PT-9 cockpit upgrade flag is false")
    if written["paperops_cockpit_notification_notification_ready"] is not True:
        errors.append("PT-9 notification upgrade flag is false")
    if written["paperops_cockpit_notification_readout_count"] < 5:
        errors.append("PT-9 cockpit readouts are missing")
    if (
        written["paperops_cockpit_notification_qctrl_hold_visible"] is True
        and written["paperops_cockpit_notification_submit_visible_as_held"] is not True
    ):
        errors.append("PT-9 Q-CTRL hold is not surfaced")
    if written["paperops_cockpit_notification_unsafe_write_counter_total"] != 0:
        errors.append("PT-9 unsafe counter is nonzero")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:"
        "paperops_cockpit_notification_live_send_allowed_count"
        not in cockpit_notification_errors
    ):
        errors.append("PT-9 live-send probe was not rejected")
    if (
        "paperops_30_day_operations_cockpit_notification_qctrl_not_visible"
        not in cockpit_notification_qctrl_errors
    ):
        errors.append("PT-9 Q-CTRL hold visibility probe was not rejected")
    if written["paper_live_certification_status"] not in {
        "blocked_pending_qctrl_and_phase7_proof",
        "blocked_pending_qctrl",
        "blocked_pending_phase7_proof",
        "blocked_pending_certification_gates",
        "blocked_paper_live_control_plane",
        "paper_live_certified",
    }:
        errors.append("PT-10 paper-live certification is not evaluated")
    if written["paper_live_certification_paper_live_certified"] is True:
        if written["paper_live_certification_operation_allowed"] is not True:
            errors.append("PT-10 certified paper-live without allowing paper operation")
        if written["paper_live_certification_unattended_delegation_enabled"] is not True:
            errors.append("PT-10 certified paper-live without unattended delegation")
        if written["paper_live_certification_blocker_count"] != 0:
            errors.append("PT-10 certified paper-live with blockers")
    else:
        if written["paper_live_certification_operation_allowed"] is not False:
            errors.append("PT-10 allowed paper-live operation while blocked")
        if written["paper_live_certification_unattended_delegation_enabled"] is not False:
            errors.append("PT-10 armed unattended delegation while blocked")
        if written["paper_live_certification_blocker_count"] < 1:
            errors.append("PT-10 certification blockers are missing")
    if (
        written["paper_live_certification_submission_delegation_allowed"] is True
        and written["paper_live_certification_paper_live_certified"] is not True
    ):
        errors.append("PT-10 delegated paper submission while uncertified")
    if (
        written["paper_live_certification_qctrl_hold_visible"] is True
        and written["paper_live_certification_submit_visible_as_held"] is not True
    ):
        errors.append("PT-10 Q-CTRL hold is not surfaced")
    if written["paper_live_certification_unsafe_write_counter_total"] != 0:
        errors.append("PT-10 unsafe counter is nonzero")
    if (
        "paperops_30_day_operations_unsafe_counter_nonzero:"
        "paper_live_certification_unsafe_write_counter_total"
        not in paper_live_errors
    ):
        errors.append("PT-10 unsafe probe was not rejected")
    if (
        "paperops_30_day_operations_paper_live_certified_with_blockers"
        not in paper_live_certified_errors
    ):
        errors.append("PT-10 certified-with-blockers probe was not rejected")
    if "paperops_30_day_operations_dashboard_not_public_safe" not in dashboard_errors:
        errors.append("dashboard probe was not rejected")
    if "paperops_30_day_operations_event_log_missing" not in event_errors:
        errors.append("event-log probe was not rejected")

    if errors:
        print("paperops_30_day_operations_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_30_day_operations_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
