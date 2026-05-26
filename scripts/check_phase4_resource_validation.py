#!/usr/bin/env python3
"""Run and validate the Phase 4 Resource Registry validation report."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_resource_validation import (  # noqa: E402
    build_resource_validation,
    validate_resource_validation,
    write_resource_validation,
)


def main() -> int:
    errors: list[str] = []
    artifact = build_resource_validation()
    output_path = write_resource_validation(artifact)
    validation_errors = validate_resource_validation(artifact)

    rows = artifact["resource_rows"]
    active_rows = [row for row in rows if row["active_strategy_reference"]]
    rejected_rows = [row for row in rows if row["phase4_validation_status"] == "rejected_reference"]
    live_reference_rows = [row for row in rows if row["non_live_reference"] is not True]
    authority_flag_violations = [
        f"{row['resource_key']}:{flag}"
        for row in rows
        for flag, enabled in row["authority_flags"].items()
        if enabled is not False
    ]

    rejected_probe = deepcopy(artifact)
    rejected_probe["resource_rows"][0]["phase4_validation_status"] = "rejected_reference"
    rejected_probe["resource_rows"][0]["active_strategy_reference"] = True
    rejected_probe["resource_rows"][0]["strategy_provenance_allowed"] = True
    rejected_probe["active_strategy_reference_count"] = artifact["active_strategy_reference_count"] + 1
    rejected_probe_errors = validate_resource_validation(rejected_probe)

    private_probe = deepcopy(artifact)
    private_row = next(row for row in private_probe["resource_rows"] if row["private_world_model"])
    private_row["authority_flags"]["live_observation_authority"] = True
    private_probe_errors = validate_resource_validation(private_probe)

    active_missing_note_probe = deepcopy(artifact)
    active_missing_note_probe["resource_rows"][0]["active_strategy_reference"] = True
    active_missing_note_probe["resource_rows"][0]["decision_note_present"] = False
    active_missing_note_probe["active_strategy_reference_count"] = artifact["active_strategy_reference_count"] + 1
    active_missing_note_probe_errors = validate_resource_validation(active_missing_note_probe)

    yahoo_probe = deepcopy(artifact)
    yahoo_probe["capability_considerations"][0]["resource_registry_entry"] = True
    yahoo_probe["capability_considerations"][0]["canonical_rank_impact_allowed"] = True
    yahoo_probe_errors = validate_resource_validation(yahoo_probe)

    preference_rows = [row for row in rows if row["resource_key"] == "preference_mcp"]
    preference_row = preference_rows[0] if preference_rows else {}
    preference_capabilities = [
        item for item in artifact["capability_considerations"] if item.get("key") == "preference_mcp"
    ]
    preference_capability = preference_capabilities[0] if preference_capabilities else {}

    preference_active_probe = deepcopy(artifact)
    for row in preference_active_probe["resource_rows"]:
        if row["resource_key"] == "preference_mcp":
            row["active_strategy_reference"] = True
            row["strategy_provenance_allowed"] = True
            break
    preference_active_probe["active_strategy_reference_count"] = (
        artifact["active_strategy_reference_count"] + 1
    )
    preference_active_probe_errors = validate_resource_validation(preference_active_probe)

    preference_capability_probe = deepcopy(artifact)
    for item in preference_capability_probe["capability_considerations"]:
        if item.get("key") == "preference_mcp":
            item["canonical_rank_impact_allowed"] = True
            item["source_quorum_credit_allowed"] = True
            break
    preference_capability_probe_errors = validate_resource_validation(preference_capability_probe)

    print("phase4_resource_validation_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_resource_validation_schema_version={artifact['resource_validation_schema_version']}")
    print(f"phase4_resource_validation_artifact_path={output_path}")
    print(f"phase4_resource_count={artifact['resource_count']}")
    print(f"phase4_resource_validated_strategy_reference_count={artifact['validated_resource_count']}")
    print(f"phase4_resource_architecture_reference_count={artifact['architecture_reference_count']}")
    print(f"phase4_resource_provisional_reference_count={artifact['provisional_resource_count']}")
    print(f"phase4_resource_private_foundational_prior_count={artifact['private_foundational_prior_count']}")
    print(f"phase4_resource_rejected_reference_count={artifact['rejected_reference_count']}")
    print(f"phase4_resource_active_strategy_reference_count={artifact['active_strategy_reference_count']}")
    print(f"phase4_resource_live_reference_count={len(live_reference_rows)}")
    print(f"phase4_resource_authority_flag_violation_count={len(authority_flag_violations)}")
    print(f"phase4_resource_rejected_active_reference_count={len([row for row in rejected_rows if row['active_strategy_reference']])}")
    print(f"phase4_resource_validation_error_count={len(validation_errors)}")
    print(f"phase4_resource_rejected_probe_error_count={len(rejected_probe_errors)}")
    print(f"phase4_resource_private_probe_error_count={len(private_probe_errors)}")
    print(f"phase4_resource_active_missing_note_probe_error_count={len(active_missing_note_probe_errors)}")
    print(f"phase4_resource_yahoo_probe_error_count={len(yahoo_probe_errors)}")
    print(
        "phase4_resource_preference="
        f"present={bool(preference_row)},"
        f"category={preference_row.get('category')},"
        f"status={preference_row.get('phase4_validation_status')},"
        f"strategy_provenance_allowed={preference_row.get('strategy_provenance_allowed')}"
    )
    print(
        "phase4_resource_preference_capability="
        f"registry_entry={preference_capability.get('resource_registry_entry')},"
        f"canonical_rank_impact_allowed={preference_capability.get('canonical_rank_impact_allowed')},"
        f"source_quorum_credit_allowed={preference_capability.get('source_quorum_credit_allowed')}"
    )
    print(
        "phase4_resource_preference_active_probe_error_count="
        f"{len(preference_active_probe_errors)}"
    )
    print(
        "phase4_resource_preference_capability_probe_error_count="
        f"{len(preference_capability_probe_errors)}"
    )
    print(f"phase4_resource_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_resource_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_resource_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_resource_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_resource_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["resource_count"] != len(rows):
        errors.append("resource_count_mismatch")
    if active_rows:
        errors.append("unexpected_active_strategy_references")
    if live_reference_rows:
        errors.append("resource_registry_entries_treated_as_live")
    if authority_flag_violations:
        errors.append("resource_authority_flag_violations")
    if rejected_rows:
        errors.append("unexpected_rejected_resources")
    if not any(error.startswith("rejected_resource_active_strategy_provenance:") for error in rejected_probe_errors):
        errors.append("rejected_probe_not_rejected")
    if not any(error.startswith("private_world_model_live_authority:") for error in private_probe_errors):
        errors.append("private_probe_not_rejected")
    if not any(error.startswith("active_reference_missing_decision_note:") for error in active_missing_note_probe_errors):
        errors.append("active_missing_note_probe_not_rejected")
    if "yahoo_finance_marked_resource_registry_entry" not in yahoo_probe_errors:
        errors.append("yahoo_resource_registry_probe_not_rejected")
    if "yahoo_finance_canonical_rank_impact_allowed" not in yahoo_probe_errors:
        errors.append("yahoo_rank_probe_not_rejected")
    if not preference_row:
        errors.append("preference_resource_registry_entry_missing")
    elif preference_row.get("category") != "supplemental_data_plane":
        errors.append("preference_resource_category_invalid")
    elif preference_row.get("active_strategy_reference") is not False:
        errors.append("preference_resource_active_strategy_reference")
    elif preference_row.get("strategy_provenance_allowed") is not False:
        errors.append("preference_resource_strategy_provenance_allowed")
    if not preference_capability:
        errors.append("preference_capability_consideration_missing")
    elif (
        preference_capability.get("resource_registry_entry") is not True
        or preference_capability.get("canonical_rank_impact_allowed") is not False
        or preference_capability.get("source_quorum_credit_allowed") is not False
    ):
        errors.append("preference_capability_policy_invalid")
    if not any(
        error.startswith("active_strategy_reference_status_invalid:preference_mcp")
        for error in preference_active_probe_errors
    ):
        errors.append("preference_active_probe_not_rejected")
    if "preference_mcp_canonical_rank_impact_allowed" not in preference_capability_probe_errors:
        errors.append("preference_capability_rank_probe_not_rejected")
    if "preference_mcp_source_quorum_credit_allowed" not in preference_capability_probe_errors:
        errors.append("preference_capability_source_quorum_probe_not_rejected")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_resource_validation_error={error}")
        print("phase4_resource_validation_check=failed")
        return 1

    print("phase4_resource_validation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
