#!/usr/bin/env python3
"""Validate truthful, read-only TradingView supplemental-adapter state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.evidence_packet_normalization import (  # noqa: E402
    normalize_adapter_evidence_packet,
    validate_normalized_evidence_packet,
)
from orchestrator.tradingview_mcp_adapter import (  # noqa: E402
    TRADINGVIEW_MCP_CONNECTION_STATES,
    fetch_tradingview_mcp_live,
    fetch_tradingview_mcp_sample,
    tradingview_mcp_adapter_status,
    tradingview_mcp_evidence_items,
    tradingview_mcp_packet_context,
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


def main() -> int:
    live = "--live" in sys.argv
    settings = Settings.from_env()
    envelope = fetch_tradingview_mcp_live() if live else fetch_tradingview_mcp_sample()
    status = tradingview_mcp_adapter_status(settings)
    context = tradingview_mcp_packet_context(settings)
    evidence_items = tradingview_mcp_evidence_items(envelope)
    normalized_packet = normalize_adapter_evidence_packet(
        source_key="tradingview_mcp",
        evidence_items=evidence_items,
        packet_type="technical_confirmation_packet",
        context_role="supplemental_technical_confirmation_only",
        summary="TradingView supplemental technical-analysis context for review only.",
    )
    normalized_errors = validate_normalized_evidence_packet(normalized_packet)
    events = envelope.get("events") if isinstance(envelope.get("events"), list) else []
    connection_state = str(status.get("connection_state") or status.get("status") or "")
    authority_fields = (
        "signal_authority",
        "risk_approval_authority",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "quantum_job_authority",
        "live_capital_enabled",
    )
    errors: list[str] = []
    if connection_state not in TRADINGVIEW_MCP_CONNECTION_STATES:
        errors.append("connection_state_invalid")
    if status.get("status") != connection_state:
        errors.append("status_connection_state_mismatch")
    if status.get("connected") is not (connection_state == "live_supplemental"):
        errors.append("connected_flag_not_derived_from_live_state")
    if int(status.get("sample_records_in_canonical_context_count") or 0) != 0:
        errors.append("sample_record_leaked_into_canonical_context")
    if live and connection_state == "live_supplemental":
        if not events or not evidence_items:
            errors.append("live_state_without_provider_records")
        if any(event.get("raw_payload", {}).get("sample") is True for event in events):
            errors.append("live_state_contains_sample_record")
        for event in events:
            raw = event.get("raw_payload") if isinstance(event.get("raw_payload"), dict) else {}
            for field in (
                "provider_symbol",
                "venue",
                "retrieved_at",
                "provider_response_sha256",
                "terms_note",
            ):
                if raw.get(field) in {None, ""}:
                    errors.append(f"live_provenance_missing:{field}")
    if not live:
        if not events or not evidence_items:
            errors.append("sample_fixture_empty")
        if any(event.get("raw_payload", {}).get("sample") is not True for event in events):
            errors.append("sample_fixture_origin_missing")
    if evidence_items and normalized_errors:
        errors.append("normalized_packet_invalid:" + ",".join(normalized_errors[:5]))
    if context.get("context_role") != "read_only_supplemental_technical_confirmation":
        errors.append("context_role_mismatch")
    authority_leaks = [field for field in authority_fields if bool(status.get(field))]
    if authority_leaks:
        errors.append("authority_leak:" + ",".join(authority_leaks))
    if _contains_secret_like_value(status) or _contains_secret_like_value(context):
        errors.append("secret_like_value_in_output")

    print("tradingview_mcp_adapter_check=" + ("ok" if not errors else "error"))
    print(f"tradingview_mcp_connection_state={connection_state}")
    print(f"tradingview_mcp_connected={status.get('connected')}")
    print(f"tradingview_mcp_live_calls_enabled={status.get('live_calls_enabled')}")
    print(f"tradingview_mcp_ta_importable={status.get('tradingview_ta_importable')}")
    print(f"tradingview_mcp_screener_importable={status.get('tradingview_screener_importable')}")
    print(f"tradingview_mcp_event_count={len(events)}")
    print(f"tradingview_mcp_canonical_sample_count={status.get('sample_records_in_canonical_context_count')}")
    print("tradingview_mcp_source_quorum_credit_allowed=False")
    print("tradingview_mcp_execution_allowed=False")
    print("tradingview_mcp_paper_order_allowed=False")
    print("tradingview_mcp_broker_write_allowed=False")
    for error in errors:
        print(f"tradingview_mcp_adapter_error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
