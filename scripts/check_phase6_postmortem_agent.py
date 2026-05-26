#!/usr/bin/env python3
"""Validate Q6-5 deterministic Postmortem Agent draft."""

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
from orchestrator.phase6_postmortem_agent import (  # noqa: E402
    SOURCE_OUTCOME_REF,
    SOURCE_PACKET_CONTRACT_REF,
    build_phase6_postmortem_draft,
    phase6_postmortem_draft_paths,
    validate_phase6_postmortem_draft,
    write_phase6_postmortem_draft,
)
from orchestrator.phase6_postmortem_packets import (  # noqa: E402
    POSTMORTEM_PACKET_SECTIONS,
    validate_phase6_postmortem_packet_contract,
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
    refs = [SOURCE_PACKET_CONTRACT_REF, SOURCE_OUTCOME_REF]
    for ref in (SOURCE_PACKET_CONTRACT_REF, SOURCE_OUTCOME_REF):
        payload = _read_json(root / ref)
        provenance = payload.get("provenance", {}) if isinstance(payload, dict) else {}
        if not isinstance(provenance, dict):
            continue
        for source_ref in provenance.get("source_refs", []):
            if isinstance(source_ref, str):
                refs.append(source_ref)
    return sorted(
        {
            ref
            for ref in refs
            if ref.startswith("data/runtime/")
            and not ref.startswith("data/runtime/phase6_postmortem_draft")
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


def _outcome_record(outcome: dict[str, object]) -> dict[str, object]:
    records = outcome.get("outcome_records", [])
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    before_hashes = _file_hashes(settings)
    output_path, history_path, event_log_path = phase6_postmortem_draft_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    root = _repo_root(settings)
    contract = _read_json(root / SOURCE_PACKET_CONTRACT_REF)
    outcome = _read_json(root / SOURCE_OUTCOME_REF)
    contract_errors = (
        validate_phase6_postmortem_packet_contract(contract) if contract else []
    )
    outcome_errors = validate_phase6_closed_trade_outcome(outcome) if outcome else []

    artifact = build_phase6_postmortem_draft(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_postmortem_draft(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_postmortem_draft(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    approved_probe = deepcopy(written)
    approved_probe["postmortem_approved"] = True
    approved_probe["approval_state"] = "approved"
    approved_errors = validate_phase6_postmortem_draft(approved_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_postmortem_draft(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_postmortem_draft(knowledge_graph_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_postmortem_draft(mutation_probe)

    llm_probe = deepcopy(written)
    llm_probe["llm_used"] = True
    llm_errors = validate_phase6_postmortem_draft(llm_probe)

    packet_draft_flag_probe = deepcopy(written)
    packet_draft_flag_probe["packet"]["postmortem_draft_created"] = True
    packet_draft_flag_errors = validate_phase6_postmortem_draft(packet_draft_flag_probe)

    narrative_only_probe = deepcopy(written)
    narrative_only_probe["packet"]["narrative_only"] = True
    narrative_only_probe["packet"]["sections"] = []
    narrative_only_probe["packet"]["narrative_body"] = "Prose-only postmortem."
    narrative_errors = validate_phase6_postmortem_draft(narrative_only_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["packet"]["sections"][0]["assertions"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_postmortem_draft(local_path_probe)

    unknown_marker_probe = deepcopy(written)
    unknown_marker_probe["unknown_markers"] = unknown_marker_probe["unknown_markers"][1:]
    unknown_marker_errors = validate_phase6_postmortem_draft(unknown_marker_probe)

    deferred_marker_probe = deepcopy(written)
    deferred_marker_probe["deferred_markers"] = deferred_marker_probe["deferred_markers"][1:]
    deferred_marker_errors = validate_phase6_postmortem_draft(deferred_marker_probe)

    missing_ref_probe = deepcopy(written)
    missing_ref_probe["missing_ref_markers"] = missing_ref_probe["missing_ref_markers"][1:]
    missing_ref_errors = validate_phase6_postmortem_draft(missing_ref_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_postmortem_draft(proof_credit_probe)

    outcome_record = _outcome_record(outcome)
    expected_unknown_count = len(outcome_record.get("unknown_fields", []))
    expected_deferred_count = len(outcome_record.get("deferred_fields", []))

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if contract_errors:
        errors.extend(contract_errors)
    if outcome_errors:
        errors.extend(outcome_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_5_source_artifacts_mutated")
    if written["status"] != "draft":
        errors.append("postmortem_draft_status_not_draft")
    if written["draft_state"] != "deterministic_postmortem_draft_created":
        errors.append("postmortem_draft_state_invalid")
    if written["postmortem_draft_created"] is not True:
        errors.append("postmortem_draft_not_created")
    if written["postmortem_draft_count"] != 1:
        errors.append("postmortem_draft_count_invalid")
    if written["postmortem_approved"] is not False:
        errors.append("postmortem_approved")
    if written["approval_state"] != "not_requested":
        errors.append("approval_state_not_requested")
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
    if written["llm_required"] is not False or written["llm_used"] is not False:
        errors.append("llm_used_or_required")
    if written["packet_section_count"] != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("packet_section_count_invalid")
    if written["source_assertion_count"] < len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("source_assertion_count_too_low")
    if written["packet_validation_error_count"] != 0:
        errors.append("packet_validation_errors_present")
    if written["unknown_marker_count"] != expected_unknown_count:
        errors.append("unknown_marker_count_unexpected")
    if written["deferred_marker_count"] != expected_deferred_count:
        errors.append("deferred_marker_count_unexpected")
    if written["missing_ref_count"] < 1:
        errors.append("missing_ref_count_missing")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("postmortem_draft_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if "postmortem_approved" not in approved_errors:
        errors.append("approved_probe_not_rejected")
    if "postmortem_draft_approval_state_invalid" not in approved_errors:
        errors.append("approval_state_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if (
        "postmortem_draft_write_enabled:learning_write_created"
        not in learning_write_errors
    ):
        errors.append("learning_write_created_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if (
        "postmortem_draft_write_enabled:knowledge_graph_write_created"
        not in knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "postmortem_draft_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_probe_not_rejected")
    if "postmortem_draft_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_probe_not_rejected")
    if "postmortem_draft_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "postmortem_draft_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "llm_used" not in llm_errors:
        errors.append("llm_probe_not_rejected")
    if (
        "postmortem_packet:packet_write_enabled:postmortem_draft_created"
        not in packet_draft_flag_errors
    ):
        errors.append("packet_draft_created_probe_not_rejected")
    if "postmortem_packet:narrative_only_packet" not in narrative_errors:
        errors.append("narrative_only_probe_not_rejected")
    if "postmortem_packet:packet_assertion_local_source_ref" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if not _has_error(unknown_marker_errors, "unknown_marker_missing:"):
        errors.append("unknown_marker_probe_not_rejected")
    if not _has_error(deferred_marker_errors, "deferred_marker_missing:"):
        errors.append("deferred_marker_probe_not_rejected")
    if not _has_error(missing_ref_errors, "missing_ref_marker_missing:"):
        errors.append("missing_ref_probe_not_rejected")
    if "postmortem_draft_write_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")

    print(f"phase6_postmortem_agent_status={written['status']}")
    print(f"phase6_postmortem_agent_artifact_path={output_path}")
    print(f"phase6_postmortem_agent_history_path={history_path}")
    print(f"phase6_postmortem_agent_event_log_path={event_log_path}")
    print(f"phase6_postmortem_agent_draft_state={written['draft_state']}")
    print(f"phase6_postmortem_agent_postmortem_draft_created={written['postmortem_draft_created']}")
    print(f"phase6_postmortem_agent_postmortem_approved={written['postmortem_approved']}")
    print(f"phase6_postmortem_agent_approval_state={written['approval_state']}")
    print(f"phase6_postmortem_agent_source_outcome_ref={written['source_outcome_ref']}")
    print(f"phase6_postmortem_agent_packet_section_count={written['packet_section_count']}")
    print(f"phase6_postmortem_agent_source_assertion_count={written['source_assertion_count']}")
    print(f"phase6_postmortem_agent_unknown_marker_count={written['unknown_marker_count']}")
    print(f"phase6_postmortem_agent_deferred_marker_count={written['deferred_marker_count']}")
    print(f"phase6_postmortem_agent_missing_ref_count={written['missing_ref_count']}")
    print(f"phase6_postmortem_agent_llm_used={written['llm_used']}")
    print(f"phase6_postmortem_agent_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_postmortem_agent_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_postmortem_agent_model_weight_update_created="
        f"{written['model_weight_update_created']}"
    )
    print(
        "phase6_postmortem_agent_trust_score_update_created="
        f"{written['trust_score_update_created']}"
    )
    print(f"phase6_postmortem_agent_policy_mutation_created={written['policy_mutation_created']}")
    print(
        "phase6_postmortem_agent_strategy_mutation_created="
        f"{written['strategy_mutation_created']}"
    )
    print(f"phase6_postmortem_agent_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_postmortem_agent_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_postmortem_agent_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_postmortem_agent_blocker_count={written['blocker_count']}")
    print(f"phase6_postmortem_agent_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_postmortem_agent_validation_error_count={len(validation_errors)}")
    print(f"phase6_postmortem_agent_packet_validation_error_count={written['packet_validation_error_count']}")
    print(f"phase6_postmortem_agent_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_postmortem_agent_schema_summary_status={schema_summary['status']}")
    print(f"phase6_postmortem_agent_contract_error_count={len(contract_errors)}")
    print(f"phase6_postmortem_agent_outcome_error_count={len(outcome_errors)}")
    print(f"phase6_postmortem_agent_next_stage={written['recommended_next_stage']}")
    print("phase6_postmortem_agent_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_postmortem_agent_error={error}")
        print("phase6_postmortem_agent_check=failed")
        return 1

    print("phase6_postmortem_agent_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
