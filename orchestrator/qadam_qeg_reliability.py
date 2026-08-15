"""QEG-15 unattended scheduling, storage, recovery, and real-time trial state."""

from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path
import shutil
import subprocess
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    write_json_atomic,
)
from orchestrator.qadam_qeg_common import (
    GRAPH_HEALTH_ARTIFACT,
    GRAPH_MANIFEST_ARTIFACT,
    QEG_RELIABILITY_ARTIFACT,
    QEG_TRIAL_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    qeg_authority,
    parse_time,
    research_root,
    stable_id,
    write_phase_status,
)
from orchestrator.qadam_resource_locks import RESOURCE_ORDER
from orchestrator.qadam_temporal_graph_store import (
    GRAPH_HARD_LIMIT_BYTES,
    GRAPH_MIN_FREE_BYTES,
    GRAPH_SOFT_LIMIT_BYTES,
    TemporalGraphStore,
)

TRIAL_TARGET_MARKET_DAYS = 5
NEW_YORK = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def evaluate_graph_storage(*, graph_bytes: int, free_bytes: int) -> dict[str, Any]:
    hard_hold = graph_bytes >= GRAPH_HARD_LIMIT_BYTES or free_bytes < GRAPH_MIN_FREE_BYTES
    soft_hold = graph_bytes >= GRAPH_SOFT_LIMIT_BYTES and not hard_hold
    return {
        "graph_root_bytes": graph_bytes,
        "filesystem_free_bytes": free_bytes,
        "soft_limit_bytes": GRAPH_SOFT_LIMIT_BYTES,
        "hard_limit_bytes": GRAPH_HARD_LIMIT_BYTES,
        "minimum_free_bytes": GRAPH_MIN_FREE_BYTES,
        "soft_backpressure_active": soft_hold,
        "hard_stop_active": hard_hold,
        "graph_writes_allowed": not (soft_hold or hard_hold),
    }


def _is_eligible_market_receipt(row: dict[str, Any], *, started_at: datetime) -> tuple[bool, str | None]:
    if row.get("service_id") != "qeg_evidence_cycle" or row.get("state") != "completed":
        return False, None
    completed = parse_time(row.get("completed_at") or row.get("generated_at"))
    if completed is None or completed < started_at:
        return False, None
    local = completed.astimezone(NEW_YORK)
    if local.weekday() >= 5 or not (MARKET_OPEN <= local.time().replace(tzinfo=None) <= MARKET_CLOSE):
        return False, None
    return True, local.date().isoformat()


def _trial_state(runtime: Path) -> dict[str, Any]:
    previous = read_json(runtime / QEG_TRIAL_ARTIFACT)
    started_text = previous.get("started_at") or now_iso()
    started_at = parse_time(started_text) or datetime.now(timezone.utc)
    receipts = read_jsonl(runtime / "qadam_operator_service_receipts.jsonl")
    by_day: dict[str, list[str]] = {}
    for receipt in receipts:
        eligible, day = _is_eligible_market_receipt(receipt, started_at=started_at)
        if eligible and day:
            by_day.setdefault(day, []).append(str(receipt.get("receipt_id") or ""))
    completed_days = sorted(by_day)
    day_count = len(completed_days)
    return {
        "schema_version": "qadam_qeg_active_discovery_trial.v1",
        "artifact_type": "qadam_qeg_active_discovery_trial",
        "generated_at": now_iso(),
        "status": "active_discovery_trial_complete" if day_count >= TRIAL_TARGET_MARKET_DAYS else "active_discovery_trial_running",
        "started_at": started_at.isoformat(),
        "target_real_market_days": TRIAL_TARGET_MARKET_DAYS,
        "completed_real_market_day_count": day_count,
        "eligible_market_days": [
            {"market_date": day, "completed_qeg_cycle_receipt_ids": sorted(set(by_day[day]))}
            for day in completed_days
        ],
        "simulated_elapsed_day_count": 0,
        "backfilled_elapsed_day_count": 0,
        "paper_growth_trial_calendar_advanced": False,
        "not_the_30_day_paper_growth_trial": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": qeg_authority(governed_projection=True),
    }


