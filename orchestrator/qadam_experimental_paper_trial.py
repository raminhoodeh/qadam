"""Real-calendar experimental paper trial and outcome projection."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_guarded_paper_launch import refresh_experimental_trial_calendar
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_experimental_paper_trial.v1"
OUTCOMES_ARTIFACT = "qadam_experimental_paper_outcomes.jsonl"
SUMMARY_ARTIFACT = "qadam_30_day_paper_growth_trial_summary.json"
CHECK_ARTIFACT = "qadam_experimental_paper_trial_checks.json"


def _number(*values: Any, default: float = 0.0) -> float:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def build_experimental_paper_trial(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runtime = runtime_dir(settings)
    epoch = read_json(runtime / "current_paper_epoch.json")
    calendar = refresh_experimental_trial_calendar(settings)
    release = read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    lineage = read_jsonl(runtime / "qadam_paper_trade_lineage.jsonl")
    proof = read_json(runtime / "qadam_paper_proof_eligibility.json")
    lifecycle = read_json(runtime / "qadam_paper_lifecycle_v3.json")
    performance = read_json(runtime / "qadam_paper_performance_summary.json")
    portfolio = read_json(runtime / "qsase_dashboard_status.json").get(
        "dashboard_portfolio", {}
    )
    epoch_id = epoch.get("paper_epoch_id")
    outcomes = [
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_experimental_paper_outcome",
            "generated_at": row.get("generated_at"),
            "paper_epoch_id": row.get("paper_epoch_id"),
            "lineage_record_id": row.get("lineage_record_id"),
            "instrument": row.get("instrument"),
            "direction": row.get("direction"),
            "lifecycle_state": row.get("current_lifecycle_state"),
            "metrics": row.get("metrics", {}),
            "postmortem_complete": row.get("postmortem_complete") is True,
            "proof_tier": "experimental_forward_outcome",
            "validated_edge_evidence": False,
            "validated_edge_credit": False,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        for row in lineage
        if row.get("paper_epoch_id") == epoch_id
        and row.get("proof_tiers", {}).get("experimental_forward_outcome") is True
    ]
    trial_active = bool(
        epoch.get("paper_epoch_kind") == "clean_experimental_operator_epoch"
        and release.get("experimental_paper_release_effective") is True
        and calendar.get("status") in {"active_real_calendar", "complete_real_calendar"}
    )
    trial_complete = bool(trial_active and int(calendar.get("trial_day") or 0) >= 30)
    starting = _number(epoch.get("starting_balance"), default=100000.0)
    current = _number(portfolio.get("current_value"), default=starting)
    net_pnl = _number(performance.get("qadam_realized_net_pnl"), default=0.0)
    drawdown = _number(portfolio.get("drawdown_pct"), default=0.0)
    closed_count = int(lifecycle.get("closed_trade_record_count") or 0)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_30_day_paper_growth_trial_summary",
        "generated_at": now_iso(),
        "status": (
            "complete_pending_operator_review"
            if trial_complete
            else "active"
            if trial_active
            else "not_started_waiting_for_guarded_release"
        ),
        "paper_epoch_id": epoch_id,
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or "legacy_test",
        "trial_started_at": calendar.get("trial_started_at"),
        "trial_day": int(calendar.get("trial_day") or 0),
        "calendar_days_remaining": int(calendar.get("calendar_days_remaining") or 30),
        "trial_length_days": 30,
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
        "calendar_pause_allowed": False,
        "starting_value_usd": starting,
        "current_value_usd": current,
        "net_paper_pnl_usd": net_pnl,
        "net_paper_return_pct": round(((current / starting) - 1.0) * 100.0, 6)
        if starting
        else None,
        "drawdown_pct": drawdown,
        "submitted_paper_order_count": int(
            proof.get("broker_execution_fact_count") or 0
        ),
        "open_position_count": int(portfolio.get("position_count") or 0),
        "closed_paper_trade_count": closed_count,
        "experimental_forward_outcome_count": len(outcomes),
        "validated_edge_evidence_count": 0,
        "validated_edge_credit_count": 0,
        "performance_metrics": {
            "win_count": int(performance.get("qadam_win_count") or 0),
            "loss_count": int(performance.get("qadam_loss_count") or 0),
            "hit_rate": None,
            "expectancy": None,
            "sharpe": None,
            "sortino": None,
            "benchmark_relative_return_pct": None,
            "turnover": None,
            "slippage_cost_usd": None,
            "spread_cost_usd": None,
            "proxy_basis_risk": "not_measurable_without_current_epoch_outcomes"
            if not outcomes
            else "recorded_per_outcome",
        },
        "day_30_recommendation": (
            "operator_review_required_continue_revise_or_stop"
            if trial_complete
            else "not_due"
        ),
        "no_forced_trades": True,
        "poor_results_retained": True,
        "automatic_strategy_promotion_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return summary, outcomes


def validate_experimental_paper_trial(
    summary: dict[str, Any], outcomes: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    if summary.get("backfill_used") is not False:
        errors.append("experimental_trial_calendar_backfilled")
    if summary.get("simulated_elapsed_time_used") is not False:
        errors.append("experimental_trial_simulated_elapsed_time")
    if summary.get("validated_edge_evidence_count") != 0:
        errors.append("experimental_trial_granted_validated_edge_evidence")
    if summary.get("validated_edge_credit_count") != 0:
        errors.append("experimental_trial_granted_validated_edge_credit")
    if summary.get("automatic_strategy_promotion_allowed") is not False:
        errors.append("experimental_trial_allows_automatic_promotion")
    epoch_id = summary.get("paper_epoch_id")
    for row in outcomes:
        if row.get("paper_epoch_id") != epoch_id:
            errors.append("experimental_trial_outcome_epoch_mismatch")
        if row.get("proof_tier") != "experimental_forward_outcome":
            errors.append("experimental_trial_outcome_tier_invalid")
        if row.get("validated_edge_credit") is not False:
            errors.append("experimental_trial_outcome_granted_edge_credit")
        errors.extend(validate_authority(row.get("authority", {}), prefix="trial_outcome"))
    for field in ("paper_order_created_count", "broker_write_count", "proof_credit_created_count"):
        if int(summary.get(field) or 0) != 0:
            errors.append(f"experimental_trial_forbidden_count:{field}")
    if summary.get("live_capital_enabled") is not False:
        errors.append("experimental_trial_live_capital_enabled")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="trial_summary"))
    return unique_errors(errors)


def build_and_write_experimental_paper_trial(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[str]]:
    summary, outcomes = build_experimental_paper_trial(settings)
    errors = validate_experimental_paper_trial(summary, outcomes)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_paper_trial_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "trial_state": summary["status"],
        "trial_day": summary["trial_day"],
        "experimental_forward_outcome_count": len(outcomes),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(SUMMARY_ARTIFACT, summary)
    store.write_jsonl(OUTCOMES_ARTIFACT, outcomes)
    store.write_json(CHECK_ARTIFACT, checks)
    return summary, outcomes, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "OUTCOMES_ARTIFACT",
    "SUMMARY_ARTIFACT",
    "build_and_write_experimental_paper_trial",
    "build_experimental_paper_trial",
    "validate_experimental_paper_trial",
]
