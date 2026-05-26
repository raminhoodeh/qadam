#!/usr/bin/env python3
"""Validate Qadam's paper-only operational readiness gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_operational_readiness import (  # noqa: E402
    PAPER_OPS_SCHEMA_VERSION,
    build_paper_operational_readiness,
    paper_operational_readiness_paths,
    validate_paper_operational_readiness,
    write_paper_operational_readiness,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_operational_readiness_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paper_operational_readiness(settings=settings)
    output_path, history_path, event_log_path, written = write_paper_operational_readiness(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paper_operational_readiness(written)
    replay = EventLog(event_log_path, echo=False).replay()

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_paper_operational_readiness(live_capital_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_probe["alpaca_post_called_count"] = 1
    broker_post_errors = validate_paper_operational_readiness(broker_post_probe)

    alpaca_live_endpoint_probe = deepcopy(written)
    alpaca_live_endpoint_probe["alpaca_paper_post_live_endpoint_called_count"] = 1
    alpaca_live_endpoint_errors = validate_paper_operational_readiness(alpaca_live_endpoint_probe)

    lifecycle_poller_live_endpoint_probe = deepcopy(written)
    lifecycle_poller_live_endpoint_probe["paper_lifecycle_poller_live_endpoint_called_count"] = 1
    lifecycle_poller_live_endpoint_errors = validate_paper_operational_readiness(
        lifecycle_poller_live_endpoint_probe
    )

    lifecycle_poller_broker_post_probe = deepcopy(written)
    lifecycle_poller_broker_post_probe["paper_lifecycle_poller_broker_post_called_count"] = 1
    lifecycle_poller_broker_post_errors = validate_paper_operational_readiness(
        lifecycle_poller_broker_post_probe
    )

    lifecycle_poller_proof_probe = deepcopy(written)
    lifecycle_poller_proof_probe["paper_lifecycle_poller_phase7_proof_credit_allowed"] = True
    lifecycle_poller_proof_errors = validate_paper_operational_readiness(
        lifecycle_poller_proof_probe
    )

    exit_live_endpoint_probe = deepcopy(written)
    exit_live_endpoint_probe["paper_exit_path_live_endpoint_called_count"] = 1
    exit_live_endpoint_errors = validate_paper_operational_readiness(exit_live_endpoint_probe)

    exit_broker_post_probe = deepcopy(written)
    exit_broker_post_probe["paper_exit_path_broker_post_called_count"] = 1
    exit_broker_post_errors = validate_paper_operational_readiness(exit_broker_post_probe)

    exit_cancel_probe = deepcopy(written)
    exit_cancel_probe["paper_exit_path_order_cancel_called_count"] = 1
    exit_cancel_errors = validate_paper_operational_readiness(exit_cancel_probe)

    exit_proof_probe = deepcopy(written)
    exit_proof_probe["paper_exit_path_phase7_proof_credit_allowed"] = True
    exit_proof_errors = validate_paper_operational_readiness(exit_proof_probe)

    notification_live_send_probe = deepcopy(written)
    notification_live_send_probe["notification_review_live_send_allowed_count"] = 1
    notification_live_send_errors = validate_paper_operational_readiness(
        notification_live_send_probe
    )

    notification_command_probe = deepcopy(written)
    notification_command_probe["notification_review_command_path_enabled_count"] = 1
    notification_command_errors = validate_paper_operational_readiness(
        notification_command_probe
    )

    notification_broker_probe = deepcopy(written)
    notification_broker_probe["notification_review_broker_write_allowed_count"] = 1
    notification_broker_errors = validate_paper_operational_readiness(
        notification_broker_probe
    )

    notification_proof_probe = deepcopy(written)
    notification_proof_probe["notification_review_phase7_proof_credit_allowed"] = True
    notification_proof_errors = validate_paper_operational_readiness(
        notification_proof_probe
    )

    operations_scheduler_probe = deepcopy(written)
    operations_scheduler_probe["paperops_30_day_operations_automation_active"] = False
    operations_scheduler_errors = validate_paper_operational_readiness(
        operations_scheduler_probe
    )

    operations_prompt_probe = deepcopy(written)
    operations_prompt_probe["paperops_30_day_operations_automation_prompt_paperops_bound"] = False
    operations_prompt_errors = validate_paper_operational_readiness(operations_prompt_probe)

    operations_dashboard_probe = deepcopy(written)
    operations_dashboard_probe["paperops_30_day_operations_dashboard_mirror_public_safe"] = False
    operations_dashboard_errors = validate_paper_operational_readiness(
        operations_dashboard_probe
    )

    operations_unsafe_probe = deepcopy(written)
    operations_unsafe_probe["paperops_30_day_operations_unsafe_write_counter_total"] = 1
    operations_unsafe_errors = validate_paper_operational_readiness(operations_unsafe_probe)

    mode_probe = deepcopy(written)
    mode_probe["mode"] = "live"
    mode_errors = validate_paper_operational_readiness(mode_probe)

    quantum_probe = deepcopy(written)
    quantum_probe["quantum_provider_required_as_execution_prerequisite"] = True
    quantum_errors = validate_paper_operational_readiness(quantum_probe)

    qctrl_execution_probe = deepcopy(written)
    qctrl_execution_probe["qctrl_execution_allowed"] = True
    qctrl_execution_errors = validate_paper_operational_readiness(qctrl_execution_probe)

    telegram_probe = deepcopy(written)
    telegram_probe["telegram_required_for_trade_execution"] = True
    telegram_errors = validate_paper_operational_readiness(telegram_probe)

    strategy_research_probe = deepcopy(written)
    strategy_research_probe["strategy_research_trade_candidate_creation_allowed"] = True
    strategy_research_errors = validate_paper_operational_readiness(strategy_research_probe)

    print(f"paper_ops_status={written['status']}")
    print(f"paper_ops_schema_version={PAPER_OPS_SCHEMA_VERSION}")
    print(f"paper_ops_artifact_path={output_path}")
    print(f"paper_ops_history_path={history_path}")
    print(f"paper_ops_event_log_path={event_log_path}")
    print(f"paper_ops_mode={written['mode']}")
    print(f"paper_ops_enabled={written['paper_operational_enabled']}")
    print(f"paper_ops_alpaca_paper_submit_enabled={written['alpaca_paper_submit_enabled']}")
    print(f"paper_ops_quantum_paper_parity_required={written['quantum_paper_parity_required']}")
    print(f"paper_ops_qctrl_paper_consultation_enabled={written['qctrl_paper_consultation_enabled']}")
    print(f"paper_ops_head_of_quant_oracle_result_count={written['head_of_quant_oracle_result_count']}")
    print(f"paper_ops_head_of_quant_latest_backend={written['head_of_quant_latest_backend']}")
    print(f"paper_ops_qctrl_readiness_status={written['qctrl_readiness_status']}")
    print(f"paper_ops_qctrl_credential_configured={written['qctrl_credential_configured']}")
    print(f"paper_ops_qctrl_sdk_package_importable={written['qctrl_sdk_package_importable']}")
    print(f"paper_ops_qctrl_paper_consultation_status={written['qctrl_paper_consultation_status']}")
    print(
        "paper_ops_qctrl_paper_consultation_provider_call_recorded="
        f"{written['qctrl_paper_consultation_provider_call_recorded']}"
    )
    print(
        "paper_ops_qctrl_paper_consultation_head_note_status="
        f"{written['qctrl_paper_consultation_head_note_status']}"
    )
    print(f"paper_ops_qctrl_provider_call_count={written['qctrl_provider_call_count']}")
    print(f"paper_ops_strategy_research_intake_status={written['strategy_research_intake_status']}")
    print(f"paper_ops_strategy_research_candidate_count={written['strategy_research_candidate_count']}")
    print(
        "paper_ops_strategy_research_trade_candidate_creation_allowed="
        f"{written['strategy_research_trade_candidate_creation_allowed']}"
    )
    print(f"paper_ops_strategy_research_execution_allowed={written['strategy_research_execution_allowed']}")
    print(f"paper_ops_safe_to_continue_paper_only={written['safe_to_continue_paper_only']}")
    print(f"paper_ops_full_paper_operational_ready={written['full_paper_operational_ready']}")
    print(f"paper_ops_ready_capability_count={written['ready_capability_count']}")
    print(f"paper_ops_required_capability_ready_count={written['required_capability_ready_count']}")
    print(f"paper_ops_phase7_run_state={written['phase7_run_state']}")
    print(f"paper_ops_phase7_active_day_number={written['phase7_active_day_number']}")
    print(f"paper_ops_qualified_setup_count={written['qualified_setup_count']}")
    print(f"paper_ops_submitted_paper_order_count={written['submitted_paper_order_count']}")
    print(f"paper_ops_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"paper_ops_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paper_ops_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"paper_ops_alpaca_paper_post_gate_status={written['alpaca_paper_post_gate_status']}")
    print(
        "paper_ops_alpaca_paper_post_path_available="
        f"{written['alpaca_paper_post_path_available']}"
    )
    print(
        "paper_ops_alpaca_paper_post_eligible_submit_record_count="
        f"{written['alpaca_paper_post_eligible_submit_record_count']}"
    )
    print(
        "paper_ops_alpaca_paper_post_called_count="
        f"{written['alpaca_paper_post_called_count']}"
    )
    print(
        "paper_ops_alpaca_paper_post_succeeded_count="
        f"{written['alpaca_paper_post_succeeded_count']}"
    )
    print(
        "paper_ops_alpaca_paper_post_live_endpoint_called_count="
        f"{written['alpaca_paper_post_live_endpoint_called_count']}"
    )
    print(f"paper_ops_lifecycle_poller_status={written['paper_lifecycle_poller_status']}")
    print(
        "paper_ops_lifecycle_poller_source_submitted_order_count="
        f"{written['paper_lifecycle_poller_source_submitted_paper_order_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_poll_candidate_count="
        f"{written['paper_lifecycle_poller_poll_candidate_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_order_poll_called_count="
        f"{written['paper_lifecycle_poller_order_poll_called_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_position_poll_called_count="
        f"{written['paper_lifecycle_poller_position_poll_called_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_broker_get_called_count="
        f"{written['paper_lifecycle_poller_broker_get_called_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_broker_post_called_count="
        f"{written['paper_lifecycle_poller_broker_post_called_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_live_endpoint_called_count="
        f"{written['paper_lifecycle_poller_live_endpoint_called_count']}"
    )
    print(
        "paper_ops_lifecycle_poller_q7_lifecycle_mutation_performed="
        f"{written['paper_lifecycle_poller_q7_lifecycle_mutation_performed']}"
    )
    print(f"paper_ops_exit_path_status={written['paper_exit_path_status']}")
    print(f"paper_ops_exit_path_enabled={written['paper_exit_path_enabled']}")
    print(f"paper_ops_exit_path_available={written['paper_exit_path_available']}")
    print(
        "paper_ops_exit_path_open_position_readback_count="
        f"{written['paper_exit_path_open_position_readback_count']}"
    )
    print(
        "paper_ops_exit_path_eligible_exit_record_count="
        f"{written['paper_exit_path_eligible_exit_record_count']}"
    )
    print(
        "paper_ops_exit_path_close_called_count="
        f"{written['paper_exit_path_close_called_count']}"
    )
    print(
        "paper_ops_exit_path_broker_write_called_count="
        f"{written['paper_exit_path_broker_write_called_count']}"
    )
    print(
        "paper_ops_exit_path_broker_post_called_count="
        f"{written['paper_exit_path_broker_post_called_count']}"
    )
    print(
        "paper_ops_exit_path_live_endpoint_called_count="
        f"{written['paper_exit_path_live_endpoint_called_count']}"
    )
    print(f"paper_ops_notification_review_status={written['notification_review_status']}")
    print(
        "paper_ops_notification_review_record_count="
        f"{written['notification_review_record_count']}"
    )
    print(
        "paper_ops_notification_review_lifecycle_type_count="
        f"{written['notification_review_lifecycle_type_count']}"
    )
    print(
        "paper_ops_notification_review_eligible_review_count="
        f"{written['notification_review_eligible_review_count']}"
    )
    print(
        "paper_ops_notification_review_send_gate="
        f"{written['notification_review_send_gate']}"
    )
    print(
        "paper_ops_notification_review_send_test_gate_state="
        f"{written['notification_review_send_test_gate_state']}"
    )
    print(
        "paper_ops_notification_review_live_send_allowed_count="
        f"{written['notification_review_live_send_allowed_count']}"
    )
    print(
        "paper_ops_notification_review_command_path_enabled_count="
        f"{written['notification_review_command_path_enabled_count']}"
    )
    print(
        "paper_ops_notification_review_broker_write_allowed_count="
        f"{written['notification_review_broker_write_allowed_count']}"
    )
    print(
        "paper_ops_notification_review_paper_order_allowed_count="
        f"{written['notification_review_paper_order_allowed_count']}"
    )
    print(
        "paper_ops_notification_review_position_close_allowed_count="
        f"{written['notification_review_position_close_allowed_count']}"
    )
    print(
        "paper_ops_notification_review_live_endpoint_allowed_count="
        f"{written['notification_review_live_endpoint_allowed_count']}"
    )
    print(f"paper_ops_30_day_operations_status={written['paperops_30_day_operations_status']}")
    print(
        "paper_ops_30_day_operations_scheduler_status="
        f"{written['paperops_30_day_operations_scheduler_status']}"
    )
    print(f"paper_ops_30_day_operations_run_id={written['paperops_30_day_operations_run_id']}")
    print(
        "paper_ops_30_day_operations_active_day_number="
        f"{written['paperops_30_day_operations_active_day_number']}"
    )
    print(
        "paper_ops_30_day_operations_completed_calendar_day_count="
        f"{written['paperops_30_day_operations_completed_calendar_day_count']}"
    )
    print(
        "paper_ops_30_day_operations_calendar_days_remaining="
        f"{written['paperops_30_day_operations_calendar_days_remaining']}"
    )
    print(
        "paper_ops_30_day_operations_automation_active="
        f"{written['paperops_30_day_operations_automation_active']}"
    )
    print(
        "paper_ops_30_day_operations_automation_prompt_paperops_bound="
        f"{written['paperops_30_day_operations_automation_prompt_paperops_bound']}"
    )
    print(
        "paper_ops_30_day_operations_cycle_status="
        f"{written['paperops_30_day_operations_cycle_status']}"
    )
    print(
        "paper_ops_30_day_operations_cycle_command_count="
        f"{written['paperops_30_day_operations_cycle_command_count']}"
    )
    print(
        "paper_ops_30_day_operations_dashboard_mirror_status="
        f"{written['paperops_30_day_operations_dashboard_mirror_status']}"
    )
    print(
        "paper_ops_30_day_operations_dashboard_mirror_public_safe="
        f"{written['paperops_30_day_operations_dashboard_mirror_public_safe']}"
    )
    print(
        "paper_ops_30_day_operations_unsafe_write_counter_total="
        f"{written['paperops_30_day_operations_unsafe_write_counter_total']}"
    )
    print(f"paper_ops_live_capital_enabled={written['live_capital_enabled']}")
    print(f"paper_ops_blocker_count={written['blocker_count']}")
    print(f"paper_ops_blockers={','.join(written['blockers'])}")
    print(f"paper_ops_hard_safety_failure_count={written['hard_safety_failure_count']}")
    print(f"paper_ops_recommended_next_stage={written['recommended_next_stage']}")
    print(f"paper_ops_validation_errors={validation_errors}")
    print(f"paper_ops_event_log_events={replay['total_events']}")

    if validation_errors:
        errors.append(f"paper ops validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("paper ops event log did not record exactly one event")
    if written["mode"] != "paper":
        errors.append("paper ops must run in paper mode")
    if written["live_capital_enabled"] is not False:
        errors.append("paper ops enabled live capital")
    if written["safe_to_continue_paper_only"] is not True:
        errors.append("paper ops hard safety is not clean")
    if written["full_paper_operational_ready"] is True and written["blocker_count"]:
        errors.append("paper ops claims full readiness while blockers exist")
    if (
        written["recommended_next_stage"]
        != "Resolve PaperOps-Q Q-CTRL product access for successful paper consultation"
    ):
        errors.append("paper ops next unblock should be PaperOps-Q product access")
    if "paper_ops_live_capital_enabled" not in live_capital_errors:
        errors.append("live capital probe was not rejected")
    if "paper_ops_unsafe_counter_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker POST probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:alpaca_paper_post_live_endpoint_called_count"
        not in alpaca_live_endpoint_errors
    ):
        errors.append("Alpaca paper POST live-endpoint probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paper_lifecycle_poller_live_endpoint_called_count"
        not in lifecycle_poller_live_endpoint_errors
    ):
        errors.append("PaperOps lifecycle poller live-endpoint probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paper_lifecycle_poller_broker_post_called_count"
        not in lifecycle_poller_broker_post_errors
    ):
        errors.append("PaperOps lifecycle poller broker-POST probe was not rejected")
    if "paper_ops_lifecycle_poller_proof_credit_allowed" not in lifecycle_poller_proof_errors:
        errors.append("PaperOps lifecycle poller proof-credit probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paper_exit_path_live_endpoint_called_count"
        not in exit_live_endpoint_errors
    ):
        errors.append("PaperOps exit path live-endpoint probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paper_exit_path_broker_post_called_count"
        not in exit_broker_post_errors
    ):
        errors.append("PaperOps exit path broker-POST probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paper_exit_path_order_cancel_called_count"
        not in exit_cancel_errors
    ):
        errors.append("PaperOps exit path order-cancel probe was not rejected")
    if "paper_ops_exit_path_proof_credit_allowed" not in exit_proof_errors:
        errors.append("PaperOps exit path proof-credit probe was not rejected")
    if (
        "paper_ops_notification_unsafe_counter_nonzero:"
        "notification_review_live_send_allowed_count"
        not in notification_live_send_errors
    ):
        errors.append("PaperOps notification live-send probe was not rejected")
    if (
        "paper_ops_notification_unsafe_counter_nonzero:"
        "notification_review_command_path_enabled_count"
        not in notification_command_errors
    ):
        errors.append("PaperOps notification command-path probe was not rejected")
    if (
        "paper_ops_notification_unsafe_counter_nonzero:"
        "notification_review_broker_write_allowed_count"
        not in notification_broker_errors
    ):
        errors.append("PaperOps notification broker-write probe was not rejected")
    if "paper_ops_notification_phase7_proof_credit_allowed" not in notification_proof_errors:
        errors.append("PaperOps notification proof-credit probe was not rejected")
    if "paper_ops_30_day_operations_scheduler_inactive" not in operations_scheduler_errors:
        errors.append("PaperOps-6 scheduler probe was not rejected")
    if "paper_ops_30_day_operations_prompt_not_bound" not in operations_prompt_errors:
        errors.append("PaperOps-6 prompt probe was not rejected")
    if "paper_ops_30_day_operations_dashboard_not_public_safe" not in operations_dashboard_errors:
        errors.append("PaperOps-6 dashboard probe was not rejected")
    if (
        "paper_ops_unsafe_counter_nonzero:paperops_30_day_operations_unsafe_write_counter_total"
        not in operations_unsafe_errors
    ):
        errors.append("PaperOps-6 unsafe-counter probe was not rejected")
    if "paper_ops_mode_not_paper" not in mode_errors:
        errors.append("live mode probe was not rejected")
    if "paper_ops_quantum_provider_execution_prerequisite" not in quantum_errors:
        errors.append("quantum execution-prerequisite probe was not rejected")
    if "paper_ops_qctrl_execution_authority" not in qctrl_execution_errors:
        errors.append("Q-CTRL execution-authority probe was not rejected")
    if "paper_ops_telegram_trade_execution_required" not in telegram_errors:
        errors.append("Telegram execution probe was not rejected")
    if "paper_ops_strategy_research_trade_authority" not in strategy_research_errors:
        errors.append("strategy research authority probe was not rejected")

    if errors:
        print("paper_operational_readiness_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paper_operational_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
