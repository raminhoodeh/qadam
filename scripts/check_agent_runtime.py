#!/usr/bin/env python3
"""Check Agent OS runtime permission enforcement."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.agent_runtime import (
    agent_runtime_summary,
    authorize_tool_call,
    create_shadow_triage_packet,
    validate_all_sample_outputs,
)


def main() -> int:
    allow_research = authorize_tool_call("research_analyst", "source_registry")
    block_research = authorize_tool_call("research_analyst", "execution_venues")
    allow_risk = authorize_tool_call("risk_agent", "execution_venues")
    block_broker = authorize_tool_call("strategy_lead", "place_order")
    sample_outputs = validate_all_sample_outputs()
    packet = create_shadow_triage_packet(
        source_event_refs=("sample:nasa_firms:physical_anomaly", "sample:fred:macro_context"),
        summary="Sample shadow triage packet for runtime enforcement validation.",
        uncertainty="medium",
    )
    summary = agent_runtime_summary()

    print("agent_runtime_status=" + summary["status"])
    print(f"agent_runtime_authorization_check_count={summary['authorization_check_count']}")
    print(f"agent_runtime_expected_block_count={summary['expected_block_count']}")
    print(f"agent_runtime_sample_output_count={summary['sample_output_count']}")
    print(f"agent_runtime_shadow_queue_status={summary['shadow_queue_status']}")
    print(f"agent_runtime_shadow_queue_packet_count={summary['shadow_queue_packet_count']}")
    print(f"agent_runtime_sample_outputs_status={sample_outputs['status']}")
    print(f"agent_runtime_allow_research_source_registry={allow_research.allowed}:{allow_research.reason}")
    print(f"agent_runtime_block_research_execution_venues={block_research.allowed}:{block_research.reason}")
    print(f"agent_runtime_allow_risk_execution_venues={allow_risk.allowed}:{allow_risk.reason}")
    print(f"agent_runtime_block_strategy_place_order={block_broker.allowed}:{block_broker.reason}")
    print(f"agent_runtime_shadow_packet_id={packet['packet_id']}")
    print(f"agent_runtime_boundary={summary['boundary']}")

    if not allow_research.allowed:
        print("agent_runtime_research_source_registry_not_allowed=true")
        return 1
    if block_research.allowed:
        print("agent_runtime_research_execution_venues_not_blocked=true")
        return 1
    if not allow_risk.allowed:
        print("agent_runtime_risk_execution_venues_not_allowed=true")
        return 1
    if block_broker.allowed:
        print("agent_runtime_broker_write_not_blocked=true")
        return 1
    if sample_outputs["status"] != "ok":
        print("agent_runtime_sample_outputs_not_ok=true")
        return 1
    if summary["status"] != "ok":
        for error in summary["errors"]:
            print(f"agent_runtime_error={error}")
        return 1

    print("agent_runtime_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
