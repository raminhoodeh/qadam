"""Bridge qualified qualitative patterns to current strategy-family semantics."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import read_json, sha256_json
from orchestrator.qadam_qualitative_common import (
    QUALITATIVE_CHALLENGES_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_DIRECTIONS_ARTIFACT,
    QUALITATIVE_PATTERNS_ARTIFACT,
    QUALITATIVE_PATTERN_BRIDGE_ARTIFACT,
    QUALITATIVE_STRATEGY_IMPACTS_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
    stable_id,
)
from orchestrator.qadam_strategy_foundry_v3 import build_strategy_hypothesis


def build_qualitative_strategy_bridge(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    patterns = read_jsonl(runtime / QUALITATIVE_PATTERNS_ARTIFACT)
    challenges = read_jsonl(runtime / QUALITATIVE_CHALLENGES_ARTIFACT)
    strategy_map = read_json(runtime / "qadam_strategy_evidence_map_v3.json")
    strategy_index = {
        str(row.get("strategy_family_id")): row
        for row in strategy_map.get("strategies") or []
        if isinstance(row, dict) and row.get("strategy_family_id")
    }
    directions: list[dict[str, Any]] = []
    impacts: list[dict[str, Any]] = []
    for pattern in patterns:
        holdout_passed = pattern.get("holdout_state") == "passed"
        direction = str(pattern.get("direction") or "unresolved")
        family = str(pattern.get("strategy_family_id") or "emerging_qualitative_strategy")
        strategy = strategy_index.get(family)
        canonical_draft = None
        blockers: list[str] = []
        if not holdout_passed:
            blockers.append("untouched_holdout_required")
        if direction not in {"long", "short"}:
            blockers.append("direction_rule_required")
        if strategy is None:
            blockers.append("strategy_family_mapping_requires_emerging_strategy_review")
        if not blockers and strategy is not None:
            edge = {
                "edge_id": stable_id("qualitative-validated-edge", pattern.get("pattern_id")),
                "promotion_class": "validated_research_edge",
                "source_feature_definition": pattern.get("claim_type"),
                "instrument": pattern.get("instrument_symbol"),
                "direction": direction,
                "horizon": f"{pattern.get('horizon')}_forward" if not str(pattern.get("horizon") or "").endswith("_forward") else pattern.get("horizon"),
                "score_version": "qadam_qualitative_pattern.v1",
                "label_version": "qadam_qualitative_label.v1",
                "backtest_run_id": stable_id("qualitative-backtest-run", pattern.get("pattern_id")),
                "fold_ids": ["chronological_train", "untouched_holdout"],
                "dataset_hashes": {"qualitative_pattern": sha256_json(pattern)},
                "decay_state": "active",
                "gross_expectancy": pattern.get("gross_expectancy"),
                "net_expectancy": pattern.get("net_expectancy"),
                "confidence_distribution": {"research_score": pattern.get("research_score")},
                "strategy_family_id": family,
                "strategy_fit_vector": {family: 1.0},
                "regime": "qualitative_event",
                "latest_supporting_sample": (pattern.get("untouched_holdout_metrics") or {}).get("latest_supporting_sample"),
                "falsifiers": [pattern.get("what_invalidates_it")],
                "retirement_conditions": ["untouched forward expectancy becomes nonpositive", "source timing or provenance fails"],
            }
            try:
                canonical_draft = build_strategy_hypothesis(
                    edge,
                    strategy,
                    generated_at=now_iso(),
                    edge_registry_lineage={
                        "edge_registry_artifact": QUALITATIVE_PATTERNS_ARTIFACT,
                        "edge_registry_summary_artifact": QUALITATIVE_PATTERN_BRIDGE_ARTIFACT,
                        "edge_registry_record_set_hash": sha256_json(patterns),
                        "strategy_evidence_map_record_set_hash": sha256_json(strategy_map.get("strategies") or []),
                        "complete": True,
                    },
                )
            except ValueError as exc:
                blockers.append(f"strategy_foundry_contract_rejected:{exc}")
        directions.append({
            "schema_version": "qadam_qualitative_direction_resolution.v1",
            "direction_resolution_id": stable_id("qualitative-direction", pattern.get("pattern_id")),
            "pattern_id": pattern.get("pattern_id"),
            "direction": direction,
            "state": "resolved_from_validated_signed_holdout" if canonical_draft else "held_before_foundry",
            "evidence_refs": [pattern.get("pattern_id")],
            "expires_at": (
                (canonical_draft.get("freshness") or {}).get("expires_at")
                if isinstance(canonical_draft, dict)
                else None
            ),
            "actionable": canonical_draft is not None,
            "authority": public_authority(),
        })
        impacts.append({
            "schema_version": "qadam_qualitative_strategy_impact.v1",
            "impact_id": stable_id("qualitative-strategy-impact", pattern.get("pattern_id")),
            "pattern_id": pattern.get("pattern_id"),
            "impact_state": "strategy_foundry_nomination" if canonical_draft else "research_only_not_admitted",
            "core_family_refinement": family if family in strategy_index else None,
            "emerging_strategy_formation": family if family not in strategy_index else None,
            "blockers": blockers,
            "canonical_draft": canonical_draft,
            "strategy_mutated": False,
            "authority": public_authority(),
        })
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QUALITATIVE_DIRECTIONS_ARTIFACT, directions)
    store.write_jsonl(QUALITATIVE_STRATEGY_IMPACTS_ARTIFACT, impacts)
    summary = {
        "schema_version": "qadam_qualitative_pattern_score_bridge.v1",
        "artifact_type": "qadam_qualitative_pattern_score_bridge",
        "generated_at": now_iso(),
        "status": (
            "ready_no_qualified_pattern"
            if not patterns
            else "ready_strategy_foundry_nominations"
            if any(row.get("canonical_draft") is not None for row in impacts)
            else "ready_patterns_held_for_validation"
        ),
        "claim_count": len(claims),
        "challenge_count": len(challenges),
        "qualified_pattern_count": len(patterns),
        "actionable_direction_count": sum(row["actionable"] for row in directions),
        "strategy_impact_count": len(impacts),
        "canonical_strategy_draft_count": sum(row.get("canonical_draft") is not None for row in impacts),
        "source_document_skipped_pattern_recognition_count": 0,
        "strategy_mutation_count": 0,
        "authority": public_authority(),
    }
    store.write_json(QUALITATIVE_PATTERN_BRIDGE_ARTIFACT, summary)
    return {"summary": summary, "directions": directions, "impacts": impacts}, []


__all__ = ["build_qualitative_strategy_bridge"]
