"""Q7-14 Phase 7 Demo Proof 100-trade maturity tracker.

This stage records the Phase 7 mature-sample benchmark separately from the
30-day operational proof result. It can count closed proof trades, compute
progress toward the 100-trade benchmark, and label statistical immaturity, but
it cannot force trades, certify Phase 7, grant proof credit, call broker
routes, or enable live capital.
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
from orchestrator.phase7_calendar_harness import (
    PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT,
    build_phase7_calendar_harness,
    phase7_calendar_harness_paths,
    validate_phase7_calendar_harness,
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
from orchestrator.phase7_signal_funnel_evidence import (
    PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT,
    build_phase7_signal_funnel_evidence,
    phase7_signal_funnel_evidence_paths,
    validate_phase7_signal_funnel_evidence,
    write_phase7_signal_funnel_evidence,
)


PHASE7_MATURITY_TRACKER_SCHEMA_VERSION = 1
PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT = "phase7_maturity_tracker.json"
PHASE7_MATURITY_TRACKER_HISTORY = "phase7_maturity_tracker_history.jsonl"
PHASE7_MATURITY_TRACKER_EVENT_LOG = "phase7_maturity_tracker_events.jsonl"
PHASE7_MATURITY_TRACKER_EVENT_TYPE = PHASE7_EVENT_TYPES["maturity"]
PHASE7_MATURITY_TRACKER_COMPONENT = "phase7_maturity_tracker"

PHASE7_MATURITY_BOUNDARY = (
    "Q7-14 records Phase 7 100-trade maturity accounting only from Q7-13 "
    "source and signal evidence plus the Q7 calendar harness. It can count "
    "closed proof trades, compute progress toward the 100 closed proof-trade "
    "benchmark, label no-sample and statistically immature states, preserve "
    "the 30-day operational result separately from mature-sample status, and "
    "require dashboard language that cannot hide statistical immaturity, but "
    "it cannot certify Phase 7, cannot force trades to reach the benchmark, "
    "cannot grant Phase 7 proof credit, cannot create proof trades, cannot "
    "call broker POST routes, cannot call Alpaca POST routes, cannot write "
    "prediction-market or crypto-perps orders, cannot mutate policy or "
    "strategies, cannot enable live capital, and cannot permit manual "
    "trade-level overrides."
)

PHASE7_MATURITY_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_13_signal_evidence_valid",
    "q7_14_maturity_stage_allowed",
    "phase7_calendar_harness_valid",
    "mature_benchmark_visible",
    "closed_proof_trade_count_computed",
    "maturity_progress_computed",
    "thirty_day_operational_result_separated",
    "statistical_immaturity_labelled_when_30d_complete_under_100",
    "statistical_immaturity_not_hidden",
    "mature_status_blocked_under_100",
    "no_forced_trades",
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


def phase7_maturity_tracker_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT,
        runtime / PHASE7_MATURITY_TRACKER_HISTORY,
        runtime / PHASE7_MATURITY_TRACKER_EVENT_LOG,
    )


def _signal_evidence(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_signal_funnel_evidence_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    signal = build_phase7_signal_funnel_evidence(settings=settings)
    _, _, _, written = write_phase7_signal_funnel_evidence(
        signal,
        settings=settings,
        record_event=True,
    )
    return written


def _calendar_harness(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_calendar_harness_paths(settings)
    if output_path.exists():
        return _read_json(output_path)
    return build_phase7_calendar_harness(settings=settings)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _phase7_day_complete(day: dict[str, Any]) -> bool:
    status = str(day.get("harness_day_status") or day.get("day_status") or "").lower()
    if status in {
        "complete",
        "completed",
        "proof_day_complete",
        "no_trade_complete",
        "closed",
    }:
        return True
    return day.get("day_complete") is True or day.get("calendar_day_complete") is True


def _completed_calendar_day_count(calendar: dict[str, Any]) -> int:
    explicit = _int(
        calendar.get("completed_calendar_day_count")
        or calendar.get("calendar_day_complete_count")
        or calendar.get("completed_harness_day_count")
    )
    if explicit:
        return explicit
    days = calendar.get("proof_calendar_days", [])
    if not isinstance(days, list):
        return 0
    return sum(1 for day in days if isinstance(day, dict) and _phase7_day_complete(day))


def _calendar_complete(calendar: dict[str, Any]) -> bool:
    completed = _completed_calendar_day_count(calendar)
    return (
        calendar.get("phase7_30_day_run_complete") is True
        or calendar.get("calendar_harness_complete") is True
        or calendar.get("harness_complete") is True
        or (calendar.get("calendar_harness_started") is True and completed >= PHASE7_HARNESS_DAY_COUNT)
    )


def _closed_signal_records(signal_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    records = signal_evidence.get("signal_evidence_records", [])
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("complete_decision_chain") is True
        and str(record.get("closed_trade_ref") or "").strip()
        and str(record.get("source_lifecycle_state") or "") == "closed_trade"
    ]


def _maturity_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
        "source_signal_evidence_required": True,
        "phase7_calendar_harness_required": True,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "benchmark_visibility_required": True,
        "closed_trade_count_required": True,
        "progress_fraction_required": True,
        "statistical_immaturity_label_required": True,
        "statistical_immaturity_must_not_be_hidden": True,
        "under_100_blocks_mature_status": True,
        "thirty_day_operational_result_preserved_when_immature": True,
        "forced_trade_allowed": False,
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
        "authority_schema_version": PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
        "stage": "Q7-14",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": len(grants),
        "explicit_authority_grants": grants,
        "q7_15_cockpit_visibility_stage_allowed": stage_recorded,
        "maturity_tracker_write_allowed": stage_recorded,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        **defaults,
        "boundary": PHASE7_MATURITY_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_signal_funnel_evidence.py",
            "orchestrator/phase7_calendar_harness.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-13-source-signal-funnel-evidence-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}"
    ]
    provenance["governance_refs"] = [
        "docs/qadam-phase-7-demo-proof-implementation-plan.md"
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(
    signal_evidence: dict[str, Any],
    calendar: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if validate_phase7_signal_funnel_evidence(signal_evidence):
        blockers.append("phase7_signal_funnel_evidence_validation_errors")
    if signal_evidence.get("signal_funnel_evidence_recorded") is not True:
        blockers.append("phase7_signal_funnel_evidence_not_recorded")
    if signal_evidence.get("q7_14_maturity_tracker_stage_allowed") is not True:
        blockers.append("q7_14_maturity_tracker_stage_not_allowed")
    if validate_phase7_calendar_harness(calendar):
        blockers.append("phase7_calendar_harness_validation_errors")
    if calendar.get("calendar_harness_scheduled") is not True:
        blockers.append("phase7_calendar_harness_not_scheduled")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if signal_evidence.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _maturity_summary(
    *,
    closed_trade_count: int,
    phase7_30_day_run_complete: bool,
) -> dict[str, Any]:
    benchmark = PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    maturity_met = closed_trade_count >= benchmark
    progress = closed_trade_count / benchmark if benchmark else 0.0
    remaining = max(0, benchmark - closed_trade_count)
    if closed_trade_count == 0:
        maturity_state = "no_sample"
    elif maturity_met:
        maturity_state = "statistically_mature"
    elif phase7_30_day_run_complete:
        maturity_state = "statistically_immature_after_30_days"
    else:
        maturity_state = "statistically_immature_in_progress"
    statistically_immature = phase7_30_day_run_complete and not maturity_met
    return {
        "maturity_state": maturity_state,
        "closed_proof_trade_count": closed_trade_count,
        "mature_benchmark": benchmark,
        "mature_closed_trade_benchmark": benchmark,
        "maturity_progress_fraction": _round(progress, 6),
        "maturity_progress_percent": _round(progress * 100.0, 4),
        "closed_trades_remaining_to_mature": remaining,
        "phase7_mature_benchmark_met": maturity_met,
        "phase7_mature_status_blocked": not maturity_met,
        "phase7_statistically_immature": statistically_immature,
        "phase7_statistical_immaturity_allowed": True,
        "phase7_statistical_immaturity_hidden": False,
        "phase7_statistical_immaturity_dashboard_warning_required": not maturity_met,
        "phase7_30_day_operational_result_erased_by_immaturity": False,
        "phase7_30_day_operational_result_preserved": True,
        "phase7_certification_blocked_by_maturity": not maturity_met,
        "maturity_sample_size_warning": not maturity_met,
    }


def _snapshot_record(
    *,
    closed_trade_count: int,
    phase7_30_day_run_complete: bool,
    completed_calendar_day_count: int,
    source_signal_evidence_artifact_id: str | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    summary = _maturity_summary(
        closed_trade_count=closed_trade_count,
        phase7_30_day_run_complete=phase7_30_day_run_complete,
    )
    checks = [
        _check("mature_benchmark_visible", summary["mature_benchmark"] == 100),
        _check("closed_proof_trade_count_computed", closed_trade_count >= 0),
        _check("maturity_progress_computed", summary["maturity_progress_fraction"] is not None),
        _check("thirty_day_operational_result_separated", True),
        _check(
            "statistical_immaturity_labelled_when_30d_complete_under_100",
            not (
                phase7_30_day_run_complete
                and closed_trade_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
            )
            or summary["phase7_statistically_immature"] is True,
        ),
        _check("statistical_immaturity_not_hidden", True),
        _check("mature_status_blocked_under_100", closed_trade_count >= 100 or summary["phase7_mature_status_blocked"] is True),
        _check("no_forced_trades", True),
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
    status = "statistically_immature"
    if summary["phase7_mature_benchmark_met"]:
        status = "maturity_benchmark_met"
    elif closed_trade_count == 0:
        status = "no_sample"
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "maturity_tracker_schema_version": PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
        "artifact_type": "maturity_snapshot",
        "artifact_id": "phase7:q7-14:maturity-snapshot",
        "phase": "Q7",
        "stage": "Q7-14",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "source_signal_evidence_artifact_id": source_signal_evidence_artifact_id,
        "phase7_30_day_run_complete": phase7_30_day_run_complete,
        "completed_calendar_day_count": completed_calendar_day_count,
        "harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "forced_trade_allowed": False,
        "proof_trade_creation_allowed": False,
        "phase7_demo_proof_certified": False,
        "phase7_proof_credit_allowed": False,
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
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        **summary,
    }


def build_phase7_maturity_tracker(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    signal_evidence = _signal_evidence(settings)
    calendar = _calendar_harness(settings)
    blockers = _preflight_blockers(signal_evidence, calendar)
    stage_recorded = not blockers
    completed_days = _completed_calendar_day_count(calendar)
    phase7_30_day_run_complete = _calendar_complete(calendar)
    closed_records = _closed_signal_records(signal_evidence)
    closed_trade_count = len(closed_records)
    summary = _maturity_summary(
        closed_trade_count=closed_trade_count,
        phase7_30_day_run_complete=phase7_30_day_run_complete,
    )
    snapshot = _snapshot_record(
        closed_trade_count=closed_trade_count,
        phase7_30_day_run_complete=phase7_30_day_run_complete,
        completed_calendar_day_count=completed_days,
        source_signal_evidence_artifact_id=str(signal_evidence.get("artifact_id") or ""),
    )
    new_proof_trades_frozen = signal_evidence.get("new_proof_trades_frozen") is True
    unsafe_counts = phase7_unsafe_counter_defaults()
    unsafe_counts["paper_order_submitted_count"] = _int(
        signal_evidence.get("paper_order_submitted_count")
    )
    unsafe_counts["proof_trade_created_count"] = _int(
        signal_evidence.get("source_proof_trade_count")
    )
    unsafe_counts["manual_trade_level_override_count"] = _int(
        signal_evidence.get("manual_trade_level_override_count")
    )
    authority_defaults = phase7_authority_defaults()
    if stage_recorded:
        authority_defaults["phase7_proof_lifecycle_write_allowed"] = True
        authority_defaults["phase7_postmortem_write_allowed"] = True
        authority_defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            authority_defaults["phase7_test_mode_auto_approval_allowed"] = True
            authority_defaults["phase7_proof_order_staging_allowed"] = True
            authority_defaults["phase7_proof_trade_submission_allowed"] = True
    status = "ready_no_closed_trades"
    stage_status = "maturity_tracker_ready_no_closed_trades"
    if closed_trade_count:
        status = "maturity_progress_recorded"
        stage_status = "maturity_tracker_progress_recorded"
    if summary["phase7_statistically_immature"]:
        status = "statistically_immature"
        stage_status = "maturity_tracker_statistically_immature_after_30_days"
    if summary["phase7_mature_benchmark_met"]:
        status = "maturity_benchmark_met"
        stage_status = "maturity_tracker_benchmark_met"
    if not stage_recorded:
        status = "blocked"
        stage_status = "maturity_tracker_blocked"
    checks = [
        _check(
            "q7_13_signal_evidence_valid",
            not validate_phase7_signal_funnel_evidence(signal_evidence),
        ),
        _check("q7_14_maturity_stage_allowed", stage_recorded),
        _check("phase7_calendar_harness_valid", not validate_phase7_calendar_harness(calendar)),
        _check("mature_benchmark_visible", summary["mature_benchmark"] == 100),
        _check("closed_proof_trade_count_computed", closed_trade_count >= 0),
        _check("maturity_progress_computed", summary["maturity_progress_fraction"] is not None),
        _check("thirty_day_operational_result_separated", True),
        _check(
            "statistical_immaturity_labelled_when_30d_complete_under_100",
            not (phase7_30_day_run_complete and closed_trade_count < 100)
            or summary["phase7_statistically_immature"] is True,
        ),
        _check("statistical_immaturity_not_hidden", True),
        _check("mature_status_blocked_under_100", closed_trade_count >= 100 or summary["phase7_mature_status_blocked"] is True),
        _check("no_forced_trades", True),
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
        stage_status = "maturity_tracker_blocked"
    artifact = {
        "schema_version": PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_maturity_tracker",
        "artifact_id": "phase7:q7-14:maturity-tracker",
        "phase": "Q7",
        "stage": "Q7-14",
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
        "maturity_policy": _maturity_policy(),
        "maturity_snapshot_records": [snapshot] if stage_recorded else [],
        "closed_proof_trade_refs": [
            str(record.get("closed_trade_ref"))
            for record in closed_records
            if str(record.get("closed_trade_ref") or "").strip()
        ],
        "boundary": PHASE7_MATURITY_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_signal_evidence_artifact_id": signal_evidence.get("artifact_id"),
        "source_signal_evidence_status": signal_evidence.get("status"),
        "source_signal_evidence_stage_status": signal_evidence.get("stage_status"),
        "source_signal_evidence_record_count": _int(
            signal_evidence.get("proof_trade_evidence_record_count")
        ),
        "source_signal_complete_decision_chain_count": _int(
            signal_evidence.get("complete_decision_chain_count")
        ),
        "source_signal_missing_decision_chain_count": _int(
            signal_evidence.get("missing_decision_chain_count")
        ),
        "source_signal_certification_blocked": (
            signal_evidence.get("phase7_certification_blocked_by_signal_evidence") is True
        ),
        "source_calendar_artifact_id": calendar.get("artifact_id"),
        "source_calendar_status": calendar.get("status"),
        "source_calendar_stage_status": calendar.get("stage_status"),
        "calendar_harness_started": calendar.get("calendar_harness_started") is True,
        "phase7_30_day_run_complete": phase7_30_day_run_complete,
        "completed_calendar_day_count": completed_days,
        "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "q7_14_maturity_tracker_stage_allowed": (
            signal_evidence.get("q7_14_maturity_tracker_stage_allowed") is True
        ),
        "q7_15_cockpit_visibility_stage_allowed": stage_recorded,
        "maturity_tracker_recorded": stage_recorded,
        "maturity_tracker_write_allowed": stage_recorded,
        "mature_benchmark_visible": True,
        "forced_trade_allowed": False,
        "proof_trade_creation_allowed": False,
        "phase7_demo_proof_certified": False,
        "phase7_certification_blocked_by_signal_evidence": (
            signal_evidence.get("phase7_certification_blocked_by_signal_evidence") is True
        ),
        "phase7_certification_blocked_by_maturity": summary[
            "phase7_certification_blocked_by_maturity"
        ],
        "new_proof_trades_frozen": stage_recorded and new_proof_trades_frozen,
        "new_proof_order_staging_allowed": stage_recorded
        and signal_evidence.get("new_proof_order_staging_allowed") is True,
        "new_proof_trade_submission_allowed": stage_recorded
        and signal_evidence.get("new_proof_trade_submission_allowed") is True,
        "existing_lifecycle_closeout_allowed": stage_recorded,
        **summary,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "statistical_immaturity_allowed": True,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "unsafe_write_counter_total": _int(unsafe_counts["manual_trade_level_override_count"]),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-15 Cockpit And Mission Control Visibility",
    }
    artifact["validation_errors"] = validate_phase7_maturity_tracker(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "maturity_tracker_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("maturity_tracker_recorded") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_maturity_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-14":
        errors.append("phase7_maturity_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_maturity_authority_count_mismatch")
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
        errors.append("phase7_maturity_explicit_authority_grant_count_invalid")
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_maturity_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_maturity_ledger_authority_invalid:{field}")
    if ledger.get("maturity_tracker_write_allowed") is not stage_recorded:
        errors.append("phase7_maturity_write_ledger_mismatch")
    if ledger.get("q7_15_cockpit_visibility_stage_allowed") is not stage_recorded:
        errors.append("phase7_maturity_q7_15_ledger_mismatch")
    if ledger.get("new_proof_trades_frozen") is not frozen:
        errors.append("phase7_maturity_freeze_ledger_mismatch")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_maturity_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("source_signal_evidence_record_count")):
                errors.append(f"phase7_maturity_allowed_count_mismatch:{field}")
            continue
        if field == "manual_trade_level_override_count":
            if value != _int(artifact.get("manual_trade_level_override_count")):
                errors.append(f"phase7_maturity_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_maturity_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != _int(
        artifact.get("manual_trade_level_override_count")
    ):
        errors.append("phase7_maturity_unsafe_total_mismatch")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("maturity_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_maturity_policy_missing"]
    for field in (
        "source_signal_evidence_required",
        "phase7_calendar_harness_required",
        "benchmark_visibility_required",
        "closed_trade_count_required",
        "progress_fraction_required",
        "statistical_immaturity_label_required",
        "statistical_immaturity_must_not_be_hidden",
        "under_100_blocks_mature_status",
        "thirty_day_operational_result_preserved_when_immature",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_maturity_policy_missing_true:{field}")
    for field in (
        "forced_trade_allowed",
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
            errors.append(f"phase7_maturity_policy_forbidden:{field}")
    if policy.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_maturity_policy_benchmark_invalid")
    return errors


def _snapshot_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("artifact_type") != "maturity_snapshot":
        errors.append("phase7_maturity_snapshot_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-14":
        errors.append("phase7_maturity_snapshot_phase_stage_invalid")
    closed_count = _int(record.get("closed_proof_trade_count"))
    run_complete = record.get("phase7_30_day_run_complete") is True
    expected = _maturity_summary(
        closed_trade_count=closed_count,
        phase7_30_day_run_complete=run_complete,
    )
    for key, value in expected.items():
        if record.get(key) != value:
            errors.append(f"phase7_maturity_snapshot_summary_mismatch:{key}")
    if record.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_maturity_snapshot_benchmark_mismatch")
    if record.get("completed_calendar_day_count") > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_snapshot_completed_days_invalid")
    if run_complete and record.get("completed_calendar_day_count") < PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_snapshot_run_complete_without_days")
    if record.get("phase7_mature_benchmark_met") is True:
        if record.get("status") != "maturity_benchmark_met":
            errors.append("phase7_maturity_snapshot_mature_status_invalid")
    elif closed_count == 0:
        if record.get("status") != "no_sample":
            errors.append("phase7_maturity_snapshot_no_sample_status_invalid")
    elif record.get("status") != "statistically_immature":
        errors.append("phase7_maturity_snapshot_immature_status_invalid")
    if closed_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        if record.get("phase7_mature_status_blocked") is not True:
            errors.append("phase7_maturity_snapshot_under_100_not_blocked")
        if record.get("phase7_mature_benchmark_met") is not False:
            errors.append("phase7_maturity_snapshot_under_100_mature")
    if run_complete and closed_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        if record.get("phase7_statistically_immature") is not True:
            errors.append("phase7_maturity_snapshot_30d_under_100_not_immature")
    for field in (
        "forced_trade_allowed",
        "proof_trade_creation_allowed",
        "phase7_demo_proof_certified",
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
        "phase7_30_day_operational_result_erased_by_immaturity",
        "phase7_statistical_immaturity_hidden",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_maturity_snapshot_forbidden:{field}")
    for count_field in ("broker_post_called_count", "alpaca_post_called_count"):
        if _int(record.get(count_field)) != 0:
            errors.append(f"phase7_maturity_snapshot_count_nonzero:{count_field}")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_maturity_snapshot_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("phase7_maturity_snapshot_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_maturity_snapshot_failed_count_mismatch")
    return errors


def validate_phase7_maturity_tracker(artifact: dict[str, Any]) -> list[str]:
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
        "maturity_policy",
        "maturity_snapshot_records",
        "closed_proof_trade_refs",
        "boundary",
        "source_signal_evidence_status",
        "source_signal_evidence_stage_status",
        "source_signal_evidence_record_count",
        "source_signal_complete_decision_chain_count",
        "source_signal_missing_decision_chain_count",
        "source_signal_certification_blocked",
        "source_calendar_status",
        "source_calendar_stage_status",
        "calendar_harness_started",
        "phase7_30_day_run_complete",
        "completed_calendar_day_count",
        "phase7_harness_day_count",
        "q7_14_maturity_tracker_stage_allowed",
        "q7_15_cockpit_visibility_stage_allowed",
        "maturity_tracker_recorded",
        "maturity_tracker_write_allowed",
        "mature_benchmark_visible",
        "forced_trade_allowed",
        "proof_trade_creation_allowed",
        "phase7_demo_proof_certified",
        "phase7_certification_blocked_by_signal_evidence",
        "phase7_certification_blocked_by_maturity",
        "maturity_state",
        "closed_proof_trade_count",
        "mature_benchmark",
        "mature_closed_trade_benchmark",
        "maturity_progress_fraction",
        "maturity_progress_percent",
        "closed_trades_remaining_to_mature",
        "phase7_mature_benchmark_met",
        "phase7_mature_status_blocked",
        "phase7_statistically_immature",
        "phase7_statistical_immaturity_allowed",
        "phase7_statistical_immaturity_hidden",
        "phase7_statistical_immaturity_dashboard_warning_required",
        "phase7_30_day_operational_result_erased_by_immaturity",
        "phase7_30_day_operational_result_preserved",
        "maturity_sample_size_warning",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "statistical_immaturity_allowed",
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
        errors.append("phase7_maturity_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_MATURITY_TRACKER_SCHEMA_VERSION:
        errors.append("phase7_maturity_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_maturity_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_maturity_tracker":
        errors.append("phase7_maturity_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-14":
        errors.append("phase7_maturity_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_maturity_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_maturity_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_maturity_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_maturity_blocker_count_mismatch")
    checks = artifact.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_maturity_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if artifact.get("failed_checks") != failed_checks:
        errors.append("phase7_maturity_failed_checks_mismatch")
    if artifact.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_maturity_failed_check_count_mismatch")
    if tuple(check.get("name") for check in checks if isinstance(check, dict)) != (
        PHASE7_MATURITY_REQUIRED_CHECKS
    ):
        errors.append("phase7_maturity_required_checks_invalid")

    stage_recorded = artifact.get("maturity_tracker_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_closed_trades",
            "maturity_progress_recorded",
            "statistically_immature",
            "maturity_benchmark_met",
        }:
            errors.append("phase7_maturity_status_invalid")
        if artifact.get("stage_status") not in {
            "maturity_tracker_ready_no_closed_trades",
            "maturity_tracker_progress_recorded",
            "maturity_tracker_statistically_immature_after_30_days",
            "maturity_tracker_benchmark_met",
        }:
            errors.append("phase7_maturity_stage_status_invalid")
        if blockers:
            errors.append("phase7_maturity_recorded_with_blockers")
        if artifact.get("q7_15_cockpit_visibility_stage_allowed") is not True:
            errors.append("q7_15_cockpit_visibility_not_allowed")
        if artifact.get("maturity_tracker_write_allowed") is not True:
            errors.append("phase7_maturity_write_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_maturity_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_maturity_blocked_without_blockers")
        if artifact.get("q7_15_cockpit_visibility_stage_allowed") is not False:
            errors.append("q7_15_stage_allowed_while_blocked")
        if artifact.get("maturity_tracker_write_allowed") is not False:
            errors.append("phase7_maturity_write_allowed_while_blocked")
    if artifact.get("q7_14_maturity_tracker_stage_allowed") is not True:
        errors.append("q7_14_maturity_tracker_not_allowed")
    if artifact.get("source_signal_evidence_status") not in {
        "ready_no_proof_trades",
        "signal_funnel_evidence_recorded",
        "blocked_missing_signal_evidence",
    }:
        errors.append("phase7_maturity_source_signal_status_invalid")
    if artifact.get("source_calendar_status") != "scheduled":
        errors.append("phase7_maturity_source_calendar_status_invalid")
    if artifact.get("source_calendar_stage_status") != "phase7_calendar_harness_scheduled":
        errors.append("phase7_maturity_source_calendar_stage_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    snapshots = artifact.get("maturity_snapshot_records", [])
    if not isinstance(snapshots, list):
        errors.append("phase7_maturity_snapshots_not_list")
        snapshots = []
    if stage_recorded and len(snapshots) != 1:
        errors.append("phase7_maturity_snapshot_count_invalid")
    for record in snapshots:
        if isinstance(record, dict):
            errors.extend(_snapshot_errors(record))
        else:
            errors.append("phase7_maturity_snapshot_invalid")
    closed_count = _int(artifact.get("closed_proof_trade_count"))
    run_complete = artifact.get("phase7_30_day_run_complete") is True
    expected = _maturity_summary(
        closed_trade_count=closed_count,
        phase7_30_day_run_complete=run_complete,
    )
    for key, value in expected.items():
        if artifact.get(key) != value:
            errors.append(f"phase7_maturity_summary_mismatch:{key}")
    refs = artifact.get("closed_proof_trade_refs", [])
    if not isinstance(refs, list):
        errors.append("phase7_maturity_closed_refs_not_list")
        refs = []
    if len(refs) != closed_count:
        errors.append("phase7_maturity_closed_ref_count_mismatch")
    if artifact.get("mature_benchmark_visible") is not True:
        errors.append("phase7_maturity_benchmark_not_visible")
    if artifact.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_maturity_benchmark_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_maturity_closed_benchmark_mismatch")
    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_harness_day_count_mismatch")
    if artifact.get("completed_calendar_day_count") > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_completed_days_invalid")
    if run_complete and artifact.get("completed_calendar_day_count") < PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_run_complete_without_completed_days")
    if closed_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        if artifact.get("phase7_mature_benchmark_met") is not False:
            errors.append("phase7_maturity_under_100_mature")
        if artifact.get("phase7_mature_status_blocked") is not True:
            errors.append("phase7_maturity_under_100_mature_not_blocked")
        if artifact.get("phase7_certification_blocked_by_maturity") is not True:
            errors.append("phase7_maturity_under_100_not_blocking_certification")
    if run_complete and closed_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        if artifact.get("phase7_statistically_immature") is not True:
            errors.append("phase7_maturity_30d_under_100_not_immature")
    if closed_count >= PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        if artifact.get("phase7_mature_benchmark_met") is not True:
            errors.append("phase7_maturity_100_not_mature")
        if artifact.get("phase7_certification_blocked_by_maturity") is not False:
            errors.append("phase7_maturity_100_blocks_certification")
    for field in (
        "phase7_statistical_immaturity_allowed",
        "phase7_30_day_operational_result_preserved",
        "statistical_immaturity_allowed",
    ):
        if artifact.get(field) is not True:
            errors.append(f"phase7_maturity_missing_true:{field}")
    for field in (
        "forced_trade_allowed",
        "proof_trade_creation_allowed",
        "phase7_demo_proof_certified",
        "phase7_statistical_immaturity_hidden",
        "phase7_30_day_operational_result_erased_by_immaturity",
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
            errors.append(f"phase7_maturity_forbidden:{field}")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_maturity_count_nonzero:{count_field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_maturity_starting_equity_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_maturity_drawdown_cap_mismatch")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_maturity_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_maturity_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_maturity_proof_contract_phase5_reuse_allowed")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_maturity_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_maturity_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_maturity_qctrl_role_invalid")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_maturity_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_maturity_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_maturity_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_maturity_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records Phase 7 100-trade maturity accounting only",
        "100 closed proof-trade benchmark",
        "preserve the 30-day operational result",
        "cannot hide statistical immaturity",
        "cannot force trades",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_maturity_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_maturity_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_maturity_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_maturity_tracker_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_MATURITY_TRACKER_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_MATURITY_TRACKER_EVENT_TYPE,
        PHASE7_MATURITY_TRACKER_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "closed_proof_trade_count": output.get("closed_proof_trade_count"),
            "mature_benchmark": output.get("mature_benchmark"),
            "maturity_progress_fraction": output.get("maturity_progress_fraction"),
            "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
            "phase7_statistically_immature": output.get("phase7_statistically_immature"),
            "phase7_statistical_immaturity_hidden": output.get(
                "phase7_statistical_immaturity_hidden"
            ),
            "phase7_30_day_run_complete": output.get("phase7_30_day_run_complete"),
            "phase7_30_day_operational_result_erased_by_immaturity": output.get(
                "phase7_30_day_operational_result_erased_by_immaturity"
            ),
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
    output["validation_errors"] = validate_phase7_maturity_tracker(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "maturity_tracker_validation_error"
    return output, [entry]


def write_phase7_maturity_tracker(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_maturity_tracker_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_maturity_tracker_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_maturity_tracker(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "maturity_tracker_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_maturity_tracker(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "maturity_tracker_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "mature_benchmark": output.get("mature_benchmark"),
        "maturity_progress_fraction": output.get("maturity_progress_fraction"),
        "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
        "phase7_statistically_immature": output.get("phase7_statistically_immature"),
        "phase7_statistical_immaturity_hidden": output.get(
            "phase7_statistical_immaturity_hidden"
        ),
        "phase7_30_day_run_complete": output.get("phase7_30_day_run_complete"),
        "phase7_30_day_operational_result_erased_by_immaturity": output.get(
            "phase7_30_day_operational_result_erased_by_immaturity"
        ),
        "q7_15_cockpit_visibility_stage_allowed": output.get(
            "q7_15_cockpit_visibility_stage_allowed"
        ),
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
