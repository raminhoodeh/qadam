#!/usr/bin/env python3
"""Validate Q6-14 shadow strategy runner."""

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
from orchestrator.phase6_readiness import (  # noqa: E402
    build_phase6_readiness,
    validate_phase6_readiness,
)
from orchestrator.phase6_shadow_strategy_runner import (  # noqa: E402
    SOURCE_CLOSED_TRADE_OUTCOME_REF,
    SOURCE_POSITION_MONITOR_REF,
    SOURCE_STRATEGY_UNIVERSE_REF,
    SOURCE_TRUST_SCORE_UPDATES_REF,
    build_phase6_shadow_strategy_runner,
    phase6_shadow_strategy_runner_paths,
    validate_phase6_shadow_strategy_runner,
    write_phase6_shadow_strategy_runner,
)
from orchestrator.phase6_trust_score_updates import (  # noqa: E402
    validate_phase6_trust_score_updates,
)


def _repo_root(settings: Settings) -> Path:
    return Path(settings.runtime_dir).parent.parent


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _source_refs(artifact: dict[str, object]) -> list[str]:
    refs: list[str] = [
        SOURCE_TRUST_SCORE_UPDATES_REF,
        SOURCE_STRATEGY_UNIVERSE_REF,
        SOURCE_POSITION_MONITOR_REF,
        SOURCE_CLOSED_TRADE_OUTCOME_REF,
    ]
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
            and not ref.startswith("data/runtime/phase6_shadow_strategy_replay")
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


