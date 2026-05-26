#!/usr/bin/env python3
"""Validate Q6-13 trust-score update proposals."""

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
from orchestrator.phase4_trust_scores import validate_trust_score_recalculation  # noqa: E402
from orchestrator.phase6_artifacts import (  # noqa: E402
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
)
from orchestrator.phase6_model_weight_updates import (  # noqa: E402
    validate_phase6_model_weight_updates,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)
from orchestrator.phase6_trust_score_updates import (  # noqa: E402
    SOURCE_MODEL_WEIGHT_REF,
    SOURCE_TRUST_SCORE_REF,
    build_phase6_trust_score_updates,
    phase6_trust_score_updates_paths,
    validate_phase6_trust_score_updates,
    write_phase6_trust_score_updates,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = [SOURCE_MODEL_WEIGHT_REF, SOURCE_TRUST_SCORE_REF]
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
            and not ref.startswith("data/runtime/phase6_trust_score_update_proposals")
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


def _active_trust_scores(settings: Settings) -> dict[str, float]:
    artifact = _read_json(_repo_root(settings) / SOURCE_TRUST_SCORE_REF)
    output: dict[str, float] = {}
    for row in artifact.get("scores", []):
        if not isinstance(row, dict):
            continue
        source_key = row.get("source_key")
        value = row.get("final_provisional_score")
        if isinstance(source_key, str) and isinstance(value, int | float):
            output[source_key] = float(value)
    return output


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    prebuilt = build_phase6_trust_score_updates(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    active_scores_before = _active_trust_scores(settings)
    output_path, history_path, event_log_path = phase6_trust_score_updates_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    model_weight = _read_json(_repo_root(settings) / SOURCE_MODEL_WEIGHT_REF)
    model_weight_errors = (
        validate_phase6_model_weight_updates(model_weight) if model_weight else []
    )
    trust_artifact = _read_json(_repo_root(settings) / SOURCE_TRUST_SCORE_REF)
    trust_errors = validate_trust_score_recalculation(trust_artifact) if trust_artifact else []

    output_path, history_path, event_log_path, written = write_phase6_trust_score_updates(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_trust_score_updates(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    active_scores_after = _active_trust_scores(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    apply_probe = deepcopy(written)
    apply_probe["apply_allowed"] = True
    apply_errors = validate_phase6_trust_score_updates(apply_probe)

    authority_probe = deepcopy(written)
    authority_probe["phase6_trust_score_update_allowed"] = True
    authority_probe["phase6_trust_score_update_allowed_count"] = 1
    authority_probe["trust_score_update_allowed"] = True
    authority_errors = validate_phase6_trust_score_updates(authority_probe)

    proposal_allowed_probe = deepcopy(written)
    proposal_allowed_probe["trust_score_update_proposal_allowed"] = True
    proposal_allowed_probe["trust_score_update_proposed"] = True
    proposal_allowed_probe["active_proposal_count"] = 1
    proposal_allowed_errors = validate_phase6_trust_score_updates(proposal_allowed_probe)

    applied_probe = deepcopy(written)
    applied_probe["trust_score_update_applied"] = True
    applied_probe["trust_score_update_created"] = True
    applied_errors = validate_phase6_trust_score_updates(applied_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["active_trust_score_mutated"] = True
    mutation_probe["canonical_rank_mutated"] = True
    mutation_probe["source_quorum_credit_granted"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_trust_score_updates(mutation_probe)

    unapproved_delta_probe = deepcopy(written)
    first_key = next(iter(unapproved_delta_probe["after_score_table"]))
    unapproved_delta_probe["after_score_table"][first_key] = round(
        float(unapproved_delta_probe["after_score_table"][first_key]) + 0.01,
        6,
    )
    unapproved_delta_probe["score_delta_table"][first_key] = 0.01
    unapproved_delta_probe["after_score"] = round(
        sum(float(value) for value in unapproved_delta_probe["after_score_table"].values())
        / len(unapproved_delta_probe["after_score_table"]),
        6,
    )
    unapproved_delta_probe["score_delta_total_abs"] = 0.01
    unapproved_delta_errors = validate_phase6_trust_score_updates(unapproved_delta_probe)

    record_raw_probe = deepcopy(written)
    record_raw_probe["proposal_records"][0]["raw_payload_copied"] = True
    record_raw_probe["raw_payload_copied_count"] = 1
    record_raw_errors = validate_phase6_trust_score_updates(record_raw_probe)

    record_payload_probe = deepcopy(written)
    record_payload_probe["proposal_records"][0]["raw_payload"] = {"not_allowed": True}
    record_payload_errors = validate_phase6_trust_score_updates(record_payload_probe)

    record_local_path_probe = deepcopy(written)
    record_local_path_probe["proposal_records"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    record_local_path_errors = validate_phase6_trust_score_updates(record_local_path_probe)

    record_apply_probe = deepcopy(written)
    record_apply_probe["proposal_records"][0]["apply_allowed"] = True
    record_apply_probe["proposal_records"][0]["trust_score_update_applied"] = True
    record_apply_probe["proposal_records"][0]["active_trust_score_mutated"] = True
    record_apply_errors = validate_phase6_trust_score_updates(record_apply_probe)

    supplemental_probe = deepcopy(written)
    supplemental_probe["supplemental_policy_records"][0]["score_included"] = True
    supplemental_probe["supplemental_policy_records"][0]["canonical_rank_impact_allowed"] = True
    supplemental_probe["supplemental_policy_records"][0]["source_quorum_credit_allowed"] = True
    supplemental_errors = validate_phase6_trust_score_updates(supplemental_probe)

    supplemental_verdict_probe = deepcopy(written)
    supplemental_verdict_probe["supplemental_policy_records"][0][
        "supplemental_only_verdict_rejected"
    ] = False
    supplemental_verdict_probe["supplemental_only_verdict_rejected"] = False
    supplemental_verdict_errors = validate_phase6_trust_score_updates(supplemental_verdict_probe)

    source_state_probe = deepcopy(written)
    source_state_probe["source_model_weight_status"] = "error"
    source_state_probe["source_approval_state"] = "rejected"
    source_state_errors = validate_phase6_trust_score_updates(source_state_probe)

    cockpit_probe = deepcopy(written)
    cockpit_probe["cockpit_safe_status"]["before_score_table"] = written["before_score_table"]
    cockpit_errors = validate_phase6_trust_score_updates(cockpit_probe)

    cockpit_mismatch_probe = deepcopy(written)
    cockpit_mismatch_probe["cockpit_safe_status"]["proposal_record_count"] = 999
    cockpit_mismatch_errors = validate_phase6_trust_score_updates(cockpit_mismatch_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_trust_score_updates(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_trust_score_updates(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_trust_score_updates(phase5_proof_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_trust_score_updates(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if model_weight_errors:
        errors.extend(model_weight_errors)
    if trust_errors:
        errors.extend(trust_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_13_source_artifacts_mutated")
    if active_scores_before != active_scores_after:
        errors.append("active_source_trust_scores_mutated")
    if written["status"] != "blocked":
        errors.append("trust_score_updates_status_not_blocked")
    if written["proposal_state"] != "blocked_pending_learning_approval":
        errors.append("trust_score_updates_state_not_blocked")
    if written["source_model_weight_status"] != "blocked":
        errors.append("source_model_weight_status_not_blocked")
    if written["source_approval_state"] != "deferred":
        errors.append("source_approval_state_not_deferred")
    if written["source_approved_evidence_count"] != 0:
        errors.append("approved_evidence_unexpected")
    if written["canonical_source_score_count"] != 35:
        errors.append("canonical_source_score_count_not_35")
    if written["supplemental_policy_record_count"] != 2:
        errors.append("supplemental_policy_record_count_not_2")
    if written["proposal_record_count"] != 35:
        errors.append("proposal_record_count_not_35")
    if written["active_proposal_count"] != 0:
        errors.append("active_proposal_count_not_zero")
    if written["blocked_proposal_count"] != 35:
        errors.append("blocked_proposal_count_not_35")
    if written["approved_evidence_count"] != 0:
        errors.append("approved_evidence_count_not_zero")
    if written["trust_score_update_count"] != 0:
        errors.append("trust_score_update_count_not_zero")
    if written["before_score_table"] != written["after_score_table"]:
        errors.append("blocked_after_score_changed")
    if written["score_delta_total_abs"] != 0.0:
        errors.append("blocked_score_delta_nonzero")
    for key in (
        "trust_score_update_proposal_allowed",
        "trust_score_update_proposed",
        "apply_allowed",
        "trust_score_update_allowed",
        "trust_score_update_applied",
        "active_trust_score_mutated",
        "canonical_rank_mutated",
        "source_quorum_credit_granted",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "model_weight_update_created",
        "trust_score_update_created",
        "policy_mutation_created",
        "strategy_mutation_created",
        "phase5_source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "yahoo_finance_score_included",
        "yahoo_finance_canonical_rank_impact_allowed",
        "yahoo_finance_source_quorum_credit_allowed",
        "preference_mcp_score_included",
        "preference_mcp_canonical_rank_impact_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "preference_mcp_source_36",
    ):
        if written[key] is not False:
            errors.append(f"{key}_not_false")
    for key in (
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "source_hash_mutation_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        expected = 2 if key == "blocker_count" else 0
        if written[key] != expected:
            errors.append(f"{key}_unexpected:{written[key]}")
    if written["single_source_verdict_rejected"] is not True:
        errors.append("single_source_verdict_not_rejected")
    if written["supplemental_only_verdict_rejected"] is not True:
        errors.append("supplemental_only_verdict_not_rejected")
    if written["single_source_verdict_rejection_count"] < 1:
        errors.append("single_source_rejection_count_missing")
    if written["supplemental_only_verdict_rejection_count"] < 2:
        errors.append("supplemental_rejection_count_missing")
    if replay["total_events"] != 1:
        errors.append("event_log_replay_count_mismatch")

    if "trust_score_updates_write_enabled:apply_allowed" not in apply_errors:
        errors.append("apply_probe_not_rejected")
    if not _has_error(authority_errors, "authority_enabled:phase6_trust_score_update_allowed"):
        errors.append("authority_probe_not_rejected")
    if "trust_score_updates_write_enabled:trust_score_update_allowed" not in authority_errors:
        errors.append("trust_score_update_allowed_probe_not_rejected")
    if (
        "trust_score_updates_write_enabled:trust_score_update_proposal_allowed"
        not in proposal_allowed_errors
    ):
        errors.append("proposal_allowed_probe_not_rejected")
    if "trust_score_updates_unapproved_proposed" not in proposal_allowed_errors:
        errors.append("unapproved_proposed_probe_not_rejected")
    if "trust_score_updates_write_enabled:trust_score_update_applied" not in applied_errors:
        errors.append("applied_probe_not_rejected")
    if "trust_score_updates_write_enabled:trust_score_update_created" not in applied_errors:
        errors.append("trust_score_update_created_probe_not_rejected")
    if "trust_score_updates_write_enabled:active_trust_score_mutated" not in mutation_errors:
        errors.append("active_trust_score_mutation_probe_not_rejected")
    if "trust_score_updates_write_enabled:canonical_rank_mutated" not in mutation_errors:
        errors.append("canonical_rank_mutation_probe_not_rejected")
    if "trust_score_updates_write_enabled:source_quorum_credit_granted" not in mutation_errors:
        errors.append("source_quorum_probe_not_rejected")
    if "trust_score_updates_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "trust_score_updates_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if "trust_score_updates_unapproved_after_changed" not in unapproved_delta_errors:
        errors.append("unapproved_delta_probe_not_rejected")
    if "trust_score_updates_unapproved_delta_nonzero" not in unapproved_delta_errors:
        errors.append("unapproved_delta_nonzero_probe_not_rejected")
    if not _has_error(record_raw_errors, "trust_score_updates_private_or_local_payload_exposed"):
        errors.append("record_raw_probe_not_rejected")
    if "proposal_record_forbidden_payload" not in record_payload_errors:
        errors.append("record_payload_probe_not_rejected")
    if "proposal_record_local_source_ref" not in record_local_path_errors:
        errors.append("record_local_path_probe_not_rejected")
    if "proposal_record_apply_allowed" not in record_apply_errors:
        errors.append("record_apply_probe_not_rejected")
    if "proposal_record_trust_score_update_applied" not in record_apply_errors:
        errors.append("record_applied_probe_not_rejected")
    if "proposal_record_active_trust_score_mutated" not in record_apply_errors:
        errors.append("record_mutation_probe_not_rejected")
    if "supplemental_policy_score_included" not in supplemental_errors:
        errors.append("supplemental_score_probe_not_rejected")
    if "supplemental_policy_rank_impact_allowed" not in supplemental_errors:
        errors.append("supplemental_rank_probe_not_rejected")
    if "supplemental_policy_source_quorum_credit_allowed" not in supplemental_errors:
        errors.append("supplemental_quorum_probe_not_rejected")
    if "supplemental_only_verdict_not_rejected" not in supplemental_verdict_errors:
        errors.append("supplemental_verdict_probe_not_rejected")
    if "supplemental_only_verdict_rejected_not_true" not in supplemental_verdict_errors:
        errors.append("supplemental_artifact_verdict_probe_not_rejected")
    if "source_model_weight_status_invalid" not in source_state_errors:
        errors.append("source_status_probe_not_rejected")
    if "source_approval_state_invalid" not in source_state_errors:
        errors.append("source_approval_probe_not_rejected")
    if not _has_error(cockpit_errors, "cockpit_safe_status_forbidden_fields:"):
        errors.append("cockpit_probe_not_rejected")
    if "cockpit_safe_status_mismatch:proposal_record_count" not in cockpit_mismatch_errors:
        errors.append("cockpit_mismatch_probe_not_rejected")
    if (
        "trust_score_updates_write_enabled:phase5_source_artifacts_mutated"
        not in phase5_mutation_errors
    ):
        errors.append("phase5_mutation_probe_not_rejected")
    if "trust_score_updates_write_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(unsafe_errors, "trust_score_updates_unsafe_count_nonzero:"):
        errors.append("unsafe_probe_not_rejected")

    print(f"phase6_trust_score_updates_status={written['status']}")
    print(f"phase6_trust_score_updates_artifact_path={output_path}")
    print(f"phase6_trust_score_updates_history_path={history_path}")
    print(f"phase6_trust_score_updates_event_log_path={event_log_path}")
    print(f"phase6_trust_score_updates_proposal_state={written['proposal_state']}")
    print(f"phase6_trust_score_updates_source_model_weight_status={written['source_model_weight_status']}")
    print(f"phase6_trust_score_updates_source_approval_state={written['source_approval_state']}")
    print(f"phase6_trust_score_updates_source_approved_evidence_count={written['source_approved_evidence_count']}")
    print(f"phase6_trust_score_updates_canonical_source_score_count={written['canonical_source_score_count']}")
    print(f"phase6_trust_score_updates_supplemental_policy_record_count={written['supplemental_policy_record_count']}")
    print(f"phase6_trust_score_updates_proposal_record_count={written['proposal_record_count']}")
    print(f"phase6_trust_score_updates_active_proposal_count={written['active_proposal_count']}")
    print(f"phase6_trust_score_updates_blocked_proposal_count={written['blocked_proposal_count']}")
    print(f"phase6_trust_score_updates_approved_evidence_count={written['approved_evidence_count']}")
    print(f"phase6_trust_score_updates_trust_score_update_count={written['trust_score_update_count']}")
    print(f"phase6_trust_score_updates_before_score={written['before_score']}")
    print(f"phase6_trust_score_updates_after_score={written['after_score']}")
    print(f"phase6_trust_score_updates_score_delta_total_abs={written['score_delta_total_abs']}")
    print(
        "phase6_trust_score_updates_trust_score_update_proposal_allowed="
        f"{written['trust_score_update_proposal_allowed']}"
    )
    print(f"phase6_trust_score_updates_trust_score_update_proposed={written['trust_score_update_proposed']}")
    print(f"phase6_trust_score_updates_apply_allowed={written['apply_allowed']}")
    print(f"phase6_trust_score_updates_trust_score_update_allowed={written['trust_score_update_allowed']}")
    print(f"phase6_trust_score_updates_trust_score_update_applied={written['trust_score_update_applied']}")
    print(f"phase6_trust_score_updates_active_trust_score_mutated={written['active_trust_score_mutated']}")
    print(f"phase6_trust_score_updates_canonical_rank_mutated={written['canonical_rank_mutated']}")
    print(f"phase6_trust_score_updates_source_quorum_credit_granted={written['source_quorum_credit_granted']}")
    print(f"phase6_trust_score_updates_single_source_verdict_rejected={written['single_source_verdict_rejected']}")
    print(f"phase6_trust_score_updates_supplemental_only_verdict_rejected={written['supplemental_only_verdict_rejected']}")
    print(f"phase6_trust_score_updates_yahoo_finance_score_included={written['yahoo_finance_score_included']}")
    print(
        "phase6_trust_score_updates_preference_mcp_source_quorum_credit_allowed="
        f"{written['preference_mcp_source_quorum_credit_allowed']}"
    )
    print(f"phase6_trust_score_updates_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_trust_score_updates_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_trust_score_updates_knowledge_graph_commit_created="
        f"{written['knowledge_graph_commit_created']}"
    )
    print(f"phase6_trust_score_updates_chroma_write_created={written['chroma_write_created']}")
    print(f"phase6_trust_score_updates_graph_backend_write_created={written['graph_backend_write_created']}")
    print(f"phase6_trust_score_updates_model_weight_update_created={written['model_weight_update_created']}")
    print(f"phase6_trust_score_updates_trust_score_update_created={written['trust_score_update_created']}")
    print(f"phase6_trust_score_updates_policy_mutation_created={written['policy_mutation_created']}")
    print(f"phase6_trust_score_updates_strategy_mutation_created={written['strategy_mutation_created']}")
    print(f"phase6_trust_score_updates_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(f"phase6_trust_score_updates_private_payload_copied_count={written['private_payload_copied_count']}")
    print(f"phase6_trust_score_updates_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_trust_score_updates_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_trust_score_updates_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_trust_score_updates_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_trust_score_updates_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_trust_score_updates_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase6_trust_score_updates_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_trust_score_updates_blocker_count={written['blocker_count']}")
    print(f"phase6_trust_score_updates_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_trust_score_updates_validation_error_count={len(validation_errors)}")
    print(f"phase6_trust_score_updates_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_trust_score_updates_schema_summary_status={schema_summary['status']}")
    print(f"phase6_trust_score_updates_model_weight_error_count={len(model_weight_errors)}")
    print(f"phase6_trust_score_updates_trust_recalculation_error_count={len(trust_errors)}")
    print(f"phase6_trust_score_updates_next_stage={written['recommended_next_stage']}")
    print("phase6_trust_score_updates_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_trust_score_updates_error={error}")
        print("phase6_trust_score_updates_check=failed")
        return 1

    print("phase6_trust_score_updates_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
