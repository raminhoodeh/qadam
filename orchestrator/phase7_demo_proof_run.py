"""Actual Phase 7 paper-operation run ledger.

The Q7-0 through Q7-18 modules define and validate the Phase 7 structure. This
module is the operational overlay that starts the real calendar clock and
records each observation pass. The original 30-day proof window is preserved as
a legacy milestone, but paper operation remains active indefinitely after that
milestone. It does not backfill days, force trades, grant proof credit, call
brokers, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)


PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION = 1
PHASE7_DEMO_PROOF_RUN_RUNTIME_ARTIFACT = "phase7_demo_proof_run.json"
PHASE7_DEMO_PROOF_RUN_HISTORY = "phase7_demo_proof_run_history.jsonl"
PHASE7_DEMO_PROOF_RUN_EVENT_LOG = "phase7_demo_proof_run_events.jsonl"
PHASE7_DEMO_PROOF_RUN_EVENT_TYPE = "phase7_demo_proof_run_recorded"
PHASE7_DEMO_PROOF_RUN_COMPONENT = "phase7_demo_proof_run"
PHASE7_DEMO_PROOF_TIMEZONE = "America/Chicago"
PHASE7_OPERATION_HORIZON = "indefinite"

SOURCE_REFS: dict[str, str] = {
    "calendar_harness": "data/runtime/phase7_calendar_harness.json",
    "qualified_setup_ledger": "data/runtime/phase7_qualified_setup_ledger.json",
    "weekly_cadence": "data/runtime/phase7_weekly_cadence_tracker.json",
    "auto_approval": "data/runtime/phase7_test_mode_auto_approval_router.json",
    "proof_order_staging": "data/runtime/phase7_proof_order_staging.json",
    "guarded_submit": "data/runtime/phase7_guarded_alpaca_paper_submit_path.json",
    "proof_lifecycle": "data/runtime/phase7_proof_lifecycle_monitor.json",
    "postmortem": "data/runtime/phase7_proof_postmortem_contract.json",
    "performance": "data/runtime/phase7_performance_evaluator.json",
    "drawdown": "data/runtime/phase7_drawdown_risk_sentinel.json",
    "override": "data/runtime/phase7_override_detector.json",
    "signal_evidence": "data/runtime/phase7_signal_funnel_evidence.json",
    "maturity": "data/runtime/phase7_maturity_tracker.json",
    "certification": "data/runtime/phase7_certification.json",
    "live_promotion": "data/runtime/phase7_live_promotion_review.json",
}

PHASE7_DEMO_PROOF_RUN_BOUNDARY = (
    "The Phase 7 paper-operation run ledger starts and tracks the actual "
    "calendar observation period indefinitely. The original 30 consecutive "
    "calendar day window is retained as a legacy milestone only. It can record "
    "qualified setup availability, no-trade rationale, and downstream proof "
    "lifecycle counts from existing Q7 artifacts, but it cannot backfill "
    "calendar days, cannot simulate elapsed time, cannot force trades, cannot "
    "create a proof trade without a qualified setup, cannot grant Phase 7 "
    "proof credit, cannot count Phase 5 test trades toward Phase 7 proof, "
    "cannot call broker POST routes, cannot call Alpaca POST routes, cannot "
    "write prediction-market or crypto-perps orders, cannot load live "
    "credentials, cannot enable live capital, cannot permit manual trade-level "
    "overrides, and cannot certify Phase 7."
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase7_artifact_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "run_state",
    "generated_at",
    "timezone",
    "local_observation_date",
    "run_id",
    "run_started",
    "actual_calendar_run",
    "backfill_used",
    "simulated_time_used",
    "start_date",
    "end_date",
    "operation_horizon",
    "legacy_30_day_milestone_complete",
    "actual_elapsed_calendar_day_count",
    "paper_operation_day_number",
    "scheduled_calendar_day_count",
    "completed_calendar_day_count",
    "active_day_number",
    "calendar_days_remaining",
    "phase7_30_day_run_complete",
    "consecutive_calendar_days_preserved",
    "qualified_setups_exist",
    "qualified_setup_count",
    "auto_approved_setup_count",
    "staged_order_count",
    "submitted_paper_order_count",
    "closed_proof_trade_count",
    "postmortem_due_count",
    "evaluated_trade_count",
    "collection_state",
    "proof_trade_collection_attempted",
    "proof_trade_collection_blocker_count",
    "proof_trade_collection_blockers",
    "no_trade_rationale",
    "weekly_proof_trade_target",
    "weekly_target_formula",
    "no_forced_trades",
    "phase7_proof_credit_allowed",
    "phase5_test_trades_count_for_phase7",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "manual_trade_level_override_count",
    "unsafe_write_counter_total",
    "live_credentials_loaded",
    "live_capital_enabled",
    "certification_status",
    "live_promotion_status",
    "blocker_count",
    "blockers",
    "recommended_next_action",
    "boundary",
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_local() -> datetime:
    return datetime.now(ZoneInfo(PHASE7_DEMO_PROOF_TIMEZONE))


def _date_text(value: date) -> str:
    return value.isoformat()


def _parse_date(value: str | date | None) -> date:
    if value is None:
        return _now_local().date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_json_ref(ref: str, settings: Settings | None = None) -> dict[str, Any]:
    return _read_json_path(_path(ref, settings))


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def phase7_demo_proof_run_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_DEMO_PROOF_RUN_RUNTIME_ARTIFACT,
        runtime / PHASE7_DEMO_PROOF_RUN_HISTORY,
        runtime / PHASE7_DEMO_PROOF_RUN_EVENT_LOG,
    )


def _source_status_records(
    sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, ref in SOURCE_REFS.items():
        source = sources.get(key, {})
        status = str(source.get("status") or "missing")
        records.append(
            {
                "source_key": key,
                "source_ref": ref,
                "source_status": status,
                "source_stage": source.get("stage", "missing"),
                "public_safe": source.get("public_safe") is True,
                "recorded": source.get("recorded") is True,
                "validation_error_count": len(source.get("validation_errors", []) or []),
            }
        )
    return records


def _authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION,
        "stage": "Phase7-Run",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "actual_calendar_observation_allowed": True,
        **phase7_authority_defaults(),
        "boundary": PHASE7_DEMO_PROOF_RUN_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(tuple(SOURCE_REFS.values()))
    provenance["decision_chain_refs"] = [
        SOURCE_REFS["qualified_setup_ledger"],
        SOURCE_REFS["auto_approval"],
        SOURCE_REFS["proof_order_staging"],
        SOURCE_REFS["signal_evidence"],
    ]
    provenance["execution_evidence_refs"] = [
        SOURCE_REFS["guarded_submit"],
        SOURCE_REFS["proof_lifecycle"],
        SOURCE_REFS["postmortem"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REFS["drawdown"],
        SOURCE_REFS["override"],
        SOURCE_REFS["certification"],
        SOURCE_REFS["live_promotion"],
    ]
    return provenance


def _existing_run(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_demo_proof_run_paths(settings)
    return _read_json_path(output_path)


def _run_dates(
    *,
    existing: dict[str, Any],
    start_date: str | date | None,
    reset: bool,
) -> tuple[str, date, date]:
    if existing and not reset:
        existing_start = str(existing.get("start_date") or "")
        if existing_start:
            start = _parse_date(existing_start)
            run_id = str(existing.get("run_id") or f"phase7-demo-proof-{start.isoformat()}")
            return run_id, start, start + timedelta(days=PHASE7_HARNESS_DAY_COUNT - 1)
    start = _parse_date(start_date)
    run_id = f"phase7-demo-proof-{start.isoformat()}"
    return run_id, start, start + timedelta(days=PHASE7_HARNESS_DAY_COUNT - 1)


def _previous_day_records(existing: dict[str, Any]) -> dict[int, dict[str, Any]]:
    records: dict[int, dict[str, Any]] = {}
    for record in existing.get("calendar_day_records", []) or []:
        if isinstance(record, dict):
            day_number = _int(record.get("day_number"))
            if day_number:
                records[day_number] = record
    return records


def _counts_from_sources(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    qualified = sources["qualified_setup_ledger"]
    auto = sources["auto_approval"]
    staging = sources["proof_order_staging"]
    submit = sources["guarded_submit"]
    lifecycle = sources["proof_lifecycle"]
    postmortem = sources["postmortem"]
    performance = sources["performance"]
    drawdown = sources["drawdown"]
    override = sources["override"]
    signal = sources["signal_evidence"]
    certification = sources["certification"]
    live_promotion = sources["live_promotion"]
    return {
        "qualified_setup_count": _int(qualified.get("qualified_setup_count")),
        "eligible_setup_count": _int(qualified.get("eligible_setup_count")),
        "auto_approved_setup_count": _int(auto.get("auto_approved_setup_count")),
        "staged_order_count": _int(staging.get("staged_order_count")),
        "submitted_paper_order_count": _int(submit.get("submitted_paper_order_count")),
        "broker_receipt_record_count": _int(submit.get("broker_receipt_record_count")),
        "open_position_count": _int(lifecycle.get("open_position_count")),
        "closed_proof_trade_count": _int(lifecycle.get("closed_proof_trade_count")),
        "postmortem_due_count": _int(postmortem.get("postmortem_due_count")),
        "postmortem_missing_count": _int(postmortem.get("postmortem_missing_count")),
        "evaluated_trade_count": _int(performance.get("evaluated_trade_count")),
        "expectancy_after_costs_positive": performance.get("expectancy_after_costs_positive")
        is True,
        "drawdown_within_cap": drawdown.get("drawdown_within_cap") is True,
        "drawdown_cap_breached": drawdown.get("drawdown_cap_breached") is True,
        "risk_halt_active": drawdown.get("risk_halt_active") is True,
        "override_count": _int(override.get("override_count")),
        "manual_trade_level_override_count": _int(
            override.get("manual_trade_level_override_count")
        ),
        "sample_contaminated": override.get("sample_contaminated") is True,
        "complete_decision_chain_count": _int(signal.get("complete_decision_chain_count")),
        "missing_decision_chain_count": _int(signal.get("missing_decision_chain_count")),
        "source_signal_chains_complete": signal.get(
            "phase7_certification_blocked_by_signal_evidence"
        )
        is not True,
        "certification_status": str(certification.get("status") or "missing"),
        "phase7_demo_proof_certified": certification.get("phase7_demo_proof_certified")
        is True,
        "live_promotion_status": str(live_promotion.get("status") or "missing"),
    }


def _collection_state(
    *,
    run_state: str,
    counts: dict[str, Any],
) -> tuple[str, list[str], str]:
    blockers: list[str] = []
    if run_state == "scheduled_not_started":
        return (
            "scheduled_waiting_for_start_date",
            ["start_date_not_reached"],
            "start_date_not_reached",
        )
    if not counts["qualified_setup_count"]:
        return (
            "active_no_qualified_setups",
            ["no_qualified_setups_detected"],
            "no_q7_qualified_setups_detected_for_active_observation",
        )
    if not counts["auto_approved_setup_count"]:
        blockers.append("qualified_setups_pending_auto_approval")
    if not counts["staged_order_count"]:
        blockers.append("qualified_setups_pending_order_staging")
    if not counts["submitted_paper_order_count"]:
        blockers.append("qualified_setups_pending_guarded_paper_submit")
    if blockers:
        return (
            "qualified_setups_detected_pending_downstream_collection",
            blockers,
            "qualified_setups_exist_but_downstream_collection_incomplete",
        )
    return (
        "proof_trade_collection_active",
        [],
        "qualified_setups_collected_through_guarded_paper_submit",
    )


def _calendar_day_records(
    *,
    start: date,
    current: date,
    previous: dict[int, dict[str, Any]],
    counts: dict[str, Any],
    collection_state: str,
    no_trade_rationale: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for day_number in range(1, PHASE7_HARNESS_DAY_COUNT + 1):
        day_date = start + timedelta(days=day_number - 1)
        previous_record = previous.get(day_number, {})
        if day_date < current:
            day_status = "completed_observation"
        elif day_date == current:
            day_status = "active_observation"
        else:
            day_status = "scheduled_future"
        if current > start + timedelta(days=PHASE7_HARNESS_DAY_COUNT - 1):
            day_status = "completed_observation"
        record = {
            "day_number": day_number,
            "calendar_date": day_date.isoformat(),
            "day_status": day_status,
            "proof_week_number": min(((day_number - 1) // 7) + 1, 5),
            "qualified_setup_count": _int(previous_record.get("qualified_setup_count")),
            "auto_approved_setup_count": _int(
                previous_record.get("auto_approved_setup_count")
            ),
            "staged_order_count": _int(previous_record.get("staged_order_count")),
            "submitted_paper_order_count": _int(
                previous_record.get("submitted_paper_order_count")
            ),
            "closed_proof_trade_count": _int(
                previous_record.get("closed_proof_trade_count")
            ),
            "no_trade_rationale": previous_record.get("no_trade_rationale"),
            "collection_state": previous_record.get("collection_state"),
            "forced_trade_allowed": False,
            "proof_credit_allowed": False,
            "broker_post_called": False,
            "alpaca_post_called": False,
            "live_capital_enabled": False,
            "manual_trade_level_override_allowed": False,
        }
        if day_status == "active_observation":
            record.update(
                {
                    "qualified_setup_count": counts["qualified_setup_count"],
                    "auto_approved_setup_count": counts["auto_approved_setup_count"],
                    "staged_order_count": counts["staged_order_count"],
                    "submitted_paper_order_count": counts["submitted_paper_order_count"],
                    "closed_proof_trade_count": counts["closed_proof_trade_count"],
                    "no_trade_rationale": no_trade_rationale,
                    "collection_state": collection_state,
                }
            )
        if day_status == "completed_observation" and not record["no_trade_rationale"]:
            record["no_trade_rationale"] = "no_q7_qualified_setups_recorded_for_completed_day"
            record["collection_state"] = "completed_no_qualified_setups_recorded"
        records.append(record)
    return records


def build_phase7_demo_proof_run(
    settings: Settings | None = None,
    *,
    start_date: str | date | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    existing = _existing_run(settings)
    run_id, start, end = _run_dates(existing=existing, start_date=start_date, reset=reset)
    generated_at = _now_utc().isoformat()
    current = _now_local().date()
    sources = {key: _read_json_ref(ref, settings) for key, ref in SOURCE_REFS.items()}
    source_records = _source_status_records(sources)
    counts = _counts_from_sources(sources)
    if current < start:
        run_state = "scheduled_not_started"
        active_day_number = None
        actual_elapsed_days = 0
        completed_days = 0
    else:
        run_state = "active"
        active_day_number = (current - start).days + 1
        actual_elapsed_days = max(0, (current - start).days)
        completed_days = min(actual_elapsed_days, PHASE7_HARNESS_DAY_COUNT)
    collection_state, collection_blockers, no_trade_rationale = _collection_state(
        run_state=run_state,
        counts=counts,
    )
    previous = _previous_day_records(existing if not reset else {})
    day_records = _calendar_day_records(
        start=start,
        current=current,
        previous=previous,
        counts=counts,
        collection_state=collection_state,
        no_trade_rationale=no_trade_rationale,
    )
    unsafe_counts = phase7_unsafe_counter_defaults()
    source_missing_count = sum(1 for record in source_records if record["source_status"] == "missing")
    source_validation_error_count = sum(
        _int(record.get("validation_error_count")) for record in source_records
    )
    blockers: list[str] = []
    if source_missing_count:
        blockers.append("phase7_demo_proof_source_missing")
    if source_validation_error_count:
        blockers.append("phase7_demo_proof_source_validation_errors")
    if counts["manual_trade_level_override_count"]:
        blockers.append("manual_trade_level_override_detected")
    if counts["sample_contaminated"]:
        blockers.append("sample_contaminated")
    if counts["drawdown_cap_breached"] or counts["risk_halt_active"]:
        blockers.append("drawdown_or_risk_halt_active")
    blockers = sorted(set(blockers))
    artifact = {
        "schema_version": PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_demo_proof_run",
        "artifact_id": f"phase7:demo-proof-run:{run_id}",
        "phase": "Q7",
        "stage": "Phase7-Run",
        "status": "running" if run_state == "active" else run_state,
        "run_state": run_state,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "event_contract": {
            "event_category": "demo_proof_run",
            "event_type": PHASE7_DEMO_PROOF_RUN_EVENT_TYPE,
            "event_log_required": True,
            "append_only": True,
            "supersession_required_for_change": True,
            "raw_secret_exposed": False,
            "raw_payload_exposed": False,
            "broker_identifier_exposed": False,
        },
        "runtime_artifact_path": None,
        "history_log_path": None,
        "timezone": PHASE7_DEMO_PROOF_TIMEZONE,
        "local_observation_date": current.isoformat(),
        "run_id": run_id,
        "run_started": current >= start,
        "actual_calendar_run": True,
        "backfill_used": False,
        "simulated_time_used": False,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "operation_horizon": PHASE7_OPERATION_HORIZON,
        "legacy_30_day_milestone_complete": completed_days >= PHASE7_HARNESS_DAY_COUNT,
        "actual_elapsed_calendar_day_count": actual_elapsed_days,
        "paper_operation_day_number": active_day_number,
        "scheduled_calendar_day_count": PHASE7_HARNESS_DAY_COUNT,
        "calendar_day_records": day_records,
        "completed_calendar_day_count": completed_days,
        "active_day_number": active_day_number,
        "calendar_days_remaining": max(0, PHASE7_HARNESS_DAY_COUNT - completed_days),
        "phase7_30_day_run_complete": completed_days >= PHASE7_HARNESS_DAY_COUNT,
        "consecutive_calendar_days_preserved": True,
        "source_status_records": source_records,
        "source_artifact_count": len(source_records),
        "source_missing_count": source_missing_count,
        "source_validation_error_count": source_validation_error_count,
        "authority_ledger": _authority_ledger(),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "boundary": PHASE7_DEMO_PROOF_RUN_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        **counts,
        "qualified_setups_exist": counts["qualified_setup_count"] > 0,
        "collection_state": collection_state,
        "proof_trade_collection_attempted": run_state == "active",
        "proof_trade_collection_blockers": collection_blockers,
        "proof_trade_collection_blocker_count": len(collection_blockers),
        "no_trade_rationale": no_trade_rationale,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "no_forced_trades": True,
        "phase7_proof_credit_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "phase5_test_trade_reuse_count": 0,
        "ui_inferred_readiness_count": 0,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "live_credentials_loaded": False,
        "live_capital_enabled": False,
        "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "certification_status": counts["certification_status"],
        "live_promotion_status": counts["live_promotion_status"],
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_action": (
            "Keep the hourly Phase 7 paper-operation observation running indefinitely"
            if run_state == "active"
            else "Wait for the configured start date"
        ),
    }
    artifact["validation_errors"] = validate_phase7_demo_proof_run(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["run_state"] = "validation_error"
    artifact["public_status"] = phase7_demo_proof_run_public_status_from_artifact(artifact)
    return artifact


def _calendar_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = artifact.get("calendar_day_records", [])
    if not isinstance(records, list):
        return ["phase7_demo_run_calendar_records_not_list"]
    if len(records) != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_demo_run_calendar_day_count_mismatch")
    dates: list[date] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append("phase7_demo_run_calendar_record_invalid")
            continue
        if record.get("day_number") != index:
            errors.append("phase7_demo_run_calendar_day_number_mismatch")
        try:
            dates.append(date.fromisoformat(str(record.get("calendar_date"))))
        except ValueError:
            errors.append("phase7_demo_run_calendar_date_invalid")
        for field in (
            "forced_trade_allowed",
            "proof_credit_allowed",
            "broker_post_called",
            "alpaca_post_called",
            "live_capital_enabled",
            "manual_trade_level_override_allowed",
        ):
            if record.get(field) is not False:
                errors.append(f"phase7_demo_run_calendar_forbidden:{field}")
        if _int(record.get("proof_trade_count")) and not _int(
            record.get("qualified_setup_count")
        ):
            errors.append("phase7_demo_run_trade_without_qualified_setup")
    if dates:
        expected_start = date.fromisoformat(str(artifact.get("start_date")))
        expected = [expected_start + timedelta(days=offset) for offset in range(len(dates))]
        if dates != expected:
            errors.append("phase7_demo_run_calendar_not_consecutive")
    return errors


def validate_phase7_demo_proof_run(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "event_log_correlation_id",
        "event_contract",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "calendar_day_records",
        "source_status_records",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase7_demo_run_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION:
        errors.append("phase7_demo_run_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_demo_proof_run":
        errors.append("phase7_demo_run_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Phase7-Run":
        errors.append("phase7_demo_run_phase_stage_mismatch")
    if artifact.get("actual_calendar_run") is not True:
        errors.append("phase7_demo_run_not_actual_calendar")
    if artifact.get("backfill_used") is not False:
        errors.append("phase7_demo_run_backfill_used")
    if artifact.get("simulated_time_used") is not False:
        errors.append("phase7_demo_run_simulated_time_used")
    if artifact.get("scheduled_calendar_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_demo_run_day_count_mismatch")
    if artifact.get("completed_calendar_day_count", 0) > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_demo_run_completed_day_count_invalid")
    if artifact.get("calendar_days_remaining", 0) < 0:
        errors.append("phase7_demo_run_remaining_days_invalid")
    if artifact.get("phase7_30_day_run_complete") is True and artifact.get(
        "completed_calendar_day_count"
    ) != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_demo_run_complete_count_mismatch")
    if artifact.get("consecutive_calendar_days_preserved") is not True:
        errors.append("phase7_demo_run_consecutive_days_not_preserved")
    if artifact.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("phase7_demo_run_weekly_target_mismatch")
    if artifact.get("weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("phase7_demo_run_weekly_formula_mismatch")
    if artifact.get("no_forced_trades") is not True:
        errors.append("phase7_demo_run_forced_trades_allowed")
    if artifact.get("qualified_setups_exist") != (artifact.get("qualified_setup_count", 0) > 0):
        errors.append("phase7_demo_run_qualified_setup_flag_mismatch")
    if _int(artifact.get("submitted_paper_order_count")) and not _int(
        artifact.get("qualified_setup_count")
    ):
        errors.append("phase7_demo_run_submit_without_qualified_setup")
    if _int(artifact.get("closed_proof_trade_count")) and not _int(
        artifact.get("submitted_paper_order_count")
    ):
        errors.append("phase7_demo_run_close_without_submit")
    if artifact.get("proof_trade_collection_attempted") is True and not artifact.get(
        "active_day_number"
    ):
        errors.append("phase7_demo_run_collection_attempt_without_active_day")
    if artifact.get("proof_trade_collection_blocker_count") != len(
        artifact.get("proof_trade_collection_blockers", []) or []
    ):
        errors.append("phase7_demo_run_collection_blocker_count_mismatch")
    if not str(artifact.get("no_trade_rationale") or "").strip():
        errors.append("phase7_demo_run_no_trade_rationale_missing")
    errors.extend(_calendar_errors(artifact))

    for field in (
        "phase7_proof_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "live_credentials_loaded",
        "live_capital_enabled",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_demo_run_forbidden:{field}")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_demo_run_authority_enabled:{field}")
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_demo_run_authority_ledger_missing")
        ledger = {}
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_demo_run_authority_grant_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if ledger.get(field) is not False:
            errors.append(f"phase7_demo_run_ledger_authority_enabled:{field}")
    unsafe_total = sum(_int(artifact.get(field)) for field in PHASE7_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_demo_run_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_demo_run_unsafe_total_nonzero")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if _int(artifact.get(field)) != 0:
            errors.append(f"phase7_demo_run_unsafe_count_nonzero:{field}")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_demo_run_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("phase7_demo_run_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_demo_run_event_log_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "actual calendar observation period indefinitely",
        "legacy milestone only",
        "cannot backfill calendar days",
        "cannot simulate elapsed time",
        "cannot force trades",
        "cannot create a proof trade without a qualified setup",
        "cannot grant Phase 7 proof credit",
        "cannot call broker POST routes",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_demo_run_boundary_weak")
            break
    return sorted(set(errors))


def phase7_demo_proof_run_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PUBLIC_STATUS_FIELDS
        if field in artifact
    }
    public_status["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return public_status


def attach_phase7_demo_proof_run_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_DEMO_PROOF_RUN_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_DEMO_PROOF_RUN_EVENT_TYPE,
        PHASE7_DEMO_PROOF_RUN_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "run_id": output.get("run_id"),
            "run_state": output.get("run_state"),
            "start_date": output.get("start_date"),
            "end_date": output.get("end_date"),
            "local_observation_date": output.get("local_observation_date"),
            "active_day_number": output.get("active_day_number"),
            "completed_calendar_day_count": output.get("completed_calendar_day_count"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "submitted_paper_order_count": output.get("submitted_paper_order_count"),
            "closed_proof_trade_count": output.get("closed_proof_trade_count"),
            "collection_state": output.get("collection_state"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase7_demo_proof_run(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
        output["run_state"] = "validation_error"
    output["public_status"] = phase7_demo_proof_run_public_status_from_artifact(output)
    return output, entry


def write_phase7_demo_proof_run(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_demo_proof_run_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_demo_proof_run_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_demo_proof_run(output)
        output["public_status"] = phase7_demo_proof_run_public_status_from_artifact(output)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_demo_proof_run(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
        output["run_state"] = "validation_error"
    output["public_status"] = phase7_demo_proof_run_public_status_from_artifact(output)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_DEMO_PROOF_RUN_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "run_id": output.get("run_id"),
        "status": output.get("status"),
        "run_state": output.get("run_state"),
        "recorded_at": _now_utc().isoformat(),
        "local_observation_date": output.get("local_observation_date"),
        "active_day_number": output.get("active_day_number"),
        "completed_calendar_day_count": output.get("completed_calendar_day_count"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "collection_state": output.get("collection_state"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
