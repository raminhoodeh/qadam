"""EF-3 deterministic direction and emerging-strategy translation.

Research relationships are converted into explicit long, short, or abstain
states using only current EF-2 trigger evidence.  This module never creates a
trade candidate, approval, or order.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import record_set_hash, safe_float, stable_id

SCHEMA_VERSION = "qadam_strategy_translation.v1"
PHASE_ID = "EF-3"

DIRECTIONS_ARTIFACT = "qadam_direction_resolutions.jsonl"
REJECTIONS_ARTIFACT = "qadam_direction_resolution_rejections.jsonl"
FORMATIONS_ARTIFACT = "qadam_emerging_strategy_formations.jsonl"
SUMMARY_ARTIFACT = "qadam_strategy_translation_summary.json"

PATTERN_SCORES_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
POWER_SCORES_ARTIFACT = "qadam_power_market_pattern_scores.jsonl"
POWER_CHECK_ARTIFACT = "qadam_power_market_edge_engine_checks.json"
POWER_REGISTRY_ARTIFACT = "qadam_power_market_strategy_registry.json"
EVENT_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATION_ARTIFACT = "qadam_current_market_dislocations.jsonl"
STRATEGY_MAP_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
INSTRUMENT_REGISTRY_ARTIFACT = "qadam_instrument_role_registry.json"
MARKET_CONTEXT_ARTIFACT = "market_context_packet.json"

ALLOWED_DIRECTIONS = {"long", "short", "abstain_direction_unresolved"}
EVENT_STRATEGIES = {
    "crude_oil_energy_security_disruption",
    "defence_repricing_geopolitical_watch",
    "semiconductor_policy_options_asymmetry",
}
REGIME_STRATEGIES = {"silver_macro_liquidity_stress", "power_scarcity_congestion"}
PREDICTION_STRATEGY = "prediction_market_geopolitical_dislocation"
MARKET_DIRECTION_MINIMUM_ABSOLUTE_MOVE_PCT = 0.25
MARKET_DIRECTION_MINIMUM_VOLUME_RATIO = 0.35


def _explicit_direction(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    if raw in {"long", "buy"} or raw.startswith("upside_"):
        return "long"
    if raw in {"short", "sell"} or raw.startswith("downside_"):
        return "short"
    return None


def _trigger_direction(value: Any) -> str:
    value = str(value or "").strip().lower()
    if value in {"long", "positive_for_strategy_expression"}:
        return "long"
    if value in {"short", "negative_for_strategy_expression"}:
        return "short"
    return "abstain_direction_unresolved"


def _strategy_ids(strategy_map: dict[str, Any]) -> set[str]:
    return {
        str(row.get("strategy_family_id"))
        for row in strategy_map.get("strategies", [])
        if isinstance(row, dict) and row.get("strategy_family_id")
    }


def _instrument_rows(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("symbol") or "").upper(): row
        for row in registry.get("instruments", [])
        if isinstance(row, dict) and row.get("symbol")
    }


def _matching_events(score: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strategy_id = str(score.get("strategy_family_id") or "")
    instrument = str(score.get("instrument") or "").upper()
    rows = [
        row
        for row in events
        if row.get("trigger_state") == "active"
        and row.get("sample_or_fixture") is False
        and row.get("strategy_family_id") == strategy_id
        and instrument in {str(value).upper() for value in row.get("affected_instruments", [])}
    ]
    return sorted(
        rows,
        key=lambda row: (str(row.get("available_at") or ""), str(row.get("trigger_id") or "")),
        reverse=True,
    )


def _matching_regime(strategy_id: str, regimes: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [row for row in regimes if row.get("strategy_family_id") == strategy_id]
    return max(rows, key=lambda row: str(row.get("available_at") or ""), default=None)


def _matching_dislocations(
    score: dict[str, Any], dislocations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    instrument = str(score.get("instrument") or "").upper()
    return [
        row
        for row in dislocations
        if row.get("measurement_state") == "active"
        and (
            str(row.get("listed_proxy") or "").upper() == instrument
            or instrument in {str(value).upper() for value in row.get("affected_instruments", [])}
        )
    ]


def _universal_market_records(
    market_context: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(market_context, dict):
        return {}
    for packet in market_context.get("recent_packets", []):
        if not isinstance(packet, dict) or packet.get("packet_role") != (
            "universal_current_market_context"
        ):
            continue
        payload = packet.get("price_volume_context")
        payload = payload if isinstance(payload, dict) else {}
        return {
            str(row.get("symbol") or "").upper(): row
            for row in payload.get("records", [])
            if isinstance(row, dict) and row.get("symbol")
        }
    return {}


def _live_market_direction(
    score: dict[str, Any], market_context: dict[str, Any] | None
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Resolve only from a current, actionable Alpaca market observation.

    This is a confirmation fallback for an active strategy event, not an
    independent catalyst. Daily closes and out-of-session quotes cannot resolve
    direction.
    """

    symbol = str(score.get("instrument") or "").upper()
    record = _universal_market_records(market_context).get(symbol, {})
    move = record.get("percent_move")
    volume_ratio = record.get("volume_ratio")
    actionable_session = bool(
        record.get("provider_backed") is True
        and (
            record.get("quote_actionable") is True
            or record.get("trade_actionable") is True
        )
        and str(record.get("session_state") or "").lower()
        in {"regular", "regular_session", "open", "live"}
    )
    if (
        not actionable_session
        or move is None
        or volume_ratio is None
        or abs(safe_float(move)) < MARKET_DIRECTION_MINIMUM_ABSOLUTE_MOVE_PCT
        or safe_float(volume_ratio) < MARKET_DIRECTION_MINIMUM_VOLUME_RATIO
    ):
        return None, None, {
            "available": False,
            "symbol": symbol,
            "reason": "No current actionable market move with sufficient volume is available.",
        }
    direction = "long" if safe_float(move) > 0 else "short"
    observed_at = (
        record.get("quote_observed_at")
        or record.get("last_trade_observed_at")
        or record.get("available_at")
    )
    evidence_id = stable_id(
        "current-market-direction",
        symbol,
        direction,
        move,
        volume_ratio,
        observed_at,
    )
    return direction, evidence_id, {
        "available": True,
        "symbol": symbol,
        "direction": direction,
        "percent_move": safe_float(move),
        "volume_ratio": safe_float(volume_ratio),
        "observed_at": observed_at,
        "provider": record.get("provider") or record.get("source"),
        "provider_backed": True,
        "quote_actionable": record.get("quote_actionable") is True,
        "trade_actionable": record.get("trade_actionable") is True,
        "minimum_absolute_move_pct": MARKET_DIRECTION_MINIMUM_ABSOLUTE_MOVE_PCT,
        "minimum_volume_ratio": MARKET_DIRECTION_MINIMUM_VOLUME_RATIO,
    }


