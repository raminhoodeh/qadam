"""Public-safe CATC projections for the existing Qadam dashboard UX."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic

SCHEMA_VERSION = "qadam_catc_dashboard_projection.v1"
DASHBOARD_ARTIFACT = "qadam_canonical_autonomous_tradeability_dashboard_summary.json"
TELEGRAM_ARTIFACT = "qadam_canonical_autonomous_tradeability_telegram_summary.json"
CHECK_ARTIFACT = "qadam_catc_dashboard_projection_checks.json"


def _age_seconds(value: Any) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def build_catc_dashboard_projection(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = ControlPlaneStore.from_settings(settings)
    integrity = store.integrity_report()
    sources = read_json(runtime / "qadam_source_capability_registry.json")
    context = read_json(runtime / "qadam_execution_context_summary.json")
    router = read_json(runtime / "qadam_router_v3_why_not_trading_now.json")
    lifecycle = read_json(runtime / "qadam_lifecycle_control_plane_checks.json")
    operator = read_json(runtime / "qadam_operator_service_status.json")
    gate_policy = read_json(runtime / "qadam_gate_policy_checks.json")
    errors: list[str] = []
    if integrity.get("status") != "passed":
        errors.append("control_plane_integrity_failed")
    if sources and sources.get("status") != "passed":
        errors.append("source_capability_registry_blocked")
    if gate_policy and gate_policy.get("status") != "passed":
        errors.append("gate_policy_blocked")
    primary_reason = str(
        router.get("primary_reason")
        or "No current setup is ready for guarded Alpaca Paper review."
    )
    current_state = str(router.get("current_router_state") or "no-setup")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_autonomous_tradeability_dashboard_summary",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "degraded",
        "protected_dashboard_ux": True,
        "route_list_changed": False,
        "sidebar_order_changed": False,
        "ten_stage_lifecycle_changed": False,
        "capital_mode": "paper_only",
        "current_setup_state": current_state,
        "primary_blocker": {
            "summary": primary_reason,
            "dependent_consequences_are_not_independent_blockers": True,
        },
        "source_capability": sources.get("counts", {}),
        "execution_context": {
            "instrument_count": context.get("instrument_count", 0),
            "quote_ready_count": context.get("quote_ready_count", 0),
            "status_counts": context.get("status_counts", {}),
            "generated_at": context.get("generated_at"),
            "age_seconds": _age_seconds(context.get("generated_at")),
        },
        "control_plane": {
            "database_integrity": integrity.get("status"),
            "counts": integrity.get("counts", {}),
            "json_outputs_are_rebuildable_projections": True,
        },
        "lifecycle": {
            "record_count": lifecycle.get("stored_lifecycle_event_count", 0),
            "ambiguous_record_count": lifecycle.get("ambiguous_lifecycle_record_count", 0),
            "missing_handoff_lineage_count": lifecycle.get("missing_handoff_lineage_count", 0),
            "missing_lineage_invented_count": 0,
        },
        "operator": {
            "status": operator.get("status") or "not_reported",
            "operational_health_is_not_tradeability": True,
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "command_disabled": True,
        "validation_errors": errors,
    }
    return payload, errors


def build_and_write_catc_dashboard_projection(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload, errors = build_catc_dashboard_projection(settings)
    telegram = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_autonomous_tradeability_telegram_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "material_change_required": False,
        "candidate_message": None,
        "review_only": True,
        "command_disabled": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    checks = {
        **payload,
        "artifact_type": "qadam_catc_dashboard_projection_checks",
        "dashboard_read_only": True,
        "telegram_read_only": True,
        "validation_error_count": len(errors),
    }
    write_json_atomic(runtime / DASHBOARD_ARTIFACT, payload)
    write_json_atomic(runtime / TELEGRAM_ARTIFACT, telegram)
    write_json_atomic(runtime / CHECK_ARTIFACT, checks)
    return payload, errors


__all__ = ["build_and_write_catc_dashboard_projection", "build_catc_dashboard_projection"]
