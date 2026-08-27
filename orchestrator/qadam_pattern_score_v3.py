"""OR-5 deterministic point-in-time Pattern Score V3 and feature engine."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    canonical_json,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import (
    STRATEGY_HYPOTHESES,
    clamp,
    contains_forbidden_key,
    record_set_hash,
    safe_float,
    stable_id,
)

SCHEMA_VERSION = "qadam_pattern_score_v3.v1"
PHASE_ID = "OR-5"
MODEL_VERSION = "pattern_score_v3.2_learning_lineage"
FEATURE_SET_VERSION = "qadam_feature_registry.v1"

FEATURE_REGISTRY_ARTIFACT = "qadam_feature_registry.json"
PRIMARY_ARTIFACT = "qadam_pattern_score_v3.json"
RECORDS_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
REJECTIONS_ARTIFACT = "qadam_pattern_score_v3_rejections.jsonl"
DASHBOARD_ARTIFACT = "qadam_pattern_score_v3_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_pattern_score_v3_checks.json"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
SOURCE_OPERATIONAL_ARTIFACT = "qadam_source_operational_state.jsonl"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
ELIGIBILITY_ARTIFACT = "qadam_relationship_eligibility_graph.jsonl"
STAGE1_LEARNING_INPUT_ARTIFACT = "qadam_stage1_learning_input.json"

SCORER_INPUT_ARTIFACTS = (
    SOURCE_UNIVERSE_ARTIFACT,
    SOURCE_OPERATIONAL_ARTIFACT,
    TRADING_UNIVERSE_ARTIFACT,
    STRATEGY_UNIVERSE_ARTIFACT,
    ELIGIBILITY_ARTIFACT,
    STAGE1_LEARNING_INPUT_ARTIFACT,
)
FORBIDDEN_LABEL_KEYS = {
    "forward_return",
    "gross_return",
    "net_return",
    "price_after",
    "outcome",
    "label",
    "max_favorable_excursion",
    "max_adverse_excursion",
}
CRITICAL_FEATURES = (
    "fresh_source_quorum",
    "current_market_price",
    "volatility_context",
    "volume_or_flow_context",
)


@dataclass(frozen=True)
class PatternScoreBundle:
    feature_registry: dict[str, Any]
    primary: dict[str, Any]
    records: list[dict[str, Any]]
    rejections: list[dict[str, Any]]
    dashboard: dict[str, Any]


FEATURE_DEFINITIONS = (
    ("source_trust", "weighted_mean", "source trust posture", "available_at <= decision_at", "zero_and_block_if_missing", [0, 1], "source_reliability"),
    ("source_freshness", "fresh_ratio", "source operational state", "observed_at inside category budget", "zero_and_block_if_missing", [0, 1], "source_reliability"),
    ("fresh_source_quorum", "eligible_ratio", "source operational state", "fresh independent source only", "zero_and_block", [0, 1], "source_reliability"),
    ("source_independence", "cluster_ratio", "relationship eligibility graph", "cluster known before score", "conservative_half_weight", [0, 1], "point_in_time_alignment"),
    ("causal_mapping_strength", "causal_plus_half_broad_ratio", "relationship eligibility graph", "mapping frozen before labels", "zero", [0, 1], "research_design"),
    ("current_market_price", "presence_indicator", "trading universe current snapshot", "market observation <= decision_at", "zero_and_block", [0, 1], "market_data"),
    ("volatility_context", "presence_indicator", "trading universe current snapshot", "market observation <= decision_at", "zero_and_block", [0, 1], "market_data"),
    ("volume_or_flow_context", "presence_indicator", "trading universe current snapshot", "market observation <= decision_at", "zero_and_block", [0, 1], "market_data"),
    ("paperability_context", "guarded_route_indicator", "trading universe", "route metadata current at score", "zero", [0, 1], "paperops_boundary"),
    ("strategy_fit", "configured_family_mapping", "strategy universe", "strategy map frozen before score", "zero_for_agnostic", [0, 1], "strategy_research"),
    ("negative_control", "registered_control_indicator", "relationship eligibility graph", "control assigned before labels", "zero", [0, 1], "research_design"),
)

COMPONENT_WEIGHTS = {
    "source_trust": 0.18,
    "source_freshness": 0.18,
    "fresh_source_quorum": 0.12,
    "source_independence": 0.10,
    "causal_mapping_strength": 0.12,
    "current_market_price": 0.08,
    "volatility_context": 0.06,
    "volume_or_flow_context": 0.06,
    "paperability_context": 0.05,
    "strategy_fit": 0.05,
}


def score_pattern_feature_vector(
    features: dict[str, float],
    *,
    missing_critical_features: list[str] | None = None,
    negative_control: bool = False,
) -> dict[str, Any]:
    """Apply the frozen V3 component model to a point-in-time feature vector."""
    normalized = {
        feature: clamp(safe_float(features.get(feature)))
        for feature in (*COMPONENT_WEIGHTS, "negative_control")
    }
    contributions = {
        feature: round(normalized[feature] * weight, 8)
        for feature, weight in COMPONENT_WEIGHTS.items()
    }
    penalties = {
        "stale_source_penalty": round(
            0.15 * (1.0 - normalized["source_freshness"]), 8
        ),
        "missing_market_penalty": (
            0.12 if not normalized["current_market_price"] else 0.0
        ),
        "missing_volatility_penalty": (
            0.06 if not normalized["volatility_context"] else 0.0
        ),
        "missing_volume_penalty": (
            0.06 if not normalized["volume_or_flow_context"] else 0.0
        ),
        "source_duplication_penalty": round(
            0.08 * (1.0 - normalized["source_independence"]), 8
        ),
        "negative_control_penalty": 0.25 if negative_control else 0.0,
    }
    gross = round(sum(contributions.values()), 8)
    penalty_total = round(sum(penalties.values()), 8)
    raw_score = clamp(gross - penalty_total)
    missing = list(
        missing_critical_features
        if missing_critical_features is not None
        else [
            feature
            for feature in CRITICAL_FEATURES
            if not normalized.get(feature)
        ]
    )
    return {
        "features": normalized,
        "component_contributions": contributions,
        "penalties": penalties,
        "gross_component_score": gross,
        "penalty_total": penalty_total,
        "raw_pattern_score": raw_score,
        "missing_critical_features": missing,
        "confidence_state": (
            "blocked_missing_critical_features" if missing else "score_ready_for_tape"
        ),
    }


def build_feature_registry(generated_at: str | None = None) -> dict[str, Any]:
    generated = generated_at or now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_feature_registry",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "feature_registry_frozen",
        "feature_set_version": FEATURE_SET_VERSION,
        "score_model_version": MODEL_VERSION,
        "features": [
            {
                "feature_id": feature_id,
                "transformation": transformation,
                "input_provenance": provenance,
                "availability_rule": availability,
                "missing_value_policy": missing,
                "expected_range": expected_range,
                "owner": owner,
                "label_access_allowed": False,
            }
            for feature_id, transformation, provenance, availability, missing, expected_range, owner in FEATURE_DEFINITIONS
        ],
        "strategy_feature_packs": {
            strategy_id: {
                "direction_hypothesis": hypothesis["direction"],
                "horizon_hypothesis": hypothesis["horizon"],
                "features": list(COMPONENT_WEIGHTS),
            }
            for strategy_id, hypothesis in STRATEGY_HYPOTHESES.items()
        },
        "strategy_agnostic_feature_pack": {
            "features": [feature for feature in COMPONENT_WEIGHTS if feature != "strategy_fit"],
            "direction_hypothesis": "undetermined_before_evidence",
            "horizon_hypothesis": "3d_forward",
        },
        "negative_control_feature_pack": {
            "features": ["negative_control", "source_trust", "source_freshness"],
            "assignment_frozen_before_labels": True,
        },
        "llm_extraction_policy": {
            "local_gemma_allowed": True,
            "structured_json_required": True,
            "cache_key_fields": ["content_sha256", "prompt_version", "model_version"],
            "historical_cache_present": False,
            "frontier_gemini_score_mutation_allowed": False,
            "frontier_review_role": "post_score_shortlist_challenge_only",
        },
        "rank_score_v2_policy": {
            "artifact": "data/runtime/qadam_pattern_engine_v2_records.jsonl",
            "role": "research_ranking_reference_only",
            "used_in_v3_score": False,
            "reason": "V2 rank_score is not a probability or validated edge.",
        },
        "authority": authority_flags(),
    }


def _latest_timestamp(values: list[Any]) -> str | None:
    parsed: list[tuple[datetime, str]] = []
    for value in values:
        if not value:
            continue
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        parsed.append((timestamp.astimezone(timezone.utc), str(value)))
    return max(parsed)[0].isoformat() if parsed else None


def _feature_values(
    source_keys: list[str],
    instrument: dict[str, Any],
    *,
    sources_by_key: dict[str, dict[str, Any]],
    operational_by_key: dict[str, dict[str, Any]],
    eligibility_by_pair: dict[tuple[str, str], dict[str, Any]],
    strategy_fit: float,
    negative_control: bool = False,
) -> tuple[dict[str, float], list[dict[str, Any]], list[str], str | None]:
    symbol = str(instrument.get("symbol") or "unknown")
    source_rows: list[dict[str, Any]] = []
    for key in source_keys:
        source = sources_by_key.get(key, {})
        operational = operational_by_key.get(key, {})
        relationship = eligibility_by_pair.get((key, symbol), {})
        source_rows.append(
            {
                "source_key": key,
                "trust_score": safe_float(source.get("trust_score")),
                "fresh": operational.get("freshness_state") == "fresh",
                "quorum_eligible": operational.get("source_quorum_eligible") is True,
                "available_at": operational.get("observed_at"),
                "mapping_class": relationship.get("mapping_class"),
                "independence_cluster_id": relationship.get("source_independence_cluster_id"),
                "provenance": [
                    f"data/runtime/{SOURCE_UNIVERSE_ARTIFACT}",
                    f"data/runtime/{SOURCE_OPERATIONAL_ARTIFACT}",
                    f"data/runtime/{ELIGIBILITY_ARTIFACT}",
                ],
            }
        )
    count = len(source_rows)
    trust = sum(row["trust_score"] for row in source_rows) / count if count else 0.0
    freshness = sum(row["fresh"] for row in source_rows) / count if count else 0.0
    quorum = sum(row["quorum_eligible"] for row in source_rows) / count if count else 0.0
    clusters = {row["independence_cluster_id"] for row in source_rows if row["independence_cluster_id"]}
    independence = len(clusters) / count if count else 0.0
    mapping = (
        sum(
            1.0 if row["mapping_class"] == "causal_strategy_mapping" else 0.5
            if row["mapping_class"] == "broad_discovery_mapping"
            else 0.0
            for row in source_rows
        )
        / count
        if count
        else 0.0
    )
    price_present = instrument.get("price_or_odds_value") is not None
    volatility_present = instrument.get("rolling_volatility_20d") is not None or str(
        instrument.get("volatility_context")
    ) == "available"
    volume_present = str(instrument.get("volume_context")) == "available"
    paperability = instrument.get("paper_route_available") is True
    features = {
        "source_trust": clamp(trust),
        "source_freshness": clamp(freshness),
        "fresh_source_quorum": clamp(quorum),
        "source_independence": clamp(independence),
        "causal_mapping_strength": clamp(mapping),
        "current_market_price": float(price_present),
        "volatility_context": float(volatility_present),
        "volume_or_flow_context": float(volume_present),
        "paperability_context": float(paperability),
        "strategy_fit": clamp(strategy_fit),
        "negative_control": float(negative_control),
    }
    missing: list[str] = []
    if quorum <= 0:
        missing.append("fresh_source_quorum")
    if not price_present:
        missing.append("current_market_price")
    if not volatility_present:
        missing.append("volatility_context")
    if not volume_present:
        missing.append("volume_or_flow_context")
    decision_at = _latest_timestamp(
        [row["available_at"] for row in source_rows] + [instrument.get("market_observation_timestamp")]
    )
    return features, source_rows, missing, decision_at


def _score_record(
    *,
    strategy_id: str | None,
    strategy_label: str,
    instrument: dict[str, Any],
    source_keys: list[str],
    sources_by_key: dict[str, dict[str, Any]],
    operational_by_key: dict[str, dict[str, Any]],
    eligibility_by_pair: dict[tuple[str, str], dict[str, Any]],
    generated_at: str,
    applied_learning_version_ids: list[str],
    stage1_learning_input_version: str | None,
    strategy_agnostic: bool = False,
    negative_control: bool = False,
) -> dict[str, Any]:
    features, source_rows, missing, decision_at = _feature_values(
        source_keys,
        instrument,
        sources_by_key=sources_by_key,
        operational_by_key=operational_by_key,
        eligibility_by_pair=eligibility_by_pair,
        strategy_fit=0.0 if strategy_agnostic else 1.0,
        negative_control=negative_control,
    )
    scored = score_pattern_feature_vector(
        features,
        missing_critical_features=missing,
        negative_control=negative_control,
    )
    symbol = str(instrument.get("symbol") or "unknown")
    hypothesis = STRATEGY_HYPOTHESES.get(
        strategy_id or "",
        {"direction": "undetermined_before_evidence", "horizon": "3d_forward"},
    )
    input_material = {
        "model_version": MODEL_VERSION,
        "feature_set_version": FEATURE_SET_VERSION,
        "strategy_id": strategy_id,
        "instrument": symbol,
        "direction_hypothesis": hypothesis["direction"],
        "horizon_hypothesis": hypothesis["horizon"],
        "features": features,
        "source_rows": source_rows,
        "applied_learning_version_ids": applied_learning_version_ids,
        "stage1_learning_input_version": stage1_learning_input_version,
    }
    fingerprint = sha256_text(canonical_json(input_material))
    score_id = stable_id("pattern-score-v3", MODEL_VERSION, fingerprint)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_v3_record",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "score_id": score_id,
        "feature_vector_id": stable_id("feature-vector-v3", FEATURE_SET_VERSION, fingerprint),
        "model_version": MODEL_VERSION,
        "feature_set_version": FEATURE_SET_VERSION,
        "input_fingerprint": fingerprint,
        "applied_learning_version_ids": applied_learning_version_ids,
        "stage1_learning_input_version": stage1_learning_input_version,
        "scoring_as_of": decision_at,
        "strategy_family_id": strategy_id,
        "strategy_label": strategy_label,
        "strategy_agnostic": strategy_agnostic,
        "negative_control": negative_control,
        "instrument": symbol,
        "market_family": instrument.get("market_family"),
        "direction_hypothesis": hypothesis["direction"],
        "horizon_hypothesis": hypothesis["horizon"],
        "features": scored["features"],
        "feature_inputs": source_rows,
        "component_contributions": scored["component_contributions"],
        "penalties": scored["penalties"],
        "gross_component_score": scored["gross_component_score"],
        "penalty_total": scored["penalty_total"],
        "raw_pattern_score": scored["raw_pattern_score"],
        "score_is_probability": False,
        "score_is_validated_edge": False,
        "rank_score_v2_used": False,
        "label_fields_available_to_scorer": False,
        "missing_critical_features": scored["missing_critical_features"],
        "confidence_state": scored["confidence_state"],
        "permitted_next_action": (
            "wait_for_real_evidence"
            if missing
            else "append_to_historical_score_tape_research_only"
        ),
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "provenance": [f"data/runtime/{artifact}" for artifact in SCORER_INPUT_ARTIFACTS],
        "authority": authority_flags(),
    }


def _record_set_material_hash(records: list[dict[str, Any]]) -> str:
    material = [
        {
            "score_id": record.get("score_id"),
            "input_fingerprint": record.get("input_fingerprint"),
            "raw_pattern_score": record.get("raw_pattern_score"),
            "confidence_state": record.get("confidence_state"),
            "missing_critical_features": record.get("missing_critical_features", []),
            "permitted_next_action": record.get("permitted_next_action"),
        }
        for record in records
    ]
    return sha256_text(canonical_json(material))


def build_pattern_score_bundle(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> PatternScoreBundle:
    generated = generated_at or now_iso()
    runtime = runtime_dir(settings)
    source_universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    trading_universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    strategy_universe = read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT)
    sources = source_universe.get("sources") if isinstance(source_universe.get("sources"), list) else []
    instruments = trading_universe.get("instruments") if isinstance(trading_universe.get("instruments"), list) else []
    strategies = (
        strategy_universe.get("all_strategy_rows")
        if isinstance(strategy_universe.get("all_strategy_rows"), list)
        else []
    )
    operational = read_jsonl(runtime / SOURCE_OPERATIONAL_ARTIFACT)
    eligibility = read_jsonl(runtime / ELIGIBILITY_ARTIFACT)
    stage1_learning = read_json(runtime / STAGE1_LEARNING_INPUT_ARTIFACT)
    applied_learning_version_ids = sorted(
        {
            str(value)
            for value in stage1_learning.get("applied_learning_version_ids", [])
            if value
        }
    )
    stage1_learning_input_version = stage1_learning.get("input_version")
    sources_by_key = {str(record.get("source_key")): record for record in sources}
    instruments_by_symbol = {str(record.get("symbol")): record for record in instruments}
    operational_by_key = {str(record.get("source_key")): record for record in operational}
    eligibility_by_pair = {
        (str(record.get("source_key")), str(record.get("instrument"))): record
        for record in eligibility
    }
    records: list[dict[str, Any]] = []
    for strategy in strategies:
        strategy_id = str(strategy.get("strategy_family_id") or "unknown")
        source_keys = [str(value) for value in strategy.get("source_keywords", [])]
        for market in strategy.get("watched_markets", []):
            symbol = str(market.get("symbol") or "")
            instrument = instruments_by_symbol.get(symbol, market)
            records.append(
                _score_record(
                    strategy_id=strategy_id,
                    strategy_label=str(strategy.get("label") or strategy_id),
                    instrument=instrument,
                    source_keys=source_keys,
                    sources_by_key=sources_by_key,
                    operational_by_key=operational_by_key,
                    eligibility_by_pair=eligibility_by_pair,
                    generated_at=generated,
                    applied_learning_version_ids=applied_learning_version_ids,
                    stage1_learning_input_version=stage1_learning_input_version,
                )
            )
    for instrument in instruments:
        symbol = str(instrument.get("symbol") or "")
        mapped_sources = sorted(
            {
                str(record.get("source_key"))
                for record in eligibility
                if record.get("instrument") == symbol
                and record.get("mapping_class") in {
                    "causal_strategy_mapping",
                    "broad_discovery_mapping",
                }
            }
        )
        records.append(
            _score_record(
                strategy_id=None,
                strategy_label="Strategy-agnostic discovery",
                instrument=instrument,
                source_keys=mapped_sources,
                sources_by_key=sources_by_key,
                operational_by_key=operational_by_key,
                eligibility_by_pair=eligibility_by_pair,
                generated_at=generated,
                applied_learning_version_ids=applied_learning_version_ids,
                stage1_learning_input_version=stage1_learning_input_version,
                strategy_agnostic=True,
            )
        )
    negative_by_instrument: dict[str, list[str]] = {}
    for relationship in eligibility:
        if relationship.get("mapping_class") == "negative_control":
            negative_by_instrument.setdefault(str(relationship.get("instrument")), []).append(
                str(relationship.get("source_key"))
            )
    for symbol, source_keys in sorted(negative_by_instrument.items()):
        instrument = instruments_by_symbol.get(symbol)
        if not instrument:
            continue
        records.append(
            _score_record(
                strategy_id=None,
                strategy_label="Frozen negative control",
                instrument=instrument,
                source_keys=sorted(source_keys),
                sources_by_key=sources_by_key,
                operational_by_key=operational_by_key,
                eligibility_by_pair=eligibility_by_pair,
                generated_at=generated,
                applied_learning_version_ids=applied_learning_version_ids,
                stage1_learning_input_version=stage1_learning_input_version,
                strategy_agnostic=True,
                negative_control=True,
            )
        )
    records.sort(key=lambda record: (record["negative_control"], -record["raw_pattern_score"], record["score_id"]))
    rejections = [
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_pattern_score_v3_rejection",
            "generated_at": generated,
            "relationship_id": relationship.get("relationship_id"),
            "source_key": relationship.get("source_key"),
            "instrument": relationship.get("instrument"),
            "rejection_reason": "pair_intentionally_not_meaningful",
            "score_created": False,
            "authority": authority_flags(),
        }
        for relationship in eligibility
        if relationship.get("mapping_class") == "pair_intentionally_not_meaningful"
    ]
    confidence_counts = Counter(record["confidence_state"] for record in records)
    record_set_material_hash = _record_set_material_hash(records)
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "pattern_score_v3_ready_with_evidence_holds",
        "model_version": MODEL_VERSION,
        "feature_set_version": FEATURE_SET_VERSION,
        "record_count": len(records),
        "strategy_informed_record_count": sum(not record["strategy_agnostic"] for record in records),
        "strategy_agnostic_record_count": sum(record["strategy_agnostic"] and not record["negative_control"] for record in records),
        "negative_control_record_count": sum(record["negative_control"] for record in records),
        "rejection_count": len(rejections),
        "confidence_state_counts": dict(sorted(confidence_counts.items())),
        "labels_read_by_scorer": False,
        "forward_returns_read_by_scorer": False,
        "frontier_llm_called": False,
        "local_llm_called": False,
        "record_set_hash": record_set_hash(records),
        "record_set_material_hash": record_set_material_hash,
        "input_material_fingerprint": record_set_material_hash,
        "applied_learning_version_ids": applied_learning_version_ids,
        "applied_learning_version_count": len(applied_learning_version_ids),
        "stage1_learning_input_version": stage1_learning_input_version,
        "input_artifacts": [f"data/runtime/{artifact}" for artifact in SCORER_INPUT_ARTIFACTS],
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_v3_dashboard_summary",
        "generated_at": generated,
        "status": primary["status"],
        "headline": "Qadam can score current evidence, but missing market context blocks confidence",
        "plain_english": (
            "The score measures how much source-side evidence exists before outcomes are known. "
            "It is not a probability, trade instruction, or proof that the idea made money."
        ),
        "record_count": len(records),
        "input_material_fingerprint": record_set_material_hash,
        "ready_for_tape_count": confidence_counts.get("score_ready_for_tape", 0),
        "blocked_missing_evidence_count": confidence_counts.get("blocked_missing_critical_features", 0),
        "applied_learning_version_count": len(applied_learning_version_ids),
        "top_records": [
            {
                "score_id": record["score_id"],
                "strategy": record["strategy_label"],
                "instrument": record["instrument"],
                "raw_pattern_score": record["raw_pattern_score"],
                "confidence_state": record["confidence_state"],
                "missing_critical_features": record["missing_critical_features"],
            }
            for record in records
            if not record["negative_control"]
        ][:8],
        "authority": authority_flags(),
    }
    return PatternScoreBundle(
        feature_registry=build_feature_registry(generated),
        primary=primary,
        records=records,
        rejections=rejections,
        dashboard=dashboard,
    )


def validate_pattern_score_bundle(bundle: PatternScoreBundle) -> list[str]:
    errors: list[str] = []
    if not bundle.records:
        errors.append("pattern_score_v3_records_empty")
    if bundle.primary.get("labels_read_by_scorer") is not False:
        errors.append("pattern_score_scorer_read_labels")
    if bundle.primary.get("forward_returns_read_by_scorer") is not False:
        errors.append("pattern_score_scorer_read_forward_returns")
    if any(contains_forbidden_key(record, FORBIDDEN_LABEL_KEYS) for record in bundle.records):
        errors.append("pattern_score_record_contains_label_field")
    for record in bundle.records:
        score = safe_float(record.get("raw_pattern_score"), -1.0)
        if not 0.0 <= score <= 1.0:
            errors.append(f"pattern_score_out_of_bounds:{record.get('score_id')}")
        contributions = sum(safe_float(value) for value in record.get("component_contributions", {}).values())
        penalties = sum(safe_float(value) for value in record.get("penalties", {}).values())
        if abs(contributions - safe_float(record.get("gross_component_score"))) > 1e-7:
            errors.append(f"pattern_component_sum_mismatch:{record.get('score_id')}")
        if abs(penalties - safe_float(record.get("penalty_total"))) > 1e-7:
            errors.append(f"pattern_penalty_sum_mismatch:{record.get('score_id')}")
        expected = clamp(contributions - penalties)
        if abs(expected - score) > 1e-7:
            errors.append(f"pattern_final_score_mismatch:{record.get('score_id')}")
        missing = record.get("missing_critical_features", [])
        if missing and record.get("confidence_state") != "blocked_missing_critical_features":
            errors.append(f"pattern_missing_feature_not_blocked:{record.get('score_id')}")
        features = record.get("features", {})
        if safe_float(features.get("source_independence"), 1.0) < 1.0 and safe_float(
            record.get("penalties", {}).get("source_duplication_penalty")
        ) <= 0:
            errors.append(f"pattern_duplicate_source_not_penalized:{record.get('score_id')}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="pattern_score"))
        if record.get("applied_learning_version_ids") != bundle.primary.get(
            "applied_learning_version_ids"
        ):
            errors.append(f"pattern_learning_lineage_mismatch:{record.get('score_id')}")
    if not any(record.get("strategy_agnostic") is True and not record.get("negative_control") for record in bundle.records):
        errors.append("strategy_agnostic_discovery_missing")
    if not any(record.get("negative_control") is True for record in bundle.records):
        errors.append("negative_control_score_missing")
    errors.extend(validate_authority(bundle.feature_registry.get("authority", {}), prefix="feature_registry"))
    errors.extend(validate_authority(bundle.primary.get("authority", {}), prefix="pattern_score_primary"))
    return unique_errors(errors)


def build_and_write_pattern_score_v3(
    settings: Settings | None = None,
) -> tuple[PatternScoreBundle, dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    bundle = build_pattern_score_bundle(settings)
    errors = validate_pattern_score_bundle(bundle)
    fixed = "2000-01-01T00:00:00+00:00"
    deterministic_a = build_pattern_score_bundle(settings, generated_at=fixed)
    deterministic_b = build_pattern_score_bundle(settings, generated_at=fixed)
    deterministic = record_set_hash(deterministic_a.records) == record_set_hash(deterministic_b.records)
    if not deterministic:
        errors.append("pattern_score_deterministic_rerun_failed")
    errors = unique_errors(errors)
    previous_primary = read_json(runtime / PRIMARY_ARTIFACT)
    current_material_fingerprint = bundle.primary["input_material_fingerprint"]
    previous_material_fingerprint = previous_primary.get("input_material_fingerprint")
    material_change_detected = (
        previous_material_fingerprint != current_material_fingerprint
        or not (runtime / RECORDS_ARTIFACT).is_file()
    )
    if material_change_detected or errors:
        store.write_json(FEATURE_REGISTRY_ARTIFACT, bundle.feature_registry)
        store.write_json(PRIMARY_ARTIFACT, bundle.primary)
        store.write_jsonl(RECORDS_ARTIFACT, bundle.records)
        store.write_jsonl(REJECTIONS_ARTIFACT, bundle.rejections)
        store.write_json(DASHBOARD_ARTIFACT, bundle.dashboard)
    last_material_change_at = (
        bundle.primary["generated_at"]
        if material_change_detected
        else previous_primary.get("generated_at")
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_v3_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "record_count": len(bundle.records),
        "strategy_agnostic_record_count": bundle.primary["strategy_agnostic_record_count"],
        "negative_control_record_count": bundle.primary["negative_control_record_count"],
        "deterministic_rerun_passed": deterministic,
        "material_change_detected": material_change_detected,
        "input_material_fingerprint": current_material_fingerprint,
        "previous_input_material_fingerprint": previous_material_fingerprint,
        "last_material_change_at": last_material_change_at,
        "canonical_score_generation_preserved": not material_change_detected,
        "future_field_denial_passed": not any(
            contains_forbidden_key(record, FORBIDDEN_LABEL_KEYS) for record in bundle.records
        ),
        "missing_feature_policy_passed": all(
            not record["missing_critical_features"]
            or record["confidence_state"] == "blocked_missing_critical_features"
            for record in bundle.records
        ),
        "applied_learning_version_count": bundle.primary[
            "applied_learning_version_count"
        ],
        "applied_learning_lineage_passed": not any(
            error.startswith("pattern_learning_lineage_mismatch") for error in errors
        ),
        "score_bound_and_component_sum_passed": not any(
            "score_" in error or "component_sum" in error or "penalty_sum" in error
            for error in errors
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
