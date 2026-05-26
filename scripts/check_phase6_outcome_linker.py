#!/usr/bin/env python3
"""Validate Q6-8 outcome linker."""

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
from orchestrator.phase6_closed_trade_outcome import (  # noqa: E402
    validate_phase6_closed_trade_outcome,
)
from orchestrator.phase6_learning_source_intake import (  # noqa: E402
    validate_phase6_learning_source_intake,
)
from orchestrator.phase6_outcome_linker import (  # noqa: E402
    OPTIONAL_LINK_KEYS,
    REQUIRED_LINK_KEYS,
    SOURCE_INTAKE_REF,
    SOURCE_OUTCOME_REF,
    SOURCE_REVIEW_REF,
    build_phase6_outcome_linker,
    phase6_outcome_linker_paths,
    validate_phase6_outcome_linker,
    write_phase6_outcome_linker,
)
from orchestrator.phase6_postmortem_reducer import (  # noqa: E402
    validate_phase6_postmortem_reducer,
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
    refs: list[str] = [SOURCE_OUTCOME_REF, SOURCE_INTAKE_REF, SOURCE_REVIEW_REF]
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
            and not ref.startswith("data/runtime/phase6_outcome_links")
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
    prebuilt = build_phase6_outcome_linker(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    output_path, history_path, event_log_path = phase6_outcome_linker_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    root = _repo_root(settings)
    outcome = _read_json(root / SOURCE_OUTCOME_REF)
    source_intake = _read_json(root / SOURCE_INTAKE_REF)
    review = _read_json(root / SOURCE_REVIEW_REF)
    outcome_errors = validate_phase6_closed_trade_outcome(outcome) if outcome else []
    source_intake_errors = (
        validate_phase6_learning_source_intake(source_intake) if source_intake else []
    )
    review_errors = validate_phase6_postmortem_reducer(review) if review else []

    output_path, history_path, event_log_path, written = write_phase6_outcome_linker(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_outcome_linker(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    link_write_probe = deepcopy(written)
    link_write_probe["link_write_allowed"] = True
    link_write_errors = validate_phase6_outcome_linker(link_write_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_outcome_linker(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_outcome_linker(knowledge_graph_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_outcome_linker(mutation_probe)

    missing_required_probe = deepcopy(written)
    for record in missing_required_probe["link_records"]:
        if record["link_key"] == "dry_run_receipt":
            record["present"] = False
            record["source_ref"] = None
            record["selected_ref"] = None
            record["missing_reason"] = "probe_required_link_missing"
            break
    missing_required_probe["complete_outcome_link_created"] = False
    missing_required_probe["required_link_present_count"] -= 1
    missing_required_probe["missing_required_link_count"] = 1
    missing_required_probe["missing_required_links"] = ["dry_run_receipt"]
    missing_required_errors = validate_phase6_outcome_linker(missing_required_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["link_records"][0]["raw_payload_copied"] = True
    raw_payload_probe["raw_payload_copied_count"] = 1
    raw_payload_errors = validate_phase6_outcome_linker(raw_payload_probe)

    payload_field_probe = deepcopy(written)
    payload_field_probe["link_records"][0]["raw_payload"] = {"not_allowed": True}
    payload_field_errors = validate_phase6_outcome_linker(payload_field_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["link_records"][0]["source_ref"] = (
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    )
    local_path_errors = validate_phase6_outcome_linker(local_path_probe)

    optional_missing_probe = deepcopy(written)
    for record in optional_missing_probe["link_records"]:
        if record["link_key"] == "yahoo_finance_context":
            record["present"] = False
            record["safe_missing_optional_context"] = False
            record["missing_reason"] = None
            break
    optional_missing_probe["optional_link_present_count"] -= 1
    optional_missing_probe["missing_optional_link_count"] += 1
    optional_missing_probe["missing_optional_links"] = ["yahoo_finance_context"]
    optional_missing_errors = validate_phase6_outcome_linker(optional_missing_probe)

    review_state_probe = deepcopy(written)
    review_state_probe["source_review_state"] = "approved"
    review_state_errors = validate_phase6_outcome_linker(review_state_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["source_artifact_mutation_allowed"] = True
    phase5_mutation_probe["source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_outcome_linker(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_outcome_linker(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_outcome_linker(phase5_proof_probe)

    reference_probe = deepcopy(written)
    reference_probe["link_records"][0]["reference_only"] = False
    reference_errors = validate_phase6_outcome_linker(reference_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_outcome_linker(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if outcome_errors:
        errors.extend(outcome_errors)
    if source_intake_errors:
        errors.extend(source_intake_errors)
    if review_errors:
        errors.extend(review_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_8_source_artifacts_mutated")
    if written["status"] != "linked":
        errors.append("outcome_linker_status_not_linked")
    if written["complete_outcome_link_created"] is not True:
        errors.append("complete_outcome_link_not_created")
    if written["linked_ref_count"] != len(REQUIRED_LINK_KEYS) + len(OPTIONAL_LINK_KEYS):
        errors.append("linked_ref_count_invalid")
    if written["required_link_count"] != len(REQUIRED_LINK_KEYS):
        errors.append("required_link_count_invalid")
    if written["required_link_present_count"] != len(REQUIRED_LINK_KEYS):
        errors.append("required_link_present_count_invalid")
    if written["missing_required_link_count"] != 0:
        errors.append("missing_required_link_count_nonzero")
    if written["optional_link_count"] != len(OPTIONAL_LINK_KEYS):
        errors.append("optional_link_count_invalid")
    if written["optional_link_present_count"] != len(OPTIONAL_LINK_KEYS):
        errors.append("optional_link_present_count_invalid")
    if written["missing_optional_link_count"] != 0:
        errors.append("missing_optional_link_count_nonzero")
    if written["reference_only_link_count"] != written["linked_ref_count"]:
        errors.append("reference_only_link_count_invalid")
    if written["raw_payload_copied_count"] != 0:
        errors.append("raw_payload_copied_count_nonzero")
    if written["private_payload_copied_count"] != 0:
        errors.append("private_payload_copied_count_nonzero")
    if written["local_path_exposed_count"] != 0:
        errors.append("local_path_exposed_count_nonzero")
    if written["secret_ref_exposed_count"] != 0:
        errors.append("secret_ref_exposed_count_nonzero")
    if written["source_artifacts_mutated"] is not False:
        errors.append("source_artifacts_mutated")
    if written["link_write_allowed"] is not False:
        errors.append("link_write_allowed")
    if written["postmortem_approved"] is not False:
        errors.append("postmortem_approved")
    if written["approval_state"] != "not_requested":
        errors.append("approval_state_not_requested")
    if written["approval_logged"] is not False:
        errors.append("approval_logged")
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
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("outcome_linker_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "link_write_allowed" not in link_write_errors:
        errors.append("link_write_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if "outcome_linker_write_enabled:learning_write_created" not in learning_write_errors:
        errors.append("learning_write_created_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if "outcome_linker_write_enabled:knowledge_graph_write_created" not in (
        knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "outcome_linker_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_probe_not_rejected")
    if "outcome_linker_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_probe_not_rejected")
    if "outcome_linker_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "outcome_linker_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "required_links_missing" not in missing_required_errors:
        errors.append("missing_required_probe_not_rejected")
    if "complete_outcome_link_not_created" not in missing_required_errors:
        errors.append("missing_required_complete_probe_not_rejected")
    if not _has_error(raw_payload_errors, "raw_payload_copied:"):
        errors.append("raw_payload_probe_not_rejected")
    if not _has_error(payload_field_errors, "link_payload_field_forbidden:"):
        errors.append("payload_field_probe_not_rejected")
    if not _has_error(local_path_errors, "link:closed_trade_outcome_local_source_ref"):
        errors.append("local_path_probe_not_rejected")
    if "optional_missing_not_safe:yahoo_finance_context" not in optional_missing_errors:
        errors.append("optional_missing_safe_probe_not_rejected")
    if "optional_missing_reason_missing:yahoo_finance_context" not in optional_missing_errors:
        errors.append("optional_missing_reason_probe_not_rejected")
    if "source_review_state_invalid" not in review_state_errors:
        errors.append("review_state_probe_not_rejected")
    if "source_artifact_mutation_allowed" not in phase5_mutation_errors:
        errors.append("source_mutation_allowed_probe_not_rejected")
    if "source_artifacts_mutated" not in phase5_mutation_errors:
        errors.append("source_artifacts_mutated_probe_not_rejected")
    if "outcome_linker_write_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(reference_errors, "link_not_reference_only:"):
        errors.append("reference_probe_not_rejected")
    if not _has_error(unsafe_errors, "outcome_linker_unsafe_count_nonzero:"):
        errors.append("unsafe_count_probe_not_rejected")

    print(f"phase6_outcome_linker_status={written['status']}")
    print(f"phase6_outcome_linker_artifact_path={output_path}")
    print(f"phase6_outcome_linker_history_path={history_path}")
    print(f"phase6_outcome_linker_event_log_path={event_log_path}")
    print(f"phase6_outcome_linker_source_trade_ref={written['source_trade_ref']}")
    print(f"phase6_outcome_linker_source_outcome_ref={written['source_outcome_ref']}")
    print(f"phase6_outcome_linker_source_review_state={written['source_review_state']}")
    print(
        "phase6_outcome_linker_complete_outcome_link_created="
        f"{written['complete_outcome_link_created']}"
    )
    print(f"phase6_outcome_linker_linked_ref_count={written['linked_ref_count']}")
    print(f"phase6_outcome_linker_required_link_count={written['required_link_count']}")
    print(
        "phase6_outcome_linker_required_link_present_count="
        f"{written['required_link_present_count']}"
    )
    print(
        "phase6_outcome_linker_missing_required_link_count="
        f"{written['missing_required_link_count']}"
    )
    print(f"phase6_outcome_linker_optional_link_count={written['optional_link_count']}")
    print(
        "phase6_outcome_linker_optional_link_present_count="
        f"{written['optional_link_present_count']}"
    )
    print(
        "phase6_outcome_linker_missing_optional_link_count="
        f"{written['missing_optional_link_count']}"
    )
    print(f"phase6_outcome_linker_reference_only_link_count={written['reference_only_link_count']}")
    print(f"phase6_outcome_linker_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(
        "phase6_outcome_linker_private_payload_copied_count="
        f"{written['private_payload_copied_count']}"
    )
    print(f"phase6_outcome_linker_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_outcome_linker_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_outcome_linker_source_artifacts_mutated={written['source_artifacts_mutated']}")
    print(f"phase6_outcome_linker_source_hash_mutation_count={len(mutated_refs)}")
    print(f"phase6_outcome_linker_link_write_allowed={written['link_write_allowed']}")
    print(f"phase6_outcome_linker_postmortem_approved={written['postmortem_approved']}")
    print(f"phase6_outcome_linker_approval_state={written['approval_state']}")
    print(f"phase6_outcome_linker_approval_logged={written['approval_logged']}")
    print(f"phase6_outcome_linker_learning_action_count={written['learning_action_count']}")
    print(
        "phase6_outcome_linker_learning_action_approved_count="
        f"{written['learning_action_approved_count']}"
    )
    print(f"phase6_outcome_linker_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_outcome_linker_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_outcome_linker_model_weight_update_created="
        f"{written['model_weight_update_created']}"
    )
    print(
        "phase6_outcome_linker_trust_score_update_created="
        f"{written['trust_score_update_created']}"
    )
    print(f"phase6_outcome_linker_policy_mutation_created={written['policy_mutation_created']}")
    print(
        "phase6_outcome_linker_strategy_mutation_created="
        f"{written['strategy_mutation_created']}"
    )
    print(
        "phase6_outcome_linker_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_outcome_linker_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_outcome_linker_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_outcome_linker_blocker_count={written['blocker_count']}")
    print(f"phase6_outcome_linker_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_outcome_linker_validation_error_count={len(validation_errors)}")
    print(f"phase6_outcome_linker_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_outcome_linker_schema_summary_status={schema_summary['status']}")
    print(f"phase6_outcome_linker_outcome_error_count={len(outcome_errors)}")
    print(f"phase6_outcome_linker_source_intake_error_count={len(source_intake_errors)}")
    print(f"phase6_outcome_linker_review_error_count={len(review_errors)}")
    print(f"phase6_outcome_linker_next_stage={written['recommended_next_stage']}")
    print("phase6_outcome_linker_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_outcome_linker_error={error}")
        print("phase6_outcome_linker_check=failed")
        return 1

    print("phase6_outcome_linker_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
