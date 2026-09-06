"""QEG-6 bounded independent research task and proposal fan-out."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, write_json_atomic
from orchestrator.research.focus import latest_score_rows, rank_programmes
from orchestrator.qadam_qeg_common import qeg_authority, stable_id, write_phase_status

FANOUT_ARTIFACT = "qadam_graph_research_fanout.json"

ROLES = (
    ("python_coo", "deterministic_orchestration"),
    ("local_gemma", "local_claim_and_entity_extraction"),
    ("frontier_gemini", "mechanism_and_alternative_challenge"),
    ("classical_quant", "transparent_measurement"),
    ("quantum_challenger", "nonlinear_challenger_only"),
)


def _family_key(row: dict[str, Any]) -> str:
    return str(row.get("strategy_family_id") or row.get("market_family") or row.get("instrument") or "unclassified")


def build_research_fanout(settings: Settings | None = None, *, family_limit: int = 3) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated = now_iso()
    scores = latest_score_rows(read_jsonl(runtime / "qadam_pattern_score_v3_records.jsonl"), as_of=generated)
    best: dict[str, dict[str, Any]] = {}
    for row in scores:
        key = _family_key(row)
        if key not in best or float(row.get("raw_pattern_score") or 0) > float(best[key].get("raw_pattern_score") or 0):
            best[key] = row
    focus = rank_programmes(scores, read_json(runtime / "qadam_source_capability_registry.json"),
                            as_of=generated, limit=family_limit)
    selected = [best[family] for family in focus["selected_families"] if family in best]
    write_json_atomic(runtime / "qadam_research_focus.json", focus)
    tasks: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for round_index, score in enumerate(selected, 1):
        frozen_input_hash = str(score.get("input_fingerprint") or "")
        if not frozen_input_hash:
            rejected.append({"score_id": score.get("score_id"), "reason": "evidence_fingerprint_missing"})
            continue
        for role, purpose in ROLES:
            tasks.append(
                {
                    "task_id": stable_id("qeg-research-task", _family_key(score),
                                         str(score.get("instrument") or ""), frozen_input_hash, role),
                    "research_round": round_index,
                    "role": role,
                    "purpose": purpose,
                    "frozen_input_hash": frozen_input_hash,
                    "score_id": score.get("score_id"),
                    "instrument": score.get("instrument"),
                    "strategy_family_id": score.get("strategy_family_id"),
                    "first_pass_independent": True,
                    "other_role_conclusions_visible": False,
                    "status": "ready_for_bounded_execution",
                    "budget": {
                        "max_seconds": 60 if role != "quantum_challenger" else 300,
                        "max_output_chars": 12000,
                        "paid_provider_calls_allowed": False,
                        "quantum_hardware_call_allowed": False,
                    },
                    "output_is_proposed_graph_delta": True,
                    "governed_write_allowed": False,
                    "authority": qeg_authority(),
                }
            )
    payload = {
        "schema_version": "qadam_graph_research_fanout.v1",
        "artifact_type": "qadam_graph_research_fanout",
        "generated_at": generated,
        "status": "ready" if tasks else "idle_no_score_rows",
        "research_round_count": len(selected) - len(rejected),
        "rejected_inputs": rejected,
        "task_count": len(tasks),
        "role_task_counts": dict(sorted(Counter(task["role"] for task in tasks).items())),
        "tasks": tasks,
        "focus": focus,
        "deterministic_validation_required": True,
        "model_agreement_is_not_provider_independence": True,
        "authority": qeg_authority(),
    }
    errors: list[str] = []
    for task in tasks:
        if task["governed_write_allowed"] or task["authority"].get("broker_write_allowed"):
            errors.append("fanout_task_unsafe_authority")
    write_json_atomic(runtime / FANOUT_ARTIFACT, payload)
    write_phase_status(
        "QEG-6", status="passed" if not errors else "blocked", implementation_complete=not errors,
        empirical_state="bounded_research_tasks_ready", artifacts=[FANOUT_ARTIFACT], blockers=errors,
        settings=settings,
    )
    return payload, sorted(set(errors))


def validate_proposed_delta(proposal: dict[str, Any], known_source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    citations = proposal.get("source_node_ids") if isinstance(proposal.get("source_node_ids"), list) else []
    if not citations:
        errors.append("proposal_citations_missing")
    if any(str(item) not in known_source_ids for item in citations):
        errors.append("proposal_citation_unknown")
    if proposal.get("governed_write_requested") is True:
        errors.append("proposal_governed_write_forbidden")
    if proposal.get("trade_authority_requested") is True:
        errors.append("proposal_trade_authority_forbidden")
    return errors
