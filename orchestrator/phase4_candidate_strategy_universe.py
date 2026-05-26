"""Phase 4 candidate strategy universe.

Candidate strategy families are draft strategic hypotheses. They are not trade
candidates and cannot be handed to Risk Agent, Execution Policy, staged paper
orders, brokers, quantum providers, schedulers, or live capital.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.phase4_data_veracity import build_data_veracity_audit
from orchestrator.phase4_resource_validation import build_resource_validation
from orchestrator.phase4_trust_scores import build_trust_score_recalculation
from orchestrator.phase4_world_model_validation import build_world_model_validation
from orchestrator.strategy_research_intake import build_strategy_research_intake


CANDIDATE_STRATEGY_UNIVERSE_SCHEMA_VERSION = 1

FIRST_TRADING_UNIVERSE: tuple[str, ...] = (
    "prediction_markets",
    "crude_oil",
    "defence",
    "silver",
    "semiconductors",
)

CANDIDATE_AUTHORITY_FLAGS: tuple[str, ...] = (
    "signal_authority",
    "signal_confidence_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_authority",
    "execution_policy_handoff_allowed",
    "execution_authority",
    "paper_order_authority",
    "staged_paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_authority",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

PREFERENCE_CONTEXT_AUTHORITY_FLAGS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "preference_only_confirmation_allowed",
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "quantum_provider_call_allowed",
    "hardware_submission_allowed",
    "scheduler_enabled",
    "live_capital_authority",
)

PREFERENCE_CONTEXT_BOUNDARY = (
    "Preference/PREF MCP can provide supplemental domain-pack context only. It is not source 36, "
    "does not receive canonical source weight, cannot satisfy source quorum, cannot confirm a trade "
    "by itself, and cannot create trade candidates, approve risk, route execution, write brokers, "
    "call quantum providers, enable schedulers, or enable live capital."
)

PREFERENCE_DOMAIN_PACK_BLUEPRINTS: dict[str, tuple[dict[str, str], ...]] = {
    "prediction_market_geopolitical_dislocation": (
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "event_probability_and_liquidity_context",
            "allowed_context_role": "market_context_only",
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "geopolitical_narrative_context",
            "allowed_context_role": "narrative_context_only",
        },
    ),
    "crude_oil_energy_security_disruption": (
        {
            "domain_pack": "physical_movement",
            "strategy_role": "vessel_chokepoint_context",
            "allowed_context_role": "physical_context_only",
        },
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "weather_and_oil_linked_context",
            "allowed_context_role": "macro_commodity_context_only",
        },
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "oil_linked_prediction_market_context",
            "allowed_context_role": "market_context_only",
        },
    ),
    "defence_repricing_geopolitical_watch": (
        {
            "domain_pack": "filings_corporate",
            "strategy_role": "sec_filing_metadata_context",
            "allowed_context_role": "filing_context_only",
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "procurement_and_policy_narrative_context",
            "allowed_context_role": "narrative_context_only",
        },
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "conflict_and_defence_event_market_context",
            "allowed_context_role": "market_context_only",
        },
    ),
    "silver_macro_liquidity_stress": (
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "macro_weather_physical_supply_context",
            "allowed_context_role": "macro_commodity_context_only",
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "market_stress_narrative_context",
            "allowed_context_role": "narrative_context_only",
        },
    ),
    "semiconductor_policy_options_asymmetry": (
        {
            "domain_pack": "filings_corporate",
            "strategy_role": "sec_filing_and_disclosure_context",
            "allowed_context_role": "filing_context_only",
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "policy_export_control_narrative_context",
            "allowed_context_role": "narrative_context_only",
        },
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "rates_and_macro_policy_context",
            "allowed_context_role": "macro_context_only",
        },
        {
            "domain_pack": "crypto_wallets",
            "strategy_role": "risk_sentiment_only",
            "allowed_context_role": "risk_sentiment_only",
        },
    ),
}


@dataclass(frozen=True)
class StrategyFamilyBlueprint:
    candidate_key: str
    name: str
    instrument_universe: tuple[str, ...]
    catalyst_classes: tuple[str, ...]
    required_source_groups: tuple[str, ...]
    resource_references: tuple[str, ...]
    world_model_frames: tuple[str, ...]
    risk_assumptions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    no_trade_conditions: tuple[str, ...]


@dataclass(frozen=True)
class StrategyFamilyCandidate:
    object_type: str
    candidate_key: str
    name: str
    status: str
    instrument_universe: tuple[str, ...]
    catalyst_classes: tuple[str, ...]
    required_source_groups: tuple[str, ...]
    source_weights: dict[str, float]
    model_weights: dict[str, float]
    market_confirmation_requirements: dict[str, Any]
    preference_context_policy: dict[str, Any]
    quantum_role: dict[str, Any]
    strategy_research_context: dict[str, Any]
    risk_assumptions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    no_trade_conditions: tuple[str, ...]
    resource_references: tuple[str, ...]
    world_model_frames: tuple[str, ...]
    strategy_lead_context: dict[str, Any]
    signal_integrity_context: dict[str, Any]
    head_of_quant_context: dict[str, Any]
    evidence_inputs: dict[str, Any]
    risk_agent_handoff_allowed: bool
    execution_policy_handoff_allowed: bool
    trade_candidate_created: bool
    execution_allowed: bool
    paper_order_allowed: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    authority_flags: dict[str, bool]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["instrument_universe"] = list(self.instrument_universe)
        payload["catalyst_classes"] = list(self.catalyst_classes)
        payload["required_source_groups"] = list(self.required_source_groups)
        payload["risk_assumptions"] = list(self.risk_assumptions)
        payload["invalidation_conditions"] = list(self.invalidation_conditions)
        payload["no_trade_conditions"] = list(self.no_trade_conditions)
        payload["resource_references"] = list(self.resource_references)
        payload["world_model_frames"] = list(self.world_model_frames)
        return payload


STRATEGY_BLUEPRINTS: tuple[StrategyFamilyBlueprint, ...] = (
    StrategyFamilyBlueprint(
        candidate_key="prediction_market_geopolitical_dislocation",
        name="Prediction Market Geopolitical Dislocation",
        instrument_universe=("prediction_markets",),
        catalyst_classes=("conflict_escalation", "narrative_coordination", "policy_shock"),
        required_source_groups=("polymarket", "gdelt", "rss", "telegram", "acled", "conflict_tracker"),
        resource_references=("black_scholes_prediction_markets", "anatomy_of_polymarket", "edge_beats_excitement"),
        world_model_frames=("narrative_coordination_as_market_force", "institutional_self_preservation_blind_spot"),
        risk_assumptions=(
            "Binary-event probability can move before official confirmation.",
            "Prediction-market pricing must be independently corroborated before any later risk review.",
        ),
        invalidation_conditions=(
            "Polymarket or narrative sources are stale, unavailable, or single-source only.",
            "Conflict source posture contradicts the event narrative.",
        ),
        no_trade_conditions=(
            "No non-Yahoo independent market confirmation is present.",
            "Signal Integrity remains blocked or hold-only for missing second-source evidence.",
        ),
    ),
    StrategyFamilyBlueprint(
        candidate_key="crude_oil_energy_security_disruption",
        name="Crude Oil Energy Security Disruption",
        instrument_universe=("crude_oil",),
        catalyst_classes=("energy_security", "shipping_chokepoint", "conflict_fire"),
        required_source_groups=("nasa_firms", "gdelt", "acled", "fred", "bis", "conflict_tracker"),
        resource_references=("bridgewater_risk_assessment", "edge_beats_excitement", "paper_forward_evidence"),
        world_model_frames=(
            "hierarchical_power_flows_through_energy_security_and_money",
            "us_china_grand_bargain_scenario",
        ),
        risk_assumptions=(
            "Energy-security shocks can reprice crude before policy confirmation.",
            "Macro liquidity context can amplify or dampen commodity shock transmission.",
        ),
        invalidation_conditions=(
            "Physical or conflict evidence fails to confirm the claimed disruption.",
            "Macro source posture contradicts the commodity-risk narrative.",
        ),
        no_trade_conditions=(
            "Physical evidence is degraded or unavailable.",
            "Crude market confirmation is stale, unavailable, or Yahoo-only.",
        ),
    ),
    StrategyFamilyBlueprint(
        candidate_key="defence_repricing_geopolitical_watch",
        name="Defence Repricing Geopolitical Watch",
        instrument_universe=("defence",),
        catalyst_classes=("defence_posture_shift", "conflict_escalation", "procurement_or_policy_signal"),
        required_source_groups=("acled", "gdelt", "sec_edgar", "rss", "nasa_firms", "conflict_tracker"),
        resource_references=("goldman_stock_screener", "bridgewater_risk_assessment", "citadel_technical_analysis"),
        world_model_frames=(
            "shadow_networks_as_coordination_risk",
            "narrative_coordination_as_market_force",
            "us_china_grand_bargain_scenario",
        ),
        risk_assumptions=(
            "Defence instruments can reprice around conflict posture and procurement narratives.",
            "Company-level exposure requires filing or market confirmation before future strategy approval.",
        ),
        invalidation_conditions=(
            "Conflict escalation is not corroborated across independent sources.",
            "Company-level filings or market confirmation do not support the exposure thesis.",
        ),
        no_trade_conditions=(
            "No company-level exposure map exists.",
            "Options or equity market confirmation is absent, stale, or Yahoo-only.",
        ),
    ),
    StrategyFamilyBlueprint(
        candidate_key="silver_macro_liquidity_stress",
        name="Silver Macro Liquidity Stress",
        instrument_universe=("silver",),
        catalyst_classes=("liquidity_stress", "rates_shock", "currency_confidence_shift"),
        required_source_groups=("fred", "bis", "ecb", "bls", "rss", "sec_edgar"),
        resource_references=("bridgewater_risk_assessment", "citadel_technical_analysis", "paper_forward_evidence"),
        world_model_frames=(
            "institutional_self_preservation_blind_spot",
            "hierarchical_power_flows_through_energy_security_and_money",
        ),
        risk_assumptions=(
            "Silver can act as a stress-sensitive macro proxy during liquidity or confidence breaks.",
            "Rates and institutional-policy data must dominate private world-model priors.",
        ),
        invalidation_conditions=(
            "Rates, liquidity, or institutional-source posture contradicts the stress thesis.",
            "Silver market confirmation is unavailable or fails to show a pricing gap.",
        ),
        no_trade_conditions=(
            "Macro source quorum is below threshold.",
            "No non-Yahoo market confirmation or transaction-cost assumption exists.",
        ),
    ),
    StrategyFamilyBlueprint(
        candidate_key="semiconductor_policy_options_asymmetry",
        name="Semiconductor Policy Options Asymmetry",
        instrument_universe=("semiconductors",),
        catalyst_classes=("export_control_shift", "ai_chip_supply_constraint", "policy_bargain"),
        required_source_groups=("sec_edgar", "patents", "gdelt", "fred", "rss", "alpaca"),
        resource_references=("goldman_stock_screener", "citadel_technical_analysis", "edge_beats_excitement"),
        world_model_frames=(
            "us_china_grand_bargain_scenario",
            "shadow_networks_as_coordination_risk",
            "narrative_coordination_as_market_force",
        ),
        risk_assumptions=(
            "Semiconductor catalysts are asymmetric when policy timing and options distribution diverge.",
            "Head of Quant output can annotate ambiguity only after Signal Integrity context exists.",
        ),
        invalidation_conditions=(
            "Policy, filing, or patent evidence fails to support the catalyst.",
            "Options or equity market confirmation is stale, unavailable, or single-source.",
        ),
        no_trade_conditions=(
            "Signal Integrity flags missing price confirmation or second-source evidence.",
            "Head of Quant recommendation is missing, rejected, or treated as execution authority.",
        ),
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            loaded = json.loads(stripped)
            if isinstance(loaded, dict):
                rows.append(loaded)
    if limit is not None:
        rows = rows[-limit:]
    return rows


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in CANDIDATE_AUTHORITY_FLAGS}


def _runtime_artifacts(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "data_veracity": _read_json(runtime / "phase4_data_veracity_audit.json") or build_data_veracity_audit(settings),
        "trust_scores": _read_json(runtime / "phase4_trust_score_recalculation.json")
        or build_trust_score_recalculation(settings),
        "resource_validation": _read_json(runtime / "phase4_resource_validation.json")
        or build_resource_validation(settings),
        "world_model_validation": _read_json(runtime / "phase4_world_model_validation.json")
        or build_world_model_validation(settings),
        "phase2_shadow_cycle": _read_json(runtime / "phase2_shadow_cycle.json") or {},
        "signal_integrity_reviews": _read_jsonl(runtime / "signal_integrity_reviews.jsonl", limit=200),
        "strategy_lead_packets": _read_jsonl(runtime / "strategy_lead_shadow_packets.jsonl", limit=80),
        "quantum_oracle_results": _read_jsonl(runtime / "quantum_oracle_results.jsonl", limit=50),
        "preference_domain_packs": _read_json(runtime / "preference_domain_packs.json") or {},
        "preference_shadow_context": _read_json(runtime / "preference_shadow_context.json") or {},
        "strategy_research_intake": _read_json(runtime / "strategy_research_intake.json")
        or build_strategy_research_intake(settings),
    }


def _source_score_lookup(trust_scores: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("source_key")): row for row in trust_scores.get("scores", []) if row.get("source_key")}


def _source_weights(source_keys: tuple[str, ...], trust_scores: dict[str, Any]) -> dict[str, float]:
    lookup = _source_score_lookup(trust_scores)
    raw_weights: dict[str, float] = {}
    for source_key in source_keys:
        row = lookup.get(source_key)
        if row is None or row.get("quarantine") is True:
            raw_weights[source_key] = 0.0
        else:
            raw_weights[source_key] = float(row.get("final_provisional_score") or 0.0)
    total = sum(raw_weights.values())
    if total <= 0:
        return {source_key: 0.0 for source_key in source_keys}
    weights = {source_key: round(weight / total, 4) for source_key, weight in raw_weights.items()}
    delta = round(1.0 - sum(weights.values()), 4)
    if weights and abs(delta) > 0:
        first_key = next(iter(weights))
        weights[first_key] = round(weights[first_key] + delta, 4)
    return weights


def _model_weights() -> dict[str, float]:
    return {
        "data_veracity": 0.24,
        "trust_score": 0.22,
        "signal_integrity_patterns": 0.16,
        "strategy_lead_challenges": 0.16,
        "resource_registry": 0.10,
        "world_model_lens": 0.08,
        "head_of_quant_shadow_annotation": 0.04,
    }


def _resource_statuses(resource_validation: dict[str, Any]) -> dict[str, str]:
    return {
        str(row.get("resource_key")): str(row.get("phase4_validation_status"))
        for row in resource_validation.get("resource_rows", [])
        if row.get("resource_key")
    }


def _world_model_statuses(world_model_validation: dict[str, Any]) -> dict[str, str]:
    return {
        str(row.get("claim_key")): str(row.get("validation_status"))
        for row in world_model_validation.get("claims", [])
        if row.get("claim_key")
    }


def _phase2_context(phase2: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": phase2.get("mode"),
        "status": phase2.get("status"),
        "durable_replay_contract_status": phase2.get("durable_replay_contract_status"),
        "durable_replay_replayed_source_count": phase2.get("durable_replay_replayed_source_count"),
        "durable_replay_missing_source_count": phase2.get("durable_replay_missing_source_count"),
        "queued_packet_count": phase2.get("queued_packet_count"),
        "shadow_signal_count": phase2.get("shadow_signal_count"),
        "signal_integrity_review_count": phase2.get("signal_integrity_review_count"),
        "signal_integrity_trade_candidate_created_count": phase2.get("signal_integrity_trade_candidate_created_count"),
        "strategy_lead_review_mode": phase2.get("strategy_lead_review_mode"),
        "strategy_lead_source_posture": phase2.get("strategy_lead_source_posture"),
        "strategy_lead_required_challenge_count": phase2.get("strategy_lead_required_challenge_count"),
        "write_authority": phase2.get("durable_replay_write_authority"),
        "signal_authority": phase2.get("durable_replay_signal_authority"),
        "order_authority": phase2.get("durable_replay_order_authority"),
    }


def _signal_integrity_context(reviews: list[dict[str, Any]], instrument_universe: tuple[str, ...]) -> dict[str, Any]:
    matching = [
        review
        for review in reviews
        if str(review.get("instrument_focus") or "") in instrument_universe
        or str(review.get("instrument_focus") or "") == "macro_watchlist"
    ]
    if not matching:
        matching = reviews[-10:]
    counts = Counter(str(review.get("status") or "unknown") for review in matching)
    failure_counts = Counter(
        reason
        for review in matching
        for reason in review.get("failure_reasons", [])
        if isinstance(reason, str)
    )
    return {
        "review_count": len(matching),
        "status_counts": dict(sorted(counts.items())),
        "top_failure_reasons": dict(failure_counts.most_common(5)),
        "trade_candidate_created_count": sum(1 for review in matching if review.get("trade_candidate_created") is True),
        "execution_allowed_count": sum(1 for review in matching if review.get("execution_allowed") is True),
        "paper_order_allowed_count": sum(1 for review in matching if review.get("paper_order_allowed") is True),
        "boundary": "Signal Integrity context is hold/block/pass metadata only and cannot create trade candidates.",
    }


def _strategy_lead_context(packets: list[dict[str, Any]], instrument_universe: tuple[str, ...]) -> dict[str, Any]:
    matching = [
        packet
        for packet in packets
        if str(packet.get("watch_focus") or "") in instrument_universe
        or str(packet.get("watch_focus") or "") == "macro_watchlist"
    ]
    if not matching:
        matching = packets[-10:]
    challenge_count = sum(len(packet.get("strategy_review", {}).get("required_challenges", [])) for packet in matching)
    return {
        "packet_count": len(matching),
        "required_challenge_count": challenge_count,
        "risk_handoff_allowed_count": sum(
            1 for packet in matching if packet.get("strategy_review", {}).get("risk_handoff_allowed") is True
        ),
        "trade_candidate_allowed_count": sum(
            1 for packet in matching if packet.get("strategy_review", {}).get("trade_candidate_allowed") is True
        ),
        "execution_allowed_count": sum(1 for packet in matching if packet.get("execution_allowed") is True),
        "paper_order_allowed_count": sum(1 for packet in matching if packet.get("paper_order_allowed") is True),
        "boundary": "Strategy Lead packets are challenge-only and cannot approve risk or create trade candidates.",
    }


def _head_of_quant_context(results: list[dict[str, Any]], instrument_universe: tuple[str, ...]) -> dict[str, Any]:
    matching = [
        result
        for result in results
        if str(result.get("result", {}).get("instrument_focus") or result.get("job", {}).get("instrument_focus") or "")
        in instrument_universe
    ]
    if not matching:
        matching = results[-10:]
    output_routes = [result.get("result", {}).get("output_routing", {}) for result in matching]
    return {
        "annotation_count": len(matching),
        "latest_recommendation": (matching[-1].get("result", {}).get("recommendation") if matching else None),
        "latest_backend": (matching[-1].get("result", {}).get("backend") if matching else None),
        "provider_call_allowed_count": sum(1 for route in output_routes if route.get("provider_call_allowed") is True),
        "hardware_submission_allowed_count": sum(
            1 for result in matching if result.get("result", {}).get("hardware_submission_allowed") is True
        ),
        "trade_candidate_created_count": sum(
            1 for result in matching if result.get("result", {}).get("trade_candidate_created") is True
        ),
        "route_type": "shadow_annotation",
        "boundary": "Head of Quant annotations are context only and cannot upgrade strategy candidates into trades.",
    }


def _market_confirmation_requirements() -> dict[str, Any]:
    return {
        "required": True,
        "non_yahoo_independent_confirmation_required": True,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "yahoo_only_confirmation_allowed": False,
        "pricing_gap_required": True,
        "stale_confirmation_allowed": False,
        "single_source_confirmation_allowed": False,
        "boundary": (
            "Market confirmation can support later review only. Yahoo Finance is supplemental "
            "and cannot be the sole market confirmation or source of trade, order, fill, receipt, or reconciliation truth."
        ),
    }


def _quantum_role() -> dict[str, Any]:
    return {
        "role": "shadow_annotation_optional",
        "allowed_jobs": ("pattern_recognition", "strategy_collapse"),
        "provider_call_allowed": False,
        "hardware_submission_allowed": False,
        "scheduler_enabled": False,
        "confidence_delta_allowed": False,
        "trade_candidate_creation_allowed": False,
        "boundary": "Head of Quant output can annotate ambiguity only; it cannot route risk, execution, paper orders, or hardware.",
    }


def _strategy_research_context(
    blueprint: StrategyFamilyBlueprint,
    *,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    intake = artifacts.get("strategy_research_intake", {})
    rows = intake.get("candidate_records", []) if isinstance(intake, dict) else []
    matched = [
        row
        for row in rows
        if isinstance(row, dict)
        and blueprint.candidate_key in {str(item) for item in row.get("qadam_family_links", [])}
    ]
    challenge_rows = [
        {
            "candidate_key": str(row.get("candidate_key") or ""),
            "challenge": str(challenge),
        }
        for row in matched
        for challenge in row.get("strategy_lead_challenges", [])[:2]
    ]
    return {
        "source_artifact_id": intake.get("artifact_id") if isinstance(intake, dict) else None,
        "source_status": intake.get("status") if isinstance(intake, dict) else "missing",
        "source_note_ref": intake.get("source_note_ref") if isinstance(intake, dict) else None,
        "matched_research_candidate_count": len(matched),
        "matched_research_candidates": [
            {
                "candidate_key": row.get("candidate_key"),
                "name": row.get("name"),
                "status": row.get("status"),
                "qadam_role": row.get("qadam_role"),
                "paperops_readiness": row.get("paperops_readiness"),
                "blockers": list(row.get("blockers", [])),
            }
            for row in matched
        ],
        "strategy_lead_challenges": challenge_rows[:8],
        "strategy_lead_challenge_count": len(challenge_rows),
        "candidate_registry_role": "external_research_context_only",
        "paperops_backtest_request_allowed": True,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": (
            "External strategy research is context only. It can annotate strategy families and seed review questions, "
            "but cannot create trade candidates, approve risk, route execution, stage orders, "
            "write brokers, or enable live capital."
        ),
    }


def _preference_authority_flags() -> dict[str, bool]:
    return {flag: False for flag in PREFERENCE_CONTEXT_AUTHORITY_FLAGS}


def _preference_static_domain_packs(candidate_key: str) -> list[dict[str, Any]]:
    return [
        {
            **pack,
            "approved_for_pref_7_mapping": True,
            "source_scope": "in_scope",
            "provenance_required": True,
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "domain_tool_calls_allowed": False,
            "paid_tool_allowed": False,
        }
        for pack in PREFERENCE_DOMAIN_PACK_BLUEPRINTS.get(candidate_key, ())
    ]


def _preference_mapping_lookup(domain_packs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(mapping.get("candidate_key")): mapping
        for mapping in domain_packs.get("mappings", [])
        if isinstance(mapping, dict) and mapping.get("candidate_key")
    }


def _preference_context_policy(
    blueprint: StrategyFamilyBlueprint,
    *,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    domain_packs = artifacts.get("preference_domain_packs", {})
    shadow_context = artifacts.get("preference_shadow_context", {})
    mapping = _preference_mapping_lookup(domain_packs).get(blueprint.candidate_key, {})
    mapped_domain_packs = list(mapping.get("mapped_domain_packs") or _preference_static_domain_packs(blueprint.candidate_key))
    approved_domain_pack_count = sum(
        1 for pack in mapped_domain_packs if pack.get("approved_for_pref_7_mapping") is True
    )
    no_trade_conditions = (
        "Preference-only context is a hold condition, not corroboration.",
        "Missing or invalid Preference provenance is a no-trade condition.",
        "Degraded Preference quota, unverified identity, stale context, or missing domain packs blocks live Preference use.",
        "Preference context cannot be used for source quorum, risk handoff, execution, paper orders, broker writes, or live capital.",
    )
    return {
        "source_key": "preference_mcp",
        "source_role": "supplemental_multi_source_data_plane",
        "status": "mapped_context_only" if approved_domain_pack_count else "hold_missing_domain_pack_mapping",
        "domain_pack_status": domain_packs.get("status") or "static_blueprint",
        "shadow_context_status": shadow_context.get("status") or "not_run",
        "shadow_context_role": shadow_context.get("context_role") or "not_run",
        "quota_degraded": bool(shadow_context.get("quota_degraded", True)),
        "context_stale": bool(shadow_context.get("context_stale", False)),
        "mapped_domain_packs": mapped_domain_packs,
        "approved_domain_pack_count": approved_domain_pack_count,
        "preference_context_allowed": approved_domain_pack_count > 0,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "market_confirmation_as_corroboration_only": True,
        "quota_freshness_degradation_rule": (
            "If Preference identity is unverified, quota metadata is missing, context is stale, "
            "or an approved domain pack is missing, Preference becomes hold-only context and cannot "
            "increase confidence or advance strategy state."
        ),
        "no_trade_conditions": list(no_trade_conditions),
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "authority_flags": _preference_authority_flags(),
        "boundary": PREFERENCE_CONTEXT_BOUNDARY,
    }


def _preference_artifact_policy(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    policies = [candidate.get("preference_context_policy", {}) for candidate in candidates]
    domain_packs = sorted(
        {
            str(pack.get("domain_pack"))
            for policy in policies
            for pack in policy.get("mapped_domain_packs", [])
            if isinstance(pack, dict) and pack.get("domain_pack")
        }
    )
    return {
        "source_key": "preference_mcp",
        "source_role": "supplemental_multi_source_data_plane",
        "status": "mapped_context_only",
        "candidate_family_count": len(candidates),
        "candidate_family_with_domain_pack_count": sum(
            1 for policy in policies if int(policy.get("approved_domain_pack_count", 0) or 0) > 0
        ),
        "approved_domain_packs": domain_packs,
        "approved_domain_pack_count": len(domain_packs),
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "quota_freshness_degradation_rule": (
            "Quota degradation, unverified identity, stale context, missing provenance, or missing "
            "domain-pack coverage makes Preference hold-only and blocks any confidence upgrade."
        ),
        "boundary": PREFERENCE_CONTEXT_BOUNDARY,
    }


def _candidate_from_blueprint(
    blueprint: StrategyFamilyBlueprint,
    *,
    artifacts: dict[str, Any],
) -> StrategyFamilyCandidate:
    source_weights = _source_weights(blueprint.required_source_groups, artifacts["trust_scores"])
    preference_policy = _preference_context_policy(blueprint, artifacts=artifacts)
    return StrategyFamilyCandidate(
        object_type="strategy_family_candidate",
        candidate_key=blueprint.candidate_key,
        name=blueprint.name,
        status="draft_strategic_hypothesis",
        instrument_universe=blueprint.instrument_universe,
        catalyst_classes=blueprint.catalyst_classes,
        required_source_groups=blueprint.required_source_groups,
        source_weights=source_weights,
        model_weights=_model_weights(),
        market_confirmation_requirements=_market_confirmation_requirements(),
        preference_context_policy=preference_policy,
        quantum_role=_quantum_role(),
        strategy_research_context=_strategy_research_context(blueprint, artifacts=artifacts),
        risk_assumptions=blueprint.risk_assumptions,
        invalidation_conditions=blueprint.invalidation_conditions
        + (
            "Required source weight is zero because the source is quarantined or missing.",
            "Preference provenance, domain-pack mapping, quota, freshness, or source-quorum policy contradicts the thesis.",
            "Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.",
        ),
        no_trade_conditions=blueprint.no_trade_conditions
        + (
            *tuple(str(item) for item in preference_policy["no_trade_conditions"]),
            "Candidate remains outside an approved Manifested Strategy Document.",
            "Risk Agent or Execution Policy handoff is requested before Phase 4 approval.",
        ),
        resource_references=blueprint.resource_references,
        world_model_frames=blueprint.world_model_frames,
        strategy_lead_context=_strategy_lead_context(artifacts["strategy_lead_packets"], blueprint.instrument_universe),
        signal_integrity_context=_signal_integrity_context(
            artifacts["signal_integrity_reviews"], blueprint.instrument_universe
        ),
        head_of_quant_context=_head_of_quant_context(artifacts["quantum_oracle_results"], blueprint.instrument_universe),
        evidence_inputs={
            "data_veracity_artifact_id": artifacts["data_veracity"].get("artifact_id"),
            "trust_score_artifact_id": artifacts["trust_scores"].get("artifact_id"),
            "resource_validation_artifact_id": artifacts["resource_validation"].get("artifact_id"),
            "world_model_validation_artifact_id": artifacts["world_model_validation"].get("artifact_id"),
            "resource_reference_statuses": {
                key: _resource_statuses(artifacts["resource_validation"]).get(key, "missing")
                for key in blueprint.resource_references
            },
            "world_model_frame_statuses": {
                key: _world_model_statuses(artifacts["world_model_validation"]).get(key, "missing")
                for key in blueprint.world_model_frames
            },
        },
        risk_agent_handoff_allowed=False,
        execution_policy_handoff_allowed=False,
        trade_candidate_created=False,
        execution_allowed=False,
        paper_order_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        authority_flags=_authority_flags(),
        boundary=(
            "This object is a strategy_family_candidate draft only. It cannot be treated as a "
            "trade candidate, submitted to Risk Agent or Execution Policy, staged as a paper order, "
            "written to a broker, or connected to live capital."
        ),
    )


def build_candidate_strategy_universe(settings: Settings | None = None) -> dict[str, Any]:
    artifacts = _runtime_artifacts(settings)
    candidates = [_candidate_from_blueprint(blueprint, artifacts=artifacts) for blueprint in STRATEGY_BLUEPRINTS]
    candidate_dicts = [candidate.to_dict() for candidate in candidates]
    authority_violations = [
        f"{candidate.candidate_key}:{flag}"
        for candidate in candidates
        for flag, enabled in candidate.authority_flags.items()
        if enabled is not False
    ]
    phase2_context = _phase2_context(artifacts["phase2_shadow_cycle"])
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "candidate_strategy_universe_schema_version": CANDIDATE_STRATEGY_UNIVERSE_SCHEMA_VERSION,
        "artifact_type": "candidate_strategy_universe",
        "artifact_id": "phase4:q4-7:candidate-strategy-universe",
        "status": "validated" if not authority_violations else "rejected",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Candidate strategy universe contains draft strategy hypotheses only, not trade candidates.",
        "first_trading_universe": list(FIRST_TRADING_UNIVERSE),
        "strategy_family_candidate_count": len(candidates),
        "draft_hypothesis_count": len([candidate for candidate in candidates if candidate.status == "draft_strategic_hypothesis"]),
        "trade_candidate_count": 0,
        "risk_agent_handoff_allowed_count": sum(1 for candidate in candidates if candidate.risk_agent_handoff_allowed),
        "execution_policy_handoff_allowed_count": sum(
            1 for candidate in candidates if candidate.execution_policy_handoff_allowed
        ),
        "execution_allowed_count": sum(1 for candidate in candidates if candidate.execution_allowed),
        "paper_order_allowed_count": sum(1 for candidate in candidates if candidate.paper_order_allowed),
        "broker_write_allowed_count": sum(1 for candidate in candidates if candidate.broker_write_allowed),
        "live_capital_enabled_count": sum(1 for candidate in candidates if candidate.live_capital_enabled),
        "authority_flag_violation_count": len(authority_violations),
        "authority_flag_violations": authority_violations,
        "phase2_shadow_context": phase2_context,
        "head_of_quant_policy": {
            "role": "shadow_annotation_context_only",
            "provider_call_allowed": False,
            "hardware_submission_allowed": False,
            "scheduler_enabled": False,
            "trade_candidate_creation_allowed": False,
        },
        "yahoo_finance_policy": {
            "role": "supplemental_market_confirmation_only",
            "canonical_rank_impact_allowed": False,
            "sole_market_confirmation_allowed": False,
            "trade_candidate_creation_allowed": False,
        },
        "preference_mcp_policy": _preference_artifact_policy(candidate_dicts),
        "strategy_research_intake_policy": {
            "source_artifact_id": artifacts["strategy_research_intake"].get("artifact_id"),
            "status": artifacts["strategy_research_intake"].get("status"),
            "source_note_ref": artifacts["strategy_research_intake"].get("source_note_ref"),
            "research_candidate_count": artifacts["strategy_research_intake"].get("candidate_count", 0),
            "strategy_family_with_research_context_count": sum(
                1
                for candidate in candidate_dicts
                if candidate.get("strategy_research_context", {}).get("matched_research_candidate_count", 0) > 0
            ),
            "strategy_lead_challenge_count": sum(
                int(candidate.get("strategy_research_context", {}).get("strategy_lead_challenge_count", 0) or 0)
                for candidate in candidate_dicts
            ),
            "paperops_backtest_request_allowed": True,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": "Strategy research intake is external research context only.",
        },
        "candidates": candidate_dicts,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_candidate_strategy_universe(artifact)
    return artifact


def validate_candidate_strategy_universe(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "candidate_strategy_universe":
        errors.append("artifact_type_not_candidate_strategy_universe")
    if artifact.get("trade_candidate_count") != 0:
        errors.append("trade_candidate_count_not_zero")

    candidates = artifact.get("candidates")
    if not isinstance(candidates, list):
        errors.append("strategy_candidates_missing")
        candidates = []
    if artifact.get("strategy_family_candidate_count") != len(candidates):
        errors.append("strategy_family_candidate_count_mismatch")
    if artifact.get("draft_hypothesis_count") != sum(
        1 for candidate in candidates if candidate.get("status") == "draft_strategic_hypothesis"
    ):
        errors.append("draft_hypothesis_count_mismatch")

    required_fields = {
        "object_type",
        "candidate_key",
        "instrument_universe",
        "catalyst_classes",
        "required_source_groups",
        "source_weights",
        "model_weights",
        "market_confirmation_requirements",
        "preference_context_policy",
        "quantum_role",
        "strategy_research_context",
        "risk_assumptions",
        "invalidation_conditions",
        "no_trade_conditions",
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "trade_candidate_created",
        "authority_flags",
        "boundary",
    }
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "unknown_candidate")
        missing = sorted(required_fields - set(candidate))
        if missing:
            errors.append(f"strategy_candidate_fields_missing:{candidate_key}:{','.join(missing)}")
        if candidate.get("object_type") != "strategy_family_candidate":
            errors.append(f"candidate_object_type_invalid:{candidate_key}:{candidate.get('object_type')}")
        if candidate.get("trade_candidate_created") is not False:
            errors.append(f"strategy_candidate_created_trade_candidate:{candidate_key}")
        if candidate.get("risk_agent_handoff_allowed") is not False:
            errors.append(f"strategy_candidate_risk_handoff_allowed:{candidate_key}")
        if candidate.get("execution_policy_handoff_allowed") is not False:
            errors.append(f"strategy_candidate_execution_policy_handoff_allowed:{candidate_key}")
        for key in ("execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled"):
            if candidate.get(key) is not False:
                errors.append(f"strategy_candidate_authority_enabled:{candidate_key}:{key}")
        for field in (
            "instrument_universe",
            "catalyst_classes",
            "required_source_groups",
            "risk_assumptions",
            "invalidation_conditions",
            "no_trade_conditions",
        ):
            if not candidate.get(field):
                errors.append(f"strategy_candidate_required_list_empty:{candidate_key}:{field}")

        source_weights = candidate.get("source_weights")
        if not isinstance(source_weights, dict) or not source_weights:
            errors.append(f"strategy_candidate_source_weights_missing:{candidate_key}")
        else:
            required_sources = set(str(source) for source in candidate.get("required_source_groups", []))
            if set(source_weights) != required_sources:
                errors.append(f"strategy_candidate_source_weights_mismatch:{candidate_key}")
            if not 0.995 <= sum(float(value) for value in source_weights.values()) <= 1.005:
                errors.append(f"strategy_candidate_source_weights_not_normalized:{candidate_key}")

        model_weights = candidate.get("model_weights")
        if not isinstance(model_weights, dict) or not model_weights:
            errors.append(f"strategy_candidate_model_weights_missing:{candidate_key}")
        elif not 0.995 <= sum(float(value) for value in model_weights.values()) <= 1.005:
            errors.append(f"strategy_candidate_model_weights_not_normalized:{candidate_key}")

        market_confirmation = candidate.get("market_confirmation_requirements", {})
        if not isinstance(market_confirmation, dict):
            errors.append(f"strategy_candidate_market_confirmation_invalid:{candidate_key}")
        else:
            if market_confirmation.get("non_yahoo_independent_confirmation_required") is not True:
                errors.append(f"strategy_candidate_non_yahoo_confirmation_not_required:{candidate_key}")
            if market_confirmation.get("yahoo_only_confirmation_allowed") is not False:
                errors.append(f"strategy_candidate_yahoo_only_confirmation_allowed:{candidate_key}")
            if market_confirmation.get("single_source_confirmation_allowed") is not False:
                errors.append(f"strategy_candidate_single_source_confirmation_allowed:{candidate_key}")

        preference_policy = candidate.get("preference_context_policy", {})
        if not isinstance(preference_policy, dict):
            errors.append(f"strategy_candidate_preference_policy_invalid:{candidate_key}")
        else:
            if preference_policy.get("source_key") != "preference_mcp":
                errors.append(f"strategy_candidate_preference_source_key_invalid:{candidate_key}")
            if preference_policy.get("source_role") != "supplemental_multi_source_data_plane":
                errors.append(f"strategy_candidate_preference_role_invalid:{candidate_key}")
            if int(preference_policy.get("approved_domain_pack_count", 0) or 0) < 1:
                errors.append(f"strategy_candidate_preference_domain_packs_missing:{candidate_key}")
            if not preference_policy.get("mapped_domain_packs"):
                errors.append(f"strategy_candidate_preference_domain_pack_rows_missing:{candidate_key}")
            if preference_policy.get("source_quorum_credit_allowed") is not False:
                errors.append(f"strategy_candidate_preference_source_quorum_allowed:{candidate_key}")
            if preference_policy.get("preference_only_confirmation_allowed") is not False:
                errors.append(f"strategy_candidate_preference_only_confirmation_allowed:{candidate_key}")
            for key in (
                "trade_candidate_creation_allowed",
                "risk_handoff_allowed",
                "execution_allowed",
                "paper_order_allowed",
                "broker_write_allowed",
                "live_capital_enabled",
            ):
                if preference_policy.get(key) is not False:
                    errors.append(f"strategy_candidate_preference_authority_enabled:{candidate_key}:{key}")
            if "quota" not in str(preference_policy.get("quota_freshness_degradation_rule") or "").lower():
                errors.append(f"strategy_candidate_preference_quota_rule_missing:{candidate_key}")
            no_trade_text = " ".join(str(item) for item in preference_policy.get("no_trade_conditions", []))
            if "Preference-only context is a hold condition" not in no_trade_text:
                errors.append(f"strategy_candidate_preference_only_hold_missing:{candidate_key}")
            flags = preference_policy.get("authority_flags", {})
            if not isinstance(flags, dict):
                errors.append(f"strategy_candidate_preference_authority_flags_missing:{candidate_key}")
            else:
                for flag in PREFERENCE_CONTEXT_AUTHORITY_FLAGS:
                    if flags.get(flag) is not False:
                        errors.append(f"strategy_candidate_preference_authority_flag_enabled:{candidate_key}:{flag}")

        quantum_role = candidate.get("quantum_role", {})
        if not isinstance(quantum_role, dict):
            errors.append(f"strategy_candidate_quantum_role_invalid:{candidate_key}")
        else:
            for key in (
                "provider_call_allowed",
                "hardware_submission_allowed",
                "scheduler_enabled",
                "trade_candidate_creation_allowed",
            ):
                if quantum_role.get(key) is not False:
                    errors.append(f"strategy_candidate_quantum_authority_enabled:{candidate_key}:{key}")

        strategy_research = candidate.get("strategy_research_context", {})
        if not isinstance(strategy_research, dict):
            errors.append(f"strategy_candidate_research_context_invalid:{candidate_key}")
        else:
            if strategy_research.get("candidate_registry_role") != "external_research_context_only":
                errors.append(f"strategy_candidate_research_role_invalid:{candidate_key}")
            for key in (
                "trade_candidate_creation_allowed",
                "risk_handoff_allowed",
                "execution_allowed",
                "paper_order_allowed",
                "broker_write_allowed",
                "live_capital_enabled",
            ):
                if strategy_research.get(key) is not False:
                    errors.append(f"strategy_candidate_research_authority_enabled:{candidate_key}:{key}")
            matched_count = int(strategy_research.get("matched_research_candidate_count", 0) or 0)
            if matched_count > 0 and not strategy_research.get("strategy_lead_challenges"):
                errors.append(f"strategy_candidate_research_challenges_missing:{candidate_key}")
            if "context" not in str(strategy_research.get("boundary") or "").lower():
                errors.append(f"strategy_candidate_research_boundary_weak:{candidate_key}")

        flags = candidate.get("authority_flags")
        if not isinstance(flags, dict):
            errors.append(f"strategy_candidate_authority_flags_missing:{candidate_key}")
            continue
        for flag in CANDIDATE_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"strategy_candidate_authority_flag_enabled:{candidate_key}:{flag}")

    for key in (
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if artifact.get(key) != 0:
            errors.append(f"artifact_candidate_authority_count_not_zero:{key}")
    preference_policy = artifact.get("preference_mcp_policy", {})
    if not isinstance(preference_policy, dict):
        errors.append("preference_mcp_policy_missing")
    else:
        if preference_policy.get("source_role") != "supplemental_multi_source_data_plane":
            errors.append("preference_mcp_policy_role_invalid")
        if preference_policy.get("candidate_family_count") != artifact.get("strategy_family_candidate_count"):
            errors.append("preference_mcp_policy_candidate_count_mismatch")
        if preference_policy.get("candidate_family_with_domain_pack_count") != artifact.get(
            "strategy_family_candidate_count"
        ):
            errors.append("preference_mcp_policy_family_coverage_incomplete")
        if int(preference_policy.get("approved_domain_pack_count", 0) or 0) < 1:
            errors.append("preference_mcp_policy_domain_packs_missing")
        for key in (
            "source_quorum_credit_allowed",
            "preference_only_confirmation_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if preference_policy.get(key) is not False:
                errors.append(f"preference_mcp_policy_authority_enabled:{key}")
        if "hold-only" not in str(preference_policy.get("quota_freshness_degradation_rule") or ""):
            errors.append("preference_mcp_policy_quota_freshness_rule_missing")
    research_policy = artifact.get("strategy_research_intake_policy", {})
    if not isinstance(research_policy, dict):
        errors.append("strategy_research_intake_policy_missing")
    else:
        if research_policy.get("status") != "ready_for_strategy_review":
            errors.append("strategy_research_intake_policy_status_invalid")
        if int(research_policy.get("research_candidate_count", 0) or 0) != 4:
            errors.append("strategy_research_intake_policy_candidate_count_invalid")
        if int(research_policy.get("strategy_family_with_research_context_count", 0) or 0) < 4:
            errors.append("strategy_research_intake_policy_family_coverage_low")
        if int(research_policy.get("strategy_lead_challenge_count", 0) or 0) < 4:
            errors.append("strategy_research_intake_policy_challenges_missing")
        for key in (
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if research_policy.get(key) is not False:
                errors.append(f"strategy_research_intake_policy_authority_enabled:{key}")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    return errors


def write_candidate_strategy_universe(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_candidate_strategy_universe.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
