"""EF-4 immutable same-generation decision evidence packets.

Each Akber-reviewable hypothesis receives one packet assembled from a single
frozen read of the current runtime artifacts.  The packet is research context;
it cannot approve risk, create a candidate, or place an order.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import (
    CONTEXT_FIELDS,
    assemble_current_akber_context,
    build_akber_input,
)
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
from orchestrator.qadam_wave_b_common import record_set_hash, stable_id

SCHEMA_VERSION = "qadam_decision_evidence_packet.v1"
PHASE_ID = "EF-4"

PACKETS_ARTIFACT = "qadam_decision_evidence_packets.jsonl"
SUMMARY_ARTIFACT = "qadam_decision_evidence_packet_summary.json"
REJECTIONS_ARTIFACT = "qadam_decision_evidence_packet_rejections.jsonl"
INTEGRITY_ARTIFACT = "qadam_generation_integrity_checks.json"

HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
DIRECTIONS_ARTIFACT = "qadam_direction_resolutions.jsonl"
EVENT_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATION_ARTIFACT = "qadam_current_market_dislocations.jsonl"
MARKET_CONTEXT_ARTIFACT = "market_context_packet.json"
SIGNAL_INTEGRITY_ARTIFACT = "signal_integrity_reviews.jsonl"
ALPACA_MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
TRADINGVIEW_STATUS_ARTIFACT = "qadam_tradingview_supplemental_status.json"
TRADINGVIEW_CONTEXT_ARTIFACT = "tradingview_mcp_technical_context.json"
BOOKMAP_CONTEXT_ARTIFACT = "bookmap_local_bridge_context.json"
NONLINEAR_COMPARISON_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"
POWER_CONTEXT_ARTIFACT = "qadam_power_market_context.json"
POWER_CHECK_ARTIFACT = "qadam_power_market_edge_engine_checks.json"

TYPED_STATES = {"available", "inactive", "missing", "stale", "unavailable", "adverse"}
CURRENT_RESEARCH_HISTORY_LIMIT = 1024


def _direction_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("direction_resolution_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("direction_resolution_id")
    }


def _trigger_by_id(*groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            for key in ("trigger_id", "regime_id", "dislocation_id"):
                if row.get(key):
                    result[str(row[key])] = row
    return result


def _typed_state(record: dict[str, Any]) -> str:
    state = str(record.get("state") or "").lower()
    if state in {"veto", "unsafe", "invalid", "failed", "untradeable", "blocked"}:
        return "adverse"
    if state == "stale" or record.get("freshness_state") == "stale":
        return "stale"
    if any(token in state for token in ("inactive", "closed", "outside_regular_session")):
        return "inactive"
    if record.get("available") is True:
        return "available"
    if any(token in state for token in ("unavailable", "unsupported", "dependency_missing")):
        return "unavailable"
    return "missing"


def _current_trigger_context(
    resolution: dict[str, Any], trigger_index: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    evidence_ids = [str(value) for value in resolution.get("evidence_ids", []) if value]
    rows = [trigger_index[value] for value in evidence_ids if value in trigger_index]
    actionable = resolution.get("actionable_direction") in {"long", "short"}
    active = bool(
        rows
        and all(
            row.get("trigger_state") == "active"
            or row.get("regime_state") == "active"
            or row.get("measurement_state") == "active"
            for row in rows
        )
    )
    source_keys = sorted(
        {str(source) for row in rows for source in row.get("source_keys", []) if source}
    )
    observed_at = max(
        (
            str(row.get("available_at") or row.get("observed_at") or row.get("generated_at") or "")
            for row in rows
        ),
        default=None,
    )
    available = active and actionable
    return {
        "field": "fresh_catalyst",
        "available": available,
        "state": "confirmed" if available else "inactive" if rows else "missing",
        "observed_at": observed_at,
        "source_refs": evidence_ids,
        "value": {
            "direction": resolution.get("actionable_direction"),
            "trigger_records": rows,
        },
        "details": {
            "fresh_trigger_sources": source_keys,
            "direction_resolution_id": resolution.get("direction_resolution_id"),
            "trigger_count": len(rows),
            "provider_availability_is_not_a_trigger": True,
        },
        "provider": "EF-2 strategy-specific trigger factory",
        "origin_class": "canonical_runtime_artifact",
        "reason": (
            "A fresh strategy-specific trigger supports the resolved direction."
            if available
            else "The strategy-specific trigger is inactive, absent, or directionally unresolved."
        ),
        "fallback_used": False,
        "fixture_backed": False,
        "trade_authority": False,
    }


def _market_session_state(context: dict[str, Any]) -> dict[str, Any]:
    liquidity = context.get("liquidity_and_spread")
    liquidity = liquidity if isinstance(liquidity, dict) else {}
    values = liquidity.get("value")
    rows = values if isinstance(values, list) else []
    states = {
        str(row.get("session_state") or row.get("market_state") or "").lower()
        for row in rows
        if isinstance(row, dict)
    }
    if any(state in {"open", "live", "regular", "regular_session"} for state in states):
        return {
            "state": "open_actionable",
            "quote_actionable": True,
            "observed_states": sorted(states),
        }
    if rows and any(
        any(token in state for token in ("closed", "outside", "after_hours", "pre_market"))
        for state in states
    ):
        liquidity.update(
            {
                "available": False,
                "state": "inactive_market_session",
                "reason": "The quote is retained as context, but its spread is not actionable outside the regular session.",
            }
        )
        context["liquidity_and_spread"] = liquidity
        return {
            "state": "closed_inactive",
            "quote_actionable": False,
            "observed_states": sorted(states),
        }
    if liquidity.get("available") is True:
        return {
            "state": "session_state_unreported",
            "quote_actionable": False,
            "observed_states": sorted(states),
        }
    return {"state": "unavailable", "quote_actionable": False, "observed_states": sorted(states)}


def _packet_rejection(
    hypothesis_id: str | None, reasons: list[str], *, generated_at: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_evidence_packet_rejection",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "rejection_id": stable_id("qadam-decision-packet-rejection-v1", hypothesis_id, reasons),
        "hypothesis_id": hypothesis_id,
        "reasons": unique_errors(reasons),
        "permitted_next_action": "repair_lineage_or_wait_for_same_generation_evidence",
        "trade_candidate_created": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def build_decision_evidence_packets_from_inputs(
    hypotheses: list[dict[str, Any]],
    direction_resolutions: list[dict[str, Any]],
    event_triggers: list[dict[str, Any]],
    regime_observations: list[dict[str, Any]],
    market_dislocations: list[dict[str, Any]],
    current_artifacts: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    input_hashes = {
        "hypotheses": record_set_hash(hypotheses),
        "direction_resolutions": record_set_hash(direction_resolutions),
        "event_triggers": record_set_hash(event_triggers),
        "regime_observations": record_set_hash(regime_observations),
        "market_dislocations": record_set_hash(market_dislocations),
        "market_context": record_set_hash([current_artifacts.get("market_context", {})]),
        "alpaca_mirror": record_set_hash([current_artifacts.get("alpaca_mirror", {})]),
        "nonlinear_comparisons": record_set_hash(
            current_artifacts.get("nonlinear_comparisons", [])
        ),
    }
    # A decision generation identifies its evidence, not the wall-clock time of
    # the compiler pass. Re-running unchanged inputs must not orphan Akber,
    # shadow, risk, or Router records between scheduler ticks.
    generation_id = stable_id("qadam-decision-generation-v1", input_hashes)
    resolutions = _direction_by_id(direction_resolutions)
    triggers = _trigger_by_id(event_triggers, regime_observations, market_dislocations)
    packets: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    hypothesis_ids: set[str] = set()

    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        if not hypothesis_id or hypothesis_id in hypothesis_ids:
            rejections.append(
                _packet_rejection(
                    hypothesis_id or None,
                    ["hypothesis_id_missing_or_duplicate"],
                    generated_at=generated_at,
                )
            )
            continue
        hypothesis_ids.add(hypothesis_id)
        direction = hypothesis.get("direction_horizon")
        direction = direction if isinstance(direction, dict) else {}
        resolution_id = direction.get("direction_resolution_id")
        resolution = resolutions.get(str(resolution_id or ""))
        evidence_class = str(hypothesis.get("evidence_class") or "")
        if evidence_class == "experimental_unvalidated" and not resolution:
            rejections.append(
                _packet_rejection(
                    hypothesis_id,
                    ["experimental_direction_resolution_missing"],
                    generated_at=generated_at,
                )
            )
            continue
        if resolution and resolution.get("actionable_direction") != direction.get("direction"):
            rejections.append(
                _packet_rejection(
                    hypothesis_id,
                    ["direction_resolution_hypothesis_mismatch"],
                    generated_at=generated_at,
                )
            )
            continue

        context = assemble_current_akber_context(
            hypothesis, current_artifacts, generated_at=generated_at
        )
        if resolution:
            context["fresh_catalyst"] = _current_trigger_context(resolution, triggers)
        context["_assembled_from_canonical_artifacts"] = True
        context["_source_artifacts"] = unique_errors(
            [
                *context.get("_source_artifacts", []),
                DIRECTIONS_ARTIFACT,
                EVENT_ARTIFACT,
                REGIME_ARTIFACT,
                DISLOCATION_ARTIFACT,
            ]
        )
        session = _market_session_state(context)
        context["_market_session"] = session
        context["_decision_evidence_packet_id"] = "pending"
        context["_decision_generation_id"] = generation_id
        provisional = build_akber_input(
            hypothesis,
            context,
            generated_at=generated_at,
            strict_provenance=hypothesis.get("akber_review_allowed") is True,
        )
        evidence = provisional["evidence"]
        typed_states = {field: _typed_state(evidence[field]) for field in CONTEXT_FIELDS}
        mapping = hypothesis.get("instrument_proxy_mapping")
        mapping = mapping if isinstance(mapping, dict) else {}
        risk = evidence.get("risk_reward_context", {}).get("details", {})
        liquidity = evidence.get("liquidity_and_spread", {}).get("details", {})
        catalyst_details = evidence.get("fresh_catalyst", {}).get("details", {})
        source_keys = catalyst_details.get("fresh_trigger_sources", [])
        packet_id = stable_id(
            "qadam-decision-evidence-packet-v1",
            generation_id,
            hypothesis_id,
            resolution_id,
            typed_states,
        )
        context["_decision_evidence_packet_id"] = packet_id
        packets.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_decision_evidence_packet",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "decision_timestamp": generated_at,
                "decision_generation_id": generation_id,
                "decision_evidence_packet_id": packet_id,
                "hypothesis_id": hypothesis_id,
                "research_goal_id": hypothesis.get("research_goal_lineage", {}).get(
                    "research_goal_id"
                ),
                "strategy_family_id": hypothesis.get("strategy_mapping", {}).get(
                    "strategy_family_id"
                ),
                "evidence_profile": provisional.get("evidence_profile"),
                "evidence_class": evidence_class,
                "pattern_relationship_id": hypothesis.get("pattern_lineage", {}).get(
                    "pattern_relationship_id"
                ),
                "score_id": hypothesis.get("pattern_lineage", {}).get("score_id"),
                "direction_resolution_id": resolution_id,
                "direction": direction.get("direction"),
                "horizon": direction.get("horizon"),
                "observed_instrument": mapping.get("observed_instrument"),
                "execution_proxy": mapping.get("execution_proxy"),
                "historical_support_evidence": evidence.get("source_price_context"),
                "current_trigger_evidence": evidence.get("fresh_catalyst"),
                "current_price_and_volatility": {
                    "price": evidence.get("invalidation_clarity", {})
                    .get("details", {})
                    .get("current_price"),
                    "volatility": evidence.get("volatility_context"),
                },
                "confirmation_alternatives": {
                    field: evidence.get(field)
                    for field in (
                        "technical_confirmation",
                        "volume_or_flow_confirmation",
                        "pricing_gap_evidence",
                        "nonlinear_quantum_review",
                    )
                },
                "liquidity_spread_and_adv": {
                    "spread_bps": liquidity.get("spread_bps"),
                    "evidence": evidence.get("liquidity_and_spread"),
                },
                "expected_costs_and_expectancy": {
                    "expected_net_return": risk.get("expected_net_return"),
                    "spread_bps": liquidity.get("spread_bps"),
                    "expectancy_is_provisional": evidence_class == "experimental_unvalidated",
                },
                "invalidation_and_reward_to_risk": {
                    "invalidation": evidence.get("invalidation_clarity"),
                    "reward_to_risk": risk.get("reward_to_risk"),
                },
                "source_concentration": {
                    "distinct_current_trigger_source_count": len(set(source_keys)),
                    "current_trigger_sources": source_keys,
                    "single_source_trigger": len(set(source_keys)) == 1,
                },
                "proxy_and_basis_risk": {
                    "proxy_basis": mapping.get("proxy_basis"),
                    "proxy_review_required": mapping.get("proxy_review_required"),
                    "paperability": evidence.get("paperability_proxy"),
                },
                "market_session": session,
                "expiry_and_freshness": hypothesis.get("freshness", {}),
                "negative_control": False,
                "evidence_states": typed_states,
                "akber_context": context,
                "input_hashes": input_hashes,
                "mixed_generation_join": False,
                "trade_candidate_created": False,
                "risk_approval_created": False,
                "execution_approval_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )

    packet_counts = Counter(row.get("hypothesis_id") for row in packets if row.get("hypothesis_id"))
    mixed_generation_join_count = sum(
        row.get("decision_generation_id") != generation_id for row in packets
    )
    duplicate_packet_hypothesis_count = sum(value != 1 for value in packet_counts.values())
    integrity_errors: list[str] = []
    if mixed_generation_join_count:
        integrity_errors.append("mixed_generation_join_detected")
    if duplicate_packet_hypothesis_count:
        integrity_errors.append("hypothesis_packet_cardinality_invalid")
    if len(packets) + len(rejections) < len(hypotheses):
        integrity_errors.append("hypothesis_packet_accounting_incomplete")
    integrity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_generation_integrity_checks",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "decision_generation_id": generation_id,
        "status": "passed" if not integrity_errors else "blocked",
        "hypothesis_count": len(hypotheses),
        "packet_count": len(packets),
        "rejection_count": len(rejections),
        "mixed_generation_join_count": mixed_generation_join_count,
        "duplicate_packet_hypothesis_count": duplicate_packet_hypothesis_count,
        "input_hashes": input_hashes,
        "validation_errors": integrity_errors,
        "candidate_created_count": 0,
        "paper_order_created_count": 0,
        "authority": authority_flags(),
    }
    state_counts = Counter(
        value for row in packets for value in row.get("evidence_states", {}).values()
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_evidence_packet_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete" if not integrity_errors else "blocked",
        "decision_generation_id": generation_id,
        "hypothesis_count": len(hypotheses),
        "packet_count": len(packets),
        "rejection_count": len(rejections),
        "evidence_state_counts": dict(sorted(state_counts.items())),
        "closed_market_inactive_count": sum(
            row.get("market_session", {}).get("state") == "closed_inactive" for row in packets
        ),
        "mixed_generation_join_count": mixed_generation_join_count,
        "candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    return {
        "packets": packets,
        "rejections": rejections,
        "integrity": integrity,
        "summary": summary,
    }


def validate_decision_evidence_packets(state: dict[str, Any]) -> list[str]:
    errors: list[str] = list(state.get("integrity", {}).get("validation_errors", []))
    packet_ids: set[str] = set()
    hypothesis_ids: set[str] = set()
    generation_ids: set[str] = set()
    for row in state.get("packets", []):
        packet_id = str(row.get("decision_evidence_packet_id") or "")
        hypothesis_id = str(row.get("hypothesis_id") or "")
        if not packet_id or packet_id in packet_ids:
            errors.append("decision_packet_id_missing_or_duplicate")
        if not hypothesis_id or hypothesis_id in hypothesis_ids:
            errors.append("decision_packet_hypothesis_cardinality_invalid")
        packet_ids.add(packet_id)
        hypothesis_ids.add(hypothesis_id)
        generation_ids.add(str(row.get("decision_generation_id") or ""))
        if set(row.get("evidence_states", {})) != set(CONTEXT_FIELDS):
            errors.append(f"decision_packet_evidence_contract_incomplete:{packet_id}")
        if any(value not in TYPED_STATES for value in row.get("evidence_states", {}).values()):
            errors.append(f"decision_packet_typed_state_invalid:{packet_id}")
        if row.get("negative_control") is not False:
            errors.append("negative_control_became_decision_packet")
        if row.get("mixed_generation_join") is not False:
            errors.append("decision_packet_mixed_generation_join")
        for field in (
            "trade_candidate_created",
            "risk_approval_created",
            "execution_approval_created",
            "paper_order_created",
        ):
            if row.get(field) is not False:
                errors.append(f"decision_packet_created_forbidden_output:{field}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="decision_packet"))
    if len(generation_ids) > 1:
        errors.append("decision_packets_span_multiple_generations")
    for row in state.get("rejections", []):
        errors.extend(
            validate_authority(row.get("authority", {}), prefix="decision_packet_rejection")
        )
    summary = state.get("summary", {})
    if summary.get("packet_count") != len(state.get("packets", [])):
        errors.append("decision_packet_count_mismatch")
    for field in (
        "candidate_created_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if summary.get(field) != 0:
            errors.append(f"decision_packet_forbidden_count_nonzero:{field}")
    errors.extend(
        validate_authority(summary.get("authority", {}), prefix="decision_packet_summary")
    )
    return unique_errors(errors)


def _current_artifacts(
    runtime,
    *,
    include_research_history: bool = True,
) -> dict[str, Any]:
    market_context = deepcopy(read_json(runtime / MARKET_CONTEXT_ARTIFACT))
    power_checks = read_json(runtime / POWER_CHECK_ARTIFACT)
    if power_checks.get("safe_to_consume") is True:
        power_context = read_json(runtime / POWER_CONTEXT_ARTIFACT)
        market_context.setdefault("recent_packets", []).extend(
            row for row in power_context.get("recent_packets", []) if isinstance(row, dict)
        )
    return {
        "market_context": market_context,
        "signal_integrity_reviews": (
            read_jsonl(
                runtime / SIGNAL_INTEGRITY_ARTIFACT,
                limit=CURRENT_RESEARCH_HISTORY_LIMIT,
            )
            if include_research_history
            else []
        ),
        "alpaca_mirror": read_json(runtime / ALPACA_MIRROR_ARTIFACT),
        "tradingview_status": read_json(runtime / TRADINGVIEW_STATUS_ARTIFACT),
        "tradingview_context": read_json(runtime / TRADINGVIEW_CONTEXT_ARTIFACT),
        "bookmap_context": read_json(runtime / BOOKMAP_CONTEXT_ARTIFACT),
        "nonlinear_comparisons": (
            read_jsonl(
                runtime / NONLINEAR_COMPARISON_ARTIFACT,
                limit=CURRENT_RESEARCH_HISTORY_LIMIT,
            )
            if include_research_history
            else []
        ),
    }


def current_decision_artifacts(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return the canonical read-only inputs used for decision packets.

    Supplemental research lanes use this public adapter so they receive the
    same provider, price, nonlinear, and paper-mirror context as the canonical
    Strategy Foundry lane without taking ownership of those artifacts.
    """

    return _current_artifacts(runtime_dir(settings))


def build_decision_evidence_packet_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    return build_decision_evidence_packets_from_inputs(
        read_jsonl(runtime / HYPOTHESES_ARTIFACT),
        read_jsonl(runtime / DIRECTIONS_ARTIFACT),
        read_jsonl(runtime / EVENT_ARTIFACT),
        read_jsonl(runtime / REGIME_ARTIFACT),
        read_jsonl(runtime / DISLOCATION_ARTIFACT),
        _current_artifacts(runtime),
        generated_at=now_iso(),
    )


def build_and_write_decision_evidence_packets(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_decision_evidence_packet_state(settings)
    errors = validate_decision_evidence_packets(state)
    store.write_jsonl(PACKETS_ARTIFACT, state["packets"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    store.write_json(INTEGRITY_ARTIFACT, state["integrity"])
    checks = {
        **state["summary"],
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "validation_error_count": len(errors),
        "validation_errors": errors,
    }
    store.write_json(SUMMARY_ARTIFACT, checks)
    return state, checks, errors
