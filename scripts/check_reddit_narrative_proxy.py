#!/usr/bin/env python3
"""Validate the Reddit Narrative Proxy contract."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.phase1_live_adapters import fetch_phase1_live_adapter_sample  # noqa: E402
from orchestrator.reddit_narrative_proxy import (  # noqa: E402
    AUTHORITY_FLAGS,
    REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT,
    REDDIT_NARRATIVE_PROXY_SOURCE_KEY,
    REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT,
    build_reddit_narrative_proxy_packet,
    fetch_reddit_narrative_proxy_live_packet,
    validate_reddit_narrative_proxy_packet,
    write_reddit_narrative_proxy_artifact,
)
from orchestrator.signal_integrity import build_signal_integrity_review  # noqa: E402
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS, get_source, source_registry_action_category  # noqa: E402


def _reddit_only_signal_probe() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    item = EvidenceItem(
        evidence_id="reddit_narrative_proxy:safety_probe",
        source="social.reddit_narrative_proxy",
        event_type="social_signal",
        summary="NVDA retail attention is rising in the Reddit Narrative Proxy sample.",
        trust_score=0.46,
        observed_at=now,
        raw_ref="synthetic_reddit_narrative_proxy_probe",
    )
    signal = {
        "schema_version": 1,
        "signal_id": "synthetic_reddit_narrative_proxy_only",
        "status": "shadow_only",
        "title": "Reddit Narrative Proxy only safety probe",
        "instrument_focus": "semiconductors",
        "thesis": "Synthetic probe proving social proxy context cannot create a trade candidate.",
        "confidence": 0.91,
        "invalidation": "Synthetic probe only.",
        "evidence_trail": build_evidence_trail((item,)).to_dict(),
        "generated_by": "reddit_narrative_proxy_safety_probe",
        "execution_allowed": False,
        "created_at": now,
    }
    review = build_signal_integrity_review(signal).to_dict()
    return {
        "probe_id": "reddit_narrative_proxy_only",
        "signal_id": signal["signal_id"],
        "status": review["status"],
        "failure_reasons": review["failure_reasons"],
        "source_count": review["source_count"],
        "trade_candidate_created": review["trade_candidate_created"],
        "execution_allowed": review["execution_allowed"],
        "paper_order_allowed": review["paper_order_allowed"],
        "rejected_as_proxy_only": review["status"] != "passed_to_risk_shadow"
        and review["trade_candidate_created"] is False
        and review["execution_allowed"] is False
        and review["paper_order_allowed"] is False,
    }


def _validate_phase1_sample(sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if sample.get("source") != "social.reddit_narrative_proxy":
        errors.append("phase1_sample_source_mismatch")
    if sample.get("degraded") is not False:
        errors.append("phase1_sample_degraded")
    events = sample.get("events")
    if not isinstance(events, list) or not events:
        errors.append("phase1_sample_events_missing")
        return errors
    for index, event in enumerate(events):
        if event.get("source") != "social.reddit_narrative_proxy":
            errors.append(f"phase1_sample_event_source_mismatch:{index}")
        raw = event.get("raw_payload")
        if not isinstance(raw, dict):
            errors.append(f"phase1_sample_raw_payload_missing:{index}")
            continue
        if raw.get("source_quorum_credit_allowed") is not False:
            errors.append(f"phase1_sample_quorum_authority_enabled:{index}")
        if raw.get("trade_candidate_creation_allowed") is not False:
            errors.append(f"phase1_sample_candidate_authority_enabled:{index}")
    return errors


async def _build_packet(*, settings: Settings, live: bool) -> dict[str, Any]:
    if live:
        result = await fetch_reddit_narrative_proxy_live_packet(settings=settings)
        return result.packet
    return build_reddit_narrative_proxy_packet(settings=settings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Attempt live ApeWisdom fetch; degraded live status is accepted unless --require-live-success is set.")
    parser.add_argument("--require-live-success", action="store_true", help="Fail if --live cannot fetch at least one ApeWisdom endpoint.")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    errors: list[str] = []
    packet = asyncio.run(_build_packet(settings=settings, live=args.live))
    packet_errors = validate_reddit_narrative_proxy_packet(packet)
    errors.extend(packet_errors)

    source = get_source("reddit")
    if len(SOURCE_SPECS) != EXPECTED_SOURCE_COUNT:
        errors.append("source_count_changed")
    if source.status != "adapter_live_via_reddit_narrative_proxy":
        errors.append(f"reddit_source_status_invalid:{source.status}")
    if source_registry_action_category(source) != "no_user_action":
        errors.append(f"reddit_action_category_invalid:{source_registry_action_category(source)}")
    if packet.get("source_registry_slot") != REDDIT_NARRATIVE_PROXY_REGISTRY_SLOT:
        errors.append("source_registry_slot_invalid")
    if packet.get("source_key") != REDDIT_NARRATIVE_PROXY_SOURCE_KEY:
        errors.append("source_key_invalid")
    if packet.get("source_variant") != REDDIT_NARRATIVE_PROXY_SOURCE_VARIANT:
        errors.append("source_variant_invalid")
    if args.live and args.require_live_success and packet.get("degraded") is True:
        errors.append(f"live_fetch_degraded:{packet.get('degraded_reason')}")

    for key in AUTHORITY_FLAGS:
        if packet.get("authority_flags", {}).get(key) is not False:
            errors.append(f"packet_authority_enabled:{key}")

    sample = fetch_phase1_live_adapter_sample("reddit")
    errors.extend(_validate_phase1_sample(sample))

    signal_probe = _reddit_only_signal_probe()
    if signal_probe["rejected_as_proxy_only"] is not True:
        errors.append("signal_integrity_proxy_only_probe_not_rejected")
    packet["signal_integrity_proxy_only_probe"] = signal_probe
    packet["validation_errors"] = sorted(set(errors))
    packet["validation_error_count"] = len(packet["validation_errors"])
    if errors:
        packet["status"] = "invalid"

    artifact_path, history_path, event_path = write_reddit_narrative_proxy_artifact(packet, settings)

    print("reddit_narrative_proxy_status=" + str(packet.get("status")))
    print("reddit_narrative_proxy_source_key=" + str(packet.get("source_key")))
    print("reddit_narrative_proxy_source_variant=" + str(packet.get("source_variant")))
    print("reddit_narrative_proxy_registry_slot=" + str(packet.get("source_registry_slot")))
    print("reddit_narrative_proxy_observation_count=" + str(packet.get("observation_count")))
    print("reddit_narrative_proxy_live_mode=" + str(packet.get("live_mode")))
    print("reddit_narrative_proxy_degraded=" + str(packet.get("degraded")))
    print("reddit_narrative_proxy_degraded_reason=" + str(packet.get("degraded_reason")))
    print("reddit_narrative_proxy_oauth_state=" + str(packet.get("reddit_oauth_state")))
    print("reddit_narrative_proxy_source_count=" + str(len(SOURCE_SPECS)))
    print("reddit_narrative_proxy_expected_source_count=" + str(EXPECTED_SOURCE_COUNT))
    print("reddit_narrative_proxy_signal_probe_status=" + str(signal_probe["status"]))
    print("reddit_narrative_proxy_signal_probe_rejected=" + str(signal_probe["rejected_as_proxy_only"]))
    print("reddit_narrative_proxy_artifact_path=" + str(artifact_path))
    print("reddit_narrative_proxy_history_path=" + str(history_path))
    print("reddit_narrative_proxy_event_path=" + str(event_path))
    print(
        "reddit_narrative_proxy_boundary="
        "read-only aggregate social context; no source quorum, candidates, risk approval, orders, broker writes, live capital, or paper proof ledger credit."
    )
    for error in sorted(set(errors)):
        print("reddit_narrative_proxy_error=" + error)
    if errors:
        return 1
    print("reddit_narrative_proxy_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
