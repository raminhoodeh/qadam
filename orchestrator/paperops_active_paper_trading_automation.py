"""PT-8 active PaperOps paper-trading automation controller.

PT-8 binds the recurring PaperOps runner to the guarded paper broker path. It
does not create a new broker shortcut. The controller may delegate to
PaperOps-2, PaperOps-3, or PaperOps-4 only after the existing paper-only gates
are already recorded and clean.
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
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import (
    build_paperops_alpaca_paper_post,
    validate_paperops_alpaca_paper_post,
)
from orchestrator.paperops_guarded_paper_exit_enablement import (
    validate_paperops_guarded_paper_exit_enablement,
)
from orchestrator.paperops_paper_exit_path import validate_paperops_paper_exit_path
from orchestrator.paperops_paper_lifecycle_poller import (
    validate_paperops_paper_lifecycle_poller,
)
from orchestrator.paperops_paper_lifecycle_polling_enablement import (
    validate_paperops_paper_lifecycle_polling_enablement,
)
from orchestrator.paperops_submit_regression_guard import (
    build_paperops_submit_regression_guard,
    validate_paperops_submit_regression_guard,
)


PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION = 1
PAPEROPS_ACTIVE_AUTOMATION_RUNTIME_ARTIFACT = (
    "paperops_active_paper_trading_automation.json"
)
PAPEROPS_ACTIVE_AUTOMATION_HISTORY = (
    "paperops_active_paper_trading_automation_history.jsonl"
)
PAPEROPS_ACTIVE_AUTOMATION_EVENT_LOG = (
    "paperops_active_paper_trading_automation_events.jsonl"
)
PAPEROPS_ACTIVE_AUTOMATION_EVENT_TYPE = (
    "paperops_active_paper_trading_automation_recorded"
)
PAPEROPS_ACTIVE_AUTOMATION_COMPONENT = "paperops_active_paper_trading_automation"

PAPEROPS_30_DAY_AUTOMATION_ID = "qadam-phase-7-demo-proof-runner"
PAPEROPS_30_DAY_AUTOMATION_NAME = "Qadam PaperOps Autonomous Runner"

AUTONOMOUS_PASS_COMMAND_FRAGMENT = "scripts/run_paperops_autonomous_pass.py"
ACTIVE_RUNNER_COMMAND_FRAGMENT = (
    "scripts/run_active_paper_trading_automation.py --execute-paper-automation"
)
ACTIVE_CHECK_COMMAND_FRAGMENT = "scripts/check_paperops_active_paper_trading_automation.py"
TELEGRAM_INBOUND_INTAKE_COMMAND_FRAGMENT = "scripts/poll_telegram_inbound_intake.py"
RS5_DAILY_TARGET_POLICY = "minimum_not_ceiling"
RS5_OPPORTUNITY_SCAN_INTERVAL_MINUTES = 20
RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN = 3
RS5_GUARDED_SUBMIT_REQUIREMENTS: tuple[str, ...] = (
    "distinct_research_goal",
    "distinct_candidate",
    "distinct_idempotency_key",
    "passing_risk_budget",
    "no_duplicate_exposure_conflict",
    "no_daily_drawdown_breach",
    "no_source_quorum_breach",
    "no_live_capital_route",
)

REQUIRED_AUTOMATION_COMMAND_FRAGMENTS: tuple[str, ...] = (
    AUTONOMOUS_PASS_COMMAND_FRAGMENT,
)

REQUIRED_AUTOMATION_GUARDRAIL_FRAGMENTS: tuple[str, ...] = (
    "only submit to Alpaca paper",
    "respect the Q-CTRL paper consultation hold",
    "do not force trades",
    "do not edit secrets or .env files",
    "do not enable live capital",
    "do not call broker live endpoints",
    "do not grant proof credit",
    "Telegram inbound intake is read-only",
)

PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES = frozenset(
    {
        "active_automation_enabled_idle",
        "active_automation_enabled_qctrl_hold",
        "active_automation_ready_to_submit",
        "active_automation_ready_to_poll",
        "active_automation_ready_to_exit",
    }
)

PAPEROPS_ACTIVE_AUTOMATION_BOUNDARY = (
    "PT-8 binds the hourly PaperOps automation to active Alpaca paper trading. "
    "It may delegate the explicit submit, poll, and exit flags only to "
    "PaperOps-2, PaperOps-3, and PaperOps-4 after their recorded gates pass. "
    "It must respect the Q-CTRL paper consultation hold when quantum paper "
    "parity is required, must only submit to Alpaca paper, cannot edit .env or "
    "secrets, cannot force trades, cannot use live credentials, cannot call "
    "broker live endpoints, cannot grant proof credit, cannot let "
    "Q-CTRL execute orders, and cannot enable live capital. Telegram inbound "
    "intake is read-only member research intake; it can add world-event "
    "datapoints and strategy considerations, but it cannot create commands or "
    "trade authority."
)

PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_written",
    "event_log_event_count",
    "mode",
    "active_paper_trading_automation_enabled",
    "active_paper_trading_automation_effective",
    "automation_id",
    "automation_name",
    "automation_status",
    "automation_rrule",
    "automation_kind",
    "automation_active",
    "automation_hourly",
    "automation_cwd_bound",
    "automation_prompt_active_trade_bound",
    "automation_prompt_digest",
    "automation_required_command_count",
    "automation_present_command_count",
    "automation_missing_commands",
    "automation_required_guardrail_count",
    "automation_present_guardrail_count",
    "automation_missing_guardrails",
    "execute_automation_requested",
    "active_runner_command",
    "check_command",
    "paper_mode_confirmed",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "paper_endpoint_confirmed",
    "qctrl_paper_parity_required",
    "qctrl_paper_consultation_ready",
    "qctrl_consultation_hold_active",
    "paperops_readiness_status",
    "paperops_safe_to_continue",
    "paperops_full_ready",
    "paperops_blockers",
    "paperops_blocker_count",
    "paperops2_status",
    "paperops2_path_available",
    "paperops2_eligible_submit_record_count",
    "paperops2_fresh_eligible_submit_record_count",
    "paperops2_duplicate_submit_record_count",
    "paperops2_duplicate_submit_interpretation",
    "paperops2_idempotency_ledger_active",
    "paperops_submit_regression_guard_status",
    "paperops_submit_regression_guard_blocker_count",
    "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
    "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
    "paperops_submit_regression_guard_source_stale_after_post_count",
    "paperops_submit_regression_guard_validation_error_count",
    "first_week_paper_trade_mandate_status",
    "first_week_paper_trade_mandate_active",
    "first_week_paper_trade_mandate_day_number",
    "first_week_paper_trade_mandate_daily_target_trade_count",
    "first_week_paper_trade_mandate_minimum_notional_usd",
    "first_week_paper_trade_mandate_daily_ready_submit_count",
    "first_week_paper_trade_mandate_daily_submitted_count",
    "first_week_paper_trade_mandate_candidate_count",
    "rs5_guarded_paper_autonomy_status",
    "rs5_daily_target_policy",
    "rs5_daily_target_is_minimum",
    "rs5_daily_target_blocks_additional_qualified_setups",
    "rs5_opportunity_scan_interval_minutes",
    "rs5_guarded_submit_route",
    "rs5_guarded_submit_transport",
    "rs5_max_guarded_submit_attempts_per_run",
    "rs5_guarded_submit_attempt_cap_per_run",
    "rs5_guarded_submit_requirement_count",
    "rs5_guarded_submit_requirements",
    "rs5_guarded_submit_requirement_records",
    "rs5_guarded_submit_requirements_passed_count",
    "rs5_guarded_submit_missing_requirements",
    "rs5_daily_target_met",
    "rs5_additional_distinct_setup_available",
    "rs5_available_distinct_setup_count",
    "rs5_distinct_candidate_count",
    "rs5_distinct_research_goal_count",
    "rs5_distinct_idempotency_key_count",
    "rs5_duplicate_submit_record_count",
    "rs5_can_submit_multiple_today",
    "rs5_multiple_submission_guard_status",
    "why_not_trading_now",
    "why_not_trading_now_reasons",
    "paperops2_submit_called_count",
    "paperops2_submit_succeeded_count",
    "paperops3_status",
    "paperops3_source_submitted_order_count",
    "paperops3_poll_candidate_count",
    "paperops3_order_poll_called_count",
    "paperops3_open_position_count",
    "paperops4_status",
    "paperops4_exit_path_available",
    "paperops4_eligible_exit_record_count",
    "paperops4_close_called_count",
    "pt6_lifecycle_polling_ready",
    "pt7_guarded_exit_ready",
    "unattended_paper_execution_delegation_enabled",
    "unattended_paper_execution_delegation_reason",
    "idle_reason",
    "idempotency_guard_message",
    "paper_submit_step_allowed",
    "paper_poll_step_allowed",
    "paper_exit_step_allowed",
    "submit_hold_reason",
    "poll_hold_reason",
    "exit_hold_reason",
    "delegated_submit_allowed",
    "delegated_poll_allowed",
    "delegated_exit_allowed",
    "direct_broker_shortcut_allowed",
    "paper_order_submission_allowed_without_paperops2",
    "qctrl_direct_execution_allowed",
    "qctrl_broker_post_allowed",
    "forced_trades_allowed",
    "phase7_proof_credit_allowed",
    "env_file_edited",
    "secret_value_exposed",
    "raw_payload_exposed",
    "broker_order_identifier_exposed",
    "live_endpoint_called_count",
    "unsafe_write_counter_total",
    "action_records",
    "action_record_count",
    "blockers",
    "blocker_count",
    "next_required_action",
    "boundary",
    "validation_error_count",
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


def paperops_active_paper_trading_automation_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_ACTIVE_AUTOMATION_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_ACTIVE_AUTOMATION_HISTORY,
        runtime / PAPEROPS_ACTIVE_AUTOMATION_EVENT_LOG,
    )


def read_latest_paperops_active_paper_trading_automation(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_active_paper_trading_automation_paths(settings)
    return _read_json(output_path)


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
    status = str(automation.get("status") or "missing")
    kind = str(automation.get("kind") or "missing")
    rrule = str(automation.get("rrule") or "")
    return {
        "automation_id": str(automation.get("id") or PAPEROPS_30_DAY_AUTOMATION_ID),
        "automation_name": str(automation.get("name") or PAPEROPS_30_DAY_AUTOMATION_NAME),
        "automation_status": status,
        "automation_rrule": rrule,
        "automation_kind": kind,
        "automation_active": status == "ACTIVE" and kind == "cron",
        "automation_hourly": rrule == "FREQ=HOURLY;INTERVAL=1",
        "automation_cwd_bound": repo_root in [str(item) for item in cwds],
        "automation_prompt_active_trade_bound": not missing_commands
        and not missing_guardrails,
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
    paperops2 = build_paperops_alpaca_paper_post(
        settings=settings,
        execute_post=False,
    )
    return {
        "readiness": _read_json(runtime / "paper_operational_readiness.json"),
        "paper_live_qctrl_product_access": _read_json(
            runtime / "paper_live_qctrl_product_access.json"
        ),
        "qctrl_consultation": _read_json(
            runtime / "paperops_qctrl_paper_consultation.json"
        ),
        "paperops2": paperops2,
        "submit_regression_guard": build_paperops_submit_regression_guard(
            settings=settings,
            paperops2=paperops2,
        ),
        "paperops3": _read_json(runtime / "paperops_paper_lifecycle_poller.json"),
        "paperops4": _read_json(runtime / "paperops_paper_exit_path.json"),
        "pt6": _read_json(runtime / "paperops_paper_lifecycle_polling_enablement.json"),
        "pt7": _read_json(runtime / "paperops_guarded_paper_exit_enablement.json"),
        "paperops6": _read_json(runtime / "paperops_30_day_operations.json"),
    }


def _qctrl_ready(settings: Settings, snapshot: dict[str, dict[str, Any]]) -> bool:
    if not settings.quantum_paper_parity_required:
        return True
    product_access = snapshot["paper_live_qctrl_product_access"]
    qctrl_consultation = snapshot["qctrl_consultation"]
    return (
        product_access.get("status") == "qctrl_paper_consultation_ready"
        and product_access.get("paper_consultation_ready") is True
        and qctrl_consultation.get("status") == "consultation_recorded"
        and qctrl_consultation.get("provider_call_recorded") is True
        and _int(qctrl_consultation.get("provider_call_count")) >= 1
        and qctrl_consultation.get("execution_allowed") is False
        and qctrl_consultation.get("paper_order_allowed") is False
        and qctrl_consultation.get("broker_post_allowed") is False
    )


def _pt6_ready(pt6: dict[str, Any]) -> bool:
    return (
        pt6.get("status")
        in {
            "enabled_pending_submitted_paper_orders",
            "enabled_pending_explicit_poll",
        }
        and pt6.get("active_lifecycle_polling_enabled") is True
        and pt6.get("paper_lifecycle_polling_effective") is True
        and pt6.get("paper_endpoint_confirmed") is True
        and pt6.get("live_capital_enabled") is False
        and _int(pt6.get("broker_get_called_count")) == 0
        and _int(pt6.get("live_endpoint_called_count")) == 0
        and not validate_paperops_paper_lifecycle_polling_enablement(pt6)
    )


def _pt7_ready(pt7: dict[str, Any]) -> bool:
    return (
        pt7.get("status")
        in {
            "enabled_pending_open_position_readback",
            "enabled_pending_explicit_exit",
        }
        and pt7.get("guarded_paper_exit_enabled") is True
        and pt7.get("alpaca_paper_exit_effective") is True
        and pt7.get("paper_endpoint_confirmed") is True
        and pt7.get("live_capital_enabled") is False
        and _int(pt7.get("paper_position_close_called_count")) == 0
        and _int(pt7.get("live_endpoint_called_count")) == 0
        and not validate_paperops_guarded_paper_exit_enablement(pt7)
    )


def _paperops2_ready(paperops2: dict[str, Any]) -> bool:
    return (
        paperops2.get("status") == "ready_pending_explicit_execute"
        and paperops2.get("paper_post_path_available") is True
        and paperops2.get("paper_endpoint_confirmed") is True
        and _int(paperops2.get("fresh_eligible_submit_record_count")) >= 1
        and _int(paperops2.get("live_endpoint_called_count")) == 0
        and paperops2.get("live_capital_enabled") is False
        and not validate_paperops_alpaca_paper_post(paperops2)
    )


def _paperops3_poll_ready(paperops3: dict[str, Any], pt6_ready: bool) -> bool:
    return (
        pt6_ready
        and paperops3.get("status") == "ready_pending_explicit_poll"
        and _int(paperops3.get("source_submitted_paper_order_count")) >= 1
        and paperops3.get("paper_poll_path_available") is True
        and paperops3.get("paper_endpoint_confirmed") is True
        and paperops3.get("live_capital_enabled") is False
        and _int(paperops3.get("live_endpoint_called_count")) == 0
        and _int(paperops3.get("broker_post_called_count")) == 0
        and not validate_paperops_paper_lifecycle_poller(paperops3)
    )


def _paperops4_exit_ready(paperops4: dict[str, Any], pt7_ready: bool) -> bool:
    return (
        pt7_ready
        and paperops4.get("status") == "ready_pending_explicit_execute"
        and paperops4.get("paper_exit_path_available") is True
        and _int(paperops4.get("eligible_exit_record_count")) >= 1
        and paperops4.get("paper_endpoint_confirmed") is True
        and paperops4.get("live_capital_enabled") is False
        and _int(paperops4.get("live_endpoint_called_count")) == 0
        and _int(paperops4.get("broker_post_called_count")) == 0
        and not validate_paperops_paper_exit_path(paperops4)
    )


def _hold_reason(allowed: bool, failures: list[str], idle_reason: str) -> str:
    if allowed:
        return "allowed"
    if failures:
        return ",".join(failures)
    return idle_reason


def _exit_hold_reason(
    *,
    allowed: bool,
    failures: list[str],
    paperops4: dict[str, Any],
) -> str:
    if allowed:
        return "allowed"
    if failures:
        return ",".join(failures)
    if (
        paperops4.get("status") == "paper_exit_close_failed_sanitized"
        and _int(paperops4.get("paper_position_close_failed_count")) >= 1
    ):
        return "paper_exit_close_failed_sanitized_waiting_retry_or_lifecycle_refresh"
    if paperops4.get("status") == "blocked_paper_position_preflight_readback_failed":
        return "paper_position_preflight_readback_failed_waiting_lifecycle_refresh"
    if paperops4.get("status") == "ready_pending_lifecycle_mirror_refresh":
        return "paper_lifecycle_mirror_refresh_required_after_close"
    if _int(paperops4.get("suppressed_pending_close_request_exit_candidate_count")) >= 1:
        return "paper_exit_close_request_pending_waiting_lifecycle_refresh"
    if (
        paperops4.get("status") == "paper_exit_close_recorded"
        and _int(paperops4.get("paper_position_close_called_count")) >= 1
    ):
        return "paper_exit_already_recorded_waiting_lifecycle_refresh"
    if (
        paperops4.get("paper_exit_path_available") is True
        and _int(paperops4.get("eligible_exit_record_count")) >= 1
    ):
        return "paper_exit_candidate_available_pending_explicit_execute"
    return "no_open_position_exit_candidate"


def _post_candidates(paperops2: dict[str, Any]) -> list[dict[str, Any]]:
    records = paperops2.get("post_candidates", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _fresh_post_candidates(paperops2: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in _post_candidates(paperops2)
        if record.get("eligible_for_paper_post") is True
        and record.get("fresh_for_paper_post", True) is not False
        and record.get("previously_submitted_to_alpaca_paper") is not True
        and record.get("status") != "blocked_duplicate_paper_submit"
    ]


def _unique_count(records: list[dict[str, Any]], *keys: str) -> int:
    values: set[str] = set()
    for record in records:
        for key in keys:
            value = str(record.get(key) or "").strip()
            if value:
                values.add(value)
                break
    return len(values)


def _rs5_requirement_records(
    *,
    settings: Settings,
    paperops2: dict[str, Any],
    paperops2_ready: bool,
    qctrl_hold: bool,
    blockers: list[str],
    fresh_count: int,
    distinct_candidate_count: int,
    distinct_research_goal_count: int,
    distinct_idempotency_key_count: int,
) -> list[dict[str, Any]]:
    upstream_gate_passed = paperops2_ready and not blockers and not qctrl_hold
    return [
        {
            "key": "distinct_research_goal",
            "passed": distinct_research_goal_count >= fresh_count and fresh_count > 0,
            "detail": "Fresh eligible records must not collapse into one research-goal lineage.",
        },
        {
            "key": "distinct_candidate",
            "passed": distinct_candidate_count >= fresh_count and fresh_count > 0,
            "detail": "Fresh eligible records must have distinct candidate/setup identity.",
        },
        {
            "key": "distinct_idempotency_key",
            "passed": distinct_idempotency_key_count >= fresh_count and fresh_count > 0,
            "detail": "Fresh eligible records must have distinct paper-submit idempotency keys.",
        },
        {
            "key": "passing_risk_budget",
            "passed": upstream_gate_passed,
            "detail": "Risk budget remains enforced upstream by the PaperOps-2 candidate contract.",
        },
        {
            "key": "no_duplicate_exposure_conflict",
            "passed": upstream_gate_passed,
            "detail": "Duplicate exposure remains enforced upstream by PaperOps staging and idempotency.",
        },
        {
            "key": "no_daily_drawdown_breach",
            "passed": upstream_gate_passed,
            "detail": "Drawdown and paper-account limits remain upstream gates before PaperOps-2 eligibility.",
        },
        {
            "key": "no_source_quorum_breach",
            "passed": upstream_gate_passed,
            "detail": "Source quorum remains enforced before candidate eligibility.",
        },
        {
            "key": "no_live_capital_route",
            "passed": settings.live_capital_enabled is False
            and paperops2.get("live_capital_enabled") is False
            and paperops2.get("live_endpoint_allowed") is False,
            "detail": "RS-5 can only use the Alpaca paper route; live capital remains unavailable.",
        },
    ]


def _why_not_trading_now(
    *,
    paper_submit_allowed: bool,
    paper_poll_allowed: bool,
    paper_exit_allowed: bool,
    blockers: list[str],
    qctrl_hold: bool,
    paperops2_ready: bool,
    fresh_count: int,
    duplicate_count: int,
    first_week_mandate_target_met: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if paper_submit_allowed:
        return "fresh_guarded_paper_submit_ready", []
    if blockers:
        reasons.extend(blockers)
    if qctrl_hold:
        reasons.append("qctrl_paper_consultation_hold")
    if not paperops2_ready:
        if fresh_count < 1 and first_week_mandate_target_met:
            reasons.append("daily_target_met_and_no_additional_distinct_setup")
        elif fresh_count < 1 and duplicate_count >= 1:
            reasons.append("idempotency_guard_holding_duplicate_or_already_submitted_setup")
        elif fresh_count < 1:
            reasons.append("no_fresh_qualified_setup")
        else:
            reasons.append("paperops2_submit_gate_not_ready")
    if paper_poll_allowed:
        reasons.append("paper_lifecycle_poll_ready_before_new_submit")
    if paper_exit_allowed:
        reasons.append("paper_exit_ready_before_new_submit")
    unique_reasons = list(dict.fromkeys(reasons))
    if not unique_reasons:
        unique_reasons.append("waiting_for_fresh_qualified_setup")
    return ",".join(unique_reasons), unique_reasons


def _status(
    *,
    hard_blockers: list[str],
    qctrl_hold: bool,
    submit_allowed: bool,
    poll_allowed: bool,
    exit_allowed: bool,
) -> str:
    if hard_blockers:
        return "blocked_active_automation_safety_or_binding"
    if qctrl_hold:
        return "active_automation_enabled_qctrl_hold"
    if submit_allowed:
        return "active_automation_ready_to_submit"
    if poll_allowed:
        return "active_automation_ready_to_poll"
    if exit_allowed:
        return "active_automation_ready_to_exit"
    return "active_automation_enabled_idle"


def _blockers(
    *,
    settings: Settings,
    automation: dict[str, Any],
    snapshot: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    readiness = snapshot["readiness"]
    if settings.mode != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled:
        blockers.append("live_capital_enabled")
    if automation.get("automation_active") is not True:
        blockers.append("automation_not_active")
    if automation.get("automation_hourly") is not True:
        blockers.append("automation_not_hourly")
    if automation.get("automation_cwd_bound") is not True:
        blockers.append("automation_not_bound_to_qadam_workspace")
    if automation.get("automation_prompt_active_trade_bound") is not True:
        blockers.append("automation_prompt_not_active_trade_bound")
    if readiness.get("safe_to_continue_paper_only") is not True:
        blockers.append("paperops_not_safe_to_continue")
    return sorted(set(blockers))


def build_paperops_active_paper_trading_automation(
    settings: Settings | None = None,
    *,
    execute_automation_requested: bool = False,
    action_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    automation = _automation_status(_automation_config(), settings)
    readiness = snapshot["readiness"]
    paperops2 = snapshot["paperops2"]
    submit_regression_guard = snapshot["submit_regression_guard"]
    paperops3 = snapshot["paperops3"]
    paperops4 = snapshot["paperops4"]
    pt6 = snapshot["pt6"]
    pt7 = snapshot["pt7"]

    blockers = _blockers(settings=settings, automation=automation, snapshot=snapshot)
    qctrl_ready = _qctrl_ready(settings, snapshot)
    qctrl_hold = settings.quantum_paper_parity_required and not qctrl_ready
    pt6_ready = _pt6_ready(pt6)
    pt7_ready = _pt7_ready(pt7)
    submit_regression_guard_errors = validate_paperops_submit_regression_guard(
        submit_regression_guard
    )
    submit_regression_guard_ready = (
        submit_regression_guard.get("status") == "ready_fresh_submit_consistent"
        and _int(submit_regression_guard.get("blocker_count")) == 0
        and not submit_regression_guard_errors
    )
    submit_regression_guard_safe_idle = (
        submit_regression_guard.get("status")
        in {
            "healthy_idle_idempotency_guarded",
            "healthy_idle_no_fresh_submit",
            "healthy_submitted_idempotency_recorded",
            "ready_fresh_submit_consistent",
        }
        and _int(submit_regression_guard.get("blocker_count")) == 0
        and not submit_regression_guard_errors
    )
    paperops2_ready = _paperops2_ready(paperops2) and submit_regression_guard_ready
    paperops3_ready = _paperops3_poll_ready(paperops3, pt6_ready)
    paperops4_ready = _paperops4_exit_ready(paperops4, pt7_ready)
    first_week_mandate_active = (
        paperops2.get("source_first_week_mandate_active") is True
    )
    first_week_mandate_daily_target = _int(
        paperops2.get("source_first_week_mandate_daily_target_trade_count")
    )
    first_week_mandate_daily_submitted = _int(
        paperops2.get("source_first_week_mandate_daily_submitted_count")
    )
    first_week_mandate_target_met = (
        first_week_mandate_active
        and first_week_mandate_daily_target > 0
        and first_week_mandate_daily_submitted >= first_week_mandate_daily_target
    )
    fresh_submit_record_count = _int(paperops2.get("fresh_eligible_submit_record_count"))
    duplicate_submit_record_count = _int(paperops2.get("duplicate_submit_record_count"))
    fresh_candidate_records = _fresh_post_candidates(paperops2)
    fresh_candidate_record_count = max(
        fresh_submit_record_count,
        len(fresh_candidate_records),
    )
    distinct_candidate_count = max(
        fresh_candidate_record_count if fresh_candidate_record_count and not fresh_candidate_records else 0,
        _unique_count(
            fresh_candidate_records,
            "source_setup_record_id",
            "source_staged_order_artifact_id",
            "source_submit_record_artifact_id",
            "request_fingerprint",
        ),
    )
    distinct_research_goal_count = max(
        fresh_candidate_record_count if fresh_candidate_record_count and not fresh_candidate_records else 0,
        _unique_count(
            fresh_candidate_records,
            "research_goal_id",
            "source_setup_record_id",
            "source_staged_order_artifact_id",
            "source_submit_record_artifact_id",
        ),
    )
    distinct_idempotency_key_count = max(
        fresh_candidate_record_count if fresh_candidate_record_count and not fresh_candidate_records else 0,
        _unique_count(
            fresh_candidate_records,
            "source_idempotency_key",
            "idempotency_key",
            "request_fingerprint",
        ),
    )

    submit_failures: list[str] = []
    if blockers:
        submit_failures.extend(blockers)
    if qctrl_hold:
        submit_failures.append("qctrl_paper_consultation_hold")
    if not paperops2_ready:
        submit_failures.append("paperops2_submit_gate_not_ready")
    if not submit_regression_guard_safe_idle:
        submit_failures.append("paperops_submit_regression_guard_not_ready")
    paper_submit_allowed = not submit_failures
    paper_poll_allowed = not blockers and paperops3_ready
    paper_exit_allowed = not blockers and paperops4_ready
    unattended_delegation_enabled = (
        not blockers
        and settings.mode == "paper"
        and settings.live_capital_enabled is False
        and automation.get("automation_active") is True
        and automation.get("automation_prompt_active_trade_bound") is True
        and readiness.get("safe_to_continue_paper_only") is True
        and qctrl_ready
    )
    if not unattended_delegation_enabled:
        unattended_delegation_reason = "blocked:" + ",".join(
            blockers or ["paperops_or_qctrl_not_ready"]
        )
        idle_reason = None
    elif paper_submit_allowed:
        unattended_delegation_reason = "armed_fresh_paper_submit_ready"
        idle_reason = None
    elif paper_poll_allowed:
        unattended_delegation_reason = "armed_paper_poll_ready"
        idle_reason = None
    elif paper_exit_allowed:
        unattended_delegation_reason = "armed_paper_exit_ready"
        idle_reason = None
    elif first_week_mandate_target_met:
        unattended_delegation_reason = "armed_idle_first_week_paper_target_met"
        idle_reason = "daily_paper_trade_target_met"
    elif _int(paperops2.get("duplicate_submit_record_count")) >= 1:
        unattended_delegation_reason = "armed_idle_existing_order_already_submitted"
        idle_reason = "no_fresh_eligible_candidate"
    else:
        unattended_delegation_reason = "armed_idle_waiting_for_fresh_eligible_setup"
        idle_reason = "no_fresh_eligible_candidate"
    why_not_trading_now, why_not_trading_now_reasons = _why_not_trading_now(
        paper_submit_allowed=paper_submit_allowed,
        paper_poll_allowed=paper_poll_allowed,
        paper_exit_allowed=paper_exit_allowed,
        blockers=blockers,
        qctrl_hold=qctrl_hold,
        paperops2_ready=paperops2_ready,
        fresh_count=fresh_candidate_record_count,
        duplicate_count=duplicate_submit_record_count,
        first_week_mandate_target_met=first_week_mandate_target_met,
    )
    rs5_requirement_records = _rs5_requirement_records(
        settings=settings,
        paperops2=paperops2,
        paperops2_ready=paperops2_ready,
        qctrl_hold=qctrl_hold,
        blockers=blockers,
        fresh_count=fresh_candidate_record_count,
        distinct_candidate_count=distinct_candidate_count,
        distinct_research_goal_count=distinct_research_goal_count,
        distinct_idempotency_key_count=distinct_idempotency_key_count,
    )
    rs5_missing_requirements = [
        str(record["key"])
        for record in rs5_requirement_records
        if record.get("passed") is not True
    ]
    rs5_max_submit_attempts = min(
        RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN,
        max(0, fresh_candidate_record_count),
    )
    rs5_guard_status = (
        "ready_for_guarded_paper_submit"
        if paper_submit_allowed
        else (
            "idle_no_fresh_distinct_setup"
            if fresh_candidate_record_count < 1 and not blockers and not qctrl_hold
            else "blocked_by_guardrail_or_gate"
        )
    )
    duplicate_submit_interpretation = (
        "idempotency guard active: existing paper submit already recorded"
        if duplicate_submit_record_count >= 1
        else "no duplicate paper submit recorded"
    )

    actions = action_records or []
    live_endpoint_called_count = sum(
        _int(record.get("live_endpoint_called_count"))
        for record in actions
        if isinstance(record, dict)
    )
    unsafe_write_counter_total = live_endpoint_called_count
    status = _status(
        hard_blockers=blockers,
        qctrl_hold=qctrl_hold and paperops2_ready,
        submit_allowed=paper_submit_allowed,
        poll_allowed=paper_poll_allowed,
        exit_allowed=paper_exit_allowed,
    )
    enabled = status in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES
    artifact = {
        "schema_version": PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION,
        "artifact_type": "paperops_active_paper_trading_automation",
        "artifact_id": "paperops:pt-8:active-paper-trading-automation",
        "phase": "PaperOps",
        "stage": "PT-8",
        "status": status,
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
        "active_paper_trading_automation_enabled": enabled,
        "active_paper_trading_automation_effective": enabled,
        **automation,
        "execute_automation_requested": execute_automation_requested,
        "active_runner_command": ACTIVE_RUNNER_COMMAND_FRAGMENT,
        "check_command": ACTIVE_CHECK_COMMAND_FRAGMENT,
        "paper_mode_confirmed": settings.mode == "paper",
        "live_capital_enabled": settings.live_capital_enabled,
        "live_endpoint_allowed": False,
        "paper_endpoint_confirmed": paperops2.get("paper_endpoint_confirmed") is True,
        "qctrl_paper_parity_required": settings.quantum_paper_parity_required,
        "qctrl_paper_consultation_ready": qctrl_ready,
        "qctrl_consultation_hold_active": qctrl_hold,
        "paperops_readiness_status": readiness.get("status", "missing"),
        "paperops_safe_to_continue": readiness.get("safe_to_continue_paper_only")
        is True,
        "paperops_full_ready": readiness.get("full_paper_operational_ready") is True,
        "paperops_blockers": readiness.get("blockers", []) or [],
        "paperops_blocker_count": _int(readiness.get("blocker_count")),
        "paperops2_status": paperops2.get("status", "missing"),
        "paperops2_path_available": paperops2.get("paper_post_path_available") is True,
        "paperops2_eligible_submit_record_count": _int(
            paperops2.get("eligible_submit_record_count")
        ),
        "paperops2_fresh_eligible_submit_record_count": _int(
            paperops2.get("fresh_eligible_submit_record_count")
        ),
        "paperops2_duplicate_submit_record_count": _int(
            paperops2.get("duplicate_submit_record_count")
        ),
        "paperops2_duplicate_submit_interpretation": duplicate_submit_interpretation,
        "paperops2_idempotency_ledger_active": (
            paperops2.get("idempotency_ledger_active") is True
        ),
        "paperops_submit_regression_guard_status": submit_regression_guard.get(
            "status",
            "missing",
        ),
        "paperops_submit_regression_guard_blocker_count": _int(
            submit_regression_guard.get("blocker_count")
        ),
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count": _int(
            submit_regression_guard.get("fresh_submitted_ledger_collision_count")
        ),
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count": _int(
            submit_regression_guard.get("duplicate_misclassified_as_fresh_count")
        ),
        "paperops_submit_regression_guard_source_stale_after_post_count": _int(
            submit_regression_guard.get("source_stale_after_post_tolerance_count")
        ),
        "paperops_submit_regression_guard_validation_error_count": len(
            submit_regression_guard_errors
        ),
        "first_week_paper_trade_mandate_status": paperops2.get(
            "source_first_week_mandate_status",
            "not_run",
        ),
        "first_week_paper_trade_mandate_active": first_week_mandate_active,
        "first_week_paper_trade_mandate_day_number": _int(
            paperops2.get("source_first_week_mandate_day_number")
        ),
        "first_week_paper_trade_mandate_daily_target_trade_count": (
            first_week_mandate_daily_target
        ),
        "first_week_paper_trade_mandate_minimum_notional_usd": float(
            paperops2.get("source_first_week_mandate_minimum_notional_usd") or 0
        ),
        "first_week_paper_trade_mandate_daily_ready_submit_count": _int(
            paperops2.get("source_first_week_mandate_daily_ready_submit_count")
        ),
        "first_week_paper_trade_mandate_daily_submitted_count": (
            first_week_mandate_daily_submitted
        ),
        "first_week_paper_trade_mandate_candidate_count": _int(
            paperops2.get("source_first_week_mandate_candidate_count")
        ),
        "rs5_guarded_paper_autonomy_status": "guarded_paper_autonomy_contract_active",
        "rs5_daily_target_policy": RS5_DAILY_TARGET_POLICY,
        "rs5_daily_target_is_minimum": True,
        "rs5_daily_target_blocks_additional_qualified_setups": False,
        "rs5_opportunity_scan_interval_minutes": RS5_OPPORTUNITY_SCAN_INTERVAL_MINUTES,
        "rs5_guarded_submit_route": ACTIVE_RUNNER_COMMAND_FRAGMENT,
        "rs5_guarded_submit_transport": "paperops2_only",
        "rs5_max_guarded_submit_attempts_per_run": rs5_max_submit_attempts,
        "rs5_guarded_submit_attempt_cap_per_run": RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN,
        "rs5_guarded_submit_requirement_count": len(RS5_GUARDED_SUBMIT_REQUIREMENTS),
        "rs5_guarded_submit_requirements": list(RS5_GUARDED_SUBMIT_REQUIREMENTS),
        "rs5_guarded_submit_requirement_records": rs5_requirement_records,
        "rs5_guarded_submit_requirements_passed_count": len(RS5_GUARDED_SUBMIT_REQUIREMENTS)
        - len(rs5_missing_requirements),
        "rs5_guarded_submit_missing_requirements": rs5_missing_requirements,
        "rs5_daily_target_met": first_week_mandate_target_met,
        "rs5_additional_distinct_setup_available": fresh_candidate_record_count > 0,
        "rs5_available_distinct_setup_count": fresh_candidate_record_count,
        "rs5_distinct_candidate_count": distinct_candidate_count,
        "rs5_distinct_research_goal_count": distinct_research_goal_count,
        "rs5_distinct_idempotency_key_count": distinct_idempotency_key_count,
        "rs5_duplicate_submit_record_count": duplicate_submit_record_count,
        "rs5_can_submit_multiple_today": (
            unattended_delegation_enabled
            and paper_submit_allowed
            and rs5_max_submit_attempts >= 1
        ),
        "rs5_multiple_submission_guard_status": rs5_guard_status,
        "why_not_trading_now": why_not_trading_now,
        "why_not_trading_now_reasons": why_not_trading_now_reasons,
        "paperops2_submit_called_count": _int(
            paperops2.get("alpaca_paper_post_called_count")
        ),
        "paperops2_submit_succeeded_count": _int(
            paperops2.get("alpaca_paper_post_succeeded_count")
        ),
        "paperops3_status": paperops3.get("status", "missing"),
        "paperops3_source_submitted_order_count": _int(
            paperops3.get("source_submitted_paper_order_count")
        ),
        "paperops3_poll_candidate_count": _int(paperops3.get("poll_candidate_count")),
        "paperops3_order_poll_called_count": _int(
            paperops3.get("paper_order_poll_called_count")
        ),
        "paperops3_open_position_count": _int(paperops3.get("open_position_count")),
        "paperops4_status": paperops4.get("status", "missing"),
        "paperops4_exit_path_available": (
            paperops4.get("paper_exit_path_available") is True
        ),
        "paperops4_eligible_exit_record_count": _int(
            paperops4.get("eligible_exit_record_count")
        ),
        "paperops4_close_called_count": _int(
            paperops4.get("paper_position_close_called_count")
        ),
        "pt6_lifecycle_polling_ready": pt6_ready,
        "pt7_guarded_exit_ready": pt7_ready,
        "unattended_paper_execution_delegation_enabled": (
            unattended_delegation_enabled
        ),
        "unattended_paper_execution_delegation_reason": (
            unattended_delegation_reason
        ),
        "idle_reason": idle_reason,
        "idempotency_guard_message": duplicate_submit_interpretation,
        "paper_submit_step_allowed": paper_submit_allowed,
        "paper_poll_step_allowed": paper_poll_allowed,
        "paper_exit_step_allowed": paper_exit_allowed,
        "submit_hold_reason": _hold_reason(
            paper_submit_allowed,
            submit_failures,
            "no_eligible_submit_action",
        ),
        "poll_hold_reason": _hold_reason(
            paper_poll_allowed,
            blockers if blockers else [],
            "no_submitted_order_to_poll",
        ),
        "exit_hold_reason": _exit_hold_reason(
            allowed=paper_exit_allowed,
            failures=blockers if blockers else [],
            paperops4=paperops4,
        ),
        "delegated_submit_allowed": paper_submit_allowed,
        "delegated_poll_allowed": paper_poll_allowed,
        "delegated_exit_allowed": paper_exit_allowed,
        "direct_broker_shortcut_allowed": False,
        "paper_order_submission_allowed_without_paperops2": False,
        "qctrl_direct_execution_allowed": False,
        "qctrl_broker_post_allowed": False,
        "forced_trades_allowed": False,
        "phase7_proof_credit_allowed": False,
        "env_file_edited": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "live_endpoint_called_count": live_endpoint_called_count,
        "unsafe_write_counter_total": unsafe_write_counter_total,
        "action_records": actions,
        "action_record_count": len(actions),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "next_required_action": (
            "Resolve Q-CTRL paper consultation product access before automated paper submit."
            if status == "active_automation_enabled_qctrl_hold"
            else (
                "The active runner may delegate to the next ready PaperOps paper step."
                if status != "active_automation_enabled_idle"
                else "Keep the hourly active runner bound; no paper action is currently eligible."
            )
        ),
        "boundary": PAPEROPS_ACTIVE_AUTOMATION_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paperops_active_paper_trading_automation(
        artifact
    )
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_active_paper_trading_automation(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_FIELDS) - set(artifact))
    if missing:
        errors.append("paperops_active_automation_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION:
        errors.append("paperops_active_automation_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_active_paper_trading_automation":
        errors.append("paperops_active_automation_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-8":
        errors.append("paperops_active_automation_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_active_automation_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_active_automation_mode_not_paper")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_active_automation_live_capital_enabled")
    for key in (
        "live_endpoint_allowed",
        "direct_broker_shortcut_allowed",
        "paper_order_submission_allowed_without_paperops2",
        "qctrl_direct_execution_allowed",
        "qctrl_broker_post_allowed",
        "forced_trades_allowed",
        "phase7_proof_credit_allowed",
        "env_file_edited",
        "secret_value_exposed",
        "raw_payload_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_active_automation_forbidden:{key}")
    for key in ("live_endpoint_called_count", "unsafe_write_counter_total"):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_active_automation_unsafe_counter_nonzero:{key}")
    if (
        artifact.get("automation_active") is not True
        and artifact.get("status") in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES
    ):
        errors.append("paperops_active_automation_scheduler_inactive")
    if artifact.get("automation_hourly") is not True:
        errors.append("paperops_active_automation_scheduler_not_hourly")
    if artifact.get("automation_cwd_bound") is not True:
        errors.append("paperops_active_automation_scheduler_wrong_cwd")
    if artifact.get("automation_prompt_active_trade_bound") is not True:
        errors.append("paperops_active_automation_prompt_not_bound")
    if artifact.get("automation_present_command_count") != artifact.get(
        "automation_required_command_count"
    ):
        errors.append("paperops_active_automation_prompt_command_missing")
    if artifact.get("automation_present_guardrail_count") != artifact.get(
        "automation_required_guardrail_count"
    ):
        errors.append("paperops_active_automation_prompt_guardrail_missing")
    if artifact.get("paper_mode_confirmed") is not True:
        errors.append("paperops_active_automation_paper_mode_not_confirmed")
    if artifact.get("paperops_safe_to_continue") is not True:
        errors.append("paperops_active_automation_paperops_not_safe")
    if artifact.get("paper_endpoint_confirmed") is not True:
        errors.append("paperops_active_automation_paper_endpoint_not_confirmed")
    if artifact.get("unattended_paper_execution_delegation_enabled") is True:
        if artifact.get("qctrl_paper_consultation_ready") is not True:
            errors.append("paperops_active_automation_unattended_without_qctrl")
        if artifact.get("paperops_safe_to_continue") is not True:
            errors.append("paperops_active_automation_unattended_without_readiness")
        if artifact.get("automation_prompt_active_trade_bound") is not True:
            errors.append("paperops_active_automation_unattended_without_prompt")
        if artifact.get("paperops2_idempotency_ledger_active") is not True:
            errors.append("paperops_active_automation_unattended_without_idempotency")
        if _int(artifact.get("paperops_submit_regression_guard_blocker_count")) != 0:
            errors.append("paperops_active_automation_unattended_with_submit_regression")
        if _int(artifact.get("paperops_submit_regression_guard_validation_error_count")) != 0:
            errors.append("paperops_active_automation_unattended_with_submit_guard_invalid")
    if artifact.get("active_paper_trading_automation_enabled") is True:
        if artifact.get("status") not in PAPEROPS_ACTIVE_AUTOMATION_READY_STATUSES:
            errors.append("paperops_active_automation_status_invalid")
        if artifact.get("active_paper_trading_automation_effective") is not True:
            errors.append("paperops_active_automation_effective_false")
    if artifact.get("paper_submit_step_allowed") is True:
        if artifact.get("qctrl_consultation_hold_active") is True:
            errors.append("paperops_active_automation_submit_allowed_under_qctrl_hold")
        if artifact.get("paperops2_status") != "ready_pending_explicit_execute":
            errors.append("paperops_active_automation_submit_without_paperops2_ready")
        if artifact.get("paperops_submit_regression_guard_status") != (
            "ready_fresh_submit_consistent"
        ):
            errors.append("paperops_active_automation_submit_without_submit_guard_ready")
        if _int(artifact.get("paperops2_eligible_submit_record_count")) < 1:
            errors.append("paperops_active_automation_submit_without_eligible_order")
        if _int(artifact.get("paperops2_fresh_eligible_submit_record_count")) < 1:
            errors.append("paperops_active_automation_submit_without_fresh_order")
        if artifact.get("why_not_trading_now") != "fresh_guarded_paper_submit_ready":
            errors.append("paperops_active_automation_submit_why_not_mismatch")
    if artifact.get("paperops_submit_regression_guard_status") not in {
        "healthy_idle_idempotency_guarded",
        "healthy_idle_no_fresh_submit",
        "healthy_submitted_idempotency_recorded",
        "ready_fresh_submit_consistent",
    }:
        errors.append("paperops_active_automation_submit_guard_status_invalid")
    if _int(artifact.get("paperops_submit_regression_guard_blocker_count")) != 0:
        errors.append("paperops_active_automation_submit_guard_blocked")
    if _int(artifact.get("paperops_submit_regression_guard_validation_error_count")) != 0:
        errors.append("paperops_active_automation_submit_guard_validation_errors")
    for key in (
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
        "paperops_submit_regression_guard_source_stale_after_post_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_active_automation_submit_guard_counter_nonzero:{key}")
    if artifact.get("rs5_guarded_paper_autonomy_status") != (
        "guarded_paper_autonomy_contract_active"
    ):
        errors.append("paperops_active_automation_rs5_status_invalid")
    if artifact.get("rs5_daily_target_policy") != RS5_DAILY_TARGET_POLICY:
        errors.append("paperops_active_automation_rs5_daily_target_policy_invalid")
    if artifact.get("rs5_daily_target_is_minimum") is not True:
        errors.append("paperops_active_automation_rs5_daily_target_not_minimum")
    if artifact.get("rs5_daily_target_blocks_additional_qualified_setups") is not False:
        errors.append("paperops_active_automation_rs5_daily_target_ceiling_enabled")
    if _int(artifact.get("rs5_opportunity_scan_interval_minutes")) != (
        RS5_OPPORTUNITY_SCAN_INTERVAL_MINUTES
    ):
        errors.append("paperops_active_automation_rs5_scan_interval_invalid")
    if artifact.get("rs5_guarded_submit_route") != ACTIVE_RUNNER_COMMAND_FRAGMENT:
        errors.append("paperops_active_automation_rs5_route_invalid")
    if artifact.get("rs5_guarded_submit_transport") != "paperops2_only":
        errors.append("paperops_active_automation_rs5_transport_invalid")
    if _int(artifact.get("rs5_guarded_submit_attempt_cap_per_run")) != (
        RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN
    ):
        errors.append("paperops_active_automation_rs5_attempt_cap_invalid")
    max_attempts = _int(artifact.get("rs5_max_guarded_submit_attempts_per_run"))
    if max_attempts < 0 or max_attempts > RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN:
        errors.append("paperops_active_automation_rs5_attempt_count_invalid")
    if artifact.get("rs5_guarded_submit_requirement_count") != len(
        RS5_GUARDED_SUBMIT_REQUIREMENTS
    ):
        errors.append("paperops_active_automation_rs5_requirement_count_invalid")
    if tuple(artifact.get("rs5_guarded_submit_requirements") or ()) != (
        RS5_GUARDED_SUBMIT_REQUIREMENTS
    ):
        errors.append("paperops_active_automation_rs5_requirements_invalid")
    requirement_records = artifact.get("rs5_guarded_submit_requirement_records", [])
    if not isinstance(requirement_records, list):
        errors.append("paperops_active_automation_rs5_requirement_records_invalid")
        requirement_records = []
    requirement_keys = {
        str(record.get("key"))
        for record in requirement_records
        if isinstance(record, dict)
    }
    if requirement_keys != set(RS5_GUARDED_SUBMIT_REQUIREMENTS):
        errors.append("paperops_active_automation_rs5_requirement_record_keys_invalid")
    missing_requirements = [
        str(record.get("key"))
        for record in requirement_records
        if isinstance(record, dict) and record.get("passed") is not True
    ]
    if artifact.get("rs5_guarded_submit_missing_requirements") != missing_requirements:
        errors.append("paperops_active_automation_rs5_missing_requirements_mismatch")
    if _int(artifact.get("rs5_guarded_submit_requirements_passed_count")) != (
        len(RS5_GUARDED_SUBMIT_REQUIREMENTS) - len(missing_requirements)
    ):
        errors.append("paperops_active_automation_rs5_passed_requirements_mismatch")
    if artifact.get("rs5_duplicate_submit_record_count") != artifact.get(
        "paperops2_duplicate_submit_record_count"
    ):
        errors.append("paperops_active_automation_rs5_duplicate_count_mismatch")
    if artifact.get("rs5_available_distinct_setup_count") != artifact.get(
        "paperops2_fresh_eligible_submit_record_count"
    ):
        errors.append("paperops_active_automation_rs5_available_count_mismatch")
    if artifact.get("rs5_additional_distinct_setup_available") != (
        _int(artifact.get("rs5_available_distinct_setup_count")) > 0
    ):
        errors.append("paperops_active_automation_rs5_additional_setup_flag_mismatch")
    if (
        artifact.get("rs5_daily_target_met") is True
        and _int(artifact.get("rs5_available_distinct_setup_count")) > 0
        and artifact.get("idle_reason") == "daily_paper_trade_target_met"
    ):
        errors.append("paperops_active_automation_rs5_target_met_ceiling_detected")
    if (
        artifact.get("rs5_can_submit_multiple_today") is True
        and artifact.get("paper_submit_step_allowed") is not True
    ):
        errors.append("paperops_active_automation_rs5_multi_submit_without_submit_gate")
    if artifact.get("paper_submit_step_allowed") is not True:
        why = str(artifact.get("why_not_trading_now") or "").strip()
        if not why:
            errors.append("paperops_active_automation_why_not_trading_missing")
        if not isinstance(artifact.get("why_not_trading_now_reasons"), list):
            errors.append("paperops_active_automation_why_not_reasons_invalid")
    if artifact.get("first_week_paper_trade_mandate_active") is True:
        if artifact.get("first_week_paper_trade_mandate_daily_target_trade_count") != 3:
            errors.append("paperops_active_automation_first_week_target_invalid")
        if float(artifact.get("first_week_paper_trade_mandate_minimum_notional_usd") or 0) < 6000:
            errors.append("paperops_active_automation_first_week_notional_invalid")
    if artifact.get("paper_poll_step_allowed") is True:
        if artifact.get("paperops3_status") != "ready_pending_explicit_poll":
            errors.append("paperops_active_automation_poll_without_paperops3_ready")
        if _int(artifact.get("paperops3_source_submitted_order_count")) < 1:
            errors.append("paperops_active_automation_poll_without_submitted_order")
        if artifact.get("pt6_lifecycle_polling_ready") is not True:
            errors.append("paperops_active_automation_poll_without_pt6")
    if artifact.get("paper_exit_step_allowed") is True:
        if artifact.get("paperops4_status") != "ready_pending_explicit_execute":
            errors.append("paperops_active_automation_exit_without_paperops4_ready")
        if _int(artifact.get("paperops4_eligible_exit_record_count")) < 1:
            errors.append("paperops_active_automation_exit_without_candidate")
        if artifact.get("pt7_guarded_exit_ready") is not True:
            errors.append("paperops_active_automation_exit_without_pt7")
    if (
        artifact.get("qctrl_paper_parity_required") is True
        and artifact.get("qctrl_paper_consultation_ready") is not True
        and artifact.get("paper_submit_step_allowed") is True
    ):
        errors.append("paperops_active_automation_submit_bypassed_qctrl_parity")
    action_records = artifact.get("action_records", [])
    if not isinstance(action_records, list):
        errors.append("paperops_active_automation_action_records_not_list")
        action_records = []
    if _int(artifact.get("action_record_count")) != len(action_records):
        errors.append("paperops_active_automation_action_count_mismatch")
    for record in action_records:
        if not isinstance(record, dict):
            errors.append("paperops_active_automation_action_record_invalid")
            continue
        if record.get("live_endpoint_called_count") not in {0, None}:
            errors.append("paperops_active_automation_action_live_endpoint_called")
        if record.get("live_capital_enabled") is True:
            errors.append("paperops_active_automation_action_live_capital_enabled")
        if record.get("secret_value_exposed") is True:
            errors.append("paperops_active_automation_action_secret_exposed")
    if artifact.get("validation_error_count") not in {
        None,
        len(artifact.get("validation_errors", [])),
    }:
        errors.append("paperops_active_automation_validation_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-8 binds the hourly PaperOps automation",
        "PaperOps-2, PaperOps-3, and PaperOps-4",
        "Q-CTRL paper consultation hold",
        "only submit to Alpaca paper",
        "cannot edit .env",
        "cannot force trades",
        "cannot call broker live endpoints",
        "cannot grant proof credit",
        "cannot enable live capital",
        "Telegram inbound intake is read-only member research intake",
    ):
        if phrase not in boundary:
            errors.append("paperops_active_automation_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_active_paper_trading_automation(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = (
        paperops_active_paper_trading_automation_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_ACTIVE_AUTOMATION_EVENT_TYPE,
            PAPEROPS_ACTIVE_AUTOMATION_COMPONENT,
            payload={
                "status": written.get("status"),
                "active_paper_trading_automation_enabled": written.get(
                    "active_paper_trading_automation_enabled"
                ),
                "automation_prompt_active_trade_bound": written.get(
                    "automation_prompt_active_trade_bound"
                ),
                "unattended_paper_execution_delegation_enabled": written.get(
                    "unattended_paper_execution_delegation_enabled"
                ),
                "unattended_paper_execution_delegation_reason": written.get(
                    "unattended_paper_execution_delegation_reason"
                ),
                "paper_submit_step_allowed": written.get("paper_submit_step_allowed"),
                "rs5_daily_target_policy": written.get("rs5_daily_target_policy"),
                "rs5_max_guarded_submit_attempts_per_run": written.get(
                    "rs5_max_guarded_submit_attempts_per_run"
                ),
                "rs5_available_distinct_setup_count": written.get(
                    "rs5_available_distinct_setup_count"
                ),
                "rs5_can_submit_multiple_today": written.get(
                    "rs5_can_submit_multiple_today"
                ),
                "why_not_trading_now": written.get("why_not_trading_now"),
                "first_week_paper_trade_mandate_status": written.get(
                    "first_week_paper_trade_mandate_status"
                ),
                "first_week_paper_trade_mandate_daily_ready_submit_count": written.get(
                    "first_week_paper_trade_mandate_daily_ready_submit_count"
                ),
                "first_week_paper_trade_mandate_daily_submitted_count": written.get(
                    "first_week_paper_trade_mandate_daily_submitted_count"
                ),
                "paper_poll_step_allowed": written.get("paper_poll_step_allowed"),
                "paper_exit_step_allowed": written.get("paper_exit_step_allowed"),
                "qctrl_consultation_hold_active": written.get(
                    "qctrl_consultation_hold_active"
                ),
                "execute_automation_requested": written.get(
                    "execute_automation_requested"
                ),
                "live_endpoint_called_count": written.get("live_endpoint_called_count"),
                "unsafe_write_counter_total": written.get(
                    "unsafe_write_counter_total"
                ),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_active_paper_trading_automation(
        written
    )
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "active_paper_trading_automation_enabled": written.get(
            "active_paper_trading_automation_enabled"
        ),
        "unattended_paper_execution_delegation_enabled": written.get(
            "unattended_paper_execution_delegation_enabled"
        ),
        "unattended_paper_execution_delegation_reason": written.get(
            "unattended_paper_execution_delegation_reason"
        ),
        "paper_submit_step_allowed": written.get("paper_submit_step_allowed"),
        "rs5_daily_target_policy": written.get("rs5_daily_target_policy"),
        "rs5_daily_target_is_minimum": written.get("rs5_daily_target_is_minimum"),
        "rs5_max_guarded_submit_attempts_per_run": written.get(
            "rs5_max_guarded_submit_attempts_per_run"
        ),
        "rs5_available_distinct_setup_count": written.get(
            "rs5_available_distinct_setup_count"
        ),
        "rs5_can_submit_multiple_today": written.get("rs5_can_submit_multiple_today"),
        "why_not_trading_now": written.get("why_not_trading_now"),
        "first_week_paper_trade_mandate_status": written.get(
            "first_week_paper_trade_mandate_status"
        ),
        "first_week_paper_trade_mandate_daily_ready_submit_count": written.get(
            "first_week_paper_trade_mandate_daily_ready_submit_count"
        ),
        "first_week_paper_trade_mandate_daily_submitted_count": written.get(
            "first_week_paper_trade_mandate_daily_submitted_count"
        ),
        "paper_poll_step_allowed": written.get("paper_poll_step_allowed"),
        "paper_exit_step_allowed": written.get("paper_exit_step_allowed"),
        "qctrl_consultation_hold_active": written.get(
            "qctrl_consultation_hold_active"
        ),
        "execute_automation_requested": written.get("execute_automation_requested"),
        "action_record_count": written.get("action_record_count"),
        "unsafe_write_counter_total": written.get("unsafe_write_counter_total"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_active_paper_trading_automation_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_active_paper_trading_automation(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_ACTIVE_AUTOMATION_SCHEMA_VERSION,
            "artifact_type": "paperops_active_paper_trading_automation",
            "artifact_id": "paperops:pt-8:active-paper-trading-automation",
            "phase": "PaperOps",
            "stage": "PT-8",
            "status": "not_run",
            "generated_at": None,
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "active_paper_trading_automation_enabled": False,
            "active_paper_trading_automation_effective": False,
            "automation_active": False,
            "automation_prompt_active_trade_bound": False,
            "execute_automation_requested": False,
            "paper_endpoint_confirmed": False,
            "unattended_paper_execution_delegation_enabled": False,
            "unattended_paper_execution_delegation_reason": "pt8_not_run",
            "idle_reason": "pt8_not_run",
            "idempotency_guard_message": "no duplicate paper submit recorded",
            "paperops2_duplicate_submit_interpretation": "no duplicate paper submit recorded",
            "first_week_paper_trade_mandate_status": "not_run",
            "first_week_paper_trade_mandate_active": False,
            "first_week_paper_trade_mandate_day_number": 0,
            "first_week_paper_trade_mandate_daily_target_trade_count": 0,
            "first_week_paper_trade_mandate_minimum_notional_usd": 0,
            "first_week_paper_trade_mandate_daily_ready_submit_count": 0,
            "first_week_paper_trade_mandate_daily_submitted_count": 0,
            "first_week_paper_trade_mandate_candidate_count": 0,
            "rs5_guarded_paper_autonomy_status": "guarded_paper_autonomy_contract_active",
            "rs5_daily_target_policy": RS5_DAILY_TARGET_POLICY,
            "rs5_daily_target_is_minimum": True,
            "rs5_daily_target_blocks_additional_qualified_setups": False,
            "rs5_opportunity_scan_interval_minutes": RS5_OPPORTUNITY_SCAN_INTERVAL_MINUTES,
            "rs5_guarded_submit_route": ACTIVE_RUNNER_COMMAND_FRAGMENT,
            "rs5_guarded_submit_transport": "paperops2_only",
            "rs5_max_guarded_submit_attempts_per_run": 0,
            "rs5_guarded_submit_attempt_cap_per_run": RS5_GUARDED_SUBMIT_ATTEMPT_CAP_PER_RUN,
            "rs5_guarded_submit_requirement_count": len(RS5_GUARDED_SUBMIT_REQUIREMENTS),
            "rs5_guarded_submit_requirements": list(RS5_GUARDED_SUBMIT_REQUIREMENTS),
            "rs5_guarded_submit_requirement_records": [],
            "rs5_guarded_submit_requirements_passed_count": 0,
            "rs5_guarded_submit_missing_requirements": list(RS5_GUARDED_SUBMIT_REQUIREMENTS),
            "rs5_daily_target_met": False,
            "rs5_additional_distinct_setup_available": False,
            "rs5_available_distinct_setup_count": 0,
            "rs5_distinct_candidate_count": 0,
            "rs5_distinct_research_goal_count": 0,
            "rs5_distinct_idempotency_key_count": 0,
            "rs5_duplicate_submit_record_count": 0,
            "rs5_can_submit_multiple_today": False,
            "rs5_multiple_submission_guard_status": "not_run",
            "why_not_trading_now": "pt8_not_run",
            "why_not_trading_now_reasons": ["pt8_not_run"],
            "paper_submit_step_allowed": False,
            "paper_poll_step_allowed": False,
            "paper_exit_step_allowed": False,
            "qctrl_consultation_hold_active": False,
            "direct_broker_shortcut_allowed": False,
            "qctrl_direct_execution_allowed": False,
            "forced_trades_allowed": False,
            "phase7_proof_credit_allowed": False,
            "live_capital_enabled": False,
            "live_endpoint_called_count": 0,
            "unsafe_write_counter_total": 0,
            "blockers": ["pt8_not_run"],
            "blocker_count": 1,
            "validation_error_count": 0,
            "boundary": PAPEROPS_ACTIVE_AUTOMATION_BOUNDARY,
        }
    public = {key: artifact.get(key) for key in PAPEROPS_ACTIVE_AUTOMATION_PUBLIC_FIELDS}
    public["blockers"] = list(public.get("blockers") or [])
    public["paperops_blockers"] = list(public.get("paperops_blockers") or [])
    public["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return public
