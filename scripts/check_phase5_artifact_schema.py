#!/usr/bin/env python3
"""Validate Q5-1 Layer B artifact schema and authority ledger contracts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_artifacts import (  # noqa: E402
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_ARTIFACT_TYPES,
    PHASE5_AUTHORITY_FIELDS,
    PHASE5_STATUS_ENUMS,
    build_phase5_sample_artifacts,
    phase5_artifact_bundle_summary,
    phase5_artifact_contracts,
    validate_phase5_artifact,
)
from orchestrator.phase5_readiness import (  # noqa: E402
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
)


def _find_artifact(artifacts: list[dict], artifact_type: str) -> dict:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return artifact
    raise KeyError(artifact_type)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    readiness = build_phase5_layer_b_readiness(settings=settings)
    readiness_errors = validate_phase5_layer_b_readiness(readiness)
    contracts = phase5_artifact_contracts()
    sample = build_phase5_sample_artifacts()
    summary = phase5_artifact_bundle_summary(sample)

    missing_provenance_probe = deepcopy(_find_artifact(sample, "approval_policy_decision"))
    missing_provenance_probe.pop("provenance", None)
    missing_provenance_errors = validate_phase5_artifact(missing_provenance_probe)

    missing_event_log_probe = deepcopy(_find_artifact(sample, "risk_sizing_review"))
    missing_event_log_probe.pop("event_log_required", None)
    missing_event_log_errors = validate_phase5_artifact(missing_event_log_probe)

    source_posture_probe = deepcopy(_find_artifact(sample, "execution_intent"))
    source_posture_probe["source_posture"]["yahoo_finance_role"] = "canonical_source"
    source_posture_probe["source_posture"]["preference_mcp_source_36"] = True
    source_posture_errors = validate_phase5_artifact(source_posture_probe)

    authority_probe = deepcopy(_find_artifact(sample, "layer_b_authority_ledger"))
    authority_probe["broker_write_allowed"] = True
    authority_probe["authority_ledger"]["broker_write_allowed"] = True
    authority_errors = validate_phase5_artifact(authority_probe)

    live_capital_probe = deepcopy(_find_artifact(sample, "phase5_certification"))
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_artifact(live_capital_probe)

    broker_receipt_probe = deepcopy(_find_artifact(sample, "broker_submit_receipt"))
    broker_receipt_probe["broker_post_called"] = True
    broker_receipt_errors = validate_phase5_artifact(broker_receipt_probe)

    staged_order_probe = deepcopy(_find_artifact(sample, "staged_paper_order"))
    staged_order_probe["staging_allowed"] = True
    staged_order_errors = validate_phase5_artifact(staged_order_probe)

    telegram_probe = deepcopy(_find_artifact(sample, "telegram_notification"))
    telegram_probe["telegram_command_path_enabled"] = True
    telegram_errors = validate_phase5_artifact(telegram_probe)

    missing_artifact_sample = [
        artifact
        for artifact in sample
        if artifact.get("artifact_type") != "phase5_certification"
    ]
    missing_artifact_summary = phase5_artifact_bundle_summary(missing_artifact_sample)

    print("phase5_artifact_schema_status=" + summary["status"])
    print(f"phase5_artifact_schema_version={PHASE5_ARTIFACT_SCHEMA_VERSION}")
    print(f"phase5_artifact_contract_count={len(contracts)}")
    print(f"phase5_artifact_type_count={len(PHASE5_ARTIFACT_TYPES)}")
    print(f"phase5_status_enum_count={len(PHASE5_STATUS_ENUMS)}")
    print(f"phase5_authority_field_count={len(PHASE5_AUTHORITY_FIELDS)}")
    print(f"phase5_sample_artifact_count={summary['artifact_count']}")
    print(f"phase5_sample_error_count={summary['error_count']}")
    print(f"phase5_sample_authority_enabled_count={summary['authority_enabled_count']}")
    print(f"phase5_sample_source_posture_status={summary['source_posture_status']}")
    print(f"phase5_sample_provenance_status={summary['provenance_status']}")
    print(f"phase5_readiness_status={readiness['status']}")
    print(
        "phase5_readiness_implementation_allowed="
        f"{readiness['phase5_layer_b_implementation_allowed']}"
    )
    print(
        "phase5_readiness_orchestration_start_allowed="
        f"{readiness['phase5_orchestration_start_allowed']}"
    )
    print(f"phase5_readiness_error_count={len(readiness_errors)}")
    print(f"phase5_missing_provenance_probe_error_count={len(missing_provenance_errors)}")
    print(f"phase5_missing_event_log_probe_error_count={len(missing_event_log_errors)}")
    print(f"phase5_source_posture_probe_error_count={len(source_posture_errors)}")
    print(f"phase5_authority_probe_error_count={len(authority_errors)}")
    print(f"phase5_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase5_broker_receipt_probe_error_count={len(broker_receipt_errors)}")
    print(f"phase5_staged_order_probe_error_count={len(staged_order_errors)}")
    print(f"phase5_telegram_probe_error_count={len(telegram_errors)}")
    print(f"phase5_missing_artifact_error_count={missing_artifact_summary['error_count']}")
    print("phase5_artifact_boundary=" + summary["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if readiness["phase5_layer_b_implementation_allowed"] is not True:
        errors.append("phase5_readiness_not_unlocked")
    if readiness["phase5_orchestration_start_allowed"] is not False:
        errors.append("phase5_orchestration_start_allowed")
    if summary["status"] != "ok":
        errors.append("sample_bundle_invalid")
    if summary["artifact_count"] != len(PHASE5_ARTIFACT_TYPES):
        errors.append("sample_artifact_count_mismatch")
    if len(contracts) != len(PHASE5_ARTIFACT_TYPES):
        errors.append("contract_count_mismatch")
    if summary["authority_enabled_count"] != 0:
        errors.append("sample_authority_enabled")
    if "provenance_missing_or_invalid" not in missing_provenance_errors:
        errors.append("missing_provenance_probe_not_rejected")
    if not any(
        error.startswith("missing_field:risk_sizing_review:event_log_required")
        for error in missing_event_log_errors
    ):
        errors.append("missing_event_log_probe_not_rejected")
    if "yahoo_finance_role_invalid" not in source_posture_errors:
        errors.append("yahoo_source_posture_probe_not_rejected")
    if "preference_mcp_source_36" not in source_posture_errors:
        errors.append("preference_source36_probe_not_rejected")
    if "authority_enabled:broker_write_allowed" not in authority_errors:
        errors.append("authority_probe_not_rejected")
    if "authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if "broker_post_called_in_q5_1" not in broker_receipt_errors:
        errors.append("broker_receipt_probe_not_rejected")
    if "staging_allowed_in_q5_1" not in staged_order_errors:
        errors.append("staged_order_probe_not_rejected")
    if "telegram_command_path_enabled" not in telegram_errors:
        errors.append("telegram_probe_not_rejected")
    if "missing_artifact_type:phase5_certification" not in missing_artifact_summary["errors"]:
        errors.append("missing_artifact_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_artifact_schema_error={error}")
        print("phase5_artifact_schema_check=failed")
        return 1

    print("phase5_artifact_schema_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
