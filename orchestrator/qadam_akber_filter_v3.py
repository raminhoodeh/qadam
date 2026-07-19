"""OR-12 Akber Filter V3 evidence assembly and practical tradeability review.

Akber evaluates whether a research hypothesis is practical in current market
conditions. A pass remains a research decision and cannot approve risk,
execution, PaperOps handoff, or an order.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
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
from orchestrator.qadam_wave_b_common import (
    parse_timestamp,
    record_set_hash,
    safe_float,
    safe_int,
    stable_id,
)

SCHEMA_VERSION = "qadam_akber_filter_v3.v2"
PHASE_ID = "OR-12"
POLICY_VERSION = "akber-v3-policy.2-frozen-pre-holdout"

INPUTS_ARTIFACT = "qadam_akber_filter_v3_inputs.jsonl"
RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
REPLAY_ARTIFACT = "qadam_akber_filter_v3_replay.jsonl"
ABLATION_ARTIFACT = "qadam_akber_filter_v3_ablation.jsonl"
THRESHOLD_PROPOSALS_ARTIFACT = "qadam_akber_filter_v3_threshold_proposals.jsonl"
DASHBOARD_ARTIFACT = "qadam_akber_filter_v3_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_akber_filter_v3_checks.json"

HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
FOUNDRY_SUMMARY_ARTIFACT = "qadam_strategy_foundry_v3.json"
BACKTEST_MANIFEST_ARTIFACT = "qadam_backtest_run_manifest.json"
STRATEGY_MAP_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
NONLINEAR_COMPARISON_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"
MARKET_CONTEXT_ARTIFACT = "market_context_packet.json"
SIGNAL_INTEGRITY_ARTIFACT = "signal_integrity_reviews.jsonl"
ALPACA_MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
TRADINGVIEW_STATUS_ARTIFACT = "qadam_tradingview_supplemental_status.json"
TRADINGVIEW_CONTEXT_ARTIFACT = "tradingview_mcp_technical_context.json"
BOOKMAP_CONTEXT_ARTIFACT = "bookmap_local_bridge_context.json"

CURRENT_CONTEXT_MAX_AGE_SECONDS = 172_800
HISTORICAL_POLICY = {
    "minimum_independent_rows": 80,
    "minimum_fold_count": 3,
    "minimum_fold_trade_count": 20,
    "minimum_positive_fold_ratio": 0.50,
    "minimum_mean_fold_net_return": 0.0,
    "maximum_fold_drawdown": -0.35,
}

CONTEXT_FIELDS = (
    "source_price_context",
    "fresh_catalyst",
    "technical_confirmation",
    "volume_or_flow_confirmation",
    "volatility_context",
    "pricing_gap_evidence",
    "risk_reward_context",
    "invalidation_clarity",
    "liquidity_and_spread",
    "paperability_proxy",
    "nonlinear_quantum_review",
)

STAGE_FIELDS = {
    "context": ("source_price_context",),
    "catalyst": ("fresh_catalyst",),
    "confirmation": (
        "technical_confirmation",
        "volume_or_flow_confirmation",
        "volatility_context",
        "pricing_gap_evidence",
        "nonlinear_quantum_review",
    ),
    "risk": ("risk_reward_context", "invalidation_clarity"),
    "execution": ("liquidity_and_spread", "paperability_proxy"),
    "postmortem_learning": (),
}

DECISIONS = {"pass", "hold_missing_context", "veto"}
AVAILABLE_STATES = {"available", "confirmed", "pass", "ready", "measured", "reviewed"}
VETO_STATES = {"veto", "unsafe", "invalid", "failed", "untradeable", "blocked"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp_age_seconds(value: Any, *, now: str) -> float | None:
    observed = parse_timestamp(value)
    current = parse_timestamp(now)
    if observed is None or current is None:
        return None
    return max(0.0, (current - observed).total_seconds())


def _sample_or_fixture_state(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return any(token in text for token in ("sample", "fixture", "synthetic", "demo"))


def _context_evidence(
    field: str,
    *,
    available: bool,
    state: str,
    observed_at: str | None,
    source_refs: list[str],
    value: Any = None,
    details: dict[str, Any] | None = None,
    provider: str | None = None,
    origin_class: str = "canonical_runtime_artifact",
    reason: str,
    fallback_used: bool = False,
) -> dict[str, Any]:
    fixture_backed = _sample_or_fixture_state(state) or _sample_or_fixture_state(origin_class)
    return {
        "field": field,
        "available": bool(available and not fixture_backed),
        "state": "sample_or_fixture_not_admissible" if fixture_backed else state,
        "observed_at": observed_at,
        "source_refs": source_refs,
        "value": value,
        "details": details or {},
        "provider": provider,
        "origin_class": origin_class,
        "reason": reason,
        "fallback_used": fallback_used,
        "fixture_backed": fixture_backed,
        "trade_authority": False,
    }


def _matching_symbols(hypothesis: dict[str, Any]) -> set[str]:
    mapping = hypothesis.get("instrument_proxy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    symbols = {
        str(symbol).upper()
        for symbol in (
            mapping.get("observed_instrument"),
            mapping.get("execution_proxy"),
        )
        if symbol
    }
    aliases = {symbol.split("=")[0] for symbol in symbols if "=" in symbol and symbol.split("=")[0]}
    return symbols | aliases


def _matching_market_packet(
    hypothesis: dict[str, Any], market_context: dict[str, Any]
) -> dict[str, Any]:
    symbols = _matching_symbols(hypothesis)
    packets = market_context.get("recent_packets")
    rows = packets if isinstance(packets, list) else []
    matching: list[dict[str, Any]] = []
    for packet in rows:
        if not isinstance(packet, dict):
            continue
        watched = {
            str(symbol).upper() for symbol in packet.get("watched_instruments", []) if symbol
        }
        nested_symbols: set[str] = set()
        for section in ("price_volume_context", "technical_context", "orderflow_context"):
            payload = packet.get(section)
            payload = payload if isinstance(payload, dict) else {}
            nested_symbols.update(
                str(record.get("symbol")).upper()
                for record in payload.get("records", [])
                if isinstance(record, dict) and record.get("symbol")
            )
        if symbols.intersection(watched | nested_symbols):
            matching.append(packet)
    return max(
        matching,
        key=lambda row: (
            parse_timestamp(row.get("generated_at")) or datetime.min.replace(tzinfo=timezone.utc)
        ),
        default={},
    )


def _matching_records(
    packet: dict[str, Any], section: str, symbols: set[str]
) -> list[dict[str, Any]]:
    payload = packet.get(section)
    payload = payload if isinstance(payload, dict) else {}
    return [
        record
        for record in payload.get("records", [])
        if isinstance(record, dict) and str(record.get("symbol") or "").upper() in symbols
    ]


def _is_fresh_runtime_record(observed_at: Any, *, generated_at: str) -> bool:
    age = _timestamp_age_seconds(observed_at, now=generated_at)
    return age is not None and age <= CURRENT_CONTEXT_MAX_AGE_SECONDS


def _normalize_evidence(
    field: str,
    value: Any,
    *,
    generated_at: str | None = None,
    strict_provenance: bool = False,
) -> dict[str, Any]:
    if isinstance(value, dict):
        state = str(value.get("state") or value.get("status") or "unknown").lower()
        available = value.get("available")
        if available is None:
            available = state in AVAILABLE_STATES
        fixture_backed = value.get("fixture_backed") is True or _sample_or_fixture_state(state)
        observed_at = value.get("observed_at")
        age_seconds = (
            _timestamp_age_seconds(observed_at, now=generated_at)
            if generated_at and observed_at
            else None
        )
        stale = age_seconds is not None and age_seconds > CURRENT_CONTEXT_MAX_AGE_SECONDS
        source_refs = value.get("source_refs", [])
        provenance_missing = strict_provenance and (
            not isinstance(source_refs, list) or not source_refs or not value.get("origin_class")
        )
        admissible = bool(
            available is True and not fixture_backed and not stale and not provenance_missing
        )
        return {
            "field": field,
            "available": admissible,
            "state": (
                "sample_or_fixture_not_admissible"
                if fixture_backed
                else "stale"
                if stale
                else "missing_provenance"
                if provenance_missing
                else state
            ),
            "observed_at": observed_at,
            "source_refs": source_refs,
            "value": value.get("value"),
            "details": value.get("details", {}),
            "provider": value.get("provider"),
            "origin_class": value.get("origin_class"),
            "reason": value.get("reason"),
            "fallback_used": value.get("fallback_used") is True,
            "fixture_backed": fixture_backed,
            "age_seconds": age_seconds,
            "freshness_state": (
                "stale" if stale else "fresh" if age_seconds is not None else "not_applicable"
            ),
            "provenance_complete": not provenance_missing,
        }
    if value is True:
        return {
            "field": field,
            "available": True,
            "state": "available",
            "observed_at": None,
            "source_refs": [],
            "value": True,
            "details": {},
            "provider": None,
            "origin_class": "direct_test_input",
            "reason": "direct boolean evidence",
            "fallback_used": False,
            "fixture_backed": False,
            "age_seconds": None,
            "freshness_state": "not_applicable",
            "provenance_complete": not strict_provenance,
        }
    return {
        "field": field,
        "available": False,
        "state": "missing" if value in (None, False, "") else str(value).lower(),
        "observed_at": None,
        "source_refs": [],
        "value": value,
        "details": {},
        "provider": None,
        "origin_class": None,
        "reason": "evidence missing",
        "fallback_used": False,
        "fixture_backed": False,
        "age_seconds": None,
        "freshness_state": "unknown",
        "provenance_complete": not strict_provenance,
    }


def build_akber_input(
    hypothesis: dict[str, Any],
    context: dict[str, Any],
    *,
    generated_at: str,
    strict_provenance: bool = False,
) -> dict[str, Any]:
    """Create a typed, complete Akber input envelope for one V3 hypothesis."""

    hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
    if not hypothesis_id:
        raise ValueError("hypothesis_id_missing")
    if strict_provenance and hypothesis.get("akber_review_allowed") is not True:
        raise ValueError("hypothesis_not_eligible_for_akber_review")
    evidence = {
        field: _normalize_evidence(
            field,
            context.get(field),
            generated_at=generated_at,
            strict_provenance=strict_provenance,
        )
        for field in CONTEXT_FIELDS
    }
    missing = [field for field, record in evidence.items() if record["available"] is not True]
    edge_lineage = hypothesis.get("edge_lineage", {})
    applied_learning_version_ids = edge_lineage.get("applied_learning_version_ids", [])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v3_input",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "akber_input_id": stable_id(
            "akber-input-v3", hypothesis_id, evidence, applied_learning_version_ids
        ),
        "hypothesis_id": hypothesis_id,
        "edge_id": hypothesis.get("edge_lineage", {}).get("edge_id"),
        "research_goal_id": hypothesis.get("research_goal_lineage", {}).get("research_goal_id"),
        "candidate_identity_id": hypothesis.get("candidate_identity_material", {}).get(
            "candidate_identity_id"
        ),
        "applied_learning_version_ids": applied_learning_version_ids,
        "stage1_learning_input_version": edge_lineage.get("stage1_learning_input_version"),
        "policy_version": POLICY_VERSION,
        "hypothesis_state": hypothesis.get("hypothesis_state"),
        "strict_provenance_required": strict_provenance,
        "context_assembled_from_canonical_artifacts": context.get(
            "_assembled_from_canonical_artifacts"
        )
        is True,
        "context_source_artifacts": context.get("_source_artifacts", []),
        "evidence": evidence,
        "critical_context_field_count": len(CONTEXT_FIELDS),
        "missing_critical_context": missing,
        "missing_critical_context_count": len(missing),
        "context_complete": not missing,
        "fixture_or_sample_evidence_count": sum(
            record.get("fixture_backed") is True for record in evidence.values()
        ),
        "stale_evidence_count": sum(
            record.get("freshness_state") == "stale" for record in evidence.values()
        ),
        "incomplete_provenance_count": sum(
            record.get("provenance_complete") is not True for record in evidence.values()
        ),
        "thresholds_frozen_before_evaluation": True,
        "router_eligibility_recommendation_only": True,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def _hard_vetoes(akber_input: dict[str, Any]) -> list[str]:
    evidence = akber_input.get("evidence", {})
    vetoes: list[str] = []
    for field, record in evidence.items():
        if str(record.get("state") or "").lower() in VETO_STATES:
            vetoes.append(f"explicit_adverse_evidence:{field}")

    risk = evidence.get("risk_reward_context", {})
    risk_details = risk.get("details") if isinstance(risk.get("details"), dict) else {}
    expected_net = risk_details.get("expected_net_return")
    reward_to_risk = risk_details.get("reward_to_risk")
    if expected_net is not None and safe_float(expected_net) <= 0:
        vetoes.append("expected_return_non_positive_after_costs")
    if reward_to_risk is not None and safe_float(reward_to_risk) < 1.25:
        vetoes.append("reward_to_risk_below_frozen_floor")

    invalidation = evidence.get("invalidation_clarity", {})
    invalidation_details = (
        invalidation.get("details") if isinstance(invalidation.get("details"), dict) else {}
    )
    if invalidation.get("available") is True and invalidation_details.get("defined") is False:
        vetoes.append("invalidation_not_defined")

    liquidity = evidence.get("liquidity_and_spread", {})
    liquidity_details = (
        liquidity.get("details") if isinstance(liquidity.get("details"), dict) else {}
    )
    spread_bps = liquidity_details.get("spread_bps")
    if spread_bps is not None and safe_float(spread_bps) > 100:
        vetoes.append("spread_exceeds_frozen_maximum")

    paperability = evidence.get("paperability_proxy", {})
    paperability_details = (
        paperability.get("details") if isinstance(paperability.get("details"), dict) else {}
    )
    if paperability.get("available") is True and paperability_details.get("paperable") is False:
        vetoes.append("paper_proxy_not_paperable")
    return unique_errors(vetoes)


def evaluate_akber_input(akber_input: dict[str, Any]) -> dict[str, Any]:
    evidence = akber_input.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("akber_evidence_missing")
    missing = list(akber_input.get("missing_critical_context") or [])
    vetoes = _hard_vetoes(akber_input)
    if vetoes:
        decision = "veto"
    elif missing:
        decision = "hold_missing_context"
    else:
        decision = "pass"

    stages: list[dict[str, Any]] = []
    stage_labels = {
        "context": "Context",
        "catalyst": "Catalyst",
        "confirmation": "Confirmation",
        "risk": "Risk",
        "execution": "Execution",
        "postmortem_learning": "Postmortem Learning",
    }
    for stage_number, (stage, fields) in enumerate(STAGE_FIELDS.items(), start=1):
        if stage == "postmortem_learning":
            stage_state = "ready_after_outcome"
            missing_fields: list[str] = []
            stage_vetoes: list[str] = []
        else:
            missing_fields = [field for field in fields if field in missing]
            stage_vetoes = [veto for veto in vetoes if any(field in veto for field in fields)]
            stage_state = "veto" if stage_vetoes else ("hold" if missing_fields else "pass")
        stages.append(
            {
                "stage_number": stage_number,
                "stage": stage,
                "label": stage_labels[stage],
                "state": stage_state,
                "evidence_fields": list(fields),
                "missing_fields": missing_fields,
                "veto_reasons": stage_vetoes,
            }
        )

    if decision == "pass":
        explanation = (
            "The historical edge has complete current-market confirmation for Akber review. "
            "This is not risk or execution approval."
        )
    elif decision == "veto":
        explanation = (
            "Akber rejected the setup because current evidence contains an explicit "
            "adverse condition."
        )
    else:
        explanation = (
            f"Akber is waiting for {len(missing)} required context field"
            f"{'s' if len(missing) != 1 else ''}: {', '.join(missing)}."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v3_result",
        "phase_id": PHASE_ID,
        "generated_at": akber_input.get("generated_at"),
        "akber_result_id": stable_id(
            "akber-result-v3", akber_input.get("akber_input_id"), decision
        ),
        "akber_input_id": akber_input.get("akber_input_id"),
        "hypothesis_id": akber_input.get("hypothesis_id"),
        "edge_id": akber_input.get("edge_id"),
        "research_goal_id": akber_input.get("research_goal_id"),
        "applied_learning_version_ids": akber_input.get("applied_learning_version_ids", []),
        "stage1_learning_input_version": akber_input.get("stage1_learning_input_version"),
        "policy_version": akber_input.get("policy_version"),
        "decision": decision,
        "stages": stages,
        "missing_critical_context": missing,
        "missing_critical_context_count": len(missing),
        "hard_vetoes": vetoes,
        "router_eligible": decision == "pass" and not missing,
        "router_eligibility_recommendation_only": True,
        "plain_english_explanation": explanation,
        "decision_rule": (
            "explicit adverse evidence -> veto; missing required evidence -> hold; "
            "all required evidence clean -> pass"
        ),
        "akber_pass_is_execution_approval": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def _focus_terms(symbols: set[str]) -> set[str]:
    terms = {symbol.lower() for symbol in symbols}
    if symbols.intersection({"CL=F", "USO", "BNO", "XLE"}):
        terms.update({"crude", "oil", "energy"})
    if symbols.intersection({"SI=F", "SLV", "SIL", "GLD"}):
        terms.update({"silver", "metal", "macro"})
    if symbols.intersection({"ITA", "XAR", "LMT", "PPA"}):
        terms.update({"defence", "defense", "geopolitical"})
    if symbols.intersection({"SMH", "SOXX", "NVDA", "QQQ"}):
        terms.update({"semiconductor", "technology", "policy"})
    return terms


def _latest_signal_review(reviews: list[dict[str, Any]], symbols: set[str]) -> dict[str, Any]:
    terms = _focus_terms(symbols)
    matching = [
        review
        for review in reviews
        if isinstance(review, dict)
        and any(term in str(review.get("instrument_focus") or "").lower() for term in terms)
    ]
    return max(
        matching,
        key=lambda row: (
            parse_timestamp(row.get("reviewed_at")) or datetime.min.replace(tzinfo=timezone.utc)
        ),
        default={},
    )


def assemble_current_akber_context(
    hypothesis: dict[str, Any],
    artifacts: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Assemble truthful current evidence without treating samples as live data."""

    symbols = _matching_symbols(hypothesis)
    market_context = artifacts.get("market_context")
    market_context = market_context if isinstance(market_context, dict) else {}
    packet = _matching_market_packet(hypothesis, market_context)
    packet_at = packet.get("generated_at")
    packet_fresh = _is_fresh_runtime_record(packet_at, generated_at=generated_at)
    price_records = _matching_records(packet, "price_volume_context", symbols)
    technical_records = _matching_records(packet, "technical_context", symbols)
    orderflow_records = _matching_records(packet, "orderflow_context", symbols)
    price_payload = packet.get("price_volume_context")
    price_payload = price_payload if isinstance(price_payload, dict) else {}
    technical_payload = packet.get("technical_context")
    technical_payload = technical_payload if isinstance(technical_payload, dict) else {}
    orderflow_payload = packet.get("orderflow_context")
    orderflow_payload = orderflow_payload if isinstance(orderflow_payload, dict) else {}

    truthful_price_records = [
        record
        for record in price_records
        if record.get("last_close") is not None
        and not _sample_or_fixture_state(record.get("market_state"))
        and not _sample_or_fixture_state(price_payload.get("status"))
    ]
    truthful_technical_records = [
        record
        for record in technical_records
        if not _sample_or_fixture_state(technical_payload.get("status"))
        and not _sample_or_fixture_state(record.get("origin_class"))
    ]

    tradingview_status = artifacts.get("tradingview_status")
    tradingview_status = tradingview_status if isinstance(tradingview_status, dict) else {}
    tradingview_context = artifacts.get("tradingview_context")
    tradingview_context = tradingview_context if isinstance(tradingview_context, dict) else {}
    tradingview_state = str(
        tradingview_status.get("truthful_state")
        or tradingview_status.get("connection_state")
        or tradingview_context.get("connection_state")
        or tradingview_context.get("status")
        or "unavailable"
    ).lower()
    tradingview_live = bool(
        tradingview_status.get("live_calls_enabled") is True
        and tradingview_status.get("provider_backed_record_count", 0) > 0
        and not _sample_or_fixture_state(tradingview_state)
    )
    if tradingview_live:
        direct_technical = tradingview_context.get("technical_contexts")
        direct_technical = direct_technical if isinstance(direct_technical, list) else []
        truthful_technical_records.extend(
            record
            for record in direct_technical
            if isinstance(record, dict)
            and str(record.get("symbol") or "").upper() in symbols
            and _is_fresh_runtime_record(
                record.get("observed_at") or tradingview_context.get("written_at"),
                generated_at=generated_at,
            )
        )

    bookmap = artifacts.get("bookmap_context")
    bookmap = bookmap if isinstance(bookmap, dict) else {}
    bookmap_sample = bookmap.get("sample") is True or _sample_or_fixture_state(
        bookmap.get("classification")
    )
    truthful_orderflow_records = [
        record
        for record in orderflow_records
        if not bookmap_sample
        and not _sample_or_fixture_state(orderflow_payload.get("status"))
        and not _sample_or_fixture_state(record.get("origin_class"))
    ]
    if not bookmap_sample:
        direct_orderflow = bookmap.get("orderflow_contexts")
        direct_orderflow = direct_orderflow if isinstance(direct_orderflow, list) else []
        truthful_orderflow_records.extend(
            record
            for record in direct_orderflow
            if isinstance(record, dict)
            and str(record.get("symbol") or "").upper() in symbols
            and _is_fresh_runtime_record(
                record.get("observed_at") or bookmap.get("written_at"),
                generated_at=generated_at,
            )
        )

    edge_lineage = hypothesis.get("edge_lineage")
    edge_lineage = edge_lineage if isinstance(edge_lineage, dict) else {}
    expected = hypothesis.get("expected_edge_range")
    expected = expected if isinstance(expected, dict) else {}
    invalidation = hypothesis.get("invalidation_exit")
    invalidation = invalidation if isinstance(invalidation, dict) else {}
    risk = hypothesis.get("risk_concept")
    risk = risk if isinstance(risk, dict) else {}
    mapping = hypothesis.get("instrument_proxy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    hypothesis_at = str(hypothesis.get("generated_at") or generated_at)

    source_price_available = bool(
        edge_lineage.get("edge_id")
        and edge_lineage.get("edge_registry_reference", {}).get("complete") is True
        and expected.get("net_expectancy") is not None
    )
    source_price = _context_evidence(
        "source_price_context",
        available=source_price_available,
        state="validated_edge_context" if source_price_available else "missing",
        observed_at=hypothesis_at,
        source_refs=[
            f"{HYPOTHESES_ARTIFACT}#{hypothesis.get('hypothesis_id')}",
            f"qadam_edge_registry.jsonl#{edge_lineage.get('edge_id')}",
        ],
        value={
            "edge_id": edge_lineage.get("edge_id"),
            "net_expectancy": expected.get("net_expectancy"),
            "confidence_distribution": expected.get("confidence_distribution"),
        },
        details={
            "backtest_run_id": edge_lineage.get("backtest_run_id"),
            "latest_supporting_sample": edge_lineage.get("latest_supporting_sample"),
        },
        provider="OR-10 empirical edge registry",
        reason=(
            "The hypothesis carries an admitted empirical edge."
            if source_price_available
            else "No complete OR-10 edge lineage is attached."
        ),
    )

    quorum = packet.get("source_quorum_result")
    quorum = quorum if isinstance(quorum, dict) else {}
    catalyst_available = bool(
        packet
        and packet_fresh
        and packet.get("market_context_status") == "context_ready"
        and quorum.get("status") == "pass"
    )
    fresh_catalyst = _context_evidence(
        "fresh_catalyst",
        available=catalyst_available,
        state="confirmed" if catalyst_available else "missing_or_degraded",
        observed_at=packet_at,
        source_refs=[f"{MARKET_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"] if packet else [],
        value=packet.get("hypothesis"),
        details={
            "market_context_status": packet.get("market_context_status"),
            "source_quorum_status": quorum.get("status"),
            "source_quorum_score": quorum.get("score"),
            "missing_context": packet.get("missing_context", []),
        },
        provider="Qadam Market Context Packet",
        reason=(
            "A fresh corroborated catalyst packet matches the hypothesis."
            if catalyst_available
            else "No fresh matching packet has passed source quorum and context readiness."
        ),
    )

    technical_available = bool(packet_fresh and truthful_technical_records)
    technical_confirmation = _context_evidence(
        "technical_confirmation",
        available=technical_available,
        state=(
            "confirmed"
            if technical_available
            else "sample_or_fixture_not_admissible"
            if _sample_or_fixture_state(technical_payload.get("status"))
            or _sample_or_fixture_state(tradingview_state)
            else "missing"
        ),
        observed_at=packet_at,
        source_refs=[f"{MARKET_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"] if packet else [],
        value=truthful_technical_records,
        details={
            "tradingview_truthful_state": tradingview_state,
            "tradingview_live": tradingview_live,
            "supplemental_only": True,
        },
        provider="TradingView supplemental technical context",
        origin_class="supplemental_provider_context",
        reason=(
            "Fresh provider-backed technical observations corroborate the setup."
            if technical_available
            else "TradingView technical context is absent, stale, or sample-only."
        ),
        fallback_used=True,
    )

    price_volume_available = bool(
        packet_fresh
        and truthful_price_records
        and any(record.get("volume_ratio") is not None for record in truthful_price_records)
    )
    orderflow_available = bool(packet_fresh and truthful_orderflow_records)
    volume_available = price_volume_available or orderflow_available
    volume_confirmation = _context_evidence(
        "volume_or_flow_confirmation",
        available=volume_available,
        state="confirmed" if volume_available else "missing",
        observed_at=packet_at or bookmap.get("written_at"),
        source_refs=[f"{MARKET_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"] if packet else [],
        value={
            "price_volume_records": truthful_price_records,
            "orderflow_records": truthful_orderflow_records,
        },
        details={
            "bookmap_sample": bookmap_sample,
            "supplemental_only": True,
        },
        provider="Yahoo Finance or Bookmap supplemental context",
        origin_class="supplemental_provider_context",
        reason=(
            "Fresh truthful volume or order-flow evidence is available."
            if volume_available
            else "Volume or order-flow evidence is absent, stale, or sample-only."
        ),
        fallback_used=True,
    )

    volatility_records = [
        record
        for record in truthful_price_records
        if record.get("rolling_volatility_20d") is not None
    ]
    volatility_available = bool(packet_fresh and volatility_records)
    volatility_context = _context_evidence(
        "volatility_context",
        available=volatility_available,
        state="measured" if volatility_available else "missing",
        observed_at=packet_at,
        source_refs=[f"{MARKET_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"] if packet else [],
        value=volatility_records,
        provider=str(price_payload.get("provider") or "market context provider"),
        origin_class="supplemental_provider_context",
        reason=(
            "A fresh trailing-volatility measure is available."
            if volatility_available
            else "No fresh truthful volatility measure is attached."
        ),
        fallback_used=True,
    )

    signal_reviews = artifacts.get("signal_integrity_reviews")
    signal_reviews = signal_reviews if isinstance(signal_reviews, list) else []
    signal_review = _latest_signal_review(signal_reviews, symbols)
    confirmation_policy = signal_review.get("market_confirmation_policy")
    confirmation_policy = confirmation_policy if isinstance(confirmation_policy, dict) else {}
    pricing_gap_available = bool(
        signal_review
        and _is_fresh_runtime_record(signal_review.get("reviewed_at"), generated_at=generated_at)
        and confirmation_policy.get("pricing_gap_result") not in {None, "unavailable"}
        and confirmation_policy.get("pricing_gap_status")
        not in {"missing_pricing_gap", "pricing_gap_unavailable_market_confirmation_unavailable"}
    )
    pricing_gap = _context_evidence(
        "pricing_gap_evidence",
        available=pricing_gap_available,
        state="measured" if pricing_gap_available else "missing",
        observed_at=signal_review.get("reviewed_at"),
        source_refs=[f"{SIGNAL_INTEGRITY_ARTIFACT}#{signal_review.get('review_id')}"]
        if signal_review
        else [],
        value=confirmation_policy.get("pricing_gap_result"),
        details=confirmation_policy,
        provider="Qadam Signal Integrity",
        reason=(
            "Signal Integrity measured a current pricing gap."
            if pricing_gap_available
            else "No fresh matching Signal Integrity review measured a pricing gap."
        ),
    )

    expected_net = expected.get("net_expectancy")
    reward_to_risk = risk.get("expected_reward_to_risk")
    risk_available = bool(
        expected_net is not None
        and safe_float(expected_net) > 0
        and reward_to_risk is not None
        and safe_float(reward_to_risk) >= 1.25
    )
    risk_reward = _context_evidence(
        "risk_reward_context",
        available=risk_available,
        state="measured" if risk_available else "missing",
        observed_at=hypothesis_at,
        source_refs=[f"{HYPOTHESES_ARTIFACT}#{hypothesis.get('hypothesis_id')}"],
        value={"expected_net_return": expected_net, "reward_to_risk": reward_to_risk},
        details={"expected_net_return": expected_net, "reward_to_risk": reward_to_risk},
        provider="OR-11 Strategy Foundry",
        reason=(
            "Expected return after costs and reward-to-risk are both defined."
            if risk_available
            else "A positive edge may exist, but numeric reward-to-risk is not yet defined."
        ),
    )

    invalidators = invalidation.get("invalidation_conditions")
    invalidators = invalidators if isinstance(invalidators, list) else []
    invalidation_available = bool(invalidators)
    invalidation_clarity = _context_evidence(
        "invalidation_clarity",
        available=invalidation_available,
        state="defined" if invalidation_available else "missing",
        observed_at=hypothesis_at,
        source_refs=[f"{HYPOTHESES_ARTIFACT}#{hypothesis.get('hypothesis_id')}"],
        value=invalidators,
        details={"defined": invalidation_available},
        provider="OR-11 Strategy Foundry",
        reason=(
            "Explicit invalidation conditions are recorded."
            if invalidation_available
            else "No explicit invalidation condition is recorded."
        ),
    )

    spread_records = [
        record for record in truthful_price_records if record.get("spread_bps") is not None
    ]
    liquidity_available = bool(packet_fresh and spread_records)
    liquidity = _context_evidence(
        "liquidity_and_spread",
        available=liquidity_available,
        state="measured" if liquidity_available else "missing",
        observed_at=packet_at,
        source_refs=[f"{MARKET_CONTEXT_ARTIFACT}#{packet.get('packet_id')}"] if packet else [],
        value=spread_records,
        details={
            "spread_bps": min(
                (safe_float(record.get("spread_bps")) for record in spread_records),
                default=None,
            )
        },
        provider=str(price_payload.get("provider") or "market context provider"),
        reason=(
            "Fresh spread and liquidity evidence is available."
            if liquidity_available
            else "No fresh provider-backed spread measurement is attached."
        ),
    )

    mirror = artifacts.get("alpaca_mirror")
    mirror = mirror if isinstance(mirror, dict) else {}
    snapshot = mirror.get("snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    mirror_at = snapshot.get("observed_at")
    mirror_ready = bool(
        mirror.get("status") == "ok"
        and snapshot.get("mode") == "paper"
        and snapshot.get("connection_status") == "alpaca_paper_readonly_connected"
        and _is_fresh_runtime_record(mirror_at, generated_at=generated_at)
        and mapping.get("execution_proxy")
    )
    paperability = _context_evidence(
        "paperability_proxy",
        available=mirror_ready,
        state="ready" if mirror_ready else "missing_or_stale",
        observed_at=mirror_at,
        source_refs=[ALPACA_MIRROR_ARTIFACT],
        value=mapping.get("execution_proxy"),
        details={
            "paperable": mirror_ready,
            "execution_proxy": mapping.get("execution_proxy"),
            "paper_route": "guarded_alpaca_paper_via_paperops",
            "mirror_write_authority": mirror.get("write_authority"),
        },
        provider="Alpaca paper read-only mirror",
        reason=(
            "The mapped proxy exists on a fresh read-only Alpaca paper route."
            if mirror_ready
            else "The paper proxy or fresh read-only broker mirror is unavailable."
        ),
    )

    comparisons = artifacts.get("nonlinear_comparisons")
    comparisons = comparisons if isinstance(comparisons, list) else []
    horizon = hypothesis.get("direction_horizon", {}).get("horizon")
    matching_comparisons = [
        record
        for record in comparisons
        if isinstance(record, dict)
        and str(record.get("instrument") or "").upper() in symbols
        and record.get("horizon") == horizon
    ]
    quantum_available = bool(matching_comparisons)
    nonlinear_quantum = _context_evidence(
        "nonlinear_quantum_review",
        available=quantum_available,
        state="reviewed" if quantum_available else "missing",
        observed_at=max(
            (str(record.get("generated_at")) for record in matching_comparisons),
            default=hypothesis_at,
        ),
        source_refs=[
            f"{NONLINEAR_COMPARISON_ARTIFACT}#{record.get('comparison_id')}"
            for record in matching_comparisons
        ],
        value=[record.get("verdict") for record in matching_comparisons],
        details={
            "comparison_count": len(matching_comparisons),
            "physical_hardware_used": any(
                record.get("hardware_used") is True for record in matching_comparisons
            ),
            "review_is_not_trade_approval": True,
        },
        provider="OR-9 nonlinear and quantum comparison",
        reason=(
            "A matched nonlinear or quantum usefulness review exists."
            if quantum_available
            else "No OR-9 comparison matches this instrument and horizon."
        ),
    )

    return {
        "source_price_context": source_price,
        "fresh_catalyst": fresh_catalyst,
        "technical_confirmation": technical_confirmation,
        "volume_or_flow_confirmation": volume_confirmation,
        "volatility_context": volatility_context,
        "pricing_gap_evidence": pricing_gap,
        "risk_reward_context": risk_reward,
        "invalidation_clarity": invalidation_clarity,
        "liquidity_and_spread": liquidity,
        "paperability_proxy": paperability,
        "nonlinear_quantum_review": nonlinear_quantum,
        "_assembled_from_canonical_artifacts": True,
        "_source_artifacts": [
            HYPOTHESES_ARTIFACT,
            MARKET_CONTEXT_ARTIFACT,
            SIGNAL_INTEGRITY_ARTIFACT,
            ALPACA_MIRROR_ARTIFACT,
            TRADINGVIEW_STATUS_ARTIFACT,
            TRADINGVIEW_CONTEXT_ARTIFACT,
            BOOKMAP_CONTEXT_ARTIFACT,
            NONLINEAR_COMPARISON_ARTIFACT,
        ],
    }


def summarize_akber_replay(
    result: dict[str, Any],
    *,
    realized_net_return: float,
    regime: str,
    outcome_available_at: str,
) -> dict[str, Any]:
    """Create one research-only historical replay record."""

    decision_at = parse_timestamp(result.get("generated_at"))
    observed_at = parse_timestamp(outcome_available_at)
    if decision_at is None or observed_at is None or observed_at <= decision_at:
        raise ValueError("akber_replay_outcome_not_after_decision")
    decision = str(result.get("decision"))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v3_replay",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "replay_id": stable_id(
            "akber-replay-v3", result.get("akber_result_id"), outcome_available_at
        ),
        "akber_result_id": result.get("akber_result_id"),
        "hypothesis_id": result.get("hypothesis_id"),
        "applied_learning_version_ids": result.get("applied_learning_version_ids", []),
        "stage1_learning_input_version": result.get("stage1_learning_input_version"),
        "decision": decision,
        "realized_net_return": realized_net_return,
        "regime": regime,
        "outcome_available_at": outcome_available_at,
        "false_positive_removed": decision == "veto" and realized_net_return <= 0,
        "good_opportunity_filtered": decision != "pass" and realized_net_return > 0,
        "missed_opportunity_return": max(realized_net_return, 0.0) if decision != "pass" else 0.0,
        "proof_eligible": False,
        "authority": authority_flags(),
    }


