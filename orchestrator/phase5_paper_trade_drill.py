"""Q5-14 guarded end-to-end paper trade drill.

The Q5-14 drill ties the Layer B chain together from source context through
postmortem handoff. It records the complete drill contract and the current
blockers, but it does not perform broker POST calls or mutate the paper account
mirror. A real paper-submit lifecycle remains blocked until the separate
paper-submit approval artifact and upstream prerequisites exist.
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
from orchestrator.phase5_alpaca_paper_dry_run import (
    ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
    build_phase5_alpaca_paper_dry_run,
    validate_phase5_alpaca_paper_dry_run_bundle,
)
from orchestrator.phase5_approval_policy import (
    APPROVAL_POLICY_RUNTIME_ARTIFACT,
    build_phase5_approval_policy_decisions,
    validate_phase5_approval_policy_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
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
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from orchestrator.phase5_signal_review import (
    SIGNAL_REVIEW_RUNTIME_ARTIFACT,
    build_phase5_signal_review,
    validate_phase5_signal_review_bundle,
)
from orchestrator.phase5_system_map import (
    SYSTEM_MAP_RUNTIME_ARTIFACT,
    validate_phase5_system_map_bundle,
)
from orchestrator.phase5_telegram_notifier import (
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    build_phase5_telegram_notifier,
    validate_phase5_telegram_notifier_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION = 1
PAPER_TRADE_DRILL_RUNTIME_ARTIFACT = "phase5_paper_trade_drill.json"
PAPER_TRADE_DRILL_HISTORY = "phase5_paper_trade_drill_history.jsonl"
PAPER_TRADE_DRILL_EVENT_LOG = "phase5_paper_trade_drill_events.jsonl"
PAPER_TRADE_DRILL_EVENT_TYPE = "phase5_paper_trade_drill_step_written"
PAPER_TRADE_DRILL_COMPONENT = "phase5_paper_trade_drill"

PAPER_TRADE_DRILL_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{APPROVAL_POLICY_RUNTIME_ARTIFACT}",
    f"data/runtime/{RISK_SIZING_RUNTIME_ARTIFACT}",
    f"data/runtime/{KILL_SWITCH_RUNTIME_ARTIFACT}",
    f"data/runtime/{EXECUTION_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_ORDER_STAGING_RUNTIME_ARTIFACT}",
    f"data/runtime/{ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT}",
    f"data/runtime/{TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT}",
    f"data/runtime/{POSITION_MONITOR_RUNTIME_ARTIFACT}",
    f"data/runtime/{SIGNAL_REVIEW_RUNTIME_ARTIFACT}",
    f"data/runtime/{SYSTEM_MAP_RUNTIME_ARTIFACT}",
)

PAPER_TRADE_DRILL_REQUIRED_STEPS: tuple[str, ...] = (
    "source_context",
    "signal_integrity",
    "approval_policy",
    "risk_sizing",
    "kill_switch",
    "execution_adapter",
    "staged_paper_order",
    "alpaca_paper_submit_gate",
    "broker_receipt",
    "position_open",
    "position_close",
    "postmortem_due",
    "telegram_dashboard_sync",
)

PAPER_TRADE_DRILL_STEP_LABELS: dict[str, str] = {
    "source_context": "Replay/live source context",
    "signal_integrity": "Signal Integrity review",
    "approval_policy": "Approval policy",
    "risk_sizing": "Risk sizing",
    "kill_switch": "Kill switch ledger",
    "execution_adapter": "Execution adapter",
    "staged_paper_order": "Staged paper order",
    "alpaca_paper_submit_gate": "Alpaca paper submit gate",
    "broker_receipt": "Broker receipt",
    "position_open": "Position open tracking",
    "position_close": "Position close tracking",
    "postmortem_due": "Postmortem due marker",
    "telegram_dashboard_sync": "Telegram/dashboard sync",
}

PAPER_TRADE_DRILL_TERMINAL_STEPS: tuple[str, ...] = (
    "broker_receipt",
    "position_open",
    "position_close",
    "postmortem_due",
)

PAPER_TRADE_DRILL_BOUNDARY_FIELDS: tuple[str, ...] = (
    "broker_post_called",
    "alpaca_post_called",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "position_monitor_write_authority",
    "position_close_allowed",
    "position_resize_allowed",
    "order_cancel_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
)

PAPER_TRADE_DRILL_COUNT_FIELDS: tuple[str, ...] = tuple(
    f"{field}_count" for field in PAPER_TRADE_DRILL_BOUNDARY_FIELDS
)

PAPER_TRADE_DRILL_BOUNDARY = (
    "Q5-14 records the end-to-end paper trade drill chain and its current "
    "blockers. It cannot bypass explicit paper-submit approval, cannot call "
    "brokers or venues, cannot mutate the paper account mirror, cannot close, "
    "resize, or cancel positions, cannot write prediction-market venues, cannot "
    "enable live capital, and the Phase 5 test drill cannot count toward Phase "
    "7 proof."
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


def paper_trade_drill_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
        runtime / PAPER_TRADE_DRILL_HISTORY,
        runtime / PAPER_TRADE_DRILL_EVENT_LOG,
    )


def _runtime_or_build(
    settings: Settings,
    artifact_name: str,
    builder: Any,
    validator: Any,
) -> tuple[dict[str, Any], bool, list[str]]:
    runtime = _read_json(_runtime_dir(settings) / artifact_name)
    recorded = runtime is not None
    bundle = runtime or builder(settings=settings)
    return bundle, recorded, list(validator(bundle))


def _source_snapshot(
    bundle: dict[str, Any],
    *,
    recorded: bool,
    validation_errors: list[str],
    metric_fields: tuple[str, ...],
) -> dict[str, Any]:
    snapshot = {
        "stage": bundle.get("stage", "not_run"),
        "status": bundle.get("status", "not_run") if recorded else "missing_fail_closed",
        "recorded": recorded,
        "event_log_written": bundle.get("event_log_written") is True,
        "event_log_event_count": int(bundle.get("event_log_event_count", 0) or 0),
        "validation_error_count": len(validation_errors),
        "public_safe": bundle.get("public_safe") is True,
    }
    for field in metric_fields:
        value = bundle.get(field, 0)
        if isinstance(value, bool):
            snapshot[field] = value
        elif isinstance(value, float):
            snapshot[field] = value
        elif isinstance(value, dict):
            snapshot[field] = dict(value)
        elif isinstance(value, list):
            snapshot[field] = list(value)
        else:
            try:
                snapshot[field] = int(value or 0)
            except (TypeError, ValueError):
                snapshot[field] = value
    return snapshot


def _source_bundles(settings: Settings) -> dict[str, dict[str, Any]]:
    approval, approval_recorded, approval_errors = _runtime_or_build(
        settings,
        APPROVAL_POLICY_RUNTIME_ARTIFACT,
        build_phase5_approval_policy_decisions,
        validate_phase5_approval_policy_bundle,
    )
    risk, risk_recorded, risk_errors = _runtime_or_build(
        settings,
        RISK_SIZING_RUNTIME_ARTIFACT,
        build_phase5_risk_sizing_reviews,
        validate_phase5_risk_sizing_bundle,
    )
    kill, kill_recorded, kill_errors = _runtime_or_build(
        settings,
        KILL_SWITCH_RUNTIME_ARTIFACT,
        build_phase5_kill_switch_ledger,
        validate_phase5_kill_switch_ledger,
    )
    execution, execution_recorded, execution_errors = _runtime_or_build(
        settings,
        EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
        build_phase5_execution_adapter_status,
        validate_phase5_execution_adapter_status_bundle,
    )
    staging, staging_recorded, staging_errors = _runtime_or_build(
        settings,
        PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
        build_phase5_paper_order_staging_gate,
        validate_phase5_paper_order_staging_bundle,
    )
    dry_run, dry_run_recorded, dry_run_errors = _runtime_or_build(
        settings,
        ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
        build_phase5_alpaca_paper_dry_run,
        validate_phase5_alpaca_paper_dry_run_bundle,
    )
    submit, submit_recorded, submit_errors = _runtime_or_build(
        settings,
        PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
        build_phase5_paper_submit_enablement_gate,
        validate_phase5_paper_submit_enablement_bundle,
    )
    telegram, telegram_recorded, telegram_errors = _runtime_or_build(
        settings,
        TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
        build_phase5_telegram_notifier,
        validate_phase5_telegram_notifier_bundle,
    )
    position, position_recorded, position_errors = _runtime_or_build(
        settings,
        POSITION_MONITOR_RUNTIME_ARTIFACT,
        build_phase5_position_monitor,
        validate_phase5_position_monitor_bundle,
    )
    signal, signal_recorded, signal_errors = _runtime_or_build(
        settings,
        SIGNAL_REVIEW_RUNTIME_ARTIFACT,
        build_phase5_signal_review,
        validate_phase5_signal_review_bundle,
    )
    system_map_runtime = _read_json(_runtime_dir(settings) / SYSTEM_MAP_RUNTIME_ARTIFACT)
    system_map_recorded = system_map_runtime is not None
    system_map = system_map_runtime or {
        "stage": "Q5-13",
        "status": "missing_fail_closed",
        "public_safe": True,
        "event_log_written": False,
        "event_log_event_count": 0,
        "node_count": 0,
        "lane_count": 0,
        "backend_parity_error_count": 0,
        "unsafe_control_count": 0,
        "ui_inferred_node_count": 0,
    }
    system_map_errors = (
        validate_phase5_system_map_bundle(system_map)
        if system_map_recorded
        else []
    )
    return {
        "approval_policy": {
            "bundle": approval,
            "snapshot": _source_snapshot(
                approval,
                recorded=approval_recorded,
                validation_errors=approval_errors,
                metric_fields=(
                    "decision_count",
                    "eligible_count",
                    "blocked_count",
                    "risk_agent_handoff_allowed_count",
                ),
            ),
        },
        "risk_sizing": {
            "bundle": risk,
            "snapshot": _source_snapshot(
                risk,
                recorded=risk_recorded,
                validation_errors=risk_errors,
                metric_fields=(
                    "risk_review_count",
                    "paper_size_eligible_count",
                    "eligible_count",
                    "blocked_count",
                ),
            ),
        },
        "kill_switch": {
            "bundle": kill,
            "snapshot": _source_snapshot(
                kill,
                recorded=kill_recorded,
                validation_errors=kill_errors,
                metric_fields=(
                    "switch_count",
                    "active_switch_count",
                    "blocking_switch_count",
                    "clear_switch_count",
                ),
            ),
        },
        "execution_adapter": {
            "bundle": execution,
            "snapshot": _source_snapshot(
                execution,
                recorded=execution_recorded,
                validation_errors=execution_errors,
                metric_fields=(
                    "adapter_status_count",
                    "read_allowed_count",
                    "downstream_staging_allowed_count",
                    "broker_post_called_count",
                    "live_capital_enabled_count",
                ),
            ),
        },
        "paper_order_staging": {
            "bundle": staging,
            "snapshot": _source_snapshot(
                staging,
                recorded=staging_recorded,
                validation_errors=staging_errors,
                metric_fields=(
                    "staging_record_count",
                    "staged_order_count",
                    "paper_size_eligible_count",
                    "blocked_count",
                ),
            ),
        },
        "alpaca_paper_dry_run": {
            "bundle": dry_run,
            "snapshot": _source_snapshot(
                dry_run,
                recorded=dry_run_recorded,
                validation_errors=dry_run_errors,
                metric_fields=(
                    "dry_run_record_count",
                    "request_preview_count",
                    "dry_run_receipt_count",
                    "blocked_count",
                    "broker_post_called_count",
                    "alpaca_post_called_count",
                ),
            ),
        },
        "paper_submit_enablement": {
            "bundle": submit,
            "snapshot": _source_snapshot(
                submit,
                recorded=submit_recorded,
                validation_errors=submit_errors,
                metric_fields=(
                    "submit_enablement_record_count",
                    "submit_path_available_count",
                    "blocked_count",
                    "paper_submit_approval_present",
                    "paper_submit_approval_logged",
                    "paper_order_submitted_count",
                    "broker_post_called_count",
                    "alpaca_post_called_count",
                    "live_capital_enabled_count",
                ),
            ),
        },
        "telegram_notifier": {
            "bundle": telegram,
            "snapshot": _source_snapshot(
                telegram,
                recorded=telegram_recorded,
                validation_errors=telegram_errors,
                metric_fields=(
                    "notification_record_count",
                    "eligible_alert_count",
                    "queued_dry_run_alert_count",
                    "outbox_message_written_count",
                    "suppressed_alert_count",
                    "live_send_allowed_count",
                    "telegram_command_path_enabled_count",
                ),
            ),
        },
        "position_monitor": {
            "bundle": position,
            "snapshot": _source_snapshot(
                position,
                recorded=position_recorded,
                validation_errors=position_errors,
                metric_fields=(
                    "monitor_record_count",
                    "submitted_order_count",
                    "open_position_count",
                    "closed_trade_count",
                    "postmortem_due_count",
                    "postmortem_complete_count",
                    "failed_reconciliation_count",
                    "position_monitor_write_authority_count",
                    "position_close_allowed_count",
                    "position_resize_allowed_count",
                    "order_cancel_allowed_count",
                ),
            ),
        },
        "signal_review": {
            "bundle": signal,
            "snapshot": _source_snapshot(
                signal,
                recorded=signal_recorded,
                validation_errors=signal_errors,
                metric_fields=(
                    "signal_review_record_count",
                    "decision_chain_count",
                    "backend_truth_displayed_count",
                    "ui_inferred_readiness_count",
                    "governance_comment_event_count",
                    "kill_switch_action_event_count",
                    "broker_post_called_count",
                    "live_capital_enabled_count",
                ),
            ),
        },
        "system_map": {
            "bundle": system_map,
            "snapshot": _source_snapshot(
                system_map,
                recorded=system_map_recorded,
                validation_errors=system_map_errors,
                metric_fields=(
                    "node_count",
                    "lane_count",
                    "backend_parity_error_count",
                    "unsafe_control_count",
                    "ui_inferred_node_count",
                ),
            ),
        },
    }


def _metric(sources: dict[str, dict[str, Any]], source_key: str, metric: str) -> Any:
    return sources.get(source_key, {}).get("snapshot", {}).get(metric, 0)


def _paper_submit_approval_state(sources: dict[str, dict[str, Any]]) -> str:
    bundle = sources.get("paper_submit_enablement", {}).get("bundle", {})
    return str(bundle.get("paper_submit_approval_state") or "missing")


def _blockers(sources: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for source_key, payload in sources.items():
        snapshot = payload.get("snapshot", {})
        if snapshot.get("recorded") is not True:
            blockers.append(f"{source_key}_artifact_missing")
        if int(snapshot.get("validation_error_count", 0) or 0) != 0:
            blockers.append(f"{source_key}_validation_errors")
    if _metric(sources, "signal_review", "signal_review_record_count") < 1:
        blockers.append("signal_review_missing")
    if _metric(sources, "approval_policy", "decision_count") < 1:
        blockers.append("approval_policy_decision_missing")
    if _metric(sources, "risk_sizing", "paper_size_eligible_count") < 1:
        blockers.append("risk_size_eligible_trade_missing")
    if _metric(sources, "kill_switch", "blocking_switch_count") != 0:
        blockers.append("kill_switch_blocking")
    if _metric(sources, "execution_adapter", "downstream_staging_allowed_count") < 1:
        blockers.append("execution_adapter_not_staging_ready")
    if _metric(sources, "paper_order_staging", "staged_order_count") < 1:
        blockers.append("staged_paper_order_missing")
    if _metric(sources, "alpaca_paper_dry_run", "dry_run_receipt_count") < 1:
        blockers.append("alpaca_dry_run_receipt_missing")
    if _metric(sources, "paper_submit_enablement", "paper_submit_approval_present") is not True:
        blockers.append("paper_submit_approval_missing")
    if _metric(sources, "paper_submit_enablement", "submit_path_available_count") < 1:
        blockers.append("paper_submit_path_unavailable")
    if _metric(sources, "paper_submit_enablement", "paper_order_submitted_count") < 1:
        blockers.append("paper_order_submission_missing")
    if _metric(sources, "position_monitor", "submitted_order_count") < 1:
        blockers.append("submitted_order_not_mirrored")
    closed_trade_count = int(_metric(sources, "position_monitor", "closed_trade_count") or 0)
    open_position_count = int(_metric(sources, "position_monitor", "open_position_count") or 0)
    if open_position_count < 1 and closed_trade_count < 1:
        blockers.append("open_position_missing")
    if closed_trade_count < 1:
        blockers.append("closed_trade_missing")
    if _metric(sources, "position_monitor", "postmortem_due_count") < 1:
        blockers.append("postmortem_due_missing")
    if _metric(sources, "telegram_notifier", "queued_dry_run_alert_count") < 1:
        blockers.append("telegram_dry_run_alert_missing")
    if _metric(sources, "system_map", "backend_parity_error_count") != 0:
        blockers.append("dashboard_backend_parity_error")
    if _metric(sources, "system_map", "unsafe_control_count") != 0:
        blockers.append("dashboard_unsafe_control_present")
    unsafe_metrics = {
        "alpaca_paper_dry_run": ("broker_post_called_count", "alpaca_post_called_count"),
        "paper_submit_enablement": (
            "broker_post_called_count",
            "alpaca_post_called_count",
            "live_capital_enabled_count",
        ),
        "signal_review": ("broker_post_called_count", "live_capital_enabled_count"),
    }
    for source_key, metric_names in unsafe_metrics.items():
        for metric_name in metric_names:
            if int(_metric(sources, source_key, metric_name) or 0) != 0:
                blockers.append(f"unsafe_{source_key}_{metric_name}")
    return sorted(set(blockers))


def _drill_state(blockers: list[str]) -> str:
    if not blockers:
        return "paper_trade_drill_closed_trade_ready"
    if "paper_submit_approval_missing" in blockers:
        return "blocked_pending_paper_submit_approval"
    if "risk_size_eligible_trade_missing" in blockers:
        return "blocked_missing_risk_eligible_size"
    if "staged_paper_order_missing" in blockers:
        return "blocked_missing_staged_paper_order"
    if "paper_submit_path_unavailable" in blockers:
        return "blocked_submit_path_unavailable"
    return "blocked_prerequisites_missing"


def _step_specs(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    open_position_count = int(_metric(sources, "position_monitor", "open_position_count") or 0)
    closed_trade_count = int(_metric(sources, "position_monitor", "closed_trade_count") or 0)
    position_open_lifecycle_satisfied = open_position_count > 0 or closed_trade_count > 0
    position_open_backend_status = (
        "open_position"
        if open_position_count > 0
        else "closed_trade"
        if closed_trade_count > 0
        else "blocked"
    )
    return [
        {
            "step_key": "source_context",
            "source_key": "system_map",
            "metric_name": "node_count",
            "metric_value": _metric(sources, "system_map", "node_count"),
            "passed": _metric(sources, "system_map", "node_count") > 0,
            "backend_status": "ok" if _metric(sources, "system_map", "node_count") > 0 else "blocked",
            "blocker": "source_context_missing",
        },
        {
            "step_key": "signal_integrity",
            "source_key": "signal_review",
            "metric_name": "signal_review_record_count",
            "metric_value": _metric(sources, "signal_review", "signal_review_record_count"),
            "passed": _metric(sources, "signal_review", "signal_review_record_count") > 0,
            "backend_status": "ok"
            if _metric(sources, "signal_review", "signal_review_record_count") > 0
            else "blocked",
            "blocker": "signal_review_missing",
        },
        {
            "step_key": "approval_policy",
            "source_key": "approval_policy",
            "metric_name": "decision_count",
            "metric_value": _metric(sources, "approval_policy", "decision_count"),
            "passed": _metric(sources, "approval_policy", "decision_count") > 0,
            "backend_status": "ok"
            if _metric(sources, "approval_policy", "decision_count") > 0
            else "blocked",
            "blocker": "approval_policy_decision_missing",
        },
        {
            "step_key": "risk_sizing",
            "source_key": "risk_sizing",
            "metric_name": "paper_size_eligible_count",
            "metric_value": _metric(sources, "risk_sizing", "paper_size_eligible_count"),
            "passed": _metric(sources, "risk_sizing", "paper_size_eligible_count") > 0,
            "backend_status": "ok"
            if _metric(sources, "risk_sizing", "paper_size_eligible_count") > 0
            else "blocked",
            "blocker": "risk_size_eligible_trade_missing",
        },
        {
            "step_key": "kill_switch",
            "source_key": "kill_switch",
            "metric_name": "blocking_switch_count",
            "metric_value": _metric(sources, "kill_switch", "blocking_switch_count"),
            "passed": _metric(sources, "kill_switch", "blocking_switch_count") == 0,
            "backend_status": "ok"
            if _metric(sources, "kill_switch", "blocking_switch_count") == 0
            else "blocked",
            "blocker": "kill_switch_blocking",
        },
        {
            "step_key": "execution_adapter",
            "source_key": "execution_adapter",
            "metric_name": "downstream_staging_allowed_count",
            "metric_value": _metric(sources, "execution_adapter", "downstream_staging_allowed_count"),
            "passed": _metric(sources, "execution_adapter", "downstream_staging_allowed_count") > 0,
            "backend_status": "ok"
            if _metric(sources, "execution_adapter", "downstream_staging_allowed_count") > 0
            else "blocked",
            "blocker": "execution_adapter_not_staging_ready",
        },
        {
            "step_key": "staged_paper_order",
            "source_key": "paper_order_staging",
            "metric_name": "staged_order_count",
            "metric_value": _metric(sources, "paper_order_staging", "staged_order_count"),
            "passed": _metric(sources, "paper_order_staging", "staged_order_count") > 0,
            "backend_status": "staged"
            if _metric(sources, "paper_order_staging", "staged_order_count") > 0
            else "blocked",
            "blocker": "staged_paper_order_missing",
        },
        {
            "step_key": "alpaca_paper_submit_gate",
            "source_key": "paper_submit_enablement",
            "metric_name": "submit_path_available_count",
            "metric_value": _metric(sources, "paper_submit_enablement", "submit_path_available_count"),
            "passed": _metric(sources, "paper_submit_enablement", "submit_path_available_count") > 0,
            "backend_status": "ready"
            if _metric(sources, "paper_submit_enablement", "submit_path_available_count") > 0
            else "blocked",
            "blocker": "paper_submit_path_unavailable",
        },
        {
            "step_key": "broker_receipt",
            "source_key": "paper_submit_enablement",
            "metric_name": "paper_order_submitted_count",
            "metric_value": _metric(sources, "paper_submit_enablement", "paper_order_submitted_count"),
            "passed": _metric(sources, "paper_submit_enablement", "paper_order_submitted_count") > 0,
            "backend_status": "submitted_paper_order"
            if _metric(sources, "paper_submit_enablement", "paper_order_submitted_count") > 0
            else "blocked",
            "blocker": "paper_order_submission_missing",
        },
        {
            "step_key": "position_open",
            "source_key": "position_monitor",
            "metric_name": "position_open_lifecycle_count",
            "metric_value": 1 if position_open_lifecycle_satisfied else 0,
            "passed": position_open_lifecycle_satisfied,
            "backend_status": position_open_backend_status,
            "blocker": "open_position_missing",
        },
        {
            "step_key": "position_close",
            "source_key": "position_monitor",
            "metric_name": "closed_trade_count",
            "metric_value": _metric(sources, "position_monitor", "closed_trade_count"),
            "passed": _metric(sources, "position_monitor", "closed_trade_count") > 0,
            "backend_status": "closed_trade"
            if _metric(sources, "position_monitor", "closed_trade_count") > 0
            else "blocked",
            "blocker": "closed_trade_missing",
        },
        {
            "step_key": "postmortem_due",
            "source_key": "position_monitor",
            "metric_name": "postmortem_due_count",
            "metric_value": _metric(sources, "position_monitor", "postmortem_due_count"),
            "passed": _metric(sources, "position_monitor", "postmortem_due_count") > 0,
            "backend_status": "postmortem_due"
            if _metric(sources, "position_monitor", "postmortem_due_count") > 0
            else "blocked",
            "blocker": "postmortem_due_missing",
        },
        {
            "step_key": "telegram_dashboard_sync",
            "source_key": "system_map",
            "metric_name": "backend_parity_error_count",
            "metric_value": _metric(sources, "system_map", "backend_parity_error_count"),
            "passed": _metric(sources, "system_map", "backend_parity_error_count") == 0,
            "backend_status": "ok"
            if _metric(sources, "system_map", "backend_parity_error_count") == 0
            else "blocked",
            "blocker": "dashboard_backend_parity_error",
        },
    ]


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-14"
    ledger["boundary"] = (
        "Q5-14 can record the drill state and blockers only. It cannot grant "
        "broker-write, paper-submit, close, resize, cancel, notification-send, "
        "prediction-market-write, live-endpoint, or live-capital authority."
    )
    return ledger


def _step_record(
    spec: dict[str, Any],
    *,
    generated_at: str,
    step_order: int,
) -> dict[str, Any]:
    step_key = str(spec["step_key"])
    backend_status = str(spec["backend_status"])
    passed = spec.get("passed") is True
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "paper_trade_drill_schema_version": PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION,
        "artifact_type": "phase5_paper_trade_drill_step",
        "artifact_id": f"phase5:q5-14:paper-trade-drill:{_safe_key(step_key)}",
        "phase": "Q5",
        "stage": "Q5-14",
        "status": "eligible" if passed else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PAPER_TRADE_DRILL_SOURCE_REFS),
        "boundary": PAPER_TRADE_DRILL_BOUNDARY,
        **phase5_authority_defaults(),
        "step_key": step_key,
        "step_label": PAPER_TRADE_DRILL_STEP_LABELS.get(step_key, step_key),
        "step_order": step_order,
        "source_key": spec.get("source_key"),
        "backend_metric_name": spec.get("metric_name"),
        "backend_metric_value": spec.get("metric_value"),
        "backend_status": backend_status,
        "display_status": backend_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "step_passed": passed,
        "terminal_lifecycle_step": step_key in PAPER_TRADE_DRILL_TERMINAL_STEPS,
        "blocked_reason": None if passed else spec.get("blocker"),
        "broker_post_called": False,
        "alpaca_post_called": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "position_monitor_write_authority": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "phase5_test_trade": True,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
    }
    record["validation_errors"] = validate_phase5_paper_trade_drill_step(record)
    return record


def build_phase5_paper_trade_drill(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    sources = _source_bundles(settings)
    blockers = _blockers(sources)
    drill_state = _drill_state(blockers)
    records = [
        _step_record(spec, generated_at=generated_at, step_order=index)
        for index, spec in enumerate(_step_specs(sources), start=1)
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    backend_status_counts = Counter(
        str(record.get("backend_status") or "unknown") for record in records
    )
    step_blockers = sorted(
        str(record.get("blocked_reason"))
        for record in records
        if str(record.get("blocked_reason") or "").strip()
    )
    source_validation_error_count = sum(
        int(payload.get("snapshot", {}).get("validation_error_count", 0) or 0)
        for payload in sources.values()
    )
    position_open_lifecycle_satisfied = (
        int(_metric(sources, "position_monitor", "open_position_count") or 0) > 0
        or int(_metric(sources, "position_monitor", "closed_trade_count") or 0) > 0
    )
    paper_trade_drill_complete = not blockers
    bundle = {
        "schema_version": PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION,
        "artifact_type": "phase5_paper_trade_drill_bundle",
        "artifact_id": "phase5:q5-14:paper-trade-drill",
        "phase": "Q5",
        "stage": "Q5-14",
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
        "provenance": phase5_provenance(PAPER_TRADE_DRILL_SOURCE_REFS),
        "boundary": PAPER_TRADE_DRILL_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "paper_trade_drill_state": drill_state,
        "paper_trade_drill_complete": paper_trade_drill_complete,
        "phase5_paper_trade_drill_implementation_ready": True,
        "phase5_paper_trade_drill_exit_gate_passed": paper_trade_drill_complete,
        "phase7_proof_credit_allowed": False,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "step_blockers": step_blockers,
        "step_blocker_count": len(step_blockers),
        "step_count": len(records),
        "required_step_count": len(PAPER_TRADE_DRILL_REQUIRED_STEPS),
        "required_steps": list(PAPER_TRADE_DRILL_REQUIRED_STEPS),
        "status_counts": dict(sorted(status_counts.items())),
        "backend_status_counts": dict(sorted(backend_status_counts.items())),
        "source_validation_error_count": source_validation_error_count,
        "source_bundle_count": len(sources),
        "source_bundles": {
            key: deepcopy(payload["snapshot"]) for key, payload in sorted(sources.items())
        },
        "paper_submit_approval_state": _paper_submit_approval_state(sources),
        "paper_submit_approval_present": (
            _metric(sources, "paper_submit_enablement", "paper_submit_approval_present") is True
        ),
        "paper_submit_path_available_count": int(
            _metric(sources, "paper_submit_enablement", "submit_path_available_count") or 0
        ),
        "signal_review_record_count": int(
            _metric(sources, "signal_review", "signal_review_record_count") or 0
        ),
        "approval_policy_decision_count": int(
            _metric(sources, "approval_policy", "decision_count") or 0
        ),
        "risk_review_count": int(_metric(sources, "risk_sizing", "risk_review_count") or 0),
        "paper_size_eligible_count": int(
            _metric(sources, "risk_sizing", "paper_size_eligible_count") or 0
        ),
        "staged_order_count": int(
            _metric(sources, "paper_order_staging", "staged_order_count") or 0
        ),
        "dry_run_receipt_count": int(
            _metric(sources, "alpaca_paper_dry_run", "dry_run_receipt_count") or 0
        ),
        "submitted_paper_order_count": int(
            _metric(sources, "position_monitor", "submitted_order_count") or 0
        ),
        "broker_receipt_count": int(
            _metric(sources, "paper_submit_enablement", "paper_order_submitted_count") or 0
        ),
        "open_position_count": int(_metric(sources, "position_monitor", "open_position_count") or 0),
        "position_open_lifecycle_satisfied": position_open_lifecycle_satisfied,
        "position_open_lifecycle_count": 1 if position_open_lifecycle_satisfied else 0,
        "closed_trade_count": int(_metric(sources, "position_monitor", "closed_trade_count") or 0),
        "postmortem_due_count": int(
            _metric(sources, "position_monitor", "postmortem_due_count") or 0
        ),
        "telegram_dashboard_sync_status": (
            "ok"
            if "dashboard_backend_parity_error" not in blockers
            and "dashboard_unsafe_control_present" not in blockers
            else "blocked"
        ),
        "dashboard_backend_parity_error_count": int(
            _metric(sources, "system_map", "backend_parity_error_count") or 0
        ),
        "dashboard_unsafe_control_count": int(
            _metric(sources, "system_map", "unsafe_control_count") or 0
        ),
        "broker_post_called_count": int(
            _metric(sources, "paper_submit_enablement", "broker_post_called_count") or 0
        ),
        "alpaca_post_called_count": int(
            _metric(sources, "paper_submit_enablement", "alpaca_post_called_count") or 0
        ),
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "telegram_live_notifications_allowed_count": 0,
        "position_monitor_write_authority_count": int(
            _metric(sources, "position_monitor", "position_monitor_write_authority_count") or 0
        ),
        "position_close_allowed_count": int(
            _metric(sources, "position_monitor", "position_close_allowed_count") or 0
        ),
        "position_resize_allowed_count": int(
            _metric(sources, "position_monitor", "position_resize_allowed_count") or 0
        ),
        "order_cancel_allowed_count": int(
            _metric(sources, "position_monitor", "order_cancel_allowed_count") or 0
        ),
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled_count": int(
            _metric(sources, "paper_submit_enablement", "live_capital_enabled_count") or 0
        ),
        "phase7_proof_credit_allowed_count": 0,
        "secret_value_exposed_count": sum(
            1 for record in records if record.get("secret_value_exposed") is not False
        ),
        "raw_payload_exposed_count": sum(
            1 for record in records if record.get("raw_payload_exposed") is not False
        ),
        "local_path_exposed_count": sum(
            1 for record in records if record.get("local_path_exposed") is not False
        ),
        "authorization_header_exposed_count": sum(
            1 for record in records if record.get("authorization_header_exposed") is not False
        ),
        "broker_order_identifier_exposed_count": sum(
            1 for record in records if record.get("broker_order_identifier_exposed") is not False
        ),
        "records": records,
    }
    for field in PAPER_TRADE_DRILL_COUNT_FIELDS:
        bundle.setdefault(field, 0)
    bundle["validation_errors"] = validate_phase5_paper_trade_drill_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def validate_phase5_paper_trade_drill_step(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != PHASE5_ARTIFACT_SCHEMA_VERSION:
        errors.append("step_schema_version_mismatch")
    if record.get("paper_trade_drill_schema_version") != PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION:
        errors.append("step_drill_schema_version_mismatch")
    if record.get("artifact_type") != "phase5_paper_trade_drill_step":
        errors.append("step_artifact_type_mismatch")
    if record.get("phase") != "Q5" or record.get("stage") != "Q5-14":
        errors.append("step_phase_stage_mismatch")
    if record.get("public_safe") is not True:
        errors.append("step_not_public_safe")
    if record.get("event_log_required") is not True:
        errors.append("step_event_log_not_required")
    if not isinstance(record.get("event_log_written"), bool):
        errors.append("step_event_log_written_not_bool")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("step_event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("step_event_log_path_missing")
    if record.get("step_key") not in PAPER_TRADE_DRILL_REQUIRED_STEPS:
        errors.append("step_key_invalid")
    if record.get("display_status") != record.get("backend_status"):
        errors.append("step_display_backend_mismatch")
    if record.get("display_derived_from_backend") is not True:
        errors.append("step_display_not_backend_derived")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("step_ui_inferred_readiness")
    if record.get("step_passed") is True and record.get("blocked_reason") is not None:
        errors.append("step_passed_with_blocker")
    if record.get("step_passed") is not True and not str(record.get("blocked_reason") or "").strip():
        errors.append("step_blocked_without_reason")
    if record.get("phase5_test_trade") is not True:
        errors.append("step_not_tagged_phase5_test_trade")
    if record.get("phase7_proof_credit_allowed") is not False:
        errors.append("step_phase7_credit_allowed")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"step_phase5_authority_enabled:{field}")
    for field in PAPER_TRADE_DRILL_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"step_boundary_enabled:{field}")
    for exposure in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(exposure) is not False:
            errors.append(f"step_exposure_enabled:{exposure}")
    if (
        "cannot bypass explicit paper-submit approval" not in str(record.get("boundary") or "")
        or "cannot enable live capital" not in str(record.get("boundary") or "")
    ):
        errors.append("step_boundary_weak")
    return sorted(set(errors))


def validate_phase5_paper_trade_drill_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "paper_trade_drill_state",
        "paper_trade_drill_complete",
        "phase5_paper_trade_drill_implementation_ready",
        "phase5_paper_trade_drill_exit_gate_passed",
        "phase7_proof_credit_allowed",
        "blocker_count",
        "blockers",
        "step_count",
        "required_step_count",
        "required_steps",
        "source_bundles",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_paper_trade_drill_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-14":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_not_public_safe")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("step_count") != len(records):
        errors.append("step_count_mismatch")
    if bundle.get("required_step_count") != len(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("required_step_count_mismatch")
    if list(bundle.get("required_steps", [])) != list(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("required_steps_mismatch")
    step_keys = [record.get("step_key") for record in records if isinstance(record, dict)]
    if step_keys != list(PAPER_TRADE_DRILL_REQUIRED_STEPS):
        errors.append("record_step_order_mismatch")
    blockers = bundle.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_not_list")
        blockers = []
    if bundle.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if bundle.get("step_blocker_count") != len(bundle.get("step_blockers", [])):
        errors.append("step_blocker_count_mismatch")
    if bundle.get("paper_trade_drill_complete") is True:
        if blockers:
            errors.append("drill_complete_with_blockers")
        if bundle.get("phase5_paper_trade_drill_exit_gate_passed") is not True:
            errors.append("drill_complete_without_exit_gate")
        for field in (
            "paper_submit_path_available_count",
            "staged_order_count",
            "dry_run_receipt_count",
            "submitted_paper_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(bundle.get(field, 0) or 0) < 1:
                errors.append(f"drill_complete_missing_count:{field}")
        if bundle.get("position_open_lifecycle_satisfied") is not True:
            errors.append("drill_complete_missing_position_open_lifecycle")
    else:
        if bundle.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
            errors.append("blocked_drill_exit_gate_not_false")
    if (
        bundle.get("paper_submit_approval_present") is not True
        and bundle.get("phase5_paper_trade_drill_exit_gate_passed") is True
    ):
        errors.append("exit_gate_without_paper_submit_approval")
    if (
        int(bundle.get("paper_submit_path_available_count", 0) or 0) <= 0
        and bundle.get("phase5_paper_trade_drill_exit_gate_passed") is True
    ):
        errors.append("exit_gate_without_submit_path")
    if bundle.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_credit_allowed")
    if int(bundle.get("phase7_proof_credit_allowed_count", 0) or 0) != 0:
        errors.append("phase7_credit_allowed_count_nonzero")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in (
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
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
        "broker_order_identifier_exposed_count",
    ):
        if int(bundle.get(field, 0) or 0) != 0:
            errors.append(f"bundle_unsafe_count_nonzero:{field}")
    if int(bundle.get("broker_post_called_count", 0) or 0) != 0 and (
        bundle.get("phase5_paper_trade_drill_exit_gate_passed") is not True
    ):
        errors.append("broker_post_before_exit_gate")
    if int(bundle.get("alpaca_post_called_count", 0) or 0) != 0 and (
        bundle.get("phase5_paper_trade_drill_exit_gate_passed") is not True
    ):
        errors.append("alpaca_post_before_exit_gate")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("source_validation_error_count") != sum(
        int(snapshot.get("validation_error_count", 0) or 0)
        for snapshot in bundle.get("source_bundles", {}).values()
        if isinstance(snapshot, dict)
    ):
        errors.append("source_validation_error_count_mismatch")
    if bundle.get("dashboard_backend_parity_error_count") != 0:
        errors.append("dashboard_backend_parity_errors")
    if bundle.get("dashboard_unsafe_control_count") != 0:
        errors.append("dashboard_unsafe_controls")
    for record in records:
        if not isinstance(record, dict):
            errors.append("step_record_not_dict")
            continue
        errors.extend(validate_phase5_paper_trade_drill_step(record))
    if (
        "cannot bypass explicit paper-submit approval" not in str(bundle.get("boundary") or "")
        or "cannot call brokers or venues" not in str(bundle.get("boundary") or "")
        or "cannot enable live capital" not in str(bundle.get("boundary") or "")
        or "cannot count toward Phase 7 proof" not in str(bundle.get("boundary") or "")
    ):
        errors.append("bundle_boundary_weak")
    return sorted(set(errors))


def attach_phase5_paper_trade_drill_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PAPER_TRADE_DRILL_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            PAPER_TRADE_DRILL_EVENT_TYPE,
            PAPER_TRADE_DRILL_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "step_key": record.get("step_key"),
                "step_order": record.get("step_order"),
                "source_key": record.get("source_key"),
                "backend_metric_name": record.get("backend_metric_name"),
                "backend_metric_value": record.get("backend_metric_value"),
                "backend_status": record.get("backend_status"),
                "display_status": record.get("display_status"),
                "step_passed": record.get("step_passed"),
                "blocked_reason": record.get("blocked_reason"),
                "broker_post_called": record.get("broker_post_called"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "phase7_proof_credit_allowed": record.get("phase7_proof_credit_allowed"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_paper_trade_drill_step(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_paper_trade_drill_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def write_phase5_paper_trade_drill(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = paper_trade_drill_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_paper_trade_drill_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_paper_trade_drill_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_paper_trade_drill_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PAPER_TRADE_DRILL_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "paper_trade_drill_state": output.get("paper_trade_drill_state"),
        "paper_trade_drill_complete": output.get("paper_trade_drill_complete"),
        "phase5_paper_trade_drill_exit_gate_passed": output.get(
            "phase5_paper_trade_drill_exit_gate_passed"
        ),
        "blocker_count": output.get("blocker_count"),
        "step_count": output.get("step_count"),
        "paper_submit_approval_present": output.get("paper_submit_approval_present"),
        "paper_submit_path_available_count": output.get("paper_submit_path_available_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "open_position_count": output.get("open_position_count"),
        "closed_trade_count": output.get("closed_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "broker_post_called_count": output.get("broker_post_called_count"),
        "live_capital_enabled_count": output.get("live_capital_enabled_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
