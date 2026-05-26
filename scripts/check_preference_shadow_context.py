#!/usr/bin/env python3
"""Validate PREF-8 Preference/PREF MCP shadow-intelligence enrichment."""

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

from orchestrator.preference_mcp_shadow_context import (  # noqa: E402
    PREFERENCE_SHADOW_CONTEXT_BOUNDARY,
    PREFERENCE_SHADOW_CONTEXT_ROLE,
    PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION,
    PREFERENCE_SHADOW_CONTEXT_STAGE,
    build_preference_shadow_context,
    preference_shadow_packet_context,
    validate_preference_shadow_context,
    write_preference_shadow_context,
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
    probe["trade_candidate_creation_allowed"] = True
    probe["authority_flags"]["trade_candidate_creation_allowed"] = True
    probe["shadow_observations"][0]["trade_candidate_creation_allowed"] = True
    probe["validation_errors"] = validate_preference_shadow_context(probe)
    return probe


def _preference_only_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["preference_only_confirmation_allowed"] = True
    probe["validation_errors"] = validate_preference_shadow_context(probe)
    return probe


def _orderbook_permission_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["orderbook_depth_execution_or_venue_permission"] = True
    for observation in probe["shadow_observations"]:
        if observation.get("signal_class") == "orderbook_depth":
            observation["orderbook_depth_execution_or_venue_permission"] = True
            break
    probe["validation_errors"] = validate_preference_shadow_context(probe)
    return probe


def _wallet_company_truth_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["wallet_kol_company_truth_allowed"] = True
    for observation in probe["shadow_observations"]:
        if observation.get("domain_pack") == "crypto_wallets":
            observation["wallet_kol_company_truth_allowed"] = True
            observation["context_role"] = "company_truth"
            break
    probe["validation_errors"] = validate_preference_shadow_context(probe)
    return probe


def _missing_challenge_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["quota_degraded"] = True
    probe["active_required_challenges"] = [
        item
        for item in probe["active_required_challenges"]
        if "quota" not in str(item).lower()
    ]
    probe["active_required_challenge_count"] = len(probe["active_required_challenges"])
    probe["validation_errors"] = validate_preference_shadow_context(probe)
    return probe


def main() -> int:
    errors: list[str] = []
    artifact = build_preference_shadow_context(record_event=True)
    output_path, history_path = write_preference_shadow_context(artifact)
    validation_errors = validate_preference_shadow_context(artifact)
    packet_context = preference_shadow_packet_context(artifact)

    authority_probe = _authority_probe(artifact)
    preference_only_probe = _preference_only_probe(artifact)
    orderbook_permission_probe = _orderbook_permission_probe(artifact)
    wallet_company_truth_probe = _wallet_company_truth_probe(artifact)
    missing_challenge_probe = _missing_challenge_probe(artifact)

    if validation_errors:
        errors.extend(validation_errors)
    if _contains_secret_like_value(artifact) or _contains_secret_like_value(packet_context):
        errors.append("secret_like_value_in_shadow_context")
    if artifact["status"] != "challenge_only_ready":
        errors.append("shadow_context_not_ready")
    if artifact["context_role"] != PREFERENCE_SHADOW_CONTEXT_ROLE:
        errors.append("context_role_mismatch")
    if artifact["shadow_observation_count"] < 1:
        errors.append("shadow_observations_missing")
    if artifact["active_required_challenge_count"] < 1:
        errors.append("active_required_challenges_missing")
    if artifact["source_quorum_credit_allowed"] is not False:
        errors.append("source_quorum_credit_allowed")
    if artifact["preference_only_confirmation_allowed"] is not False:
        errors.append("preference_only_confirmation_allowed")
    if artifact["orderbook_depth_execution_or_venue_permission"] is not False:
        errors.append("orderbook_depth_execution_or_venue_permission")
    if artifact["wallet_kol_company_truth_allowed"] is not False:
        errors.append("wallet_kol_company_truth_allowed")
    if artifact["trade_candidate_creation_allowed"] is not False:
        errors.append("trade_candidate_creation_allowed")
    if artifact["risk_handoff_allowed"] is not False:
        errors.append("risk_handoff_allowed")
    if artifact["execution_allowed"] is not False or artifact["broker_write_allowed"] is not False:
        errors.append("execution_or_broker_authority_enabled")
    if packet_context["trade_candidate_creation_allowed"] is not False:
        errors.append("packet_context_trade_candidate_creation_allowed")
    if packet_context["source_quorum_credit_allowed"] is not False:
        errors.append("packet_context_source_quorum_credit_allowed")
    if not any(
        error.startswith("authority_flag_enabled:")
        for error in authority_probe["validation_errors"]
    ):
        errors.append("authority_probe_not_rejected")
    if "artifact_authority_enabled:preference_only_confirmation_allowed" not in (
        preference_only_probe["validation_errors"]
    ):
        errors.append("preference_only_probe_not_rejected")
    if "artifact_authority_enabled:orderbook_depth_execution_or_venue_permission" not in (
        orderbook_permission_probe["validation_errors"]
    ):
        errors.append("orderbook_permission_probe_not_rejected")
    if "artifact_authority_enabled:wallet_kol_company_truth_allowed" not in (
        wallet_company_truth_probe["validation_errors"]
    ):
        errors.append("wallet_company_truth_probe_not_rejected")
    if "quota_degraded_without_challenge" not in missing_challenge_probe["validation_errors"]:
        errors.append("missing_challenge_probe_not_rejected")

    print("preference_shadow_context_status=" + artifact["status"])
    print(f"preference_shadow_context_schema_version={PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION}")
    print(f"preference_shadow_context_stage={PREFERENCE_SHADOW_CONTEXT_STAGE}")
    print(f"preference_shadow_context_artifact_path={output_path}")
    print(f"preference_shadow_context_history_path={history_path}")
    print(f"preference_shadow_context_role={artifact['context_role']}")
    print(f"preference_shadow_context_identity_gate_status={artifact['identity_gate_status']}")
    print(f"preference_shadow_context_quota_degraded={artifact['quota_degraded']}")
    print(f"preference_shadow_context_context_stale={artifact['context_stale']}")
    print(f"preference_shadow_context_single_source_hold={artifact['single_source_hold']}")
    print(f"preference_shadow_context_missing_provenance_hold={artifact['missing_provenance_hold']}")
    print(f"preference_shadow_context_shadow_observation_count={artifact['shadow_observation_count']}")
    print(
        "preference_shadow_context_distinct_upstream_source_count="
        f"{artifact['preference_distinct_upstream_source_count']}"
    )
    print(
        "preference_shadow_context_active_required_challenge_count="
        f"{artifact['active_required_challenge_count']}"
    )
    print(
        "preference_shadow_context_source_quorum_credit_allowed="
        f"{artifact['source_quorum_credit_allowed']}"
    )
    print(
        "preference_shadow_context_preference_only_confirmation_allowed="
        f"{artifact['preference_only_confirmation_allowed']}"
    )
    print(
        "preference_shadow_context_orderbook_depth_execution_or_venue_permission="
        f"{artifact['orderbook_depth_execution_or_venue_permission']}"
    )
    print(
        "preference_shadow_context_wallet_kol_company_truth_allowed="
        f"{artifact['wallet_kol_company_truth_allowed']}"
    )
    print(
        "preference_shadow_context_trade_candidate_creation_allowed="
        f"{artifact['trade_candidate_creation_allowed']}"
    )
    print(f"preference_shadow_context_execution_allowed={artifact['execution_allowed']}")
    print(f"preference_shadow_context_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"preference_shadow_context_validation_error_count={len(validation_errors)}")
    print(f"preference_shadow_context_authority_probe_error_count={len(authority_probe['validation_errors'])}")
    print(
        "preference_shadow_context_preference_only_probe_error_count="
        f"{len(preference_only_probe['validation_errors'])}"
    )
    print(
        "preference_shadow_context_orderbook_permission_probe_error_count="
        f"{len(orderbook_permission_probe['validation_errors'])}"
    )
    print(
        "preference_shadow_context_wallet_company_truth_probe_error_count="
        f"{len(wallet_company_truth_probe['validation_errors'])}"
    )
    print(
        "preference_shadow_context_missing_challenge_probe_error_count="
        f"{len(missing_challenge_probe['validation_errors'])}"
    )
    print(f"preference_shadow_context_boundary={PREFERENCE_SHADOW_CONTEXT_BOUNDARY}")

    if errors:
        for error in errors:
            print(f"preference_shadow_context_error={error}")
        print("preference_shadow_context_check=failed")
        return 1

    print("preference_shadow_context_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
