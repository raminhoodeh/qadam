"""Q7-2 Phase 7 Demo Proof 30-day calendar harness.

This stage creates the scheduled calendar and proof-week ledger for the
30-day Demo Proof run. It is scheduling-only: it does not start the harness,
create qualified setups, create proof trades, stage or submit orders, grant
proof credit, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    build_phase7_sample_artifacts,
    phase7_artifact_bundle_summary,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    build_phase7_readiness,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
    validate_phase7_readiness,
)


PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION = 1
PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT = "phase7_calendar_harness.json"
PHASE7_CALENDAR_HARNESS_HISTORY = "phase7_calendar_harness_history.jsonl"
PHASE7_CALENDAR_HARNESS_EVENT_LOG = "phase7_calendar_harness_events.jsonl"
PHASE7_CALENDAR_HARNESS_EVENT_TYPE = PHASE7_EVENT_TYPES["proof_calendar"]
PHASE7_CALENDAR_HARNESS_COMPONENT = "phase7_calendar_harness"

PROOF_WEEK_RANGES: tuple[tuple[int, int], ...] = (
    (1, 7),
    (8, 14),
    (15, 21),
    (22, 28),
    (29, 30),
)

PHASE7_CALENDAR_BOUNDARY = (
    "Q7-2 can schedule the 30 consecutive calendar day Demo Proof harness and "
    "define proof-week indexing only. It cannot start the proof harness, "
    "cannot create qualified setups, cannot auto-approve trades, cannot stage "
    "or submit proof orders, cannot create proof trades, cannot grant Phase 7 "
    "proof credit, cannot call broker POST routes, cannot call Alpaca POST "
    "routes, cannot call live endpoints, cannot enable live capital, and "
    "cannot permit manual trade-level overrides."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _parse_start_date(start_date: str | date | None) -> date:
    if start_date is None:
        return datetime.now(timezone.utc).date()
    if isinstance(start_date, date):
        return start_date
    return date.fromisoformat(start_date)


def phase7_calendar_harness_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT,
        runtime / PHASE7_CALENDAR_HARNESS_HISTORY,
        runtime / PHASE7_CALENDAR_HARNESS_EVENT_LOG,
    )


def _proof_week_for_day(day_number: int) -> tuple[int, int, int, bool]:
    for index, (start_day, end_day) in enumerate(PROOF_WEEK_RANGES, start=1):
        if start_day <= day_number <= end_day:
            return index, start_day, end_day, (end_day - start_day + 1) < 7
    raise ValueError(f"day number outside Phase 7 range: {day_number}")


def _calendar_days(start: date) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for day_number in range(1, PHASE7_HARNESS_DAY_COUNT + 1):
        current_date = start + timedelta(days=day_number - 1)
        week_number, week_start_day, week_end_day, partial_week = _proof_week_for_day(
            day_number
        )
        days.append(
            {
                "day_number": day_number,
                "calendar_date": current_date.isoformat(),
                "proof_week_number": week_number,
                "proof_week_day_number": day_number - week_start_day + 1,
                "proof_week_start_day_number": week_start_day,
                "proof_week_end_day_number": week_end_day,
                "is_partial_week": partial_week,
                "calendar_record_present": True,
                "harness_day_status": "scheduled_not_started",
                "no_trade_record_required": True,
                "no_trade_rationale_required": True,
                "qualified_setup_count": 0,
                "target_proof_trade_count": 0,
                "proof_trade_count": 0,
                "closed_proof_trade_count": 0,
                "forced_trade_allowed": False,
                "proof_credit_allowed": False,
                "broker_post_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return days


def _proof_weeks(start: date) -> list[dict[str, Any]]:
    weeks: list[dict[str, Any]] = []
    for week_number, (start_day, end_day) in enumerate(PROOF_WEEK_RANGES, start=1):
        day_count = end_day - start_day + 1
        partial_week = day_count < 7
        weeks.append(
            {
                "proof_week_number": week_number,
                "start_day_number": start_day,
                "end_day_number": end_day,
                "day_count": day_count,
                "start_date": (start + timedelta(days=start_day - 1)).isoformat(),
                "end_date": (start + timedelta(days=end_day - 1)).isoformat(),
                "is_partial_week": partial_week,
                "partial_week_trade_pressure_allowed": False,
                "weekly_target_formula": "min(3, qualified_setup_count)",
                "max_weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
                "qualified_setup_count": 0,
                "target_proof_trade_count": 0,
                "proof_trade_count": 0,
                "closed_proof_trade_count": 0,
                "forced_trade_allowed": False,
                "cadence_state": "not_evaluated_until_q7_4",
                "no_forced_trade_exception_required": True,
            }
        )
    return weeks


def _calendar_policy() -> dict[str, Any]:
    return {
        "run_start_policy": "explicit_q7_start_record_required_before_counting",
        "run_end_policy": "complete_after_30_consecutive_calendar_days_if_valid",
        "pause_policy": "pause_requires_explicit_outage_record_and_restart_review",
        "restart_policy": "restart_creates_new_calendar_harness_artifact",
        "outage_policy": (
            "outage days still require calendar records and no-trade rationale; "
            "outages cannot create forced trades"
        ),
        "invalid_run_conditions": [
            "missing_calendar_day",
            "non_consecutive_calendar_day",
            "manual_trade_level_override",
            "phase5_test_trade_counted_as_phase7_proof",
            "proof_trade_without_qualified_setup",
            "broker_or_live_write_outside_guarded_paper_path",
            "live_capital_enabled",
        ],
        "week_5_policy": "partial_observation_week_not_forced_trade_pressure",
        "qualified_setup_ledger_required_for_targets": True,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION,
        "stage": "Q7-2",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "q7_3_qualified_setup_ledger_stage_allowed": True,
        **phase7_authority_defaults(),
        "boundary": PHASE7_CALENDAR_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            "data/runtime/phase7_readiness.json",
            "orchestrator/phase7_artifacts.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-1-artifact-schema-authority-ledger-audit-2026-05-25.md",
        )
    )
    provenance["governance_refs"] = [
        "docs/qadam-phase-7-demo-proof-implementation-plan.md"
    ]
    return provenance


def _q7_1_schema_passed() -> tuple[bool, dict[str, Any]]:
    summary = phase7_artifact_bundle_summary(build_phase7_sample_artifacts())
    return summary.get("status") == "ok", summary


def _preflight_blockers(settings: Settings) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    q7_1_passed, schema_summary = _q7_1_schema_passed()
    blockers: list[str] = []
    if readiness_errors:
        blockers.append("phase7_readiness_validation_errors")
    if readiness.get("phase7_re_entry_gate_passed") is not True:
        blockers.append("phase7_re_entry_gate_not_passed")
    if readiness.get("q7_1_artifact_schema_stage_allowed") is not True:
        blockers.append("q7_1_schema_stage_not_allowed")
    if readiness.get("phase7_demo_proof_implementation_allowed") is not False:
        blockers.append("phase7_demo_proof_implementation_already_allowed")
    if not q7_1_passed:
        blockers.append("q7_1_artifact_schema_not_valid")
    return sorted(set(blockers)), readiness, schema_summary


def build_phase7_calendar_harness(
    settings: Settings | None = None,
    *,
    start_date: str | date | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    start = _parse_start_date(start_date)
    end = start + timedelta(days=PHASE7_HARNESS_DAY_COUNT - 1)
    blockers, readiness, schema_summary = _preflight_blockers(settings)
    days = _calendar_days(start)
    weeks = _proof_weeks(start)
    unsafe_counts = phase7_unsafe_counter_defaults()
    calendar_harness_scheduled = not blockers
    artifact = {
        "schema_version": PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_calendar_harness",
        "artifact_id": f"phase7:q7-2:calendar-harness:{start.isoformat()}",
        "phase": "Q7",
        "stage": "Q7-2",
        "status": "scheduled" if calendar_harness_scheduled else "blocked",
        "stage_status": (
            "phase7_calendar_harness_scheduled"
            if calendar_harness_scheduled
            else "phase7_calendar_harness_blocked"
        ),
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
        "authority_ledger": _authority_ledger(),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "calendar_policy": _calendar_policy(),
        "proof_calendar_days": days,
        "proof_weeks": weeks,
        "boundary": PHASE7_CALENDAR_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        "phase7_readiness_status": readiness.get("status"),
        "phase7_re_entry_gate_passed": readiness.get("phase7_re_entry_gate_passed")
        is True,
        "q7_1_artifact_schema_passed": schema_summary.get("status") == "ok",
        "q7_1_artifact_contract_count": schema_summary.get("artifact_count", 0),
        "q7_2_calendar_harness_stage_allowed": calendar_harness_scheduled,
        "q7_3_qualified_setup_ledger_stage_allowed": calendar_harness_scheduled,
        "calendar_harness_scheduled": calendar_harness_scheduled,
        "calendar_harness_started": False,
        "harness_started": False,
        "harness_start_event_recorded": False,
        "run_paused": False,
        "run_invalidated": False,
        "restart_required": False,
        "scheduled_start_date": start.isoformat(),
        "scheduled_end_date": end.isoformat(),
        "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "calendar_day_record_count": len(days),
        "calendar_record_present_count": sum(
            1 for day in days if day.get("calendar_record_present") is True
        ),
        "consecutive_calendar_days_required": True,
        "consecutive_calendar_days_validated": True,
        "proof_week_count": len(weeks),
        "full_proof_week_count": sum(1 for week in weeks if not week["is_partial_week"]),
        "partial_proof_week_count": sum(1 for week in weeks if week["is_partial_week"]),
        "week_5_partial_observation_only": True,
        "partial_week_trade_pressure_allowed": False,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "weekly_target_applies_only_where_qualified_setups_exist": True,
        "no_forced_trades": True,
        "qualified_setup_ledger_required": True,
        "phase7_demo_day_count": 0,
        "qualified_setup_count": 0,
        "proof_trade_count": 0,
        "closed_proof_trade_count": 0,
        "postmortem_due_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-3 Qualified Setup Ledger",
    }
    artifact["validation_errors"] = validate_phase7_calendar_harness(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "phase7_calendar_harness_validation_error"
    return artifact


def _date_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    days = artifact.get("proof_calendar_days", [])
    if not isinstance(days, list):
        return ["calendar_days_not_list"]
    if len(days) != PHASE7_HARNESS_DAY_COUNT:
        errors.append("calendar_day_count_mismatch")
    expected_numbers = list(range(1, PHASE7_HARNESS_DAY_COUNT + 1))
    day_numbers = [day.get("day_number") for day in days if isinstance(day, dict)]
    if day_numbers != expected_numbers:
        errors.append("calendar_day_numbers_not_sequential")
    try:
        start = date.fromisoformat(str(artifact.get("scheduled_start_date")))
        end = date.fromisoformat(str(artifact.get("scheduled_end_date")))
    except ValueError:
        errors.append("calendar_start_or_end_date_invalid")
        return errors
    if (end - start).days + 1 != PHASE7_HARNESS_DAY_COUNT:
        errors.append("calendar_date_range_mismatch")
    for index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            errors.append("calendar_day_record_invalid")
            continue
        try:
            current = date.fromisoformat(str(day.get("calendar_date")))
        except ValueError:
            errors.append("calendar_day_date_invalid")
            continue
        if current != start + timedelta(days=index - 1):
            errors.append("calendar_dates_not_consecutive")
        expected_week, week_start, week_end, partial_week = _proof_week_for_day(index)
        if day.get("proof_week_number") != expected_week:
            errors.append("calendar_day_week_mapping_invalid")
        if day.get("proof_week_start_day_number") != week_start:
            errors.append("calendar_day_week_start_invalid")
        if day.get("proof_week_end_day_number") != week_end:
            errors.append("calendar_day_week_end_invalid")
        if day.get("is_partial_week") is not partial_week:
            errors.append("calendar_day_partial_week_mismatch")
        if day.get("calendar_record_present") is not True:
            errors.append("calendar_day_record_not_present")
        if day.get("harness_day_status") != "scheduled_not_started":
            errors.append("calendar_day_status_invalid")
        if day.get("no_trade_record_required") is not True:
            errors.append("calendar_day_no_trade_record_not_required")
        if day.get("no_trade_rationale_required") is not True:
            errors.append("calendar_day_no_trade_rationale_not_required")
        for count_field in (
            "qualified_setup_count",
            "target_proof_trade_count",
            "proof_trade_count",
            "closed_proof_trade_count",
        ):
            if int(day.get(count_field, 0) or 0) != 0:
                errors.append(f"calendar_day_premature_count:{count_field}")
        for forbidden_field in (
            "forced_trade_allowed",
            "proof_credit_allowed",
            "broker_post_allowed",
            "live_capital_enabled",
        ):
            if day.get(forbidden_field) is not False:
                errors.append(f"calendar_day_forbidden:{forbidden_field}")
    return errors


def _week_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    weeks = artifact.get("proof_weeks", [])
    if not isinstance(weeks, list):
        return ["proof_weeks_not_list"]
    if len(weeks) != len(PROOF_WEEK_RANGES):
        errors.append("proof_week_count_mismatch")
    try:
        start = date.fromisoformat(str(artifact.get("scheduled_start_date")))
    except ValueError:
        start = None
    for week_number, (start_day, end_day) in enumerate(PROOF_WEEK_RANGES, start=1):
        if week_number > len(weeks) or not isinstance(weeks[week_number - 1], dict):
            errors.append(f"proof_week_missing:{week_number}")
            continue
        week = weeks[week_number - 1]
        day_count = end_day - start_day + 1
        partial_week = day_count < 7
        if week.get("proof_week_number") != week_number:
            errors.append("proof_week_number_mismatch")
        if week.get("start_day_number") != start_day or week.get("end_day_number") != end_day:
            errors.append("proof_week_day_range_mismatch")
        if week.get("day_count") != day_count:
            errors.append("proof_week_day_count_mismatch")
        if start is not None:
            if week.get("start_date") != (start + timedelta(days=start_day - 1)).isoformat():
                errors.append("proof_week_start_date_mismatch")
            if week.get("end_date") != (start + timedelta(days=end_day - 1)).isoformat():
                errors.append("proof_week_end_date_mismatch")
        if week.get("is_partial_week") is not partial_week:
            errors.append("proof_week_partial_flag_mismatch")
        if partial_week and week.get("partial_week_trade_pressure_allowed") is not False:
            errors.append("partial_week_trade_pressure_allowed")
        if week.get("weekly_target_formula") != "min(3, qualified_setup_count)":
            errors.append("proof_week_target_formula_invalid")
        if week.get("max_weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
            errors.append("proof_week_target_mismatch")
        for count_field in (
            "qualified_setup_count",
            "target_proof_trade_count",
            "proof_trade_count",
            "closed_proof_trade_count",
        ):
            if int(week.get(count_field, 0) or 0) != 0:
                errors.append(f"proof_week_premature_count:{count_field}")
        if week.get("forced_trade_allowed") is not False:
            errors.append("proof_week_forced_trade_allowed")
        if week.get("cadence_state") != "not_evaluated_until_q7_4":
            errors.append("proof_week_cadence_state_invalid")
    if artifact.get("full_proof_week_count") != 4:
        errors.append("full_proof_week_count_mismatch")
    if artifact.get("partial_proof_week_count") != 1:
        errors.append("partial_proof_week_count_mismatch")
    if artifact.get("week_5_partial_observation_only") is not True:
        errors.append("week_5_partial_observation_not_marked")
    return errors


def validate_phase7_calendar_harness(artifact: dict[str, Any]) -> list[str]:
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
        "calendar_policy",
        "proof_calendar_days",
        "proof_weeks",
        "boundary",
        "phase7_re_entry_gate_passed",
        "q7_1_artifact_schema_passed",
        "q7_2_calendar_harness_stage_allowed",
        "q7_3_qualified_setup_ledger_stage_allowed",
        "calendar_harness_scheduled",
        "calendar_harness_started",
        "scheduled_start_date",
        "scheduled_end_date",
        "calendar_day_record_count",
        "calendar_record_present_count",
        "consecutive_calendar_days_validated",
        "proof_week_count",
        "full_proof_week_count",
        "partial_proof_week_count",
        "weekly_proof_trade_target",
        "weekly_target_formula",
        "no_forced_trades",
        "qualified_setup_ledger_required",
        "phase7_demo_day_count",
        "qualified_setup_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_calendar_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION:
        errors.append("phase7_calendar_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_calendar_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_calendar_harness":
        errors.append("phase7_calendar_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-2":
        errors.append("phase7_calendar_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_calendar_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_calendar_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_calendar_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_calendar_blocker_count_mismatch")

    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_calendar_authority_ledger_missing")
        ledger = {}
    if ledger.get("stage") != "Q7-2":
        errors.append("phase7_calendar_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_calendar_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_calendar_explicit_authority_grant")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_calendar_authority_enabled:{field}")
        if ledger.get(field) is not False:
            errors.append(f"phase7_calendar_ledger_authority_enabled:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"phase7_calendar_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_calendar_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_calendar_unsafe_total_nonzero")

    if artifact.get("phase7_re_entry_gate_passed") is not True:
        errors.append("phase7_calendar_re_entry_gate_not_passed")
    if artifact.get("q7_1_artifact_schema_passed") is not True:
        errors.append("phase7_calendar_q7_1_schema_not_passed")
    if artifact.get("q7_1_artifact_contract_count") != 19:
        errors.append("phase7_calendar_q7_1_contract_count_mismatch")

    gate_passed = artifact.get("q7_2_calendar_harness_stage_allowed") is True
    if gate_passed:
        if artifact.get("status") != "scheduled":
            errors.append("phase7_calendar_status_not_scheduled")
        if artifact.get("stage_status") != "phase7_calendar_harness_scheduled":
            errors.append("phase7_calendar_stage_status_not_scheduled")
        if blockers:
            errors.append("phase7_calendar_scheduled_with_blockers")
        if artifact.get("q7_3_qualified_setup_ledger_stage_allowed") is not True:
            errors.append("phase7_calendar_q7_3_not_allowed_after_schedule")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_calendar_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_calendar_blocked_without_blockers")
        if artifact.get("q7_3_qualified_setup_ledger_stage_allowed") is not False:
            errors.append("phase7_calendar_q7_3_allowed_while_blocked")

    if artifact.get("calendar_harness_started") is not False:
        errors.append("phase7_calendar_harness_started")
    if artifact.get("harness_started") is not False:
        errors.append("phase7_calendar_harness_started")
    if artifact.get("harness_start_event_recorded") is not False:
        errors.append("phase7_calendar_harness_start_event_recorded")
    if artifact.get("run_paused") is not False:
        errors.append("phase7_calendar_run_paused")
    if artifact.get("run_invalidated") is not False:
        errors.append("phase7_calendar_run_invalidated")
    if artifact.get("restart_required") is not False:
        errors.append("phase7_calendar_restart_required")
    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_calendar_harness_day_count_mismatch")
    if artifact.get("calendar_day_record_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("calendar_day_record_count_mismatch")
    if artifact.get("calendar_record_present_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("calendar_record_present_count_mismatch")
    if artifact.get("consecutive_calendar_days_required") is not True:
        errors.append("consecutive_calendar_days_not_required")
    if artifact.get("consecutive_calendar_days_validated") is not True:
        errors.append("consecutive_calendar_days_not_validated")
    if artifact.get("proof_week_count") != len(PROOF_WEEK_RANGES):
        errors.append("proof_week_count_mismatch")
    if artifact.get("partial_week_trade_pressure_allowed") is not False:
        errors.append("partial_week_trade_pressure_allowed")
    if artifact.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("weekly_proof_trade_target_mismatch")
    if artifact.get("weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("weekly_target_formula_invalid")
    if artifact.get("weekly_target_applies_only_where_qualified_setups_exist") is not True:
        errors.append("weekly_target_forces_trades")
    if artifact.get("no_forced_trades") is not True:
        errors.append("forced_trades_allowed")
    if artifact.get("qualified_setup_ledger_required") is not True:
        errors.append("qualified_setup_ledger_not_required")
    for count_field in (
        "phase7_demo_day_count",
        "qualified_setup_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"phase7_calendar_premature_count:{count_field}")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("q6_deferred_learning_counts_as_proof") is not False:
        errors.append("q6_deferred_learning_counts_as_proof")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("mature_closed_trade_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("statistical_immaturity_not_allowed")

    policy = artifact.get("calendar_policy", {})
    if not isinstance(policy, dict):
        errors.append("calendar_policy_missing")
        policy = {}
    if policy.get("qualified_setup_ledger_required_for_targets") is not True:
        errors.append("calendar_policy_qualified_setup_ledger_not_required")
    if policy.get("proof_trade_creation_allowed") is not False:
        errors.append("calendar_policy_proof_trade_creation_allowed")
    if policy.get("proof_credit_allowed") is not False:
        errors.append("calendar_policy_proof_credit_allowed")
    if policy.get("live_capital_enabled") is not False:
        errors.append("calendar_policy_live_capital_enabled")
    if "outages cannot create forced trades" not in str(policy.get("outage_policy")):
        errors.append("calendar_policy_outage_forced_trade_boundary_missing")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("proof_contract_harness_day_count_mismatch")
    if proof_contract.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("proof_contract_weekly_target_mismatch")
    if proof_contract.get("no_forced_trades") is not True:
        errors.append("proof_contract_forced_trades_allowed")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("proof_contract_phase5_reuse_allowed")
    if proof_contract.get("q6_deferred_learning_counts_as_proof") is not False:
        errors.append("proof_contract_q6_deferred_counts_as_proof")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("proof_contract_manual_override_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("source_posture_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("source_posture_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("source_posture_qctrl_role_invalid")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("provenance_local_path_leak")
        lowered = ref_text.lower()
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"provenance_exposure_enabled:{field}")

    errors.extend(_date_errors(artifact))
    errors.extend(_week_errors(artifact))

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "30 consecutive calendar day",
        "cannot start the proof harness",
        "cannot create qualified setups",
        "cannot create proof trades",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
        "cannot permit manual trade-level overrides",
    ):
        if phrase not in boundary:
            errors.append("phase7_calendar_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_calendar_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("phase7_calendar_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_calendar_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_calendar_harness_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_CALENDAR_HARNESS_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_CALENDAR_HARNESS_EVENT_TYPE,
        PHASE7_CALENDAR_HARNESS_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "scheduled_start_date": output.get("scheduled_start_date"),
            "scheduled_end_date": output.get("scheduled_end_date"),
            "calendar_day_record_count": output.get("calendar_day_record_count"),
            "proof_week_count": output.get("proof_week_count"),
            "full_proof_week_count": output.get("full_proof_week_count"),
            "partial_proof_week_count": output.get("partial_proof_week_count"),
            "calendar_harness_started": output.get("calendar_harness_started"),
            "proof_trade_count": output.get("proof_trade_count"),
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
    output["validation_errors"] = validate_phase7_calendar_harness(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "phase7_calendar_harness_validation_error"
    return output, entry


def write_phase7_calendar_harness(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_calendar_harness_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_calendar_harness_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_calendar_harness(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "phase7_calendar_harness_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_calendar_harness(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "phase7_calendar_harness_validation_error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "scheduled_start_date": output.get("scheduled_start_date"),
        "scheduled_end_date": output.get("scheduled_end_date"),
        "calendar_day_record_count": output.get("calendar_day_record_count"),
        "proof_week_count": output.get("proof_week_count"),
        "calendar_harness_started": output.get("calendar_harness_started"),
        "proof_trade_count": output.get("proof_trade_count"),
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
