"""Permanent operator-reliability status, soak, and fail-closed certification."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore
from orchestrator.qadam_artifact_ownership import build_artifact_ownership_audit
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    validate_authority,
    write_json_atomic,
)
from orchestrator.qadam_operator_service import (
    CIRCUIT_BREAKERS_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    SERVICE_DEFINITIONS,
    SESSION_LEDGER_ARTIFACT,
    STATUS_ARTIFACT,
    _last_successful_receipts,
    operator_build_identity,
)
from orchestrator.qadam_state_root import build_state_root_preflight
from orchestrator.qadam_storage_retention import (
    STATUS_ARTIFACT as STORAGE_STATUS_ARTIFACT,
    live_storage_health,
    validate_storage_status,
)

SCHEMA_VERSION = "qadam_permanent_operator_reliability.v1"
SOAK_ARTIFACT = "qadam_permanent_operator_reliability_soak.json"
CERTIFICATION_ARTIFACT = "qadam_permanent_operator_reliability_certification.json"
STATUS_SUMMARY_ARTIFACT = "qadam_permanent_operator_reliability_status.json"
REQUIRED_SOAK_SECONDS = 24 * 60 * 60
REQUIRED_SOAK_SESSIONS = 120


def _parse(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _market_period(timestamp: datetime) -> str:
    local = timestamp.astimezone(ZoneInfo("America/New_York"))
    if local.weekday() >= 5:
        return "market_closed"
    minutes = local.hour * 60 + local.minute
    return "market_open" if 570 <= minutes < 960 else "market_closed"


def build_reliability_soak(runtime: Path | None = None) -> dict[str, Any]:
    runtime = (runtime or runtime_dir()).resolve()
    now = datetime.now(timezone.utc)
    build_identity = operator_build_identity()
    identity = {
        key: build_identity.get(key)
        for key in (
            "service_contract_hash",
            "git_commit",
            "dirty_worktree_digest",
            "python_executable",
            "python_version",
            "dependency_lock_digest",
            "state_root",
            "launchd_template_sha256",
        )
    }
    prior = read_json(runtime / SOAK_ARTIFACT)
    if prior.get("activation_identity") == identity and _parse(prior.get("started_at")):
        started = _parse(prior.get("started_at")) or now
    else:
        started = now
    sessions = []
    for record in read_jsonl(runtime / SESSION_LEDGER_ARTIFACT):
        generated = _parse(record.get("generated_at"))
        if generated is not None and generated >= started:
            sessions.append((generated, record))
    invalid_sessions = [
        (generated, record)
        for generated, record in sessions
        if record.get("operator_observation_ready") is not True
        or int(record.get("dispatch_failed_count") or 0) != 0
        or record.get("operator_build_identity_matches") is not True
        or validate_authority(record.get("authority") or {}, prefix="soak_session_authority")
    ]
    if invalid_sessions:
        # A reliability soak is contiguous. Any unhealthy session starts a new
        # evidence window instead of allowing later healthy sessions to hide it.
        started = max(generated for generated, _record in invalid_sessions)
        sessions = [(generated, record) for generated, record in sessions if generated > started]
    periods = sorted({_market_period(timestamp) for timestamp, _record in sessions})
    failure_count = sum(
        int(record.get("dispatch_failed_count") or 0) for _timestamp, record in sessions
    )
    paper_order_count = sum(
        int(record.get("paper_order_created_count") or 0) for _timestamp, record in sessions
    )
    broker_write_count = sum(
        int(record.get("broker_write_count") or 0) for _timestamp, record in sessions
    )
    elapsed = max(0.0, (now - started).total_seconds())
    circuits = read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT)
    open_circuits = int(circuits.get("open_circuit_count") or 0)
    repair_queue = read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    complete = (
        elapsed >= REQUIRED_SOAK_SECONDS
        and len(sessions) >= REQUIRED_SOAK_SESSIONS
        and set(periods) == {"market_closed", "market_open"}
        and failure_count == 0
        and open_circuits == 0
        and int(repair_queue.get("critical_request_count") or 0) == 0
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_permanent_operator_reliability_soak",
        "generated_at": now.isoformat(),
        "status": "passed" if complete else "running",
        "started_at": started.isoformat(),
        "activation_identity": identity,
        "real_elapsed_seconds": elapsed,
        "required_elapsed_seconds": REQUIRED_SOAK_SECONDS,
        "real_session_count": len(sessions),
        "required_session_count": REQUIRED_SOAK_SESSIONS,
        "observed_market_periods": periods,
        "required_market_periods": ["market_closed", "market_open"],
        "dispatch_failure_count": failure_count,
        "invalid_session_count": len(invalid_sessions),
        "all_counted_sessions_observation_ready": all(
            record.get("operator_observation_ready") is True for _timestamp, record in sessions
        ),
        "open_circuit_count": open_circuits,
        "critical_repair_request_count": int(repair_queue.get("critical_request_count") or 0),
        "paper_order_created_count": paper_order_count,
        "broker_write_count": broker_write_count,
        "simulated_elapsed_time_used": False,
        "paper_growth_trial_calendar_advanced_by_soak": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / SOAK_ARTIFACT, result)
    return result


def _generation_checks(runtime: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records = []
    errors = []
    resources = sorted(
        {
            resource
            for definition in SERVICE_DEFINITIONS
            for resource in (*definition.write_resources, *definition.append_resources)
        }
    )
    for resource in resources:
        store = ArtifactGenerationStore(runtime, resource)
        try:
            reference = store.resolve_current()
        except Exception as exc:
            records.append({"resource": resource, "status": "not_yet_published", "error": str(exc)})
            errors.append(f"generation_not_ready:{resource}")
            continue
        records.append(
            {
                "resource": resource,
                "status": "passed",
                "generation_id": reference.generation_id,
                "producer": reference.manifest.get("producer"),
            }
        )
    return records, errors


def build_permanent_reliability_certification(
    runtime: Path | None = None,
) -> dict[str, Any]:
    runtime = (runtime or runtime_dir()).resolve()
    state_root = build_state_root_preflight()
    ownership = build_artifact_ownership_audit(runtime)
    locks = read_json(runtime / "qadam_resource_lock_checks.json")
    generations_probe = read_json(runtime / "qadam_artifact_generation_checks.json")
    generations, generation_errors = _generation_checks(runtime)
    operator = read_json(runtime / STATUS_ARTIFACT)
    circuits = read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT)
    repair_queue = read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    storage_status = read_json(runtime / STORAGE_STATUS_ARTIFACT)
    storage_status = {
        **storage_status,
        "disk": live_storage_health(
            runtime,
            previous=(
                storage_status.get("disk")
                if isinstance(storage_status.get("disk"), dict)
                else None
            ),
        ),
    }
    storage_errors = validate_storage_status(storage_status)
    soak = build_reliability_soak(runtime)
    latest_receipts = _last_successful_receipts(runtime)
    generation_binding_records = []
    generation_binding_errors = []
    for definition in SERVICE_DEFINITIONS:
        if not definition.read_resources:
            continue
        receipt = latest_receipts.get(definition.service_id) or {}
        complete = receipt.get("input_generation_binding_complete") is True
        mixed_count = int(receipt.get("mixed_generation_join_count") or 0)
        generation_binding_records.append(
            {
                "service_id": definition.service_id,
                "receipt_id": receipt.get("receipt_id"),
                "input_generation_ids": receipt.get("input_generation_ids") or {},
                "binding_complete": complete,
                "mixed_generation_join_count": mixed_count,
            }
        )
        if not complete:
            generation_binding_errors.append(
                f"input_generation_binding_incomplete:{definition.service_id}"
            )
        if mixed_count:
            generation_binding_errors.append(
                f"mixed_generation_join:{definition.service_id}:{mixed_count}"
            )
    operator_authority = operator.get("authority") or {}
    authority_valid = not validate_authority(
        operator_authority,
        prefix="operator_authority",
    )
    groups = {
        "state_root": state_root.get("status") == "passed",
        "artifact_ownership": ownership.get("status") == "passed",
        "resource_locks": locks.get("status") == "passed",
        "generation_protocol": generations_probe.get("status") == "passed",
        "generation_publication": not generation_errors,
        "generation_binding": not generation_binding_errors,
        "operator_running": operator.get("service_running") is True,
        "build_binding": operator.get("build_identity", {}).get("running_build_matches_current")
        is True,
        "launchd_binding": operator.get("launchd", {}).get("installed_template_matches") is True,
        "circuits_closed": int(circuits.get("open_circuit_count") or 0) == 0,
        "repair_queue_clear": int(repair_queue.get("open_request_count") or 0) == 0,
        "storage_retention": not storage_errors,
        "paper_only": authority_valid
        and operator_authority.get("paper_only") is True
        and operator_authority.get("live_capital_enabled") is False
        and operator_authority.get("live_broker_endpoint_allowed") is False,
        "guarded_paperops_only": operator.get("direct_broker_client_import_allowed") is False,
        "real_soak": soak.get("status") == "passed",
    }
    implementation_groups = {key: value for key, value in groups.items() if key != "real_soak"}
    implementation_complete = all(implementation_groups.values())
    permanent_certified = implementation_complete and groups["real_soak"]
    blockers = [key for key, passed in groups.items() if not passed]
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_permanent_operator_reliability_certification",
        "generated_at": now_iso(),
        "status": (
            "passed"
            if permanent_certified
            else "provisional_soak"
            if implementation_complete
            else "blocked"
        ),
        "implementation_complete": implementation_complete,
        "permanent_reliability_certified": permanent_certified,
        "certification_groups": groups,
        "generation_records": generations,
        "generation_binding_records": generation_binding_records,
        "generation_binding_errors": generation_binding_errors,
        "storage_retention": storage_status,
        "storage_retention_errors": storage_errors,
        "soak": soak,
        "blockers": blockers,
        "guarantee_boundary": (
            "This certifies the tested operating contract and sustained soak; "
            "it does not promise that hardware, providers, networks, or software "
            "can never fail. Failures must remain bounded, truthful, and recoverable."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / CERTIFICATION_ARTIFACT, result)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_permanent_operator_reliability_status",
        "generated_at": result["generated_at"],
        "status": result["status"],
        "implementation_complete": implementation_complete,
        "permanent_reliability_certified": permanent_certified,
        "open_circuit_count": int(circuits.get("open_circuit_count") or 0),
        "repair_request_count": int(repair_queue.get("open_request_count") or 0),
        "real_soak_elapsed_seconds": soak.get("real_elapsed_seconds"),
        "real_soak_required_seconds": REQUIRED_SOAK_SECONDS,
        "blockers": blockers,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / STATUS_SUMMARY_ARTIFACT, summary)
    return result
