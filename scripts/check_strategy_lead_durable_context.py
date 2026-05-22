#!/usr/bin/env python3
"""Validate Strategy Lead consumes durable replay context without authority."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase2_shadow_cycle import DEFAULT_PHASE2_SOURCES, run_phase2_shadow_cycle  # noqa: E402
from orchestrator.strategy_lead import StrategyLeadShadowStore  # noqa: E402


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
    packets = StrategyLeadShadowStore(settings=settings).read()
    packet = next(
        (item for item in reversed(packets) if item.get("packet_id") == report["strategy_lead_packet_id"]),
        {},
    )
    source_context = packet.get("source_context", {})
    strategy_review = packet.get("strategy_review", {})

    print(f"strategy_lead_durable_context_status={report['strategy_lead_status']}")
    print(f"strategy_lead_durable_context_packet_id={report['strategy_lead_packet_id']}")
    print(f"strategy_lead_durable_context_source_mode={source_context.get('mode')}")
    print(f"strategy_lead_durable_context_source_posture={strategy_review.get('source_posture')}")
    print(f"strategy_lead_durable_context_review_mode={strategy_review.get('review_mode')}")
    print(f"strategy_lead_durable_context_replayed={source_context.get('durable_replay_replayed_source_count')}")
    print(f"strategy_lead_durable_context_missing={source_context.get('durable_replay_missing_source_count')}")
    print(f"strategy_lead_durable_context_challenge_count={len(strategy_review.get('required_challenges', []))}")

    if report["status"] != "ok":
        return 1
    if not packet:
        return 1
    if source_context.get("mode") != "durable_replay":
        return 1
    if source_context.get("durable_replay_status") != "ok":
        return 1
    if source_context.get("durable_replay_replayed_source_count") != len(DEFAULT_PHASE2_SOURCES):
        return 1
    if source_context.get("durable_replay_missing_source_count") != 0:
        return 1
    if strategy_review.get("review_mode") != "durable_replay_shadow_review":
        return 1
    if strategy_review.get("source_posture") != "durable_replay_complete":
        return 1
    if len(strategy_review.get("required_challenges", [])) < 4:
        return 1
    authority_values = (
        packet.get("execution_allowed"),
        packet.get("paper_order_allowed"),
        source_context.get("write_authority"),
        source_context.get("signal_authority"),
        source_context.get("order_authority"),
        strategy_review.get("risk_handoff_allowed"),
        strategy_review.get("trade_candidate_allowed"),
        strategy_review.get("execution_allowed"),
        strategy_review.get("paper_order_allowed"),
        strategy_review.get("broker_write_allowed"),
    )
    if any(bool(value) for value in authority_values):
        return 1

    print("strategy_lead_durable_context_check=ok")
    print("strategy_lead_durable_context_boundary=Strategy Lead consumes replay context but remains non-executable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
