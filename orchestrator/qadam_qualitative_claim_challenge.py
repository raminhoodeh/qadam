"""Blinded functional challenges for grounded qualitative claims."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    QUALITATIVE_CHALLENGES_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
    stable_id,
)

PERSPECTIVES = {
    "business_quality": "Does the operating evidence support durable economics rather than a weak headline?",
    "catalyst": "What changed now, when was it public, and can it matter inside the declared horizon?",
    "macro_regime": "Which macro regime strengthens or invalidates the mechanism?",
    "market_reaction": "Do price, volatility, volume, flow and prediction markets confirm the thesis?",
    "adversarial_skeptic": "Could leakage, crowding, prior pricing or another cause explain the observation?",
}


def challenge_qualitative_claims(
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    runtime = runtime_dir(settings)
    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    rows: list[dict[str, Any]] = []
    for claim in claims:
        for perspective, question in PERSPECTIVES.items():
            missing: list[str] = []
            if not claim.get("availability_time"):
                missing.append("availability_time")
            if not claim.get("instrument_hypotheses"):
                missing.append("instrument_mapping")
            if claim.get("direction") == "unspecified":
                missing.append("direction")
            if perspective == "market_reaction":
                missing.extend(["decision_time_market_confirmation", "current_execution_measurement"])
            rows.append({
                "schema_version": "qadam_qualitative_claim_challenge.v1",
                "artifact_type": "qadam_qualitative_claim_challenge",
                "challenge_id": stable_id("claim-challenge", claim.get("claim_id"), perspective),
                "claim_id": claim.get("claim_id"),
                "perspective": perspective,
                "question": question,
                "evidence_ids": [claim.get("document_id")],
                "direction": claim.get("direction"),
                "horizon": "unresolved_until_historical_alignment",
                "mechanism": claim.get("predicate"),
                "counterargument": "The claim may already be priced or may not causally affect the mapped instrument.",
                "falsifier": claim.get("falsifier"),
                "uncertainty": "high" if missing else "medium",
                "missing_context": sorted(set(missing)),
                "review_state": "needs_evidence" if missing else "challenged",
                "model_mode": "schema_constrained_functional_review",
                "models_are_independent_sources": False,
                "generated_at": now_iso(),
                "authority": public_authority(),
            })
    AtomicArtifactStore(runtime).write_jsonl(QUALITATIVE_CHALLENGES_ARTIFACT, rows)
    return rows, []


__all__ = ["challenge_qualitative_claims", "PERSPECTIVES"]
