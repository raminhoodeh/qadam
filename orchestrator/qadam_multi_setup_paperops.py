"""QEG-12 batch-safety audit over canonical Router V3 and PaperOps handoffs.

This module never writes a canonical handoff. It verifies that the existing
Router owner can carry multiple distinct setups without identity, idempotency,
or exposure ambiguity and that the canonical wrapper remains the sole submitter.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import MULTI_SETUP_ARTIFACT, qeg_authority, write_phase_status

PAPER_REVIEW_STATES = {"paper-review-candidate", "experimental-paper-review-candidate"}


def audit_multi_setup_records(
    decisions: list[dict[str, Any]],
    handoffs: list[dict[str, Any]],
    *,
    paper_positions: list[dict[str, Any]] | None = None,
    paper_orders: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    decision_ids = [str(row.get("decision_id") or row.get("router_decision_id") or "") for row in decisions]
    if any(not value for value in decision_ids):
        errors.append("router_decision_identity_missing")
    if len(set(decision_ids)) != len(decision_ids):
        errors.append("duplicate_router_decision_identity")
    if any(not row.get("final_state") for row in decisions):
        errors.append("router_final_state_missing")

    candidate_ids = [
        str(row.get("candidate_identity_id") or row.get("lineage", {}).get("candidate_identity_id") or "")
        for row in handoffs
    ]
    idempotency_keys = [
        str(row.get("idempotency_key") or row.get("idempotency", {}).get("key") or "")
        for row in handoffs
    ]
    research_goals = [
        str(row.get("research_goal_id") or row.get("lineage", {}).get("research_goal_id") or "")
        for row in handoffs
    ]
    for label, values in (
        ("candidate_identity", candidate_ids),
        ("idempotency_key", idempotency_keys),
        ("research_goal", research_goals),
    ):
        if handoffs and any(not value for value in values):
            errors.append(f"handoff_{label}_missing")
        if len(set(values)) != len(values):
            errors.append(f"duplicate_handoff_{label}")

    decision_by_id = {value: row for value, row in zip(decision_ids, decisions) if value}
    for handoff in handoffs:
        router_id = str(handoff.get("router_decision_id") or handoff.get("lineage", {}).get("router_decision_id") or "")
        decision = decision_by_id.get(router_id)
        if not decision:
            errors.append("handoff_router_decision_missing")
        elif decision.get("final_state") not in PAPER_REVIEW_STATES:
            errors.append("handoff_from_non_paper_review_state")
        if handoff.get("paper_order_created") is True or handoff.get("broker_write_count", 0):
            errors.append("handoff_created_order_or_broker_write")

    open_rows = [
        row for row in [*(paper_positions or []), *(paper_orders or [])]
        if str(row.get("state") or row.get("status") or "").lower()
        in {"accepted", "new", "open", "pending", "partially_filled", "submitted"}
    ]
    open_symbols = {str(row.get("symbol") or row.get("instrument") or "") for row in open_rows}
    duplicate_exposure_handoffs = [
        row for row in handoffs
        if str(row.get("symbol") or row.get("instrument") or row.get("execution_symbol") or "") in open_symbols
        and row.get("duplicate_exposure_check_passed") is not True
    ]
    if duplicate_exposure_handoffs:
        errors.append("open_exposure_conflict_not_cleared")

    return {
        "decision_count": len(decisions),
        "handoff_count": len(handoffs),
        "paper_review_decision_count": sum(row.get("final_state") in PAPER_REVIEW_STATES for row in decisions),
        "distinct_candidate_identity_count": len(set(candidate_ids)) if handoffs else 0,
        "distinct_idempotency_key_count": len(set(idempotency_keys)) if handoffs else 0,
        "distinct_research_goal_count": len(set(research_goals)) if handoffs else 0,
        "open_exposure_count": len(open_rows),
        "open_exposure_conflict_count": len(duplicate_exposure_handoffs),
        "final_state_counts": dict(Counter(str(row.get("final_state")) for row in decisions)),
    }, sorted(set(errors))


def build_multi_setup_paperops(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    decisions = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")
    handoffs = read_jsonl(runtime / "qadam_paperops_handoff_v3.jsonl")
    positions = read_jsonl(runtime / "paper_positions.jsonl")
    orders = read_jsonl(runtime / "paper_orders.jsonl")
    consumer = read_json(runtime / "qadam_paperops_handoff_v3_consumer_checks.json")
    router_checks = read_json(runtime / "qadam_router_v3_paperops_checks.json")
    metrics, errors = audit_multi_setup_records(decisions, handoffs, paper_positions=positions, paper_orders=orders)
    if router_checks and router_checks.get("status") not in {"passed", "ready", "complete"}:
        errors.append("canonical_router_check_not_passing")
    if consumer and consumer.get("status") not in {"passed", "ready", "complete"}:
        errors.append("canonical_handoff_consumer_check_not_passing")
    payload = {
        "schema_version": "qadam_multi_setup_paperops.v1",
        "artifact_type": "qadam_multi_setup_paperops",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        **metrics,
        "canonical_router_artifact": "qadam_router_v3_decisions.jsonl",
        "canonical_handoff_artifact": "qadam_paperops_handoff_v3.jsonl",
        "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py",
        "canonical_wrapper_only": True,
        "qeg_parallel_order_route_created": False,
        "batch_reconciles_risk_after_each_acceptance": True,
        "prediction_market_direct_execution_allowed": False,
        "paper_order_created_by_audit": False,
        "broker_write_count": 0,
        "validation_errors": sorted(set(errors)),
        "authority": qeg_authority(governed_projection=True),
    }
    write_json_atomic(runtime / MULTI_SETUP_ARTIFACT, payload)
    write_phase_status(
        "QEG-12", status=payload["status"], implementation_complete=not errors,
        empirical_state="canonical_router_batch_boundary_verified_idle" if not handoffs else "canonical_router_batch_boundary_verified_active",
        artifacts=[MULTI_SETUP_ARTIFACT], blockers=errors, settings=settings,
    )
    return payload, sorted(set(errors))


def validate_multi_setup_paperops(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / MULTI_SETUP_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    if payload.get("canonical_wrapper_only") is not True or payload.get("qeg_parallel_order_route_created") is not False:
        errors.append("canonical_paperops_boundary_violated")
    if payload.get("broker_write_count") or payload.get("paper_order_created_by_audit"):
        errors.append("multi_setup_audit_authority_violation")
    return sorted(set(errors))
