"""Build the durable CATC-0 through CATC-17 implementation status."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic

SCHEMA_VERSION = "qadam_catc_implementation_status.v1"
ARTIFACT = "qadam_catc_implementation_status.json"

PHASES = (
    ("CATC-0", "Quiescence, Evidence Freeze, And Worktree Protection", "qadam_catc_baseline.json"),
    ("CATC-1", "Runtime Authority And Supersession Registry", "qadam_runtime_authority_audit.json"),
    ("CATC-2", "Transactional Control-Plane Store", "qadam_control_plane_projection_summary.json"),
    ("CATC-3", "Immutable Research Generation Contract", "qadam_artifact_generation_checks.json"),
    ("CATC-4", "Canonical Schemas And Decision Identity", "qadam_decision_schema_checks.json"),
    ("CATC-5", "Source Capability And Evidence-Usability Registry", "qadam_source_capability_registry_checks.json"),
    ("CATC-6", "Trigger, Direction, Mapping, And Proxy Compiler", "qadam_trigger_proxy_compiler_checks.json"),
    ("CATC-7", "Market-Hours Execution Context Service", "qadam_execution_context_checks.json"),
    ("CATC-8", "Akber Evidence-Fit And Challenger Policy", "qadam_gate_policy_checks.json"),
    ("CATC-9", "Atomic Shadow, Risk, And Router Decision", "qadam_atomic_decision_checks.json"),
    ("CATC-10", "Canonical Handoff And PaperOps Exactly-Once Path", "qadam_control_plane_projection_summary.json"),
    ("CATC-11", "Lifecycle, Exit, Postmortem, And Proof Lineage", "qadam_lifecycle_control_plane_checks.json"),
    ("CATC-12", "Scheduler And Reliability Domain Separation", "qadam_runtime_domain_checks.json"),
    ("CATC-13", "Learning, Strategy Versioning, And Backtest Alignment", "qadam_strategy_learning_alignment_checks.json"),
    ("CATC-14", "Dashboard, Telegram, And Documentation Projections", "qadam_catc_dashboard_projection_checks.json"),
    ("CATC-15", "Legacy Migration And Active-Runtime Retirement", "qadam_runtime_authority_audit.json"),
    ("CATC-16", "Real-Market Verification And Five-Session Soak", "qadam_catc_real_market_soak.json"),
    ("CATC-17", "Certification, Deployment, And Empirical Paper Trial", "qadam_canonical_autonomous_tradeability_certification.json"),
)


def _commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return completed.stdout.strip()


def build_and_write_catc_implementation_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    root = Path(__file__).resolve().parents[1]
    certification = read_json(
        runtime / "qadam_canonical_autonomous_tradeability_certification.json"
    )
    soak = read_json(runtime / "qadam_catc_real_market_soak.json")
    phase_rows: list[dict[str, Any]] = []
    for phase_id, name, artifact in PHASES:
        evidence = read_json(runtime / artifact)
        evidence_status = str(evidence.get("status") or "missing")
        if phase_id == "CATC-16":
            phase_status = (
                "completed"
                if soak.get("observation_ready") is True
                else "implemented_observation_pending"
            )
        elif phase_id == "CATC-17":
            phase_status = (
                "completed"
                if certification.get("observation_ready") is True
                else "implemented_certified_soak_pending"
                if certification.get("implementation_ready") is True
                else "blocked"
            )
        else:
            accepted = evidence_status in {
                "passed",
                "captured",
                "implementation_ready",
                "complete",
            }
            phase_status = "completed" if accepted else "blocked"
        phase_rows.append(
            {
                "phase_id": phase_id,
                "name": name,
                "status": phase_status,
                "acceptance_artifact": artifact,
                "acceptance_artifact_status": evidence_status,
            }
        )
    blocked = [row["phase_id"] for row in phase_rows if row["status"] == "blocked"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_implementation_status",
        "generated_at": now_iso(),
        "status": (
            "blocked"
            if blocked
            else "observation_ready"
            if certification.get("observation_ready") is True
            else "implementation_ready_real_market_soak_pending"
        ),
        "installed_commit": _commit(root),
        "phase_count": len(phase_rows),
        "implemented_phase_count": sum(
            row["status"] != "blocked" for row in phase_rows
        ),
        "fully_observed_phase_count": sum(
            row["status"] == "completed" for row in phase_rows
        ),
        "phases": phase_rows,
        "blockers": blocked,
        "real_market_soak": {
            "required_session_count": soak.get("required_session_count", 5),
            "verified_same_build_session_count": soak.get(
                "verified_same_build_session_count", 0
            ),
            "simulated_session_count": 0,
            "backfilled_session_count": 0,
        },
        "paper_only": True,
        "guarded_alpaca_paper_route_only": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / ARTIFACT, payload)
    return payload


__all__ = ["build_and_write_catc_implementation_status"]
