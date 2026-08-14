"""QEG-5 immutable hypothesis, attempt and negative-result memory."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, sha256_json, write_json_atomic
from orchestrator.qadam_qeg_common import EXPERIMENT_SUMMARY_ARTIFACT, qeg_authority, stable_id, write_phase_status
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore

MEMORY_INDEX_ARTIFACT = "qadam_experiment_memory_index.json"

INPUTS = {
    "pattern_score": "qadam_pattern_score_v3_records.jsonl",
    "edge": "qadam_edge_registry.jsonl",
    "shadow_decision": "qadam_forward_shadow_decisions.jsonl",
    "shadow_outcome": "qadam_forward_shadow_outcomes.jsonl",
    "active_outcome": "qadam_active_discovery_outcomes.jsonl",
    "promotion_proposal": "qadam_strategy_promotion_proposals.jsonl",
    "admission_decision": "qadam_strategy_admission_decisions.jsonl",
}


def attempt_fingerprint(record: dict[str, Any]) -> str:
    immutable_question = {
        key: record.get(key)
        for key in (
            "research_goal_id", "hypothesis_id", "strategy_family_id", "instrument",
            "direction", "direction_hypothesis", "horizon", "horizon_hypothesis",
            "edge_id", "policy_version", "model_version",
        )
        if record.get(key) is not None
    }
    immutable_question["source_keys"] = sorted(
        {
            str(item.get("source_key"))
            for item in record.get("feature_inputs", [])
            if isinstance(item, dict) and item.get("source_key")
        }
    )
    return sha256_json(immutable_question)


def novelty_disposition(fingerprint: str, existing: Iterable[dict[str, Any]]) -> str:
    matches = [row for row in existing if row.get("attempt_fingerprint") == fingerprint]
    if not matches:
        return "novel_attempt"
    if any(row.get("outcome_state") in {"rejected", "failed", "negative"} for row in matches):
        return "previously_rejected_same_reason"
    return "duplicate_attempt"


def _negative_numeric(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return float(value) < 0
    except (TypeError, ValueError):
        return False


def preregister_experiment(definition: dict[str, Any], existing: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    fingerprint = attempt_fingerprint(definition)
    required = (
        "research_goal_id", "economic_mechanism", "instrument", "expected_horizon",
        "falsifier", "baseline_model", "success_criteria", "failure_criteria",
    )
    missing = [key for key in required if not definition.get(key)]
    payload = {
        "experiment_id": stable_id("qeg-experiment", fingerprint),
        "attempt_fingerprint": fingerprint,
        "preregistered_at": now_iso(),
        "preregistered_before_outcome": True,
        "definition": deepcopy(definition),
        "novelty_disposition": novelty_disposition(fingerprint, existing),
        "missing_required_fields": missing,
        "test_allowed": not missing,
        "holdout_read_allowed": False,
        "authority": qeg_authority(),
    }
    return payload


def build_experiment_memory(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    records: list[dict[str, Any]] = []
    graph_records: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for record_class, filename in INPUTS.items():
        for row in read_jsonl(runtime / filename):
            source_id = str(
                row.get("score_id") or row.get("edge_id") or row.get("decision_id")
                or row.get("outcome_id") or row.get("outcome_record_id")
                or row.get("proposal_id") or row.get("admission_decision_id")
                or stable_id("legacy-record", filename, sha256_json(row))
            )
            unique = f"{filename}:{source_id}"
            if unique in seen_source_ids:
                continue
            seen_source_ids.add(unique)
            negative = bool(
                row.get("negative_control")
                or row.get("direction_correct") is False
                or _negative_numeric(row.get("net_return_after_costs"))
                or str(row.get("final_state") or row.get("decision") or "").startswith(("hold", "veto", "reject"))
            )
            memory = {
                "memory_id": stable_id("qeg-memory", unique),
                "source_artifact": f"data/runtime/{filename}",
                "source_record_id": source_id,
                "record_class": record_class,
                "attempt_fingerprint": attempt_fingerprint(row),
                "preregistration_state": (
                    "recorded_before_outcome"
                    if row.get("decision_frozen_before_outcome") or row.get("preregistered_before_outcome")
                    else "legacy_preregistration_not_proven"
                ),
                "outcome_state": "negative" if negative else "observed",
                "failure_reason": row.get("typed_expiry_reason") or row.get("rejection_reasons") or row.get("measurement_state"),
                "regime": row.get("regime") or row.get("market_regime") or "unclassified",
                "instrument": row.get("instrument"),
                "strategy_family_id": row.get("strategy_family_id"),
                "generated_at": row.get("generated_at"),
                "retest_condition": (
                    "new independent provider evidence or genuinely new regime"
                    if negative else "outcome maturity or independent replication"
                ),
                "independent_evidence_credit": False,
                "authority": qeg_authority(),
            }
            records.append(memory)
            node_type = {
                "pattern_score": "pattern_relationship",
                "edge": "validated_edge",
                "shadow_decision": "shadow_decision",
                "shadow_outcome": "experiment_result",
                "active_outcome": "experiment_result",
                "promotion_proposal": "improvement_proposal",
                "admission_decision": "strategy_version",
            }[record_class]
            layer = "governed" if record_class in {"admission_decision"} else "tested"
            graph_records.append(
                build_node(
                    node_type, memory["memory_id"], layer=layer,
                    evidence_state="governed_projection" if layer == "governed" else "research_only",
                    payload=memory, available_at=row.get("generated_at"),
                    source_artifact=memory["source_artifact"],
                )
            )
    fingerprint_counts = Counter(row["attempt_fingerprint"] for row in records)
    duplicate_count = sum(count - 1 for count in fingerprint_counts.values() if count > 1)
    store = TemporalGraphStore(settings)
    append = store.append(graph_records) if graph_records else {"written": 0, "duplicates": 0}
    manifest = store.rebuild()
    class_counts = Counter(row["record_class"] for row in records)
    outcome_counts = Counter(row["outcome_state"] for row in records)
    summary = {
        "schema_version": "qadam_experiment_memory.v1",
        "artifact_type": "qadam_experiment_memory_summary",
        "generated_at": now_iso(),
        "status": "complete",
        "memory_record_count": len(records),
        "record_class_counts": dict(sorted(class_counts.items())),
        "outcome_state_counts": dict(sorted(outcome_counts.items())),
        "negative_result_count": outcome_counts.get("negative", 0),
        "duplicate_fingerprint_count": duplicate_count,
        "duplicate_records_grant_independent_credit": False,
        "legacy_records_without_proven_preregistration_count": sum(
            row["preregistration_state"] == "legacy_preregistration_not_proven" for row in records
        ),
        "graph_records_written": append["written"],
        "graph_generation_id": manifest.get("generation_id"),
        "authority": qeg_authority(),
        "blockers": [],
    }
    write_json_atomic(runtime / MEMORY_INDEX_ARTIFACT, {"generated_at": now_iso(), "records": records})
    write_json_atomic(runtime / EXPERIMENT_SUMMARY_ARTIFACT, summary)
    write_phase_status(
        "QEG-5", status="passed", implementation_complete=True,
        empirical_state="persistent_experiment_memory_built",
        artifacts=[MEMORY_INDEX_ARTIFACT, EXPERIMENT_SUMMARY_ARTIFACT], settings=settings,
    )
    return summary, []


def validate_experiment_memory(settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    index = read_json(runtime / MEMORY_INDEX_ARTIFACT)
    records = index.get("records") if isinstance(index.get("records"), list) else []
    errors: list[str] = []
    if not records:
        errors.append("experiment_memory_empty")
    probe = preregister_experiment(
        {
            "research_goal_id": "qeg-probe",
            "economic_mechanism": "provider event precedes listed-market repricing",
            "instrument": "SPY",
            "expected_horizon": "3d_forward",
            "falsifier": "no repeatable return difference",
            "baseline_model": "persistence",
            "success_criteria": "positive untouched net expectancy",
            "failure_criteria": "holdout or cost failure",
        },
        records,
    )
    if not probe["test_allowed"] or not probe["preregistered_before_outcome"]:
        errors.append("preregistration_probe_failed")
    duplicate = preregister_experiment(probe["definition"], [probe])
    if duplicate["novelty_disposition"] != "duplicate_attempt":
        errors.append("duplicate_probe_not_detected")
    return errors
