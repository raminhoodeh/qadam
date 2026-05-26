#!/usr/bin/env python3
"""Run and validate the Phase 4 Data Veracity Audit."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_data_veracity import (  # noqa: E402
    build_data_veracity_audit,
    validate_data_veracity_audit,
    write_data_veracity_audit,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


def main() -> int:
    errors: list[str] = []
    artifact = build_data_veracity_audit()
    output_path = write_data_veracity_audit(artifact)
    validation_errors = validate_data_veracity_audit(artifact)

    authority_probe = deepcopy(artifact)
    authority_probe["canonical_sources"][0]["authority_flags"]["execution_authority"] = True
    authority_probe_errors = validate_data_veracity_audit(authority_probe)

    yahoo_probe = deepcopy(artifact)
    yahoo_probe["supplemental_sources"][0]["canonical_source"] = True
    yahoo_probe_errors = validate_data_veracity_audit(yahoo_probe)

    preference_rows = [
        row for row in artifact["supplemental_sources"] if row.get("source_key") == "preference_mcp"
    ]
    preference = preference_rows[0] if preference_rows else {}
    preference_policy = artifact.get("preference_mcp_policy", {})
    preference_probe = deepcopy(artifact)
    for row in preference_probe["supplemental_sources"]:
        if row.get("source_key") == "preference_mcp":
            row["canonical_source"] = True
            row["reason_codes"] = []
            break
    preference_probe_errors = validate_data_veracity_audit(preference_probe)

    source_fields = {
        "coverage_status",
        "freshness_status",
        "latency_status",
        "degradation_status",
        "corroboration_status",
        "evidence_basis",
        "routing_boundary",
    }
    source_field_complete_count = sum(
        1
        for row in artifact["canonical_sources"]
        if source_fields.issubset(set(row)) and row.get("evidence_basis") and row.get("routing_boundary")
    )
    supplemental_field_complete_count = sum(
        1
        for row in artifact["supplemental_sources"]
        if source_fields.issubset(set(row)) and row.get("evidence_basis") and row.get("routing_boundary")
    )
    canonical_separated = all(row.get("canonical_source") is True for row in artifact["canonical_sources"])
    supplemental_separated = all(row.get("canonical_source") is False for row in artifact["supplemental_sources"])
    yahoo = artifact["supplemental_sources"][0]

    print("phase4_data_veracity_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_data_veracity_schema_version={artifact['audit_schema_version']}")
    print(f"phase4_data_veracity_artifact_path={output_path}")
    print(f"phase4_data_veracity_canonical_source_count={artifact['canonical_source_count']}")
    print(f"phase4_data_veracity_expected_source_count={artifact['expected_canonical_source_count']}")
    print(f"phase4_data_veracity_supplemental_source_count={artifact['supplemental_source_count']}")
    print(f"phase4_data_veracity_quarantined_source_count={artifact['quarantined_source_count']}")
    print(f"phase4_data_veracity_authority_flag_violation_count={artifact['authority_flag_violation_count']}")
    print(f"phase4_data_veracity_source_field_complete_count={source_field_complete_count}")
    print(f"phase4_data_veracity_supplemental_field_complete_count={supplemental_field_complete_count}")
    print(f"phase4_data_veracity_canonical_separated={canonical_separated}")
    print(f"phase4_data_veracity_supplemental_separated={supplemental_separated}")
    print(
        "phase4_data_veracity_durable="
        f"{artifact['durable_replay']['status']},"
        f"{artifact['durable_replay']['contract_status']},"
        f"replayed={artifact['durable_replay']['replayed_source_count']},"
        f"missing={artifact['durable_replay']['missing_source_count']}"
    )
    print(
        "phase4_data_veracity_yahoo="
        f"{yahoo['coverage_status']},"
        f"{yahoo['corroboration_status']},"
        f"canonical={yahoo['canonical_source']}"
    )
    print(
        "phase4_data_veracity_preference="
        f"{preference.get('coverage_status')},"
        f"{preference.get('corroboration_status')},"
        f"canonical={preference.get('canonical_source')}"
    )
    print(
        "phase4_data_veracity_preference_source_promotion="
        f"status={preference_policy.get('source_promotion_status')},"
        f"decisions={preference_policy.get('source_promotion_decision_count')},"
        f"promoted={preference_policy.get('source_promotion_promoted_decision_count')},"
        f"source_count_after={preference_policy.get('source_promotion_canonical_source_count_after')}"
    )
    print(f"phase4_data_veracity_validation_error_count={len(validation_errors)}")
    print(f"phase4_data_veracity_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_data_veracity_yahoo_probe_error_count={len(yahoo_probe_errors)}")
    print(f"phase4_data_veracity_preference_probe_error_count={len(preference_probe_errors)}")
    print(f"phase4_data_veracity_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_data_veracity_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_data_veracity_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_data_veracity_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_data_veracity_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["canonical_source_count"] != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if not canonical_separated or not supplemental_separated:
        errors.append("source_classification_not_separated")
    if source_field_complete_count != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_fields_incomplete")
    if supplemental_field_complete_count != artifact["supplemental_source_count"]:
        errors.append("supplemental_source_fields_incomplete")
    if artifact["authority_flag_violation_count"] != 0:
        errors.append("authority_flag_violation_count_not_zero")
    if not any(error.startswith("source_authority_enabled:") for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if "yahoo_marked_canonical" not in yahoo_probe_errors:
        errors.append("yahoo_canonical_probe_not_rejected")
    if yahoo["corroboration_status"] != "supplemental_hold_single_source_not_allowed":
        errors.append("yahoo_single_source_hold_missing")
    if not preference:
        errors.append("preference_supplemental_row_missing")
    elif preference.get("canonical_source") is not False:
        errors.append("preference_marked_canonical")
    elif "canonical_rank_impact_disallowed" not in preference.get("reason_codes", []):
        errors.append("preference_canonical_rank_boundary_missing")
    if "preference_mcp_marked_canonical" not in preference_probe_errors:
        errors.append("preference_canonical_probe_not_rejected")
    if "preference_mcp_rank_boundary_missing" not in preference_probe_errors:
        errors.append("preference_rank_probe_not_rejected")
    if preference_policy.get("source_promotion_status") != "validated":
        errors.append("preference_source_promotion_status_not_validated")
    if preference_policy.get("source_promotion_decision_count") != 6:
        errors.append("preference_source_promotion_decision_count_mismatch")
    if preference_policy.get("source_promotion_promoted_decision_count") != 0:
        errors.append("preference_source_promotion_promoted")
    if preference_policy.get("source_promotion_canonical_source_count_after") != EXPECTED_SOURCE_COUNT:
        errors.append("preference_source_promotion_source_count_mismatch")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "fill_confirmation_authority",
        "receipt_evidence_authority",
        "reconciliation_truth_authority",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_data_veracity_error={error}")
        print("phase4_data_veracity_check=failed")
        return 1

    print("phase4_data_veracity_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
