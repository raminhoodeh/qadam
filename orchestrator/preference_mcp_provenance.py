"""Preference/PREF MCP provenance and source-quorum contract.

PREF-5 prevents source washing through the Preference aggregator. Preference can
be useful context, but Qadam only treats upstream sources as distinct when each
upstream identity and provenance path is explicit and hashable.
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.preference_mcp_identity import (
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    SECRET_LIKE_PATTERNS,
)

PREFERENCE_PROVENANCE_SCHEMA_VERSION = 1
PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION = 1
PREFERENCE_PROVENANCE_STAGE = "PREF-5"
PREFERENCE_PROVENANCE_ARTIFACT_TYPE = "preference_mcp_provenance_source_quorum"
PREFERENCE_PROVENANCE_ARTIFACT_ID = "preference:pref-5:provenance-source-quorum"
PREFERENCE_PROVENANCE_EVENT_TYPE = "preference_mcp_provenance_source_quorum_checked"
PREFERENCE_PROVENANCE_EVENT_COMPONENT = "preference_mcp_provenance"
PREFERENCE_PROVENANCE_BOUNDARY = (
    "Preference/PREF MCP PREF-5 validates provenance and source-quorum policy. "
    "Preference remains supplemental, cannot be promoted as source 36, cannot "
    "source-wash multiple claims through one aggregator identity, cannot count "
    "toward strategy source quorum without explicit upstream identity, and "
    "cannot create trade candidates, approve risk, write to brokers, call "
    "quantum providers, submit hardware jobs, enable schedulers, provide fills, "
    "receipts, reconciliation truth, or enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _blank_authority_flags() -> dict[str, bool]:
    return {
        "source_quorum_credit_allowed": False,
        "preference_counts_as_canonical_source": False,
        "strategy_source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_approval_authority": False,
        "execution_authority": False,
        "paper_order_authority": False,
        "broker_write_authority": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "quantum_provider_call_allowed": False,
        "hardware_submission_allowed": False,
        "scheduler_enabled": False,
        "live_capital_authority": False,
    }


def _source_identity(
    *,
    upstream_source_name: str,
    upstream_provenance_url: str,
    upstream_provenance_id: str,
    provenance_path: tuple[str, ...],
) -> str:
    identity_hash = stable_hash(
        {
            "upstream_source_name": upstream_source_name,
            "upstream_provenance_url": upstream_provenance_url,
            "upstream_provenance_id": upstream_provenance_id,
            "provenance_path": list(provenance_path),
        }
    ).split(":", 1)[1][:16]
    safe_source = upstream_source_name.strip().lower().replace(" ", "_") or "unknown"
    return f"preference_upstream:{safe_source}:{identity_hash}"


def build_preference_provenance_block(
    *,
    tool_ref: str | None,
    pref_request_id: str | None,
    response_id: str | None,
    query: str,
    upstream_source_name: str,
    upstream_provenance_url: str,
    upstream_provenance_id: str | None,
    provenance_path: tuple[str, ...] | list[str],
    fetched_at: str,
    observed_at: str,
    freshness_seconds: int | None,
    cadence: str,
    credit_cost_metadata: dict[str, Any] | None,
    payload_fingerprint_fields: dict[str, Any],
    live_discovered: bool,
    raw_response_archived: bool,
) -> dict[str, Any]:
    path = tuple(str(item) for item in provenance_path if str(item).strip())
    provenance_id = upstream_provenance_id or "/".join(path)
    query_hash = stable_hash({"query": query.strip()})
    payload_hash_fields = dict(payload_fingerprint_fields)
    payload_hash_fields["query_hash"] = query_hash
    payload_hash = stable_hash(payload_hash_fields)
    upstream_identity = _source_identity(
        upstream_source_name=upstream_source_name,
        upstream_provenance_url=upstream_provenance_url,
        upstream_provenance_id=provenance_id,
        provenance_path=path,
    )
    block = {
        "schema_version": PREFERENCE_PROVENANCE_SCHEMA_VERSION,
        "stage": PREFERENCE_PROVENANCE_STAGE,
        "provider": PREFERENCE_PROVIDER_LABEL,
        "source_key": PREFERENCE_SOURCE_KEY,
        "tool_ref": tool_ref,
        "pref_request_id": pref_request_id,
        "response_id": response_id,
        "query": query.strip(),
        "query_hash": query_hash,
        "payload_hash": payload_hash,
        "payload_hash_fields": payload_hash_fields,
        "provenance_mode": "live" if live_discovered else "deterministic_sample",
        "upstream_source_name": upstream_source_name,
        "upstream_source_identity": upstream_identity,
        "upstream_provenance_url": upstream_provenance_url,
        "upstream_provenance_id": provenance_id,
        "provenance_path": list(path),
        "fetched_at": fetched_at,
        "observed_at": observed_at,
        "freshness_seconds": freshness_seconds,
        "cadence": cadence,
        "credit_cost_metadata": credit_cost_metadata or {
            "mode": "offline_sample",
            "paid_tool": False,
            "credits_consumed": 0,
        },
        "live_discovered": live_discovered,
        "raw_response_archived": raw_response_archived,
        "quarantine_status": "accepted",
        "source_quorum_credit_allowed": False,
        "counts_against_strategy_source_quorum": False,
        "boundary": PREFERENCE_PROVENANCE_BOUNDARY,
    }
    errors = validate_preference_provenance_block(block)
    if errors:
        block["quarantine_status"] = "quarantined"
        block["quarantine_reasons"] = errors
    else:
        block["quarantine_reasons"] = []
    return block


def validate_preference_provenance_block(block: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "provider",
        "source_key",
        "query",
        "query_hash",
        "payload_hash",
        "payload_hash_fields",
        "upstream_source_name",
        "upstream_source_identity",
        "upstream_provenance_url",
        "upstream_provenance_id",
        "provenance_path",
        "fetched_at",
        "observed_at",
        "credit_cost_metadata",
        "source_quorum_credit_allowed",
        "counts_against_strategy_source_quorum",
    }
    for field in sorted(required - set(block)):
        errors.append(f"missing_field:{field}")
    if block.get("schema_version") != PREFERENCE_PROVENANCE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if block.get("provider") != PREFERENCE_PROVIDER_LABEL:
        errors.append("provider_mismatch")
    if block.get("source_key") != PREFERENCE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if not str(block.get("upstream_source_name") or "").strip():
        errors.append("missing_upstream_source_name")
    if str(block.get("upstream_source_name") or "").strip() == PREFERENCE_SOURCE_KEY:
        errors.append("aggregator_used_as_upstream_source")
    if not str(block.get("upstream_source_identity") or "").startswith("preference_upstream:"):
        errors.append("missing_upstream_source_identity")
    if not str(block.get("upstream_provenance_url") or "").strip():
        errors.append("missing_upstream_provenance_url")
    if not str(block.get("upstream_provenance_id") or "").strip():
        errors.append("missing_upstream_provenance_id")
    provenance_path = block.get("provenance_path")
    if not isinstance(provenance_path, list) or not provenance_path:
        errors.append("missing_provenance_path")
    expected_query_hash = stable_hash({"query": str(block.get("query") or "").strip()})
    if block.get("query_hash") != expected_query_hash:
        errors.append("query_hash_mismatch")
    hash_fields = block.get("payload_hash_fields")
    if not isinstance(hash_fields, dict) or not hash_fields:
        errors.append("missing_payload_hash_fields")
    elif block.get("payload_hash") != stable_hash(hash_fields):
        errors.append("payload_hash_mismatch")
    if block.get("source_quorum_credit_allowed") is not False:
        errors.append("source_quorum_credit_allowed")
    if block.get("counts_against_strategy_source_quorum") is not False:
        errors.append("counts_against_strategy_source_quorum")
    credit = block.get("credit_cost_metadata")
    if not isinstance(credit, dict):
        errors.append("credit_cost_metadata_not_object")
    else:
        if credit.get("paid_tool") is not False:
            errors.append("paid_tool_credit_metadata_not_false")
        if int(credit.get("credits_consumed", 0) or 0) != 0:
            errors.append("credits_consumed_not_zero")
    if _contains_secret_like_value(block):
        errors.append("secret_like_value_exposed")
    return errors


def _event_provenance(event: dict[str, Any]) -> dict[str, Any] | None:
    raw_payload = event.get("raw_payload") if isinstance(event, dict) else None
    if not isinstance(raw_payload, dict):
        return None
    provenance = raw_payload.get("preference_provenance")
    return provenance if isinstance(provenance, dict) else None


def _canonical_identity(item: dict[str, Any]) -> str:
    upstream_identity = str(item.get("upstream_source_identity") or "").strip()
    if upstream_identity:
        return upstream_identity
    source = str(item.get("source") or "unknown_canonical_source").strip()
    return f"canonical:{source}"


def build_preference_source_quorum_report(
    *,
    preference_events: list[dict[str, Any]],
    canonical_evidence: list[dict[str, Any]] | None = None,
    event_log: EventLog | None = None,
    record_event: bool = False,
) -> dict[str, Any]:
    canonical_evidence = canonical_evidence or []
    valid_blocks: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    overclaim_event_ids: list[str] = []
    for index, event in enumerate(preference_events):
        event_id = str(event.get("event_id") or f"event:{index}")
        provenance = _event_provenance(event)
        if provenance is None:
            quarantined.append(
                {
                    "event_id": event_id,
                    "quarantine_reasons": ["missing_preference_provenance"],
                }
            )
            continue
        errors = validate_preference_provenance_block(provenance)
        raw_payload = event.get("raw_payload", {})
        if isinstance(raw_payload, dict) and raw_payload.get("counts_against_source_quorum") is not False:
            errors.append("event_counts_against_source_quorum")
            overclaim_event_ids.append(event_id)
        if provenance.get("counts_against_strategy_source_quorum") is not False:
            overclaim_event_ids.append(event_id)
        if errors:
            quarantined.append({"event_id": event_id, "quarantine_reasons": errors})
        else:
            valid_blocks.append(provenance)

    upstream_identities = [
        str(block.get("upstream_source_identity")) for block in valid_blocks if block.get("upstream_source_identity")
    ]
    upstream_counts = Counter(upstream_identities)
    duplicate_identities = sorted(identity for identity, count in upstream_counts.items() if count > 1)
    canonical_identities = sorted({_canonical_identity(item) for item in canonical_evidence})
    preference_identity_set = set(upstream_identities)
    canonical_overlap = sorted(preference_identity_set.intersection(canonical_identities))
    combined_identities = sorted(preference_identity_set.union(canonical_identities))

    if quarantined:
        preference_context_status = "quarantined_missing_or_invalid_provenance"
    elif duplicate_identities:
        preference_context_status = "duplicate_upstream_identity_hold"
    elif len(preference_identity_set) >= 2:
        preference_context_status = "explicit_multi_upstream_context"
    elif len(preference_identity_set) == 1:
        preference_context_status = "supplemental_single_upstream_hold"
    else:
        preference_context_status = "no_preference_provenance"

    if canonical_overlap:
        combined_context_status = "hold_duplicate_canonical_or_upstream_identity"
    elif preference_identity_set and canonical_identities:
        combined_context_status = "distinct_preference_and_canonical_context"
    elif preference_identity_set:
        combined_context_status = "preference_only_supplemental_context"
    elif canonical_identities:
        combined_context_status = "canonical_only_context"
    else:
        combined_context_status = "no_source_context"

    report = {
        "schema_version": PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_PROVENANCE_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_PROVENANCE_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_PROVENANCE_STAGE,
        "status": "validated" if not quarantined and not duplicate_identities else "blocked",
        "generated_at": _now(),
        "public_safe": True,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "preference_observation_count": len(preference_events),
        "valid_preference_observation_count": len(valid_blocks),
        "quarantined_observation_count": len(quarantined),
        "quarantined_observations": quarantined,
        "overclaim_event_ids": sorted(set(overclaim_event_ids)),
        "preference_distinct_upstream_source_count": len(preference_identity_set),
        "preference_upstream_identities": sorted(preference_identity_set),
        "duplicate_upstream_identity_count": len(duplicate_identities),
        "duplicate_upstream_identities": duplicate_identities,
        "preference_context_status": preference_context_status,
        "preference_multi_source_context_allowed": (
            preference_context_status == "explicit_multi_upstream_context"
        ),
        "preference_counts_as_canonical_source": False,
        "preference_only_source_quorum_allowed": False,
        "canonical_evidence_count": len(canonical_evidence),
        "canonical_source_identities": canonical_identities,
        "canonical_overlap_with_preference_count": len(canonical_overlap),
        "canonical_overlap_with_preference": canonical_overlap,
        "combined_distinct_source_count": len(combined_identities),
        "combined_context_status": combined_context_status,
        "combined_preference_canonical_context_allowed": (
            combined_context_status == "distinct_preference_and_canonical_context"
        ),
        "strategy_source_quorum_credit_allowed": False,
        "source_quorum_overclaim_rejected": not overclaim_event_ids,
        "authority_flags": _blank_authority_flags(),
        "boundary": PREFERENCE_PROVENANCE_BOUNDARY,
    }
    report["validation_errors"] = validate_preference_source_quorum_report(report)

    if record_event:
        event_log = event_log or EventLog(echo=False)
        event_log.write(
            PREFERENCE_PROVENANCE_EVENT_TYPE,
            PREFERENCE_PROVENANCE_EVENT_COMPONENT,
            {
                "stage": report["stage"],
                "status": report["status"],
                "preference_observation_count": report["preference_observation_count"],
                "valid_preference_observation_count": report["valid_preference_observation_count"],
                "quarantined_observation_count": report["quarantined_observation_count"],
                "duplicate_upstream_identity_count": report["duplicate_upstream_identity_count"],
                "preference_context_status": report["preference_context_status"],
                "combined_context_status": report["combined_context_status"],
                "strategy_source_quorum_credit_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            },
        )
    return report


def validate_preference_source_quorum_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "status",
        "public_safe",
        "preference_observation_count",
        "valid_preference_observation_count",
        "quarantined_observation_count",
        "duplicate_upstream_identity_count",
        "preference_counts_as_canonical_source",
        "preference_only_source_quorum_allowed",
        "strategy_source_quorum_credit_allowed",
        "authority_flags",
        "boundary",
    }
    for field in sorted(required - set(report)):
        errors.append(f"missing_field:{field}")
    if report.get("schema_version") != PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if report.get("artifact_type") != PREFERENCE_PROVENANCE_ARTIFACT_TYPE:
        errors.append("artifact_type_mismatch")
    if report.get("stage") != PREFERENCE_PROVENANCE_STAGE:
        errors.append("stage_not_pref_5")
    if report.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if int(report.get("quarantined_observation_count") or 0) > 0:
        errors.append("quarantined_observations_present")
    if int(report.get("duplicate_upstream_identity_count") or 0) > 0:
        errors.append("duplicate_upstream_identities_present")
    if int(report.get("canonical_overlap_with_preference_count") or 0) > 0:
        errors.append("canonical_overlap_with_preference_present")
    if report.get("overclaim_event_ids"):
        errors.append("source_quorum_overclaim_events_present")
    if report.get("preference_counts_as_canonical_source") is not False:
        errors.append("preference_counts_as_canonical_source")
    if report.get("preference_only_source_quorum_allowed") is not False:
        errors.append("preference_only_source_quorum_allowed")
    if report.get("strategy_source_quorum_credit_allowed") is not False:
        errors.append("strategy_source_quorum_credit_allowed")
    if (
        report.get("combined_preference_canonical_context_allowed") is True
        and report.get("canonical_overlap_with_preference_count", 0) != 0
    ):
        errors.append("combined_context_allowed_with_canonical_overlap")
    if (
        report.get("combined_context_status") == "distinct_preference_and_canonical_context"
        and not report.get("combined_preference_canonical_context_allowed")
    ):
        errors.append("distinct_combined_context_not_marked_allowed")
    flags = report.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for key, value in flags.items():
            if value is not False:
                errors.append(f"authority_flag_enabled:{key}")
    if _contains_secret_like_value(report):
        errors.append("secret_like_value_exposed")
    return errors


def preference_provenance_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_provenance_source_quorum.json",
        runtime_dir / "preference_provenance_source_quorum_history.jsonl",
    )


def write_preference_source_quorum_report(
    report: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_provenance_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report["runtime_artifact_path"] = str(output_path)
    report["history_log_path"] = str(history_path)
    report["validation_errors"] = validate_preference_source_quorum_report(report)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_SOURCE_QUORUM_SCHEMA_VERSION,
        "artifact_id": report.get("artifact_id"),
        "stage": report.get("stage"),
        "status": report.get("status"),
        "generated_at": report.get("generated_at"),
        "recorded_at": _now(),
        "preference_observation_count": report.get("preference_observation_count"),
        "valid_preference_observation_count": report.get("valid_preference_observation_count"),
        "quarantined_observation_count": report.get("quarantined_observation_count"),
        "duplicate_upstream_identity_count": report.get("duplicate_upstream_identity_count"),
        "combined_context_status": report.get("combined_context_status"),
        "validation_error_count": len(report.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path
