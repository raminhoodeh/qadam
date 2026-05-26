#!/usr/bin/env python3
"""Validate Q6-11 Knowledge Graph read path."""

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
from orchestrator.phase6_knowledge_graph_read_path import (  # noqa: E402
    SOURCE_STAGING_REF,
    build_phase6_knowledge_graph_read_path,
    phase6_knowledge_graph_read_path_paths,
    search_phase6_knowledge_graph_read_path,
    validate_phase6_knowledge_graph_read_path,
    write_phase6_knowledge_graph_read_path,
)
from orchestrator.phase6_knowledge_graph_staging import (  # noqa: E402
    validate_phase6_knowledge_graph_staging,
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
    refs: list[str] = [SOURCE_STAGING_REF]
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
            and not ref.startswith("data/runtime/phase6_knowledge_graph_read_view")
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
    prebuilt = build_phase6_knowledge_graph_read_path(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    output_path, history_path, event_log_path = phase6_knowledge_graph_read_path_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    staging = _read_json(_repo_root(settings) / SOURCE_STAGING_REF)
    staging_errors = validate_phase6_knowledge_graph_staging(staging) if staging else []

    output_path, history_path, event_log_path, written = write_phase6_knowledge_graph_read_path(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_knowledge_graph_read_path(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    write_probe = deepcopy(written)
    write_probe["write_allowed"] = True
    write_errors = validate_phase6_knowledge_graph_read_path(write_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_errors = validate_phase6_knowledge_graph_read_path(learning_write_probe)

    kg_write_probe = deepcopy(written)
    kg_write_probe["phase6_knowledge_graph_write_allowed"] = True
    kg_write_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    kg_write_probe["knowledge_graph_write_created"] = True
    kg_write_errors = validate_phase6_knowledge_graph_read_path(kg_write_probe)

    commit_probe = deepcopy(written)
    commit_probe["knowledge_graph_commit_created"] = True
    commit_probe["chroma_write_created"] = True
    commit_probe["graph_backend_write_created"] = True
    commit_errors = validate_phase6_knowledge_graph_read_path(commit_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_knowledge_graph_read_path(mutation_probe)

    result_raw_probe = deepcopy(written)
    result_raw_probe["read_results"][0]["raw_payload_copied"] = True
    result_raw_probe["raw_payload_copied_count"] = 1
    result_raw_errors = validate_phase6_knowledge_graph_read_path(result_raw_probe)

    result_payload_probe = deepcopy(written)
    result_payload_probe["read_results"][0]["raw_payload"] = {"not_allowed": True}
    result_payload_errors = validate_phase6_knowledge_graph_read_path(result_payload_probe)

    result_local_path_probe = deepcopy(written)
    result_local_path_probe["read_results"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    result_local_path_errors = validate_phase6_knowledge_graph_read_path(result_local_path_probe)

    result_write_probe = deepcopy(written)
    result_write_probe["read_results"][0]["write_allowed"] = True
    result_write_probe["read_results"][0]["mutation_allowed"] = True
    result_write_probe["read_results"][0]["commit_allowed"] = True
    result_write_errors = validate_phase6_knowledge_graph_read_path(result_write_probe)

    result_reference_probe = deepcopy(written)
    result_reference_probe["read_results"][0]["reference_only"] = False
    result_reference_errors = validate_phase6_knowledge_graph_read_path(result_reference_probe)

    source_status_probe = deepcopy(written)
    source_status_probe["source_staging_status"] = "error"
    source_status_probe["source_approval_state"] = "rejected"
    source_status_errors = validate_phase6_knowledge_graph_read_path(source_status_probe)

    search_probe = deepcopy(written)
    search_probe["search_enabled"] = False
    search_probe["search_result_count_by_query"]["crude oil"] = 0
    search_errors = validate_phase6_knowledge_graph_read_path(search_probe)

    count_probe = deepcopy(written)
    count_probe["result_count"] = 0
    count_errors = validate_phase6_knowledge_graph_read_path(count_probe)

    cockpit_probe = deepcopy(written)
    cockpit_probe["cockpit_safe_status"]["source_refs"] = ["data/runtime/private.json"]
    cockpit_errors = validate_phase6_knowledge_graph_read_path(cockpit_probe)

    cockpit_mismatch_probe = deepcopy(written)
    cockpit_mismatch_probe["cockpit_safe_status"]["result_count"] = 999
    cockpit_mismatch_errors = validate_phase6_knowledge_graph_read_path(cockpit_mismatch_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_knowledge_graph_read_path(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_knowledge_graph_read_path(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_knowledge_graph_read_path(phase5_proof_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_knowledge_graph_read_path(unsafe_probe)

    crude_results = search_phase6_knowledge_graph_read_path(written, "crude oil")
    paper_results = search_phase6_knowledge_graph_read_path(written, "paper lifecycle")

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if staging_errors:
        errors.extend(staging_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_11_source_artifacts_mutated")
    if written["status"] != "read_only":
        errors.append("knowledge_graph_read_path_status_not_read_only")
    if written["read_view_state"] != "read_only_seed_context_available":
        errors.append("read_view_state_not_seed_context")
    if written["source_staging_status"] != "blocked":
        errors.append("source_staging_status_not_blocked")
    if written["source_approval_state"] != "deferred":
        errors.append("source_approval_state_not_deferred")
    if written["source_staged_entry_count"] != 0:
        errors.append("source_staged_entry_count_nonzero")
    if written["source_blocked_action_count"] != 5:
        errors.append("source_blocked_action_count_invalid")
    if written["result_count"] != 1:
        errors.append("result_count_invalid")
    if written["seed_result_count"] != 1:
        errors.append("seed_result_count_invalid")
    if written["staged_result_count"] != 0:
        errors.append("staged_result_count_nonzero")
    if written["approved_learning_entry_count"] != 0:
        errors.append("approved_learning_entry_count_nonzero")
    if written["search_enabled"] is not True:
        errors.append("search_not_enabled")
    if len(crude_results) != 1:
        errors.append("crude_oil_search_count_invalid")
    if len(paper_results) != 1:
        errors.append("paper_lifecycle_search_count_invalid")
    if crude_results and crude_results[0].get("raw_payload_copied") is not False:
        errors.append("crude_search_raw_payload_copied")
    if crude_results and crude_results[0].get("seed_context") is not True:
        errors.append("crude_search_seed_context_missing")
    if written["write_allowed"] is not False:
        errors.append("write_allowed")
    if written["learning_write_created"] is not False:
        errors.append("learning_write_created")
    if written["knowledge_graph_write_created"] is not False:
        errors.append("knowledge_graph_write_created")
    if written["knowledge_graph_commit_created"] is not False:
        errors.append("knowledge_graph_commit_created")
    if written["chroma_write_created"] is not False:
        errors.append("chroma_write_created")
    if written["graph_backend_write_created"] is not False:
        errors.append("graph_backend_write_created")
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
    if written["blocker_count"] != 0:
        errors.append("blocker_count_nonzero")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "write_allowed" not in write_errors:
        errors.append("write_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_authority_probe_not_rejected")
    if "authority_enabled:phase6_knowledge_graph_write_allowed" not in kg_write_errors:
        errors.append("kg_authority_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:knowledge_graph_write_created" not in (
        kg_write_errors
    ):
        errors.append("kg_write_created_probe_not_rejected")
    if not _has_error(commit_errors, "knowledge_graph_read_path_write_enabled:"):
        errors.append("commit_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:model_weight_update_created" not in (
        mutation_errors
    ):
        errors.append("model_weight_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:trust_score_update_created" not in (
        mutation_errors
    ):
        errors.append("trust_score_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:policy_mutation_created" not in (
        mutation_errors
    ):
        errors.append("policy_mutation_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:strategy_mutation_created" not in (
        mutation_errors
    ):
        errors.append("strategy_mutation_probe_not_rejected")
    if not _has_error(result_raw_errors, "read_result_raw_payload_copied:"):
        errors.append("result_raw_payload_probe_not_rejected")
    if not _has_error(result_payload_errors, "read_result_payload_field_forbidden:"):
        errors.append("result_payload_field_probe_not_rejected")
    if not _has_error(
        result_local_path_errors,
        "read_result:q6-11-read:q5e-seed-context:crude_oil_energy_security_disruption_local_source_ref",
    ):
        errors.append("result_local_path_probe_not_rejected")
    if not _has_error(result_write_errors, "read_result_write_or_mutation_allowed:"):
        errors.append("result_write_probe_not_rejected")
    if not _has_error(result_reference_errors, "read_result_not_reference_only:"):
        errors.append("result_reference_probe_not_rejected")
    if "source_staging_status_invalid" not in source_status_errors:
        errors.append("source_staging_status_probe_not_rejected")
    if "source_approval_state_invalid" not in source_status_errors:
        errors.append("source_approval_state_probe_not_rejected")
    if "search_not_enabled" not in search_errors:
        errors.append("search_enabled_probe_not_rejected")
    if "search_query_count_invalid:crude oil" not in search_errors:
        errors.append("search_count_probe_not_rejected")
    if "result_count_mismatch" not in count_errors:
        errors.append("count_probe_not_rejected")
    if "cockpit_safe_status_unexpected_fields:source_refs" not in cockpit_errors:
        errors.append("cockpit_forbidden_probe_not_rejected")
    if "cockpit_safe_status_mismatch:result_count" not in cockpit_mismatch_errors:
        errors.append("cockpit_mismatch_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:phase5_source_artifacts_mutated" not in (
        phase5_mutation_errors
    ):
        errors.append("phase5_mutation_probe_not_rejected")
    if "knowledge_graph_read_path_write_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(unsafe_errors, "knowledge_graph_read_path_unsafe_count_nonzero:"):
        errors.append("unsafe_count_probe_not_rejected")

    print(f"phase6_knowledge_graph_read_path_status={written['status']}")
    print(f"phase6_knowledge_graph_read_path_artifact_path={output_path}")
    print(f"phase6_knowledge_graph_read_path_history_path={history_path}")
    print(f"phase6_knowledge_graph_read_path_event_log_path={event_log_path}")
    print(f"phase6_knowledge_graph_read_path_read_view_state={written['read_view_state']}")
    print(f"phase6_knowledge_graph_read_path_source_staging_status={written['source_staging_status']}")
    print(f"phase6_knowledge_graph_read_path_source_approval_state={written['source_approval_state']}")
    print(
        "phase6_knowledge_graph_read_path_source_staged_entry_count="
        f"{written['source_staged_entry_count']}"
    )
    print(
        "phase6_knowledge_graph_read_path_source_blocked_action_count="
        f"{written['source_blocked_action_count']}"
    )
    print(f"phase6_knowledge_graph_read_path_result_count={written['result_count']}")
    print(f"phase6_knowledge_graph_read_path_seed_result_count={written['seed_result_count']}")
    print(f"phase6_knowledge_graph_read_path_staged_result_count={written['staged_result_count']}")
    print(
        "phase6_knowledge_graph_read_path_approved_learning_entry_count="
        f"{written['approved_learning_entry_count']}"
    )
    print(f"phase6_knowledge_graph_read_path_search_enabled={written['search_enabled']}")
    print(f"phase6_knowledge_graph_read_path_crude_oil_search_result_count={len(crude_results)}")
    print(
        "phase6_knowledge_graph_read_path_paper_lifecycle_search_result_count="
        f"{len(paper_results)}"
    )
    print(
        "phase6_knowledge_graph_read_path_cockpit_safe_result_count="
        f"{written['cockpit_safe_status']['result_count']}"
    )
    print(
        "phase6_knowledge_graph_read_path_cockpit_safe_seed_result_count="
        f"{written['cockpit_safe_status']['seed_result_count']}"
    )
    print(f"phase6_knowledge_graph_read_path_write_allowed={written['write_allowed']}")
    print(f"phase6_knowledge_graph_read_path_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_knowledge_graph_read_path_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_knowledge_graph_read_path_knowledge_graph_commit_created="
        f"{written['knowledge_graph_commit_created']}"
    )
    print(f"phase6_knowledge_graph_read_path_chroma_write_created={written['chroma_write_created']}")
    print(
        "phase6_knowledge_graph_read_path_graph_backend_write_created="
        f"{written['graph_backend_write_created']}"
    )
    print(f"phase6_knowledge_graph_read_path_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(
        "phase6_knowledge_graph_read_path_private_payload_copied_count="
        f"{written['private_payload_copied_count']}"
    )
    print(f"phase6_knowledge_graph_read_path_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_knowledge_graph_read_path_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_knowledge_graph_read_path_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_knowledge_graph_read_path_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_knowledge_graph_read_path_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_knowledge_graph_read_path_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_knowledge_graph_read_path_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_knowledge_graph_read_path_blocker_count={written['blocker_count']}")
    print(f"phase6_knowledge_graph_read_path_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_knowledge_graph_read_path_validation_error_count={len(validation_errors)}")
    print(f"phase6_knowledge_graph_read_path_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_knowledge_graph_read_path_schema_summary_status={schema_summary['status']}")
    print(f"phase6_knowledge_graph_read_path_staging_error_count={len(staging_errors)}")
    print(f"phase6_knowledge_graph_read_path_next_stage={written['recommended_next_stage']}")
    print("phase6_knowledge_graph_read_path_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_knowledge_graph_read_path_error={error}")
        print("phase6_knowledge_graph_read_path_check=failed")
        return 1

    print("phase6_knowledge_graph_read_path_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
