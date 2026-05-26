"""Q5-5 execution adapter status contract.

This module promotes execution venues into public-safe, replayable status
records. It only reports read status, permission posture, kill-switch posture,
and future reconciliation prerequisites. It does not create execution intents,
stage orders, submit paper orders, call brokers, or enable live capital.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.execution import execution_registry
from orchestrator.paper_account import (
    ALPACA_PAPER_BASE_URL,
    ALPACA_READONLY_PATHS,
    alpaca_paper_mirror_status,
    paper_account_shadow_context,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    validate_phase5_kill_switch_ledger,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION = 1
EXECUTION_ADAPTER_RUNTIME_ARTIFACT = "phase5_execution_adapter_status.json"
EXECUTION_ADAPTER_HISTORY = "phase5_execution_adapter_status_history.jsonl"
EXECUTION_ADAPTER_EVENT_LOG = "phase5_execution_adapter_events.jsonl"
EXECUTION_ADAPTER_EVENT_TYPE = "phase5_execution_adapter_status_written"
EXECUTION_ADAPTER_COMPONENT = "phase5_execution_adapter_status"
GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT = "phase5_guarded_postmortem_due.json"
EXECUTION_ADAPTER_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_kill_switch_ledger.json",
    "data/runtime/phase5_risk_sizing_reviews.json",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/paper_positions.jsonl",
    "data/runtime/paper_orders.jsonl",
    "data/runtime/alpaca_paper_mirror.json",
    f"data/runtime/{GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT}",
)

EXECUTION_ADAPTER_REQUIRED_CHECKS: tuple[str, ...] = (
    "venue_registry_present",
    "venue_mode_not_live",
    "credential_state_known",
    "account_mode_paper",
    "account_balance_known",
    "open_orders_known",
    "open_positions_known",
    "market_session_state_known",
    "permission_scope_read_only",
    "rate_limit_state_known",
    "kill_switch_clear",
    "write_health_blocked",
    "live_endpoint_blocked",
)

EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES: tuple[str, ...] = (
    "event_log_prewrite_required",
    "idempotency_key_required_later",
    "pre_trade_snapshot_required_later",
    "duplicate_order_guard_required_later",
    "broker_echo_required_later",
    "post_submit_reconciliation_required_later",
    "postmortem_link_required_later",
    "paper_account_write_authority_must_remain_false",
)

EXECUTION_ADAPTER_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "risk_agent_handoff_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "execution_adapter_write_authority",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "staged_paper_order_allowed",
    "staged_order_created",
    "paper_order_submission_allowed",
    "paper_order_submitted",
    "broker_write_allowed",
    "broker_post_called",
    "broker_submit_receipt_created",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "position_created",
    "position_monitor_write_authority",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "crypto_perps_write_allowed",
    "downstream_staging_allowed",
    "reconciliation_ready_for_submit",
)

EXECUTION_ADAPTER_COUNT_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed_count",
    "trade_candidate_created_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "execution_adapter_write_authority_count",
    "paper_order_staging_allowed_count",
    "paper_order_submission_allowed_count",
    "paper_order_allowed_count",
    "staged_order_created_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "broker_submit_receipt_created_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "crypto_perps_write_allowed_count",
    "reconciliation_ready_for_submit_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
)

EXECUTION_ADAPTER_BOUNDARY = (
    "Q5-5 execution adapter status records are read-only venue readiness "
    "contracts. They can report credentials, paper-account state, kill-switch "
    "state, permissions, degradation, and future reconciliation prerequisites, "
    "but they cannot create execution intents, stage or submit paper orders, "
    "write brokers, call prediction-market write endpoints, send live alerts, "
    "create positions, or enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-5"
    ledger["boundary"] = (
        "Q5-5 records read-only adapter status only. Every execution, order, "
        "broker, prediction-market write, position, and live-capital flag stays false."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _endpoint_classification(alpaca_status: dict[str, Any]) -> str:
    base_url = str(alpaca_status.get("base_url") or "")
    if base_url.rstrip("/").startswith(ALPACA_PAPER_BASE_URL):
        return "alpaca_paper_endpoint"
    return "live_or_unknown_endpoint_blocked"


def _kill_switch_context(
    venue: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    path = _runtime_dir(settings) / KILL_SWITCH_RUNTIME_ARTIFACT
    ledger = _read_json(path)
    if ledger is None:
        return {
            "status": "fail_closed",
            "ledger_recorded": False,
            "validation_error_count": 1,
            "active": True,
            "blockers": ["kill_switch_ledger_missing_fail_closed"],
            "matched_scopes": ["global:all", f"venue:{venue.get('key', 'unknown')}"],
        }
    validation_errors = validate_phase5_kill_switch_ledger(ledger)
    matched_scopes = {
        "global:all",
        f"venue:{venue.get('key', 'unknown')}",
    }
    adapter = str(venue.get("adapter") or "")
    if adapter == "alpaca":
        matched_scopes.add("broker_adapter:alpaca")
    if str(venue.get("key") or "") == "prediction_market_router":
        matched_scopes.add("prediction_market_adapter:pmxt_polyrouter")
    switches = [
        switch
        for switch in ledger.get("switches", [])
        if isinstance(switch, dict) and switch.get("switch_scope") in matched_scopes
    ]
    active_switches = [
        str(switch.get("switch_scope") or "unknown")
        for switch in switches
        if switch.get("blocks_new_actions") is True or switch.get("switch_active") is True
    ]
    blockers: list[str] = []
    if validation_errors:
        blockers.append("kill_switch_ledger_validation_failed")
    blockers.extend(f"active_kill_switch:{scope}" for scope in active_switches)
    return {
        "status": "clear" if not blockers else "blocked",
        "ledger_recorded": True,
        "validation_error_count": len(validation_errors),
        "active": bool(blockers),
        "blockers": sorted(dict.fromkeys(blockers)),
        "matched_scopes": sorted(matched_scopes),
        "matched_switch_count": len(switches),
    }


def _alpaca_status(settings: Settings) -> dict[str, Any]:
    mirror = alpaca_paper_mirror_status(settings)
    account = paper_account_shadow_context(settings)
    postmortem_due_artifact = _read_json(
        _runtime_dir(settings) / GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT
    ) or {}
    endpoint = _endpoint_classification(mirror)
    credentials_configured = mirror.get("status") == "configured"
    paper_mode = mirror.get("paper_mode") is True
    connection_status = str(account.get("connection_status") or "missing")
    account_mode = str(account.get("mode") or "missing")
    balance = float(account.get("current_balance_gbp") or 0.0)
    open_orders = int(account.get("open_order_count", 0) or 0)
    open_positions = int(account.get("open_position_count", 0) or 0)
    degraded = not credentials_configured or not paper_mode or endpoint != "alpaca_paper_endpoint"
    read_health = "read_only_available" if not degraded else "blocked_read_unavailable"
    blockers: list[str] = []
    guarded_postmortem_due_ready = (
        postmortem_due_artifact.get("status") == "postmortem_due"
        and postmortem_due_artifact.get("postmortem_due_marker_created") is True
        and int(postmortem_due_artifact.get("postmortem_due_count", 0) or 0) >= 1
    )
    hold_reasons = (
        []
        if guarded_postmortem_due_ready
        else ["market_session_not_checked_q5_5", "q5_6_staging_gate_not_implemented"]
    )
    if not credentials_configured:
        blockers.append("alpaca_paper_credentials_missing")
    if not paper_mode:
        blockers.append("alpaca_account_mode_not_paper")
    if endpoint != "alpaca_paper_endpoint":
        blockers.append("alpaca_live_or_unknown_endpoint_blocked")
    if account_mode != "paper":
        blockers.append("paper_account_context_mode_not_paper")
    if balance <= 0:
        blockers.append("paper_account_balance_unavailable")
    if account.get("write_authority") is not False:
        blockers.append("paper_account_write_authority_enabled")
    if account.get("live_capital_enabled") is not False:
        blockers.append("paper_account_live_capital_enabled")
    return {
        "credential_status": "configured" if credentials_configured else "missing_credentials",
        "credentials_configured": credentials_configured,
        "account_mode": account_mode,
        "account_connection_status": connection_status,
        "paper_mode": paper_mode,
        "current_balance_gbp": balance,
        "cash_gbp": float(account.get("cash_gbp") or 0.0),
        "equity_gbp": float(account.get("equity_gbp") or balance),
        "open_order_count": open_orders,
        "open_position_count": open_positions,
        "closed_trade_count": int(account.get("closed_trade_count", 0) or 0),
        "market_session_state": (
            "guarded_q5e_lifecycle_verified"
            if guarded_postmortem_due_ready
            else "not_checked_q5_5_blocks_staging"
        ),
        "permission_scope": "read_only",
        "rate_limit_status": "not_degraded_local_contract",
        "degraded": degraded,
        "degraded_reasons": blockers,
        "read_health": read_health,
        "write_health": "blocked_q5_5_status_contract",
        "endpoint_classification": endpoint,
        "base_url_exposed": False,
        "readonly_paths": sorted(ALPACA_READONLY_PATHS),
        "readonly_path_count": len(ALPACA_READONLY_PATHS),
        "blockers": blockers,
        "hold_reasons": hold_reasons,
        "execution_adapter_read_allowed": credentials_configured and paper_mode and not degraded,
        "guarded_postmortem_due_ready": guarded_postmortem_due_ready,
        "guarded_postmortem_due_artifact_id": postmortem_due_artifact.get("artifact_id"),
        "guarded_postmortem_due_ref": postmortem_due_artifact.get("postmortem_due_ref"),
    }


def _non_alpaca_status(venue: dict[str, Any]) -> dict[str, Any]:
    venue_key = str(venue.get("key") or "unknown")
    is_prediction = venue_key == "prediction_market_router"
    is_privex = str(venue.get("adapter") or "") == "privex"
    if is_privex:
        read_health = "read_disabled_first_release_live_blocked"
        hold_reasons: list[str] = []
        blockers = ["privex_first_release_live_blocked"]
        permission_scope = "disabled"
        market_session_state = "not_applicable_live_blocked"
        credential_status = "not_configured"
    elif is_prediction:
        read_health = "read_only_placeholder_disabled"
        hold_reasons = ["prediction_market_route_read_only_placeholder"]
        blockers = []
        permission_scope = "read_only_placeholder"
        market_session_state = "not_checked_q5_5_blocks_staging"
        credential_status = "missing_credentials"
    else:
        read_health = "disabled_unknown_adapter"
        hold_reasons = []
        blockers = ["unknown_adapter_disabled"]
        permission_scope = "disabled"
        market_session_state = "not_checked"
        credential_status = "unknown"
    return {
        "credential_status": credential_status,
        "credentials_configured": False,
        "account_mode": str(venue.get("account_scope") or "unknown"),
        "account_connection_status": "not_connected",
        "paper_mode": False,
        "current_balance_gbp": 0.0,
        "cash_gbp": 0.0,
        "equity_gbp": 0.0,
        "open_order_count": 0,
        "open_position_count": 0,
        "closed_trade_count": 0,
        "market_session_state": market_session_state,
        "permission_scope": permission_scope,
        "rate_limit_status": "not_checked_disabled",
        "degraded": bool(blockers),
        "degraded_reasons": blockers,
        "read_health": read_health,
        "write_health": "blocked_q5_5_status_contract",
        "endpoint_classification": "no_endpoint_enabled",
        "base_url_exposed": False,
        "readonly_paths": [],
        "readonly_path_count": 0,
        "blockers": blockers,
        "hold_reasons": hold_reasons,
        "execution_adapter_read_allowed": False,
    }


def _adapter_context(venue: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if str(venue.get("key") or "") == "alpaca_paper":
        return _alpaca_status(settings)
    return _non_alpaca_status(venue)


def _checks(
    venue: dict[str, Any],
    adapter: dict[str, Any],
    kill_switch: dict[str, Any],
) -> list[dict[str, Any]]:
    venue_mode = str(venue.get("mode") or "missing")
    return [
        _check("venue_registry_present", bool(venue.get("key"))),
        _check("venue_mode_not_live", venue_mode != "live"),
        _check("credential_state_known", adapter.get("credential_status") != "unknown"),
        _check("account_mode_paper", adapter.get("account_mode") in {"paper", "paper_or_read_only_first"}),
        _check("account_balance_known", float(adapter.get("current_balance_gbp", 0.0) or 0.0) >= 0.0),
        _check("open_orders_known", isinstance(adapter.get("open_order_count"), int)),
        _check("open_positions_known", isinstance(adapter.get("open_position_count"), int)),
        _check("market_session_state_known", bool(adapter.get("market_session_state"))),
        _check(
            "permission_scope_read_only",
            str(adapter.get("permission_scope") or "").startswith("read_only")
            or adapter.get("permission_scope") == "disabled",
        ),
        _check("rate_limit_state_known", bool(adapter.get("rate_limit_status"))),
        _check("kill_switch_clear", kill_switch.get("active") is False),
        _check("write_health_blocked", str(adapter.get("write_health") or "").startswith("blocked")),
        _check("live_endpoint_blocked", adapter.get("endpoint_classification") != "live_endpoint"),
    ]


def _status_from_context(
    venue: dict[str, Any],
    adapter: dict[str, Any],
    kill_switch: dict[str, Any],
    blockers: list[str],
    hold_reasons: list[str],
) -> tuple[str, str]:
    if str(venue.get("mode") or "") == "live_blocked" or str(venue.get("adapter") or "") == "privex":
        return "live_blocked", "live_blocked_first_release_excluded"
    if kill_switch.get("active") is True:
        return "blocked", "blocked_by_kill_switch"
    if blockers:
        return "blocked", "blocked_adapter_status_failed"
    if hold_reasons:
        return "hold", "hold_read_only_status_collected"
    return "eligible", "eligible_read_only_status_for_q5_6"


def _execution_adapter_status(
    venue: dict[str, Any],
    *,
    settings: Settings,
    generated_at: str,
) -> dict[str, Any]:
    adapter = _adapter_context(venue, settings)
    kill_switch = _kill_switch_context(venue, settings)
    checks = _checks(venue, adapter, kill_switch)
    blockers = list(adapter.get("blockers", [])) + [
        check["name"] for check in checks if not check["passed"] and check["name"] != "account_mode_paper"
    ]
    blockers.extend(kill_switch.get("blockers", []))
    blockers = sorted(dict.fromkeys(str(blocker) for blocker in blockers if blocker))
    hold_reasons = sorted(dict.fromkeys(str(reason) for reason in adapter.get("hold_reasons", [])))
    guarded_staging_ready = (
        str(venue.get("key") or "") == "alpaca_paper"
        and adapter.get("guarded_postmortem_due_ready") is True
        and adapter.get("execution_adapter_read_allowed") is True
        and not blockers
        and kill_switch.get("active") is False
    )
    if str(venue.get("key") or "") == "alpaca_paper" and not guarded_staging_ready:
        hold_reasons.append("q5_6_staging_gate_not_implemented")
    status, decision = _status_from_context(venue, adapter, kill_switch, blockers, hold_reasons)
    if guarded_staging_ready:
        status = "eligible"
        decision = "eligible_guarded_q5e_staging_readiness_for_q5_14"
    venue_key = str(venue.get("key") or "unknown")
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "execution_adapter_schema_version": PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION,
        "artifact_type": "execution_adapter_status",
        "artifact_id": f"phase5:q5-5:execution-adapter:{_safe_key(venue_key)}",
        "phase": "Q5",
        "stage": "Q5-5",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(EXECUTION_ADAPTER_SOURCE_REFS),
        "boundary": EXECUTION_ADAPTER_BOUNDARY,
        **phase5_authority_defaults(),
        "venue_key": venue_key,
        "venue_name": str(venue.get("name") or venue_key),
        "adapter_key": str(venue.get("adapter") or "unknown"),
        "venue_mode": str(venue.get("mode") or "disabled"),
        "account_scope": str(venue.get("account_scope") or "unknown"),
        "network_scope": str(venue.get("network_scope") or "unknown"),
        "first_release_allowed": venue.get("first_release_allowed") is True,
        "credential_status": adapter["credential_status"],
        "credentials_configured": adapter["credentials_configured"],
        "permissions_status": adapter["permission_scope"],
        "permission_scope": adapter["permission_scope"],
        "read_health": adapter["read_health"],
        "write_health": adapter["write_health"],
        "rate_limit_status": adapter["rate_limit_status"],
        "degraded": adapter["degraded"],
        "degraded_reasons": adapter["degraded_reasons"],
        "degraded_reason_count": len(adapter["degraded_reasons"]),
        "market_session_state": adapter["market_session_state"],
        "endpoint_classification": adapter["endpoint_classification"],
        "base_url_exposed": adapter["base_url_exposed"],
        "readonly_paths": adapter["readonly_paths"],
        "readonly_path_count": adapter["readonly_path_count"],
        "account_mode": adapter["account_mode"],
        "account_connection_status": adapter["account_connection_status"],
        "paper_mode": adapter["paper_mode"],
        "current_balance_gbp": adapter["current_balance_gbp"],
        "cash_gbp": adapter["cash_gbp"],
        "equity_gbp": adapter["equity_gbp"],
        "open_order_count": adapter["open_order_count"],
        "open_position_count": adapter["open_position_count"],
        "closed_trade_count": adapter["closed_trade_count"],
        "execution_adapter_decision": decision,
        "execution_adapter_read_allowed": adapter["execution_adapter_read_allowed"],
        "downstream_staging_allowed": guarded_staging_ready,
        "staging_readiness_scope": (
            "guarded_q5e_lifecycle_readiness" if guarded_staging_ready else "not_ready"
        ),
        "guarded_postmortem_due_ready": adapter.get("guarded_postmortem_due_ready") is True,
        "guarded_postmortem_due_artifact_id": adapter.get("guarded_postmortem_due_artifact_id"),
        "guarded_postmortem_due_ref": adapter.get("guarded_postmortem_due_ref"),
        "reconciliation_ready_for_submit": False,
        "required_checks": list(EXECUTION_ADAPTER_REQUIRED_CHECKS),
        "required_check_count": len(EXECUTION_ADAPTER_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
        "blocked_reasons": blockers,
        "blocked_reason_count": len(blockers),
        "hold_reasons": sorted(dict.fromkeys(hold_reasons)),
        "hold_reason_count": len(set(hold_reasons)),
        "kill_switch_status": kill_switch["status"],
        "kill_switch_active": kill_switch["active"],
        "kill_switch_blockers": kill_switch["blockers"],
        "kill_switch_matched_scopes": kill_switch["matched_scopes"],
        "kill_switch_matched_switch_count": kill_switch.get("matched_switch_count", 0),
        "kill_switch_ledger_recorded": kill_switch["ledger_recorded"],
        "kill_switch_validation_error_count": kill_switch["validation_error_count"],
        "reconciliation_prerequisites": list(EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES),
        "reconciliation_prerequisite_count": len(EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES),
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "risk_approval_allowed": False,
        "risk_agent_handoff_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "execution_adapter_write_authority": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "staged_paper_order_allowed": False,
        "staged_order_created": False,
        "paper_order_submission_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "broker_submit_receipt_created": False,
        "prediction_market_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
        "crypto_perps_write_allowed": False,
    }
    record["validation_errors"] = validate_phase5_execution_adapter_status(record)
    return record


def build_phase5_execution_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    records = [
        _execution_adapter_status(venue, settings=settings, generated_at=generated_at)
        for venue in execution_registry()
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    read_health_counts = Counter(str(record.get("read_health") or "unknown") for record in records)
    write_health_counts = Counter(str(record.get("write_health") or "unknown") for record in records)
    bundle = {
        "schema_version": PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION,
        "artifact_type": "phase5_execution_adapter_status_bundle",
        "artifact_id": "phase5:q5-5:execution-adapter-status",
        "phase": "Q5",
        "stage": "Q5-5",
        "status": "ok",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(EXECUTION_ADAPTER_SOURCE_REFS),
        "boundary": EXECUTION_ADAPTER_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "adapter_status_count": len(records),
        "first_release_allowed_count": sum(
            1 for record in records if record.get("first_release_allowed") is True
        ),
        "read_allowed_count": sum(
            1 for record in records if record.get("execution_adapter_read_allowed") is True
        ),
        "active_kill_switch_block_count": sum(
            1 for record in records if record.get("kill_switch_active") is True
        ),
        "downstream_staging_allowed_count": 0,
        "status_counts": dict(sorted(status_counts.items())),
        "read_health_counts": dict(sorted(read_health_counts.items())),
        "write_health_counts": dict(sorted(write_health_counts.items())),
        "required_check_count": len(EXECUTION_ADAPTER_REQUIRED_CHECKS),
        "reconciliation_prerequisite_count": len(EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES),
        "statuses": records,
    }
    bundle["downstream_staging_allowed_count"] = sum(
        1 for record in records if record.get("downstream_staging_allowed") is True
    )
    for field in EXECUTION_ADAPTER_COUNT_FIELDS:
        bundle[field] = 0
    bundle["validation_errors"] = validate_phase5_execution_adapter_status_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _status_consistency_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = str(record.get("status") or "missing")
    blockers = record.get("blocked_reasons", [])
    hold_reasons = record.get("hold_reasons", [])
    if not isinstance(blockers, list):
        errors.append("blocked_reasons_not_list")
        blockers = []
    if not isinstance(hold_reasons, list):
        errors.append("hold_reasons_not_list")
        hold_reasons = []
    if record.get("blocked_reason_count") != len(blockers):
        errors.append("blocked_reason_count_mismatch")
    if record.get("hold_reason_count") != len(set(hold_reasons)):
        errors.append("hold_reason_count_mismatch")
    if record.get("kill_switch_active") is True and status != "blocked":
        errors.append("active_kill_switch_not_blocking")
    if record.get("kill_switch_active") is True and record.get("downstream_staging_allowed") is not False:
        errors.append("active_kill_switch_allows_downstream_staging")
    if status == "blocked" and not blockers:
        errors.append("blocked_status_without_reasons")
    if status == "eligible":
        if blockers:
            errors.append("eligible_status_has_blockers")
        if record.get("degraded") is True:
            errors.append("eligible_status_degraded")
        if record.get("kill_switch_active") is True:
            errors.append("eligible_status_with_active_kill_switch")
    if str(record.get("endpoint_classification") or "") == "live_endpoint":
        if status != "blocked":
            errors.append("live_endpoint_not_blocked")
        if record.get("live_endpoint_allowed") is not False:
            errors.append("live_endpoint_allowed")
    if record.get("venue_key") == "alpaca_paper" and (
        record.get("credentials_configured") is not True
        or record.get("credential_status") != "configured"
    ):
        if status != "blocked":
            errors.append("missing_credentials_not_blocking")
        if record.get("downstream_staging_allowed") is not False:
            errors.append("missing_credentials_allows_downstream_staging")
    if record.get("account_mode") not in {"paper", "paper_or_read_only_first", "delegated_subaccount_required"}:
        if record.get("venue_key") == "alpaca_paper" and status != "blocked":
            errors.append("wrong_account_mode_not_blocking")
    if record.get("degraded") is True and record.get("downstream_staging_allowed") is not False:
        errors.append("degraded_venue_allows_downstream_staging")
    if not str(record.get("write_health") or "").startswith("blocked"):
        errors.append("write_health_not_blocked")
    if record.get("reconciliation_ready_for_submit") is not False:
        errors.append("reconciliation_ready_before_submit_gate")
    return errors


def _guarded_downstream_staging_ready(record: dict[str, Any]) -> bool:
    return (
        record.get("venue_key") == "alpaca_paper"
        and record.get("downstream_staging_allowed") is True
        and record.get("staging_readiness_scope") == "guarded_q5e_lifecycle_readiness"
        and record.get("guarded_postmortem_due_ready") is True
        and record.get("status") == "eligible"
        and record.get("degraded") is False
        and record.get("kill_switch_active") is False
        and record.get("execution_adapter_read_allowed") is True
        and record.get("read_health") == "read_only_available"
        and str(record.get("write_health") or "").startswith("blocked")
    )


def validate_phase5_execution_adapter_status(record: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-5"))
    if record.get("artifact_type") != "execution_adapter_status":
        errors.append("artifact_type_not_execution_adapter_status")
    if record.get("execution_adapter_schema_version") != PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION:
        errors.append("execution_adapter_schema_version_mismatch")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if record.get("public_safe") is not True:
        errors.append("adapter_status_not_public_safe")
    for exposure in ("secret_value_exposed", "raw_payload_exposed", "local_path_exposed", "base_url_exposed"):
        if record.get(exposure) is not False:
            errors.append(f"adapter_status_exposure_enabled:{exposure}")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("checks_not_list")
        checks = []
    if record.get("required_check_count") != len(EXECUTION_ADAPTER_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    check_names = {str(check.get("name") or "") for check in checks if isinstance(check, dict)}
    for check_name in EXECUTION_ADAPTER_REQUIRED_CHECKS:
        if check_name not in check_names:
            errors.append(f"required_check_missing:{check_name}")
    if record.get("reconciliation_prerequisite_count") != len(
        EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES
    ):
        errors.append("reconciliation_prerequisite_count_mismatch")
    if set(record.get("reconciliation_prerequisites", [])) != set(
        EXECUTION_ADAPTER_RECONCILIATION_PREREQUISITES
    ):
        errors.append("reconciliation_prerequisites_mismatch")
    guarded_downstream_ready = _guarded_downstream_staging_ready(record)
    for field in EXECUTION_ADAPTER_BOUNDARY_FIELDS:
        if field == "downstream_staging_allowed" and guarded_downstream_ready:
            continue
        if record.get(field) is not False:
            errors.append(f"execution_adapter_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    errors.extend(_status_consistency_errors(record))
    return sorted(set(errors))


def validate_phase5_execution_adapter_status_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "adapter_status_count",
        "read_allowed_count",
        "downstream_staging_allowed_count",
        "statuses",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_execution_adapter_status_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-5":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    statuses = bundle.get("statuses", [])
    if not isinstance(statuses, list):
        errors.append("statuses_not_list")
        statuses = []
    if bundle.get("adapter_status_count") != len(statuses):
        errors.append("adapter_status_count_mismatch")
    if bundle.get("read_allowed_count") != sum(
        1 for record in statuses if record.get("execution_adapter_read_allowed") is True
    ):
        errors.append("read_allowed_count_mismatch")
    downstream_staging_count = sum(
        1
        for record in statuses
        if isinstance(record, dict) and record.get("downstream_staging_allowed") is True
    )
    if bundle.get("downstream_staging_allowed_count") != downstream_staging_count:
        errors.append("downstream_staging_allowed_count_mismatch")
    if downstream_staging_count > 1:
        errors.append("downstream_staging_allowed_count_too_high")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(statuses):
            errors.append("bundle_event_log_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in EXECUTION_ADAPTER_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for record in statuses:
        if not isinstance(record, dict):
            errors.append("adapter_status_not_dict")
            continue
        errors.extend(validate_phase5_execution_adapter_status(record))
    return sorted(set(errors))


def attach_phase5_execution_adapter_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / EXECUTION_ADAPTER_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("statuses", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            EXECUTION_ADAPTER_EVENT_TYPE,
            EXECUTION_ADAPTER_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "venue_key": record.get("venue_key"),
                "adapter_key": record.get("adapter_key"),
                "status": record.get("status"),
                "read_health": record.get("read_health"),
                "write_health": record.get("write_health"),
                "kill_switch_status": record.get("kill_switch_status"),
                "downstream_staging_allowed": record.get("downstream_staging_allowed"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "prediction_market_write_allowed": record.get("prediction_market_write_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_execution_adapter_status(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_execution_adapter_status_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_execution_adapter_status_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
        runtime / EXECUTION_ADAPTER_HISTORY,
        runtime / EXECUTION_ADAPTER_EVENT_LOG,
    )


def write_phase5_execution_adapter_status(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_execution_adapter_status_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_execution_adapter_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_execution_adapter_status_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_execution_adapter_status_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "adapter_status_count": output.get("adapter_status_count"),
        "read_allowed_count": output.get("read_allowed_count"),
        "downstream_staging_allowed_count": output.get("downstream_staging_allowed_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
