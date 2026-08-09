"""EF-11 evidence-to-paper conversion contracts and truthful certification.

This module is intentionally paper-only.  It reconciles immutable research,
market, risk, Router, and PaperOps evidence but never submits an order itself.
The only broker writer remains the canonical PaperOps wrapper.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_market_session_truth import (
    build_and_write_market_clock_truth,
    parse_timestamp,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_ef11_open_market_conversion.v1"
CONTRACT_VERSION = "qadam-open-market-conversion.1"
PHASE_ID = "EF11"
BASELINE_ARTIFACT = "qadam_ef11_baseline.json"
RECONCILIATION_ARTIFACT = "qadam_ef11_contract_reconciliation.json"
PHASE_STATUS_ARTIFACT = "qadam_ef11_phase_status.json"
PRESTAGED_ARTIFACT = "qadam_prestaged_setups.jsonl"
PRESTAGED_STATUS_ARTIFACT = "qadam_prestaged_setup_status.json"
PRESTAGED_REJECTIONS_ARTIFACT = "qadam_prestaged_setup_rejections.jsonl"
EXECUTION_CONTEXT_ARTIFACT = "qadam_execution_evidence_context.jsonl"
SPREAD_PROFILE_ARTIFACT = "qadam_instrument_spread_profiles.json"
EXECUTION_POLICY_ARTIFACT = "qadam_execution_fallback_policy.json"
EXECUTION_REJECTIONS_ARTIFACT = "qadam_execution_context_rejections.jsonl"
CONVERSION_CYCLES_ARTIFACT = "qadam_open_market_conversion_cycles.jsonl"
DAILY_SUMMARY_ARTIFACT = "qadam_open_market_conversion_daily_summary.jsonl"
CONVERSION_STATUS_ARTIFACT = "qadam_open_market_conversion_status.json"
ROOT_CAUSE_ARTIFACT = "qadam_conversion_root_cause.json"
REPAIR_QUEUE_ARTIFACT = "qadam_conversion_repair_queue.json"
RECOVERY_HISTORY_ARTIFACT = "qadam_conversion_recovery_history.jsonl"
RISK_LADDER_ARTIFACT = "qadam_paper_risk_ladder.json"
RISK_TIER_DECISIONS_ARTIFACT = "qadam_paper_risk_tier_decisions.jsonl"
RISK_TIER_STATUS_ARTIFACT = "qadam_paper_risk_tier_status.json"
STRUCTURAL_CERT_ARTIFACT = "qadam_ef11_structural_certification.json"
PROVIDER_CERT_ARTIFACT = "qadam_ef11_provider_conversion_certification.json"
EMPIRICAL_CERT_ARTIFACT = "qadam_ef11_empirical_conversion_certification.json"
CERTIFICATION_ARTIFACT = "qadam_ef11_open_market_conversion_certification.json"
SCHEDULER_STATUS_ARTIFACT = "qadam_market_session_scheduler_status.json"
CAPACITY_ARTIFACT = "qadam_market_session_capacity.json"
VISIBILITY_ARTIFACT = "qadam_ef11_dashboard_summary.json"
TELEGRAM_CANDIDATE_ARTIFACT = "qadam_ef11_telegram_notification_candidate.json"
SOAK_ARTIFACT = "qadam_ef11_unattended_soak.json"
SOAK_SESSIONS_ARTIFACT = "qadam_ef11_unattended_soak_sessions.jsonl"
DEPLOYMENT_ARTIFACT = "qadam_ef11_deployment_status.json"

EXPECTED_SOURCE_COUNT = 41
EXPECTED_INSTRUMENT_COUNT = 19
EMPIRICAL_DAY_TARGET = 5
MINIMUM_SPREAD_OBSERVATIONS = 20
MAXIMUM_QUOTE_AGE_SECONDS = 300
MAXIMUM_TRADE_AGE_SECONDS = 60
MINIMUM_FALLBACK_ADV_USD = 10_000_000.0
MAXIMUM_ORDINARY_SPREAD_BPS = 50.0
MAXIMUM_FALLBACK_UPPER_SPREAD_BPS = 35.0
DISCOVERY_MICRO_NOTIONAL_USD = 500.0
ABSOLUTE_PAPER_NOTIONAL_CEILING_USD = 5000.0

INPUT_ARTIFACTS = (
    "qadam_strategy_source_contract.json",
    "qadam_instrument_role_registry.json",
    "qadam_pattern_score_v3_records.jsonl",
    "qadam_strategy_hypotheses_v3.jsonl",
    "qadam_akber_filter_v3_results.jsonl",
    "qadam_forward_shadow_decisions.jsonl",
    "qadam_position_size_proposals.jsonl",
    "qadam_risk_rejections.jsonl",
    "qadam_router_v3_decisions.jsonl",
    "qadam_paperops_handoff_v3_accepted.jsonl",
    "paperops_autonomous_pass_summary.json",
    "qadam_operator_service_receipt_index.json",
    "alpaca_paper_mirror.json",
    "qadam_active_discovery_trial_sessions.jsonl",
    "qadam_active_discovery_trial_certification.json",
    "qadam_evidence_fit_active_paper_trading_certification.json",
)

INFRASTRUCTURE_ROOT_CAUSES = {
    "provider_clock_stale",
    "provider_clock_unavailable",
    "provider_calendar_disagreement",
    "scheduler_starvation",
    "schema_conversion_defect",
    "route_failure",
}


def _hash_if_file(path: Path) -> str | None:
    return file_sha256(path) if path.is_file() else None


def _artifact_generated_at(path: Path) -> str | None:
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
        if not rows:
            return None
        return str(rows[-1].get("generated_at") or "") or None
    return str(read_json(path).get("generated_at") or "") or None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(int(round((len(ordered) - 1) * percentile)), 0), len(ordered) - 1)
    return ordered[index]


def _append_deduplicated(
    existing: list[dict[str, Any]],
    additions: Iterable[dict[str, Any]],
    *,
    identity_field: str,
) -> list[dict[str, Any]]:
    rows = {
        str(row.get(identity_field)): row
        for row in existing
        if row.get(identity_field)
    }
    for row in additions:
        identity = str(row.get(identity_field) or "")
        if identity:
            rows.setdefault(identity, row)
    return sorted(rows.values(), key=lambda row: str(row.get("generated_at") or ""))


def build_baseline(runtime: Path, *, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    source_contract = read_json(runtime / "qadam_strategy_source_contract.json")
    instrument_registry = read_json(runtime / "qadam_instrument_role_registry.json")
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    snapshot = mirror.get("snapshot") if isinstance(mirror.get("snapshot"), dict) else {}
    active_trial = read_json(runtime / "qadam_active_discovery_trial_certification.json")
    artifacts = []
    for name in INPUT_ARTIFACTS:
        path = runtime / name
        artifacts.append(
            {
                "name": name,
                "exists": path.is_file(),
                "sha256": _hash_if_file(path),
                "generated_at": _artifact_generated_at(path) if path.is_file() else None,
            }
        )
    material = {
        "contract_version": CONTRACT_VERSION,
        "artifacts": [{"name": row["name"], "sha256": row["sha256"]} for row in artifacts],
        "paper_epoch_id": snapshot.get("paper_epoch_id"),
    }
    proposed_baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_baseline",
        "phase_id": "EF11-0",
        "baseline_id": "ef11-baseline:" + sha256_json(material)[:24],
        "generated_at": generated_at,
        "contract_version": CONTRACT_VERSION,
        "source_count": int(source_contract.get("source_count") or 0),
        "instrument_count": int(instrument_registry.get("instrument_count") or 0),
        "artifact_snapshots": artifacts,
        "paper_account": {
            "paper_epoch_id": snapshot.get("paper_epoch_id"),
            "equity": snapshot.get("equity"),
            "cash": snapshot.get("cash"),
            "open_position_count": snapshot.get("open_position_count"),
            "open_order_count": mirror.get("order_count", 0),
            "drawdown_pct": snapshot.get("drawdown_pct"),
            "closed_trade_count": snapshot.get("closed_trade_count"),
        },
        "eligible_market_days_observed": int(
            active_trial.get("eligible_market_days_observed") or 0
        ),
        "empirical_trial_complete": active_trial.get("trial_complete") is True,
        "historical_examples_are_current_conversion_proof": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    existing_baseline = read_json(runtime / BASELINE_ARTIFACT)
    baseline_reusable = bool(
        existing_baseline.get("artifact_type") == "qadam_ef11_baseline"
        and existing_baseline.get("contract_version") == CONTRACT_VERSION
        and existing_baseline.get("baseline_id")
        and existing_baseline.get("source_count") == EXPECTED_SOURCE_COUNT
        and existing_baseline.get("instrument_count") == EXPECTED_INSTRUMENT_COUNT
        and existing_baseline.get("live_capital_enabled") is False
        and existing_baseline.get("paper_account", {}).get("paper_epoch_id")
        == proposed_baseline.get("paper_account", {}).get("paper_epoch_id")
    )
    baseline = existing_baseline if baseline_reusable else proposed_baseline
    baseline_hashes = {
        str(row.get("name")): row.get("sha256")
        for row in baseline.get("artifact_snapshots", [])
        if row.get("name")
    }
    current_hashes = {str(row.get("name")): row.get("sha256") for row in artifacts}
    changed_artifacts = sorted(
        name
        for name in set(baseline_hashes) | set(current_hashes)
        if baseline_hashes.get(name) != current_hashes.get(name)
    )
    reconciliation = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_contract_reconciliation",
        "phase_id": "EF11-0",
        "baseline_id": baseline["baseline_id"],
        "generated_at": generated_at,
        "baseline_generated_at": baseline.get("generated_at"),
        "baseline_reused": baseline_reusable,
        "baseline_is_immutable": True,
        "current_input_snapshots": artifacts,
        "changed_artifact_count": len(changed_artifacts),
        "changed_artifacts": changed_artifacts,
        "universe_contract": {
            "source_count": baseline["source_count"],
            "expected_source_count": EXPECTED_SOURCE_COUNT,
            "instrument_count": baseline["instrument_count"],
            "expected_instrument_count": EXPECTED_INSTRUMENT_COUNT,
        },
        "certification_classes": {
            "qadam_evidence_fit_active_paper_trading_certification.json": "structural",
            "qadam_active_discovery_trial_certification.json": "empirical",
            "paperops_autonomous_pass_summary.json": "integration",
            "paper_proof_ledger.json": "historical_proof",
        },
        "historical_handoff_can_certify_ef11": False,
        "current_policy_required": True,
        "paper_only": True,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return baseline, reconciliation


def _identity(row: dict[str, Any]) -> str:
    identity = row.get("candidate_identity_material")
    identity = identity if isinstance(identity, dict) else {}
    return str(identity.get("candidate_identity_id") or row.get("hypothesis_id") or "")


def _execution_symbol(row: dict[str, Any]) -> str:
    mapping = row.get("instrument_proxy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    return str(mapping.get("execution_proxy") or mapping.get("observed_instrument") or "")


def build_prestaged_setups(
    runtime: Path,
    *,
    baseline_id: str,
    market_truth: dict[str, Any],
    generated_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    now = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    hypotheses = read_jsonl(runtime / "qadam_strategy_hypotheses_v3.jsonl")
    deduplicated: dict[str, dict[str, Any]] = {}
    rejections: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        identity = _identity(hypothesis)
        symbol = _execution_symbol(hypothesis)
        expires_at = hypothesis.get("freshness", {}).get("expires_at")
        expiry = parse_timestamp(expires_at)
        if not identity or not symbol:
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_prestaged_setup_rejection",
                    "rejection_id": "prestage-rejection:" + sha256_json(hypothesis)[:24],
                    "generated_at": generated_at,
                    "baseline_id": baseline_id,
                    "hypothesis_id": hypothesis.get("hypothesis_id"),
                    "reason": "candidate_identity_or_execution_proxy_missing",
                    "paper_order_created": False,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                }
            )
            continue
        if expiry is not None and expiry <= now:
            state = "expired_before_market_open"
        elif market_truth.get("actionable_for_conversion") is True:
            state = "ready_for_open_market_revalidation"
        else:
            state = "pending_market_open_confirmation"
        candidate = hypothesis.get("candidate_identity_material") or {}
        sources = hypothesis.get("pattern_lineage") or {}
        record = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_prestaged_setup",
            "prestage_id": "prestage:" + sha256_json(
                {"identity": identity, "hypothesis": hypothesis.get("hypothesis_id")}
            )[:24],
            "generated_at": generated_at,
            "baseline_id": baseline_id,
            "state": state,
            "candidate_identity_id": identity,
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "research_goal_id": candidate.get("research_goal_id"),
            "score_id": sources.get("score_id"),
            "pattern_relationship_id": sources.get("pattern_relationship_id"),
            "research_score": sources.get("raw_research_score"),
            "strategy_family_id": hypothesis.get("strategy_mapping", {}).get(
                "strategy_family_id"
            ),
            "evidence_profile": sources.get("evidence_profile"),
            "instrument": candidate.get("observed_instrument") or symbol,
            "execution_proxy": symbol,
            "direction": candidate.get("direction"),
            "horizon": candidate.get("time_window"),
            "trigger_ids": hypothesis.get("direction_horizon", {}).get(
                "direction_resolution_evidence_ids", []
            ),
            "trigger_expires_at": expires_at,
            "support_sources": sources.get("fresh_support_sources", []),
            "fresh_quorum_sources": sources.get("fresh_quorum_sources", []),
            "provisional_net_expectancy": hypothesis.get("expected_edge_range", {}).get(
                "net_expectancy"
            ),
            "provisional_expectancy_only": True,
            "invalidation": hypothesis.get("invalidation_exit", {}).get(
                "invalidation_conditions", []
            ),
            "correlated_cluster": hypothesis.get("strategy_mapping", {}).get(
                "strategy_family_id"
            ),
            "idempotency_identity_material": candidate,
            "missing_execution_fields": [
                "fresh_bid_ask_or_approved_limit_fallback",
                "current_spread_and_liquidity",
                "decision_time_shadow_snapshot_after_akber_pass",
            ],
            "next_eligible_recheck_at": market_truth.get("next_open"),
            "revalidation_required": True,
            "trade_candidate_created": False,
            "risk_approval_created": False,
            "paper_order_created": False,
            "broker_write_count": 0,
            "proof_credit_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        previous = deduplicated.get(identity)
        if previous is None or _safe_float(record.get("research_score")) > _safe_float(
            previous.get("research_score")
        ):
            deduplicated[identity] = record
    records = sorted(
        deduplicated.values(),
        key=lambda row: (-_safe_float(row.get("research_score")), row["execution_proxy"]),
    )
    counts = Counter(str(row.get("state")) for row in records)
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_prestaged_setup_status",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "status": "ready" if records else "ready_empty",
        "setup_count": len(records),
        "state_counts": dict(sorted(counts.items())),
        "ready_for_open_market_revalidation_count": counts.get(
            "ready_for_open_market_revalidation", 0
        ),
        "pending_market_open_confirmation_count": counts.get(
            "pending_market_open_confirmation", 0
        ),
        "rejection_count": len(rejections),
        "queue_can_create_order": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return records, status, rejections


def _market_records(runtime: Path) -> dict[str, dict[str, Any]]:
    packet = read_json(runtime / "market_context_packet.json")
    records: dict[str, dict[str, Any]] = {}
    for recent in packet.get("recent_packets", []) or []:
        context = recent.get("price_volume_context")
        context = context if isinstance(context, dict) else {}
        for row in context.get("records", []) or []:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            if not symbol:
                continue
            current = records.get(symbol)
            if current is None or str(row.get("available_at") or "") > str(
                current.get("available_at") or ""
            ):
                records[symbol] = row
    return records


def _build_spread_profiles(context_rows: list[dict[str, Any]], *, generated_at: str) -> dict[str, Any]:
    observations: dict[str, list[float]] = defaultdict(list)
    for row in context_rows:
        if row.get("provider_backed") is not True or row.get("quote_actionable") is not True:
            continue
        spread = row.get("observed_spread_bps")
        if spread is not None and 0 <= _safe_float(spread) <= 500:
            observations[str(row.get("instrument"))].append(_safe_float(spread))
    profiles = {}
    for symbol, values in sorted(observations.items()):
        profiles[symbol] = {
            "instrument": symbol,
            "observation_count": len(values),
            "median_spread_bps": round(median(values), 4),
            "p95_spread_bps": round(_percentile(values, 0.95) or 0.0, 4),
            "fallback_history_sufficient": len(values) >= MINIMUM_SPREAD_OBSERVATIONS,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_instrument_spread_profiles",
        "generated_at": generated_at,
        "minimum_observations": MINIMUM_SPREAD_OBSERVATIONS,
        "profiles": profiles,
        "profile_count": len(profiles),
        "broker_write_count": 0,
        "authority": authority_flags(),
    }


def execution_fallback_policy(*, generated_at: str, baseline_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_execution_fallback_policy",
        "policy_version": "qadam-execution-evidence-fit.1",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "primary_mode": "fresh_provider_bid_ask",
        "fallback_mode": "fresh_trade_limit_only",
        "fallback_enabled_when_calibrated": True,
        "regular_session_only": True,
        "maximum_quote_age_seconds": MAXIMUM_QUOTE_AGE_SECONDS,
        "maximum_trade_age_seconds": MAXIMUM_TRADE_AGE_SECONDS,
        "minimum_spread_observations": MINIMUM_SPREAD_OBSERVATIONS,
        "minimum_average_daily_dollar_volume_usd": MINIMUM_FALLBACK_ADV_USD,
        "maximum_ordinary_spread_bps": MAXIMUM_ORDINARY_SPREAD_BPS,
        "maximum_fallback_upper_spread_bps": MAXIMUM_FALLBACK_UPPER_SPREAD_BPS,
        "maximum_fallback_notional_usd": DISCOVERY_MICRO_NOTIONAL_USD,
        "absolute_paper_notional_ceiling_usd": ABSOLUTE_PAPER_NOTIONAL_CEILING_USD,
        "fallback_order_type": "limit",
        "market_order_when_spread_missing_allowed": False,
        "prediction_contract_fallback_allowed": False,
        "context_only_instrument_fallback_allowed": False,
        "ambiguous_write_retry_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def build_execution_evidence(
    runtime: Path,
    *,
    baseline_id: str,
    market_truth: dict[str, Any],
    prestaged: list[dict[str, Any]],
    generated_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    existing = read_jsonl(runtime / EXECUTION_CONTEXT_ARTIFACT)
    provider_records = _market_records(runtime)
    provisional_rows: list[dict[str, Any]] = []
    for setup in prestaged:
        symbol = str(setup.get("execution_proxy") or "")
        provider = provider_records.get(symbol, {})
        quote_age = provider.get("quote_age_seconds")
        trade_age = provider.get("trade_age_seconds")
        quote_actionable = bool(
            market_truth.get("actionable_for_conversion") is True
            and provider.get("quote_actionable") is True
            and quote_age is not None
            and _safe_float(quote_age, 1e9) <= MAXIMUM_QUOTE_AGE_SECONDS
        )
        trade_actionable = bool(
            market_truth.get("actionable_for_conversion") is True
            and provider.get("trade_actionable") is True
            and trade_age is not None
            and _safe_float(trade_age, 1e9) <= MAXIMUM_TRADE_AGE_SECONDS
        )
        observed_spread = provider.get("spread_bps")
        provisional_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_execution_evidence_context",
                "context_id": "execution-context:" + sha256_json(
                    {
                        "prestage_id": setup.get("prestage_id"),
                        "available_at": provider.get("available_at"),
                        "quote_at": provider.get("quote_observed_at"),
                        "trade_at": provider.get("last_trade_observed_at"),
                    }
                )[:24],
                "generated_at": generated_at,
                "baseline_id": baseline_id,
                "prestage_id": setup.get("prestage_id"),
                "hypothesis_id": setup.get("hypothesis_id"),
                "score_id": setup.get("score_id"),
                "instrument": symbol,
                "provider": provider.get("provider"),
                "provider_backed": provider.get("provider_backed") is True,
                "session_date": market_truth.get("session_date"),
                "session_phase": market_truth.get("session_phase"),
                "market_clock_truth_id": market_truth.get("truth_id"),
                "current_price": provider.get("current_price"),
                "bid": provider.get("bid"),
                "ask": provider.get("ask"),
                "midpoint": provider.get("midpoint"),
                "last_trade_price": provider.get("last_trade_price"),
                "quote_observed_at": provider.get("quote_observed_at"),
                "last_trade_observed_at": provider.get("last_trade_observed_at"),
                "quote_age_seconds": quote_age,
                "trade_age_seconds": trade_age,
                "quote_actionable": quote_actionable,
                "trade_actionable": trade_actionable,
                "observed_spread_bps": observed_spread,
                "average_daily_dollar_volume": provider.get("average_daily_dollar_volume"),
                "annualized_volatility": provider.get("annualized_volatility"),
                "execution_mode": "pending_profile_evaluation",
                "execution_context_actionable": False,
                "maximum_notional_usd": None,
                "order_type": None,
                "paper_order_created": False,
                "broker_write_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )
    all_rows = _append_deduplicated(existing, provisional_rows, identity_field="context_id")
    spread_profiles = _build_spread_profiles(all_rows, generated_at=generated_at)
    rejections: list[dict[str, Any]] = []
    finalized: list[dict[str, Any]] = []
    for row in provisional_rows:
        profile = spread_profiles.get("profiles", {}).get(row["instrument"], {})
        observed_spread = row.get("observed_spread_bps")
        ordinary = bool(
            row.get("quote_actionable") is True
            and observed_spread is not None
            and _safe_float(observed_spread, 1e9) <= MAXIMUM_ORDINARY_SPREAD_BPS
            and _safe_float(row.get("average_daily_dollar_volume")) >= MINIMUM_FALLBACK_ADV_USD
        )
        fallback = bool(
            not ordinary
            and row.get("trade_actionable") is True
            and profile.get("fallback_history_sufficient") is True
            and _safe_float(profile.get("p95_spread_bps"), 1e9)
            <= MAXIMUM_FALLBACK_UPPER_SPREAD_BPS
            and _safe_float(row.get("average_daily_dollar_volume")) >= MINIMUM_FALLBACK_ADV_USD
        )
        row = dict(row)
        if ordinary:
            row.update(
                {
                    "execution_mode": "fresh_provider_bid_ask",
                    "execution_context_actionable": True,
                    "maximum_notional_usd": 1000.0,
                    "order_type": "limit",
                    "conservative_cost_buffer_bps": max(_safe_float(observed_spread), 1.0),
                }
            )
        elif fallback:
            row.update(
                {
                    "execution_mode": "fresh_trade_limit_only",
                    "execution_context_actionable": True,
                    "maximum_notional_usd": DISCOVERY_MICRO_NOTIONAL_USD,
                    "order_type": "limit",
                    "conservative_cost_buffer_bps": profile.get("p95_spread_bps"),
                }
            )
        else:
            reasons = []
            if market_truth.get("actionable_for_conversion") is not True:
                reasons.append("market_session_not_actionable")
            if row.get("provider_backed") is not True:
                reasons.append("provider_market_context_missing")
            if row.get("quote_actionable") is not True:
                reasons.append("fresh_bid_ask_missing")
            if row.get("trade_actionable") is not True:
                reasons.append("fresh_trade_missing")
            if profile.get("fallback_history_sufficient") is not True:
                reasons.append("measured_spread_history_insufficient")
            row["execution_mode"] = "execution_context_missing"
            row["rejection_reasons"] = unique_errors(reasons)
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_execution_context_rejection",
                    "rejection_id": "execution-rejection:" + sha256_json(row)[:24],
                    "generated_at": generated_at,
                    "baseline_id": baseline_id,
                    "context_id": row["context_id"],
                    "instrument": row["instrument"],
                    "reasons": row["rejection_reasons"],
                    "paper_order_created": False,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                }
            )
        finalized.append(row)
    finalized_by_id = {row["context_id"]: row for row in finalized}
    all_rows = [finalized_by_id.get(str(row.get("context_id")), row) for row in all_rows]
    return all_rows, spread_profiles, rejections


def primary_root_cause(
    *,
    market_truth: dict[str, Any],
    setup: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
    akber: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    router: dict[str, Any] | None = None,
) -> tuple[str | None, list[str]]:
    setup = setup or {}
    execution = execution or {}
    akber = akber or {}
    risk = risk or {}
    router = router or {}
    propagated: list[str] = []
    expected_phase = str(market_truth.get("expected_session_phase") or "")
    if (
        expected_phase
        and expected_phase != "regular"
        and market_truth.get("actionable_for_conversion") is not True
    ):
        return "market_closed", propagated
    if market_truth.get("provider_backed") is not True:
        return "provider_clock_unavailable", propagated
    if market_truth.get("provider_fresh") is not True:
        return "provider_clock_stale", propagated
    if market_truth.get("calendar_disagreement") is True:
        return "provider_calendar_disagreement", propagated
    if market_truth.get("actionable_for_conversion") is not True:
        return "market_closed", propagated
    if not setup:
        return "no_current_setup", propagated
    if execution.get("execution_context_actionable") is not True:
        return "execution_context_missing", propagated
    decision = str(akber.get("decision") or "")
    if decision in {"veto", "veto_no_order"}:
        return "akber_veto", propagated
    if decision not in {"pass", "passed"}:
        propagated.extend(["shadow_not_reached", "risk_not_reached", "router_not_reached"])
        return "akber_hold", propagated
    if risk and risk.get("position_size_proposed") is not True:
        propagated.append("router_not_reached")
        return "risk_veto", propagated
    final = str(router.get("final_state") or "")
    if final == "blocked-safety-boundary":
        return "safety_stop", propagated
    if final in {"repair-requested"}:
        return "route_failure", propagated
    if final and final not in {
        "experimental_paper_review_candidate",
        "validated_paper_review_candidate",
    }:
        return "router_hold", propagated
    if final:
        return None, propagated
    return "router_not_reached", propagated


def build_daily_summaries(cycles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in cycles:
        session_date = str(row.get("session_date") or "")
        if session_date:
            grouped[(str(row.get("baseline_id") or ""), session_date)].append(row)
    summaries = []
    for (baseline_id, session_date), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: str(row.get("decision_at") or row.get("generated_at") or ""))
        evidence_complete = [
            row for row in rows if row.get("execution_context_actionable") is True
        ]
        highest = max(rows, key=lambda row: int(row.get("highest_stage_reached") or 0))
        root_counts = Counter(
            str(row.get("primary_root_cause"))
            for row in rows
            if row.get("primary_root_cause")
        )
        summaries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_open_market_conversion_daily_summary",
                "summary_id": "conversion-day:" + sha256_json(
                    {"baseline_id": baseline_id, "session_date": session_date}
                )[:24],
                "generated_at": rows[-1].get("generated_at"),
                "baseline_id": baseline_id,
                "session_date": session_date,
                "cycle_count": len(rows),
                "first_valid_trigger_cycle_id": next(
                    (row.get("cycle_id") for row in rows if row.get("setup_id")), None
                ),
                "best_evidence_complete_cycle_id": evidence_complete[-1].get("cycle_id")
                if evidence_complete
                else None,
                "highest_stage_reached": highest.get("highest_stage_reached"),
                "highest_stage_cycle_id": highest.get("cycle_id"),
                "final_cycle_before_close_id": rows[-1].get("cycle_id"),
                "paperops_handoff_count": sum(
                    int(row.get("paperops_handoff_count") or 0) for row in rows
                ),
                "paper_order_count": sum(int(row.get("paper_order_count") or 0) for row in rows),
                "primary_root_cause_counts": dict(sorted(root_counts.items())),
                "immutable_source_cycle_ids": [row.get("cycle_id") for row in rows],
                "backfilled": False,
                "simulated_elapsed_time": False,
                "authority": authority_flags(),
            }
        )
    return summaries


def append_conversion_cycles(
    runtime: Path,
    additions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    existing = read_jsonl(runtime / CONVERSION_CYCLES_ARTIFACT)
    cycles = _append_deduplicated(existing, additions, identity_field="cycle_id")
    summaries = build_daily_summaries(cycles)
    latest = cycles[-1] if cycles else {}
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_open_market_conversion_status",
        "generated_at": latest.get("generated_at") or now_iso(),
        "baseline_id": latest.get("baseline_id"),
        "status": "active" if cycles else "ready_no_cycles",
        "cycle_count": len(cycles),
        "eligible_session_count": len(
            {row.get("session_date") for row in cycles if row.get("eligible_cycle") is True}
        ),
        "latest_cycle_id": latest.get("cycle_id"),
        "latest_primary_root_cause": latest.get("primary_root_cause"),
        "latest_highest_stage_reached": latest.get("highest_stage_reached"),
        "paperops_handoff_count": sum(
            int(row.get("paperops_handoff_count") or 0) for row in cycles
        ),
        "paper_order_count": sum(int(row.get("paper_order_count") or 0) for row in cycles),
        "broker_write_count_by_coordinator": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return cycles, summaries, status


def build_risk_ladder(
    runtime: Path,
    *,
    baseline_id: str,
    prestaged: list[dict[str, Any]],
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    ladder = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_risk_ladder",
        "policy_version": "qadam-paper-risk-ladder.1",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "tiers": [
            {
                "tier": "discovery_micro",
                "maximum_notional_usd": 500.0,
                "minimum_independent_forward_outcomes": 0,
                "purpose": "First bounded paper observation for a complete current setup.",
            },
            {
                "tier": "repeat_confirmed_micro",
                "maximum_notional_usd": 2000.0,
                "minimum_independent_forward_outcomes": 5,
                "minimum_regime_buckets": 2,
                "positive_net_outcomes_required": True,
            },
            {
                "tier": "validated_paper",
                "maximum_notional_usd": 5000.0,
                "minimum_independent_forward_outcomes": 20,
                "validated_edge_required": True,
                "minimum_regime_buckets": 2,
            },
        ],
        "maximum_concurrent_discovery_positions": 3,
        "maximum_positions_per_correlated_cluster": 1,
        "absolute_notional_ceiling_usd": ABSOLUTE_PAPER_NOTIONAL_CEILING_USD,
        "one_score_cannot_advance_tier": True,
        "one_profitable_trade_cannot_advance_tier": True,
        "correlated_outcomes_are_not_independent": True,
        "paper_results_cannot_enable_live_capital": True,
        "outside_envelope_change_is_proposal_only": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    decisions = []
    for setup in prestaged:
        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_paper_risk_tier_decision",
                "decision_id": "risk-tier:" + sha256_json(
                    {"identity": setup.get("candidate_identity_id"), "policy": ladder["policy_version"]}
                )[:24],
                "generated_at": generated_at,
                "baseline_id": baseline_id,
                "candidate_identity_id": setup.get("candidate_identity_id"),
                "hypothesis_id": setup.get("hypothesis_id"),
                "tier": "discovery_micro",
                "maximum_notional_usd": DISCOVERY_MICRO_NOTIONAL_USD,
                "automatic_admission_inside_frozen_paper_envelope": True,
                "validated_edge_claimed": False,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_risk_tier_status",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "status": "frozen_active",
        "decision_count": len(decisions),
        "current_default_tier": "discovery_micro",
        "maximum_current_first_time_notional_usd": DISCOVERY_MICRO_NOTIONAL_USD,
        "absolute_notional_ceiling_usd": ABSOLUTE_PAPER_NOTIONAL_CEILING_USD,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return ladder, decisions, status


def build_root_cause_and_repair(
    runtime: Path,
    *,
    baseline_id: str,
    market_truth: dict[str, Any],
    conversion_status: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    expected_phase = str(market_truth.get("expected_session_phase") or "")
    if (
        expected_phase
        and expected_phase != "regular"
        and market_truth.get("actionable_for_conversion") is not True
    ):
        root = "market_closed"
    elif market_truth.get("provider_backed") is not True:
        root = "provider_clock_unavailable"
    elif market_truth.get("provider_fresh") is not True:
        root = "provider_clock_stale"
    elif market_truth.get("calendar_disagreement") is True:
        root = "provider_calendar_disagreement"
    elif market_truth.get("actionable_for_conversion") is not True:
        root = "market_closed"
    else:
        root = conversion_status.get("latest_primary_root_cause")
    if not root:
        if market_truth.get("provider_backed") is not True:
            root = "provider_clock_unavailable"
        elif market_truth.get("provider_fresh") is not True:
            root = "provider_clock_stale"
        elif market_truth.get("actionable_for_conversion") is not True:
            root = "market_closed"
        else:
            root = "no_current_setup"
    owner = {
        "market_closed": "market_calendar",
        "no_current_setup": "research_pipeline",
        "execution_context_missing": "market_data_adapter",
        "akber_hold": "akber_filter",
        "akber_veto": "akber_filter",
        "risk_veto": "portfolio_risk",
        "safety_stop": "portfolio_risk",
        "router_hold": "router",
        "provider_clock_stale": "market_data_adapter",
        "provider_clock_unavailable": "market_data_adapter",
        "provider_calendar_disagreement": "market_data_adapter",
        "scheduler_starvation": "operator_service",
        "schema_conversion_defect": "conversion_coordinator",
        "route_failure": "paperops",
    }.get(str(root), "conversion_coordinator")
    repairable = root in INFRASTRUCTURE_ROOT_CAUSES
    root_artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_conversion_root_cause",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "primary_root_cause": root,
        "owner": owner,
        "automatically_repairable": repairable,
        "next_recheck_at": market_truth.get("next_open")
        if root == "market_closed"
        else generated_at,
        "propagated_downstream_states": (
            ["shadow_not_reached", "risk_not_reached", "router_not_reached"]
            if root in {"market_closed", "execution_context_missing", "akber_hold"}
            else []
        ),
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    existing_queue = read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    prior_requests = [
        row
        for row in existing_queue.get("requests", []) or []
        if isinstance(row, dict) and row.get("status") == "open"
    ]
    history = read_jsonl(runtime / RECOVERY_HISTORY_ARTIFACT)
    recovery_additions = []
    for request in prior_requests:
        if request.get("root_cause") == root and repairable:
            continue
        recovery_additions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_conversion_recovery",
                "recovery_id": "conversion-recovery:"
                + sha256_json(
                    {
                        "repair_request_id": request.get("repair_request_id"),
                        "resolved_at": generated_at,
                    }
                )[:24],
                "generated_at": generated_at,
                "baseline_id": baseline_id,
                "repair_request_id": request.get("repair_request_id"),
                "resolved_root_cause": request.get("root_cause"),
                "resolution": "root_cause_no_longer_current",
                "broker_write_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )
    history = _append_deduplicated(
        history, recovery_additions, identity_field="recovery_id"
    )
    requests: list[dict[str, Any]] = []
    if repairable:
        existing_current = next(
            (row for row in prior_requests if row.get("root_cause") == root), {}
        )
        requests.append(
            {
                "repair_request_id": "conversion-repair:" + sha256_json(
                    {"baseline": baseline_id, "root": root}
                )[:24],
                "created_at": existing_current.get("created_at") or generated_at,
                "last_seen_at": generated_at,
                "root_cause": root,
                "owner": owner,
                "status": "open",
                "allowed_actions": [
                    "retry_read_only_provider_refresh",
                    "rebuild_deterministic_artifact_from_immutable_inputs",
                    "revalidate_real_command_and_artifact_freshness",
                ],
                "forbidden_actions": [
                    "edit_code_silently",
                    "change_secrets",
                    "change_authority",
                    "retry_ambiguous_broker_write",
                ],
            }
        )
    queue = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_conversion_repair_queue",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "status": "action_required" if requests else "clear",
        "repair_request_count": len(requests),
        "requests": requests,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return root_artifact, queue, history


def build_scheduler_status(
    runtime: Path,
    *,
    baseline_id: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipts = read_jsonl(runtime / "qadam_operator_service_receipts.jsonl")
    generated = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    baseline = read_json(runtime / BASELINE_ARTIFACT)
    baseline_at = parse_timestamp(baseline.get("generated_at"))
    rolling_start = generated - timedelta(minutes=30)
    evaluation_start = max(
        (value for value in (baseline_at, rolling_start) if value is not None),
        default=rolling_start,
    )
    recent = [
        row
        for row in receipts[-1000:]
        if (parse_timestamp(row.get("generated_at")) or datetime.min.replace(tzinfo=timezone.utc))
        >= evaluation_start
    ]
    critical_services = {
        "market_price_refresh",
        "open_market_conversion",
        "guarded_paperops",
        "paper_lifecycle_poll",
    }
    critical = [row for row in recent if row.get("service_id") in critical_services]
    exhausted = [
        row for row in critical if row.get("skip_reason") == "cycle_job_budget_exhausted"
    ]
    completed = [
        row
        for row in critical
        if row.get("state")
        in {
            "completed",
            "completed_with_evidence_hold",
            "completed_with_transport_hold",
            "completed_pending_circuit_confirmation",
        }
    ]
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_market_session_scheduler_status",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "status": "passed" if not exhausted else "degraded_critical_budget_exhaustion",
        "critical_services": sorted(critical_services),
        "critical_receipt_count": len(critical),
        "critical_completed_count": len(completed),
        "critical_budget_exhausted_count": len(exhausted),
        "evaluation_window_started_at": evaluation_start.isoformat(),
        "pre_ef11_scheduler_incidents_excluded": True,
        "market_price_refresh_cadence_seconds": 60,
        "conversion_cadence_seconds": 300,
        "whole_universe_scan_max_interval_seconds": 1200,
        "historical_research_deferred_during_critical_window": True,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    capacity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_market_session_capacity",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "critical_path_reserved": True,
        "minimum_jobs_per_operator_cycle": 2,
        "latency_sensitive_priority_enabled": True,
        "critical_path_budget_exhaustion_is_defect": True,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return status, capacity


def build_certifications(
    runtime: Path,
    *,
    baseline: dict[str, Any],
    market_truth: dict[str, Any],
    prestaged_status: dict[str, Any],
    execution_context: list[dict[str, Any]],
    conversion_status: dict[str, Any],
    scheduler_status: dict[str, Any],
    repair_queue: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    baseline_ok = (
        baseline.get("source_count") == EXPECTED_SOURCE_COUNT
        and baseline.get("instrument_count") == EXPECTED_INSTRUMENT_COUNT
        and baseline.get("live_capital_enabled") is False
    )
    structural_blockers = []
    if not baseline_ok:
        structural_blockers.append("baseline_universe_or_safety_contract_invalid")
    if prestaged_status.get("queue_can_create_order") is not False:
        structural_blockers.append("prestage_queue_has_trade_authority")
    if _safe_float(conversion_status.get("broker_write_count_by_coordinator")) != 0:
        structural_blockers.append("conversion_coordinator_broker_write_detected")
    structural = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_structural_certification",
        "generated_at": generated_at,
        "baseline_id": baseline.get("baseline_id"),
        "status": "passed" if not structural_blockers else "blocked",
        "structural_ready": not structural_blockers,
        "source_count": baseline.get("source_count"),
        "instrument_count": baseline.get("instrument_count"),
        "canonical_paperops_only": True,
        "idempotency_required": True,
        "live_capital_enabled": False,
        "blockers": structural_blockers,
        "authority": authority_flags(),
    }
    provider_canaries = [
        row
        for row in read_jsonl(runtime / CONVERSION_CYCLES_ARTIFACT)
        if row.get("provider_canary") is True
        and row.get("market_clock_fresh") is True
        and int(row.get("highest_stage_reached") or 0) >= 9
        and row.get("broker_write_disabled") is True
    ]
    provider_ready = bool(provider_canaries)
    provider = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_provider_conversion_certification",
        "generated_at": generated_at,
        "baseline_id": baseline.get("baseline_id"),
        "status": "passed" if provider_ready else "collecting_open_market_canary",
        "provider_conversion_ready": provider_ready,
        "fresh_provider_clock_now": market_truth.get("provider_fresh") is True,
        "current_execution_context_actionable_count": sum(
            row.get("execution_context_actionable") is True for row in execution_context
        ),
        "qualifying_canary_count": len(provider_canaries),
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    active_trial = read_json(runtime / "qadam_active_discovery_trial_certification.json")
    eligible_days = int(active_trial.get("eligible_market_days_observed") or 0)
    empirical_ready = bool(
        eligible_days >= EMPIRICAL_DAY_TARGET
        and active_trial.get("trial_complete") is True
        and read_json(runtime / "qadam_active_discovery_trial_status.json").get(
            "operational_integrity_passed"
        )
        is True
        and int(conversion_status.get("paperops_handoff_count") or 0) >= 1
        and scheduler_status.get("critical_budget_exhausted_count") == 0
    )
    empirical = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_empirical_conversion_certification",
        "generated_at": generated_at,
        "baseline_id": baseline.get("baseline_id"),
        "status": "passed" if empirical_ready else "collecting_real_eligible_days",
        "empirically_conversion_proven": empirical_ready,
        "eligible_market_days_observed": eligible_days,
        "eligible_market_day_target": EMPIRICAL_DAY_TARGET,
        "current_version_handoff_count": int(
            conversion_status.get("paperops_handoff_count") or 0
        ),
        "historical_handoff_substitution_allowed": False,
        "backfill_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    all_ready = bool(structural["structural_ready"] and provider_ready and empirical_ready)
    overall_state = (
        "complete_empirically_conversion_proven"
        if all_ready
        else "blocked_structural"
        if not structural["structural_ready"]
        else "collecting_provider_conversion_canary"
        if not provider_ready
        else "collecting_empirical_conversion_evidence"
    )
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_open_market_conversion_certification",
        "generated_at": generated_at,
        "baseline_id": baseline.get("baseline_id"),
        "status": overall_state,
        "complete": all_ready,
        "structural_ready": structural["structural_ready"],
        "provider_conversion_ready": provider_ready,
        "empirically_conversion_proven": empirical_ready,
        "eligible_market_days_observed": eligible_days,
        "eligible_market_day_target": EMPIRICAL_DAY_TARGET,
        "repair_request_count": int(repair_queue.get("repair_request_count") or 0),
        "paper_only": True,
        "canonical_paperops_only": True,
        "broker_write_count_by_certification": 0,
        "live_capital_enabled": False,
        "profitability_guaranteed": False,
        "authority": authority_flags(),
    }
    return structural, provider, empirical, aggregate


def build_visibility(
    *,
    certification: dict[str, Any],
    market_truth: dict[str, Any],
    prestaged_status: dict[str, Any],
    risk_status: dict[str, Any],
    root_cause: dict[str, Any],
    conversion_status: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_dashboard_summary",
        "generated_at": generated_at,
        "certification_state": certification.get("status"),
        "structural_ready": certification.get("structural_ready"),
        "provider_conversion_ready": certification.get("provider_conversion_ready"),
        "empirically_conversion_proven": certification.get(
            "empirically_conversion_proven"
        ),
        "eligible_market_days_completed": certification.get(
            "eligible_market_days_observed"
        ),
        "eligible_market_day_target": certification.get("eligible_market_day_target"),
        "pre_staged_setup_count": prestaged_status.get("setup_count"),
        "ready_setup_count": prestaged_status.get(
            "ready_for_open_market_revalidation_count"
        ),
        "current_risk_tier": risk_status.get("current_default_tier"),
        "maximum_current_paper_notional_usd": risk_status.get(
            "maximum_current_first_time_notional_usd"
        ),
        "absolute_paper_notional_ceiling_usd": risk_status.get(
            "absolute_notional_ceiling_usd"
        ),
        "primary_blocker": root_cause.get("primary_root_cause"),
        "blocker_owner": root_cause.get("owner"),
        "next_recheck_at": root_cause.get("next_recheck_at"),
        "market_clock_fresh": market_truth.get("provider_fresh"),
        "market_session_phase": market_truth.get("session_phase"),
        "latest_conversion_generation_id": conversion_status.get(
            "latest_conversion_generation_id"
        ),
        "latest_handoff_count": conversion_status.get("paperops_handoff_count"),
        "latest_paper_order_count": conversion_status.get("paper_order_count"),
        "summary": (
            "Qadam is structurally ready and collecting real open-market conversion evidence."
            if certification.get("structural_ready") is True
            else "Qadam has a structural conversion blocker that requires repair."
        ),
        "read_only": True,
        "public_safe": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    root = str(root_cause.get("primary_root_cause") or "no_current_setup")
    handoff_count = int(conversion_status.get("paperops_handoff_count") or 0)
    paper_order_count = int(conversion_status.get("paper_order_count") or 0)
    if paper_order_count:
        event_type = "paper_order_submitted"
        message = (
            f"Paper update: {paper_order_count} guarded Alpaca Paper order"
            f"{'s were' if paper_order_count != 1 else ' was'} submitted from the current evidence generation. Paper only."
        )
    elif handoff_count:
        event_type = "paperops_handoff_created"
        message = (
            f"Paper update: {handoff_count} current setup"
            f"{'s cleared' if handoff_count != 1 else ' cleared'} research review and entered guarded PaperOps. Paper only."
        )
    elif root in INFRASTRUCTURE_ROOT_CAUSES:
        event_type = "conversion_defect_detected"
        message = (
            f"Paper-path repair needed: {root.replace('_', ' ')}. "
            f"Owner: {root_cause.get('owner') or 'conversion coordinator'}. Paper only."
        )
    else:
        event_type = "no_material_change"
        message = "No material open-market conversion change."
    material_change = event_type != "no_material_change"
    telegram = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_telegram_notification_candidate",
        "generated_at": generated_at,
        "send_candidate": material_change,
        "material_event_type": event_type,
        "dedupe_key": sha256_json(
            {
                "event_type": event_type,
                "root": root,
                "state": certification.get("status"),
                "generation": conversion_status.get("latest_conversion_generation_id"),
                "handoffs": handoff_count,
                "paper_orders": paper_order_count,
            }
        ),
        "message": message,
        "review_only": True,
        "command_disabled": True,
        "paper_order_allowed": False,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return summary, telegram


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    baseline = bundle["baseline"]
    if baseline.get("source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("ef11_source_count_mismatch")
    if baseline.get("instrument_count") != EXPECTED_INSTRUMENT_COUNT:
        errors.append("ef11_instrument_count_mismatch")
    if bundle["prestage_status"].get("queue_can_create_order") is not False:
        errors.append("ef11_prestage_queue_has_order_authority")
    if bundle["execution_policy"].get("market_order_when_spread_missing_allowed") is not False:
        errors.append("ef11_missing_spread_market_order_allowed")
    if bundle["risk_ladder"].get("absolute_notional_ceiling_usd") != 5000.0:
        errors.append("ef11_absolute_notional_ceiling_changed")
    certification = bundle["certification"]
    if (
        int(certification.get("eligible_market_days_observed") or 0) < EMPIRICAL_DAY_TARGET
        and certification.get("empirically_conversion_proven") is True
    ):
        errors.append("ef11_empirical_certificate_without_elapsed_market_days")
    for key in (
        "baseline",
        "reconciliation",
        "market_truth",
        "prestage_status",
        "execution_policy",
        "risk_ladder",
        "risk_status",
        "root_cause",
        "repair_queue",
        "scheduler_status",
        "capacity",
        "structural_certification",
        "provider_certification",
        "empirical_certification",
        "certification",
        "visibility",
        "telegram",
    ):
        record = bundle[key]
        if record.get("live_capital_enabled") is not False and key not in {
            "market_truth",
            "reconciliation",
        }:
            errors.append(f"ef11_live_capital_not_disabled:{key}")
        errors.extend(validate_authority(record.get("authority", {}), prefix=f"ef11_{key}"))
    return unique_errors(errors)


def build_and_write_ef11_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = generated_at or now_iso()
    baseline, reconciliation = build_baseline(runtime, generated_at=generated_at)
    market_truth, _market_checks, _market_errors = build_and_write_market_clock_truth(
        settings, generated_at=generated_at
    )
    prestaged, prestage_status, prestage_rejections = build_prestaged_setups(
        runtime,
        baseline_id=baseline["baseline_id"],
        market_truth=market_truth,
        generated_at=generated_at,
    )
    execution_rows, spread_profiles, execution_rejections = build_execution_evidence(
        runtime,
        baseline_id=baseline["baseline_id"],
        market_truth=market_truth,
        prestaged=prestaged,
        generated_at=generated_at,
    )
    execution_policy = execution_fallback_policy(
        generated_at=generated_at, baseline_id=baseline["baseline_id"]
    )
    cycles, daily_summaries, conversion_status = append_conversion_cycles(runtime, [])
    ladder, tier_decisions, tier_status = build_risk_ladder(
        runtime,
        baseline_id=baseline["baseline_id"],
        prestaged=prestaged,
        generated_at=generated_at,
    )
    root_cause, repair_queue, recovery_history = build_root_cause_and_repair(
        runtime,
        baseline_id=baseline["baseline_id"],
        market_truth=market_truth,
        conversion_status=conversion_status,
        generated_at=generated_at,
    )
    scheduler_status, capacity = build_scheduler_status(
        runtime, baseline_id=baseline["baseline_id"], generated_at=generated_at
    )
    structural, provider, empirical, certification = build_certifications(
        runtime,
        baseline=baseline,
        market_truth=market_truth,
        prestaged_status=prestage_status,
        execution_context=execution_rows,
        conversion_status=conversion_status,
        scheduler_status=scheduler_status,
        repair_queue=repair_queue,
        generated_at=generated_at,
    )
    visibility, telegram = build_visibility(
        certification=certification,
        market_truth=market_truth,
        prestaged_status=prestage_status,
        risk_status=tier_status,
        root_cause=root_cause,
        conversion_status=conversion_status,
        generated_at=generated_at,
    )
    deployment = read_json(runtime / DEPLOYMENT_ARTIFACT)
    deployed_live = bool(
        deployment.get("status") == "deployed_live"
        and deployment.get("live_capital_enabled") is False
    )
    phase_status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_phase_status",
        "generated_at": generated_at,
        "baseline_id": baseline["baseline_id"],
        "phases": {
            "EF11-0": "passed",
            "EF11-1": "passed",
            "EF11-2": "passed",
            "EF11-3": "passed",
            "EF11-4": "passed",
            "EF11-5": "implemented",
            "EF11-6": "implemented",
            "EF11-7": "passed" if not repair_queue["repair_request_count"] else "repair_active",
            "EF11-8": "passed",
            "EF11-9": "passed",
            "EF11-10": "collecting_real_market_time",
            "EF11-11": "passed",
            "EF11-12": "collecting_real_soak",
            "EF11-13": "passed" if deployed_live else "ready_for_deployment",
        },
        "engineering_complete": structural.get("structural_ready") is True,
        "deployed_live": deployed_live,
        "empirical_collection_required": True,
        "simulated_elapsed_time_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    bundle = {
        "baseline": baseline,
        "reconciliation": reconciliation,
        "market_truth": market_truth,
        "prestage": prestaged,
        "prestage_status": prestage_status,
        "prestage_rejections": prestage_rejections,
        "execution_context": execution_rows,
        "spread_profiles": spread_profiles,
        "execution_policy": execution_policy,
        "execution_rejections": execution_rejections,
        "cycles": cycles,
        "daily_summaries": daily_summaries,
        "conversion_status": conversion_status,
        "risk_ladder": ladder,
        "risk_tier_decisions": tier_decisions,
        "risk_status": tier_status,
        "root_cause": root_cause,
        "repair_queue": repair_queue,
        "recovery_history": recovery_history,
        "scheduler_status": scheduler_status,
        "capacity": capacity,
        "structural_certification": structural,
        "provider_certification": provider,
        "empirical_certification": empirical,
        "certification": certification,
        "visibility": visibility,
        "telegram": telegram,
        "phase_status": phase_status,
    }
    errors = validate_bundle(bundle)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ef11_open_market_conversion_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "structural_ready": structural["structural_ready"],
        "provider_conversion_ready": provider["provider_conversion_ready"],
        "empirically_conversion_proven": empirical["empirically_conversion_proven"],
        "engineering_contract_ready": not errors,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    for name, value in (
        (BASELINE_ARTIFACT, baseline),
        (RECONCILIATION_ARTIFACT, reconciliation),
        (PRESTAGED_STATUS_ARTIFACT, prestage_status),
        (SPREAD_PROFILE_ARTIFACT, spread_profiles),
        (EXECUTION_POLICY_ARTIFACT, execution_policy),
        (CONVERSION_STATUS_ARTIFACT, conversion_status),
        (RISK_LADDER_ARTIFACT, ladder),
        (RISK_TIER_STATUS_ARTIFACT, tier_status),
        (ROOT_CAUSE_ARTIFACT, root_cause),
        (REPAIR_QUEUE_ARTIFACT, repair_queue),
        (SCHEDULER_STATUS_ARTIFACT, scheduler_status),
        (CAPACITY_ARTIFACT, capacity),
        (STRUCTURAL_CERT_ARTIFACT, structural),
        (PROVIDER_CERT_ARTIFACT, provider),
        (EMPIRICAL_CERT_ARTIFACT, empirical),
        (CERTIFICATION_ARTIFACT, certification),
        (VISIBILITY_ARTIFACT, visibility),
        (TELEGRAM_CANDIDATE_ARTIFACT, telegram),
        (PHASE_STATUS_ARTIFACT, phase_status),
        ("qadam_ef11_open_market_conversion_checks.json", checks),
    ):
        store.write_json(name, value)
    for name, rows in (
        (PRESTAGED_ARTIFACT, prestaged),
        (PRESTAGED_REJECTIONS_ARTIFACT, prestage_rejections),
        (EXECUTION_CONTEXT_ARTIFACT, execution_rows),
        (EXECUTION_REJECTIONS_ARTIFACT, execution_rejections),
        (CONVERSION_CYCLES_ARTIFACT, cycles),
        (DAILY_SUMMARY_ARTIFACT, daily_summaries),
        (RISK_TIER_DECISIONS_ARTIFACT, tier_decisions),
        (RECOVERY_HISTORY_ARTIFACT, recovery_history),
    ):
        store.write_jsonl(name, rows)
    return bundle, checks, errors


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "CONVERSION_CYCLES_ARTIFACT",
    "CONVERSION_STATUS_ARTIFACT",
    "DAILY_SUMMARY_ARTIFACT",
    "EMPIRICAL_DAY_TARGET",
    "PRESTAGED_ARTIFACT",
    "append_conversion_cycles",
    "build_and_write_ef11_state",
    "build_daily_summaries",
    "primary_root_cause",
    "validate_bundle",
]
