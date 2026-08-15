"""Compile all research lanes into typed contributions and blocker ownership."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_evidence_contracts import build_lane_contribution, validate_lane_contribution
from orchestrator.qadam_operator_ready_common import read_json as read_runtime_json
from orchestrator.qadam_qualitative_common import (
    LANE_AUTHORITY_ARTIFACT,
    LANE_BLOCKERS_ARTIFACT,
    LANE_CONTRIBUTIONS_ARTIFACT,
    LANE_FUNNEL_ARTIFACT,
    LANE_REGISTRY_PATH,
    PREDICTION_RESEARCH_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_PATTERNS_ARTIFACT,
    QUALITATIVE_STRATEGY_IMPACTS_ARTIFACT,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    repo_root,
    runtime_dir,
    stable_id,
    unique,
)

DRAFTS_ARTIFACT = "qadam_strategy_drafts_v3.jsonl"


def _draft_evidence_refs(draft: dict[str, Any]) -> list[str]:
    reasoning = draft.get("qualitative_reasoning")
    reasoning = reasoning if isinstance(reasoning, dict) else {}
    refs = list(reasoning.get("cited_evidence_refs") or [])
    pattern = draft.get("pattern_lineage")
    if isinstance(pattern, dict):
        refs.extend([pattern.get("score_id"), pattern.get("pattern_relationship_id")])
    return unique(refs)


def build_lane_conversion(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    registry = read_json(repo_root() / LANE_REGISTRY_PATH)
    generated_at = now_iso()
    contributions: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for draft in read_jsonl(runtime / DRAFTS_ARTIFACT):
        tier = "A4"
        lane_id = "validated_paper" if str(draft.get("evidence_class")) == "validated_paper_strategy" else "discovery_micro"
        freshness = draft.get("freshness") if isinstance(draft.get("freshness"), dict) else {}
        contribution = build_lane_contribution(
            lane_id=lane_id,
            contribution_state="paper_review_nominated",
            authority_tier=tier,
            evidence_profile=str(draft.get("experimental_tier") or draft.get("evidence_class") or "discovery_micro"),
            subject={
                "hypothesis_id": draft.get("hypothesis_id"),
                "candidate_identity_id": (draft.get("candidate_identity_material") or {}).get("candidate_identity_id"),
                "strategy_family_id": (draft.get("strategy_mapping") or {}).get("strategy_family_id"),
                "instrument": (draft.get("instrument_proxy_mapping") or {}).get("execution_proxy"),
                "direction": (draft.get("direction_horizon") or {}).get("direction"),
                "horizon": (draft.get("direction_horizon") or {}).get("horizon"),
            },
            evidence_refs=_draft_evidence_refs(draft),
            generation_id=str(draft.get("generation_id") or draft.get("generated_at") or stable_id("draft-generation", draft.get("hypothesis_id"))),
            observed_at=freshness.get("latest_supporting_sample") or draft.get("generated_at"),
            expires_at=freshness.get("expires_at"),
            blockers=[],
            canonical_draft=draft,
        )
        contributions.append(contribution)

    qualitative_a4_count = 0
    for impact in read_jsonl(runtime / QUALITATIVE_STRATEGY_IMPACTS_ARTIFACT):
        draft = impact.get("canonical_draft")
        if not isinstance(draft, dict):
            continue
        freshness = draft.get("freshness") if isinstance(draft.get("freshness"), dict) else {}
        strategy_family = (draft.get("strategy_mapping") or {}).get("strategy_family_id")
        contribution = build_lane_contribution(
            lane_id="strategy_informed" if impact.get("core_family_refinement") else "strategy_agnostic",
            contribution_state="paper_review_nominated",
            authority_tier="A4",
            evidence_profile="qualitative_validated_pattern",
            subject={
                "hypothesis_id": draft.get("hypothesis_id"),
                "candidate_identity_id": (draft.get("candidate_identity_material") or {}).get("candidate_identity_id"),
                "strategy_family_id": strategy_family,
                "instrument": (draft.get("instrument_proxy_mapping") or {}).get("execution_proxy"),
                "direction": (draft.get("direction_horizon") or {}).get("direction"),
                "horizon": (draft.get("direction_horizon") or {}).get("horizon"),
            },
            evidence_refs=[str(impact.get("pattern_id"))],
            generation_id=str(draft.get("generated_at") or stable_id("qualitative-draft-generation", draft.get("hypothesis_id"))),
            observed_at=freshness.get("latest_supporting_sample") or draft.get("generated_at"),
            expires_at=freshness.get("expires_at"),
            blockers=[],
            canonical_draft=draft,
        )
        contributions.append(contribution)
        qualitative_a4_count += 1

    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    qualitative_patterns = read_jsonl(runtime / QUALITATIVE_PATTERNS_ARTIFACT)
    qualitative_blocker = "untouched_holdout_and_mature_forward_labels_required" if claims else "no_grounded_claims"
    if not qualitative_a4_count:
        contributions.append(build_lane_contribution(
            lane_id="qualitative_agent_reach",
            contribution_state="held",
            authority_tier="A2",
            evidence_profile="qualitative_context_catalyst",
            subject={"claim_count": len(claims), "qualified_pattern_count": len(qualitative_patterns)},
            evidence_refs=[str(row.get("claim_id")) for row in claims],
            generation_id=stable_id("qualitative-generation", [row.get("claim_id") for row in claims]),
            observed_at=max((str(row.get("availability_time") or "") for row in claims), default=None),
            expires_at=None,
            blockers=[{"code": qualitative_blocker, "owner": "qadam_qualitative_history_and_pattern_lab"}],
        ))
        blockers.append({"lane_id": "qualitative_agent_reach", "blocker_code": qualitative_blocker, "owner": "qadam_qualitative_history_and_pattern_lab", "safe_next_action": "collect mature forward labels and rerun preregistered tests"})

    prediction = read_runtime_json(runtime / PREDICTION_RESEARCH_ARTIFACT)
    prediction_blocker = "decision_time_liquidity_and_forward_outcome_required"
    contributions.append(build_lane_contribution(
        lane_id="prediction_disagreement",
        contribution_state="held",
        authority_tier="A2",
        evidence_profile="prediction_disagreement",
        subject={
            "contract_count": prediction.get("contract_count", 0),
            "large_historical_disagreement_count": prediction.get("large_disagreement_count", 0),
            "strategy_nomination_count": prediction.get("strategy_nomination_count", 0),
        },
        evidence_refs=[str(row.get("signal_id")) for row in prediction.get("disagreements", []) if row.get("signal_id")],
        generation_id=stable_id("prediction-generation", prediction.get("generated_at"), prediction.get("contract_count")),
        observed_at=prediction.get("generated_at"),
        expires_at=None,
        blockers=[{"code": prediction_blocker, "owner": "qadam_prediction_market_research"}],
    ))
    blockers.append({"lane_id": "prediction_disagreement", "blocker_code": prediction_blocker, "owner": "qadam_prediction_market_research", "safe_next_action": "capture current venue liquidity and mature listed-proxy outcomes"})

    validation_errors = [error for row in contributions for error in validate_lane_contribution(row)]
    lane_rows = registry.get("lanes") if isinstance(registry.get("lanes"), list) else []
    authority_inventory = {
        "schema_version": "qadam_lane_authority_inventory.v1",
        "artifact_type": "qadam_lane_authority_inventory",
        "generated_at": generated_at,
        "status": "passed" if not validation_errors else "blocked",
        "lane_count": len(lane_rows),
        "lanes": lane_rows,
        "research_lane_with_a5_or_a6_count": sum(str(row.get("maximum_authority")) in {"A5", "A6"} and row.get("lane_id") not in {"portfolio_risk_router", "guarded_paperops"} for row in lane_rows),
        "direct_broker_authority_count": sum(row.get("direct_broker_authority") is not False for row in lane_rows),
        "authority": public_authority(),
    }
    state_counts = Counter(str(row.get("contribution_state")) for row in contributions)
    funnel = {
        "schema_version": "qadam_lane_conversion_funnel.v1",
        "artifact_type": "qadam_lane_conversion_funnel",
        "generated_at": generated_at,
        "status": "passed" if not validation_errors else "blocked",
        "contribution_count": len(contributions),
        "state_counts": dict(sorted(state_counts.items())),
        "a4_nomination_count": sum(row.get("authority_tier") == "A4" for row in contributions),
        "held_count": state_counts.get("held", 0),
        "canonical_draft_count": sum(isinstance(row.get("canonical_draft"), dict) for row in contributions),
        "validation_errors": unique(validation_errors),
        "schema_invalid_contribution_count": len(validation_errors),
        "ownerless_blocker_count": sum(not row.get("owner") for row in blockers),
        "order_created_count": 0,
        "broker_write_count": 0,
        "authority": public_authority(),
    }
    blocker_artifact = {
        "schema_version": "qadam_lane_blocker_ownership.v1",
        "artifact_type": "qadam_lane_blocker_ownership",
        "generated_at": generated_at,
        "status": "owned" if all(row.get("owner") for row in blockers) else "blocked_unowned",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "unowned_blocker_count": sum(not row.get("owner") for row in blockers),
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(LANE_CONTRIBUTIONS_ARTIFACT, contributions)
    store.write_json(LANE_AUTHORITY_ARTIFACT, authority_inventory)
    store.write_json(LANE_FUNNEL_ARTIFACT, funnel)
    store.write_json(LANE_BLOCKERS_ARTIFACT, blocker_artifact)
    return {"contributions": contributions, "authority": authority_inventory, "funnel": funnel, "blockers": blocker_artifact}, unique(validation_errors)


__all__ = ["build_lane_conversion"]
