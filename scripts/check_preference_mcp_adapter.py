#!/usr/bin/env python3
"""Validate PREF-3 Preference/PREF MCP offline sample adapter."""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.preference_mcp_adapter import (  # noqa: E402
    PREFERENCE_MCP_ADAPTER_BOUNDARY,
    PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
    PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION,
    PREFERENCE_MCP_ADAPTER_STAGE,
    PREFERENCE_MCP_LIVE_SMOKE_BOUNDARY,
    PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION,
    PREFERENCE_MCP_LIVE_SMOKE_STAGE,
    build_preference_mcp_live_smoke,
    fetch_preference_mcp_sample,
    preference_mcp_adapter_status,
    validate_preference_mcp_live_smoke,
    validate_preference_mcp_sample_envelope,
    write_preference_mcp_live_smoke,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402

SECRET_LIKE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpref_agent_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.IGNORECASE),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _first_raw_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    events = envelope.get("events")
    if not isinstance(events, list) or not events:
        return {}
    event = events[0]
    if not isinstance(event, dict):
        return {}
    raw_payload = event.get("raw_payload")
    return raw_payload if isinstance(raw_payload, dict) else {}


def _authority_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    raw_payload = _first_raw_payload(probe)
    raw_payload["authority_flags"]["broker_write_authority"] = True
    probe["validation_errors"] = validate_preference_mcp_sample_envelope(probe)
    return probe


def _live_call_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    raw_payload = _first_raw_payload(probe)
    raw_payload["live_mcp_call_attempted"] = True
    raw_payload["search_tools_call_attempted"] = True
    probe["validation_errors"] = validate_preference_mcp_sample_envelope(probe)
    return probe


def _source_quorum_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    raw_payload = _first_raw_payload(probe)
    raw_payload["counts_against_source_quorum"] = True
    probe["validation_errors"] = validate_preference_mcp_sample_envelope(probe)
    return probe


def _missing_provenance_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    raw_payload = _first_raw_payload(probe)
    raw_payload.pop("preference_provenance", None)
    probe["validation_errors"] = validate_preference_mcp_sample_envelope(probe)
    return probe


def _secret_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    raw_payload = _first_raw_payload(probe)
    raw_payload["sample_tool_ref"] = "pref_" + "agent_" + "DO_NOT_USE_EXAMPLE_SECRET"
    probe["validation_errors"] = validate_preference_mcp_sample_envelope(probe)
    return probe


def _live_smoke_authority_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["domain_tool_calls_allowed"] = True
    probe["authority_flags"]["broker_write_authority"] = True
    probe["validation_errors"] = validate_preference_mcp_live_smoke(probe)
    return probe


def _live_smoke_catalog_without_identity_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["mode"] = "live_catalog_only"
    probe["live_catalog_call_attempted"] = True
    probe["search_tools_call_attempted"] = True
    probe["identity_gate_status"] = "blocked"
    probe["identity_status"]["status"] = "blocked"
    probe["validation_errors"] = validate_preference_mcp_live_smoke(probe)
    return probe


def _live_smoke_domain_tool_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["domain_tool_call_attempted"] = True
    probe["live_read_only_tool_call_attempted"] = True
    probe["domain_data_requested"] = True
    probe["validation_errors"] = validate_preference_mcp_live_smoke(probe)
    return probe


def _live_smoke_paid_tool_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["paid_tools_allowed_by_config"] = True
    probe["paid_tool_calls_allowed"] = True
    probe["paid_tool_call_attempted"] = True
    probe["validation_errors"] = validate_preference_mcp_live_smoke(probe)
    return probe


def _live_smoke_secret_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["credential_status"]["source"] = "pref_" + "agent_" + "DO_NOT_USE_EXAMPLE_SECRET"
    probe["validation_errors"] = validate_preference_mcp_live_smoke(probe)
    return probe


