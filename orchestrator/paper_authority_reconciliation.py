"""RS-0 paper authority reconciliation contract.

This contract separates paper-trading authority from current operational
readiness. A paused scheduler, no fresh setup, or a Q-CTRL consultation hold
must be visible as blockers, but they are not the same thing as unsafe live
capital authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings


PAPER_AUTHORITY_RECONCILIATION_SCHEMA_VERSION = 1

PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "paper_authorized",
    "paper_submission_transport",
    "paper_submit_currently_allowed",
    "paper_poll_currently_allowed",
    "paper_exit_currently_allowed",
    "live_capital_enabled",
    "live_capital_blocked",
    "full_potential_state",
    "current_blockers",
    "current_blocker_count",
    "safety_blockers",
    "operational_blockers",
    "opportunity_or_risk_blockers",
    "external_blockers",
    "stale_historical_blockers",
    "stale_historical_blocker_count",
    "allowed_paper_actions",
    "forbidden_actions",
    "why_not_trading_now",
    "next_required_action",
    "rate_limit_policy",
    "boundary",
    "validation_error_count",
)

_STALE_HISTORICAL_BLOCKERS: tuple[dict[str, str], ...] = (
    {
        "key": "phase2_non_executable_intelligence_chain",
        "reason": "Historical Phase 2 shadow-intelligence wording; no longer a global PaperOps paper-submit ban.",
    },
    {
        "key": "phase5_pre_paperops_submit_blockers",
        "reason": "Phase 5 dry-run blockers are superseded by PaperOps guarded paper-route gates.",
    },
    {
        "key": "phase7_proof_credit_blocked",
        "reason": "Phase 7 proof credit remains blocked, but proof credit is separate from guarded paper trading.",
    },
)

_ALLOWED_PAPER_ACTIONS: tuple[str, ...] = (
    "scan_opportunities_every_20_minutes",
    "create_research_goals",
    "run_local_research_compression",
    "run_strategy_lead_challenge_review",
    "stage_guarded_paper_order",
    "submit_guarded_alpaca_paper_order_when_gates_pass",
    "poll_paper_order_and_position_lifecycle",
    "run_guarded_paper_exit_when_exit_candidate_passes",
)

_FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "enable_live_capital",
    "call_live_broker_endpoints",
    "submit_orders_from_dashboard",
    "submit_orders_from_telegram",
    "let_local_llm_approve_risk",
    "let_frontier_llm_approve_risk",
    "let_quantum_oracle_create_or_submit_trades",
    "use_unmanaged_broker_write_shortcuts",
    "force_trades_without_gates",
    "grant_phase7_proof_credit_from_paper_submission",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, set):
        return sorted(str(item) for item in value if str(item))
    return [str(value)]


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _build_safety_blockers(settings: Settings, active: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if settings.mode != "paper" or active.get("mode", settings.mode) != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled or active.get("live_capital_enabled") is not False:
        blockers.append("live_capital_enabled")
    for key in (
        "live_endpoint_allowed",
        "direct_broker_shortcut_allowed",
        "paper_order_submission_allowed_without_paperops2",
        "qctrl_direct_execution_allowed",
        "qctrl_broker_post_allowed",
        "forced_trades_allowed",
        "phase7_proof_credit_allowed",
    ):
        if active.get(key) is not False:
            blockers.append(key)
    if _int(active.get("live_endpoint_called_count")) != 0:
        blockers.append("live_endpoint_called")
    if _int(active.get("unsafe_write_counter_total")) != 0:
        blockers.append("unsafe_write_counter_nonzero")
    return blockers


def _build_operational_blockers(active: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for blocker in _as_list(active.get("blockers")):
        if blocker in {
            "automation_not_found",
            "automation_not_active",
            "automation_not_hourly",
            "automation_wrong_cwd",
            "automation_prompt_not_bound",
            "readiness_not_safe_to_continue",
            "alpaca_paper_endpoint_not_confirmed",
            "mode_not_paper",
            "live_capital_enabled",
        }:
            _append_unique(blockers, blocker)
    if active.get("automation_active") is not True:
        _append_unique(blockers, "automation_not_active")
    if active.get("automation_hourly") is not True:
        _append_unique(blockers, "automation_not_hourly")
    if active.get("automation_cwd_bound") is not True:
        _append_unique(blockers, "automation_wrong_cwd")
    if active.get("automation_prompt_active_trade_bound") is not True:
        _append_unique(blockers, "automation_prompt_not_bound")
    if active.get("paperops_safe_to_continue") is not True:
        _append_unique(blockers, "readiness_not_safe_to_continue")
    if active.get("paper_endpoint_confirmed") is not True:
        _append_unique(blockers, "alpaca_paper_endpoint_not_confirmed")
    return blockers


def _build_opportunity_or_risk_blockers(active: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if active.get("qctrl_consultation_hold_active") is True:
        blockers.append("qctrl_paper_consultation_hold")
    if _int(active.get("paperops2_fresh_eligible_submit_record_count")) < 1:
        blockers.append("no_fresh_eligible_candidate")
    if active.get("paperops2_status") not in {
        "ready_pending_explicit_execute",
        "submitted_paper_order_recorded",
    }:
        blockers.append("paperops2_submit_gate_not_ready")
    if active.get("paper_poll_step_allowed") is not True and _int(
        active.get("paperops3_source_submitted_order_count")
    ) > 0:
        blockers.append("paper_poll_gate_not_ready")
    if active.get("paper_exit_step_allowed") is not True and _int(
        active.get("paperops4_eligible_exit_record_count")
    ) > 0:
        blockers.append("paper_exit_gate_not_ready")
    return blockers


def _status(
    *,
    safety_blockers: list[str],
    operational_blockers: list[str],
    opportunity_or_risk_blockers: list[str],
    active: dict[str, Any],
) -> str:
    if safety_blockers:
        return "blocked_by_safety"
    if active.get("paper_submit_step_allowed") is True:
        return "paper_authorized_ready_to_submit"
    if active.get("paper_poll_step_allowed") is True:
        return "paper_authorized_ready_to_poll"
    if active.get("paper_exit_step_allowed") is True:
        return "paper_authorized_ready_to_exit"
    if operational_blockers:
        return "paper_authorized_blocked_operational"
    if opportunity_or_risk_blockers:
        return "paper_authorized_waiting_for_setup"
    return "paper_authorized_idle"


def _full_potential_state(status: str) -> str:
    if status == "blocked_by_safety":
        return "safety_blocked"
    if status == "paper_authorized_blocked_operational":
        return "authorized_but_not_armed"
    if status == "paper_authorized_waiting_for_setup":
        return "authorized_waiting_for_qualified_setup"
    if status in {
        "paper_authorized_ready_to_submit",
        "paper_authorized_ready_to_poll",
        "paper_authorized_ready_to_exit",
    }:
        return "authorized_and_actionable"
    return "authorized_idle"


def _why_not_trading_now(
    *,
    status: str,
    safety_blockers: list[str],
    operational_blockers: list[str],
    opportunity_or_risk_blockers: list[str],
) -> str:
    if status == "blocked_by_safety":
        return "Safety blocker prevents paper operation: " + ", ".join(safety_blockers)
    if status == "paper_authorized_blocked_operational":
        return (
            "Paper trading is authorized, but the operational runner is not armed: "
            + ", ".join(operational_blockers)
        )
    if status == "paper_authorized_waiting_for_setup":
        return (
            "Paper trading is authorized; no fresh qualified setup is currently eligible: "
            + ", ".join(opportunity_or_risk_blockers)
        )
    if status == "paper_authorized_ready_to_submit":
        return "A guarded Alpaca paper submit step is eligible through PaperOps."
    if status == "paper_authorized_ready_to_poll":
        return "A paper order or position lifecycle poll is eligible through PaperOps."
    if status == "paper_authorized_ready_to_exit":
        return "A guarded paper exit step is eligible through PaperOps."
    return "Paper trading is authorized and idle; Qadam is waiting for the next qualified setup."


def _next_required_action(status: str) -> str:
    if status == "blocked_by_safety":
        return "Resolve safety blockers before any paper operation."
    if status == "paper_authorized_blocked_operational":
        return "Arm the hourly PaperOps autonomous runner or invoke the guarded runner manually."
    if status == "paper_authorized_waiting_for_setup":
        return "Continue source scans and research-goal lifecycle until a fresh qualified setup passes."
    if status == "paper_authorized_ready_to_submit":
        return "Run the guarded PaperOps active paper trading runner."
    if status == "paper_authorized_ready_to_poll":
        return "Run the PaperOps lifecycle poller."
    if status == "paper_authorized_ready_to_exit":
        return "Run the guarded PaperOps paper exit path."
    return "Continue the 20-minute opportunity scan cadence."


def build_paper_authority_reconciliation(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    active = payload.get("paperops_active_paper_trading_automation", {})
    generated_at = generated_at or _now()
    safety_blockers = _build_safety_blockers(settings, active)
    operational_blockers = _build_operational_blockers(active)
    opportunity_or_risk_blockers = _build_opportunity_or_risk_blockers(active)
    external_blockers: list[str] = []
    status = _status(
        safety_blockers=safety_blockers,
        operational_blockers=operational_blockers,
        opportunity_or_risk_blockers=opportunity_or_risk_blockers,
        active=active,
    )
    current_blockers = (
        safety_blockers + operational_blockers + opportunity_or_risk_blockers + external_blockers
    )
    contract = {
        "schema_version": PAPER_AUTHORITY_RECONCILIATION_SCHEMA_VERSION,
        "artifact_type": "paper_authority_reconciliation",
        "artifact_id": "paperops:rs-0:paper-authority-reconciliation",
        "phase": "RS",
        "stage": "RS-0",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "mode": settings.mode,
        "paper_authorized": not safety_blockers,
        "paper_submission_transport": "paperops_guarded_alpaca_paper",
        "paper_submit_currently_allowed": active.get("paper_submit_step_allowed") is True
        and not safety_blockers
        and not operational_blockers,
        "paper_poll_currently_allowed": active.get("paper_poll_step_allowed") is True
        and not safety_blockers
        and not operational_blockers,
        "paper_exit_currently_allowed": active.get("paper_exit_step_allowed") is True
        and not safety_blockers
        and not operational_blockers,
        "live_capital_enabled": settings.live_capital_enabled,
        "live_capital_blocked": settings.live_capital_enabled is False,
        "full_potential_state": _full_potential_state(status),
        "current_blockers": current_blockers,
        "current_blocker_count": len(current_blockers),
        "safety_blockers": safety_blockers,
        "operational_blockers": operational_blockers,
        "opportunity_or_risk_blockers": opportunity_or_risk_blockers,
        "external_blockers": external_blockers,
        "stale_historical_blockers": list(_STALE_HISTORICAL_BLOCKERS),
        "stale_historical_blocker_count": len(_STALE_HISTORICAL_BLOCKERS),
        "allowed_paper_actions": list(_ALLOWED_PAPER_ACTIONS),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "why_not_trading_now": _why_not_trading_now(
            status=status,
            safety_blockers=safety_blockers,
            operational_blockers=operational_blockers,
            opportunity_or_risk_blockers=opportunity_or_risk_blockers,
        ),
        "next_required_action": _next_required_action(status),
        "rate_limit_policy": (
            "HTTP 429 is a temporary operational blocker. Retry paper submits only "
            "through PaperOps with the same idempotency key, bounded attempts, and no "
            "live-capital or unmanaged broker-write fallback."
        ),
        "boundary": (
            "RS-0 reconciles paper authority only. It can classify current blockers "
            "and authorize the guarded Alpaca paper route when gates pass, but it "
            "cannot submit orders, enable live capital, bypass risk checks, let LLMs "
            "or quantum outputs approve trades, or create dashboard/Telegram order authority."
        ),
        "validation_error_count": 0,
    }
    errors = validate_paper_authority_reconciliation(contract)
    contract["validation_error_count"] = len(errors)
    if errors:
        contract["status"] = "invalid"
    return contract


def validate_paper_authority_reconciliation(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PAPER_AUTHORITY_RECONCILIATION_PUBLIC_FIELDS) - set(contract))
    if missing:
        errors.append("paper_authority_reconciliation_missing_fields:" + ",".join(missing))
    if contract.get("schema_version") != PAPER_AUTHORITY_RECONCILIATION_SCHEMA_VERSION:
        errors.append("paper_authority_reconciliation_schema_version_mismatch")
    if contract.get("artifact_type") != "paper_authority_reconciliation":
        errors.append("paper_authority_reconciliation_artifact_type_mismatch")
    if contract.get("public_safe") is not True:
        errors.append("paper_authority_reconciliation_not_public_safe")
    if contract.get("mode") != "paper":
        errors.append("paper_authority_reconciliation_mode_not_paper")
    if contract.get("live_capital_enabled") is not False:
        errors.append("paper_authority_reconciliation_live_capital_enabled")
    if contract.get("live_capital_blocked") is not True:
        errors.append("paper_authority_reconciliation_live_capital_not_blocked")
    if contract.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        errors.append("paper_authority_reconciliation_transport_invalid")
    stale_keys = {
        str(item.get("key"))
        for item in contract.get("stale_historical_blockers", [])
        if isinstance(item, dict)
    }
    current_keys = set(_as_list(contract.get("current_blockers")))
    if stale_keys & current_keys:
        errors.append("paper_authority_reconciliation_stale_blocker_current")
    if contract.get("status", "").startswith("paper_authorized") and contract.get(
        "safety_blockers"
    ):
        errors.append("paper_authority_reconciliation_authorized_with_safety_blockers")
    if contract.get("paper_submit_currently_allowed") is True and contract.get(
        "paper_authorized"
    ) is not True:
        errors.append("paper_authority_reconciliation_submit_without_authority")
    boundary = str(contract.get("boundary") or "")
    for phrase in (
        "cannot submit orders",
        "enable live capital",
        "bypass risk checks",
        "LLMs or quantum outputs approve trades",
        "dashboard/Telegram order authority",
    ):
        if phrase not in boundary:
            errors.append("paper_authority_reconciliation_boundary_weak")
            break
    rate_limit_policy = str(contract.get("rate_limit_policy") or "")
    for phrase in ("HTTP 429", "same idempotency key", "bounded attempts"):
        if phrase not in rate_limit_policy:
            errors.append("paper_authority_reconciliation_rate_limit_policy_weak")
            break
    forbidden = set(_as_list(contract.get("forbidden_actions")))
    for action in (
        "enable_live_capital",
        "call_live_broker_endpoints",
        "submit_orders_from_dashboard",
        "submit_orders_from_telegram",
        "use_unmanaged_broker_write_shortcuts",
        "force_trades_without_gates",
    ):
        if action not in forbidden:
            errors.append("paper_authority_reconciliation_forbidden_action_missing")
            break
    return errors
