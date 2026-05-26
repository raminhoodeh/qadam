"""Preference/PREF MCP identity and status contract.

PREF-1 is deliberately narrow: it can inspect local configuration and, when
explicitly requested, call only the free account-status MCP tool. It cannot call
domain tools, consume paid tools, create observations, or change trading state.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status, secret_value

PREFERENCE_MCP_IDENTITY_SCHEMA_VERSION = 1
PREFERENCE_SOURCE_KEY = "preference_mcp"
PREFERENCE_PROVIDER_LABEL = "preference_labs_mcp"
PREFERENCE_STATUS_TOOL_NAME = "preference_account_status"
PREFERENCE_DISCOVERY_TOOL_NAME = "search_tools"
PREFERENCE_CLASSIFICATION = "proposed_supplemental_multi_source_data_plane"
PREFERENCE_EVENT_TYPE = "preference_mcp_identity_status_checked"
PREFERENCE_EVENT_COMPONENT = "preference_mcp_identity"
PREFERENCE_BOUNDARY = (
    "Preference/PREF MCP identity status is read-only. PREF-1 cannot call domain "
    "tools, consume paid tools, create trade candidates, approve risk, stage or "
    "submit paper orders, write to brokers, call quantum providers, submit "
    "hardware jobs, enable schedulers, provide fills, receipts, reconciliation "
    "truth, or enable live capital."
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _blank_authority_flags() -> dict[str, bool]:
    return {
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
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


def _key_format_status(api_key: str | None) -> str:
    if not api_key:
        return "missing"
    if api_key.startswith("pref_agent_") and len(api_key) > len("pref_agent_") + 8:
        return "agent_key_format"
    return "configured_unknown_format"


def _jsonrpc_account_status(api_key: str, settings: Settings) -> dict[str, Any]:
    request_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": PREFERENCE_STATUS_TOOL_NAME,
            "arguments": {},
        },
    }
    encoded = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        settings.preference_mcp_endpoint,
        data=encoded,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.preference_mcp_timeout_seconds) as response:
        response_bytes = response.read()
    decoded = json.loads(response_bytes.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("preference_mcp_status_response_not_object")
    return decoded


def _walk_values(payload: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for value in payload.values():
            values.append(value)
            values.extend(_walk_values(value))
    elif isinstance(payload, list):
        for item in payload:
            values.append(item)
            values.extend(_walk_values(item))
    return values


def _find_first_string(payload: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            found = _find_first_string(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first_string(item, keys)
            if found:
                return found
    return None


def _quota_metadata_present(payload: dict[str, Any]) -> bool:
    quota_markers = (
        "daily_included_credits",
        "persistent_credits",
        "remaining",
        "credits",
        "quota",
        "reset",
        "reset_at",
        "renews_at",
    )
    for value in _walk_values(payload):
        if isinstance(value, dict) and any(marker in value for marker in quota_markers):
            return True
    return any(marker in payload for marker in quota_markers)


def _identity_status_from_response(payload: dict[str, Any]) -> str:
    identity = _find_first_string(payload, ("identity", "identity_type", "account_type", "type"))
    if not identity:
        return "missing_identity"
    normalized = identity.strip().lower()
    if normalized == "anonymous":
        return "anonymous"
    if "linked" in normalized or "account" in normalized:
        return "linked_account"
    if "agent" in normalized or "registered" in normalized:
        return "registered_agent"
    return "non_anonymous"


def _sanitized_response_summary(payload: dict[str, Any]) -> dict[str, Any]:
    identity_status = _identity_status_from_response(payload)
    return {
        "identity_status": identity_status,
        "quota_metadata_present": _quota_metadata_present(payload),
        "jsonrpc_error_present": "error" in payload,
        "result_present": "result" in payload,
    }


def _live_status_check(settings: Settings, api_key: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _jsonrpc_account_status(api_key, settings), None
    except urllib.error.HTTPError as exc:
        return None, f"http_error:{exc.code}"
    except urllib.error.URLError as exc:
        return None, f"url_error:{exc.reason.__class__.__name__}"
    except TimeoutError:
        return None, "timeout"
    except Exception as exc:  # noqa: BLE001 - live status should degrade explicitly
        return None, f"status_check_error:{exc.__class__.__name__}"


def build_preference_mcp_identity_status(
    *,
    settings: Settings | None = None,
    live_status_check: bool = False,
    event_log: EventLog | None = None,
    record_event: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    credential = secret_status("PREFERENCE_API_KEY", settings)
    api_key = secret_value("PREFERENCE_API_KEY", settings)
    key_configured = bool(api_key)
    live_call_allowed = (
        live_status_check
        and settings.preference_mcp_enabled
        and key_configured
        and settings.preference_mcp_transport == "streamable-http"
    )
    blocked_reasons: list[str] = []
    live_response_summary: dict[str, Any] | None = None
    live_error: str | None = None

    if not settings.preference_mcp_enabled:
        blocked_reasons.append("preference_mcp_disabled")
    if not key_configured:
        blocked_reasons.append("preference_api_key_missing")
    if not live_status_check:
        blocked_reasons.append("live_status_check_not_requested")
    if settings.preference_mcp_transport != "streamable-http":
        blocked_reasons.append("unsupported_transport")

    live_call_attempted = False
    identity_status = "not_verified"
    quota_metadata_present = False
    if live_call_allowed and api_key:
        live_call_attempted = True
        live_response, live_error = _live_status_check(settings, api_key)
        if live_response is None:
            blocked_reasons.append(live_error or "live_status_check_failed")
        else:
            live_response_summary = _sanitized_response_summary(live_response)
            identity_status = str(live_response_summary["identity_status"])
            quota_metadata_present = bool(live_response_summary["quota_metadata_present"])
            if identity_status in {"anonymous", "missing_identity"}:
                blocked_reasons.append(f"identity_{identity_status}")
            if not quota_metadata_present:
                blocked_reasons.append("quota_metadata_missing")

    verified_identity = (
        live_call_attempted
        and identity_status not in {"anonymous", "missing_identity", "not_verified"}
        and quota_metadata_present
        and not live_error
    )
    status = "verified_non_anonymous" if verified_identity else "blocked"

    artifact = {
        "schema_version": PREFERENCE_MCP_IDENTITY_SCHEMA_VERSION,
        "artifact_type": "preference_mcp_identity_status",
        "artifact_id": "preference:pref-1:identity-status",
        "phase": "PREF",
        "stage": "PREF-1",
        "status": status,
        "generated_at": _now(),
        "public_safe": True,
        "classification": PREFERENCE_CLASSIFICATION,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "endpoint": settings.preference_mcp_endpoint,
        "transport": settings.preference_mcp_transport,
        "enabled": settings.preference_mcp_enabled,
        "credential_status": {
            "key": "PREFERENCE_API_KEY",
            "configured": credential.configured,
            "source": credential.source,
            "key_format_status": _key_format_status(api_key),
        },
        "live_status_check_requested": live_status_check,
        "live_status_call_attempted": live_call_attempted,
        "live_status_error": live_error,
        "identity_status": identity_status,
        "quota_metadata_present": quota_metadata_present,
        "live_response_summary": live_response_summary,
        "daily_call_budget": settings.preference_mcp_daily_call_budget,
        "run_call_budget": settings.preference_mcp_run_call_budget,
        "paid_tools_allowed_by_config": settings.preference_mcp_paid_tools_allowed,
        "tool_allowlist_count": len(settings.preference_mcp_tool_allowlist),
        "domain_allowlist": list(settings.preference_mcp_domain_allowlist),
        "domain_allowlist_count": len(settings.preference_mcp_domain_allowlist),
        "status_tool_name": PREFERENCE_STATUS_TOOL_NAME,
        "discovery_tool_name": PREFERENCE_DISCOVERY_TOOL_NAME,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "blocked_reason_count": len(set(blocked_reasons)),
        "authority_flags": _blank_authority_flags(),
        "boundary": PREFERENCE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_mcp_identity_status(artifact)

    if record_event:
        event_log = event_log or EventLog(echo=False)
        event_log.write(
            PREFERENCE_EVENT_TYPE,
            PREFERENCE_EVENT_COMPONENT,
            {
                "stage": artifact["stage"],
                "status": artifact["status"],
                "enabled": artifact["enabled"],
                "credential_configured": credential.configured,
                "credential_source": credential.source,
                "live_status_call_attempted": live_call_attempted,
                "identity_status": identity_status,
                "quota_metadata_present": quota_metadata_present,
                "blocked_reasons": artifact["blocked_reasons"],
                "domain_tool_calls_allowed": False,
                "paid_tool_calls_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            },
        )
    return artifact


def validate_preference_mcp_identity_status(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "status",
        "public_safe",
        "credential_status",
        "identity_status",
        "quota_metadata_present",
        "domain_tool_calls_allowed",
        "paid_tool_calls_allowed",
        "authority_flags",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    for field in missing:
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_MCP_IDENTITY_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != "preference_mcp_identity_status":
        errors.append("artifact_type_not_preference_mcp_identity_status")
    if artifact.get("stage") != "PREF-1":
        errors.append("stage_not_pref_1")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("domain_tool_calls_allowed") is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact.get("paid_tool_calls_allowed") is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact.get("paid_tools_allowed_by_config") is not False:
        errors.append("paid_tools_allowed_by_config")
    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for key, value in flags.items():
            if value is not False:
                errors.append(f"authority_flag_enabled:{key}")
    if artifact.get("status") == "verified_non_anonymous":
        if artifact.get("identity_status") in {"anonymous", "missing_identity", "not_verified"}:
            errors.append("verified_with_invalid_identity")
        if artifact.get("quota_metadata_present") is not True:
            errors.append("verified_without_quota_metadata")
        if artifact.get("live_status_call_attempted") is not True:
            errors.append("verified_without_live_status_call")
    else:
        blocked = artifact.get("blocked_reasons", [])
        if not isinstance(blocked, list) or not blocked:
            errors.append("blocked_without_reason")
    credential_status = artifact.get("credential_status", {})
    if isinstance(credential_status, dict) and any(
        str(value).startswith("pref_agent_") for value in credential_status.values()
    ):
        errors.append("credential_secret_value_exposed")
    if _has_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors
