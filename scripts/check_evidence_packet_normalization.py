#!/usr/bin/env python3
"""Validate canonical evidence packet normalization across source shapes."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.bookmap_local_bridge import (  # noqa: E402
    bookmap_local_bridge_evidence_items,
    fetch_bookmap_local_bridge_sample,
)
from orchestrator.credential_bound_adapters import credential_bound_adapter_registry  # noqa: E402
from orchestrator.evidence_packet_normalization import (  # noqa: E402
    EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION,
    EVIDENCE_PACKET_NORMALIZATION_VERSION,
    normalize_adapter_evidence_packet,
    normalize_signal_evidence_packet,
    validate_normalized_evidence_packet,
)
from orchestrator.intelligence import deterministic_shadow_triage, sample_evidence_items  # noqa: E402
from orchestrator.provider_decision_pass import provider_decision_registry  # noqa: E402
from orchestrator.tradingview_mcp_adapter import (  # noqa: E402
    fetch_tradingview_mcp_sample,
    tradingview_mcp_evidence_items,
)


SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _raw_ref_count(packet: dict[str, Any]) -> int:
    return sum(1 for item in packet.get("items", []) if isinstance(item, dict) and "raw_ref" in item)


def _authority_leak_count(packet: dict[str, Any]) -> int:
    fields = (
        "source_quorum_credit_allowed",
        "risk_handoff_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "performance_credit_allowed",
        "quantum_job_authority",
        "live_capital_enabled",
    )
    item_fields = (
        "source_quorum_credit_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    )
    return sum(1 for field in fields if packet.get(field) is not False) + sum(
        1
        for item in packet.get("items", [])
        if isinstance(item, dict)
        for field in item_fields
        if item.get(field) is not False
    )


def main() -> int:
    errors: list[str] = []
    signals = deterministic_shadow_triage(sample_evidence_items())
    if not signals:
        errors.append("synthetic_shadow_signal_missing")
        shadow_packet = {}
    else:
        shadow_packet = normalize_signal_evidence_packet(signals[0].to_dict())

    tradingview_items = tradingview_mcp_evidence_items(fetch_tradingview_mcp_sample())
    tradingview_packet = normalize_adapter_evidence_packet(
        source_key="tradingview_mcp",
        evidence_items=tradingview_items,
        packet_type="technical_confirmation_packet",
        context_role="supplemental_technical_confirmation_only",
        summary="TradingView MCP sample technical-analysis evidence normalized for review only.",
    )
    bookmap_items = bookmap_local_bridge_evidence_items(fetch_bookmap_local_bridge_sample())
    bookmap_packet = normalize_adapter_evidence_packet(
        source_key="bookmap",
        evidence_items=bookmap_items,
        packet_type="orderflow_confirmation_packet",
        context_role="supplemental_orderflow_confirmation_only",
        summary="Bookmap local order-flow evidence normalized for review only.",
    )

    packets = [shadow_packet, tradingview_packet, bookmap_packet]
    provider_types = [
        packet_type
        for state in provider_decision_registry().get("states", [])
        for packet_type in state.get("evidence_packet_types", [])
    ]
    credential_types = [
        packet_type
        for state in credential_bound_adapter_registry().get("states", [])
        for packet_type in state.get("evidence_packet_types", [])
    ]
    validation_errors = [
        f"{packet.get('packet_id', packet.get('trail_id', 'unknown'))}:{error}"
        for packet in packets
        for error in validate_normalized_evidence_packet(packet)
    ]
    authority_leaks = sum(_authority_leak_count(packet) for packet in packets)
    raw_ref_leaks = sum(_raw_ref_count(packet) for packet in packets)
    secret_like = _contains_secret_like_value(packets)

    if validation_errors:
        errors.append("validation_errors:" + ",".join(validation_errors[:5]))
    if authority_leaks:
        errors.append(f"authority_leaks:{authority_leaks}")
    if raw_ref_leaks:
        errors.append(f"raw_ref_leaks:{raw_ref_leaks}")
    if secret_like:
        errors.append("secret_like_value_in_packets")
    if not provider_types:
        errors.append("provider_evidence_packet_types_missing")
    if not credential_types:
        errors.append("credential_evidence_packet_types_missing")

    print("evidence_packet_normalization_status=" + ("ok" if not errors else "error"))
    print(f"evidence_packet_normalization_schema_version={EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION}")
    print(f"evidence_packet_normalization_version={EVIDENCE_PACKET_NORMALIZATION_VERSION}")
    print(f"evidence_packet_normalization_packet_count={len(packets)}")
    print(f"evidence_packet_normalization_item_count={sum(len(packet.get('items', [])) for packet in packets)}")
    print(f"evidence_packet_normalization_provider_packet_type_count={len(provider_types)}")
    print(f"evidence_packet_normalization_credential_packet_type_count={len(credential_types)}")
    print(f"evidence_packet_normalization_authority_leak_count={authority_leaks}")
    print(f"evidence_packet_normalization_raw_ref_leak_count={raw_ref_leaks}")
    print(f"evidence_packet_normalization_secret_like_value_present={secret_like}")
    print(
        "evidence_packet_normalization_packet_types="
        + ",".join(sorted({packet.get("packet_type", "unknown") for packet in packets}))
    )
    print(
        "evidence_packet_normalization_boundary="
        "read-only evidence normalization; no source quorum, trade, broker, quantum job, proof credit, or live capital authority"
    )
    for error in errors:
        print(f"evidence_packet_normalization_error={error}")
    if errors:
        return 1
    print("evidence_packet_normalization_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
