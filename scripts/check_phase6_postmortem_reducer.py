#!/usr/bin/env python3
"""Validate Q6-7 postmortem reducer and review gate."""

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
from orchestrator.phase6_postmortem_analysis import (  # noqa: E402
    validate_phase6_postmortem_analysis,
)
from orchestrator.phase6_postmortem_reducer import (  # noqa: E402
    CLASSIFICATION_OPTIONS,
    GOVERNANCE_STATES,
    SOURCE_ANALYSIS_REF,
    build_phase6_postmortem_reducer,
    phase6_postmortem_reducer_paths,
    validate_phase6_postmortem_reducer,
    write_phase6_postmortem_reducer,
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
    return json.loads(path.read_text(encoding="utf-8"))


def _source_refs(settings: Settings) -> list[str]:
    root = _repo_root(settings)
    refs = [SOURCE_ANALYSIS_REF]
    analysis = _read_json(root / SOURCE_ANALYSIS_REF)
    provenance = analysis.get("provenance", {}) if isinstance(analysis, dict) else {}
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str):
                refs.append(ref)
    for ref in (
        analysis.get("source_postmortem_draft_ref") if isinstance(analysis, dict) else None,
        analysis.get("postmortem_draft_ref") if isinstance(analysis, dict) else None,
    ):
        if isinstance(ref, str):
            refs.append(ref)
    return sorted(
        {
            ref
            for ref in refs
            if ref.startswith("data/runtime/")
            and not ref.startswith("data/runtime/phase6_postmortem_reduced_review")
        }
    )


