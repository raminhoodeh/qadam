#!/usr/bin/env python3
"""Validate the Q4-12 Phase 4 certification gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase4_approval_record import (  # noqa: E402
    attach_fund_manager_approval_event_log,
    build_fund_manager_approval_event,
)
from orchestrator.phase4_certification import (  # noqa: E402
    CERTIFICATION_EVENT_LOG,
    CERTIFICATION_EVENT_TYPE,
    PHASE4_CERTIFICATION_SCHEMA_VERSION,
    build_phase4_certification,
    validate_phase4_certification,
    write_phase4_certification,
)
from orchestrator.phase4_strategy_toggles import (  # noqa: E402
    attach_strategy_toggle_event_log,
    build_strategy_toggle_snapshot,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    event_log_path = runtime_dir / CERTIFICATION_EVENT_LOG
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_phase4_certification(settings=settings)
    output_path, written_artifact = write_phase4_certification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase4_certification(written_artifact)
    event_replay = EventLog(event_log_path, echo=False).replay()
    latest_event = event_replay["last_by_component"].get("phase4_certification", {})

    approved_event = build_fund_manager_approval_event(
        approval_state="approved",
        approver_label="fund_manager_ramin",
        settings=settings,
    )
    approved_event, _ = attach_fund_manager_approval_event_log(
        approved_event,
        event_log_path=runtime_dir / "phase4_certification_approval_probe.jsonl",
        settings=settings,
    )
    approved_toggle = build_strategy_toggle_snapshot(
        settings=settings,
        approval_event=approved_event,
    )
    approved_toggle, _ = attach_strategy_toggle_event_log(
        approved_toggle,
        event_log_path=runtime_dir / "phase4_certification_toggle_probe.jsonl",
        settings=settings,
    )
    approved_probe = build_phase4_certification(
        settings=settings,
        approval_event=approved_event,
        strategy_toggle_snapshot=approved_toggle,
    )
    approved_probe_errors = validate_phase4_certification(approved_probe)

    dishonest_probe = deepcopy(written_artifact)
    dishonest_probe["phase4_certified"] = True
    dishonest_probe["phase4_complete"] = True
    dishonest_probe["phase4_certification_allowed"] = True
    dishonest_probe["phase5_handoff_allowed"] = True
    dishonest_probe["status"] = "certified"
    dishonest_probe["approval_state"] = "amendments_required"
    dishonest_probe["approval_logged"] = False
    dishonest_probe_errors = validate_phase4_certification(dishonest_probe)

    authority_probe = deepcopy(written_artifact)
    authority_probe["broker_write_allowed"] = True
    authority_probe_errors = validate_phase4_certification(authority_probe)

    missing_toggle_log_probe = deepcopy(written_artifact)
    missing_toggle_log_probe["strategy_toggle_event_log_written"] = False
    missing_toggle_log_errors = validate_phase4_certification(missing_toggle_log_probe)

    preference_gate = written_artifact["preference_mcp_certification_gate"]

    preference_identity_probe = deepcopy(written_artifact)
    preference_identity_probe["preference_mcp_certification_gate"]["preference_enabled"] = True
    preference_identity_probe["preference_mcp_certification_gate"]["identity_status"] = "anonymous"
    preference_identity_probe["preference_mcp_certification_gate"]["identity_gate_status"] = "blocked"
    preference_identity_probe["preference_mcp_certification_gate"]["identity_blocker_active"] = True
    preference_identity_errors = validate_phase4_certification(preference_identity_probe)

    preference_provenance_probe = deepcopy(written_artifact)
    preference_provenance_probe["preference_mcp_certification_gate"]["provenance_status"] = "blocked"
    preference_provenance_probe["preference_mcp_certification_gate"]["provenance_validation_error_count"] = 1
    preference_provenance_errors = validate_phase4_certification(preference_provenance_probe)

    preference_domain_probe = deepcopy(written_artifact)
    preference_domain_probe["preference_mcp_certification_gate"]["approved_domain_pack_count"] = 0
    preference_domain_probe["preference_mcp_certification_gate"][
        "candidate_family_with_domain_pack_count"
    ] = 0
    preference_domain_errors = validate_phase4_certification(preference_domain_probe)

    preference_paid_tool_probe = deepcopy(written_artifact)
    preference_paid_tool_probe["preference_mcp_certification_gate"]["paid_tools_allowed"] = True
    preference_paid_tool_probe["preference_mcp_certification_gate"][
        "paid_tool_explicit_approval_present"
    ] = False
    preference_paid_tool_errors = validate_phase4_certification(preference_paid_tool_probe)

    preference_source_quorum_probe = deepcopy(written_artifact)
    preference_source_quorum_probe["preference_mcp_certification_gate"][
        "source_quorum_credit_allowed"
    ] = True
    preference_source_quorum_errors = validate_phase4_certification(preference_source_quorum_probe)

    preference_source_promotion_probe = deepcopy(written_artifact)
    preference_source_promotion_probe["preference_mcp_certification_gate"][
        "source_promotion_promoted_decision_count"
    ] = 1
    preference_source_promotion_errors = validate_phase4_certification(
        preference_source_promotion_probe
    )

    print("phase4_certification_status=" + written_artifact["status"])
    print(f"phase4_certification_schema_version={PHASE4_CERTIFICATION_SCHEMA_VERSION}")
    print(f"phase4_certification_artifact_path={output_path}")
    print(f"phase4_certification_event_log_path={event_log_path}")
    print(f"phase4_certification_event_type={latest_event.get('event_type')}")
    print(f"phase4_certification_event_log_total_events={event_replay['total_events']}")
    print(f"phase4_certification_logged={written_artifact['certification_logged']}")
    print(f"phase4_certification_phase={written_artifact['phase']}")
    print(f"phase4_certification_stage={written_artifact['stage']}")
    print(f"phase4_certification_stage_status={written_artifact['stage_status']}")
    print(f"phase4_certification_phase4_certified={written_artifact['phase4_certified']}")
    print(f"phase4_certification_phase4_complete={written_artifact['phase4_complete']}")
    print(f"phase4_certification_exit_gate={written_artifact['phase4_exit_gate']}")
    print(f"phase4_certification_phase5_handoff_allowed={written_artifact['phase5_handoff_allowed']}")
    print(f"phase4_certification_approval_state={written_artifact['approval_state']}")
    print(f"phase4_certification_approval_logged={written_artifact['approval_logged']}")
    print(
        "phase4_certification_required_amendment_count="
        f"{written_artifact['approval_required_amendment_count']}"
    )
    print(f"phase4_certification_blocker_count={written_artifact['certification_blocker_count']}")
    print(
        "phase4_certification_blockers="
        + ",".join(written_artifact["certification_blockers"])
    )
    print(
        "phase4_certification_artifact_validation_error_count="
        f"{written_artifact['artifact_validation_summary']['artifact_validation_error_count']}"
    )
    print(
        "phase4_certification_bundle_error_count="
        f"{written_artifact['artifact_bundle_summary']['error_count']}"
    )
    print(
        "phase4_certification_validated_artifact_count="
        f"{written_artifact['artifact_validation_summary']['validated_artifact_count']}"
    )
    print(
        "phase4_certification_strategy_explicitness_complete="
        f"{written_artifact['strategy_explicitness']['complete']}"
    )
    print(
        "phase4_certification_active_instrument_count="
        f"{written_artifact['strategy_explicitness']['active_instrument_count']}"
    )
    print(
        "phase4_certification_catalyst_class_count="
        f"{written_artifact['strategy_explicitness']['catalyst_class_count']}"
    )
    print(
        "phase4_certification_source_weight_count="
        f"{written_artifact['strategy_explicitness']['source_weight_count']}"
    )
    print(
        "phase4_certification_model_weight_count="
        f"{written_artifact['strategy_explicitness']['model_weight_count']}"
    )
    print(
        "phase4_certification_quantum_role_count="
        f"{written_artifact['strategy_explicitness']['quantum_role_count']}"
    )
    print(
        "phase4_certification_risk_assumption_count="
        f"{written_artifact['strategy_explicitness']['risk_assumption_count']}"
    )
    print(
        "phase4_certification_world_model_complete="
        f"{written_artifact['world_model_validation_status']['complete']}"
    )
    print(
        "phase4_certification_world_model_claim_count="
        f"{written_artifact['world_model_validation_status']['claim_count']}"
    )
    print(
        "phase4_certification_phase3_zero_authority_status="
        f"{written_artifact['phase3_zero_authority']['status']}"
    )
    print(
        "phase4_certification_phase3_zero_authority_violation_count="
        f"{written_artifact['phase3_zero_authority']['violation_count']}"
    )
    print(
        "phase4_certification_preference_gate_status="
        f"{preference_gate['status']}"
    )
    print(
        "phase4_certification_preference_enabled="
        f"{preference_gate['preference_enabled']}"
    )
    print(
        "phase4_certification_preference_identity_status="
        f"{preference_gate['identity_status']}"
    )
    print(
        "phase4_certification_preference_identity_blocker_active="
        f"{preference_gate['identity_blocker_active']}"
    )
    print(
        "phase4_certification_preference_provenance_status="
        f"{preference_gate['provenance_status']}"
    )
    print(
        "phase4_certification_preference_domain_pack_count="
        f"{preference_gate['approved_domain_pack_count']}"
    )
    print(
        "phase4_certification_preference_family_domain_pack_count="
        f"{preference_gate['candidate_family_with_domain_pack_count']}"
    )
    print(
        "phase4_certification_preference_source_promotion_status="
        f"{preference_gate['source_promotion_status']}"
    )
    print(
        "phase4_certification_preference_source_promotion_decision_count="
        f"{preference_gate['source_promotion_decision_count']}"
    )
    print(
        "phase4_certification_preference_source_promotion_promoted_count="
        f"{preference_gate['source_promotion_promoted_decision_count']}"
    )
    print(
        "phase4_certification_preference_source_promotion_source_count_after="
        f"{preference_gate['source_promotion_canonical_source_count_after']}"
    )
    print(
        "phase4_certification_preference_source_promotion_source36="
        f"{preference_gate['preference_mcp_source_36']}"
    )
    print(
        "phase4_certification_preference_source_quorum_credit_allowed="
        f"{preference_gate['source_quorum_credit_allowed']}"
    )
    print(
        "phase4_certification_preference_paid_tools_allowed="
        f"{preference_gate['paid_tools_allowed']}"
    )
    print(
        "phase4_certification_preference_blocker_count="
        f"{preference_gate['certification_blocker_count']}"
    )
    print(f"phase4_certification_strategy_toggle_count={written_artifact['strategy_toggle_count']}")
    print(
        "phase4_certification_strategy_toggle_event_log_written="
        f"{written_artifact['strategy_toggle_event_log_written']}"
    )
    print(
        "phase4_certification_draft_strategy_toggle_count="
        f"{written_artifact['draft_strategy_toggle_count']}"
    )
    print(
        "phase4_certification_approved_shadow_strategy_toggle_count="
        f"{written_artifact['approved_shadow_strategy_toggle_count']}"
    )
    print(f"phase4_certification_trade_candidate_count={written_artifact['trade_candidate_count']}")
    print(f"phase4_certification_execution_allowed_count={written_artifact['execution_allowed_count']}")
    print(f"phase4_certification_paper_order_allowed_count={written_artifact['paper_order_allowed_count']}")
    print(f"phase4_certification_broker_write_allowed_count={written_artifact['broker_write_allowed_count']}")
    print(f"phase4_certification_live_capital_enabled_count={written_artifact['live_capital_enabled_count']}")
    print(f"phase4_certification_provider_call_allowed_count={written_artifact['provider_call_allowed_count']}")
    print(
        "phase4_certification_hardware_submission_allowed_count="
        f"{written_artifact['hardware_submission_allowed_count']}"
    )
    print(f"phase4_certification_scheduler_enabled_count={written_artifact['scheduler_enabled_count']}")
    print(f"phase4_certification_authority_violation_count={written_artifact['authority_violation_count']}")
    print(f"phase4_certification_validation_error_count={len(validation_errors)}")
    print(f"phase4_certification_approved_probe_certified={approved_probe['phase4_certified']}")
    print(
        "phase4_certification_approved_probe_phase5_handoff_allowed="
        f"{approved_probe['phase5_handoff_allowed']}"
    )
    print(
        "phase4_certification_approved_probe_approved_shadow_count="
        f"{approved_probe['approved_shadow_strategy_toggle_count']}"
    )
    print(
        "phase4_certification_approved_probe_error_count="
        f"{len(approved_probe_errors)}"
    )
    print(
        "phase4_certification_dishonest_probe_error_count="
        f"{len(dishonest_probe_errors)}"
    )
    print(
        "phase4_certification_authority_probe_error_count="
        f"{len(authority_probe_errors)}"
    )
    print(
        "phase4_certification_missing_toggle_log_probe_error_count="
        f"{len(missing_toggle_log_errors)}"
    )
    print(
        "phase4_certification_preference_identity_probe_error_count="
        f"{len(preference_identity_errors)}"
    )
    print(
        "phase4_certification_preference_provenance_probe_error_count="
        f"{len(preference_provenance_errors)}"
    )
    print(
        "phase4_certification_preference_domain_probe_error_count="
        f"{len(preference_domain_errors)}"
    )
    print(
        "phase4_certification_preference_paid_tool_probe_error_count="
        f"{len(preference_paid_tool_errors)}"
    )
    print(
        "phase4_certification_preference_source_quorum_probe_error_count="
        f"{len(preference_source_quorum_errors)}"
    )
    print(
        "phase4_certification_preference_source_promotion_probe_error_count="
        f"{len(preference_source_promotion_errors)}"
    )
    print(f"phase4_certification_boundary={written_artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if written_artifact["approval_logged"] is not True:
        errors.append("approval_event_not_logged")
    if written_artifact["approval_state"] == "approved":
        if written_artifact["status"] != "certified":
            errors.append("certification_status_not_certified")
        if written_artifact["phase4_certified"] is not True:
            errors.append("phase4_not_certified")
        if written_artifact["phase4_complete"] is not True:
            errors.append("phase4_not_complete")
        if written_artifact["phase5_handoff_allowed"] is not True:
            errors.append("phase5_handoff_not_allowed")
        if written_artifact["certification_blockers"]:
            errors.append("certified_with_blockers")
    elif written_artifact["approval_state"] == "amendments_required":
        if written_artifact["status"] != "blocked":
            errors.append("certification_status_not_blocked")
        if written_artifact["phase4_certified"] is not False:
            errors.append("phase4_certified_unexpectedly_true")
        if written_artifact["phase4_complete"] is not False:
            errors.append("phase4_complete_unexpectedly_true")
        if written_artifact["phase5_handoff_allowed"] is not False:
            errors.append("phase5_handoff_allowed")
        if "explicit_fund_manager_approval_required" not in written_artifact["certification_blockers"]:
            errors.append("missing_explicit_approval_blocker")
    else:
        errors.append("approval_state_not_supported_for_certification_gate")
    if written_artifact["artifact_validation_summary"]["artifact_validation_error_count"] != 0:
        errors.append("artifact_validation_errors_present")
    if written_artifact["artifact_bundle_summary"]["error_count"] != 0:
        errors.append("artifact_bundle_errors_present")
    if written_artifact["strategy_explicitness"]["complete"] is not True:
        errors.append("strategy_explicitness_incomplete")
    if written_artifact["world_model_validation_status"]["complete"] is not True:
        errors.append("world_model_validation_incomplete")
    if written_artifact["phase3_zero_authority"]["violation_count"] != 0:
        errors.append("phase3_zero_authority_violation")
    if preference_gate["status"] != "validated":
        errors.append("preference_gate_not_validated")
    if preference_gate["preference_enabled"] is not False:
        errors.append("preference_gate_unexpectedly_enabled")
    if preference_gate["identity_blocker_active"] is not False:
        errors.append("preference_identity_blocker_active")
    if preference_gate["provenance_status"] != "validated":
        errors.append("preference_provenance_not_validated")
    if preference_gate["approved_domain_pack_count"] != 6:
        errors.append("preference_domain_pack_count_mismatch")
    if (
        preference_gate["candidate_family_with_domain_pack_count"]
        != preference_gate["strategy_family_candidate_count"]
    ):
        errors.append("preference_domain_pack_family_coverage_incomplete")
    if preference_gate["source_promotion_status"] != "validated":
        errors.append("preference_source_promotion_not_validated")
    if preference_gate["source_promotion_decision_count"] != 6:
        errors.append("preference_source_promotion_decision_count_mismatch")
    if preference_gate["source_promotion_promoted_decision_count"] != 0:
        errors.append("preference_source_promotion_promoted_count_nonzero")
    if preference_gate["source_promotion_canonical_source_count_after"] != 35:
        errors.append("preference_source_promotion_source_count_mismatch")
    if preference_gate["preference_mcp_source_36"] is not False:
        errors.append("preference_source36_enabled")
    if preference_gate["source_quorum_credit_allowed"] is not False:
        errors.append("preference_source_quorum_enabled")
    if preference_gate["paid_tools_allowed"] is not False:
        errors.append("preference_paid_tools_enabled")
    if preference_gate["certification_blocker_count"] != 0:
        errors.append("preference_certification_blockers_present")
    if written_artifact["strategy_toggle_event_log_written"] is not True:
        errors.append("strategy_toggle_event_log_missing")
    if written_artifact["approval_state"] == "approved":
        if written_artifact["draft_strategy_toggle_count"] != 0:
            errors.append("approved_draft_strategy_toggle_count_mismatch")
        if written_artifact["approved_shadow_strategy_toggle_count"] != 5:
            errors.append("approved_shadow_strategy_toggle_count_mismatch")
    else:
        if written_artifact["draft_strategy_toggle_count"] != 5:
            errors.append("draft_strategy_toggle_count_mismatch")
        if written_artifact["approved_shadow_strategy_toggle_count"] != 0:
            errors.append("approved_shadow_toggles_enabled")
    if event_replay["total_events"] != 1:
        errors.append("event_log_event_count_mismatch")
    if latest_event.get("event_type") != CERTIFICATION_EVENT_TYPE:
        errors.append("event_log_event_type_mismatch")
    if approved_probe_errors:
        errors.append("approved_probe_invalid")
    if approved_probe["phase4_certified"] is not True:
        errors.append("approved_probe_not_certified")
    if approved_probe["phase5_handoff_allowed"] is not True:
        errors.append("approved_probe_phase5_handoff_not_allowed")
    if approved_probe["approved_shadow_strategy_toggle_count"] != 5:
        errors.append("approved_probe_toggle_count_mismatch")
    if approved_probe["preference_mcp_certification_gate"]["status"] != "validated":
        errors.append("approved_probe_preference_gate_not_validated")
    if approved_probe["preference_mcp_certification_gate"]["certification_blocker_count"] != 0:
        errors.append("approved_probe_preference_blockers_present")
    if (
        approved_probe["preference_mcp_certification_gate"][
            "source_promotion_promoted_decision_count"
        ]
        != 0
    ):
        errors.append("approved_probe_preference_source_promotion_promoted")
    if "certified_without_approved_logged_approval" not in dishonest_probe_errors:
        errors.append("dishonest_probe_not_rejected")
    if "authority_flag_enabled:broker_write_allowed" not in authority_probe_errors:
        errors.append("authority_probe_not_rejected")
    if "strategy_toggle_event_log_not_written" not in missing_toggle_log_errors:
        errors.append("missing_toggle_log_probe_not_rejected")
    if "preference_enabled_identity_not_verified" not in preference_identity_errors:
        errors.append("preference_identity_probe_not_rejected")
    if "preference_provenance_validation_failed" not in preference_provenance_errors:
        errors.append("preference_provenance_probe_not_rejected")
    if "preference_domain_pack_coverage_incomplete" not in preference_domain_errors:
        errors.append("preference_domain_probe_not_rejected")
    if (
        "preference_paid_tools_enabled_without_explicit_approval"
        not in preference_paid_tool_errors
    ):
        errors.append("preference_paid_tool_probe_not_rejected")
    if "preference_source_quorum_credit_allowed" not in preference_source_quorum_errors:
        errors.append("preference_source_quorum_probe_not_rejected")
    if (
        "preference_source_promotion_policy_invalid"
        not in preference_source_promotion_errors
    ):
        errors.append("preference_source_promotion_probe_not_rejected")

    for key in (
        "trade_candidate_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "provider_call_allowed_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "hardware_scheduler_enabled_count",
        "scheduler_enabled_count",
        "authority_violation_count",
    ):
        if written_artifact.get(key) != 0:
            errors.append(f"certification_authority_count_not_zero:{key}")
    for key in (
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "quantum_provider_call_allowed",
        "quantum_hardware_submission_allowed",
        "hardware_submission_allowed",
        "hardware_submitted",
        "hardware_scheduler_enabled",
        "scheduler_enabled",
    ):
        if written_artifact.get(key) is not False:
            errors.append(f"certification_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_certification_error={error}")
        print("phase4_certification_check=failed")
        return 1

    print("phase4_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
