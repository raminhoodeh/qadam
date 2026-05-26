"""Q5-7 Alpaca paper adapter dry-run contract.

This module converts Q5-6 staged-paper-order records into public-safe Alpaca
paper request previews and simulated receipt schemas. It does not call Alpaca,
submit paper orders, allocate broker-usable IDs, write broker state, or enable
live capital.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_execution_adapter_status import (
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_paper_order_staging import (
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase5_paper_order_staging_gate,
    validate_phase5_paper_order_staging_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION = 1
ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT = "phase5_alpaca_paper_dry_run.json"
ALPACA_PAPER_DRY_RUN_HISTORY = "phase5_alpaca_paper_dry_run_history.jsonl"
ALPACA_PAPER_DRY_RUN_EVENT_LOG = "phase5_alpaca_paper_dry_run_events.jsonl"
ALPACA_PAPER_DRY_RUN_EVENT_TYPE = "phase5_alpaca_paper_dry_run_written"
ALPACA_PAPER_DRY_RUN_COMPONENT = "phase5_alpaca_paper_dry_run"
ALPACA_PAPER_DRY_RUN_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_paper_order_staging_gate.json",
    "data/runtime/phase5_execution_adapter_status.json",
    "data/runtime/phase5_kill_switch_ledger.json",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/alpaca_paper_mirror.json",
)

ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS: tuple[str, ...] = (
    "q5_6_staging_bundle_valid",
    "source_staging_record_present",
    "source_staged_order_ready",
    "selected_venue_alpaca_paper",
    "alpaca_adapter_record_present",
    "alpaca_read_only_available",
    "alpaca_write_blocked",
    "alpaca_account_mode_paper",
    "alpaca_live_endpoint_blocked",
    "kill_switch_clear",
    "idempotency_key_deterministic",
    "duplicate_order_guard_collision_free",
    "request_preview_schema_ready",
    "pre_trade_snapshot_schema_ready",
    "simulated_receipt_schema_ready",
    "broker_post_disabled",
    "broker_write_disabled",
    "paper_submission_disabled",
    "live_capital_disabled",
    "submission_separated",
)

ALPACA_PAPER_DRY_RUN_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
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
    "live_capital_enabled",
    "live_endpoint_allowed",
    "crypto_perps_write_allowed",
    "submission_allowed",
    "broker_submit_ready",
    "broker_usable_idempotency_key_allocated",
)

ALPACA_PAPER_DRY_RUN_COUNT_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed_count",
    "trade_candidate_created_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "paper_execution_allowed_count",
    "paper_order_allowed_count",
    "paper_order_submission_allowed_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_submit_receipt_created_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "crypto_perps_write_allowed_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "base_url_exposed_count",
)

ALPACA_PAPER_DRY_RUN_BOUNDARY = (
    "Q5-7 Alpaca paper dry-run records can build public-safe request previews, "
    "deterministic idempotency previews, duplicate-order guard previews, "
    "pre-trade snapshot schemas, and simulated receipt schemas only. This stage "
    "cannot call Alpaca POST routes, allocate broker-usable IDs, submit paper "
    "orders, write brokers, create positions, expose secrets, use live "
    "endpoints, or enable live capital."
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
    ledger["stage"] = "Q5-7"
    ledger["boundary"] = (
        "Q5-7 creates Alpaca paper dry-run previews only. Broker POST, broker "
        "write, paper-order submission, position creation, and live capital stay false."
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _staging_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / PAPER_ORDER_STAGING_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_paper_order_staging_gate(settings=settings)


def _execution_adapter_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / EXECUTION_ADAPTER_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_execution_adapter_status(settings=settings)


def _adapter_by_venue(adapter_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(status.get("venue_key") or ""): status
        for status in adapter_bundle.get("statuses", [])
        if isinstance(status, dict)
    }


def _idempotency_material(source_record: dict[str, Any]) -> dict[str, Any]:
    existing = source_record.get("idempotency_material")
    if isinstance(existing, dict):
        return {
            "stage": str(existing.get("stage") or "Q5-7"),
            "source_staged_paper_order_artifact_id": str(
                existing.get("source_staged_paper_order_artifact_id") or "unknown"
            ),
            "strategy_family_key": str(existing.get("strategy_family_key") or "unknown_strategy"),
            "selected_venue": str(existing.get("selected_venue") or "unknown_venue"),
            "instrument": str(existing.get("instrument") or "unknown_instrument"),
            "side": str(existing.get("side") or "not_determined"),
            "quantity": str(existing.get("quantity") or "0.00000000"),
            "order_type": str(existing.get("order_type") or "not_applicable"),
            "time_in_force": str(existing.get("time_in_force") or "not_applicable"),
            "max_loss_gbp": str(existing.get("max_loss_gbp") or "0.00"),
            "idempotency_seed": str(existing.get("idempotency_seed") or "missing"),
        }
    return {
        "stage": "Q5-7",
        "source_staged_paper_order_artifact_id": str(source_record.get("artifact_id") or "unknown"),
        "strategy_family_key": str(source_record.get("strategy_family_key") or "unknown_strategy"),
        "selected_venue": str(source_record.get("selected_venue") or "unknown_venue"),
        "instrument": str(source_record.get("instrument") or "unknown_instrument"),
        "side": str(source_record.get("side") or "not_determined"),
        "quantity": f"{_float(source_record.get('quantity'), 0.0):.8f}",
        "order_type": str(source_record.get("order_type") or "not_applicable"),
        "time_in_force": str(source_record.get("time_in_force") or "not_applicable"),
        "max_loss_gbp": f"{_float(source_record.get('max_loss_gbp'), 0.0):.2f}",
        "idempotency_seed": str(source_record.get("idempotency_seed") or "missing"),
    }


def _idempotency_key(source_record: dict[str, Any]) -> str:
    material = _idempotency_material(source_record)
    digest = hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()
    return f"q5-7-dryrun-{digest[:24]}"


def _receipt_id(source_record: dict[str, Any]) -> str:
    material = _idempotency_material(source_record)
    material["receipt_scope"] = "simulated_submit_receipt"
    digest = hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()
    return f"q5-7-receipt-{digest[:24]}"


def _request_preview(
    source_record: dict[str, Any],
    *,
    idempotency_key: str,
    request_preview_allowed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "status": "preview_ready_no_post" if request_preview_allowed else "blocked_no_staged_order",
        "adapter": "alpaca",
        "account_mode_required": "paper",
        "paper_account_required": True,
        "http_method_preview": "POST_DISABLED_PREVIEW_ONLY",
        "broker_path_template": "/v2/orders",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "post_call_allowed": False,
        "request_body_preview": {
            "symbol": None,
            "instrument": source_record.get("instrument"),
            "side": source_record.get("side"),
            "qty": source_record.get("quantity"),
            "notional_gbp": source_record.get("notional_gbp"),
            "type": source_record.get("order_type"),
            "time_in_force": source_record.get("time_in_force"),
            "client_order_id_preview": idempotency_key,
            "extended_hours": False,
        },
        "raw_payload_exposed": False,
        "boundary": (
            "This is a schema preview for later paper submit. It contains no URL, "
            "secret, Authorization header, raw broker payload, or POST authority."
        ),
    }


def _pre_trade_snapshot_schema(
    *,
    account_context: dict[str, Any],
    request_preview_allowed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "status": "schema_ready_not_captured"
        if request_preview_allowed
        else "schema_defined_not_captured",
        "required_fields": [
            "account_scope",
            "mode",
            "connection_status",
            "current_balance_gbp",
            "cash_gbp",
            "equity_gbp",
            "open_position_count",
            "open_order_count",
            "write_authority",
            "live_capital_enabled",
            "captured_at",
        ],
        "account_scope": str(account_context.get("account_scope") or "paper"),
        "mode": str(account_context.get("mode") or "paper"),
        "connection_status": str(
            account_context.get("connection_status") or account_context.get("status") or "unknown"
        ),
        "current_balance_gbp": _float(account_context.get("current_balance_gbp"), 0.0),
        "cash_gbp": _float(account_context.get("cash_gbp"), 0.0),
        "equity_gbp": _float(account_context.get("equity_gbp"), 0.0),
        "open_position_count": int(account_context.get("open_position_count", 0) or 0),
        "open_order_count": int(account_context.get("open_order_count", 0) or 0),
        "capture_performed": False,
        "snapshot_ref": "not_captured",
        "write_authority": False,
        "live_capital_enabled": False,
        "boundary": (
            "Pre-trade snapshot schema is defined for the future submit gate, "
            "but Q5-7 captures no order snapshot and writes no account state."
        ),
    }


def _duplicate_order_guard(
    *,
    idempotency_key: str,
    request_preview_allowed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "status": "preview_clear" if request_preview_allowed else "blocked_no_staged_order",
        "guard_key": idempotency_key,
        "collision_scope": "q5_7_alpaca_paper_dry_run_preview_keys",
        "collision_checked": True,
        "collision_detected": False,
        "duplicate_detected": False,
        "known_preview_key_count": 1,
        "lookup_sources": [
            "phase5_alpaca_paper_dry_run_runtime_artifact",
            "phase5_paper_order_staging_gate",
            "event_log:phase5_alpaca_paper_dry_run_written",
        ],
        "lookup_performed": False,
        "guard_write_performed": False,
        "block_policy": "future_submit_must_block_on_duplicate_preview_key_or_source_artifact",
        "boundary": (
            "Duplicate guard is a deterministic preview only; Q5-7 performs no "
            "broker lookup and writes no guard state."
        ),
    }


def _simulated_receipt(
    source_record: dict[str, Any],
    *,
    idempotency_key: str,
    request_preview_allowed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "status": "simulated_ready_no_broker_post"
        if request_preview_allowed
        else "not_created",
        "mode": "dry_run_only",
        "adapter": "alpaca",
        "venue": source_record.get("selected_venue"),
        "simulated_receipt_id": _receipt_id(source_record),
        "client_order_id_preview": idempotency_key,
        "external_order_id": "not_created",
        "broker_order_id_exposed": False,
        "fill_status": "not_submitted",
        "broker_post_called": False,
        "paper_order_submitted": False,
        "raw_broker_payload_stored": False,
        "receipt_created": request_preview_allowed,
        "boundary": (
            "Simulated receipt schema is deterministic and dry-run only. No "
            "external broker order ID or raw broker response exists in Q5-7."
        ),
    }


def _dry_run_checks(
    source_record: dict[str, Any],
    *,
    staging_bundle_errors: list[str],
    adapter_bundle_errors: list[str],
    adapter_status: dict[str, Any],
    idempotency_key: str,
    duplicate_guard: dict[str, Any],
    request_preview: dict[str, Any],
    pre_trade_snapshot: dict[str, Any],
    simulated_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_venue = str(source_record.get("selected_venue") or "missing")
    source_staged = (
        source_record.get("status") == "staged"
        and source_record.get("staging_allowed") is True
        and source_record.get("order_state") == "staged_ready_for_dry_run"
    )
    return [
        _check("q5_6_staging_bundle_valid", not staging_bundle_errors, detail=staging_bundle_errors),
        _check("source_staging_record_present", bool(source_record.get("artifact_id"))),
        _check("source_staged_order_ready", source_staged),
        _check("selected_venue_alpaca_paper", selected_venue == "alpaca_paper"),
        _check("alpaca_adapter_record_present", bool(adapter_status.get("artifact_id"))),
        _check("alpaca_read_only_available", adapter_status.get("read_health") == "read_only_available"),
        _check("alpaca_write_blocked", str(adapter_status.get("write_health") or "").startswith("blocked")),
        _check(
            "alpaca_account_mode_paper",
            adapter_status.get("paper_mode") is True and adapter_status.get("account_mode") == "paper",
        ),
        _check(
            "alpaca_live_endpoint_blocked",
            adapter_status.get("endpoint_classification") != "live_endpoint"
            and adapter_status.get("live_endpoint_allowed") is not True,
        ),
        _check("kill_switch_clear", source_record.get("kill_switch_clear") is True),
        _check(
            "idempotency_key_deterministic",
            idempotency_key == _idempotency_key(source_record),
        ),
        _check(
            "duplicate_order_guard_collision_free",
            duplicate_guard.get("collision_checked") is True
            and duplicate_guard.get("collision_detected") is False
            and duplicate_guard.get("duplicate_detected") is False,
        ),
        _check(
            "request_preview_schema_ready",
            request_preview.get("post_call_allowed") is False
            and request_preview.get("authorization_header_included") is False
            and request_preview.get("base_url_exposed") is False,
        ),
        _check(
            "pre_trade_snapshot_schema_ready",
            pre_trade_snapshot.get("capture_performed") is False
            and pre_trade_snapshot.get("write_authority") is False
            and pre_trade_snapshot.get("live_capital_enabled") is False,
        ),
        _check(
            "simulated_receipt_schema_ready",
            simulated_receipt.get("broker_post_called") is False
            and simulated_receipt.get("paper_order_submitted") is False
            and simulated_receipt.get("raw_broker_payload_stored") is False,
        ),
        _check("broker_post_disabled", True),
        _check("broker_write_disabled", True),
        _check("paper_submission_disabled", True),
        _check("live_capital_disabled", True),
        _check("submission_separated", True),
        _check("q5_5_execution_adapter_bundle_valid", not adapter_bundle_errors, detail=adapter_bundle_errors),
    ]


def _record_status_from_checks(checks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failed = [
        str(check.get("name") or "unknown_check")
        for check in checks
        if not check.get("passed")
        and check.get("name") != "q5_5_execution_adapter_bundle_valid"
    ]
    failed.append("q5_8_paper_submit_gate_not_implemented")
    return "blocked", sorted(dict.fromkeys(failed))


def _alpaca_dry_run_record(
    source_record: dict[str, Any],
    *,
    staging_bundle_errors: list[str],
    adapter_bundle_errors: list[str],
    adapter_status: dict[str, Any],
    account_context: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    strategy_key = str(source_record.get("strategy_family_key") or "unknown_strategy")
    artifact_id = f"phase5:q5-7:alpaca-paper-dry-run:{_safe_key(strategy_key)}"
    idempotency_key = _idempotency_key(source_record)
    request_preview_allowed = (
        source_record.get("status") == "staged"
        and source_record.get("staging_allowed") is True
        and source_record.get("selected_venue") == "alpaca_paper"
        and adapter_status.get("read_health") == "read_only_available"
        and str(adapter_status.get("write_health") or "").startswith("blocked")
        and adapter_status.get("paper_mode") is True
        and adapter_status.get("endpoint_classification") != "live_endpoint"
        and source_record.get("kill_switch_clear") is True
        and not staging_bundle_errors
        and not adapter_bundle_errors
    )
    duplicate_guard = _duplicate_order_guard(
        idempotency_key=idempotency_key,
        request_preview_allowed=request_preview_allowed,
    )
    request_preview = _request_preview(
        source_record,
        idempotency_key=idempotency_key,
        request_preview_allowed=request_preview_allowed,
    )
    pre_trade_snapshot = _pre_trade_snapshot_schema(
        account_context=account_context,
        request_preview_allowed=request_preview_allowed,
    )
    simulated_receipt = _simulated_receipt(
        source_record,
        idempotency_key=idempotency_key,
        request_preview_allowed=request_preview_allowed,
    )
    checks = _dry_run_checks(
        source_record,
        staging_bundle_errors=staging_bundle_errors,
        adapter_bundle_errors=adapter_bundle_errors,
        adapter_status=adapter_status,
        idempotency_key=idempotency_key,
        duplicate_guard=duplicate_guard,
        request_preview=request_preview,
        pre_trade_snapshot=pre_trade_snapshot,
        simulated_receipt=simulated_receipt,
    )
    status, blockers = _record_status_from_checks(checks)
    dry_run_receipt_created = request_preview_allowed
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "alpaca_paper_dry_run_schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "artifact_type": "broker_submit_receipt",
        "artifact_id": artifact_id,
        "phase": "Q5",
        "stage": "Q5-7",
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
        "provenance": phase5_provenance(ALPACA_PAPER_DRY_RUN_SOURCE_REFS),
        "boundary": ALPACA_PAPER_DRY_RUN_BOUNDARY,
        **phase5_authority_defaults(),
        "source_staged_paper_order_artifact_id": source_record.get("artifact_id"),
        "source_staged_paper_order_status": source_record.get("status"),
        "source_staged_paper_order_state": source_record.get("order_state"),
        "strategy_family_key": strategy_key,
        "selected_venue": str(source_record.get("selected_venue") or "missing"),
        "broker_adapter": "alpaca",
        "endpoint_classification": adapter_status.get("endpoint_classification", "missing"),
        "paper_mode_confirmed": adapter_status.get("paper_mode") is True,
        "alpaca_read_health": adapter_status.get("read_health", "missing"),
        "alpaca_write_health": adapter_status.get("write_health", "missing"),
        "receipt_state": "dry_run_receipt_preview_ready"
        if dry_run_receipt_created
        else "blocked_no_request_preview",
        "request_preview_allowed": request_preview_allowed,
        "request_preview": request_preview,
        "dry_run_receipt_created": dry_run_receipt_created,
        "simulated_submit_receipt": simulated_receipt,
        "simulated_receipt": simulated_receipt,
        "pre_trade_snapshot_schema": pre_trade_snapshot,
        "duplicate_order_guard": duplicate_guard,
        "idempotency_material": _idempotency_material(source_record),
        "idempotency_key": idempotency_key,
        "idempotency_key_preview": idempotency_key,
        "idempotency_key_allocated": False,
        "broker_usable_idempotency_key_allocated": False,
        "required_checks": list(ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS),
        "required_check_count": len(ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
        "blocked_reasons": blockers,
        "blocked_reason_count": len(blockers),
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "risk_approval_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
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
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
        "crypto_perps_write_allowed": False,
        "submission_allowed": False,
        "broker_submit_ready": False,
    }
    record["validation_errors"] = validate_phase5_alpaca_paper_dry_run_record(record)
    return record


def _annotate_duplicate_guards(records: list[dict[str, Any]]) -> None:
    counts = Counter(str(record.get("idempotency_key_preview") or "") for record in records)
    for record in records:
        key = str(record.get("idempotency_key_preview") or "")
        guard = record.get("duplicate_order_guard", {})
        if isinstance(guard, dict):
            guard["known_preview_key_count"] = counts.get(key, 0)
            guard["collision_detected"] = counts.get(key, 0) > 1
            guard["duplicate_detected"] = counts.get(key, 0) > 1
            guard["status"] = "blocked_duplicate_preview_key" if counts.get(key, 0) > 1 else guard.get("status")
        if counts.get(key, 0) > 1 and "duplicate_order_guard_collision_free" not in record.get(
            "blocked_reasons", []
        ):
            record["blocked_reasons"] = sorted(
                dict.fromkeys(
                    list(record.get("blocked_reasons", []))
                    + ["duplicate_order_guard_collision_free"]
                )
            )
            record["blocked_reason_count"] = len(record["blocked_reasons"])
        record["validation_errors"] = validate_phase5_alpaca_paper_dry_run_record(record)


def build_phase5_alpaca_paper_dry_run(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    staging_bundle = _staging_bundle(settings)
    adapter_bundle = _execution_adapter_bundle(settings)
    staging_errors = validate_phase5_paper_order_staging_bundle(staging_bundle)
    adapter_errors = validate_phase5_execution_adapter_status_bundle(adapter_bundle)
    adapter_status = _adapter_by_venue(adapter_bundle).get("alpaca_paper", {})
    account_context = paper_account_shadow_context(settings)
    generated_at = _now()
    records = [
        _alpaca_dry_run_record(
            record,
            staging_bundle_errors=staging_errors,
            adapter_bundle_errors=adapter_errors,
            adapter_status=adapter_status,
            account_context=account_context,
            generated_at=generated_at,
        )
        for record in staging_bundle.get("records", [])
        if isinstance(record, dict)
    ]
    _annotate_duplicate_guards(records)
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    receipt_state_counts = Counter(str(record.get("receipt_state") or "unknown") for record in records)
    idempotency_counts = Counter(str(record.get("idempotency_key_preview") or "") for record in records)
    duplicate_keys = {key for key, count in idempotency_counts.items() if key and count > 1}
    bundle = {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "artifact_type": "phase5_alpaca_paper_dry_run_bundle",
        "artifact_id": "phase5:q5-7:alpaca-paper-dry-run",
        "phase": "Q5",
        "stage": "Q5-7",
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
        "provenance": phase5_provenance(ALPACA_PAPER_DRY_RUN_SOURCE_REFS),
        "boundary": ALPACA_PAPER_DRY_RUN_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "source_staging_record_count": int(staging_bundle.get("staging_record_count", 0) or 0),
        "source_staged_order_count": int(staging_bundle.get("staged_order_count", 0) or 0),
        "dry_run_record_count": len(records),
        "request_preview_count": sum(1 for record in records if record.get("request_preview_allowed") is True),
        "dry_run_receipt_count": sum(1 for record in records if record.get("dry_run_receipt_created") is True),
        "blocked_count": status_counts.get("blocked", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "receipt_state_counts": dict(sorted(receipt_state_counts.items())),
        "required_check_count": len(ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS),
        "idempotency_key_count": len([key for key in idempotency_counts if key]),
        "idempotency_collision_count": len(duplicate_keys),
        "duplicate_guard_collision_count": sum(
            1
            for record in records
            if record.get("duplicate_order_guard", {}).get("collision_detected") is True
        ),
        "staging_bundle_validation_error_count": len(staging_errors),
        "execution_adapter_bundle_validation_error_count": len(adapter_errors),
        "records": records,
    }
    for field in ALPACA_PAPER_DRY_RUN_COUNT_FIELDS:
        bundle[field] = 0
    bundle["validation_errors"] = validate_phase5_alpaca_paper_dry_run_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _record_status_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("status") == "submitted_paper_order":
        errors.append("dry_run_status_submitted_paper_order")
    blockers = record.get("blocked_reasons", [])
    if not isinstance(blockers, list):
        errors.append("blocked_reasons_not_list")
        blockers = []
    if record.get("blocked_reason_count") != len(blockers):
        errors.append("blocked_reason_count_mismatch")
    if record.get("status") == "blocked" and not blockers:
        errors.append("blocked_dry_run_without_blockers")
    if record.get("request_preview_allowed") is True:
        if record.get("source_staged_paper_order_status") != "staged":
            errors.append("request_preview_without_staged_source")
        if record.get("selected_venue") != "alpaca_paper":
            errors.append("request_preview_not_alpaca_paper")
        if record.get("paper_mode_confirmed") is not True:
            errors.append("request_preview_without_paper_mode")
        if record.get("alpaca_read_health") != "read_only_available":
            errors.append("request_preview_without_alpaca_readiness")
        if not str(record.get("alpaca_write_health") or "").startswith("blocked"):
            errors.append("request_preview_without_write_block")
        if record.get("endpoint_classification") == "live_endpoint":
            errors.append("request_preview_live_endpoint")
    if record.get("dry_run_receipt_created") is True and record.get("request_preview_allowed") is not True:
        errors.append("dry_run_receipt_without_request_preview")
    return errors


def _nested_schema_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    request_preview = record.get("request_preview", {})
    if not isinstance(request_preview, dict):
        errors.append("request_preview_not_dict")
        request_preview = {}
    for field in (
        "post_call_allowed",
        "authorization_header_included",
        "base_url_exposed",
        "raw_payload_exposed",
    ):
        if request_preview.get(field) is not False:
            errors.append(f"request_preview_authority_or_exposure_enabled:{field}")
    if request_preview.get("http_method_preview") != "POST_DISABLED_PREVIEW_ONLY":
        errors.append("request_preview_method_not_disabled")
    duplicate_guard = record.get("duplicate_order_guard", {})
    if not isinstance(duplicate_guard, dict):
        errors.append("duplicate_guard_not_dict")
        duplicate_guard = {}
    if duplicate_guard.get("collision_checked") is not True:
        errors.append("duplicate_guard_collision_not_checked")
    if duplicate_guard.get("collision_detected") is not False:
        errors.append("duplicate_guard_collision_detected")
    if duplicate_guard.get("duplicate_detected") is not False:
        errors.append("duplicate_guard_duplicate_detected")
    if duplicate_guard.get("lookup_performed") is not False:
        errors.append("duplicate_guard_lookup_performed")
    if duplicate_guard.get("guard_write_performed") is not False:
        errors.append("duplicate_guard_write_performed")
    if duplicate_guard.get("guard_key") != record.get("idempotency_key_preview"):
        errors.append("duplicate_guard_key_mismatch")
    snapshot = record.get("pre_trade_snapshot_schema", {})
    if not isinstance(snapshot, dict):
        errors.append("pre_trade_snapshot_not_dict")
        snapshot = {}
    for field in ("capture_performed", "write_authority", "live_capital_enabled"):
        if snapshot.get(field) is not False:
            errors.append(f"pre_trade_snapshot_authority_enabled:{field}")
    if snapshot.get("snapshot_ref") != "not_captured":
        errors.append("pre_trade_snapshot_captured")
    receipt = record.get("simulated_submit_receipt", {})
    if not isinstance(receipt, dict):
        errors.append("simulated_receipt_not_dict")
        receipt = {}
    for field in ("broker_post_called", "paper_order_submitted", "raw_broker_payload_stored"):
        if receipt.get(field) is not False:
            errors.append(f"simulated_receipt_authority_enabled:{field}")
    if receipt.get("broker_order_id_exposed") is not False:
        errors.append("simulated_receipt_broker_order_id_exposed")
    if receipt.get("simulated_receipt_id") != _receipt_id(record):
        errors.append("simulated_receipt_id_not_deterministic")
    return errors


def validate_phase5_alpaca_paper_dry_run_record(record: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-7"))
    if record.get("artifact_type") != "broker_submit_receipt":
        errors.append("artifact_type_not_broker_submit_receipt")
    if record.get("alpaca_paper_dry_run_schema_version") != PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION:
        errors.append("alpaca_paper_dry_run_schema_version_mismatch")
    if record.get("public_safe") is not True:
        errors.append("alpaca_dry_run_not_public_safe")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if record.get("required_check_count") != len(ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    check_names = {
        str(check.get("name") or "")
        for check in record.get("checks", [])
        if isinstance(check, dict)
    }
    for check in ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS:
        if check not in check_names:
            errors.append(f"required_check_missing:{check}")
    expected_idempotency = _idempotency_key(record)
    if record.get("idempotency_key") != expected_idempotency:
        errors.append("idempotency_key_not_deterministic")
    if record.get("idempotency_key_preview") != expected_idempotency:
        errors.append("idempotency_preview_not_deterministic")
    if not str(record.get("idempotency_key") or "").startswith("q5-7-dryrun-"):
        errors.append("idempotency_key_not_q5_7_scoped")
    if record.get("idempotency_key_allocated") is not False:
        errors.append("idempotency_key_allocated")
    for exposure in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
    ):
        if record.get(exposure) is not False:
            errors.append(f"alpaca_dry_run_exposure_enabled:{exposure}")
    for field in ALPACA_PAPER_DRY_RUN_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"alpaca_dry_run_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    errors.extend(_record_status_errors(record))
    errors.extend(_nested_schema_errors(record))
    return sorted(set(errors))


def validate_phase5_alpaca_paper_dry_run_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "dry_run_record_count",
        "request_preview_count",
        "dry_run_receipt_count",
        "blocked_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_alpaca_paper_dry_run_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-7":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("dry_run_record_count") != len(records):
        errors.append("dry_run_record_count_mismatch")
    if bundle.get("request_preview_count") != sum(
        1 for record in records if isinstance(record, dict) and record.get("request_preview_allowed") is True
    ):
        errors.append("request_preview_count_mismatch")
    if bundle.get("dry_run_receipt_count") != sum(
        1 for record in records if isinstance(record, dict) and record.get("dry_run_receipt_created") is True
    ):
        errors.append("dry_run_receipt_count_mismatch")
    status_counts = Counter(
        str(record.get("status") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    if bundle.get("blocked_count") != status_counts.get("blocked", 0):
        errors.append("blocked_count_mismatch")
    idempotency_counts = Counter(
        str(record.get("idempotency_key_preview") or "")
        for record in records
        if isinstance(record, dict)
    )
    duplicate_keys = {key for key, count in idempotency_counts.items() if key and count > 1}
    if bundle.get("idempotency_collision_count") != len(duplicate_keys):
        errors.append("idempotency_collision_count_mismatch")
    if bundle.get("duplicate_guard_collision_count") != 0:
        errors.append("duplicate_guard_collision_count_not_zero")
    if bundle.get("idempotency_collision_count") != 0:
        errors.append("idempotency_collision_count_not_zero")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in ALPACA_PAPER_DRY_RUN_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("alpaca_dry_run_record_not_dict")
            continue
        errors.extend(validate_phase5_alpaca_paper_dry_run_record(record))
    return sorted(set(errors))


def attach_phase5_alpaca_paper_dry_run_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / ALPACA_PAPER_DRY_RUN_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            ALPACA_PAPER_DRY_RUN_EVENT_TYPE,
            ALPACA_PAPER_DRY_RUN_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "source_staged_paper_order_artifact_id": record.get(
                    "source_staged_paper_order_artifact_id"
                ),
                "strategy_family_key": record.get("strategy_family_key"),
                "status": record.get("status"),
                "receipt_state": record.get("receipt_state"),
                "request_preview_allowed": record.get("request_preview_allowed"),
                "dry_run_receipt_created": record.get("dry_run_receipt_created"),
                "broker_post_called": record.get("broker_post_called"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "paper_order_submitted": record.get("paper_order_submitted"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "blocked_reason_count": record.get("blocked_reason_count"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_alpaca_paper_dry_run_record(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_alpaca_paper_dry_run_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_alpaca_paper_dry_run_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
        runtime / ALPACA_PAPER_DRY_RUN_HISTORY,
        runtime / ALPACA_PAPER_DRY_RUN_EVENT_LOG,
    )


def write_phase5_alpaca_paper_dry_run(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_alpaca_paper_dry_run_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_alpaca_paper_dry_run_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_alpaca_paper_dry_run_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_alpaca_paper_dry_run_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "dry_run_record_count": output.get("dry_run_record_count"),
        "request_preview_count": output.get("request_preview_count"),
        "dry_run_receipt_count": output.get("dry_run_receipt_count"),
        "blocked_count": output.get("blocked_count"),
        "idempotency_collision_count": output.get("idempotency_collision_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
