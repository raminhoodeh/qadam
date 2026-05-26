#!/usr/bin/env python3
"""Validate Phase 4 Strategy Manifestation artifact schema contracts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_artifacts import (  # noqa: E402
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    PHASE4_ARTIFACT_TYPES,
    PHASE4_AUTHORITY_BOUNDARY_FIELDS,
    PHASE4_STATUS_ENUMS,
    build_phase4_sample_artifacts,
    phase4_artifact_bundle_summary,
    phase4_artifact_contracts,
    validate_phase4_artifact,
)


def _find_artifact(artifacts: list[dict], artifact_type: str) -> dict:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return artifact
    raise KeyError(artifact_type)


def main() -> int:
    errors: list[str] = []
    contracts = phase4_artifact_contracts()
    sample = build_phase4_sample_artifacts(include_approval_event=True)
    summary = phase4_artifact_bundle_summary(sample)
    missing_approval_sample = build_phase4_sample_artifacts(include_approval_event=False)
    missing_approval_summary = phase4_artifact_bundle_summary(missing_approval_sample)

    toggle_snapshot = _find_artifact(sample, "strategy_toggle_snapshot")
    approved_shadow_toggle = toggle_snapshot["toggles"][0]
    approved_shadow_authority_false = all(
        approved_shadow_toggle.get(field) is False
        for field in ("execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled")
    )

    authority_probe = deepcopy(toggle_snapshot)
    authority_probe["authority_boundary"]["execution_allowed"] = True
    authority_probe_errors = validate_phase4_artifact(authority_probe)

    toggle_probe = deepcopy(toggle_snapshot)
    toggle_probe["toggles"][0]["broker_write_allowed"] = True
    toggle_probe_errors = validate_phase4_artifact(toggle_probe)

    approved_sample = build_phase4_sample_artifacts(include_approval_event=True)
    strategy_metadata = _find_artifact(approved_sample, "manifested_strategy_metadata")
    strategy_metadata["status"] = "approved_shadow"
    strategy_metadata["document_fingerprint"] = "sample-strategy-fingerprint"
    approval = _find_artifact(approved_sample, "fund_manager_approval_event")
    approval["status"] = "approved_shadow"
    approval["approval_state"] = "approved"
    approval["approval_logged"] = True
    approval["approver_label"] = "fund_manager"
    approval["event_log_correlation_id"] = "sample-approval-event"
    approved_summary = phase4_artifact_bundle_summary(approved_sample)

    print("phase4_artifact_schema_status=" + ("ok" if not errors else "error"))
    print(f"phase4_artifact_schema_version={PHASE4_ARTIFACT_SCHEMA_VERSION}")
    print(f"phase4_artifact_type_count={len(PHASE4_ARTIFACT_TYPES)}")
    print(f"phase4_contract_count={len(contracts)}")
    print(f"phase4_status_enum_count={len(PHASE4_STATUS_ENUMS)}")
    print(f"phase4_authority_boundary_field_count={len(PHASE4_AUTHORITY_BOUNDARY_FIELDS)}")
    print(f"phase4_sample_artifact_count={summary['artifact_count']}")
    print(f"phase4_sample_bundle_status={summary['status']}")
    print(f"phase4_sample_bundle_error_count={summary['error_count']}")
    print(f"phase4_sample_approval_state={summary['approval_state']}")
    print(f"phase4_sample_approval_logged={summary['approval_logged']}")
    print(f"phase4_sample_strategy_document_ready={summary['strategy_document_ready']}")
    print(f"phase4_sample_certification_allowed={summary['phase4_certification_allowed']}")
    print(f"phase4_missing_approval_status={missing_approval_summary['status']}")
    print(f"phase4_missing_approval_certification_allowed={missing_approval_summary['phase4_certification_allowed']}")
    print(
        "phase4_missing_approval_errors="
        + ",".join(missing_approval_summary["errors"][:4])
    )
    print(f"phase4_approved_shadow_toggle_authority_false={approved_shadow_authority_false}")
    print(f"phase4_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_toggle_probe_error_count={len(toggle_probe_errors)}")
    print(f"phase4_logged_approval_strategy_document_ready={approved_summary['strategy_document_ready']}")
    print(f"phase4_logged_approval_certification_allowed={approved_summary['phase4_certification_allowed']}")
    print("phase4_artifact_boundary=" + summary["boundary"])

    if summary["status"] != "ok":
        errors.append("sample_bundle_invalid")
    if summary["phase4_certification_allowed"] is not False:
        errors.append("unapproved_sample_certification_allowed")
    if missing_approval_summary["phase4_certification_allowed"] is not False:
        errors.append("missing_approval_certification_allowed")
    if "missing_artifact_type:fund_manager_approval_event" not in missing_approval_summary["errors"]:
        errors.append("missing_approval_error_absent")
    if not approved_shadow_authority_false:
        errors.append("approved_shadow_toggle_has_authority")
    if not any(error == "authority_boundary_enabled:execution_allowed" for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if not any(error.endswith(":broker_write_allowed") for error in toggle_probe_errors):
        errors.append("toggle_probe_not_rejected")
    if approved_summary["phase4_certification_allowed"] is not True:
        errors.append("logged_approval_not_certification_ready")
    if len(contracts) != len(PHASE4_ARTIFACT_TYPES):
        errors.append("contract_count_mismatch")

    if errors:
        for error in errors:
            print(f"phase4_artifact_schema_error={error}")
        print("phase4_artifact_schema_check=failed")
        return 1

    print("phase4_artifact_schema_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
