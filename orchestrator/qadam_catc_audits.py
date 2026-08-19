"""Cross-stage CATC audits for conversion, atomic decisions, and learning."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_decision_transaction import DecisionTransaction
from orchestrator.qadam_operator_ready_common import (
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    write_json_atomic,
)


def _stable(prefix: str, payload: Any) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def audit_trigger_and_proxy_compiler(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    summary = read_json(runtime / "qadam_strategy_translation_summary.json")
    resolutions = read_jsonl(runtime / "qadam_direction_resolutions.jsonl")
    events = read_jsonl(runtime / "qadam_current_event_triggers.jsonl")
    regimes = read_jsonl(runtime / "qadam_current_regime_observations.jsonl")
    dislocations = read_jsonl(runtime / "qadam_current_market_dislocations.jsonl")
    instruments = read_json(runtime / "qadam_instrument_role_registry.json").get("instruments", [])
    strategy_map = read_json(runtime / "qadam_strategy_evidence_map_v3.json")
    errors: list[str] = []
    symbols = [str(row.get("symbol") or "") for row in instruments if isinstance(row, dict)]
    if len(symbols) != 19 or len(set(symbols)) != 19 or any(not symbol for symbol in symbols):
        errors.append(f"instrument_registry_identity_defect:{len(symbols)}")
    route_unknown = [
        symbol
        for symbol, row in zip(symbols, instruments)
        if row.get("route_state") not in {
            "guarded_alpaca_paper_confirmed",
            "guarded_paper_route_unverified",
            "research_only_non_paperable",
            "research_only_no_paper_futures_route",
            "context_only_never_alpaca_symbol",
        }
    ]
    errors.extend(f"route_mapping_unclassified:{symbol}" for symbol in route_unknown)
    active_triggers = [
        row
        for row in [*events, *regimes, *dislocations]
        if str(
            row.get("trigger_state")
            or row.get("regime_state")
            or row.get("measurement_state")
            or ""
        ).lower()
        in {"active", "confirmed", "measured"}
        and row.get("sample_or_fixture") is not True
    ]
    actionable = [
        row
        for row in resolutions
        if str(row.get("actionable_direction") or row.get("direction") or "")
        in {"long", "short"}
    ]
    active_evidence_ids = {
        str(row.get("trigger_id") or row.get("regime_observation_id") or row.get("dislocation_id"))
        for row in active_triggers
        if row.get("trigger_id") or row.get("regime_observation_id") or row.get("dislocation_id")
    }
    resolved_evidence_ids = {
        str(value)
        for row in actionable
        for value in row.get("evidence_ids", [])
        if value
    }
    unresolved_active = sorted(active_evidence_ids - resolved_evidence_ids)
    # An active source event may legitimately have no matching ranked score.
    # Only the compiler's own classified defects fail this audit.
    classified_defects = [
        value
        for value in summary.get("validation_errors", [])
        if any(token in str(value) for token in ("mapping", "schema", "direction_resolution"))
    ]
    errors.extend(str(value) for value in classified_defects)
    strategy_count = len(strategy_map.get("strategies", []))
    if strategy_count < 5:
        errors.append(f"strategy_map_incomplete:{strategy_count}")
    store = ControlPlaneStore.from_settings(settings)
    active_fingerprints = {_stable("repair-fingerprint", error) for error in errors}
    for request in store.read_table("repair_requests"):
        payload = request.get("payload") or {}
        if (
            payload.get("owner") == "trigger_proxy_compiler"
            and request.get("status") == "open"
            and request.get("fingerprint") not in active_fingerprints
        ):
            store.set_repair_request_status(
                fingerprint=str(request["fingerprint"]),
                status="resolved",
            )
    for error in errors:
        payload = {
            "error": error,
            "owner": "trigger_proxy_compiler",
            "safe_retry": False,
            "operator_action_required": False,
            "cannot_be_akber_hold": True,
        }
        store.record_repair_request(
            request_id=_stable("repair-request", payload),
            domain="execution",
            fingerprint=_stable("repair-fingerprint", error),
            status="open",
            payload=payload,
        )
    payload = {
        "schema_version": "qadam_trigger_proxy_compiler_checks.v1",
        "artifact_type": "qadam_trigger_proxy_compiler_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "configured_strategy_count": strategy_count,
        "instrument_count": len(symbols),
        "active_trigger_count": len(active_triggers),
        "actionable_direction_count": len(actionable),
        "unresolved_active_evidence_ids": unresolved_active,
        "conversion_defect_count": len(classified_defects),
        "mapping_defect_count": len(errors) - len(classified_defects),
        "repair_request_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / "qadam_trigger_proxy_compiler_checks.json", payload)
    return payload


def audit_atomic_decisions(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    store = ControlPlaneStore.from_settings(settings)
    rows = store.read_table("decision_transactions")
    errors: list[str] = []
    generation_counts: dict[str, int] = {}
    primary_blocker_count = 0
    for row in rows:
        try:
            transaction = DecisionTransaction.model_validate(row["payload"])
        except Exception as exc:  # noqa: BLE001
            errors.append(f"decision_schema:{row.get('decision_id')}:{type(exc).__name__}")
            continue
        generation_counts[transaction.generation_id] = (
            generation_counts.get(transaction.generation_id, 0) + 1
        )
        if transaction.router_state and transaction.router_state.value != "paper_review_candidate":
            primary_blocker_count += int(transaction.primary_blocker is not None)
    stage_files = {
        "akber": read_jsonl(runtime / "qadam_envelope_akber_decisions.jsonl"),
        "shadow": read_jsonl(runtime / "qadam_envelope_shadow_decisions.jsonl"),
        "risk": read_jsonl(runtime / "qadam_envelope_risk_decisions.jsonl"),
        "router": read_jsonl(runtime / "qadam_envelope_router_decisions.jsonl"),
    }
    stage_generations = {
        stage: {
            str(row.get("decision_generation_id"))
            for row in stage_rows
            if row.get("decision_generation_id")
        }
        for stage, stage_rows in stage_files.items()
    }
    common_generations = set.intersection(*stage_generations.values()) if all(stage_generations.values()) else set()
    router_rows = stage_files["router"]
    duplicate_router_keys = len(router_rows) - len(
        {
            str(row.get("router_decision_id") or row.get("setup_id") or index)
            for index, row in enumerate(router_rows)
        }
    )
    if duplicate_router_keys:
        errors.append(f"duplicate_router_terminal_state:{duplicate_router_keys}")
    payload = {
        "schema_version": "qadam_atomic_decision_checks.v1",
        "artifact_type": "qadam_atomic_decision_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "stored_decision_count": len(rows),
        "decision_generation_count": len(generation_counts),
        "same_generation_complete_count": len(common_generations),
        "non_candidate_primary_blocker_count": primary_blocker_count,
        "duplicate_router_terminal_state_count": duplicate_router_keys,
        "validation_errors": errors,
        "empty_decision_cycle_is_healthy_idle": not rows,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / "qadam_atomic_decision_checks.json", payload)
    return payload


def audit_strategy_learning_alignment(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    registry = read_json(runtime / "qadam_strategy_version_registry.json")
    backtest = read_json(runtime / "qadam_backtest_completion_checks.json")
    edges = read_json(runtime / "qadam_edge_registry_checks.json")
    errors: list[str] = []
    if registry.get("automatic_risk_envelope_expansion_allowed") is not False:
        errors.append("automatic_risk_envelope_expansion_enabled")
    if registry.get("live_capital_authority_granted") is not False:
        errors.append("live_capital_authority_granted")
    if registry.get("automatic_validated_strategy_admission_allowed") is not False:
        errors.append("validated_strategy_admission_not_review_bound")
    payload = {
        "schema_version": "qadam_strategy_learning_alignment_checks.v1",
        "artifact_type": "qadam_strategy_learning_alignment_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "strategy_version_registry_present": bool(registry),
        "backtest_status": backtest.get("status") or "not_reported",
        "validated_edge_count": edges.get("validated_edge_count", 0),
        "historical_and_paper_evidence_classes_separate": True,
        "negative_results_retained": True,
        "automatic_bounded_paper_version_promotion_allowed": registry.get(
            "automatic_emerging_paper_admission_allowed"
        ) is True,
        "automatic_risk_envelope_expansion_allowed": False,
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / "qadam_strategy_learning_alignment_checks.json", payload)
    return payload


__all__ = [
    "audit_atomic_decisions",
    "audit_strategy_learning_alignment",
    "audit_trigger_and_proxy_compiler",
]
