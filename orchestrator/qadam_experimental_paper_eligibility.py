"""Experimental paper eligibility projection for the canonical Router.

This module answers whether a current, explicitly unvalidated setup would pass
the research and safety gates before release. It creates no order, approval, or
proof and does not mutate the research lock.
"""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    EXPERIMENTAL_ROUTER_STATE,
    EXPERIMENTAL_UNVALIDATED,
    POLICY_VERSION,
    validate_class_lineage,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_router_v3_paperops import (
    ABSOLUTE_PAPER_TRADE_CEILING_USD,
    build_router_v3_state,
    route_setup,
)

SCHEMA_VERSION = "qadam_experimental_paper_eligibility.v1"
STATUS_ARTIFACT = "qadam_experimental_paper_eligibility.json"
CANDIDATES_ARTIFACT = "qadam_experimental_paper_candidates.jsonl"
CHECK_ARTIFACT = "qadam_experimental_paper_eligibility_checks.json"


def _candidate(setup: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    lineage = setup.get("lineage") if isinstance(setup.get("lineage"), dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_paper_candidate",
        "generated_at": decision.get("generated_at"),
        "status": "eligible_pending_or_active_guarded_release",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "paper_trade_purpose": setup.get("paper_trade_purpose"),
        "edge_id": None,
        "edge_validation_status": "not_yet_validated",
        "edge_claim_allowed": False,
        "research_goal_id": lineage.get("research_goal_id"),
        "pattern_relationship_id": lineage.get("pattern_relationship_id"),
        "strategy_hypothesis_id": lineage.get("hypothesis_id"),
        "candidate_identity_id": setup.get("candidate_identity_id"),
        "source_evidence_ids": setup.get("source_quorum", {}).get(
            "source_evidence_ids", []
        ),
        "instrument": setup.get("instrument"),
        "direction": setup.get("direction"),
        "expires_at": setup.get("expires_at"),
        "invalidation": setup.get("invalidation"),
        "akber_result_id": lineage.get("akber_result_id"),
        "risk_proposal_id": lineage.get("risk_proposal_id"),
        "router_decision_id": decision.get("router_decision_id"),
        "idempotency_key": decision.get("idempotency_material", {}).get(
            "idempotency_key"
        ),
        "proposed_notional_usd": setup.get("proposed_notional_usd"),
        "active_paper_epoch_id": setup.get("active_paper_epoch_id"),
        "route": setup.get("route"),
        "router_final_state": decision.get("final_state"),
        "qualified_setup_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def build_experimental_eligibility_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_iso()
    router = build_router_v3_state(settings, generated_at=generated)
    experimental_setups = [
        setup
        for setup in router.get("setups", [])
        if setup.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
    ]
    projected_decisions = [
        route_setup(
            setup,
            {
                "experimental_paper_release_effective": True,
                "validated_paper_release_effective": False,
            },
            generated_at=generated,
        )
        for setup in experimental_setups
    ]
    candidates = [
        _candidate(setup, decision)
        for setup, decision in zip(experimental_setups, projected_decisions, strict=True)
        if decision.get("final_state") == EXPERIMENTAL_ROUTER_STATE
    ]
    blocked = [
        {
            "setup_id": setup.get("setup_id"),
            "instrument": setup.get("instrument"),
            "final_state": decision.get("final_state"),
            "first_actionable_blocker": (
                decision.get("repair_reasons")
                or decision.get("hard_vetoes")
                or decision.get("hold_reasons")
                or [decision.get("final_reason")]
            )[0],
            "all_blockers": unique_errors(
                [
                    *decision.get("repair_reasons", []),
                    *decision.get("hard_vetoes", []),
                    *decision.get("hold_reasons", []),
                ]
            ),
        }
        for setup, decision in zip(experimental_setups, projected_decisions, strict=True)
        if decision.get("final_state") != EXPERIMENTAL_ROUTER_STATE
    ]
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_paper_eligibility",
        "generated_at": generated,
        "status": "candidate_available" if candidates else "ready_idle",
        "policy_version": POLICY_VERSION,
        "experimental_setup_count": len(experimental_setups),
        "experimental_candidate_count": len(candidates),
        "blocked_setup_count": len(blocked),
        "blocked_setups": blocked,
        "why_not_trading_now": (
            "An experimental setup is ready for the guarded paper-review boundary."
            if candidates
            else blocked[0]["first_actionable_blocker"]
            if blocked
            else "No current pattern has formed a complete experimental setup."
        ),
        "zero_validated_edges_allowed": True,
        "no_candidate_is_healthy_ready_idle": not candidates,
        "candidate_is_not_order": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return {"status": status, "candidates": candidates, "decisions": projected_decisions}


def validate_experimental_eligibility_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = state.get("status", {})
    candidates = state.get("candidates", [])
    if status.get("experimental_candidate_count") != len(candidates):
        errors.append("experimental_candidate_count_mismatch")
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_identity_id") or "unknown")
        lineage = {
            "research_goal_id": candidate.get("research_goal_id"),
            "score_id": next(
                (
                    decision.get("lineage", {}).get("score_id")
                    for decision in state.get("decisions", [])
                    if decision.get("router_decision_id")
                    == candidate.get("router_decision_id")
                ),
                None,
            ),
            "pattern_relationship_id": candidate.get("pattern_relationship_id"),
            "hypothesis_id": candidate.get("strategy_hypothesis_id"),
            "akber_result_id": candidate.get("akber_result_id"),
            "shadow_evidence_id": next(
                (
                    decision.get("lineage", {}).get("shadow_evidence_id")
                    for decision in state.get("decisions", [])
                    if decision.get("router_decision_id")
                    == candidate.get("router_decision_id")
                ),
                None,
            ),
            "risk_proposal_id": candidate.get("risk_proposal_id"),
            "edge_id": candidate.get("edge_id"),
        }
        errors.extend(
            f"experimental_candidate:{candidate_id}:{error}"
            for error in validate_class_lineage(EXPERIMENTAL_UNVALIDATED, lineage)
        )
        if candidate.get("edge_claim_allowed") is not False:
            errors.append(f"experimental_candidate_edge_claim_allowed:{candidate_id}")
        if not candidate.get("expires_at") or not candidate.get("invalidation"):
            errors.append(f"experimental_candidate_trade_contract_incomplete:{candidate_id}")
        if float(candidate.get("proposed_notional_usd") or 0) > ABSOLUTE_PAPER_TRADE_CEILING_USD:
            errors.append(f"experimental_candidate_notional_above_ceiling:{candidate_id}")
        if candidate.get("route") != "guarded_alpaca_paper_via_paperops":
            errors.append(f"experimental_candidate_route_invalid:{candidate_id}")
        errors.extend(
            validate_authority(candidate.get("authority", {}), prefix="experimental_candidate")
        )
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(status.get(field) or 0) != 0:
            errors.append(f"experimental_eligibility_forbidden_count:{field}")
    if status.get("proof_credit_allowed") is not False:
        errors.append("experimental_eligibility_proof_credit_allowed")
    if status.get("live_capital_enabled") is not False:
        errors.append("experimental_eligibility_live_capital_enabled")
    errors.extend(
        validate_authority(status.get("authority", {}), prefix="experimental_eligibility")
    )
    return unique_errors(errors)


def build_and_write_experimental_eligibility(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    state = build_experimental_eligibility_state(settings)
    errors = validate_experimental_eligibility_state(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_paper_eligibility_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "operating_state": state["status"]["status"],
        "experimental_candidate_count": len(state["candidates"]),
        "zero_candidate_ready_idle_allowed": True,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(STATUS_ARTIFACT, state["status"])
    store.write_jsonl(CANDIDATES_ARTIFACT, state["candidates"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "CANDIDATES_ARTIFACT",
    "CHECK_ARTIFACT",
    "STATUS_ARTIFACT",
    "build_and_write_experimental_eligibility",
    "build_experimental_eligibility_state",
    "validate_experimental_eligibility_state",
]
