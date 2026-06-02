"""Q7-4 Phase 7 Demo Proof weekly cadence tracker.

This stage calculates weekly proof cadence from the Q7-3 qualified setup ledger.
It is accounting-only: it does not force trades, auto-approve setups, stage or
submit orders, create proof trades, grant proof credit, or enable live capital.
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
from orchestrator.phase7_qualified_setup_ledger import (
    PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT,
    build_phase7_qualified_setup_ledger,
    phase7_qualified_setup_ledger_paths,
    validate_phase7_qualified_setup_ledger,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)


PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION = 1
PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT = "phase7_weekly_cadence_tracker.json"
PHASE7_WEEKLY_CADENCE_HISTORY = "phase7_weekly_cadence_tracker_history.jsonl"
PHASE7_WEEKLY_CADENCE_EVENT_LOG = "phase7_weekly_cadence_tracker_events.jsonl"
PHASE7_WEEKLY_CADENCE_EVENT_TYPE = PHASE7_EVENT_TYPES["weekly_cadence"]
PHASE7_WEEKLY_CADENCE_COMPONENT = "phase7_weekly_cadence_tracker"

PHASE7_WEEKLY_CADENCE_BOUNDARY = (
    "Q7-4 computes weekly proof cadence from the qualified setup ledger only. "
    "It cannot force trades, cannot create qualified setups, cannot "
    "auto-approve trades, cannot stage or submit proof orders, cannot create "
    "proof trades, cannot grant Phase 7 proof credit, cannot reuse Phase 5 "
    "test trades as proof, cannot call broker POST routes, cannot call live "
    "endpoints, cannot enable live capital, and cannot permit manual "
    "trade-level overrides."
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


def phase7_weekly_cadence_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT,
        runtime / PHASE7_WEEKLY_CADENCE_HISTORY,
        runtime / PHASE7_WEEKLY_CADENCE_EVENT_LOG,
    )


def _setup_ledger(settings: Settings) -> dict[str, Any]:
    ledger_path, _, _ = phase7_qualified_setup_ledger_paths(settings)
    if ledger_path.exists():
        return _read_json(ledger_path)
    return build_phase7_qualified_setup_ledger(settings=settings)


def _cadence_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "target_applies_only_where_qualified_setups_exist": True,
        "no_forced_trades": True,
        "qualified_setups_must_be_accounted_for": True,
        "missed_qualified_setup_requires_backend_blocker": True,
        "partial_week_trade_pressure_allowed": False,
        "harness_start_required_before_positive_target": True,
        "proof_trade_creation_allowed": False,
        "auto_approval_allowed": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
    }


def _authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION,
        "stage": "Q7-4",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "q7_5_test_mode_auto_approval_router_stage_allowed": True,
        **phase7_authority_defaults(),
        "boundary": PHASE7_WEEKLY_CADENCE_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_calendar_harness.py",
            "orchestrator/phase7_qualified_setup_ledger.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-3-qualified-setup-ledger-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _weekly_target(qualified_setup_count: int) -> int:
    return min(PHASE7_WEEKLY_PROOF_TRADE_TARGET, max(0, qualified_setup_count))


def _cadence_record(summary: dict[str, Any]) -> dict[str, Any]:
    qualified_count = int(summary.get("qualified_setup_count", 0) or 0)
    blocked_count = int(summary.get("blocked_setup_count", 0) or 0)
    expired_count = int(summary.get("expired_setup_count", 0) or 0)
    proof_trade_count = int(summary.get("proof_trade_count", 0) or 0)
    target = _weekly_target(qualified_count)
    pending_auto_approval_count = int(summary.get("pending_auto_approval_count", 0) or 0)
    if target > 0 and pending_auto_approval_count == 0:
        pending_auto_approval_count = max(0, target - proof_trade_count - blocked_count - expired_count)
    accounted_count = (
        proof_trade_count
        + blocked_count
        + expired_count
        + pending_auto_approval_count
    )
    missed_count = max(0, target - accounted_count)
    no_trade_explained = summary.get("no_trade_explanation_recorded") is True
    if target == 0 and no_trade_explained:
        cadence_state = "satisfied_no_qualified_setups"
    elif pending_auto_approval_count > 0 and missed_count == 0:
        cadence_state = "pending_auto_approval"
    elif missed_count == 0:
        cadence_state = "satisfied"
    else:
        cadence_state = "failed_missed_qualified_setups"
    return {
        "cadence_record_id": f"q7-4:proof-week:{summary.get('proof_week_number')}",
        "proof_week_number": summary.get("proof_week_number"),
        "start_day_number": summary.get("start_day_number"),
        "end_day_number": summary.get("end_day_number"),
        "start_date": summary.get("start_date"),
        "end_date": summary.get("end_date"),
        "is_partial_week": summary.get("is_partial_week") is True,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "max_weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "qualified_setup_count": qualified_count,
        "policy_blocked_qualified_setup_count": blocked_count,
        "expired_qualified_setup_count": expired_count,
        "target_proof_trade_count": target,
        "proof_trade_count": proof_trade_count,
        "closed_proof_trade_count": 0,
        "pending_auto_approval_count": pending_auto_approval_count,
        "accounted_qualified_setup_count": accounted_count,
        "missed_qualified_setup_count": missed_count,
        "no_trade_explanation_recorded": no_trade_explained,
        "no_trade_rationale": summary.get("no_trade_rationale"),
        "no_forced_trade_rule_applied": True,
        "no_forced_trade_exception_recorded": target == 0 and no_trade_explained,
        "forced_trade_allowed": False,
        "partial_week_trade_pressure_allowed": False,
        "cadence_satisfied": missed_count == 0,
        "cadence_state": cadence_state,
        "proof_trade_creation_allowed": False,
        "auto_approval_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _cadence_records(setup_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = setup_ledger.get("weekly_setup_summaries", [])
    if not isinstance(summaries, list):
        return []
    return [_cadence_record(summary) for summary in summaries if isinstance(summary, dict)]


def _preflight_blockers(setup_ledger: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    ledger_errors = validate_phase7_qualified_setup_ledger(setup_ledger)
    if ledger_errors:
        blockers.append("phase7_qualified_setup_ledger_validation_errors")
    if setup_ledger.get("status") not in {
        "read_only_no_q7_setups",
        "read_only_q7_setups_recorded",
    }:
        blockers.append("phase7_qualified_setup_ledger_status_invalid")
    if setup_ledger.get("stage_status") not in {
        "qualified_setup_ledger_recorded_no_q7_setup_window",
        "qualified_setup_ledger_recorded_with_q7_setups",
    }:
        blockers.append("phase7_qualified_setup_ledger_stage_status_invalid")
    if setup_ledger.get("q7_4_weekly_cadence_tracker_stage_allowed") is not True:
        blockers.append("q7_4_weekly_cadence_tracker_not_allowed")
    if int(setup_ledger.get("weekly_setup_summary_count", 0) or 0) != 5:
        blockers.append("phase7_weekly_setup_summary_count_mismatch")
    return sorted(set(blockers))


def build_phase7_weekly_cadence_tracker(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    setup_ledger = _setup_ledger(settings)
    blockers = _preflight_blockers(setup_ledger)
    records = _cadence_records(setup_ledger)
    unsafe_counts = phase7_unsafe_counter_defaults()
    tracker_recorded = not blockers
    target_total = sum(int(record.get("target_proof_trade_count", 0) or 0) for record in records)
    proof_trade_total = sum(int(record.get("proof_trade_count", 0) or 0) for record in records)
    missed_total = sum(int(record.get("missed_qualified_setup_count", 0) or 0) for record in records)
    no_forced_exception_count = sum(
        1 for record in records if record.get("no_forced_trade_exception_recorded") is True
    )
    pending_auto_approval_total = sum(
        int(record.get("pending_auto_approval_count", 0) or 0) for record in records
    )
    status = "cadence_satisfied_no_q7_setups"
    stage_status = "weekly_cadence_recorded_no_qualified_setups"
    if pending_auto_approval_total:
        status = "cadence_pending_q7_handoff"
        stage_status = "weekly_cadence_pending_auto_approval"
    if not tracker_recorded:
        status = "blocked"
        stage_status = "weekly_cadence_tracker_blocked"
    artifact = {
        "schema_version": PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_weekly_cadence_tracker",
        "artifact_id": "phase7:q7-4:weekly-cadence-tracker",
        "phase": "Q7",
        "stage": "Q7-4",
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
        "authority_ledger": _authority_ledger(),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "cadence_policy": _cadence_policy(),
        "weekly_cadence_records": records,
        "boundary": PHASE7_WEEKLY_CADENCE_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        "source_setup_ledger_artifact_id": setup_ledger.get("artifact_id"),
        "source_setup_ledger_status": setup_ledger.get("status"),
        "source_setup_ledger_stage_status": setup_ledger.get("stage_status"),
        "q7_4_weekly_cadence_tracker_stage_allowed": (
            setup_ledger.get("q7_4_weekly_cadence_tracker_stage_allowed") is True
        ),
        "q7_5_test_mode_auto_approval_router_stage_allowed": tracker_recorded,
        "weekly_cadence_tracker_recorded": tracker_recorded,
        "weekly_cadence_record_count": len(records),
        "weekly_cadence_satisfied_count": sum(
            1 for record in records if record.get("cadence_satisfied") is True
        ),
        "weekly_cadence_failed_count": sum(
            1 for record in records if record.get("cadence_satisfied") is not True
        ),
        "weekly_target_total": target_total,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "weekly_target_applies_only_where_qualified_setups_exist": True,
        "qualified_setup_count": int(setup_ledger.get("qualified_setup_count", 0) or 0),
        "eligible_setup_count": int(setup_ledger.get("eligible_setup_count", 0) or 0),
        "blocked_setup_count": int(setup_ledger.get("blocked_setup_count", 0) or 0),
        "expired_setup_count": int(setup_ledger.get("expired_setup_count", 0) or 0),
        "target_proof_trade_count": target_total,
        "proof_trade_count": proof_trade_total,
        "closed_proof_trade_count": 0,
        "pending_auto_approval_count": pending_auto_approval_total,
        "missed_qualified_setup_count": missed_total,
        "missed_qualified_setup_unexplained_count": missed_total,
        "no_forced_trade_rule_applied": True,
        "no_forced_trade_exception_count": no_forced_exception_count,
        "no_trade_week_explanation_count": int(
            setup_ledger.get("no_trade_week_explanation_count", 0) or 0
        ),
        "partial_week_trade_pressure_allowed": False,
        "calendar_harness_started": setup_ledger.get("calendar_harness_started") is True,
        "phase7_demo_day_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-5 Test-Mode Auto-Approval Router",
    }
    artifact["validation_errors"] = validate_phase7_weekly_cadence_tracker(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "weekly_cadence_tracker_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["weekly_cadence_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-4":
        errors.append("weekly_cadence_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("weekly_cadence_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("weekly_cadence_explicit_authority_grant")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"weekly_cadence_authority_enabled:{field}")
        if ledger.get(field) is not False:
            errors.append(f"weekly_cadence_ledger_authority_enabled:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"weekly_cadence_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("weekly_cadence_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("weekly_cadence_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("cadence_policy", {})
    if not isinstance(policy, dict):
        return ["weekly_cadence_policy_missing"]
    if policy.get("weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("weekly_cadence_policy_formula_invalid")
    if policy.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("weekly_cadence_policy_target_mismatch")
    for field in (
        "target_applies_only_where_qualified_setups_exist",
        "no_forced_trades",
        "qualified_setups_must_be_accounted_for",
        "missed_qualified_setup_requires_backend_blocker",
        "harness_start_required_before_positive_target",
    ):
        if policy.get(field) is not True:
            errors.append(f"weekly_cadence_policy_missing_true:{field}")
    for field in (
        "partial_week_trade_pressure_allowed",
        "proof_trade_creation_allowed",
        "auto_approval_allowed",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
    ):
        if policy.get(field) is not False:
            errors.append(f"weekly_cadence_policy_forbidden:{field}")
    return errors


def _record_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = artifact.get("weekly_cadence_records", [])
    if not isinstance(records, list):
        return ["weekly_cadence_records_not_list"]
    if len(records) != 5:
        errors.append("weekly_cadence_record_count_mismatch")
    for expected_week, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append("weekly_cadence_record_invalid")
            continue
        if record.get("proof_week_number") != expected_week:
            errors.append("weekly_cadence_week_number_mismatch")
        qualified_count = int(record.get("qualified_setup_count", 0) or 0)
        blocked_count = int(record.get("policy_blocked_qualified_setup_count", 0) or 0)
        expired_count = int(record.get("expired_qualified_setup_count", 0) or 0)
        proof_trade_count = int(record.get("proof_trade_count", 0) or 0)
        pending_auto_approval_count = int(record.get("pending_auto_approval_count", 0) or 0)
        expected_target = _weekly_target(qualified_count)
        expected_accounted = (
            proof_trade_count
            + blocked_count
            + expired_count
            + pending_auto_approval_count
        )
        expected_missed = max(0, expected_target - expected_accounted)
        if record.get("weekly_target_formula") != "min(3, qualified_setup_count)":
            errors.append("weekly_cadence_record_formula_invalid")
        if record.get("max_weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
            errors.append("weekly_cadence_record_target_mismatch")
        if int(record.get("target_proof_trade_count", 0) or 0) != expected_target:
            errors.append("weekly_cadence_record_target_invalid")
        if int(record.get("accounted_qualified_setup_count", 0) or 0) != expected_accounted:
            errors.append("weekly_cadence_record_accounted_count_invalid")
        if int(record.get("missed_qualified_setup_count", 0) or 0) != expected_missed:
            errors.append("weekly_cadence_record_missed_count_invalid")
        if record.get("no_forced_trade_rule_applied") is not True:
            errors.append("weekly_cadence_no_forced_rule_not_applied")
        if record.get("forced_trade_allowed") is not False:
            errors.append("weekly_cadence_forced_trade_allowed")
        if record.get("partial_week_trade_pressure_allowed") is not False:
            errors.append("weekly_cadence_partial_week_pressure_allowed")
        if record.get("proof_trade_creation_allowed") is not False:
            errors.append("weekly_cadence_record_proof_trade_creation_allowed")
        if record.get("auto_approval_allowed") is not False:
            errors.append("weekly_cadence_record_auto_approval_allowed")
        if record.get("proof_credit_allowed") is not False:
            errors.append("weekly_cadence_record_proof_credit_allowed")
        if record.get("live_capital_enabled") is not False:
            errors.append("weekly_cadence_record_live_capital_enabled")
        if expected_target == 0:
            if record.get("no_trade_explanation_recorded") is not True:
                errors.append("weekly_cadence_no_trade_explanation_missing")
            if record.get("no_forced_trade_exception_recorded") is not True:
                errors.append("weekly_cadence_no_forced_exception_missing")
            if record.get("cadence_state") != "satisfied_no_qualified_setups":
                errors.append("weekly_cadence_zero_target_state_invalid")
            if pending_auto_approval_count != 0:
                errors.append("weekly_cadence_pending_auto_approval_without_target")
        if expected_target > 0:
            if pending_auto_approval_count <= 0 and expected_missed == 0:
                errors.append("weekly_cadence_positive_target_without_pending_or_missed")
            if pending_auto_approval_count > 0 and record.get("cadence_state") != (
                "pending_auto_approval"
            ):
                errors.append("weekly_cadence_pending_state_invalid")
        if expected_missed > 0 and record.get("cadence_satisfied") is True:
            errors.append("weekly_cadence_missed_setup_marked_satisfied")
        if expected_missed == 0 and record.get("cadence_satisfied") is not True:
            errors.append("weekly_cadence_satisfied_record_marked_failed")
    return errors


def validate_phase7_weekly_cadence_tracker(artifact: dict[str, Any]) -> list[str]:
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
        "cadence_policy",
        "weekly_cadence_records",
        "boundary",
        "source_setup_ledger_status",
        "source_setup_ledger_stage_status",
        "q7_4_weekly_cadence_tracker_stage_allowed",
        "q7_5_test_mode_auto_approval_router_stage_allowed",
        "weekly_cadence_tracker_recorded",
        "weekly_cadence_record_count",
        "weekly_cadence_satisfied_count",
        "weekly_cadence_failed_count",
        "weekly_target_total",
        "weekly_target_formula",
        "weekly_proof_trade_target",
        "weekly_target_applies_only_where_qualified_setups_exist",
        "qualified_setup_count",
        "eligible_setup_count",
        "blocked_setup_count",
        "expired_setup_count",
        "target_proof_trade_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "pending_auto_approval_count",
        "missed_qualified_setup_count",
        "missed_qualified_setup_unexplained_count",
        "no_forced_trade_rule_applied",
        "no_forced_trade_exception_count",
        "no_trade_week_explanation_count",
        "partial_week_trade_pressure_allowed",
        "calendar_harness_started",
        "phase7_demo_day_count",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("weekly_cadence_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION:
        errors.append("weekly_cadence_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("weekly_cadence_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_weekly_cadence_tracker":
        errors.append("weekly_cadence_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-4":
        errors.append("weekly_cadence_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("weekly_cadence_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("weekly_cadence_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("weekly_cadence_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("weekly_cadence_blocker_count_mismatch")
    if artifact.get("q7_4_weekly_cadence_tracker_stage_allowed") is not True:
        errors.append("q7_4_weekly_cadence_tracker_not_allowed")
    if artifact.get("source_setup_ledger_status") not in {
        "read_only_no_q7_setups",
        "read_only_q7_setups_recorded",
    }:
        errors.append("weekly_cadence_source_setup_ledger_status_invalid")
    if artifact.get("source_setup_ledger_stage_status") not in {
        "qualified_setup_ledger_recorded_no_q7_setup_window",
        "qualified_setup_ledger_recorded_with_q7_setups",
    }:
        errors.append("weekly_cadence_source_setup_ledger_stage_status_invalid")

    tracker_recorded = artifact.get("weekly_cadence_tracker_recorded") is True
    if tracker_recorded:
        if artifact.get("status") not in {
            "cadence_satisfied_no_q7_setups",
            "cadence_pending_q7_handoff",
        }:
            errors.append("weekly_cadence_status_invalid")
        if artifact.get("stage_status") not in {
            "weekly_cadence_recorded_no_qualified_setups",
            "weekly_cadence_pending_auto_approval",
        }:
            errors.append("weekly_cadence_stage_status_invalid")
        if blockers:
            errors.append("weekly_cadence_recorded_with_blockers")
        if artifact.get("q7_5_test_mode_auto_approval_router_stage_allowed") is not True:
            errors.append("q7_5_test_mode_auto_approval_router_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("weekly_cadence_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("weekly_cadence_blocked_without_blockers")
        if artifact.get("q7_5_test_mode_auto_approval_router_stage_allowed") is not False:
            errors.append("q7_5_test_mode_auto_approval_router_allowed_while_blocked")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    errors.extend(_record_errors(artifact))

    records = artifact.get("weekly_cadence_records", [])
    if isinstance(records, list):
        target_total = sum(int(record.get("target_proof_trade_count", 0) or 0) for record in records if isinstance(record, dict))
        proof_trade_total = sum(int(record.get("proof_trade_count", 0) or 0) for record in records if isinstance(record, dict))
        missed_total = sum(int(record.get("missed_qualified_setup_count", 0) or 0) for record in records if isinstance(record, dict))
        pending_total = sum(int(record.get("pending_auto_approval_count", 0) or 0) for record in records if isinstance(record, dict))
        satisfied_count = sum(1 for record in records if isinstance(record, dict) and record.get("cadence_satisfied") is True)
        failed_count = sum(1 for record in records if isinstance(record, dict) and record.get("cadence_satisfied") is not True)
        no_forced_exception_count = sum(
            1
            for record in records
            if isinstance(record, dict)
            and record.get("no_forced_trade_exception_recorded") is True
        )
        if artifact.get("weekly_cadence_record_count") != len(records):
            errors.append("weekly_cadence_record_count_field_mismatch")
        if artifact.get("weekly_target_total") != target_total:
            errors.append("weekly_cadence_target_total_mismatch")
        if artifact.get("target_proof_trade_count") != target_total:
            errors.append("weekly_cadence_target_proof_trade_count_mismatch")
        if artifact.get("proof_trade_count") != proof_trade_total:
            errors.append("weekly_cadence_proof_trade_total_mismatch")
        if artifact.get("missed_qualified_setup_count") != missed_total:
            errors.append("weekly_cadence_missed_total_mismatch")
        if artifact.get("pending_auto_approval_count") != pending_total:
            errors.append("weekly_cadence_pending_auto_approval_total_mismatch")
        if artifact.get("missed_qualified_setup_unexplained_count") != missed_total:
            errors.append("weekly_cadence_unexplained_missed_total_mismatch")
        if artifact.get("weekly_cadence_satisfied_count") != satisfied_count:
            errors.append("weekly_cadence_satisfied_count_mismatch")
        if artifact.get("weekly_cadence_failed_count") != failed_count:
            errors.append("weekly_cadence_failed_count_mismatch")
        if artifact.get("no_forced_trade_exception_count") != no_forced_exception_count:
            errors.append("weekly_cadence_no_forced_exception_count_mismatch")

    for count_field in (
        "blocked_setup_count",
        "expired_setup_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "missed_qualified_setup_count",
        "missed_qualified_setup_unexplained_count",
        "phase7_demo_day_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"weekly_cadence_count_nonzero:{count_field}")
    if artifact.get("weekly_cadence_record_count") != 5:
        errors.append("weekly_cadence_record_count_not_five")
    if artifact.get("weekly_cadence_satisfied_count") != 5:
        errors.append("weekly_cadence_satisfied_count_not_five")
    if artifact.get("weekly_cadence_failed_count") != 0:
        errors.append("weekly_cadence_failed_count_nonzero")
    expected_no_forced = sum(
        1
        for record in records
        if isinstance(record, dict)
        and record.get("no_forced_trade_exception_recorded") is True
    ) if isinstance(records, list) else 0
    if artifact.get("no_forced_trade_exception_count") != expected_no_forced:
        errors.append("weekly_cadence_no_forced_exception_count_mismatch")
    if artifact.get("weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("weekly_cadence_top_formula_invalid")
    if artifact.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("weekly_cadence_top_target_mismatch")
    if artifact.get("weekly_target_applies_only_where_qualified_setups_exist") is not True:
        errors.append("weekly_cadence_top_target_forces_trades")
    if artifact.get("no_forced_trade_rule_applied") is not True:
        errors.append("weekly_cadence_top_no_forced_rule_not_applied")
    if artifact.get("partial_week_trade_pressure_allowed") is not False:
        errors.append("weekly_cadence_top_partial_week_pressure_allowed")
    for field in (
        "calendar_harness_started",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
    ):
        if artifact.get(field) is not False:
            errors.append(f"weekly_cadence_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("weekly_cadence_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("weekly_cadence_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("weekly_cadence_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("weekly_cadence_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("weekly_cadence_source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("weekly_cadence_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("weekly_cadence_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("weekly_cadence_qctrl_role_invalid")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("weekly_cadence_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("weekly_cadence_proof_contract_day_count_mismatch")
    if proof_contract.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("weekly_cadence_proof_contract_weekly_target_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("weekly_cadence_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("weekly_cadence_proof_contract_manual_override_allowed")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("weekly_cadence_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("weekly_cadence_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("weekly_cadence_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"weekly_cadence_provenance_exposure_enabled:{field}")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot force trades",
        "cannot auto-approve trades",
        "cannot create proof trades",
        "cannot grant Phase 7 proof credit",
        "cannot reuse Phase 5 test trades as proof",
        "cannot enable live capital",
        "cannot permit manual trade-level overrides",
    ):
        if phrase not in boundary:
            errors.append("weekly_cadence_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("weekly_cadence_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("weekly_cadence_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("weekly_cadence_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_weekly_cadence_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_WEEKLY_CADENCE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_WEEKLY_CADENCE_EVENT_TYPE,
        PHASE7_WEEKLY_CADENCE_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "weekly_cadence_record_count": output.get("weekly_cadence_record_count"),
            "weekly_cadence_satisfied_count": output.get("weekly_cadence_satisfied_count"),
            "weekly_cadence_failed_count": output.get("weekly_cadence_failed_count"),
            "weekly_target_total": output.get("weekly_target_total"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "proof_trade_count": output.get("proof_trade_count"),
            "missed_qualified_setup_count": output.get("missed_qualified_setup_count"),
            "no_forced_trade_exception_count": output.get("no_forced_trade_exception_count"),
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
    output["validation_errors"] = validate_phase7_weekly_cadence_tracker(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "weekly_cadence_tracker_validation_error"
    return output, entry


def write_phase7_weekly_cadence_tracker(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_weekly_cadence_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_weekly_cadence_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_weekly_cadence_tracker(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "weekly_cadence_tracker_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_weekly_cadence_tracker(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "weekly_cadence_tracker_validation_error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "weekly_cadence_record_count": output.get("weekly_cadence_record_count"),
        "weekly_cadence_satisfied_count": output.get("weekly_cadence_satisfied_count"),
        "weekly_cadence_failed_count": output.get("weekly_cadence_failed_count"),
        "weekly_target_total": output.get("weekly_target_total"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "proof_trade_count": output.get("proof_trade_count"),
        "missed_qualified_setup_count": output.get("missed_qualified_setup_count"),
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
