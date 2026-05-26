#!/usr/bin/env python3
"""Validate Q6-10 Knowledge Graph staged-write gate."""

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
from orchestrator.phase6_knowledge_graph_staging import (  # noqa: E402
    SOURCE_APPROVAL_REF,
    build_phase6_knowledge_graph_staging,
    phase6_knowledge_graph_staging_paths,
    validate_phase6_knowledge_graph_staging,
    write_phase6_knowledge_graph_staging,
)
from orchestrator.phase6_learning_approval import (  # noqa: E402
    validate_phase6_learning_approval,
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


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = [SOURCE_APPROVAL_REF]
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
            and not ref.startswith("data/runtime/phase6_knowledge_graph_staged_writes")
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


def _fake_entry() -> dict[str, object]:
    return {
        "staged_entry_id": "q6-10-kg-entry:probe",
        "entry_state": "staged_pending_commit_validation",
        "source_action_id": "q6-9-action:probe",
        "analysis_packet_type": "probe",
        "graph_namespace": "phase6_learning_memory",
        "graph_subject": "crude_oil_energy_security_disruption",
        "catalyst_taxonomy": {
            "taxonomy_version": "q6-10-v1",
            "node_type": "probe",
            "category": "probe",
            "strategy_family_key": "crude_oil_energy_security_disruption",
        },
        "outcome_classification": "useful",
        "confidence": 0.5,
        "approval_ref": SOURCE_APPROVAL_REF,
        "approval_event_log_ref": "data/runtime/phase6_learning_approval_ledger_events.jsonl",
        "source_refs": [SOURCE_APPROVAL_REF],
        "supersedes_ref": None,
        "supersession_id": "q6-10-supersession:probe:v1",
        "rollback_ref": "q6-10-rollback:probe:v1",
        "destructive_overwrite_allowed": False,
        "commit_allowed": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
    }


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    prebuilt = build_phase6_knowledge_graph_staging(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    output_path, history_path, event_log_path = phase6_knowledge_graph_staging_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    approval = _read_json(_repo_root(settings) / SOURCE_APPROVAL_REF)
    approval_errors = validate_phase6_learning_approval(approval) if approval else []

    output_path, history_path, event_log_path, written = write_phase6_knowledge_graph_staging(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_knowledge_graph_staging(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    staged_without_approval_probe = deepcopy(written)
    staged_without_approval_probe["status"] = "staged"
    staged_without_approval_probe["kg_write_state"] = "staged_entries_pending_commit_validation"
    staged_without_approval_probe["staged_write_allowed"] = True
    staged_without_approval_probe["knowledge_graph_staged_write_allowed"] = True
    staged_without_approval_probe["staged_entries"] = [_fake_entry()]
    staged_without_approval_probe["staged_entry_count"] = 1
    staged_without_approval_probe["approved_kg_action_count"] = 1
    staged_without_approval_probe["blocked_action_records"] = []
    staged_without_approval_probe["blocked_action_count"] = 0
    staged_without_approval_probe["missing_approval_blocks_staging"] = False
    staged_without_approval_errors = validate_phase6_knowledge_graph_staging(
        staged_without_approval_probe
    )

    missing_approval_probe = deepcopy(written)
    missing_approval_probe["missing_approval_blocks_staging"] = False
    missing_approval_errors = validate_phase6_knowledge_graph_staging(missing_approval_probe)

    kg_authority_probe = deepcopy(written)
    kg_authority_probe["phase6_knowledge_graph_write_allowed"] = True
    kg_authority_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    kg_authority_errors = validate_phase6_knowledge_graph_staging(kg_authority_probe)

    learning_authority_probe = deepcopy(written)
    learning_authority_probe["phase6_learning_write_allowed"] = True
    learning_authority_probe["phase6_learning_write_allowed_count"] = 1
    learning_authority_errors = validate_phase6_knowledge_graph_staging(
        learning_authority_probe
    )

    graph_commit_probe = deepcopy(written)
    graph_commit_probe["knowledge_graph_commit_allowed"] = True
    graph_commit_probe["actual_graph_commit_created"] = True
    graph_commit_probe["knowledge_graph_write_created"] = True
    graph_commit_errors = validate_phase6_knowledge_graph_staging(graph_commit_probe)

    chroma_probe = deepcopy(written)
    chroma_probe["chroma_write_allowed"] = True
    chroma_probe["graph_backend_write_allowed"] = True
    chroma_probe["chroma_write_created"] = True
    chroma_probe["graph_backend_write_created"] = True
    chroma_errors = validate_phase6_knowledge_graph_staging(chroma_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_knowledge_graph_staging(mutation_probe)

    destructive_probe = deepcopy(written)
    destructive_probe["destructive_overwrite_allowed"] = True
    destructive_errors = validate_phase6_knowledge_graph_staging(destructive_probe)

    missing_supersession_probe = deepcopy(staged_without_approval_probe)
    missing_supersession_probe["staged_entries"][0]["supersession_id"] = None
    missing_supersession_errors = validate_phase6_knowledge_graph_staging(
        missing_supersession_probe
    )

    entry_commit_probe = deepcopy(staged_without_approval_probe)
    entry_commit_probe["staged_entries"][0]["commit_allowed"] = True
    entry_commit_probe["staged_entries"][0]["knowledge_graph_write_created"] = True
    entry_commit_errors = validate_phase6_knowledge_graph_staging(entry_commit_probe)

    raw_payload_probe = deepcopy(staged_without_approval_probe)
    raw_payload_probe["staged_entries"][0]["raw_payload_copied"] = True
    raw_payload_probe["raw_payload_copied_count"] = 1
    raw_payload_errors = validate_phase6_knowledge_graph_staging(raw_payload_probe)

    payload_field_probe = deepcopy(staged_without_approval_probe)
    payload_field_probe["staged_entries"][0]["raw_payload"] = {"not_allowed": True}
    payload_field_errors = validate_phase6_knowledge_graph_staging(payload_field_probe)

    local_path_probe = deepcopy(staged_without_approval_probe)
    local_path_probe["staged_entries"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_knowledge_graph_staging(local_path_probe)

    blocked_action_payload_probe = deepcopy(written)
    blocked_action_payload_probe["blocked_action_records"][0]["raw_payload_copied"] = True
    blocked_action_payload_probe["raw_payload_copied_count"] = 1
    blocked_action_payload_errors = validate_phase6_knowledge_graph_staging(
        blocked_action_payload_probe
    )

    source_status_probe = deepcopy(written)
    source_status_probe["source_approval_status"] = "rejected"
    source_status_probe["source_approval_state"] = "rejected"
    source_status_errors = validate_phase6_knowledge_graph_staging(source_status_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_knowledge_graph_staging(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_knowledge_graph_staging(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_knowledge_graph_staging(phase5_proof_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_knowledge_graph_staging(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if approval_errors:
        errors.extend(approval_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_10_source_artifacts_mutated")
    if written["status"] != "blocked":
        errors.append("knowledge_graph_staging_status_not_blocked")
    if written["kg_write_state"] != "blocked_pending_learning_approval":
        errors.append("kg_write_state_not_blocked_pending_approval")
    if written["source_approval_state"] != "deferred":
        errors.append("source_approval_state_not_deferred")
    if written["source_approved_action_count"] != 0:
        errors.append("source_approved_action_count_nonzero")
    if written["candidate_action_count"] != 5:
        errors.append("candidate_action_count_invalid")
    if written["blocked_action_count"] != 5:
        errors.append("blocked_action_count_invalid")
    if written["staged_entry_count"] != 0:
        errors.append("staged_entry_count_nonzero")
    if written["staged_write_allowed"] is not False:
        errors.append("staged_write_allowed")
    if written["knowledge_graph_staged_write_allowed"] is not False:
        errors.append("knowledge_graph_staged_write_allowed")
    if written["missing_approval_blocks_staging"] is not True:
        errors.append("missing_approval_not_blocking_staging")
    if written["knowledge_graph_commit_allowed"] is not False:
        errors.append("knowledge_graph_commit_allowed")
    if written["chroma_write_allowed"] is not False:
        errors.append("chroma_write_allowed")
    if written["graph_backend_write_allowed"] is not False:
        errors.append("graph_backend_write_allowed")
    if written["learning_write_created"] is not False:
        errors.append("learning_write_created")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["actual_graph_commit_created"] is not False:
        errors.append("actual_graph_commit_created")
    if written["chroma_write_created"] is not False:
        errors.append("chroma_write_created")
    if written["graph_backend_write_created"] is not False:
        errors.append("graph_backend_write_created")
    if written["destructive_overwrite_allowed"] is not False:
        errors.append("destructive_overwrite_allowed")
    if written["supersession_required"] is not True:
        errors.append("supersession_not_required")
    if written["rollback_available"] is not True:
        errors.append("rollback_not_available")
    if written["raw_payload_copied_count"] != 0:
        errors.append("raw_payload_copied_count_nonzero")
    if written["private_payload_copied_count"] != 0:
        errors.append("private_payload_copied_count_nonzero")
    if written["local_path_exposed_count"] != 0:
        errors.append("local_path_exposed_count_nonzero")
    if written["secret_ref_exposed_count"] != 0:
        errors.append("secret_ref_exposed_count_nonzero")
    if written["phase5_source_artifacts_mutated"] is not False:
        errors.append("phase5_source_artifacts_mutated")
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] < 1:
        errors.append("blocker_count_missing")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "staged_entries_without_approval" not in staged_without_approval_errors:
        errors.append("staged_without_approval_probe_not_rejected")
    if "missing_approval_not_blocking_staging" not in missing_approval_errors:
        errors.append("missing_approval_probe_not_rejected")
    if "phase6_knowledge_graph_write_allowed" not in kg_authority_errors:
        errors.append("kg_authority_probe_not_rejected")
    if "phase6_learning_write_allowed" not in learning_authority_errors:
        errors.append("learning_authority_probe_not_rejected")
    if not _has_error(graph_commit_errors, "kg_staging_commit_or_write_enabled:"):
        errors.append("graph_commit_probe_not_rejected")
    if not _has_error(chroma_errors, "kg_staging_commit_or_write_enabled:"):
        errors.append("chroma_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "destructive_overwrite_allowed" not in destructive_errors:
        errors.append("destructive_probe_not_rejected")
    if not _has_error(missing_supersession_errors, "staged_entry_supersession_missing:"):
        errors.append("missing_supersession_probe_not_rejected")
    if not _has_error(entry_commit_errors, "staged_entry_commit_allowed:"):
        errors.append("entry_commit_probe_not_rejected")
    if not _has_error(entry_commit_errors, "staged_entry_write_created:"):
        errors.append("entry_write_probe_not_rejected")
    if not _has_error(raw_payload_errors, "staged_entry_raw_payload_copied:"):
        errors.append("raw_payload_probe_not_rejected")
    if not _has_error(payload_field_errors, "staged_entry_payload_field_forbidden:"):
        errors.append("payload_field_probe_not_rejected")
    if not _has_error(local_path_errors, "staged_entry:q6-10-kg-entry:probe_local_source_ref"):
        errors.append("local_path_probe_not_rejected")
    if not _has_error(blocked_action_payload_errors, "blocked_action_raw_payload_copied:"):
        errors.append("blocked_action_payload_probe_not_rejected")
    if "source_approval_status_invalid" not in source_status_errors:
        errors.append("source_status_probe_not_rejected")
    if "source_approval_state_invalid" not in source_status_errors:
        errors.append("source_state_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:phase5_source_artifacts_mutated" not in (
        phase5_mutation_errors
    ):
        errors.append("phase5_mutation_probe_not_rejected")
    if "knowledge_graph_staging_write_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(unsafe_errors, "knowledge_graph_staging_unsafe_count_nonzero:"):
        errors.append("unsafe_count_probe_not_rejected")

    print(f"phase6_knowledge_graph_staging_status={written['status']}")
    print(f"phase6_knowledge_graph_staging_artifact_path={output_path}")
    print(f"phase6_knowledge_graph_staging_history_path={history_path}")
    print(f"phase6_knowledge_graph_staging_event_log_path={event_log_path}")
    print(f"phase6_knowledge_graph_staging_kg_write_state={written['kg_write_state']}")
    print(f"phase6_knowledge_graph_staging_approval_ref={written['approval_ref']}")
    print(f"phase6_knowledge_graph_staging_source_approval_state={written['source_approval_state']}")
    print(
        "phase6_knowledge_graph_staging_source_approved_action_count="
        f"{written['source_approved_action_count']}"
    )
    print(f"phase6_knowledge_graph_staging_candidate_action_count={written['candidate_action_count']}")
    print(f"phase6_knowledge_graph_staging_blocked_action_count={written['blocked_action_count']}")
    print(f"phase6_knowledge_graph_staging_staged_entry_count={written['staged_entry_count']}")
    print(f"phase6_knowledge_graph_staging_staged_write_allowed={written['staged_write_allowed']}")
    print(
        "phase6_knowledge_graph_staging_knowledge_graph_staged_write_allowed="
        f"{written['knowledge_graph_staged_write_allowed']}"
    )
    print(
        "phase6_knowledge_graph_staging_missing_approval_blocks_staging="
        f"{written['missing_approval_blocks_staging']}"
    )
    print(
        "phase6_knowledge_graph_staging_knowledge_graph_commit_allowed="
        f"{written['knowledge_graph_commit_allowed']}"
    )
    print(f"phase6_knowledge_graph_staging_chroma_write_allowed={written['chroma_write_allowed']}")
    print(
        "phase6_knowledge_graph_staging_graph_backend_write_allowed="
        f"{written['graph_backend_write_allowed']}"
    )
    print(f"phase6_knowledge_graph_staging_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_knowledge_graph_staging_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_knowledge_graph_staging_actual_graph_commit_created="
        f"{written['actual_graph_commit_created']}"
    )
    print(f"phase6_knowledge_graph_staging_chroma_write_created={written['chroma_write_created']}")
    print(
        "phase6_knowledge_graph_staging_graph_backend_write_created="
        f"{written['graph_backend_write_created']}"
    )
    print(
        "phase6_knowledge_graph_staging_destructive_overwrite_allowed="
        f"{written['destructive_overwrite_allowed']}"
    )
    print(f"phase6_knowledge_graph_staging_supersession_required={written['supersession_required']}")
    print(f"phase6_knowledge_graph_staging_rollback_available={written['rollback_available']}")
    print(f"phase6_knowledge_graph_staging_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(
        "phase6_knowledge_graph_staging_private_payload_copied_count="
        f"{written['private_payload_copied_count']}"
    )
    print(f"phase6_knowledge_graph_staging_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_knowledge_graph_staging_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_knowledge_graph_staging_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_knowledge_graph_staging_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_knowledge_graph_staging_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_knowledge_graph_staging_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_knowledge_graph_staging_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_knowledge_graph_staging_blocker_count={written['blocker_count']}")
    print(f"phase6_knowledge_graph_staging_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_knowledge_graph_staging_validation_error_count={len(validation_errors)}")
    print(f"phase6_knowledge_graph_staging_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_knowledge_graph_staging_schema_summary_status={schema_summary['status']}")
    print(f"phase6_knowledge_graph_staging_approval_error_count={len(approval_errors)}")
    print(f"phase6_knowledge_graph_staging_next_stage={written['recommended_next_stage']}")
    print("phase6_knowledge_graph_staging_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_knowledge_graph_staging_error={error}")
        print("phase6_knowledge_graph_staging_check=failed")
        return 1

    print("phase6_knowledge_graph_staging_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
