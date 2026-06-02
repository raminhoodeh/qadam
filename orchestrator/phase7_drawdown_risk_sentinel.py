"""Q7-11 Phase 7 Demo Proof drawdown and risk sentinel.

This stage consumes the Q7-10 performance evaluator and records whether the
20 percent max drawdown cap has been breached. It can freeze new Phase 7 proof
trades when the cap is breached, but it cannot grant proof credit, certify the
run, mutate strategy or policy, call broker routes, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
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
from orchestrator.phase7_performance_evaluator import (
    PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT,
    build_phase7_performance_evaluator,
    phase7_performance_evaluator_paths,
    validate_phase7_performance_evaluator,
    write_phase7_performance_evaluator,
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


PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION = 1
PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT = (
    "phase7_drawdown_risk_sentinel.json"
)
PHASE7_DRAWDOWN_RISK_SENTINEL_HISTORY = "phase7_drawdown_risk_sentinel_history.jsonl"
PHASE7_DRAWDOWN_RISK_SENTINEL_EVENT_LOG = "phase7_drawdown_risk_sentinel_events.jsonl"
PHASE7_DRAWDOWN_RISK_SENTINEL_EVENT_TYPE = PHASE7_EVENT_TYPES["risk_halt"]
PHASE7_DRAWDOWN_RISK_SENTINEL_COMPONENT = "phase7_drawdown_risk_sentinel"

PHASE7_DRAWDOWN_RISK_SENTINEL_BOUNDARY = (
    "Q7-11 records the Phase 7 drawdown and risk-halt sentinel only from Q7-10 "
    "performance evaluation data. It can compute realized drawdown, track "
    "unrealized drawdown availability, compare combined drawdown against the "
    "20 percent cap, and freeze new Phase 7 proof-trade staging/submission "
    "when the cap is breached, but it cannot certify Phase 7, cannot grant "
    "Phase 7 proof credit, cannot create proof trades, cannot call broker "
    "POST routes, cannot call Alpaca POST routes, cannot write prediction-"
    "market or crypto-perps orders, cannot mutate policy or strategies, cannot "
    "enable live capital, and cannot permit manual trade-level overrides."
)

PHASE7_DRAWDOWN_RISK_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_10_performance_evaluator_valid",
    "q7_11_drawdown_stage_allowed",
    "source_trade_metrics_present_or_no_sample",
    "peak_equity_computed",
    "current_equity_computed",
    "realized_drawdown_computed",
    "unrealized_drawdown_tracked",
    "combined_drawdown_computed",
    "drawdown_cap_checked",
    "risk_halt_state_recorded",
    "breach_freezes_new_proof_trades",
    "review_required_when_breached",
    "certification_blocks_unresolved_breach",
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


def phase7_drawdown_risk_sentinel_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT,
        runtime / PHASE7_DRAWDOWN_RISK_SENTINEL_HISTORY,
        runtime / PHASE7_DRAWDOWN_RISK_SENTINEL_EVENT_LOG,
    )


def _performance_evaluator(settings: Settings) -> dict[str, Any]:
    performance_path, _, _ = phase7_performance_evaluator_paths(settings)
    if performance_path.exists():
        return _read_json(performance_path)
    performance = build_phase7_performance_evaluator(settings=settings)
    _, _, _, written = write_phase7_performance_evaluator(
        performance,
        settings=settings,
        record_event=True,
    )
    return written


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


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _closed_at(record: dict[str, Any]) -> datetime:
    value = record.get("closed_at") or record.get("generated_at")
    if value:
        try:
            parsed = datetime.fromisoformat(str(value))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _drawdown_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION,
        "source_performance_evaluator_required": True,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "realized_drawdown_required": True,
        "unrealized_drawdown_required_when_open_positions_exist": True,
        "combined_drawdown_required": True,
        "breach_operator": "greater_than_max_drawdown_fraction",
        "breach_freezes_new_proof_trades": True,
        "risk_halt_event_required_when_breached": True,
        "risk_halt_review_required_when_breached": True,
        "unresolved_breach_blocks_phase7_certification": True,
        "risk_halt_scope": "freeze_new_phase7_proof_trades_only",
        "existing_lifecycle_closeout_allowed": True,
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


def _authority_ledger(
    *,
    stage_recorded: bool,
    new_proof_trades_frozen: bool,
) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    if stage_recorded:
        defaults["phase7_proof_lifecycle_write_allowed"] = True
        defaults["phase7_postmortem_write_allowed"] = True
        defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            defaults["phase7_test_mode_auto_approval_allowed"] = True
            defaults["phase7_proof_order_staging_allowed"] = True
            defaults["phase7_proof_trade_submission_allowed"] = True
    grants = [field for field in PHASE7_AUTHORITY_FLAGS if defaults[field]]
    return {
        "authority_schema_version": PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION,
        "stage": "Q7-11",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": len(grants),
        "explicit_authority_grants": grants,
        "q7_12_override_detector_stage_allowed": stage_recorded,
        "risk_halt_write_allowed": stage_recorded,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        **defaults,
        "boundary": PHASE7_DRAWDOWN_RISK_SENTINEL_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_performance_evaluator.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-10-performance-evaluator-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}"
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(performance: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    performance_errors = validate_phase7_performance_evaluator(performance)
    if performance_errors:
        blockers.append("phase7_performance_evaluator_validation_errors")
    if performance.get("performance_evaluator_recorded") is not True:
        blockers.append("phase7_performance_evaluator_not_recorded")
    if performance.get("q7_11_drawdown_risk_sentinel_stage_allowed") is not True:
        blockers.append("q7_11_drawdown_risk_sentinel_stage_not_allowed")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if performance.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _source_trade_metric_records(performance: dict[str, Any]) -> list[dict[str, Any]]:
    records = performance.get("trade_metric_records", [])
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict) and record.get("status") == "evaluated"
    ]


def _equity_summary(
    records: list[dict[str, Any]],
    *,
    unrealized_pnl_gbp: float = 0.0,
) -> dict[str, Any]:
    ordered = sorted(records, key=_closed_at)
    equity = PHASE7_PAPER_ACCOUNT_STARTING_GBP
    peak = equity
    max_realized_drawdown = 0.0
    equity_points: list[dict[str, Any]] = []
    for index, record in enumerate(ordered, start=1):
        pnl = _float(record.get("net_pnl_after_costs_gbp"), 0.0)
        equity = round(equity + pnl, 6)
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_realized_drawdown = max(max_realized_drawdown, drawdown)
        equity_points.append(
            {
                "sequence": index,
                "closed_at": _closed_at(record).isoformat(),
                "source_closed_trade_ref": record.get("source_closed_trade_ref"),
                "net_pnl_after_costs_gbp": _round(pnl, 4),
                "equity_after_trade_gbp": _round(equity, 4),
                "peak_equity_gbp": _round(peak, 4),
                "realized_drawdown_fraction": _round(drawdown, 6) or 0.0,
            }
        )
    mark_to_market_equity = equity + unrealized_pnl_gbp
    unrealized_drawdown = (peak - mark_to_market_equity) / peak if peak else 0.0
    unrealized_drawdown = max(0.0, unrealized_drawdown)
    combined_drawdown = max(max_realized_drawdown, unrealized_drawdown)
    breached = combined_drawdown > PHASE7_MAX_DRAWDOWN_FRACTION
    return {
        "equity_curve_points": equity_points,
        "equity_curve_point_count": len(equity_points),
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "realized_pnl_after_costs_gbp": _round(
            equity - PHASE7_PAPER_ACCOUNT_STARTING_GBP,
            4,
        ),
        "unrealized_pnl_gbp": _round(unrealized_pnl_gbp, 4),
        "current_equity_gbp": _round(equity, 4),
        "mark_to_market_equity_gbp": _round(mark_to_market_equity, 4),
        "peak_equity_gbp": _round(peak, 4),
        "realized_drawdown_fraction_observed": _round(max_realized_drawdown, 6) or 0.0,
        "unrealized_drawdown_fraction_observed": _round(unrealized_drawdown, 6) or 0.0,
        "max_drawdown_fraction_observed": _round(combined_drawdown, 6) or 0.0,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "drawdown_within_cap": not breached,
        "drawdown_cap_breached": breached,
        "drawdown_breach_count": 1 if breached else 0,
        "drawdown_breach_detected_at": _now() if breached else None,
        "drawdown_state": (
            "breached_unresolved"
            if breached
            else "within_cap"
            if records
            else "no_sample_within_cap"
        ),
    }


def build_phase7_drawdown_risk_sentinel(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    performance = _performance_evaluator(settings)
    blockers = _preflight_blockers(performance)
    stage_recorded = not blockers
    records = _source_trade_metric_records(performance)
    open_position_count = _int(performance.get("open_position_count"))
    unrealized_pnl_gbp = _float(performance.get("unrealized_pnl_gbp"), 0.0)
    unrealized_required = open_position_count > 0
    unrealized_available = not unrealized_required
    summary = _equity_summary(records, unrealized_pnl_gbp=unrealized_pnl_gbp)
    drawdown_breached = bool(summary["drawdown_cap_breached"])
    new_proof_trades_frozen = stage_recorded and drawdown_breached
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    if stage_recorded:
        authority_defaults["phase7_proof_lifecycle_write_allowed"] = True
        authority_defaults["phase7_postmortem_write_allowed"] = True
        authority_defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            authority_defaults["phase7_test_mode_auto_approval_allowed"] = True
            authority_defaults["phase7_proof_order_staging_allowed"] = True
            authority_defaults["phase7_proof_trade_submission_allowed"] = True
    status = "ready_no_drawdown_sample"
    stage_status = "drawdown_sentinel_ready_no_closed_trades"
    if records:
        status = "drawdown_within_cap"
        stage_status = "drawdown_sentinel_within_cap"
    if drawdown_breached:
        status = "risk_halt_active"
        stage_status = "drawdown_breach_risk_halt_active"
    if not stage_recorded:
        status = "blocked"
        stage_status = "drawdown_risk_sentinel_blocked"
    checks = [
        _check(
            "q7_10_performance_evaluator_valid",
            not validate_phase7_performance_evaluator(performance),
        ),
        _check("q7_11_drawdown_stage_allowed", stage_recorded),
        _check("source_trade_metrics_present_or_no_sample", True),
        _check("peak_equity_computed", summary["peak_equity_gbp"] is not None),
        _check("current_equity_computed", summary["current_equity_gbp"] is not None),
        _check("realized_drawdown_computed", True),
        _check(
            "unrealized_drawdown_tracked",
            unrealized_available or not stage_recorded,
            detail={"open_position_count": open_position_count},
        ),
        _check("combined_drawdown_computed", True),
        _check("drawdown_cap_checked", True),
        _check("risk_halt_state_recorded", True),
        _check(
            "breach_freezes_new_proof_trades",
            (not drawdown_breached) or new_proof_trades_frozen,
        ),
        _check("review_required_when_breached", True),
        _check("certification_blocks_unresolved_breach", True),
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
    if failed_checks and stage_recorded:
        blockers = sorted(set([*blockers, *failed_checks]))
        stage_recorded = False
        status = "blocked"
        stage_status = "drawdown_risk_sentinel_blocked"
    artifact = {
        "schema_version": PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_drawdown_risk_sentinel",
        "artifact_id": "phase7:q7-11:drawdown-risk-sentinel",
        "phase": "Q7",
        "stage": "Q7-11",
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
        "authority_ledger": _authority_ledger(
            stage_recorded=stage_recorded,
            new_proof_trades_frozen=new_proof_trades_frozen,
        ),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "drawdown_policy": _drawdown_policy(),
        "source_trade_metric_records": records,
        "boundary": PHASE7_DRAWDOWN_RISK_SENTINEL_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_performance_artifact_id": performance.get("artifact_id"),
        "source_performance_status": performance.get("status"),
        "source_performance_stage_status": performance.get("stage_status"),
        "source_performance_recorded": performance.get("performance_evaluator_recorded")
        is True,
        "source_closed_proof_trade_count": _int(
            performance.get("closed_proof_trade_count")
        ),
        "source_evaluated_trade_count": _int(performance.get("evaluated_trade_count")),
        "source_performance_metric_record_count": _int(
            performance.get("performance_metric_record_count")
        ),
        "source_performance_drawdown_within_cap": performance.get(
            "drawdown_within_cap"
        )
        is True,
        "source_performance_max_drawdown_fraction_observed": _float(
            performance.get("max_drawdown_fraction_observed"),
            0.0,
        ),
        "q7_11_drawdown_risk_sentinel_stage_allowed": (
            performance.get("q7_11_drawdown_risk_sentinel_stage_allowed") is True
        ),
        "q7_12_override_detector_stage_allowed": stage_recorded,
        "drawdown_sentinel_recorded": stage_recorded,
        "risk_halt_write_allowed": stage_recorded,
        "risk_halt_allowed": stage_recorded,
        "risk_halt_required": drawdown_breached,
        "risk_halt_active": new_proof_trades_frozen,
        "risk_halt_event_required": drawdown_breached,
        "risk_halt_event_recorded": False,
        "risk_halt_review_required": drawdown_breached,
        "risk_halt_review_state": (
            "required_pending_review" if drawdown_breached else "not_required"
        ),
        "risk_halt_unresolved": drawdown_breached,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        "new_proof_trade_freeze_active": new_proof_trades_frozen,
        "new_proof_trade_freeze_reason": (
            "max_drawdown_cap_breached" if drawdown_breached else None
        ),
        "new_proof_order_staging_allowed": stage_recorded
        and not new_proof_trades_frozen,
        "new_proof_trade_submission_allowed": stage_recorded
        and not new_proof_trades_frozen,
        "existing_lifecycle_closeout_allowed": stage_recorded,
        "open_position_count": open_position_count,
        "unrealized_mark_to_market_required": unrealized_required,
        "unrealized_mark_to_market_available": unrealized_available,
        "phase7_certification_blocked_by_drawdown": drawdown_breached,
        "phase7_certification_blocked_by_unresolved_risk_halt": drawdown_breached,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "paper_order_submitted_count": _int(performance.get("paper_order_submitted_count")),
        "proof_trade_created_count": _int(performance.get("proof_trade_created_count")),
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-12 Override Detector",
        **summary,
    }
    artifact["validation_errors"] = validate_phase7_drawdown_risk_sentinel(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "drawdown_risk_sentinel_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("drawdown_sentinel_recorded") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_drawdown_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-11":
        errors.append("phase7_drawdown_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_drawdown_authority_count_mismatch")
    expected_true = {
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    }
    if stage_recorded and not frozen:
        expected_true.update(
            {
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
            }
        )
    expected_grants = len(expected_true) if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_drawdown_explicit_authority_grant_count_invalid")
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_drawdown_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_drawdown_ledger_authority_invalid:{field}")
    if ledger.get("risk_halt_write_allowed") is not stage_recorded:
        errors.append("phase7_drawdown_risk_halt_write_ledger_mismatch")
    if ledger.get("new_proof_trades_frozen") is not frozen:
        errors.append("phase7_drawdown_freeze_ledger_mismatch")
    allowed_count_fields = {"paper_order_submitted_count", "proof_trade_created_count"}
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_drawdown_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("proof_trade_created_count")):
                errors.append(f"phase7_drawdown_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_drawdown_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        _int(artifact.get(field))
        for field in PHASE7_UNSAFE_COUNT_FIELDS
        if field not in allowed_count_fields
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_drawdown_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_drawdown_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("drawdown_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_drawdown_policy_missing"]
    for field in (
        "source_performance_evaluator_required",
        "realized_drawdown_required",
        "unrealized_drawdown_required_when_open_positions_exist",
        "combined_drawdown_required",
        "breach_freezes_new_proof_trades",
        "risk_halt_event_required_when_breached",
        "risk_halt_review_required_when_breached",
        "unresolved_breach_blocks_phase7_certification",
        "existing_lifecycle_closeout_allowed",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_drawdown_policy_missing_true:{field}")
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
            errors.append(f"phase7_drawdown_policy_forbidden:{field}")
    if float(policy.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_drawdown_policy_cap_invalid")
    if policy.get("risk_halt_scope") != "freeze_new_phase7_proof_trades_only":
        errors.append("phase7_drawdown_policy_scope_invalid")
    return errors


def validate_phase7_drawdown_risk_sentinel(artifact: dict[str, Any]) -> list[str]:
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
        "drawdown_policy",
        "source_trade_metric_records",
        "boundary",
        "source_performance_status",
        "source_closed_proof_trade_count",
        "source_evaluated_trade_count",
        "source_performance_metric_record_count",
        "source_performance_drawdown_within_cap",
        "source_performance_max_drawdown_fraction_observed",
        "q7_11_drawdown_risk_sentinel_stage_allowed",
        "q7_12_override_detector_stage_allowed",
        "drawdown_sentinel_recorded",
        "risk_halt_write_allowed",
        "risk_halt_allowed",
        "risk_halt_required",
        "risk_halt_active",
        "risk_halt_event_required",
        "risk_halt_event_recorded",
        "risk_halt_review_required",
        "risk_halt_review_state",
        "risk_halt_unresolved",
        "new_proof_trades_frozen",
        "new_proof_trade_freeze_active",
        "new_proof_trade_freeze_reason",
        "new_proof_order_staging_allowed",
        "new_proof_trade_submission_allowed",
        "existing_lifecycle_closeout_allowed",
        "open_position_count",
        "unrealized_mark_to_market_required",
        "unrealized_mark_to_market_available",
        "equity_curve_points",
        "equity_curve_point_count",
        "paper_account_starting_gbp",
        "current_equity_gbp",
        "mark_to_market_equity_gbp",
        "peak_equity_gbp",
        "realized_pnl_after_costs_gbp",
        "unrealized_pnl_gbp",
        "realized_drawdown_fraction_observed",
        "unrealized_drawdown_fraction_observed",
        "max_drawdown_fraction_observed",
        "max_drawdown_fraction",
        "drawdown_within_cap",
        "drawdown_cap_breached",
        "drawdown_breach_count",
        "drawdown_state",
        "phase7_certification_blocked_by_drawdown",
        "phase7_certification_blocked_by_unresolved_risk_halt",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "mature_closed_trade_benchmark",
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
        "checks",
        "failed_checks",
        "failed_check_count",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_drawdown_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION:
        errors.append("phase7_drawdown_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_drawdown_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_drawdown_risk_sentinel":
        errors.append("phase7_drawdown_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-11":
        errors.append("phase7_drawdown_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_drawdown_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_drawdown_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_drawdown_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_drawdown_blocker_count_mismatch")
    checks = artifact.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_drawdown_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if artifact.get("failed_checks") != failed_checks:
        errors.append("phase7_drawdown_failed_checks_mismatch")
    if artifact.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_drawdown_failed_check_count_mismatch")
    if tuple(check.get("name") for check in checks if isinstance(check, dict)) != (
        PHASE7_DRAWDOWN_RISK_REQUIRED_CHECKS
    ):
        errors.append("phase7_drawdown_required_checks_invalid")

    stage_recorded = artifact.get("drawdown_sentinel_recorded") is True
    drawdown_breached = artifact.get("drawdown_cap_breached") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_drawdown_sample",
            "drawdown_within_cap",
            "risk_halt_active",
        }:
            errors.append("phase7_drawdown_status_invalid")
        if artifact.get("stage_status") not in {
            "drawdown_sentinel_ready_no_closed_trades",
            "drawdown_sentinel_within_cap",
            "drawdown_breach_risk_halt_active",
        }:
            errors.append("phase7_drawdown_stage_status_invalid")
        if blockers:
            errors.append("phase7_drawdown_recorded_with_blockers")
        if artifact.get("q7_12_override_detector_stage_allowed") is not True:
            errors.append("q7_12_override_detector_not_allowed")
        if artifact.get("risk_halt_write_allowed") is not True:
            errors.append("phase7_drawdown_risk_halt_write_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_drawdown_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_drawdown_blocked_without_blockers")
        if artifact.get("q7_12_override_detector_stage_allowed") is not False:
            errors.append("q7_12_stage_allowed_while_blocked")
    if artifact.get("q7_11_drawdown_risk_sentinel_stage_allowed") is not True:
        errors.append("q7_11_drawdown_risk_sentinel_not_allowed")

    records = artifact.get("source_trade_metric_records", [])
    if not isinstance(records, list):
        errors.append("phase7_drawdown_source_records_not_list")
        records = []
    summary = _equity_summary(
        [record for record in records if isinstance(record, dict)],
        unrealized_pnl_gbp=_float(artifact.get("unrealized_pnl_gbp"), 0.0),
    )
    summary_fields = (
        "equity_curve_point_count",
        "paper_account_starting_gbp",
        "realized_pnl_after_costs_gbp",
        "unrealized_pnl_gbp",
        "current_equity_gbp",
        "mark_to_market_equity_gbp",
        "peak_equity_gbp",
        "realized_drawdown_fraction_observed",
        "unrealized_drawdown_fraction_observed",
        "max_drawdown_fraction_observed",
        "max_drawdown_fraction",
        "drawdown_within_cap",
        "drawdown_cap_breached",
        "drawdown_breach_count",
        "drawdown_state",
    )
    for field in summary_fields:
        if artifact.get(field) != summary.get(field):
            errors.append(f"phase7_drawdown_metric_mismatch:{field}")
    if artifact.get("equity_curve_point_count") != len(artifact.get("equity_curve_points", [])):
        errors.append("phase7_drawdown_equity_curve_count_mismatch")
    if artifact.get("source_evaluated_trade_count") != len(records):
        errors.append("phase7_drawdown_source_evaluated_count_mismatch")
    if artifact.get("source_closed_proof_trade_count") != len(records):
        errors.append("phase7_drawdown_source_closed_count_mismatch")
    if artifact.get("source_performance_metric_record_count") != len(records):
        errors.append("phase7_drawdown_source_metric_count_mismatch")

    if drawdown_breached:
        if artifact.get("drawdown_within_cap") is not False:
            errors.append("phase7_drawdown_breached_but_within_cap")
        if artifact.get("risk_halt_required") is not True:
            errors.append("phase7_drawdown_breach_halt_not_required")
        if artifact.get("risk_halt_active") is not True:
            errors.append("phase7_drawdown_breach_halt_not_active")
        if frozen is not True:
            errors.append("phase7_drawdown_breach_not_frozen")
        if artifact.get("new_proof_order_staging_allowed") is not False:
            errors.append("phase7_drawdown_breach_staging_not_frozen")
        if artifact.get("new_proof_trade_submission_allowed") is not False:
            errors.append("phase7_drawdown_breach_submission_not_frozen")
        if artifact.get("risk_halt_review_required") is not True:
            errors.append("phase7_drawdown_breach_review_not_required")
        if artifact.get("risk_halt_review_state") != "required_pending_review":
            errors.append("phase7_drawdown_breach_review_state_invalid")
        if artifact.get("phase7_certification_blocked_by_drawdown") is not True:
            errors.append("phase7_drawdown_breach_not_blocking_certification")
        if artifact.get("phase7_certification_blocked_by_unresolved_risk_halt") is not True:
            errors.append("phase7_drawdown_unresolved_halt_not_blocking")
    else:
        if artifact.get("drawdown_within_cap") is not True:
            errors.append("phase7_drawdown_not_breached_but_not_within_cap")
        if artifact.get("risk_halt_required") is not False:
            errors.append("phase7_drawdown_halt_required_without_breach")
        if artifact.get("risk_halt_active") is not False:
            errors.append("phase7_drawdown_halt_active_without_breach")
        if frozen is not False:
            errors.append("phase7_drawdown_frozen_without_breach")
        if stage_recorded and artifact.get("new_proof_order_staging_allowed") is not True:
            errors.append("phase7_drawdown_staging_frozen_without_breach")
        if stage_recorded and artifact.get("new_proof_trade_submission_allowed") is not True:
            errors.append("phase7_drawdown_submission_frozen_without_breach")
        if artifact.get("risk_halt_review_required") is not False:
            errors.append("phase7_drawdown_review_required_without_breach")
        if artifact.get("risk_halt_review_state") != "not_required":
            errors.append("phase7_drawdown_review_state_invalid")
        if artifact.get("phase7_certification_blocked_by_drawdown") is not False:
            errors.append("phase7_drawdown_blocks_certification_without_breach")
        if artifact.get("phase7_certification_blocked_by_unresolved_risk_halt") is not False:
            errors.append("phase7_drawdown_unresolved_halt_without_breach")
    if _int(artifact.get("open_position_count")) > 0:
        if artifact.get("unrealized_mark_to_market_required") is not True:
            errors.append("phase7_drawdown_unrealized_requirement_missing")
        if artifact.get("unrealized_mark_to_market_available") is not True:
            errors.append("phase7_drawdown_unrealized_mark_to_market_missing")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_drawdown_starting_equity_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_drawdown_cap_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_drawdown_mature_benchmark_mismatch")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
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
            errors.append(f"phase7_drawdown_count_nonzero:{count_field}")
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
            errors.append(f"phase7_drawdown_forbidden:{field}")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_drawdown_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_drawdown_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_drawdown_qctrl_role_invalid")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_drawdown_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_drawdown_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_drawdown_proof_contract_phase5_reuse_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_drawdown_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_drawdown_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_drawdown_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_drawdown_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records the Phase 7 drawdown and risk-halt sentinel only",
        "20 percent cap",
        "freeze new Phase 7 proof-trade staging/submission",
        "cannot certify Phase 7",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_drawdown_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_drawdown_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_drawdown_event_log_count_invalid")
        if artifact.get("risk_halt_active") is True and (
            artifact.get("risk_halt_event_recorded") is not True
        ):
            errors.append("phase7_drawdown_active_halt_event_not_recorded")
    return sorted(set(errors))


def attach_phase7_drawdown_risk_sentinel_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path
        or (_runtime_dir(settings) / PHASE7_DRAWDOWN_RISK_SENTINEL_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_DRAWDOWN_RISK_SENTINEL_EVENT_TYPE,
        PHASE7_DRAWDOWN_RISK_SENTINEL_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "drawdown_state": output.get("drawdown_state"),
            "max_drawdown_fraction_observed": output.get(
                "max_drawdown_fraction_observed"
            ),
            "drawdown_within_cap": output.get("drawdown_within_cap"),
            "risk_halt_active": output.get("risk_halt_active"),
            "new_proof_trades_frozen": output.get("new_proof_trades_frozen"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["risk_halt_event_recorded"] = output.get("risk_halt_active") is True
    output["validation_errors"] = validate_phase7_drawdown_risk_sentinel(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "drawdown_risk_sentinel_validation_error"
    return output, [entry]


def write_phase7_drawdown_risk_sentinel(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_drawdown_risk_sentinel_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_drawdown_risk_sentinel_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_drawdown_risk_sentinel(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "drawdown_risk_sentinel_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_drawdown_risk_sentinel(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "drawdown_risk_sentinel_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_closed_proof_trade_count": output.get(
            "source_closed_proof_trade_count"
        ),
        "source_evaluated_trade_count": output.get("source_evaluated_trade_count"),
        "max_drawdown_fraction_observed": output.get("max_drawdown_fraction_observed"),
        "drawdown_within_cap": output.get("drawdown_within_cap"),
        "risk_halt_active": output.get("risk_halt_active"),
        "new_proof_trades_frozen": output.get("new_proof_trades_frozen"),
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
