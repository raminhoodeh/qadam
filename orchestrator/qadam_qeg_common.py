"""Shared primitives for the Qadam Evidence Graph programme.

The QEG layer is an evidence and coordination plane.  It deliberately inherits
Qadam's existing authority contract and never becomes a broker-write actor.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_evidence_graph.v1"
PROGRAM_ID = "qadam_compounding_evidence_graph"
PHASE_IDS = tuple(f"QEG-{index}" for index in range(17))

PHASE_STATUS_ARTIFACT = "qadam_qeg_phase_status.json"
REPAIR_QUEUE_ARTIFACT = "qadam_qeg_repair_queue.json"
BASELINE_ARTIFACT = "qadam_qeg_baseline.json"
OWNERSHIP_ARTIFACT = "qadam_qeg_artifact_ownership.json"
COMPATIBILITY_ARTIFACT = "qadam_qeg_compatibility_matrix.json"
DASHBOARD_UX_BASELINE_ARTIFACT = "qadam_qeg_dashboard_ux_baseline.json"

GRAPH_MANIFEST_ARTIFACT = "qadam_temporal_graph_manifest.json"
GRAPH_HEALTH_ARTIFACT = "qadam_temporal_graph_health.json"
CLAIM_SUMMARY_ARTIFACT = "qadam_claim_registry_summary.json"
REFERENCE_SUMMARY_ARTIFACT = "qadam_reference_registry_summary.json"
EXPERIMENT_SUMMARY_ARTIFACT = "qadam_experiment_memory_summary.json"
PATTERN_CANDIDATES_ARTIFACT = "qadam_graph_pattern_candidates.json"
ACTIONABILITY_QUEUE_ARTIFACT = "qadam_actionability_queue.json"
EXPERIMENT_BRIDGE_ARTIFACT = "qadam_graph_experiment_bridge.json"
QUANTUM_CHALLENGER_ARTIFACT = "qadam_graph_quantum_challenger.json"
STRATEGY_VERSIONS_ARTIFACT = "qadam_graph_strategy_versions.json"
PAPER_ADMISSION_ARTIFACT = "qadam_paper_strategy_admission.json"
ACTIVE_DISCOVERY_FUNNEL_ARTIFACT = "qadam_graph_active_discovery_funnel.json"
MULTI_SETUP_ARTIFACT = "qadam_multi_setup_paperops.json"
OUTCOME_LEARNING_ARTIFACT = "qadam_graph_outcome_learning_summary.json"
CHALLENGER_TOURNAMENT_ARTIFACT = "qadam_strategy_challenger_tournament.json"
QEG_DASHBOARD_ARTIFACT = "qadam_qeg_dashboard_projection.json"
QEG_TELEGRAM_ARTIFACT = "qadam_qeg_telegram_projection.json"
QEG_TELEGRAM_DEDUPE_ARTIFACT = "qadam_qeg_telegram_dedupe_ledger.jsonl"
QEG_RESOURCE_REGISTRY_ARTIFACT = "qadam_qeg_curated_resource_registry.json"
QEG_HYPOTHESES_ARTIFACT = "qadam_qeg_strategy_hypotheses.jsonl"
QEG_DECISION_PACKETS_ARTIFACT = "qadam_qeg_decision_evidence_packets.jsonl"
QEG_AKBER_INPUTS_ARTIFACT = "qadam_qeg_akber_inputs.jsonl"
QEG_AKBER_RESULTS_ARTIFACT = "qadam_qeg_akber_results.jsonl"
QEG_RELIABILITY_ARTIFACT = "qadam_qeg_operator_reliability.json"
QEG_TRIAL_ARTIFACT = "qadam_qeg_active_discovery_trial.json"
QEG_CYCLE_ARTIFACT = "qadam_qeg_cycle_summary.json"
CERTIFICATION_ARTIFACT = "qadam_compounding_evidence_graph_certification.json"

ATTACHMENT_SHA256 = "0961d7296975372614d440ff002e41d269671b8b51a631642b25c47e5c2de6f5"
ATTACHMENT_PATH = Path(
    "/tmp/codex-remote-attachments/019ea17c-4579-73d1-9bda-81dc99971a47/"
    "9EF4B29C-62DB-43AA-B15C-D17A3E1FD36E/"
    "1-Qadam-3366fe2ecf3780dcabeec1e27c28365e.md"
)


def qeg_authority(*, governed_projection: bool = False) -> dict[str, Any]:
    flags = authority_flags()
    flags.update(
        {
            "temporal_graph_write_allowed": not governed_projection,
            "governed_projection_only": governed_projection,
            "graph_can_satisfy_source_quorum_alone": False,
            "graph_can_create_strategy_authority": False,
            "graph_can_create_trade_authority": False,
            "automatic_code_mutation_allowed": False,
            "automatic_risk_envelope_expansion_allowed": False,
        }
    )
    return flags


def research_root(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    data_root = Path(active.data_root)
    if not data_root.is_absolute():
        data_root = ROOT / data_root
    path = data_root / "research/qadam_temporal_evidence_graph"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def record_hash(payload: dict[str, Any], *, omit: Iterable[str] = ()) -> str:
    ignored = set(omit)
    return sha256_json({key: value for key, value in payload.items() if key not in ignored})


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def public_artifact(name: str) -> str:
    return f"data/runtime/{name}"


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    payload = read_json(path)
    for key in (
        "records",
        "rows",
        "sources",
        "instruments",
        "hypotheses",
        "strategies",
        "decisions",
        "results",
    ):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return [payload] if payload else []


def write_phase_status(
    phase_id: str,
    *,
    status: str,
    implementation_complete: bool,
    empirical_state: str,
    artifacts: Iterable[str] = (),
    blockers: Iterable[str] = (),
    settings: Settings | None = None,
) -> dict[str, Any]:
    if phase_id not in PHASE_IDS:
        raise ValueError(f"unknown_qeg_phase:{phase_id}")
    runtime = runtime_dir(settings)
    path = runtime / PHASE_STATUS_ARTIFACT
    current = read_json(path)
    phases = current.get("phases") if isinstance(current.get("phases"), dict) else {}
    phases[phase_id] = {
        "phase_id": phase_id,
        "status": status,
        "implementation_complete": implementation_complete,
        "empirical_state": empirical_state,
        "artifacts": sorted(set(str(item) for item in artifacts)),
        "blockers": sorted(set(str(item) for item in blockers)),
        "updated_at": now_iso(),
    }
    completed = sum(bool(item.get("implementation_complete")) for item in phases.values())
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_qeg_phase_status",
        "generated_at": now_iso(),
        "status": "implementation_complete" if completed == len(PHASE_IDS) else "implementation_in_progress",
        "phase_count": len(PHASE_IDS),
        "recorded_phase_count": len(phases),
        "implementation_complete_phase_count": completed,
        "phases": dict(sorted(phases.items())),
        "authority": qeg_authority(),
    }
    write_json_atomic(path, payload)
    return payload


def artifact_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)), "exists": False}
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": digest,
    }


def runtime_input(name: str, settings: Settings | None = None) -> Path:
    return runtime_dir(settings) / name


def freshness_label(generated_at: Any, *, now: datetime | None = None, max_age_seconds: int = 900) -> str:
    parsed = parse_time(generated_at)
    if parsed is None:
        return "unknown"
    age = ((now or datetime.now(timezone.utc)) - parsed).total_seconds()
    if age < -60:
        return "future_dated"
    return "fresh" if age <= max_age_seconds else "stale"
