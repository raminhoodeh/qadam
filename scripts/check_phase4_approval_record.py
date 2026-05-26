#!/usr/bin/env python3
"""Validate the Q4-10 Phase 4 Fund Manager approval record contract."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase4_approval_record import (  # noqa: E402
    APPROVAL_EVENT_LOG,
    PHASE4_APPROVAL_RECORD_SCHEMA_VERSION,
    approval_bundle_certification_summary,
    build_fund_manager_approval_event,
    validate_fund_manager_approval_event,
    write_fund_manager_approval_event,
)
from orchestrator.phase4_strategy_toggles import (  # noqa: E402
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    artifact_path = runtime_dir / "phase4_fund_manager_approval_event.json"
    artifact = (
        json.loads(artifact_path.read_text(encoding="utf-8"))
        if artifact_path.exists()
        else build_fund_manager_approval_event(settings=settings)
    )
    event_log_path = Path(artifact.get("event_log_path") or (runtime_dir / APPROVAL_EVENT_LOG))
    if artifact.get("approval_logged") is True and event_log_path.exists():
        written_artifact = deepcopy(artifact)
        written_artifact["validation_errors"] = validate_fund_manager_approval_event(
            written_artifact
        )
        output_path = artifact_path
        output_path.write_text(
            json.dumps(written_artifact, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        output_path, written_artifact = write_fund_manager_approval_event(
            artifact,
            path=artifact_path,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    validation_errors = validate_fund_manager_approval_event(written_artifact)
    event_replay = EventLog(event_log_path, echo=False).replay()
    latest_event = event_replay["last_by_component"].get("phase4_fund_manager_approval", {})
    current_summary = approval_bundle_certification_summary(written_artifact)
    current_toggle = build_strategy_toggle_snapshot(
        settings=settings,
        approval_event=written_artifact,
    )
    current_toggle_errors = validate_strategy_toggle_snapshot(current_toggle)

    approved_probe = build_fund_manager_approval_event(
        approval_state="approved",
        approver_label="fund_manager_ramin",
        settings=settings,
    )
    _, approved_probe = write_fund_manager_approval_event(
        approved_probe,
        path=runtime_dir / "phase4_fund_manager_approval_event.approved_probe.json",
        settings=settings,
        record_event=True,
        event_log_path=runtime_dir / "phase4_approval_events.approved_probe.jsonl",
    )
    approved_probe_errors = validate_fund_manager_approval_event(approved_probe)
    approved_summary = approval_bundle_certification_summary(approved_probe)
    approved_toggle = build_strategy_toggle_snapshot(
        settings=settings,
        approval_event=approved_probe,
    )
    approved_toggle_errors = validate_strategy_toggle_snapshot(approved_toggle)

    missing_log_probe = deepcopy(written_artifact)
    missing_log_probe["approval_logged"] = False
    missing_log_probe["event_log_correlation_id"] = None
    missing_log_errors = validate_fund_manager_approval_event(missing_log_probe)

    fingerprint_probe = deepcopy(written_artifact)
    fingerprint_probe["strategy_artifact_fingerprint"] = "bad-fingerprint"
    fingerprint_errors = validate_fund_manager_approval_event(fingerprint_probe)

    authority_probe = deepcopy(written_artifact)
    authority_probe["broker_write_allowed"] = True
    authority_errors = validate_fund_manager_approval_event(authority_probe)

    amendments_probe = deepcopy(written_artifact)
    amendments_probe["approval_state"] = "amendments_required"
    amendments_probe["status"] = "draft"
    amendments_probe["certification_candidate"] = False
    amendments_probe["approved_strategy_families"] = []
    amendments_probe["required_amendments"] = []
    amendments_errors = validate_fund_manager_approval_event(amendments_probe)

    approved_bad_probe = deepcopy(approved_probe)
    approved_bad_probe["approved_strategy_families"] = []
    approved_bad_errors = validate_fund_manager_approval_event(approved_bad_probe)

    preference_scope_probe = deepcopy(written_artifact)
    preference_scope_probe["preference_mcp_approval_scope"]["source_quorum_credit_allowed"] = True
    preference_scope_errors = validate_fund_manager_approval_event(preference_scope_probe)

    preference_source_promotion_probe = deepcopy(written_artifact)
    preference_source_promotion_probe["preference_mcp_approval_scope"][
        "source_promotion_promoted_decision_count"
    ] = 1
    preference_source_promotion_errors = validate_fund_manager_approval_event(
        preference_source_promotion_probe
    )

    preference_scope = written_artifact["preference_mcp_approval_scope"]

    print("phase4_approval_record_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_approval_record_schema_version={PHASE4_APPROVAL_RECORD_SCHEMA_VERSION}")
    print(f"phase4_approval_record_artifact_path={output_path}")
    print(f"phase4_approval_record_event_log_path={event_log_path}")
    print(f"phase4_approval_record_state={written_artifact['approval_state']}")
    print(f"phase4_approval_record_status_field={written_artifact['status']}")
    print(f"phase4_approval_record_logged={written_artifact['approval_logged']}")
    print(f"phase4_approval_record_event_log_total_events={event_replay['total_events']}")
    print(f"phase4_approval_record_event_type={latest_event.get('event_type')}")
    print(f"phase4_approval_record_approver_label={written_artifact['approver_label']}")
    print(
        "phase4_approval_record_strategy_fingerprint="
        f"{written_artifact['strategy_artifact_fingerprint']}"
    )
    print(
        "phase4_approval_record_approved_strategy_family_count="
        f"{len(written_artifact['approved_strategy_families'])}"
    )
    print(
        "phase4_approval_record_rejected_strategy_family_count="
        f"{len(written_artifact['rejected_strategy_families'])}"
    )
    print(
        "phase4_approval_record_required_amendment_count="
        f"{len(written_artifact['required_amendments'])}"
    )
    print(
        "phase4_approval_record_preference_aware_strategy_document="
        f"{preference_scope['preference_aware_strategy_document']}"
    )
    print(
        "phase4_approval_record_preference_domain_pack_count="
        f"{preference_scope['approved_domain_pack_count']}"
    )
    print(
        "phase4_approval_record_preference_family_policy_count="
        f"{preference_scope['candidate_family_with_policy_count']}"
    )
    print(
        "phase4_approval_record_preference_source_quorum_credit_allowed="
        f"{preference_scope['source_quorum_credit_allowed']}"
    )
    print(
        "phase4_approval_record_preference_paid_tool_calls_approved="
        f"{preference_scope['paid_tool_calls_approved']}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_status="
        f"{preference_scope['source_promotion_status']}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_decision_count="
        f"{preference_scope['source_promotion_decision_count']}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_promoted_count="
        f"{preference_scope['source_promotion_promoted_decision_count']}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_source_count_after="
        f"{preference_scope['source_promotion_canonical_source_count_after']}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_source36="
        f"{preference_scope['preference_mcp_source_36']}"
    )
    print(f"phase4_approval_record_validation_error_count={len(validation_errors)}")
    print(
        "phase4_approval_record_amendments_certification_allowed="
        f"{current_summary['phase4_certification_allowed']}"
    )
    print(
        "phase4_approval_record_approved_probe_error_count="
        f"{len(approved_probe_errors)}"
    )
    print(
        "phase4_approval_record_approved_probe_certification_allowed="
        f"{approved_summary['phase4_certification_allowed']}"
    )
    print(
        "phase4_approval_record_approved_probe_toggle_approved_shadow_count="
        f"{approved_toggle['approved_shadow_toggle_count']}"
    )
    print(
        "phase4_approval_record_approved_probe_toggle_error_count="
        f"{len(approved_toggle_errors)}"
    )
    print(
        "phase4_approval_record_amendments_toggle_draft_count="
        f"{current_toggle['draft_toggle_count']}"
    )
    print(
        "phase4_approval_record_amendments_toggle_error_count="
        f"{len(current_toggle_errors)}"
    )
    print(
        "phase4_approval_record_missing_log_probe_error_count="
        f"{len(missing_log_errors)}"
    )
    print(
        "phase4_approval_record_fingerprint_probe_error_count="
        f"{len(fingerprint_errors)}"
    )
    print(
        "phase4_approval_record_authority_probe_error_count="
        f"{len(authority_errors)}"
    )
    print(
        "phase4_approval_record_amendments_probe_error_count="
        f"{len(amendments_errors)}"
    )
    print(
        "phase4_approval_record_approved_bad_probe_error_count="
        f"{len(approved_bad_errors)}"
    )
    print(
        "phase4_approval_record_preference_scope_probe_error_count="
        f"{len(preference_scope_errors)}"
    )
    print(
        "phase4_approval_record_preference_source_promotion_probe_error_count="
        f"{len(preference_source_promotion_errors)}"
    )
    print(
        "phase4_approval_record_trade_candidate_count="
        f"{written_artifact['trade_candidate_count']}"
    )
    print(f"phase4_approval_record_execution_allowed={written_artifact['execution_allowed']}")
    print(f"phase4_approval_record_paper_order_allowed={written_artifact['paper_order_allowed']}")
    print(f"phase4_approval_record_broker_write_allowed={written_artifact['broker_write_allowed']}")
    print(f"phase4_approval_record_live_capital_enabled={written_artifact['live_capital_enabled']}")
    print(f"phase4_approval_record_boundary={written_artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if written_artifact["approval_logged"] is not True:
        errors.append("approval_record_not_logged")
    if event_replay["total_events"] < 1:
        errors.append("event_log_event_count_missing")
    if latest_event.get("event_type") != "phase4_fund_manager_approval_recorded":
        errors.append("event_log_event_type_mismatch")
    if written_artifact["approval_state"] == "approved":
        if written_artifact["status"] != "approved_shadow":
            errors.append("approved_status_not_approved_shadow")
        if written_artifact["required_amendments"]:
            errors.append("approved_required_amendments_present")
        if len(written_artifact["approved_strategy_families"]) != 5:
            errors.append("approved_strategy_family_count_mismatch")
        if current_summary["phase4_certification_allowed"] is not True:
            errors.append("approved_certification_not_allowed")
        if current_toggle["approved_shadow_toggle_count"] != 5:
            errors.append("approved_toggle_not_approved_shadow")
    elif written_artifact["approval_state"] == "amendments_required":
        if written_artifact["status"] != "draft":
            errors.append("amendments_status_not_draft")
        if not written_artifact["required_amendments"]:
            errors.append("required_amendments_missing")
        if current_summary["phase4_certification_allowed"] is not False:
            errors.append("amendments_certification_allowed")
        if current_toggle["draft_toggle_count"] != 5:
            errors.append("amendments_toggle_not_draft")
    else:
        errors.append("approval_state_not_supported_for_phase4_gate")
    if approved_probe_errors:
        errors.append("approved_probe_invalid")
    if approved_summary["phase4_certification_allowed"] is not True:
        errors.append("approved_probe_certification_not_allowed")
    if approved_toggle["approved_shadow_toggle_count"] != 5:
        errors.append("approved_probe_toggle_not_approved_shadow")
    if approved_toggle_errors:
        errors.append("approved_probe_toggle_invalid")
    if current_toggle_errors:
        errors.append("current_toggle_invalid")
    if "approval_decision_not_logged" not in missing_log_errors:
        errors.append("missing_log_probe_not_rejected")
    if "strategy_artifact_fingerprint_mismatch" not in fingerprint_errors:
        errors.append("fingerprint_probe_not_rejected")
    if "approval_authority_enabled:broker_write_allowed" not in authority_errors:
        errors.append("authority_probe_not_rejected")
    if "required_amendments_missing" not in amendments_errors:
        errors.append("amendments_probe_not_rejected")
    if "approved_strategy_families_missing" not in approved_bad_errors:
        errors.append("approved_bad_probe_not_rejected")
    if preference_scope["preference_aware_strategy_document"] is not True:
        errors.append("preference_aware_strategy_document_missing")
    if preference_scope["approved_domain_pack_count"] != 6:
        errors.append("preference_domain_pack_count_mismatch")
    if preference_scope["candidate_family_with_policy_count"] != 5:
        errors.append("preference_family_policy_count_mismatch")
    if preference_scope["source_quorum_credit_allowed"] is not False:
        errors.append("preference_source_quorum_enabled")
    if preference_scope["paid_tool_calls_approved"] is not False:
        errors.append("preference_paid_tool_approval_unexpected")
    if preference_scope["source_promotion_status"] != "validated":
        errors.append("preference_source_promotion_not_validated")
    if preference_scope["source_promotion_decision_count"] != 6:
        errors.append("preference_source_promotion_decision_count_mismatch")
    if preference_scope["source_promotion_promoted_decision_count"] != 0:
        errors.append("preference_source_promotion_promoted_count_nonzero")
    if preference_scope["source_promotion_canonical_source_count_after"] != 35:
        errors.append("preference_source_promotion_source_count_mismatch")
    if preference_scope["preference_mcp_source_36"] is not False:
        errors.append("preference_source36_enabled")
    if (
        "preference_approval_scope_authority_enabled:source_quorum_credit_allowed"
        not in preference_scope_errors
    ):
        errors.append("preference_scope_probe_not_rejected")
    if (
        "preference_approval_scope_source_promotion_invalid"
        not in preference_source_promotion_errors
    ):
        errors.append("preference_source_promotion_probe_not_rejected")
    for key in (
        "trade_candidate_count",
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if written_artifact.get(key) != 0:
            errors.append(f"approval_authority_count_not_zero:{key}")
    for key in (
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "staged_paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "quantum_provider_call_allowed",
        "quantum_hardware_submission_allowed",
        "scheduler_enabled",
    ):
        if written_artifact.get(key) is not False:
            errors.append(f"approval_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_approval_record_error={error}")
        print("phase4_approval_record_check=failed")
        return 1

    print("phase4_approval_record_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