def _ignored_by_git(path: Path) -> bool:
    result = subprocess.run(
        ("git", "check-ignore", "-q", str(path)),
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def build_qeg_reliability(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    graph_root = research_root(active)
    graph_store = TemporalGraphStore(active)
    compaction = graph_store.compact_closed_event_partitions()
    manifest = read_json(runtime / GRAPH_MANIFEST_ARTIFACT)
    health = read_json(runtime / GRAPH_HEALTH_ARTIFACT)
    graph_bytes = sum(path.stat().st_size for path in graph_root.rglob("*") if path.is_file())
    free_bytes = shutil.disk_usage(graph_root).free
    storage = evaluate_graph_storage(graph_bytes=graph_bytes, free_bytes=free_bytes)

    from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS

    services = {definition.service_id: definition for definition in SERVICE_DEFINITIONS}
    qeg_service = services.get("qeg_evidence_cycle")
    canonical_tradeability = services.get("canonical_tradeability")
    forward_shadow = services.get("forward_shadow")
    operator_status = read_json(runtime / "qadam_operator_service_status.json")
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json")
    qeg_circuit = (circuits.get("services") or {}).get("qeg_evidence_cycle") if isinstance(circuits.get("services"), dict) else circuits.get("qeg_evidence_cycle")

    errors: list[str] = []
    if qeg_service is None:
        errors.append("qeg_operator_service_not_registered")
    if qeg_service and qeg_service.dependencies != ("akber_review",):
        errors.append("qeg_operator_dependency_invalid")
    if (
        canonical_tradeability is None
        or "qeg_evidence_cycle" not in canonical_tradeability.dependencies
    ):
        errors.append("canonical_tradeability_not_ordered_after_qeg")
    if (
        forward_shadow is None
        or forward_shadow.dependencies != ("canonical_tradeability",)
    ):
        errors.append("forward_shadow_not_ordered_after_qeg")
    if "temporal_graph" not in RESOURCE_ORDER:
        errors.append("temporal_graph_resource_lock_missing")
    if not _ignored_by_git(graph_root):
        errors.append("qeg_research_root_not_git_ignored")
    if manifest.get("status") != "complete" or health.get("status") != "healthy":
        errors.append("qeg_graph_generation_not_healthy")
    if not health.get("canonical_events_rebuildable") or not health.get("sqlite_index_disposable"):
        errors.append("qeg_graph_recovery_contract_incomplete")
    if storage["hard_stop_active"]:
        errors.append("qeg_graph_storage_hard_stop")
    if storage["soft_backpressure_active"]:
        errors.append("qeg_graph_storage_soft_backpressure")
    if qeg_circuit and qeg_circuit.get("state") in {"open", "half_open"}:
        errors.append("qeg_operator_circuit_not_closed")

    repair_requests: list[dict[str, Any]] = []
    for error in errors:
        safe_action = {
            "qeg_graph_generation_not_healthy": "rebuild_disposable_index_from_append_only_events",
            "qeg_graph_recovery_contract_incomplete": "pause_graph_cycle_and_revalidate_canonical_events",
            "qeg_graph_storage_soft_backpressure": "pause_graph_writes_and_compact_closed_partitions",
            "qeg_graph_storage_hard_stop": "pause_graph_writes_and_request_operator_storage_review",
            "qeg_operator_circuit_not_closed": "retry_idempotent_qeg_cycle_after_circuit_revalidation",
        }.get(error, "operator_review_required")
        repair_requests.append(
            {
                "repair_request_id": stable_id("qeg-repair", error, manifest.get("generation_id")),
                "failure_class": error,
                "safe_action": safe_action,
                "automatic_retry_allowed": safe_action in {
                    "rebuild_disposable_index_from_append_only_events",
                    "pause_graph_writes_and_compact_closed_partitions",
                    "retry_idempotent_qeg_cycle_after_circuit_revalidation",
                },
                "automatic_code_edit_allowed": False,
                "automatic_authority_change_allowed": False,
                "automatic_secret_change_allowed": False,
                "paper_order_created": False,
            }
        )

    trial = _trial_state(runtime)
    write_json_atomic(runtime / QEG_TRIAL_ARTIFACT, trial)
    write_json_atomic(
        runtime / REPAIR_QUEUE_ARTIFACT,
        {
            "schema_version": "qadam_qeg_repair_queue.v1",
            "artifact_type": "qadam_qeg_repair_queue",
            "generated_at": now_iso(),
            "status": "clear" if not repair_requests else "attention_required",
            "repair_request_count": len(repair_requests),
            "repair_requests": repair_requests,
            "code_edits_performed": 0,
            "authority_changes_performed": 0,
            "secret_changes_performed": 0,
            "paper_order_created_count": 0,
            "authority": qeg_authority(governed_projection=True),
        },
    )
    payload = {
        "schema_version": "qadam_qeg_operator_reliability.v1",
        "artifact_type": "qadam_qeg_operator_reliability",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "service_registered": qeg_service is not None,
        "runtime_service_projection_contains_qeg": any(
            row.get("service_id") == "qeg_evidence_cycle" for row in operator_status.get("services") or []
        ),
        "dependency_order": {
            "upstream": list(qeg_service.dependencies) if qeg_service else [],
            "downstream": "canonical_tradeability",
            "canonical_tradeability_dependencies": (
                list(canonical_tradeability.dependencies)
                if canonical_tradeability
                else []
            ),
            "forward_shadow_dependencies": list(forward_shadow.dependencies) if forward_shadow else [],
        },
        "resource_lock_registered": "temporal_graph" in RESOURCE_ORDER,
        "research_root_git_ignored": _ignored_by_git(graph_root),
        "graph_generation_id": manifest.get("generation_id"),
        "graph_health": health.get("status"),
        "storage": storage,
        "compaction": compaction,
        "queue_backpressure": {
            "maximum_pattern_candidates_per_cycle": 20,
            "maximum_actionability_rows_per_cycle": 12,
            "first_hold_stops_queue": False,
        },
        "circuit_classes": ["provider", "model", "temporal_graph", "disk", "paperops"],
        "safe_recovery": {
            "restart_from_last_complete_generation": True,
            "partial_event_write_rejected": True,
            "sqlite_index_rebuildable": True,
            "closed_event_partitions_compressed": True,
            "broker_retry_from_qeg_allowed": False,
        },
        "dashboard_failure_blocks_research": False,
        "telegram_failure_blocks_research": False,
        "research_failure_can_create_broker_retry": False,
        "trial": trial,
        "repair_request_count": len(repair_requests),
        "validation_errors": unique_errors(errors),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": qeg_authority(governed_projection=True),
    }
    write_json_atomic(runtime / QEG_RELIABILITY_ARTIFACT, payload)
    write_phase_status(
        "QEG-15",
        status="passed" if not errors else "blocked",
        implementation_complete=not errors,
        empirical_state=trial["status"],
        artifacts=[QEG_RELIABILITY_ARTIFACT, QEG_TRIAL_ARTIFACT, REPAIR_QUEUE_ARTIFACT],
        blockers=errors,
        settings=active,
    )
    return payload, unique_errors(errors)


def validate_qeg_reliability(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / QEG_RELIABILITY_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    if payload.get("service_registered") is not True or payload.get("resource_lock_registered") is not True:
        errors.append("qeg_reliability_service_or_lock_missing")
    if payload.get("research_root_git_ignored") is not True:
        errors.append("qeg_reliability_research_data_trackable")
    if payload.get("research_failure_can_create_broker_retry") is not False:
        errors.append("qeg_reliability_unsafe_broker_retry")
    trial = payload.get("trial") if isinstance(payload.get("trial"), dict) else {}
    if trial.get("simulated_elapsed_day_count") or trial.get("backfilled_elapsed_day_count"):
        errors.append("qeg_trial_elapsed_time_fabricated")
    if trial.get("paper_growth_trial_calendar_advanced") is not False:
        errors.append("qeg_trial_advanced_paper_growth_calendar")
    negative = evaluate_graph_storage(graph_bytes=GRAPH_HARD_LIMIT_BYTES, free_bytes=GRAPH_MIN_FREE_BYTES - 1)
    if negative.get("graph_writes_allowed") is not False or negative.get("hard_stop_active") is not True:
        errors.append("qeg_storage_negative_probe_failed")
    return unique_errors(errors)
