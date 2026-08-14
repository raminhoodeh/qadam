"""QEG-13 persistent attribution for trades, holds, vetoes and non-trades."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import ACTIVE_DISCOVERY_FUNNEL_ARTIFACT, OUTCOME_LEARNING_ARTIFACT, qeg_authority, stable_id, write_phase_status
from orchestrator.qadam_temporal_graph_contracts import build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore


def _normalise(source_artifact: str, row: dict[str, Any]) -> dict[str, Any]:
    source_id = (
        row.get("outcome_record_id") or row.get("outcome_id") or row.get("postmortem_id")
        or row.get("decision_id") or row.get("router_decision_id") or row.get("evaluation_id")
        or stable_id("qeg-outcome-source", source_artifact, row)
    )
    final_state = str(row.get("outcome_type") or row.get("final_state") or row.get("decision") or "observed")
    matured = bool(row.get("matured") or row.get("outcome_matured") or row.get("real_close_verified"))
    lineage = row.get("lineage") if isinstance(row.get("lineage"), dict) else {}
    return {
        "learning_record_id": stable_id("qeg-learning", source_artifact, source_id),
        "source_artifact": source_artifact,
        "source_record_id": source_id,
        "record_type": final_state,
        "matured": matured,
        "strategy_family_id": row.get("strategy_family_id") or lineage.get("strategy_family_id"),
        "strategy_version_id": row.get("strategy_version_id") or lineage.get("strategy_version_id"),
        "instrument": row.get("instrument") or row.get("symbol"),
        "net_return_after_costs": row.get("net_return_after_costs") or row.get("realized_net_pnl"),
        "source_attribution": row.get("source_attribution") or lineage.get("source_ids") or [],
        "model_attribution": row.get("model_attribution") or [],
        "quantum_attribution": row.get("quantum_attribution") or "not_attributable_without_matched_increment",
        "akber_state": row.get("akber_decision") or row.get("akber_state") or "not_reached",
        "risk_state": row.get("risk_state") or "not_reached",
        "router_state": row.get("router_state") or row.get("final_state") or "not_reached",
        "execution_state": row.get("execution_state") or row.get("measurement_state") or "not_reached",
        "negative_result": any(token in final_state.lower() for token in ("hold", "veto", "reject", "failed", "negative")),
        "proposal_only": True,
        "code_mutated": False,
        "risk_policy_mutated": False,
        "live_authority_mutated": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": qeg_authority(),
    }


def build_graph_outcome_learning(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    sources = (
        "qadam_active_discovery_outcomes.jsonl",
        "qadam_forward_shadow_outcomes.jsonl",
        "qadam_experimental_paper_outcomes.jsonl",
        "qadam_paper_postmortems_v3.jsonl",
        "qadam_router_v3_decisions.jsonl",
    )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for filename in sources:
        for source in read_jsonl(runtime / filename):
            record = _normalise(filename, source)
            if record["learning_record_id"] in seen:
                continue
            seen.add(record["learning_record_id"])
            rows.append(record)
    funnel = read_json(runtime / ACTIVE_DISCOVERY_FUNNEL_ARTIFACT)
    for source in funnel.get("evaluations") or []:
        record = _normalise(ACTIVE_DISCOVERY_FUNNEL_ARTIFACT, source)
        if record["learning_record_id"] not in seen:
            seen.add(record["learning_record_id"])
            rows.append(record)

    proposals: list[dict[str, Any]] = []
    for row in rows:
        if not row["matured"] or not row["strategy_family_id"]:
            continue
        proposal_type = "retire_or_narrow_relationship" if row["negative_result"] else "replicate_before_paper_version_change"
        proposals.append(
            {
                "proposal_id": stable_id("qeg-improvement-proposal", row["learning_record_id"], proposal_type),
                "parent_learning_record_id": row["learning_record_id"],
                "strategy_family_id": row["strategy_family_id"],
                "proposal_type": proposal_type,
                "exact_change": "No change applied; freeze an incumbent/challenger test first.",
                "state": "proposal_waiting_for_frozen_challenger",
                "automatic_code_change_allowed": False,
                "automatic_risk_change_allowed": False,
                "automatic_live_change_allowed": False,
                "paper_order_created": False,
                "authority": qeg_authority(),
            }
        )

    errors: list[str] = []
    if any(row.get("code_mutated") or row.get("risk_policy_mutated") or row.get("live_authority_mutated") for row in rows):
        errors.append("outcome_learning_mutation_violation")
    if any(not row.get("proposal_only") for row in rows):
        errors.append("outcome_learning_not_proposal_only")
    graph_records = [
        build_node(
            "postmortem", row["learning_record_id"], layer="tested", evidence_state="research_only",
            payload=row, available_at=now_iso(), source_artifact=f"data/runtime/{OUTCOME_LEARNING_ARTIFACT}",
        )
        for row in rows
    ] + [
        build_node(
            "improvement_proposal", row["proposal_id"], layer="tested", evidence_state="research_only",
            payload=row, available_at=now_iso(), source_artifact=f"data/runtime/{OUTCOME_LEARNING_ARTIFACT}",
        )
        for row in proposals
    ]
    store = TemporalGraphStore(settings)
    append = store.append(graph_records) if graph_records else {"written": 0}
    manifest = store.rebuild()
    payload = {
        "schema_version": "qadam_graph_outcome_learning.v1",
        "artifact_type": "qadam_graph_outcome_learning_summary",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "learning_record_count": len(rows),
        "matured_record_count": sum(row["matured"] for row in rows),
        "negative_record_count": sum(row["negative_result"] for row in rows),
        "record_type_counts": dict(Counter(row["record_type"] for row in rows)),
        "proposal_count": len(proposals),
        "records": rows,
        "proposals": proposals,
        "graph_records_written": append["written"],
        "graph_generation_id": manifest.get("generation_id"),
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / OUTCOME_LEARNING_ARTIFACT, payload)
    return payload, errors


def validate_graph_outcome_learning(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / OUTCOME_LEARNING_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("records") or []:
        if row.get("paper_order_created") or row.get("proof_credit_granted"):
            errors.append("learning_record_authority_violation")
    for row in payload.get("proposals") or []:
        if row.get("automatic_code_change_allowed") or row.get("automatic_risk_change_allowed"):
            errors.append("improvement_proposal_scope_violation")
    return sorted(set(errors))
