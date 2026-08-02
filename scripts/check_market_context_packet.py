#!/usr/bin/env python3
"""Validate RS-3 market context packets and source-quality boundaries."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.market_context import (  # noqa: E402
    MARKET_CONTEXT_PACKET_VERSION,
    MARKET_CONTEXT_SCHEMA_VERSION,
    run_market_context_packet_cycle,
    validate_market_context_packet,
)
from orchestrator.research_goal import ensure_sample_research_goals  # noqa: E402

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _contains_secret_like_value(payload: object) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def main() -> int:
    settings = Settings.from_env()
    seed = ensure_sample_research_goals(settings=settings)
    report = run_market_context_packet_cycle(settings=settings, limit=8)
    packets = report.get("recent_packets", [])
    errors: list[str] = []

    print(f"market_context_packet_status={report.get('status')}")
    print(f"market_context_packet_schema_version={report.get('schema_version')}")
    print(f"market_context_packet_version={report.get('packet_version')}")
    print(f"market_context_packet_count={report.get('packet_count')}")
    print(f"market_context_context_ready_count={report.get('context_ready_count')}")
    print(f"market_context_hold_for_context_count={report.get('hold_for_context_count')}")
    print(f"market_context_average_source_quality_score={report.get('average_source_quality_score')}")
    print(f"market_context_average_trust_score={report.get('average_trust_score')}")
    print(f"market_context_yahoo_finance_status={report.get('yahoo_finance_status')}")
    print(f"market_context_alpaca_market_data_status={report.get('alpaca_market_data_status')}")
    print(f"market_context_tradingview_mcp_status={report.get('tradingview_mcp_status')}")
    print(f"market_context_bookmap_local_bridge_status={report.get('bookmap_local_bridge_status')}")
    print(f"market_context_paper_account_context_status={report.get('paper_account_context_status')}")
    print(f"market_context_seed_status={seed.get('status')}")

    if report.get("schema_version") != MARKET_CONTEXT_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if report.get("packet_version") != MARKET_CONTEXT_PACKET_VERSION:
        errors.append("packet_version_mismatch")
    if report.get("status") != "ok":
        errors.append("status_not_ok")
    if int(report.get("packet_count", 0) or 0) < 1:
        errors.append("packet_count_missing")
    if not isinstance(packets, list) or not packets:
        errors.append("recent_packets_missing")
    if _contains_secret_like_value(report):
        errors.append("secret_like_value_detected")

    authority_counts = report.get("authority_counts", {})
    if not isinstance(authority_counts, dict):
        errors.append("authority_counts_missing")
    else:
        for key, value in authority_counts.items():
            if int(value or 0) != 0:
                errors.append(f"authority_count_enabled:{key}")

    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("packet_not_dict")
            continue
        try:
            validate_market_context_packet(packet)
        except Exception as exc:  # noqa: BLE001 - checker reports exact contract failure.
            errors.append(f"packet_validation_error:{exc}")
            continue
        if not str(packet.get("research_goal_id") or "").strip():
            errors.append("packet_research_goal_id_missing")
        taxonomy = packet.get("source_taxonomy")
        if not isinstance(taxonomy, list) or not taxonomy:
            errors.append("packet_source_taxonomy_missing")
        else:
            roles = {row.get("role") for row in taxonomy if isinstance(row, dict)}
            if "supplemental_market_confirmation" not in roles:
                errors.append("packet_yahoo_role_missing")
            if "supplemental_technical_confirmation" not in roles:
                errors.append("packet_tradingview_role_missing")
            if "supplemental_orderflow_confirmation" not in roles:
                errors.append("packet_bookmap_role_missing")
            if "paper_account_context" not in roles:
                errors.append("packet_paper_context_role_missing")
        quality = packet.get("source_quality", {})
        if float(quality.get("trust_score_average", 0) or 0) <= 0:
            errors.append("packet_trust_average_missing")
        if float(quality.get("source_quality_score", 0) or 0) <= 0:
            errors.append("packet_source_quality_score_missing")
        if packet.get("price_volume_context", {}).get("role") != "supplemental_market_confirmation_only":
            errors.append("packet_yahoo_role_not_supplemental")
        if packet.get("technical_context", {}).get("role") != "supplemental_technical_confirmation_only":
            errors.append("packet_tradingview_role_not_supplemental")
        orderflow_context = packet.get("orderflow_context", {})
        if orderflow_context.get("role") != "supplemental_orderflow_confirmation_only":
            errors.append("packet_bookmap_role_not_supplemental")
        for field in (
            "source_quorum_credit_allowed",
            "trade_candidate_creation_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
        ):
            if orderflow_context.get(field) is not False:
                errors.append(f"packet_bookmap_authority_enabled:{field}")
        if packet.get("paper_account_context", {}).get("authority") != "read_only_paper_account_context_only":
            errors.append("packet_paper_context_not_read_only")
        for field in (
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
            "source_quorum_credit_allowed",
        ):
            if packet.get(field) is not False:
                errors.append(f"packet_authority_enabled:{field}")

    for error in errors:
        print(f"market_context_packet_error={error}")
    if errors:
        print("market_context_packet_check=failed")
        return 1
    print("market_context_packet_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
