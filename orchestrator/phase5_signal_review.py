"""Q5-12 Signal Review UI and governance action contract.

This module assembles the public-safe decision chain shown in the cockpit. It
links each proposed signal back to backend Layer B artifacts and records
governance comments / kill-switch action intents as Event Log entries only. It
cannot approve trades, place orders, mutate kill switches, write brokers, or
enable live capital.
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
from orchestrator.phase5_alpaca_paper_dry_run import ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT
from orchestrator.phase5_approval_policy import (
    APPROVAL_POLICY_RUNTIME_ARTIFACT,
    build_phase5_approval_policy_decisions,
    validate_phase5_approval_policy_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
)
from orchestrator.phase5_execution_adapter_status import (
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    build_phase5_kill_switch_ledger,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase5_paper_order_staging_gate,
    validate_phase5_paper_order_staging_bundle,
)
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_position_monitor import (
    POSITION_MONITOR_RUNTIME_ARTIFACT,
    build_phase5_position_monitor,
    validate_phase5_position_monitor_bundle,
)
from orchestrator.phase5_prediction_market_adapter import (
    PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
)
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from orchestrator.phase5_telegram_notifier import TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION = 1
SIGNAL_REVIEW_RUNTIME_ARTIFACT = "phase5_signal_review.json"
SIGNAL_REVIEW_HISTORY = "phase5_signal_review_history.jsonl"
SIGNAL_REVIEW_EVENT_LOG = "phase5_signal_review_events.jsonl"
SIGNAL_REVIEW_EVENT_TYPE = "phase5_signal_review_written"
SIGNAL_REVIEW_GOVERNANCE_COMMENT_EVENT_TYPE = (
    "phase5_signal_review_governance_comment_written"
)
SIGNAL_REVIEW_KILL_SWITCH_ACTION_EVENT_TYPE = (
    "phase5_signal_review_kill_switch_action_written"
)
SIGNAL_REVIEW_COMPONENT = "phase5_signal_review"

SIGNAL_REVIEW_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{APPROVAL_POLICY_RUNTIME_ARTIFACT}",
    f"data/runtime/{RISK_SIZING_RUNTIME_ARTIFACT}",
    f"data/runtime/{KILL_SWITCH_RUNTIME_ARTIFACT}",
    f"data/runtime/{EXECUTION_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_ORDER_STAGING_RUNTIME_ARTIFACT}",
    f"data/runtime/{ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT}",
    f"data/runtime/{PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT}",
    f"data/runtime/{POSITION_MONITOR_RUNTIME_ARTIFACT}",
    "data/runtime/signal_integrity_reviews.jsonl",
)

SIGNAL_REVIEW_CHAIN_STEPS: tuple[str, ...] = (
    "signal_integrity",
    "approval_policy",
    "risk_agent",
    "kill_switches",
    "source_posture",
    "venue_status",
    "staged_order_status",
    "broker_receipt",
    "position_state",
)

SIGNAL_REVIEW_REQUIRED_CHECKS: tuple[str, ...] = (
    "approval_policy_bundle_valid",
    "risk_sizing_bundle_valid",
    "kill_switch_ledger_recorded",
    "kill_switch_ledger_valid",
    "execution_adapter_bundle_valid",
    "paper_order_staging_bundle_valid",
    "paper_submit_enablement_bundle_valid",
    "position_monitor_bundle_valid",
    "decision_chain_complete",
    "decision_chain_from_backend_artifacts",
    "governance_comment_linked_to_artifact",
    "governance_comment_event_log_required",
    "kill_switch_action_available_after_q5_4",
    "kill_switch_action_event_log_only",
    "no_trade_approval_control",
    "no_order_placement_control",
    "no_position_resize_control",
    "no_position_close_control",
    "no_order_cancel_control",
    "no_broker_or_venue_write_control",
    "no_live_capital_control",
    "no_secret_or_raw_payload_exposure",
)

SIGNAL_REVIEW_BOUNDARY_FIELDS: tuple[str, ...] = (
    "trade_approval_control_enabled",
    "trade_rejection_control_enabled",
    "order_place_control_enabled",
    "order_modify_control_enabled",
    "position_resize_control_enabled",
    "position_close_control_enabled",
    "order_cancel_control_enabled",
    "governance_comment_writes_broker",
    "governance_comment_grants_authority",
    "kill_switch_mutation_authority",
    "kill_switch_action_mutates_state",
    "risk_approval_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "execution_adapter_write_authority",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "paper_order_submitted",
    "broker_write_allowed",
    "broker_post_called",
    "alpaca_post_called",
    "broker_submit_receipt_created",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "telegram_command_path_enabled",
    "position_created",
    "position_monitor_write_authority",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "source_quorum_bypass_allowed",
)

SIGNAL_REVIEW_EXPOSURE_FIELDS: tuple[str, ...] = (
    "secret_value_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
    "authorization_header_exposed",
    "account_identifier_exposed",
    "broker_order_identifier_exposed",
)

SIGNAL_REVIEW_COUNT_FIELDS: tuple[str, ...] = tuple(
    f"{field}_count" for field in SIGNAL_REVIEW_BOUNDARY_FIELDS + SIGNAL_REVIEW_EXPOSURE_FIELDS
)

SIGNAL_REVIEW_BOUNDARY = (
    "Q5-12 Signal Review is a read-only UI and governance layer. It can display "
    "backend decision truth, write governance comments, and record kill-switch "
    "action intents in the Event Log after Q5-4, but it cannot approve, reject, "
    "place, modify, resize, close, or cancel trades, cannot call brokers or "
    "venues, cannot mutate kill switches, and cannot enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-12"
    ledger["boundary"] = (
        "Q5-12 grants only Event Log recording for governance comments and "
        "kill-switch action intents. It grants no approval, order, broker, "
        "venue, kill-switch mutation, position mutation, Telegram command, or "
        "live-capital authority."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _approval_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / APPROVAL_POLICY_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_approval_policy_decisions(settings=settings), bundle is not None)


def _risk_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / RISK_SIZING_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_risk_sizing_reviews(settings=settings), bundle is not None)


def _kill_switch_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / KILL_SWITCH_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_kill_switch_ledger(settings=settings), bundle is not None)


def _execution_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / EXECUTION_ADAPTER_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_execution_adapter_status(settings=settings), bundle is not None)


def _staging_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / PAPER_ORDER_STAGING_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_paper_order_staging_gate(settings=settings), bundle is not None)


def _paper_submit_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_paper_submit_enablement_gate(settings=settings), bundle is not None)


def _position_bundle(settings: Settings | None = None) -> tuple[dict[str, Any], bool]:
    runtime_path = _runtime_dir(settings) / POSITION_MONITOR_RUNTIME_ARTIFACT
    bundle = _read_json(runtime_path)
    return (bundle or build_phase5_position_monitor(settings=settings), bundle is not None)


def _records_by_strategy(bundle: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    records = bundle.get(key, [])
    if not isinstance(records, list):
        return {}
    return {
        str(record.get("strategy_family_key") or ""): record
        for record in records
        if isinstance(record, dict) and record.get("strategy_family_key")
    }


def _statuses_by_venue(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    statuses = bundle.get("statuses", [])
    if not isinstance(statuses, list):
        return {}
    return {
        str(status.get("venue_key") or ""): status
        for status in statuses
        if isinstance(status, dict) and status.get("venue_key")
    }


def _chain_entry(
    *,
    key: str,
    label: str,
    stage: str,
    source_artifact_id: str | None,
    backend_status: str,
    detail: str,
) -> dict[str, Any]:
    source_id = source_artifact_id or f"phase5:q5-12:source-fallback:{_safe_key(key)}"
    return {
        "key": key,
        "label": label,
        "stage": stage,
        "source_artifact_id": source_id,
        "backend_status": backend_status,
        "display_status": backend_status,
        "detail": detail,
        "truth_source": "backend_runtime_artifact",
        "ui_inferred": False,
    }


def _position_chain_status(position_bundle: dict[str, Any]) -> tuple[str, str, str | None]:
    records = [
        record
        for record in position_bundle.get("records", [])
        if isinstance(record, dict)
    ]
    sentinel = next(
        (
            record
            for record in records
            if record.get("artifact_type") == "position_state"
            and record.get("position_state") == "no_submitted_paper_orders"
        ),
        records[0] if records else {},
    )
    if int(position_bundle.get("submitted_order_count", 0) or 0) == 0:
        return (
            "blocked_no_submitted_paper_orders",
            "No Q5-submitted paper order exists; position controls remain hidden.",
            sentinel.get("artifact_id"),
        )
    lifecycle = str(sentinel.get("lifecycle_state") or sentinel.get("status") or "unknown")
    return (
        lifecycle,
        f"{position_bundle.get('open_position_count', 0)} open positions mirrored.",
        sentinel.get("artifact_id"),
    )


def _kill_switch_status(
    *,
    staging_record: dict[str, Any],
    kill_bundle: dict[str, Any],
    recorded: bool,
) -> tuple[str, str]:
    if not recorded:
        return "missing_fail_closed", "Q5-4 ledger is missing; UI kill-switch actions unavailable."
    if staging_record.get("kill_switch_clear") is True:
        return "clear", "Q5-4 ledger recorded and matched scopes are clear."
    active_count = int(kill_bundle.get("active_switch_count", 0) or 0)
    return "blocked", f"{active_count} active kill-switch scopes block downstream actions."


def _governance_action(
    *,
    review_id: str,
    strategy_key: str,
    target_artifact_id: str | None,
    kill_switch_ledger_recorded: bool,
) -> dict[str, Any]:
    target = target_artifact_id or f"phase5:q5-12:missing-target:{_safe_key(strategy_key)}"
    return {
        "action_id": f"phase5:q5-12:governance-action:{_safe_key(strategy_key)}",
        "action_type": "governance_comment_and_kill_switch_intent",
        "review_id": review_id,
        "strategy_family_key": strategy_key,
        "target_artifact_id": target,
        "target_artifact_stage": "Q5-3",
        "comment_text": (
            "Q5-12 governance note: decision chain is visible from backend artifacts; "
            "no approval or order control is granted."
        ),
        "comment_state": "pending_event_log",
        "comment_event_log_required": True,
        "comment_event_log_written": False,
        "comment_event_log_correlation_id": None,
        "kill_switch_action_available": kill_switch_ledger_recorded,
        "kill_switch_action_mode": (
            "event_log_only_no_mutation"
            if kill_switch_ledger_recorded
            else "unavailable_until_q5_4_ledger_recorded"
        ),
        "target_kill_switch_scope": f"strategy_family:{strategy_key}",
        "kill_switch_action_state": "pending_event_log" if kill_switch_ledger_recorded else "unavailable",
        "kill_switch_action_event_log_required": kill_switch_ledger_recorded,
        "kill_switch_action_event_log_written": False,
        "kill_switch_action_event_log_correlation_id": None,
        "kill_switch_mutation_authority": False,
        "trade_approval_control_enabled": False,
        "order_place_control_enabled": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": (
            "Governance action writes Event Log evidence only. It cannot approve "
            "trades, place orders, mutate kill switches, write brokers, or enable live capital."
        ),
    }


def _signal_review_record(
    *,
    approval: dict[str, Any],
    risk: dict[str, Any],
    staging: dict[str, Any],
    submit: dict[str, Any],
    venue: dict[str, Any],
    position_bundle: dict[str, Any],
    kill_bundle: dict[str, Any],
    kill_switch_ledger_recorded: bool,
    backend_validation_error_count: int,
    generated_at: str,
) -> dict[str, Any]:
    strategy_key = str(approval.get("strategy_family_key") or risk.get("strategy_family_key") or "unknown")
    review_id = f"phase5:q5-12:signal-review:{_safe_key(strategy_key)}"
    signal_evidence = risk.get("signal_evidence", {}) if isinstance(risk.get("signal_evidence"), dict) else {}
    source_posture = risk.get("source_posture") or approval.get("source_posture") or phase5_source_posture()
    venue_key = str(staging.get("selected_venue") or venue.get("venue_key") or "unknown_venue")
    kill_status, kill_detail = _kill_switch_status(
        staging_record=staging,
        kill_bundle=kill_bundle,
        recorded=kill_switch_ledger_recorded,
    )
    position_status, position_detail, position_artifact_id = _position_chain_status(position_bundle)
    source_status = (
        "canonical_required_context_only"
        if source_posture.get("canonical_source_required") is True
        else "source_posture_invalid"
    )
    chain = {
        "signal_integrity": _chain_entry(
            key="signal_integrity",
            label="Signal Integrity",
            stage="Signal Integrity",
            source_artifact_id=signal_evidence.get("latest_review_id"),
            backend_status=str(signal_evidence.get("latest_review_status") or "missing"),
            detail=(
                f"{signal_evidence.get('passed_to_risk_shadow_count', 0)} passed, "
                f"{signal_evidence.get('hold_for_corroboration_count', 0)} held, "
                f"{signal_evidence.get('blocked_count', 0)} blocked."
            ),
        ),
        "approval_policy": _chain_entry(
            key="approval_policy",
            label="Approval policy",
            stage="Q5-2",
            source_artifact_id=approval.get("artifact_id"),
            backend_status=str(approval.get("status") or "missing"),
            detail=str(approval.get("policy_decision") or "missing_policy_decision"),
        ),
        "risk_agent": _chain_entry(
            key="risk_agent",
            label="Risk Agent",
            stage="Q5-3",
            source_artifact_id=risk.get("artifact_id"),
            backend_status=str(risk.get("status") or "missing"),
            detail=str(risk.get("risk_decision") or "missing_risk_decision"),
        ),
        "kill_switches": _chain_entry(
            key="kill_switches",
            label="Kill switches",
            stage="Q5-4",
            source_artifact_id=kill_bundle.get("artifact_id"),
            backend_status=kill_status,
            detail=kill_detail,
        ),
        "source_posture": _chain_entry(
            key="source_posture",
            label="Source posture",
            stage="Q5 source posture",
            source_artifact_id=risk.get("artifact_id") or approval.get("artifact_id"),
            backend_status=source_status,
            detail=(
                "Yahoo Finance and Preference/PREF MCP remain supplemental only; "
                "canonical replayable sources are still required."
            ),
        ),
        "venue_status": _chain_entry(
            key="venue_status",
            label="Venue status",
            stage="Q5-5",
            source_artifact_id=venue.get("artifact_id"),
            backend_status=str(venue.get("status") or "missing"),
            detail=(
                f"{venue_key}: read {venue.get('read_health', 'unknown')} / "
                f"write {venue.get('write_health', 'unknown')}"
            ),
        ),
        "staged_order_status": _chain_entry(
            key="staged_order_status",
            label="Staged order status",
            stage="Q5-6",
            source_artifact_id=staging.get("artifact_id"),
            backend_status=str(staging.get("order_state") or staging.get("status") or "missing"),
            detail=f"staging_allowed={staging.get('staging_allowed') is True}",
        ),
        "broker_receipt": _chain_entry(
            key="broker_receipt",
            label="Broker receipt",
            stage="Q5-8",
            source_artifact_id=submit.get("artifact_id"),
            backend_status=str(submit.get("receipt_state") or submit.get("status") or "missing"),
            detail=(
                f"submit_path={submit.get('submit_path_key', 'missing')} / "
                f"post_called={submit.get('broker_post_called') is True}"
            ),
        ),
        "position_state": _chain_entry(
            key="position_state",
            label="Position state",
            stage="Q5-11",
            source_artifact_id=position_artifact_id,
            backend_status=position_status,
            detail=position_detail,
        ),
    }
    failed_checks = [
        step
        for step, value in chain.items()
        if value.get("backend_status") in {"missing", "source_posture_invalid", "missing_fail_closed"}
    ]
    status = "blocked" if risk.get("status") == "blocked" or staging.get("status") == "blocked" else "hold"
    action = _governance_action(
        review_id=review_id,
        strategy_key=strategy_key,
        target_artifact_id=risk.get("artifact_id") or approval.get("artifact_id"),
        kill_switch_ledger_recorded=kill_switch_ledger_recorded,
    )
    record = {
        "schema_version": PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION,
        "signal_review_schema_version": PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION,
        "artifact_type": "phase5_signal_review",
        "artifact_id": review_id,
        "phase": "Q5",
        "stage": "Q5-12",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": source_posture,
        "provenance": phase5_provenance(SIGNAL_REVIEW_SOURCE_REFS),
        "boundary": SIGNAL_REVIEW_BOUNDARY,
        **phase5_authority_defaults(),
        "strategy_family_key": strategy_key,
        "primary_instrument": str(risk.get("primary_instrument") or approval.get("primary_instrument") or "unknown"),
        "selected_venue": venue_key,
        "source_approval_policy_artifact_id": approval.get("artifact_id"),
        "source_risk_sizing_artifact_id": risk.get("artifact_id"),
        "source_staged_order_artifact_id": staging.get("artifact_id"),
        "source_submit_artifact_id": submit.get("artifact_id"),
        "source_position_artifact_id": position_artifact_id,
        "decision_chain_truth_source": "backend_runtime_artifacts",
        "backend_truth_displayed": True,
        "ui_inferred_readiness": False,
        "chain_step_count": len(chain),
        "decision_chain": chain,
        "failed_check_count": len(failed_checks) + backend_validation_error_count,
        "failed_checks": failed_checks,
        "backend_validation_error_count": backend_validation_error_count,
        "governance_action": action,
        "governance_comment_target_artifact_id": action["target_artifact_id"],
        "governance_comment_event_log_required": True,
        "governance_comment_event_log_written": False,
        "kill_switch_action_available": action["kill_switch_action_available"],
        "kill_switch_action_mode": action["kill_switch_action_mode"],
        "kill_switch_action_event_log_required": action["kill_switch_action_event_log_required"],
        "kill_switch_action_event_log_written": False,
        "trade_approval_control_enabled": False,
        "trade_rejection_control_enabled": False,
        "order_place_control_enabled": False,
        "order_modify_control_enabled": False,
        "position_resize_control_enabled": False,
        "position_close_control_enabled": False,
        "order_cancel_control_enabled": False,
        "governance_comment_writes_broker": False,
        "governance_comment_grants_authority": False,
        "kill_switch_action_mutates_state": False,
        "risk_approval_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "execution_adapter_write_authority": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "broker_submit_receipt_created": False,
        "prediction_market_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "telegram_command_path_enabled": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "source_quorum_bypass_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "account_identifier_exposed": False,
        "broker_order_identifier_exposed": False,
    }
    record["validation_errors"] = validate_phase5_signal_review_record(record)
    return record


def build_phase5_signal_review(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    approval, approval_recorded = _approval_bundle(settings)
    risk, risk_recorded = _risk_bundle(settings)
    kill_switch, kill_recorded = _kill_switch_bundle(settings)
    execution, execution_recorded = _execution_bundle(settings)
    staging, staging_recorded = _staging_bundle(settings)
    submit, submit_recorded = _paper_submit_bundle(settings)
    position, position_recorded = _position_bundle(settings)
    approval_errors = validate_phase5_approval_policy_bundle(approval)
    risk_errors = validate_phase5_risk_sizing_bundle(risk)
    kill_errors = validate_phase5_kill_switch_ledger(kill_switch)
    execution_errors = validate_phase5_execution_adapter_status_bundle(execution)
    staging_errors = validate_phase5_paper_order_staging_bundle(staging)
    submit_errors = validate_phase5_paper_submit_enablement_bundle(submit)
    position_errors = validate_phase5_position_monitor_bundle(position)
    backend_validation_error_count = sum(
        len(errors)
        for errors in (
            approval_errors,
            risk_errors,
            kill_errors,
            execution_errors,
            staging_errors,
            submit_errors,
            position_errors,
        )
    )
    risk_by_strategy = _records_by_strategy(risk, "reviews")
    staging_by_strategy = _records_by_strategy(staging, "records")
    submit_by_strategy = _records_by_strategy(submit, "records")
    venues_by_key = _statuses_by_venue(execution)
    records = []
    for approval_record in approval.get("decisions", []):
        if not isinstance(approval_record, dict):
            continue
        strategy_key = str(approval_record.get("strategy_family_key") or "")
        risk_record = risk_by_strategy.get(strategy_key, {})
        staging_record = staging_by_strategy.get(strategy_key, {})
        submit_record = submit_by_strategy.get(strategy_key, {})
        venue_key = str(staging_record.get("selected_venue") or "")
        venue_record = venues_by_key.get(venue_key, {})
        records.append(
            _signal_review_record(
                approval=approval_record,
                risk=risk_record,
                staging=staging_record,
                submit=submit_record,
                venue=venue_record,
                position_bundle=position,
                kill_bundle=kill_switch,
                kill_switch_ledger_recorded=kill_recorded,
                backend_validation_error_count=backend_validation_error_count,
                generated_at=generated_at,
            )
        )
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    chain_status_counts = Counter(
        str(step.get("backend_status") or "unknown")
        for record in records
        for step in record.get("decision_chain", {}).values()
        if isinstance(step, dict)
    )
    governance_actions = [
        record.get("governance_action")
        for record in records
        if isinstance(record.get("governance_action"), dict)
    ]
    bundle = {
        "schema_version": PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION,
        "artifact_type": "phase5_signal_review_bundle",
        "artifact_id": "phase5:q5-12:signal-review",
        "phase": "Q5",
        "stage": "Q5-12",
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
        "provenance": phase5_provenance(SIGNAL_REVIEW_SOURCE_REFS),
        "boundary": SIGNAL_REVIEW_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "required_check_count": len(SIGNAL_REVIEW_REQUIRED_CHECKS),
        "required_chain_steps": list(SIGNAL_REVIEW_CHAIN_STEPS),
        "chain_step_count": len(SIGNAL_REVIEW_CHAIN_STEPS),
        "signal_review_record_count": len(records),
        "decision_chain_count": sum(int(record.get("chain_step_count", 0) or 0) for record in records),
        "governance_action_count": len(governance_actions),
        "governance_comment_count": len(governance_actions),
        "governance_comment_event_count": 0,
        "kill_switch_action_available_count": sum(
            1 for action in governance_actions if action.get("kill_switch_action_available") is True
        ),
        "kill_switch_action_event_count": 0,
        "q5_2_approval_policy_recorded": approval_recorded,
        "q5_3_risk_sizing_recorded": risk_recorded,
        "q5_4_kill_switch_ledger_recorded": kill_recorded,
        "q5_5_execution_adapter_recorded": execution_recorded,
        "q5_6_paper_order_staging_recorded": staging_recorded,
        "q5_8_paper_submit_enablement_recorded": submit_recorded,
        "q5_11_position_monitor_recorded": position_recorded,
        "approval_policy_validation_error_count": len(approval_errors),
        "risk_sizing_validation_error_count": len(risk_errors),
        "kill_switch_validation_error_count": len(kill_errors),
        "execution_adapter_validation_error_count": len(execution_errors),
        "paper_order_staging_validation_error_count": len(staging_errors),
        "paper_submit_enablement_validation_error_count": len(submit_errors),
        "position_monitor_validation_error_count": len(position_errors),
        "backend_validation_error_count": backend_validation_error_count,
        "backend_truth_displayed_count": sum(
            1 for record in records if record.get("backend_truth_displayed") is True
        ),
        "ui_inferred_readiness_count": sum(
            1 for record in records if record.get("ui_inferred_readiness") is True
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "chain_status_counts": dict(sorted(chain_status_counts.items())),
        "records": records,
    }
    for field in SIGNAL_REVIEW_COUNT_FIELDS:
        source_field = field.removesuffix("_count")
        bundle[field] = sum(1 for record in records if record.get(source_field) is True)
    bundle["validation_errors"] = validate_phase5_signal_review_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _chain_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    chain = record.get("decision_chain", {})
    if not isinstance(chain, dict):
        return ["decision_chain_not_dict"]
    missing = sorted(set(SIGNAL_REVIEW_CHAIN_STEPS) - set(chain))
    if missing:
        errors.append("decision_chain_missing_steps:" + ",".join(missing))
    if record.get("chain_step_count") != len(chain):
        errors.append("chain_step_count_mismatch")
    for step_key in SIGNAL_REVIEW_CHAIN_STEPS:
        step = chain.get(step_key, {})
        if not isinstance(step, dict):
            errors.append(f"decision_chain_step_not_dict:{step_key}")
            continue
        if step.get("key") != step_key:
            errors.append(f"decision_chain_step_key_mismatch:{step_key}")
        if step.get("truth_source") != "backend_runtime_artifact":
            errors.append(f"decision_chain_step_not_backend_truth:{step_key}")
        if step.get("ui_inferred") is not False:
            errors.append(f"decision_chain_step_inferred:{step_key}")
        if step.get("backend_status") != step.get("display_status"):
            errors.append(f"decision_chain_display_status_mismatch:{step_key}")
        if not str(step.get("backend_status") or "").strip():
            errors.append(f"decision_chain_backend_status_missing:{step_key}")
        if not str(step.get("source_artifact_id") or "").strip():
            errors.append(f"decision_chain_source_artifact_missing:{step_key}")
    return errors


def _governance_action_errors(action: dict[str, Any], *, event_log_written: bool) -> list[str]:
    errors: list[str] = []
    if not str(action.get("target_artifact_id") or "").strip():
        errors.append("governance_action_target_missing")
    if action.get("comment_event_log_required") is not True:
        errors.append("governance_comment_event_log_not_required")
    if event_log_written:
        if action.get("comment_event_log_written") is not True:
            errors.append("governance_comment_event_log_not_written")
        if not str(action.get("comment_event_log_correlation_id") or "").strip():
            errors.append("governance_comment_event_log_correlation_missing")
        if action.get("kill_switch_action_available") is True:
            if action.get("kill_switch_action_event_log_written") is not True:
                errors.append("kill_switch_action_event_log_not_written")
            if not str(action.get("kill_switch_action_event_log_correlation_id") or "").strip():
                errors.append("kill_switch_action_event_log_correlation_missing")
    if action.get("kill_switch_action_available") is True:
        if action.get("kill_switch_action_mode") != "event_log_only_no_mutation":
            errors.append("kill_switch_action_mode_invalid")
        if action.get("kill_switch_action_event_log_required") is not True:
            errors.append("kill_switch_action_event_log_not_required")
    if action.get("kill_switch_mutation_authority") is not False:
        errors.append("kill_switch_action_mutation_authority_enabled")
    for field in (
        "trade_approval_control_enabled",
        "order_place_control_enabled",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if action.get(field) is not False:
            errors.append(f"governance_action_boundary_enabled:{field}")
    return errors


def validate_phase5_signal_review_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION:
        errors.append("signal_review_schema_version_mismatch")
    if record.get("artifact_type") != "phase5_signal_review":
        errors.append("artifact_type_not_phase5_signal_review")
    if record.get("phase") != "Q5" or record.get("stage") != "Q5-12":
        errors.append("phase_stage_mismatch")
    if record.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if record.get("backend_truth_displayed") is not True:
        errors.append("backend_truth_not_displayed")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("ui_inferred_readiness_enabled")
    source_posture = record.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("source_posture_invalid")
    else:
        if source_posture.get("canonical_source_required") is not True:
            errors.append("canonical_source_not_required")
        if source_posture.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
            errors.append("yahoo_finance_role_not_supplemental")
        if source_posture.get("preference_mcp_source_36") is not False:
            errors.append("preference_mcp_source_36")
        if source_posture.get("source_quorum_bypass_allowed") is not False:
            errors.append("source_quorum_bypass_allowed")
    provenance = record.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("provenance_invalid")
    else:
        if provenance.get("event_log_required") is not True:
            errors.append("provenance_event_log_not_required")
        for field in ("raw_secret_exposed", "raw_payload_exposed", "local_path_exposed"):
            if provenance.get(field) is not False:
                errors.append(f"provenance_exposure_enabled:{field}")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    errors.extend(_chain_errors(record))
    action = record.get("governance_action", {})
    if not isinstance(action, dict):
        errors.append("governance_action_missing")
    else:
        errors.extend(
            _governance_action_errors(
                action,
                event_log_written=record.get("event_log_written") is True,
            )
        )
        if record.get("governance_comment_target_artifact_id") != action.get("target_artifact_id"):
            errors.append("governance_comment_target_mismatch")
        if record.get("governance_comment_event_log_written") != action.get(
            "comment_event_log_written"
        ):
            errors.append("governance_comment_event_log_state_mismatch")
        if record.get("kill_switch_action_event_log_written") != action.get(
            "kill_switch_action_event_log_written"
        ):
            errors.append("kill_switch_action_event_log_state_mismatch")
    for field in SIGNAL_REVIEW_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"signal_review_boundary_enabled:{field}")
    for field in SIGNAL_REVIEW_EXPOSURE_FIELDS:
        if record.get(field) is not False:
            errors.append(f"signal_review_exposure_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    boundary = str(record.get("boundary") or "")
    if "cannot approve, reject, place, modify, resize, close, or cancel" not in boundary:
        errors.append("boundary_missing_trade_control_block")
    if "cannot call brokers or venues" not in boundary:
        errors.append("boundary_missing_broker_venue_block")
    if "cannot mutate kill switches" not in boundary:
        errors.append("boundary_missing_kill_switch_mutation_block")
    return sorted(set(errors))


def validate_phase5_signal_review_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "required_chain_steps",
        "signal_review_record_count",
        "decision_chain_count",
        "governance_action_count",
        "governance_comment_count",
        "kill_switch_action_available_count",
        "backend_truth_displayed_count",
        "ui_inferred_readiness_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_signal_review_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-12":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    if set(bundle.get("required_chain_steps", [])) != set(SIGNAL_REVIEW_CHAIN_STEPS):
        errors.append("required_chain_steps_mismatch")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("signal_review_record_count") != len(records):
        errors.append("signal_review_record_count_mismatch")
    if bundle.get("decision_chain_count") != len(records) * len(SIGNAL_REVIEW_CHAIN_STEPS):
        errors.append("decision_chain_count_mismatch")
    if bundle.get("backend_truth_displayed_count") != len(records):
        errors.append("backend_truth_displayed_count_mismatch")
    if bundle.get("ui_inferred_readiness_count") != 0:
        errors.append("ui_inferred_readiness_count_nonzero")
    if bundle.get("governance_action_count") != len(records):
        errors.append("governance_action_count_mismatch")
    if bundle.get("governance_comment_count") != len(records):
        errors.append("governance_comment_count_mismatch")
    if bundle.get("q5_4_kill_switch_ledger_recorded") is True:
        if bundle.get("kill_switch_action_available_count") != len(records):
            errors.append("kill_switch_action_available_count_mismatch")
    if bundle.get("event_log_written") is True:
        expected_event_count = (
            len(records)
            + int(bundle.get("governance_comment_event_count", 0) or 0)
            + int(bundle.get("kill_switch_action_event_count", 0) or 0)
        )
        if bundle.get("event_log_event_count") != expected_event_count:
            errors.append("bundle_event_log_count_mismatch")
        if bundle.get("governance_comment_event_count") != len(records):
            errors.append("governance_comment_event_count_mismatch")
        if bundle.get("q5_4_kill_switch_ledger_recorded") is True and bundle.get(
            "kill_switch_action_event_count"
        ) != len(records):
            errors.append("kill_switch_action_event_count_mismatch")
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
    if int(bundle.get("backend_validation_error_count", 0) or 0) != 0:
        errors.append("backend_validation_errors_present")
    for field in SIGNAL_REVIEW_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("record_not_dict")
            continue
        errors.extend(validate_phase5_signal_review_record(record))
    boundary = str(bundle.get("boundary") or "")
    if "cannot approve, reject, place, modify, resize, close, or cancel" not in boundary:
        errors.append("bundle_boundary_missing_trade_control_block")
    if "cannot call brokers or venues" not in boundary:
        errors.append("bundle_boundary_missing_broker_venue_block")
    if "cannot enable live capital" not in boundary:
        errors.append("bundle_boundary_missing_live_capital_block")
    return sorted(set(errors))


def attach_phase5_signal_review_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / SIGNAL_REVIEW_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    comment_count = 0
    kill_action_count = 0
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        review_entry = log.write(
            SIGNAL_REVIEW_EVENT_TYPE,
            SIGNAL_REVIEW_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "strategy_family_key": record.get("strategy_family_key"),
                "status": record.get("status"),
                "chain_step_count": record.get("chain_step_count"),
                "backend_truth_displayed": record.get("backend_truth_displayed"),
                "ui_inferred_readiness": record.get("ui_inferred_readiness"),
                "trade_approval_control_enabled": record.get("trade_approval_control_enabled"),
                "order_place_control_enabled": record.get("order_place_control_enabled"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = review_entry.correlation_id
        record["event_log_created_at"] = review_entry.created_at
        entries.append(review_entry)

        action = record.get("governance_action", {})
        if isinstance(action, dict):
            comment_entry = log.write(
                SIGNAL_REVIEW_GOVERNANCE_COMMENT_EVENT_TYPE,
                SIGNAL_REVIEW_COMPONENT,
                {
                    "artifact_id": action.get("action_id"),
                    "review_id": action.get("review_id"),
                    "target_artifact_id": action.get("target_artifact_id"),
                    "strategy_family_key": action.get("strategy_family_key"),
                    "comment_state": "event_log_recorded",
                    "approval_control_enabled": action.get("trade_approval_control_enabled"),
                    "order_place_control_enabled": action.get("order_place_control_enabled"),
                    "broker_write_allowed": action.get("broker_write_allowed"),
                    "live_capital_enabled": action.get("live_capital_enabled"),
                    "boundary": action.get("boundary"),
                },
            )
            action["comment_state"] = "event_log_recorded"
            action["comment_event_log_written"] = True
            action["comment_event_log_correlation_id"] = comment_entry.correlation_id
            action["comment_event_log_created_at"] = comment_entry.created_at
            record["governance_comment_event_log_written"] = True
            comment_count += 1
            entries.append(comment_entry)

            if action.get("kill_switch_action_available") is True:
                kill_entry = log.write(
                    SIGNAL_REVIEW_KILL_SWITCH_ACTION_EVENT_TYPE,
                    SIGNAL_REVIEW_COMPONENT,
                    {
                        "artifact_id": action.get("action_id"),
                        "review_id": action.get("review_id"),
                        "target_artifact_id": action.get("target_artifact_id"),
                        "target_kill_switch_scope": action.get("target_kill_switch_scope"),
                        "strategy_family_key": action.get("strategy_family_key"),
                        "action_mode": action.get("kill_switch_action_mode"),
                        "kill_switch_mutation_authority": action.get(
                            "kill_switch_mutation_authority"
                        ),
                        "broker_write_allowed": action.get("broker_write_allowed"),
                        "live_capital_enabled": action.get("live_capital_enabled"),
                        "boundary": action.get("boundary"),
                    },
                )
                action["kill_switch_action_state"] = "event_log_recorded"
                action["kill_switch_action_event_log_written"] = True
                action["kill_switch_action_event_log_correlation_id"] = kill_entry.correlation_id
                action["kill_switch_action_event_log_created_at"] = kill_entry.created_at
                record["kill_switch_action_event_log_written"] = True
                kill_action_count += 1
                entries.append(kill_entry)
        record["validation_errors"] = validate_phase5_signal_review_record(record)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["governance_comment_event_count"] = comment_count
    output["kill_switch_action_event_count"] = kill_action_count
    output["validation_errors"] = validate_phase5_signal_review_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_signal_review_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / SIGNAL_REVIEW_RUNTIME_ARTIFACT,
        runtime / SIGNAL_REVIEW_HISTORY,
        runtime / SIGNAL_REVIEW_EVENT_LOG,
    )


def write_phase5_signal_review(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_signal_review_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_signal_review_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_signal_review_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_signal_review_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "signal_review_record_count": output.get("signal_review_record_count"),
        "decision_chain_count": output.get("decision_chain_count"),
        "governance_comment_event_count": output.get("governance_comment_event_count"),
        "kill_switch_action_event_count": output.get("kill_switch_action_event_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
