#!/usr/bin/env python3
"""Validate PREF-5 Preference/PREF MCP provenance and source-quorum policy."""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.preference_mcp_adapter import fetch_preference_mcp_sample  # noqa: E402
from orchestrator.preference_mcp_provenance import (  # noqa: E402
    PREFERENCE_PROVENANCE_BOUNDARY,
    PREFERENCE_PROVENANCE_SCHEMA_VERSION,
    PREFERENCE_PROVENANCE_STAGE,
    PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION,
    build_preference_source_quorum_report,
    validate_preference_provenance_block,
    validate_preference_source_quorum_report,
    write_preference_source_quorum_report,
)

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


def _events(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    events = envelope.get("events", [])
    return [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []


def _first_provenance(events: list[dict[str, Any]]) -> dict[str, Any]:
    raw_payload = events[0].get("raw_payload", {}) if events else {}
    provenance = raw_payload.get("preference_provenance") if isinstance(raw_payload, dict) else None
    return provenance if isinstance(provenance, dict) else {}


def _missing_provenance_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    probe_events = deepcopy(events)
    probe_events[0]["raw_payload"].pop("preference_provenance", None)
    return build_preference_source_quorum_report(preference_events=probe_events)


def _duplicate_upstream_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    probe_events = [deepcopy(events[0]), deepcopy(events[0])]
    probe_events[1]["event_id"] = str(probe_events[1]["event_id"]) + ":duplicate"
    return build_preference_source_quorum_report(preference_events=probe_events)


def _source_quorum_overclaim_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    probe_events = deepcopy(events)
    probe_events[0]["raw_payload"]["counts_against_source_quorum"] = True
    probe_events[0]["raw_payload"]["preference_provenance"][
        "counts_against_strategy_source_quorum"
    ] = True
    return build_preference_source_quorum_report(preference_events=probe_events)


def _payload_hash_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    probe_events = deepcopy(events)
    probe_events[0]["raw_payload"]["preference_provenance"]["payload_hash"] = "sha256:bad"
    return build_preference_source_quorum_report(preference_events=probe_events)


def _aggregator_identity_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    probe_events = deepcopy(events)
    provenance = probe_events[0]["raw_payload"]["preference_provenance"]
    provenance["upstream_source_name"] = "preference_mcp"
    return build_preference_source_quorum_report(preference_events=probe_events)


def _canonical_distinct_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    return build_preference_source_quorum_report(
        preference_events=[deepcopy(events[0])],
        canonical_evidence=[
            {
                "source": "physical.nasa_firms",
                "event_type": "physical_anomaly",
                "summary": "Canonical NASA FIRMS context is distinct from Preference upstream source.",
            }
        ],
    )


def _canonical_duplicate_probe(events: list[dict[str, Any]]) -> dict[str, Any]:
    provenance = _first_provenance(events)
    return build_preference_source_quorum_report(
        preference_events=[deepcopy(events[0])],
        canonical_evidence=[
            {
                "source": "preference_duplicate_probe",
                "upstream_source_identity": provenance.get("upstream_source_identity"),
                "summary": "Duplicate canonical identity should not count as a distinct source.",
            }
        ],
    )


def main() -> int:
    envelope = fetch_preference_mcp_sample()
    events = _events(envelope)
    report = build_preference_source_quorum_report(preference_events=events, record_event=True)
    output_path, history_path = write_preference_source_quorum_report(report)
    validation_errors = validate_preference_source_quorum_report(report)
    provenance_errors = [
        error
        for event in events
        for error in validate_preference_provenance_block(
            event.get("raw_payload", {}).get("preference_provenance", {})
            if isinstance(event.get("raw_payload"), dict)
            else {}
        )
    ]

    missing_provenance_probe = _missing_provenance_probe(events)
    duplicate_upstream_probe = _duplicate_upstream_probe(events)
    source_quorum_overclaim_probe = _source_quorum_overclaim_probe(events)
    payload_hash_probe = _payload_hash_probe(events)
    aggregator_identity_probe = _aggregator_identity_probe(events)
    canonical_distinct_probe = _canonical_distinct_probe(events)
    canonical_duplicate_probe = _canonical_duplicate_probe(events)

    errors: list[str] = list(validation_errors)
    if provenance_errors:
        errors.append("sample_event_provenance_invalid")
    if _contains_secret_like_value(report) or _contains_secret_like_value(envelope):
        errors.append("secret_like_value_in_output")
    if report["preference_counts_as_canonical_source"] is not False:
        errors.append("preference_counts_as_canonical_source")
    if report["preference_only_source_quorum_allowed"] is not False:
        errors.append("preference_only_source_quorum_allowed")
    if report["strategy_source_quorum_credit_allowed"] is not False:
        errors.append("strategy_source_quorum_credit_allowed")
    if report["quarantined_observation_count"] != 0:
        errors.append("sample_quarantined_observations")
    if report["duplicate_upstream_identity_count"] != 0:
        errors.append("sample_duplicate_upstream_identities")
    if not report["preference_multi_source_context_allowed"]:
        errors.append("sample_multi_source_context_not_allowed")
    if not missing_provenance_probe["validation_errors"]:
        errors.append("missing_provenance_probe_not_rejected")
    if not duplicate_upstream_probe["validation_errors"]:
        errors.append("duplicate_upstream_probe_not_rejected")
    if not source_quorum_overclaim_probe["validation_errors"]:
        errors.append("source_quorum_overclaim_probe_not_rejected")
    if not payload_hash_probe["validation_errors"]:
        errors.append("payload_hash_probe_not_rejected")
    if not aggregator_identity_probe["validation_errors"]:
        errors.append("aggregator_identity_probe_not_rejected")
    if canonical_distinct_probe["validation_errors"]:
        errors.append("canonical_distinct_probe_failed")
    if not canonical_distinct_probe["combined_preference_canonical_context_allowed"]:
        errors.append("canonical_distinct_context_not_allowed")
    if not canonical_duplicate_probe["validation_errors"]:
        errors.append("canonical_duplicate_probe_not_rejected")

    print("preference_provenance_status=" + report["status"])
    print(f"preference_provenance_schema_version={PREFERENCE_PROVENANCE_SCHEMA_VERSION}")
    print(f"preference_source_quorum_schema_version={PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION}")
    print(f"preference_provenance_stage={PREFERENCE_PROVENANCE_STAGE}")
    print(f"preference_provenance_artifact_path={output_path}")
    print(f"preference_provenance_history_path={history_path}")
    print(f"preference_provenance_observation_count={report['preference_observation_count']}")
    print(
        "preference_provenance_valid_observation_count="
        f"{report['valid_preference_observation_count']}"
    )
    print(
        "preference_provenance_quarantined_observation_count="
        f"{report['quarantined_observation_count']}"
    )
    print(
        "preference_provenance_distinct_upstream_source_count="
        f"{report['preference_distinct_upstream_source_count']}"
    )
    print(
        "preference_provenance_duplicate_upstream_identity_count="
        f"{report['duplicate_upstream_identity_count']}"
    )
    print(
        "preference_provenance_context_status="
        f"{report['preference_context_status']}"
    )
    print(
        "preference_provenance_multi_source_context_allowed="
        f"{report['preference_multi_source_context_allowed']}"
    )
    print(
        "preference_provenance_counts_as_canonical_source="
        f"{report['preference_counts_as_canonical_source']}"
    )
    print(
        "preference_provenance_only_source_quorum_allowed="
        f"{report['preference_only_source_quorum_allowed']}"
    )
    print(
        "preference_provenance_strategy_source_quorum_credit_allowed="
        f"{report['strategy_source_quorum_credit_allowed']}"
    )
    print(
        "preference_provenance_combined_context_status="
        f"{canonical_distinct_probe['combined_context_status']}"
    )
    print(
        "preference_provenance_combined_context_allowed="
        f"{canonical_distinct_probe['combined_preference_canonical_context_allowed']}"
    )
    print(f"preference_provenance_validation_error_count={len(validation_errors)}")
    print(f"preference_provenance_event_validation_error_count={len(provenance_errors)}")
    print(
        "preference_provenance_missing_probe_error_count="
        f"{len(missing_provenance_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_duplicate_probe_error_count="
        f"{len(duplicate_upstream_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_overclaim_probe_error_count="
        f"{len(source_quorum_overclaim_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_payload_hash_probe_error_count="
        f"{len(payload_hash_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_aggregator_identity_probe_error_count="
        f"{len(aggregator_identity_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_canonical_distinct_probe_error_count="
        f"{len(canonical_distinct_probe['validation_errors'])}"
    )
    print(
        "preference_provenance_canonical_duplicate_probe_error_count="
        f"{len(canonical_duplicate_probe['validation_errors'])}"
    )
    print(f"preference_provenance_boundary={PREFERENCE_PROVENANCE_BOUNDARY}")

    for error in errors:
        print(f"preference_provenance_error={error}")
    if errors:
        print("preference_provenance_check=failed")
        return 1

    print("preference_provenance_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