def _file_hashes(settings: Settings) -> dict[str, str | None]:
    root = _repo_root(settings)
    hashes: dict[str, str | None] = {}
    for ref in _source_refs(settings):
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
    before_hashes = _file_hashes(settings)
    output_path, history_path, event_log_path = phase6_postmortem_reducer_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    root = _repo_root(settings)
    analysis = _read_json(root / SOURCE_ANALYSIS_REF)
    analysis_errors = validate_phase6_postmortem_analysis(analysis) if analysis else []

    artifact = build_phase6_postmortem_reducer(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_postmortem_reducer(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_postmortem_reducer(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    approved_without_reviewer_probe = deepcopy(written)
    approved_without_reviewer_probe["status"] = "approved"
    approved_without_reviewer_probe["review_state"] = "approved"
    approved_without_reviewer_probe["governance_state"] = "approved"
    approved_without_reviewer_probe["approval_state"] = "approved"
    approved_without_reviewer_probe["postmortem_approved"] = True
    approved_without_reviewer_probe["event_log_written"] = False
    approved_without_reviewer_probe["event_log_correlation_id"] = None
    approved_without_reviewer_errors = validate_phase6_postmortem_reducer(
        approved_without_reviewer_probe
    )

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_postmortem_reducer(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_postmortem_reducer(knowledge_graph_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_postmortem_reducer(mutation_probe)

    write_allowed_probe = deepcopy(written)
    write_allowed_probe["write_allowed"] = True
    write_allowed_errors = validate_phase6_postmortem_reducer(write_allowed_probe)

    missing_reduced_probe = deepcopy(written)
    missing_reduced_probe["reduced_postmortem_created"] = False
    missing_reduced_probe["classification_records"] = []
    missing_reduced_probe["classification_record_count"] = 0
    missing_reduced_errors = validate_phase6_postmortem_reducer(missing_reduced_probe)

    invalid_classification_probe = deepcopy(written)
    invalid_classification_probe["classification_records"][0]["classification"] = "invented"
    invalid_classification_errors = validate_phase6_postmortem_reducer(
        invalid_classification_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["classification_records"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_postmortem_reducer(local_path_probe)

    reviewer_probe = deepcopy(written)
    reviewer_probe["reviewer_label"] = "Fund Manager"
    reviewer_probe["review_queue"][0]["reviewer_label"] = "Fund Manager"
    reviewer_errors = validate_phase6_postmortem_reducer(reviewer_probe)

    learning_action_probe = deepcopy(written)
    learning_action_probe["learning_action_count"] = 1
    learning_action_probe["learning_action_approved_count"] = 1
    learning_action_probe["classification_records"][0]["learning_action_approved"] = True
    learning_action_errors = validate_phase6_postmortem_reducer(learning_action_probe)

    review_queue_learning_action_probe = deepcopy(written)
    review_queue_learning_action_probe["review_queue"][0]["learning_action_approved"] = True
    review_queue_learning_action_errors = validate_phase6_postmortem_reducer(
        review_queue_learning_action_probe
    )

    llm_probe = deepcopy(written)
    llm_probe["llm_used"] = True
    llm_errors = validate_phase6_postmortem_reducer(llm_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_postmortem_reducer(proof_credit_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if analysis_errors:
        errors.extend(analysis_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_7_source_artifacts_mutated")
    if written["status"] != "pending_review":
        errors.append("postmortem_reducer_status_not_pending_review")
    if written["review_state"] != "review_required":
        errors.append("review_state_not_required")
    if written["governance_state"] != "review_required":
        errors.append("governance_state_not_required")
    if set(written["governance_states"]) != set(GOVERNANCE_STATES):
        errors.append("governance_states_invalid")
    if set(written["classification_options"]) != set(CLASSIFICATION_OPTIONS):
        errors.append("classification_options_invalid")
    if written["reduced_postmortem_created"] is not True:
        errors.append("reduced_postmortem_not_created")
    if written["classification_record_count"] != 5:
        errors.append("classification_record_count_invalid")
    if written["review_queue_count"] != 5:
        errors.append("review_queue_count_invalid")
    if written["useful_classification_count"] != 2:
        errors.append("useful_classification_count_invalid")
    if written["harmful_classification_count"] != 0:
        errors.append("harmful_classification_count_invalid")
    if written["neutral_classification_count"] != 1:
        errors.append("neutral_classification_count_invalid")
    if written["untestable_classification_count"] != 2:
        errors.append("untestable_classification_count_invalid")
    if written["postmortem_approved"] is not False:
        errors.append("postmortem_approved")
    if written["approval_state"] != "not_requested":
        errors.append("approval_state_not_requested")
    if written["approval_logged"] is not False:
        errors.append("approval_logged")
    if written["reviewer_label"] is not None:
        errors.append("reviewer_label_set")
    if written["write_allowed"] is not False:
        errors.append("write_allowed")
    if written["learning_action_count"] != 0:
        errors.append("learning_action_count_nonzero")
    if written["learning_action_approved_count"] != 0:
        errors.append("learning_action_approved_count_nonzero")
    if written["learning_write_allowed"] is not False:
        errors.append("learning_write_allowed")
    if written["learning_write_created"] is not False:
        errors.append("learning_write_created")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["model_weight_update_created"] is not False:
        errors.append("model_weight_update_created")
    if written["trust_score_update_created"] is not False:
        errors.append("trust_score_update_created")
    if written["policy_mutation_created"] is not False:
        errors.append("policy_mutation_created")
    if written["strategy_mutation_created"] is not False:
        errors.append("strategy_mutation_created")
    if written["llm_used"] is not False:
        errors.append("llm_used")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("postmortem_reducer_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "postmortem_approved_before_review" not in approved_without_reviewer_errors:
        errors.append("approved_probe_not_rejected")
    if "approved_without_reviewer" not in approved_without_reviewer_errors:
        errors.append("approved_without_reviewer_probe_not_rejected")
    if "approved_without_event_log" not in approved_without_reviewer_errors:
        errors.append("approved_without_event_log_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if "postmortem_reducer_write_enabled:learning_write_created" not in learning_write_errors:
        errors.append("learning_write_created_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if (
        "postmortem_reducer_write_enabled:knowledge_graph_write_created"
        not in knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "postmortem_reducer_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_probe_not_rejected")
    if "postmortem_reducer_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_probe_not_rejected")
    if "postmortem_reducer_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "postmortem_reducer_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "write_allowed" not in write_allowed_errors:
        errors.append("write_allowed_probe_not_rejected")
    if "reduced_postmortem_not_created" not in missing_reduced_errors:
        errors.append("missing_reduced_probe_not_rejected")
    if "classification_record_count_invalid" not in missing_reduced_errors:
        errors.append("missing_classifications_probe_not_rejected")
    if not _has_error(invalid_classification_errors, "classification_invalid:"):
        errors.append("invalid_classification_probe_not_rejected")
    if not _has_error(local_path_errors, "classification_record:catalyst_analysis_local_source_ref"):
        errors.append("local_path_probe_not_rejected")
    if "reviewer_label_set_before_review" not in reviewer_errors:
        errors.append("reviewer_probe_not_rejected")
    if "review_queue_reviewer_set_before_review" not in reviewer_errors:
        errors.append("review_queue_reviewer_probe_not_rejected")
    if "learning_action_count_nonzero" not in learning_action_errors:
        errors.append("learning_action_count_probe_not_rejected")
    if not _has_error(learning_action_errors, "classification_learning_action_approved:"):
        errors.append("classification_learning_action_probe_not_rejected")
    if "review_queue_learning_action_approved" not in review_queue_learning_action_errors:
        errors.append("review_queue_learning_action_probe_not_rejected")
    if "llm_used" not in llm_errors:
        errors.append("llm_probe_not_rejected")
    if "postmortem_reducer_write_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_probe_not_rejected")

    print(f"phase6_postmortem_reducer_status={written['status']}")
    print(f"phase6_postmortem_reducer_artifact_path={output_path}")
    print(f"phase6_postmortem_reducer_history_path={history_path}")
    print(f"phase6_postmortem_reducer_event_log_path={event_log_path}")
    print(f"phase6_postmortem_reducer_review_state={written['review_state']}")
    print(f"phase6_postmortem_reducer_governance_state={written['governance_state']}")
    print(f"phase6_postmortem_reducer_reduced_postmortem_created={written['reduced_postmortem_created']}")
    print(f"phase6_postmortem_reducer_classification_record_count={written['classification_record_count']}")
    print(f"phase6_postmortem_reducer_useful_classification_count={written['useful_classification_count']}")
    print(f"phase6_postmortem_reducer_harmful_classification_count={written['harmful_classification_count']}")
    print(f"phase6_postmortem_reducer_neutral_classification_count={written['neutral_classification_count']}")
    print(f"phase6_postmortem_reducer_untestable_classification_count={written['untestable_classification_count']}")
    print(f"phase6_postmortem_reducer_review_queue_count={written['review_queue_count']}")
    print(f"phase6_postmortem_reducer_postmortem_approved={written['postmortem_approved']}")
    print(f"phase6_postmortem_reducer_approval_state={written['approval_state']}")
    print(f"phase6_postmortem_reducer_approval_logged={written['approval_logged']}")
    print(f"phase6_postmortem_reducer_reviewer_label={written['reviewer_label']}")
    print(f"phase6_postmortem_reducer_write_allowed={written['write_allowed']}")
    print(f"phase6_postmortem_reducer_learning_action_count={written['learning_action_count']}")
    print(
        "phase6_postmortem_reducer_learning_action_approved_count="
        f"{written['learning_action_approved_count']}"
    )
    print(f"phase6_postmortem_reducer_proposed_learning_action_count={written['proposed_learning_action_count']}")
    print(f"phase6_postmortem_reducer_llm_used={written['llm_used']}")
    print(f"phase6_postmortem_reducer_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_postmortem_reducer_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_postmortem_reducer_model_weight_update_created="
        f"{written['model_weight_update_created']}"
    )
    print(
        "phase6_postmortem_reducer_trust_score_update_created="
        f"{written['trust_score_update_created']}"
    )
    print(f"phase6_postmortem_reducer_policy_mutation_created={written['policy_mutation_created']}")
    print(
        "phase6_postmortem_reducer_strategy_mutation_created="
        f"{written['strategy_mutation_created']}"
    )
    print(f"phase6_postmortem_reducer_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_postmortem_reducer_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_postmortem_reducer_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_postmortem_reducer_blocker_count={written['blocker_count']}")
    print(
        "phase6_postmortem_reducer_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(f"phase6_postmortem_reducer_validation_error_count={len(validation_errors)}")
    print(f"phase6_postmortem_reducer_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_postmortem_reducer_schema_summary_status={schema_summary['status']}")
    print(f"phase6_postmortem_reducer_analysis_error_count={len(analysis_errors)}")
    print(f"phase6_postmortem_reducer_next_stage={written['recommended_next_stage']}")
    print("phase6_postmortem_reducer_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_postmortem_reducer_error={error}")
        print("phase6_postmortem_reducer_check=failed")
        return 1

    print("phase6_postmortem_reducer_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
