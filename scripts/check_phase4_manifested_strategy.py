#!/usr/bin/env python3
"""Validate the Q4-8 Manifested Strategy Draft and metadata artifact."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_manifested_strategy import (  # noqa: E402
    MANIFESTED_STRATEGY_PATH,
    REQUIRED_DOCUMENT_TERMS,
    build_manifested_strategy_metadata,
    validate_manifested_strategy_metadata,
    write_manifested_strategy_metadata,
)


def main() -> int:
    errors: list[str] = []
    artifact = build_manifested_strategy_metadata(MANIFESTED_STRATEGY_PATH)
    output_path = write_manifested_strategy_metadata(artifact)
    text = Path(MANIFESTED_STRATEGY_PATH).read_text(encoding="utf-8") if Path(MANIFESTED_STRATEGY_PATH).exists() else ""
    validation_errors = validate_manifested_strategy_metadata(artifact, document_text=text)

    lowered = text.lower()
    term_complete_count = sum(1 for term in REQUIRED_DOCUMENT_TERMS if term.lower() in lowered)
    candidate_complete_count = sum(
        1 for candidate_key in artifact["strategy_family_candidate_keys"] if candidate_key.lower() in lowered
    )
    instrument_complete_count = sum(1 for instrument in artifact["active_instruments"] if instrument.lower() in lowered)
    preference_manifestation = artifact.get("preference_mcp_manifestation", {})
    preference_domain_pack_complete_count = sum(
        1
        for domain_pack in preference_manifestation.get("approved_domain_packs", [])
        if str(domain_pack).lower() in lowered
    )

    missing_term_probe = deepcopy(artifact)
    missing_term_errors = validate_manifested_strategy_metadata(
        missing_term_probe,
        document_text=text.replace("No execution", "Execution disabled"),
    )

    fingerprint_probe = deepcopy(artifact)
    fingerprint_probe["document_fingerprint"] = "bad-fingerprint"
    fingerprint_probe_errors = validate_manifested_strategy_metadata(fingerprint_probe, document_text=text)

    approval_probe = deepcopy(artifact)
    approval_probe["approval_required"] = False
    approval_probe_errors = validate_manifested_strategy_metadata(approval_probe, document_text=text)

    authority_probe = deepcopy(artifact)
    authority_probe["execution_allowed"] = True
    authority_probe_errors = validate_manifested_strategy_metadata(authority_probe, document_text=text)

    trade_candidate_probe = deepcopy(artifact)
    trade_candidate_probe["trade_candidate_count"] = 1
    trade_candidate_errors = validate_manifested_strategy_metadata(trade_candidate_probe, document_text=text)

    preference_source_quorum_probe = deepcopy(artifact)
    preference_source_quorum_probe["preference_mcp_manifestation"]["source_quorum_credit_allowed"] = True
    preference_source_quorum_errors = validate_manifested_strategy_metadata(
        preference_source_quorum_probe,
        document_text=text,
    )

    preference_domain_probe = deepcopy(artifact)
    preference_domain_probe["preference_mcp_manifestation"]["approved_domain_packs"] = []
    preference_domain_probe["preference_mcp_manifestation"]["approved_domain_pack_count"] = 0
    preference_domain_errors = validate_manifested_strategy_metadata(preference_domain_probe, document_text=text)

    preference_term_errors = validate_manifested_strategy_metadata(
        artifact,
        document_text=text.replace("Preference/PREF MCP", "PREF provider"),
    )

    print("phase4_manifested_strategy_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_manifested_strategy_schema_version={artifact['manifested_strategy_metadata_schema_version']}")
    print(f"phase4_manifested_strategy_document_path={artifact['document_path']}")
    print(f"phase4_manifested_strategy_metadata_path={output_path}")
    print(f"phase4_manifested_strategy_document_fingerprint={artifact['document_fingerprint']}")
    print(f"phase4_manifested_strategy_active_instrument_count={artifact['active_instrument_count']}")
    print(f"phase4_manifested_strategy_catalyst_class_count={artifact['catalyst_class_count']}")
    print(f"phase4_manifested_strategy_candidate_count={artifact['strategy_family_candidate_count']}")
    print(f"phase4_manifested_strategy_trade_candidate_count={artifact['trade_candidate_count']}")
    print(f"phase4_manifested_strategy_term_complete_count={term_complete_count}")
    print(f"phase4_manifested_strategy_candidate_complete_count={candidate_complete_count}")
    print(f"phase4_manifested_strategy_instrument_complete_count={instrument_complete_count}")
    print(
        "phase4_manifested_strategy_preference_domain_pack_count="
        f"{preference_manifestation.get('approved_domain_pack_count')}"
    )
    print(
        "phase4_manifested_strategy_preference_domain_pack_complete_count="
        f"{preference_domain_pack_complete_count}"
    )
    print(
        "phase4_manifested_strategy_preference_family_policy_count="
        f"{preference_manifestation.get('candidate_family_with_policy_count')}"
    )
    print(f"phase4_manifested_strategy_approval_required={artifact['approval_required']}")
    print(f"phase4_manifested_strategy_approval_state={artifact['approval_state']}")
    print(f"phase4_manifested_strategy_approved_shadow_ready={artifact['approved_shadow_ready']}")
    print(f"phase4_manifested_strategy_validation_error_count={len(validation_errors)}")
    print(f"phase4_manifested_strategy_missing_term_probe_error_count={len(missing_term_errors)}")
    print(f"phase4_manifested_strategy_fingerprint_probe_error_count={len(fingerprint_probe_errors)}")
    print(f"phase4_manifested_strategy_approval_probe_error_count={len(approval_probe_errors)}")
    print(f"phase4_manifested_strategy_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_manifested_strategy_trade_candidate_probe_error_count={len(trade_candidate_errors)}")
    print(
        "phase4_manifested_strategy_preference_source_quorum_probe_error_count="
        f"{len(preference_source_quorum_errors)}"
    )
    print(
        "phase4_manifested_strategy_preference_domain_probe_error_count="
        f"{len(preference_domain_errors)}"
    )
    print(
        "phase4_manifested_strategy_preference_term_probe_error_count="
        f"{len(preference_term_errors)}"
    )
    print(
        "phase4_manifested_strategy_preference_source_quorum_credit_allowed="
        f"{artifact['preference_source_quorum_credit_allowed']}"
    )
    print(
        "phase4_manifested_strategy_preference_only_confirmation_allowed="
        f"{artifact['preference_only_confirmation_allowed']}"
    )
    print(f"phase4_manifested_strategy_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_manifested_strategy_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_manifested_strategy_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_manifested_strategy_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_manifested_strategy_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["document_fingerprint"] is None:
        errors.append("document_fingerprint_missing")
    if term_complete_count != len(REQUIRED_DOCUMENT_TERMS):
        errors.append("required_terms_missing")
    if candidate_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("candidate_sections_missing")
    if instrument_complete_count != artifact["active_instrument_count"]:
        errors.append("active_instruments_missing")
    if preference_domain_pack_complete_count != preference_manifestation.get("approved_domain_pack_count"):
        errors.append("preference_domain_packs_missing")
    if preference_manifestation.get("candidate_family_with_policy_count") != artifact["strategy_family_candidate_count"]:
        errors.append("preference_family_policy_count_mismatch")
    if artifact["trade_candidate_count"] != 0:
        errors.append("trade_candidate_count_not_zero")
    if artifact["approval_required"] is not True or artifact["approval_state"] != "not_requested":
        errors.append("approval_state_invalid")
    if artifact["approved_shadow_ready"] is not False:
        errors.append("approved_shadow_ready_not_false")
    if "manifested_strategy_missing_term:No execution" not in missing_term_errors:
        errors.append("missing_term_probe_not_rejected")
    if "document_fingerprint_mismatch" not in fingerprint_probe_errors:
        errors.append("fingerprint_probe_not_rejected")
    if "approval_required_not_true" not in approval_probe_errors:
        errors.append("approval_probe_not_rejected")
    if not any(error.startswith("manifested_strategy_authority_enabled:") for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if "trade_candidate_count_not_zero" not in trade_candidate_errors:
        errors.append("trade_candidate_probe_not_rejected")
    if "preference_manifestation_authority_enabled:source_quorum_credit_allowed" not in preference_source_quorum_errors:
        errors.append("preference_source_quorum_probe_not_rejected")
    if "preference_manifestation_domain_packs_missing" not in preference_domain_errors:
        errors.append("preference_domain_probe_not_rejected")
    if "manifested_strategy_missing_term:Preference/PREF MCP" not in preference_term_errors:
        errors.append("preference_term_probe_not_rejected")
    for key in (
        "trade_candidate_creation_allowed",
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "preference_source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "preference_trade_candidate_creation_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_manifested_strategy_error={error}")
        print("phase4_manifested_strategy_check=failed")
        return 1

    print("phase4_manifested_strategy_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
