"""Q5-9 prediction-market read-only adapter placeholder.

This module maps Polymarket and Kalshi context into provenance-preserving
read-only route records and explicitly blocks all prediction-market, perps, and
live-spend write paths. It does not call Preference/PREF MCP live tools, submit
orders, spend funds, or enable broker/venue writes.
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
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.preference_mcp_adapter import PreferenceMCPAdapter
from orchestrator.preference_mcp_provenance import (
    build_preference_source_quorum_report,
    preference_provenance_paths,
    validate_preference_provenance_block,
    validate_preference_source_quorum_report,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION = 1
PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT = "phase5_prediction_market_adapter.json"
PREDICTION_MARKET_ADAPTER_HISTORY = "phase5_prediction_market_adapter_history.jsonl"
PREDICTION_MARKET_ADAPTER_EVENT_LOG = "phase5_prediction_market_adapter_events.jsonl"
PREDICTION_MARKET_ADAPTER_EVENT_TYPE = "phase5_prediction_market_adapter_written"
PREDICTION_MARKET_ADAPTER_COMPONENT = "phase5_prediction_market_adapter"

PREDICTION_MARKET_ADAPTER_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/preference_provenance_source_quorum.json",
    "data/runtime/preference_mcp_first_universe_domain_packs.json",
    "data/runtime/preference_tool_catalog.json",
    "data/runtime/phase5_execution_adapter_status.json",
    "data/runtime/phase5_paper_submit_enablement_gate.json",
)

PREDICTION_MARKET_ROUTE_KEYS: tuple[str, ...] = (
    "polymarket_context",
    "kalshi_context",
    "hyperliquid_context",
    "dflow_context",
    "privex_base_perps",
    "privex_coti_perps",
)

PREDICTION_MARKET_REQUIRED_CHECKS: tuple[str, ...] = (
    "route_definition_present",
    "route_mode_not_live",
    "read_only_context_allowed",
    "preference_provenance_valid",
    "preference_source_quorum_not_counted",
    "preference_not_canonical_source",
    "domain_tool_call_not_performed",
    "paid_tool_not_used",
    "guarded_placeholder_present",
    "guarded_placeholder_blocks_spend",
    "guarded_placeholder_blocks_write",
    "prediction_market_write_blocked",
    "crypto_perps_write_blocked",
    "broker_write_blocked",
    "paper_order_blocked",
    "live_capital_disabled",
    "live_endpoint_blocked",
    "raw_payload_not_exposed",
    "authorization_not_exposed",
    "execution_adapter_bundle_valid",
    "paper_submit_gate_valid",
)

PREDICTION_MARKET_BOUNDARY_FIELDS: tuple[str, ...] = (
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
    "prediction_market_order_allowed",
    "prediction_market_spend_allowed",
    "prediction_market_live_order_allowed",
    "polymarket_write_allowed",
    "kalshi_write_allowed",
    "hyperliquid_write_allowed",
    "dflow_write_allowed",
    "privex_write_allowed",
    "crypto_perps_write_allowed",
    "paid_preference_tools_allowed",
    "telegram_live_notifications_allowed",
    "position_created",
    "position_monitor_write_authority",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "source_quorum_bypass_allowed",
)

PREDICTION_MARKET_COUNT_FIELDS: tuple[str, ...] = (
    "prediction_market_write_allowed_count",
    "prediction_market_order_allowed_count",
    "prediction_market_spend_allowed_count",
    "prediction_market_live_order_allowed_count",
    "polymarket_write_allowed_count",
    "kalshi_write_allowed_count",
    "hyperliquid_write_allowed_count",
    "dflow_write_allowed_count",
    "privex_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "paid_preference_tools_allowed_count",
    "broker_write_allowed_count",
    "broker_post_called_count",
    "paper_order_allowed_count",
    "paper_order_submitted_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "base_url_exposed_count",
)

PREDICTION_MARKET_ADAPTER_BOUNDARY = (
    "Q5-9 prediction-market adapter records are read-only source-context "
    "placeholders. Polymarket and Kalshi context can inform policy and risk "
    "caution only when Preference/PREF MCP provenance is valid. This stage "
    "cannot write prediction-market venues, spend funds, use perps routes, "
    "submit paper orders, write brokers, expose secrets, use live endpoints, or "
    "enable live capital."
)

ROUTE_BLUEPRINTS: tuple[dict[str, Any], ...] = (
    {
        "route_key": "polymarket_context",
        "venue_key": "prediction_market:polymarket",
        "venue_name": "Polymarket Context",
        "adapter_key": "preference_mcp_polymarket_context",
        "venue_mode": "read_only",
        "network_scope": "polymarket",
        "upstream_source": "polymarket",
        "domain_pack": "prediction_markets",
        "context_kind": "orderbook_depth",
        "status_when_context_present": "hold",
        "placeholder_status": "paper_not_available",
        "first_release_allowed": True,
    },
    {
        "route_key": "kalshi_context",
        "venue_key": "prediction_market:kalshi",
        "venue_name": "Kalshi Context",
        "adapter_key": "preference_mcp_kalshi_context",
        "venue_mode": "read_only",
        "network_scope": "kalshi",
        "upstream_source": "kalshi",
        "domain_pack": "prediction_markets",
        "context_kind": "market_summary",
        "status_when_context_present": "hold",
        "placeholder_status": "paper_not_available",
        "first_release_allowed": True,
    },
    {
        "route_key": "hyperliquid_context",
        "venue_key": "derivatives:hyperliquid",
        "venue_name": "Hyperliquid Context",
        "adapter_key": "preference_mcp_hyperliquid_context",
        "venue_mode": "live_blocked",
        "network_scope": "hyperliquid",
        "upstream_source": "hyperliquid",
        "domain_pack": "crypto_derivatives",
        "context_kind": "disabled_perps_context",
        "status_when_context_present": "live_blocked",
        "placeholder_status": "live_blocked",
        "first_release_allowed": False,
    },
    {
        "route_key": "dflow_context",
        "venue_key": "flow:dflow",
        "venue_name": "dFlow Context",
        "adapter_key": "preference_mcp_dflow_context",
        "venue_mode": "live_blocked",
        "network_scope": "dflow",
        "upstream_source": "dflow",
        "domain_pack": "order_flow",
        "context_kind": "disabled_flow_context",
        "status_when_context_present": "live_blocked",
        "placeholder_status": "live_blocked",
        "first_release_allowed": False,
    },
    {
        "route_key": "privex_base_perps",
        "venue_key": "perps:privex_base",
        "venue_name": "PriveX Base Perps",
        "adapter_key": "privex_base_perps_disabled",
        "venue_mode": "live_blocked",
        "network_scope": "base:8453",
        "upstream_source": "privex",
        "domain_pack": "crypto_perps",
        "context_kind": "disabled_perps_rail",
        "status_when_context_present": "live_blocked",
        "placeholder_status": "live_blocked",
        "first_release_allowed": False,
    },
    {
        "route_key": "privex_coti_perps",
        "venue_key": "perps:privex_coti",
        "venue_name": "PriveX COTI Perps",
        "adapter_key": "privex_coti_perps_disabled",
        "venue_mode": "live_blocked",
        "network_scope": "coti:2632500",
        "upstream_source": "privex",
        "domain_pack": "crypto_perps",
        "context_kind": "disabled_perps_rail",
        "status_when_context_present": "live_blocked",
        "placeholder_status": "live_blocked",
        "first_release_allowed": False,
    },
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-9"
    ledger["boundary"] = (
        "Q5-9 grants no execution, spend, broker, prediction-market write, "
        "crypto-perps write, Telegram live-notification, or live-capital "
        "authority. It records read-only source-context routes only."
    )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def prediction_market_adapter_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
        runtime / PREDICTION_MARKET_ADAPTER_HISTORY,
        runtime / PREDICTION_MARKET_ADAPTER_EVENT_LOG,
    )


def _execution_adapter_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / EXECUTION_ADAPTER_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_execution_adapter_status(settings=settings)


def _paper_submit_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_paper_submit_enablement_gate(settings=settings)


def _preference_events(settings: Settings) -> list[dict[str, Any]]:
    adapter = PreferenceMCPAdapter(settings=settings)
    payload = adapter.sample_payload()
    return [event.to_dict() for event in adapter.normalize_payload(payload)]


def _event_lookup(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for event in events:
        raw_payload = event.get("raw_payload", {})
        if not isinstance(raw_payload, dict):
            continue
        upstream = str(raw_payload.get("upstream_source") or "").lower()
        domain_pack = str(raw_payload.get("domain_pack") or "")
        if domain_pack == "prediction_markets" and upstream:
            lookup[upstream] = event
    return lookup


def _public_context_snapshot(event: dict[str, Any] | None) -> dict[str, Any]:
    if not event:
        return {
            "status": "missing",
            "context_available": False,
            "event_id": None,
            "event_type": None,
            "summary": None,
            "metric": None,
            "value": None,
            "unit": None,
            "secondary_metric": None,
            "secondary_value": None,
            "observed_at": None,
            "raw_payload_exposed": False,
        }
    raw_payload = event.get("raw_payload", {})
    if not isinstance(raw_payload, dict):
        raw_payload = {}
    return {
        "status": "available",
        "context_available": True,
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "summary": event.get("normalised_summary"),
        "metric": raw_payload.get("metric"),
        "value": _float(raw_payload.get("value"), 0.0),
        "unit": raw_payload.get("unit"),
        "secondary_metric": raw_payload.get("secondary_metric"),
        "secondary_value": raw_payload.get("secondary_value"),
        "observed_at": event.get("ingested_at"),
        "raw_payload_exposed": False,
    }


def _provenance_summary(event: dict[str, Any] | None) -> dict[str, Any]:
    raw_payload = event.get("raw_payload", {}) if event else {}
    provenance = raw_payload.get("preference_provenance") if isinstance(raw_payload, dict) else None
    if not isinstance(provenance, dict):
        return {
            "status": "missing",
            "provenance_valid": False,
            "upstream_source_name": None,
            "upstream_source_identity": None,
            "payload_hash": None,
            "source_quorum_credit_allowed": False,
            "counts_against_strategy_source_quorum": False,
        }
    return {
        "status": "valid" if not validate_preference_provenance_block(provenance) else "invalid",
        "provenance_valid": not validate_preference_provenance_block(provenance),
        "upstream_source_name": provenance.get("upstream_source_name"),
        "upstream_source_identity": provenance.get("upstream_source_identity"),
        "payload_hash": provenance.get("payload_hash"),
        "source_quorum_credit_allowed": provenance.get("source_quorum_credit_allowed") is True,
        "counts_against_strategy_source_quorum": (
            provenance.get("counts_against_strategy_source_quorum") is True
        ),
    }


def _guarded_placeholder(blueprint: dict[str, Any]) -> dict[str, Any]:
    placeholder_status = str(blueprint["placeholder_status"])
    return {
        "schema_version": PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION,
        "status": placeholder_status,
        "route_key": blueprint["route_key"],
        "venue_key": blueprint["venue_key"],
        "write_route_enabled": False,
        "can_place_order": False,
        "order_placement_allowed": False,
        "spend_allowed": False,
        "paper_market_available": False,
        "paper_route_available": False,
        "live_market_available": False,
        "live_route_allowed": False,
        "position_open_allowed": False,
        "sandbox_route_approved": False,
        "order_payload_template_available": False,
        "reason": (
            "prediction_market_paper_path_not_available"
            if placeholder_status == "paper_not_available"
            else "first_release_live_and_perps_routes_blocked"
        ),
        "boundary": (
            "This placeholder blocks prediction-market and perps execution. It "
            "can expose read-only context only and cannot spend or submit orders."
        ),
    }


def _route_checks(
    *,
    blueprint: dict[str, Any],
    context: dict[str, Any],
    provenance: dict[str, Any],
    source_report: dict[str, Any],
    execution_adapter_errors: list[str],
    paper_submit_errors: list[str],
    placeholder: dict[str, Any],
) -> list[dict[str, Any]]:
    read_only_route = blueprint["venue_mode"] == "read_only"
    provenance_required = read_only_route
    provenance_valid = provenance.get("provenance_valid") is True
    return [
        _check("route_definition_present", bool(blueprint.get("route_key"))),
        _check("route_mode_not_live", blueprint.get("venue_mode") != "live"),
        _check(
            "read_only_context_allowed",
            (read_only_route and context.get("context_available") is True)
            or blueprint.get("venue_mode") == "live_blocked",
        ),
        _check("preference_provenance_valid", provenance_valid if provenance_required else True),
        _check(
            "preference_source_quorum_not_counted",
            provenance.get("source_quorum_credit_allowed") is False
            and source_report.get("strategy_source_quorum_credit_allowed") is False,
        ),
        _check(
            "preference_not_canonical_source",
            source_report.get("preference_counts_as_canonical_source") is False,
        ),
        _check("domain_tool_call_not_performed", True),
        _check("paid_tool_not_used", True),
        _check("guarded_placeholder_present", bool(placeholder.get("route_key"))),
        _check("guarded_placeholder_blocks_spend", placeholder.get("spend_allowed") is False),
        _check("guarded_placeholder_blocks_write", placeholder.get("write_route_enabled") is False),
        _check("prediction_market_write_blocked", True),
        _check("crypto_perps_write_blocked", True),
        _check("broker_write_blocked", True),
        _check("paper_order_blocked", True),
        _check("live_capital_disabled", True),
        _check("live_endpoint_blocked", True),
        _check("raw_payload_not_exposed", context.get("raw_payload_exposed") is False),
        _check("authorization_not_exposed", True),
        _check("execution_adapter_bundle_valid", not execution_adapter_errors, detail=execution_adapter_errors),
        _check("paper_submit_gate_valid", not paper_submit_errors, detail=paper_submit_errors),
    ]


def _status_from_blueprint(
    blueprint: dict[str, Any],
    context: dict[str, Any],
    provenance: dict[str, Any],
) -> tuple[str, str]:
    if blueprint["venue_mode"] == "live_blocked":
        return "live_blocked", "live_blocked_first_release_excluded"
    if context.get("context_available") and provenance.get("provenance_valid") is True:
        return "hold", "read_only_context_available_for_policy_risk_caution"
    return "blocked", "blocked_missing_prediction_market_context_or_provenance"


def _route_record(
    blueprint: dict[str, Any],
    *,
    event: dict[str, Any] | None,
    source_report: dict[str, Any],
    execution_adapter_errors: list[str],
    paper_submit_errors: list[str],
    generated_at: str,
) -> dict[str, Any]:
    context = _public_context_snapshot(event)
    provenance = _provenance_summary(event)
    placeholder = _guarded_placeholder(blueprint)
    checks = _route_checks(
        blueprint=blueprint,
        context=context,
        provenance=provenance,
        source_report=source_report,
        execution_adapter_errors=execution_adapter_errors,
        paper_submit_errors=paper_submit_errors,
        placeholder=placeholder,
    )
    status, decision = _status_from_blueprint(blueprint, context, provenance)
    blockers = sorted(check["name"] for check in checks if not check["passed"])
    hold_reasons = []
    if status == "hold":
        hold_reasons.append("read_only_prediction_market_context_for_policy_risk_caution")
    if status == "live_blocked":
        hold_reasons.append("first_release_live_and_perps_routes_blocked")
    route_key = str(blueprint["route_key"])
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "prediction_market_adapter_schema_version": PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION,
        "artifact_type": "execution_adapter_status",
        "artifact_id": f"phase5:q5-9:prediction-market-adapter:{_safe_key(route_key)}",
        "phase": "Q5",
        "stage": "Q5-9",
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
        "provenance": phase5_provenance(PREDICTION_MARKET_ADAPTER_SOURCE_REFS),
        "boundary": PREDICTION_MARKET_ADAPTER_BOUNDARY,
        **phase5_authority_defaults(),
        "route_key": route_key,
        "venue_key": blueprint["venue_key"],
        "venue_name": blueprint["venue_name"],
        "adapter_key": blueprint["adapter_key"],
        "venue_mode": blueprint["venue_mode"],
        "account_scope": "read_only_context",
        "network_scope": blueprint["network_scope"],
        "first_release_allowed": blueprint["first_release_allowed"] is True,
        "read_health": "read_only_context_available"
        if context.get("context_available")
        else "read_disabled_first_release_live_blocked"
        if blueprint["venue_mode"] == "live_blocked"
        else "blocked_missing_context",
        "write_health": "blocked_q5_9_read_only_context",
        "permissions_status": "read_only_context_only",
        "permission_scope": "read_only_context_only",
        "credential_status": "not_required_preference_context_sample"
        if context.get("context_available")
        else "not_configured",
        "credentials_configured": False,
        "endpoint_classification": "no_write_endpoint_enabled",
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "read_only_route": blueprint["venue_mode"] == "read_only",
        "context_kind": blueprint["context_kind"],
        "context_snapshot": context,
        "context_available": context.get("context_available") is True,
        "context_informs_policy_risk_caution": (
            status == "hold" and context.get("context_available") is True
        ),
        "preference_context_snapshot": context,
        "preference_provenance": provenance,
        "preference_provenance_required": blueprint["venue_mode"] == "read_only",
        "preference_provenance_valid": provenance.get("provenance_valid") is True,
        "preference_context_status": source_report.get("preference_context_status"),
        "preference_multi_source_context_allowed": (
            source_report.get("preference_multi_source_context_allowed") is True
        ),
        "preference_counts_as_canonical_source": False,
        "preference_only_source_quorum_allowed": False,
        "preference_source_quorum_credit_allowed": False,
        "strategy_source_quorum_credit_allowed": False,
        "preference_paid_tools_allowed": False,
        "domain_tool_call_performed": False,
        "live_mcp_call_performed": False,
        "search_tools_call_performed": False,
        "paid_tool_call_performed": False,
        "guarded_execution_placeholder": placeholder,
        "guarded_placeholder_status": placeholder["status"],
        "execution_adapter_decision": decision,
        "execution_adapter_read_allowed": False,
        "downstream_staging_allowed": False,
        "reconciliation_ready_for_submit": False,
        "required_checks": list(PREDICTION_MARKET_REQUIRED_CHECKS),
        "required_check_count": len(PREDICTION_MARKET_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failed_check_count": sum(1 for check in checks if not check["passed"]),
        "blocked_reasons": blockers,
        "blocked_reason_count": len(blockers),
        "hold_reasons": sorted(dict.fromkeys(hold_reasons)),
        "hold_reason_count": len(set(hold_reasons)),
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
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
        "prediction_market_order_allowed": False,
        "prediction_market_spend_allowed": False,
        "prediction_market_live_order_allowed": False,
        "polymarket_write_allowed": False,
        "kalshi_write_allowed": False,
        "hyperliquid_write_allowed": False,
        "dflow_write_allowed": False,
        "privex_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "paid_preference_tools_allowed": False,
        "telegram_live_notifications_allowed": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
        "source_quorum_bypass_allowed": False,
    }
    record["validation_errors"] = validate_phase5_prediction_market_route(record)
    return record


def build_phase5_prediction_market_adapter(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    events = _preference_events(settings)
    source_report = build_preference_source_quorum_report(preference_events=events)
    source_report_errors = validate_preference_source_quorum_report(source_report)
    execution_bundle = _execution_adapter_bundle(settings)
    execution_errors = validate_phase5_execution_adapter_status_bundle(execution_bundle)
    paper_submit_bundle = _paper_submit_bundle(settings)
    paper_submit_errors = validate_phase5_paper_submit_enablement_bundle(paper_submit_bundle)
    lookup = _event_lookup(events)
    generated_at = _now()
    records = [
        _route_record(
            blueprint,
            event=lookup.get(str(blueprint["upstream_source"]).lower()),
            source_report=source_report,
            execution_adapter_errors=execution_errors,
            paper_submit_errors=paper_submit_errors,
            generated_at=generated_at,
        )
        for blueprint in ROUTE_BLUEPRINTS
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    placeholder_counts = Counter(
        str(record.get("guarded_placeholder_status") or "unknown") for record in records
    )
    read_health_counts = Counter(str(record.get("read_health") or "unknown") for record in records)
    bundle = {
        "schema_version": PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION,
        "artifact_type": "phase5_prediction_market_adapter_bundle",
        "artifact_id": "phase5:q5-9:prediction-market-adapter",
        "phase": "Q5",
        "stage": "Q5-9",
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
        "provenance": phase5_provenance(PREDICTION_MARKET_ADAPTER_SOURCE_REFS),
        "boundary": PREDICTION_MARKET_ADAPTER_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "route_count": len(records),
        "prediction_market_route_count": sum(
            1 for record in records if str(record.get("venue_key") or "").startswith("prediction_market:")
        ),
        "read_only_route_count": sum(1 for record in records if record.get("read_only_route") is True),
        "preference_prediction_market_context_count": sum(
            1
            for record in records
            if record.get("context_available") is True
            and str(record.get("venue_key") or "").startswith("prediction_market:")
        ),
        "context_available_count": sum(1 for record in records if record.get("context_available") is True),
        "policy_risk_caution_context_count": sum(
            1 for record in records if record.get("context_informs_policy_risk_caution") is True
        ),
        "guarded_placeholder_count": len(records),
        "paper_not_available_count": placeholder_counts.get("paper_not_available", 0),
        "live_blocked_count": status_counts.get("live_blocked", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "placeholder_status_counts": dict(sorted(placeholder_counts.items())),
        "read_health_counts": dict(sorted(read_health_counts.items())),
        "required_check_count": len(PREDICTION_MARKET_REQUIRED_CHECKS),
        "preference_provenance_status": source_report.get("status"),
        "preference_context_status": source_report.get("preference_context_status"),
        "preference_distinct_upstream_source_count": source_report.get(
            "preference_distinct_upstream_source_count",
            0,
        ),
        "preference_multi_source_context_allowed": (
            source_report.get("preference_multi_source_context_allowed") is True
        ),
        "preference_counts_as_canonical_source": False,
        "preference_only_source_quorum_allowed": False,
        "preference_source_quorum_credit_allowed": False,
        "strategy_source_quorum_credit_allowed": False,
        "preference_source_quorum_validation_error_count": len(source_report_errors),
        "execution_adapter_bundle_validation_error_count": len(execution_errors),
        "paper_submit_gate_validation_error_count": len(paper_submit_errors),
        "preference_provenance_runtime_artifact_recorded": preference_provenance_paths(settings)[0].exists(),
        "records": records,
    }
    for field in PREDICTION_MARKET_COUNT_FIELDS:
        bundle[field] = sum(
            1
            for record in records
            if record.get(field.removesuffix("_count")) is True
        )
    bundle["validation_errors"] = validate_phase5_prediction_market_adapter_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _record_status_errors(record: dict[str, Any]) -> list[str]:
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
    if status == "hold":
        if record.get("context_informs_policy_risk_caution") is not True:
            errors.append("hold_without_policy_risk_caution_context")
        if record.get("read_only_route") is not True:
            errors.append("hold_not_read_only_route")
    if status == "live_blocked" and record.get("live_capital_enabled") is not False:
        errors.append("live_blocked_with_live_capital")
    if status == "eligible":
        errors.append("prediction_market_route_eligible")
    return errors


def _nested_route_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    context = record.get("context_snapshot", {})
    if not isinstance(context, dict):
        errors.append("context_snapshot_not_dict")
        context = {}
    if context.get("raw_payload_exposed") is not False:
        errors.append("context_raw_payload_exposed")
    provenance = record.get("preference_provenance", {})
    if not isinstance(provenance, dict):
        errors.append("preference_provenance_not_dict")
        provenance = {}
    if record.get("preference_provenance_required") is True and provenance.get("provenance_valid") is not True:
        errors.append("required_preference_provenance_invalid")
    for field in (
        "source_quorum_credit_allowed",
        "counts_against_strategy_source_quorum",
    ):
        if provenance.get(field) is not False:
            errors.append(f"preference_provenance_overclaims:{field}")
    placeholder = record.get("guarded_execution_placeholder", {})
    if not isinstance(placeholder, dict):
        errors.append("guarded_placeholder_not_dict")
        placeholder = {}
    if str(placeholder.get("status") or "") not in {"paper_not_available", "live_blocked"}:
        errors.append("guarded_placeholder_status_invalid")
    for field in (
        "write_route_enabled",
        "can_place_order",
        "order_placement_allowed",
        "spend_allowed",
        "paper_market_available",
        "paper_route_available",
        "live_market_available",
        "live_route_allowed",
        "position_open_allowed",
        "sandbox_route_approved",
        "order_payload_template_available",
    ):
        if placeholder.get(field) is not False:
            errors.append(f"guarded_placeholder_authority_enabled:{field}")
    return errors


def validate_phase5_prediction_market_route(record: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(record, expected_stage="Q5-9"))
    if record.get("artifact_type") != "execution_adapter_status":
        errors.append("artifact_type_not_execution_adapter_status")
    if record.get("prediction_market_adapter_schema_version") != PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION:
        errors.append("prediction_market_adapter_schema_version_mismatch")
    if record.get("route_key") not in PREDICTION_MARKET_ROUTE_KEYS:
        errors.append("route_key_invalid")
    if record.get("required_check_count") != len(PREDICTION_MARKET_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    check_names = {
        str(check.get("name") or "")
        for check in record.get("checks", [])
        if isinstance(check, dict)
    }
    for check in PREDICTION_MARKET_REQUIRED_CHECKS:
        if check not in check_names:
            errors.append(f"required_check_missing:{check}")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    for exposure in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
    ):
        if record.get(exposure) is not False:
            errors.append(f"prediction_market_exposure_enabled:{exposure}")
    for field in PREDICTION_MARKET_BOUNDARY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"prediction_market_boundary_enabled:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    if record.get("domain_tool_call_performed") is not False:
        errors.append("domain_tool_call_performed")
    if record.get("live_mcp_call_performed") is not False:
        errors.append("live_mcp_call_performed")
    if record.get("search_tools_call_performed") is not False:
        errors.append("search_tools_call_performed")
    if record.get("paid_tool_call_performed") is not False:
        errors.append("paid_tool_call_performed")
    if record.get("preference_counts_as_canonical_source") is not False:
        errors.append("preference_counts_as_canonical_source")
    if record.get("preference_source_quorum_credit_allowed") is not False:
        errors.append("preference_source_quorum_credit_allowed")
    if record.get("strategy_source_quorum_credit_allowed") is not False:
        errors.append("strategy_source_quorum_credit_allowed")
    if record.get("endpoint_classification") == "live_endpoint":
        errors.append("live_endpoint_classification")
    if record.get("write_health") != "blocked_q5_9_read_only_context":
        errors.append("write_health_not_blocked_q5_9")
    errors.extend(_record_status_errors(record))
    errors.extend(_nested_route_errors(record))
    return sorted(set(errors))


def validate_phase5_prediction_market_adapter_bundle(bundle: dict[str, Any]) -> list[str]:
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
        "route_count",
        "prediction_market_route_count",
        "read_only_route_count",
        "preference_prediction_market_context_count",
        "guarded_placeholder_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_prediction_market_adapter_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-9":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("route_count") != len(records):
        errors.append("route_count_mismatch")
    if bundle.get("guarded_placeholder_count") != len(records):
        errors.append("guarded_placeholder_count_mismatch")
    if bundle.get("prediction_market_route_count") != sum(
        1
        for record in records
        if isinstance(record, dict) and str(record.get("venue_key") or "").startswith("prediction_market:")
    ):
        errors.append("prediction_market_route_count_mismatch")
    if bundle.get("read_only_route_count") != sum(
        1 for record in records if isinstance(record, dict) and record.get("read_only_route") is True
    ):
        errors.append("read_only_route_count_mismatch")
    if bundle.get("preference_prediction_market_context_count") != sum(
        1
        for record in records
        if isinstance(record, dict)
        and record.get("context_available") is True
        and str(record.get("venue_key") or "").startswith("prediction_market:")
    ):
        errors.append("preference_prediction_market_context_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("preference_provenance_status") != "validated":
        errors.append("preference_provenance_status_not_validated")
    for field in (
        "preference_counts_as_canonical_source",
        "preference_only_source_quorum_allowed",
        "preference_source_quorum_credit_allowed",
        "strategy_source_quorum_credit_allowed",
    ):
        if bundle.get(field) is not False:
            errors.append(f"bundle_preference_overclaim:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in PREDICTION_MARKET_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("prediction_market_route_not_dict")
            continue
        errors.extend(validate_phase5_prediction_market_route(record))
    return sorted(set(errors))


def attach_phase5_prediction_market_adapter_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PREDICTION_MARKET_ADAPTER_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            PREDICTION_MARKET_ADAPTER_EVENT_TYPE,
            PREDICTION_MARKET_ADAPTER_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "route_key": record.get("route_key"),
                "venue_key": record.get("venue_key"),
                "status": record.get("status"),
                "context_available": record.get("context_available"),
                "preference_provenance_valid": record.get("preference_provenance_valid"),
                "guarded_placeholder_status": record.get("guarded_placeholder_status"),
                "prediction_market_write_allowed": record.get("prediction_market_write_allowed"),
                "crypto_perps_write_allowed": record.get("crypto_perps_write_allowed"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "paper_order_allowed": record.get("paper_order_allowed"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_prediction_market_route(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_prediction_market_adapter_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def write_phase5_prediction_market_adapter(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = prediction_market_adapter_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_prediction_market_adapter_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_prediction_market_adapter_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_prediction_market_adapter_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PREDICTION_MARKET_ADAPTER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "route_count": output.get("route_count"),
        "prediction_market_route_count": output.get("prediction_market_route_count"),
        "preference_prediction_market_context_count": output.get(
            "preference_prediction_market_context_count"
        ),
        "guarded_placeholder_count": output.get("guarded_placeholder_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
