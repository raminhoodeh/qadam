"""QEG-13 fair incumbent-versus-challenger tournament registry."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, sha256_json, write_json_atomic
from orchestrator.qadam_qeg_common import CHALLENGER_TOURNAMENT_ARTIFACT, OUTCOME_LEARNING_ARTIFACT, qeg_authority, stable_id, write_phase_status


def build_strategy_challenger_tournament(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    learning = read_json(runtime / OUTCOME_LEARNING_ARTIFACT)
    tournaments: list[dict[str, Any]] = []
    for proposal in learning.get("proposals") or []:
        frozen_definition = {
            "proposal_id": proposal.get("proposal_id"),
            "strategy_family_id": proposal.get("strategy_family_id"),
            "incumbent_version": "current_governed_version",
            "challenger_change": proposal.get("exact_change"),
            "evaluation": ["untouched_holdout", "costs", "stability", "negative_controls", "forward_shadow"],
        }
        tournaments.append(
            {
                "tournament_id": stable_id("qeg-challenger-tournament", sha256_json(frozen_definition)),
                "frozen_definition": frozen_definition,
                "frozen_definition_hash": sha256_json(frozen_definition),
                "state": "waiting_for_independent_evidence",
                "winner": None,
                "automatic_paper_version_promotion": False,
                "promotion_reason": "No fair completed challenger evidence exists yet.",
                "rollback_rule": "retain incumbent until challenger passes every frozen criterion",
                "code_mutated": False,
                "risk_envelope_expanded": False,
                "live_capital_changed": False,
                "authority": qeg_authority(),
            }
        )
    errors: list[str] = []
    if learning.get("status") != "passed":
        errors.append("outcome_learning_not_passed")
    if any(row.get("code_mutated") or row.get("risk_envelope_expanded") or row.get("live_capital_changed") for row in tournaments):
        errors.append("challenger_tournament_mutation_violation")
    payload = {
        "schema_version": "qadam_strategy_challenger_tournament.v1",
        "artifact_type": "qadam_strategy_challenger_tournament",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "tournament_count": len(tournaments),
        "completed_tournament_count": sum(row["state"] == "complete" for row in tournaments),
        "automatic_promotion_count": sum(row["automatic_paper_version_promotion"] for row in tournaments),
        "tournaments": tournaments,
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / CHALLENGER_TOURNAMENT_ARTIFACT, payload)
    write_phase_status(
        "QEG-13", status=payload["status"], implementation_complete=not errors,
        empirical_state="outcomes_attributed_challengers_waiting_for_evidence",
        artifacts=[OUTCOME_LEARNING_ARTIFACT, CHALLENGER_TOURNAMENT_ARTIFACT], blockers=errors, settings=settings,
    )
    return payload, errors


def validate_strategy_challenger_tournament(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / CHALLENGER_TOURNAMENT_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("tournaments") or []:
        if sha256_json(row.get("frozen_definition") or {}) != row.get("frozen_definition_hash"):
            errors.append("challenger_frozen_definition_hash_mismatch")
        if row.get("automatic_paper_version_promotion") and row.get("state") != "complete":
            errors.append("premature_challenger_promotion")
    return sorted(set(errors))