def resolve_direction(
    score: dict[str, Any],
    events: list[dict[str, Any]],
    regimes: list[dict[str, Any]],
    dislocations: list[dict[str, Any]],
    *,
    generated_at: str,
    market_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_id = str(score.get("score_id") or "")
    strategy_id = str(score.get("strategy_family_id") or "")
    raw_direction = str(score.get("direction_hypothesis") or "")
    evidence_ids: list[str] = []
    actionable = "abstain_direction_unresolved"
    reason = "No strategy-specific current trigger resolved a direction."
    resolver = "strategy_agnostic_abstain"
    invalidation: list[str] = []
    market_confirmation: dict[str, Any] = {"available": False}

    if strategy_id in EVENT_STRATEGIES:
        resolver = "event_polarity_v1"
        rows = _matching_events(score, events)
        evidence_ids = [str(row.get("trigger_id")) for row in rows if row.get("trigger_id")]
        directions = {_trigger_direction(row.get("direction_clue")) for row in rows}
        directions.discard("abstain_direction_unresolved")
        invalidation = sorted(
            {str(value) for row in rows for value in row.get("invalidation_clues", []) if value}
        )
        if len(directions) == 1:
            actionable = next(iter(directions))
            reason = (
                f"Current {strategy_id.replace('_', ' ')} evidence has one consistent "
                f"directional interpretation: {actionable}."
            )
        elif rows:
            market_direction, market_evidence_id, market_confirmation = (
                _live_market_direction(score, market_context)
            )
            explicit_direction = _explicit_direction(raw_direction)
            if (
                not directions
                and market_direction
                and (explicit_direction is None or explicit_direction == market_direction)
            ):
                actionable = market_direction
                resolver = "event_plus_live_market_confirmation_v1"
                if market_evidence_id:
                    evidence_ids.append(market_evidence_id)
                reason = (
                    "The active event is directionally ambiguous, but the current "
                    f"provider-backed {score.get('instrument')} move and volume resolve "
                    f"a bounded experimental {actionable} direction."
                )
            elif explicit_direction and market_direction and explicit_direction != market_direction:
                reason = (
                    "The strategy direction conflicts with current provider-backed market "
                    "confirmation, so Qadam abstains."
                )
            else:
                reason = (
                    "Current event evidence is ambiguous and no actionable live-market "
                    "confirmation resolves it, so Qadam abstains."
                )
        else:
            reason = "No fresh instrument-relevant event trigger is available for this strategy."
    elif strategy_id in REGIME_STRATEGIES:
        resolver = "numeric_regime_v1"
        row = _matching_regime(strategy_id, regimes)
        if row:
            evidence_ids = [str(row.get("regime_id"))]
            actionable = _trigger_direction(row.get("direction_clue"))
            if row.get("regime_state") != "active":
                actionable = "abstain_direction_unresolved"
                reason = f"The numeric regime is {row.get('regime_state')}; it is observed but not active."
            else:
                reason = (
                    f"The active numeric regime resolves the current direction to {actionable}."
                )
        else:
            reason = "No current numeric regime observation is available."
    elif strategy_id == PREDICTION_STRATEGY:
        resolver = "compatible_contract_dislocation_v1"
        rows = _matching_dislocations(score, dislocations)
        evidence_ids = [str(row.get("dislocation_id")) for row in rows if row.get("dislocation_id")]
        directions = {_trigger_direction(row.get("direction_clue")) for row in rows}
        directions.discard("abstain_direction_unresolved")
        if len(directions) == 1:
            actionable = next(iter(directions))
            reason = f"A compatible measured contract dislocation resolves to {actionable}."
        else:
            reason = "No single compatible prediction-market dislocation resolves an actionable listed-market direction."
    elif not strategy_id:
        explicit = _explicit_direction(raw_direction)
        reason = (
            "The relationship is strategy-agnostic and needs a distinct economic mechanism before direction can be resolved."
            if explicit is None
            else "An explicit research direction exists, but no distinct strategy-specific current trigger supports it."
        )

    resolution_id = stable_id(
        "qadam-direction-resolution-v1",
        score_id,
        raw_direction,
        actionable,
        evidence_ids,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_direction_resolution",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "direction_resolution_id": resolution_id,
        "score_id": score_id,
        "strategy_family_id": strategy_id or None,
        "strategy_agnostic": score.get("strategy_agnostic") is True,
        "instrument": score.get("instrument"),
        "horizon": score.get("horizon_hypothesis"),
        "raw_research_direction": raw_direction,
        "raw_explicit_direction": _explicit_direction(raw_direction),
        "actionable_direction": actionable,
        "resolution_state": "resolved"
        if actionable in {"long", "short"}
        else "abstain_direction_unresolved",
        "resolver": resolver,
        "explanation": reason,
        "evidence_ids": evidence_ids,
        "market_confirmation": market_confirmation,
        "invalidation_conditions": invalidation or ["current trigger expires or reverses"],
        "negative_control": score.get("negative_control") is True,
        "paper_order_created": False,
        "trade_candidate_created": False,
        "authority": authority_flags(),
    }


def _formation_rejection(
    score: dict[str, Any], reasons: list[str], *, generated_at: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_translation_rejection",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "rejection_id": stable_id(
            "qadam-strategy-translation-rejection-v1", score.get("score_id"), reasons
        ),
        "score_id": score.get("score_id"),
        "instrument": score.get("instrument"),
        "rejection_scope": "direction_resolution"
        if score.get("negative_control") is True
        else "emerging_strategy_formation",
        "reasons": unique_errors(reasons),
        "permitted_next_action": "remain_research_observation",
        "trade_candidate_created": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def build_strategy_translation_from_inputs(
    pattern_scores: list[dict[str, Any]],
    events: list[dict[str, Any]],
    regimes: list[dict[str, Any]],
    dislocations: list[dict[str, Any]],
    strategy_map: dict[str, Any],
    instrument_registry: dict[str, Any],
    power_registry: dict[str, Any],
    *,
    generated_at: str,
    market_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configured = _strategy_ids(strategy_map)
    instruments = _instrument_rows(instrument_registry)
    resolutions: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    formations: list[dict[str, Any]] = []

    for score in pattern_scores:
        if score.get("negative_control") is True:
            rejections.append(
                _formation_rejection(
                    score,
                    ["negative_control_cannot_resolve_direction_or_form_strategy"],
                    generated_at=generated_at,
                )
            )
            continue
        resolution = resolve_direction(
            score,
            events,
            regimes,
            dislocations,
            generated_at=generated_at,
            market_context=market_context,
        )
        resolutions.append(resolution)
        if score.get("strategy_agnostic") is not True:
            continue
        symbol = str(score.get("instrument") or "").upper()
        route = instruments.get(symbol, {})
        reasons: list[str] = []
        if resolution["actionable_direction"] not in {"long", "short"}:
            reasons.append("actionable_direction_missing")
        if not score.get("economic_mechanism"):
            reasons.append("distinct_economic_mechanism_missing")
        if not score.get("source_recipe"):
            reasons.append("distinct_source_recipe_missing")
        if route.get("route_state") != "guarded_alpaca_paper_confirmed":
            reasons.append("paperable_instrument_or_approved_proxy_missing")
        if not score.get("invalidation_condition"):
            reasons.append("invalidation_condition_missing")
        if score.get("strategy_family_id") in configured:
            reasons.append("duplicates_configured_strategy_family")
        if reasons:
            rejections.append(_formation_rejection(score, reasons, generated_at=generated_at))
            continue
        formation_id = stable_id(
            "qadam-emerging-strategy-formation-v1",
            score.get("score_id"),
            resolution.get("direction_resolution_id"),
            symbol,
        )
        formations.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_emerging_strategy_formation",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "formation_id": formation_id,
                "formation_state": "emerging_strategy_review_only",
                "score_id": score.get("score_id"),
                "direction_resolution_id": resolution.get("direction_resolution_id"),
                "economic_mechanism": score.get("economic_mechanism"),
                "source_recipe": score.get("source_recipe"),
                "instrument": symbol,
                "actionable_direction": resolution.get("actionable_direction"),
                "invalidation_condition": score.get("invalidation_condition"),
                "paper_order_created": False,
                "trade_candidate_created": False,
                "authority": authority_flags(),
            }
        )

    power_rows = power_registry.get("strategies", [])
    power_state = (
        power_rows[0].get("admission_state")
        if power_rows and isinstance(power_rows[0], dict)
        else "unavailable"
    )
    counts = Counter(row["actionable_direction"] for row in resolutions)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_translation_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "pattern_score_count": len(pattern_scores),
        "non_negative_control_score_count": sum(
            row.get("negative_control") is not True for row in pattern_scores
        ),
        "direction_resolution_count": len(resolutions),
        "direction_counts": dict(sorted(counts.items())),
        "emerging_strategy_formation_count": len(formations),
        "rejection_count": len(rejections),
        "live_market_direction_fallback": {
            "enabled": True,
            "purpose": "resolve an ambiguous active event for a bounded paper experiment",
            "regular_session_actionable_quote_or_trade_required": True,
            "minimum_absolute_move_pct": MARKET_DIRECTION_MINIMUM_ABSOLUTE_MOVE_PCT,
            "minimum_volume_ratio": MARKET_DIRECTION_MINIMUM_VOLUME_RATIO,
            "cannot_create_a_catalyst_alone": True,
            "cannot_override_conflicting_explicit_direction": True,
        },
        "power_emerging_strategy_state": power_state,
        "power_automatically_promoted": False,
        "input_hashes": {
            "pattern_scores": record_set_hash(pattern_scores),
            "event_triggers": record_set_hash(events),
            "regime_observations": record_set_hash(regimes),
            "market_dislocations": record_set_hash(dislocations),
        },
        "candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    return {
        "resolutions": resolutions,
        "rejections": rejections,
        "formations": formations,
        "summary": summary,
    }


