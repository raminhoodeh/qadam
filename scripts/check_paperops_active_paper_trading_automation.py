#!/usr/bin/env python3
"""Validate PT-8 active PaperOps paper-trading automation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_active_paper_trading_automation import (  # noqa: E402
    PAPEROPS_ACTIVE_AUTOMATION_COMPONENT,
    PAPEROPS_ACTIVE_AUTOMATION_EVENT_TYPE,
    PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION,
    build_paperops_active_paper_trading_automation,
    paperops_active_paper_trading_automation_paths,
    validate_paperops_active_paper_trading_automation,
    write_paperops_active_paper_trading_automation,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = (
        paperops_active_paper_trading_automation_paths(settings)
    )
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_active_paper_trading_automation(settings=settings)
    output_path, history_path, event_path, written = (
        write_paperops_active_paper_trading_automation(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_path,
        )
    )
    validation_errors = validate_paperops_active_paper_trading_automation(written)
    replay = EventLog(event_path, echo=False).replay()

    prompt_probe = deepcopy(written)
    prompt_probe["automation_prompt_active_trade_bound"] = False
    prompt_probe["automation_present_command_count"] = max(
        0,
        int(prompt_probe["automation_present_command_count"]) - 1,
    )
    prompt_probe["automation_missing_commands"] = ["scripts/run_active_paper_trading_automation.py --execute-paper-automation"]
    prompt_errors = validate_paperops_active_paper_trading_automation(prompt_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_active_paper_trading_automation(
        live_capital_probe
    )

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["live_endpoint_allowed"] = True
    live_endpoint_probe["live_endpoint_called_count"] = 1
    live_endpoint_probe["unsafe_write_counter_total"] = 1
    live_endpoint_errors = validate_paperops_active_paper_trading_automation(
        live_endpoint_probe
    )

    qctrl_bypass_probe = deepcopy(written)
    qctrl_bypass_probe["qctrl_paper_parity_required"] = True
    qctrl_bypass_probe["qctrl_paper_consultation_ready"] = False
    qctrl_bypass_probe["qctrl_consultation_hold_active"] = True
    qctrl_bypass_probe["paper_submit_step_allowed"] = True
    qctrl_bypass_errors = validate_paperops_active_paper_trading_automation(
        qctrl_bypass_probe
    )

    direct_broker_probe = deepcopy(written)
    direct_broker_probe["direct_broker_shortcut_allowed"] = True
    direct_broker_probe["paper_order_submission_allowed_without_paperops2"] = True
    direct_broker_errors = validate_paperops_active_paper_trading_automation(
        direct_broker_probe
    )

    forced_probe = deepcopy(written)
    forced_probe["forced_trades_allowed"] = True
    forced_errors = validate_paperops_active_paper_trading_automation(forced_probe)

    qctrl_execution_probe = deepcopy(written)
    qctrl_execution_probe["qctrl_direct_execution_allowed"] = True
    qctrl_execution_probe["qctrl_broker_post_allowed"] = True
    qctrl_execution_errors = validate_paperops_active_paper_trading_automation(
        qctrl_execution_probe
    )

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paperops_active_paper_trading_automation(secret_probe)

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_active_paper_trading_automation(proof_probe)

    daily_target_ceiling_probe = deepcopy(written)
    daily_target_ceiling_probe["rs5_daily_target_met"] = True
    daily_target_ceiling_probe["rs5_available_distinct_setup_count"] = 1
    daily_target_ceiling_probe["rs5_additional_distinct_setup_available"] = True
    daily_target_ceiling_probe["idle_reason"] = "daily_paper_trade_target_met"
    daily_target_ceiling_errors = validate_paperops_active_paper_trading_automation(
        daily_target_ceiling_probe
    )

    rs5_policy_probe = deepcopy(written)
    rs5_policy_probe["rs5_daily_target_policy"] = "hard_ceiling"
    rs5_policy_probe["rs5_daily_target_is_minimum"] = False
    rs5_policy_probe["rs5_daily_target_blocks_additional_qualified_setups"] = True
    rs5_policy_errors = validate_paperops_active_paper_trading_automation(
        rs5_policy_probe
    )

    rs5_route_probe = deepcopy(written)
    rs5_route_probe["rs5_guarded_submit_route"] = "scripts/unmanaged_broker_post.py"
    rs5_route_probe["rs5_guarded_submit_transport"] = "direct_broker_shortcut"
    rs5_route_errors = validate_paperops_active_paper_trading_automation(
        rs5_route_probe
    )

    why_not_probe = deepcopy(written)
    why_not_probe["paper_submit_step_allowed"] = False
    why_not_probe["why_not_trading_now"] = ""
    why_not_probe["why_not_trading_now_reasons"] = []
    why_not_errors = validate_paperops_active_paper_trading_automation(why_not_probe)

    print(f"paperops_active_automation_status={written['status']}")
    print(
        "paperops_active_automation_schema_version="
        f"{PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION}"
    )
    print(f"paperops_active_automation_artifact_path={output_path}")
    print(f"paperops_active_automation_history_path={history_path}")
    print(f"paperops_active_automation_event_log_path={event_path}")
    print(f"paperops_active_automation_mode={written['mode']}")
    print(
        "paperops_active_automation_enabled="
        f"{written['active_paper_trading_automation_enabled']}"
    )
    print(
        "paperops_active_automation_effective="
        f"{written['active_paper_trading_automation_effective']}"
    )
    print(
        "paperops_active_automation_prompt_bound="
        f"{written['automation_prompt_active_trade_bound']}"
    )
    print(f"paperops_active_automation_scheduler_active={written['automation_active']}")
    print(f"paperops_active_automation_scheduler_hourly={written['automation_hourly']}")
    print(
        "paperops_active_automation_present_command_count="
        f"{written['automation_present_command_count']}"
    )
    print(
        "paperops_active_automation_required_command_count="
        f"{written['automation_required_command_count']}"
    )
    print(
        "paperops_active_automation_present_guardrail_count="
        f"{written['automation_present_guardrail_count']}"
    )
    print(
        "paperops_active_automation_required_guardrail_count="
        f"{written['automation_required_guardrail_count']}"
    )
    print(
        "paperops_active_automation_missing_commands="
        f"{','.join(written['automation_missing_commands'])}"
    )
    print(
        "paperops_active_automation_missing_guardrails="
        f"{','.join(written['automation_missing_guardrails'])}"
    )
    print(
        "paperops_active_automation_execute_requested="
        f"{written['execute_automation_requested']}"
    )
    print(
        "paperops_active_automation_qctrl_required="
        f"{written['qctrl_paper_parity_required']}"
    )
    print(
        "paperops_active_automation_qctrl_ready="
        f"{written['qctrl_paper_consultation_ready']}"
    )
    print(
        "paperops_active_automation_qctrl_hold="
        f"{written['qctrl_consultation_hold_active']}"
    )
    print(
        "paperops_active_automation_readiness_status="
        f"{written['paperops_readiness_status']}"
    )
    print(
        "paperops_active_automation_safe_to_continue="
        f"{written['paperops_safe_to_continue']}"
    )
    print(
        "paperops_active_automation_paperops2_status="
        f"{written['paperops2_status']}"
    )
    print(
        "paperops_active_automation_paperops2_path_available="
        f"{written['paperops2_path_available']}"
    )
    print(
        "paperops_active_automation_paperops2_eligible_submit_record_count="
        f"{written['paperops2_eligible_submit_record_count']}"
    )
    print(
        "paperops_active_automation_paperops2_fresh_eligible_submit_record_count="
        f"{written['paperops2_fresh_eligible_submit_record_count']}"
    )
    print(
        "paperops_active_automation_paperops2_duplicate_submit_record_count="
        f"{written['paperops2_duplicate_submit_record_count']}"
    )
    print(
        "paperops_active_automation_paperops2_duplicate_submit_interpretation="
        f"{written['paperops2_duplicate_submit_interpretation']}"
    )
    print(
        "paperops_active_automation_paperops2_idempotency_ledger_active="
        f"{written['paperops2_idempotency_ledger_active']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_status="
        f"{written['first_week_paper_trade_mandate_status']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_active="
        f"{written['first_week_paper_trade_mandate_active']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_day_number="
        f"{written['first_week_paper_trade_mandate_day_number']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_daily_target_trade_count="
        f"{written['first_week_paper_trade_mandate_daily_target_trade_count']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_minimum_notional_usd="
        f"{written['first_week_paper_trade_mandate_minimum_notional_usd']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_daily_ready_submit_count="
        f"{written['first_week_paper_trade_mandate_daily_ready_submit_count']}"
    )
    print(
        "paperops_active_automation_first_week_mandate_daily_submitted_count="
        f"{written['first_week_paper_trade_mandate_daily_submitted_count']}"
    )
    print(
        "paperops_active_automation_rs5_status="
        f"{written['rs5_guarded_paper_autonomy_status']}"
    )
    print(
        "paperops_active_automation_rs5_daily_target_policy="
        f"{written['rs5_daily_target_policy']}"
    )
    print(
        "paperops_active_automation_rs5_daily_target_is_minimum="
        f"{written['rs5_daily_target_is_minimum']}"
    )
    print(
        "paperops_active_automation_rs5_daily_target_blocks_additional_setups="
        f"{written['rs5_daily_target_blocks_additional_qualified_setups']}"
    )
    print(
        "paperops_active_automation_rs5_opportunity_scan_interval_minutes="
        f"{written['rs5_opportunity_scan_interval_minutes']}"
    )
    print(
        "paperops_active_automation_rs5_guarded_submit_route="
        f"{written['rs5_guarded_submit_route']}"
    )
    print(
        "paperops_active_automation_rs5_guarded_submit_transport="
        f"{written['rs5_guarded_submit_transport']}"
    )
    print(
        "paperops_active_automation_rs5_max_guarded_submit_attempts_per_run="
        f"{written['rs5_max_guarded_submit_attempts_per_run']}"
    )
    print(
        "paperops_active_automation_rs5_available_distinct_setup_count="
        f"{written['rs5_available_distinct_setup_count']}"
    )
    print(
        "paperops_active_automation_rs5_distinct_candidate_count="
        f"{written['rs5_distinct_candidate_count']}"
    )
    print(
        "paperops_active_automation_rs5_distinct_research_goal_count="
        f"{written['rs5_distinct_research_goal_count']}"
    )
    print(
        "paperops_active_automation_rs5_distinct_idempotency_key_count="
        f"{written['rs5_distinct_idempotency_key_count']}"
    )
    print(
        "paperops_active_automation_rs5_can_submit_multiple_today="
        f"{written['rs5_can_submit_multiple_today']}"
    )
    print(
        "paperops_active_automation_rs5_guard_status="
        f"{written['rs5_multiple_submission_guard_status']}"
    )
    print(
        "paperops_active_automation_why_not_trading_now="
        f"{written['why_not_trading_now']}"
    )
    print(
        "paperops_active_automation_paperops2_submit_called_count="
        f"{written['paperops2_submit_called_count']}"
    )
    print(
        "paperops_active_automation_paperops3_status="
        f"{written['paperops3_status']}"
    )
    print(
        "paperops_active_automation_paperops3_source_submitted_order_count="
        f"{written['paperops3_source_submitted_order_count']}"
    )
    print(
        "paperops_active_automation_paperops3_order_poll_called_count="
        f"{written['paperops3_order_poll_called_count']}"
    )
    print(
        "paperops_active_automation_paperops3_open_position_count="
        f"{written['paperops3_open_position_count']}"
    )
    print(
        "paperops_active_automation_paperops4_status="
        f"{written['paperops4_status']}"
    )
    print(
        "paperops_active_automation_paperops4_exit_path_available="
        f"{written['paperops4_exit_path_available']}"
    )
    print(
        "paperops_active_automation_paperops4_eligible_exit_record_count="
        f"{written['paperops4_eligible_exit_record_count']}"
    )
    print(
        "paperops_active_automation_paperops4_close_called_count="
        f"{written['paperops4_close_called_count']}"
    )
    print(
        "paperops_active_automation_submit_step_allowed="
        f"{written['paper_submit_step_allowed']}"
    )
    print(
        "paperops_active_automation_unattended_delegation_enabled="
        f"{written['unattended_paper_execution_delegation_enabled']}"
    )
    print(
        "paperops_active_automation_unattended_delegation_reason="
        f"{written['unattended_paper_execution_delegation_reason']}"
    )
    print(f"paperops_active_automation_idle_reason={written['idle_reason'] or ''}")
    print(
        "paperops_active_automation_idempotency_guard_message="
        f"{written['idempotency_guard_message']}"
    )
    print(
        "paperops_active_automation_poll_step_allowed="
        f"{written['paper_poll_step_allowed']}"
    )
    print(
        "paperops_active_automation_exit_step_allowed="
        f"{written['paper_exit_step_allowed']}"
    )
    print(
        "paperops_active_automation_submit_hold_reason="
        f"{written['submit_hold_reason']}"
    )
    print(
        "paperops_active_automation_poll_hold_reason="
        f"{written['poll_hold_reason']}"
    )
    print(
        "paperops_active_automation_exit_hold_reason="
        f"{written['exit_hold_reason']}"
    )
    print(
        "paperops_active_automation_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_active_automation_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "paperops_active_automation_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(f"paperops_active_automation_event_log_events={replay['total_events']}")
    print(f"paperops_active_automation_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PT-8 validation failed: {validation_errors}")
    if replay["total_events"] < 1:
        errors.append("PT-8 event log did not record a recorded event")
    if (
        replay.get("by_type", {}).get(PAPEROPS_ACTIVE_AUTOMATION_EVENT_TYPE, 0) < 1
        or replay.get("by_component", {}).get(PAPEROPS_ACTIVE_AUTOMATION_COMPONENT, 0) < 1
    ):
        errors.append("PT-8 event log missing active automation event")
    if written["mode"] != "paper":
        errors.append("PT-8 mode is not paper")
    if written["active_paper_trading_automation_enabled"] is not True:
        errors.append("PT-8 active paper automation is not enabled")
    if written["automation_active"] is not True:
        errors.append("PT-8 scheduler is not active")
    if written["automation_prompt_active_trade_bound"] is not True:
        errors.append("PT-8 automation prompt is not active-trade bound")
    if written["paperops_safe_to_continue"] is not True:
        errors.append("PT-8 PaperOps readiness is not safe to continue")
    if written["paper_endpoint_confirmed"] is not True:
        errors.append("PT-8 does not see an Alpaca paper endpoint")
    if written["unattended_paper_execution_delegation_enabled"] is not True:
        errors.append("PT-8 unattended paper execution delegation is not armed")
    if written["paperops2_idempotency_ledger_active"] is not True:
        errors.append("PT-8 does not see the PaperOps-2 idempotency ledger")
    if written["first_week_paper_trade_mandate_active"] is True:
        if written["first_week_paper_trade_mandate_daily_target_trade_count"] != 3:
            errors.append("PT-8 first-week mandate target is not three paper trades")
        if float(written["first_week_paper_trade_mandate_minimum_notional_usd"]) < 6000:
            errors.append("PT-8 first-week mandate notional is below USD 6000")
    if written["qctrl_consultation_hold_active"] is True and (
        written["paper_submit_step_allowed"] is True
    ):
        errors.append("PT-8 allowed submit while Q-CTRL hold is active")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-8 enabled live capital")
    if written["live_endpoint_called_count"] != 0:
        errors.append("PT-8 called a live endpoint")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("PT-8 unsafe counter is nonzero")
    if "paperops_active_automation_prompt_not_bound" not in prompt_errors:
        errors.append("prompt-bound probe was not rejected")
    if "paperops_active_automation_live_capital_enabled" not in live_capital_errors:
        errors.append("live-capital probe was not rejected")
    if "paperops_active_automation_forbidden:live_endpoint_allowed" not in live_endpoint_errors:
        errors.append("live-endpoint authority probe was not rejected")
    if (
        "paperops_active_automation_unsafe_counter_nonzero:live_endpoint_called_count"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint counter probe was not rejected")
    if (
        "paperops_active_automation_submit_allowed_under_qctrl_hold"
        not in qctrl_bypass_errors
    ):
        errors.append("Q-CTRL hold bypass probe was not rejected")
    if (
        "paperops_active_automation_forbidden:direct_broker_shortcut_allowed"
        not in direct_broker_errors
    ):
        errors.append("direct broker shortcut probe was not rejected")
    if "paperops_active_automation_forbidden:forced_trades_allowed" not in forced_errors:
        errors.append("forced-trade probe was not rejected")
    if (
        "paperops_active_automation_forbidden:qctrl_direct_execution_allowed"
        not in qctrl_execution_errors
    ):
        errors.append("Q-CTRL execution probe was not rejected")
    if "paperops_active_automation_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("secret-exposure probe was not rejected")
    if (
        "paperops_active_automation_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("proof-credit probe was not rejected")
    if "paperops_active_automation_rs5_target_met_ceiling_detected" not in (
        daily_target_ceiling_errors
    ):
        errors.append("RS-5 daily-target ceiling probe was not rejected")
    if "paperops_active_automation_rs5_daily_target_policy_invalid" not in (
        rs5_policy_errors
    ):
        errors.append("RS-5 policy probe was not rejected")
    if "paperops_active_automation_rs5_daily_target_not_minimum" not in (
        rs5_policy_errors
    ):
        errors.append("RS-5 minimum-target probe was not rejected")
    if "paperops_active_automation_rs5_daily_target_ceiling_enabled" not in (
        rs5_policy_errors
    ):
        errors.append("RS-5 ceiling-enabled probe was not rejected")
    if "paperops_active_automation_rs5_route_invalid" not in rs5_route_errors:
        errors.append("RS-5 route probe was not rejected")
    if "paperops_active_automation_rs5_transport_invalid" not in rs5_route_errors:
        errors.append("RS-5 transport probe was not rejected")
    if "paperops_active_automation_why_not_trading_missing" not in why_not_errors:
        errors.append("why-not-trading probe was not rejected")

    if errors:
        print("paperops_active_paper_trading_automation_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_active_paper_trading_automation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
