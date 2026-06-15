#!/usr/bin/env python3
"""Validate the Agent Reach supplemental source-enrichment bridge."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.agent_reach_bridge import (  # noqa: E402
    AGENT_REACH_BRIDGE_CONTEXT_ROLE,
    AGENT_REACH_BRIDGE_PACKET_TYPE,
    agent_reach_bridge_evidence_items,
    validate_agent_reach_bridge_status,
    write_agent_reach_bridge_snapshot,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.evidence_packet_normalization import (  # noqa: E402
    normalize_adapter_evidence_packet,
    validate_normalized_evidence_packet,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bPVZ[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bQzJJC[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _authority_leak_count(payload: dict[str, Any]) -> int:
    authority_fields = (
        "source_quorum_credit_allowed",
        "signal_authority",
        "risk_approval_authority",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "quantum_job_authority",
        "live_capital_enabled",
        "raw_payload_exposed",
        "local_path_exposed",
        "cookies_exposed",
        "browser_session_authority",
    )
    channel_leaks = sum(
        1
        for channel in payload.get("channels", [])
        if isinstance(channel, dict)
        for field in authority_fields
        if channel.get(field) is not False
    )
    return sum(1 for field in authority_fields if payload.get(field) is not False) + channel_leaks


def main() -> int:
    settings = Settings.from_env()
    status = write_agent_reach_bridge_snapshot(settings=settings)
    evidence_items = agent_reach_bridge_evidence_items(status)
    packet = normalize_adapter_evidence_packet(
        source_key="agent_reach",
        evidence_items=evidence_items,
        packet_type=AGENT_REACH_BRIDGE_PACKET_TYPE,
        context_role=AGENT_REACH_BRIDGE_CONTEXT_ROLE,
        summary="Agent Reach social/news/web capability evidence normalized for Qadam review only.",
    )
    errors = validate_agent_reach_bridge_status(status)
    packet_errors = validate_normalized_evidence_packet(packet)
    if packet_errors:
        errors.extend(f"packet:{error}" for error in packet_errors)
    if _contains_secret_like_value(status) or _contains_secret_like_value(packet):
        errors.append("secret_like_value_present")
    authority_leak_count = _authority_leak_count(status)
    if authority_leak_count:
        errors.append(f"authority_leak_count:{authority_leak_count}")
    if status.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if "reddit_credentials_missing" not in status.get("gap_coverage", []):
        errors.append("reddit_gap_coverage_missing")

    print("agent_reach_bridge_status=" + ("ok" if not errors else "error"))
    print(f"agent_reach_bridge_reference_status={status.get('status')}")
    print(f"agent_reach_bridge_channel_file_count={status.get('channel_file_count')}")
    print(f"agent_reach_bridge_mapped_channel_count={status.get('mapped_channel_count')}")
    print(f"agent_reach_bridge_available_mapped_channel_count={status.get('available_mapped_channel_count')}")
    print(f"agent_reach_bridge_selected_runtime_evidence_channel_count={status.get('selected_runtime_evidence_channel_count')}")
    print(f"agent_reach_bridge_qadam_existing_source_match_count={status.get('qadam_existing_source_match_count')}")
    print(f"agent_reach_bridge_canonical_source_count={status.get('canonical_source_count')}")
    print(f"agent_reach_bridge_counts_as_canonical_source={status.get('counts_as_canonical_source')}")
    print(f"agent_reach_bridge_zero_config_channel_count={status.get('zero_config_channel_count')}")
    print(f"agent_reach_bridge_login_or_cookie_channel_count={status.get('login_or_cookie_channel_count')}")
    print(f"agent_reach_bridge_mcp_or_local_setup_channel_count={status.get('mcp_or_local_setup_channel_count')}")
    print(f"agent_reach_bridge_evidence_item_count={len(evidence_items)}")
    print(f"agent_reach_bridge_packet_type={packet.get('packet_type')}")
    print(f"agent_reach_bridge_packet_item_count={packet.get('item_count')}")
    print(f"agent_reach_bridge_authority_leak_count={authority_leak_count}")
    print(f"agent_reach_bridge_secret_like_value_present={_contains_secret_like_value(status) or _contains_secret_like_value(packet)}")
    print(f"agent_reach_bridge_source_quorum_credit_allowed={status.get('source_quorum_credit_allowed')}")
    print(f"agent_reach_bridge_paper_order_allowed={status.get('paper_order_allowed')}")
    print(f"agent_reach_bridge_broker_write_allowed={status.get('broker_write_allowed')}")
    print(f"agent_reach_bridge_live_capital_enabled={status.get('live_capital_enabled')}")
    print("agent_reach_bridge_gap_coverage=" + ",".join(status.get("gap_coverage", [])))
    print(
        "agent_reach_bridge_boundary="
        "read-only supplemental internet/social/news bridge; no source quorum, broker writes, cookies, browser authority, or live capital"
    )
    for error in errors:
        print(f"agent_reach_bridge_error={error}")
    if errors:
        return 1
    print("agent_reach_bridge_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