def validate_strategy_translation(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    resolutions = state.get("resolutions", [])
    ids = [str(row.get("direction_resolution_id") or "") for row in resolutions]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        errors.append("direction_resolution_id_missing_or_duplicate")
    for row in resolutions:
        if row.get("actionable_direction") not in ALLOWED_DIRECTIONS:
            errors.append("direction_resolution_value_invalid")
        if row.get("negative_control") is not False:
            errors.append("negative_control_received_direction_resolution")
        if row.get("actionable_direction") in {"long", "short"} and not row.get("evidence_ids"):
            errors.append(
                f"actionable_direction_evidence_missing:{row.get('direction_resolution_id')}"
            )
        if not row.get("explanation"):
            errors.append("direction_resolution_explanation_missing")
        errors.extend(validate_authority(row.get("authority", {}), prefix="direction_resolution"))
    for row in state.get("formations", []):
        if row.get("actionable_direction") not in {"long", "short"}:
            errors.append("emerging_strategy_direction_not_actionable")
        if row.get("trade_candidate_created") is not False:
            errors.append("emerging_strategy_created_trade_candidate")
        errors.extend(validate_authority(row.get("authority", {}), prefix="emerging_strategy"))
    for row in state.get("rejections", []):
        errors.extend(validate_authority(row.get("authority", {}), prefix="translation_rejection"))
    summary = state.get("summary", {})
    if summary.get("direction_resolution_count") != len(resolutions):
        errors.append("direction_resolution_count_mismatch")
    for field in (
        "candidate_created_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if summary.get(field) != 0:
            errors.append(f"strategy_translation_forbidden_count_nonzero:{field}")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="translation_summary"))
    return unique_errors(errors)


