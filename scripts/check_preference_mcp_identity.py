#!/usr/bin/env python3
"""Validate PREF-1 Preference/PREF MCP identity and status gating."""

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
from orchestrator.preference_mcp_identity import (  # noqa: E402
    PREFERENCE_BOUNDARY,
    PREFERENCE_CLASSIFICATION,
    PREFERENCE_MCP_IDENTITY_SCHEMA_VERSION,
    build_preference_mcp_identity_status,
    validate_preference_mcp_identity_status,
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


def _write_runtime_artifact(settings: Settings, artifact: dict[str, Any]) -> Path:
    output_path = Path(settings.runtime_dir) / "preference_mcp_identity_status.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _positive_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["status"] = "verified_non_anonymous"
    probe["enabled"] = True
    probe["live_status_check_requested"] = True
    probe["live_status_call_attempted"] = True
    probe["live_status_error"] = None
    probe["identity_status"] = "registered_agent"
    probe["quota_metadata_present"] = True
    probe["live_response_summary"] = {
        "identity_status": "registered_agent",
        "quota_metadata_present": True,
        "jsonrpc_error_present": False,
        "result_present": True,
    }
    probe["blocked_reasons"] = []
    probe["blocked_reason_count"] = 0
    probe["validation_errors"] = validate_preference_mcp_identity_status(probe)
    return probe


def _anonymous_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = _positive_probe(base)
    probe["identity_status"] = "anonymous"
    probe["live_response_summary"]["identity_status"] = "anonymous"
    probe["validation_errors"] = validate_preference_mcp_identity_status(probe)
    return probe


def _quota_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = _positive_probe(base)
    probe["quota_metadata_present"] = False
    probe["live_response_summary"]["quota_metadata_present"] = False
    probe["validation_errors"] = validate_preference_mcp_identity_status(probe)
    return probe


def _authority_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["domain_tool_calls_allowed"] = True
    probe["authority_flags"]["domain_tool_calls_allowed"] = True
    probe["validation_errors"] = validate_preference_mcp_identity_status(probe)
    return probe


def _secret_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["credential_status"]["source"] = "pref_" + "agent_" + "DO_NOT_USE_EXAMPLE_SECRET"
    probe["validation_errors"] = validate_preference_mcp_identity_status(probe)
    return probe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-status-only",
        action="store_true",
        help="Attempt only the Preference account-status MCP call when enabled and configured.",
    )
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="Fail unless a non-anonymous Preference identity with quota metadata is verified.",
    )
    parser.add_argument(
        "--no-event",
        action="store_true",
        help="Do not append the sanitized PREF-1 status event.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    artifact = build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=args.live_status_only,
        record_event=not args.no_event,
    )
    output_path = _write_runtime_artifact(settings, artifact)
    validation_errors = validate_preference_mcp_identity_status(artifact)
    positive_probe = _positive_probe(artifact)
    anonymous_probe = _anonymous_probe(artifact)
    quota_probe = _quota_probe(artifact)
    authority_probe = _authority_probe(artifact)
    secret_probe = _secret_probe(artifact)

    errors: list[str] = list(validation_errors)
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_in_status")
    if artifact["paid_tool_calls_allowed"] is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact["domain_tool_calls_allowed"] is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact["authority_flags"].get("broker_write_authority") is not False:
        errors.append("broker_write_authority_enabled")
    if artifact["authority_flags"].get("live_capital_authority") is not False:
        errors.append("live_capital_authority_enabled")
    if artifact["status"] == "verified_non_anonymous" and artifact["identity_status"] == "anonymous":
        errors.append("anonymous_identity_verified")
    if args.require_verified and artifact["status"] != "verified_non_anonymous":
        errors.append("verified_identity_required")
    if positive_probe["validation_errors"]:
        errors.append("positive_probe_failed")
    if not anonymous_probe["validation_errors"]:
        errors.append("anonymous_probe_not_rejected")
    if not quota_probe["validation_errors"]:
        errors.append("quota_probe_not_rejected")
    if not authority_probe["validation_errors"]:
        errors.append("authority_probe_not_rejected")
    if not secret_probe["validation_errors"]:
        errors.append("secret_probe_not_rejected")

    print("preference_mcp_identity_status=" + artifact["status"])
    print(f"preference_mcp_identity_schema_version={PREFERENCE_MCP_IDENTITY_SCHEMA_VERSION}")
    print(f"preference_mcp_identity_classification={PREFERENCE_CLASSIFICATION}")
    print(f"preference_mcp_identity_artifact_path={output_path}")
    print(f"preference_mcp_identity_stage={artifact['stage']}")
    print(f"preference_mcp_identity_enabled={artifact['enabled']}")
    print(
        "preference_mcp_identity_credential_configured="
        f"{artifact['credential_status']['configured']}"
    )
    print(f"preference_mcp_identity_credential_source={artifact['credential_status']['source']}")
    print(
        "preference_mcp_identity_key_format_status="
        f"{artifact['credential_status']['key_format_status']}"
    )
    print(
        "preference_mcp_identity_live_status_check_requested="
        f"{artifact['live_status_check_requested']}"
    )
    print(
        "preference_mcp_identity_live_status_call_attempted="
        f"{artifact['live_status_call_attempted']}"
    )
    print(f"preference_mcp_identity_live_status_error={artifact['live_status_error']}")
    print(f"preference_mcp_identity_identity_status={artifact['identity_status']}")
    print(f"preference_mcp_identity_quota_metadata_present={artifact['quota_metadata_present']}")
    print(f"preference_mcp_identity_daily_call_budget={artifact['daily_call_budget']}")
    print(f"preference_mcp_identity_run_call_budget={artifact['run_call_budget']}")
    print(
        "preference_mcp_identity_paid_tools_allowed_by_config="
        f"{artifact['paid_tools_allowed_by_config']}"
    )
    print(f"preference_mcp_identity_tool_allowlist_count={artifact['tool_allowlist_count']}")
    print(f"preference_mcp_identity_domain_allowlist_count={artifact['domain_allowlist_count']}")
    print(f"preference_mcp_identity_domain_allowlist={','.join(artifact['domain_allowlist'])}")
    print(f"preference_mcp_identity_blocked_reason_count={artifact['blocked_reason_count']}")
    print(f"preference_mcp_identity_blocked_reasons={','.join(artifact['blocked_reasons'])}")
    print(f"preference_mcp_identity_domain_tool_calls_allowed={artifact['domain_tool_calls_allowed']}")
    print(f"preference_mcp_identity_paid_tool_calls_allowed={artifact['paid_tool_calls_allowed']}")
    print(
        "preference_mcp_identity_trade_candidate_creation_allowed="
        f"{artifact['authority_flags']['trade_candidate_creation_allowed']}"
    )
    print(
        "preference_mcp_identity_broker_write_authority="
        f"{artifact['authority_flags']['broker_write_authority']}"
    )
    print(
        "preference_mcp_identity_live_capital_authority="
        f"{artifact['authority_flags']['live_capital_authority']}"
    )
    print(f"preference_mcp_identity_validation_error_count={len(validation_errors)}")
    print(
        "preference_mcp_identity_positive_probe_error_count="
        f"{len(positive_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_identity_anonymous_probe_error_count="
        f"{len(anonymous_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_identity_quota_probe_error_count="
        f"{len(quota_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_identity_authority_probe_error_count="
        f"{len(authority_probe['validation_errors'])}"
    )
    print(
        "preference_mcp_identity_secret_probe_error_count="
        f"{len(secret_probe['validation_errors'])}"
    )
    print(f"preference_mcp_identity_boundary={PREFERENCE_BOUNDARY}")

    if errors:
        for error in errors:
            print(f"preference_mcp_identity_error={error}")
        print("preference_mcp_identity_check=failed")
        return 1

    print("preference_mcp_identity_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
