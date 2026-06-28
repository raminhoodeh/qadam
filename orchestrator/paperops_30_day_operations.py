"""PaperOps-6 paper run operations contract.

This stage binds the indefinite paper growth operation to the recurring
PaperOps operational pass. It records scheduler, cycle, calendar, and cockpit
mirror state without creating orders, calling brokers, sending notifications,
or granting proof credit.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paperops_close_to_ledger import build_paperops_close_to_ledger
from orchestrator.paperops_source_gap_visibility import (
    build_paperops_source_gap_visibility,
)
from orchestrator.paperops_submit_regression_guard import (
    build_paperops_submit_regression_guard,
)


PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION = 1
PAPEROPS_30_DAY_OPERATIONS_RUNTIME_ARTIFACT = "paperops_30_day_operations.json"
PAPEROPS_30_DAY_OPERATIONS_HISTORY = "paperops_30_day_operations_history.jsonl"
PAPEROPS_30_DAY_OPERATIONS_EVENT_LOG = "paperops_30_day_operations_events.jsonl"
PAPEROPS_30_DAY_OPERATIONS_EVENT_TYPE = "paperops_30_day_operations_recorded"
PAPEROPS_30_DAY_OPERATIONS_COMPONENT = "paperops_30_day_operations"

PAPEROPS_30_DAY_AUTOMATION_ID = "qadam-phase-7-demo-proof-runner"
PAPEROPS_30_DAY_AUTOMATION_NAME = "Qadam PaperOps Autonomous Runner"
SELF_OBSERVER_CYCLE_FAILURE_LABELS = frozenset(
    {
        "paperops_notification_review",
        "paperops_cockpit_notification_upgrade",
        "paper_live_certification",
        "paperops_30_day_operations",
        "paper_ops_readiness",
    }
)

PAPER_LIVE_CERTIFICATION_ACCEPTED_STATUSES = {
    "blocked_pending_qctrl_and_phase7_proof",
    "blocked_pending_qctrl",
    "blocked_pending_phase7_proof",
    "blocked_pending_certification_gates",
    "blocked_paper_live_control_plane",
    "paper_live_certified",
}

REQUIRED_AUTOMATION_COMMAND_FRAGMENTS: tuple[str, ...] = (
    "scripts/run_paperops_autonomous_pass.py",
)

REQUIRED_AUTOMATION_GUARDRAIL_FRAGMENTS: tuple[str, ...] = (
    "Preserve the actual paper growth trial calendar",
    "without backfilling or simulating elapsed time",
    "Do not force trades",
    "do not edit secrets or .env files",
    "do not load live credentials",
    "do not enable live capital",
    "do not call broker live endpoints",
    "only submit to Alpaca paper",
    "respect the Q-CTRL paper consultation hold",
    "do not grant proof credit",
)

PAPEROPS_30_DAY_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "run_id",
    "run_state",
    "start_date",
    "end_date",
    "operation_horizon",
    "legacy_30_day_milestone_complete",
    "actual_elapsed_calendar_day_count",
    "paper_operation_day_number",
    "timezone",
    "local_observation_date",
    "actual_calendar_run",
    "scheduled_calendar_day_count",
    "active_day_number",
    "completed_calendar_day_count",
    "calendar_days_remaining",
    "phase7_30_day_run_complete",
    "consecutive_calendar_days_preserved",
    "backfill_used",
    "simulated_time_used",
    "no_forced_trades",
    "qualified_setup_count",
    "submitted_paper_order_count",
    "closed_proof_trade_count",
    "paperops_close_to_ledger_status",
    "paperops_close_to_ledger_closed_proof_trade_count",
    "paperops_close_to_ledger_postmortem_due_marker_created_count",
    "paperops_close_to_ledger_blocker_count",
    "paperops_submit_regression_guard_status",
    "paperops_submit_regression_guard_source_paperops2_status",
    "paperops_submit_regression_guard_fresh_eligible_submit_record_count",
    "paperops_submit_regression_guard_duplicate_submit_record_count",
    "paperops_submit_regression_guard_source_stale_after_post_count",
    "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
    "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
    "paperops_submit_regression_guard_blocker_count",
    "paperops_submit_regression_guard_validation_error_count",
    "paperops_source_gap_visibility_status",
    "paperops_source_gap_visibility_policy_status",
    "paperops_source_gap_visibility_optional_gap_count",
    "paperops_source_gap_visibility_optional_gap_keys",
    "paperops_source_gap_visibility_required_gap_count",
    "paperops_source_gap_visibility_trade_blocking_gap_count",
    "paperops_source_gap_visibility_source_quorum_blocking_gap_count",
    "paperops_source_gap_visibility_silent_blocker_count",
    "paperops_source_gap_visibility_blocker_count",
    "paperops_source_gap_visibility_live_endpoint_called_count",
    "paperops_source_gap_visibility_broker_post_called_count",
    "paperops_source_gap_visibility_live_capital_enabled",
    "no_trade_rationale",
    "collection_state",
    "scheduler_status",
    "automation_id",
    "automation_name",
    "automation_status",
    "automation_rrule",
    "automation_kind",
    "automation_transport",
    "automation_active",
    "automation_hourly",
    "automation_cwd_bound",
    "automation_prompt_paperops_bound",
    "automation_prompt_digest",
    "automation_required_command_count",
    "automation_present_command_count",
    "automation_missing_commands",
    "automation_required_guardrail_count",
    "automation_present_guardrail_count",
    "automation_missing_guardrails",
    "paper_operational_cycle_status",
    "paper_operational_cycle_observed_status",
    "paper_operational_cycle_command_count",
    "paper_operational_cycle_command_passed_count",
    "paper_operational_cycle_command_failed_count",
    "paper_operational_cycle_observed_command_passed_count",
    "paper_operational_cycle_observed_command_failed_count",
    "paper_operational_cycle_self_observer_failed_count",
    "paper_operational_cycle_self_observer_failed_commands",
    "paper_operational_cycle_blocking_failed_commands",
    "paper_operational_cycle_safe_to_continue",
    "paper_operational_cycle_full_ready",
    "paper_operational_cycle_blocker_count",
    "paper_operational_cycle_blockers",
    "paper_operational_cycle_unsafe_write_counter_total",
    "dashboard_mirror_status",
    "dashboard_mirror_mode",
    "dashboard_mirror_public_safe",
    "dashboard_mirror_public_boundary",
    "dashboard_mirror_trigger_trading_allowed",
    "dashboard_mirror_secret_exposed",
    "paperops_notification_review_status",
    "paperops_notification_live_send_allowed_count",
    "paperops_notification_command_path_enabled_count",
    "paperops_notification_broker_write_allowed_count",
    "paperops_active_automation_status",
    "paperops_active_automation_enabled",
    "paperops_active_automation_qctrl_hold",
    "paperops_active_automation_submit_step_allowed",
    "paperops_active_automation_unattended_delegation_enabled",
    "paperops_active_automation_unattended_delegation_reason",
    "paperops_active_automation_idle_reason",
    "paperops_active_automation_idempotency_guard_message",
    "paperops_active_automation_live_endpoint_called_count",
    "paperops_cockpit_notification_upgrade_status",
    "paperops_cockpit_notification_upgrade_ready",
    "paperops_cockpit_notification_notification_ready",
    "paperops_cockpit_notification_readout_count",
    "paperops_cockpit_notification_notification_record_count",
    "paperops_cockpit_notification_qctrl_hold_visible",
    "paperops_cockpit_notification_submit_visible_as_held",
    "paperops_cockpit_notification_live_send_allowed_count",
    "paperops_cockpit_notification_command_path_enabled_count",
    "paperops_cockpit_notification_broker_write_allowed_count",
    "paperops_cockpit_notification_unsafe_write_counter_total",
    "paper_live_certification_status",
    "paper_live_certification_control_plane_certified",
    "paper_live_certification_paper_live_certified",
    "paper_live_certification_operation_allowed",
    "paper_live_certification_unattended_delegation_enabled",
    "paper_live_certification_unattended_delegation_reason",
    "paper_live_certification_submission_delegation_allowed",
    "paper_live_certification_blocker_count",
    "paper_live_certification_qctrl_hold_visible",
    "paper_live_certification_submit_visible_as_held",
    "paper_live_certification_phase7_30_day_run_complete",
    "paper_live_certification_phase7_demo_proof_certified",
    "paper_live_certification_unsafe_write_counter_total",
    "live_capital_enabled",
    "live_credentials_loaded",
    "phase7_proof_credit_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_called_count",
    "notification_live_send_allowed_count",
    "telegram_command_path_enabled_count",
    "broker_write_allowed_count",
    "unsafe_write_counter_total",
    "blockers",
    "blocker_count",
    "recommended_next_action",
    "boundary",
)

PAPEROPS_30_DAY_BOUNDARY = (
    "PaperOps-6 operates the active indefinite paper growth operation "
    "by verifying the hourly scheduler, PaperOps cycle, and public-safe "
    "dashboard mirror. It may bind the scheduler to the PT-8 active paper "
    "runner, but only through Alpaca paper and the recorded PaperOps gates. "
    "The original 30-day paper growth trial is retained as a legacy milestone "
    "only and does not stop PaperOps. It cannot backfill days, cannot simulate "
    "elapsed time, cannot force trades, cannot create trades without qualified "
    "setups, cannot submit broker orders outside the guarded PaperOps gates, "
    "cannot call live endpoints, cannot send live Telegram messages, cannot "
    "load live credentials, cannot bypass the Q-CTRL paper consultation hold, "
    "cannot grant proof credit, and cannot enable live capital. PT-9 cockpit "
    "and notification visibility remains public-safe and review-only."
    " PT-10 paper-live certification may evaluate the state only; it cannot "
    "bypass Q-CTRL, certify an incomplete proof run, submit orders, or enable "
    "live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def paperops_30_day_operations_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_30_DAY_OPERATIONS_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_30_DAY_OPERATIONS_HISTORY,
        runtime / PAPEROPS_30_DAY_OPERATIONS_EVENT_LOG,
    )


def read_latest_paperops_30_day_operations(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_30_day_operations_paths(settings)
    return _read_json(output_path)


def _automation_path() -> Path:
    return (
        Path.home()
        / ".codex"
        / "automations"
        / PAPEROPS_30_DAY_AUTOMATION_ID
        / "automation.toml"
    )


def _automation_config() -> dict[str, Any]:
    path = _automation_path()
    if not path.exists():
        return {
            "present": False,
            "id": PAPEROPS_30_DAY_AUTOMATION_ID,
            "name": PAPEROPS_30_DAY_AUTOMATION_NAME,
            "status": "missing",
            "kind": "missing",
            "rrule": "",
            "prompt": "",
            "cwds": [],
        }
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    payload["present"] = True
    return payload


def _automation_status(automation: dict[str, Any], settings: Settings) -> dict[str, Any]:
    prompt = str(automation.get("prompt") or "")
    cwds = automation.get("cwds") or []
    if isinstance(cwds, str):
        cwds = [cwds]
    repo_root = str(_repo_root(settings).resolve())
    command_presence = {
        command: command in prompt for command in REQUIRED_AUTOMATION_COMMAND_FRAGMENTS
    }
    guardrail_presence = {
        guardrail: guardrail.lower() in prompt.lower()
        for guardrail in REQUIRED_AUTOMATION_GUARDRAIL_FRAGMENTS
    }
    missing_commands = [
        command for command, present in command_presence.items() if not present
    ]
    missing_guardrails = [
        guardrail for guardrail, present in guardrail_presence.items() if not present
    ]
    rrule = str(automation.get("rrule") or "")
    status = str(automation.get("status") or "missing")
    kind = str(automation.get("kind") or "missing")
    return {
        "automation_id": str(automation.get("id") or PAPEROPS_30_DAY_AUTOMATION_ID),
        "automation_name": str(automation.get("name") or PAPEROPS_30_DAY_AUTOMATION_NAME),
        "automation_status": status,
        "automation_rrule": rrule,
        "automation_kind": kind,
        "automation_transport": str(automation.get("execution_environment") or "local"),
        "automation_active": status == "ACTIVE" and kind == "cron",
        "automation_hourly": rrule == "FREQ=HOURLY;INTERVAL=1",
        "automation_cwd_bound": repo_root in [str(item) for item in cwds],
        "automation_prompt_paperops_bound": not missing_commands and not missing_guardrails,
        "automation_prompt_digest": (
            hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else None
        ),
        "automation_required_command_count": len(REQUIRED_AUTOMATION_COMMAND_FRAGMENTS),
        "automation_present_command_count": sum(command_presence.values()),
        "automation_missing_commands": missing_commands,
        "automation_required_guardrail_count": len(REQUIRED_AUTOMATION_GUARDRAIL_FRAGMENTS),
        "automation_present_guardrail_count": sum(guardrail_presence.values()),
        "automation_missing_guardrails": missing_guardrails,
    }


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "demo_run": _read_json(runtime / "phase7_demo_proof_run.json"),
        "cycle": _read_json(runtime / "paper_operational_cycle.json"),
        "readiness": _read_json(runtime / "paper_operational_readiness.json"),
        "notification_review": _read_json(runtime / "paperops_notification_review.json"),
        "active_automation": _read_json(
            runtime / "paperops_active_paper_trading_automation.json"
        ),
        "cockpit_notification_upgrade": _read_json(
            runtime / "paperops_cockpit_notification_upgrade.json"
        ),
        "paper_live_certification": _read_json(runtime / "paper_live_certification.json"),
        "cockpit": _read_json(runtime / "cockpit-status.json"),
    }


def _dashboard_mirror_status(cockpit: dict[str, Any]) -> dict[str, Any]:
    mission = cockpit.get("mission_control", {}) if isinstance(cockpit, dict) else {}
    boundary = str(cockpit.get("boundary") or mission.get("boundary") or "")
    public_safe = (
        bool(cockpit)
        and cockpit.get("mode") == "paper"
        and mission.get("status") == "read_only_mission_control"
        and "Public-safe read-only snapshot" in boundary
        and "cannot trigger trading" in boundary
    )
    return {
        "dashboard_mirror_status": mission.get("status", "missing"),
        "dashboard_mirror_mode": cockpit.get("mode", "missing"),
        "dashboard_mirror_public_safe": public_safe,
        "dashboard_mirror_public_boundary": boundary,
        "dashboard_mirror_trigger_trading_allowed": False if public_safe else None,
        "dashboard_mirror_secret_exposed": False,
    }


def _cycle_status(cycle: dict[str, Any]) -> dict[str, Any]:
    command_count = _int(cycle.get("command_count"))
    observed_passed_count = _int(cycle.get("command_passed_count"))
    observed_failed_count = _int(cycle.get("command_failed_count"))
    failed_commands = [
        str(label)
        for label in (cycle.get("failed_commands") or [])
        if str(label).strip()
    ]
    self_observer_failures = [
        label for label in failed_commands if label in SELF_OBSERVER_CYCLE_FAILURE_LABELS
    ]
    blocking_failures = [
        label
        for label in failed_commands
        if label not in SELF_OBSERVER_CYCLE_FAILURE_LABELS
    ]
    blocking_failed_count = (
        len(blocking_failures) if failed_commands else observed_failed_count
    )
    effective_passed_count = max(0, command_count - blocking_failed_count)
    hard_safety_failures = _int(cycle.get("hard_safety_failure_count"))
    unsafe_total = _int(cycle.get("unsafe_write_counter_total"))
    raw_status = str(cycle.get("status") or "missing")
    effective_status = raw_status
    if (
        raw_status == "paper_cycle_failed"
        and failed_commands
        and not blocking_failures
        and command_count >= 22
        and hard_safety_failures == 0
        and unsafe_total == 0
    ):
        effective_status = "paper_cycle_self_observer_recovery"
    return {
        "paper_operational_cycle_status": effective_status,
        "paper_operational_cycle_observed_status": raw_status,
        "paper_operational_cycle_command_count": command_count,
        "paper_operational_cycle_command_passed_count": effective_passed_count,
        "paper_operational_cycle_command_failed_count": blocking_failed_count,
        "paper_operational_cycle_observed_command_passed_count": observed_passed_count,
        "paper_operational_cycle_observed_command_failed_count": observed_failed_count,
        "paper_operational_cycle_self_observer_failed_count": len(
            self_observer_failures
        ),
        "paper_operational_cycle_self_observer_failed_commands": self_observer_failures,
        "paper_operational_cycle_blocking_failed_commands": blocking_failures,
        "paper_operational_cycle_safe_to_continue": (
            cycle.get("safe_to_continue_paper_only") is True
            or (
                command_count >= 22
                and blocking_failed_count == 0
                and hard_safety_failures == 0
                and unsafe_total == 0
            )
        ),
        "paper_operational_cycle_full_ready": (
            cycle.get("full_paper_operational_ready") is True
        ),
        "paper_operational_cycle_blocker_count": _int(cycle.get("blocker_count")),
        "paper_operational_cycle_blockers": cycle.get("blockers", []) or [],
        "paper_operational_cycle_unsafe_write_counter_total": unsafe_total,
    }


def _blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("actual_calendar_run") is not True:
        blockers.append("phase7_actual_calendar_run_not_confirmed")
    if artifact.get("scheduled_calendar_day_count") != 30:
        blockers.append("phase7_30_day_window_not_confirmed")
    if artifact.get("consecutive_calendar_days_preserved") is not True:
        blockers.append("phase7_consecutive_calendar_days_not_preserved")
    if artifact.get("backfill_used") is not False:
        blockers.append("backfill_detected")
    if artifact.get("simulated_time_used") is not False:
        blockers.append("simulated_time_detected")
    if artifact.get("no_forced_trades") is not True:
        blockers.append("forced_trade_policy_not_confirmed")
    if artifact.get("automation_active") is not True:
        blockers.append("paperops_scheduler_not_active")
    if artifact.get("automation_hourly") is not True:
        blockers.append("paperops_scheduler_not_hourly")
    if artifact.get("automation_cwd_bound") is not True:
        blockers.append("paperops_scheduler_not_bound_to_qadam_workspace")
    if artifact.get("automation_prompt_paperops_bound") is not True:
        blockers.append("paperops_scheduler_prompt_not_paperops_bound")
    if artifact.get("paper_operational_cycle_command_count", 0) < 22:
        blockers.append("paperops_cycle_not_established")
    if artifact.get("paper_operational_cycle_command_failed_count") != 0:
        blockers.append("paperops_cycle_command_failed")
    if artifact.get("paper_operational_cycle_safe_to_continue") is not True:
        blockers.append("paperops_cycle_not_safe_to_continue")
    if artifact.get("dashboard_mirror_public_safe") is not True:
        blockers.append("dashboard_mirror_not_public_safe")
    if artifact.get("paperops_submit_regression_guard_status") == (
        "blocked_submit_regression"
    ):
        blockers.append("paperops_submit_regression_guard_blocked")
    if _int(artifact.get("paperops_submit_regression_guard_blocker_count")):
        blockers.append("paperops_submit_regression_guard_has_blockers")
    if _int(
        artifact.get("paperops_submit_regression_guard_validation_error_count")
    ):
        blockers.append("paperops_submit_regression_guard_invalid")
    if _int(
        artifact.get("paperops_submit_regression_guard_source_stale_after_post_count")
    ):
        blockers.append("paperops_submit_regression_source_stale")
    if _int(
        artifact.get(
            "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count"
        )
    ):
        blockers.append("paperops_submit_regression_fresh_ledger_collision")
    if _int(
        artifact.get(
            "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count"
        )
    ):
        blockers.append("paperops_submit_regression_duplicate_misclassified")
    if artifact.get("paperops_source_gap_visibility_status") not in {
        "explicit_optional_source_gaps",
        "all_optional_sources_configured",
    }:
        blockers.append("paperops_source_gap_visibility_invalid")
    if artifact.get("paperops_source_gap_visibility_policy_status") != (
        "optional_gaps_explicit_non_blocking"
    ):
        blockers.append("paperops_source_gap_visibility_policy_invalid")
    if _int(artifact.get("paperops_source_gap_visibility_required_gap_count")):
        blockers.append("paperops_source_gap_required_gap_present")
    if _int(artifact.get("paperops_source_gap_visibility_trade_blocking_gap_count")):
        blockers.append("paperops_source_gap_trade_blocking")
    if _int(
        artifact.get("paperops_source_gap_visibility_source_quorum_blocking_gap_count")
    ):
        blockers.append("paperops_source_gap_source_quorum_blocking")
    if _int(artifact.get("paperops_source_gap_visibility_silent_blocker_count")):
        blockers.append("paperops_source_gap_silent_blocker")
    if _int(artifact.get("paperops_source_gap_visibility_blocker_count")):
        blockers.append("paperops_source_gap_visibility_has_blockers")
    if artifact.get("paperops_cockpit_notification_upgrade_status") != (
        "cockpit_notification_upgrade_ready"
    ):
        blockers.append("cockpit_notification_upgrade_not_ready")
    if artifact.get("unsafe_write_counter_total") != 0:
        blockers.append("paperops_30_day_unsafe_counter_nonzero")
    return blockers


def _recommended_next_action(artifact: dict[str, Any]) -> str:
    if artifact.get("status") == "operations_active":
        return "Keep the hourly PaperOps runner active and submit only fresh eligible Alpaca paper setups"
    if artifact.get("status") == "operations_complete_pending_certification":
        return "Legacy state only: keep PaperOps running as an indefinite paper operation"
    if artifact.get("automation_prompt_paperops_bound") is not True:
        return "Update the existing hourly automation prompt to run the canonical PaperOps autonomous pass wrapper"
    if artifact.get("dashboard_mirror_public_safe") is not True:
        return "Refresh the public-safe cockpit mirror before continuing PaperOps operations"
    return "Resolve PaperOps-6 blockers before relying on the scheduled paper operation"


def build_paperops_30_day_operations(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    demo_run = snapshot["demo_run"]
    cycle = snapshot["cycle"]
    notification_review = snapshot["notification_review"]
    active_automation = snapshot["active_automation"]
    cockpit_notification_upgrade = snapshot["cockpit_notification_upgrade"]
    paper_live_certification = snapshot["paper_live_certification"]
    close_to_ledger = build_paperops_close_to_ledger(settings=settings)
    submit_regression_guard = build_paperops_submit_regression_guard(settings=settings)
    source_gap_visibility = build_paperops_source_gap_visibility(settings=settings)
    automation = _automation_status(_automation_config(), settings)
    dashboard = _dashboard_mirror_status(snapshot["cockpit"])
    cycle_summary = _cycle_status(cycle)

    notification_live_send_count = _int(
        notification_review.get("live_send_allowed_count")
    )
    notification_command_count = _int(
        notification_review.get("telegram_command_path_enabled_count")
    )
    notification_broker_write_count = _int(
        notification_review.get("broker_write_allowed_count")
    )
    active_automation_live_endpoint_count = _int(
        active_automation.get("live_endpoint_called_count")
    )
    cockpit_notification_live_send_count = _int(
        cockpit_notification_upgrade.get("notification_live_send_allowed_count")
    )
    cockpit_notification_command_count = _int(
        cockpit_notification_upgrade.get("notification_command_path_enabled_count")
    )
    cockpit_notification_broker_write_count = _int(
        cockpit_notification_upgrade.get("notification_broker_write_allowed_count")
    )
    cockpit_notification_unsafe_count = _int(
        cockpit_notification_upgrade.get("unsafe_write_counter_total")
    )
    paper_live_certification_unsafe_count = _int(
        paper_live_certification.get("unsafe_write_counter_total")
    )
    unsafe_total = sum(
        _int(value)
        for value in (
            demo_run.get("broker_post_called_count"),
            demo_run.get("alpaca_post_called_count"),
            demo_run.get("live_endpoint_allowed_count"),
            notification_live_send_count,
            notification_command_count,
            notification_broker_write_count,
            active_automation_live_endpoint_count,
            submit_regression_guard.get("live_endpoint_called_count"),
            submit_regression_guard.get("broker_post_called_count"),
            source_gap_visibility.get("live_endpoint_called_count"),
            source_gap_visibility.get("broker_post_called_count"),
            cockpit_notification_live_send_count,
            cockpit_notification_command_count,
            cockpit_notification_broker_write_count,
            cockpit_notification_unsafe_count,
            paper_live_certification_unsafe_count,
            cycle_summary["paper_operational_cycle_unsafe_write_counter_total"],
        )
    )

    artifact = {
        "schema_version": PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION,
        "artifact_type": "paperops_30_day_operations",
        "artifact_id": "paperops:30-day-operations:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-6",
        "status": "pending_validation",
        "generated_at": generated_at,
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
        "mode": settings.mode,
        "paper_operational_enabled": settings.paper_operational_enabled,
        "run_id": demo_run.get("run_id"),
        "run_state": demo_run.get("run_state", "missing"),
        "start_date": demo_run.get("start_date"),
        "end_date": demo_run.get("end_date"),
        "operation_horizon": demo_run.get("operation_horizon", "indefinite"),
        "legacy_30_day_milestone_complete": (
            demo_run.get("legacy_30_day_milestone_complete") is True
            or demo_run.get("phase7_30_day_run_complete") is True
        ),
        "actual_elapsed_calendar_day_count": _int(
            demo_run.get("actual_elapsed_calendar_day_count")
        ),
        "paper_operation_day_number": demo_run.get("paper_operation_day_number")
        or demo_run.get("active_day_number"),
        "timezone": demo_run.get("timezone"),
        "local_observation_date": demo_run.get("local_observation_date"),
        "actual_calendar_run": demo_run.get("actual_calendar_run") is True,
        "scheduled_calendar_day_count": _int(
            demo_run.get("scheduled_calendar_day_count")
        ),
        "active_day_number": demo_run.get("active_day_number"),
        "completed_calendar_day_count": _int(
            demo_run.get("completed_calendar_day_count")
        ),
        "calendar_days_remaining": _int(demo_run.get("calendar_days_remaining")),
        "phase7_30_day_run_complete": (
            demo_run.get("phase7_30_day_run_complete") is True
        ),
        "consecutive_calendar_days_preserved": (
            demo_run.get("consecutive_calendar_days_preserved") is True
        ),
        "backfill_used": demo_run.get("backfill_used") is True,
        "simulated_time_used": demo_run.get("simulated_time_used") is True,
        "no_forced_trades": demo_run.get("no_forced_trades") is True,
        "qualified_setup_count": _int(demo_run.get("qualified_setup_count")),
        "submitted_paper_order_count": _int(
            demo_run.get("submitted_paper_order_count")
        ),
        "closed_proof_trade_count": max(
            _int(demo_run.get("closed_proof_trade_count")),
            _int(close_to_ledger.get("closed_proof_trade_count")),
        ),
        "paperops_close_to_ledger_status": close_to_ledger.get("status", "missing"),
        "paperops_close_to_ledger_closed_proof_trade_count": _int(
            close_to_ledger.get("closed_proof_trade_count")
        ),
        "paperops_close_to_ledger_postmortem_due_marker_created_count": _int(
            close_to_ledger.get("postmortem_due_marker_created_count")
        ),
        "paperops_close_to_ledger_blocker_count": _int(
            close_to_ledger.get("blocker_count")
        ),
        "paperops_submit_regression_guard_status": submit_regression_guard.get(
            "status", "missing"
        ),
        "paperops_submit_regression_guard_source_paperops2_status": (
            submit_regression_guard.get("source_paperops2_status", "missing")
        ),
        "paperops_submit_regression_guard_fresh_eligible_submit_record_count": _int(
            submit_regression_guard.get("fresh_eligible_submit_record_count")
        ),
        "paperops_submit_regression_guard_duplicate_submit_record_count": _int(
            submit_regression_guard.get("duplicate_submit_record_count")
        ),
        "paperops_submit_regression_guard_source_stale_after_post_count": _int(
            submit_regression_guard.get("source_stale_after_post_tolerance_count")
        ),
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count": _int(
            submit_regression_guard.get("fresh_submitted_ledger_collision_count")
        ),
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count": _int(
            submit_regression_guard.get("duplicate_misclassified_as_fresh_count")
        ),
        "paperops_submit_regression_guard_blocker_count": _int(
            submit_regression_guard.get("blocker_count")
        ),
        "paperops_submit_regression_guard_validation_error_count": _int(
            submit_regression_guard.get("validation_error_count")
        ),
        "paperops_source_gap_visibility_status": source_gap_visibility.get(
            "status", "missing"
        ),
        "paperops_source_gap_visibility_policy_status": source_gap_visibility.get(
            "source_gap_policy_status", "missing"
        ),
        "paperops_source_gap_visibility_optional_gap_count": _int(
            source_gap_visibility.get("optional_gap_count")
        ),
        "paperops_source_gap_visibility_optional_gap_keys": [
            str(key)
            for key in source_gap_visibility.get("optional_gap_keys", []) or []
            if str(key).strip()
        ],
        "paperops_source_gap_visibility_required_gap_count": _int(
            source_gap_visibility.get("required_gap_count")
        ),
        "paperops_source_gap_visibility_trade_blocking_gap_count": _int(
            source_gap_visibility.get("trade_blocking_source_gap_count")
        ),
        "paperops_source_gap_visibility_source_quorum_blocking_gap_count": _int(
            source_gap_visibility.get("source_quorum_blocking_gap_count")
        ),
        "paperops_source_gap_visibility_silent_blocker_count": _int(
            source_gap_visibility.get("silent_blocker_count")
        ),
        "paperops_source_gap_visibility_blocker_count": _int(
            source_gap_visibility.get("blocker_count")
        ),
        "paperops_source_gap_visibility_live_endpoint_called_count": _int(
            source_gap_visibility.get("live_endpoint_called_count")
        ),
        "paperops_source_gap_visibility_broker_post_called_count": _int(
            source_gap_visibility.get("broker_post_called_count")
        ),
        "paperops_source_gap_visibility_live_capital_enabled": (
            source_gap_visibility.get("live_capital_enabled") is True
        ),
        "no_trade_rationale": demo_run.get("no_trade_rationale"),
        "collection_state": demo_run.get("collection_state"),
        "scheduler_status": "active_hourly_paperops_runner",
        **automation,
        **cycle_summary,
        **dashboard,
        "paperops_notification_review_status": notification_review.get(
            "status",
            "missing",
        ),
        "paperops_notification_live_send_allowed_count": notification_live_send_count,
        "paperops_notification_command_path_enabled_count": notification_command_count,
        "paperops_notification_broker_write_allowed_count": notification_broker_write_count,
        "paperops_active_automation_status": active_automation.get(
            "status",
            "missing",
        ),
        "paperops_active_automation_enabled": (
            active_automation.get("active_paper_trading_automation_enabled") is True
        ),
        "paperops_active_automation_qctrl_hold": (
            active_automation.get("qctrl_consultation_hold_active") is True
        ),
        "paperops_active_automation_submit_step_allowed": (
            active_automation.get("paper_submit_step_allowed") is True
        ),
        "paperops_active_automation_unattended_delegation_enabled": (
            active_automation.get(
                "unattended_paper_execution_delegation_enabled"
            )
            is True
        ),
        "paperops_active_automation_unattended_delegation_reason": (
            active_automation.get(
                "unattended_paper_execution_delegation_reason"
            )
            or "not_armed"
        ),
        "paperops_active_automation_idle_reason": (
            active_automation.get("idle_reason") or ""
        ),
        "paperops_active_automation_idempotency_guard_message": (
            active_automation.get("idempotency_guard_message") or ""
        ),
        "paperops_active_automation_live_endpoint_called_count": (
            active_automation_live_endpoint_count
        ),
        "paperops_cockpit_notification_upgrade_status": (
            cockpit_notification_upgrade.get("status", "missing")
        ),
        "paperops_cockpit_notification_upgrade_ready": (
            cockpit_notification_upgrade.get("cockpit_upgrade_ready") is True
        ),
        "paperops_cockpit_notification_notification_ready": (
            cockpit_notification_upgrade.get("notification_upgrade_ready") is True
        ),
        "paperops_cockpit_notification_readout_count": _int(
            cockpit_notification_upgrade.get("fund_manager_readout_count")
        ),
        "paperops_cockpit_notification_notification_record_count": _int(
            cockpit_notification_upgrade.get("notification_record_count")
        ),
        "paperops_cockpit_notification_qctrl_hold_visible": (
            cockpit_notification_upgrade.get("qctrl_hold_visible") is True
        ),
        "paperops_cockpit_notification_submit_visible_as_held": (
            cockpit_notification_upgrade.get("paper_submit_visible_as_held") is True
        ),
        "paperops_cockpit_notification_live_send_allowed_count": (
            cockpit_notification_live_send_count
        ),
        "paperops_cockpit_notification_command_path_enabled_count": (
            cockpit_notification_command_count
        ),
        "paperops_cockpit_notification_broker_write_allowed_count": (
            cockpit_notification_broker_write_count
        ),
        "paperops_cockpit_notification_unsafe_write_counter_total": (
            cockpit_notification_unsafe_count
        ),
        "paper_live_certification_status": paper_live_certification.get(
            "status",
            "missing",
        ),
        "paper_live_certification_control_plane_certified": (
            paper_live_certification.get("paper_live_control_plane_certified") is True
        ),
        "paper_live_certification_paper_live_certified": (
            paper_live_certification.get("paper_live_certified") is True
        ),
        "paper_live_certification_operation_allowed": (
            paper_live_certification.get("paper_live_operation_allowed") is True
        ),
        "paper_live_certification_unattended_delegation_enabled": (
            paper_live_certification.get(
                "paper_live_unattended_execution_delegation_enabled"
            )
            is True
        ),
        "paper_live_certification_unattended_delegation_reason": (
            paper_live_certification.get(
                "paper_live_unattended_execution_delegation_reason"
            )
            or "not_armed"
        ),
        "paper_live_certification_submission_delegation_allowed": (
            paper_live_certification.get("paper_live_submission_delegation_allowed")
            is True
        ),
        "paper_live_certification_blocker_count": _int(
            paper_live_certification.get("certification_blocker_count")
        ),
        "paper_live_certification_qctrl_hold_visible": (
            paper_live_certification.get("qctrl_hold_visible") is True
        ),
        "paper_live_certification_submit_visible_as_held": (
            paper_live_certification.get("paper_submit_visible_as_held") is True
        ),
        "paper_live_certification_phase7_30_day_run_complete": (
            paper_live_certification.get("phase7_30_day_run_complete") is True
        ),
        "paper_live_certification_phase7_demo_proof_certified": (
            paper_live_certification.get("phase7_demo_proof_certified") is True
        ),
        "paper_live_certification_unsafe_write_counter_total": (
            paper_live_certification_unsafe_count
        ),
        "live_capital_enabled": settings.live_capital_enabled,
        "live_credentials_loaded": _safe_bool(demo_run.get("live_credentials_loaded")),
        "phase7_proof_credit_allowed": (
            demo_run.get("phase7_proof_credit_allowed") is True
        ),
        "broker_post_called_count": _int(demo_run.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(demo_run.get("alpaca_post_called_count")),
        "live_endpoint_called_count": _int(demo_run.get("live_endpoint_allowed_count")),
        "notification_live_send_allowed_count": notification_live_send_count,
        "telegram_command_path_enabled_count": notification_command_count,
        "broker_write_allowed_count": notification_broker_write_count,
        "unsafe_write_counter_total": unsafe_total,
        "boundary": PAPEROPS_30_DAY_BOUNDARY,
    }
    blockers = _blockers(artifact)
    if blockers:
        status = "blocked_pending_operations_enablement"
    else:
        status = "operations_active"
    artifact["blockers"] = blockers
    artifact["blocker_count"] = len(blockers)
    artifact["status"] = status
    artifact["scheduler_status"] = (
        "active_hourly_paperops_runner"
        if artifact.get("automation_active")
        and artifact.get("automation_hourly")
        and artifact.get("automation_prompt_paperops_bound")
        else "scheduler_pending_paperops_binding"
    )
    artifact["recommended_next_action"] = _recommended_next_action(artifact)
    artifact["validation_errors"] = validate_paperops_30_day_operations(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    artifact["public_status"] = paperops_30_day_operations_public_status_from_artifact(
        artifact
    )
    return artifact


def validate_paperops_30_day_operations(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PAPEROPS_30_DAY_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "event_log_correlation_id",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_30_day_operations_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION:
        errors.append("paperops_30_day_operations_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_30_day_operations":
        errors.append("paperops_30_day_operations_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-6":
        errors.append("paperops_30_day_operations_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_30_day_operations_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_30_day_operations_mode_not_paper")
    if artifact.get("actual_calendar_run") is not True:
        errors.append("paperops_30_day_operations_not_actual_calendar")
    if artifact.get("scheduled_calendar_day_count") != 30:
        errors.append("paperops_30_day_operations_day_count_mismatch")
    if artifact.get("consecutive_calendar_days_preserved") is not True:
        errors.append("paperops_30_day_operations_calendar_not_consecutive")
    if artifact.get("backfill_used") is not False:
        errors.append("paperops_30_day_operations_backfill_used")
    if artifact.get("simulated_time_used") is not False:
        errors.append("paperops_30_day_operations_simulated_time_used")
    if artifact.get("no_forced_trades") is not True:
        errors.append("paperops_30_day_operations_forced_trades_allowed")
    if artifact.get("qualified_setup_count", 0) == 0 and (
        _int(artifact.get("submitted_paper_order_count")) > 0
        or _int(artifact.get("closed_proof_trade_count")) > 0
    ):
        errors.append("paperops_30_day_operations_trade_without_qualified_setup")
    for key in (
        "automation_active",
        "automation_hourly",
        "automation_cwd_bound",
        "automation_prompt_paperops_bound",
    ):
        if artifact.get(key) is not True:
            errors.append(f"paperops_30_day_operations_scheduler_not_ready:{key}")
    if artifact.get("automation_present_command_count") != artifact.get(
        "automation_required_command_count"
    ):
        errors.append("paperops_30_day_operations_scheduler_command_missing")
    if artifact.get("automation_present_guardrail_count") != artifact.get(
        "automation_required_guardrail_count"
    ):
        errors.append("paperops_30_day_operations_scheduler_guardrail_missing")
    if artifact.get("paper_operational_cycle_command_count", 0) < 22:
        errors.append("paperops_30_day_operations_cycle_missing")
    if artifact.get("paper_operational_cycle_command_failed_count") != 0:
        errors.append("paperops_30_day_operations_cycle_failed_commands")
    if artifact.get("paper_operational_cycle_command_passed_count") != artifact.get(
        "paper_operational_cycle_command_count"
    ):
        errors.append("paperops_30_day_operations_cycle_not_all_passed")
    if artifact.get("paper_operational_cycle_safe_to_continue") is not True:
        errors.append("paperops_30_day_operations_cycle_not_safe")
    if artifact.get("dashboard_mirror_public_safe") is not True:
        errors.append("paperops_30_day_operations_dashboard_not_public_safe")
    if artifact.get("dashboard_mirror_status") != "read_only_mission_control":
        errors.append("paperops_30_day_operations_dashboard_not_read_only")
    if artifact.get("dashboard_mirror_mode") != "paper":
        errors.append("paperops_30_day_operations_dashboard_not_paper")
    if artifact.get("dashboard_mirror_trigger_trading_allowed") is not False:
        errors.append("paperops_30_day_operations_dashboard_can_trigger_trading")
    if artifact.get("paperops_submit_regression_guard_status") not in {
        "healthy_idle_idempotency_guarded",
        "healthy_idle_no_fresh_submit",
        "healthy_submitted_idempotency_recorded",
        "ready_fresh_submit_consistent",
    }:
        errors.append("paperops_30_day_operations_submit_regression_guard_not_ready")
    if _int(artifact.get("paperops_submit_regression_guard_blocker_count")) != 0:
        errors.append("paperops_30_day_operations_submit_regression_guard_blocked")
    if _int(
        artifact.get("paperops_submit_regression_guard_validation_error_count")
    ) != 0:
        errors.append("paperops_30_day_operations_submit_regression_guard_invalid")
    for key in (
        "paperops_submit_regression_guard_source_stale_after_post_count",
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(
                f"paperops_30_day_operations_submit_regression_counter_nonzero:{key}"
            )
    if artifact.get("paperops_source_gap_visibility_status") not in {
        "explicit_optional_source_gaps",
        "all_optional_sources_configured",
    }:
        errors.append("paperops_30_day_operations_source_gap_visibility_not_ready")
    if artifact.get("paperops_source_gap_visibility_policy_status") != (
        "optional_gaps_explicit_non_blocking"
    ):
        errors.append("paperops_30_day_operations_source_gap_visibility_policy_invalid")
    if _int(artifact.get("paperops_source_gap_visibility_blocker_count")) != 0:
        errors.append("paperops_30_day_operations_source_gap_visibility_blocked")
    for key in (
        "paperops_source_gap_visibility_required_gap_count",
        "paperops_source_gap_visibility_trade_blocking_gap_count",
        "paperops_source_gap_visibility_source_quorum_blocking_gap_count",
        "paperops_source_gap_visibility_silent_blocker_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(
                f"paperops_30_day_operations_source_gap_counter_nonzero:{key}"
            )
    if artifact.get("paperops_source_gap_visibility_live_capital_enabled") is not False:
        errors.append("paperops_30_day_operations_source_gap_live_capital_enabled")
    for key in (
        "live_capital_enabled",
        "live_credentials_loaded",
        "phase7_proof_credit_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_30_day_operations_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "notification_live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "broker_write_allowed_count",
        "paperops_notification_live_send_allowed_count",
        "paperops_notification_command_path_enabled_count",
        "paperops_notification_broker_write_allowed_count",
        "paperops_active_automation_live_endpoint_called_count",
        "paperops_source_gap_visibility_live_endpoint_called_count",
        "paperops_source_gap_visibility_broker_post_called_count",
        "paperops_cockpit_notification_live_send_allowed_count",
        "paperops_cockpit_notification_command_path_enabled_count",
        "paperops_cockpit_notification_broker_write_allowed_count",
        "paperops_cockpit_notification_unsafe_write_counter_total",
        "paper_live_certification_unsafe_write_counter_total",
        "paper_operational_cycle_unsafe_write_counter_total",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_30_day_operations_unsafe_counter_nonzero:{key}")
    if artifact.get("paperops_active_automation_status") not in {
        "active_automation_enabled_idle",
        "active_automation_enabled_qctrl_hold",
        "active_automation_ready_to_submit",
        "active_automation_ready_to_poll",
        "active_automation_ready_to_exit",
    }:
        errors.append("paperops_30_day_operations_active_automation_not_enabled")
    if artifact.get("paperops_active_automation_enabled") is not True:
        errors.append("paperops_30_day_operations_active_automation_disabled")
    if (
        artifact.get("paperops_active_automation_qctrl_hold") is True
        and artifact.get("paperops_active_automation_submit_step_allowed") is True
    ):
        errors.append("paperops_30_day_operations_active_automation_qctrl_bypass")
    if artifact.get("paperops_cockpit_notification_upgrade_status") != (
        "cockpit_notification_upgrade_ready"
    ):
        errors.append("paperops_30_day_operations_cockpit_notification_not_ready")
    if artifact.get("paperops_cockpit_notification_upgrade_ready") is not True:
        errors.append("paperops_30_day_operations_cockpit_notification_flag_false")
    if artifact.get("paperops_cockpit_notification_notification_ready") is not True:
        errors.append("paperops_30_day_operations_cockpit_notification_review_false")
    if _int(artifact.get("paperops_cockpit_notification_readout_count")) < 5:
        errors.append("paperops_30_day_operations_cockpit_notification_readouts_missing")
    if (
        artifact.get("paperops_cockpit_notification_qctrl_hold_visible") is True
        and artifact.get("paperops_cockpit_notification_submit_visible_as_held")
        is not True
    ):
        errors.append("paperops_30_day_operations_cockpit_notification_qctrl_not_visible")
    if artifact.get("paper_live_certification_status") not in {
        *PAPER_LIVE_CERTIFICATION_ACCEPTED_STATUSES,
    }:
        errors.append("paperops_30_day_operations_paper_live_certification_not_evaluated")
    paper_live_certified = artifact.get("paper_live_certification_paper_live_certified") is True
    if paper_live_certified:
        if artifact.get("paper_live_certification_operation_allowed") is not True:
            errors.append("paperops_30_day_operations_paper_live_certified_without_operation")
        if artifact.get("paper_live_certification_unattended_delegation_enabled") is not True:
            errors.append("paperops_30_day_operations_paper_live_certified_without_unattended")
        if _int(artifact.get("paper_live_certification_blocker_count")) != 0:
            errors.append("paperops_30_day_operations_paper_live_certified_with_blockers")
    else:
        if artifact.get("paper_live_certification_operation_allowed") is not False:
            errors.append("paperops_30_day_operations_paper_live_operation_allowed_while_blocked")
        if artifact.get("paper_live_certification_unattended_delegation_enabled") is not False:
            errors.append("paperops_30_day_operations_paper_live_unattended_while_blocked")
        if _int(artifact.get("paper_live_certification_blocker_count")) < 1:
            errors.append("paperops_30_day_operations_paper_live_blockers_missing")
    if (
        artifact.get("paper_live_certification_submission_delegation_allowed") is True
        and artifact.get("paper_live_certification_paper_live_certified") is not True
    ):
        errors.append("paperops_30_day_operations_paper_live_submission_delegated_while_blocked")
    if (
        artifact.get("paper_live_certification_qctrl_hold_visible") is True
        and artifact.get("paper_live_certification_submit_visible_as_held") is not True
    ):
        errors.append("paperops_30_day_operations_paper_live_submit_hold_not_visible")
    if (
        artifact.get("recorded") is True
        and artifact.get("event_log_required") is True
        and artifact.get("event_log_written") is not True
    ):
        errors.append("paperops_30_day_operations_event_log_missing")
    if artifact.get("event_log_written") is True:
        if artifact.get("event_log_event_count") != 1:
            errors.append("paperops_30_day_operations_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paperops_30_day_operations_event_correlation_missing")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "active indefinite paper growth operation",
        "legacy milestone only",
        "cannot backfill days",
        "cannot simulate elapsed time",
        "cannot force trades",
        "cannot submit broker orders",
        "cannot call live endpoints",
        "cannot grant proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_30_day_operations_boundary_weak")
            break
    if artifact.get("status") == "operations_active" and artifact.get("blocker_count"):
        errors.append("paperops_30_day_operations_active_with_blockers")
    return sorted(set(errors))


def paperops_30_day_operations_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPEROPS_30_DAY_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    return public_status


def paperops_30_day_operations_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_30_day_operations(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-6",
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "run_id": None,
            "run_state": "missing",
            "active_day_number": None,
            "completed_calendar_day_count": 0,
            "calendar_days_remaining": 30,
            "qualified_setup_count": 0,
            "submitted_paper_order_count": 0,
            "closed_proof_trade_count": 0,
            "paperops_submit_regression_guard_status": "not_run",
            "paperops_submit_regression_guard_fresh_eligible_submit_record_count": 0,
            "paperops_submit_regression_guard_duplicate_submit_record_count": 0,
            "paperops_submit_regression_guard_blocker_count": 0,
            "scheduler_status": "not_run",
            "automation_active": False,
            "automation_prompt_paperops_bound": False,
            "paper_operational_cycle_status": "missing",
            "paper_operational_cycle_command_count": 0,
            "dashboard_mirror_status": "missing",
            "dashboard_mirror_public_safe": False,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "unsafe_write_counter_total": 0,
            "validation_error_count": 0,
            "boundary": PAPEROPS_30_DAY_BOUNDARY,
        }
    return paperops_30_day_operations_public_status_from_artifact(artifact)


def attach_paperops_30_day_operations_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PAPEROPS_30_DAY_OPERATIONS_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPEROPS_30_DAY_OPERATIONS_EVENT_TYPE,
        PAPEROPS_30_DAY_OPERATIONS_COMPONENT,
        {
            "status": output.get("status"),
            "run_id": output.get("run_id"),
            "run_state": output.get("run_state"),
            "active_day_number": output.get("active_day_number"),
            "completed_calendar_day_count": output.get("completed_calendar_day_count"),
            "calendar_days_remaining": output.get("calendar_days_remaining"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "submitted_paper_order_count": output.get("submitted_paper_order_count"),
            "closed_proof_trade_count": output.get("closed_proof_trade_count"),
            "scheduler_status": output.get("scheduler_status"),
            "automation_prompt_paperops_bound": output.get(
                "automation_prompt_paperops_bound"
            ),
            "paper_operational_cycle_status": output.get(
                "paper_operational_cycle_status"
            ),
            "dashboard_mirror_status": output.get("dashboard_mirror_status"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "blocker_count": output.get("blocker_count"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_paperops_30_day_operations(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paperops_30_day_operations_public_status_from_artifact(
        output
    )
    return output, entry


def write_paperops_30_day_operations(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = paperops_30_day_operations_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_paperops_30_day_operations_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paperops_30_day_operations(output)
        output["public_status"] = paperops_30_day_operations_public_status_from_artifact(
            output
        )
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paperops_30_day_operations(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paperops_30_day_operations_public_status_from_artifact(
        output
    )
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_30_DAY_OPERATIONS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "run_id": output.get("run_id"),
        "run_state": output.get("run_state"),
        "active_day_number": output.get("active_day_number"),
        "completed_calendar_day_count": output.get("completed_calendar_day_count"),
        "calendar_days_remaining": output.get("calendar_days_remaining"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "scheduler_status": output.get("scheduler_status"),
        "paper_operational_cycle_status": output.get("paper_operational_cycle_status"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