def build_strategy_translation_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    scores = list(read_jsonl(runtime / PATTERN_SCORES_ARTIFACT))
    power_checks = read_json(runtime / POWER_CHECK_ARTIFACT)
    if power_checks.get("safe_to_consume") is True:
        scores.extend(read_jsonl(runtime / POWER_SCORES_ARTIFACT))
    return build_strategy_translation_from_inputs(
        scores,
        read_jsonl(runtime / EVENT_ARTIFACT),
        read_jsonl(runtime / REGIME_ARTIFACT),
        read_jsonl(runtime / DISLOCATION_ARTIFACT),
        read_json(runtime / STRATEGY_MAP_ARTIFACT),
        read_json(runtime / INSTRUMENT_REGISTRY_ARTIFACT),
        read_json(runtime / POWER_REGISTRY_ARTIFACT),
        generated_at=now_iso(),
        market_context=read_json(runtime / MARKET_CONTEXT_ARTIFACT),
    )


def build_and_write_strategy_translation(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_strategy_translation_state(settings)
    errors = validate_strategy_translation(state)
    store.write_jsonl(DIRECTIONS_ARTIFACT, state["resolutions"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    store.write_jsonl(FORMATIONS_ARTIFACT, state["formations"])
    checks = {
        **state["summary"],
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "validation_error_count": len(errors),
        "validation_errors": errors,
    }
    store.write_json(SUMMARY_ARTIFACT, checks)
    return state, checks, errors
