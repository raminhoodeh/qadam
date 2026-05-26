#!/usr/bin/env python3
"""Validate Q6-1 Phase 6 artifact schema and authority ledger contracts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase6_artifacts import (  # noqa: E402
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_ARTIFACT_TYPES,
    PHASE6_AUTHORITY_FIELDS,
    PHASE6_STATUS_ENUMS,
    PHASE6_UNSAFE_COUNT_FIELDS,
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
    phase6_artifact_contracts,
    phase6_event_contracts,
    validate_phase6_artifact,
    validate_phase6_event_contracts,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)


def _find_artifact(artifacts: list[dict], artifact_type: str) -> dict:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return artifact
    raise KeyError(artifact_type)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    contracts = phase6_artifact_contracts()
    event_contracts = phase6_event_contracts()
    event_contract_errors = validate_phase6_event_contracts(event_contracts)
    sample = build_phase6_sample_artifacts()
    summary = phase6_artifact_bundle_summary(sample)

    missing_provenance_probe = deepcopy(_find_artifact(sample, "postmortem_draft"))
    missing_provenance_probe.pop("provenance", None)
    missing_provenance_errors = validate_phase6_artifact(missing_provenance_probe)

    weak_boundary_probe = deepcopy(_find_artifact(sample, "closed_trade_outcome"))
    weak_boundary_probe["boundary"] = "ok"
    weak_boundary_errors = validate_phase6_artifact(weak_boundary_probe)

    local_path_probe = deepcopy(_find_artifact(sample, "learning_source_inventory"))
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_artifact(local_path_probe)

    source_posture_probe = deepcopy(_find_artifact(sample, "outcome_link"))
    source_posture_probe["source_posture"]["yahoo_finance_role"] = "canonical_source"
    source_posture_probe["source_posture"]["preference_mcp_source_36"] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase6_artifact(source_posture_probe)

    hidden_learning_write_probe = deepcopy(_find_artifact(sample, "knowledge_graph_staged_write"))
    hidden_learning_write_probe["phase6_learning_write_allowed"] = True
    hidden_learning_write_probe["authority_ledger"]["phase6_learning_write_allowed"] = True
    hidden_learning_write_probe["phase6_learning_write_allowed_count"] = 1
    hidden_learning_write_errors = validate_phase6_artifact(hidden_learning_write_probe)

    policy_mutation_probe = deepcopy(_find_artifact(sample, "architect_learning_summary"))
    policy_mutation_probe["phase6_policy_mutation_allowed"] = True
    policy_mutation_probe["authority_ledger"]["phase6_policy_mutation_allowed"] = True
    policy_mutation_probe["policy_mutation_allowed"] = True
    policy_mutation_probe["phase6_policy_mutation_allowed_count"] = 1
    policy_mutation_errors = validate_phase6_artifact(policy_mutation_probe)

    proof_credit_probe = deepcopy(_find_artifact(sample, "phase6_certification"))
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_artifact(proof_credit_probe)

    live_capital_probe = deepcopy(_find_artifact(sample, "phase6_certification"))
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase6_artifact(live_capital_probe)

    event_contract_probe = deepcopy(event_contracts)
    event_contract_probe.pop("postmortem_draft", None)
    missing_event_contract_errors = validate_phase6_event_contracts(event_contract_probe)

    missing_artifact_sample = [
        artifact
        for artifact in sample
        if artifact.get("artifact_type") != "phase6_certification"
    ]
    missing_artifact_summary = phase6_artifact_bundle_summary(missing_artifact_sample)

    print("phase6_artifact_schema_status=" + summary["status"])
    print(f"phase6_artifact_schema_version={PHASE6_ARTIFACT_SCHEMA_VERSION}")
    print(f"phase6_artifact_contract_count={len(contracts)}")
    print(f"phase6_artifact_type_count={len(PHASE6_ARTIFACT_TYPES)}")
    print(f"phase6_status_enum_count={len(PHASE6_STATUS_ENUMS)}")
    print(f"phase6_authority_field_count={len(PHASE6_AUTHORITY_FIELDS)}")
    print(f"phase6_unsafe_counter_field_count={len(PHASE6_UNSAFE_COUNT_FIELDS)}")
    print(f"phase6_event_contract_count={len(event_contracts)}")
    print(f"phase6_event_contract_error_count={len(event_contract_errors)}")
    print(f"phase6_sample_artifact_count={summary['artifact_count']}")
    print(f"phase6_sample_error_count={summary['error_count']}")
    print(f"phase6_sample_authority_enabled_count={summary['authority_enabled_count']}")
    print(f"phase6_sample_unsafe_counter_total={summary['unsafe_counter_total']}")
    print(f"phase6_sample_source_posture_status={summary['source_posture_status']}")
    print(f"phase6_sample_provenance_status={summary['provenance_status']}")
    print(f"phase6_sample_event_contract_status={summary['event_contract_status']}")
    print(f"phase6_readiness_status={readiness['status']}")
    print(f"phase6_readiness_re_entry_gate_passed={readiness['phase6_re_entry_gate_passed']}")
    print(
        "phase6_readiness_q6_1_artifact_schema_stage_allowed="
        f"{readiness['q6_1_artifact_schema_stage_allowed']}"
    )
    print(
        "phase6_readiness_phase6_implementation_allowed="
        f"{readiness['phase6_learning_loop_implementation_allowed']}"
    )
    print(f"phase6_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_missing_provenance_probe_error_count={len(missing_provenance_errors)}")
    print(f"phase6_weak_boundary_probe_error_count={len(weak_boundary_errors)}")
    print(f"phase6_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase6_source_posture_probe_error_count={len(source_posture_errors)}")
    print(
        "phase6_hidden_learning_write_probe_error_count="
        f"{len(hidden_learning_write_errors)}"
    )
    print(f"phase6_policy_mutation_probe_error_count={len(policy_mutation_errors)}")
    print(f"phase6_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase6_live_capital_probe_error_count={len(live_capital_errors)}")
    print(
        "phase6_missing_event_contract_probe_error_count="
        f"{len(missing_event_contract_errors)}"
    )
    print(f"phase6_missing_artifact_error_count={missing_artifact_summary['error_count']}")
    print("phase6_artifact_boundary=" + summary["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if readiness["phase6_re_entry_gate_passed"] is not True:
        errors.append("phase6_readiness_not_passed")
    if readiness["q6_1_artifact_schema_stage_allowed"] is not True:
        errors.append("q6_1_artifact_schema_not_allowed")
    if readiness["phase6_learning_loop_implementation_allowed"] is not False:
        errors.append("phase6_implementation_allowed_before_schema")
    if event_contract_errors:
        errors.extend(event_contract_errors)
    if summary["status"] != "ok":
        errors.append("sample_bundle_invalid")
    if summary["artifact_count"] != len(PHASE6_ARTIFACT_TYPES):
        errors.append("sample_artifact_count_mismatch")
    if len(contracts) != len(PHASE6_ARTIFACT_TYPES):
        errors.append("contract_count_mismatch")
    if summary["authority_enabled_count"] != 0:
        errors.append("sample_authority_enabled")
    if summary["unsafe_counter_total"] != 0:
        errors.append("sample_unsafe_counter_nonzero")
    if "provenance_missing_or_invalid" not in missing_provenance_errors:
        errors.append("missing_provenance_probe_not_rejected")
    if "boundary_weak_or_missing" not in weak_boundary_errors:
        errors.append("weak_boundary_probe_not_rejected")
    if "provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "yahoo_finance_role_invalid" not in source_posture_errors:
        errors.append("yahoo_source_posture_probe_not_rejected")
    if "preference_mcp_source_36" not in source_posture_errors:
        errors.append("preference_source36_probe_not_rejected")
    if "qctrl_role_invalid" not in source_posture_errors:
        errors.append("qctrl_source_posture_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in hidden_learning_write_errors:
        errors.append("hidden_learning_write_probe_not_rejected")
    if (
        "unsafe_counter_nonzero:phase6_learning_write_allowed_count"
        not in hidden_learning_write_errors
    ):
        errors.append("hidden_learning_write_counter_probe_not_rejected")
    if "architect_policy_mutation_allowed_in_q6_1" not in policy_mutation_errors:
        errors.append("policy_mutation_specific_probe_not_rejected")
    if "authority_enabled:phase6_policy_mutation_allowed" not in policy_mutation_errors:
        errors.append("policy_mutation_authority_probe_not_rejected")
    if "phase7_proof_credit_allowed_in_q6_1" not in proof_credit_errors:
        errors.append("proof_credit_specific_probe_not_rejected")
    if "authority_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_authority_probe_not_rejected")
    if "authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "unsafe_counter_nonzero:live_capital_enabled_count" not in live_capital_errors:
        errors.append("live_capital_counter_probe_not_rejected")
    if "event_contract_missing:postmortem_draft" not in missing_event_contract_errors:
        errors.append("missing_event_contract_probe_not_rejected")
    if "missing_artifact_type:phase6_certification" not in missing_artifact_summary["errors"]:
        errors.append("missing_artifact_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_artifact_schema_error={error}")
        print("phase6_artifact_schema_check=failed")
        return 1

    print("phase6_artifact_schema_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
