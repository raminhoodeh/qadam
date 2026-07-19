"""Phase 12 clean-epoch performance, lineage, and proof monitor."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_clean_epoch_operating.v1"
STATUS_ARTIFACT = "qadam_clean_epoch_operating_status.json"
CHECK_ARTIFACT = "qadam_clean_epoch_operating_checks.json"


def build_clean_epoch_operating_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    epoch = read_json(runtime / "current_paper_epoch.json")
    launch = read_json(runtime / "qadam_guarded_paper_launch_checks.json")
    lifecycle = read_json(runtime / "qadam_paper_lifecycle_v3.json")
    lineage = read_jsonl(runtime / "qadam_paper_trade_lineage.jsonl")
    postmortems = read_jsonl(runtime / "qadam_paper_postmortems_v3.jsonl")
    proof = read_json(runtime / "qadam_paper_proof_eligibility.json")
    performance = read_json(runtime / "qadam_paper_performance_summary.json")
    learning = read_jsonl(runtime / "qadam_learning_attribution_v3.jsonl")
    improvements = read_jsonl(runtime / "qadam_improvement_proposals.jsonl")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    dashboard = read_json(runtime / "qadam_dashboard_epoch_isolation.json")
    public_bridge = read_json(runtime / "qadam_public_status_bridge_checks.json")
    epoch_id = str(epoch.get("paper_epoch_id") or "").strip()
    clean = epoch.get("paper_epoch_kind") == "clean_operator_epoch" and bool(epoch_id)
    mismatched_lineage = [
        str(record.get("lineage_record_id") or "unknown")
        for record in lineage
        if clean and record.get("paper_epoch_id") != epoch_id
    ]
    proof_ids = set(str(value) for value in proof.get("proof_eligible_lineage_record_ids", []))
    current_lineage_ids = {
        str(record.get("lineage_record_id"))
        for record in lineage
        if record.get("lineage_record_id")
    }
    proof_leaks = sorted(proof_ids - current_lineage_ids)
    unsafe_improvements = [
        str(record.get("proposal_id") or "unknown")
        for record in improvements
        if record.get("applied") is True
        and not (
            isinstance(record.get("approval"), dict)
            and record.get("approval", {}).get("approved") is True
        )
    ]
    launched = launch.get("guarded_paper_operation_running") is True
    monitoring_active = bool(
        launched
        and clean
        and service.get("service_running") is True
        and dashboard.get("status") == "passed"
        and not mismatched_lineage
        and not proof_leaks
        and not unsafe_improvements
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_operating_status",
        "generated_at": now_iso(),
        "status": (
            "monitoring_active"
            if monitoring_active
            else "waiting_for_guarded_launch"
            if not launched
            else "blocked"
        ),
        "post_launch_monitoring_active": monitoring_active,
        "paper_epoch_id": epoch_id or None,
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or "legacy_test",
        "starting_balance": epoch.get("starting_balance"),
        "account_currency": epoch.get("account_currency"),
        "service_running": service.get("service_running") is True,
        "dashboard_epoch_isolation_passed": dashboard.get("status") == "passed",
        "public_bridge_operating_ready": public_bridge.get("operating_ready") is True,
        "current_epoch_order_count": int(lifecycle.get("order_record_count") or 0),
        "current_epoch_position_count": int(lifecycle.get("position_record_count") or 0),
        "current_epoch_closed_trade_count": int(
            lifecycle.get("closed_trade_record_count") or 0
        ),
        "current_epoch_lineage_count": len(lineage),
        "current_epoch_postmortem_count": len(postmortems),
        "proof_eligible_count": int(proof.get("proof_eligible_count") or 0),
        "proof_credit_created_count": int(proof.get("proof_credit_created_count") or 0),
        "realized_net_pnl": performance.get("qadam_realized_net_pnl"),
        "performance_claim_allowed": performance.get("performance_claim_allowed") is True,
        "learning_attribution_record_count": len(learning),
        "strategy_changes_proposal_only": not unsafe_improvements,
        "epoch_mismatched_lineage_count": len(mismatched_lineage),
        "epoch_mismatched_lineage_ids": mismatched_lineage[:25],
        "proof_epoch_leak_count": len(proof_leaks),
        "proof_epoch_leak_ids": proof_leaks[:25],
        "unsafe_applied_improvement_count": len(unsafe_improvements),
        "unsafe_applied_improvement_ids": unsafe_improvements[:25],
        "real_calendar_only": True,
        "forced_trade_allowed": False,
        "live_capital_enabled": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }


def validate_clean_epoch_operating_status(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("post_launch_monitoring_active") is True:
        for field in (
            "service_running",
            "dashboard_epoch_isolation_passed",
            "strategy_changes_proposal_only",
            "real_calendar_only",
        ):
            if payload.get(field) is not True:
                errors.append(f"clean_epoch_monitoring_without_gate:{field}")
        if payload.get("paper_epoch_kind") != "clean_operator_epoch":
            errors.append("clean_epoch_monitoring_wrong_epoch_kind")
    for field in (
        "epoch_mismatched_lineage_count",
        "proof_epoch_leak_count",
        "unsafe_applied_improvement_count",
        "proof_credit_created_count",
    ):
        if int(payload.get(field) or 0) != 0:
            errors.append(f"clean_epoch_operating_forbidden_count:{field}")
    if payload.get("forced_trade_allowed") is not False:
        errors.append("clean_epoch_operating_forced_trade_allowed")
    if payload.get("live_capital_enabled") is not False:
        errors.append("clean_epoch_operating_live_capital_enabled")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="clean_epoch_operating"))
    return unique_errors(errors)


def build_and_write_clean_epoch_operating_status(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload = build_clean_epoch_operating_status(settings)
    errors = validate_clean_epoch_operating_status(payload)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_operating_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "post_launch_monitoring_active": payload["post_launch_monitoring_active"],
        "paper_epoch_id": payload["paper_epoch_id"],
        "current_epoch_lineage_count": payload["current_epoch_lineage_count"],
        "proof_eligible_count": payload["proof_eligible_count"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, payload)
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "STATUS_ARTIFACT",
    "build_and_write_clean_epoch_operating_status",
    "build_clean_epoch_operating_status",
    "validate_clean_epoch_operating_status",
]