def _resolve_research_path(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = _repo_root() / path
    resolved = path.resolve()
    research_root = (_repo_root() / "data" / "research").resolve()
    try:
        resolved.relative_to(research_root)
    except ValueError:
        return None
    return resolved


def load_historical_akber_inputs(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Load and verify the immutable OR-8 result and fold partitions."""

    errors: list[str] = []
    bulk = manifest.get("bulk_results")
    bulk = bulk if isinstance(bulk, dict) else {}
    result_path = _resolve_research_path(bulk.get("result_path"))
    fold_path = _resolve_research_path(bulk.get("fold_path"))
    if manifest.get("status") != "complete":
        errors.append("or8_backtest_manifest_not_complete")
    if result_path is None or not result_path.exists():
        errors.append("or8_result_partition_missing_or_outside_research_store")
    if fold_path is None or not fold_path.exists():
        errors.append("or8_fold_partition_missing_or_outside_research_store")
    results = read_jsonl(result_path) if result_path and result_path.exists() else []
    folds = read_jsonl(fold_path) if fold_path and fold_path.exists() else []
    if safe_int(bulk.get("result_count"), -1) != len(results):
        errors.append("or8_result_count_mismatch")
    if safe_int(bulk.get("fold_count"), -1) != len(folds):
        errors.append("or8_fold_count_mismatch")
    if results and record_set_hash(results) != bulk.get("result_record_set_hash"):
        errors.append("or8_result_record_set_hash_mismatch")
    if folds and record_set_hash(folds) != bulk.get("fold_record_set_hash"):
        errors.append("or8_fold_record_set_hash_mismatch")
    return results, folds, unique_errors(errors)


def _instrument_paperability(instrument: str, strategy_map: dict[str, Any]) -> dict[str, Any]:
    rows = strategy_map.get("strategies")
    rows = rows if isinstance(rows, list) else []
    matching_families: list[str] = []
    paperable_proxies: set[str] = set()
    direct = False
    for strategy in rows:
        if not isinstance(strategy, dict):
            continue
        contribution = strategy.get("instrument_contribution")
        contribution = contribution if isinstance(contribution, dict) else {}
        instruments = contribution.get("instruments")
        instruments = instruments if isinstance(instruments, list) else []
        if not any(
            isinstance(row, dict) and row.get("symbol") == instrument for row in instruments
        ):
            continue
        matching_families.append(str(strategy.get("strategy_family_id")))
        for row in instruments:
            if not isinstance(row, dict) or row.get("paper_route_available") is not True:
                continue
            symbol = str(row.get("symbol") or "")
            if symbol:
                paperable_proxies.add(symbol)
            if symbol == instrument:
                direct = True
    return {
        "paperable": bool(paperable_proxies),
        "directly_paperable": direct,
        "paperable_proxies": sorted(paperable_proxies),
        "matching_strategy_families": sorted(matching_families),
    }


def _fold_evidence(folds: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [
        row.get("test_metrics")
        for row in folds
        if isinstance(row, dict) and isinstance(row.get("test_metrics"), dict)
    ]
    returns = [safe_float(row.get("mean_net_return")) for row in metrics]
    drawdowns = [safe_float(row.get("maximum_drawdown")) for row in metrics]
    trade_counts = [safe_int(row.get("trade_count")) for row in metrics]
    missing_costs = [safe_int(row.get("missing_cost_outcome_count")) for row in metrics]
    return {
        "fold_count": len(metrics),
        "fold_trade_count": sum(trade_counts),
        "mean_fold_net_return": mean(returns) if returns else None,
        "positive_fold_ratio": (
            sum(value > 0 for value in returns) / len(returns) if returns else None
        ),
        "worst_fold_drawdown": min(drawdowns) if drawdowns else None,
        "missing_cost_outcome_count": sum(missing_costs),
    }


def _historical_stage_states(
    policy_inputs: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    active = dict(HISTORICAL_POLICY)
    if policy:
        active.update(policy)
    context_pass = bool(
        policy_inputs.get("chronological") is True
        and policy_inputs.get("holdout_untouched_during_tuning") is True
        and safe_int(policy_inputs.get("independent_row_count"))
        >= safe_int(active["minimum_independent_rows"])
        and safe_int(policy_inputs.get("fold_count")) >= safe_int(active["minimum_fold_count"])
    )
    source_count = safe_int(policy_inputs.get("independent_source_count"))
    catalyst_pass = source_count >= 2
    positive_ratio = safe_float(policy_inputs.get("positive_fold_ratio"), -1.0)
    mean_fold_return = safe_float(policy_inputs.get("mean_fold_net_return"), -1.0)
    confirmation_veto = bool(positive_ratio < 0.25 and mean_fold_return < 0)
    confirmation_pass = bool(
        positive_ratio >= safe_float(active["minimum_positive_fold_ratio"])
        and mean_fold_return > safe_float(active["minimum_mean_fold_net_return"])
    )
    worst_drawdown = safe_float(policy_inputs.get("worst_fold_drawdown"), -1.0)
    risk_veto = bool(mean_fold_return <= -0.002 or worst_drawdown < -0.50)
    risk_pass = bool(
        mean_fold_return > safe_float(active["minimum_mean_fold_net_return"])
        and worst_drawdown >= safe_float(active["maximum_fold_drawdown"])
    )
    execution_pass = bool(
        policy_inputs.get("cost_adjusted") is True
        and safe_int(policy_inputs.get("missing_cost_outcome_count")) == 0
        and safe_int(policy_inputs.get("fold_trade_count"))
        >= safe_int(active["minimum_fold_trade_count"])
        and policy_inputs.get("paperable_proxy_available") is True
    )

    def stage(
        number: int,
        name: str,
        passed: bool,
        *,
        veto: bool = False,
        evidence: dict[str, Any],
        explanation: str,
    ) -> dict[str, Any]:
        return {
            "stage_number": number,
            "stage": name,
            "state": "veto" if veto else "pass" if passed else "hold",
            "evidence": evidence,
            "plain_english": explanation,
        }

    return [
        stage(
            1,
            "context",
            context_pass,
            evidence={
                key: policy_inputs.get(key)
                for key in (
                    "chronological",
                    "holdout_untouched_during_tuning",
                    "independent_row_count",
                    "fold_count",
                )
            },
            explanation="Checks whether the historical test is chronological, independent, and large enough to inspect.",
        ),
        stage(
            2,
            "catalyst",
            catalyst_pass,
            evidence={"independent_source_count": source_count},
            explanation="Checks whether at least two independent source histories contributed before the outcome window.",
        ),
        stage(
            3,
            "confirmation",
            confirmation_pass,
            veto=confirmation_veto,
            evidence={
                "positive_fold_ratio": positive_ratio,
                "mean_fold_net_return": mean_fold_return,
            },
            explanation="Checks whether the relationship repeated across pre-holdout walk-forward folds rather than appearing once.",
        ),
        stage(
            4,
            "risk",
            risk_pass,
            veto=risk_veto,
            evidence={
                "mean_fold_net_return": mean_fold_return,
                "worst_fold_drawdown": worst_drawdown,
            },
            explanation="Checks whether pre-holdout return stayed positive without an unacceptable historical drawdown.",
        ),
        stage(
            5,
            "execution",
            execution_pass,
            evidence={
                key: policy_inputs.get(key)
                for key in (
                    "cost_adjusted",
                    "missing_cost_outcome_count",
                    "fold_trade_count",
                    "paperable_proxy_available",
                )
            },
            explanation="Checks costs, observation count, and whether an approved paper proxy exists.",
        ),
        {
            "stage_number": 6,
            "stage": "postmortem_learning",
            "state": "ready_after_outcome",
            "evidence": {"untouched_holdout_reserved": True},
            "plain_english": "Reserves the untouched holdout for measuring whether Akber's earlier decision helped or hurt.",
        },
    ]


def _decision_from_historical_stages(
    stages: list[dict[str, Any]], *, ignored_stage: str | None = None
) -> str:
    gating = [
        row
        for row in stages
        if row.get("stage") != "postmortem_learning" and row.get("stage") != ignored_stage
    ]
    if any(row.get("state") == "veto" for row in gating):
        return "veto"
    if any(row.get("state") != "pass" for row in gating):
        return "hold_missing_context"
    return "pass"


def build_historical_akber_replay(
    results: list[dict[str, Any]],
    folds: list[dict[str, Any]],
    strategy_map: dict[str, Any],
    manifest: dict[str, Any],
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    """Replay Akber with pre-holdout evidence, then reveal untouched outcomes."""

    folds_by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    for fold in folds:
        hypothesis_id = str(fold.get("hypothesis_id") or "")
        if hypothesis_id:
            folds_by_hypothesis.setdefault(hypothesis_id, []).append(fold)
    replay: list[dict[str, Any]] = []
    for result in results:
        if result.get("method_class") != "qadam" or result.get("negative_control") is True:
            continue
        hypothesis_id = str(result.get("hypothesis_id") or "")
        holdout = result.get("holdout_metrics")
        holdout = holdout if isinstance(holdout, dict) else {}
        decision_at = parse_timestamp(result.get("holdout_start_at"))
        outcome_at = parse_timestamp(result.get("holdout_end_at"))
        if (
            holdout.get("state") != "measured"
            or holdout.get("mean_net_return") is None
            or decision_at is None
            or outcome_at is None
            or outcome_at <= decision_at
        ):
            continue
        matching_folds = folds_by_hypothesis.get(hypothesis_id, [])
        fold_evidence = _fold_evidence(matching_folds)
        paperability = _instrument_paperability(str(result.get("instrument") or ""), strategy_map)
        policy_inputs = {
            "chronological": result.get("chronological") is True,
            "holdout_untouched_during_tuning": result.get("holdout_untouched_during_tuning")
            is True,
            "independent_row_count": result.get("independent_row_count"),
            "independent_source_count": len(set(result.get("source_keys", []))),
            "cost_adjusted": result.get("cost_adjusted") is True,
            "paperable_proxy_available": paperability.get("paperable") is True,
            **fold_evidence,
        }
        stages = _historical_stage_states(policy_inputs)
        decision = _decision_from_historical_stages(stages)
        mean_net = holdout.get("mean_net_return")
        measured = True
        replay.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_akber_filter_v3_historical_replay",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "replay_id": stable_id(
                    "akber-historical-replay-v3",
                    manifest.get("run_id"),
                    hypothesis_id,
                    POLICY_VERSION,
                ),
                "backtest_run_id": manifest.get("run_id"),
                "backtest_hypothesis_id": hypothesis_id,
                "method_id": result.get("method_id"),
                "strategy_family_id": result.get("strategy_family_id"),
                "instrument": result.get("instrument"),
                "horizon": result.get("horizon"),
                "policy_version": POLICY_VERSION,
                "decision_evidence_cutoff": result.get("holdout_start_at"),
                "outcome_window_start": result.get("holdout_start_at"),
                "outcome_available_at": result.get("holdout_end_at"),
                "decision_frozen_before_holdout_outcome": True,
                "holdout_fields_used_to_make_decision": [],
                "pre_holdout_policy_inputs": policy_inputs,
                "stages": stages,
                "decision": decision,
                "paperability": paperability,
                "paperability_mapping_scope": (
                    "current_approved_proxy_mapping_used_as_an_operational_constraint;"
                    "not_claimed_as_historical_market_availability"
                ),
                "outcome": {
                    "measured": measured,
                    "mean_net_return": mean_net,
                    "cumulative_net_return": holdout.get("cumulative_net_return"),
                    "hit_rate": holdout.get("hit_rate"),
                    "maximum_drawdown": holdout.get("maximum_drawdown"),
                    "trade_count": holdout.get("trade_count"),
                    "regime_mean_net_returns": holdout.get("regime_mean_net_returns", {}),
                },
                "false_positive_removed": bool(
                    measured and decision != "pass" and safe_float(mean_net) <= 0
                ),
                "good_opportunity_filtered": bool(
                    measured and decision != "pass" and safe_float(mean_net) > 0
                ),
                "passed_negative_outcome": bool(
                    measured and decision == "pass" and safe_float(mean_net) <= 0
                ),
                "passed_positive_outcome": bool(
                    measured and decision == "pass" and safe_float(mean_net) > 0
                ),
                "replay_is_result_level_diagnostic_not_portfolio_simulation": True,
                "threshold_change_applied": False,
                "strategy_mutation_created": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "proof_eligible": False,
                "authority": authority_flags(),
            }
        )
    return replay


def _replay_metrics(
    replay: list[dict[str, Any]], *, ignored_stage: str | None = None
) -> dict[str, Any]:
    measured = [row for row in replay if row.get("outcome", {}).get("measured") is True]
    decisions = {
        row["replay_id"]: _decision_from_historical_stages(
            row.get("stages", []), ignored_stage=ignored_stage
        )
        for row in measured
    }
    passed = [row for row in measured if decisions.get(row["replay_id"]) == "pass"]
    all_returns = [safe_float(row["outcome"].get("mean_net_return")) for row in measured]
    passed_returns = [safe_float(row["outcome"].get("mean_net_return")) for row in passed]
    all_drawdowns = [safe_float(row["outcome"].get("maximum_drawdown")) for row in measured]
    passed_drawdowns = [safe_float(row["outcome"].get("maximum_drawdown")) for row in passed]
    all_turnover = sum(safe_int(row["outcome"].get("trade_count")) for row in measured)
    passed_turnover = sum(safe_int(row["outcome"].get("trade_count")) for row in passed)
    false_positives_removed = sum(
        decisions.get(row["replay_id"]) != "pass"
        and safe_float(row["outcome"].get("mean_net_return")) <= 0
        for row in measured
    )
    good_opportunities_filtered = sum(
        decisions.get(row["replay_id"]) != "pass"
        and safe_float(row["outcome"].get("mean_net_return")) > 0
        for row in measured
    )
    missed_opportunity_cost = sum(
        max(0.0, safe_float(row["outcome"].get("mean_net_return")))
        for row in measured
        if decisions.get(row["replay_id"]) != "pass"
    )
    selection_net_effect = sum(
        -safe_float(row["outcome"].get("mean_net_return"))
        for row in measured
        if decisions.get(row["replay_id"]) != "pass"
    )
    regime_values: dict[str, list[float]] = {}
    for row in passed:
        for regime, value in row["outcome"].get("regime_mean_net_returns", {}).items():
            regime_values.setdefault(str(regime), []).append(safe_float(value))
    unfiltered_expectancy = mean(all_returns) if all_returns else None
    filtered_expectancy = mean(passed_returns) if passed_returns else None
    unfiltered_drawdown = min(all_drawdowns) if all_drawdowns else None
    filtered_drawdown = min(passed_drawdowns) if passed_drawdowns else None
    return {
        "measured_replay_count": len(measured),
        "pass_count": len(passed),
        "hold_count": sum(decision == "hold_missing_context" for decision in decisions.values()),
        "veto_count": sum(decision == "veto" for decision in decisions.values()),
        "unfiltered_mean_net_return": unfiltered_expectancy,
        "filtered_mean_net_return": filtered_expectancy,
        "expectancy_change": (
            filtered_expectancy - unfiltered_expectancy
            if filtered_expectancy is not None and unfiltered_expectancy is not None
            else None
        ),
        "unfiltered_worst_drawdown": unfiltered_drawdown,
        "filtered_worst_drawdown": filtered_drawdown,
        "drawdown_change": (
            filtered_drawdown - unfiltered_drawdown
            if filtered_drawdown is not None and unfiltered_drawdown is not None
            else None
        ),
        "unfiltered_turnover_proxy": all_turnover,
        "filtered_turnover_proxy": passed_turnover,
        "turnover_change": passed_turnover - all_turnover,
        "false_positives_removed": false_positives_removed,
        "good_opportunities_filtered": good_opportunities_filtered,
        "missed_opportunity_cost_result_level_sum": missed_opportunity_cost,
        "selection_net_effect_result_level_sum": selection_net_effect,
        "passed_regime_mean_net_returns": {
            regime: mean(values) for regime, values in sorted(regime_values.items())
        },
        "metrics_are_result_level_diagnostics_not_portfolio_returns": True,
    }


def build_stage_ablations(
    replay: list[dict[str, Any]], *, generated_at: str
) -> list[dict[str, Any]]:
    base = _replay_metrics(replay)
    records: list[dict[str, Any]] = []
    for stage in STAGE_FIELDS:
        metrics = _replay_metrics(replay, ignored_stage=stage)
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_akber_filter_v3_stage_ablation",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "ablation_id": stable_id("akber-stage-ablation-v3", POLICY_VERSION, stage),
                "policy_version": POLICY_VERSION,
                "stage_removed": stage,
                "stage_was_gating": stage != "postmortem_learning",
                "base_metrics": base,
                "ablation_metrics": metrics,
                "delta": {
                    "pass_count": metrics["pass_count"] - base["pass_count"],
                    "false_positives_removed": metrics["false_positives_removed"]
                    - base["false_positives_removed"],
                    "good_opportunities_filtered": metrics["good_opportunities_filtered"]
                    - base["good_opportunities_filtered"],
                    "expectancy_change": (
                        metrics["filtered_mean_net_return"] - base["filtered_mean_net_return"]
                        if metrics["filtered_mean_net_return"] is not None
                        and base["filtered_mean_net_return"] is not None
                        else None
                    ),
                    "drawdown_change": (
                        metrics["filtered_worst_drawdown"] - base["filtered_worst_drawdown"]
                        if metrics["filtered_worst_drawdown"] is not None
                        and base["filtered_worst_drawdown"] is not None
                        else None
                    ),
                    "turnover_change": metrics["filtered_turnover_proxy"]
                    - base["filtered_turnover_proxy"],
                },
                "holdout_used_to_change_policy": False,
                "threshold_change_applied": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "proof_eligible": False,
                "authority": authority_flags(),
            }
        )
    return records


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[max(0, min(index, len(ordered) - 1))]


def build_threshold_proposals(
    replay: list[dict[str, Any]],
    *,
    generated_at: str,
    validated_edge_count: int,
) -> list[dict[str, Any]]:
    inputs = [row.get("pre_holdout_policy_inputs", {}) for row in replay]
    definitions = [
        (
            "minimum_independent_rows",
            float(HISTORICAL_POLICY["minimum_independent_rows"]),
            _quantile(
                [safe_float(row.get("independent_row_count")) for row in inputs],
                0.25,
            ),
            "25th percentile of pre-holdout independent sample counts",
        ),
        (
            "minimum_fold_trade_count",
            float(HISTORICAL_POLICY["minimum_fold_trade_count"]),
            _quantile([safe_float(row.get("fold_trade_count")) for row in inputs], 0.25),
            "25th percentile of pre-holdout walk-forward trade counts",
        ),
        (
            "minimum_positive_fold_ratio",
            float(HISTORICAL_POLICY["minimum_positive_fold_ratio"]),
            median([safe_float(row.get("positive_fold_ratio")) for row in inputs])
            if inputs
            else None,
            "median positive-fold ratio before untouched holdout",
        ),
        (
            "minimum_mean_fold_net_return",
            float(HISTORICAL_POLICY["minimum_mean_fold_net_return"]),
            median([safe_float(row.get("mean_fold_net_return")) for row in inputs])
            if inputs
            else None,
            "median pre-holdout walk-forward net return",
        ),
        (
            "maximum_fold_drawdown",
            float(HISTORICAL_POLICY["maximum_fold_drawdown"]),
            _quantile(
                [safe_float(row.get("worst_fold_drawdown")) for row in inputs],
                0.25,
            ),
            "25th percentile of pre-holdout worst-fold drawdown",
        ),
    ]
    records: list[dict[str, Any]] = []
    for name, current, proposed, basis in definitions:
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_akber_filter_v3_threshold_proposal",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "proposal_id": stable_id(
                    "akber-threshold-proposal-v3", POLICY_VERSION, name, proposed
                ),
                "current_policy_version": POLICY_VERSION,
                "threshold_name": name,
                "current_value": current,
                "proposed_value": proposed,
                "proposal_basis": basis,
                "proposal_sample_count": len(inputs),
                "proposal_evidence_window": "pre_holdout_training_and_walk_forward_only",
                "untouched_holdout_used_to_generate_proposal": False,
                "proposal_state": (
                    "proposal_only_insufficient_validated_edge_support"
                    if validated_edge_count == 0
                    else "proposal_only_pending_explicit_versioned_review"
                ),
                "explicit_operator_review_required": True,
                "threshold_change_applied": False,
                "strategy_mutation_created": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return records


def build_akber_filter_v3_from_inputs(
    hypotheses: list[dict[str, Any]],
    foundry_summary: dict[str, Any],
    backtest_manifest: dict[str, Any],
    historical_results: list[dict[str, Any]],
    historical_folds: list[dict[str, Any]],
    strategy_map: dict[str, Any],
    current_artifacts: dict[str, Any],
    *,
    generated_at: str,
    historical_input_errors: list[str] | None = None,
) -> dict[str, Any]:
    generated = generated_at
    input_errors = list(historical_input_errors or [])
    if foundry_summary.get("implementation_complete") is not True:
        input_errors.append("or11_foundry_not_complete")
    if foundry_summary.get("admission_contract") != "durable_or10_edge_registry_only":
        input_errors.append("or11_admission_contract_invalid")
    if safe_int(foundry_summary.get("hypothesis_count"), -1) != len(hypotheses):
        input_errors.append("or11_hypothesis_count_mismatch")
    if safe_int(strategy_map.get("strategy_count"), -1) <= 0:
        input_errors.append("or10_strategy_map_missing")
    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "unknown")
        if not hypothesis.get("edge_lineage", {}).get("edge_id"):
            input_errors.append(f"or11_hypothesis_edge_lineage_missing:{hypothesis_id}")
        if hypothesis.get("hypothesis_state") == "shadow_only" and hypothesis.get(
            "akber_review_allowed"
        ):
            input_errors.append(f"or11_exploratory_hypothesis_akber_enabled:{hypothesis_id}")

    inputs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if not input_errors:
        for hypothesis in hypotheses:
            if hypothesis.get("akber_review_allowed") is not True:
                continue
            context = assemble_current_akber_context(
                hypothesis, current_artifacts, generated_at=generated
            )
            akber_input = build_akber_input(
                hypothesis,
                context,
                generated_at=generated,
                strict_provenance=True,
            )
            inputs.append(akber_input)
            results.append(evaluate_akber_input(akber_input))

    replay = (
        build_historical_akber_replay(
            historical_results,
            historical_folds,
            strategy_map,
            backtest_manifest,
            generated_at=generated,
        )
        if not input_errors
        else []
    )
    historical_qadam_result_count = sum(
        result.get("method_class") == "qadam" and result.get("negative_control") is not True
        for result in historical_results
    )
    historical_exclusion_count = historical_qadam_result_count - len(replay)
    ablation = build_stage_ablations(replay, generated_at=generated) if replay else []
    edge_class_counts = foundry_summary.get("edge_class_counts")
    edge_class_counts = edge_class_counts if isinstance(edge_class_counts, dict) else {}
    validated_edge_count = safe_int(edge_class_counts.get("validated_research_edge"))
    threshold_proposals = (
        build_threshold_proposals(
            replay,
            generated_at=generated,
            validated_edge_count=validated_edge_count,
        )
        if replay
        else []
    )
    decision_counts = Counter(record["decision"] for record in results)
    historical_metrics = _replay_metrics(replay) if replay else {}
    historical_measurable = bool(
        replay and historical_metrics.get("measured_replay_count") == len(replay) and ablation
    )
    valid_no_current_hypothesis_outcome = bool(
        not input_errors and not hypotheses and not inputs and not results
    )
    if input_errors:
        status = "akber_v3_blocked_invalid_input"
    elif hypotheses:
        status = "akber_v3_complete_with_current_reviews"
    else:
        status = "akber_v3_complete_no_current_hypotheses"
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v3_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": status,
        "implementation_complete": not input_errors,
        "valid_no_current_hypothesis_outcome": valid_no_current_hypothesis_outcome,
        "headline": (
            "No edge-backed idea is waiting at Akber's filter"
            if not hypotheses
            else "Akber is checking whether each edge-backed idea is practical now"
        ),
        "plain_english": (
            "Akber asks six questions in order: does the context fit, is the catalyst fresh, "
            "does the market confirm it, is the risk clear, can the paper proxy be used cleanly, "
            "and will the outcome be recorded for learning?"
        ),
        "hypothesis_count": len(hypotheses),
        "input_count": len(inputs),
        "result_count": len(results),
        "decision_counts": dict(sorted(decision_counts.items())),
        "historical_replay_count": len(replay),
        "historical_qadam_result_count": historical_qadam_result_count,
        "historical_exclusion_count": historical_exclusion_count,
        "historical_exclusion_reason": (
            "no_complete_untouched_holdout_outcome" if historical_exclusion_count else None
        ),
        "net_historical_contribution_measurable": historical_measurable,
        "historical_filter_metrics": historical_metrics,
        "historical_measurement_scope": (
            "result_level_untouched_holdout_diagnostic_not_portfolio_return"
        ),
        "ablation_count": len(ablation),
        "threshold_proposal_count": len(threshold_proposals),
        "threshold_change_applied": False,
        "current_context_rule": (
            "Canonical provider-backed context is preferred. Truthfully labelled supplemental "
            "context may corroborate; sample, fixture, stale, or dependency-missing data cannot pass."
        ),
        "decision_rule": (
            "Explicit adverse evidence means veto; missing required evidence means hold; "
            "all required evidence clean means pass."
        ),
        "next_action": (
            "Improve evidence until OR-10 admits an edge and OR-11 forms a hypothesis."
            if not hypotheses
            else "Fill every missing current-market field without using samples or stale fallbacks."
        ),
        "paperops_state": "watch_only_research_lock_active",
        "authority": authority_flags(),
    }
    return {
        "inputs": inputs,
        "results": results,
        "replay": replay,
        "ablation": ablation,
        "threshold_proposals": threshold_proposals,
        "dashboard": dashboard,
        "historical_metrics": historical_metrics,
        "input_errors": unique_errors(input_errors),
        "input_lineage": {
            "foundry_artifact": FOUNDRY_SUMMARY_ARTIFACT,
            "foundry_generated_at": foundry_summary.get("generated_at"),
            "foundry_hypothesis_count": len(hypotheses),
            "backtest_manifest_artifact": BACKTEST_MANIFEST_ARTIFACT,
            "backtest_run_id": backtest_manifest.get("run_id"),
            "historical_qadam_result_count": historical_qadam_result_count,
            "measurable_historical_replay_count": len(replay),
            "historical_exclusion_count": historical_exclusion_count,
            "backtest_result_record_set_hash": backtest_manifest.get("bulk_results", {}).get(
                "result_record_set_hash"
            ),
            "backtest_fold_record_set_hash": backtest_manifest.get("bulk_results", {}).get(
                "fold_record_set_hash"
            ),
            "complete": not input_errors,
        },
    }


def build_akber_filter_v3_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    foundry_summary = read_json(runtime / FOUNDRY_SUMMARY_ARTIFACT)
    backtest_manifest = read_json(runtime / BACKTEST_MANIFEST_ARTIFACT)
    historical_results, historical_folds, historical_errors = load_historical_akber_inputs(
        backtest_manifest
    )
    current_artifacts = {
        "market_context": read_json(runtime / MARKET_CONTEXT_ARTIFACT),
        "signal_integrity_reviews": (
            read_jsonl(runtime / SIGNAL_INTEGRITY_ARTIFACT) if hypotheses else []
        ),
        "alpaca_mirror": read_json(runtime / ALPACA_MIRROR_ARTIFACT),
        "tradingview_status": read_json(runtime / TRADINGVIEW_STATUS_ARTIFACT),
        "tradingview_context": read_json(runtime / TRADINGVIEW_CONTEXT_ARTIFACT),
        "bookmap_context": read_json(runtime / BOOKMAP_CONTEXT_ARTIFACT),
        "nonlinear_comparisons": read_jsonl(runtime / NONLINEAR_COMPARISON_ARTIFACT),
    }
    return build_akber_filter_v3_from_inputs(
        hypotheses,
        foundry_summary,
        backtest_manifest,
        historical_results,
        historical_folds,
        read_json(runtime / STRATEGY_MAP_ARTIFACT),
        current_artifacts,
        generated_at=generated,
        historical_input_errors=historical_errors,
    )


def validate_akber_filter_v3_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(f"akber_input_invalid:{error}" for error in state.get("input_errors", []))
    inputs = state["inputs"]
    results = state["results"]
    if state.get("input_lineage", {}).get("complete") is not True:
        errors.append("akber_input_lineage_incomplete")
    input_by_id = {record.get("akber_input_id"): record for record in inputs}
    if len(input_by_id) != len(inputs):
        errors.append("akber_input_id_missing_or_duplicate")
    for record in inputs:
        evidence = record.get("evidence")
        if not isinstance(evidence, dict) or set(evidence) != set(CONTEXT_FIELDS):
            errors.append(f"akber_context_contract_incomplete:{record.get('akber_input_id')}")
        if record.get("trade_candidate_created") is not False:
            errors.append("akber_input_created_trade_candidate")
        if record.get("strict_provenance_required") is True:
            for field, evidence_record in evidence.items():
                if evidence_record.get("available") is True and (
                    evidence_record.get("fixture_backed") is True
                    or evidence_record.get("freshness_state") == "stale"
                    or evidence_record.get("provenance_complete") is not True
                ):
                    errors.append(
                        f"akber_admitted_unsafe_context:{record.get('akber_input_id')}:{field}"
                    )
        errors.extend(validate_authority(record.get("authority", {}), prefix="akber_input"))
    for result in results:
        if result.get("akber_input_id") not in input_by_id:
            errors.append("akber_result_input_lineage_missing")
        if result.get("decision") not in DECISIONS:
            errors.append("akber_decision_invalid")
        if len(result.get("stages", [])) != len(STAGE_FIELDS):
            errors.append("akber_six_stage_contract_incomplete")
        elif [row.get("stage") for row in result.get("stages", [])] != list(STAGE_FIELDS):
            errors.append("akber_six_stage_order_invalid")
        if (
            result.get("router_eligible") is True
            and result.get("missing_critical_context_count") != 0
        ):
            errors.append("akber_router_eligible_with_missing_context")
        if result.get("decision") == "pass" and result.get("hard_vetoes"):
            errors.append("akber_pass_with_hard_veto")
        if result.get("akber_pass_is_execution_approval") is not False:
            errors.append("akber_pass_became_execution_approval")
        for field in (
            "risk_approval_created",
            "execution_approval_created",
            "trade_candidate_created",
            "paper_order_created",
        ):
            if result.get(field) is not False:
                errors.append(f"akber_authority_object_created:{field}")
        errors.extend(validate_authority(result.get("authority", {}), prefix="akber_result"))
    replay_ids: set[str] = set()
    for record in state["replay"]:
        replay_id = str(record.get("replay_id") or "")
        if not replay_id or replay_id in replay_ids:
            errors.append("akber_replay_id_missing_or_duplicate")
        replay_ids.add(replay_id)
        decision_at = parse_timestamp(record.get("decision_evidence_cutoff"))
        outcome_at = parse_timestamp(record.get("outcome_available_at"))
        if decision_at is None or outcome_at is None or outcome_at <= decision_at:
            errors.append(f"akber_replay_temporal_order_invalid:{replay_id}")
        if record.get("decision_frozen_before_holdout_outcome") is not True:
            errors.append(f"akber_replay_not_frozen_before_outcome:{replay_id}")
        if record.get("holdout_fields_used_to_make_decision"):
            errors.append(f"akber_replay_holdout_leakage:{replay_id}")
        if len(record.get("stages", [])) != len(STAGE_FIELDS):
            errors.append(f"akber_replay_stage_contract_incomplete:{replay_id}")
        if record.get("proof_eligible") is not False:
            errors.append("akber_replay_proof_eligible")
        for field in (
            "threshold_change_applied",
            "strategy_mutation_created",
            "trade_candidate_created",
            "paper_order_created",
        ):
            if record.get(field) is not False:
                errors.append(f"akber_replay_created_forbidden_output:{replay_id}:{field}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="akber_replay"))
    ablation_stages = [record.get("stage_removed") for record in state["ablation"]]
    if state["replay"] and ablation_stages != list(STAGE_FIELDS):
        errors.append("akber_stage_ablation_coverage_incomplete")
    for record in state["ablation"]:
        if (
            record.get("threshold_change_applied") is not False
            or record.get("holdout_used_to_change_policy") is not False
            or record.get("proof_eligible") is not False
        ):
            errors.append(f"akber_ablation_boundary_invalid:{record.get('ablation_id')}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="akber_ablation"))
    for record in state["threshold_proposals"]:
        if record.get("untouched_holdout_used_to_generate_proposal") is not False:
            errors.append(f"akber_threshold_proposal_leaks_holdout:{record.get('proposal_id')}")
        if (
            record.get("threshold_change_applied") is not False
            or record.get("explicit_operator_review_required") is not True
        ):
            errors.append(
                f"akber_threshold_proposal_applied_without_review:{record.get('proposal_id')}"
            )
        errors.extend(validate_authority(record.get("authority", {}), prefix="akber_threshold"))
    if state["threshold_proposals"] and state["dashboard"].get("threshold_change_applied"):
        errors.append("akber_threshold_change_applied_without_review")
    if not state["replay"]:
        errors.append("akber_historical_replay_missing")
    if not state["ablation"]:
        errors.append("akber_historical_ablation_missing")
    if state["dashboard"].get("net_historical_contribution_measurable") is not True:
        errors.append("akber_historical_contribution_not_measurable")
    if (
        not inputs
        and not results
        and state["dashboard"].get("valid_no_current_hypothesis_outcome") is not True
    ):
        errors.append("akber_valid_no_current_hypothesis_state_missing")
    errors.extend(
        validate_authority(state["dashboard"].get("authority", {}), prefix="akber_dashboard")
    )
    return unique_errors(errors)


def build_and_write_akber_filter_v3(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_akber_filter_v3_state(settings)
    store.write_jsonl(INPUTS_ARTIFACT, state["inputs"])
    store.write_jsonl(RESULTS_ARTIFACT, state["results"])
    store.write_jsonl(REPLAY_ARTIFACT, state["replay"])
    store.write_jsonl(ABLATION_ARTIFACT, state["ablation"])
    store.write_jsonl(THRESHOLD_PROPOSALS_ARTIFACT, state["threshold_proposals"])
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    errors = validate_akber_filter_v3_state(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v3_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "implementation_complete": not errors
        and state["dashboard"].get("implementation_complete") is True,
        "valid_no_current_hypothesis_outcome": state["dashboard"].get(
            "valid_no_current_hypothesis_outcome"
        ),
        "policy_version": POLICY_VERSION,
        "input_lineage": state.get("input_lineage", {}),
        "input_validation_error_count": len(state.get("input_errors", [])),
        "input_count": len(state["inputs"]),
        "result_count": len(state["results"]),
        "pass_count": sum(record.get("decision") == "pass" for record in state["results"]),
        "hold_count": sum(
            record.get("decision") == "hold_missing_context" for record in state["results"]
        ),
        "veto_count": sum(record.get("decision") == "veto" for record in state["results"]),
        "historical_replay_count": len(state["replay"]),
        "historical_qadam_result_count": state["dashboard"].get("historical_qadam_result_count"),
        "historical_exclusion_count": state["dashboard"].get("historical_exclusion_count"),
        "ablation_count": len(state["ablation"]),
        "threshold_proposal_count": len(state["threshold_proposals"]),
        "historical_filter_metrics": state.get("historical_metrics", {}),
        "net_historical_contribution_measurable": state["dashboard"][
            "net_historical_contribution_measurable"
        ],
        "router_eligible_with_missing_context_count": sum(
            record.get("router_eligible") is True
            and record.get("missing_critical_context_count") != 0
            for record in state["results"]
        ),
        "sample_or_fixture_context_admitted_count": sum(
            evidence.get("available") is True and evidence.get("fixture_backed") is True
            for record in state["inputs"]
            for evidence in record.get("evidence", {}).values()
        ),
        "threshold_change_applied_count": 0,
        "execution_approval_created_count": 0,
        "risk_approval_created_count": 0,
        "trade_candidate_created_count": 0,
        "order_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "paperops_watch_only": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