def _run_live_smoke(*, mode: str, record_event: bool) -> int:
    artifact = build_preference_mcp_live_smoke(mode=mode, record_event=record_event)
    output_path, history_path = write_preference_mcp_live_smoke(artifact)
    validation_errors = validate_preference_mcp_live_smoke(artifact)
    authority_probe = _live_smoke_authority_probe(artifact)
    catalog_without_identity_probe = _live_smoke_catalog_without_identity_probe(artifact)
    domain_tool_probe = _live_smoke_domain_tool_probe(artifact)
    paid_tool_probe = _live_smoke_paid_tool_probe(artifact)
    secret_probe = _live_smoke_secret_probe(artifact)

    errors: list[str] = list(validation_errors)
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_in_live_smoke")
    if artifact["domain_tool_call_attempted"] is not False:
        errors.append("domain_tool_call_attempted")
    if artifact["paid_tool_call_attempted"] is not False:
        errors.append("paid_tool_call_attempted")
    if artifact["domain_data_requested"] is not False:
        errors.append("domain_data_requested")
    if artifact["source_quorum_credit_allowed"] is not False:
        errors.append("source_quorum_credit_allowed")
    if artifact["domain_tool_calls_allowed"] is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact["paid_tool_calls_allowed"] is not False:
        errors.append("paid_tool_calls_allowed")
    if mode == "live_status_only" and artifact["search_tools_call_attempted"] is not False:
        errors.append("live_status_only_search_tools_attempted")
    if mode == "live_catalog_only" and artifact["identity_gate_status"] != "verified_non_anonymous":
        if artifact["search_tools_call_attempted"] is not False:
            errors.append("search_tools_attempted_without_verified_identity")
    if not authority_probe["validation_errors"]:
        errors.append("live_smoke_authority_probe_not_rejected")
    if not catalog_without_identity_probe["validation_errors"]:
        errors.append("live_smoke_catalog_without_identity_probe_not_rejected")
    if not domain_tool_probe["validation_errors"]:
        errors.append("live_smoke_domain_tool_probe_not_rejected")
    if not paid_tool_probe["validation_errors"]:
        errors.append("live_smoke_paid_tool_probe_not_rejected")
    if not secret_probe["validation_errors"]:
        errors.append("live_smoke_secret_probe_not_rejected")

    print("preference_mcp_live_smoke_status=" + artifact["status"])
    print(f"preference_mcp_live_smoke_schema_version={PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION}")
    print(f"preference_mcp_live_smoke_stage={PREFERENCE_MCP_LIVE_SMOKE_STAGE}")
    print(f"preference_mcp_live_smoke_mode={artifact['mode']}")
    print(f"preference_mcp_live_smoke_artifact_path={output_path}")
    print(f"preference_mcp_live_smoke_history_path={history_path}")
    print(f"preference_mcp_live_smoke_enabled={artifact['enabled']}")
    print(
        "preference_mcp_live_smoke_credential_configured="
        f"{artifact['credential_status']['configured']}"
    )
    print(f"preference_mcp_live_smoke_credential_source={artifact['credential_status']['source']}")
    print(f"preference_mcp_live_smoke_identity_gate_status={artifact['identity_gate_status']}")
    print(
        "preference_mcp_live_smoke_identity_status="
        f"{artifact['identity_gate_identity_status']}"
    )
    print(
        "preference_mcp_live_smoke_identity_quota_metadata_present="
        f"{artifact['identity_gate_quota_metadata_present']}"
    )
    print(
        "preference_mcp_live_smoke_live_status_call_attempted="
        f"{artifact['live_status_call_attempted']}"
    )
    print(
        "preference_mcp_live_smoke_live_catalog_call_attempted="
        f"{artifact['live_catalog_call_attempted']}"
    )
    print(
        "preference_mcp_live_smoke_search_tools_call_attempted="
        f"{artifact['search_tools_call_attempted']}"
    )
    print(
        "preference_mcp_live_smoke_domain_tool_call_attempted="
        f"{artifact['domain_tool_call_attempted']}"
    )
    print(
        "preference_mcp_live_smoke_paid_tool_call_attempted="
        f"{artifact['paid_tool_call_attempted']}"
    )
    print(
        "preference_mcp_live_smoke_domain_data_requested="
        f"{artifact['domain_data_requested']}"
    )
    print(
        "preference_mcp_live_smoke_source_quorum_credit_allowed="
        f"{artifact['source_quorum_credit_allowed']}"
    )
    print(
        "preference_mcp_live_smoke_live_call_attempt_count="
        f"{artifact['live_call_attempt_count']}"
    )
    print(f"preference_mcp_live_smoke_run_call_budget={artifact['run_call_budget']}")
    print(f"preference_mcp_live_smoke_catalog_error={artifact['catalog_error']}")
    print(f"preference_mcp_live_smoke_blocked_reason_count={artifact['blocked_reason_count']}")
    print(f"preference_mcp_live_smoke_blocked_reasons={','.join(artifact['blocked_reasons'])}")
    print(f"preference_mcp_live_smoke_validation_error_count={len(validation_errors)}")
    print(
        "preference_mcp_live_smoke_authority_probe_error_count="
        f"{len(authority_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_live_smoke_catalog_without_identity_probe_error_count="
        f"{len(catalog_without_identity_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_live_smoke_domain_tool_probe_error_count="
        f"{len(domain_tool_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_live_smoke_paid_tool_probe_error_count="
        f"{len(paid_tool_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_live_smoke_secret_probe_error_count="
        f"{len(secret_probe['validation_errors'])}"
    )
    print(f"preference_mcp_live_smoke_boundary={PREFERENCE_MCP_LIVE_SMOKE_BOUNDARY}")

    for error in errors:
        print(f"preference_mcp_live_smoke_error={error}")
    if errors:
        print("preference_mcp_live_smoke_check=failed")
        return 1

    print("preference_mcp_live_smoke_check=ok")
    return 0


