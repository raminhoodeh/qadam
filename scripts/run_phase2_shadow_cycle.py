#!/usr/bin/env python3
"""Run Qadam Phase 2 shadow intelligence without execution authority."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase2_shadow_cycle import DEFAULT_PHASE2_SOURCES, run_phase2_shadow_cycle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 2 shadow-intelligence cycle.")
    parser.add_argument("--live-sources", action="store_true", help="Use read-only live source adapters.")
    parser.add_argument(
        "--durable-replay",
        action="store_true",
        help="Use read-only Postgres/Timescale replayed source observations instead of adapter fetches.",
    )
    parser.add_argument("--live-local-llm", action="store_true", help="Call LM Studio chat/completions.")
    parser.add_argument("--events-per-source", type=int, default=3)
    parser.add_argument("--research-limit", type=int, default=8)
    parser.add_argument(
        "--sources",
        default=",".join(DEFAULT_PHASE2_SOURCES),
        help="Comma-separated source keys to include.",
    )
    args = parser.parse_args()

    sources = tuple(source.strip() for source in args.sources.split(",") if source.strip())
    report = run_phase2_shadow_cycle(
        sources=sources,
        live_sources=args.live_sources,
        durable_replay=args.durable_replay,
        live_local_llm=args.live_local_llm,
        events_per_source=args.events_per_source,
        research_limit=args.research_limit,
    )

    print(f"phase2_shadow_cycle_status={report['status']}")
    print(f"phase2_shadow_cycle_mode={report['mode']}")
    print(f"phase2_shadow_cycle_live_local_llm={report['live_local_llm']}")
    print(f"phase2_shadow_cycle_source_count={report['source_count']}")
    print(f"phase2_shadow_cycle_source_degraded_count={report['source_degraded_count']}")
    print(f"phase2_shadow_cycle_preference_mcp_status={report['preference_mcp_shadow_context_status']}")
    print(f"phase2_shadow_cycle_preference_mcp_role={report['preference_mcp_shadow_context_role']}")
    print(
        "phase2_shadow_cycle_preference_mcp_shadow_observation_count="
        f"{report['preference_mcp_shadow_observation_count']}"
    )
    print(
        "phase2_shadow_cycle_preference_mcp_active_required_challenge_count="
        f"{report['preference_mcp_active_required_challenge_count']}"
    )
    print(
        "phase2_shadow_cycle_preference_mcp_source_quorum_credit_allowed="
        f"{report['preference_mcp_source_quorum_credit_allowed']}"
    )
    print(
        "phase2_shadow_cycle_preference_mcp_trade_candidate_creation_allowed="
        f"{report['preference_mcp_trade_candidate_creation_allowed']}"
    )
    print(
        "phase2_shadow_cycle_preference_mcp_risk_handoff_allowed="
        f"{report['preference_mcp_risk_handoff_allowed']}"
    )
    print(f"phase2_shadow_cycle_preference_mcp_execution_allowed={report['preference_mcp_execution_allowed']}")
    print(
        "phase2_shadow_cycle_preference_mcp_broker_write_allowed="
        f"{report['preference_mcp_broker_write_allowed']}"
    )
    print(f"phase2_shadow_cycle_tradingview_mcp_status={report['tradingview_mcp_status']}")
    print(f"phase2_shadow_cycle_tradingview_mcp_role={report['tradingview_mcp_context_role']}")
    print(
        "phase2_shadow_cycle_tradingview_mcp_context_count="
        f"{report['tradingview_mcp_technical_context_count']}"
    )
    print(
        "phase2_shadow_cycle_tradingview_mcp_trade_candidate_creation_allowed="
        f"{report['tradingview_mcp_trade_candidate_creation_allowed']}"
    )
    print(f"phase2_shadow_cycle_tradingview_mcp_execution_allowed={report['tradingview_mcp_execution_allowed']}")
    print(f"phase2_shadow_cycle_tradingview_mcp_paper_order_allowed={report['tradingview_mcp_paper_order_allowed']}")
    print(f"phase2_shadow_cycle_tradingview_mcp_broker_write_allowed={report['tradingview_mcp_broker_write_allowed']}")
    print(f"phase2_shadow_cycle_bookmap_status={report['bookmap_local_bridge_status']}")
    print(f"phase2_shadow_cycle_bookmap_role={report['bookmap_local_bridge_context_role']}")
    print(
        "phase2_shadow_cycle_bookmap_context_count="
        f"{report['bookmap_local_bridge_orderflow_context_count']}"
    )
    print(
        "phase2_shadow_cycle_bookmap_trade_candidate_creation_allowed="
        f"{report['bookmap_local_bridge_trade_candidate_creation_allowed']}"
    )
    print(f"phase2_shadow_cycle_bookmap_execution_allowed={report['bookmap_local_bridge_execution_allowed']}")
    print(f"phase2_shadow_cycle_bookmap_paper_order_allowed={report['bookmap_local_bridge_paper_order_allowed']}")
    print(f"phase2_shadow_cycle_bookmap_broker_write_allowed={report['bookmap_local_bridge_broker_write_allowed']}")
    print(f"phase2_shadow_cycle_strategy_research_intake_status={report['strategy_research_intake_status']}")
    print(f"phase2_shadow_cycle_strategy_research_candidate_count={report['strategy_research_candidate_count']}")
    print(f"phase2_shadow_cycle_strategy_research_challenge_count={report['strategy_research_challenge_count']}")
    print(
        "phase2_shadow_cycle_strategy_research_trade_candidate_creation_allowed="
        f"{report['strategy_research_trade_candidate_creation_allowed']}"
    )
    print(f"phase2_shadow_cycle_strategy_research_risk_handoff_allowed={report['strategy_research_risk_handoff_allowed']}")
    print(f"phase2_shadow_cycle_strategy_research_execution_allowed={report['strategy_research_execution_allowed']}")
    print(f"phase2_shadow_cycle_strategy_research_paper_order_allowed={report['strategy_research_paper_order_allowed']}")
    print(f"phase2_shadow_cycle_strategy_research_broker_write_allowed={report['strategy_research_broker_write_allowed']}")
    print(f"phase2_shadow_cycle_research_goal_hardening={report['research_goal_hardening']}")
    print(f"phase2_shadow_cycle_research_goal_hardening_version={report['research_goal_hardening_version']}")
    print(f"phase2_shadow_cycle_research_goal_candidate_ready_count={report['research_goal_candidate_ready_count']}")
    print(f"phase2_shadow_cycle_research_goal_closed_no_trade_count={report['research_goal_closed_no_trade_count']}")
    print(f"phase2_shadow_cycle_research_goal_stale_goal_count={report['research_goal_stale_goal_count']}")
    print(f"phase2_shadow_cycle_research_goal_expired_goal_count={report['research_goal_expired_goal_count']}")
    print(f"phase2_shadow_cycle_research_goal_average_priority_score={report['research_goal_average_priority_score']}")
    print(f"phase2_shadow_cycle_research_goal_by_priority_label={report['research_goal_by_priority_label']}")
    print(f"phase2_shadow_cycle_market_context_status={report['market_context_status']}")
    print(f"phase2_shadow_cycle_market_context_packet_version={report['market_context_packet_version']}")
    print(f"phase2_shadow_cycle_market_context_packet_count={report['market_context_packet_count']}")
    print(f"phase2_shadow_cycle_market_context_ready_count={report['market_context_ready_count']}")
    print(f"phase2_shadow_cycle_market_context_hold_count={report['market_context_hold_count']}")
    print(
        "phase2_shadow_cycle_market_context_average_source_quality_score="
        f"{report['market_context_average_source_quality_score']}"
    )
    print(f"phase2_shadow_cycle_market_context_average_trust_score={report['market_context_average_trust_score']}")
    print(f"phase2_shadow_cycle_market_context_yahoo_finance_status={report['market_context_yahoo_finance_status']}")
    print(
        "phase2_shadow_cycle_market_context_tradingview_mcp_status="
        f"{report['market_context_tradingview_mcp_status']}"
    )
    print(
        "phase2_shadow_cycle_market_context_bookmap_local_bridge_status="
        f"{report['market_context_bookmap_local_bridge_status']}"
    )
    print(
        "phase2_shadow_cycle_market_context_paper_account_context_status="
        f"{report['market_context_paper_account_context_status']}"
    )
    print(
        "phase2_shadow_cycle_market_context_trade_candidate_creation_allowed_count="
        f"{report['market_context_trade_candidate_creation_allowed_count']}"
    )
    print(
        "phase2_shadow_cycle_market_context_source_quorum_credit_allowed_count="
        f"{report['market_context_source_quorum_credit_allowed_count']}"
    )
    print(f"phase2_shadow_cycle_queued_packet_count={report['queued_packet_count']}")
    print(f"phase2_shadow_cycle_durable_replay_requested={report['durable_replay_requested']}")
    print(f"phase2_shadow_cycle_durable_replay_status={report['durable_replay_status']}")
    print(f"phase2_shadow_cycle_durable_replay_contract_status={report['durable_replay_contract_status']}")
    print(f"phase2_shadow_cycle_durable_replay_observation_count={report['durable_replay_observation_count']}")
    print(f"phase2_shadow_cycle_durable_replay_replayed_source_count={report['durable_replay_replayed_source_count']}")
    print(f"phase2_shadow_cycle_durable_replay_missing_source_count={report['durable_replay_missing_source_count']}")
    print(f"phase2_shadow_cycle_durable_replay_write_authority={report['durable_replay_write_authority']}")
    print(f"phase2_shadow_cycle_durable_replay_signal_authority={report['durable_replay_signal_authority']}")
    print(f"phase2_shadow_cycle_durable_replay_order_authority={report['durable_replay_order_authority']}")
    print(f"phase2_shadow_cycle_shadow_signal_count={report['shadow_signal_count']}")
    print(f"phase2_shadow_cycle_signal_integrity_status={report['signal_integrity_status']}")
    print(f"phase2_shadow_cycle_signal_integrity_review_count={report['signal_integrity_review_count']}")
    print(f"phase2_shadow_cycle_signal_integrity_blocked_count={report['signal_integrity_blocked_count']}")
    print(f"phase2_shadow_cycle_signal_integrity_hold_count={report['signal_integrity_hold_count']}")
    print(
        "phase2_shadow_cycle_signal_integrity_passed_to_risk_shadow_count="
        f"{report['signal_integrity_passed_to_risk_shadow_count']}"
    )
    print(
        "phase2_shadow_cycle_signal_integrity_trade_candidate_created_count="
        f"{report['signal_integrity_trade_candidate_created_count']}"
    )
    print(f"phase2_shadow_cycle_risk_agent_status={report['risk_agent_status']}")
    print(f"phase2_shadow_cycle_risk_agent_review_count={report['risk_agent_review_count']}")
    print(f"phase2_shadow_cycle_risk_agent_blocked_count={report['risk_agent_blocked_count']}")
    print(f"phase2_shadow_cycle_risk_agent_policy_hold_count={report['risk_agent_policy_hold_count']}")
    print(f"phase2_shadow_cycle_risk_agent_shadow_ready_count={report['risk_agent_shadow_ready_count']}")
    print(f"phase2_shadow_cycle_risk_agent_execution_allowed_count={report['risk_agent_execution_allowed_count']}")
    print(f"phase2_shadow_cycle_risk_agent_paper_order_allowed_count={report['risk_agent_paper_order_allowed_count']}")
    print(f"phase2_shadow_cycle_risk_agent_order_created_count={report['risk_agent_order_created_count']}")
    print(f"phase2_shadow_cycle_risk_agent_broker_write_allowed_count={report['risk_agent_broker_write_allowed_count']}")
    print(f"phase2_shadow_cycle_execution_policy_status={report['execution_policy_status']}")
    print(f"phase2_shadow_cycle_execution_policy_review_count={report['execution_policy_review_count']}")
    print(f"phase2_shadow_cycle_execution_policy_blocked_by_policy_count={report['execution_policy_blocked_by_policy_count']}")
    print(f"phase2_shadow_cycle_execution_policy_kill_switch_hold_count={report['execution_policy_kill_switch_hold_count']}")
    print(
        "phase2_shadow_cycle_execution_policy_paper_order_shadow_ready_count="
        f"{report['execution_policy_paper_order_shadow_ready_count']}"
    )
    print(f"phase2_shadow_cycle_execution_policy_execution_allowed_count={report['execution_policy_execution_allowed_count']}")
    print(
        "phase2_shadow_cycle_execution_policy_staged_paper_order_allowed_count="
        f"{report['execution_policy_staged_paper_order_allowed_count']}"
    )
    print(f"phase2_shadow_cycle_execution_policy_paper_order_created_count={report['execution_policy_paper_order_created_count']}")
    print(f"phase2_shadow_cycle_execution_policy_broker_write_allowed_count={report['execution_policy_broker_write_allowed_count']}")
    print(f"phase2_shadow_cycle_execution_policy_live_capital_enabled_count={report['execution_policy_live_capital_enabled_count']}")
    print(f"phase2_shadow_cycle_staged_paper_order_status={report['staged_paper_order_status']}")
    print(f"phase2_shadow_cycle_staged_paper_order_review_count={report['staged_paper_order_review_count']}")
    print(
        "phase2_shadow_cycle_staged_paper_order_blocked_before_staging_count="
        f"{report['staged_paper_order_blocked_before_staging_count']}"
    )
    print(
        "phase2_shadow_cycle_staged_paper_order_reconciliation_hold_count="
        f"{report['staged_paper_order_reconciliation_hold_count']}"
    )
    print(
        "phase2_shadow_cycle_staged_paper_order_disabled_contract_hold_count="
        f"{report['staged_paper_order_disabled_contract_hold_count']}"
    )
    print(f"phase2_shadow_cycle_staged_paper_order_execution_allowed_count={report['staged_paper_order_execution_allowed_count']}")
    print(f"phase2_shadow_cycle_staged_paper_order_created_count={report['staged_paper_order_created_count']}")
    print(f"phase2_shadow_cycle_staged_paper_order_submittable_count={report['staged_paper_order_submittable_count']}")
    print(f"phase2_shadow_cycle_staged_paper_order_broker_write_allowed_count={report['staged_paper_order_broker_write_allowed_count']}")
    print(f"phase2_shadow_cycle_staged_paper_order_live_capital_enabled_count={report['staged_paper_order_live_capital_enabled_count']}")
    print(f"phase2_shadow_cycle_broker_reconciliation_status={report['broker_reconciliation_status']}")
    print(f"phase2_shadow_cycle_broker_reconciliation_review_count={report['broker_reconciliation_review_count']}")
    print(
        "phase2_shadow_cycle_broker_reconciliation_blocked_before_count="
        f"{report['broker_reconciliation_blocked_before_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_route_closed_count="
        f"{report['broker_reconciliation_route_closed_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_contract_hold_count="
        f"{report['broker_reconciliation_contract_hold_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_idempotency_key_allocated_count="
        f"{report['broker_reconciliation_idempotency_key_allocated_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_event_log_prewrite_created_count="
        f"{report['broker_reconciliation_event_log_prewrite_created_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_pre_trade_snapshot_created_count="
        f"{report['broker_reconciliation_pre_trade_snapshot_created_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_duplicate_order_guard_ready_count="
        f"{report['broker_reconciliation_duplicate_order_guard_ready_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_broker_echo_verified_count="
        f"{report['broker_reconciliation_broker_echo_verified_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_post_submit_reconciliation_ready_count="
        f"{report['broker_reconciliation_post_submit_reconciliation_ready_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_postmortem_link_ready_count="
        f"{report['broker_reconciliation_postmortem_link_ready_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_paper_order_submit_allowed_count="
        f"{report['broker_reconciliation_paper_order_submit_allowed_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_broker_write_allowed_count="
        f"{report['broker_reconciliation_broker_write_allowed_count']}"
    )
    print(
        "phase2_shadow_cycle_broker_reconciliation_live_capital_enabled_count="
        f"{report['broker_reconciliation_live_capital_enabled_count']}"
    )
    print(f"phase2_shadow_cycle_paper_submit_receipt_status={report['paper_submit_receipt_status']}")
    print(f"phase2_shadow_cycle_paper_submit_receipt_review_count={report['paper_submit_receipt_review_count']}")
    print(
        "phase2_shadow_cycle_paper_submit_receipt_blocked_before_count="
        f"{report['paper_submit_receipt_blocked_before_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_dry_run_blocked_count="
        f"{report['paper_submit_receipt_dry_run_blocked_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_dry_run_ready_count="
        f"{report['paper_submit_receipt_dry_run_ready_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_dry_run_created_count="
        f"{report['paper_submit_receipt_dry_run_created_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_paper_order_submitted_count="
        f"{report['paper_submit_receipt_paper_order_submitted_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_broker_post_called_count="
        f"{report['paper_submit_receipt_broker_post_called_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_broker_write_allowed_count="
        f"{report['paper_submit_receipt_broker_write_allowed_count']}"
    )
    print(
        "phase2_shadow_cycle_paper_submit_receipt_live_capital_enabled_count="
        f"{report['paper_submit_receipt_live_capital_enabled_count']}"
    )
    print(f"phase2_shadow_cycle_local_research_status={report['local_research_status']}")
    print(f"phase2_shadow_cycle_local_research_mode={report['local_research_mode']}")
    print(f"phase2_shadow_cycle_paper_account_context_status={report['paper_account_context_status']}")
    print(f"phase2_shadow_cycle_paper_account_connection_status={report['paper_account_connection_status']}")
    print(f"phase2_shadow_cycle_paper_account_current_balance_gbp={report['paper_account_current_balance_gbp']}")
    print(f"phase2_shadow_cycle_paper_account_order_count={report['paper_account_order_count']}")
    print(f"phase2_shadow_cycle_paper_account_open_position_count={report['paper_account_open_position_count']}")
    print(f"phase2_shadow_cycle_paper_account_write_authority={report['paper_account_write_authority']}")
    print(f"phase2_shadow_cycle_paper_account_live_capital_enabled={report['paper_account_live_capital_enabled']}")
    print(f"phase2_shadow_cycle_strategy_lead_status={report['strategy_lead_status']}")
    print(f"phase2_shadow_cycle_strategy_lead_execution_allowed={report['strategy_lead_execution_allowed']}")
    print(f"phase2_shadow_cycle_strategy_lead_paper_order_allowed={report['strategy_lead_paper_order_allowed']}")
    print(f"phase2_shadow_cycle_strategy_lead_source_mode={report['strategy_lead_source_mode']}")
    print(f"phase2_shadow_cycle_strategy_lead_source_posture={report['strategy_lead_source_posture']}")
    print(f"phase2_shadow_cycle_strategy_lead_review_mode={report['strategy_lead_review_mode']}")
    print(f"phase2_shadow_cycle_strategy_lead_evidence_pressure={report['strategy_lead_evidence_pressure']}")
    print(f"phase2_shadow_cycle_strategy_lead_required_challenge_count={report['strategy_lead_required_challenge_count']}")
    print(
        "phase2_shadow_cycle_strategy_lead_preference_mcp_context_status="
        f"{report['strategy_lead_preference_mcp_context_status']}"
    )
    print(
        "phase2_shadow_cycle_strategy_lead_preference_mcp_challenge_count="
        f"{report['strategy_lead_preference_mcp_challenge_count']}"
    )
    print(
        "phase2_shadow_cycle_strategy_lead_strategy_research_context_status="
        f"{report['strategy_lead_strategy_research_context_status']}"
    )
    print(
        "phase2_shadow_cycle_strategy_lead_strategy_research_candidate_count="
        f"{report['strategy_lead_strategy_research_candidate_count']}"
    )
    print(
        "phase2_shadow_cycle_strategy_lead_strategy_research_challenge_count="
        f"{report['strategy_lead_strategy_research_challenge_count']}"
    )
    print(f"phase2_shadow_cycle_strategy_lead_risk_handoff_allowed={report['strategy_lead_risk_handoff_allowed']}")
    print(f"phase2_shadow_cycle_strategy_lead_trade_candidate_allowed={report['strategy_lead_trade_candidate_allowed']}")
    print(f"phase2_shadow_cycle_report_path={report['report_path']}")
    print(f"phase2_shadow_cycle_boundary={report['boundary']}")
    for result in report["source_results"]:
        print(
            "phase2_shadow_cycle_source="
            + ",".join(
                [
                    result["source_key"],
                    result["status"],
                    f"events={result['event_count']}",
                    f"queued={result['queued_packet_count']}",
                    f"reason={result['degraded_reason'] or 'none'}",
                ]
            )
        )

    if report["status"] != "ok":
        return 1
    if args.durable_replay and report["durable_replay_contract_status"] not in {
        "durable_phase2_replay_ready",
        "durable_replay_ready",
    }:
        return 1
    if args.durable_replay and report["durable_replay_missing_source_count"] != 0:
        return 1
    if report["durable_replay_write_authority"] or report["durable_replay_signal_authority"]:
        return 1
    if report["durable_replay_order_authority"]:
        return 1
    if report["preference_mcp_shadow_context_status"] != "challenge_only_ready":
        return 1
    if report["preference_mcp_shadow_context_role"] != "read_only_shadow_challenge_context":
        return 1
    if report["preference_mcp_shadow_observation_count"] < 1:
        return 1
    if report["preference_mcp_active_required_challenge_count"] < 1:
        return 1
    if report["preference_mcp_source_quorum_credit_allowed"]:
        return 1
    if report["preference_mcp_trade_candidate_creation_allowed"]:
        return 1
    if report["preference_mcp_risk_handoff_allowed"]:
        return 1
    if report["preference_mcp_execution_allowed"] or report["preference_mcp_broker_write_allowed"]:
        return 1
    if report["tradingview_mcp_source_quorum_credit_allowed"]:
        return 1
    if report["tradingview_mcp_trade_candidate_creation_allowed"]:
        return 1
    if report["tradingview_mcp_risk_handoff_allowed"]:
        return 1
    if report["tradingview_mcp_execution_allowed"]:
        return 1
    if report["tradingview_mcp_paper_order_allowed"] or report["tradingview_mcp_broker_write_allowed"]:
        return 1
    if report["bookmap_local_bridge_context_role"] != "read_only_supplemental_orderflow_confirmation":
        return 1
    if report["bookmap_local_bridge_source_quorum_credit_allowed"]:
        return 1
    if report["bookmap_local_bridge_trade_candidate_creation_allowed"]:
        return 1
    if report["bookmap_local_bridge_risk_handoff_allowed"]:
        return 1
    if report["bookmap_local_bridge_execution_allowed"]:
        return 1
    if report["bookmap_local_bridge_paper_order_allowed"] or report["bookmap_local_bridge_broker_write_allowed"]:
        return 1
    if report["bookmap_order_injection_allowed"] or report["bookmap_trading_mode_allowed"]:
        return 1
    if report["strategy_research_intake_status"] != "ready_for_strategy_review":
        return 1
    if report["strategy_research_candidate_count"] != 4:
        return 1
    if report["strategy_research_challenge_count"] < 4:
        return 1
    if report["strategy_research_trade_candidate_creation_allowed"]:
        return 1
    if report["strategy_research_risk_handoff_allowed"]:
        return 1
    if report["strategy_research_execution_allowed"]:
        return 1
    if report["strategy_research_paper_order_allowed"]:
        return 1
    if report["strategy_research_broker_write_allowed"]:
        return 1
    if report["research_goal_hardening"].get("status") != "ok":
        return 1
    if report["research_goal_hardening_version"] != "rs2_2026_06_03":
        return 1
    if report["research_goal_candidate_ready_count"] < 0:
        return 1
    if report["research_goal_closed_no_trade_count"] < 0:
        return 1
    if report["research_goal_stale_goal_count"] < 0:
        return 1
    if report["research_goal_expired_goal_count"] < 0:
        return 1
    if report["market_context_status"] != "ok":
        return 1
    if report["market_context_packet_version"] != "rs3_2026_06_03":
        return 1
    if report["market_context_packet_count"] < 1:
        return 1
    if report["market_context_average_source_quality_score"] <= 0:
        return 1
    if report["market_context_average_trust_score"] <= 0:
        return 1
    if report["market_context_execution_allowed_count"] != 0:
        return 1
    if report["market_context_paper_order_allowed_count"] != 0:
        return 1
    if report["market_context_trade_candidate_creation_allowed_count"] != 0:
        return 1
    if report["market_context_risk_handoff_allowed_count"] != 0:
        return 1
    if report["market_context_broker_write_allowed_count"] != 0:
        return 1
    if report["market_context_live_capital_enabled_count"] != 0:
        return 1
    if report["market_context_source_quorum_credit_allowed_count"] != 0:
        return 1
    if report["strategy_lead_strategy_research_context_status"] != "ready_for_strategy_review":
        return 1
    if report["strategy_lead_strategy_research_candidate_count"] != 4:
        return 1
    if report["strategy_lead_strategy_research_challenge_count"] < 4:
        return 1
    if report["strategy_lead_execution_allowed"] or report["strategy_lead_paper_order_allowed"]:
        return 1
    if report["strategy_lead_risk_handoff_allowed"] or report["strategy_lead_trade_candidate_allowed"]:
        return 1
    if report["paper_account_write_authority"] or report["paper_account_live_capital_enabled"]:
        return 1
    if report["signal_integrity_trade_candidate_created_count"] != 0:
        return 1
    if report["risk_agent_execution_allowed_count"] != 0:
        return 1
    if report["risk_agent_paper_order_allowed_count"] != 0:
        return 1
    if report["risk_agent_order_created_count"] != 0:
        return 1
    if report["risk_agent_broker_write_allowed_count"] != 0:
        return 1
    if report["execution_policy_execution_allowed_count"] != 0:
        return 1
    if report["execution_policy_staged_paper_order_allowed_count"] != 0:
        return 1
    if report["execution_policy_paper_order_created_count"] != 0:
        return 1
    if report["execution_policy_broker_write_allowed_count"] != 0:
        return 1
    if report["execution_policy_live_capital_enabled_count"] != 0:
        return 1
    if report["staged_paper_order_execution_allowed_count"] != 0:
        return 1
    if report["staged_paper_order_created_count"] != 0:
        return 1
    if report["staged_paper_order_submittable_count"] != 0:
        return 1
    if report["staged_paper_order_broker_write_allowed_count"] != 0:
        return 1
    if report["staged_paper_order_live_capital_enabled_count"] != 0:
        return 1
    if report["broker_reconciliation_idempotency_key_allocated_count"] != 0:
        return 1
    if report["broker_reconciliation_event_log_prewrite_created_count"] != 0:
        return 1
    if report["broker_reconciliation_pre_trade_snapshot_created_count"] != 0:
        return 1
    if report["broker_reconciliation_duplicate_order_guard_ready_count"] != 0:
        return 1
    if report["broker_reconciliation_broker_echo_verified_count"] != 0:
        return 1
    if report["broker_reconciliation_post_submit_reconciliation_ready_count"] != 0:
        return 1
    if report["broker_reconciliation_postmortem_link_ready_count"] != 0:
        return 1
    if report["broker_reconciliation_paper_order_submit_allowed_count"] != 0:
        return 1
    if report["broker_reconciliation_broker_write_allowed_count"] != 0:
        return 1
    if report["broker_reconciliation_live_capital_enabled_count"] != 0:
        return 1
    if report["paper_submit_receipt_paper_order_submitted_count"] != 0:
        return 1
    if report["paper_submit_receipt_broker_post_called_count"] != 0:
        return 1
    if report["paper_submit_receipt_broker_write_allowed_count"] != 0:
        return 1
    if report["paper_submit_receipt_live_capital_enabled_count"] != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
