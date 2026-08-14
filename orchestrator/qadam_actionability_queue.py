"""QEG-7 actionability queue, intentionally separate from research rank."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import ACTIONABILITY_QUEUE_ARTIFACT, PATTERN_CANDIDATES_ARTIFACT, qeg_authority, write_phase_status


def build_actionability_queue(settings: Settings | None = None, *, top_k: int = 12) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    patterns = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    candidates = patterns.get("candidates") if isinstance(patterns.get("candidates"), list) else []
    queue = sorted(
        candidates,
        key=lambda row: (float(row.get("actionability_rank") or 0), float(row.get("research_rank") or 0)),
        reverse=True,
    )[:top_k]
    rows = []
    for index, candidate in enumerate(queue, 1):
        blockers = [str(item) for item in candidate.get("actionability_blockers", [])]
        rows.append(
            {
                "queue_rank": index,
                "pattern_relationship_id": candidate.get("pattern_relationship_id"),
                "instrument": candidate.get("instrument"),
                "strategy_family_id": candidate.get("strategy_family_id"),
                "research_rank": candidate.get("research_rank"),
                "actionability_rank": candidate.get("actionability_rank"),
                "state": "ready_for_preregistered_experiment" if not blockers else "research_hold",
                "blockers": blockers,
                "next_action": candidate.get("next_action"),
                "is_trade_candidate": False,
                "paper_order_created": False,
                "authority": qeg_authority(),
            }
        )
    payload = {
        "schema_version": "qadam_actionability_queue.v1",
        "artifact_type": "qadam_actionability_queue",
        "generated_at": now_iso(),
        "status": "complete",
        "queue_count": len(rows),
        "ready_for_preregistered_experiment_count": sum(row["state"] == "ready_for_preregistered_experiment" for row in rows),
        "research_hold_count": sum(row["state"] == "research_hold" for row in rows),
        "queue_continues_after_first_hold": True,
        "research_rank_separate_from_actionability": True,
        "rows": rows,
        "authority": qeg_authority(),
    }
    errors: list[str] = []
    if any(row["is_trade_candidate"] or row["paper_order_created"] for row in rows):
        errors.append("actionability_queue_authority_violation")
    write_json_atomic(runtime / ACTIONABILITY_QUEUE_ARTIFACT, payload)
    write_phase_status(
        "QEG-7", status="passed" if not errors else "blocked", implementation_complete=not errors,
        empirical_state="graph_patterns_ranked_for_actionability",
        artifacts=[PATTERN_CANDIDATES_ARTIFACT, ACTIONABILITY_QUEUE_ARTIFACT], blockers=errors,
        settings=settings,
    )
    return payload, errors
