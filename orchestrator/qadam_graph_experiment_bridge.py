"""QEG-8 bridge from graph questions to frozen statistical experiments.

The bridge preregisters future tests and links older results as prior context.
It never retroactively treats an old test as validation of a newly defined
graph path.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_experiment_memory import preregister_experiment
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import (
    ACTIONABILITY_QUEUE_ARTIFACT,
    EXPERIMENT_BRIDGE_ARTIFACT,
    GRAPH_MANIFEST_ARTIFACT,
    PATTERN_CANDIDATES_ARTIFACT,
    qeg_authority,
    stable_id,
    write_phase_status,
)
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore


def _candidate_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    return {str(row.get("pattern_relationship_id")): row for row in rows if row.get("pattern_relationship_id")}


def _prior_matches(candidate: dict[str, Any], prior: list[dict[str, Any]]) -> list[dict[str, Any]]:
    instrument = str(candidate.get("instrument") or "")
    family = str(candidate.get("strategy_family_id") or "")
    horizon = str(candidate.get("horizon") or "5d_forward")
    exact = [
        row for row in prior
        if str(row.get("instrument") or "") == instrument
        and str(row.get("strategy_family_id") or "") == family
        and str(row.get("horizon") or "") == horizon
    ]
    if not exact:
        exact = [
            row for row in prior
            if str(row.get("instrument") or "") == instrument
            and str(row.get("horizon") or "") == horizon
        ]
    return exact[:25]


def build_graph_experiment_bridge(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    graph = read_json(runtime / GRAPH_MANIFEST_ARTIFACT)
    patterns = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    queue = read_json(runtime / ACTIONABILITY_QUEUE_ARTIFACT)
    registry = read_json(runtime / "qadam_backtest_completion_experiment_registry.json")
    statistical = read_json(runtime / "qadam_statistical_backtest_checks.json")
    previous_bridge = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    previous_experiments = (
        previous_bridge.get("experiments")
        if isinstance(previous_bridge.get("experiments"), list)
        else []
    )
    previous_by_fingerprint = {
        str(row.get("attempt_fingerprint")): row
        for row in previous_experiments
        if row.get("attempt_fingerprint")
    }
    prior = registry.get("experiments") if isinstance(registry.get("experiments"), list) else []
    candidates = _candidate_index(patterns)
    queue_rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    graph_generation = str(graph.get("generation_id") or "")
    query_cutoff = generated_at
    experiments: list[dict[str, Any]] = []
    graph_records: list[dict[str, Any]] = []
    seen_preregistrations: list[dict[str, Any]] = list(previous_experiments)

    for row in queue_rows:
        if row.get("state") != "ready_for_preregistered_experiment":
            continue
        candidate = candidates.get(str(row.get("pattern_relationship_id") or ""), {})
        definition = {
            "research_goal_id": stable_id("qeg-research-goal", candidate.get("pattern_relationship_id")),
            "hypothesis_id": candidate.get("pattern_relationship_id"),
            "strategy_family_id": candidate.get("strategy_family_id"),
            "economic_mechanism": candidate.get("economic_mechanism"),
            "instrument": candidate.get("instrument"),
            "direction_hypothesis": "direction_to_be_resolved_before_current_decision",
            "expected_horizon": candidate.get("horizon") or "5d_forward",
            "horizon_hypothesis": candidate.get("horizon") or "5d_forward",
            "falsifier": candidate.get("falsifier"),
            "baseline_model": "matched_transparent_classical_baseline",
            "success_criteria": "positive untouched out-of-sample expectancy after costs and false-discovery control",
            "failure_criteria": "holdout, cost, stability, concentration, or negative-control failure",
            "graph_generation_id": graph_generation,
            "point_in_time_query_cutoff": query_cutoff,
            "score_id": candidate.get("score_id"),
            "source_path_hash": stable_id("qeg-source-path", candidate.get("source_path", [])),
            "holdout_outcomes_read_before_preregistration": False,
        }
        preregistration = preregister_experiment(definition, seen_preregistrations)
        matches = _prior_matches(candidate, prior)
        previous = previous_by_fingerprint.get(str(preregistration["attempt_fingerprint"]))
        if previous:
            record = deepcopy(previous)
            record["reused_frozen_preregistration"] = True
        else:
            record = {
                **preregistration,
                "pattern_relationship_id": candidate.get("pattern_relationship_id"),
                "graph_generation_id": graph_generation,
                "point_in_time_query_cutoff": query_cutoff,
                "programme_lane": "focused_graph_programme",
                "prior_context_match_count": len(matches),
                "prior_context_experiment_ids": [item.get("experiment_id") for item in matches],
                "prior_context_is_new_validation": False,
                "current_result_state": "preregistered_waiting_for_frozen_test",
                "historical_result_created": False,
                "current_trigger_created": False,
                "paper_proof_credit_created": False,
                "reused_frozen_preregistration": False,
            }
        seen_preregistrations.append(record)
        experiments.append(record)
        frozen_at = str(record.get("preregistered_at") or generated_at)
        frozen_generation = str(record.get("graph_generation_id") or graph_generation)
        frozen_cutoff = str(record.get("point_in_time_query_cutoff") or query_cutoff)
        graph_records.extend(
            [
                build_node(
                    "experiment_definition", record["experiment_id"], layer="tested",
                    evidence_state="research_only", payload=record,
                    available_at=frozen_at, generated_at=frozen_at,
                    source_artifact=f"data/runtime/{EXPERIMENT_BRIDGE_ARTIFACT}",
                    node_id=record["experiment_id"],
                ),
                build_edge(
                    "tested_by", str(candidate.get("pattern_relationship_id")), record["experiment_id"],
                    layer="tested", evidence_state="research_only",
                    payload={"graph_generation_id": frozen_generation, "query_cutoff": frozen_cutoff},
                    available_at=frozen_at, generated_at=frozen_at,
                    source_artifact=f"data/runtime/{EXPERIMENT_BRIDGE_ARTIFACT}",
                ),
            ]
        )

    errors: list[str] = []
    if not graph_generation:
        errors.append("graph_generation_missing")
    if int(registry.get("experiment_count") or 0) != len(prior):
        errors.append("backtest_registry_count_mismatch")
    if statistical.get("holdout_tuning_violation_count") not in (0, None):
        errors.append("existing_holdout_tuning_violation")
    if any(not item.get("preregistered_before_outcome") for item in experiments):
        errors.append("preregistration_order_violation")
    if any(item.get("prior_context_is_new_validation") for item in experiments):
        errors.append("legacy_result_retroactive_validation_violation")

    store = TemporalGraphStore(settings)
    append = store.append(graph_records) if graph_records else {"written": 0, "duplicates": 0}
    rebuilt = store.rebuild()
    payload = {
        "schema_version": "qadam_graph_experiment_bridge.v1",
        "artifact_type": "qadam_graph_experiment_bridge",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "graph_generation_id": graph_generation,
        "point_in_time_query_cutoff": query_cutoff,
        "backtest_registry_experiment_count": len(prior),
        "statistical_attempted_hypothesis_count": statistical.get("attempted_hypothesis_count"),
        "preregistered_experiment_count": len(experiments),
        "reused_frozen_preregistration_count": sum(
            bool(item.get("reused_frozen_preregistration")) for item in experiments
        ),
        "prior_context_link_count": sum(item["prior_context_match_count"] for item in experiments),
        "focused_programme_count": len({item["definition"].get("strategy_family_id") for item in experiments}),
        "whole_universe_challenger_capacity_share": registry.get("challenger_capacity_share", 0.2),
        "experiments": experiments,
        "result_state_counts": dict(Counter(item["current_result_state"] for item in experiments)),
        "graph_records_written": append["written"],
        "resulting_graph_generation_id": rebuilt.get("generation_id"),
        "historical_results_are_current_triggers": False,
        "historical_results_are_paper_proof": False,
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / EXPERIMENT_BRIDGE_ARTIFACT, payload)
    write_phase_status(
        "QEG-8", status=payload["status"], implementation_complete=not errors,
        empirical_state="experiments_preregistered_evidence_maturing",
        artifacts=[EXPERIMENT_BRIDGE_ARTIFACT], blockers=errors, settings=settings,
    )
    return payload, errors


def validate_graph_experiment_bridge(settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    payload = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("experiments") or []:
        if not row.get("graph_generation_id") or not row.get("point_in_time_query_cutoff"):
            errors.append("experiment_missing_frozen_graph_or_cutoff")
        if row.get("holdout_read_allowed") is not False:
            errors.append("preregistered_experiment_holdout_unsealed")
        if row.get("historical_result_created") or row.get("current_trigger_created"):
            errors.append("experiment_bridge_authority_violation")
    return sorted(set(errors))
