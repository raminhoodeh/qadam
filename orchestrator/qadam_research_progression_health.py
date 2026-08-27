"""Explain whether Qadam's research loop is learning, waiting, or blocked."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    canonical_json,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
)

SCHEMA_VERSION = "qadam_research_progression_health.v1"
STATUS_ARTIFACT = "qadam_research_progression_health.json"
HISTORY_ARTIFACT = "qadam_research_progression_health_history.jsonl"
CHECK_ARTIFACT = "qadam_research_progression_health_checks.json"
OPERATOR_HEALTH_MAX_AGE_SECONDS = 30 * 60


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _edge_count(payload: dict[str, Any]) -> int:
    return int(
        payload.get("validated_edge_count")
        or payload.get("edge_count")
        or payload.get("summary", {}).get("edge_count")
        or 0
    )


def _is_fresh(payload: dict[str, Any], now: datetime, max_age_seconds: int) -> bool:
    generated_at = _timestamp(payload.get("generated_at"))
    return bool(
        generated_at is not None
        and 0 <= (now - generated_at).total_seconds() <= max_age_seconds
    )


def build_research_progression_health(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    now = _timestamp(generated) or datetime.now(timezone.utc)
    sources = read_json(runtime / "qadam_source_capability_registry.json")
    score = read_json(runtime / "qadam_pattern_score_v3.json")
    score_checks = read_json(runtime / "qadam_pattern_score_v3_checks.json")
    score_rows = read_jsonl(runtime / "qadam_pattern_score_v3_records.jsonl")
    tape = read_json(runtime / "qadam_pattern_score_tape_checks.json")
    labels = read_json(runtime / "qadam_forward_labels_checks.json")
    shadow = read_json(runtime / "qadam_forward_shadow_checks.json")
    shadow_decisions = read_jsonl(runtime / "qadam_forward_shadow_decisions.jsonl")
    edges = read_json(runtime / "qadam_edge_registry_summary.json")
    strategies = read_jsonl(runtime / "qadam_strategy_hypotheses_v3.jsonl")
    readiness = read_json(runtime / "qadam_unattended_observation_readiness.json")
    operator_status = read_json(runtime / "qadam_operator_service_status.json")
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json")
    repair_queue = read_json(runtime / "qadam_operator_repair_queue.json")

    active_shadow_states = {
        "open",
        "pending",
        "waiting_for_outcome",
        "entry_observed_waiting_for_outcome",
    }
    active_shadow = [
        row
        for row in shadow_decisions
        if row.get("lifecycle_state") in active_shadow_states
        and (_timestamp(row.get("outcome_grace_expires_at")) or now) >= now
    ]
    due_shadow = [
        row
        for row in active_shadow
        if (_timestamp(row.get("outcome_due_at")) or now) <= now
    ]
    ranked_patterns = sorted(
        (row for row in score_rows if row.get("negative_control") is not True),
        key=lambda row: float(row.get("raw_pattern_score") or 0.0),
        reverse=True,
    )
    top_patterns = [
        {
            "score_id": row.get("score_id"),
            "strategy": row.get("strategy_label"),
            "instrument": row.get("instrument"),
            "research_score": row.get("raw_pattern_score"),
            "confidence_state": row.get("confidence_state"),
            "next_action": row.get("permitted_next_action"),
        }
        for row in ranked_patterns[:5]
    ]
    strategy_scoped_source_gaps = int(
        sources.get("counts", {}).get("strategy_scoped_source_gap")
        or sources.get("counts", {}).get("active_strategy_source_failure")
        or 0
    )
    validated_edges = _edge_count(edges)
    exact_stop_reasons: list[dict[str, Any]] = []
    if strategy_scoped_source_gaps:
        exact_stop_reasons.append(
            {
                "stage": "source_evidence",
                "reason": "strategy_scoped_source_gaps",
                "count": strategy_scoped_source_gaps,
                "effect": "Only affected strategy families lose source coverage.",
            }
        )
    if score_checks.get("material_change_detected") is False:
        exact_stop_reasons.append(
            {
                "stage": "pattern_scoring",
                "reason": "no_new_material_evidence",
                "count": 0,
                "effect": "The prior score generation is preserved instead of being relabelled as new learning.",
            }
        )
    if validated_edges == 0:
        exact_stop_reasons.append(
            {
                "stage": "edge_validation",
                "reason": "no_relationship_survived_holdout_costs_and_stability",
                "count": 0,
                "effect": "No validated-lane promotion is available.",
            }
        )
    if not strategies:
        exact_stop_reasons.append(
            {
                "stage": "strategy_formation",
                "reason": "no_current_strategy_hypothesis",
                "count": 0,
                "effect": "There is nothing new to send into Akber review from this generation.",
            }
        )

    state_material = {
        "source_material_fingerprint": sources.get("material_fingerprint"),
        "score_material_fingerprint": score.get("input_material_fingerprint"),
        "score_material_change_detected": score_checks.get("material_change_detected"),
        "historical_label_count": labels.get("label_count"),
        "shadow_outcome_count": shadow.get("outcome_count"),
        "active_shadow_decision_ids": sorted(
            str(row.get("decision_id")) for row in active_shadow
        ),
        "validated_edge_count": validated_edges,
        "strategy_hypothesis_ids": sorted(
            str(row.get("hypothesis_id")) for row in strategies
        ),
        "top_pattern_ids": [row.get("score_id") for row in top_patterns],
    }
    state_fingerprint = sha256_text(canonical_json(state_material))
    previous = read_json(runtime / STATUS_ARTIFACT)
    material_progress_detected = previous.get("state_fingerprint") != state_fingerprint
    operator_status_fresh = _is_fresh(
        operator_status, now, OPERATOR_HEALTH_MAX_AGE_SECONDS
    )
    open_circuit_count = int(circuits.get("open_circuit_count") or 0)
    open_repair_count = int(repair_queue.get("open_request_count") or 0)
    process_running = operator_status.get("liveness", {}).get("process_running") is True
    operational_blockers: list[str] = []
    if operator_status:
        if not operator_status_fresh:
            operational_blockers.append("operator_health_stale")
        if not process_running:
            operational_blockers.append("operator_service_not_running")
        if open_circuit_count:
            operational_blockers.append("operator_circuit_open")
        if open_repair_count:
            operational_blockers.append("operator_repair_open")
        if operator_status.get("operational_ready") is not True:
            operational_blockers.append("operator_not_operationally_ready")
        observation_ready = bool(
            operator_status_fresh
            and not operational_blockers
            and operator_status.get("observation_ready") is True
        )
    else:
        # Test and bootstrap runtimes may not have an operator projection yet.
        observation_ready = readiness.get("observation_ready") is True
    if operational_blockers:
        exact_stop_reasons.insert(
            0,
            {
                "stage": "operator_runtime",
                "reason": "operator_health_blocked",
                "count": len(operational_blockers),
                "blockers": operational_blockers,
                "effect": "Research records remain readable, but unattended progression is not healthy.",
            },
        )
    status = (
        "blocked_operationally"
        if operational_blockers
        else "progressed_materially"
        if material_progress_detected
        else "healthy_waiting_for_new_evidence"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_progression_health",
        "generated_at": generated,
        "status": status,
        "state_fingerprint": state_fingerprint,
        "material_progress_detected": material_progress_detected,
        "last_material_progress_at": (
            generated
            if material_progress_detected
            else previous.get("last_material_progress_at")
        ),
        "observation_ready": observation_ready,
        "operator_truth": {
            "status_fresh": operator_status_fresh,
            "process_running": process_running,
            "operational_ready": operator_status.get("operational_ready"),
            "observation_ready": operator_status.get("observation_ready"),
            "open_circuit_count": open_circuit_count,
            "open_repair_count": open_repair_count,
            "blockers": operational_blockers,
        },
        "source_truth": {
            "catalogue_count": sources.get("counts", {}).get("catalogue", 0),
            "fresh_provider_backed_count": sources.get("counts", {}).get(
                "fresh_current_confirmation", 0
            ),
            "classified_limit_count": sources.get("counts", {}).get(
                "classified_limit", 0
            ),
            "strategy_scoped_source_gap_count": strategy_scoped_source_gaps,
            "active_strategy_source_failure_count": strategy_scoped_source_gaps,
            "operating_status": sources.get("operating_status"),
            "strategy_coverage": sources.get("strategy_source_coverage", []),
        },
        "pattern_truth": {
            "current_record_count": score.get("record_count", 0),
            "score_ready_count": score.get("confidence_state_counts", {}).get(
                "score_ready_for_tape", 0
            ),
            "blocked_missing_feature_count": score.get(
                "confidence_state_counts", {}
            ).get("blocked_missing_critical_features", 0),
            "material_change_detected": score_checks.get("material_change_detected"),
            "last_material_change_at": score_checks.get("last_material_change_at"),
            "top_patterns": top_patterns,
        },
        "validation_truth": {
            "historical_score_row_count": tape.get("score_tape_row_count", 0),
            "historical_label_count": labels.get("label_count", 0),
            "live_shadow_decision_count": shadow.get("decision_count", 0),
            "live_shadow_outcome_count": shadow.get("outcome_count", 0),
            "active_shadow_decision_count": len(active_shadow),
            "due_shadow_outcome_count": len(due_shadow),
            "validated_edge_count": validated_edges,
            "current_strategy_hypothesis_count": len(strategies),
        },
        "exact_stop_reasons": exact_stop_reasons,
        "next_actions": [
            "Refresh only strategy-required providers that are unavailable now.",
            "Preserve score generations until a source observation or scoring input materially changes.",
            "Poll due forward-shadow outcomes independently of source-score refreshes.",
            "Promote only relationships that survive holdout, costs, stability, and real forward observation.",
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }


def build_and_write_research_progression_health(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload = build_research_progression_health(settings)
    errors: list[str] = []
    if not payload.get("state_fingerprint"):
        errors.append("research_progression_state_fingerprint_missing")
    if payload.get("paper_order_created_count") != 0:
        errors.append("research_progression_created_paper_order")
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, payload)
    if payload.get("material_progress_detected") is True:
        append_jsonl_durable(runtime / HISTORY_ARTIFACT, payload)
    checks = {
        **payload,
        "artifact_type": "qadam_research_progression_health_checks",
        "status": "passed" if not errors else "blocked",
        "validation_error_count": len(errors),
        "validation_errors": errors,
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "build_and_write_research_progression_health",
    "build_research_progression_health",
]
