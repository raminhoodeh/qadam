#!/usr/bin/env python3
"""Validate the Phase 2 Research Goal lifecycle contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.research_goal import (  # noqa: E402
    RESEARCH_GOAL_HARDENING_VERSION,
    RESEARCH_GOAL_SCHEMA_VERSION,
    ResearchGoalStore,
    ensure_sample_research_goals,
    research_goal_summary,
)


def main() -> int:
    settings = Settings.from_env()
    seed_result = ensure_sample_research_goals(settings=settings)
    hardening = ResearchGoalStore(settings=settings).harden_lifecycle()
    summary = research_goal_summary(settings=settings, limit=8)
    authority_counts = summary.get("authority_counts", {})
    recent_goals = summary.get("recent_goals", [])

    print(f"research_goal_lifecycle_status={summary.get('status')}")
    print(f"research_goal_lifecycle_schema_version={summary.get('schema_version')}")
    print(f"research_goal_lifecycle_hardening_version={summary.get('hardening_version')}")
    print(f"research_goal_lifecycle_seed_status={seed_result.get('status')}")
    print(f"research_goal_lifecycle_seed_created_or_updated_count={seed_result.get('created_or_updated_count')}")
    print(f"research_goal_lifecycle_hardened_snapshot_count={hardening.get('appended_hardened_snapshot_count')}")
    print(f"research_goal_lifecycle_record_count={summary.get('goal_record_count', 0)}")
    print(f"research_goal_lifecycle_active_goal_count={summary.get('active_goal_count', 0)}")
    print(f"research_goal_lifecycle_by_status={summary.get('by_status', {})}")
    print(f"research_goal_lifecycle_by_effective_status={summary.get('by_effective_status', {})}")
    print(f"research_goal_lifecycle_by_market_channel={summary.get('by_market_channel', {})}")
    print(f"research_goal_lifecycle_by_priority_label={summary.get('by_priority_label', {})}")
    print(f"research_goal_lifecycle_average_priority_score={summary.get('average_priority_score')}")
    print(f"research_goal_lifecycle_candidate_ready_goal_count={summary.get('candidate_ready_goal_count')}")
    print(f"research_goal_lifecycle_closed_no_trade_goal_count={summary.get('closed_no_trade_goal_count')}")
    print(f"research_goal_lifecycle_stale_goal_count={summary.get('stale_goal_count')}")
    print(f"research_goal_lifecycle_expired_goal_count={summary.get('expired_goal_count')}")
    print(f"research_goal_lifecycle_recent_goal_count={len(recent_goals)}")
    print(f"research_goal_lifecycle_execution_allowed_count={authority_counts.get('execution_allowed', 0)}")
    print(f"research_goal_lifecycle_paper_order_allowed_count={authority_counts.get('paper_order_allowed', 0)}")
    print(
        "research_goal_lifecycle_trade_candidate_creation_allowed_count="
        f"{authority_counts.get('trade_candidate_creation_allowed', 0)}"
    )
    print(f"research_goal_lifecycle_risk_handoff_allowed_count={authority_counts.get('risk_handoff_allowed', 0)}")
    print(f"research_goal_lifecycle_broker_write_allowed_count={authority_counts.get('broker_write_allowed', 0)}")
    print(f"research_goal_lifecycle_live_capital_enabled_count={authority_counts.get('live_capital_enabled', 0)}")
    print(f"research_goal_lifecycle_boundary={summary.get('boundary')}")

    if summary.get("status") != "ok":
        return 1
    if summary.get("schema_version") != RESEARCH_GOAL_SCHEMA_VERSION:
        return 1
    if summary.get("hardening_version") != RESEARCH_GOAL_HARDENING_VERSION:
        return 1
    if seed_result.get("status") != "ok":
        return 1
    if int(summary.get("active_goal_count", 0) or 0) < 2:
        return 1
    if not recent_goals:
        return 1
    if not any(goal.get("market_channel") == "energy_transport" for goal in recent_goals):
        return 1
    if not any(goal.get("market_channel") == "semiconductors" for goal in recent_goals):
        return 1
    for goal in recent_goals:
        if int(goal.get("minimum_source_quorum", 0) or 0) < 2:
            return 1
        if not goal.get("required_sources"):
            return 1
        if not goal.get("watched_instruments"):
            return 1
        if not goal.get("missing_corroboration"):
            return 1
        if goal.get("research_goal_hardening_version") != RESEARCH_GOAL_HARDENING_VERSION:
            return 1
        for score_field in (
            "source_quorum_score",
            "market_confirmation_score",
            "worldview_relevance_score",
            "akber_stage_score",
            "contradiction_score",
            "latency_freshness_score",
            "risk_readiness_score",
            "priority_score",
        ):
            try:
                score = float(goal.get(score_field))
            except (TypeError, ValueError):
                return 1
            if not 0 <= score <= 1:
                return 1
        if goal.get("status") == "candidate_ready" and goal.get("candidate_ready_blockers"):
            return 1
        if goal.get("status") == "closed_no_trade" and not goal.get("close_reason"):
            return 1
        if not goal.get("expires_at"):
            return 1
        if goal.get("priority_label") not in {"low", "medium", "high", "candidate_ready", "closed_no_trade"}:
            return 1
        if "pre-signal research state" not in str(goal.get("boundary", "")):
            return 1
        for field in (
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if goal.get(field) is not False:
                return 1
    if any(int(value or 0) != 0 for value in authority_counts.values()):
        return 1

    print("research_goal_lifecycle_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
