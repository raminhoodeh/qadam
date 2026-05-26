#!/usr/bin/env python3
"""Validate Q6-17 Phase 6 certification."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase6_artifacts import (  # noqa: E402
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
)
from orchestrator.phase6_certification import (  # noqa: E402
    PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES,
    PHASE6_CERTIFICATION_RUNTIME_ARTIFACT,
    PHASE6_CERTIFICATION_SCHEMA_VERSION,
    build_phase6_certification,
    phase6_certification_paths,
    phase6_certification_public_status,
    validate_phase6_certification,
    write_phase6_certification,
)
from orchestrator.phase6_cockpit_visibility import (  # noqa: E402
    build_phase6_cockpit_visibility,
    validate_phase6_cockpit_visibility,
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


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = []
    provenance = artifact.get("provenance", {})
    if isinstance(provenance, dict):
        refs.extend(ref for ref in provenance.get("source_refs", []) if isinstance(ref, str))
    return sorted(
        {
            ref
            for ref in refs
            if ref.startswith("data/runtime/")
            and not ref.startswith("data/runtime/phase6_certification")
        }
    )


def _file_hashes(settings: Settings, artifact: dict[str, object]) -> dict[str, str | None]:
    root = _repo_root(settings)
    hashes: dict[str, str | None] = {}
    for ref in _source_refs(artifact):
        path = root / ref
        if not path.exists():
            hashes[ref] = None
            continue
        hashes[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    root = _repo_root(settings)
    prebuilt = build_phase6_certification(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    output_path, history_path, event_log_path = phase6_certification_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    cockpit_visibility = build_phase6_cockpit_visibility(settings=settings)
    cockpit_visibility_errors = validate_phase6_cockpit_visibility(cockpit_visibility)

    output_path, history_path, event_log_path, written = write_phase6_certification(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_certification(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]
    public_status = phase6_certification_public_status(settings=settings)
    runtime_copy = _read_json(root / f"data/runtime/{PHASE6_CERTIFICATION_RUNTIME_ARTIFACT}")

    certified_with_blocker_probe = deepcopy(written)
    certified_with_blocker_probe["certification_blockers"] = [
        "probe_certification_blocker"
    ]
    certified_with_blocker_probe["certification_blocker_count"] = 1
    certified_with_blocker_errors = validate_phase6_certification(
        certified_with_blocker_probe
    )

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_certification(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_certification(phase5_proof_probe)

    phase7_demo_probe = deepcopy(written)
    phase7_demo_probe["phase6_certified"] = False
    phase7_demo_probe["phase6_complete"] = False
    phase7_demo_probe["phase6_exit_gate"] = False
    phase7_demo_probe["status"] = "blocked"
    phase7_demo_probe["certification_blockers"] = ["probe_certification_blocker"]
    phase7_demo_probe["certification_blocker_count"] = 1
    phase7_demo_probe["phase7_demo_proof_planning_allowed"] = True
    phase7_demo_errors = validate_phase6_certification(phase7_demo_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase6_certification(live_capital_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_write_allowed"] = True
    broker_probe["broker_write_allowed_count"] = 1
    broker_errors = validate_phase6_certification(broker_probe)

    postmortem_probe = deepcopy(written)
    postmortem_probe["postmortem_explicitly_deferred_count"] = 0
    postmortem_probe["unresolved_postmortem_count"] = 0
    postmortem_probe["reviewed_postmortem_coverage_satisfied"] = True
    postmortem_errors = validate_phase6_certification(postmortem_probe)

    learning_review_probe = deepcopy(written)
    learning_review_probe["learning_actions_review_satisfied"] = True
    learning_review_probe["pending_review_action_count"] = 1
    learning_review_errors = validate_phase6_certification(learning_review_probe)

    gate_display_probe = deepcopy(written)
    gate_display_probe["gate_records"][0]["display_status"] = "dishonest_status"
    gate_display_errors = validate_phase6_certification(gate_display_probe)

    gate_ui_probe = deepcopy(written)
    gate_ui_probe["gate_records"][0]["ui_inferred_readiness"] = True
    gate_ui_errors = validate_phase6_certification(gate_ui_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_certification(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if cockpit_visibility_errors:
        errors.extend(cockpit_visibility_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("phase6_certification_mutated_source_refs:" + ",".join(mutated_refs))
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase6_certification_not_written")
    if public_status.get("artifact_id") != written["artifact_id"]:
        errors.append("phase6_certification_public_status_artifact_mismatch")
    if public_status.get("runtime_artifact_path") or public_status.get("event_log_path"):
        errors.append("phase6_certification_public_status_local_path_field")

    if written["schema_version"] != 1:
        errors.append("phase6_certification_schema_version_root_mismatch")
    if written["phase6_certification_schema_version"] != PHASE6_CERTIFICATION_SCHEMA_VERSION:
        errors.append("phase6_certification_schema_version_mismatch")
    if written["input_gate_count"] != len(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("phase6_certification_input_gate_count_mismatch")
    if written["input_gate_passed_count"] != len(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("phase6_certification_input_gate_passed_count_mismatch")
    if written["input_gate_blocked_count"] != 0:
        errors.append("phase6_certification_input_gate_blocked")
    if written["status"] != "certified":
        errors.append("phase6_certification_not_certified")
    if written["stage_status"] != "phase6_certified":
        errors.append("phase6_certification_stage_status_mismatch")
    if written["phase6_certified"] is not True:
        errors.append("phase6_certification_not_certified_true")
    if written["phase6_exit_gate"] is not True:
        errors.append("phase6_certification_exit_gate_not_open")
    if written["phase7_demo_proof_planning_allowed"] is not True:
        errors.append("phase6_certification_phase7_demo_not_allowed")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase6_certification_phase7_credit_allowed")
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase6_certification_phase5_trade_counted_for_phase7")
    if written["postmortem_due_count"] < 1:
        errors.append("phase6_certification_postmortem_due_missing")
    if written["postmortem_resolved_count"] != 0:
        errors.append("phase6_certification_postmortem_resolved_unexpected")
    if written["postmortem_explicitly_deferred_count"] != written["postmortem_due_count"]:
        errors.append("phase6_certification_postmortem_not_explicitly_deferred")
    if written["unresolved_postmortem_count"] != 0:
        errors.append("phase6_certification_unresolved_postmortem_nonzero")
    if written["reviewed_postmortem_coverage_satisfied"] is not True:
        errors.append("phase6_certification_reviewed_coverage_not_satisfied")
    if written["approval_state"] != "deferred":
        errors.append("phase6_certification_approval_state_not_deferred")
    if written["explicitly_deferred_action_count"] != written["proposed_action_count"]:
        errors.append("phase6_certification_actions_not_explicitly_deferred")
    if written["pending_review_action_count"] != 0:
        errors.append("phase6_certification_pending_actions_nonzero")
    if written["learning_actions_review_satisfied"] is not True:
        errors.append("phase6_certification_learning_review_not_satisfied")
    if written["knowledge_graph_requirement_satisfied"] is not True:
        errors.append("phase6_certification_kg_requirement_not_satisfied")
    if written["certification_blocker_count"] != 0:
        errors.append("phase6_certification_blockers_present")
    for count_key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
    ):
        if written[count_key] < 1:
            errors.append(f"phase6_certification_missing_count:{count_key}")
    if written["cockpit_visibility_status"] != "visible":
        errors.append("phase6_certification_cockpit_not_visible")
    if written["cockpit_backend_derived"] is not True:
        errors.append("phase6_certification_cockpit_not_backend_derived")
    if written["cockpit_ui_inferred_readiness_count"] != 0:
        errors.append("phase6_certification_cockpit_ui_inferred")
    if written["blocking_unsafe_count"] != 0:
        errors.append("phase6_certification_blocking_unsafe_nonzero")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("phase6_certification_unsafe_total_nonzero")
    if written["event_log_written"] is not True:
        errors.append("phase6_certification_event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("phase6_certification_event_log_event_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("phase6_certification_event_log_replay_count_mismatch")

    if not _has_error(certified_with_blocker_errors, "phase6_certified_with_blockers"):
        errors.append("certified_with_blocker_probe_not_rejected")
    if not _has_error(proof_credit_errors, "phase7_proof_credit_allowed"):
        errors.append("proof_credit_probe_not_rejected")
    if not _has_error(phase5_proof_errors, "phase5_test_trades_count_for_phase7"):
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(phase7_demo_errors, "blocked_phase6_certification_phase7_demo_allowed"):
        errors.append("phase7_demo_probe_not_rejected")
    if not _has_error(live_capital_errors, "phase6_certification_live_capital_enabled"):
        errors.append("live_capital_probe_not_rejected")
    if not _has_error(broker_errors, "phase6_certification_broker_write_allowed"):
        errors.append("broker_write_probe_not_rejected")
    if not _has_error(postmortem_errors, "phase6_certification_false_postmortem_coverage"):
        errors.append("false_postmortem_coverage_probe_not_rejected")
    if not _has_error(learning_review_errors, "phase6_certification_false_learning_review"):
        errors.append("false_learning_review_probe_not_rejected")
    if not _has_error(gate_display_errors, "gate_display_backend_mismatch"):
        errors.append("gate_display_probe_not_rejected")
    if not _has_error(gate_ui_errors, "gate_ui_inferred_readiness"):
        errors.append("gate_ui_probe_not_rejected")
    if not _has_error(unsafe_errors, "phase6_certification_unsafe_count_nonzero"):
        errors.append("unsafe_probe_not_rejected")

    print(f"phase6_certification_status={written['status']}")
    print(f"phase6_certification_schema_version={PHASE6_CERTIFICATION_SCHEMA_VERSION}")
    print(f"phase6_certification_artifact_path={output_path}")
    print(f"phase6_certification_history_path={history_path}")
    print(f"phase6_certification_event_log_path={event_log_path}")
    print(f"phase6_certification_stage_status={written['stage_status']}")
    print(f"phase6_certification_certification_state={written['certification_state']}")
    print(f"phase6_certification_phase6_certified={written['phase6_certified']}")
    print(f"phase6_certification_phase6_exit_gate={written['phase6_exit_gate']}")
    print(
        "phase6_certification_phase7_demo_proof_planning_allowed="
        f"{written['phase7_demo_proof_planning_allowed']}"
    )
    print(
        "phase6_certification_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_certification_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(f"phase6_certification_input_gate_count={written['input_gate_count']}")
    print(f"phase6_certification_input_gate_passed_count={written['input_gate_passed_count']}")
    print(f"phase6_certification_input_gate_blocked_count={written['input_gate_blocked_count']}")
    print(f"phase6_certification_blocker_count={written['certification_blocker_count']}")
    print(f"phase6_certification_blockers={','.join(written['certification_blockers'])}")
    print(f"phase6_certification_postmortem_due_count={written['postmortem_due_count']}")
    print(
        "phase6_certification_postmortem_resolved_count="
        f"{written['postmortem_resolved_count']}"
    )
    print(
        "phase6_certification_unresolved_postmortem_count="
        f"{written['unresolved_postmortem_count']}"
    )
    print(
        "phase6_certification_reviewed_postmortem_coverage_satisfied="
        f"{written['reviewed_postmortem_coverage_satisfied']}"
    )
    print(f"phase6_certification_approval_state={written['approval_state']}")
    print(f"phase6_certification_proposed_action_count={written['proposed_action_count']}")
    print(f"phase6_certification_approved_action_count={written['approved_action_count']}")
    print(
        "phase6_certification_explicitly_deferred_action_count="
        f"{written['explicitly_deferred_action_count']}"
    )
    print(
        "phase6_certification_pending_review_action_count="
        f"{written['pending_review_action_count']}"
    )
    print(
        "phase6_certification_learning_actions_review_satisfied="
        f"{written['learning_actions_review_satisfied']}"
    )
    print(
        "phase6_certification_knowledge_graph_requirement_satisfied="
        f"{written['knowledge_graph_requirement_satisfied']}"
    )
    print(
        "phase6_certification_knowledge_graph_read_result_count="
        f"{written['knowledge_graph_read_result_count']}"
    )
    print(
        "phase6_certification_model_weight_proposal_count="
        f"{written['model_weight_proposal_count']}"
    )
    print(
        "phase6_certification_trust_score_proposal_count="
        f"{written['trust_score_proposal_count']}"
    )
    print(
        "phase6_certification_shadow_replay_variant_count="
        f"{written['shadow_replay_variant_count']}"
    )
    print(
        "phase6_certification_architect_recommendation_count="
        f"{written['architect_recommendation_count']}"
    )
    print(f"phase6_certification_cockpit_visibility_status={written['cockpit_visibility_status']}")
    print(f"phase6_certification_cockpit_backend_derived={written['cockpit_backend_derived']}")
    print(f"phase6_certification_blocking_unsafe_count={written['blocking_unsafe_count']}")
    print(f"phase6_certification_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_certification_event_log_written={written['event_log_written']}")
    print(f"phase6_certification_event_log_event_count={written['event_log_event_count']}")
    print(f"phase6_certification_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_certification_validation_error_count={len(validation_errors)}")
    print(f"phase6_certification_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_certification_schema_summary_status={schema_summary['status']}")
    print(f"phase6_certification_cockpit_visibility_error_count={len(cockpit_visibility_errors)}")
    print(f"phase6_certification_source_mutation_count={len(mutated_refs)}")
    print(f"phase6_certification_next_stage={written['recommended_next_stage']}")
    print("phase6_certification_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_certification_error={error}")
        print("phase6_certification_check=failed")
        return 1

    print("phase6_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
