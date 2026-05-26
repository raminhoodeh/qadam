#!/usr/bin/env python3
"""Validate Q6-16 cockpit and dashboard visibility."""

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
from orchestrator.phase6_artifacts import (  # noqa: E402
    PHASE6_AUTHORITY_FIELDS,
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
)
from orchestrator.phase6_cockpit_visibility import (  # noqa: E402
    PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
    build_phase6_cockpit_visibility,
    phase6_cockpit_visibility_paths,
    phase6_cockpit_visibility_public_status,
    validate_phase6_cockpit_visibility,
    write_phase6_cockpit_visibility,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    root = _repo_root(settings)
    prebuilt = build_phase6_cockpit_visibility(settings=settings)
    output_path, history_path, event_log_path = phase6_cockpit_visibility_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())

    output_path, history_path, event_log_path, written = write_phase6_cockpit_visibility(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_cockpit_visibility(written)
    replay = EventLog(event_log_path, echo=False).replay()
    public_status = phase6_cockpit_visibility_public_status(settings=settings)
    runtime_copy = _read_json(root / f"data/runtime/{PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}")

    ui_probe = deepcopy(written)
    ui_probe["ui_inferred_readiness_count"] = 1
    ui_probe["source_status_records"][0]["ui_inferred_readiness"] = True
    ui_errors = validate_phase6_cockpit_visibility(ui_probe)

    backend_probe = deepcopy(written)
    backend_probe["backend_derived"] = False
    backend_probe["display_derived_from_backend"] = False
    backend_probe["dashboard_uses_backend_status"] = False
    backend_errors = validate_phase6_cockpit_visibility(backend_probe)

    parity_probe = deepcopy(written)
    parity_probe["backend_parity_error_count"] = 1
    parity_probe["source_status_records"][0]["display_status"] = "ui_override"
    parity_errors = validate_phase6_cockpit_visibility(parity_probe)

    public_path_probe = deepcopy(written)
    public_path_probe["public_status"]["source_status_records"][0]["source_ref"] = (
        "/Users/raminhoodeh/Desktop/qadam/private.json"
    )
    public_path_errors = validate_phase6_cockpit_visibility(public_path_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["public_status"]["raw_payload"] = {"forbidden": True}
    raw_payload_probe["raw_payload_exposed_count"] = 1
    raw_payload_errors = validate_phase6_cockpit_visibility(raw_payload_probe)

    broker_id_probe = deepcopy(written)
    broker_id_probe["public_status"]["source_status_records"][0]["source_ref"] = (
        "data/runtime/external_order_id.json"
    )
    broker_id_probe["broker_identifier_exposed_count"] = 1
    broker_id_errors = validate_phase6_cockpit_visibility(broker_id_probe)

    authority_probe = deepcopy(written)
    authority_probe["phase6_learning_write_allowed"] = True
    authority_probe["phase6_learning_write_allowed_count"] = 1
    authority_probe["blocked_authorities"] = [
        field for field in authority_probe["blocked_authorities"] if field != "phase6_learning_write_allowed"
    ]
    authority_probe["blocked_authority_count"] = len(authority_probe["blocked_authorities"])
    authority_errors = validate_phase6_cockpit_visibility(authority_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_cockpit_visibility(proof_credit_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_cockpit_visibility(unsafe_probe)

    resolved_probe = deepcopy(written)
    resolved_probe["postmortem_resolved_count"] = 1
    unresolved_errors = validate_phase6_cockpit_visibility(resolved_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_cockpit_visibility_not_written")
    if written["status"] != "visible":
        errors.append("cockpit_visibility_status_not_visible")
    if written["visibility_state"] != "backend_derived_deferred_learning_visible":
        errors.append("cockpit_visibility_state_mismatch")
    if written["learning_state"] != "deferred_learning_visible":
        errors.append("cockpit_visibility_learning_state_mismatch")
    if written["backend_derived"] is not True:
        errors.append("cockpit_visibility_not_backend_derived")
    if written["display_derived_from_backend"] is not True:
        errors.append("cockpit_visibility_display_not_backend_derived")
    if written["dashboard_uses_backend_status"] is not True:
        errors.append("cockpit_visibility_dashboard_not_backend_derived")
    if written["ui_inferred_readiness_count"] != 0:
        errors.append("cockpit_visibility_ui_inferred_count_nonzero")
    if written["backend_parity_error_count"] != 0:
        errors.append("cockpit_visibility_backend_parity_error")
    if written["source_missing_count"] != 0:
        errors.append("cockpit_visibility_source_missing")
    if written["source_validation_error_count"] != 0:
        errors.append("cockpit_visibility_source_validation_errors")
    if written["postmortem_due_count"] < 1:
        errors.append("cockpit_visibility_postmortem_due_missing")
    if written["postmortem_resolved_count"] != 0:
        errors.append("cockpit_visibility_resolved_postmortem_unexpected")
    if written["closed_trade_outcome_count"] < 1:
        errors.append("cockpit_visibility_closed_trade_missing")
    if written["approval_state"] != "deferred":
        errors.append("cockpit_visibility_approval_state_not_deferred")
    if written["pending_review_action_count"] != 0:
        errors.append("cockpit_visibility_pending_review_actions_not_cleared")
    if written["deferred_action_count"] != 5:
        errors.append("cockpit_visibility_deferred_action_count_mismatch")
    if written["explicitly_deferred_action_count"] != 5:
        errors.append("cockpit_visibility_explicit_deferred_action_count_mismatch")
    if written["learning_actions_review_satisfied"] is not True:
        errors.append("cockpit_visibility_learning_review_not_satisfied")
    if written["staged_graph_entry_count"] != 0:
        errors.append("cockpit_visibility_staged_graph_entries_unexpected")
    if written["knowledge_graph_read_result_count"] < 1:
        errors.append("cockpit_visibility_kg_read_result_missing")
    if written["model_weight_proposal_count"] < 1:
        errors.append("cockpit_visibility_model_weight_proposal_missing")
    if written["trust_score_proposal_count"] < 1:
        errors.append("cockpit_visibility_trust_score_proposal_missing")
    if written["shadow_replay_variant_count"] < 1:
        errors.append("cockpit_visibility_shadow_replay_missing")
    if written["architect_recommendation_count"] < 1:
        errors.append("cockpit_visibility_architect_recommendation_missing")
    if written["blocked_authority_count"] != len(PHASE6_AUTHORITY_FIELDS):
        errors.append("cockpit_visibility_blocked_authority_count_mismatch")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("cockpit_visibility_unsafe_total_nonzero")
    for key in (
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if written[key] != 0:
            errors.append(f"cockpit_visibility_exposure_nonzero:{key}")
    if replay["total_events"] != 1:
        errors.append("cockpit_visibility_event_log_count_mismatch")
    if public_status.get("artifact_id") != written["artifact_id"]:
        errors.append("cockpit_visibility_public_status_artifact_mismatch")
    if public_status.get("runtime_artifact_path") or public_status.get("event_log_path"):
        errors.append("cockpit_visibility_public_status_local_path_field")

    if not _has_error(ui_errors, "cockpit_visibility_ui_inferred_readiness"):
        errors.append("ui_inferred_readiness_probe_not_rejected")
    if not _has_error(ui_errors, "cockpit_visibility_source_ui_inferred"):
        errors.append("source_ui_inference_probe_not_rejected")
    if not _has_error(backend_errors, "cockpit_visibility_not_backend_derived"):
        errors.append("backend_derived_probe_not_rejected")
    if not _has_error(parity_errors, "cockpit_visibility_backend_parity_error"):
        errors.append("parity_probe_not_rejected")
    if not _has_error(parity_errors, "cockpit_visibility_source_display_backend_mismatch"):
        errors.append("source_parity_probe_not_rejected")
    if not _has_error(public_path_errors, "public_local_path"):
        errors.append("public_local_path_probe_not_rejected")
    if not _has_error(raw_payload_errors, "cockpit_visibility_exposure_count_nonzero"):
        errors.append("raw_payload_count_probe_not_rejected")
    if not _has_error(raw_payload_errors, "cockpit_visibility_public_status_extra_fields"):
        errors.append("raw_payload_public_probe_not_rejected")
    if not _has_error(broker_id_errors, "cockpit_visibility_exposure_count_nonzero"):
        errors.append("broker_identifier_count_probe_not_rejected")
    if not _has_error(broker_id_errors, "public_broker_identifier"):
        errors.append("broker_identifier_public_probe_not_rejected")
    if not _has_error(authority_errors, "authority_enabled:phase6_learning_write_allowed"):
        errors.append("authority_probe_not_rejected")
    if not _has_error(authority_errors, "cockpit_visibility_blocked_authorities_incomplete"):
        errors.append("authority_blocked_list_probe_not_rejected")
    if not _has_error(proof_credit_errors, "authority_enabled:phase7_proof_credit_allowed"):
        errors.append("proof_credit_probe_not_rejected")
    if not _has_error(unsafe_errors, "unsafe_counter_nonzero:broker_post_called_count"):
        errors.append("unsafe_counter_probe_not_rejected")
    if not _has_error(unresolved_errors, "cockpit_visibility_unapproved_resolved_postmortem"):
        errors.append("unapproved_resolved_postmortem_probe_not_rejected")

    print(f"phase6_cockpit_visibility_status={written['status']}")
    print(f"phase6_cockpit_visibility_artifact_path={output_path}")
    print(f"phase6_cockpit_visibility_history_path={history_path}")
    print(f"phase6_cockpit_visibility_event_log_path={event_log_path}")
    print(f"phase6_cockpit_visibility_visibility_state={written['visibility_state']}")
    print(f"phase6_cockpit_visibility_learning_state={written['learning_state']}")
    print(f"phase6_cockpit_visibility_backend_derived={written['backend_derived']}")
    print(
        "phase6_cockpit_visibility_ui_inferred_readiness_count="
        f"{written['ui_inferred_readiness_count']}"
    )
    print(f"phase6_cockpit_visibility_postmortem_due_count={written['postmortem_due_count']}")
    print(
        "phase6_cockpit_visibility_postmortem_resolved_count="
        f"{written['postmortem_resolved_count']}"
    )
    print(f"phase6_cockpit_visibility_approval_state={written['approval_state']}")
    print(
        "phase6_cockpit_visibility_pending_review_action_count="
        f"{written['pending_review_action_count']}"
    )
    print(
        "phase6_cockpit_visibility_deferred_action_count="
        f"{written['deferred_action_count']}"
    )
    print(
        "phase6_cockpit_visibility_explicitly_deferred_action_count="
        f"{written['explicitly_deferred_action_count']}"
    )
    print(
        "phase6_cockpit_visibility_learning_actions_review_satisfied="
        f"{written['learning_actions_review_satisfied']}"
    )
    print(
        "phase6_cockpit_visibility_staged_graph_entry_count="
        f"{written['staged_graph_entry_count']}"
    )
    print(
        "phase6_cockpit_visibility_knowledge_graph_read_result_count="
        f"{written['knowledge_graph_read_result_count']}"
    )
    print(
        "phase6_cockpit_visibility_model_weight_proposal_count="
        f"{written['model_weight_proposal_count']}"
    )
    print(
        "phase6_cockpit_visibility_trust_score_proposal_count="
        f"{written['trust_score_proposal_count']}"
    )
    print(
        "phase6_cockpit_visibility_shadow_replay_variant_count="
        f"{written['shadow_replay_variant_count']}"
    )
    print(
        "phase6_cockpit_visibility_architect_recommendation_count="
        f"{written['architect_recommendation_count']}"
    )
    print(f"phase6_cockpit_visibility_blocked_authority_count={written['blocked_authority_count']}")
    print(f"phase6_cockpit_visibility_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_cockpit_visibility_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_cockpit_visibility_validation_error_count={len(validation_errors)}")
    print(f"phase6_cockpit_visibility_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_cockpit_visibility_schema_summary_status={schema_summary['status']}")
    print(f"phase6_cockpit_visibility_public_validation_error_count={public_status['validation_error_count']}")
    print(f"phase6_cockpit_visibility_next_stage={written['recommended_next_stage']}")
    print("phase6_cockpit_visibility_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_cockpit_visibility_error={error}")
        print("phase6_cockpit_visibility_check=failed")
        return 1
    print("phase6_cockpit_visibility_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
