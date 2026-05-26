#!/usr/bin/env python3
"""Validate Q6-6 deterministic postmortem analysis packets."""

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
from orchestrator.phase6_postmortem_agent import (  # noqa: E402
    validate_phase6_postmortem_draft,
)
from orchestrator.phase6_postmortem_analysis import (  # noqa: E402
    ANALYSIS_PACKET_TYPES,
    SOURCE_POSTMORTEM_DRAFT_REF,
    build_phase6_postmortem_analysis,
    phase6_postmortem_analysis_paths,
    validate_phase6_postmortem_analysis,
    write_phase6_postmortem_analysis,
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
    refs = [SOURCE_POSTMORTEM_DRAFT_REF]
    draft = _read_json(root / SOURCE_POSTMORTEM_DRAFT_REF)
    provenance = draft.get("provenance", {}) if isinstance(draft, dict) else {}
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str):
                refs.append(ref)
    outcome_ref = draft.get("source_outcome_artifact_ref") if isinstance(draft, dict) else None
    if isinstance(outcome_ref, str):
        refs.append(outcome_ref)
    return sorted(
        {
            ref
            for ref in refs
            if ref.startswith("data/runtime/")
            and not ref.startswith("data/runtime/phase6_postmortem_analysis")
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
    output_path, history_path, event_log_path = phase6_postmortem_analysis_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    root = _repo_root(settings)
    draft = _read_json(root / SOURCE_POSTMORTEM_DRAFT_REF)
    draft_errors = validate_phase6_postmortem_draft(draft) if draft else []

    artifact = build_phase6_postmortem_analysis(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_postmortem_analysis(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_postmortem_analysis(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    approved_probe = deepcopy(written)
    approved_probe["postmortem_approved"] = True
    approved_probe["approval_state"] = "approved"
    approved_probe["packets"][0]["approval_state"] = "approved"
    approved_errors = validate_phase6_postmortem_analysis(approved_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["learning_write_allowed"] = True
    learning_write_probe["learning_write_created"] = True
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_probe["packets"][0]["learning_write_created"] = True
    learning_write_errors = validate_phase6_postmortem_analysis(learning_write_probe)

    knowledge_graph_probe = deepcopy(written)
    knowledge_graph_probe["knowledge_graph_write_created"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed"] = True
    knowledge_graph_probe["phase6_knowledge_graph_write_allowed_count"] = 1
    knowledge_graph_errors = validate_phase6_postmortem_analysis(knowledge_graph_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_postmortem_analysis(mutation_probe)

    missing_packet_probe = deepcopy(written)
    missing_packet_probe["packets"] = missing_packet_probe["packets"][1:]
    missing_packet_probe["analysis_packet_count"] = len(missing_packet_probe["packets"])
    missing_packet_errors = validate_phase6_postmortem_analysis(missing_packet_probe)

    uncited_claim_probe = deepcopy(written)
    uncited_claim_probe["packets"][0]["claims"][0]["source_refs"] = []
    uncited_claim_errors = validate_phase6_postmortem_analysis(uncited_claim_probe)

    confidence_probe = deepcopy(written)
    confidence_probe["packets"][0]["confidence"] = 1.2
    confidence_errors = validate_phase6_postmortem_analysis(confidence_probe)

    uncertainty_probe = deepcopy(written)
    uncertainty_probe["packets"][0]["uncertainty"] = []
    uncertainty_probe["packets"][0]["uncertainty_count"] = 0
    uncertainty_errors = validate_phase6_postmortem_analysis(uncertainty_probe)

    missing_evidence_probe = deepcopy(written)
    missing_evidence_probe["packets"][0]["missing_evidence"] = []
    missing_evidence_probe["packets"][0]["missing_evidence_count"] = 0
    missing_evidence_errors = validate_phase6_postmortem_analysis(missing_evidence_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["packets"][0]["claims"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase6_postmortem_analysis(local_path_probe)

    llm_probe = deepcopy(written)
    llm_probe["llm_used"] = True
    llm_errors = validate_phase6_postmortem_analysis(llm_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_postmortem_analysis(proof_credit_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if draft_errors:
        errors.extend(draft_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_6_source_artifacts_mutated")
    if written["status"] != "draft":
        errors.append("postmortem_analysis_status_not_draft")
    if written["analysis_state"] != "deterministic_analysis_packets_created":
        errors.append("analysis_state_invalid")
    if written["analysis_packet_count"] != len(ANALYSIS_PACKET_TYPES):
        errors.append("analysis_packet_count_invalid")
    if set(written["analysis_packet_types"]) != set(ANALYSIS_PACKET_TYPES):
        errors.append("analysis_packet_types_invalid")
    if written["claim_count"] < len(ANALYSIS_PACKET_TYPES):
        errors.append("claim_count_too_low")
    if written["all_claims_cited"] is not True:
        errors.append("all_claims_cited_false")
    if written["confidence_packet_count"] != len(ANALYSIS_PACKET_TYPES):
        errors.append("confidence_packet_count_invalid")
    if written["uncertainty_count"] < len(ANALYSIS_PACKET_TYPES):
        errors.append("uncertainty_count_too_low")
    if written["missing_evidence_count"] < len(ANALYSIS_PACKET_TYPES):
        errors.append("missing_evidence_count_too_low")
    if written["approval_state"] != "not_requested":
        errors.append("approval_state_not_requested")
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
    if written["llm_used"] is not False:
        errors.append("llm_used")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("postmortem_analysis_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")

    if "postmortem_approved" not in approved_errors:
        errors.append("approved_probe_not_rejected")
    if "approval_state_invalid" not in approved_errors:
        errors.append("approval_state_probe_not_rejected")
    if not _has_error(approved_errors, "analysis_packet_approval_state_invalid:"):
        errors.append("packet_approval_probe_not_rejected")
    if "learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_allowed_probe_not_rejected")
    if (
        "postmortem_analysis_write_enabled:learning_write_created"
        not in learning_write_errors
    ):
        errors.append("learning_write_created_probe_not_rejected")
    if "authority_enabled:phase6_learning_write_allowed" not in learning_write_errors:
        errors.append("learning_write_authority_probe_not_rejected")
    if (
        "analysis_packet:catalyst_analysis_write_enabled:learning_write_created"
        not in learning_write_errors
    ):
        errors.append("packet_learning_write_probe_not_rejected")
    if (
        "postmortem_analysis_write_enabled:knowledge_graph_write_created"
        not in knowledge_graph_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "postmortem_analysis_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_probe_not_rejected")
    if "postmortem_analysis_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_probe_not_rejected")
    if "postmortem_analysis_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "postmortem_analysis_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "analysis_packet_count_invalid" not in missing_packet_errors:
        errors.append("missing_packet_probe_not_rejected")
    if "analysis_packet_type_set_mismatch" not in missing_packet_errors:
        errors.append("missing_packet_type_probe_not_rejected")
    if not _has_error(uncited_claim_errors, "analysis_claim:catalyst_analysis_source_refs_missing"):
        errors.append("uncited_claim_probe_not_rejected")
    if "all_claims_cited_mismatch" not in uncited_claim_errors:
        errors.append("all_claims_cited_probe_not_rejected")
    if not _has_error(confidence_errors, "analysis_packet_confidence_invalid:"):
        errors.append("confidence_probe_not_rejected")
    if not _has_error(uncertainty_errors, "analysis_packet_uncertainty_missing:"):
        errors.append("uncertainty_probe_not_rejected")
    if not _has_error(
        missing_evidence_errors,
        "analysis_packet_missing_evidence_missing:",
    ):
        errors.append("missing_evidence_probe_not_rejected")
    if not _has_error(local_path_errors, "analysis_claim:catalyst_analysis_local_source_ref"):
        errors.append("local_path_probe_not_rejected")
    if "llm_used" not in llm_errors:
        errors.append("llm_probe_not_rejected")
    if "postmortem_analysis_write_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_probe_not_rejected")

    print(f"phase6_postmortem_analysis_status={written['status']}")
    print(f"phase6_postmortem_analysis_artifact_path={output_path}")
    print(f"phase6_postmortem_analysis_history_path={history_path}")
    print(f"phase6_postmortem_analysis_event_log_path={event_log_path}")
    print(f"phase6_postmortem_analysis_state={written['analysis_state']}")
    print(f"phase6_postmortem_analysis_packet_count={written['analysis_packet_count']}")
    print(
        "phase6_postmortem_analysis_packet_types="
        f"{','.join(written['analysis_packet_types'])}"
    )
    print(f"phase6_postmortem_analysis_claim_count={written['claim_count']}")
    print(f"phase6_postmortem_analysis_all_claims_cited={written['all_claims_cited']}")
    print(
        "phase6_postmortem_analysis_confidence_packet_count="
        f"{written['confidence_packet_count']}"
    )
    print(f"phase6_postmortem_analysis_uncertainty_count={written['uncertainty_count']}")
    print(
        "phase6_postmortem_analysis_missing_evidence_count="
        f"{written['missing_evidence_count']}"
    )
    print(f"phase6_postmortem_analysis_postmortem_approved={written['postmortem_approved']}")
    print(f"phase6_postmortem_analysis_approval_state={written['approval_state']}")
    print(f"phase6_postmortem_analysis_llm_used={written['llm_used']}")
    print(f"phase6_postmortem_analysis_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_postmortem_analysis_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_postmortem_analysis_model_weight_update_created="
        f"{written['model_weight_update_created']}"
    )
    print(
        "phase6_postmortem_analysis_trust_score_update_created="
        f"{written['trust_score_update_created']}"
    )
    print(
        "phase6_postmortem_analysis_policy_mutation_created="
        f"{written['policy_mutation_created']}"
    )
    print(
        "phase6_postmortem_analysis_strategy_mutation_created="
        f"{written['strategy_mutation_created']}"
    )
    print(f"phase6_postmortem_analysis_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_postmortem_analysis_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_postmortem_analysis_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase6_postmortem_analysis_blocker_count={written['blocker_count']}")
    print(
        "phase6_postmortem_analysis_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(f"phase6_postmortem_analysis_validation_error_count={len(validation_errors)}")
    print(f"phase6_postmortem_analysis_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_postmortem_analysis_schema_summary_status={schema_summary['status']}")
    print(f"phase6_postmortem_analysis_draft_error_count={len(draft_errors)}")
    print(f"phase6_postmortem_analysis_next_stage={written['recommended_next_stage']}")
    print("phase6_postmortem_analysis_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_postmortem_analysis_error={error}")
        print("phase6_postmortem_analysis_check=failed")
        return 1

    print("phase6_postmortem_analysis_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
