"""Q5-6 paper-order staging gate.

This module creates replayable `staged_paper_order` gate records from Q5-3 risk
reviews, Q5-4 kill-switch state, and Q5-5 execution-adapter status. A staged
paper order can exist only after policy, risk, kill-switch, source, venue,
order-field, idempotency, Event Log prewrite, and reconciliation prerequisites
pass. In the current runtime state Q5-3 has no paper-size-eligible reviews, so
Q5-6 records blocked staging gates and creates zero staged orders.
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
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION = 1
PAPER_ORDER_STAGING_RUNTIME_ARTIFACT = "phase5_paper_order_staging_gate.json"
PAPER_ORDER_STAGING_HISTORY = "phase5_paper_order_staging_gate_history.jsonl"
PAPER_ORDER_STAGING_EVENT_LOG = "phase5_paper_order_staging_events.jsonl"
PAPER_ORDER_STAGING_EVENT_TYPE = "phase5_paper_order_staging_gate_written"
PAPER_ORDER_STAGING_COMPONENT = "phase5_paper_order_staging_gate"
PAPER_ORDER_STAGING_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_risk_sizing_reviews.json",
    "data/runtime/phase5_kill_switch_ledger.json",
    "data/runtime/phase5_execution_adapter_status.json",
    "data/runtime/phase5_approval_policy_decisions.json",
    "data/runtime/paper_account_snapshots.jsonl",
)

PAPER_ORDER_STAGING_REQUIRED_CHECKS: tuple[str, ...] = (
    "approval_policy_eligible",
    "risk_sizing_eligible",
    "paper_size_positive",
    "source_posture_valid",
    "decision_source_coverage_complete",
    "kill_switch_ledger_valid",
    "kill_switch_clear",
    "execution_adapter_bundle_valid",
    "venue_read_ready",
    "venue_write_blocked",
    "instrument_valid",
    "side_valid",
    "quantity_positive",
    "order_type_valid",
    "limit_stop_fields_valid",
    "time_in_force_valid",
    "invalidation_present",
    "max_loss_within_risk",
    "idempotency_seed_valid",
    "event_log_prewrite_ready",
    "reconciliation_prerequisites_recorded",
    "submission_separated",
)

PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES: tuple[str, ...] = (
    "event_log_prewrite_recorded",
    "idempotency_key_allocated",
    "pre_trade_snapshot_available",
    "duplicate_order_guard_ready",
    "broker_echo_not_required_until_submit",
    "post_submit_reconciliation_not_required_until_submit",
    "postmortem_link_seeded",
    "paper_account_write_authority_false",
)

PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS: tuple[str, ...] = (
    "risk_review_retracted_or_repaired",
    "active_kill_switch_after_staging",
    "venue_status_degraded_after_staging",
    "paper_account_state_changed_before_submit",
    "market_session_closed_before_submit",
    "idempotency_collision_detected",
    "operator_cancels_before_submit",
)

PAPER_ORDER_STAGING_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "paper_execution_allowed",
    "paper_order_allowed",
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
    "submission_allowed",
    "broker_submit_ready",
)

PAPER_ORDER_STAGING_COUNT_FIELDS: tuple[str, ...] = (
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
    "broker_submit_receipt_created_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "crypto_perps_write_allowed_count",
)

PAPER_ORDER_STAGING_BOUNDARY = (
    "Q5-6 paper-order staging gates can create a staged paper-order record only "
    "after policy, risk, kill-switch, source, venue, order-field, idempotency, "
    "Event Log prewrite, and reconciliation prerequisites pass. Staging is not "
    "broker submit: this stage cannot submit paper orders, write brokers, call "
    "prediction-market write endpoints, send live alerts, create positions, or "
    "enable live capital."
)

SIGNAL_INTEGRITY_RISK_BLOCKER_PREFIXES: tuple[str, ...] = (
    "signal_",
    "signal_integrity",
)
SOURCE_POSTURE_CHECKS: frozenset[str] = frozenset(
    {
        "source_posture_valid",
        "decision_source_coverage_complete",
    }
)
KILL_SWITCH_CHECKS: frozenset[str] = frozenset(
    {
        "kill_switch_ledger_valid",
        "kill_switch_clear",
    }
)
EXECUTION_ADAPTER_CHECKS: frozenset[str] = frozenset(
    {
        "execution_adapter_bundle_valid",
        "venue_read_ready",
        "venue_write_blocked",
    }
)
ORDER_FIELD_CHECKS: frozenset[str] = frozenset(
    {
        "instrument_valid",
        "side_valid",
        "quantity_positive",
        "order_type_valid",
        "limit_stop_fields_valid",
        "time_in_force_valid",
        "invalidation_present",
        "max_loss_within_risk",
    }
)
IDEMPOTENCY_AND_PREWRITE_CHECKS: frozenset[str] = frozenset(
    {
        "idempotency_seed_valid",
        "event_log_prewrite_ready",
        "reconciliation_prerequisites_recorded",
        "submission_separated",
    }
)
STAGING_PRIMARY_CAUSE_PRIORITY: tuple[str, ...] = (
    "global_context",
    "approval_policy",
    "signal_integrity",
    "risk_sizing",
    "source_posture",
    "kill_switch",
    "execution_adapter",
    "order_fields",
    "idempotency_prewrite",
    "unknown",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _risk_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / RISK_SIZING_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_risk_sizing_reviews(settings=settings)


def _kill_switch_bundle(settings: Settings | None = None) -> dict[str, Any] | None:
    return _read_json(_runtime_dir(settings) / KILL_SWITCH_RUNTIME_ARTIFACT)


def _execution_adapter_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / EXECUTION_ADAPTER_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_execution_adapter_status(settings=settings)


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-6"
    ledger["boundary"] = (
        "Q5-6 records paper-order staging gates only. Paper-order submission, "
        "broker writes, prediction-market writes, positions, and live capital stay false."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _selected_venue(primary_instrument: str) -> str:
    if primary_instrument == "prediction_markets":
        return "prediction_market_router"
    return "alpaca_paper"


def _adapter_by_venue(adapter_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(status.get("venue_key") or ""): status
        for status in adapter_bundle.get("statuses", [])
        if isinstance(status, dict)
    }


def _matched_kill_switches(
    *,
    kill_bundle: dict[str, Any] | None,
    strategy_key: str,
    instrument: str,
    venue: str,
) -> dict[str, Any]:
    scopes = {
        "global:all",
        f"strategy_family:{strategy_key}",
        f"instrument:{instrument}",
        f"venue:{venue}",
    }
    if venue == "alpaca_paper":
        scopes.add("broker_adapter:alpaca")
    if venue == "prediction_market_router":
        scopes.add("prediction_market_adapter:pmxt_polyrouter")
    if kill_bundle is None:
        return {
            "ledger_present": False,
            "validation_error_count": 1,
            "matched_scopes": sorted(scopes),
            "active_switches": sorted(scopes),
            "clear": False,
            "blockers": ["kill_switch_ledger_missing_fail_closed"],
        }
    validation_errors = validate_phase5_kill_switch_ledger(kill_bundle)
    switches = [
        switch
        for switch in kill_bundle.get("switches", [])
        if isinstance(switch, dict) and switch.get("switch_scope") in scopes
    ]
    active = [
        str(switch.get("switch_scope") or "unknown")
        for switch in switches
        if switch.get("switch_active") is True or switch.get("blocks_new_actions") is True
    ]
    blockers = []
    if validation_errors:
        blockers.append("kill_switch_ledger_validation_failed")
    blockers.extend(f"active_kill_switch:{scope}" for scope in active)
    return {
        "ledger_present": True,
        "validation_error_count": len(validation_errors),
        "matched_scopes": sorted(scopes),
        "matched_switch_count": len(switches),
        "active_switches": sorted(active),
        "clear": not blockers,
        "blockers": sorted(dict.fromkeys(blockers)),
    }


def _order_fields(review: dict[str, Any], selected_venue: str) -> dict[str, Any]:
    proposed_risk_gbp = _float(review.get("proposed_risk_gbp"), 0.0)
    eligible_for_alpaca_staging = (
        review.get("paper_size_eligible") is True
        and proposed_risk_gbp > 0.0
        and selected_venue == "alpaca_paper"
    )
    idempotency_seed_material = "|".join(
        (
            "q5-6",
            str(review.get("artifact_id") or "unknown"),
            str(review.get("strategy_family_key") or "unknown_strategy"),
            str(review.get("primary_instrument") or "unknown_instrument"),
            selected_venue,
            f"{proposed_risk_gbp:.2f}",
        )
    )
    idempotency_seed = hashlib.sha256(idempotency_seed_material.encode("utf-8")).hexdigest()
    invalidation_conditions = [
        str(item) for item in review.get("invalidation_conditions", []) or []
    ]
    invalidation = invalidation_conditions[0] if invalidation_conditions else ""
    idempotency_key = f"q5-6-stage-{idempotency_seed[:24]}" if eligible_for_alpaca_staging else None
    return {
        "instrument": str(review.get("primary_instrument") or "unknown_instrument"),
        "side": "buy" if eligible_for_alpaca_staging else "not_determined",
        "quantity": 1.0 if eligible_for_alpaca_staging else 0.0,
        "notional_gbp": proposed_risk_gbp if eligible_for_alpaca_staging else 0.0,
        "order_type": "market" if eligible_for_alpaca_staging else "not_applicable",
        "limit_price": None,
        "stop_price": None,
        "time_in_force": "day" if eligible_for_alpaca_staging else "not_applicable",
        "max_loss_gbp": proposed_risk_gbp,
        "risk_size_gbp": proposed_risk_gbp,
        "invalidation": invalidation,
        "idempotency_seed": idempotency_seed,
        "idempotency_key": idempotency_key,
    }


def _prewrite_payload(
    *,
    artifact_id: str,
    strategy_key: str,
    selected_venue: str,
    order_fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
        "prewrite_type": "paper_order_staging_prewrite",
        "artifact_id": artifact_id,
        "strategy_family_key": strategy_key,
        "selected_venue": selected_venue,
        "instrument": order_fields["instrument"],
        "side": order_fields["side"],
        "quantity": order_fields["quantity"],
        "order_type": order_fields["order_type"],
        "idempotency_seed": order_fields["idempotency_seed"],
        "submission_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }


def _failed_check_names(checks: list[dict[str, Any]]) -> set[str]:
    return {
        str(check.get("name") or "")
        for check in checks
        if isinstance(check, dict) and check.get("passed") is False
    }


def _signal_integrity_risk_blockers(risk_review: dict[str, Any]) -> list[str]:
    blockers = risk_review.get("risk_blockers", [])
    if not isinstance(blockers, list):
        return []
    return [
        str(blocker)
        for blocker in blockers
        if isinstance(blocker, str)
        and (
            blocker == "signal_integrity_passed"
            or blocker.startswith(SIGNAL_INTEGRITY_RISK_BLOCKER_PREFIXES)
        )
    ]


def _blocked_diagnostics(
    *,
    risk_review: dict[str, Any],
    checks: list[dict[str, Any]],
    global_errors: list[str],
    kill_context: dict[str, Any],
) -> dict[str, Any]:
    failed_checks = _failed_check_names(checks)
    signal_integrity_blockers = _signal_integrity_risk_blockers(risk_review)
    approval_policy_blocked = str(risk_review.get("approval_policy_status") or "") != "eligible"
    risk_sizing_blocked = (
        risk_review.get("paper_size_eligible") is not True
        or str(risk_review.get("risk_decision") or "") != "paper_size_eligible"
    )
    diagnostics = {
        "blocked_by_global_context": bool(global_errors),
        "blocked_by_approval_policy": approval_policy_blocked,
        "blocked_by_signal_integrity": bool(signal_integrity_blockers),
        "blocked_by_risk_sizing": risk_sizing_blocked,
        "blocked_by_source_posture": bool(failed_checks & SOURCE_POSTURE_CHECKS),
        "blocked_by_kill_switch": (
            bool(failed_checks & KILL_SWITCH_CHECKS)
            or bool(kill_context.get("blockers"))
            or int(kill_context.get("validation_error_count", 0) or 0) > 0
        ),
        "blocked_by_execution_adapter": bool(failed_checks & EXECUTION_ADAPTER_CHECKS),
        "blocked_by_order_fields": bool(failed_checks & ORDER_FIELD_CHECKS),
        "blocked_by_idempotency_prewrite": bool(failed_checks & IDEMPOTENCY_AND_PREWRITE_CHECKS),
        "signal_integrity_blockers": signal_integrity_blockers,
    }
    cause_details = {
        "global_context": sorted(dict.fromkeys(str(item) for item in global_errors)),
        "approval_policy": (
            [f"approval_policy_status:{risk_review.get('approval_policy_status')}"]
            if approval_policy_blocked
            else []
        ),
        "signal_integrity": signal_integrity_blockers,
        "risk_sizing": (
            [
                f"risk_decision:{risk_review.get('risk_decision')}",
                f"paper_size_eligible:{risk_review.get('paper_size_eligible')}",
            ]
            if risk_sizing_blocked
            else []
        ),
        "source_posture": sorted(failed_checks & SOURCE_POSTURE_CHECKS),
        "kill_switch": sorted(
            dict.fromkeys(
                list(failed_checks & KILL_SWITCH_CHECKS)
                + [str(item) for item in kill_context.get("blockers", []) or []]
            )
        ),
        "execution_adapter": sorted(failed_checks & EXECUTION_ADAPTER_CHECKS),
        "order_fields": sorted(failed_checks & ORDER_FIELD_CHECKS),
        "idempotency_prewrite": sorted(failed_checks & IDEMPOTENCY_AND_PREWRITE_CHECKS),
        "unknown": [],
    }
    primary_cause = "not_blocked"
    primary_cause_details: list[str] = []
    for cause in STAGING_PRIMARY_CAUSE_PRIORITY:
        if diagnostics.get(f"blocked_by_{cause}") is True:
            primary_cause = cause
            primary_cause_details = cause_details.get(cause, [])
            break
    if primary_cause == "not_blocked" and any(
        value is True for key, value in diagnostics.items() if key.startswith("blocked_by_")
    ):
        primary_cause = "unknown"
        primary_cause_details = cause_details["unknown"]
    diagnostics["blocked_primary_cause"] = primary_cause
    diagnostics["blocked_primary_cause_details"] = primary_cause_details[:8]
    return diagnostics


def _staging_gate_record(
    risk_review: dict[str, Any],
    *,
    kill_bundle: dict[str, Any] | None,
    adapter_bundle: dict[str, Any],
    settings: Settings,
    generated_at: str,
    global_errors: list[str],
) -> dict[str, Any]:
    strategy_key = str(risk_review.get("strategy_family_key") or "unknown_strategy")
    primary_instrument = str(risk_review.get("primary_instrument") or "unknown_instrument")
    selected_venue = _selected_venue(primary_instrument)
    adapter_status = _adapter_by_venue(adapter_bundle).get(selected_venue, {})
    kill_context = _matched_kill_switches(
        kill_bundle=kill_bundle,
        strategy_key=strategy_key,
        instrument=primary_instrument,
        venue=selected_venue,
    )
    order_fields = _order_fields(risk_review, selected_venue)
    artifact_id = f"phase5:q5-6:paper-order-staging:{_safe_key(strategy_key)}"
    source_summary = risk_review.get("source_summary", {})
    if not isinstance(source_summary, dict):
        source_summary = {}
    max_loss_gbp = _float(order_fields["max_loss_gbp"], 0.0)
    proposed_risk_gbp = _float(risk_review.get("proposed_risk_gbp"), 0.0)
    checks = [
        _check("global_context_validated", not global_errors, detail=global_errors),
        _check("approval_policy_eligible", risk_review.get("approval_policy_status") == "eligible"),
        _check("risk_sizing_eligible", risk_review.get("paper_size_eligible") is True),
        _check("paper_size_positive", proposed_risk_gbp > 0.0),
        _check(
            "source_posture_valid",
            source_summary.get("source_weights_normalized") is True
            and not source_summary.get("zero_weight_sources"),
        ),
        _check(
            "decision_source_coverage_complete",
            source_summary.get("canonical_source_count") == EXPECTED_SOURCE_COUNT
            and source_summary.get("all_canonical_sources_considered") is True
            and source_summary.get("decision_source_usage_complete") is True
            and source_summary.get("source_quorum_bypass_allowed") is False,
        ),
        _check("kill_switch_ledger_valid", kill_context["validation_error_count"] == 0),
        _check("kill_switch_clear", kill_context["clear"]),
        _check("execution_adapter_bundle_valid", not validate_phase5_execution_adapter_status_bundle(adapter_bundle)),
        _check("venue_read_ready", adapter_status.get("read_health") == "read_only_available"),
        _check("venue_write_blocked", str(adapter_status.get("write_health") or "").startswith("blocked")),
        _check("instrument_valid", bool(primary_instrument) and primary_instrument != "unknown_instrument"),
        _check("side_valid", order_fields["side"] in {"buy", "sell"}),
        _check("quantity_positive", _float(order_fields["quantity"], 0.0) > 0.0),
        _check("order_type_valid", order_fields["order_type"] in {"market", "limit", "stop", "stop_limit"}),
        _check(
            "limit_stop_fields_valid",
            order_fields["order_type"] == "market"
            or order_fields["limit_price"] is not None
            or order_fields["stop_price"] is not None,
        ),
        _check("time_in_force_valid", order_fields["time_in_force"] in {"day", "gtc", "opg", "cls", "ioc", "fok"}),
        _check("invalidation_present", bool(order_fields["invalidation"])),
        _check("max_loss_within_risk", 0.0 < max_loss_gbp <= proposed_risk_gbp),
        _check("idempotency_seed_valid", len(order_fields["idempotency_seed"]) == 64),
        _check("event_log_prewrite_ready", bool(order_fields["idempotency_key"])),
        _check("reconciliation_prerequisites_recorded", True),
        _check("submission_separated", True),
    ]
    blockers = [
        check["name"]
        for check in checks
        if not check["passed"] and check["name"] != "global_context_validated"
    ]
    blockers.extend(global_errors)
    blockers.extend(kill_context["blockers"])
    blockers = sorted(dict.fromkeys(blockers))
    staged = not blockers
    order_state = "staged_ready_for_dry_run" if staged else "blocked_not_staged"
    blocked_diagnostics = _blocked_diagnostics(
        risk_review=risk_review,
        checks=checks,
        global_errors=global_errors,
        kill_context=kill_context,
    )
    if staged:
        blocked_diagnostics.update(
            {
                "blocked_by_global_context": False,
                "blocked_by_approval_policy": False,
                "blocked_by_signal_integrity": False,
                "blocked_by_risk_sizing": False,
                "blocked_by_source_posture": False,
                "blocked_by_kill_switch": False,
                "blocked_by_execution_adapter": False,
                "blocked_by_order_fields": False,
                "blocked_by_idempotency_prewrite": False,
                "blocked_primary_cause": "not_blocked",
                "blocked_primary_cause_details": [],
            }
        )
    prewrite_payload = _prewrite_payload(
        artifact_id=artifact_id,
        strategy_key=strategy_key,
        selected_venue=selected_venue,
        order_fields=order_fields,
    )
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "paper_order_staging_schema_version": PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_type": "staged_paper_order",
        "artifact_id": artifact_id,
        "phase": "Q5",
        "stage": "Q5-6",
        "status": "staged" if staged else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PAPER_ORDER_STAGING_SOURCE_REFS),
        "boundary": PAPER_ORDER_STAGING_BOUNDARY,
        **phase5_authority_defaults(),
        "source_risk_sizing_artifact_id": risk_review.get("artifact_id"),
        "strategy_family_key": strategy_key,
        "approval_policy_status": risk_review.get("approval_policy_status"),
        "risk_decision": risk_review.get("risk_decision"),
        "paper_size_eligible": risk_review.get("paper_size_eligible") is True,
        "proposed_risk_gbp": proposed_risk_gbp,
        "max_risk_gbp": _float(risk_review.get("max_risk_gbp"), 0.0),
        "selected_venue": selected_venue,
        "execution_adapter_status": adapter_status.get("status", "missing"),
        "execution_adapter_read_health": adapter_status.get("read_health", "missing"),
        "execution_adapter_write_health": adapter_status.get("write_health", "missing"),
        "order_state": order_state,
        "instrument": order_fields["instrument"],
        "side": order_fields["side"],
        "quantity": order_fields["quantity"],
        "notional_gbp": order_fields["notional_gbp"],
        "order_type": order_fields["order_type"],
        "limit_price": order_fields["limit_price"],
        "stop_price": order_fields["stop_price"],
        "time_in_force": order_fields["time_in_force"],
        "max_loss_gbp": order_fields["max_loss_gbp"],
        "risk_size_gbp": order_fields["risk_size_gbp"],
        "invalidation": order_fields["invalidation"],
        "idempotency_seed": order_fields["idempotency_seed"],
        "idempotency_key": order_fields["idempotency_key"],
        "idempotency_material": {
            "stage": "Q5-6",
            "source_risk_sizing_artifact_id": str(risk_review.get("artifact_id") or "unknown"),
            "strategy_family_key": strategy_key,
            "selected_venue": selected_venue,
            "instrument": order_fields["instrument"],
            "side": order_fields["side"],
            "quantity": f"{_float(order_fields['quantity'], 0.0):.8f}",
            "order_type": order_fields["order_type"],
            "time_in_force": order_fields["time_in_force"],
            "max_loss_gbp": f"{_float(order_fields['max_loss_gbp'], 0.0):.2f}",
            "idempotency_seed": order_fields["idempotency_seed"],
        },
        "staging_allowed": staged,
        "submission_allowed": False,
        "broker_submit_ready": False,
        "event_log_prewrite_required": True,
        "event_log_prewrite_ready": staged,
        "event_log_prewrite_payload": prewrite_payload,
        "event_log_prewrite_fingerprint": hashlib.sha256(
            json.dumps(prewrite_payload, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "reconciliation_prerequisites": list(PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES),
        "reconciliation_prerequisite_count": len(PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES),
        "cancellation_conditions": list(PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS),
        "cancellation_condition_count": len(PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS),
        "required_checks": list(PAPER_ORDER_STAGING_REQUIRED_CHECKS),
        "required_check_count": len(PAPER_ORDER_STAGING_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
        "blocked_reasons": blockers,
        "blocked_reason_count": len(blockers),
        **blocked_diagnostics,
        "kill_switch_clear": kill_context["clear"],
        "kill_switch_matched_scopes": kill_context["matched_scopes"],
        "kill_switch_active_switches": kill_context["active_switches"],
        "kill_switch_validation_error_count": kill_context["validation_error_count"],
        "source_summary": source_summary,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "risk_approval_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "paper_execution_allowed": False,
        "paper_order_allowed": False,
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
    record["validation_errors"] = validate_phase5_paper_order_staging_record(record)
    return record


def build_phase5_paper_order_staging_gate(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    risk_bundle = _risk_bundle(settings)
    kill_bundle = _kill_switch_bundle(settings)
    adapter_bundle = _execution_adapter_bundle(settings)
    generated_at = _now()
    global_errors: list[str] = []
    if validate_phase5_risk_sizing_bundle(risk_bundle):
        global_errors.append("risk_sizing_bundle_validation_failed")
    if kill_bundle is None:
        global_errors.append("kill_switch_ledger_missing")
    elif validate_phase5_kill_switch_ledger(kill_bundle):
        global_errors.append("kill_switch_ledger_validation_failed")
    if validate_phase5_execution_adapter_status_bundle(adapter_bundle):
        global_errors.append("execution_adapter_bundle_validation_failed")
    records = [
        _staging_gate_record(
            review,
            kill_bundle=kill_bundle,
            adapter_bundle=adapter_bundle,
            settings=settings,
            generated_at=generated_at,
            global_errors=global_errors,
        )
        for review in risk_bundle.get("reviews", [])
        if isinstance(review, dict)
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    order_state_counts = Counter(str(record.get("order_state") or "unknown") for record in records)
    blocked_primary_cause_counts = Counter(
        str(record.get("blocked_primary_cause") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    bundle = {
        "schema_version": PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_type": "phase5_paper_order_staging_gate_bundle",
        "artifact_id": "phase5:q5-6:paper-order-staging-gate",
        "phase": "Q5",
        "stage": "Q5-6",
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
        "provenance": phase5_provenance(PAPER_ORDER_STAGING_SOURCE_REFS),
        "boundary": PAPER_ORDER_STAGING_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "risk_review_count": len(risk_bundle.get("reviews", []) or []),
        "paper_size_eligible_count": int(risk_bundle.get("paper_size_eligible_count", 0) or 0),
        "staging_record_count": len(records),
        "staged_order_count": status_counts.get("staged", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "cancelled_count": status_counts.get("cancelled", 0),
        "failed_reconciliation_count": status_counts.get("failed_reconciliation", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "order_state_counts": dict(sorted(order_state_counts.items())),
        "blocked_primary_cause_counts": dict(sorted(blocked_primary_cause_counts.items())),
        "required_check_count": len(PAPER_ORDER_STAGING_REQUIRED_CHECKS),
        "reconciliation_prerequisite_count": len(PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES),
        "cancellation_condition_count": len(PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS),
        "global_error_count": len(global_errors),
        "global_errors": sorted(dict.fromkeys(global_errors)),
        "records": records,
    }
    for field in PAPER_ORDER_STAGING_COUNT_FIELDS:
        bundle[field] = 0
    bundle["validation_errors"] = validate_phase5_paper_order_staging_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _staging_status_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = str(record.get("status") or "missing")
    blocked_flags = {
        "global_context": record.get("blocked_by_global_context") is True,
        "approval_policy": record.get("blocked_by_approval_policy") is True,
        "signal_integrity": record.get("blocked_by_signal_integrity") is True,
        "risk_sizing": record.get("blocked_by_risk_sizing") is True,
        "source_posture": record.get("blocked_by_source_posture") is True,
        "kill_switch": record.get("blocked_by_kill_switch") is True,
        "execution_adapter": record.get("blocked_by_execution_adapter") is True,
        "order_fields": record.get("blocked_by_order_fields") is True,
        "idempotency_prewrite": record.get("blocked_by_idempotency_prewrite") is True,
    }
    primary_cause = str(record.get("blocked_primary_cause") or "missing")
    primary_cause_details = record.get("blocked_primary_cause_details", [])
    if not isinstance(primary_cause_details, list):
        errors.append("blocked_primary_cause_details_not_list")
        primary_cause_details = []
    blockers = record.get("blocked_reasons", [])
    if not isinstance(blockers, list):
        errors.append("blocked_reasons_not_list")
        blockers = []
    if record.get("blocked_reason_count") != len(blockers):
        errors.append("blocked_reason_count_mismatch")
    if status == "staged":
        if any(blocked_flags.values()):
            errors.append("staged_order_has_blocked_flags")
        if primary_cause != "not_blocked":
            errors.append("staged_order_primary_cause_invalid")
        if primary_cause_details:
            errors.append("staged_order_primary_cause_details_present")
        if blockers:
            errors.append("staged_order_has_blockers")
        if record.get("paper_size_eligible") is not True:
            errors.append("staged_order_without_risk_eligibility")
        if record.get("kill_switch_clear") is not True:
            errors.append("staged_order_without_kill_switch_clear")
        if record.get("execution_adapter_read_health") != "read_only_available":
            errors.append("staged_order_without_venue_readiness")
        if record.get("staging_allowed") is not True:
            errors.append("staged_order_without_staging_allowed")
        if record.get("event_log_prewrite_ready") is not True:
            errors.append("staged_order_without_event_log_prewrite")
        source_summary = record.get("source_summary", {})
        if not isinstance(source_summary, dict):
            errors.append("staged_order_without_source_summary")
            source_summary = {}
        if source_summary.get("decision_source_usage_complete") is not True:
            errors.append("staged_order_without_decision_source_coverage")
        if source_summary.get("all_canonical_sources_considered") is not True:
            errors.append("staged_order_without_canonical_source_coverage")
        if source_summary.get("source_quorum_bypass_allowed") is not False:
            errors.append("staged_order_with_source_quorum_bypass")
        if not str(record.get("idempotency_key") or "").strip():
            errors.append("staged_order_without_idempotency_key")
        if _float(record.get("quantity"), 0.0) <= 0.0:
            errors.append("staged_order_without_positive_quantity")
        if record.get("side") not in {"buy", "sell"}:
            errors.append("staged_order_invalid_side")
        if record.get("order_type") not in {"market", "limit", "stop", "stop_limit"}:
            errors.append("staged_order_invalid_order_type")
    if status == "blocked":
        if not blockers:
            errors.append("blocked_staging_without_blockers")
        if not any(blocked_flags.values()):
            errors.append("blocked_staging_without_blocked_flags")
        if primary_cause not in STAGING_PRIMARY_CAUSE_PRIORITY:
            errors.append("blocked_primary_cause_invalid")
        elif blocked_flags.get(primary_cause) is not True:
            errors.append("blocked_primary_cause_flag_mismatch")
    if record.get("submission_allowed") is not False:
        errors.append("staging_submission_not_separated")
    if record.get("broker_submit_ready") is not False:
        errors.append("staging_broker_submit_ready")
    return errors


def validate_phase5_paper_order_staging_record(record: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-6"))
    if record.get("artifact_type") != "staged_paper_order":
        errors.append("artifact_type_not_staged_paper_order")
    if record.get("paper_order_staging_schema_version") != PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION:
        errors.append("paper_order_staging_schema_version_mismatch")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if record.get("required_check_count") != len(PAPER_ORDER_STAGING_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    check_names = {
        str(check.get("name") or "")
        for check in record.get("checks", [])
        if isinstance(check, dict)
    }
    for check in PAPER_ORDER_STAGING_REQUIRED_CHECKS:
        if check not in check_names:
            errors.append(f"required_check_missing:{check}")
    if record.get("reconciliation_prerequisite_count") != len(
        PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES
    ):
        errors.append("reconciliation_prerequisite_count_mismatch")
    if set(record.get("reconciliation_prerequisites", [])) != set(
        PAPER_ORDER_STAGING_RECONCILIATION_PREREQUISITES
    ):
        errors.append("reconciliation_prerequisites_mismatch")
    if record.get("cancellation_condition_count") != len(PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS):
        errors.append("cancellation_condition_count_mismatch")
    if set(record.get("cancellation_conditions", [])) != set(PAPER_ORDER_STAGING_CANCELLATION_CONDITIONS):
        errors.append("cancellation_conditions_mismatch")
    if len(str(record.get("idempotency_seed") or "")) != 64:
        errors.append("idempotency_seed_invalid")
    if len(str(record.get("event_log_prewrite_fingerprint") or "")) != 64:
        errors.append("event_log_prewrite_fingerprint_invalid")
    prewrite = record.get("event_log_prewrite_payload", {})
    if not isinstance(prewrite, dict):
        errors.append("event_log_prewrite_payload_invalid")
    else:
        for field in ("artifact_id", "strategy_family_key", "selected_venue", "idempotency_seed"):
            if field not in prewrite:
                errors.append(f"event_log_prewrite_payload_missing:{field}")
        for field in ("submission_allowed", "broker_write_allowed", "live_capital_enabled"):
            if prewrite.get(field) is not False:
                errors.append(f"event_log_prewrite_authority_enabled:{field}")
    for exposure in ("secret_value_exposed", "raw_payload_exposed", "local_path_exposed"):
        if record.get(exposure) is not False:
            errors.append(f"paper_order_staging_exposure_enabled:{exposure}")
    for field in PAPER_ORDER_STAGING_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"paper_order_staging_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    errors.extend(_staging_status_errors(record))
    return sorted(set(errors))


def validate_phase5_paper_order_staging_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "staging_record_count",
        "staged_order_count",
        "blocked_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_paper_order_staging_gate_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-6":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("staging_record_count") != len(records):
        errors.append("staging_record_count_mismatch")
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    if bundle.get("staged_order_count") != status_counts.get("staged", 0):
        errors.append("staged_order_count_mismatch")
    if bundle.get("blocked_count") != status_counts.get("blocked", 0):
        errors.append("blocked_count_mismatch")
    blocked_primary_cause_counts = Counter(
        str(record.get("blocked_primary_cause") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    if bundle.get("blocked_primary_cause_counts") != dict(sorted(blocked_primary_cause_counts.items())):
        errors.append("blocked_primary_cause_counts_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in PAPER_ORDER_STAGING_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("staging_record_not_dict")
            continue
        errors.extend(validate_phase5_paper_order_staging_record(record))
    return sorted(set(errors))


def attach_phase5_paper_order_staging_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PAPER_ORDER_STAGING_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            PAPER_ORDER_STAGING_EVENT_TYPE,
            PAPER_ORDER_STAGING_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "strategy_family_key": record.get("strategy_family_key"),
                "status": record.get("status"),
                "order_state": record.get("order_state"),
                "selected_venue": record.get("selected_venue"),
                "staging_allowed": record.get("staging_allowed"),
                "submission_allowed": record.get("submission_allowed"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "blocked_reason_count": record.get("blocked_reason_count"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_paper_order_staging_record(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_paper_order_staging_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_paper_order_staging_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
        runtime / PAPER_ORDER_STAGING_HISTORY,
        runtime / PAPER_ORDER_STAGING_EVENT_LOG,
    )


def write_phase5_paper_order_staging_gate(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_paper_order_staging_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_paper_order_staging_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_paper_order_staging_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_paper_order_staging_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "staging_record_count": output.get("staging_record_count"),
        "staged_order_count": output.get("staged_order_count"),
        "blocked_count": output.get("blocked_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
