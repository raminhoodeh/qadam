"""EF-2 strategy-specific current trigger factory.

Provider-backed events, numeric macro/market regimes, and compatible prediction
contracts are translated into typed research triggers.  Translation is
read-only: a trigger cannot create a strategy, candidate, approval, or order.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_discovery_micro_conversion import INSTRUMENT_ROLES
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, stable_id

SCHEMA_VERSION = "qadam_trigger_factory.v1"
PHASE_ID = "EF-2"

EVENT_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATION_ARTIFACT = "qadam_current_market_dislocations.jsonl"
SUMMARY_ARTIFACT = "qadam_trigger_factory_summary.json"
REJECTIONS_ARTIFACT = "qadam_trigger_factory_rejections.jsonl"

SOURCE_CONTRACT_ARTIFACT = "qadam_strategy_source_contract.json"
INSTRUMENT_REGISTRY_ARTIFACT = "qadam_instrument_role_registry.json"
MARKET_CONTEXT_ARTIFACT = "market_context_packet.json"
RESEARCH_GOALS_ARTIFACT = "research_goals.jsonl"
POWER_CONTEXT_ARTIFACT = "qadam_power_market_context.json"

STRATEGY_RULES: dict[str, dict[str, Any]] = {
    "crude_oil_energy_security_disruption": {
        "channels": {"energy_transport", "macro_watchlist"},
        "symbols": {"CL=F", "USO", "BNO", "XLE"},
        "keywords": {
            "oil",
            "crude",
            "energy",
            "shipping",
            "tanker",
            "chokepoint",
            "sanction",
            "hormuz",
            "red sea",
            "supply disruption",
            "middle east",
        },
        "positive": {
            "disruption",
            "sanction",
            "attack",
            "shortage",
            "closure",
            "blockade",
            "piracy",
            "escalation",
        },
        "negative": {"ceasefire", "reopen", "oversupply", "bearish", "production increase"},
    },
    "defence_repricing_geopolitical_watch": {
        "channels": {"defence_geopolitics"},
        "symbols": {"ITA", "XAR", "LMT", "PPA", "RTX"},
        "keywords": {
            "defence",
            "defense",
            "military",
            "arms",
            "missile",
            "security",
            "war",
            "conflict",
            "nato",
            "procurement",
            "defense deal",
        },
        "positive": {
            "deal",
            "contract",
            "spending",
            "escalation",
            "procurement",
            "order",
            "award",
            "attack",
        },
        "negative": {"peace", "ceasefire", "budget cut", "cancellation", "de-escalation"},
    },
    "semiconductor_policy_options_asymmetry": {
        "channels": {"semiconductors"},
        "symbols": {"SMH", "SOXX", "NVDA", "QQQ", "TSM"},
        "keywords": {
            "semiconductor",
            "chip",
            "foundry",
            "fabrication",
            "export control",
            "ai accelerator",
            "hynix",
            "nvidia",
            "tsmc",
            "technology policy",
        },
        "positive": {
            "investment",
            "expansion",
            "approval",
            "subsidy",
            "demand",
            "partnership",
            "plant",
            "plants",
            "fab",
            "capacity",
        },
        "negative": {"restriction", "ban", "sanction", "selling", "shutdown", "export control"},
    },
}

CAUSAL_MECHANISMS: dict[str, tuple[dict[str, Any], ...]] = {
    "crude_oil_energy_security_disruption": (
        {
            "mechanism": "physical_supply_or_transport_constraint",
            "terms": {"blockade", "closure", "chokepoint", "piracy", "attack", "disruption"},
            "direction": "positive_for_strategy_expression",
            "confidence": 0.76,
            "invalidation": "The transport constraint clears or observed oil pricing rejects the disruption thesis.",
        },
        {
            "mechanism": "policy_or_production_supply_expansion",
            "terms": {"reopen", "production increase", "oversupply", "ceasefire"},
            "direction": "negative_for_strategy_expression",
            "confidence": 0.70,
            "invalidation": "The announced supply increase fails to materialise or disruption resumes.",
        },
    ),
    "defence_repricing_geopolitical_watch": (
        {
            "mechanism": "procurement_or_budget_demand_increase",
            "terms": {"procurement", "contract", "spending", "award", "defense deal", "defence deal"},
            "direction": "positive_for_strategy_expression",
            "confidence": 0.78,
            "invalidation": "The procurement, contract, or spending decision is cancelled or materially reduced.",
        },
        {
            "mechanism": "defence_demand_reduction",
            "terms": {"budget cut", "cancellation", "peace agreement", "de-escalation"},
            "direction": "negative_for_strategy_expression",
            "confidence": 0.70,
            "invalidation": "Security demand or procurement rises despite the de-escalation signal.",
        },
    ),
    "semiconductor_policy_options_asymmetry": (
        {
            "mechanism": "fabrication_capacity_or_investment_expansion",
            "terms": {"plant", "plants", "fab", "capacity", "investment", "subsidy", "expansion"},
            "direction": "positive_for_strategy_expression",
            "confidence": 0.66,
            "invalidation": "The capacity plan is delayed, cancelled, unfunded, or already fully reflected in prices.",
        },
        {
            "mechanism": "technology_supply_or_market_access_constraint",
            "terms": {"export control", "restriction", "ban", "sanction", "shutdown"},
            "direction": "negative_for_strategy_expression",
            "confidence": 0.74,
            "invalidation": "The restriction is withdrawn, diluted, or offset by alternative supply or demand.",
        },
    ),
}


def _latest_by_id(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(field) or "")
        if not key:
            continue
        if key not in latest or str(row.get("updated_at") or row.get("generated_at") or "") > str(
            latest[key].get("updated_at") or latest[key].get("generated_at") or ""
        ):
            latest[key] = row
    return latest


def _source_contract_by_key(source_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in source_contract.get("sources", []):
        if not isinstance(row, dict):
            continue
        for key in (row.get("source_key"), row.get("canonical_source_key")):
            if key:
                rows[str(key).lower()] = row
    return rows


def _event_text(packet: dict[str, Any], goal: dict[str, Any]) -> str:
    text = str(goal.get("hypothesis") or packet.get("hypothesis") or "").strip()
    marker = "corroborate it:"
    if marker in text.lower():
        index = text.lower().index(marker) + len(marker)
        text = text[index:].strip()
    return " ".join(text.split())


def _source_keys(packet: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(row.get("source_key") or "").lower()
            for row in packet.get("source_taxonomy", [])
            if isinstance(row, dict)
            and row.get("observed_in_goal") is True
            and row.get("source_key")
        }
    )


def _classify_event(packet: dict[str, Any], text: str) -> tuple[str | None, list[str], list[str]]:
    lowered = text.lower()
    channel = str(packet.get("market_channel") or "").lower()
    watched = {str(value).upper() for value in packet.get("watched_instruments", [])}
    matches: list[tuple[int, str, list[str], list[str]]] = []
    for strategy_id, rule in STRATEGY_RULES.items():
        keywords = sorted(keyword for keyword in rule["keywords"] if keyword in lowered)
        symbols = sorted(watched.intersection(rule["symbols"]))
        channel_match = channel in rule["channels"]
        if keywords and symbols and channel_match:
            matches.append((len(keywords) * 3 + len(symbols), strategy_id, keywords, symbols))
    if not matches:
        return None, [], []
    _score, strategy_id, keywords, symbols = max(matches)
    return strategy_id, keywords, symbols


def _causal_classification(strategy_id: str, text: str) -> dict[str, Any]:
    rule = STRATEGY_RULES[strategy_id]
    lowered = text.lower()
    positive = sorted(token for token in rule["positive"] if token in lowered)
    negative = sorted(token for token in rule["negative"] if token in lowered)
    mechanism_matches = []
    for definition in CAUSAL_MECHANISMS.get(strategy_id, ()):
        terms = sorted(term for term in definition["terms"] if term in lowered)
        if terms:
            mechanism_matches.append((definition, terms))
    directions = {item[0]["direction"] for item in mechanism_matches}
    if len(directions) == 1:
        definition, terms = max(
            mechanism_matches,
            key=lambda item: (len(item[1]), safe_float(item[0].get("confidence"))),
        )
        direction = str(definition["direction"])
        mechanism = str(definition["mechanism"])
        confidence = safe_float(definition.get("confidence"))
        invalidation = str(definition.get("invalidation") or "The causal event reverses.")
        matched = terms
    elif positive and not negative:
        direction = "positive_for_strategy_expression"
        mechanism = "strategy_supporting_event_language"
        confidence = 0.58
        invalidation = "The event is corrected, reversed, or rejected by current market evidence."
        matched = positive
    elif negative and not positive:
        direction = "negative_for_strategy_expression"
        mechanism = "strategy_opposing_event_language"
        confidence = 0.58
        invalidation = "The event is corrected, reversed, or rejected by current market evidence."
        matched = negative
    else:
        direction = "ambiguous"
        mechanism = "causal_mechanism_unresolved"
        confidence = 0.0
        invalidation = "No trade interpretation is permitted until a single causal mechanism is resolved."
        matched = sorted(set(positive + negative))
    return {
        "event": " ".join(text.split()),
        "mechanism": mechanism,
        "direction_clue": direction,
        "confidence": confidence,
        "matched_terms": matched,
        "conflicting_mechanism_count": len(directions) if len(directions) > 1 else 0,
        "invalidation": invalidation,
        "classifier": "deterministic_strategy_causal_classifier_v2",
        "not_a_probability": True,
        "not_execution_approval": True,
    }


def _polarity(strategy_id: str, text: str) -> tuple[str, list[str]]:
    classification = _causal_classification(strategy_id, text)
    return str(classification["direction_clue"]), list(classification["matched_terms"])


def build_event_triggers(
    market_context: dict[str, Any],
    research_goals: list[dict[str, Any]],
    source_contract: dict[str, Any],
    *,
    generated_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    goals = _latest_by_id(research_goals, "goal_id")
    source_rows = _source_contract_by_key(source_contract)
    now = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    triggers: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for packet in market_context.get("recent_packets", []):
        if (
            not isinstance(packet, dict)
            or packet.get("packet_role") == "universal_current_market_context"
        ):
            continue
        goal_id = str(packet.get("research_goal_id") or "")
        goal = goals.get(goal_id, {})
        text = _event_text(packet, goal)
        sources = _source_keys(packet)
        strategy_id, matched_terms, affected = _classify_event(packet, text)
        reasons: list[str] = []
        if (
            str(packet.get("research_goal_origin") or goal.get("origin") or "").lower()
            != "live_source"
        ):
            reasons.append("not_a_live_source_event")
        if not strategy_id:
            reasons.append("no_explicit_strategy_causal_relevance")
        eligible_sources = [
            key
            for key in sources
            if source_rows.get(key, {}).get("availability_state") == "live_fresh"
            and "current_trigger" in source_rows.get(key, {}).get("allowed_roles", [])
            and safe_float(source_rows.get(key, {}).get("trust_score")) >= 0.55
        ]
        if not eligible_sources:
            reasons.append("no_fresh_trigger_eligible_source")
        publication_at = goal.get("created_at") or goal.get("updated_at")
        available_at = packet.get("generated_at")
        publication = parse_timestamp(publication_at)
        available = parse_timestamp(available_at)
        if publication is None or available is None:
            reasons.append("publication_or_availability_time_missing")
        elif publication > now or available > now:
            reasons.append("future_timestamp_not_admissible")
        elif now - publication > timedelta(hours=72):
            reasons.append("event_expired")
        if reasons:
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_trigger_factory_rejection",
                    "phase_id": PHASE_ID,
                    "generated_at": generated_at,
                    "rejection_id": stable_id("trigger-rejection", goal_id, reasons, text),
                    "record_type": "event",
                    "research_goal_id": goal_id or None,
                    "summary": text[:240],
                    "reasons": unique_errors(reasons),
                    "authority": authority_flags(),
                }
            )
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        dedupe_key = (str(strategy_id), normalized)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        causal_classification = _causal_classification(str(strategy_id), text)
        polarity = str(causal_classification["direction_clue"])
        polarity_terms = list(causal_classification["matched_terms"])
        expires_at = (publication + timedelta(hours=72)).isoformat() if publication else None
        trigger_id = stable_id(
            "current-event-trigger",
            strategy_id,
            normalized,
            publication_at,
            eligible_sources,
        )
        triggers.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_current_event_trigger",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "trigger_id": trigger_id,
                "trigger_type": "event_catalyst",
                "strategy_family_id": strategy_id,
                "research_goal_id": goal_id,
                "source_event_refs": goal.get("source_event_refs", []),
                "source_keys": eligible_sources,
                "source_trust_scores": {
                    key: source_rows[key].get("trust_score") for key in eligible_sources
                },
                "publication_at": publication_at,
                "available_at": available_at,
                "timestamp_semantics": "provider_event_time_then_qadam_packet_availability",
                "event_summary": text,
                "affected_instruments": affected,
                "matched_causal_terms": matched_terms,
                "catalyst_strength": "high" if len(matched_terms) >= 2 else "medium",
                "direction_clue": polarity,
                "direction_clue_terms": polarity_terms,
                "causal_classification": causal_classification,
                "instrument_expressions": {
                    symbol: INSTRUMENT_ROLES.get(
                        symbol,
                        {"role": "listed_instrument", "basis_risk": "unclassified"},
                    )
                    for symbol in affected
                },
                "invalidation_clues": [
                    causal_classification["invalidation"],
                    "affected instruments move against the directional interpretation",
                ],
                "expires_at": expires_at,
                "trigger_state": "active",
                "provider_availability_is_not_trigger": True,
                "sample_or_fixture": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return triggers, rejections


def _universal_market_records(market_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    for packet in market_context.get("recent_packets", []):
        if (
            isinstance(packet, dict)
            and packet.get("packet_role") == "universal_current_market_context"
        ):
            payload = packet.get("price_volume_context")
            payload = payload if isinstance(payload, dict) else {}
            return {
                str(row.get("symbol")).upper(): row
                for row in payload.get("records", [])
                if isinstance(row, dict)
                and row.get("symbol")
                and row.get("provider_backed") is True
            }
    return {}


def _latest_raw_payload(source_key: str) -> tuple[dict[str, Any], str | None]:
    root = ROOT / "data" / "raw_payloads" / source_key
    paths = sorted(root.glob("**/*.json")) if root.exists() else []
    if not paths:
        return {}, None
    path = paths[-1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, None
    return (payload if isinstance(payload, dict) else {}), str(path.relative_to(ROOT))


def load_macro_observations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fred, fred_path = _latest_raw_payload("fred")
    for series in fred.get("series", []):
        if not isinstance(series, dict):
            continue
        observations = [
            row
            for row in series.get("observations", [])
            if isinstance(row, dict) and str(row.get("value") or "") not in {"", "."}
        ]
        if not observations:
            continue
        latest = observations[0]
        previous = observations[1] if len(observations) > 1 else None
        rows.append(
            {
                "source_key": "fred",
                "series_id": series.get("series_id"),
                "label": series.get("title"),
                "observed_at": f"{latest.get('date')}T23:59:59+00:00",
                "available_at": f"{latest.get('date')}T23:59:59+00:00",
                "value": safe_float(latest.get("value")),
                "previous_value": safe_float(previous.get("value")) if previous else None,
                "raw_reference": fred_path,
                "provider_backed": True,
            }
        )
    ecb, ecb_path = _latest_raw_payload("ecb")
    try:
        dataset = ecb["dataSets"][0]
        series = next(iter(dataset["series"].values()))
        values = ecb["structure"]["dimensions"]["observation"][0]["values"]
        observation_items = sorted(
            ((int(index), value) for index, value in series["observations"].items()),
            key=lambda item: item[0],
        )
        latest_index, latest_value = observation_items[-1]
        previous_value = observation_items[-2][1] if len(observation_items) > 1 else None
        date = values[latest_index]["id"]
        rows.append(
            {
                "source_key": "ecb",
                "series_id": "EXR.D.USD.EUR.SP00.A",
                "label": "US dollar per euro reference rate",
                "observed_at": f"{date}T23:59:59+02:00",
                "available_at": ecb.get("header", {}).get("prepared"),
                "value": safe_float(latest_value[0]),
                "previous_value": safe_float(previous_value[0]) if previous_value else None,
                "raw_reference": ecb_path,
                "provider_backed": True,
            }
        )
    except (KeyError, IndexError, StopIteration, TypeError, ValueError):
        pass
    return rows


def build_regime_observations(
    market_context: dict[str, Any],
    macro_observations: list[dict[str, Any]],
    power_context: dict[str, Any],
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    market = _universal_market_records(market_context)
    required = {symbol: market.get(symbol) for symbol in ("SIL", "SLV", "GLD", "SPY")}
    available_market = {symbol: row for symbol, row in required.items() if row}
    macro_by_series = {str(row.get("series_id")): row for row in macro_observations}
    silver_moves = [
        safe_float(required[symbol].get("percent_move"))
        for symbol in ("SIL", "SLV")
        if required[symbol]
    ]
    benchmark_moves = [
        safe_float(required[symbol].get("percent_move"))
        for symbol in ("GLD", "SPY")
        if required[symbol]
    ]
    volume_ratios = [
        safe_float(required[symbol].get("volume_ratio"))
        for symbol in ("SIL", "SLV")
        if required[symbol]
    ]
    relative_move = (
        sum(silver_moves) / len(silver_moves) - sum(benchmark_moves) / len(benchmark_moves)
        if silver_moves and benchmark_moves
        else None
    )
    dgs10 = macro_by_series.get("DGS10", {})
    vix = macro_by_series.get("VIXCLS", {})
    ecb = macro_by_series.get("EXR.D.USD.EUR.SP00.A", {})
    yield_change_bps = (
        (safe_float(dgs10.get("value")) - safe_float(dgs10.get("previous_value"))) * 100
        if dgs10.get("previous_value") is not None
        else None
    )
    vix_change_pct = (
        (safe_float(vix.get("value")) / safe_float(vix.get("previous_value")) - 1) * 100
        if safe_float(vix.get("previous_value")) != 0
        else None
    )
    eurusd_change_pct = (
        (safe_float(ecb.get("value")) / safe_float(ecb.get("previous_value")) - 1) * 100
        if safe_float(ecb.get("previous_value")) != 0
        else None
    )
    components: list[float] = []
    if relative_move is not None:
        components.append(max(-2.0, min(2.0, relative_move / 1.5)))
    if yield_change_bps is not None:
        components.append(max(-2.0, min(2.0, -yield_change_bps / 10.0)))
    if vix_change_pct is not None:
        components.append(max(-2.0, min(2.0, vix_change_pct / 5.0)))
    if eurusd_change_pct is not None:
        components.append(max(-2.0, min(2.0, -eurusd_change_pct / 0.5)))
    average_volume_ratio = sum(volume_ratios) / len(volume_ratios) if volume_ratios else None
    if average_volume_ratio is not None:
        components.append(max(-2.0, min(2.0, average_volume_ratio - 1.0)))
    regime_score = sum(components) / len(components) if components else None
    numeric_complete = (
        len(available_market) == 4 and len(macro_by_series) >= 3 and regime_score is not None
    )
    active = bool(
        numeric_complete
        and regime_score >= 0.60
        and relative_move is not None
        and relative_move > 0
    )
    rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_current_regime_observation",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "regime_id": stable_id("silver-regime", generated_at, relative_move, regime_score),
            "strategy_family_id": "silver_macro_liquidity_stress",
            "regime_type": "macro_liquidity_stress",
            "transformation_version": "silver-regime.v1",
            "numeric_measurements": {
                "silver_relative_move_pct": relative_move,
                "silver_average_volume_ratio": average_volume_ratio,
                "ten_year_yield_change_bps": yield_change_bps,
                "vix_change_pct": vix_change_pct,
                "eurusd_change_pct": eurusd_change_pct,
                "regime_score": regime_score,
            },
            "thresholds": {"active_long_score": 0.60, "active_short_score": -0.60},
            "regime_state": "active"
            if active
            else "inactive"
            if numeric_complete
            else "missing_numeric_inputs",
            "direction_clue": "long"
            if active
            else "short"
            if numeric_complete and regime_score <= -0.60
            else "abstain_direction_unresolved",
            "observed_at": max(
                [str(row.get("observed_at") or "") for row in available_market.values()]
                + [str(row.get("observed_at") or "") for row in macro_observations]
            ),
            "available_at": generated_at,
            "source_refs": [
                *(f"{MARKET_CONTEXT_ARTIFACT}#{symbol}" for symbol in sorted(available_market)),
                *(
                    str(row.get("raw_reference"))
                    for row in macro_observations
                    if row.get("raw_reference")
                ),
            ],
            "provider_availability_is_not_trigger": True,
            "sample_or_fixture": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "authority": authority_flags(),
        }
    ]
    for packet in power_context.get("recent_packets", []):
        if not isinstance(packet, dict):
            continue
        gap = packet.get("pricing_gap_evidence")
        gap = gap if isinstance(gap, dict) else {}
        value = gap.get("value")
        value = value if isinstance(value, dict) else {}
        measurement = value.get("feature_value")
        percentile = value.get("feature_percentile")
        if measurement is None or percentile is None:
            continue
        active_power = gap.get("available") is True and str(gap.get("state")) in {
            "available",
            "measured",
            "active",
        }
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_current_regime_observation",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "regime_id": stable_id(
                    "power-regime", packet.get("packet_id"), measurement, percentile
                ),
                "strategy_family_id": "power_scarcity_congestion",
                "regime_type": "power_scarcity_or_congestion",
                "transformation_version": "power-mechanism-feature.v1",
                "numeric_measurements": {
                    "feature_value": safe_float(measurement),
                    "feature_percentile": safe_float(percentile),
                    "method": value.get("method"),
                },
                "thresholds": {"active_percentile": 0.90},
                "regime_state": "active" if active_power else "inactive",
                "direction_clue": "long" if active_power else "abstain_direction_unresolved",
                "observed_at": gap.get("observed_at") or packet.get("generated_at"),
                "available_at": packet.get("generated_at"),
                "source_refs": [f"{POWER_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"],
                "provider_availability_is_not_trigger": True,
                "sample_or_fixture": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return rows


def _normalize_contract_title(value: Any) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", str(value or "").lower())
    stop = {"will", "the", "a", "an", "by", "before", "after", "in", "on", "of", "to"}
    return " ".join(token for token in text.split() if token not in stop)


def build_market_dislocations(
    contracts: list[dict[str, Any]], *, generated_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        title = _normalize_contract_title(contract.get("title") or contract.get("question"))
        if title:
            grouped.setdefault(title, []).append(contract)
    rows: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for title, candidates in grouped.items():
        by_venue = {str(row.get("venue") or "").lower(): row for row in candidates}
        kalshi = by_venue.get("kalshi")
        polymarket = by_venue.get("polymarket")
        if not kalshi or not polymarket:
            continue
        if any(
            row.get("probability") is None
            or row.get("observed_at") is None
            or row.get("contract_id") is None
            or row.get("settlement_rule_hash") is None
            for row in (kalshi, polymarket)
        ):
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_trigger_factory_rejection",
                    "phase_id": PHASE_ID,
                    "generated_at": generated_at,
                    "rejection_id": stable_id(
                        "dislocation-rejection", title, "incomplete_contract_lineage"
                    ),
                    "record_type": "market_dislocation",
                    "summary": title,
                    "reasons": ["incomplete_contract_lineage"],
                    "authority": authority_flags(),
                }
            )
            continue
        compatible = kalshi["settlement_rule_hash"] == polymarket["settlement_rule_hash"]
        if not compatible:
            continue
        gap = safe_float(kalshi["probability"]) - safe_float(polymarket["probability"])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_current_market_dislocation",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "dislocation_id": stable_id(
                    "prediction-dislocation",
                    title,
                    gap,
                    kalshi["contract_id"],
                    polymarket["contract_id"],
                ),
                "strategy_family_id": "prediction_market_geopolitical_dislocation",
                "normalized_event_identity": title,
                "contract_lineage": [
                    {
                        key: row.get(key)
                        for key in (
                            "venue",
                            "contract_id",
                            "probability",
                            "liquidity",
                            "observed_at",
                            "settlement_rule_hash",
                        )
                    }
                    for row in (kalshi, polymarket)
                ],
                "settlement_rules_compatible": True,
                "probability_gap": gap,
                "absolute_probability_gap": abs(gap),
                "measurement_state": "active" if abs(gap) >= 0.08 else "inactive",
                "direction_clue": "event_specific_proxy_resolution_required",
                "listed_proxy": None,
                "observed_at": max(str(kalshi["observed_at"]), str(polymarket["observed_at"])),
                "available_at": generated_at,
                "sample_or_fixture": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return rows, rejections


def build_trigger_factory_from_inputs(
    market_context: dict[str, Any],
    research_goals: list[dict[str, Any]],
    source_contract: dict[str, Any],
    power_context: dict[str, Any],
    macro_observations: list[dict[str, Any]],
    prediction_contracts: list[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    events, event_rejections = build_event_triggers(
        market_context, research_goals, source_contract, generated_at=generated_at
    )
    regimes = build_regime_observations(
        market_context, macro_observations, power_context, generated_at=generated_at
    )
    dislocations, dislocation_rejections = build_market_dislocations(
        prediction_contracts, generated_at=generated_at
    )
    rejections = [*event_rejections, *dislocation_rejections]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_trigger_factory_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "event_trigger_count": len(events),
        "active_event_trigger_count": sum(row.get("trigger_state") == "active" for row in events),
        "regime_observation_count": len(regimes),
        "active_regime_count": sum(row.get("regime_state") == "active" for row in regimes),
        "market_dislocation_count": len(dislocations),
        "active_market_dislocation_count": sum(
            row.get("measurement_state") == "active" for row in dislocations
        ),
        "rejection_count": len(rejections),
        "rejection_reason_counts": dict(
            sorted(
                Counter(reason for row in rejections for reason in row.get("reasons", [])).items()
            )
        ),
        "candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    return {
        "events": events,
        "regimes": regimes,
        "dislocations": dislocations,
        "rejections": rejections,
        "summary": summary,
    }


def validate_trigger_factory(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for row in state.get("events", []):
        trigger_id = str(row.get("trigger_id") or "")
        if not trigger_id or trigger_id in ids:
            errors.append("event_trigger_id_missing_or_duplicate")
        ids.add(trigger_id)
        if row.get("sample_or_fixture") is not False:
            errors.append(f"fixture_event_became_trigger:{trigger_id}")
        if (
            not row.get("publication_at")
            or not row.get("available_at")
            or not row.get("source_keys")
        ):
            errors.append(f"event_trigger_lineage_incomplete:{trigger_id}")
        if row.get("trigger_state") == "active" and not row.get("matched_causal_terms"):
            errors.append(f"generic_event_activated_trigger:{trigger_id}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="event_trigger"))
    for row in state.get("regimes", []):
        regime_id = str(row.get("regime_id") or "")
        measurements = row.get("numeric_measurements")
        if (
            not regime_id
            or not isinstance(measurements, dict)
            or not any(
                isinstance(value, (int, float)) and math.isfinite(value)
                for value in measurements.values()
            )
        ):
            errors.append(f"regime_numeric_measurement_missing:{regime_id}")
        if row.get("sample_or_fixture") is not False:
            errors.append(f"fixture_regime_became_trigger:{regime_id}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="regime_trigger"))
    for row in state.get("dislocations", []):
        dislocation_id = str(row.get("dislocation_id") or "")
        if row.get("settlement_rules_compatible") is not True or not isinstance(
            row.get("probability_gap"), (int, float)
        ):
            errors.append(f"dislocation_measurement_invalid:{dislocation_id}")
        if row.get("listed_proxy") in {"KALSHI:EVENTS", "POLYMARKET:EVENTS"}:
            errors.append(f"prediction_contract_became_execution_symbol:{dislocation_id}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="dislocation_trigger"))
    for row in state.get("rejections", []):
        errors.extend(validate_authority(row.get("authority", {}), prefix="trigger_rejection"))
    summary = state.get("summary", {})
    if summary.get("candidate_created_count") != 0 or summary.get("paper_order_created_count") != 0:
        errors.append("trigger_factory_created_forbidden_output")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="trigger_summary"))
    return unique_errors(errors)


def build_trigger_factory_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    return build_trigger_factory_from_inputs(
        read_json(runtime / MARKET_CONTEXT_ARTIFACT),
        read_jsonl(runtime / RESEARCH_GOALS_ARTIFACT),
        read_json(runtime / SOURCE_CONTRACT_ARTIFACT),
        read_json(runtime / POWER_CONTEXT_ARTIFACT),
        load_macro_observations(),
        [],
        generated_at=now_iso(),
    )


def build_and_write_trigger_factory(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_trigger_factory_state(settings)
    errors = validate_trigger_factory(state)
    store.write_jsonl(EVENT_ARTIFACT, state["events"])
    store.write_jsonl(REGIME_ARTIFACT, state["regimes"])
    store.write_jsonl(DISLOCATION_ARTIFACT, state["dislocations"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    checks = {
        **state["summary"],
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "validation_error_count": len(errors),
        "validation_errors": errors,
    }
    store.write_json(SUMMARY_ARTIFACT, checks)
    return state, checks, errors
