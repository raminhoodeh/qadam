"""Translate qualitative evidence into only the Akber roles it can support."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    LANE_CONTRIBUTIONS_ARTIFACT,
    QUALITATIVE_AKBER_EXPLANATIONS_ARTIFACT,
    QUALITATIVE_AKBER_INPUTS_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
    stable_id,
)


def build_qualitative_akber_bridge(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    contributions = [row for row in read_jsonl(runtime / LANE_CONTRIBUTIONS_ARTIFACT) if row.get("lane_id") == "qualitative_agent_reach"]
    inputs: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []
    for claim in claims:
        direction = str(claim.get("direction") or "unspecified")
        context_available = bool(claim.get("instrument_hypotheses") and claim.get("independence_cluster"))
        catalyst_available = bool(claim.get("availability_time") and direction != "unspecified" and claim.get("novelty_state") == "first_in_cluster")
        missing = [
            field for field, present in (
                ("decision_time_market_confirmation", False),
                ("current_volatility", False),
                ("current_spread_and_liquidity", False),
                ("current_cost_adjusted_expectancy", False),
                ("decision_time_shadow", False),
            ) if not present
        ]
        inputs.append({
            "schema_version": "qadam_qualitative_akber_input.v1",
            "input_id": stable_id("qualitative-akber-input", claim.get("claim_id")),
            "claim_id": claim.get("claim_id"),
            "evidence_profile": "qualitative_management",
            "context": {"state": "available" if context_available else "missing", "evidence_refs": [claim.get("claim_id")]},
            "catalyst": {"state": "available" if catalyst_available else "missing", "evidence_refs": [claim.get("claim_id")] if catalyst_available else []},
            "confirmation": {"state": "missing", "required_owner": "market_context_packet"},
            "risk": {"state": "missing", "required_owner": "portfolio_risk_engine"},
            "execution": {"state": "missing", "required_owner": "alpaca_paper_market_context"},
            "postmortem": {"state": "not_applicable_before_decision"},
            "missing_fields": missing,
            "adverse_fields": [],
            "decision": "hold_missing_context",
            "paper_order_allowed": False,
            "authority": public_authority(),
        })
        explanations.append({
            "claim_id": claim.get("claim_id"),
            "plain_english": "The official claim can explain what changed and which market may be affected. It cannot supply a live quote, spread, expected return, risk limit or execution approval.",
            "missing_is_not_adverse": True,
            "next_action": "Wait for market confirmation and mature historical evidence, then recompile through the canonical lane.",
            "authority": public_authority(),
        })
    eligibility = {
        "schema_version": "qadam_qualitative_paper_eligibility.v1",
        "artifact_type": "qadam_qualitative_paper_eligibility",
        "generated_at": now_iso(),
        "status": "held_no_complete_qualitative_setup",
        "claim_count": len(claims),
        "lane_contribution_count": len(contributions),
        "context_eligible_count": sum(row["context"]["state"] == "available" for row in inputs),
        "catalyst_eligible_count": sum(row["catalyst"]["state"] == "available" for row in inputs),
        "paper_review_eligible_count": 0,
        "spread_or_liquidity_fabricated_count": 0,
        "expected_return_fabricated_count": 0,
        "paper_order_created_count": 0,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QUALITATIVE_AKBER_INPUTS_ARTIFACT, inputs)
    store.write_jsonl(QUALITATIVE_AKBER_EXPLANATIONS_ARTIFACT, explanations)
    store.write_json(QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT, eligibility)
    return {"inputs": inputs, "explanations": explanations, "eligibility": eligibility}, []


__all__ = ["build_qualitative_akber_bridge"]
