"""Q5-3 Risk Agent paper-sizing contract.

This module consumes Q5-2 approval-policy decisions and current evidence
posture, then emits Phase 5 `risk_sizing_review` artifacts. It can mark a
strategy family as paper-size eligible only when policy, evidence, paper-account
state, source posture, market confirmation, and invalidation checks pass. It
cannot create trade candidates, execution intents, staged orders, broker
receipts, positions, or broker-write authority.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.phase4_candidate_strategy_universe import (
    build_candidate_strategy_universe,
    validate_candidate_strategy_universe,
)
from orchestrator.phase5_approval_policy import (
    APPROVAL_POLICY_RUNTIME_ARTIFACT,
    build_phase5_approval_policy_decisions,
    validate_phase5_approval_policy_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.signal_integrity import SignalIntegrityReviewStore
from world_monitor.source_registry import (
    EXPECTED_SOURCE_COUNT,
    canonical_decision_source_coverage,
)


PHASE5_RISK_SIZING_SCHEMA_VERSION = 1
MAX_RISK_PCT_PER_IDEA = 1.0
MAX_DRAWDOWN_PCT = 10.0
RISK_SIZING_RUNTIME_ARTIFACT = "phase5_risk_sizing_reviews.json"
RISK_SIZING_HISTORY = "phase5_risk_sizing_reviews_history.jsonl"
RISK_SIZING_EVENT_LOG = "phase5_risk_sizing_events.jsonl"
RISK_SIZING_EVENT_TYPE = "phase5_risk_sizing_review_written"
RISK_SIZING_COMPONENT = "phase5_risk_agent_paper_sizing"
RISK_SIZING_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_approval_policy_decisions.json",
    "data/runtime/phase4_candidate_strategy_universe.json",
    "data/runtime/signal_integrity_reviews.jsonl",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/preference_provenance_source_quorum.json",
)

RISK_SIZING_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "risk_approval_authority",
    "risk_agent_approval_authority",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "staged_paper_order_allowed",
    "staged_order_created",
    "paper_order_submission_allowed",
    "paper_order_submitted",
    "broker_write_allowed",
    "broker_post_called",
    "broker_submit_receipt_created",
    "position_created",
    "live_capital_enabled",
)

RISK_SIZING_COUNT_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed_count",
    "trade_candidate_created_count",
    "execution_policy_handoff_allowed_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "paper_order_allowed_count",
    "staged_order_created_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_submit_receipt_created_count",
    "position_created_count",
    "live_capital_enabled_count",
)

RISK_SIZING_BOUNDARY = (
    "Q5-3 Risk Agent paper-sizing reviews can block, hold, or mark a strategy "
    "family as paper-size eligible for later kill-switch checks. They cannot "
    "create trade candidates, hand off to Execution Policy, create execution "
    "intents, stage or submit paper orders, write brokers, create receipts, "
    "create positions, or enable live capital."
)

INSTRUMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "prediction_markets": ("prediction_markets", "polymarket", "kalshi"),
    "crude_oil": ("crude_oil", "oil", "energy_transport", "energy_security"),
    "defence": ("defence", "defense", "conflict", "geopolitical"),
    "silver": ("silver", "macro", "liquidity"),
    "semiconductors": ("semiconductors", "semiconductor", "chips", "ai_chip"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_universe(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_candidate_strategy_universe.json"
    return _read_json(runtime_path) or build_candidate_strategy_universe(settings)


def _approval_policy_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / APPROVAL_POLICY_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_approval_policy_decisions(settings)


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-3"
    ledger["boundary"] = (
        "Q5-3 records Risk Agent sizing decisions only. Every execution, order, "
        "broker, position, and live-capital authority flag remains false."
    )
    return ledger


def _candidate_by_key(candidate_universe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(candidate.get("candidate_key")): candidate
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("candidate_key")
    }


def _approval_decisions(approval_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        decision
        for decision in approval_bundle.get("decisions", [])
        if isinstance(decision, dict)
    ]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _all_false(payload: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(payload.get(field) is False for field in fields)


def _matches_instrument(primary_instrument: str, review_focus: str) -> bool:
    primary = primary_instrument.lower()
    focus = review_focus.lower()
    if not primary or not focus:
        return False
    if primary in focus or focus in primary:
        return True
    aliases = INSTRUMENT_ALIASES.get(primary, ())
    return any(alias in focus for alias in aliases)


def _matching_signal_reviews(
    primary_instrument: str,
    signal_reviews: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    matches = [
        review
        for review in signal_reviews
        if _matches_instrument(primary_instrument, str(review.get("instrument_focus") or ""))
    ]
    return tuple(matches[-20:])


def _merge_counts(*counts: dict[str, Any]) -> dict[str, int]:
    merged: Counter[str] = Counter()
    for count in counts:
        if not isinstance(count, dict):
            continue
        for key, value in count.items():
            merged[str(key)] += int(value or 0)
    return dict(sorted(merged.items()))


def _top_failure_reasons(
    candidate_context: dict[str, Any],
    matching_reviews: tuple[dict[str, Any], ...],
) -> dict[str, int]:
    failures: Counter[str] = Counter()
    context_reasons = candidate_context.get("top_failure_reasons", {})
    if isinstance(context_reasons, dict):
        for reason, count in context_reasons.items():
            failures[str(reason)] += int(count or 0)
    for review in matching_reviews:
        for reason in review.get("failure_reasons", []) or []:
            failures[str(reason)] += 1
    return dict(failures.most_common(10))


def _latest_signal_review(matching_reviews: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return matching_reviews[-1] if matching_reviews else {}


def _signal_evidence_summary(
    candidate: dict[str, Any],
    primary_instrument: str,
    signal_reviews: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    context = candidate.get("signal_integrity_context", {})
    if not isinstance(context, dict):
        context = {}
    matching = _matching_signal_reviews(primary_instrument, signal_reviews)
    latest = _latest_signal_review(matching)
    live_counts = Counter(str(review.get("status") or "unknown") for review in matching)
    status_counts = _merge_counts(context.get("status_counts", {}), dict(live_counts))
    passed_count = int(status_counts.get("passed_to_risk_shadow", 0) or 0)
    latest_market = latest.get("market_confirmation_policy", {})
    if not isinstance(latest_market, dict):
        latest_market = {}
    latest_preference = latest.get("preference_context_policy", {})
    if not isinstance(latest_preference, dict):
        latest_preference = {}
    top_failures = _top_failure_reasons(context, matching)
    return {
        "candidate_context_review_count": int(context.get("review_count", 0) or 0),
        "matching_live_review_count": len(matching),
        "status_counts": status_counts,
        "passed_to_risk_shadow_count": passed_count,
        "hold_for_corroboration_count": int(status_counts.get("hold_for_corroboration", 0) or 0),
        "blocked_count": int(status_counts.get("blocked", 0) or 0),
        "latest_review_id": latest.get("review_id"),
        "latest_review_status": str(latest.get("status") or "missing"),
        "latest_reviewed_at": latest.get("reviewed_at"),
        "latest_integrity_score": _float(latest.get("integrity_score"), 0.0),
        "latest_source_count": int(_float(latest.get("source_count"), 0)),
        "latest_evidence_item_count": int(_float(latest.get("evidence_item_count"), 0)),
        "latest_average_trust_score": _float(latest.get("average_trust_score"), 0.0),
        "latest_min_trust_score": _float(latest.get("min_trust_score"), 0.0),
        "latest_market_confirmation_status": str(latest_market.get("status") or "missing"),
        "latest_market_confirmation_pricing_gap": str(latest_market.get("pricing_gap") or "missing"),
        "latest_market_confirmation_stale": latest_market.get("stale") is True,
        "latest_market_confirmation_unavailable": latest_market.get("unavailable") is True,
        "latest_market_uses_yahoo_finance": latest_market.get("uses_yahoo_finance") is True,
        "latest_market_providers": list(latest_market.get("providers", []) or []),
        "latest_preference_status": str(latest_preference.get("status") or "missing"),
        "latest_preference_source_quorum_credit_allowed": (
            latest_preference.get("source_quorum_credit_allowed") is True
        ),
        "latest_preference_only_confirmation_allowed": (
            latest_preference.get("preference_only_confirmation_allowed") is True
        ),
        "latest_preference_risk_handoff_allowed": (
            latest_preference.get("risk_handoff_allowed") is True
        ),
        "top_failure_reasons": top_failures,
        "signal_integrity_passed": passed_count > 0,
        "trade_candidate_created_count": int(context.get("trade_candidate_created_count", 0) or 0),
        "execution_allowed_count": int(context.get("execution_allowed_count", 0) or 0),
        "paper_order_allowed_count": int(context.get("paper_order_allowed_count", 0) or 0),
    }


def _source_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    source_weights = candidate.get("source_weights", {})
    if not isinstance(source_weights, dict):
        source_weights = {}
    required_sources = [
        str(source) for source in candidate.get("required_source_groups", []) or []
    ]
    weights = [float(value or 0.0) for value in source_weights.values()]
    coverage = candidate.get("decision_source_coverage")
    if not isinstance(coverage, dict):
        coverage = canonical_decision_source_coverage(
            required_source_groups=required_sources,
            source_weights=source_weights,
            coverage_scope="phase5_risk_sizing_source_summary",
        )
    return {
        "required_source_group_count": len(required_sources),
        "required_source_groups": required_sources,
        "source_weight_count": len(source_weights),
        "source_weight_sum": round(sum(weights), 4),
        "min_source_weight": round(min(weights), 4) if weights else 0.0,
        "zero_weight_sources": sorted(
            source for source, weight in source_weights.items() if float(weight or 0.0) <= 0
        ),
        "source_weights_normalized": 0.995 <= sum(weights) <= 1.005,
        "canonical_source_count": int(coverage.get("canonical_source_count", 0) or 0),
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "all_canonical_sources_considered": (
            coverage.get("all_canonical_sources_considered") is True
        ),
        "decision_source_usage_complete": (
            coverage.get("decision_source_usage_complete") is True
        ),
        "source_quorum_bypass_allowed": (
            coverage.get("source_quorum_bypass_allowed") is True
        ),
        "decision_source_coverage": coverage,
    }


def _market_policy_summary(decision: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    policy = candidate.get("market_confirmation_requirements", {})
    if not isinstance(policy, dict):
        policy = decision.get("market_confirmation_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return {
        "required": policy.get("required") is True,
        "non_yahoo_independent_confirmation_required": (
            policy.get("non_yahoo_independent_confirmation_required") is True
        ),
        "yahoo_finance_role": str(policy.get("yahoo_finance_role") or "missing"),
        "yahoo_only_confirmation_allowed": policy.get("yahoo_only_confirmation_allowed") is True,
        "stale_confirmation_allowed": policy.get("stale_confirmation_allowed") is True,
        "single_source_confirmation_allowed": policy.get("single_source_confirmation_allowed") is True,
        "pricing_gap_required": policy.get("pricing_gap_required") is True,
    }


def _preference_policy_summary(decision: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    policy = candidate.get("preference_context_policy", {})
    if not isinstance(policy, dict):
        policy = decision.get("preference_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return {
        "source_role": str(policy.get("source_role") or "missing"),
        "status": str(policy.get("status") or "missing"),
        "approved_domain_pack_count": int(policy.get("approved_domain_pack_count", 0) or 0),
        "source_quorum_credit_allowed": policy.get("source_quorum_credit_allowed") is True,
        "preference_only_confirmation_allowed": (
            policy.get("preference_only_confirmation_allowed") is True
        ),
        "risk_handoff_allowed": policy.get("risk_handoff_allowed") is True,
        "execution_allowed": policy.get("execution_allowed") is True,
        "paper_order_allowed": policy.get("paper_order_allowed") is True,
        "broker_write_allowed": policy.get("broker_write_allowed") is True,
        "live_capital_enabled": policy.get("live_capital_enabled") is True,
        "quota_degraded": policy.get("quota_degraded") is True,
        "context_stale": policy.get("context_stale") is True,
    }


def _risk_caps(settings: Settings, account_context: dict[str, Any]) -> dict[str, float]:
    policy_balance = float(settings.trial_balance_gbp)
    current_balance = _float(account_context.get("current_balance_gbp"), policy_balance)
    sizing_balance = min(policy_balance, current_balance)
    max_risk_gbp = round(sizing_balance * MAX_RISK_PCT_PER_IDEA / 100, 2)
    return {
        "policy_balance_gbp": round(policy_balance, 2),
        "current_balance_gbp": round(current_balance, 2),
        "sizing_balance_gbp": round(sizing_balance, 2),
        "max_risk_gbp": max_risk_gbp,
        "max_risk_pct": MAX_RISK_PCT_PER_IDEA,
        "max_drawdown_pct": MAX_DRAWDOWN_PCT,
    }


def _risk_score(
    *,
    source_summary: dict[str, Any],
    signal_evidence: dict[str, Any],
    risk_blockers: list[str],
    caution_count: int,
) -> float:
    score = 0.35
    score += min(0.25, _float(source_summary.get("min_source_weight"), 0.0))
    score += min(0.25, _float(signal_evidence.get("latest_integrity_score"), 0.0) * 0.25)
    score += 0.1 if signal_evidence.get("signal_integrity_passed") is True else 0.0
    score -= min(0.5, len(risk_blockers) * 0.08)
    score -= min(0.15, caution_count * 0.03)
    return round(max(0.0, min(1.0, score)), 3)


def _risk_review(
    decision: dict[str, Any],
    *,
    candidate: dict[str, Any] | None,
    settings: Settings,
    account_context: dict[str, Any],
    signal_reviews: tuple[dict[str, Any], ...],
    global_errors: list[str],
) -> dict[str, Any]:
    candidate = candidate or {}
    strategy_key = str(decision.get("strategy_family_key") or "unknown_strategy")
    primary_instrument = str(decision.get("primary_instrument") or "")
    if not primary_instrument:
        instruments = candidate.get("instrument_universe", []) or []
        primary_instrument = str(instruments[0]) if instruments else "unknown_instrument"
    source_summary = _source_summary(candidate)
    market_policy = _market_policy_summary(decision, candidate)
    preference_policy = _preference_policy_summary(decision, candidate)
    signal_evidence = _signal_evidence_summary(candidate, primary_instrument, signal_reviews)
    risk_caps = _risk_caps(settings, account_context)
    invalidation_conditions = [
        str(item) for item in candidate.get("invalidation_conditions", []) or []
    ]
    no_trade_conditions = [
        str(item) for item in candidate.get("no_trade_conditions", []) or []
    ]
    account_drawdown = _float(account_context.get("drawdown_pct"), 0.0)
    checks = [
        _check("global_context_validated", not global_errors, detail=global_errors),
        _check("approval_policy_eligible", decision.get("status") == "eligible"),
        _check(
            "approval_policy_decision_allows_q5_3",
            decision.get("policy_decision") == "eligible_for_q5_3_risk_sizing_contract",
        ),
        _check("approved_strategy_toggle", decision.get("approved_strategy_toggle_state") == "approved_shadow"),
        _check("paper_account_mode", account_context.get("mode") == "paper"),
        _check("paper_account_live_capital_disabled", account_context.get("live_capital_enabled") is False),
        _check("paper_account_write_authority_disabled", account_context.get("write_authority") is False),
        _check("paper_account_order_authority_disabled", account_context.get("paper_order_allowed") is False),
        _check("drawdown_within_cap", account_drawdown <= MAX_DRAWDOWN_PCT, detail=account_drawdown),
        _check("source_weights_present", source_summary["source_weight_count"] > 0),
        _check("source_weights_normalized", source_summary["source_weights_normalized"]),
        _check("source_weights_nonzero", not source_summary["zero_weight_sources"]),
        _check(
            "canonical_decision_source_coverage_complete",
            source_summary["canonical_source_count"] == EXPECTED_SOURCE_COUNT
            and source_summary["all_canonical_sources_considered"] is True
            and source_summary["decision_source_usage_complete"] is True
            and source_summary["source_quorum_bypass_allowed"] is False,
        ),
        _check("signal_integrity_passed", signal_evidence["signal_integrity_passed"]),
        _check("signal_integrity_no_trade_candidate", signal_evidence["trade_candidate_created_count"] == 0),
        _check("signal_integrity_no_execution", signal_evidence["execution_allowed_count"] == 0),
        _check("signal_integrity_no_paper_order", signal_evidence["paper_order_allowed_count"] == 0),
        _check("market_confirmation_required", market_policy["required"]),
        _check(
            "non_yahoo_market_confirmation_required",
            market_policy["non_yahoo_independent_confirmation_required"],
        ),
        _check("yahoo_supplemental_only", market_policy["yahoo_finance_role"] == "supplemental_market_confirmation_only"),
        _check("yahoo_only_confirmation_blocked", not market_policy["yahoo_only_confirmation_allowed"]),
        _check("stale_confirmation_blocked", not market_policy["stale_confirmation_allowed"]),
        _check(
            "single_source_confirmation_blocked",
            not market_policy["single_source_confirmation_allowed"],
        ),
        _check("pricing_gap_required", market_policy["pricing_gap_required"]),
        _check(
            "latest_market_confirmation_available",
            signal_evidence["latest_market_confirmation_status"]
            == "market_confirmation_corroboration_available",
        ),
        _check(
            "latest_market_confirmation_fresh",
            not signal_evidence["latest_market_confirmation_stale"],
        ),
        _check(
            "pricing_gap_confirmed",
            signal_evidence["latest_market_confirmation_pricing_gap"]
            == "pass_pricing_gap_confirmed",
        ),
        _check("invalidation_conditions_present", bool(invalidation_conditions)),
        _check("no_trade_conditions_present", bool(no_trade_conditions)),
        _check(
            "preference_supplemental_only",
            preference_policy["source_role"] == "supplemental_multi_source_data_plane",
        ),
        _check("preference_domain_pack_mapped", preference_policy["approved_domain_pack_count"] > 0),
        _check("preference_not_source_quorum", not preference_policy["source_quorum_credit_allowed"]),
        _check("preference_not_sole_confirmation", not preference_policy["preference_only_confirmation_allowed"]),
        _check("preference_no_risk_handoff", not preference_policy["risk_handoff_allowed"]),
        _check("preference_no_execution", not preference_policy["execution_allowed"]),
        _check("preference_no_paper_order", not preference_policy["paper_order_allowed"]),
        _check("preference_no_broker_write", not preference_policy["broker_write_allowed"]),
        _check("preference_no_live_capital", not preference_policy["live_capital_enabled"]),
    ]
    risk_blockers = [
        check["name"]
        for check in checks
        if not check["passed"]
        and check["name"]
        not in {
            "global_context_validated",
        }
    ]
    risk_blockers.extend(global_errors)
    latest_signal_ready = (
        signal_evidence["latest_review_status"] == "passed_to_risk_shadow"
        and signal_evidence["latest_market_confirmation_status"]
        == "market_confirmation_corroboration_available"
        and signal_evidence["latest_market_confirmation_pricing_gap"]
        == "pass_pricing_gap_confirmed"
    )
    top_failures = set(signal_evidence.get("top_failure_reasons", {}))
    if not latest_signal_ready:
        if "market_confirmation_unavailable" in top_failures:
            risk_blockers.append("signal_market_confirmation_unavailable")
        if "market_confirmation_stale" in top_failures:
            risk_blockers.append("signal_market_confirmation_stale")
        if "preference_only_confirmation_hold" in top_failures:
            risk_blockers.append("signal_preference_only_confirmation_hold")
        if "missing_pricing_gap" in top_failures:
            risk_blockers.append("signal_pricing_gap_missing")
    risk_blockers = sorted(dict.fromkeys(risk_blockers))
    cautions: list[str] = []
    if preference_policy["quota_degraded"]:
        cautions.append("preference_quota_degraded_context_only")
    if decision.get("caution_count", 0):
        cautions.extend(str(item) for item in decision.get("cautions", []) or [])
    cautions = sorted(dict.fromkeys(cautions))
    if risk_blockers:
        status = "blocked"
        risk_decision = "blocked_risk_gate_failed"
    else:
        status = "eligible"
        risk_decision = "paper_size_eligible"
    proposed_risk_gbp = round(risk_caps["max_risk_gbp"] * 0.5, 2) if status == "eligible" else 0.0
    proposed_risk_pct = round(MAX_RISK_PCT_PER_IDEA * 0.5, 3) if status == "eligible" else 0.0
    review = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "risk_sizing_schema_version": PHASE5_RISK_SIZING_SCHEMA_VERSION,
        "artifact_type": "risk_sizing_review",
        "artifact_id": f"phase5:q5-3:risk-sizing:{strategy_key}",
        "phase": "Q5",
        "stage": "Q5-3",
        "status": status,
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(RISK_SIZING_SOURCE_REFS),
        "boundary": RISK_SIZING_BOUNDARY,
        **phase5_authority_defaults(),
        "strategy_family_key": strategy_key,
        "source_approval_policy_artifact_id": decision.get("artifact_id"),
        "approval_policy_status": str(decision.get("status") or "missing"),
        "approval_policy_decision": str(decision.get("policy_decision") or "missing"),
        "approved_strategy_toggle_state": str(decision.get("approved_strategy_toggle_state") or "missing"),
        "primary_instrument": primary_instrument,
        "risk_decision": risk_decision,
        "paper_size_eligible": status == "eligible",
        "proposed_risk_gbp": proposed_risk_gbp,
        "proposed_risk_pct": proposed_risk_pct,
        "max_risk_gbp": risk_caps["max_risk_gbp"],
        "max_risk_pct": risk_caps["max_risk_pct"],
        "policy_balance_gbp": risk_caps["policy_balance_gbp"],
        "sizing_balance_gbp": risk_caps["sizing_balance_gbp"],
        "drawdown_pct": account_drawdown,
        "max_drawdown_pct": risk_caps["max_drawdown_pct"],
        "source_summary": source_summary,
        "signal_evidence": signal_evidence,
        "market_confirmation_policy": market_policy,
        "preference_policy": preference_policy,
        "invalidation_conditions": invalidation_conditions,
        "invalidation_condition_count": len(invalidation_conditions),
        "no_trade_conditions": no_trade_conditions,
        "no_trade_condition_count": len(no_trade_conditions),
        "risk_checks": checks,
        "risk_blockers": risk_blockers,
        "risk_blocker_count": len(risk_blockers),
        "risk_cautions": cautions,
        "risk_caution_count": len(cautions),
        "risk_score": _risk_score(
            source_summary=source_summary,
            signal_evidence=signal_evidence,
            risk_blockers=risk_blockers,
            caution_count=len(cautions),
        ),
        "next_required_stage": "Q5-4" if status == "eligible" else "Q5-3_repair",
        "next_required_action": (
            "Evaluate kill switches in Q5-4 before any execution intent or order staging."
            if status == "eligible"
            else "Repair evidence, market confirmation, pricing gap, or safety blockers before Q5-4."
        ),
        "risk_approval_allowed": False,
        "risk_approval_authority": False,
        "risk_agent_approval_authority": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "staged_paper_order_allowed": False,
        "staged_order_created": False,
        "paper_order_submission_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "broker_submit_receipt_created": False,
        "position_created": False,
        "live_capital_enabled": False,
    }
    review["validation_errors"] = validate_phase5_risk_sizing_review(review)
    return review


def _global_context_errors(
    *,
    approval_bundle: dict[str, Any],
    candidate_universe: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    approval_errors = validate_phase5_approval_policy_bundle(approval_bundle)
    candidate_errors = validate_candidate_strategy_universe(candidate_universe)
    if approval_errors:
        errors.append("approval_policy_bundle_validation_failed")
    if candidate_errors:
        errors.append("candidate_strategy_universe_validation_failed")
    if approval_bundle.get("status") != "ok":
        errors.append("approval_policy_bundle_not_ok")
    if approval_bundle.get("event_log_written") is not True:
        errors.append("approval_policy_event_log_not_written")
    if approval_bundle.get("decision_count") != len(approval_bundle.get("decisions", []) or []):
        errors.append("approval_policy_decision_count_mismatch")
    if approval_bundle.get("phase5_orchestration_start_allowed") is not False:
        errors.append("phase5_orchestration_start_allowed")
    if approval_bundle.get("preference_mcp_source_36") is not False:
        errors.append("preference_mcp_source_36")
    if approval_bundle.get("preference_paid_tools_allowed") is not False:
        errors.append("preference_paid_tools_allowed")
    if approval_bundle.get("preference_source_quorum_credit_allowed") is not False:
        errors.append("preference_source_quorum_credit_allowed")
    if approval_bundle.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_role_not_supplemental")
    if candidate_universe.get("trade_candidate_count") != 0:
        errors.append("candidate_universe_trade_candidate_count_not_zero")
    return sorted(dict.fromkeys(errors))


def build_phase5_risk_sizing_reviews(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    approval_bundle = _approval_policy_bundle(settings)
    candidate_universe = _candidate_universe(settings)
    account_context = paper_account_shadow_context(settings)
    signal_reviews = SignalIntegrityReviewStore(settings=settings).read(limit=300)
    candidates = _candidate_by_key(candidate_universe)
    global_errors = _global_context_errors(
        approval_bundle=approval_bundle,
        candidate_universe=candidate_universe,
    )
    reviews = [
        _risk_review(
            decision,
            candidate=candidates.get(str(decision.get("strategy_family_key") or "")),
            settings=settings,
            account_context=account_context,
            signal_reviews=signal_reviews,
            global_errors=global_errors,
        )
        for decision in _approval_decisions(approval_bundle)
    ]
    status_counts = Counter(str(review.get("status") or "unknown") for review in reviews)
    risk_decision_counts = Counter(str(review.get("risk_decision") or "unknown") for review in reviews)
    bundle = {
        "schema_version": PHASE5_RISK_SIZING_SCHEMA_VERSION,
        "artifact_type": "phase5_risk_sizing_review_bundle",
        "artifact_id": "phase5:q5-3:risk-sizing-reviews",
        "phase": "Q5",
        "stage": "Q5-3",
        "status": "ok",
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(RISK_SIZING_SOURCE_REFS),
        "boundary": RISK_SIZING_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "approval_policy_decision_count": int(approval_bundle.get("decision_count", 0) or 0),
        "approval_policy_eligible_count": int(approval_bundle.get("eligible_count", 0) or 0),
        "global_risk_errors": global_errors,
        "global_risk_error_count": len(global_errors),
        "risk_review_count": len(reviews),
        "eligible_count": status_counts.get("eligible", 0),
        "hold_count": status_counts.get("hold", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "paper_size_eligible_count": risk_decision_counts.get("paper_size_eligible", 0),
        "risk_decision_counts": dict(sorted(risk_decision_counts.items())),
        "max_risk_pct_per_idea": MAX_RISK_PCT_PER_IDEA,
        "max_drawdown_pct": MAX_DRAWDOWN_PCT,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "preference_source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "reviews": reviews,
    }
    for field in RISK_SIZING_COUNT_FIELDS:
        bundle[field] = 0
    bundle["validation_errors"] = validate_phase5_risk_sizing_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _risk_status_consistency_errors(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = str(review.get("status") or "missing")
    risk_decision = str(review.get("risk_decision") or "")
    blockers = review.get("risk_blockers", [])
    if not isinstance(blockers, list):
        errors.append("risk_blockers_not_list")
        blockers = []
    if review.get("risk_blocker_count") != len(blockers):
        errors.append("risk_blocker_count_mismatch")
    proposed_risk = _float(review.get("proposed_risk_gbp"), -1.0)
    proposed_risk_pct = _float(review.get("proposed_risk_pct"), -1.0)
    max_risk = _float(review.get("max_risk_gbp"), 0.0)
    max_risk_pct = _float(review.get("max_risk_pct"), 0.0)
    if proposed_risk < 0 or proposed_risk_pct < 0:
        errors.append("proposed_risk_negative")
    if proposed_risk > max_risk:
        errors.append("proposed_risk_above_cap")
    if proposed_risk_pct > max_risk_pct:
        errors.append("proposed_risk_pct_above_cap")
    if status == "eligible":
        if risk_decision != "paper_size_eligible":
            errors.append("eligible_risk_decision_not_paper_size_eligible")
        if blockers:
            errors.append("eligible_risk_review_has_blockers")
        if proposed_risk <= 0:
            errors.append("eligible_risk_review_without_positive_size")
        if review.get("paper_size_eligible") is not True:
            errors.append("eligible_risk_review_paper_size_flag_false")
        if review.get("approval_policy_status") != "eligible":
            errors.append("eligible_without_q5_2_policy")
        if review.get("approved_strategy_toggle_state") != "approved_shadow":
            errors.append("eligible_without_approved_shadow_toggle")
        if review.get("signal_evidence", {}).get("signal_integrity_passed") is not True:
            errors.append("eligible_without_signal_integrity_pass")
        if review.get("invalidation_condition_count", 0) < 1:
            errors.append("eligible_without_invalidation_conditions")
        if _float(review.get("drawdown_pct"), 0.0) > _float(review.get("max_drawdown_pct"), 0.0):
            errors.append("eligible_with_drawdown_above_cap")
    elif status == "blocked":
        if not risk_decision.startswith("blocked_"):
            errors.append("blocked_risk_decision_prefix_invalid")
        if not blockers:
            errors.append("blocked_risk_review_without_blockers")
        if proposed_risk != 0:
            errors.append("blocked_risk_review_has_size")
        if review.get("paper_size_eligible") is not False:
            errors.append("blocked_risk_review_paper_size_flag_true")
    elif status == "hold":
        if not risk_decision.startswith("hold_"):
            errors.append("hold_risk_decision_prefix_invalid")
        if proposed_risk != 0:
            errors.append("hold_risk_review_has_size")
    return errors


def validate_phase5_risk_sizing_review(review: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(review, expected_stage="Q5-3"))
    if review.get("artifact_type") != "risk_sizing_review":
        errors.append("artifact_type_not_risk_sizing_review")
    if review.get("risk_sizing_schema_version") != PHASE5_RISK_SIZING_SCHEMA_VERSION:
        errors.append("risk_sizing_schema_version_mismatch")
    if review.get("event_log_written") is True:
        if not str(review.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(review.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if review.get("yahoo_finance_role") not in (None, "supplemental_market_confirmation_only"):
        errors.append("yahoo_finance_role_not_supplemental")
    if review.get("preference_mcp_source_36") is True:
        errors.append("preference_mcp_source_36")
    if review.get("preference_paid_tools_allowed") is True:
        errors.append("preference_paid_tools_allowed")
    if review.get("preference_source_quorum_credit_allowed") is True:
        errors.append("preference_source_quorum_credit_allowed")
    if review.get("preference_only_confirmation_allowed") is True:
        errors.append("preference_only_confirmation_allowed")
    market_policy = review.get("market_confirmation_policy", {})
    if not isinstance(market_policy, dict):
        errors.append("market_confirmation_policy_invalid")
    else:
        if market_policy.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
            errors.append("market_yahoo_role_not_supplemental")
        if market_policy.get("yahoo_only_confirmation_allowed") is not False:
            errors.append("market_yahoo_only_confirmation_allowed")
    preference_policy = review.get("preference_policy", {})
    if not isinstance(preference_policy, dict):
        errors.append("preference_policy_invalid")
    else:
        if preference_policy.get("source_quorum_credit_allowed") is not False:
            errors.append("preference_policy_source_quorum_credit_allowed")
        if preference_policy.get("preference_only_confirmation_allowed") is not False:
            errors.append("preference_policy_only_confirmation_allowed")
        for field in ("risk_handoff_allowed", "execution_allowed", "paper_order_allowed", "broker_write_allowed"):
            if preference_policy.get(field) is not False:
                errors.append(f"preference_policy_authority_enabled:{field}")
    source_summary = review.get("source_summary", {})
    if not isinstance(source_summary, dict):
        errors.append("source_summary_invalid")
    else:
        coverage = source_summary.get("decision_source_coverage")
        review_status = str(review.get("status") or "")
        if source_summary.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
            errors.append("source_summary_canonical_source_count_mismatch")
        if source_summary.get("all_canonical_sources_considered") is not True:
            errors.append("source_summary_canonical_sources_not_considered")
        if (
            review_status == "eligible"
            and source_summary.get("decision_source_usage_complete") is not True
        ):
            errors.append("source_summary_decision_source_usage_incomplete")
        if source_summary.get("source_quorum_bypass_allowed") is not False:
            errors.append("source_summary_source_quorum_bypass_allowed")
        if not isinstance(coverage, dict):
            errors.append("source_summary_decision_source_coverage_missing")
        else:
            if coverage.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
                errors.append("source_summary_coverage_count_mismatch")
            if (
                review_status == "eligible"
                and coverage.get("decision_source_usage_complete") is not True
            ):
                errors.append("source_summary_coverage_usage_incomplete")
    for field in RISK_SIZING_BOUNDARY_FIELDS:
        if review.get(field) is not False:
            errors.append(f"risk_sizing_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if review.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    errors.extend(_risk_status_consistency_errors(review))
    return sorted(set(errors))


def validate_phase5_risk_sizing_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "risk_review_count",
        "eligible_count",
        "hold_count",
        "blocked_count",
        "reviews",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_RISK_SIZING_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_risk_sizing_review_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-3":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    reviews = bundle.get("reviews", [])
    if not isinstance(reviews, list):
        errors.append("reviews_not_list")
        reviews = []
    if bundle.get("risk_review_count") != len(reviews):
        errors.append("risk_review_count_mismatch")
    status_counts = Counter(str(review.get("status") or "unknown") for review in reviews)
    if bundle.get("eligible_count") != status_counts.get("eligible", 0):
        errors.append("eligible_count_mismatch")
    if bundle.get("hold_count") != status_counts.get("hold", 0):
        errors.append("hold_count_mismatch")
    if bundle.get("blocked_count") != status_counts.get("blocked", 0):
        errors.append("blocked_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(reviews):
            errors.append("bundle_event_log_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in RISK_SIZING_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    if bundle.get("preference_mcp_source_36") is not False:
        errors.append("bundle_preference_mcp_source_36")
    if bundle.get("preference_paid_tools_allowed") is not False:
        errors.append("bundle_preference_paid_tools_allowed")
    if bundle.get("preference_source_quorum_credit_allowed") is not False:
        errors.append("bundle_preference_source_quorum_credit_allowed")
    if bundle.get("preference_only_confirmation_allowed") is not False:
        errors.append("bundle_preference_only_confirmation_allowed")
    if bundle.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("bundle_yahoo_finance_role_not_supplemental")
    for review in reviews:
        errors.extend(validate_phase5_risk_sizing_review(review))
    return sorted(set(errors))


def attach_phase5_risk_sizing_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / RISK_SIZING_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for review in output.get("reviews", []):
        if not isinstance(review, dict):
            continue
        entry = log.write(
            RISK_SIZING_EVENT_TYPE,
            RISK_SIZING_COMPONENT,
            {
                "artifact_id": review.get("artifact_id"),
                "strategy_family_key": review.get("strategy_family_key"),
                "status": review.get("status"),
                "risk_decision": review.get("risk_decision"),
                "proposed_risk_gbp": review.get("proposed_risk_gbp"),
                "max_risk_gbp": review.get("max_risk_gbp"),
                "risk_blocker_count": review.get("risk_blocker_count"),
                "paper_size_eligible": review.get("paper_size_eligible"),
                "execution_allowed": review.get("execution_allowed"),
                "paper_order_allowed": review.get("paper_order_allowed"),
                "broker_write_allowed": review.get("broker_write_allowed"),
                "live_capital_enabled": review.get("live_capital_enabled"),
                "boundary": review.get("boundary"),
            },
        )
        review["event_log_written"] = True
        review["event_log_path"] = str(log.path)
        review["event_log_correlation_id"] = entry.correlation_id
        review["event_log_created_at"] = entry.created_at
        review["validation_errors"] = validate_phase5_risk_sizing_review(review)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_risk_sizing_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_risk_sizing_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / RISK_SIZING_RUNTIME_ARTIFACT,
        runtime / RISK_SIZING_HISTORY,
        runtime / RISK_SIZING_EVENT_LOG,
    )


def write_phase5_risk_sizing_reviews(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_risk_sizing_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_risk_sizing_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_risk_sizing_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_risk_sizing_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_RISK_SIZING_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "risk_review_count": output.get("risk_review_count"),
        "eligible_count": output.get("eligible_count"),
        "hold_count": output.get("hold_count"),
        "blocked_count": output.get("blocked_count"),
        "paper_size_eligible_count": output.get("paper_size_eligible_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