def _strategy_authority_snapshot(settings: Settings) -> dict[str, object]:
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
            }
    return {}


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    prebuilt = build_phase6_shadow_strategy_runner(settings=settings)
    before_hashes = _file_hashes(settings, prebuilt)
    strategy_before = _strategy_authority_snapshot(settings)
    output_path, history_path, event_log_path = phase6_shadow_strategy_runner_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase6_readiness(settings=settings)
    readiness_errors = validate_phase6_readiness(readiness)
    schema_summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    trust_updates = _read_json(_repo_root(settings) / SOURCE_TRUST_SCORE_UPDATES_REF)
    trust_errors = validate_phase6_trust_score_updates(trust_updates) if trust_updates else []

    output_path, history_path, event_log_path, written = write_phase6_shadow_strategy_runner(
        prebuilt,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_shadow_strategy_runner(written)
    replay = EventLog(event_log_path, echo=False).replay()
    after_hashes = _file_hashes(settings, prebuilt)
    strategy_after = _strategy_authority_snapshot(settings)
    mutated_refs = [
        ref for ref, before_hash in before_hashes.items() if after_hashes.get(ref) != before_hash
    ]

    runner_authority_probe = deepcopy(written)
    runner_authority_probe["phase6_shadow_strategy_runner_allowed"] = True
    runner_authority_probe["phase6_shadow_strategy_runner_allowed_count"] = 1
    runner_authority_errors = validate_phase6_shadow_strategy_runner(runner_authority_probe)

    replay_allowed_probe = deepcopy(written)
    replay_allowed_probe["shadow_strategy_replay_allowed"] = True
    replay_allowed_probe["shadow_strategy_replay_created"] = True
    replay_allowed_probe["active_replay_count"] = 1
    replay_allowed_errors = validate_phase6_shadow_strategy_runner(replay_allowed_probe)

    candidate_probe = deepcopy(written)
    candidate_probe["trade_candidate_creation_allowed"] = True
    candidate_probe["trade_candidate_created"] = True
    candidate_probe["trade_candidate_created_count"] = 1
    candidate_errors = validate_phase6_shadow_strategy_runner(candidate_probe)

    order_probe = deepcopy(written)
    order_probe["order_creation_allowed"] = True
    order_probe["paper_order_allowed"] = True
    order_probe["paper_order_created"] = True
    order_probe["paper_order_allowed_count"] = 1
    order_errors = validate_phase6_shadow_strategy_runner(order_probe)

    execution_probe = deepcopy(written)
    execution_probe["execution_allowed"] = True
    execution_probe["execution_intent_created"] = True
    execution_probe["broker_post_allowed"] = True
    execution_probe["alpaca_post_allowed"] = True
    execution_probe["execution_allowed_count"] = 1
    execution_probe["broker_post_called_count"] = 1
    execution_probe["alpaca_post_called_count"] = 1
    execution_errors = validate_phase6_shadow_strategy_runner(execution_probe)

    mutation_probe = deepcopy(written)
    mutation_probe["model_weight_update_created"] = True
    mutation_probe["trust_score_update_created"] = True
    mutation_probe["policy_mutation_created"] = True
    mutation_probe["strategy_mutation_created"] = True
    mutation_errors = validate_phase6_shadow_strategy_runner(mutation_probe)

    record_action_probe = deepcopy(written)
    record_action_probe["replay_records"][0]["trade_candidate_created"] = True
    record_action_probe["replay_records"][0]["paper_order_allowed"] = True
    record_action_probe["replay_records"][0]["execution_allowed"] = True
    record_action_errors = validate_phase6_shadow_strategy_runner(record_action_probe)

    record_delta_probe = deepcopy(written)
    record_delta_probe["replay_records"][0]["actual_vs_hypothetical_delta"][
        "trade_candidate_created_delta"
    ] = 1
    record_delta_errors = validate_phase6_shadow_strategy_runner(record_delta_probe)

    record_raw_probe = deepcopy(written)
    record_raw_probe["replay_records"][0]["raw_payload_copied"] = True
    record_raw_probe["raw_payload_copied_count"] = 1
    record_raw_errors = validate_phase6_shadow_strategy_runner(record_raw_probe)

    record_payload_probe = deepcopy(written)
    record_payload_probe["replay_records"][0]["raw_payload"] = {"not_allowed": True}
    record_payload_errors = validate_phase6_shadow_strategy_runner(record_payload_probe)

    record_local_path_probe = deepcopy(written)
    record_local_path_probe["replay_records"][0]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    record_local_path_errors = validate_phase6_shadow_strategy_runner(record_local_path_probe)

    source_state_probe = deepcopy(written)
    source_state_probe["source_trust_score_status"] = "error"
    source_state_probe["source_approval_state"] = "rejected"
    source_state_errors = validate_phase6_shadow_strategy_runner(source_state_probe)

    cockpit_probe = deepcopy(written)
    cockpit_probe["cockpit_safe_status"]["source_refs"] = ["data/runtime/private.json"]
    cockpit_errors = validate_phase6_shadow_strategy_runner(cockpit_probe)

    cockpit_mismatch_probe = deepcopy(written)
    cockpit_mismatch_probe["cockpit_safe_status"]["variant_record_count"] = 999
    cockpit_mismatch_errors = validate_phase6_shadow_strategy_runner(cockpit_mismatch_probe)

    phase5_mutation_probe = deepcopy(written)
    phase5_mutation_probe["phase5_source_artifacts_mutated"] = True
    phase5_mutation_errors = validate_phase6_shadow_strategy_runner(phase5_mutation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_shadow_strategy_runner(proof_credit_probe)

    phase5_proof_probe = deepcopy(written)
    phase5_proof_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_proof_errors = validate_phase6_shadow_strategy_runner(phase5_proof_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 1
    unsafe_errors = validate_phase6_shadow_strategy_runner(unsafe_probe)

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("phase6_artifact_schema_not_valid")
    if trust_errors:
        errors.extend(trust_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if mutated_refs:
        errors.append("q6_14_source_artifacts_mutated")
    if strategy_before != strategy_after:
        errors.append("active_strategy_artifact_mutated")
    if written["status"] != "blocked":
        errors.append("shadow_strategy_runner_status_not_blocked")
    if written["replay_state"] != "blocked_pending_learning_approval":
        errors.append("shadow_strategy_runner_state_not_blocked")
    if written["source_trust_score_status"] != "blocked":
        errors.append("source_trust_score_status_not_blocked")
    if written["source_approval_state"] != "deferred":
        errors.append("source_approval_state_not_deferred")
    if written["source_approved_evidence_count"] != 0:
        errors.append("approved_evidence_count_unexpected")
    if written["approved_fact_count"] != 0:
        errors.append("approved_fact_count_not_zero")
    if written["variant_record_count"] != 3:
        errors.append("variant_record_count_not_three")
    if written["active_replay_count"] != 0:
        errors.append("active_replay_count_not_zero")
    if written["blocked_replay_count"] != 3:
        errors.append("blocked_replay_count_not_three")
    if written["evaluated_variant_count"] != 0:
        errors.append("evaluated_variant_count_not_zero")
    if written["actual_vs_hypothetical_comparison_count"] != 3:
        errors.append("comparison_count_not_three")
    if written["evaluated_comparison_count"] != 0:
        errors.append("evaluated_comparison_count_not_zero")
    if written["replay_output_exists"] is not True:
        errors.append("replay_output_missing")
    if written["shadow_strategy_replay_allowed"] is not False:
        errors.append("shadow_strategy_replay_allowed")
    if written["shadow_strategy_replay_created"] is not False:
        errors.append("shadow_strategy_replay_created")
    for key in (
        "trade_candidate_creation_allowed",
        "trade_candidate_created",
        "order_creation_allowed",
        "paper_order_allowed",
        "paper_order_created",
        "execution_allowed",
        "execution_intent_created",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
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
    ):
        if written[key] is not False:
            errors.append(f"{key}_not_false")
    for key in (
        "trade_candidate_created_count",
        "paper_order_allowed_count",
        "execution_allowed_count",
        "paper_order_created_count",
        "execution_intent_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
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

    if not _has_error(runner_authority_errors, "authority_enabled:phase6_shadow_strategy_runner_allowed"):
        errors.append("runner_authority_probe_not_rejected")
    if "shadow_strategy_runner_unapproved_replay_allowed" not in replay_allowed_errors:
        errors.append("replay_allowed_probe_not_rejected")
    if "shadow_strategy_runner_unapproved_replay_created" not in replay_allowed_errors:
        errors.append("replay_created_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:trade_candidate_creation_allowed" not in candidate_errors:
        errors.append("candidate_creation_allowed_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:trade_candidate_created" not in candidate_errors:
        errors.append("candidate_created_probe_not_rejected")
    if not _has_error(candidate_errors, "shadow_strategy_runner_action_count_nonzero:"):
        errors.append("candidate_count_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:order_creation_allowed" not in order_errors:
        errors.append("order_creation_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:paper_order_allowed" not in order_errors:
        errors.append("paper_order_allowed_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:paper_order_created" not in order_errors:
        errors.append("paper_order_created_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:execution_allowed" not in execution_errors:
        errors.append("execution_allowed_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:execution_intent_created" not in execution_errors:
        errors.append("execution_intent_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:broker_post_allowed" not in execution_errors:
        errors.append("broker_post_allowed_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:alpaca_post_allowed" not in execution_errors:
        errors.append("alpaca_post_allowed_probe_not_rejected")
    if not _has_error(execution_errors, "shadow_strategy_runner_action_count_nonzero:"):
        errors.append("execution_count_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:model_weight_update_created" not in mutation_errors:
        errors.append("model_weight_mutation_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:trust_score_update_created" not in mutation_errors:
        errors.append("trust_score_mutation_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:policy_mutation_created" not in mutation_errors:
        errors.append("policy_mutation_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:strategy_mutation_created" not in mutation_errors:
        errors.append("strategy_mutation_probe_not_rejected")
    if not _has_error(record_action_errors, "replay_record_action_enabled:"):
        errors.append("record_action_probe_not_rejected")
    if not _has_error(record_delta_errors, "replay_record_action_delta_nonzero:"):
        errors.append("record_delta_probe_not_rejected")
    if not _has_error(record_raw_errors, "shadow_strategy_runner_private_or_local_payload_exposed"):
        errors.append("record_raw_probe_not_rejected")
    if "replay_record_forbidden_payload" not in record_payload_errors:
        errors.append("record_payload_probe_not_rejected")
    if "replay_record_local_source_ref" not in record_local_path_errors:
        errors.append("record_local_path_probe_not_rejected")
    if "source_trust_score_status_invalid" not in source_state_errors:
        errors.append("source_status_probe_not_rejected")
    if "source_approval_state_invalid" not in source_state_errors:
        errors.append("source_approval_probe_not_rejected")
    if not _has_error(cockpit_errors, "cockpit_safe_status_forbidden_fields:"):
        errors.append("cockpit_probe_not_rejected")
    if "cockpit_safe_status_mismatch:variant_record_count" not in cockpit_mismatch_errors:
        errors.append("cockpit_mismatch_probe_not_rejected")
    if (
        "shadow_strategy_runner_write_enabled:phase5_source_artifacts_mutated"
        not in phase5_mutation_errors
    ):
        errors.append("phase5_mutation_probe_not_rejected")
    if "shadow_strategy_runner_write_enabled:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_proof_errors:
        errors.append("phase5_proof_probe_not_rejected")
    if not _has_error(unsafe_errors, "shadow_strategy_runner_unsafe_count_nonzero:"):
        errors.append("unsafe_probe_not_rejected")

    print(f"phase6_shadow_strategy_runner_status={written['status']}")
    print(f"phase6_shadow_strategy_runner_artifact_path={output_path}")
    print(f"phase6_shadow_strategy_runner_history_path={history_path}")
    print(f"phase6_shadow_strategy_runner_event_log_path={event_log_path}")
    print(f"phase6_shadow_strategy_runner_replay_state={written['replay_state']}")
    print(f"phase6_shadow_strategy_runner_source_trust_score_status={written['source_trust_score_status']}")
    print(f"phase6_shadow_strategy_runner_source_approval_state={written['source_approval_state']}")
    print(
        "phase6_shadow_strategy_runner_source_approved_evidence_count="
        f"{written['source_approved_evidence_count']}"
    )
    print(f"phase6_shadow_strategy_runner_approved_fact_count={written['approved_fact_count']}")
    print(f"phase6_shadow_strategy_runner_variant_record_count={written['variant_record_count']}")
    print(f"phase6_shadow_strategy_runner_active_replay_count={written['active_replay_count']}")
    print(f"phase6_shadow_strategy_runner_blocked_replay_count={written['blocked_replay_count']}")
    print(f"phase6_shadow_strategy_runner_evaluated_variant_count={written['evaluated_variant_count']}")
    print(
        "phase6_shadow_strategy_runner_actual_vs_hypothetical_comparison_count="
        f"{written['actual_vs_hypothetical_comparison_count']}"
    )
    print(f"phase6_shadow_strategy_runner_evaluated_comparison_count={written['evaluated_comparison_count']}")
    print(f"phase6_shadow_strategy_runner_replay_output_exists={written['replay_output_exists']}")
    print(
        "phase6_shadow_strategy_runner_shadow_strategy_replay_allowed="
        f"{written['shadow_strategy_replay_allowed']}"
    )
    print(
        "phase6_shadow_strategy_runner_shadow_strategy_replay_created="
        f"{written['shadow_strategy_replay_created']}"
    )
    print(
        "phase6_shadow_strategy_runner_trade_candidate_creation_allowed="
        f"{written['trade_candidate_creation_allowed']}"
    )
    print(f"phase6_shadow_strategy_runner_trade_candidate_created={written['trade_candidate_created']}")
    print(
        "phase6_shadow_strategy_runner_trade_candidate_created_count="
        f"{written['trade_candidate_created_count']}"
    )
    print(f"phase6_shadow_strategy_runner_order_creation_allowed={written['order_creation_allowed']}")
    print(f"phase6_shadow_strategy_runner_paper_order_allowed={written['paper_order_allowed']}")
    print(f"phase6_shadow_strategy_runner_paper_order_allowed_count={written['paper_order_allowed_count']}")
    print(f"phase6_shadow_strategy_runner_paper_order_created={written['paper_order_created']}")
    print(f"phase6_shadow_strategy_runner_paper_order_created_count={written['paper_order_created_count']}")
    print(f"phase6_shadow_strategy_runner_execution_allowed={written['execution_allowed']}")
    print(f"phase6_shadow_strategy_runner_execution_allowed_count={written['execution_allowed_count']}")
    print(f"phase6_shadow_strategy_runner_execution_intent_created={written['execution_intent_created']}")
    print(
        "phase6_shadow_strategy_runner_execution_intent_created_count="
        f"{written['execution_intent_created_count']}"
    )
    print(f"phase6_shadow_strategy_runner_broker_post_allowed={written['broker_post_allowed']}")
    print(f"phase6_shadow_strategy_runner_alpaca_post_allowed={written['alpaca_post_allowed']}")
    print(f"phase6_shadow_strategy_runner_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase6_shadow_strategy_runner_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase6_shadow_strategy_runner_learning_write_created={written['learning_write_created']}")
    print(
        "phase6_shadow_strategy_runner_knowledge_graph_write_created="
        f"{written['knowledge_graph_write_created']}"
    )
    print(
        "phase6_shadow_strategy_runner_knowledge_graph_commit_created="
        f"{written['knowledge_graph_commit_created']}"
    )
    print(f"phase6_shadow_strategy_runner_chroma_write_created={written['chroma_write_created']}")
    print(f"phase6_shadow_strategy_runner_graph_backend_write_created={written['graph_backend_write_created']}")
    print(f"phase6_shadow_strategy_runner_model_weight_update_created={written['model_weight_update_created']}")
    print(f"phase6_shadow_strategy_runner_trust_score_update_created={written['trust_score_update_created']}")
    print(f"phase6_shadow_strategy_runner_policy_mutation_created={written['policy_mutation_created']}")
    print(f"phase6_shadow_strategy_runner_strategy_mutation_created={written['strategy_mutation_created']}")
    print(f"phase6_shadow_strategy_runner_raw_payload_copied_count={written['raw_payload_copied_count']}")
    print(
        "phase6_shadow_strategy_runner_private_payload_copied_count="
        f"{written['private_payload_copied_count']}"
    )
    print(f"phase6_shadow_strategy_runner_local_path_exposed_count={written['local_path_exposed_count']}")
    print(f"phase6_shadow_strategy_runner_secret_ref_exposed_count={written['secret_ref_exposed_count']}")
    print(f"phase6_shadow_strategy_runner_source_hash_mutation_count={len(mutated_refs)}")
    print(
        "phase6_shadow_strategy_runner_phase5_source_artifacts_mutated="
        f"{written['phase5_source_artifacts_mutated']}"
    )
    print(
        "phase6_shadow_strategy_runner_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase6_shadow_strategy_runner_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase6_shadow_strategy_runner_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_shadow_strategy_runner_blocker_count={written['blocker_count']}")
    print(f"phase6_shadow_strategy_runner_event_log_replay_total_events={replay['total_events']}")
    print(f"phase6_shadow_strategy_runner_validation_error_count={len(validation_errors)}")
    print(f"phase6_shadow_strategy_runner_readiness_error_count={len(readiness_errors)}")
    print(f"phase6_shadow_strategy_runner_schema_summary_status={schema_summary['status']}")
    print(f"phase6_shadow_strategy_runner_trust_score_error_count={len(trust_errors)}")
    print(f"phase6_shadow_strategy_runner_next_stage={written['recommended_next_stage']}")
    print("phase6_shadow_strategy_runner_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_shadow_strategy_runner_error={error}")
        print("phase6_shadow_strategy_runner_check=failed")
        return 1

    print("phase6_shadow_strategy_runner_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
