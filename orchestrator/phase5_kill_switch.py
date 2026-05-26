"""Q5-4 kill-switch ledger.

This module creates replayable `kill_switch_event` artifacts for Phase 5 Layer B.
The ledger can only block future actions. It cannot grant kill-switch mutation
authority, execution authority, broker writes, notification sends, positions, or
live capital.
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
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_KILL_SWITCH_SCHEMA_VERSION = 1
KILL_SWITCH_RUNTIME_ARTIFACT = "phase5_kill_switch_ledger.json"
KILL_SWITCH_HISTORY = "phase5_kill_switch_ledger_history.jsonl"
KILL_SWITCH_EVENT_LOG = "phase5_kill_switch_events.jsonl"
KILL_SWITCH_EVENT_TYPE = "phase5_kill_switch_event_written"
KILL_SWITCH_COMPONENT = "phase5_kill_switch_ledger"
KILL_SWITCH_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_risk_sizing_reviews.json",
    "data/runtime/phase5_approval_policy_decisions.json",
    "data/runtime/phase4_candidate_strategy_universe.json",
    "data/runtime/preference_source_promotion_decisions.json",
    "data/runtime/yahoo_finance_adapter_status.json",
)

KILL_SWITCH_SCOPE_TYPES: tuple[str, ...] = (
    "global",
    "strategy_family",
    "instrument",
    "venue",
    "broker_adapter",
    "prediction_market_adapter",
    "model_provider",
    "data_source_group",
    "telegram_live_alerting",
)

KILL_SWITCH_STATES: tuple[str, ...] = (
    "armed_clear",
    "engaged_block_new_actions",
    "fail_closed_missing_state",
    "fail_closed_corrupt_state",
    "cancelled_expired",
)

KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS: tuple[str, ...] = (
    "approval_policy",
    "risk_sizing",
    "execution_adapter_status",
    "execution_intent",
    "paper_order_staging",
    "paper_order_submission",
    "telegram_notification",
)

KILL_SWITCH_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "risk_agent_handoff_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
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
    "telegram_command_path_enabled",
    "position_created",
    "position_monitor_write_authority",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "downstream_action_allowed",
)

KILL_SWITCH_COUNT_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed_count",
    "risk_agent_handoff_allowed_count",
    "trade_candidate_created_count",
    "execution_policy_handoff_allowed_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "paper_order_allowed_count",
    "staged_order_created_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_submit_receipt_created_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "live_capital_enabled_count",
    "kill_switch_mutation_authority_count",
)

KILL_SWITCH_BOUNDARY = (
    "Q5-4 kill switches can block new Layer B actions before policy, risk, "
    "execution intent, staging, submit, and notification checks. They cannot "
    "create trade candidates, stage or submit paper orders, write brokers, send "
    "live Telegram execution alerts, mutate switches from the cockpit, or enable "
    "live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _risk_sizing_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / RISK_SIZING_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_risk_sizing_reviews(settings=settings)


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-4"
    ledger["boundary"] = (
        "Q5-4 records kill-switch states only. Every execution, order, broker, "
        "notification, position, mutation-authority, and live-capital flag stays false."
    )
    return ledger


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _scope(scope_type: str, scope_key: str, *, reason: str) -> dict[str, Any]:
    return {
        "scope_type": scope_type,
        "scope_key": scope_key,
        "switch_scope": f"{scope_type}:{scope_key}",
        "reason": reason,
    }


def _unique(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(value for value in values if value))


def _strategy_scopes(risk_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    strategies = _unique(
        [
            str(review.get("strategy_family_key") or "")
            for review in risk_bundle.get("reviews", [])
            if isinstance(review, dict)
        ]
    )
    return [
        _scope(
            "strategy_family",
            strategy,
            reason="Strategy-family kill switch must be clear before downstream Layer B work.",
        )
        for strategy in strategies
    ]


def _instrument_scopes(risk_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    instruments = _unique(
        [
            str(review.get("primary_instrument") or "")
            for review in risk_bundle.get("reviews", [])
            if isinstance(review, dict)
        ]
    )
    return [
        _scope(
            "instrument",
            instrument,
            reason="Instrument kill switch must be clear before paper sizing can advance.",
        )
        for instrument in instruments
    ]


def _venue_scopes() -> list[dict[str, Any]]:
    return [
        _scope(
            "venue",
            str(venue.get("key") or "unknown_venue"),
            reason="Venue kill switch must be clear before any adapter status can advance.",
        )
        for venue in execution_registry()
    ]


def _broker_adapter_scopes() -> list[dict[str, Any]]:
    broker_adapters = _unique(
        [
            str(venue.get("adapter") or "")
            for venue in execution_registry()
            if str(venue.get("adapter") or "") == "alpaca"
        ]
    )
    return [
        _scope(
            "broker_adapter",
            adapter,
            reason="Broker-adapter kill switch must be clear before any broker write gate exists.",
        )
        for adapter in broker_adapters
    ]


def _prediction_market_adapter_scopes() -> list[dict[str, Any]]:
    adapters = _unique(
        [
            str(venue.get("adapter") or "")
            for venue in execution_registry()
            if str(venue.get("key") or "") == "prediction_market_router"
        ]
    )
    return [
        _scope(
            "prediction_market_adapter",
            adapter,
            reason="Prediction-market adapter kill switch must be clear before route eligibility.",
        )
        for adapter in adapters
    ]


def _model_provider_scopes() -> list[dict[str, Any]]:
    return [
        _scope(
            "model_provider",
            "local_oracle",
            reason="Local-oracle kill switch must be clear before model context can influence Layer B.",
        ),
        _scope(
            "model_provider",
            "llm_research_stack",
            reason="LLM research-stack kill switch must be clear before model context can influence Layer B.",
        ),
    ]


def _data_source_group_scopes() -> list[dict[str, Any]]:
    return [
        _scope(
            "data_source_group",
            "canonical_sources",
            reason="Canonical-source group must be healthy before downstream Layer B work.",
        ),
        _scope(
            "data_source_group",
            "yahoo_finance",
            reason="Yahoo Finance remains supplemental and can be blocked independently.",
        ),
        _scope(
            "data_source_group",
            "preference_mcp",
            reason="Preference/PREF MCP remains supplemental and can be blocked independently.",
        ),
    ]


def _scope_definitions(risk_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _scope(
            "global",
            "all",
            reason="Global kill switch must be clear before any new Layer B action.",
        ),
        *_strategy_scopes(risk_bundle),
        *_instrument_scopes(risk_bundle),
        *_venue_scopes(),
        *_broker_adapter_scopes(),
        *_prediction_market_adapter_scopes(),
        *_model_provider_scopes(),
        *_data_source_group_scopes(),
        _scope(
            "telegram_live_alerting",
            "default",
            reason="Telegram live-alerting kill switch must be clear before outbound live alerts.",
        ),
    ]


def _switch_status(switch_state: str) -> str:
    if switch_state in {"engaged_block_new_actions", "fail_closed_missing_state", "fail_closed_corrupt_state"}:
        return "blocked"
    if switch_state == "cancelled_expired":
        return "cancelled"
    return "hold"


def _switch_blocks(switch_state: str) -> bool:
    return switch_state in {
        "engaged_block_new_actions",
        "fail_closed_missing_state",
        "fail_closed_corrupt_state",
    }


def _kill_switch_event(scope: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    switch_state = "armed_clear"
    scope_type = str(scope["scope_type"])
    scope_key = str(scope["scope_key"])
    event = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "kill_switch_schema_version": PHASE5_KILL_SWITCH_SCHEMA_VERSION,
        "artifact_type": "kill_switch_event",
        "artifact_id": f"phase5:q5-4:kill-switch:{scope_type}:{_safe_key(scope_key)}",
        "phase": "Q5",
        "stage": "Q5-4",
        "status": _switch_status(switch_state),
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(KILL_SWITCH_SOURCE_REFS),
        "boundary": KILL_SWITCH_BOUNDARY,
        **phase5_authority_defaults(),
        "switch_scope": str(scope["switch_scope"]),
        "scope_type": scope_type,
        "scope_key": scope_key,
        "switch_state": switch_state,
        "switch_active": _switch_blocks(switch_state),
        "blocks_new_actions": _switch_blocks(switch_state),
        "actor_label": "system_q5_4_bootstrap",
        "reason": str(scope["reason"]),
        "expires_at": None,
        "required_before_steps": list(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS),
        "required_before_step_count": len(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS),
        "default_fail_closed_on_missing_state": True,
        "default_fail_closed_on_corrupt_state": True,
        "missing_state_effective_state": "fail_closed_missing_state",
        "corrupt_state_effective_state": "fail_closed_corrupt_state",
        "mutation_event_logged": False,
        "acknowledged": False,
        "acknowledged_at": None,
        "downstream_action": "new_layer_b_action",
        "switch_clear_for_downstream_gate": not _switch_blocks(switch_state),
        "downstream_action_allowed": False,
        "downstream_action_blocked": False,
        "risk_approval_allowed": False,
        "risk_agent_handoff_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
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
        "telegram_command_path_enabled": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
    }
    event["validation_errors"] = validate_phase5_kill_switch_event(event)
    return event


def _scope_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(event.get("scope_type") or "unknown") for event in events)
    return {scope_type: counts.get(scope_type, 0) for scope_type in KILL_SWITCH_SCOPE_TYPES}


def build_phase5_kill_switch_ledger(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    risk_bundle = _risk_sizing_bundle(settings)
    generated_at = _now()
    risk_errors = validate_phase5_risk_sizing_bundle(risk_bundle)
    scopes = _scope_definitions(risk_bundle)
    events = [_kill_switch_event(scope, generated_at=generated_at) for scope in scopes]
    state_counts = Counter(str(event.get("switch_state") or "missing") for event in events)
    status_counts = Counter(str(event.get("status") or "unknown") for event in events)
    scope_counts = _scope_counts(events)
    bundle = {
        "schema_version": PHASE5_KILL_SWITCH_SCHEMA_VERSION,
        "artifact_type": "phase5_kill_switch_ledger",
        "artifact_id": "phase5:q5-4:kill-switch-ledger",
        "phase": "Q5",
        "stage": "Q5-4",
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
        "provenance": phase5_provenance(KILL_SWITCH_SOURCE_REFS),
        "boundary": KILL_SWITCH_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "q5_3_risk_review_count": int(risk_bundle.get("risk_review_count", 0) or 0),
        "q5_3_paper_size_eligible_count": int(
            risk_bundle.get("paper_size_eligible_count", 0) or 0
        ),
        "q5_3_validation_error_count": len(risk_errors),
        "switch_count": len(events),
        "active_switch_count": sum(1 for event in events if event.get("switch_active") is True),
        "blocking_switch_count": sum(1 for event in events if event.get("blocks_new_actions") is True),
        "clear_switch_count": state_counts.get("armed_clear", 0),
        "cancelled_switch_count": state_counts.get("cancelled_expired", 0),
        "fail_closed_default_count": len(events),
        "missing_state_fail_closed_default_count": len(events),
        "corrupt_state_fail_closed_default_count": len(events),
        "scope_counts": scope_counts,
        "state_counts": dict(sorted(state_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "required_scope_types": list(KILL_SWITCH_SCOPE_TYPES),
        "required_scope_type_count": len(KILL_SWITCH_SCOPE_TYPES),
        "required_enforcement_points": list(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS),
        "required_enforcement_point_count": len(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS),
        "default_fail_closed_on_missing_state": True,
        "default_fail_closed_on_corrupt_state": True,
        "switches": events,
    }
    for field in KILL_SWITCH_COUNT_FIELDS:
        bundle[field] = 0
    bundle["validation_errors"] = validate_phase5_kill_switch_ledger(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _event_has_required_steps(event: dict[str, Any]) -> bool:
    steps = event.get("required_before_steps", [])
    if not isinstance(steps, list):
        return False
    return set(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS).issubset(set(steps))


def _kill_switch_state_errors(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    switch_state = event.get("switch_state")
    if switch_state in {None, ""}:
        errors.append("switch_state_missing_fail_closed")
        if event.get("blocks_new_actions") is not True:
            errors.append("missing_state_not_blocking")
        if event.get("status") != "blocked":
            errors.append("missing_state_status_not_blocked")
        return errors
    if switch_state not in KILL_SWITCH_STATES:
        errors.append("switch_state_corrupt_fail_closed")
        if event.get("blocks_new_actions") is not True:
            errors.append("corrupt_state_not_blocking")
        if event.get("status") != "blocked":
            errors.append("corrupt_state_status_not_blocked")
        return errors
    should_block = _switch_blocks(str(switch_state))
    if event.get("switch_active") is not should_block:
        errors.append("switch_active_state_mismatch")
    if event.get("blocks_new_actions") is not should_block:
        errors.append("blocks_new_actions_state_mismatch")
    if event.get("status") != _switch_status(str(switch_state)):
        errors.append("switch_status_state_mismatch")
    if should_block:
        if event.get("switch_clear_for_downstream_gate") is not False:
            errors.append("active_switch_clear_for_downstream_gate")
        if event.get("downstream_action_allowed") is not False:
            errors.append("active_switch_allows_downstream_action")
        if event.get("downstream_action_blocked") is not True:
            errors.append("active_switch_not_blocking")
    if switch_state == "armed_clear":
        if event.get("switch_clear_for_downstream_gate") is not True:
            errors.append("clear_switch_not_clear_for_downstream_gate")
        if event.get("downstream_action_allowed") is not False:
            errors.append("clear_switch_grants_downstream_action")
        if event.get("downstream_action_blocked") is not False:
            errors.append("clear_switch_downstream_block_flag_true")
    return errors


def validate_phase5_kill_switch_event(event: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(event, expected_stage="Q5-4"))
    if event.get("artifact_type") != "kill_switch_event":
        errors.append("artifact_type_not_kill_switch_event")
    if event.get("kill_switch_schema_version") != PHASE5_KILL_SWITCH_SCHEMA_VERSION:
        errors.append("kill_switch_schema_version_mismatch")
    if event.get("scope_type") not in KILL_SWITCH_SCOPE_TYPES:
        errors.append("scope_type_invalid")
    if not str(event.get("switch_scope") or "").startswith(f"{event.get('scope_type')}:"):
        errors.append("switch_scope_prefix_mismatch")
    if event.get("required_before_step_count") != len(KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS):
        errors.append("required_before_step_count_mismatch")
    if not _event_has_required_steps(event):
        errors.append("required_enforcement_points_missing")
    if event.get("default_fail_closed_on_missing_state") is not True:
        errors.append("missing_state_fail_closed_default_disabled")
    if event.get("default_fail_closed_on_corrupt_state") is not True:
        errors.append("corrupt_state_fail_closed_default_disabled")
    if event.get("missing_state_effective_state") != "fail_closed_missing_state":
        errors.append("missing_state_effective_state_invalid")
    if event.get("corrupt_state_effective_state") != "fail_closed_corrupt_state":
        errors.append("corrupt_state_effective_state_invalid")
    if event.get("event_log_written") is True:
        if not str(event.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(event.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if event.get("acknowledged") is True:
        if event.get("mutation_event_logged") is not True:
            errors.append("acknowledged_without_logged_mutation")
        if event.get("event_log_written") is not True:
            errors.append("acknowledged_without_event_log_write")
        if not str(event.get("acknowledged_at") or "").strip():
            errors.append("acknowledged_at_missing")
    if event.get("mutation_event_logged") is True and event.get("event_log_written") is not True:
        errors.append("mutation_logged_without_event_log_write")
    for field in KILL_SWITCH_BOUNDARY_FIELDS:
        if event.get(field) is not False:
            errors.append(f"kill_switch_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if event.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    errors.extend(_kill_switch_state_errors(event))
    return sorted(set(errors))


def validate_phase5_kill_switch_ledger(bundle: dict[str, Any]) -> list[str]:
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
        "switch_count",
        "active_switch_count",
        "blocking_switch_count",
        "fail_closed_default_count",
        "required_scope_types",
        "required_enforcement_points",
        "switches",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_KILL_SWITCH_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_kill_switch_ledger":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-4":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    switches = bundle.get("switches", [])
    if not isinstance(switches, list):
        errors.append("switches_not_list")
        switches = []
    if bundle.get("switch_count") != len(switches):
        errors.append("switch_count_mismatch")
    active_count = sum(1 for event in switches if event.get("switch_active") is True)
    blocking_count = sum(1 for event in switches if event.get("blocks_new_actions") is True)
    if bundle.get("active_switch_count") != active_count:
        errors.append("active_switch_count_mismatch")
    if bundle.get("blocking_switch_count") != blocking_count:
        errors.append("blocking_switch_count_mismatch")
    if active_count != blocking_count:
        errors.append("active_and_blocking_count_mismatch")
    if bundle.get("fail_closed_default_count") != len(switches):
        errors.append("fail_closed_default_count_mismatch")
    if bundle.get("default_fail_closed_on_missing_state") is not True:
        errors.append("bundle_missing_state_fail_closed_default_disabled")
    if bundle.get("default_fail_closed_on_corrupt_state") is not True:
        errors.append("bundle_corrupt_state_fail_closed_default_disabled")
    if set(bundle.get("required_scope_types", [])) != set(KILL_SWITCH_SCOPE_TYPES):
        errors.append("required_scope_types_mismatch")
    if set(bundle.get("required_enforcement_points", [])) != set(
        KILL_SWITCH_REQUIRED_ENFORCEMENT_POINTS
    ):
        errors.append("required_enforcement_points_mismatch")
    scope_counts = bundle.get("scope_counts", {})
    if not isinstance(scope_counts, dict):
        errors.append("scope_counts_invalid")
        scope_counts = {}
    for scope_type in KILL_SWITCH_SCOPE_TYPES:
        if int(scope_counts.get(scope_type, 0) or 0) < 1:
            errors.append(f"scope_type_missing:{scope_type}")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(switches):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("q5_3_validation_error_count", 0) != 0:
        errors.append("q5_3_bundle_validation_failed")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in KILL_SWITCH_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for event in switches:
        if not isinstance(event, dict):
            errors.append("switch_event_not_dict")
            continue
        errors.extend(validate_phase5_kill_switch_event(event))
    return sorted(set(errors))


def attach_phase5_kill_switch_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / KILL_SWITCH_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for event in output.get("switches", []):
        if not isinstance(event, dict):
            continue
        entry = log.write(
            KILL_SWITCH_EVENT_TYPE,
            KILL_SWITCH_COMPONENT,
            {
                "artifact_id": event.get("artifact_id"),
                "switch_scope": event.get("switch_scope"),
                "scope_type": event.get("scope_type"),
                "scope_key": event.get("scope_key"),
                "switch_state": event.get("switch_state"),
                "switch_active": event.get("switch_active"),
                "blocks_new_actions": event.get("blocks_new_actions"),
                "actor_label": event.get("actor_label"),
                "reason": event.get("reason"),
                "expires_at": event.get("expires_at"),
                "execution_allowed": event.get("execution_allowed"),
                "paper_order_allowed": event.get("paper_order_allowed"),
                "broker_write_allowed": event.get("broker_write_allowed"),
                "telegram_live_notifications_allowed": event.get(
                    "telegram_live_notifications_allowed"
                ),
                "live_capital_enabled": event.get("live_capital_enabled"),
                "boundary": event.get("boundary"),
            },
        )
        event["event_log_written"] = True
        event["event_log_path"] = str(log.path)
        event["event_log_correlation_id"] = entry.correlation_id
        event["event_log_created_at"] = entry.created_at
        event["mutation_event_logged"] = True
        event["acknowledged"] = True
        event["acknowledged_at"] = entry.created_at
        event["validation_errors"] = validate_phase5_kill_switch_event(event)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_kill_switch_ledger(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_kill_switch_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / KILL_SWITCH_RUNTIME_ARTIFACT,
        runtime / KILL_SWITCH_HISTORY,
        runtime / KILL_SWITCH_EVENT_LOG,
    )


def write_phase5_kill_switch_ledger(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_kill_switch_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_kill_switch_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_kill_switch_ledger(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_kill_switch_ledger(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_KILL_SWITCH_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "switch_count": output.get("switch_count"),
        "active_switch_count": output.get("active_switch_count"),
        "blocking_switch_count": output.get("blocking_switch_count"),
        "fail_closed_default_count": output.get("fail_closed_default_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
