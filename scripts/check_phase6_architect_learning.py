#!/usr/bin/env python3
"""Validate Q6-15 Architect learning summary."""

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
from orchestrator.phase6_architect_learning import (  # noqa: E402
    SOURCE_SHADOW_REPLAY_REF,
    SOURCE_STRATEGY_UNIVERSE_REF,
    build_phase6_architect_learning,
    phase6_architect_learning_paths,
    validate_phase6_architect_learning,
    write_phase6_architect_learning,
)
from orchestrator.phase6_artifacts import (  # noqa: E402
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
)
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)
from orchestrator.phase6_shadow_strategy_runner import (  # noqa: E402
    validate_phase6_shadow_strategy_runner,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = [SOURCE_SHADOW_REPLAY_REF, SOURCE_STRATEGY_UNIVERSE_REF]
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
            and not ref.startswith("data/runtime/phase6_architect_learning_summary")
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


def _strategy_snapshot(settings: Settings) -> dict[str, object]:
    artifact = _read_json(_repo_root(settings) / SOURCE_STRATEGY_UNIVERSE_REF)
    for candidate in artifact.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("candidate_key") == "crude_oil_energy_security_disruption":
            return {
                "trade_candidate_created": candidate.get("trade_candidate_created"),
                "paper_order_allowed": candidate.get("paper_order_allowed"),
                "execution_allowed": candidate.get("execution_allowed"),
                "broker_write_allowed": candidate.get("broker_write_allowed"),
                "live_capital_enabled": candidate.get("live_capital_enabled"),
                "model_weights": candidate.get("model_weights"),
                "source_weights": candidate.get("source_weights"),
                "risk_assumptions": candidate.get("risk_assumptions"),
                "no_trade_conditions": candidate.get("no_trade_conditions"),
            }
    return {}


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    prebuilt = build_phase6_architect_learning(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    strategy_before = _strategy_snapshot(settings)
    output_path, history_path, event_log_path = phase6_architect_learning_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    shadow_replay = _read_json(_repo_root(settings) / SOURCE_SHADOW_REPLAY_REF)
    shadow_errors = validate_phase6_shadow_strategy_runner(shadow_replay) if shadow_replay else []

    output_path, history_path, event_log_path, written = write_phase6_architect_learning(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_architect_learning(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    strategy_after = _strategy_snapshot(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    architect_authority_probe = deepcopy(written)
    architect_authority_probe["phase6_architect_policy_mutation_allowed"] = True
    architect_authority_probe["phase6_policy_mutation_allowed"] = True
    architect_authority_probe["phase6_policy_mutation_allowed_count"] = 1
    architect_authority_errors = validate_phase6_architect_learning(architect_authority_probe)

    recommendation_probe = deepcopy(written)
    recommendation_probe["recommendation_records"][0]["recommendation_allowed"] = True
    recommendation_probe["active_recommendation_count"] = 1
    recommendation_errors = validate_phase6_architect_learning(recommendation_probe)

    policy_probe = deepcopy(written)
    policy_probe["policy_mutation_allowed"] = True
    policy_probe["policy_mutation_created"] = True
    policy_errors = validate_phase6_architect_learning(policy_probe)

    strategy_probe = deepcopy(written)
    strategy_probe["strategy_mutation_allowed"] = True
    strategy_probe["strategy_mutation_created"] = True
    strategy_errors = validate_phase6_architect_learning(strategy_probe)

    risk_probe = deepcopy(written)
    risk_probe["risk_limit_update_allowed"] = True
    risk_probe["risk_limit_update_created"] = True
    risk_errors = validate_phase6_architect_learning(risk_probe)

    source_model_trust_probe = deepcopy(written)
    source_model_trust_probe["source_weight_update_allowed"] = True
    source_model_trust_probe["source_weight_update_created"] = True
    source_model_trust_probe["model_weight_update_allowed"] = True
    source_model_trust_probe["model_weight_update_created"] = True
    source_model_trust_probe["trust_score_update_allowed"] = True
    source_model_trust_probe["trust_score_update_created"] = True
    source_model_trust_errors = validate_phase6_architect_learning(source_model_trust_probe)

    record_action_probe = deepcopy(written)
    record_action_probe["recommendation_records"][0]["apply_allowed"] = True
    record_action_probe["recommendation_records"][0]["policy_mutation_allowed"] = True
    record_action_probe["recommendation_records"][0]["strategy_mutation_allowed"] = True
    record_action_errors = validate_phase6_architect_learning(record_action_probe)

    record_raw_probe = deepcopy(written)
    record_raw_probe["recommendation_records"][0]["raw_payload_copied"] = True
    record_raw_probe["raw_payload_copied_count"] = 1
    record_raw_errors = validate_phase6_architect_learning(record_raw_probe)

    record_payload_probe = deepcopy(written)
    record_payload_probe["recommendation_records"][0]["raw_payload"] = {"not_allowed": True}
    record_payload_errors = validate_phase6_architect_learning(record_payload_probe)

    record_local_path_probe = deepcopy(written)
    record_local_path_probe["recommendation_records"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    record_local_path_errors = validate_phase6_architect_learning(record_local_path_probe)

    source_state_probe = deepcopy(written)
    source_state_probe["source_shadow_replay_status"] = "error"
    source_state_probe["source_approval_state"] = "rejected"
    source_state_errors = validate_phase6_architect_learning(source_state_probe)

    cockpit_probe = deepcopy(written)
    cockpit_probe["cockpit_safe_status"]["source_refs"] = ["data/runtime/private.json"]
    cockpit_errors = validate_phase6_architect_learning(cockpit_probe)

    cockpit_mismatch_probe = deepcopy(written)
    cockpit_mismatch_probe["cockpit_safe_status"]["recommendation_count"] = 999
    cockpit_mismatch_errors = validate_phase6_architect_learning(cockpit_mismatch_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_architect_learning(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_architect_learning(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_architect_learning(phase5_proof_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_architect_learning(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if shadow_errors:
        errors.extend(shadow_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_15_source_artifacts_mutated")
    if strategy_before != strategy_after:
        errors.append("active_strategy_artifact_mutated")
    if written["status"] != "blocked":
        errors.append("architect_learning_status_not_blocked")
    if written["summary_state"] != "blocked_pending_learning_approval":
        errors.append("architect_learning_state_not_blocked")
    if written["source_shadow_replay_status"] != "blocked":
        errors.append("source_shadow_replay_status_not_blocked")
    if written["source_approval_state"] != "deferred":
        errors.append("source_approval_state_not_deferred")
    if written["source_approved_fact_count"] != 0:
        errors.append("source_approved_fact_count_unexpected")
    if written["approved_fact_count"] != 0:
        errors.append("approved_fact_count_not_zero")
    if written["architect_summary_created"] is not True:
        errors.append("architect_summary_not_created")
    if written["recommendation_count"] != 4:
        errors.append("recommendation_count_not_four")
    if written["recommendation_record_count"] != 4:
        errors.append("recommendation_record_count_not_four")
    if written["active_recommendation_count"] != 0:
        errors.append("active_recommendation_count_not_zero")
    if written["blocked_recommendation_count"] != 4:
        errors.append("blocked_recommendation_count_not_four")
    if written["governance_pending_count"] != 4:
        errors.append("governance_pending_count_not_four")
    for key in (
        "policy_recommendation_count",
        "strategy_recommendation_count",
        "risk_limit_recommendation_count",
        "source_model_trust_recommendation_count",
    ):
        if written[key] != 1:
            errors.append(f"{key}_not_one")
    for key in (
        "recommendation_apply_allowed",
        "policy_mutation_allowed",
        "policy_mutation_created",
        "strategy_mutation_allowed",
        "strategy_mutation_created",
        "risk_limit_update_allowed",
        "risk_limit_update_created",
        "source_weight_update_allowed",
        "source_weight_update_created",
        "model_weight_update_allowed",
        "model_weight_update_created",
        "trust_score_update_allowed",
        "trust_score_update_created",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "phase5_source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
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
    if replay["total_events"] != 1:
        errors.append("event_log_replay_count_mismatch")

    if not _has_error(architect_authority_errors, "authority_enabled:phase6_architect_policy_mutation_allowed"):
        errors.append("architect_authority_probe_not_rejected")
    if not _has_error(architect_authority_errors, "authority_enabled:phase6_policy_mutation_allowed"):
        errors.append("policy_authority_probe_not_rejected")
    if "architect_learning_unapproved_active_recommendations" not in recommendation_errors:
        errors.append("recommendation_probe_not_rejected")
    if "architect_learning_write_enabled:policy_mutation_allowed" not in policy_errors:
        errors.append("policy_mutation_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:policy_mutation_created" not in policy_errors:
        errors.append("policy_mutation_created_probe_not_rejected")
    if "architect_learning_write_enabled:strategy_mutation_allowed" not in strategy_errors:
        errors.append("strategy_mutation_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:strategy_mutation_created" not in strategy_errors:
        errors.append("strategy_mutation_created_probe_not_rejected")
    if "architect_learning_write_enabled:risk_limit_update_allowed" not in risk_errors:
        errors.append("risk_limit_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:risk_limit_update_created" not in risk_errors:
        errors.append("risk_limit_created_probe_not_rejected")
    if "architect_learning_write_enabled:source_weight_update_allowed" not in source_model_trust_errors:
        errors.append("source_weight_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:source_weight_update_created" not in source_model_trust_errors:
        errors.append("source_weight_created_probe_not_rejected")
    if "architect_learning_write_enabled:model_weight_update_allowed" not in source_model_trust_errors:
        errors.append("model_weight_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:model_weight_update_created" not in source_model_trust_errors:
        errors.append("model_weight_created_probe_not_rejected")
    if "architect_learning_write_enabled:trust_score_update_allowed" not in source_model_trust_errors:
        errors.append("trust_score_allowed_probe_not_rejected")
    if "architect_learning_write_enabled:trust_score_update_created" not in source_model_trust_errors:
        errors.append("trust_score_created_probe_not_rejected")
    if not _has_error(record_action_errors, "recommendation_record_action_enabled:"):
        errors.append("record_action_probe_not_rejected")
    if not _has_error(record_raw_errors, "architect_learning_private_or_local_payload_exposed"):
        errors.append("record_raw_probe_not_rejected")
    if "recommendation_record_forbidden_payload" not in record_payload_errors:
        errors.append("record_payload_probe_not_rejected")
    if "recommendation_record_local_source_ref" not in record_local_path_errors:
        errors.append("record_local_path_probe_not_rejected")
    if "source_shadow_replay_status_invalid" not in source_state_errors:
        errors.append("source_status_probe_not_rejected")
    if "source_approval_state_invalid" not in source_state_errors:
        errors.append("source_approval_probe_not_rejected")
    if not _has_error(cockpit_errors, "cockpit_safe_status_forbidden_fields:"):
        errors.append("cockpit_probe_not_rejected")
    if "cockpit_safe_status_mismatch:recommendation_count" not in cockpit_mismatch_errors:
        errors.append("cockpit_mismatch_probe_not_rejected")
    if "architect_learning_write_enabled:phase5_source_artifacts_mutated" not in phase5_mutation_errors:
        errors.append("phase5_mutation_probe_not_rejected")
    if "architect_learning_write_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(unsafe_errors, "architect_learning_unsafe_count_nonzero:"):
        errors.append("unsafe_probe_not_rejected")

    print(f"phase6_architect_learning_status={written['status']}")
    print(f"phase6_architect_learning_artifact_path={output_path}")
    print(f"phase6_architect_learning_history_path={history_path}")
    print(f"phase6_architect_learning_event_log_path={event_log_path}")
    print(f"phase6_architect_learning_summary_state={written['summary_state']}")
    print(f"phase6_architect_learning_source_shadow_replay_status={written['source_shadow_replay_status']}")
    print(f"phase6_architect_learning_source_approval_state={written['source_approval_state']}")
    print(f"phase6_architect_learning_source_approved_fact_count={written['source_approved_fact_count']}")
    print(f"phase6_architect_learning_approved_fact_count={written['approved_fact_count']}")
    print(f"phase6_architect_learning_architect_summary_created={written['architect_summary_created']}")
    print(f"phase6_architect_learning_recommendation_count={written['recommendation_count']}")
    print(f"phase6_architect_learning_recommendation_record_count={written['recommendation_record_count']}")
    print(f"phase6_architect_learning_active_recommendation_count={written['active_recommendation_count']}")
    print(f"phase6_architect_learning_blocked_recommendation_count={written['blocked_recommendation_count']}")
    print(f"phase6_architect_learning_governance_pending_count={written['governance_pending_count']}")
    print(f"phase6_architect_learning_policy_recommendation_count={written['policy_recommendation_count']}")
    print(f"phase6_architect_learning_strategy_recommendation_count={written['strategy_recommendation_count']}")
    print(
        "phase6_architect_learning_risk_limit_recommendation_count="
        f"{written['risk_limit_recommendation_count']}"
    )
    print(
        "phase6_architect_learning_source_model_trust_recommendation_count="
        f"{written['source_model_trust_recommendation_count']}"
    )
    print(f"phase6_architect_learning_recommendation_apply_allowed={written['recommendation_apply_allowed']}")
    print(f"phase6_architect_learning_policy_mutation_allowed={written['policy_mutation_allowed']}")
    print(f"phase6_architect_learning_policy_mutation_created={written['policy_mutation_created']}")
    print(f"phase6_architect_learning_strategy_mutation_allowed={written['strategy_mutation_allowed']}")
    print(f"phase6_architect_learning_strategy_mutation_created={written['strategy_mutation_created']}")
    print(f"phase6_architect_learning_risk_limit_update_allowed={written['risk_limit_update_allowed']}")
    print(f"phase6_architect_learning_risk_limit_update_created={written['risk_limit_update_created']}")
    print(f"phase6_architect_learning_source_weight_update_allowed={written['source_weight_update_allowed']}")
    print(f"phase6_architect_learning_source_weight_update_created={written['source_weight_update_created']}")
    print(f"phase6_architect_learning_model_weight_update_allowed={written['model_weight_update_allowed']}")
    print(f"phase6_architect_learning_model_weight_update_created={written['model_weight_update_created']}")
    print(f"phase6_architect_learning_trust_score_update_allowed={written['trust_score_update_allowed']}")
    print(f"phase6_architect_learning_trust_score_update_created={written['trust_score_update_created']}")
    print(f"phase6_architect_learning_learning_write_created={written['learning_write_created']}")
    print(f"phase6_architect_learning_knowledge_graph_write_created={written['knowledge_graph_write_created']}")
    print(f"phase6_architect_learning_knowledge_graph_commit_created={written['knowledge_graph_commit_created']}")
    print(f"phase6_architect_learning_chroma_write_created={written['chroma_write_created']}")
    print(f"phase6_architect_learning_graph_backend_write_created={written['graph_backend_write_created']}")
    print(f"phase6_architect_learning_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(f"phase6_architect_learning_private_payload_copied_count={written['private_payload_copied_count']}")
    print(f"phase6_architect_learning_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_architect_learning_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_architect_learning_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_architect_learning_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_architect_learning_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(f"phase6_architect_learning_phase7_proof_credit_allowed={written['phase7_proof_credit_allowed']}")
    print(f"phase6_architect_learning_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_architect_learning_blocker_count={written['blocker_count']}")
    print(f"phase6_architect_learning_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_architect_learning_validation_error_count={len(validation_errors)}")
    print(f"phase6_architect_learning_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_architect_learning_schema_summary_status={schema_summary['status']}")
    print(f"phase6_architect_learning_shadow_replay_error_count={len(shadow_errors)}")
    print(f"phase6_architect_learning_next_stage={written['recommended_next_stage']}")
    print("phase6_architect_learning_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_architect_learning_error={error}")
        print("phase6_architect_learning_check=failed")
        return 1

    print("phase6_architect_learning_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
