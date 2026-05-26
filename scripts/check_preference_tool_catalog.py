#!/usr/bin/env python3
"""Validate PREF-2 Preference/PREF MCP tool catalog gating."""

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

from orchestrator.config import Settings  # noqa: E402
from orchestrator.preference_mcp_catalog import (  # noqa: E402
    PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES,
    PREFERENCE_TOOL_CATALOG_BOUNDARY,
    PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION,
    build_preference_tool_catalog,
    validate_preference_tool_catalog,
    write_preference_tool_catalog,
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


def _authority_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["domain_tool_calls_allowed"] = True
    probe["authority_flags"]["domain_tool_calls_allowed"] = True
    probe["validation_errors"] = validate_preference_tool_catalog(probe)
    return probe


def _live_without_identity_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["live_catalog_call_attempted"] = True
    probe["search_tools_call_attempted"] = True
    probe["identity_status"]["status"] = "blocked"
    probe["identity_gate_status"] = "blocked"
    probe["validation_errors"] = validate_preference_tool_catalog(probe)
    return probe


def _outside_scope_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    for entry in probe["catalog_entries"]:
        if entry["domain_pack"] == "sports_lines":
            entry["approval_status"] = "approved_for_catalog_only"
            break
    probe["status_counts"] = {
        status: sum(
            1
            for entry in probe["catalog_entries"]
            if entry["approval_status"] == status
        )
        for status in PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES
    }
    probe["status_counts"] = {
        status: count for status, count in probe["status_counts"].items() if count
    }
    probe["validation_errors"] = validate_preference_tool_catalog(probe)
    return probe


def _candidate_without_live_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["catalog_entries"][0]["approval_status"] = "candidate_read_only"
    probe["status_counts"] = {
        status: sum(
            1
            for entry in probe["catalog_entries"]
            if entry["approval_status"] == status
        )
        for status in PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES
    }
    probe["status_counts"] = {
        status: count for status, count in probe["status_counts"].items() if count
    }
    probe["candidate_read_only_count"] = probe["status_counts"].get("candidate_read_only", 0)
    probe["approved_for_catalog_only_count"] = probe["status_counts"].get(
        "approved_for_catalog_only",
        0,
    )
    probe["validation_errors"] = validate_preference_tool_catalog(probe)
    return probe


def _secret_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["catalog_entries"][0]["tool_ref"] = "pref_" + "agent_" + "DO_NOT_USE_EXAMPLE_SECRET"
    probe["validation_errors"] = validate_preference_tool_catalog(probe)
    return probe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="Fail unless PREF-1 has verified a non-anonymous Preference identity.",
    )
    parser.add_argument(
        "--no-event",
        action="store_true",
        help="Do not append the sanitized PREF-2 catalog event.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    artifact = build_preference_tool_catalog(settings=settings, record_event=not args.no_event)
    output_path, history_path = write_preference_tool_catalog(artifact, settings=settings)
    validation_errors = validate_preference_tool_catalog(artifact)
    authority_probe = _authority_probe(artifact)
    live_without_identity_probe = _live_without_identity_probe(artifact)
    outside_scope_probe = _outside_scope_probe(artifact)
    candidate_without_live_probe = _candidate_without_live_probe(artifact)
    secret_probe = _secret_probe(artifact)

    errors: list[str] = list(validation_errors)
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_in_catalog")
    if artifact["search_tools_call_attempted"] is not False:
        errors.append("search_tools_call_attempted")
    if artifact["live_catalog_call_attempted"] is not False:
        errors.append("live_catalog_call_attempted")
    if artifact["domain_tool_calls_allowed"] is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact["paid_tool_calls_allowed"] is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact["candidate_read_only_count"] != 0:
        errors.append("candidate_read_only_before_live_discovery")
    if args.require_verified and artifact["identity_gate_status"] != "verified_non_anonymous":
        errors.append("verified_identity_required")
    if not authority_probe["validation_errors"]:
        errors.append("authority_probe_not_rejected")
    if not live_without_identity_probe["validation_errors"]:
        errors.append("live_without_identity_probe_not_rejected")
    if not outside_scope_probe["validation_errors"]:
        errors.append("outside_scope_probe_not_rejected")
    if not candidate_without_live_probe["validation_errors"]:
        errors.append("candidate_without_live_probe_not_rejected")
    if not secret_probe["validation_errors"]:
        errors.append("secret_probe_not_rejected")

    print("preference_tool_catalog_status=" + artifact["status"])
    print(f"preference_tool_catalog_schema_version={PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION}")
    print(f"preference_tool_catalog_artifact_path={output_path}")
    print(f"preference_tool_catalog_history_path={history_path}")
    print(f"preference_tool_catalog_stage={artifact['stage']}")
    print(f"preference_tool_catalog_identity_gate_status={artifact['identity_gate_status']}")
    print(
        "preference_tool_catalog_identity_status="
        f"{artifact['identity_gate_identity_status']}"
    )
    print(
        "preference_tool_catalog_identity_quota_metadata_present="
        f"{artifact['identity_gate_quota_metadata_present']}"
    )
    print(
        "preference_tool_catalog_live_catalog_call_attempted="
        f"{artifact['live_catalog_call_attempted']}"
    )
    print(
        "preference_tool_catalog_search_tools_call_attempted="
        f"{artifact['search_tools_call_attempted']}"
    )
    print(f"preference_tool_catalog_search_tools_allowed={artifact['search_tools_allowed']}")
    print(
        "preference_tool_catalog_domain_tool_calls_allowed="
        f"{artifact['domain_tool_calls_allowed']}"
    )
    print(
        "preference_tool_catalog_paid_tool_calls_allowed="
        f"{artifact['paid_tool_calls_allowed']}"
    )
    print(f"preference_tool_catalog_domain_pack_count={artifact['domain_pack_count']}")
    print(f"preference_tool_catalog_entry_count={artifact['catalog_entry_count']}")
    print(
        "preference_tool_catalog_approved_for_catalog_only_count="
        f"{artifact['approved_for_catalog_only_count']}"
    )
    print(
        "preference_tool_catalog_candidate_read_only_count="
        f"{artifact['candidate_read_only_count']}"
    )
    print(
        "preference_tool_catalog_blocked_outside_scope_count="
        f"{artifact['blocked_outside_scope_count']}"
    )
    print(
        "preference_tool_catalog_blocked_paid_tool_count="
        f"{artifact['blocked_paid_tool_count']}"
    )
    print(
        "preference_tool_catalog_blocked_no_provenance_count="
        f"{artifact['blocked_no_provenance_count']}"
    )
    print(f"preference_tool_catalog_blocked_reason_count={artifact['blocked_reason_count']}")
    print(f"preference_tool_catalog_blocked_reasons={','.join(artifact['blocked_reasons'])}")
    print(f"preference_tool_catalog_validation_error_count={len(validation_errors)}")
    print(
        "preference_tool_catalog_authority_probe_error_count="
        f"{len(authority_probe['validation_errors'])}"
    )
    print(
        "preference_tool_catalog_live_without_identity_probe_error_count="
        f"{len(live_without_identity_probe['validation_errors'])}"
    )
    print(
        "preference_tool_catalog_outside_scope_probe_error_count="
        f"{len(outside_scope_probe['validation_errors'])}"
    )
    print(
        "preference_tool_catalog_candidate_without_live_probe_error_count="
        f"{len(candidate_without_live_probe['validation_errors'])}"
    )
    print(
        "preference_tool_catalog_secret_probe_error_count="
        f"{len(secret_probe['validation_errors'])}"
    )
    print(f"preference_tool_catalog_boundary={PREFERENCE_TOOL_CATALOG_BOUNDARY}")

    if errors:
        for error in errors:
            print(f"preference_tool_catalog_error={error}")
        print("preference_tool_catalog_check=failed")
        return 1

    print("preference_tool_catalog_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
