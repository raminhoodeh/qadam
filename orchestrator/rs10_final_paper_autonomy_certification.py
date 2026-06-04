"""RS-10 final paper-autonomy certification.

RS-10 certifies the final first-release paper-autonomy posture. It separates
authorization from current actionability: Qadam may be certified to operate the
guarded paper loop while still waiting for a fresh qualified setup, lifecycle
poll, or exit candidate.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry


RS10_FINAL_PAPER_AUTONOMY_SCHEMA_VERSION = 1
RS10_FINAL_PAPER_AUTONOMY_RUNTIME_ARTIFACT = (
    "rs10_final_paper_autonomy_certification.json"
)
RS10_FINAL_PAPER_AUTONOMY_HISTORY = (
    "rs10_final_paper_autonomy_certification_history.jsonl"
)
RS10_FINAL_PAPER_AUTONOMY_EVENT_LOG = (
    "rs10_final_paper_autonomy_certification_events.jsonl"
)
RS10_FINAL_PAPER_AUTONOMY_EVENT_TYPE = (
    "rs10_final_paper_autonomy_certification_recorded"
)
RS10_FINAL_PAPER_AUTONOMY_COMPONENT = "rs10_final_paper_autonomy_certification"

RS10_BOUNDARY = (
    "RS-10 certifies guarded paper autonomy only. It can certify that Qadam is "
    "authorized to run the paper-only PaperOps loop and submit multiple guarded "
    "Alpaca paper trades per day when distinct setups pass all gates, but it "
    "cannot force trades, cannot submit without PaperOps gates, cannot bypass "
    "risk checks, cannot let LLMs or quantum outputs approve trades, cannot give "
    "dashboard or Telegram command authority, cannot use unmanaged broker-write "
    "shortcuts, cannot grant Phase 7 proof credit, and cannot enable live capital."
)

AUTHORITY_FIELDS: tuple[str, ...] = (
    "dashboard_command_authority",
    "telegram_command_authority",
    "local_llm_execution_authority",
    "frontier_llm_execution_authority",
    "quantum_execution_authority",
    "unmanaged_broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
)

UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
    "live_endpoint_called_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "telegram_command_path_enabled_count",
    "unsafe_write_counter_total",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count",
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "rs10_final_paper_autonomy_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "certification_state",
    "final_paper_autonomy_certified",
    "paper_authority_certified",
    "guarded_paper_autonomy_allowed",
    "autonomy_currently_actionable",
    "multiple_paper_trades_per_day_allowed_when_gates_pass",
    "paper_submit_currently_allowed",
    "paper_poll_currently_allowed",
    "paper_exit_currently_allowed",
    "paper_submission_transport",
    "daily_target_policy",
    "daily_target_is_minimum",
    "opportunity_scan_interval_minutes",
    "max_guarded_submit_attempts_per_run",
    "available_distinct_setup_count",
    "can_submit_multiple_today",
    "live_capital_enabled",
    "live_capital_blocked",
    "dashboard_command_authority",
    "telegram_command_authority",
    "local_llm_execution_authority",
    "frontier_llm_execution_authority",
    "quantum_execution_authority",
    "unmanaged_broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "phase7_proof_credit_allowed",
    "paper_account_mirror_status",
    "paper_current_balance_gbp",
    "paper_open_position_count",
    "paper_closed_trade_count",
    "paper_order_count",
    "source_online_count",
    "source_total_count",
    "durable_replay_status",
    "durable_replayed_source_count",
    "research_goal_active_count",
    "market_context_packet_count",
    "local_research_status",
    "strategy_lead_status",
    "signal_integrity_status",
    "risk_agent_status",
    "execution_policy_status",
    "staged_paper_order_status",
    "broker_reconciliation_status",
    "paper_submit_receipt_status",
    "paper_lifecycle_status",
    "operator_inbox_status",
    "rs9_learning_loop_status",
    "rs9_paperops_guarded_paper_trading_not_blocked",
    "qctrl_paper_consultation_ready",
    "paperops_active_status",
    "paperops_active_automation_enabled",
    "paperops_active_automation_effective",
    "paperops_unattended_delegation_enabled",
    "paperops_why_not_trading_now",
    "paper_live_certification_status",
    "paper_live_control_plane_certified",
    "paper_live_certified",
    "paper_live_certification_blocker_count",
    "paper_live_context_blockers",
    "current_blockers",
    "current_blocker_count",
    "safety_blockers",
    "safety_blocker_count",
    "operational_blockers",
    "opportunity_or_risk_blockers",
    "certification_blockers",
    "certification_blocker_count",
    "stale_historical_blocker_count",
    "stale_blocker_in_current_count",
    "allowed_paper_actions",
    "forbidden_actions",
    "rate_limit_policy_present",
    "rate_limit_policy",
    "why_not_trading_now",
    "next_action",
    *UNSAFE_COUNT_FIELDS,
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _repo_root(settings) / ref
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_local_path(value: str) -> bool:
    if value.startswith("/") or value.startswith("~"):
        return True
    return len(value) > 2 and value[1:3] == ":\\"


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in AUTHORITY_FIELDS}


def _unsafe_defaults() -> dict[str, int]:
    return {field: 0 for field in UNSAFE_COUNT_FIELDS}


def rs10_final_paper_autonomy_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / RS10_FINAL_PAPER_AUTONOMY_RUNTIME_ARTIFACT,
        runtime / RS10_FINAL_PAPER_AUTONOMY_HISTORY,
        runtime / RS10_FINAL_PAPER_AUTONOMY_EVENT_LOG,
    )


def _load_source_payload(
    payload: dict[str, Any] | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    if payload is not None:
        return payload
    return _read_json("data/runtime/cockpit-status.json", settings) or {}


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {
        field: deepcopy(artifact.get(field))
        for field in PUBLIC_STATUS_FIELDS
        if field in artifact
    }
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _public_safety_errors(payload: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_payload",
                "private_payload",
                "broker_order_id",
                "external_order_id",
                "access_token",
                "refresh_token",
                "secret",
                "chat_id",
                "bot_token",
            }:
                errors.append(f"public_forbidden_key:{path}.{key}")
            errors.extend(_public_safety_errors(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            errors.extend(_public_safety_errors(item, f"{path}[{index}]"))
    elif isinstance(payload, str):
        lowered = payload.lower()
        if _has_local_path(payload):
            errors.append(f"public_local_path:{path}")
        if any(marker in lowered for marker in ("api_key", "bearer ", "secret_", "token_", "token=", "secret=")):
            errors.append(f"public_secret_ref:{path}")
        if any(marker in lowered for marker in ("broker_order_id", "external_order_id", "fill_id")):
            errors.append(f"public_broker_identifier:{path}")
    return errors


def _certification_status(
    *,
    final_certified: bool,
    currently_actionable: bool,
    current_blocker_count: int,
) -> str:
    if not final_certified:
        return "blocked_pending_final_certification"
    if currently_actionable:
        return "certified_actionable"
    if current_blocker_count:
        return "certified_waiting_for_qualified_setup"
    return "certified_idle"


def build_rs10_final_paper_autonomy_certification(
    payload: dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    source = _load_source_payload(payload, settings)
    mission = source.get("mission_control", {})
    stack = mission.get("system_stack", {})
    capital = source.get("capital", {})
    cognition = source.get("cognition", {})
    paper_authority = source.get("paper_authority_reconciliation", {})
    paper_live = source.get("paper_live_certification", {})
    active = source.get("paperops_active_paper_trading_automation", {})
    durable = source.get("durable_ingestion", {})
    rs9 = source.get("rs9_learning_loop", {})
    paper_lifecycle = source.get("paper_lifecycle_portfolio_postmortem", {})
    operator_inbox = source.get("operator_inbox", {})

    current_blockers = [str(item) for item in _list(paper_authority.get("current_blockers"))]
    safety_blockers = [str(item) for item in _list(paper_authority.get("safety_blockers"))]
    operational_blockers = [
        str(item) for item in _list(paper_authority.get("operational_blockers"))
    ]
    opportunity_or_risk_blockers = [
        str(item)
        for item in _list(paper_authority.get("opportunity_or_risk_blockers"))
    ]
    stale_keys = {
        str(item.get("key"))
        for item in _list(paper_authority.get("stale_historical_blockers"))
        if isinstance(item, dict)
    }
    stale_blocker_in_current_count = len(stale_keys & set(current_blockers))

    paper_submit_allowed = paper_authority.get("paper_submit_currently_allowed") is True
    paper_poll_allowed = paper_authority.get("paper_poll_currently_allowed") is True
    paper_exit_allowed = paper_authority.get("paper_exit_currently_allowed") is True
    currently_actionable = paper_submit_allowed or paper_poll_allowed or paper_exit_allowed

    unsafe_values = {
        "live_endpoint_called_count": _int(active.get("live_endpoint_called_count")),
        "broker_post_called_count": _int(paper_live.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(paper_live.get("alpaca_post_called_count")),
        "broker_write_allowed_count": _int(paper_live.get("broker_write_allowed_count")),
        "telegram_command_path_enabled_count": _int(
            paper_live.get("telegram_command_path_enabled_count")
        ),
        "raw_payload_exposed_count": 0,
        "private_payload_exposed_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "broker_identifier_exposed_count": 0,
    }
    unsafe_values["unsafe_write_counter_total"] = sum(
        value
        for key, value in unsafe_values.items()
        if key != "unsafe_write_counter_total"
    ) + _int(active.get("unsafe_write_counter_total"))

    certification_blockers: list[str] = []
    if source.get("mode") != "paper" or settings.mode != "paper":
        certification_blockers.append("mode_not_paper")
    if settings.live_capital_enabled or paper_authority.get("live_capital_enabled") is True:
        certification_blockers.append("live_capital_enabled")
    if paper_authority.get("paper_authorized") is not True:
        certification_blockers.append("paper_authority_not_certified")
    if safety_blockers:
        certification_blockers.append("safety_blockers_present")
    if stale_blocker_in_current_count:
        certification_blockers.append("stale_blocker_shown_as_current")
    if active.get("active_paper_trading_automation_enabled") is not True:
        certification_blockers.append("active_paper_automation_not_enabled")
    if active.get("active_paper_trading_automation_effective") is not True:
        certification_blockers.append("active_paper_automation_not_effective")
    if active.get("unattended_paper_execution_delegation_enabled") is not True:
        certification_blockers.append("unattended_paper_delegation_not_enabled")
    if active.get("paper_endpoint_confirmed") is not True:
        certification_blockers.append("alpaca_paper_endpoint_not_confirmed")
    if active.get("qctrl_paper_consultation_ready") is not True:
        certification_blockers.append("qctrl_paper_consultation_not_ready")
    if rs9.get("paperops_guarded_paper_trading_not_blocked") is not True:
        certification_blockers.append("rs9_blocks_guarded_paperops")
    if capital.get("mirror_status") not in {"ok", "live", "mirrored"} and capital.get(
        "connection_status"
    ) not in {"ok", "live", "mirrored", "alpaca_paper_readonly_connected"}:
        certification_blockers.append("paper_account_mirror_not_green")
    if unsafe_values["unsafe_write_counter_total"]:
        certification_blockers.append("unsafe_write_counter_nonzero")
    if paper_authority.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        certification_blockers.append("paper_submission_transport_invalid")

    final_certified = len(certification_blockers) == 0
    status = _certification_status(
        final_certified=final_certified,
        currently_actionable=currently_actionable,
        current_blocker_count=len(current_blockers),
    )

    artifact = {
        "schema_version": 1,
        "rs10_final_paper_autonomy_schema_version": (
            RS10_FINAL_PAPER_AUTONOMY_SCHEMA_VERSION
        ),
        "artifact_type": "rs10_final_paper_autonomy_certification",
        "artifact_id": "rs:rs-10:final-paper-autonomy-certification",
        "phase": "RS",
        "stage": "RS-10",
        "status": status,
        "generated_at": generated_at or _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "validation_error_count": 0,
        "certification_state": "certified" if final_certified else "blocked",
        "final_paper_autonomy_certified": final_certified,
        "paper_authority_certified": paper_authority.get("paper_authorized") is True,
        "guarded_paper_autonomy_allowed": final_certified,
        "autonomy_currently_actionable": currently_actionable,
        "multiple_paper_trades_per_day_allowed_when_gates_pass": final_certified,
        "paper_submit_currently_allowed": paper_submit_allowed,
        "paper_poll_currently_allowed": paper_poll_allowed,
        "paper_exit_currently_allowed": paper_exit_allowed,
        "paper_submission_transport": paper_authority.get(
            "paper_submission_transport",
            "paperops_guarded_alpaca_paper",
        ),
        "daily_target_policy": active.get("rs5_daily_target_policy", "minimum_not_ceiling"),
        "daily_target_is_minimum": active.get("rs5_daily_target_is_minimum") is True,
        "opportunity_scan_interval_minutes": _int(
            active.get("rs5_opportunity_scan_interval_minutes")
        ),
        "max_guarded_submit_attempts_per_run": _int(
            active.get("rs5_max_guarded_submit_attempts_per_run")
        ),
        "available_distinct_setup_count": _int(
            active.get("rs5_available_distinct_setup_count")
        ),
        "can_submit_multiple_today": active.get("rs5_can_submit_multiple_today") is True,
        "live_capital_enabled": False,
        "live_capital_blocked": True,
        **_authority_defaults(),
        "paper_account_mirror_status": capital.get("mirror_status")
        or capital.get("connection_status", "unknown"),
        "paper_current_balance_gbp": round(_float(capital.get("current_balance_gbp")), 2),
        "paper_open_position_count": _int(capital.get("open_position_count")),
        "paper_closed_trade_count": _int(capital.get("closed_trade_count")),
        "paper_order_count": _int(capital.get("order_count")),
        "source_online_count": _int(
            mission.get("data_sources", {}).get("online_count")
            or stack.get("source_online_count")
        ),
        "source_total_count": _int(
            mission.get("data_sources", {}).get("total_count")
            or source.get("watching_count")
        ),
        "durable_replay_status": durable.get("replay_status")
        or durable.get("contract_status", "unknown"),
        "durable_replayed_source_count": _int(durable.get("replayed_source_count")),
        "research_goal_active_count": _int(
            cognition.get("research_goals", {}).get("active_goal_count")
        ),
        "market_context_packet_count": _int(
            cognition.get("market_context", {}).get("packet_count")
        ),
        "local_research_status": stack.get("local_llm", "unknown"),
        "strategy_lead_status": stack.get("frontier_llm", "unknown"),
        "signal_integrity_status": cognition.get("signal_integrity", {}).get(
            "status",
            "unknown",
        ),
        "risk_agent_status": source.get("risk_agent", {}).get("status", "unknown"),
        "execution_policy_status": source.get("execution_policy", {}).get(
            "status",
            "unknown",
        ),
        "staged_paper_order_status": source.get("staged_paper_order", {}).get(
            "status",
            "unknown",
        ),
        "broker_reconciliation_status": source.get("broker_reconciliation", {}).get(
            "status",
            "unknown",
        ),
        "paper_submit_receipt_status": source.get("paper_submit_receipt", {}).get(
            "status",
            "unknown",
        ),
        "paper_lifecycle_status": paper_lifecycle.get("status", "unknown"),
        "operator_inbox_status": operator_inbox.get("status", "unknown"),
        "rs9_learning_loop_status": rs9.get("status", "unknown"),
        "rs9_paperops_guarded_paper_trading_not_blocked": (
            rs9.get("paperops_guarded_paper_trading_not_blocked") is True
        ),
        "qctrl_paper_consultation_ready": active.get("qctrl_paper_consultation_ready")
        is True,
        "paperops_active_status": active.get("status", "unknown"),
        "paperops_active_automation_enabled": (
            active.get("active_paper_trading_automation_enabled") is True
        ),
        "paperops_active_automation_effective": (
            active.get("active_paper_trading_automation_effective") is True
        ),
        "paperops_unattended_delegation_enabled": (
            active.get("unattended_paper_execution_delegation_enabled") is True
        ),
        "paperops_why_not_trading_now": active.get("why_not_trading_now")
        or paper_authority.get("why_not_trading_now"),
        "paper_live_certification_status": paper_live.get("status", "unknown"),
        "paper_live_control_plane_certified": (
            paper_live.get("paper_live_control_plane_certified") is True
        ),
        "paper_live_certified": paper_live.get("paper_live_certified") is True,
        "paper_live_certification_blocker_count": _int(
            paper_live.get("certification_blocker_count")
        ),
        "paper_live_context_blockers": [
            str(item) for item in _list(paper_live.get("certification_blockers"))
        ],
        "current_blockers": current_blockers,
        "current_blocker_count": len(current_blockers),
        "safety_blockers": safety_blockers,
        "safety_blocker_count": len(safety_blockers),
        "operational_blockers": operational_blockers,
        "opportunity_or_risk_blockers": opportunity_or_risk_blockers,
        "certification_blockers": sorted(set(certification_blockers)),
        "certification_blocker_count": len(set(certification_blockers)),
        "stale_historical_blocker_count": _int(
            paper_authority.get("stale_historical_blocker_count")
        ),
        "stale_blocker_in_current_count": stale_blocker_in_current_count,
        "allowed_paper_actions": [
            str(item) for item in _list(paper_authority.get("allowed_paper_actions"))
        ],
        "forbidden_actions": [
            str(item) for item in _list(paper_authority.get("forbidden_actions"))
        ],
        "rate_limit_policy_present": "HTTP 429"
        in str(paper_authority.get("rate_limit_policy") or ""),
        "rate_limit_policy": paper_authority.get("rate_limit_policy", ""),
        "why_not_trading_now": paper_authority.get("why_not_trading_now")
        or active.get("why_not_trading_now")
        or "No current why-not-trading reason exported.",
        "next_action": (
            "Run the guarded PaperOps runner."
            if currently_actionable
            else paper_authority.get("next_required_action")
            or active.get("next_required_action")
            or "Continue 20-minute opportunity scans until a qualified setup passes."
        ),
        **unsafe_values,
        "boundary": RS10_BOUNDARY,
    }
    return _refresh_validation(artifact)


def validate_rs10_final_paper_autonomy_certification(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS)
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("rs10_missing_fields:" + ",".join(missing))
    if artifact.get("rs10_final_paper_autonomy_schema_version") != (
        RS10_FINAL_PAPER_AUTONOMY_SCHEMA_VERSION
    ):
        errors.append("rs10_schema_version_mismatch")
    if artifact.get("phase") != "RS" or artifact.get("stage") != "RS-10":
        errors.append("rs10_phase_stage_mismatch")
    if artifact.get("status") not in {
        "certified_actionable",
        "certified_waiting_for_qualified_setup",
        "certified_idle",
        "blocked_pending_final_certification",
    }:
        errors.append("rs10_status_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("rs10_not_public_safe")
    if artifact.get("certification_blocker_count") != len(
        artifact.get("certification_blockers", []) or []
    ):
        errors.append("rs10_certification_blocker_count_mismatch")
    if artifact.get("current_blocker_count") != len(artifact.get("current_blockers", []) or []):
        errors.append("rs10_current_blocker_count_mismatch")
    if artifact.get("safety_blocker_count") != len(artifact.get("safety_blockers", []) or []):
        errors.append("rs10_safety_blocker_count_mismatch")
    if artifact.get("stale_blocker_in_current_count") != len(
        set(artifact.get("current_blockers", []) or [])
        & set(artifact.get("stale_historical_blockers", []) or [])
    ) and artifact.get("stale_blocker_in_current_count") != 0:
        errors.append("rs10_stale_blocker_count_mismatch")
    if artifact.get("stale_blocker_in_current_count") != 0:
        errors.append("rs10_stale_blocker_in_current")
    if artifact.get("final_paper_autonomy_certified") is True:
        if artifact.get("certification_state") != "certified":
            errors.append("rs10_certified_state_mismatch")
        if artifact.get("certification_blockers"):
            errors.append("rs10_certified_with_blockers")
        if artifact.get("paper_authority_certified") is not True:
            errors.append("rs10_certified_without_paper_authority")
        if artifact.get("guarded_paper_autonomy_allowed") is not True:
            errors.append("rs10_certified_without_guarded_autonomy")
    else:
        if artifact.get("status").startswith("certified"):
            errors.append("rs10_uncertified_with_certified_status")
        if not artifact.get("certification_blockers"):
            errors.append("rs10_uncertified_without_blockers")
    if artifact.get("autonomy_currently_actionable") is True and not any(
        artifact.get(key) is True
        for key in (
            "paper_submit_currently_allowed",
            "paper_poll_currently_allowed",
            "paper_exit_currently_allowed",
        )
    ):
        errors.append("rs10_actionable_without_action")
    if artifact.get("paper_submit_currently_allowed") is True and artifact.get(
        "paperops_active_status"
    ) != "active_automation_ready_to_submit":
        errors.append("rs10_submit_allowed_without_active_submit_status")
    if artifact.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        errors.append("rs10_invalid_submission_transport")
    if artifact.get("daily_target_policy") != "minimum_not_ceiling":
        errors.append("rs10_daily_target_policy_invalid")
    if artifact.get("daily_target_is_minimum") is not True:
        errors.append("rs10_daily_target_not_minimum")
    if _int(artifact.get("opportunity_scan_interval_minutes")) != 20:
        errors.append("rs10_scan_interval_invalid")
    if _int(artifact.get("max_guarded_submit_attempts_per_run")) > 3:
        errors.append("rs10_submit_attempt_cap_invalid")
    if artifact.get("rate_limit_policy_present") is not True:
        errors.append("rs10_rate_limit_policy_missing")
    rate_limit_policy = str(artifact.get("rate_limit_policy") or "")
    for phrase in ("HTTP 429", "same idempotency key", "bounded attempts"):
        if phrase not in rate_limit_policy:
            errors.append("rs10_rate_limit_policy_weak")
            break
    for field in AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"rs10_authority_enabled:{field}")
    if artifact.get("live_capital_blocked") is not True:
        errors.append("rs10_live_capital_not_blocked")
    if artifact.get("multiple_paper_trades_per_day_allowed_when_gates_pass") is not (
        artifact.get("final_paper_autonomy_certified") is True
    ):
        errors.append("rs10_multiple_trades_policy_mismatch")
    unsafe_total = 0
    for field in UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field != "unsafe_write_counter_total":
            unsafe_total += value
        if value != 0:
            errors.append(f"rs10_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("rs10_unsafe_total_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded paper autonomy only",
        "multiple guarded Alpaca paper trades per day",
        "cannot force trades",
        "cannot submit without PaperOps gates",
        "cannot bypass risk checks",
        "LLMs or quantum outputs approve trades",
        "dashboard or Telegram command authority",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("rs10_boundary_weak")
            break
    public_status = artifact.get("public_status")
    if isinstance(public_status, dict):
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("rs10_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"rs10_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))
    if artifact.get("event_log_written") is True:
        if "event_log_correlation_id" in artifact and not artifact.get(
            "event_log_correlation_id"
        ):
            errors.append("rs10_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("rs10_event_count_mismatch")
    return sorted(set(errors))


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_rs10_final_paper_autonomy_certification(
            artifact
        )
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked_pending_final_certification"
        artifact["certification_state"] = "blocked"
        artifact["final_paper_autonomy_certified"] = False
        artifact["guarded_paper_autonomy_allowed"] = False
        artifact["multiple_paper_trades_per_day_allowed_when_gates_pass"] = False
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def attach_rs10_final_paper_autonomy_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / RS10_FINAL_PAPER_AUTONOMY_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        RS10_FINAL_PAPER_AUTONOMY_EVENT_TYPE,
        RS10_FINAL_PAPER_AUTONOMY_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "final_paper_autonomy_certified": output.get(
                "final_paper_autonomy_certified"
            ),
            "autonomy_currently_actionable": output.get(
                "autonomy_currently_actionable"
            ),
            "paper_submit_currently_allowed": output.get(
                "paper_submit_currently_allowed"
            ),
            "current_blocker_count": output.get("current_blocker_count"),
            "certification_blocker_count": output.get("certification_blocker_count"),
            "why_not_trading_now": output.get("why_not_trading_now"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    return _refresh_validation(output), entry


def write_rs10_final_paper_autonomy_certification(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = rs10_final_paper_autonomy_paths(
        settings
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_rs10_final_paper_autonomy_event_log(
            output,
            event_log_path=event_log_path or default_event_path,
            settings=settings,
        )
    else:
        output = _refresh_validation(output)
    output = _refresh_validation(output)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": RS10_FINAL_PAPER_AUTONOMY_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "final_paper_autonomy_certified": output.get("final_paper_autonomy_certified"),
        "autonomy_currently_actionable": output.get("autonomy_currently_actionable"),
        "current_blocker_count": output.get("current_blocker_count"),
        "certification_blocker_count": output.get("certification_blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, Path(event_log_path or default_event_path), output


def rs10_final_paper_autonomy_public_status(
    *,
    settings: Settings | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if payload is not None:
        _, _, _, artifact = write_rs10_final_paper_autonomy_certification(
            build_rs10_final_paper_autonomy_certification(
                payload,
                settings=settings,
                generated_at=payload.get("generated_at"),
            ),
            settings=settings,
            record_event=True,
        )
        return _public_status_from_artifact(artifact)
    output_path, _, _ = rs10_final_paper_autonomy_paths(settings)
    artifact = None
    if output_path.exists():
        payload_data = json.loads(output_path.read_text(encoding="utf-8"))
        artifact = payload_data if isinstance(payload_data, dict) else None
    if artifact is None or artifact.get("recorded") is not True:
        _, _, _, artifact = write_rs10_final_paper_autonomy_certification(
            build_rs10_final_paper_autonomy_certification(settings=settings),
            settings=settings,
            record_event=True,
        )
    validation_errors = validate_rs10_final_paper_autonomy_certification(artifact)
    public_status = _public_status_from_artifact(artifact)
    public_status["validation_error_count"] = len(validation_errors)
    return public_status
