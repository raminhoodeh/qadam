"""Read-only tournament projection of durable strategy registrations and outcomes."""

import json
from pathlib import Path

from orchestrator.qadam_control_plane_store import ControlPlaneStore, DATABASE_NAME
from orchestrator.qadam_forward_evaluation import evaluate_forward_version, _time
from orchestrator.qadam_operator_ready_common import authority_flags


def forward_tournament(runtime: Path, shadows: list[dict], *, generated_at: str) -> tuple[dict, dict]:
    registrations = []
    database = runtime / DATABASE_NAME
    available = database.is_file()
    if available:
        with ControlPlaneStore(database, initialize=False).connect() as connection:
            registrations = [dict(row) for row in connection.execute(
                "SELECT aggregate_id,payload_json,MIN(created_at) AS created_at FROM operating_events "
                "WHERE aggregate_type='strategy_version' AND event_type='strategy_definition_registered' "
                "GROUP BY aggregate_id,payload_json ORDER BY created_at,aggregate_id"
            )]
    candidates, freezes = [], []
    for trial_index, registration in enumerate(registrations, 1):
        version = registration["aggregate_id"]
        definition = json.loads(registration["payload_json"])
        registered = _time(registration["created_at"])
        outcomes = [row for row in shadows if registered and _time(row.get("decision_at"))
                    and _time(row.get("decision_at")) >= registered]
        evaluation = evaluate_forward_version(version, outcomes, as_of=generated_at, trial_index=trial_index)
        candidates.append({**evaluation, "strategy_family_id": definition.get("strategy_family_id"),
                           "registered_at": registration["created_at"],
                           "state": "emerging_review_eligible" if evaluation["eligible_for_emerging_review"] else "collecting_matched_forward_evidence"})
        freezes.append({"strategy_version_id": version, "registered_at": registration["created_at"],
                        "definition": definition, "backfilled": False})
    common = {"generated_at": generated_at, "schema_version": "qadam_forward_tournament.v2",
              "authority": authority_flags(), "paper_order_created_count": 0,
              "proof_credit_created_count": 0, "simulated_elapsed_time": False,
              "canonical_registration_available": available}
    tournament = {**common, "artifact_type": "qadam_forward_strategy_tournament",
                  "status": "collecting_matched_forward_evidence" if candidates else "waiting_for_registered_strategy_versions",
                  "candidate_count": len(candidates), "candidates": candidates,
                  "forward_validated_count": 0,
                  "emerging_review_eligible_count": sum(row["eligible_for_emerging_review"] for row in candidates),
                  "comparators": ["matched_SPY_after_modelled_costs", "no_trade"],
                  "real_market_days_elapsed": None,
                  "elapsed_time_basis": "use_independent_provider_matched_event_windows_not_wall_clock"}
    registry = {**common, "artifact_type": "qadam_forward_research_freeze_registry",
                "status": "registered" if freezes else "waiting_for_registered_strategy_versions",
                "freeze_count": len(freezes), "freezes": freezes,
                "parameter_change_restarts_clock": True, "retrospective_preregistration_allowed": False}
    return tournament, registry
