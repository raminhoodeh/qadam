#!/usr/bin/env python3
"""Validate the read-only TradingView MCP technical-analysis adapter."""

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
from orchestrator.phase2_shadow_cycle import run_phase2_shadow_cycle  # noqa: E402
from orchestrator.tradingview_mcp_adapter import (  # noqa: E402
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
    events = envelope.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    phase2_report = run_phase2_shadow_cycle(
        sources=("tradingview_mcp", "rss"),
        live_sources=False,
        durable_replay=False,
        live_local_llm=False,
        events_per_source=1,
        research_limit=4,
        settings=settings,
    )

    authority_values = {
        "status_signal_authority": status.get("signal_authority"),
        "status_risk_approval_authority": status.get("risk_approval_authority"),
        "status_trade_candidate_creation_allowed": status.get("trade_candidate_creation_allowed"),
        "status_execution_allowed": status.get("execution_allowed"),
        "status_paper_order_allowed": status.get("paper_order_allowed"),
        "status_broker_write_allowed": status.get("broker_write_allowed"),
        "status_quantum_job_authority": status.get("quantum_job_authority"),
        "status_live_capital_enabled": status.get("live_capital_enabled"),
        "context_source_quorum_credit_allowed": context.get("source_quorum_credit_allowed"),
        "context_trade_candidate_creation_allowed": context.get("trade_candidate_creation_allowed"),
        "context_risk_handoff_allowed": context.get("risk_handoff_allowed"),
        "context_execution_allowed": context.get("execution_allowed"),
        "context_paper_order_allowed": context.get("paper_order_allowed"),
        "context_broker_write_allowed": context.get("broker_write_allowed"),
        "phase2_tradingview_trade_candidate_creation_allowed": phase2_report.get(
            "tradingview_mcp_trade_candidate_creation_allowed"
        ),
        "phase2_tradingview_risk_handoff_allowed": phase2_report.get(
            "tradingview_mcp_risk_handoff_allowed"
        ),
        "phase2_tradingview_execution_allowed": phase2_report.get("tradingview_mcp_execution_allowed"),
        "phase2_tradingview_paper_order_allowed": phase2_report.get(
            "tradingview_mcp_paper_order_allowed"
        ),
        "phase2_tradingview_broker_write_allowed": phase2_report.get(
            "tradingview_mcp_broker_write_allowed"
        ),
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
    errors: list[str] = []
    if status.get("status") != "connected":
        errors.append("adapter_not_connected")
    if event_count < 1:
        errors.append("event_count_empty")
    if not evidence_items:
        errors.append("evidence_items_empty")
    if context.get("context_role") != "read_only_supplemental_technical_confirmation":
        errors.append("context_role_mismatch")
    if int(context.get("technical_context_count", 0) or 0) < 1:
        errors.append("technical_context_count_empty")
    if phase2_report.get("tradingview_mcp_status") not in {
        "technical_context_recorded",
        "not_initialized",
    }:
        errors.append("phase2_tradingview_status_unexpected")
    if phase2_report.get("tradingview_mcp_context_role") != (
        "read_only_supplemental_technical_confirmation"
    ):
        errors.append("phase2_tradingview_context_role_mismatch")
    if phase2_report.get("queued_packet_count", 0) < 2:
        errors.append("phase2_queue_not_fed")
    if authority_leaks:
        errors.append("authority_leak:" + ",".join(authority_leaks))
    if _contains_secret_like_value(status) or _contains_secret_like_value(context):
        errors.append("secret_like_value_in_output")

    print("tradingview_mcp_adapter_status=" + ("ok" if not errors else "error"))
    print(f"tradingview_mcp_adapter_connected={status.get('connected')}")
    print(f"tradingview_mcp_adapter_local_checkout_exists={status.get('local_checkout_exists')}")
    print(f"tradingview_mcp_adapter_mcp_config_exists={status.get('mcp_config_exists')}")
    print(f"tradingview_mcp_adapter_package_importable={status.get('package_importable')}")
    print(f"tradingview_mcp_adapter_service_importable={status.get('service_importable')}")
    print(f"tradingview_mcp_adapter_live_calls_enabled={status.get('live_calls_enabled')}")
    print(f"tradingview_mcp_adapter_event_count={event_count}")
    print(f"tradingview_mcp_adapter_evidence_item_count={len(evidence_items)}")
    print(f"tradingview_mcp_adapter_context_count={context.get('technical_context_count')}")
    print(
        "tradingview_mcp_adapter_phase2_queued_packet_count="
        f"{phase2_report.get('queued_packet_count')}"
    )
    print(
        "tradingview_mcp_adapter_phase2_strategy_challenge_count="
        f"{phase2_report.get('strategy_lead_required_challenge_count')}"
    )
    print("tradingview_mcp_adapter_execution_allowed=False")
    print("tradingview_mcp_adapter_paper_order_allowed=False")
    print("tradingview_mcp_adapter_broker_write_allowed=False")
    print(
        "tradingview_mcp_adapter_boundary="
        "TradingView MCP observes and analyses; Alpaca Paper executes; Qadam governs."
    )
    for error in errors:
        print(f"tradingview_mcp_adapter_error={error}")
    if errors:
        return 1
    print("tradingview_mcp_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
