#!/usr/bin/env python3
"""Validate the read-only Bookmap local bridge adapter."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import orchestrator.bookmap_local_bridge as bookmap_module  # noqa: E402
from orchestrator.bookmap_local_bridge import (  # noqa: E402
    bookmap_local_bridge_evidence_items,
    bookmap_local_bridge_packet_context,
    bookmap_local_bridge_status,
    fetch_bookmap_local_bridge_live,
    fetch_bookmap_local_bridge_sample,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.evidence_packet_normalization import (  # noqa: E402
    normalize_adapter_evidence_packet,
    validate_normalized_evidence_packet,
)
from orchestrator.phase2_shadow_cycle import run_phase2_shadow_cycle  # noqa: E402

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


def _with_env(values: dict[str, str | None], callback: Any) -> Any:
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return callback()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _live_fixture_check() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixture_payload = {
        "records": [
            {
                "symbol": "CL",
                "instrument_name": "Fixture crude orderflow",
                "venue": "fixture_bookmap",
                "timeframe": "intraday",
                "bridge_channel": "fixture_snapshot",
                "setup_type": "fixture_absorption_watch",
                "direction": "watch_breakout_or_reversal",
                "orderflow_score": 0.71,
                "liquidity_state": "fixture_liquidity_shelf",
                "absorption_state": "fixture_absorption",
                "imbalance_state": "fixture_balanced",
                "support_resistance": {
                    "support": "fixture support",
                    "resistance": "fixture resistance",
                },
                "candidate_watchlist_context": "Fixture Bookmap context remains supplemental.",
                "obvious_orderflow_context_flag": True,
            }
        ]
    }
    original_snapshot = bookmap_module._http_snapshot

    def _fixture_snapshot(url: str, settings: Settings) -> dict[str, Any]:
        if not url.startswith("http://127.0.0.1:8765/"):
            raise AssertionError("fixture snapshot called with non-loopback URL")
        return fixture_payload

    def _run() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        settings = Settings.from_env()
        bookmap_module._http_snapshot = _fixture_snapshot
        try:
            envelope = fetch_bookmap_local_bridge_live()
        finally:
            bookmap_module._http_snapshot = original_snapshot
        status = bookmap_local_bridge_status(settings)
        context = bookmap_local_bridge_packet_context(settings)
        return envelope, status, context

    return _with_env(
        {
            "BOOKMAP_BRIDGE_URL": "http://127.0.0.1:8765/bookmap",
            "BOOKMAP_LOCAL_BRIDGE_LIVE_PROBE_ENABLED": "true",
            "BOOKMAP_LOCAL_BRIDGE_ENABLED": "true",
        },
        _run,
    )


def _nonlocal_block_check() -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        return fetch_bookmap_local_bridge_live()

    return _with_env(
        {
            "BOOKMAP_BRIDGE_URL": "https://example.com/bookmap",
            "BOOKMAP_LOCAL_BRIDGE_LIVE_PROBE_ENABLED": "true",
            "BOOKMAP_LOCAL_BRIDGE_ENABLED": "true",
        },
        _run,
    )


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    sample_envelope = fetch_bookmap_local_bridge_sample()
    sample_evidence = bookmap_local_bridge_evidence_items(sample_envelope)
    normalized_packet = normalize_adapter_evidence_packet(
        source_key="bookmap",
        evidence_items=sample_evidence,
        packet_type="orderflow_confirmation_packet",
        context_role="supplemental_orderflow_confirmation_only",
        summary="Bookmap local order-flow context normalized for review only.",
    )
    normalized_packet_errors = validate_normalized_evidence_packet(normalized_packet)
    live_envelope, live_status, live_context = _live_fixture_check()
    nonlocal_envelope = _nonlocal_block_check()
    phase2_report = run_phase2_shadow_cycle(
        sources=("bookmap", "rss"),
        live_sources=False,
        durable_replay=False,
        live_local_llm=False,
        events_per_source=1,
        research_limit=4,
        settings=settings,
    )

    sample_events = sample_envelope.get("events", [])
    live_events = live_envelope.get("events", [])
    sample_event_count = len(sample_events) if isinstance(sample_events, list) else 0
    live_event_count = len(live_events) if isinstance(live_events, list) else 0
    authority_values = {
        "status_signal_authority": live_status.get("signal_authority"),
        "status_risk_approval_authority": live_status.get("risk_approval_authority"),
        "status_trade_candidate_creation_allowed": live_status.get("trade_candidate_creation_allowed"),
        "status_execution_allowed": live_status.get("execution_allowed"),
        "status_paper_order_allowed": live_status.get("paper_order_allowed"),
        "status_broker_write_allowed": live_status.get("broker_write_allowed"),
        "status_bookmap_order_injection_allowed": live_status.get("bookmap_order_injection_allowed"),
        "status_bookmap_trading_mode_allowed": live_status.get("bookmap_trading_mode_allowed"),
        "status_quantum_job_authority": live_status.get("quantum_job_authority"),
        "status_live_capital_enabled": live_status.get("live_capital_enabled"),
        "context_source_quorum_credit_allowed": live_context.get("source_quorum_credit_allowed"),
        "context_trade_candidate_creation_allowed": live_context.get("trade_candidate_creation_allowed"),
        "context_risk_handoff_allowed": live_context.get("risk_handoff_allowed"),
        "context_execution_allowed": live_context.get("execution_allowed"),
        "context_paper_order_allowed": live_context.get("paper_order_allowed"),
        "context_broker_write_allowed": live_context.get("broker_write_allowed"),
        "phase2_bookmap_trade_candidate_creation_allowed": phase2_report.get(
            "bookmap_local_bridge_trade_candidate_creation_allowed"
        ),
        "phase2_bookmap_risk_handoff_allowed": phase2_report.get(
            "bookmap_local_bridge_risk_handoff_allowed"
        ),
        "phase2_bookmap_execution_allowed": phase2_report.get("bookmap_local_bridge_execution_allowed"),
        "phase2_bookmap_paper_order_allowed": phase2_report.get("bookmap_local_bridge_paper_order_allowed"),
        "phase2_bookmap_broker_write_allowed": phase2_report.get("bookmap_local_bridge_broker_write_allowed"),
        "phase2_bookmap_order_injection_allowed": phase2_report.get("bookmap_order_injection_allowed"),
        "phase2_bookmap_trading_mode_allowed": phase2_report.get("bookmap_trading_mode_allowed"),
        "phase2_signal_integrity_trade_candidate_created_count": phase2_report.get(
            "signal_integrity_trade_candidate_created_count"
        ),
        "phase2_risk_agent_order_created_count": phase2_report.get("risk_agent_order_created_count"),
        "phase2_execution_policy_paper_order_created_count": phase2_report.get(
            "execution_policy_paper_order_created_count"
        ),
        "phase2_paper_submit_receipt_broker_post_called_count": phase2_report.get(
            "paper_submit_receipt_broker_post_called_count"
        ),
        "phase2_paper_submit_receipt_paper_order_submitted_count": phase2_report.get(
            "paper_submit_receipt_paper_order_submitted_count"
        ),
    }
    authority_leaks = [key for key, value in authority_values.items() if bool(value)]

    if sample_event_count < 1:
        errors.append("sample_event_count_empty")
    if not sample_evidence:
        errors.append("sample_evidence_empty")
    if normalized_packet_errors:
        errors.append("normalized_packet_invalid:" + ",".join(normalized_packet_errors[:5]))
    if live_status.get("status") != "connected":
        errors.append("fixture_live_not_connected")
    if live_event_count < 1:
        errors.append("fixture_live_event_count_empty")
    if live_context.get("context_role") != "read_only_supplemental_orderflow_confirmation":
        errors.append("context_role_mismatch")
    if int(live_context.get("orderflow_context_count", 0) or 0) < 1:
        errors.append("orderflow_context_count_empty")
    if nonlocal_envelope.get("degraded_reason") != "nonlocal_bridge_url_blocked":
        errors.append("nonlocal_url_not_blocked")
    if phase2_report.get("bookmap_local_bridge_context_role") != (
        "read_only_supplemental_orderflow_confirmation"
    ):
        errors.append("phase2_bookmap_context_role_mismatch")
    if phase2_report.get("queued_packet_count", 0) < 2:
        errors.append("phase2_queue_not_fed")
    if authority_leaks:
        errors.append("authority_leak:" + ",".join(authority_leaks))
    public_payload = {
        "status": live_status,
        "context": live_context,
        "phase2_bookmap": {
            key: phase2_report.get(key)
            for key in (
                "bookmap_local_bridge_status",
                "bookmap_local_bridge_context_role",
                "bookmap_local_bridge_orderflow_context_count",
                "bookmap_local_bridge_execution_allowed",
                "bookmap_local_bridge_paper_order_allowed",
                "bookmap_local_bridge_broker_write_allowed",
                "bookmap_order_injection_allowed",
                "bookmap_trading_mode_allowed",
            )
        },
    }
    if _contains_secret_like_value(public_payload):
        errors.append("secret_like_value_in_public_output")

    print("bookmap_local_bridge_status=" + ("ok" if not errors else "error"))
    print(f"bookmap_local_bridge_sample_event_count={sample_event_count}")
    print(f"bookmap_local_bridge_sample_evidence_count={len(sample_evidence)}")
    print(f"bookmap_local_bridge_normalized_packet_status={normalized_packet.get('status')}")
    print(f"bookmap_local_bridge_normalized_packet_item_count={normalized_packet.get('item_count')}")
    print(f"bookmap_local_bridge_fixture_connected={live_status.get('connected')}")
    print(f"bookmap_local_bridge_fixture_event_count={live_event_count}")
    print(f"bookmap_local_bridge_context_count={live_context.get('orderflow_context_count')}")
    print(
        "bookmap_local_bridge_phase2_queued_packet_count="
        f"{phase2_report.get('queued_packet_count')}"
    )
    print("bookmap_local_bridge_execution_allowed=False")
    print("bookmap_local_bridge_paper_order_allowed=False")
    print("bookmap_local_bridge_broker_write_allowed=False")
    print("bookmap_local_bridge_bookmap_order_injection_allowed=False")
    print("bookmap_local_bridge_bookmap_trading_mode_allowed=False")
    print(
        "bookmap_local_bridge_boundary="
        "Bookmap observes local orderflow; Qadam governs; Alpaca Paper executes."
    )
    for error in errors:
        print(f"bookmap_local_bridge_error={error}")
    if errors:
        return 1
    print("bookmap_local_bridge_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