def _run_sample_check() -> int:

    status = preference_mcp_adapter_status()
    envelope = fetch_preference_mcp_sample()
    validation_errors = validate_preference_mcp_sample_envelope(envelope)
    authority_probe = _authority_probe(envelope)
    live_call_probe = _live_call_probe(envelope)
    source_quorum_probe = _source_quorum_probe(envelope)
    missing_provenance_probe = _missing_provenance_probe(envelope)
    secret_probe = _secret_probe(envelope)

    events = envelope.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    raw_archive_path = str(envelope.get("raw_archive_path") or "")
    errors: list[str] = list(validation_errors)
    if status["canonical_source_count"] != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_changed")
    if status["sample_fixture_count"] != 6:
        errors.append("sample_fixture_count_mismatch")
    if event_count != status["sample_fixture_count"]:
        errors.append("event_count_fixture_mismatch")
    if _contains_secret_like_value(envelope) or _contains_secret_like_value(status):
        errors.append("secret_like_value_in_output")
    if status["live_mcp_call_allowed"] is not False:
        errors.append("live_mcp_call_allowed")
    if status["search_tools_allowed"] is not False:
        errors.append("search_tools_allowed")
    if status["domain_tool_calls_allowed"] is not False:
        errors.append("domain_tool_calls_allowed")
    if status["paid_tool_calls_allowed"] is not False:
        errors.append("paid_tool_calls_allowed")
    if status["source_quorum_credit_allowed"] is not False:
        errors.append("source_quorum_credit_allowed")
    if not raw_archive_path:
        errors.append("raw_archive_path_missing")
    if not authority_probe["validation_errors"]:
        errors.append("authority_probe_not_rejected")
    if not live_call_probe["validation_errors"]:
        errors.append("live_call_probe_not_rejected")
    if not source_quorum_probe["validation_errors"]:
        errors.append("source_quorum_probe_not_rejected")
    if not missing_provenance_probe["validation_errors"]:
        errors.append("missing_provenance_probe_not_rejected")
    if not secret_probe["validation_errors"]:
        errors.append("secret_probe_not_rejected")

    print("preference_mcp_adapter_status=" + ("ok" if not errors else "error"))
    print(f"preference_mcp_adapter_schema_version={PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION}")
    print(f"preference_mcp_adapter_stage={PREFERENCE_MCP_ADAPTER_STAGE}")
    print(f"preference_mcp_adapter_classification={PREFERENCE_MCP_ADAPTER_CLASSIFICATION}")
    print(f"preference_mcp_adapter_mode={status['mode']}")
    print(f"preference_mcp_adapter_source={envelope.get('source')}")
    print(f"preference_mcp_adapter_event_count={event_count}")
    print(f"preference_mcp_adapter_sample_fixture_count={status['sample_fixture_count']}")
    print(f"preference_mcp_adapter_raw_archive_path={raw_archive_path}")
    print(f"preference_mcp_adapter_degraded={envelope.get('degraded')}")
    print(f"preference_mcp_adapter_identity_gate_status={status['identity_gate_status']}")
    print(f"preference_mcp_adapter_catalog_gate_status={status['catalog_gate_status']}")
    print(
        "preference_mcp_adapter_catalog_validation_error_count="
        f"{status['catalog_validation_error_count']}"
    )
    print(f"preference_mcp_adapter_canonical_source_count={status['canonical_source_count']}")
    print(f"preference_mcp_adapter_live_mcp_call_allowed={status['live_mcp_call_allowed']}")
    print(f"preference_mcp_adapter_search_tools_allowed={status['search_tools_allowed']}")
    print(
        "preference_mcp_adapter_domain_tool_calls_allowed="
        f"{status['domain_tool_calls_allowed']}"
    )
    print(
        "preference_mcp_adapter_paid_tool_calls_allowed="
        f"{status['paid_tool_calls_allowed']}"
    )
    print(
        "preference_mcp_adapter_source_quorum_credit_allowed="
        f"{status['source_quorum_credit_allowed']}"
    )
    print(
        "preference_mcp_adapter_trade_candidate_creation_allowed="
        f"{status['authority_flags']['trade_candidate_creation_allowed']}"
    )
    print(
        "preference_mcp_adapter_broker_write_authority="
        f"{status['authority_flags']['broker_write_authority']}"
    )
    print(
        "preference_mcp_adapter_live_capital_authority="
        f"{status['authority_flags']['live_capital_authority']}"
    )
    print(f"preference_mcp_adapter_validation_error_count={len(validation_errors)}")
    print(
        "preference_mcp_adapter_authority_probe_error_count="
        f"{len(authority_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_adapter_live_call_probe_error_count="
        f"{len(live_call_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_adapter_source_quorum_probe_error_count="
        f"{len(source_quorum_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_adapter_missing_provenance_probe_error_count="
        f"{len(missing_provenance_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_adapter_secret_probe_error_count="
        f"{len(secret_probe['validation_errors'])}"
    )
    print(f"preference_mcp_adapter_boundary={PREFERENCE_MCP_ADAPTER_BOUNDARY}")

    for error in errors:
        print(f"preference_mcp_adapter_error={error}")
    if errors:
        print("preference_mcp_adapter_check=failed")
        return 1

    print("preference_mcp_adapter_check=ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-event",
        action="store_true",
        help="Do not append sanitized PREF-4 live-smoke events.",
    )
    parser.add_argument(
        "--live-status-only",
        action="store_true",
        help="Run the PREF-4 status-only live smoke gate.",
    )
    parser.add_argument(
        "--live-catalog-only",
        action="store_true",
        help="Run the PREF-4 catalog-only live smoke gate after status verification.",
    )
    args = parser.parse_args()

    selected_live_modes = [args.live_status_only, args.live_catalog_only]
    if sum(1 for selected in selected_live_modes if selected) > 1:
        print("preference_mcp_adapter_error=choose_one_live_mode")
        return 2
    if args.live_status_only:
        return _run_live_smoke(mode="live_status_only", record_event=not args.no_event)
    if args.live_catalog_only:
        return _run_live_smoke(mode="live_catalog_only", record_event=not args.no_event)
    return _run_sample_check()


if __name__ == "__main__":
    raise SystemExit(main())
