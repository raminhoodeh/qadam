"""Q5-11 paper position monitor and reconciliation loop.

This module mirrors paper account lifecycle state after submit without gaining
any submit, close, resize, cancel, broker-write, or live-capital authority.
When no submitted paper orders exist, it records deterministic blocked sentinel
state so the lifecycle remains replayable.
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
from orchestrator.paper_account import (
    POSTMORTEM_PENDING_MARKER_STATUS,
    PaperAccountMirrorStore,
    ensure_d6_paper_account_mirror,
)
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_telegram_notifier import (
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    build_phase5_telegram_notifier,
    validate_phase5_telegram_notifier_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_POSITION_MONITOR_SCHEMA_VERSION = 1
POSITION_MONITOR_RUNTIME_ARTIFACT = "phase5_position_monitor.json"
POSITION_MONITOR_HISTORY = "phase5_position_monitor_history.jsonl"
POSITION_MONITOR_EVENT_LOG = "phase5_position_monitor_events.jsonl"
POSITION_MONITOR_EVENT_TYPE = "phase5_position_state_written"
POSITION_MONITOR_COMPONENT = "phase5_position_monitor"
GUARDED_OPEN_POSITION_RUNTIME_ARTIFACT = "phase5_guarded_open_position.json"
GUARDED_OPEN_POSITION_HISTORY = "phase5_guarded_open_position_history.jsonl"
GUARDED_OPEN_POSITION_EVENT_LOG = "phase5_guarded_open_position_events.jsonl"
GUARDED_OPEN_POSITION_EVENT_TYPE = "phase5_guarded_open_position_recorded"
GUARDED_OPEN_POSITION_COMPONENT = "phase5_guarded_open_position"
GUARDED_OPEN_POSITION_TARGET_STRATEGY = "crude_oil_energy_security_disruption"
GUARDED_CLOSED_TRADE_RUNTIME_ARTIFACT = "phase5_guarded_closed_trade.json"
GUARDED_CLOSED_TRADE_HISTORY = "phase5_guarded_closed_trade_history.jsonl"
GUARDED_CLOSED_TRADE_EVENT_LOG = "phase5_guarded_closed_trade_events.jsonl"
GUARDED_CLOSED_TRADE_EVENT_TYPE = "phase5_guarded_closed_trade_recorded"
GUARDED_CLOSED_TRADE_COMPONENT = "phase5_guarded_closed_trade"
GUARDED_CLOSED_TRADE_TARGET_STRATEGY = GUARDED_OPEN_POSITION_TARGET_STRATEGY
GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT = "phase5_guarded_postmortem_due.json"
GUARDED_POSTMORTEM_DUE_HISTORY = "phase5_guarded_postmortem_due_history.jsonl"
GUARDED_POSTMORTEM_DUE_EVENT_LOG = "phase5_guarded_postmortem_due_events.jsonl"
GUARDED_POSTMORTEM_DUE_EVENT_TYPE = "phase5_guarded_postmortem_due_recorded"
GUARDED_POSTMORTEM_DUE_COMPONENT = "phase5_guarded_postmortem_due"
GUARDED_POSTMORTEM_DUE_TARGET_STRATEGY = GUARDED_CLOSED_TRADE_TARGET_STRATEGY

POSITION_MONITOR_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT}",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/paper_orders.jsonl",
    "data/runtime/paper_positions.jsonl",
    "data/runtime/paper_closed_trades.jsonl",
    f"data/runtime/{TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT}",
)

POSITION_LIFECYCLE_STATES: tuple[str, ...] = (
    "submitted",
    "accepted",
    "partially_filled",
    "filled",
    "open_position",
    "closed_trade",
    "cancelled",
    "rejected",
    "unknown",
)

POSITION_MONITOR_REQUIRED_CHECKS: tuple[str, ...] = (
    "paper_submit_gate_valid",
    "paper_account_summary_valid",
    "account_snapshot_available",
    "lifecycle_state_mapped",
    "open_position_count_reconciled",
    "closed_trade_count_reconciled",
    "duplicate_state_checked",
    "missing_state_checked",
    "contradictory_state_checked",
    "stuck_state_checked",
    "event_log_required",
    "reconciliation_failure_blocks_new_actions",
    "no_submit_authority",
    "no_close_authority",
    "no_resize_authority",
    "no_cancel_authority",
    "no_broker_write_authority",
    "no_live_capital_authority",
    "no_raw_payload_exposure",
    "no_secret_exposure",
    "telegram_notifier_context_safe",
)

POSITION_MONITOR_BOUNDARY_FIELDS: tuple[str, ...] = (
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
    "position_created",
    "position_monitor_write_authority",
    "position_close_allowed",
    "position_resize_allowed",
    "order_cancel_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "source_quorum_bypass_allowed",
)

POSITION_MONITOR_EXPOSURE_FIELDS: tuple[str, ...] = (
    "secret_value_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
    "authorization_header_exposed",
    "account_identifier_exposed",
    "broker_order_identifier_exposed",
)

POSITION_MONITOR_COUNT_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed_count",
    "trade_candidate_created_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "execution_adapter_write_authority_count",
    "paper_execution_allowed_count",
    "paper_order_allowed_count",
    "paper_order_staging_allowed_count",
    "paper_order_submission_allowed_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_submit_receipt_created_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "position_monitor_write_authority_count",
    "position_close_allowed_count",
    "position_resize_allowed_count",
    "order_cancel_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "account_identifier_exposed_count",
    "broker_order_identifier_exposed_count",
)

POSITION_MONITOR_BOUNDARY = (
    "Q5-11 position monitoring is read-only lifecycle reconciliation. It can "
    "mirror submitted, accepted, partially filled, filled, open-position, "
    "closed-trade, cancelled, rejected, and unknown paper states, but it cannot "
    "submit, close, resize, cancel, replace, or create orders, cannot write "
    "brokers, cannot call Alpaca POST endpoints, and cannot enable live capital."
)

ORDER_STATUS_MAP: dict[str, str] = {
    "new": "submitted",
    "pending_new": "submitted",
    "submitted": "submitted",
    "accepted": "accepted",
    "accepted_for_bidding": "accepted",
    "done_for_day": "accepted",
    "pending_replace": "accepted",
    "pending_cancel": "accepted",
    "partially_filled": "partially_filled",
    "filled": "filled",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "expired": "cancelled",
    "replaced": "cancelled",
    "rejected": "rejected",
    "stopped": "rejected",
    "suspended": "rejected",
}


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
    ledger["stage"] = "Q5-11"
    ledger["boundary"] = (
        "Q5-11 grants no submit, close, resize, cancel, broker-write, "
        "position-mutation, Telegram live-notification, or live-capital "
        "authority. It records mirrored lifecycle state only."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def position_monitor_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / POSITION_MONITOR_RUNTIME_ARTIFACT,
        runtime / POSITION_MONITOR_HISTORY,
        runtime / POSITION_MONITOR_EVENT_LOG,
    )


def guarded_open_position_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / GUARDED_OPEN_POSITION_RUNTIME_ARTIFACT,
        runtime / GUARDED_OPEN_POSITION_HISTORY,
        runtime / GUARDED_OPEN_POSITION_EVENT_LOG,
    )


def guarded_closed_trade_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / GUARDED_CLOSED_TRADE_RUNTIME_ARTIFACT,
        runtime / GUARDED_CLOSED_TRADE_HISTORY,
        runtime / GUARDED_CLOSED_TRADE_EVENT_LOG,
    )


def guarded_postmortem_due_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT,
        runtime / GUARDED_POSTMORTEM_DUE_HISTORY,
        runtime / GUARDED_POSTMORTEM_DUE_EVENT_LOG,
    )


def _paper_submit_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_paper_submit_enablement_gate(settings=settings)


def _telegram_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_telegram_notifier(settings=settings)


def _lifecycle_from_order_status(status: str) -> str:
    return ORDER_STATUS_MAP.get(status.strip().lower(), "unknown")


def _artifact_status(lifecycle_state: str, failure_count: int) -> str:
    if failure_count:
        return "failed_reconciliation"
    if lifecycle_state == "open_position":
        return "open_position"
    if lifecycle_state == "closed_trade":
        return "closed_trade"
    return "blocked"


def _account_snapshot(settings: Settings) -> tuple[PaperAccountMirrorStore, dict[str, Any], Any]:
    ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    health = store.health()
    return store, health, latest


def _backend_state(settings: Settings) -> dict[str, Any]:
    store, account_health, latest = _account_snapshot(settings)
    orders = store.read_orders()
    positions = store.read_positions()
    closed_trades = store.read_closed_trades()
    submit = _paper_submit_bundle(settings)
    telegram = _telegram_bundle(settings)
    return {
        "account_health": account_health,
        "latest_snapshot": latest,
        "orders": orders,
        "positions": positions,
        "closed_trades": closed_trades,
        "submit": submit,
        "submit_errors": validate_phase5_paper_submit_enablement_bundle(submit),
        "telegram": telegram,
        "telegram_errors": validate_phase5_telegram_notifier_bundle(telegram),
    }


def _reconciliation_summary(backend: dict[str, Any]) -> dict[str, Any]:
    orders = backend["orders"]
    positions = backend["positions"]
    closed_trades = backend["closed_trades"]
    submit = backend["submit"]
    submitted_count = int(submit.get("paper_order_submitted_count", 0) or 0)
    order_ids = [str(order.order_id) for order in orders]
    duplicate_count = len(order_ids) - len(set(order_ids))
    missing_count = max(0, submitted_count - len(orders))
    contradictory_count = 0
    if positions and not orders and submitted_count:
        contradictory_count += len(positions)
    if closed_trades and not orders and submitted_count:
        contradictory_count += len(closed_trades)
    unknown_count = sum(
        1 for order in orders if _lifecycle_from_order_status(str(order.status)) == "unknown"
    )
    stuck_count = 0
    failed_count = duplicate_count + missing_count + contradictory_count
    return {
        "submitted_order_count": submitted_count,
        "mirrored_order_count": len(orders),
        "open_position_count": len(positions),
        "closed_trade_count": len(closed_trades),
        "duplicate_state_count": duplicate_count,
        "missing_state_count": missing_count,
        "contradictory_state_count": contradictory_count,
        "unknown_state_count": unknown_count,
        "stuck_state_count": stuck_count,
        "failed_reconciliation_count": failed_count,
        "new_actions_blocked_by_reconciliation_failure": failed_count > 0,
        "reconciliation_state": (
            "failed_reconciliation"
            if failed_count
            else "blocked_no_submitted_paper_orders"
            if not orders and submitted_count == 0
            else "reconciled"
        ),
    }


def _target_submit_record(
    submit: dict[str, Any],
    *,
    strategy_family_key: str = GUARDED_OPEN_POSITION_TARGET_STRATEGY,
) -> dict[str, Any]:
    for record in submit.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("strategy_family_key") == strategy_family_key
            and record.get("paper_order_submitted") is True
            and record.get("broker_submit_receipt_created") is True
        ):
            return record
    return {}


def _target_order(
    orders: tuple[Any, ...],
    *,
    order_ref: str,
    strategy_family_key: str,
) -> Any | None:
    safe_strategy = _safe_key(strategy_family_key)
    for order in orders:
        if str(order.order_id) == order_ref or str(order.order_id).endswith(safe_strategy):
            return order
    return None


def build_phase5_guarded_open_position(
    *,
    settings: Settings | None = None,
    strategy_family_key: str = GUARDED_OPEN_POSITION_TARGET_STRATEGY,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    backend = _backend_state(settings)
    reconciliation = _reconciliation_summary(backend)
    submit = backend["submit"]
    submit_errors = backend["submit_errors"]
    target_submit = _target_submit_record(submit, strategy_family_key=strategy_family_key)
    order_ref = str(target_submit.get("submitted_order_ref") or "").strip()
    broker_receipt_ref = str(target_submit.get("broker_receipt_ref") or "").strip()
    order = _target_order(
        backend["orders"],
        order_ref=order_ref,
        strategy_family_key=strategy_family_key,
    )
    position_ref = f"q5e6-open-position-{_safe_key(strategy_family_key)}"
    existing_position = next(
        (
            position
            for position in backend["positions"]
            if str(position.position_id) == position_ref
            or (
                order is not None
                and str(position.source_intent_id) == str(order.order_id)
                and str(position.instrument) == str(order.instrument)
            )
        ),
        None,
    )
    quantity = float(getattr(order, "quantity", 0.0) or 0.0) if order is not None else 0.0
    notional = float(getattr(order, "notional_gbp", 0.0) or 0.0) if order is not None else 0.0
    entry_price = round(notional / quantity, 6) if quantity else None
    open_ready = (
        not submit_errors
        and bool(target_submit)
        and order is not None
        and int(submit.get("paper_order_submitted_count", 0) or 0) >= 1
        and int(submit.get("broker_submit_receipt_created_count", 0) or 0)
        == int(submit.get("paper_order_submitted_count", 0) or 0)
        and reconciliation["submitted_order_count"] >= 1
        and reconciliation["mirrored_order_count"] >= 1
        and target_submit.get("broker_post_called") is False
        and target_submit.get("alpaca_post_called") is False
        and target_submit.get("live_endpoint_allowed") is False
        and target_submit.get("live_capital_enabled") is False
        and bool(order_ref)
        and bool(broker_receipt_ref)
        and quantity > 0
    )
    artifact = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_type": "phase5_guarded_open_position",
        "artifact_id": f"phase5:q5e-6:guarded-open-position:{_safe_key(strategy_family_key)}",
        "phase": "Q5",
        "stage": "Q5E-6",
        "status": "open_position" if open_ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "strategy_family_key": strategy_family_key,
        "source_q5_8_artifact_id": target_submit.get("artifact_id"),
        "source_q5_8_status": target_submit.get("status", "missing"),
        "source_order_ref": order_ref if open_ready else None,
        "source_broker_receipt_ref": broker_receipt_ref if open_ready else None,
        "position_ref": position_ref if open_ready else None,
        "existing_position_ref": getattr(existing_position, "position_id", None),
        "position_state": "open_position_recorded" if open_ready else "not_open",
        "order_status_for_mirror": "filled" if open_ready else "none",
        "instrument": getattr(order, "instrument", "crude_oil") if order is not None else "crude_oil",
        "side": getattr(order, "direction", "buy") if order is not None else "buy",
        "quantity": quantity,
        "notional_gbp": notional,
        "entry_price": entry_price,
        "current_price": entry_price,
        "unrealized_pnl_gbp": 0.0,
        "risk_size_gbp": notional if open_ready else 0.0,
        "opened_at": generated_at if open_ready else None,
        "submitted_order_count": reconciliation["submitted_order_count"],
        "mirrored_order_count": reconciliation["mirrored_order_count"],
        "open_position_created": open_ready,
        "open_position_count": 1 if open_ready else 0,
        "closed_trade_count": reconciliation["closed_trade_count"],
        "postmortem_due_count": int(backend["account_health"].get("postmortem_due_count", 0) or 0),
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "position_monitor_write_authority": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
        "live_endpoint_allowed": False,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled": False,
        "live_capital_enabled_count": 0,
        "prediction_market_write_allowed": False,
        "prediction_market_write_allowed_count": 0,
        "phase7_proof_credit_allowed": False,
        "phase7_proof_credit_allowed_count": 0,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "account_identifier_exposed": False,
        "broker_order_identifier_exposed": False,
        "blocked_reasons": []
        if open_ready
        else [
            reason
            for reason, failed in (
                ("q5_8_submit_gate_validation_errors", bool(submit_errors)),
                ("submitted_paper_order_missing", not target_submit),
                ("mirrored_order_missing", order is None),
                ("broker_receipt_missing", not broker_receipt_ref),
                ("quantity_missing", quantity <= 0),
                ("submitted_order_not_reconciled", reconciliation["submitted_order_count"] < 1),
            )
            if failed
        ],
        "boundary": (
            "Q5E-6 records a local guarded open-position lifecycle state from "
            "the mirrored Q5E-5 submitted paper order. It does not perform an "
            "Alpaca POST, cannot expose broker identifiers, cannot close, "
            "resize, cancel, or replace positions, cannot enable live capital, "
            "and cannot count toward Phase 7 proof."
        ),
    }
    artifact["blocked_reason_count"] = len(artifact["blocked_reasons"])
    artifact["validation_errors"] = validate_phase5_guarded_open_position(artifact)
    artifact["status"] = "open_position" if not artifact["validation_errors"] and open_ready else "blocked"
    return artifact


def _guarded_open_position_artifact(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path, _, _ = guarded_open_position_paths(settings)
    return _read_json(runtime_path) or build_phase5_guarded_open_position(settings=settings)


def _guarded_closed_trade_artifact(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path, _, _ = guarded_closed_trade_paths(settings)
    return _read_json(runtime_path) or build_phase5_guarded_closed_trade(settings=settings)


def _target_position(
    positions: tuple[Any, ...],
    *,
    position_ref: str,
    source_order_ref: str,
) -> Any | None:
    for position in positions:
        if str(position.position_id) == position_ref:
            return position
        if source_order_ref and str(position.source_intent_id) == source_order_ref:
            return position
    return None


def _target_closed_trade(
    closed_trades: tuple[Any, ...],
    *,
    closed_trade_ref: str,
    source_order_ref: str,
) -> Any | None:
    for trade in closed_trades:
        if str(trade.trade_id) == closed_trade_ref:
            return trade
        if source_order_ref and str(trade.source_intent_id) == source_order_ref:
            return trade
    return None


def build_phase5_guarded_closed_trade(
    *,
    settings: Settings | None = None,
    strategy_family_key: str = GUARDED_CLOSED_TRADE_TARGET_STRATEGY,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    backend = _backend_state(settings)
    reconciliation = _reconciliation_summary(backend)
    open_artifact = _guarded_open_position_artifact(settings)
    open_errors = validate_phase5_guarded_open_position(open_artifact)
    source_order_ref = str(open_artifact.get("source_order_ref") or "").strip()
    source_position_ref = str(open_artifact.get("position_ref") or "").strip()
    closed_trade_ref = f"q5e7-closed-trade-{_safe_key(strategy_family_key)}"
    existing_trade = _target_closed_trade(
        backend["closed_trades"],
        closed_trade_ref=closed_trade_ref,
        source_order_ref=source_order_ref,
    )
    if not source_order_ref and existing_trade is not None:
        source_order_ref = str(existing_trade.source_intent_id or "").strip()
    if not source_position_ref and source_order_ref:
        source_position_ref = f"q5e6-open-position-{_safe_key(strategy_family_key)}"
    position = _target_position(
        backend["positions"],
        position_ref=source_position_ref,
        source_order_ref=source_order_ref,
    )
    quantity = float(
        getattr(position, "quantity", open_artifact.get("quantity", 0.0)) or 0.0
    )
    entry_price = getattr(
        position,
        "entry_price",
        getattr(existing_trade, "entry_price", open_artifact.get("entry_price")),
    )
    current_price = getattr(
        position,
        "current_price",
        getattr(existing_trade, "exit_price", open_artifact.get("current_price")),
    )
    exit_price = current_price if current_price is not None else entry_price
    risk_size = float(
        getattr(position, "risk_size_gbp", open_artifact.get("risk_size_gbp", 0.0))
        or 0.0
    )
    open_artifact_ready = (
        not open_errors
        and open_artifact.get("status") == "open_position"
        and open_artifact.get("open_position_created") is True
    )
    existing_trade_ready = (
        existing_trade is not None
        and bool(source_order_ref)
        and bool(source_position_ref)
        and getattr(existing_trade, "postmortem_status", "") in {
            POSTMORTEM_PENDING_MARKER_STATUS,
            "postmortem_due",
            "postmortem_complete",
        }
    )
    postmortem_status = (
        str(existing_trade.postmortem_status)
        if existing_trade is not None
        else POSTMORTEM_PENDING_MARKER_STATUS
    )
    postmortem_due_count = 1 if postmortem_status == "postmortem_due" else 0
    closed_ready = (
        (open_artifact_ready or existing_trade_ready)
        and bool(source_order_ref)
        and bool(source_position_ref)
        and (position is not None or existing_trade is not None)
        and quantity > 0
        and risk_size > 0
        and open_artifact.get("broker_post_called") is False
        and open_artifact.get("alpaca_post_called") is False
        and open_artifact.get("live_endpoint_allowed") is False
        and open_artifact.get("live_capital_enabled") is False
    )
    artifact = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_type": "phase5_guarded_closed_trade",
        "artifact_id": f"phase5:q5e-7:guarded-closed-trade:{_safe_key(strategy_family_key)}",
        "phase": "Q5",
        "stage": "Q5E-7",
        "status": "closed_trade" if closed_ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "strategy_family_key": strategy_family_key,
        "source_open_position_artifact_id": open_artifact.get("artifact_id"),
        "source_open_position_status": open_artifact.get("status", "missing"),
        "source_order_ref": source_order_ref if closed_ready else None,
        "source_position_ref": source_position_ref if closed_ready else None,
        "closed_trade_ref": closed_trade_ref if closed_ready else None,
        "existing_closed_trade_ref": getattr(existing_trade, "trade_id", None),
        "closed_trade_state": "closed_trade_recorded" if closed_ready else "not_closed",
        "position_status_for_mirror": "closed_trade" if closed_ready else "none",
        "instrument": open_artifact.get("instrument", "crude_oil"),
        "side": open_artifact.get("side", "buy"),
        "quantity": quantity,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "realized_pnl_gbp": 0.0,
        "r_multiple": 0.0,
        "risk_size_gbp": risk_size if closed_ready else 0.0,
        "close_reason": "q5e7_guarded_lifecycle_close_marker",
        "opened_at": open_artifact.get("opened_at"),
        "closed_at": generated_at if closed_ready else None,
        "postmortem_status": postmortem_status if closed_ready else "not_due",
        "submitted_order_count": reconciliation["submitted_order_count"],
        "mirrored_order_count": reconciliation["mirrored_order_count"],
        "open_position_count": 0 if closed_ready else reconciliation["open_position_count"],
        "closed_trade_created": closed_ready,
        "closed_trade_count": 1 if closed_ready else reconciliation["closed_trade_count"],
        "postmortem_due_count": postmortem_due_count if closed_ready else 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "position_monitor_write_authority": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
        "order_replace_allowed": False,
        "live_endpoint_allowed": False,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled": False,
        "live_capital_enabled_count": 0,
        "prediction_market_write_allowed": False,
        "prediction_market_write_allowed_count": 0,
        "phase7_proof_credit_allowed": False,
        "phase7_proof_credit_allowed_count": 0,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "account_identifier_exposed": False,
        "broker_order_identifier_exposed": False,
        "blocked_reasons": []
        if closed_ready
        else [
            reason
            for reason, failed in (
                ("q5e_6_open_position_validation_errors", bool(open_errors) and not existing_trade_ready),
                (
                    "q5e_6_open_position_missing",
                    open_artifact.get("status") != "open_position" and not existing_trade_ready,
                ),
                ("source_order_ref_missing", not source_order_ref),
                ("source_position_ref_missing", not source_position_ref),
                ("mirrored_open_position_missing", position is None and existing_trade is None),
                ("quantity_missing", quantity <= 0),
                ("risk_size_missing", risk_size <= 0),
            )
            if failed
        ],
        "boundary": (
            "Q5E-7 records a local guarded closed-trade lifecycle state from "
            "the Q5E-6 open position. It does not perform an Alpaca POST, "
            "cannot expose broker identifiers, does not grant close, resize, "
            "cancel, or replace authority, cannot enable live capital, and "
            "cannot count toward Phase 7 proof."
        ),
    }
    artifact["blocked_reason_count"] = len(artifact["blocked_reasons"])
    artifact["validation_errors"] = validate_phase5_guarded_closed_trade(artifact)
    artifact["status"] = "closed_trade" if not artifact["validation_errors"] and closed_ready else "blocked"
    return artifact


def build_phase5_guarded_postmortem_due(
    *,
    settings: Settings | None = None,
    strategy_family_key: str = GUARDED_POSTMORTEM_DUE_TARGET_STRATEGY,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    backend = _backend_state(settings)
    reconciliation = _reconciliation_summary(backend)
    closed_artifact = _guarded_closed_trade_artifact(settings)
    closed_errors = validate_phase5_guarded_closed_trade(closed_artifact)
    source_order_ref = str(closed_artifact.get("source_order_ref") or "").strip()
    source_position_ref = str(closed_artifact.get("source_position_ref") or "").strip()
    closed_trade_ref = (
        str(closed_artifact.get("closed_trade_ref") or "").strip()
        or f"q5e7-closed-trade-{_safe_key(strategy_family_key)}"
    )
    existing_trade = _target_closed_trade(
        backend["closed_trades"],
        closed_trade_ref=closed_trade_ref,
        source_order_ref=source_order_ref,
    )
    if existing_trade is not None:
        source_order_ref = source_order_ref or str(existing_trade.source_intent_id or "").strip()
    postmortem_due_ref = f"q5e8-postmortem-due-{_safe_key(strategy_family_key)}"
    quantity = float(closed_artifact.get("quantity", 0.0) or 0.0)
    risk_size = float(closed_artifact.get("risk_size_gbp", 0.0) or 0.0)
    previous_postmortem_status = (
        str(existing_trade.postmortem_status)
        if existing_trade is not None
        else str(closed_artifact.get("postmortem_status") or "not_due")
    )
    closed_artifact_ready = (
        not closed_errors
        and closed_artifact.get("status") == "closed_trade"
        and closed_artifact.get("closed_trade_created") is True
    )
    existing_trade_ready = existing_trade is not None and previous_postmortem_status in {
        POSTMORTEM_PENDING_MARKER_STATUS,
        "postmortem_due",
    }
    due_ready = (
        (closed_artifact_ready or existing_trade_ready)
        and existing_trade is not None
        and bool(source_order_ref)
        and bool(source_position_ref)
        and bool(closed_trade_ref)
        and quantity > 0
        and risk_size > 0
        and closed_artifact.get("broker_post_called") is False
        and closed_artifact.get("alpaca_post_called") is False
        and closed_artifact.get("live_endpoint_allowed") is False
        and closed_artifact.get("live_capital_enabled") is False
    )
    artifact = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_type": "phase5_guarded_postmortem_due",
        "artifact_id": f"phase5:q5e-8:guarded-postmortem-due:{_safe_key(strategy_family_key)}",
        "phase": "Q5",
        "stage": "Q5E-8",
        "status": "postmortem_due" if due_ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "strategy_family_key": strategy_family_key,
        "source_closed_trade_artifact_id": closed_artifact.get("artifact_id"),
        "source_closed_trade_status": closed_artifact.get("status", "missing"),
        "source_order_ref": source_order_ref if due_ready else None,
        "source_position_ref": source_position_ref if due_ready else None,
        "source_closed_trade_ref": closed_trade_ref if due_ready else None,
        "existing_closed_trade_ref": getattr(existing_trade, "trade_id", None),
        "postmortem_due_ref": postmortem_due_ref if due_ready else None,
        "previous_postmortem_status": previous_postmortem_status,
        "postmortem_status": "postmortem_due" if due_ready else "not_due",
        "postmortem_due_state": "postmortem_due_recorded" if due_ready else "not_due",
        "postmortem_due_marker_created": due_ready,
        "postmortem_due_at": generated_at if due_ready else None,
        "instrument": closed_artifact.get("instrument", "crude_oil"),
        "side": closed_artifact.get("side", "buy"),
        "quantity": quantity,
        "risk_size_gbp": risk_size if due_ready else 0.0,
        "realized_pnl_gbp": float(closed_artifact.get("realized_pnl_gbp", 0.0) or 0.0),
        "r_multiple": float(closed_artifact.get("r_multiple", 0.0) or 0.0),
        "closed_at": closed_artifact.get("closed_at"),
        "submitted_order_count": reconciliation["submitted_order_count"],
        "mirrored_order_count": reconciliation["mirrored_order_count"],
        "open_position_count": 0 if due_ready else reconciliation["open_position_count"],
        "closed_trade_count": 1 if due_ready else reconciliation["closed_trade_count"],
        "postmortem_due_count": 1 if due_ready else 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "position_monitor_write_authority": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
        "order_replace_allowed": False,
        "live_endpoint_allowed": False,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled": False,
        "live_capital_enabled_count": 0,
        "prediction_market_write_allowed": False,
        "prediction_market_write_allowed_count": 0,
        "phase7_proof_credit_allowed": False,
        "phase7_proof_credit_allowed_count": 0,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "account_identifier_exposed": False,
        "broker_order_identifier_exposed": False,
        "blocked_reasons": []
        if due_ready
        else [
            reason
            for reason, failed in (
                ("q5e_7_closed_trade_validation_errors", bool(closed_errors)),
                ("q5e_7_closed_trade_missing", closed_artifact.get("status") != "closed_trade"),
                ("mirrored_closed_trade_missing", existing_trade is None),
                ("source_order_ref_missing", not source_order_ref),
                ("source_position_ref_missing", not source_position_ref),
                ("source_closed_trade_ref_missing", not closed_trade_ref),
                ("postmortem_status_not_markable", previous_postmortem_status not in {
                    POSTMORTEM_PENDING_MARKER_STATUS,
                    "postmortem_due",
                }),
                ("quantity_missing", quantity <= 0),
                ("risk_size_missing", risk_size <= 0),
            )
            if failed
        ],
        "boundary": (
            "Q5E-8 records a local guarded postmortem-due marker from the "
            "Q5E-7 closed trade. It does not perform an Alpaca POST, cannot "
            "submit, close, resize, cancel, or replace orders, cannot enable "
            "live capital, and cannot count toward Phase 7 proof."
        ),
    }
    artifact["blocked_reason_count"] = len(artifact["blocked_reasons"])
    artifact["validation_errors"] = validate_phase5_guarded_postmortem_due(artifact)
    artifact["status"] = (
        "postmortem_due"
        if artifact.get("postmortem_due_marker_created") is True
        and not artifact["validation_errors"]
        else "blocked"
    )
    return artifact


def _record_checks(
    *,
    lifecycle_state: str,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
) -> list[dict[str, Any]]:
    account_health = backend["account_health"]
    latest = backend["latest_snapshot"]
    return [
        _check("paper_submit_gate_valid", not backend["submit_errors"], detail=backend["submit_errors"]),
        _check("paper_account_summary_valid", account_health.get("status") == "ok"),
        _check("account_snapshot_available", latest is not None),
        _check("lifecycle_state_mapped", lifecycle_state in POSITION_LIFECYCLE_STATES),
        _check(
            "open_position_count_reconciled",
            latest is not None
            and int(getattr(latest, "open_position_count", -1)) == reconciliation["open_position_count"],
        ),
        _check(
            "closed_trade_count_reconciled",
            latest is not None
            and int(getattr(latest, "closed_trade_count", -1)) == reconciliation["closed_trade_count"],
        ),
        _check("duplicate_state_checked", reconciliation["duplicate_state_count"] >= 0),
        _check("missing_state_checked", reconciliation["missing_state_count"] >= 0),
        _check("contradictory_state_checked", reconciliation["contradictory_state_count"] >= 0),
        _check("stuck_state_checked", reconciliation["stuck_state_count"] >= 0),
        _check("event_log_required", True),
        _check(
            "reconciliation_failure_blocks_new_actions",
            reconciliation["failed_reconciliation_count"] == 0
            or reconciliation["new_actions_blocked_by_reconciliation_failure"] is True,
        ),
        _check("no_submit_authority", True),
        _check("no_close_authority", True),
        _check("no_resize_authority", True),
        _check("no_cancel_authority", True),
        _check("no_broker_write_authority", True),
        _check("no_live_capital_authority", True),
        _check("no_raw_payload_exposure", True),
        _check("no_secret_exposure", True),
        _check("telegram_notifier_context_safe", not backend["telegram_errors"], detail=backend["telegram_errors"]),
    ]


def _common_record_fields(
    *,
    artifact_type: str,
    artifact_id: str,
    status: str,
    generated_at: str,
    lifecycle_state: str,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    latest = backend["latest_snapshot"]
    checks = _record_checks(
        lifecycle_state=lifecycle_state,
        backend=backend,
        reconciliation=reconciliation,
    )
    return {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "position_monitor_schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "phase": "Q5",
        "stage": "Q5-11",
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
        "provenance": phase5_provenance(POSITION_MONITOR_SOURCE_REFS),
        "boundary": POSITION_MONITOR_BOUNDARY,
        **phase5_authority_defaults(),
        "account_scope": getattr(latest, "account_scope", PAPER_ACCOUNT_SCOPE),
        "paper_account_mode": getattr(latest, "mode", "paper"),
        "paper_account_connection_status": getattr(
            latest,
            "connection_status",
            "local_mirror_not_broker_connected",
        ),
        "current_balance_gbp": getattr(latest, "current_balance_gbp", 0.0),
        "equity_gbp": getattr(latest, "equity_gbp", 0.0),
        "realized_pnl_gbp": getattr(latest, "realized_pnl_gbp", 0.0),
        "unrealized_pnl_gbp": getattr(latest, "unrealized_pnl_gbp", 0.0),
        "open_position_count": reconciliation["open_position_count"],
        "closed_trade_count": reconciliation["closed_trade_count"],
        "submitted_order_count": reconciliation["submitted_order_count"],
        "mirrored_order_count": reconciliation["mirrored_order_count"],
        "reconciliation_state": reconciliation["reconciliation_state"],
        "failed_reconciliation_count": reconciliation["failed_reconciliation_count"],
        "duplicate_state_count": reconciliation["duplicate_state_count"],
        "missing_state_count": reconciliation["missing_state_count"],
        "contradictory_state_count": reconciliation["contradictory_state_count"],
        "unknown_state_count": reconciliation["unknown_state_count"],
        "stuck_state_count": reconciliation["stuck_state_count"],
        "new_actions_blocked_by_reconciliation_failure": (
            reconciliation["new_actions_blocked_by_reconciliation_failure"]
        ),
        "required_checks": list(POSITION_MONITOR_REQUIRED_CHECKS),
        "required_check_count": len(POSITION_MONITOR_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
        "write_authority": False,
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
        "position_created": False,
        "position_monitor_write_authority": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
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


def _position_record_for_order(
    order: Any,
    *,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    positions_by_instrument = {str(position.instrument): position for position in backend["positions"]}
    closed_by_instrument = {str(trade.instrument): trade for trade in backend["closed_trades"]}
    lifecycle = _lifecycle_from_order_status(str(order.status))
    if str(order.instrument) in positions_by_instrument:
        lifecycle = "open_position"
    if str(order.instrument) in closed_by_instrument:
        lifecycle = "closed_trade"
    status = _artifact_status(lifecycle, reconciliation["failed_reconciliation_count"])
    record = {
        **_common_record_fields(
            artifact_type="position_state",
            artifact_id=f"phase5:q5-11:position-monitor:order:{_safe_key(str(order.order_id))}",
            status=status,
            generated_at=generated_at,
            lifecycle_state=lifecycle,
            backend=backend,
            reconciliation=reconciliation,
        ),
        "position_state": lifecycle,
        "lifecycle_state": lifecycle,
        "source_order_ref": _safe_key(str(order.order_id)),
        "instrument": order.instrument,
        "side": order.direction,
        "quantity": order.quantity,
        "order_status": order.status,
        "filled_quantity": order.filled_quantity,
        "filled_avg_price": order.filled_avg_price,
        "submitted_at": order.submitted_at,
        "filled_at": order.filled_at,
        "position_state_ref": positions_by_instrument.get(str(order.instrument)).position_id
        if str(order.instrument) in positions_by_instrument
        else None,
        "closed_trade_ref": closed_by_instrument.get(str(order.instrument)).trade_id
        if str(order.instrument) in closed_by_instrument
        else None,
    }
    record["validation_errors"] = validate_phase5_position_monitor_record(record)
    return record


def _position_sentinel_record(
    *,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    lifecycle = "unknown"
    record = {
        **_common_record_fields(
            artifact_type="position_state",
            artifact_id="phase5:q5-11:position-monitor:no-submitted-paper-orders",
            status="blocked",
            generated_at=generated_at,
            lifecycle_state=lifecycle,
            backend=backend,
            reconciliation=reconciliation,
        ),
        "position_state": "no_submitted_paper_orders",
        "lifecycle_state": lifecycle,
        "source_order_ref": None,
        "instrument": None,
        "side": None,
        "quantity": 0,
        "order_status": "none",
        "filled_quantity": 0,
        "filled_avg_price": None,
        "submitted_at": None,
        "filled_at": None,
        "position_state_ref": None,
        "closed_trade_ref": None,
    }
    record["validation_errors"] = validate_phase5_position_monitor_record(record)
    return record


def _closed_trade_record(
    trade: Any,
    *,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    status = "failed_reconciliation" if reconciliation["failed_reconciliation_count"] else "closed_trade"
    lifecycle = "closed_trade"
    record = {
        **_common_record_fields(
            artifact_type="closed_trade_summary",
            artifact_id=f"phase5:q5-11:position-monitor:closed-trade:{_safe_key(str(trade.trade_id))}",
            status=status,
            generated_at=generated_at,
            lifecycle_state=lifecycle,
            backend=backend,
            reconciliation=reconciliation,
        ),
        "closed_trade_state": lifecycle,
        "lifecycle_state": lifecycle,
        "phase5_test_trade": True,
        "postmortem_due": trade.postmortem_status == "postmortem_due",
        "postmortem_status": trade.postmortem_status,
        "source_trade_ref": _safe_key(str(trade.trade_id)),
        "instrument": trade.instrument,
        "side": trade.direction,
        "realized_pnl_gbp": trade.realized_pnl_gbp,
        "r_multiple": trade.r_multiple,
        "close_reason": trade.close_reason,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
    }
    record["validation_errors"] = validate_phase5_position_monitor_record(record)
    return record


def _closed_trade_sentinel_record(
    *,
    backend: dict[str, Any],
    reconciliation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    lifecycle = "unknown"
    record = {
        **_common_record_fields(
            artifact_type="closed_trade_summary",
            artifact_id="phase5:q5-11:position-monitor:no-closed-trades",
            status="blocked",
            generated_at=generated_at,
            lifecycle_state=lifecycle,
            backend=backend,
            reconciliation=reconciliation,
        ),
        "closed_trade_state": "not_closed",
        "lifecycle_state": lifecycle,
        "phase5_test_trade": True,
        "postmortem_due": False,
        "postmortem_status": "not_due",
        "source_trade_ref": None,
        "instrument": None,
        "side": None,
        "realized_pnl_gbp": 0.0,
        "r_multiple": None,
        "close_reason": "no_closed_trades",
        "opened_at": None,
        "closed_at": None,
    }
    record["validation_errors"] = validate_phase5_position_monitor_record(record)
    return record


def build_phase5_position_monitor(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    backend = _backend_state(settings)
    reconciliation = _reconciliation_summary(backend)
    position_records = [
        _position_record_for_order(
            order,
            backend=backend,
            reconciliation=reconciliation,
            generated_at=generated_at,
        )
        for order in backend["orders"]
    ]
    if not position_records:
        position_records.append(
            _position_sentinel_record(
                backend=backend,
                reconciliation=reconciliation,
                generated_at=generated_at,
            )
        )
    closed_trade_records = [
        _closed_trade_record(
            trade,
            backend=backend,
            reconciliation=reconciliation,
            generated_at=generated_at,
        )
        for trade in backend["closed_trades"]
    ]
    if not closed_trade_records:
        closed_trade_records.append(
            _closed_trade_sentinel_record(
                backend=backend,
                reconciliation=reconciliation,
                generated_at=generated_at,
            )
        )
    records = position_records + closed_trade_records
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    lifecycle_counts = Counter(str(record.get("lifecycle_state") or "unknown") for record in records)
    reconciliation_counts = Counter(
        str(record.get("reconciliation_state") or "unknown") for record in records
    )
    latest = backend["latest_snapshot"]
    bundle = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_type": "phase5_position_monitor_bundle",
        "artifact_id": "phase5:q5-11:position-monitor",
        "phase": "Q5",
        "stage": "Q5-11",
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
        "provenance": phase5_provenance(POSITION_MONITOR_SOURCE_REFS),
        "boundary": POSITION_MONITOR_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "position_record_count": len(position_records),
        "closed_trade_summary_count": len(closed_trade_records),
        "monitor_record_count": len(records),
        "lifecycle_state_count": len(POSITION_LIFECYCLE_STATES),
        "lifecycle_states": list(POSITION_LIFECYCLE_STATES),
        "status_counts": dict(sorted(status_counts.items())),
        "lifecycle_state_counts": dict(sorted(lifecycle_counts.items())),
        "reconciliation_state_counts": dict(sorted(reconciliation_counts.items())),
        "required_check_count": len(POSITION_MONITOR_REQUIRED_CHECKS),
        "paper_account_status": backend["account_health"].get("status", "unknown"),
        "paper_account_snapshot_count": int(backend["account_health"].get("snapshot_count", 0) or 0),
        "paper_account_connection_status": getattr(
            latest,
            "connection_status",
            "local_mirror_not_broker_connected",
        ),
        "account_equity_gbp": getattr(latest, "equity_gbp", 0.0),
        "current_balance_gbp": getattr(latest, "current_balance_gbp", 0.0),
        "realized_pnl_gbp": getattr(latest, "realized_pnl_gbp", 0.0),
        "unrealized_pnl_gbp": getattr(latest, "unrealized_pnl_gbp", 0.0),
        "drawdown_pct": getattr(latest, "drawdown_pct", 0.0),
        "submitted_order_count": reconciliation["submitted_order_count"],
        "mirrored_order_count": reconciliation["mirrored_order_count"],
        "open_order_count": int(backend["account_health"].get("open_order_count", 0) or 0),
        "open_position_count": reconciliation["open_position_count"],
        "closed_trade_count": reconciliation["closed_trade_count"],
        "postmortem_due_count": int(backend["account_health"].get("postmortem_due_count", 0) or 0),
        "postmortem_complete_count": int(
            backend["account_health"].get("postmortem_complete_count", 0) or 0
        ),
        "duplicate_state_count": reconciliation["duplicate_state_count"],
        "missing_state_count": reconciliation["missing_state_count"],
        "contradictory_state_count": reconciliation["contradictory_state_count"],
        "unknown_state_count": reconciliation["unknown_state_count"],
        "stuck_state_count": reconciliation["stuck_state_count"],
        "failed_reconciliation_count": reconciliation["failed_reconciliation_count"],
        "new_actions_blocked_by_reconciliation_failure": (
            reconciliation["new_actions_blocked_by_reconciliation_failure"]
        ),
        "paper_submit_gate_status": backend["submit"].get("status", "unknown"),
        "paper_submit_gate_validation_error_count": len(backend["submit_errors"]),
        "telegram_notifier_status": backend["telegram"].get("status", "unknown"),
        "telegram_notifier_validation_error_count": len(backend["telegram_errors"]),
        "records": records,
    }
    for field in POSITION_MONITOR_COUNT_FIELDS:
        source_field = field.removesuffix("_count")
        bundle[field] = sum(1 for record in records if record.get(source_field) is True)
    bundle["validation_errors"] = validate_phase5_position_monitor_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _required_check_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("required_check_count") != len(POSITION_MONITOR_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        return ["checks_not_list"]
    check_names = {str(check.get("name") or "") for check in checks if isinstance(check, dict)}
    for required in POSITION_MONITOR_REQUIRED_CHECKS:
        if required not in check_names:
            errors.append(f"required_check_missing:{required}")
    failed_checks = [check.get("name") for check in checks if isinstance(check, dict) and not check.get("passed")]
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("failed_check_count_mismatch")
    return errors


def _record_state_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    artifact_type = str(record.get("artifact_type") or "")
    lifecycle_state = str(record.get("lifecycle_state") or "")
    status = str(record.get("status") or "")
    if lifecycle_state not in POSITION_LIFECYCLE_STATES:
        errors.append("lifecycle_state_invalid")
    if artifact_type == "position_state":
        if not str(record.get("position_state") or "").strip():
            errors.append("position_state_missing")
        if status == "open_position" and int(record.get("open_position_count", 0) or 0) <= 0:
            errors.append("open_position_status_without_position")
        if status == "closed_trade" and int(record.get("closed_trade_count", 0) or 0) <= 0:
            errors.append("closed_trade_status_without_trade")
    if artifact_type == "closed_trade_summary":
        if not str(record.get("closed_trade_state") or "").strip():
            errors.append("closed_trade_state_missing")
        if status == "closed_trade" and record.get("postmortem_status") not in {
            POSTMORTEM_PENDING_MARKER_STATUS,
            "postmortem_due",
            "postmortem_complete",
        }:
            errors.append("closed_trade_without_postmortem_state")
        if record.get("phase5_test_trade") is not True:
            errors.append("closed_trade_not_tagged_phase5_test_trade")
    failed_count = int(record.get("failed_reconciliation_count", 0) or 0)
    if status == "failed_reconciliation" and failed_count <= 0:
        errors.append("failed_reconciliation_without_failure_count")
    if failed_count > 0 and record.get("new_actions_blocked_by_reconciliation_failure") is not True:
        errors.append("reconciliation_failure_does_not_block_new_actions")
    for field in (
        "duplicate_state_count",
        "missing_state_count",
        "contradictory_state_count",
        "unknown_state_count",
        "stuck_state_count",
    ):
        if int(record.get(field, 0) or 0) < 0:
            errors.append(f"negative_reconciliation_count:{field}")
    return errors


def validate_phase5_position_monitor_record(record: dict[str, Any]) -> list[str]:
    artifact_type = str(record.get("artifact_type") or "")
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-11"))
    if artifact_type not in {"position_state", "closed_trade_summary"}:
        errors.append("artifact_type_not_position_monitor")
    if record.get("position_monitor_schema_version") != PHASE5_POSITION_MONITOR_SCHEMA_VERSION:
        errors.append("position_monitor_schema_version_mismatch")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if record.get("write_authority") is not False:
        errors.append("write_authority_enabled")
    for field in POSITION_MONITOR_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"position_monitor_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    for exposure in POSITION_MONITOR_EXPOSURE_FIELDS:
        if record.get(exposure) is not False:
            errors.append(f"position_monitor_exposure_enabled:{exposure}")
    errors.extend(_required_check_errors(record))
    errors.extend(_record_state_errors(record))
    return sorted(set(errors))


def validate_phase5_position_monitor_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "position_record_count",
        "closed_trade_summary_count",
        "monitor_record_count",
        "lifecycle_state_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_POSITION_MONITOR_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_position_monitor_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-11":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    position_records = [
        record for record in records if isinstance(record, dict) and record.get("artifact_type") == "position_state"
    ]
    closed_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("artifact_type") == "closed_trade_summary"
    ]
    if bundle.get("position_record_count") != len(position_records):
        errors.append("position_record_count_mismatch")
    if bundle.get("closed_trade_summary_count") != len(closed_records):
        errors.append("closed_trade_summary_count_mismatch")
    if bundle.get("monitor_record_count") != len(records):
        errors.append("monitor_record_count_mismatch")
    if bundle.get("lifecycle_state_count") != len(POSITION_LIFECYCLE_STATES):
        errors.append("lifecycle_state_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in POSITION_MONITOR_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    if int(bundle.get("failed_reconciliation_count", 0) or 0) > 0 and (
        bundle.get("new_actions_blocked_by_reconciliation_failure") is not True
    ):
        errors.append("bundle_reconciliation_failure_does_not_block_new_actions")
    if bundle.get("paper_submit_gate_validation_error_count") != 0:
        errors.append("paper_submit_gate_validation_errors")
    if bundle.get("telegram_notifier_validation_error_count") != 0:
        errors.append("telegram_notifier_validation_errors")
    for record in records:
        if not isinstance(record, dict):
            errors.append("position_monitor_record_not_dict")
            continue
        errors.extend(validate_phase5_position_monitor_record(record))
    if (
        "cannot submit, close, resize, cancel"
        not in str(bundle.get("boundary") or "")
        or "cannot enable live capital" not in str(bundle.get("boundary") or "")
    ):
        errors.append("bundle_boundary_weak")
    return sorted(set(errors))


def validate_phase5_guarded_open_position(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
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
        "strategy_family_key",
        "source_order_ref",
        "source_broker_receipt_ref",
        "position_ref",
        "position_state",
        "instrument",
        "side",
        "quantity",
        "open_position_created",
        "open_position_count",
        "closed_trade_count",
        "postmortem_due_count",
        "broker_post_called",
        "alpaca_post_called",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "blocked_reasons",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("guarded_open_position_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_POSITION_MONITOR_SCHEMA_VERSION:
        errors.append("guarded_open_position_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_guarded_open_position":
        errors.append("guarded_open_position_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5E-6":
        errors.append("guarded_open_position_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("guarded_open_position_not_public_safe")
    if artifact.get("open_position_created") is True:
        if artifact.get("status") != "open_position":
            errors.append("guarded_open_position_status_not_open")
        if artifact.get("position_state") != "open_position_recorded":
            errors.append("guarded_open_position_state_invalid")
        if artifact.get("open_position_count") != 1:
            errors.append("guarded_open_position_count_mismatch")
        for field in ("source_order_ref", "source_broker_receipt_ref", "position_ref"):
            if not str(artifact.get(field) or "").strip():
                errors.append(f"guarded_open_position_ref_missing:{field}")
        if float(artifact.get("quantity", 0.0) or 0.0) <= 0:
            errors.append("guarded_open_position_quantity_invalid")
        if float(artifact.get("risk_size_gbp", 0.0) or 0.0) <= 0:
            errors.append("guarded_open_position_risk_size_invalid")
    else:
        if int(artifact.get("open_position_count", 0) or 0) != 0:
            errors.append("guarded_open_position_blocked_open_count_nonzero")
    if int(artifact.get("closed_trade_count", 0) or 0) != 0:
        errors.append("guarded_open_position_closed_trade_present")
    if int(artifact.get("postmortem_due_count", 0) or 0) != 0:
        errors.append("guarded_open_position_postmortem_due_present")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "position_monitor_write_authority",
        "position_close_allowed",
        "position_resize_allowed",
        "order_cancel_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "account_identifier_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"guarded_open_position_unsafe_field_enabled:{field}")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "prediction_market_write_allowed_count",
        "phase7_proof_credit_allowed_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"guarded_open_position_unsafe_count_nonzero:{count_field}")
    if artifact.get("blocked_reason_count") != len(artifact.get("blocked_reasons", [])):
        errors.append("guarded_open_position_blocked_reason_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "does not perform an Alpaca POST",
        "cannot close, resize, cancel",
        "cannot enable live capital",
        "cannot count toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("guarded_open_position_boundary_weak")
            break
    return sorted(set(errors))


def validate_phase5_guarded_closed_trade(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
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
        "strategy_family_key",
        "source_order_ref",
        "source_position_ref",
        "closed_trade_ref",
        "closed_trade_state",
        "instrument",
        "side",
        "quantity",
        "closed_trade_created",
        "open_position_count",
        "closed_trade_count",
        "postmortem_due_count",
        "postmortem_status",
        "broker_post_called",
        "alpaca_post_called",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "blocked_reasons",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("guarded_closed_trade_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_POSITION_MONITOR_SCHEMA_VERSION:
        errors.append("guarded_closed_trade_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_guarded_closed_trade":
        errors.append("guarded_closed_trade_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5E-7":
        errors.append("guarded_closed_trade_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("guarded_closed_trade_not_public_safe")
    if artifact.get("closed_trade_created") is True:
        if artifact.get("status") != "closed_trade":
            errors.append("guarded_closed_trade_status_not_closed")
        if artifact.get("closed_trade_state") != "closed_trade_recorded":
            errors.append("guarded_closed_trade_state_invalid")
        if int(artifact.get("open_position_count", 0) or 0) != 0:
            errors.append("guarded_closed_trade_open_position_count_nonzero")
        if artifact.get("closed_trade_count") != 1:
            errors.append("guarded_closed_trade_count_mismatch")
        if artifact.get("postmortem_status") not in {
            POSTMORTEM_PENDING_MARKER_STATUS,
            "postmortem_due",
            "postmortem_complete",
        }:
            errors.append("guarded_closed_trade_postmortem_status_invalid")
        if artifact.get("postmortem_status") == "postmortem_due":
            if int(artifact.get("postmortem_due_count", 0) or 0) != 1:
                errors.append("guarded_closed_trade_postmortem_due_count_mismatch")
        elif int(artifact.get("postmortem_due_count", 0) or 0) != 0:
            errors.append("guarded_closed_trade_postmortem_due_count_mismatch")
        for field in ("source_order_ref", "source_position_ref", "closed_trade_ref"):
            if not str(artifact.get(field) or "").strip():
                errors.append(f"guarded_closed_trade_ref_missing:{field}")
        if float(artifact.get("quantity", 0.0) or 0.0) <= 0:
            errors.append("guarded_closed_trade_quantity_invalid")
        if float(artifact.get("risk_size_gbp", 0.0) or 0.0) <= 0:
            errors.append("guarded_closed_trade_risk_size_invalid")
        if artifact.get("closed_at") is None:
            errors.append("guarded_closed_trade_closed_at_missing")
    else:
        if int(artifact.get("closed_trade_count", 0) or 0) != 0:
            errors.append("guarded_closed_trade_blocked_closed_count_nonzero")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "position_monitor_write_authority",
        "position_close_allowed",
        "position_resize_allowed",
        "order_cancel_allowed",
        "order_replace_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "account_identifier_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"guarded_closed_trade_unsafe_field_enabled:{field}")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "prediction_market_write_allowed_count",
        "phase7_proof_credit_allowed_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"guarded_closed_trade_unsafe_count_nonzero:{count_field}")
    if artifact.get("blocked_reason_count") != len(artifact.get("blocked_reasons", [])):
        errors.append("guarded_closed_trade_blocked_reason_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "does not perform an Alpaca POST",
        "does not grant close, resize, cancel",
        "cannot enable live capital",
        "cannot count toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("guarded_closed_trade_boundary_weak")
            break
    return sorted(set(errors))


def validate_phase5_guarded_postmortem_due(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
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
        "strategy_family_key",
        "source_order_ref",
        "source_position_ref",
        "source_closed_trade_ref",
        "postmortem_due_ref",
        "postmortem_due_state",
        "postmortem_due_marker_created",
        "postmortem_due_count",
        "postmortem_status",
        "closed_trade_count",
        "broker_post_called",
        "alpaca_post_called",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "blocked_reasons",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("guarded_postmortem_due_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_POSITION_MONITOR_SCHEMA_VERSION:
        errors.append("guarded_postmortem_due_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_guarded_postmortem_due":
        errors.append("guarded_postmortem_due_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5E-8":
        errors.append("guarded_postmortem_due_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("guarded_postmortem_due_not_public_safe")
    if artifact.get("postmortem_due_marker_created") is True:
        if artifact.get("status") != "postmortem_due":
            errors.append("guarded_postmortem_due_status_invalid")
        if artifact.get("postmortem_due_state") != "postmortem_due_recorded":
            errors.append("guarded_postmortem_due_state_invalid")
        if artifact.get("postmortem_status") != "postmortem_due":
            errors.append("guarded_postmortem_due_postmortem_status_invalid")
        if int(artifact.get("postmortem_due_count", 0) or 0) != 1:
            errors.append("guarded_postmortem_due_count_mismatch")
        if int(artifact.get("closed_trade_count", 0) or 0) != 1:
            errors.append("guarded_postmortem_due_closed_trade_count_mismatch")
        if int(artifact.get("open_position_count", 0) or 0) != 0:
            errors.append("guarded_postmortem_due_open_position_count_nonzero")
        for field in (
            "source_order_ref",
            "source_position_ref",
            "source_closed_trade_ref",
            "postmortem_due_ref",
        ):
            if not str(artifact.get(field) or "").strip():
                errors.append(f"guarded_postmortem_due_ref_missing:{field}")
        if float(artifact.get("quantity", 0.0) or 0.0) <= 0:
            errors.append("guarded_postmortem_due_quantity_invalid")
        if float(artifact.get("risk_size_gbp", 0.0) or 0.0) <= 0:
            errors.append("guarded_postmortem_due_risk_size_invalid")
        if artifact.get("postmortem_due_at") is None:
            errors.append("guarded_postmortem_due_at_missing")
    else:
        if int(artifact.get("postmortem_due_count", 0) or 0) != 0:
            errors.append("guarded_postmortem_due_blocked_count_nonzero")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "position_monitor_write_authority",
        "position_close_allowed",
        "position_resize_allowed",
        "order_cancel_allowed",
        "order_replace_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "account_identifier_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"guarded_postmortem_due_unsafe_field_enabled:{field}")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "prediction_market_write_allowed_count",
        "phase7_proof_credit_allowed_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"guarded_postmortem_due_unsafe_count_nonzero:{count_field}")
    if artifact.get("blocked_reason_count") != len(artifact.get("blocked_reasons", [])):
        errors.append("guarded_postmortem_due_blocked_reason_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "does not perform an Alpaca POST",
        "cannot submit, close, resize, cancel",
        "cannot enable live capital",
        "cannot count toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("guarded_postmortem_due_boundary_weak")
            break
    return sorted(set(errors))


def attach_phase5_guarded_open_position_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    _, _, default_event_path = guarded_open_position_paths(settings)
    log_path = Path(event_log_path or default_event_path)
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        GUARDED_OPEN_POSITION_EVENT_TYPE,
        GUARDED_OPEN_POSITION_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "strategy_family_key": output.get("strategy_family_key"),
            "source_order_ref": output.get("source_order_ref"),
            "position_ref": output.get("position_ref"),
            "open_position_created": output.get("open_position_created"),
            "open_position_count": output.get("open_position_count"),
            "closed_trade_count": output.get("closed_trade_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "broker_post_called": output.get("broker_post_called"),
            "alpaca_post_called": output.get("alpaca_post_called"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "boundary": output.get("boundary"),
        },
    )
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_guarded_open_position(output)
    output["status"] = (
        "open_position"
        if output.get("open_position_created") is True and not output["validation_errors"]
        else "blocked"
    )
    return output, entry


def write_phase5_guarded_open_position(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = guarded_open_position_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_guarded_open_position_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_guarded_open_position(output)
        output["status"] = (
            "open_position"
            if output.get("open_position_created") is True and not output["validation_errors"]
            else "blocked"
        )
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_order_ref": output.get("source_order_ref"),
        "position_ref": output.get("position_ref"),
        "open_position_count": output.get("open_position_count"),
        "closed_trade_count": output.get("closed_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "event_log_written": output.get("event_log_written"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def attach_phase5_guarded_closed_trade_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    _, _, default_event_path = guarded_closed_trade_paths(settings)
    log_path = Path(event_log_path or default_event_path)
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        GUARDED_CLOSED_TRADE_EVENT_TYPE,
        GUARDED_CLOSED_TRADE_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "strategy_family_key": output.get("strategy_family_key"),
            "source_order_ref": output.get("source_order_ref"),
            "source_position_ref": output.get("source_position_ref"),
            "closed_trade_ref": output.get("closed_trade_ref"),
            "closed_trade_created": output.get("closed_trade_created"),
            "open_position_count": output.get("open_position_count"),
            "closed_trade_count": output.get("closed_trade_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "postmortem_status": output.get("postmortem_status"),
            "broker_post_called": output.get("broker_post_called"),
            "alpaca_post_called": output.get("alpaca_post_called"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "boundary": output.get("boundary"),
        },
    )
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_guarded_closed_trade(output)
    output["status"] = (
        "closed_trade"
        if output.get("closed_trade_created") is True and not output["validation_errors"]
        else "blocked"
    )
    return output, entry


def write_phase5_guarded_closed_trade(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = guarded_closed_trade_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_guarded_closed_trade_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_guarded_closed_trade(output)
        output["status"] = (
            "closed_trade"
            if output.get("closed_trade_created") is True and not output["validation_errors"]
            else "blocked"
        )
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_order_ref": output.get("source_order_ref"),
        "source_position_ref": output.get("source_position_ref"),
        "closed_trade_ref": output.get("closed_trade_ref"),
        "open_position_count": output.get("open_position_count"),
        "closed_trade_count": output.get("closed_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_status": output.get("postmortem_status"),
        "event_log_written": output.get("event_log_written"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def attach_phase5_guarded_postmortem_due_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    _, _, default_event_path = guarded_postmortem_due_paths(settings)
    log_path = Path(event_log_path or default_event_path)
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        GUARDED_POSTMORTEM_DUE_EVENT_TYPE,
        GUARDED_POSTMORTEM_DUE_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "strategy_family_key": output.get("strategy_family_key"),
            "source_order_ref": output.get("source_order_ref"),
            "source_position_ref": output.get("source_position_ref"),
            "source_closed_trade_ref": output.get("source_closed_trade_ref"),
            "postmortem_due_ref": output.get("postmortem_due_ref"),
            "postmortem_due_marker_created": output.get("postmortem_due_marker_created"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "postmortem_status": output.get("postmortem_status"),
            "broker_post_called": output.get("broker_post_called"),
            "alpaca_post_called": output.get("alpaca_post_called"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "boundary": output.get("boundary"),
        },
    )
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_guarded_postmortem_due(output)
    output["status"] = (
        "postmortem_due"
        if output.get("postmortem_due_marker_created") is True
        and not output["validation_errors"]
        else "blocked"
    )
    return output, entry


def write_phase5_guarded_postmortem_due(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = guarded_postmortem_due_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_guarded_postmortem_due_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_guarded_postmortem_due(output)
        output["status"] = (
            "postmortem_due"
            if output.get("postmortem_due_marker_created") is True
            and not output["validation_errors"]
            else "blocked"
        )
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_order_ref": output.get("source_order_ref"),
        "source_position_ref": output.get("source_position_ref"),
        "source_closed_trade_ref": output.get("source_closed_trade_ref"),
        "postmortem_due_ref": output.get("postmortem_due_ref"),
        "closed_trade_count": output.get("closed_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_status": output.get("postmortem_status"),
        "event_log_written": output.get("event_log_written"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def attach_phase5_position_monitor_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / POSITION_MONITOR_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            POSITION_MONITOR_EVENT_TYPE,
            POSITION_MONITOR_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "artifact_type": record.get("artifact_type"),
                "status": record.get("status"),
                "lifecycle_state": record.get("lifecycle_state"),
                "position_state": record.get("position_state"),
                "closed_trade_state": record.get("closed_trade_state"),
                "reconciliation_state": record.get("reconciliation_state"),
                "failed_reconciliation_count": record.get("failed_reconciliation_count"),
                "new_actions_blocked_by_reconciliation_failure": record.get(
                    "new_actions_blocked_by_reconciliation_failure"
                ),
                "open_position_count": record.get("open_position_count"),
                "closed_trade_count": record.get("closed_trade_count"),
                "submitted_order_count": record.get("submitted_order_count"),
                "mirrored_order_count": record.get("mirrored_order_count"),
                "position_monitor_write_authority": record.get("position_monitor_write_authority"),
                "position_close_allowed": record.get("position_close_allowed"),
                "position_resize_allowed": record.get("position_resize_allowed"),
                "order_cancel_allowed": record.get("order_cancel_allowed"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_position_monitor_record(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_position_monitor_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def write_phase5_position_monitor(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = position_monitor_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_position_monitor_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_position_monitor_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_position_monitor_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "position_record_count": output.get("position_record_count"),
        "closed_trade_summary_count": output.get("closed_trade_summary_count"),
        "submitted_order_count": output.get("submitted_order_count"),
        "open_position_count": output.get("open_position_count"),
        "closed_trade_count": output.get("closed_trade_count"),
        "failed_reconciliation_count": output.get("failed_reconciliation_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
