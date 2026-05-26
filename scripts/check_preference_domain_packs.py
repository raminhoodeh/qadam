#!/usr/bin/env python3
"""Validate PREF-7 Preference/PREF MCP first-universe domain-pack mapping."""

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

from orchestrator.preference_mcp_domain_packs import (  # noqa: E402
    PREFERENCE_DOMAIN_PACK_BOUNDARY,
    PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION,
    PREFERENCE_DOMAIN_PACK_STAGE,
    build_preference_domain_pack_mapping,
    validate_preference_domain_pack_mapping,
    write_preference_domain_pack_mapping,
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


def _missing_family_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["mappings"] = probe["mappings"][:-1]
    probe["strategy_family_count"] = len(probe["mappings"])
    probe["strategy_family_with_allowed_pack_count"] = len(probe["mappings"])
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def _authority_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["domain_tool_calls_allowed"] = True
    probe["authority_flags"]["domain_tool_calls_allowed"] = True
    probe["mappings"][0]["authority_flags"]["domain_tool_calls_allowed"] = True
    probe["mappings"][0]["mapped_domain_packs"][0]["domain_tool_calls_allowed"] = True
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def _preference_only_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["preference_only_confirmation_allowed"] = True
    probe["mappings"][0]["preference_only_confirmation_allowed"] = True
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def _sports_pack_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    sports_pack = deepcopy(probe["mappings"][0]["mapped_domain_packs"][0])
    sports_pack["domain_pack"] = "sports_lines"
    sports_pack["source_scope"] = "outside_current_strategy_universe"
    sports_pack["approval_status"] = "approved_for_catalog_only"
    probe["mappings"][0]["mapped_domain_packs"].append(sports_pack)
    probe["unique_domain_packs"] = sorted({pack["domain_pack"] for mapping in probe["mappings"] for pack in mapping["mapped_domain_packs"]})
    probe["unique_domain_pack_count"] = len(probe["unique_domain_packs"])
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def _wallet_company_truth_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    for mapping in probe["mappings"]:
        for pack in mapping["mapped_domain_packs"]:
            if pack["domain_pack"] == "crypto_wallets":
                pack["company_truth_allowed"] = True
                pack["allowed_context_role"] = "company_truth"
                break
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def _source_quorum_probe(base: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(base)
    probe["source_quorum_credit_allowed"] = True
    probe["mappings"][0]["source_quorum_credit_allowed"] = True
    probe["mappings"][0]["mapped_domain_packs"][0]["source_quorum_credit_allowed"] = True
    probe["validation_errors"] = validate_preference_domain_pack_mapping(probe)
    return probe


def main() -> int:
    errors: list[str] = []
    artifact = build_preference_domain_pack_mapping()
    output_path, history_path = write_preference_domain_pack_mapping(artifact)
    validation_errors = validate_preference_domain_pack_mapping(artifact)

    missing_family_probe = _missing_family_probe(artifact)
    authority_probe = _authority_probe(artifact)
    preference_only_probe = _preference_only_probe(artifact)
    sports_pack_probe = _sports_pack_probe(artifact)
    wallet_company_truth_probe = _wallet_company_truth_probe(artifact)
    source_quorum_probe = _source_quorum_probe(artifact)

    if validation_errors:
        errors.extend(validation_errors)
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_in_domain_pack_mapping")
    if artifact["strategy_family_count"] != artifact["expected_strategy_family_count"]:
        errors.append("strategy_family_count_mismatch")
    if artifact["strategy_family_with_allowed_pack_count"] != artifact["expected_strategy_family_count"]:
        errors.append("not_all_strategy_families_have_allowed_pack")
    if artifact["domain_tool_calls_allowed"] is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact["paid_tool_calls_allowed"] is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact["source_quorum_credit_allowed"] is not False:
        errors.append("source_quorum_credit_allowed")
    if artifact["preference_only_confirmation_allowed"] is not False:
        errors.append("preference_only_confirmation_allowed")
    if artifact["trade_candidate_creation_allowed"] is not False:
        errors.append("trade_candidate_creation_allowed")
    if not any(error.startswith("strategy_family_missing_domain_pack:") for error in missing_family_probe["validation_errors"]):
        errors.append("missing_family_probe_not_rejected")
    if not any(error.startswith("authority_flag_enabled:") for error in authority_probe["validation_errors"]):
        errors.append("authority_probe_not_rejected")
    if "artifact_authority_enabled:preference_only_confirmation_allowed" not in preference_only_probe["validation_errors"]:
        errors.append("preference_only_probe_not_rejected")
    if not any(error.startswith("sports_lines_domain_pack_mapped:") for error in sports_pack_probe["validation_errors"]):
        errors.append("sports_pack_probe_not_rejected")
    if not any(error.startswith("crypto_wallets_company_truth_allowed:") for error in wallet_company_truth_probe["validation_errors"]):
        errors.append("wallet_company_truth_probe_not_rejected")
    if "artifact_authority_enabled:source_quorum_credit_allowed" not in source_quorum_probe["validation_errors"]:
        errors.append("source_quorum_probe_not_rejected")

    print("preference_domain_pack_status=" + artifact["status"])
    print(f"preference_domain_pack_schema_version={PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION}")
    print(f"preference_domain_pack_stage={PREFERENCE_DOMAIN_PACK_STAGE}")
    print(f"preference_domain_pack_artifact_path={output_path}")
    print(f"preference_domain_pack_history_path={history_path}")
    print(f"preference_domain_pack_catalog_status={artifact['catalog_status']}")
    print(f"preference_domain_pack_catalog_live_call_attempted={artifact['catalog_live_call_attempted']}")
    print(f"preference_domain_pack_strategy_family_count={artifact['strategy_family_count']}")
    print(f"preference_domain_pack_expected_strategy_family_count={artifact['expected_strategy_family_count']}")
    print(
        "preference_domain_pack_strategy_family_with_allowed_pack_count="
        f"{artifact['strategy_family_with_allowed_pack_count']}"
    )
    print(f"preference_domain_pack_unique_domain_pack_count={artifact['unique_domain_pack_count']}")
    print(f"preference_domain_pack_unique_domain_packs={','.join(artifact['unique_domain_packs'])}")
    print(f"preference_domain_pack_live_mcp_call_allowed={artifact['live_mcp_call_allowed']}")
    print(f"preference_domain_pack_search_tools_allowed={artifact['search_tools_allowed']}")
    print(f"preference_domain_pack_domain_tool_calls_allowed={artifact['domain_tool_calls_allowed']}")
    print(f"preference_domain_pack_paid_tool_calls_allowed={artifact['paid_tool_calls_allowed']}")
    print(f"preference_domain_pack_source_quorum_credit_allowed={artifact['source_quorum_credit_allowed']}")
    print(
        "preference_domain_pack_preference_only_confirmation_allowed="
        f"{artifact['preference_only_confirmation_allowed']}"
    )
    print(f"preference_domain_pack_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"preference_domain_pack_execution_allowed={artifact['execution_allowed']}")
    print(f"preference_domain_pack_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"preference_domain_pack_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"preference_domain_pack_live_capital_enabled={artifact['live_capital_enabled']}")
    print(f"preference_domain_pack_validation_error_count={len(validation_errors)}")
    print(f"preference_domain_pack_missing_family_probe_error_count={len(missing_family_probe['validation_errors'])}")
    print(f"preference_domain_pack_authority_probe_error_count={len(authority_probe['validation_errors'])}")
    print(f"preference_domain_pack_preference_only_probe_error_count={len(preference_only_probe['validation_errors'])}")
    print(f"preference_domain_pack_sports_pack_probe_error_count={len(sports_pack_probe['validation_errors'])}")
    print(
        "preference_domain_pack_wallet_company_truth_probe_error_count="
        f"{len(wallet_company_truth_probe['validation_errors'])}"
    )
    print(f"preference_domain_pack_source_quorum_probe_error_count={len(source_quorum_probe['validation_errors'])}")
    print(f"preference_domain_pack_boundary={PREFERENCE_DOMAIN_PACK_BOUNDARY}")

    if errors:
        for error in errors:
            print(f"preference_domain_pack_error={error}")
        print("preference_domain_pack_check=failed")
        return 1

    print("preference_domain_pack_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
