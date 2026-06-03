#!/usr/bin/env python3
"""Validate Phase 2 shadow intelligence over durable Timescale replay."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase2_shadow_cycle import DEFAULT_PHASE2_SOURCES, run_phase2_shadow_cycle  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    report = run_phase2_shadow_cycle(
        sources=DEFAULT_PHASE2_SOURCES,
        durable_replay=True,
        live_sources=False,
        live_local_llm=False,
        events_per_source=2,
        research_limit=8,
        settings=settings,
    )

    print(f"phase2_durable_replay_cycle_status={report['status']}")
    print(f"phase2_durable_replay_cycle_mode={report['mode']}")
    print(f"phase2_durable_replay_cycle_source_count={report['source_count']}")
    print(f"phase2_durable_replay_cycle_degraded_source_count={report['source_degraded_count']}")
    print(f"phase2_durable_replay_cycle_preference_mcp_status={report['preference_mcp_shadow_context_status']}")
    print(f"phase2_durable_replay_cycle_preference_mcp_role={report['preference_mcp_shadow_context_role']}")
    print(
        "phase2_durable_replay_cycle_preference_mcp_shadow_observation_count="
        f"{report['preference_mcp_shadow_observation_count']}"
    )
    print(
        "phase2_durable_replay_cycle_preference_mcp_active_required_challenge_count="
        f"{report['preference_mcp_active_required_challenge_count']}"
    )
    print(
        "phase2_durable_replay_cycle_preference_mcp_source_quorum_credit_allowed="
        f"{report['preference_mcp_source_quorum_credit_allowed']}"
    )
    print(f"phase2_durable_replay_cycle_observation_count={report['durable_replay_observation_count']}")
    print(f"phase2_durable_replay_cycle_replayed_source_count={report['durable_replay_replayed_source_count']}")
    print(f"phase2_durable_replay_cycle_missing_source_count={report['durable_replay_missing_source_count']}")
    print(f"phase2_durable_replay_cycle_queued_packet_count={report['queued_packet_count']}")
    print(f"phase2_durable_replay_cycle_shadow_signal_count={report['shadow_signal_count']}")
    print(f"phase2_durable_replay_cycle_research_goal_status={report['research_goal_status']}")
    print(f"phase2_durable_replay_cycle_research_goal_active_count={report['research_goal_active_count']}")
    print(
        "phase2_durable_replay_cycle_research_goal_created_or_updated_count="
        f"{report['research_goal_created_or_updated_count']}"
    )
    print(f"phase2_durable_replay_cycle_local_research_status={report['local_research_status']}")
    print(f"phase2_durable_replay_cycle_strategy_lead_status={report['strategy_lead_status']}")
    print(f"phase2_durable_replay_cycle_strategy_source_mode={report['strategy_lead_source_mode']}")
    print(f"phase2_durable_replay_cycle_strategy_source_posture={report['strategy_lead_source_posture']}")
    print(f"phase2_durable_replay_cycle_strategy_review_mode={report['strategy_lead_review_mode']}")
    print(f"phase2_durable_replay_cycle_strategy_evidence_pressure={report['strategy_lead_evidence_pressure']}")
    print(f"phase2_durable_replay_cycle_strategy_challenge_count={report['strategy_lead_required_challenge_count']}")
    print(f"phase2_durable_replay_cycle_report_path={report['report_path']}")
    print(
        "phase2_durable_replay_cycle_authority="
        f"write:{report['durable_replay_write_authority']},"
        f"signal:{report['durable_replay_signal_authority']},"
        f"order:{report['durable_replay_order_authority']},"
        f"strategy_execution:{report['strategy_lead_execution_allowed']},"
        f"strategy_paper_order:{report['strategy_lead_paper_order_allowed']}"
    )

    if report["status"] != "ok":
        return 1
    if report["mode"] != "durable_replay":
        return 1
    if report["durable_replay_contract_status"] != "durable_phase2_replay_ready":
        return 1
    if report["durable_replay_missing_source_count"] != 0:
        return 1
    if report["source_degraded_count"] != 0:
        return 1
    if report["preference_mcp_shadow_context_status"] != "challenge_only_ready":
        return 1
    if report["preference_mcp_shadow_context_role"] != "read_only_shadow_challenge_context":
        return 1
    if report["preference_mcp_shadow_observation_count"] < 1:
        return 1
    if report["preference_mcp_active_required_challenge_count"] < 1:
        return 1
    if report["preference_mcp_source_quorum_credit_allowed"] is not False:
        return 1
    if report["preference_mcp_trade_candidate_creation_allowed"] is not False:
        return 1
    if report["preference_mcp_execution_allowed"] is not False:
        return 1
    if report["preference_mcp_broker_write_allowed"] is not False:
        return 1
    if report["queued_packet_count"] < len(DEFAULT_PHASE2_SOURCES):
        return 1
    if report["shadow_signal_count"] < 1:
        return 1
    if report["research_goal_status"] != "ok":
        return 1
    if report["research_goal_active_count"] < len(DEFAULT_PHASE2_SOURCES):
        return 1
    if report["research_goal_created_or_updated_count"] < len(DEFAULT_PHASE2_SOURCES):
        return 1
    if report["strategy_lead_source_mode"] != "durable_replay":
        return 1
    if report["strategy_lead_source_posture"] != "durable_replay_complete":
        return 1
    if report["strategy_lead_review_mode"] != "durable_replay_shadow_review":
        return 1
    if report["strategy_lead_required_challenge_count"] < 4:
        return 1
    authority_values = (
        report["durable_replay_write_authority"],
        report["durable_replay_signal_authority"],
        report["durable_replay_order_authority"],
        report["local_research_execution_allowed"],
        report["local_research_paper_order_allowed"],
        report["strategy_lead_execution_allowed"],
        report["strategy_lead_paper_order_allowed"],
        report["strategy_lead_risk_handoff_allowed"],
        report["strategy_lead_trade_candidate_allowed"],
        report["signal_integrity_trade_candidate_created_count"],
        report["preference_mcp_trade_candidate_creation_allowed"],
        report["preference_mcp_risk_handoff_allowed"],
        report["preference_mcp_execution_allowed"],
        report["preference_mcp_broker_write_allowed"],
        report["research_goal_execution_allowed_count"],
        report["research_goal_paper_order_allowed_count"],
        report["research_goal_trade_candidate_creation_allowed_count"],
        report["research_goal_risk_handoff_allowed_count"],
        report["research_goal_broker_write_allowed_count"],
        report["research_goal_live_capital_enabled_count"],
        report["risk_agent_execution_allowed_count"],
        report["risk_agent_paper_order_allowed_count"],
        report["execution_policy_execution_allowed_count"],
        report["execution_policy_staged_paper_order_allowed_count"],
        report["staged_paper_order_created_count"],
        report["broker_reconciliation_broker_write_allowed_count"],
        report["paper_submit_receipt_broker_post_called_count"],
        report["paper_submit_receipt_paper_order_submitted_count"],
        report["paper_submit_receipt_live_capital_enabled_count"],
    )
    if any(bool(value) for value in authority_values):
        return 1

    print("phase2_durable_replay_cycle_check=ok")
    print("phase2_durable_replay_cycle_boundary=durable replay is read-only Phase 2 context")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
