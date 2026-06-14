#!/usr/bin/env python3
"""Validate durable runtime persistence for normalized evidence packets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.bookmap_local_bridge import (  # noqa: E402
    bookmap_local_bridge_evidence_items,
    fetch_bookmap_local_bridge_sample,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.evidence_packet_normalization import (  # noqa: E402
    EVIDENCE_PACKET_NORMALIZATION_VERSION,
    normalize_adapter_evidence_packet,
    normalize_signal_evidence_packet,
)
from orchestrator.evidence_packet_runtime import (  # noqa: E402
    EVIDENCE_PACKET_RUNTIME_VERSION,
    evidence_packet_runtime_paths,
    evidence_packet_runtime_public_status,
    read_evidence_packet_runtime,
    write_evidence_packet_runtime,
)
from orchestrator.intelligence import deterministic_shadow_triage, sample_evidence_items  # noqa: E402
from orchestrator.tradingview_mcp_adapter import (  # noqa: E402
    fetch_tradingview_mcp_sample,
    tradingview_mcp_evidence_items,
)


def _authority_enabled(payload: dict) -> bool:
    fields = (
        "write_authority",
        "signal_authority",
        "risk_handoff_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "quantum_job_authority",
        "performance_credit_allowed",
        "live_capital_enabled",
    )
    return any(payload.get(field) is not False for field in fields)


def main() -> int:
    settings = Settings.from_env()
    signals = deterministic_shadow_triage(sample_evidence_items())
    packets = []
    if signals:
        packets.append(normalize_signal_evidence_packet(signals[0].to_dict()))
    packets.append(
        normalize_adapter_evidence_packet(
            source_key="tradingview_mcp",
            evidence_items=tradingview_mcp_evidence_items(fetch_tradingview_mcp_sample()),
            packet_type="technical_confirmation_packet",
            context_role="supplemental_technical_confirmation_only",
            summary="TradingView MCP sample technical-analysis evidence normalized for runtime replay.",
        )
    )
    packets.append(
        normalize_adapter_evidence_packet(
            source_key="bookmap",
            evidence_items=bookmap_local_bridge_evidence_items(fetch_bookmap_local_bridge_sample()),
            packet_type="orderflow_confirmation_packet",
            context_role="supplemental_orderflow_confirmation_only",
            summary="Bookmap local order-flow evidence normalized for runtime replay.",
        )
    )

    artifact = write_evidence_packet_runtime(packets, settings=settings)
    replayed = read_evidence_packet_runtime(settings)
    public_status = evidence_packet_runtime_public_status(replayed)
    artifact_path, history_path, event_path = evidence_packet_runtime_paths(settings)
    errors: list[str] = []

    if artifact.get("status") != "ok":
        errors.append("artifact_status_not_ok")
    if replayed.get("status") != "ok":
        errors.append("replay_status_not_ok")
    if public_status.get("status") != "ok":
        errors.append("public_status_not_ok")
    if artifact.get("runtime_version") != EVIDENCE_PACKET_RUNTIME_VERSION:
        errors.append("runtime_version_mismatch")
    if artifact.get("normalization_version") != EVIDENCE_PACKET_NORMALIZATION_VERSION:
        errors.append("normalization_version_mismatch")
    if artifact.get("packet_count") != len(packets):
        errors.append("packet_count_mismatch")
    if artifact.get("item_count", 0) < len(packets):
        errors.append("item_count_too_low")
    if artifact.get("authority_leak_count") != 0:
        errors.append("authority_leak_count_nonzero")
    if artifact.get("raw_ref_leak_count") != 0:
        errors.append("raw_ref_leak_count_nonzero")
    if artifact.get("validation_error_count") != 0:
        errors.append("validation_error_count_nonzero")
    if artifact.get("snapshot_written") is not True:
        errors.append("snapshot_not_written")
    if artifact.get("history_appended") is not True:
        errors.append("history_not_appended")
    if artifact.get("event_log_written") is not True:
        errors.append("event_log_not_written")
    if artifact.get("event_log_event_count") != 1:
        errors.append("event_log_count_mismatch")
    if _authority_enabled(public_status):
        errors.append("public_status_authority_enabled")
    if public_status.get("public_safe") is not True:
        errors.append("public_status_not_public_safe")
    if "cannot create source quorum" not in public_status.get("boundary", ""):
        errors.append("runtime_boundary_weak")
    if not artifact_path.exists():
        errors.append("artifact_missing")
    if not history_path.exists():
        errors.append("history_missing")
    if not event_path.exists():
        errors.append("event_log_missing")

    print("evidence_packet_runtime_status=" + ("ok" if not errors else "error"))
    print(f"evidence_packet_runtime_version={public_status.get('runtime_version')}")
    print(f"evidence_packet_runtime_normalization_version={public_status.get('normalization_version')}")
    print(f"evidence_packet_runtime_replay_status={public_status.get('replay_status')}")
    print(f"evidence_packet_runtime_contract_status={public_status.get('contract_status')}")
    print(f"evidence_packet_runtime_packet_count={public_status.get('packet_count')}")
    print(f"evidence_packet_runtime_item_count={public_status.get('item_count')}")
    print(f"evidence_packet_runtime_source_count={public_status.get('source_count')}")
    print(f"evidence_packet_runtime_history_record_count={public_status.get('history_record_count')}")
    print(f"evidence_packet_runtime_event_log_written={public_status.get('event_log_written')}")
    print(f"evidence_packet_runtime_authority_leak_count={public_status.get('authority_leak_count')}")
    print(f"evidence_packet_runtime_raw_ref_leak_count={public_status.get('raw_ref_leak_count')}")
    print(f"evidence_packet_runtime_public_safe={public_status.get('public_safe')}")
    print(f"evidence_packet_runtime_artifact={artifact_path}")
    print(f"evidence_packet_runtime_history={history_path}")
    print(f"evidence_packet_runtime_events={event_path}")
    for error in errors:
        print(f"evidence_packet_runtime_error={error}")
    if errors:
        return 1
    print("evidence_packet_runtime_check=ok")
    print("evidence_packet_runtime_boundary=durable runtime is replay-only and cannot create trading authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
