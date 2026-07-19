"""Canonical artifact producer registry and safe refresh receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_runtime_producer_registry.v1"
REGISTRY_ARTIFACT = "qadam_runtime_producer_registry.json"
FRESHNESS_CLOSURE_ARTIFACT = "qadam_runtime_freshness_closure.json"
SOURCE_REPAIR_CLOSURE_ARTIFACT = "qadam_source_repair_closure.json"
RECEIPTS_ARTIFACT = "qadam_operator_job_receipts.jsonl"


@dataclass(frozen=True)
class Producer:
    producer_id: str
    purpose: str
    cadence_seconds: int
    artifact_names: tuple[str, ...]
    command_sequence: tuple[tuple[str, ...], ...]
    safe_refresh: bool = True
    may_call_network: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PRODUCERS = (
    Producer(
        "live_source_ingestion",
        "Run bounded real provider reads and retain evidence timestamps separately from health checks.",
        900,
        (
            "phase1_live_source_validation.json",
            "qadam_live_source_refresh_receipt.json",
        ),
        (
            ("scripts/run_source_heartbeat.py", "--once"),
            ("scripts/run_qadam_live_source_refresh.py", "--max-sources", "10"),
        ),
        may_call_network=True,
    ),
    Producer(
        "source_price_matrix_projection",
        "Rebuild the frozen 41-by-19 matrix from current evidence provenance.",
        900,
        (
            "qsase_universal_source_price_matrix.json",
            "qsase_source_reliability.json",
        ),
        (
            ("scripts/check_qsase_universal_source_price_matrix.py",),
            ("scripts/check_qsase_source_reliability.py",),
        ),
    ),
    Producer(
        "source_capability_projection",
        "Classify source freshness, history support, quarantine, and repairs.",
        900,
        (
            "qadam_source_operational_state.jsonl",
            "qadam_source_provider_capabilities_checks.json",
        ),
        (("scripts/check_qadam_source_provider_capabilities.py",),),
    ),
    Producer(
        "point_in_time_evidence_projection",
        "Rebuild point-in-time source-price eligibility and leakage evidence before scoring.",
        900,
        (
            "qadam_point_in_time_alignment_summary.json",
            "qadam_point_in_time_evidence_checks.json",
        ),
        (("scripts/check_qadam_point_in_time_evidence.py",),),
    ),
    Producer(
        "pattern_score_projection",
        "Refresh point-in-time pattern score records without creating candidates.",
        900,
        (
            "qadam_pattern_score_v3_records.jsonl",
            "qadam_pattern_score_v3_checks.json",
        ),
        (
            ("scripts/run_qadam_pattern_score_tape.py", "--resume"),
            ("scripts/check_qadam_pattern_score_v3.py",),
        ),
    ),
    Producer(
        "research_evidence_validation",
        (
            "Rebuild labels, backtests, nonlinear review, and the edge registry in "
            "dependency order after pattern scores change."
        ),
        900,
        (
            "qadam_forward_labels_checks.json",
            "qadam_statistical_backtest_checks.json",
            "qadam_nonlinear_quantum_value_checks.json",
            "qadam_edge_registry_summary.json",
            "qadam_edge_registry_checks.json",
        ),
        (
            ("scripts/check_qadam_forward_labels.py",),
            ("scripts/check_qadam_statistical_backtest.py",),
            ("scripts/check_qadam_nonlinear_quantum_value.py",),
            ("scripts/check_qadam_edge_registry.py",),
        ),
    ),
    Producer(
        "router_projection",
        "Refresh single-state Router and dry-run PaperOps handoff decisions.",
        240,
        ("qadam_router_v3_scoreboard.json", "qadam_router_v3_paperops_checks.json"),
        (("scripts/check_qadam_router_v3_paperops.py",),),
    ),
    Producer(
        "paper_lifecycle_projection",
        "Refresh current paper lifecycle and proof-boundary state.",
        300,
        ("qadam_paper_lifecycle_v3.json", "qadam_paper_lineage_and_proof_checks.json"),
        (("scripts/check_qadam_paper_lineage_and_proof.py",),),
    ),
    Producer(
        "operator_soak_projection",
        "Count conservative real-session soak evidence without simulated time.",
        240,
        ("qadam_operator_soak_v2.json", "qadam_operator_soak_v2_checks.json"),
        (("scripts/check_qadam_operator_soak_v2.py",),),
    ),
    Producer(
        "qsase_dashboard_projection",
        "Refresh public-safe dashboard section artifacts from canonical runtime state.",
        300,
        (
            "qsase_dashboard_status.json",
            "qsase_dashboard_portfolio_value_series.json",
            "qsase_dashboard_current_portfolio.json",
        ),
        (("scripts/check_qsase_dashboard_view_model.py",),),
    ),
    Producer(
        "operator_certification_projection",
        "Refresh compatibility audit and fail-closed operator certification.",
        240,
        (
            "qadam_certification_contract_audit.json",
            "qadam_operator_ready_edge_engine_certification.json",
        ),
        (
            ("scripts/check_qadam_certification_contracts.py",),
            ("scripts/check_qadam_operator_ready_edge_engine.py",),
        ),
    ),
    Producer(
        "operator_dashboard_projection",
        "Refresh dashboard route view models and freshness labels.",
        240,
        (
            "qadam_operator_dashboard_view_model.json",
            "qadam_operator_dashboard_freshness.json",
        ),
        (("scripts/check_qadam_operator_dashboard.py",),),
    ),
    Producer(
        "clean_epoch_safety_projection",
        "Audit epoch isolation, guarded launch readiness, and post-launch proof discipline.",
        240,
        (
            "qadam_dashboard_epoch_isolation.json",
            "qadam_guarded_paper_launch_checks.json",
            "qadam_clean_epoch_operating_checks.json",
            "qadam_clean_epoch_operational_readiness_certification.json",
        ),
        (
            ("scripts/check_qadam_operator_ready_edge_engine.py",),
            ("scripts/check_qadam_operator_dashboard.py",),
            ("scripts/check_qadam_dashboard_epoch_isolation.py",),
            ("scripts/check_qadam_guarded_paper_launch.py",),
            ("scripts/check_qadam_clean_epoch_operating.py",),
            ("scripts/check_qadam_clean_epoch_operational_readiness.py",),
        ),
    ),
    Producer(
        "public_status_publication",
        "Publish the validated public-safe snapshot over the one-way signed bridge.",
        240,
        (
            "qadam_public_status_publication_receipt.json",
            "qadam_public_status_parity.json",
        ),
        (
            ("scripts/export_cockpit_status.py", "--no-landing-copy"),
            ("scripts/publish_qadam_public_status.py",),
        ),
        may_call_network=True,
    ),
)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _artifact_state(runtime: Path, artifact: str, cadence_seconds: int) -> dict[str, Any]:
    path = runtime / artifact
    payload = read_json(path) if path.suffix == ".json" else {}
    generated = _parse_timestamp(payload.get("generated_at"))
    if generated is None and path.exists():
        generated = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    age = int((datetime.now(timezone.utc) - generated).total_seconds()) if generated else None
    return {
        "artifact": f"data/runtime/{artifact}",
        "exists": path.exists(),
        "generated_at": generated.isoformat() if generated else None,
        "age_seconds": age,
        "stale_after_seconds": cadence_seconds * 2,
        "freshness_state": (
            "missing"
            if not path.exists()
            else "fresh"
            if age is not None and age <= cadence_seconds * 2
            else "stale"
        ),
    }


def build_registry(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    ownership: dict[str, list[str]] = {}
    producers: list[dict[str, Any]] = []
    for producer in PRODUCERS:
        for artifact in producer.artifact_names:
            ownership.setdefault(artifact, []).append(producer.producer_id)
        row = producer.to_dict()
        row["artifacts"] = [
            _artifact_state(runtime, artifact, producer.cadence_seconds)
            for artifact in producer.artifact_names
        ]
        producers.append(row)
    duplicate_owners = {
        artifact: owners for artifact, owners in ownership.items() if len(owners) != 1
    }
    records = [artifact for producer in producers for artifact in producer["artifacts"]]
    stale = [row for row in records if row["freshness_state"] != "fresh"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_runtime_producer_registry",
        "generated_at": now_iso(),
        "status": "passed" if not duplicate_owners else "blocked",
        "producer_count": len(producers),
        "artifact_count": len(records),
        "fresh_artifact_count": len(records) - len(stale),
        "stale_or_missing_artifact_count": len(stale),
        "duplicate_owner_count": len(duplicate_owners),
        "duplicate_owners": duplicate_owners,
        "producers": producers,
        "authority": authority_flags(),
        "boundary": (
            "Artifact ownership and safe deterministic refresh only. The registry "
            "cannot release locks, create orders, write to brokers, or grant proof."
        ),
    }
    write_json_atomic(runtime / REGISTRY_ARTIFACT, payload)
    build_source_repair_closure(settings)
    return payload


def build_source_repair_closure(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    checks = read_json(runtime / "qadam_source_provider_capabilities_checks.json")
    repair_path = runtime / "qadam_provider_repair_requests.jsonl"
    repair_records = []
    if repair_path.exists():
        import json

        with repair_path.open("r", encoding="utf-8") as handle:
            repair_records = [json.loads(line) for line in handle if line.strip()]
    blocking = [
        row for row in repair_records if row.get("blocks_current_scoring") is True
    ]
    nonblocking = [
        row for row in repair_records if row.get("blocks_current_scoring") is not True
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_repair_closure",
        "generated_at": now_iso(),
        "status": "passed" if not blocking else "blocked",
        "fresh_scoring_eligible_count": int(
            checks.get("fresh_scoring_eligible_count") or 0
        ),
        "blocking_repair_request_count": len(blocking),
        "nonblocking_repair_request_count": len(nonblocking),
        "quarantined_or_context_only_count": int(
            checks.get("quarantined_or_context_only_count") or 0
        ),
        "blocking_repairs": blocking,
        "nonblocking_repair_visibility_count": len(nonblocking),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / SOURCE_REPAIR_CLOSURE_ARTIFACT, payload)
    return payload


def _run_command(command: tuple[str, ...], timeout_seconds: int = 1800) -> dict[str, Any]:
    started = now_iso()
    try:
        completed = subprocess.run(
            [sys.executable, *command],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        status = "passed" if completed.returncode == 0 else "failed"
        returncode = completed.returncode
        stdout = completed.stdout.splitlines()[-80:]
        stderr = completed.stderr.splitlines()[-80:]
        error = None
    except (OSError, subprocess.TimeoutExpired) as exc:
        status = "failed"
        returncode = None
        stdout = []
        stderr = []
        error = f"{exc.__class__.__name__}:{exc}"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_job_receipt",
        "started_at": started,
        "completed_at": now_iso(),
        "command": list(command),
        "status": status,
        "returncode": returncode,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "error": error,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def refresh_safe_producers(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    receipts: list[dict[str, Any]] = []
    failed_producers: list[str] = []
    for producer in PRODUCERS:
        if not producer.safe_refresh or producer.may_call_network:
            continue
        producer_failed = False
        for command in producer.command_sequence:
            receipt = _run_command(command)
            receipt["producer_id"] = producer.producer_id
            append_jsonl_durable(runtime / RECEIPTS_ARTIFACT, receipt)
            receipts.append(receipt)
            if receipt["status"] != "passed":
                producer_failed = True
                break
        if producer_failed:
            failed_producers.append(producer.producer_id)
    registry = build_registry(settings)
    closure = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_runtime_freshness_closure",
        "generated_at": now_iso(),
        "status": (
            "passed"
            if not failed_producers
            and registry.get("stale_or_missing_artifact_count") == 0
            else "degraded"
        ),
        "receipt_count": len(receipts),
        "failed_producer_count": len(failed_producers),
        "failed_producers": failed_producers,
        "fresh_artifact_count": registry.get("fresh_artifact_count"),
        "stale_or_missing_artifact_count": registry.get(
            "stale_or_missing_artifact_count"
        ),
        "receipts_ref": f"data/runtime/{RECEIPTS_ARTIFACT}",
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / FRESHNESS_CLOSURE_ARTIFACT, closure)
    return closure


__all__ = [
    "FRESHNESS_CLOSURE_ARTIFACT",
    "PRODUCERS",
    "RECEIPTS_ARTIFACT",
    "REGISTRY_ARTIFACT",
    "SOURCE_REPAIR_CLOSURE_ARTIFACT",
    "build_registry",
    "build_source_repair_closure",
    "refresh_safe_producers",
]
