#!/usr/bin/env python3
"""Validate Q7-1 Phase 7 Demo Proof artifact schema and authority ledger."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase7_artifacts import (  # noqa: E402
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_ARTIFACT_TYPES,
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_REQUIRED_EVENT_CATEGORIES,
    PHASE7_STATUS_ENUMS,
    PHASE7_UNSAFE_COUNT_FIELDS,
    build_phase7_sample_artifacts,
    phase7_artifact_bundle_summary,
    phase7_artifact_contracts,
    phase7_event_contracts,
    validate_phase7_artifact,
    validate_phase7_event_contracts,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    build_phase7_readiness,
    validate_phase7_readiness,
)


def _find_artifact(artifacts: list[dict], artifact_type: str) -> dict:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return artifact
    raise KeyError(artifact_type)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    contracts = phase7_artifact_contracts()
    event_contracts = phase7_event_contracts()
    event_contract_errors = validate_phase7_event_contracts(event_contracts)
    sample = build_phase7_sample_artifacts()
    summary = phase7_artifact_bundle_summary(sample)

    missing_provenance_probe = deepcopy(_find_artifact(sample, "proof_candidate"))
    missing_provenance_probe.pop("provenance", None)
    missing_provenance_errors = validate_phase7_artifact(missing_provenance_probe)

    weak_boundary_probe = deepcopy(_find_artifact(sample, "proof_week"))
    weak_boundary_probe["boundary"] = "ok"
    weak_boundary_errors = validate_phase7_artifact(weak_boundary_probe)

    local_path_probe = deepcopy(_find_artifact(sample, "source_signal_funnel_evidence"))
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private-proof.json"
    ]
    local_path_errors = validate_phase7_artifact(local_path_probe)

    source_posture_probe = deepcopy(_find_artifact(sample, "qualified_setup"))
    source_posture_probe["source_posture"]["yahoo_finance_role"] = "canonical_source"
    source_posture_probe["source_posture"]["preference_mcp_source_quorum_credit_allowed"] = (
        True
    )
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_probe["source_posture"]["private_world_model_role"] = "proof"
    source_posture_errors = validate_phase7_artifact(source_posture_probe)

    stale_90_day_probe = deepcopy(_find_artifact(sample, "proof_calendar_day"))
    stale_90_day_probe["proof_contract"]["harness_day_count"] = 90
    stale_90_day_errors = validate_phase7_artifact(stale_90_day_probe)

    stale_two_trade_probe = deepcopy(_find_artifact(sample, "proof_week"))
    stale_two_trade_probe["weekly_target"] = 2
    stale_two_trade_probe["proof_contract"]["weekly_proof_trade_target"] = 2
    stale_two_trade_errors = validate_phase7_artifact(stale_two_trade_probe)

    forced_trade_probe = deepcopy(_find_artifact(sample, "proof_week"))
    forced_trade_probe["forced_trade_allowed"] = True
    forced_trade_probe["proof_contract"]["no_forced_trades"] = False
    forced_trade_errors = validate_phase7_artifact(forced_trade_probe)

    proof_credit_probe = deepcopy(_find_artifact(sample, "phase7_certification"))
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_artifact(proof_credit_probe)

    phase5_reuse_probe = deepcopy(_find_artifact(sample, "proof_candidate"))
    phase5_reuse_probe["phase5_reuse_allowed"] = True
    phase5_reuse_probe["proof_contract"]["phase5_test_trade_reuse_allowed"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_artifact(phase5_reuse_probe)

    live_capital_probe = deepcopy(_find_artifact(sample, "phase7_certification"))
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_artifact(live_capital_probe)

    broker_post_probe = deepcopy(_find_artifact(sample, "proof_broker_receipt"))
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_artifact(broker_post_probe)

    manual_override_probe = deepcopy(_find_artifact(sample, "override_detection"))
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_probe["override_count"] = 1
    manual_override_errors = validate_phase7_artifact(manual_override_probe)

    ui_readiness_probe = deepcopy(_find_artifact(sample, "cockpit_proof_visibility"))
    ui_readiness_probe["backend_derived"] = False
    ui_readiness_probe["ui_inferred_readiness_count"] = 1
    ui_readiness_errors = validate_phase7_artifact(ui_readiness_probe)

    broker_identifier_probe = deepcopy(_find_artifact(sample, "proof_broker_receipt"))
    broker_identifier_probe["provenance"]["source_refs"] = [
        "data/runtime/broker_order_id-secret.json"
    ]
    broker_identifier_errors = validate_phase7_artifact(broker_identifier_probe)

    event_contract_probe = deepcopy(event_contracts)
    event_contract_probe.pop("broker_receipt", None)
    missing_event_contract_errors = validate_phase7_event_contracts(event_contract_probe)

    missing_artifact_sample = [
        artifact
        for artifact in sample
        if artifact.get("artifact_type") != "phase7_certification"
    ]
    missing_artifact_summary = phase7_artifact_bundle_summary(missing_artifact_sample)

    print("phase7_artifact_schema_status=" + summary["status"])
    print(f"phase7_artifact_schema_version={PHASE7_ARTIFACT_SCHEMA_VERSION}")
    print(f"phase7_artifact_contract_count={len(contracts)}")
    print(f"phase7_artifact_type_count={len(PHASE7_ARTIFACT_TYPES)}")
    print(f"phase7_status_enum_count={len(PHASE7_STATUS_ENUMS)}")
    print(f"phase7_authority_field_count={len(PHASE7_AUTHORITY_FLAGS)}")
    print(f"phase7_unsafe_counter_field_count={len(PHASE7_UNSAFE_COUNT_FIELDS)}")
    print(f"phase7_event_contract_count={len(event_contracts)}")
    print(f"phase7_required_event_category_count={len(PHASE7_REQUIRED_EVENT_CATEGORIES)}")
    print(f"phase7_event_contract_error_count={len(event_contract_errors)}")
    print(f"phase7_sample_artifact_count={summary['artifact_count']}")
    print(f"phase7_sample_error_count={summary['error_count']}")
    print(f"phase7_sample_authority_enabled_count={summary['authority_enabled_count']}")
    print(f"phase7_sample_unsafe_counter_total={summary['unsafe_counter_total']}")
    print(f"phase7_sample_proof_contract_status={summary['proof_contract_status']}")
    print(f"phase7_sample_source_posture_status={summary['source_posture_status']}")
    print(f"phase7_sample_provenance_status={summary['provenance_status']}")
    print(f"phase7_sample_event_contract_status={summary['event_contract_status']}")
    print(f"phase7_readiness_status={readiness['status']}")
    print(f"phase7_readiness_re_entry_gate_passed={readiness['phase7_re_entry_gate_passed']}")
    print(
        "phase7_readiness_q7_1_artifact_schema_stage_allowed="
        f"{readiness['q7_1_artifact_schema_stage_allowed']}"
    )
    print(
        "phase7_readiness_phase7_demo_proof_implementation_allowed="
        f"{readiness['phase7_demo_proof_implementation_allowed']}"
    )
    print(f"phase7_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_harness_day_count={PHASE7_HARNESS_DAY_COUNT}")
    print(f"phase7_weekly_proof_trade_target={PHASE7_WEEKLY_PROOF_TRADE_TARGET}")
    print(f"phase7_mature_closed_trade_benchmark={PHASE7_MATURE_CLOSED_TRADE_BENCHMARK}")
    print(
        "phase7_missing_provenance_probe_error_count="
        f"{len(missing_provenance_errors)}"
    )
    print(f"phase7_weak_boundary_probe_error_count={len(weak_boundary_errors)}")
    print(f"phase7_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_source_posture_probe_error_count={len(source_posture_errors)}")
    print(f"phase7_stale_90_day_probe_error_count={len(stale_90_day_errors)}")
    print(f"phase7_stale_two_trade_probe_error_count={len(stale_two_trade_errors)}")
    print(f"phase7_forced_trade_probe_error_count={len(forced_trade_errors)}")
    print(f"phase7_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(f"phase7_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_broker_post_probe_error_count={len(broker_post_errors)}")
    print(f"phase7_manual_override_probe_error_count={len(manual_override_errors)}")
    print(f"phase7_ui_readiness_probe_error_count={len(ui_readiness_errors)}")
    print(
        "phase7_broker_identifier_probe_error_count="
        f"{len(broker_identifier_errors)}"
    )
    print(
        "phase7_missing_event_contract_probe_error_count="
        f"{len(missing_event_contract_errors)}"
    )
    print(f"phase7_missing_artifact_error_count={missing_artifact_summary['error_count']}")
    print("phase7_artifact_boundary=" + summary["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if readiness["phase7_re_entry_gate_passed"] is not True:
        errors.append("phase7_readiness_not_passed")
    if readiness["q7_1_artifact_schema_stage_allowed"] is not True:
        errors.append("q7_1_artifact_schema_not_allowed")
    if readiness["phase7_demo_proof_implementation_allowed"] is not False:
        errors.append("phase7_implementation_allowed_before_schema")
    if event_contract_errors:
        errors.extend(event_contract_errors)
    if summary["status"] != "ok":
        errors.append("sample_bundle_invalid")
    if summary["artifact_count"] != len(PHASE7_ARTIFACT_TYPES):
        errors.append("sample_artifact_count_mismatch")
    if len(contracts) != len(PHASE7_ARTIFACT_TYPES):
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
    if "preference_mcp_source_quorum_credit_allowed" not in source_posture_errors:
        errors.append("preference_quorum_credit_probe_not_rejected")
    if "qctrl_role_invalid" not in source_posture_errors:
        errors.append("qctrl_source_posture_probe_not_rejected")
    if "private_world_model_role_invalid" not in source_posture_errors:
        errors.append("private_world_model_posture_probe_not_rejected")
    if "proof_contract_mismatch:harness_day_count" not in stale_90_day_errors:
        errors.append("stale_90_day_probe_not_rejected")
    if "proof_contract_mismatch:weekly_proof_trade_target" not in stale_two_trade_errors:
        errors.append("stale_two_trade_contract_probe_not_rejected")
    if "proof_week_target_not_three" not in stale_two_trade_errors:
        errors.append("stale_two_trade_specific_probe_not_rejected")
    if "proof_contract_missing_true:no_forced_trades" not in forced_trade_errors:
        errors.append("forced_trade_contract_probe_not_rejected")
    if "forced_trade_allowed_in_q7_1" not in forced_trade_errors:
        errors.append("forced_trade_specific_probe_not_rejected")
    if "authority_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_authority_probe_not_rejected")
    if "unsafe_counter_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_counter_probe_not_rejected")
    if "proof_contract_forbidden:phase5_test_trade_reuse_allowed" not in (
        phase5_reuse_errors
    ):
        errors.append("phase5_reuse_contract_probe_not_rejected")
    if "phase5_reuse_allowed_in_q7_1" not in phase5_reuse_errors:
        errors.append("phase5_reuse_specific_probe_not_rejected")
    if "unsafe_counter_nonzero:phase5_test_trade_reuse_count" not in (
        phase5_reuse_errors
    ):
        errors.append("phase5_reuse_counter_probe_not_rejected")
    if "authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "live_capital_enabled_in_q7_1" not in live_capital_errors:
        errors.append("live_capital_specific_probe_not_rejected")
    if "unsafe_counter_nonzero:live_capital_enabled_count" not in live_capital_errors:
        errors.append("live_capital_counter_probe_not_rejected")
    if "authority_enabled:broker_post_allowed" not in broker_post_errors:
        errors.append("broker_post_authority_probe_not_rejected")
    if "broker_post_allowed_in_q7_1" not in broker_post_errors:
        errors.append("broker_post_specific_probe_not_rejected")
    if "unsafe_counter_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker_post_counter_probe_not_rejected")
    if "authority_enabled:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "manual_override_allowed_in_q7_1" not in manual_override_errors:
        errors.append("manual_override_specific_probe_not_rejected")
    if "unsafe_counter_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_counter_probe_not_rejected")
    if "override_count_nonzero_in_q7_1" not in manual_override_errors:
        errors.append("manual_override_count_specific_probe_not_rejected")
    if "cockpit_proof_visibility_not_backend_derived" not in ui_readiness_errors:
        errors.append("ui_backend_probe_not_rejected")
    if "cockpit_proof_ui_inferred_readiness" not in ui_readiness_errors:
        errors.append("ui_inferred_probe_not_rejected")
    if "provenance_secret_ref_leak" not in broker_identifier_errors:
        errors.append("broker_secret_ref_probe_not_rejected")
    if "provenance_broker_identifier_leak" not in broker_identifier_errors:
        errors.append("broker_identifier_probe_not_rejected")
    if "event_contract_missing:broker_receipt" not in missing_event_contract_errors:
        errors.append("missing_event_contract_probe_not_rejected")
    if "missing_artifact_type:phase7_certification" not in (
        missing_artifact_summary["errors"]
    ):
        errors.append("missing_artifact_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_artifact_schema_error={error}")
        print("phase7_artifact_schema_check=failed")
        return 1

    print("phase7_artifact_schema_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
