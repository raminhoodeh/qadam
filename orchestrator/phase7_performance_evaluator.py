"""Q7-10 Phase 7 Demo Proof performance evaluator.

This stage evaluates the Phase 7 proof sample from Q7-9 postmortem coverage.
It can compute local performance metrics and certification blockers, but it
cannot certify the run, grant proof credit, mutate policy, or enable live
capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_proof_postmortem_contract import (
    PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT,
    build_phase7_proof_postmortem_contract,
    phase7_proof_postmortem_contract_paths,
    validate_phase7_proof_postmortem_contract,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)


PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION = 1
PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT = "phase7_performance_evaluator.json"
PHASE7_PERFORMANCE_EVALUATOR_HISTORY = "phase7_performance_evaluator_history.jsonl"
PHASE7_PERFORMANCE_EVALUATOR_EVENT_LOG = "phase7_performance_evaluator_events.jsonl"
PHASE7_PERFORMANCE_EVALUATOR_EVENT_TYPE = PHASE7_EVENT_TYPES["performance"]
PHASE7_PERFORMANCE_EVALUATOR_COMPONENT = "phase7_performance_evaluator"

PHASE7_PERFORMANCE_BOUNDARY = (
    "Q7-10 records local Phase 7 performance evaluation metrics only from Q7-9 "
    "postmortem-covered closed proof trades. It can compute expectancy after "
    "estimated costs, R-multiple distribution, win rate, average win/loss, "
    "Sharpe/Sortino when sample size permits, rolling seven-day and 30-day "
    "expectancy, max drawdown, and statistical maturity labels, but it cannot "
    "certify Phase 7, cannot grant Phase 7 proof credit, cannot call broker "
    "POST routes, cannot call Alpaca POST routes, cannot write prediction-"
    "market or crypto-perps orders, cannot mutate policy or strategies, cannot "
    "enable live capital, and cannot permit manual trade-level overrides."
)

PHASE7_PERFORMANCE_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_9_postmortem_contract_valid",
    "q7_10_performance_stage_allowed",
    "source_closed_trade_present",
    "postmortem_coverage_present",
    "source_lifecycle_refs_present",
    "realized_pnl_available_or_marked_unknown",
    "estimated_cost_available_or_zero",
    "r_multiple_available_or_derivable",
    "expectancy_after_costs_computed",
    "win_loss_classified",
    "drawdown_computed",
    "drawdown_cap_checked",
    "sample_maturity_labelled",
    "sharpe_sortino_guarded_by_sample_size",
    "rolling_expectancy_computed",
    "no_certification_authority",
    "no_proof_credit",
    "no_broker_post",
    "no_alpaca_post",
    "no_live_endpoint",
    "no_live_capital",
    "manual_override_disabled",
    "market_writes_disabled",
    "public_safe",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def phase7_performance_evaluator_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT,
        runtime / PHASE7_PERFORMANCE_EVALUATOR_HISTORY,
        runtime / PHASE7_PERFORMANCE_EVALUATOR_EVENT_LOG,
    )


def _postmortem_contract(settings: Settings) -> dict[str, Any]:
    postmortem_path, _, _ = phase7_proof_postmortem_contract_paths(settings)
    if postmortem_path.exists():
        return _read_json(postmortem_path)
    return build_phase7_proof_postmortem_contract(settings=settings)


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _performance_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "source_postmortem_contract_required": True,
        "postmortem_coverage_required_for_closed_trades": True,
        "expectancy_after_costs_required": True,
        "estimated_costs_required_or_zero": True,
        "r_multiple_distribution_required": True,
        "win_rate_required": True,
        "average_win_loss_required": True,
        "drawdown_required": True,
        "sharpe_sortino_only_when_sample_size_permits": True,
        "rolling_7d_30d_expectancy_required": True,
        "maturity_label_required": True,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "certification_authority_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "policy_mutation_allowed": False,
        "strategy_mutation_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(stage_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    for field in (
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    ):
        defaults[field] = stage_recorded
    return {
        "authority_schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "stage": "Q7-10",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 6 if stage_recorded else 0,
        "explicit_authority_grants": (
            [
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
                "phase7_proof_lifecycle_write_allowed",
                "phase7_postmortem_write_allowed",
                "phase7_performance_evaluation_write_allowed",
            ]
            if stage_recorded
            else []
        ),
        "q7_11_drawdown_risk_sentinel_stage_allowed": stage_recorded,
        **defaults,
        "boundary": PHASE7_PERFORMANCE_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_proof_postmortem_contract.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-9-proof-postmortem-contract-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}"
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(postmortem: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    postmortem_errors = validate_phase7_proof_postmortem_contract(postmortem)
    if postmortem_errors:
        blockers.append("phase7_proof_postmortem_validation_errors")
    if postmortem.get("proof_postmortem_contract_recorded") is not True:
        blockers.append("phase7_proof_postmortem_contract_not_recorded")
    if postmortem.get("q7_10_performance_evaluator_stage_allowed") is not True:
        blockers.append("q7_10_performance_evaluator_stage_not_allowed")
    if _int(postmortem.get("closed_trade_without_postmortem_coverage_count")) != 0:
        blockers.append("phase7_postmortem_coverage_missing")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if postmortem.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _postmortem_due_records(postmortem: dict[str, Any]) -> list[dict[str, Any]]:
    records = postmortem.get("postmortem_due_records", [])
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("postmortem_due_marker_created") is True
    ]


def _closed_at(record: dict[str, Any]) -> datetime:
    for field in ("closed_at", "postmortem_due_at", "generated_at"):
        value = record.get(field)
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return datetime.now(timezone.utc)


def _trade_metric_record(
    postmortem_record: dict[str, Any],
    *,
    stage_recorded: bool,
    postmortem_errors: list[str],
) -> dict[str, Any]:
    realized_pnl = _optional_float(postmortem_record.get("realized_pnl_gbp"))
    if realized_pnl is None:
        realized_pnl = 0.0
    estimated_cost = _float(postmortem_record.get("estimated_cost_gbp"), 0.0)
    risk_size = _float(postmortem_record.get("risk_size_gbp"), 0.0)
    explicit_r = _optional_float(postmortem_record.get("r_multiple"))
    net_pnl = realized_pnl - estimated_cost
    r_multiple = explicit_r if explicit_r is not None else None
    if r_multiple is None and risk_size > 0:
        r_multiple = net_pnl / risk_size
    closed_at = _closed_at(postmortem_record)
    checks = [
        _check("q7_9_postmortem_contract_valid", not postmortem_errors, detail=postmortem_errors),
        _check("q7_10_performance_stage_allowed", stage_recorded),
        _check("source_closed_trade_present", bool(postmortem_record.get("source_closed_trade_ref"))),
        _check("postmortem_coverage_present", postmortem_record.get("postmortem_due_marker_created") is True),
        _check(
            "source_lifecycle_refs_present",
            bool(postmortem_record.get("source_lifecycle_event_ref"))
            and bool(postmortem_record.get("source_submitted_order_ref"))
            and bool(postmortem_record.get("source_broker_receipt_ref")),
        ),
        _check("realized_pnl_available_or_marked_unknown", True),
        _check("estimated_cost_available_or_zero", estimated_cost >= 0),
        _check("r_multiple_available_or_derivable", r_multiple is not None),
        _check("expectancy_after_costs_computed", True),
        _check("win_loss_classified", True),
        _check("drawdown_computed", True),
        _check("drawdown_cap_checked", True),
        _check("sample_maturity_labelled", True),
        _check("sharpe_sortino_guarded_by_sample_size", True),
        _check("rolling_expectancy_computed", True),
        _check("no_certification_authority", True),
        _check("no_proof_credit", True),
        _check("no_broker_post", True),
        _check("no_alpaca_post", True),
        _check("no_live_endpoint", True),
        _check("no_live_capital", True),
        _check("manual_override_disabled", True),
        _check("market_writes_disabled", True),
        _check("public_safe", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    ready = stage_recorded and not failed_checks
    closed_trade_ref = str(postmortem_record.get("source_closed_trade_ref") or "unknown")
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "performance_evaluator_schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "artifact_type": "performance_evaluation",
        "artifact_id": f"phase7:q7-10:performance-metric:{_safe_key(closed_trade_ref)}",
        "phase": "Q7",
        "stage": "Q7-10",
        "status": "evaluated" if ready else "blocked",
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "source_q7_9_artifact_id": postmortem_record.get("artifact_id"),
        "source_lifecycle_event_ref": postmortem_record.get("source_lifecycle_event_ref"),
        "source_closed_trade_ref": closed_trade_ref,
        "source_setup_record_id": postmortem_record.get("source_setup_record_id"),
        "source_auto_approval_decision_id": postmortem_record.get(
            "source_auto_approval_decision_id"
        ),
        "source_order_ref": postmortem_record.get("source_submitted_order_ref"),
        "source_broker_receipt_ref": postmortem_record.get("source_broker_receipt_ref"),
        "closed_at": closed_at.isoformat(),
        "realized_pnl_gbp": realized_pnl,
        "estimated_cost_gbp": estimated_cost,
        "net_pnl_after_costs_gbp": net_pnl,
        "risk_size_gbp": risk_size,
        "r_multiple": r_multiple,
        "outcome_bucket": "win" if net_pnl > 0 else "loss" if net_pnl < 0 else "breakeven",
        "win": net_pnl > 0,
        "loss": net_pnl < 0,
        "breakeven": net_pnl == 0,
        "postmortem_coverage_present": postmortem_record.get(
            "postmortem_due_marker_created"
        )
        is True,
        "postmortem_reviewed": postmortem_record.get("postmortem_reviewed") is True,
        "postmortem_explicitly_deferred": postmortem_record.get(
            "postmortem_explicitly_deferred"
        )
        is True,
        "performance_evaluation_write_allowed": ready,
        "phase7_proof_credit_allowed": False,
        "proof_trade_credit_count": 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "required_checks": list(PHASE7_PERFORMANCE_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PERFORMANCE_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if ready else failed_checks,
        "blocked_reason_count": 0 if ready else len(failed_checks),
    }


def _trade_metric_records(
    postmortem: dict[str, Any],
    *,
    stage_recorded: bool,
) -> list[dict[str, Any]]:
    postmortem_errors = validate_phase7_proof_postmortem_contract(postmortem)
    return [
        _trade_metric_record(
            record,
            stage_recorded=stage_recorded,
            postmortem_errors=postmortem_errors,
        )
        for record in _postmortem_due_records(postmortem)
    ]


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _sharpe(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    deviation = pstdev(values)
    if deviation == 0:
        return None
    return mean(values) / deviation


def _sortino(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    downside = [min(0.0, value) for value in values]
    downside_deviation = pstdev(downside)
    if downside_deviation == 0:
        return None
    return mean(values) / downside_deviation


def _max_drawdown_fraction(net_pnls: list[float]) -> float:
    equity = PHASE7_PAPER_ACCOUNT_STARTING_GBP
    peak = equity
    max_drawdown = 0.0
    for pnl in net_pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown


def _rolling_expectancy(records: list[dict[str, Any]], *, days: int) -> float | None:
    ready = [
        record
        for record in records
        if isinstance(record, dict) and record.get("status") == "evaluated"
    ]
    if not ready:
        return None
    latest = max(_closed_at(record) for record in ready)
    start = latest - timedelta(days=days)
    values = [
        _float(record.get("net_pnl_after_costs_gbp"), 0.0)
        for record in ready
        if _closed_at(record) >= start
    ]
    return _mean(values)


def _metric_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [
        record
        for record in records
        if isinstance(record, dict) and record.get("status") == "evaluated"
    ]
    net_pnls = [_float(record.get("net_pnl_after_costs_gbp"), 0.0) for record in ready]
    realized_pnls = [_float(record.get("realized_pnl_gbp"), 0.0) for record in ready]
    costs = [_float(record.get("estimated_cost_gbp"), 0.0) for record in ready]
    r_multiples = [
        _float(record.get("r_multiple"), 0.0)
        for record in ready
        if record.get("r_multiple") is not None
    ]
    wins = [value for value in net_pnls if value > 0]
    losses = [value for value in net_pnls if value < 0]
    win_r = [
        _float(record.get("r_multiple"), 0.0)
        for record in ready
        if record.get("r_multiple") is not None and _float(record.get("r_multiple")) > 0
    ]
    loss_r = [
        _float(record.get("r_multiple"), 0.0)
        for record in ready
        if record.get("r_multiple") is not None and _float(record.get("r_multiple")) < 0
    ]
    trade_count = len(ready)
    max_drawdown = _max_drawdown_fraction(net_pnls)
    return {
        "evaluated_trade_count": trade_count,
        "cost_estimated_trade_count": len(costs),
        "r_multiple_count": len(r_multiples),
        "winning_trade_count": len(wins),
        "losing_trade_count": len(losses),
        "breakeven_trade_count": trade_count - len(wins) - len(losses),
        "total_realized_pnl_gbp": _round(sum(realized_pnls), 4),
        "total_estimated_cost_gbp": _round(sum(costs), 4),
        "total_net_pnl_after_costs_gbp": _round(sum(net_pnls), 4),
        "expectancy_before_costs_gbp": _round(_mean(realized_pnls), 6),
        "expectancy_after_costs_gbp": _round(_mean(net_pnls), 6),
        "expectancy_after_costs_positive": bool(net_pnls and _mean(net_pnls) > 0),
        "win_rate": _round(_ratio(len(wins), trade_count), 6),
        "loss_rate": _round(_ratio(len(losses), trade_count), 6),
        "average_win_gbp": _round(_mean(wins), 6),
        "average_loss_gbp": _round(_mean(losses), 6),
        "average_r_multiple": _round(_mean(r_multiples), 6),
        "average_win_r_multiple": _round(_mean(win_r), 6),
        "average_loss_r_multiple": _round(_mean(loss_r), 6),
        "max_drawdown_fraction_observed": _round(max_drawdown, 6) or 0.0,
        "drawdown_within_cap": max_drawdown <= PHASE7_MAX_DRAWDOWN_FRACTION,
        "phase7_certification_blocked_by_drawdown": (
            max_drawdown > PHASE7_MAX_DRAWDOWN_FRACTION
        ),
        "phase7_certification_blocked_by_negative_expectancy": bool(
            net_pnls and (_mean(net_pnls) is not None and _mean(net_pnls) <= 0)
        ),
        "sharpe_ratio": _round(_sharpe(net_pnls), 6),
        "sortino_ratio": _round(_sortino(net_pnls), 6),
        "sharpe_sortino_sample_size_sufficient": trade_count >= 2,
        "rolling_7d_expectancy_after_costs_gbp": _round(
            _rolling_expectancy(ready, days=7),
            6,
        ),
        "rolling_30d_expectancy_after_costs_gbp": _round(
            _rolling_expectancy(ready, days=30),
            6,
        ),
        "statistically_mature": trade_count >= PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_maturity_state": (
            "statistically_mature"
            if trade_count >= PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
            else "statistically_immature"
            if trade_count
            else "no_sample"
        ),
        "sample_size_warning": trade_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    }


def build_phase7_performance_evaluator(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    postmortem = _postmortem_contract(settings)
    blockers = _preflight_blockers(postmortem)
    stage_recorded = not blockers
    records = _trade_metric_records(postmortem, stage_recorded=stage_recorded)
    summary = _metric_summary(records)
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    for field in (
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    ):
        authority_defaults[field] = stage_recorded
    status = "ready_no_closed_trades"
    stage_status = "performance_evaluator_ready_no_closed_trades"
    if summary["evaluated_trade_count"]:
        status = "performance_metrics_recorded"
        stage_status = "performance_metrics_recorded"
    if not stage_recorded:
        status = "blocked"
        stage_status = "performance_evaluator_blocked"
    artifact = {
        "schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_performance_evaluator",
        "artifact_id": "phase7:q7-10:performance-evaluator",
        "phase": "Q7",
        "stage": "Q7-10",
        "status": status,
        "stage_status": stage_status,
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(stage_recorded),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "performance_policy": _performance_policy(),
        "trade_metric_records": records,
        "boundary": PHASE7_PERFORMANCE_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_postmortem_artifact_id": postmortem.get("artifact_id"),
        "source_postmortem_status": postmortem.get("status"),
        "source_postmortem_stage_status": postmortem.get("stage_status"),
        "source_closed_proof_trade_count": _int(
            postmortem.get("source_closed_proof_trade_count")
        ),
        "source_postmortem_due_count": _int(postmortem.get("postmortem_due_count")),
        "source_postmortem_missing_coverage_count": _int(
            postmortem.get("closed_trade_without_postmortem_coverage_count")
        ),
        "q7_10_performance_evaluator_stage_allowed": (
            postmortem.get("q7_10_performance_evaluator_stage_allowed") is True
        ),
        "q7_11_drawdown_risk_sentinel_stage_allowed": stage_recorded,
        "performance_evaluator_recorded": stage_recorded,
        "performance_evaluation_write_allowed": stage_recorded,
        "performance_metric_record_count": len(records),
        "closed_proof_trade_count": _int(postmortem.get("source_closed_proof_trade_count")),
        "postmortem_covered_trade_count": _int(postmortem.get("postmortem_due_count")),
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_order_submitted_count": _int(postmortem.get("paper_order_submitted_count")),
        "proof_trade_created_count": _int(postmortem.get("proof_trade_created_count")),
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-11 Drawdown And Risk Sentinel",
        **summary,
    }
    artifact["validation_errors"] = validate_phase7_performance_evaluator(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "performance_evaluator_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("performance_evaluator_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_performance_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-10":
        errors.append("phase7_performance_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_performance_authority_count_mismatch")
    expected_grants = 6 if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_performance_explicit_authority_grant_count_invalid")
    expected_true = {
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    }
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_performance_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_performance_ledger_authority_invalid:{field}")
    allowed_count_fields = {"paper_order_submitted_count", "proof_trade_created_count"}
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_performance_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("proof_trade_created_count")):
                errors.append(f"phase7_performance_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_performance_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        _int(artifact.get(field))
        for field in PHASE7_UNSAFE_COUNT_FIELDS
        if field not in allowed_count_fields
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_performance_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_performance_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("performance_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_performance_policy_missing"]
    for field in (
        "source_postmortem_contract_required",
        "postmortem_coverage_required_for_closed_trades",
        "expectancy_after_costs_required",
        "estimated_costs_required_or_zero",
        "r_multiple_distribution_required",
        "win_rate_required",
        "average_win_loss_required",
        "drawdown_required",
        "sharpe_sortino_only_when_sample_size_permits",
        "rolling_7d_30d_expectancy_required",
        "maturity_label_required",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_performance_policy_missing_true:{field}")
    for field in (
        "certification_authority_allowed",
        "proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "policy_mutation_allowed",
        "strategy_mutation_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"phase7_performance_policy_forbidden:{field}")
    if policy.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_performance_policy_maturity_benchmark_invalid")
    if float(policy.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_performance_policy_drawdown_invalid")
    return errors


def _trade_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ready = record.get("status") == "evaluated"
    if record.get("artifact_type") != "performance_evaluation":
        errors.append("phase7_performance_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-10":
        errors.append("phase7_performance_record_phase_stage_invalid")
    if tuple(record.get("required_checks", ())) != PHASE7_PERFORMANCE_REQUIRED_CHECKS:
        errors.append("phase7_performance_record_required_checks_invalid")
    if ready:
        for field in (
            "source_q7_9_artifact_id",
            "source_lifecycle_event_ref",
            "source_closed_trade_ref",
            "source_setup_record_id",
            "source_order_ref",
            "source_broker_receipt_ref",
            "closed_at",
        ):
            if not str(record.get(field) or "").strip():
                errors.append(f"phase7_performance_record_missing:{field}")
        if record.get("postmortem_coverage_present") is not True:
            errors.append("phase7_performance_record_postmortem_coverage_missing")
        if record.get("performance_evaluation_write_allowed") is not True:
            errors.append("phase7_performance_record_write_not_allowed")
        realized_pnl = _optional_float(record.get("realized_pnl_gbp"))
        estimated_cost = _optional_float(record.get("estimated_cost_gbp"))
        net_pnl = _optional_float(record.get("net_pnl_after_costs_gbp"))
        risk_size = _optional_float(record.get("risk_size_gbp"))
        r_multiple = _optional_float(record.get("r_multiple"))
        if realized_pnl is None:
            errors.append("phase7_performance_record_realized_pnl_missing")
        if estimated_cost is None:
            errors.append("phase7_performance_record_estimated_cost_missing")
        elif estimated_cost < 0:
            errors.append("phase7_performance_record_estimated_cost_negative")
        if net_pnl is None:
            errors.append("phase7_performance_record_net_pnl_missing")
        if r_multiple is None:
            errors.append("phase7_performance_record_r_multiple_missing")
        if realized_pnl is not None and estimated_cost is not None and net_pnl is not None:
            expected_net = _round(realized_pnl - estimated_cost, 6)
            if _round(net_pnl, 6) != expected_net:
                errors.append("phase7_performance_record_net_pnl_mismatch")
        if (
            risk_size is not None
            and risk_size > 0
            and r_multiple is not None
            and net_pnl is not None
        ):
            expected_r = _round(net_pnl / risk_size, 6)
            if _round(r_multiple, 6) != expected_r:
                errors.append("phase7_performance_record_r_multiple_mismatch")
        expected_bucket = (
            "win"
            if (net_pnl is not None and net_pnl > 0)
            else "loss"
            if (net_pnl is not None and net_pnl < 0)
            else "breakeven"
        )
        if record.get("outcome_bucket") != expected_bucket:
            errors.append("phase7_performance_record_outcome_bucket_mismatch")
        if record.get("win") is not (net_pnl is not None and net_pnl > 0):
            errors.append("phase7_performance_record_win_flag_mismatch")
        if record.get("loss") is not (net_pnl is not None and net_pnl < 0):
            errors.append("phase7_performance_record_loss_flag_mismatch")
        if record.get("breakeven") is not (net_pnl is None or net_pnl == 0):
            errors.append("phase7_performance_record_breakeven_flag_mismatch")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_performance_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("phase7_performance_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_performance_record_failed_count_mismatch")
    if ready and failed_checks:
        errors.append("phase7_performance_ready_record_has_failed_checks")
    for field in (
        "phase7_proof_credit_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_performance_record_forbidden:{field}")
    for count_field in (
        "proof_trade_credit_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
    ):
        if _int(record.get(count_field)) != 0:
            errors.append(f"phase7_performance_record_count_nonzero:{count_field}")
    return errors


def validate_phase7_performance_evaluator(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "performance_policy",
        "trade_metric_records",
        "boundary",
        "source_postmortem_status",
        "source_closed_proof_trade_count",
        "source_postmortem_due_count",
        "source_postmortem_missing_coverage_count",
        "q7_10_performance_evaluator_stage_allowed",
        "q7_11_drawdown_risk_sentinel_stage_allowed",
        "performance_evaluator_recorded",
        "performance_evaluation_write_allowed",
        "performance_metric_record_count",
        "closed_proof_trade_count",
        "postmortem_covered_trade_count",
        "evaluated_trade_count",
        "cost_estimated_trade_count",
        "r_multiple_count",
        "winning_trade_count",
        "losing_trade_count",
        "breakeven_trade_count",
        "total_realized_pnl_gbp",
        "total_estimated_cost_gbp",
        "total_net_pnl_after_costs_gbp",
        "expectancy_before_costs_gbp",
        "expectancy_after_costs_gbp",
        "expectancy_after_costs_positive",
        "win_rate",
        "loss_rate",
        "average_win_gbp",
        "average_loss_gbp",
        "average_r_multiple",
        "average_win_r_multiple",
        "average_loss_r_multiple",
        "max_drawdown_fraction_observed",
        "drawdown_within_cap",
        "phase7_certification_blocked_by_drawdown",
        "phase7_certification_blocked_by_negative_expectancy",
        "sharpe_ratio",
        "sortino_ratio",
        "sharpe_sortino_sample_size_sufficient",
        "rolling_7d_expectancy_after_costs_gbp",
        "rolling_30d_expectancy_after_costs_gbp",
        "statistically_mature",
        "statistical_maturity_state",
        "sample_size_warning",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_performance_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION:
        errors.append("phase7_performance_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_performance_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_performance_evaluator":
        errors.append("phase7_performance_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-10":
        errors.append("phase7_performance_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_performance_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_performance_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_performance_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_performance_blocker_count_mismatch")
    stage_recorded = artifact.get("performance_evaluator_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_closed_trades",
            "performance_metrics_recorded",
        }:
            errors.append("phase7_performance_status_invalid")
        if artifact.get("stage_status") not in {
            "performance_evaluator_ready_no_closed_trades",
            "performance_metrics_recorded",
        }:
            errors.append("phase7_performance_stage_status_invalid")
        if blockers:
            errors.append("phase7_performance_recorded_with_blockers")
        if artifact.get("performance_evaluation_write_allowed") is not True:
            errors.append("phase7_performance_write_not_allowed")
        if artifact.get("q7_11_drawdown_risk_sentinel_stage_allowed") is not True:
            errors.append("q7_11_drawdown_risk_sentinel_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_performance_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_performance_blocked_without_blockers")
        if artifact.get("q7_11_drawdown_risk_sentinel_stage_allowed") is not False:
            errors.append("q7_11_stage_allowed_while_blocked")
    if artifact.get("q7_10_performance_evaluator_stage_allowed") is not True:
        errors.append("q7_10_performance_evaluator_not_allowed")
    if artifact.get("source_postmortem_status") not in {
        "ready_no_closed_trades",
        "postmortem_due_markers_recorded",
    }:
        errors.append("phase7_performance_source_postmortem_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    records = artifact.get("trade_metric_records", [])
    if not isinstance(records, list):
        errors.append("phase7_performance_records_not_list")
        records = []
    for record in records:
        if isinstance(record, dict):
            errors.extend(_trade_record_errors(record))
        else:
            errors.append("phase7_performance_record_invalid")
    ready_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("status") == "evaluated"
    ]
    summary = _metric_summary(ready_records)
    summary_fields = (
        "evaluated_trade_count",
        "cost_estimated_trade_count",
        "r_multiple_count",
        "winning_trade_count",
        "losing_trade_count",
        "breakeven_trade_count",
        "total_realized_pnl_gbp",
        "total_estimated_cost_gbp",
        "total_net_pnl_after_costs_gbp",
        "expectancy_before_costs_gbp",
        "expectancy_after_costs_gbp",
        "expectancy_after_costs_positive",
        "win_rate",
        "loss_rate",
        "average_win_gbp",
        "average_loss_gbp",
        "average_r_multiple",
        "average_win_r_multiple",
        "average_loss_r_multiple",
        "max_drawdown_fraction_observed",
        "drawdown_within_cap",
        "phase7_certification_blocked_by_drawdown",
        "phase7_certification_blocked_by_negative_expectancy",
        "sharpe_ratio",
        "sortino_ratio",
        "sharpe_sortino_sample_size_sufficient",
        "rolling_7d_expectancy_after_costs_gbp",
        "rolling_30d_expectancy_after_costs_gbp",
        "statistically_mature",
        "statistical_maturity_state",
        "sample_size_warning",
    )
    for field in summary_fields:
        if artifact.get(field) != summary.get(field):
            errors.append(f"phase7_performance_metric_mismatch:{field}")
    if artifact.get("performance_metric_record_count") != len(records):
        errors.append("phase7_performance_metric_record_count_mismatch")
    closed_trade_count = _int(artifact.get("closed_proof_trade_count"))
    if closed_trade_count != _int(artifact.get("source_closed_proof_trade_count")):
        errors.append("phase7_performance_closed_count_source_mismatch")
    if artifact.get("postmortem_covered_trade_count") != (
        artifact.get("source_postmortem_due_count")
    ):
        errors.append("phase7_performance_postmortem_coverage_count_mismatch")
    if closed_trade_count != _int(artifact.get("postmortem_covered_trade_count")):
        errors.append("phase7_performance_closed_count_without_postmortem_coverage")
    if artifact.get("evaluated_trade_count") != closed_trade_count:
        errors.append("phase7_performance_evaluated_count_mismatch")
    if artifact.get("statistical_maturity_state") == "statistically_mature":
        if artifact.get("statistically_mature") is not True:
            errors.append("phase7_performance_maturity_flag_mismatch")
    if artifact.get("statistical_maturity_state") == "statistically_immature":
        if artifact.get("sample_size_warning") is not True:
            errors.append("phase7_performance_immature_without_warning")
    if closed_trade_count == 0:
        if artifact.get("expectancy_after_costs_gbp") is not None:
            errors.append("phase7_performance_empty_expectancy_not_none")
        if artifact.get("statistical_maturity_state") != "no_sample":
            errors.append("phase7_performance_empty_maturity_state_invalid")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_performance_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_performance_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_performance_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_performance_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_performance_mature_benchmark_mismatch")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_performance_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_performance_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_performance_qctrl_role_invalid")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_performance_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_performance_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_performance_proof_contract_phase5_reuse_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_performance_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_performance_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_performance_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_performance_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records local Phase 7 performance evaluation metrics only",
        "expectancy after estimated costs",
        "R-multiple distribution",
        "statistical maturity labels",
        "cannot certify Phase 7",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_performance_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_performance_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_performance_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_performance_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_PERFORMANCE_EVALUATOR_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    records = [
        record
        for record in output.get("trade_metric_records", []) or []
        if isinstance(record, dict)
    ]
    if records:
        for record in records:
            entry = log.write(
                PHASE7_PERFORMANCE_EVALUATOR_EVENT_TYPE,
                PHASE7_PERFORMANCE_EVALUATOR_COMPONENT,
                {
                    "artifact_id": record.get("artifact_id"),
                    "status": record.get("status"),
                    "source_closed_trade_ref": record.get("source_closed_trade_ref"),
                    "net_pnl_after_costs_gbp": record.get("net_pnl_after_costs_gbp"),
                    "r_multiple": record.get("r_multiple"),
                    "outcome_bucket": record.get("outcome_bucket"),
                    "phase7_proof_credit_allowed": record.get(
                        "phase7_proof_credit_allowed"
                    ),
                    "live_capital_enabled": record.get("live_capital_enabled"),
                },
            )
            record["event_log_written"] = True
            record["event_log_path"] = str(log.path)
            record["event_log_correlation_id"] = entry.correlation_id
            record["event_log_created_at"] = entry.created_at
            entries.append(entry)
        output["trade_metric_records"] = records
    else:
        entry = log.write(
            PHASE7_PERFORMANCE_EVALUATOR_EVENT_TYPE,
            PHASE7_PERFORMANCE_EVALUATOR_COMPONENT,
            {
                "artifact_id": output.get("artifact_id"),
                "status": output.get("status"),
                "stage_status": output.get("stage_status"),
                "closed_proof_trade_count": output.get("closed_proof_trade_count"),
                "evaluated_trade_count": output.get("evaluated_trade_count"),
                "expectancy_after_costs_gbp": output.get("expectancy_after_costs_gbp"),
                "max_drawdown_fraction_observed": output.get(
                    "max_drawdown_fraction_observed"
                ),
                "statistical_maturity_state": output.get("statistical_maturity_state"),
                "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
                "live_capital_enabled": output.get("live_capital_enabled"),
                "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
                "recommended_next_stage": output.get("recommended_next_stage"),
                "boundary": output.get("boundary"),
            },
        )
        entries.append(entry)
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["event_log_correlation_id"] = entries[-1].correlation_id if entries else None
    output["event_log_created_at"] = entries[-1].created_at if entries else None
    output["validation_errors"] = validate_phase7_performance_evaluator(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "performance_evaluator_validation_error"
    return output, entries


def write_phase7_performance_evaluator(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_performance_evaluator_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_performance_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_performance_evaluator(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "performance_evaluator_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_performance_evaluator(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "performance_evaluator_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "evaluated_trade_count": output.get("evaluated_trade_count"),
        "expectancy_after_costs_gbp": output.get("expectancy_after_costs_gbp"),
        "expectancy_after_costs_positive": output.get(
            "expectancy_after_costs_positive"
        ),
        "max_drawdown_fraction_observed": output.get("max_drawdown_fraction_observed"),
        "drawdown_within_cap": output.get("drawdown_within_cap"),
        "statistical_maturity_state": output.get("statistical_maturity_state"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
