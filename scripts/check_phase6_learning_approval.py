#!/usr/bin/env python3
"""Validate Q6-9 learning approval ledger."""

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
from orchestrator.phase6_learning_approval import (  # noqa: E402
    DOWNSTREAM_GATES,
    SOURCE_OUTCOME_LINK_REF,
    SOURCE_REVIEW_REF,
    build_phase6_learning_approval,
    explicitly_defer_phase6_learning_approval,
    phase6_learning_approval_paths,
    validate_phase6_learning_approval,
    write_phase6_learning_approval,
)
from orchestrator.phase6_outcome_linker import validate_phase6_outcome_linker  # noqa: E402
from orchestrator.phase6_postmortem_reducer import (  # noqa: E402
    validate_phase6_postmortem_reducer,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)

REVIEW_INSTRUCTION = (
    "Fund Manager instruction in the Codex thread on 2026-05-25: resolve or "
    "explicitly defer the pending Q6 learning approval/postmortem review. This "
    "check records explicit deferral only; it grants no learning-write, graph, "
    "model, trust, policy, broker, live-capital, or Phase 7 proof authority."
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = [SOURCE_REVIEW_REF, SOURCE_OUTCOME_LINK_REF]
    provenance = artifact.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str):
                refs.append(ref)
    return sorted(
        {
            ref
            for ref in refs
            if ref.startswith("data/runtime/")
            and not ref.startswith("data/runtime/phase6_learning_approval_ledger")
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
    prebuilt = explicitly_defer_phase6_learning_approval(
        build_phase6_learning_approval(settings=settings),
        reviewer_label="fund_manager_ramin",
        review_instruction=REVIEW_INSTRUCTION,
    )
    before_hashes = _file_hashes(settings, prebuilt)
    output_path, history_path, event_log_path = phase6_learning_approval_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    root = _repo_root(settings)
    review = _read_json(root / SOURCE_REVIEW_REF)
    outcome_link = _read_json(root / SOURCE_OUTCOME_LINK_REF)
    review_errors = validate_phase6_postmortem_reducer(review) if review else []
    outcome_link_errors = validate_phase6_outcome_linker(outcome_link) if outcome_link else []

    output_path, history_path, event_log_path, written = write_phase6_learning_approval(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_learning_approval(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    approved_probe = deepcopy(written)
    approved_probe["status"] = "approved"
    approved_probe["approval_state"] = "approved"
    approved_probe["approval_logged"] = False
    approved_probe["reviewer_label"] = None
    approved_probe["approval_event_log_ref"] = None
    approved_errors = validate_phase6_learning_approval(approved_probe)

    default_approval_probe = deepcopy(written)
    default_approval_probe["default_approval_exists"] = True
    default_approval_errors = validate_phase6_learning_approval(default_approval_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_learning_approval(learning_write_probe)

    kg_probe = deepcopy(written)
    kg_probe["knowledge_graph_staged_write_allowed"] = True
    kg_probe["knowledge_graph_write_created"] = True
    kg_probe["phase6_knowledge_graph_write_allowed"] = True
    kg_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    kg_errors = validate_phase6_learning_approval(kg_probe)

    proposal_probe = deepcopy(written)
    proposal_probe["model_weight_update_proposal_allowed"] = True
    proposal_probe["trust_score_update_proposal_allowed"] = True
    proposal_probe["strategy_learning_proposal_allowed"] = True
    proposal_probe["phase6_model_weight_update_allowed"] = True
    proposal_probe["phase6_model_weight_update_allowed_count"] = 1
    proposal_probe["phase6_trust_score_update_allowed"] = True
    proposal_probe["phase6_trust_score_update_allowed_count"] = 1
    proposal_probe["phase6_shadow_strategy_runner_allowed"] = True
    proposal_probe["phase6_shadow_strategy_runner_allowed_count"] = 1
    proposal_errors = validate_phase6_learning_approval(proposal_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_learning_approval(mutation_probe)

    downstream_probe = deepcopy(written)
    downstream_probe["downstream_advance_allowed"] = True
    downstream_probe["missing_approval_blocks_downstream"] = False
    downstream_errors = validate_phase6_learning_approval(downstream_probe)

    missing_deferred_probe = deepcopy(written)
    missing_deferred_probe["deferred_actions"] = missing_deferred_probe["deferred_actions"][1:]
    missing_deferred_probe["deferred_action_count"] = len(
        missing_deferred_probe["deferred_actions"]
    )
    missing_deferred_errors = validate_phase6_learning_approval(missing_deferred_probe)

    action_approved_probe = deepcopy(written)
    action_approved_probe["proposed_actions"][0]["approval_decision"] = "approved"
    action_approved_probe["proposed_actions"][0]["learning_action_approved"] = True
    action_approved_errors = validate_phase6_learning_approval(action_approved_probe)

    action_gate_probe = deepcopy(written)
    action_gate_probe["proposed_actions"][0]["knowledge_graph_staged_write_allowed"] = True
    action_gate_errors = validate_phase6_learning_approval(action_gate_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["proposed_actions"][0]["raw_payload_copied"] = True
    raw_payload_probe["raw_payload_copied_count"] = 1
    raw_payload_errors = validate_phase6_learning_approval(raw_payload_probe)

    payload_field_probe = deepcopy(written)
    payload_field_probe["proposed_actions"][0]["raw_payload"] = {"not_allowed": True}
    payload_field_errors = validate_phase6_learning_approval(payload_field_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["proposed_actions"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_learning_approval(local_path_probe)

    source_status_probe = deepcopy(written)
    source_status_probe["source_review_state"] = "approved"
    source_status_probe["source_outcome_link_status"] = "blocked"
    source_status_errors = validate_phase6_learning_approval(source_status_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_learning_approval(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_learning_approval(phase5_proof_probe)

    source_mutation_probe = deepcopy(written)
    source_mutation_probe["phase5_source_artifacts_mutated"] = True
    source_mutation_errors = validate_phase6_learning_approval(source_mutation_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_learning_approval(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if review_errors:
        errors.extend(review_errors)
    if outcome_link_errors:
        errors.extend(outcome_link_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_9_source_artifacts_mutated")
    if written["status"] != "deferred":
        errors.append("learning_approval_status_not_deferred")
    if written["approval_state"] != "deferred":
        errors.append("approval_state_not_deferred")
    if written["approval_logged"] is not True:
        errors.append("approval_not_logged")
    if written["reviewer_label"] != "fund_manager_ramin":
        errors.append("reviewer_label_missing")
    if not written["approval_event_log_ref"]:
        errors.append("approval_event_log_ref_missing")
    if written["default_approval_exists"] is not False:
        errors.append("default_approval_exists")
    if written["missing_approval_blocks_downstream"] is not True:
        errors.append("missing_approval_not_blocking_downstream")
    if written["proposed_action_count"] != 5:
        errors.append("proposed_action_count_invalid")
    if written["approved_action_count"] != 0:
        errors.append("approved_action_count_nonzero")
    if written["rejected_action_count"] != 0:
        errors.append("rejected_action_count_nonzero")
    if written["deferred_action_count"] != 5:
        errors.append("deferred_action_count_invalid")
    if written["pending_review_action_count"] != 0:
        errors.append("pending_review_action_count_nonzero")
    if written["learning_action_count"] != 0:
        errors.append("learning_action_count_nonzero")
    if written["learning_action_approved_count"] != 0:
        errors.append("learning_action_approved_count_nonzero")
    if written["downstream_advance_allowed"] is not False:
        errors.append("downstream_advance_allowed")
    if written["downstream_blocked_gate_count"] != len(DOWNSTREAM_GATES):
        errors.append("downstream_blocked_gate_count_invalid")
    if set(written["downstream_blocked_gates"]) != set(DOWNSTREAM_GATES):
        errors.append("downstream_blocked_gates_invalid")
    if written["knowledge_graph_staged_write_allowed"] is not False:
        errors.append("knowledge_graph_staged_write_allowed")
    if written["model_weight_update_proposal_allowed"] is not False:
        errors.append("model_weight_update_proposal_allowed")
    if written["trust_score_update_proposal_allowed"] is not False:
        errors.append("trust_score_update_proposal_allowed")
    if written["strategy_learning_proposal_allowed"] is not False:
        errors.append("strategy_learning_proposal_allowed")
    if written["postmortem_approved"] is not False:
        errors.append("postmortem_approved")
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
    if written["raw_payload_copied_count"] != 0:
        errors.append("raw_payload_copied_count_nonzero")
    if written["private_payload_copied_count"] != 0:
        errors.append("private_payload_copied_count_nonzero")
    if written["local_path_exposed_count"] != 0:
        errors.append("local_path_exposed_count_nonzero")
    if written["secret_ref_exposed_count"] != 0:
        errors.append("secret_ref_exposed_count_nonzero")
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("learning_approval_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "approval_without_event_log" not in approved_errors:
        errors.append("approved_event_log_probe_not_rejected")
    if "approval_without_reviewer" not in approved_errors:
        errors.append("approved_reviewer_probe_not_rejected")
    if "approval_event_log_ref_missing" not in approved_errors:
        errors.append("approved_event_ref_probe_not_rejected")
    if "default_approval_exists" not in default_approval_errors:
        errors.append("default_approval_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if "learning_approval_write_enabled:learning_write_created" not in learning_write_errors:
        errors.append("learning_write_created_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if "knowledge_graph_staged_write_allowed" not in kg_errors:
        errors.append("kg_staged_probe_not_rejected")
    if "learning_approval_write_enabled:knowledge_graph_write_created" not in kg_errors:
        errors.append("kg_write_created_probe_not_rejected")
    if "authority_enabled:phase6_knowledge_graph_write_allowed" not in kg_errors:
        errors.append("kg_authority_probe_not_rejected")
    if "model_weight_update_proposal_allowed" not in proposal_errors:
        errors.append("model_proposal_probe_not_rejected")
    if "trust_score_update_proposal_allowed" not in proposal_errors:
        errors.append("trust_proposal_probe_not_rejected")
    if "strategy_learning_proposal_allowed" not in proposal_errors:
        errors.append("strategy_proposal_probe_not_rejected")
    if "authority_enabled:phase6_model_weight_update_allowed" not in proposal_errors:
        errors.append("model_authority_probe_not_rejected")
    if "authority_enabled:phase6_trust_score_update_allowed" not in proposal_errors:
        errors.append("trust_authority_probe_not_rejected")
    if "authority_enabled:phase6_shadow_strategy_runner_allowed" not in proposal_errors:
        errors.append("strategy_runner_authority_probe_not_rejected")
    if "learning_approval_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_update_probe_not_rejected")
    if "learning_approval_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_update_probe_not_rejected")
    if "learning_approval_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "learning_approval_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "downstream_advance_allowed" not in downstream_errors:
        errors.append("downstream_advance_probe_not_rejected")
    if "missing_approval_not_blocking_downstream" not in downstream_errors:
        errors.append("missing_approval_block_probe_not_rejected")
    if "deferred_action_count_invalid" not in missing_deferred_errors:
        errors.append("missing_deferred_probe_not_rejected")
    if not _has_error(action_approved_errors, "action_default_approved:"):
        errors.append("action_default_approved_probe_not_rejected")
    if not _has_error(action_approved_errors, "action_learning_approved:"):
        errors.append("action_learning_approved_probe_not_rejected")
    if not _has_error(action_gate_errors, "action_downstream_gate_allowed:"):
        errors.append("action_gate_probe_not_rejected")
    if not _has_error(raw_payload_errors, "action_raw_payload_copied:"):
        errors.append("raw_payload_probe_not_rejected")
    if not _has_error(payload_field_errors, "action_payload_field_forbidden:"):
        errors.append("payload_field_probe_not_rejected")
    if not _has_error(local_path_errors, "action:q6-9-action:catalyst_analysis_local_source_ref"):
        errors.append("local_path_probe_not_rejected")
    if "source_review_state_invalid" not in source_status_errors:
        errors.append("source_review_state_probe_not_rejected")
    if "source_outcome_link_status_invalid" not in source_status_errors:
        errors.append("source_outcome_link_probe_not_rejected")
    if "learning_approval_write_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if "learning_approval_write_enabled:phase5_source_artifacts_mutated" not in (
        source_mutation_errors
    ):
        errors.append("source_mutation_probe_not_rejected")
    if not _has_error(unsafe_errors, "learning_approval_unsafe_count_nonzero:"):
        errors.append("unsafe_count_probe_not_rejected")

    print(f"phase6_learning_approval_status={written['status']}")
    print(f"phase6_learning_approval_artifact_path={output_path}")
    print(f"phase6_learning_approval_history_path={history_path}")
    print(f"phase6_learning_approval_event_log_path={event_log_path}")
    print(f"phase6_learning_approval_approval_state={written['approval_state']}")
    print(f"phase6_learning_approval_approval_logged={written['approval_logged']}")
    print(f"phase6_learning_approval_reviewer_label={written['reviewer_label']}")
    print(f"phase6_learning_approval_default_approval_exists={written['default_approval_exists']}")
    print(
        "phase6_learning_approval_missing_approval_blocks_downstream="
        f"{written['missing_approval_blocks_downstream']}"
    )
    print(f"phase6_learning_approval_source_review_state={written['source_review_state']}")
    print(
        "phase6_learning_approval_source_outcome_link_status="
        f"{written['source_outcome_link_status']}"
    )
    print(f"phase6_learning_approval_proposed_action_count={written['proposed_action_count']}")
    print(f"phase6_learning_approval_approved_action_count={written['approved_action_count']}")
    print(f"phase6_learning_approval_rejected_action_count={written['rejected_action_count']}")
    print(f"phase6_learning_approval_deferred_action_count={written['deferred_action_count']}")
    print(
        "phase6_learning_approval_pending_review_action_count="
        f"{written['pending_review_action_count']}"
    )
    print(f"phase6_learning_approval_learning_action_count={written['learning_action_count']}")
    print(
        "phase6_learning_approval_learning_action_approved_count="
        f"{written['learning_action_approved_count']}"
    )
    print(f"phase6_learning_approval_downstream_advance_allowed={written['downstream_advance_allowed']}")
    print(
        "phase6_learning_approval_downstream_blocked_gate_count="
        f"{written['downstream_blocked_gate_count']}"
    )
    print(
        "phase6_learning_approval_knowledge_graph_staged_write_allowed="
        f"{written['knowledge_graph_staged_write_allowed']}"
    )
    print(
        "phase6_learning_approval_model_weight_update_proposal_allowed="
        f"{written['model_weight_update_proposal_allowed']}"
    )
    print(
        "phase6_learning_approval_trust_score_update_proposal_allowed="
        f"{written['trust_score_update_proposal_allowed']}"
    )
    print(
        "phase6_learning_approval_strategy_learning_proposal_allowed="
        f"{written['strategy_learning_proposal_allowed']}"
    )
    print(f"phase6_learning_approval_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_learning_approval_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_learning_approval_model_weight_update_created="
        f"{written['model_weight_update_created']}"
    )
    print(
        "phase6_learning_approval_trust_score_update_created="
        f"{written['trust_score_update_created']}"
    )
    print(f"phase6_learning_approval_policy_mutation_created={written['policy_mutation_created']}")
    print(
        "phase6_learning_approval_strategy_mutation_created="
        f"{written['strategy_mutation_created']}"
    )
    print(f"phase6_learning_approval_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(
        "phase6_learning_approval_private_payload_copied_count="
        f"{written['private_payload_copied_count']}"
    )
    print(f"phase6_learning_approval_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_learning_approval_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_learning_approval_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_learning_approval_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_learning_approval_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_learning_approval_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_learning_approval_blocker_count={written['blocker_count']}")
    print(f"phase6_learning_approval_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_learning_approval_validation_error_count={len(validation_errors)}")
    print(f"phase6_learning_approval_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_learning_approval_schema_summary_status={schema_summary['status']}")
    print(f"phase6_learning_approval_review_error_count={len(review_errors)}")
    print(f"phase6_learning_approval_outcome_link_error_count={len(outcome_link_errors)}")
    print(f"phase6_learning_approval_next_stage={written['recommended_next_stage']}")
    print("phase6_learning_approval_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_learning_approval_error={error}")
        print("phase6_learning_approval_check=failed")
        return 1

    print("phase6_learning_approval_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
