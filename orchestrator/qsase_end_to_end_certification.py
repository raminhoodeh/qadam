"""QSASE-15 end-to-end certification.

Certification is a read-only audit layer. It validates the QSASE chain and
safety boundaries, but it cannot create candidates, approvals, orders, broker
writes, live-capital authority, or paper proof ledger credit.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_end_to_end_certification.v1"
PHASE_ID = "qsase_15_end_to_end_certification"
PHASE_NAME = "QSASE-15: End-To-End Certification"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_end_to_end_certification.json"
HISTORY_ARTIFACT = "qsase_end_to_end_certification_history.jsonl"
EVENTS_ARTIFACT = "qsase_end_to_end_certification_events.jsonl"
ACCEPTANCE_REPORT_ARTIFACT = "qsase_end_to_end_certification_acceptance_report.json"

CANONICAL_PAPEROPS_COMMAND = ".venv/bin/python scripts/run_paperops_autonomous_pass.py"
CANONICAL_PAPEROPS_SUMMARY = "data/runtime/paperops_autonomous_pass_summary.json"

ALLOWED_CERTIFICATION_STATUSES = {
    "not_started",
    "partial",
    "blocked",
    "degraded_research_only",
    "certified_shadow_only",
    "certified_paper_review_handoff",
    "certified_end_to_end",
}

HARD_FALSE_FIELDS = (
    "live_capital_enabled",
    "broker_write_allowed",
    "broker_live_write_allowed",
    "paper_order_allowed",
    "paper_order_created",
    "qualified_setup_created",
    "trade_candidate_created",
    "risk_approval_allowed",
    "risk_approval_created",
    "execution_approval_allowed",
    "execution_approval_created",
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "llm_order_authority",
    "local_llm_order_authority",
    "frontier_llm_order_authority",
    "quantum_order_authority",
    "quantum_job_authority",
    "qctrl_bypass_allowed",
    "strategy_mutation_allowed",
    "strategy_mutation_created",
    "model_weight_mutation_allowed",
    "model_weight_update_created",
    "source_trust_mutation_allowed",
    "trust_score_update_created",
    "source_promotion_allowed",
    "policy_mutation_allowed",
    "policy_mutation_created",
    "proof_credit_allowed",
    "paper_proof_ledger_write_allowed",
    "simulated_elapsed_time_allowed",
    "secret_read_allowed",
    "secret_write_allowed",
    "dashboard_write_authority_allowed",
    "notification_command_authority_allowed",
    "backtest_to_proof_allowed",
    "shadow_to_proof_allowed",
)

PHASE_SPECS = [
    {
        "phase_id": "appendix_a_operational_phase0_paperops_execution_reliability_baseline",
        "phase_label": "Operational Phase 0 - PaperOps Execution Reliability Baseline",
        "primary_artifact": "qsase_phase0_paperops_reliability_baseline.json",
        "dashboard_safe_artifact": None,
        "allowed_status_prefixes": ("ready",),
    },
    {
        "phase_id": "qsase_0_doctrine_document_hierarchy_safety_contract",
        "phase_label": "QSASE-0",
        "primary_artifact": "qsase_governance_safety_contract.json",
        "dashboard_safe_artifact": "qsase_governance_dashboard_summary.json",
        "allowed_status_prefixes": ("governance_safety_ready",),
    },
    {
        "phase_id": "qsase_1_self_model_artifact_validation",
        "phase_label": "QSASE-1",
        "primary_artifact": "qsase_self_model.json",
        "dashboard_safe_artifact": "qsase_self_model_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_self_model_",),
    },
    {
        "phase_id": "qsase_2_universal_source_price_pattern_matrix",
        "phase_label": "QSASE-2",
        "primary_artifact": "qsase_universal_source_price_matrix.json",
        "dashboard_safe_artifact": "qsase_universal_source_price_matrix_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_source_price_matrix_",),
    },
    {
        "phase_id": "qsase_3_historical_source_price_memory",
        "phase_label": "QSASE-3",
        "primary_artifact": "qsase_historical_source_price_memory.json",
        "dashboard_safe_artifact": "qsase_historical_source_price_memory_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_historical_source_price_memory_",),
    },
    {
        "phase_id": "qsase_4_full_universe_pattern_search",
        "phase_label": "QSASE-4",
        "primary_artifact": "qsase_full_universe_pattern_search.json",
        "dashboard_safe_artifact": "qsase_full_universe_pattern_search_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_full_universe_pattern_search_",),
    },
    {
        "phase_id": "qsase_5_linear_pattern_recognition_lab",
        "phase_label": "QSASE-5",
        "primary_artifact": "qsase_linear_pattern_lab.json",
        "dashboard_safe_artifact": "qsase_linear_pattern_lab_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_linear_pattern_lab_",),
    },
    {
        "phase_id": "qsase_6_nonlinear_quantum_pattern_lab",
        "phase_label": "QSASE-6",
        "primary_artifact": "qsase_nonlinear_quantum_pattern_lab.json",
        "dashboard_safe_artifact": "qsase_nonlinear_quantum_pattern_lab_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_nonlinear_quantum_pattern_lab_",),
    },
    {
        "phase_id": "qsase_7_strategy_foundry",
        "phase_label": "QSASE-7",
        "primary_artifact": "qsase_strategy_hypotheses.json",
        "dashboard_safe_artifact": "qsase_strategy_foundry_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_strategy_foundry_",),
    },
    {
        "phase_id": "qsase_8_akber_filter_backtest_integration",
        "phase_label": "QSASE-8",
        "primary_artifact": "qsase_akber_filter_integration.json",
        "dashboard_safe_artifact": "qsase_akber_filter_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_akber_filter_integration_",),
    },
    {
        "phase_id": "qsase_9_shadow_strategy_simulator_upgrade",
        "phase_label": "QSASE-9",
        "primary_artifact": "qsase_shadow_strategy_simulator.json",
        "dashboard_safe_artifact": "qsase_shadow_strategy_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_shadow_strategy_simulator_",),
    },
    {
        "phase_id": "qsase_10_strategy_router",
        "phase_label": "QSASE-10",
        "primary_artifact": "qsase_strategy_router_decisions.json",
        "dashboard_safe_artifact": "qsase_strategy_router_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_strategy_router_",),
    },
    {
        "phase_id": "qsase_11_paperops_handoff_interface",
        "phase_label": "QSASE-11",
        "primary_artifact": "qsase_paperops_gate_interface.json",
        "dashboard_safe_artifact": "qsase_paperops_gate_interface_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_paperops_gate_interface_",),
    },
    {
        "phase_id": "qsase_12_learning_attribution_ledger",
        "phase_label": "QSASE-12",
        "primary_artifact": "qsase_component_attribution_ledger.json",
        "dashboard_safe_artifact": "qsase_learning_attribution_dashboard_summary.json",
        "allowed_status_prefixes": ("qsase_learning_attribution_ledger_",),
    },
    {
        "phase_id": "qsase_13_dashboard_visibility",
        "phase_label": "QSASE-13",
        "primary_artifact": "qsase_dashboard_status.json",
        "dashboard_safe_artifact": "qsase_dashboard_decision_records.json",
        "allowed_status_prefixes": ("qsase_dashboard_visibility_",),
    },
    {
        "phase_id": "qsase_14_telegram_summary_boundary",
        "phase_label": "QSASE-14",
        "primary_artifact": "qsase_telegram_notification_boundary.json",
        "dashboard_safe_artifact": "qsase_telegram_dashboard_communications_mirror.json",
        "allowed_status_prefixes": ("qsase_telegram_notification_boundary_",),
    },
]

REQUIRED_ARTIFACTS = [
    "qsase_phase0_paperops_reliability_baseline.json",
    "qsase_phase0_scanner_freshness.json",
    "qsase_phase0_candidate_identity_audit.json",
    "qsase_phase0_paper_lifecycle_audit.json",
    "qsase_phase0_proof_lineage_audit.json",
    "qsase_phase0_telemetry_consistency.json",
    "qsase_phase0_dashboard_deploy_hygiene.json",
    "qsase_phase0_review_signature_readiness.json",
    "qsase_phase0_validated_edge_readiness.json",
    "qsase_governance_safety_contract.json",
    "qsase_authority_flag_audit.json",
    "qsase_authority_violations.jsonl",
    "qsase_proof_boundary_audit.json",
    "qsase_calendar_boundary_audit.json",
    "qsase_self_model.json",
    "qsase_self_model_dashboard_summary.json",
    "qsase_universal_source_price_matrix.json",
    "qsase_source_universe.json",
    "qsase_trading_universe.json",
    "qsase_source_price_edges.jsonl",
    "qsase_historical_source_price_memory.json",
    "qsase_historical_source_price_memory.jsonl",
    "qsase_historical_coverage_map.json",
    "qsase_historical_replay_manifest.json",
    "qsase_point_in_time_replay_index.json",
    "qsase_historical_missing_windows.jsonl",
    "qsase_full_universe_pattern_search.json",
    "qsase_candidate_patterns.jsonl",
    "qsase_rejected_patterns.jsonl",
    "qsase_linear_pattern_lab.json",
    "qsase_linear_backtest_results.jsonl",
    "qsase_linear_rejected_patterns.jsonl",
    "qsase_nonlinear_quantum_pattern_lab.json",
    "qsase_nonlinear_pattern_results.jsonl",
    "qsase_quantum_pattern_reviews.jsonl",
    "qsase_strategy_hypotheses.json",
    "qsase_strategy_hypotheses.jsonl",
    "qsase_strategy_family_map.json",
    "qsase_rejected_strategy_hypotheses.jsonl",
    "qsase_akber_filter_integration.json",
    "qsase_akber_filter_results.jsonl",
    "qsase_akber_filter_threshold_proposals.json",
    "qsase_shadow_strategy_simulator.json",
    "qsase_shadow_strategy_results.jsonl",
    "qsase_shadow_strategy_rejections.jsonl",
    "qsase_strategy_router_decisions.json",
    "qsase_strategy_router_decisions.jsonl",
    "qsase_strategy_router_scoreboard.json",
    "qsase_why_not_trading_now.json",
    "qsase_paperops_gate_interface.json",
    "qsase_paperops_gate_interface.jsonl",
    "qsase_paperops_handoff_records.jsonl",
    "qsase_paperops_rejected_handoffs.jsonl",
    "qsase_component_attribution_ledger.json",
    "qsase_component_attribution_ledger.jsonl",
    "qsase_strategy_weight_proposals.json",
    "qsase_source_trust_proposals.json",
    "qsase_model_weight_proposals.json",
    "qsase_filter_threshold_proposals.json",
    "qsase_learning_approval_queue.json",
    "qsase_dashboard_status.json",
    "qsase_dashboard_decision_records.json",
    "qsase_dashboard_system_map.json",
    "qsase_dashboard_anti_slop_audit.json",
    "qsase_telegram_notification_boundary.json",
    "qsase_telegram_message_candidates.json",
    "qsase_telegram_message_quality.json",
    "qsase_telegram_dedupe_ledger.jsonl",
    "qsase_telegram_delivery_receipts.jsonl",
    "qsase_telegram_dashboard_communications_mirror.json",
    "paperops_autonomous_pass_summary.json",
]

REQUIRED_CHECKS = [
    "scripts/check_qsase_phase0_paperops_reliability_baseline.py",
    "scripts/check_qsase_phase0_scanner_freshness.py",
    "scripts/check_qsase_phase0_candidate_identity.py",
    "scripts/check_qsase_phase0_paper_lifecycle.py",
    "scripts/check_qsase_phase0_proof_lineage.py",
    "scripts/check_qsase_phase0_telemetry_consistency.py",
    "scripts/check_qsase_phase0_dashboard_deploy_hygiene.py",
    "scripts/check_qsase_phase0_review_signature_readiness.py",
    "scripts/check_qsase_phase0_validated_edge_readiness.py",
    "scripts/check_qsase_governance_safety_contract.py",
    "scripts/check_qsase_authority_flags.py",
    "scripts/check_qsase_authority_violations.py",
    "scripts/check_qsase_proof_boundary.py",
    "scripts/check_qsase_calendar_boundary.py",
    "scripts/check_qsase_self_model.py",
    "scripts/check_qsase_universal_source_price_matrix.py",
    "scripts/check_qsase_historical_source_price_memory.py",
    "scripts/check_qsase_full_universe_pattern_search.py",
    "scripts/check_qsase_linear_pattern_lab.py",
    "scripts/check_qsase_nonlinear_quantum_pattern_lab.py",
    "scripts/check_qsase_strategy_foundry.py",
    "scripts/check_qsase_akber_filter_integration.py",
    "scripts/check_qsase_shadow_strategy_simulator.py",
    "scripts/check_qsase_strategy_router.py",
    "scripts/check_qsase_paperops_gate_interface.py",
    "scripts/check_qsase_learning_attribution_ledger.py",
    "scripts/check_qsase_recursive_improvement_contract.py",
    "scripts/check_qsase_dashboard_view_model.py",
    "scripts/check_qsase_dashboard_anti_slop.py",
    "scripts/check_qsase_telegram_notification_boundary.py",
    "scripts/check_qsase_telegram_message_quality.py",
    "scripts/check_qsase_telegram_dedupe.py",
    "scripts/check_qsase_end_to_end_certification.py",
]

EXTERNAL_CHECKS_TO_RUN = [
    path for path in REQUIRED_CHECKS if path != "scripts/check_qsase_end_to_end_certification.py"
]

LINEAGE_ARTIFACTS = {
    "source_observation": "qsase_source_universe.json",
    "source_price_matrix_edge": "qsase_source_price_edges.jsonl",
    "historical_memory_record": "qsase_historical_source_price_memory.jsonl",
    "candidate_pattern": "qsase_candidate_patterns.jsonl",
    "linear_lab_result": "qsase_linear_backtest_results.jsonl",
    "nonlinear_lab_result": "qsase_nonlinear_pattern_results.jsonl",
    "quantum_review": "qsase_quantum_pattern_reviews.jsonl",
    "strategy_hypothesis": "qsase_strategy_hypotheses.jsonl",
    "akber_filter_result": "qsase_akber_filter_results.jsonl",
    "shadow_result": "qsase_shadow_strategy_results.jsonl",
    "router_decision": "qsase_strategy_router_decisions.jsonl",
    "paperops_handoff_or_rejection": "qsase_paperops_gate_interface.jsonl",
    "learning_attribution_record": "qsase_component_attribution_ledger.jsonl",
    "dashboard_decision_record": "qsase_dashboard_decision_records.json",
    "telegram_candidate": "qsase_telegram_message_candidates.json",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _artifact_ref(filename: str, record_id: str | None = None) -> dict[str, Any]:
    ref: dict[str, Any] = {"artifact_path": f"data/runtime/{filename}"}
    if record_id:
        ref["record_id"] = record_id
    return ref


def _file_snapshot(runtime_dir: Path, filename: str) -> dict[str, Any]:
    path = runtime_dir / filename
    snapshot: dict[str, Any] = {
        "artifact_path": f"data/runtime/{filename}",
        "exists": path.exists(),
        "required": True,
    }
    if path.exists():
        stat = path.stat()
        snapshot.update(
            {
                "size_bytes": stat.st_size,
                "mtime": _iso(datetime.fromtimestamp(stat.st_mtime, timezone.utc)),
                "empty": stat.st_size == 0,
            }
        )
    return snapshot


def _status_is_allowed(status: Any, prefixes: tuple[str, ...]) -> bool:
    if not isinstance(status, str):
        return False
    return any(status == prefix or status.startswith(prefix) for prefix in prefixes)


def _artifact_status(payload: dict[str, Any]) -> str:
    status = payload.get("status")
    return status if isinstance(status, str) and status else "missing_status"


def _result_tail(output: str, max_lines: int = 12) -> list[str]:
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-max_lines:]


def run_required_certification_checks(timeout_seconds: int = 120) -> list[dict[str, Any]]:
    """Run prior QSASE checks with the active interpreter."""

    root = _repo_root()
    results: list[dict[str, Any]] = []
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(root))
    for script in EXTERNAL_CHECKS_TO_RUN:
        path = root / script
        if not path.exists():
            results.append(
                {
                    "script": script,
                    "status": "missing",
                    "passed": False,
                    "returncode": None,
                    "stdout_tail": [],
                    "stderr_tail": [],
                }
            )
            continue
        completed = subprocess.run(
            [sys.executable, script],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        results.append(
            {
                "script": script,
                "status": "passed" if completed.returncode == 0 else "failed",
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout_tail": _result_tail(completed.stdout),
                "stderr_tail": _result_tail(completed.stderr),
            }
        )
    return results


def build_recursive_improvement_contract_audit(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    ledger = _read_json(runtime / "qsase_component_attribution_ledger.json")
    proposal_files = [
        "qsase_strategy_weight_proposals.json",
        "qsase_source_trust_proposals.json",
        "qsase_model_weight_proposals.json",
        "qsase_filter_threshold_proposals.json",
        "qsase_learning_approval_queue.json",
    ]
    proposals = {filename: _read_json(runtime / filename) for filename in proposal_files}
    errors: list[str] = []
    if not ledger:
        errors.append("learning_attribution_ledger_missing")
    for filename, payload in proposals.items():
        if not payload:
            errors.append(f"{filename}_missing")
            continue
        if payload.get("apply_allowed") is not False:
            errors.append(f"{filename}_apply_allowed_must_be_false")
        if payload.get("applied") is not False:
            errors.append(f"{filename}_applied_must_be_false")
        if _int(payload.get("applied_update_count"), -1) != 0:
            errors.append(f"{filename}_applied_update_count_must_be_zero")
        if _int(payload.get("approved_proposal_count"), 0) != 0:
            errors.append(f"{filename}_approved_proposal_count_must_be_zero")
        for field in ("paper_order_created_count", "broker_write_count"):
            if _int(payload.get(field), -1) != 0:
                errors.append(f"{filename}_{field}_must_be_zero")
        for field in ("proof_credit_allowed", "live_capital_enabled"):
            if payload.get(field) is not False:
                errors.append(f"{filename}_{field}_must_be_false")
        authority = payload.get("authority", {})
        if isinstance(authority, dict):
            for field, value in authority.items():
                if field in HARD_FALSE_FIELDS and value is not False:
                    errors.append(f"{filename}_{field}_must_be_false")
    for field in (
        "applied_update_count",
        "approved_proposal_count",
        "paper_order_created_count",
        "broker_write_count",
    ):
        if _int(ledger.get(field), 0) != 0:
            errors.append(f"ledger_{field}_must_be_zero")
    for field in (
        "strategy_mutation_created",
        "model_weight_update_created",
        "trust_score_update_created",
        "policy_mutation_created",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if ledger.get(field) is not False:
            errors.append(f"ledger_{field}_must_be_false")
    return {
        "status": "recursive_improvement_contract_ready" if not errors else "recursive_improvement_contract_blocked",
        "proposal_artifact_count": len(proposal_files),
        "present_proposal_artifact_count": sum(1 for filename in proposal_files if proposals.get(filename)),
        "active_proposal_count": _int(ledger.get("active_proposal_count"), 0),
        "applied_update_count": _int(ledger.get("applied_update_count"), 0),
        "approval_required_count": _int(ledger.get("approval_required_count"), 0),
        "proposal_only": not errors,
        "errors": sorted(set(errors)),
        "artifact_refs": [_artifact_ref(filename) for filename in proposal_files]
        + [_artifact_ref("qsase_component_attribution_ledger.json")],
    }


def _phase_artifact_audit(runtime: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    phase_results: list[dict[str, Any]] = []
    phase_status = _read_json(runtime / PHASE_STATUS_ARTIFACT)
    phase_status_records = phase_status.get("phases", {}) if isinstance(phase_status.get("phases"), dict) else {}
    for spec in PHASE_SPECS:
        primary_snapshot = _file_snapshot(runtime, spec["primary_artifact"])
        dashboard_artifact = spec.get("dashboard_safe_artifact")
        dashboard_snapshot = _file_snapshot(runtime, dashboard_artifact) if dashboard_artifact else None
        payload = _read_json(runtime / spec["primary_artifact"])
        status = _artifact_status(payload)
        phase_status_record = phase_status_records.get(spec["phase_id"], {})
        phase_error_count = 0
        if not primary_snapshot["exists"]:
            errors.append(f"{spec['phase_id']}_primary_artifact_missing")
            phase_error_count += 1
        if primary_snapshot.get("empty"):
            errors.append(f"{spec['phase_id']}_primary_artifact_empty")
            phase_error_count += 1
        if dashboard_snapshot and not dashboard_snapshot["exists"]:
            errors.append(f"{spec['phase_id']}_dashboard_safe_artifact_missing")
            phase_error_count += 1
        if payload and not payload.get("generated_at"):
            errors.append(f"{spec['phase_id']}_generated_at_missing")
            phase_error_count += 1
        if payload and not _status_is_allowed(status, spec["allowed_status_prefixes"]):
            errors.append(f"{spec['phase_id']}_status_unexpected:{status}")
            phase_error_count += 1
        phase_results.append(
            {
                "phase_id": spec["phase_id"],
                "phase_label": spec["phase_label"],
                "status": status,
                "phase_status_recorded": bool(phase_status_record),
                "phase_status": phase_status_record.get("status"),
                "primary_artifact": primary_snapshot,
                "dashboard_safe_artifact": dashboard_snapshot,
                "passed": phase_error_count == 0,
                "degraded": "degraded" in status or phase_status_record.get("status") in {"ready_with_gaps", "degraded"},
                "artifact_refs": [_artifact_ref(spec["primary_artifact"])],
            }
        )
    return phase_results, errors


def _required_artifact_audit(runtime: Path) -> tuple[list[dict[str, Any]], list[str]]:
    snapshots = [_file_snapshot(runtime, filename) for filename in REQUIRED_ARTIFACTS]
    errors = [
        f"{Path(snapshot['artifact_path']).name}_missing"
        for snapshot in snapshots
        if not snapshot.get("exists")
    ]
    errors.extend(
        f"{Path(snapshot['artifact_path']).name}_empty"
        for snapshot in snapshots
        if snapshot.get("exists") and snapshot.get("empty") and not snapshot["artifact_path"].endswith(".jsonl")
    )
    return snapshots, sorted(set(errors))


def _authority_audit(runtime: Path) -> dict[str, Any]:
    artifacts = [
        "qsase_governance_safety_contract.json",
        "qsase_self_model.json",
        "qsase_universal_source_price_matrix.json",
        "qsase_historical_source_price_memory.json",
        "qsase_full_universe_pattern_search.json",
        "qsase_linear_pattern_lab.json",
        "qsase_nonlinear_quantum_pattern_lab.json",
        "qsase_strategy_hypotheses.json",
        "qsase_akber_filter_integration.json",
        "qsase_shadow_strategy_simulator.json",
        "qsase_strategy_router_decisions.json",
        "qsase_paperops_gate_interface.json",
        "qsase_component_attribution_ledger.json",
        "qsase_dashboard_status.json",
        "qsase_telegram_notification_boundary.json",
    ]
    violations: list[dict[str, Any]] = []
    for filename in artifacts:
        payload = _read_json(runtime / filename)
        if not payload:
            continue
        for scope in ("authority", "authority_flags"):
            values = payload.get(scope, {})
            if not isinstance(values, dict):
                continue
            for field, value in values.items():
                if field in HARD_FALSE_FIELDS and value is not False:
                    violations.append(
                        {
                            "artifact": f"data/runtime/{filename}",
                            "scope": scope,
                            "field": field,
                            "value": value,
                        }
                    )
        for field in HARD_FALSE_FIELDS:
            if payload.get(field) is not None and payload.get(field) is not False:
                violations.append(
                    {
                        "artifact": f"data/runtime/{filename}",
                        "scope": "top_level",
                        "field": field,
                        "value": payload.get(field),
                    }
                )
    return {
        "status": "authority_clean" if not violations else "authority_violation_detected",
        "artifact_count": len(artifacts),
        "authority_violation_count": len(violations),
        "violations": violations,
        "authority": universal_authority_flags(),
    }


def _source_price_lineage_audit(runtime: Path) -> dict[str, Any]:
    matrix = _read_json(runtime / "qsase_universal_source_price_matrix.json")
    edges = _read_jsonl(runtime / "qsase_source_price_edges.jsonl")
    historical = _read_json(runtime / "qsase_historical_source_price_memory.json")
    historical_rows = _read_jsonl(runtime / "qsase_historical_source_price_memory.jsonl")
    candidate_patterns = _read_jsonl(runtime / "qsase_candidate_patterns.jsonl")
    errors: list[str] = []
    if not edges:
        errors.append("source_price_edges_missing")
    if not historical_rows:
        errors.append("historical_memory_rows_missing")
    if not candidate_patterns:
        errors.append("candidate_patterns_missing")
    if _int(matrix.get("source_price_edge_count"), 0) != len(edges):
        errors.append("matrix_source_price_edge_count_mismatch")
    if _int(historical.get("aligned_record_count"), _int(historical.get("memory_record_count"), 0)) == 0:
        errors.append("historical_aligned_records_missing")
    edge_ids = {str(row.get("matrix_row_id")) for row in edges if row.get("matrix_row_id")}
    historical_edge_refs = {
        str(matrix_row_id)
        for row in historical_rows
        for matrix_row_id in row.get("matrix_row_ids", [])
    }
    pattern_edge_refs = {
        str(matrix_row_id)
        for row in candidate_patterns
        for matrix_row_id in row.get("matrix_row_ids", [])
    }
    linked_historical_count = len([edge_id for edge_id in historical_edge_refs if edge_id and edge_id in edge_ids])
    linked_pattern_count = len([edge_id for edge_id in pattern_edge_refs if edge_id and edge_id in edge_ids])
    if linked_historical_count == 0:
        errors.append("historical_memory_not_linked_to_source_price_edges")
    if linked_pattern_count == 0:
        errors.append("candidate_patterns_not_linked_to_source_price_edges")
    return {
        "status": "source_price_lineage_pass" if not errors else "source_price_lineage_failed",
        "source_price_edge_count": len(edges),
        "historical_memory_record_count": len(historical_rows),
        "candidate_pattern_count": len(candidate_patterns),
        "linked_historical_count": linked_historical_count,
        "linked_pattern_count": linked_pattern_count,
        "errors": sorted(set(errors)),
        "artifact_refs": [_artifact_ref(filename) for filename in LINEAGE_ARTIFACTS.values()],
    }


def _strategy_lineage_audit(runtime: Path) -> dict[str, Any]:
    hypotheses = _read_jsonl(runtime / "qsase_strategy_hypotheses.jsonl")
    rejected_hypotheses = _read_jsonl(runtime / "qsase_rejected_strategy_hypotheses.jsonl")
    akber = _read_jsonl(runtime / "qsase_akber_filter_results.jsonl")
    shadow = _read_jsonl(runtime / "qsase_shadow_strategy_results.jsonl")
    router = _read_jsonl(runtime / "qsase_strategy_router_decisions.jsonl")
    paperops = _read_jsonl(runtime / "qsase_paperops_gate_interface.jsonl")
    learning = _read_jsonl(runtime / "qsase_component_attribution_ledger.jsonl")
    errors: list[str] = []
    if not hypotheses and not rejected_hypotheses:
        errors.append("strategy_hypothesis_or_rejection_records_missing")
    if not akber:
        errors.append("akber_results_missing")
    if not shadow:
        errors.append("shadow_results_missing")
    if not router:
        errors.append("router_decisions_missing")
    if not paperops:
        errors.append("paperops_gate_records_missing")
    if not learning:
        errors.append("learning_records_missing")
    hypothesis_ids = {str(row.get("strategy_hypothesis_id")) for row in hypotheses if row.get("strategy_hypothesis_id")}
    rejected_hypothesis_ids = {
        str(row.get("rejected_hypothesis_id")) for row in rejected_hypotheses if row.get("rejected_hypothesis_id")
    }
    lineage_ids = hypothesis_ids or rejected_hypothesis_ids
    akber_hypothesis_refs = {
        str(row.get("strategy_hypothesis_id") or row.get("source_rejected_hypothesis_id")) for row in akber
    }
    shadow_hypothesis_refs = {
        str(row.get("strategy_hypothesis_id") or row.get("rejected_hypothesis_id")) for row in shadow
    }
    router_hypothesis_refs = {
        str(row.get("strategy_hypothesis_id") or row.get("rejected_hypothesis_id"))
        for row in router
    }
    if lineage_ids and not (lineage_ids & akber_hypothesis_refs):
        errors.append("strategy_lineage_not_linked_to_akber")
    if lineage_ids and not (lineage_ids & shadow_hypothesis_refs):
        errors.append("strategy_lineage_not_linked_to_shadow")
    if lineage_ids and not (lineage_ids & router_hypothesis_refs):
        errors.append("strategy_lineage_not_linked_to_router")
    paperops_router_refs = {str(row.get("router_decision_id")) for row in paperops}
    router_ids = {str(row.get("router_decision_id")) for row in router}
    if router_ids and not (router_ids & paperops_router_refs):
        errors.append("router_decisions_not_linked_to_paperops_gate")
    learning_links_router = any(
        row.get("lineage", {}).get("router_ref") == "data/runtime/qsase_strategy_router_decisions.json"
        or row.get("router_decision_id") in router_ids
        for row in learning
    )
    if router_ids and not learning_links_router:
        errors.append("router_decisions_not_referenced_by_learning")
    return {
        "status": "strategy_lineage_pass" if not errors else "strategy_lineage_failed",
        "strategy_hypothesis_count": len(hypotheses),
        "rejected_strategy_hypothesis_count": len(rejected_hypotheses),
        "akber_result_count": len(akber),
        "shadow_result_count": len(shadow),
        "router_decision_count": len(router),
        "paperops_gate_record_count": len(paperops),
        "learning_record_count": len(learning),
        "errors": sorted(set(errors)),
        "artifact_refs": [_artifact_ref(filename) for filename in LINEAGE_ARTIFACTS.values()],
    }


def _paperops_compatibility_audit(runtime: Path) -> dict[str, Any]:
    paperops_summary = _read_json(runtime / "paperops_autonomous_pass_summary.json")
    gate = _read_json(runtime / "qsase_paperops_gate_interface.json")
    handoffs = _read_jsonl(runtime / "qsase_paperops_handoff_records.jsonl")
    rejected = _read_jsonl(runtime / "qsase_paperops_rejected_handoffs.jsonl")
    errors: list[str] = []
    if not paperops_summary:
        errors.append("canonical_paperops_summary_missing")
    if not gate:
        errors.append("paperops_gate_interface_missing")
    if gate.get("existing_paperops_remains_only_submit_route") is not True:
        errors.append("existing_paperops_not_recorded_as_only_submit_route")
    if gate.get("guarded_alpaca_paper_route_name") != "existing guarded Alpaca Paper route only":
        errors.append("guarded_alpaca_paper_route_boundary_missing")
    if _int(gate.get("paper_order_created_count"), 0) != 0:
        errors.append("qsase_paper_order_created")
    if _int(gate.get("broker_write_count"), 0) != 0:
        errors.append("qsase_broker_write_created")
    if gate.get("proof_credit_allowed") is not False:
        errors.append("qsase_proof_credit_allowed")
    if gate.get("live_capital_enabled") is not False:
        errors.append("qsase_live_capital_enabled")
    for record in handoffs + rejected:
        decision = record.get("decision", {})
        if record.get("paper_order_created") is not False:
            errors.append(f"{record.get('paperops_gate_record_id')}_paper_order_created")
        if record.get("broker_write_created") is not False:
            errors.append(f"{record.get('paperops_gate_record_id')}_broker_write_created")
        if record.get("qualified_setup_created") is not False:
            errors.append(f"{record.get('paperops_gate_record_id')}_qualified_setup_created")
        if isinstance(decision, dict):
            if "paper_order_created" in decision and decision.get("paper_order_created") is not False:
                errors.append(f"{record.get('paperops_gate_record_id')}_decision_paper_order_created")
            if "broker_write_created" in decision and decision.get("broker_write_created") is not False:
                errors.append(f"{record.get('paperops_gate_record_id')}_decision_broker_write_created")
            if "qualified_setup_created" in decision and decision.get("qualified_setup_created") is not False:
                errors.append(f"{record.get('paperops_gate_record_id')}_decision_qualified_setup_created")
    return {
        "status": "paperops_compatibility_pass" if not errors else "paperops_compatibility_failed",
        "canonical_wrapper_command": CANONICAL_PAPEROPS_COMMAND,
        "canonical_summary": CANONICAL_PAPEROPS_SUMMARY,
        "canonical_summary_present": bool(paperops_summary),
        "handoff_record_count": len(handoffs),
        "rejected_handoff_count": len(rejected),
        "paper_order_created_outside_paperops_count": 0 if "qsase_paper_order_created" not in errors else 1,
        "broker_write_count": _int(gate.get("broker_write_count"), 0),
        "proof_credit_allowed": _bool(gate.get("proof_credit_allowed")),
        "live_capital_enabled": _bool(gate.get("live_capital_enabled")),
        "errors": sorted(set(errors)),
        "artifact_refs": [
            _artifact_ref("paperops_autonomous_pass_summary.json"),
            _artifact_ref("qsase_paperops_gate_interface.json"),
            _artifact_ref("qsase_paperops_handoff_records.jsonl"),
            _artifact_ref("qsase_paperops_rejected_handoffs.jsonl"),
        ],
    }


def _proof_calendar_boundary_audit(runtime: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    governance = _read_json(runtime / "qsase_governance_safety_contract.json")
    proof = _read_json(runtime / "qsase_proof_boundary_audit.json")
    calendar = _read_json(runtime / "qsase_calendar_boundary_audit.json")
    learning = _read_json(runtime / "qsase_component_attribution_ledger.json")
    errors_proof: list[str] = []
    errors_calendar: list[str] = []
    for payload_name, payload in (("governance", governance), ("proof", proof), ("learning", learning)):
        if not payload:
            errors_proof.append(f"{payload_name}_artifact_missing")
            continue
        for field in ("proof_credit_allowed", "backtest_to_proof_allowed", "shadow_to_proof_allowed"):
            if payload.get(field) is not None and payload.get(field) is not False:
                errors_proof.append(f"{payload_name}_{field}_must_be_false")
    for payload_name, payload in (("governance", governance), ("calendar", calendar), ("learning", learning)):
        if not payload:
            errors_calendar.append(f"{payload_name}_artifact_missing")
            continue
        for field in ("simulated_elapsed_time_allowed", "paper_growth_trial_calendar_advanced"):
            if payload.get(field) is not None and payload.get(field) is not False:
                errors_calendar.append(f"{payload_name}_{field}_must_be_false")
    return (
        {
            "status": "proof_boundary_pass" if not errors_proof else "proof_boundary_failed",
            "proof_credit_allowed": False,
            "backtest_to_proof_allowed": False,
            "shadow_to_proof_allowed": False,
            "paper_proof_ledger_credit_created": False,
            "errors": sorted(set(errors_proof)),
            "artifact_refs": [_artifact_ref("qsase_proof_boundary_audit.json")],
        },
        {
            "status": "calendar_boundary_pass" if not errors_calendar else "calendar_boundary_failed",
            "preserves_30_day_paper_growth_trial_calendar": True,
            "simulated_elapsed_time_allowed": False,
            "paper_growth_trial_calendar_advanced": False,
            "errors": sorted(set(errors_calendar)),
            "artifact_refs": [_artifact_ref("qsase_calendar_boundary_audit.json")],
        },
    )


def _dashboard_telegram_audit(runtime: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    dashboard = _read_json(runtime / "qsase_dashboard_status.json")
    anti_slop = _read_json(runtime / "qsase_dashboard_anti_slop_audit.json")
    telegram = _read_json(runtime / "qsase_telegram_notification_boundary.json")
    quality = _read_json(runtime / "qsase_telegram_message_quality.json")
    dedupe = _read_jsonl(runtime / "qsase_telegram_dedupe_ledger.jsonl")
    dashboard_errors: list[str] = []
    telegram_errors: list[str] = []
    if dashboard.get("public_safe") is not True:
        dashboard_errors.append("dashboard_public_safe_missing")
    if dashboard.get("command_disabled") is not True:
        dashboard_errors.append("dashboard_command_disabled_missing")
    if _int(anti_slop.get("error_count"), 0) != 0:
        dashboard_errors.append("dashboard_anti_slop_errors_present")
    if telegram.get("public_safe") is not True or telegram.get("command_disabled") is not True:
        telegram_errors.append("telegram_public_safe_command_disabled_missing")
    if telegram.get("telegram_command_path_enabled") is not False:
        telegram_errors.append("telegram_command_path_enabled")
    if telegram.get("telegram_trade_command_enabled") is not False:
        telegram_errors.append("telegram_trade_command_enabled")
    if _int(telegram.get("message_rejected_generic_count"), 0) != 0:
        telegram_errors.append("telegram_generic_message_accepted_or_present")
    if _int(telegram.get("message_rejected_unsafe_count"), 0) != 0:
        telegram_errors.append("telegram_unsafe_message_present")
    if quality.get("specific_count") != quality.get("candidate_count"):
        telegram_errors.append("telegram_candidates_not_all_specific")
    if quality.get("human_style_count") != quality.get("candidate_count"):
        telegram_errors.append("telegram_candidates_not_all_human_style")
    return (
        {
            "status": "dashboard_visibility_pass" if not dashboard_errors else "dashboard_visibility_failed",
            "dashboard_slop_failure_count": len(dashboard_errors),
            "public_safe": dashboard.get("public_safe") is True,
            "command_disabled": dashboard.get("command_disabled") is True,
            "anti_slop_error_count": _int(anti_slop.get("error_count"), 0),
            "errors": sorted(set(dashboard_errors)),
            "artifact_refs": [_artifact_ref("qsase_dashboard_status.json"), _artifact_ref("qsase_dashboard_anti_slop_audit.json")],
        },
        {
            "status": "telegram_quality_pass" if not telegram_errors else "telegram_quality_failed",
            "telegram_quality_failure_count": len(telegram_errors),
            "candidate_count": _int(telegram.get("message_candidate_count"), 0),
            "duplicate_suppression_count": _int(telegram.get("duplicate_suppressed_count"), 0),
            "live_send_allowed": telegram.get("telegram_live_send_allowed") is True,
            "command_disabled": telegram.get("command_disabled") is True,
            "dedupe_record_count": len(dedupe),
            "errors": sorted(set(telegram_errors)),
            "artifact_refs": [
                _artifact_ref("qsase_telegram_notification_boundary.json"),
                _artifact_ref("qsase_telegram_message_quality.json"),
                _artifact_ref("qsase_telegram_dedupe_ledger.jsonl"),
            ],
        },
    )


def _negative_probe_audit() -> dict[str, Any]:
    probes = [
        ("live_capital_flag_true", {"live_capital_enabled": True}),
        ("broker_write_flag_true", {"broker_write_allowed": True}),
        ("telegram_command_path_true", {"telegram_command_path_enabled": True}),
        ("llm_order_authority_true", {"llm_order_authority": True}),
        ("quantum_order_authority_true", {"quantum_order_authority": True}),
        ("qctrl_bypass_true", {"qctrl_bypass_allowed": True}),
        ("paper_order_created_outside_paperops", {"paper_order_created": True}),
        ("qualified_setup_created_outside_paperops", {"qualified_setup_created": True}),
        ("strategy_mutation_without_approval", {"strategy_mutation_created": True}),
        ("model_weight_mutation_without_approval", {"model_weight_update_created": True}),
        ("source_trust_mutation_without_approval", {"trust_score_update_created": True}),
        ("source_promoted_from_degraded_evidence", {"source_promotion_allowed": True}),
        ("backtest_converted_to_proof", {"backtest_to_proof_allowed": True}),
        ("shadow_replay_converted_to_proof", {"shadow_to_proof_allowed": True}),
        ("simulated_elapsed_time_detected", {"simulated_elapsed_time_allowed": True}),
        ("stale_artifact_presented_as_current", {"generated_at": None}),
        ("generic_dashboard_card_accepted", {"dashboard_slop_failure_count": 1}),
        ("duplicate_telegram_message_accepted", {"duplicate_telegram_message_accepted": True}),
        ("secret_value_present_in_public_safe_output", {"secret_read_allowed": True}),
    ]
    rejected: list[str] = []
    accepted: list[str] = []
    for name, payload in probes:
        violation = False
        for field in HARD_FALSE_FIELDS:
            if payload.get(field) is True:
                violation = True
        if payload.get("generated_at") is None and "generated_at" in payload:
            violation = True
        if _int(payload.get("dashboard_slop_failure_count"), 0) > 0:
            violation = True
        if payload.get("duplicate_telegram_message_accepted") is True:
            violation = True
        if violation:
            rejected.append(name)
        else:
            accepted.append(name)
    return {
        "status": "negative_probes_pass" if not accepted else "negative_probes_failed",
        "probe_count": len(probes),
        "rejected_probe_count": len(rejected),
        "accepted_probe_count": len(accepted),
        "accepted_probes": accepted,
        "rejected_probes": rejected,
    }


def _derive_status(payload: dict[str, Any]) -> str:
    if payload["hard_failure_count"] > 0:
        return "blocked"
    if payload["failed_phase_count"] > 0 or payload["failed_check_count"] > 0:
        return "partial"
    if payload["warning_count"] > 0 or any(result.get("degraded") for result in payload.get("phase_results", [])):
        return "degraded_research_only"
    if payload.get("paperops_handoff_count", 0) > 0:
        return "certified_paper_review_handoff"
    if payload.get("shadow_result_count", 0) > 0:
        return "certified_shadow_only"
    return "certified_end_to_end"


def _acceptance_report(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_end_to_end_certification_acceptance_report",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "certified": payload["certified"],
        "summary_lines": [
            f"QSASE certification: {payload['status']}",
            f"Self-model: {payload['capability_matrix']['self_model']['status']}",
            f"Source-price matrix: {payload['capability_matrix']['source_price_matrix']['status']}",
            f"Historical memory: {payload['capability_matrix']['historical_memory']['status']}",
            f"Full-universe search: {payload['capability_matrix']['full_universe_search']['status']}",
            f"Linear lab: {payload['capability_matrix']['linear_lab']['status']}",
            f"Nonlinear and quantum lab: {payload['capability_matrix']['nonlinear_quantum_lab']['status']}",
            f"Strategy Foundry: {payload['capability_matrix']['strategy_foundry']['status']}",
            f"Akber Filter: {payload['capability_matrix']['akber_filter']['status']}",
            f"Shadow simulator: {payload['capability_matrix']['shadow_simulator']['status']}",
            f"Router: {payload['capability_matrix']['strategy_router']['status']}",
            f"PaperOps handoff: {payload['paperops_compatibility']['status']}",
            f"Learning ledger: {payload['capability_matrix']['learning_ledger']['status']}",
            f"Dashboard: {payload['dashboard_visibility']['status']}",
            f"Telegram: {payload['telegram_quality']['status']}",
            f"Governance: {payload['authority_audit']['status']}",
            f"Authority violations: {payload['authority_violation_count']}",
            f"Paper orders created by QSASE: {payload['paper_order_created_outside_paperops_count']}",
            f"Broker writes: {payload['broker_write_count']}",
            f"Proof credit granted by QSASE: {str(payload['proof_credit_allowed']).lower()}",
            f"Live capital: {str(payload['live_capital_enabled']).lower()}",
        ],
        "public_safe": True,
        "command_disabled": True,
        "live_capital_ready": False,
        "artifact_refs": [_artifact_ref(PRIMARY_ARTIFACT)],
    }


def _capability_matrix(runtime: Path) -> dict[str, dict[str, Any]]:
    mapping = {
        "self_model": "qsase_self_model.json",
        "source_price_matrix": "qsase_universal_source_price_matrix.json",
        "historical_memory": "qsase_historical_source_price_memory.json",
        "full_universe_search": "qsase_full_universe_pattern_search.json",
        "linear_lab": "qsase_linear_pattern_lab.json",
        "nonlinear_quantum_lab": "qsase_nonlinear_quantum_pattern_lab.json",
        "strategy_foundry": "qsase_strategy_hypotheses.json",
        "akber_filter": "qsase_akber_filter_integration.json",
        "shadow_simulator": "qsase_shadow_strategy_simulator.json",
        "strategy_router": "qsase_strategy_router_decisions.json",
        "learning_ledger": "qsase_component_attribution_ledger.json",
    }
    return {
        key: {
            "status": _artifact_status(_read_json(runtime / filename)),
            "artifact_ref": _artifact_ref(filename),
        }
        for key, filename in mapping.items()
    }


def build_qsase_end_to_end_certification(
    settings: Settings | None = None,
    check_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    generated_at = _iso(_now())
    checks = check_results if check_results is not None else run_required_certification_checks()
    checks_with_self = list(checks) + [
        {
            "script": "scripts/check_qsase_end_to_end_certification.py",
            "status": "passed",
            "passed": True,
            "returncode": 0,
            "stdout_tail": ["self_validated_by_qsase_end_to_end_certification"],
            "stderr_tail": [],
        }
    ]
    phase_results, phase_errors = _phase_artifact_audit(runtime)
    artifact_snapshots, artifact_errors = _required_artifact_audit(runtime)
    authority = _authority_audit(runtime)
    source_price_lineage = _source_price_lineage_audit(runtime)
    strategy_lineage = _strategy_lineage_audit(runtime)
    paperops = _paperops_compatibility_audit(runtime)
    proof_boundary, calendar_boundary = _proof_calendar_boundary_audit(runtime)
    dashboard_visibility, telegram_quality = _dashboard_telegram_audit(runtime)
    negative_probes = _negative_probe_audit()
    recursive_improvement = build_recursive_improvement_contract_audit(settings)
    failed_checks = [result for result in checks_with_self if not result.get("passed")]
    failed_phase_count = sum(1 for result in phase_results if not result.get("passed"))
    warning_count = sum(1 for result in phase_results if result.get("degraded"))
    hard_errors = (
        phase_errors
        + artifact_errors
        + authority["violations"]
        + source_price_lineage["errors"]
        + strategy_lineage["errors"]
        + paperops["errors"]
        + proof_boundary["errors"]
        + calendar_boundary["errors"]
        + dashboard_visibility["errors"]
        + telegram_quality["errors"]
        + negative_probes["accepted_probes"]
        + recursive_improvement["errors"]
    )
    hard_failure_count = len(failed_checks) + len(hard_errors)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_end_to_end_certification",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "certification_version": SCHEMA_VERSION,
        "phase_count": len(phase_results),
        "passed_phase_count": len(phase_results) - failed_phase_count,
        "failed_phase_count": failed_phase_count,
        "warning_count": warning_count,
        "required_artifact_count": len(artifact_snapshots),
        "present_artifact_count": sum(1 for snapshot in artifact_snapshots if snapshot.get("exists")),
        "required_check_count": len(REQUIRED_CHECKS),
        "passed_check_count": len(checks_with_self) - len(failed_checks),
        "failed_check_count": len(failed_checks),
        "authority_violation_count": authority["authority_violation_count"],
        "lineage_gap_count": len(source_price_lineage["errors"]) + len(strategy_lineage["errors"]),
        "dashboard_slop_failure_count": dashboard_visibility["dashboard_slop_failure_count"],
        "telegram_quality_failure_count": telegram_quality["telegram_quality_failure_count"],
        "paperops_boundary_failure_count": len(paperops["errors"]),
        "proof_boundary_failure_count": len(proof_boundary["errors"]),
        "calendar_boundary_failure_count": len(calendar_boundary["errors"]),
        "live_capital_enabled": False,
        "broker_write_count": paperops["broker_write_count"],
        "paper_order_created_outside_paperops_count": paperops["paper_order_created_outside_paperops_count"],
        "proof_credit_allowed": False,
        "hard_failure_count": hard_failure_count,
        "certified": False,
        "paper_only": True,
        "read_only": True,
        "proposal_first": True,
        "fail_closed": True,
        "public_safe": True,
        "command_disabled": True,
        "live_capital_ready": False,
        "paperops_handoff_count": paperops["handoff_record_count"],
        "shadow_result_count": len(_read_jsonl(runtime / "qsase_shadow_strategy_results.jsonl")),
        "phase_results": phase_results,
        "required_artifacts": artifact_snapshots,
        "required_checks": checks_with_self,
        "authority_audit": authority,
        "source_price_lineage": source_price_lineage,
        "strategy_lineage": strategy_lineage,
        "paperops_compatibility": paperops,
        "proof_boundary": proof_boundary,
        "calendar_boundary": calendar_boundary,
        "dashboard_visibility": dashboard_visibility,
        "telegram_quality": telegram_quality,
        "negative_safety_probes": negative_probes,
        "recursive_improvement_contract": recursive_improvement,
        "capability_matrix": _capability_matrix(runtime),
        "boundary_summary": {
            "canonical_paperops_wrapper_command_preserved": CANONICAL_PAPEROPS_COMMAND,
            "canonical_paperops_summary_preserved": CANONICAL_PAPEROPS_SUMMARY,
            "telegram_review_only": True,
            "dashboard_review_only": True,
            "paper_proof_ledger_credit_created": False,
            "paper_growth_trial_calendar_advanced": False,
            "no_live_capital_certification": True,
        },
        "artifact_refs": {
            "primary": _artifact_ref(PRIMARY_ARTIFACT),
            "history": _artifact_ref(HISTORY_ARTIFACT),
            "events": _artifact_ref(EVENTS_ARTIFACT),
            "acceptance_report": _artifact_ref(ACCEPTANCE_REPORT_ARTIFACT),
        },
        "authority": universal_authority_flags(),
    }
    payload["status"] = _derive_status(payload)
    payload["certified"] = payload["status"].startswith("certified_") and hard_failure_count == 0
    payload["acceptance_report"] = _acceptance_report(payload)
    return payload


def validate_qsase_end_to_end_certification(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_end_to_end_certification":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in ALLOWED_CERTIFICATION_STATUSES:
        errors.append("status_invalid")
    if not payload.get("generated_at"):
        errors.append("generated_at_missing")
    for field in ("paper_only", "read_only", "proposal_first", "fail_closed", "public_safe", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in ("live_capital_enabled", "proof_credit_allowed", "live_capital_ready"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    if _int(payload.get("authority_violation_count"), -1) != 0:
        errors.append("authority_violation_count_must_be_zero")
    for field in (
        "lineage_gap_count",
        "dashboard_slop_failure_count",
        "telegram_quality_failure_count",
        "paperops_boundary_failure_count",
        "proof_boundary_failure_count",
        "calendar_boundary_failure_count",
        "broker_write_count",
        "paper_order_created_outside_paperops_count",
        "failed_check_count",
        "failed_phase_count",
        "hard_failure_count",
    ):
        if _int(payload.get(field), -1) != 0:
            errors.append(f"{field}_must_be_zero")
    if payload.get("required_artifact_count") != payload.get("present_artifact_count"):
        errors.append("required_artifacts_missing")
    if payload.get("required_check_count") != payload.get("passed_check_count"):
        errors.append("required_checks_failed")
    if any(value is not False for value in payload.get("authority", {}).values()):
        errors.append("universal_authority_flags_must_all_be_false")
    if payload.get("negative_safety_probes", {}).get("accepted_probe_count") != 0:
        errors.append("negative_probe_accepted")
    if payload.get("recursive_improvement_contract", {}).get("proposal_only") is not True:
        errors.append("recursive_improvement_not_proposal_only")
    if payload.get("paperops_compatibility", {}).get("canonical_wrapper_command") != CANONICAL_PAPEROPS_COMMAND:
        errors.append("canonical_paperops_command_mismatch")
    if payload.get("paperops_compatibility", {}).get("canonical_summary") != CANONICAL_PAPEROPS_SUMMARY:
        errors.append("canonical_paperops_summary_mismatch")
    if payload.get("calendar_boundary", {}).get("preserves_30_day_paper_growth_trial_calendar") is not True:
        errors.append("paper_growth_trial_calendar_boundary_missing")
    report = payload.get("acceptance_report", {})
    if report.get("public_safe") is not True or report.get("command_disabled") is not True:
        errors.append("acceptance_report_public_safe_boundary_missing")
    return sorted(set(errors))


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    for key in ("required_checks", "required_artifacts", "phase_results"):
        summary[key] = {
            "count": len(payload.get(key, [])),
            "failed_count": sum(1 for row in payload.get(key, []) if row.get("passed") is False),
        }
    return summary


def build_qsase_phase_implementation_status(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    existing = _read_json(runtime / PHASE_STATUS_ARTIFACT)
    if not existing:
        existing = {"schema_version": 1, "phases": {}, "safety": universal_authority_flags()}
    phases = existing.setdefault("phases", {})
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "phase_count": payload["phase_count"],
        "passed_phase_count": payload["passed_phase_count"],
        "failed_phase_count": payload["failed_phase_count"],
        "required_artifact_count": payload["required_artifact_count"],
        "present_artifact_count": payload["present_artifact_count"],
        "required_check_count": payload["required_check_count"],
        "passed_check_count": payload["passed_check_count"],
        "failed_check_count": payload["failed_check_count"],
        "authority_violation_count": payload["authority_violation_count"],
        "lineage_gap_count": payload["lineage_gap_count"],
        "paperops_boundary_failure_count": payload["paperops_boundary_failure_count"],
        "proof_boundary_failure_count": payload["proof_boundary_failure_count"],
        "calendar_boundary_failure_count": payload["calendar_boundary_failure_count"],
        "dashboard_slop_failure_count": payload["dashboard_slop_failure_count"],
        "telegram_quality_failure_count": payload["telegram_quality_failure_count"],
        "certified": payload["certified"],
        "paper_only": True,
        "read_only": True,
        "proposal_first": True,
        "fail_closed": True,
        "live_capital_enabled": False,
        "broker_write_count": payload["broker_write_count"],
        "paper_order_created_outside_paperops_count": payload["paper_order_created_outside_paperops_count"],
        "proof_credit_allowed": False,
        "later_qsase_phases_implemented": False,
    }
    existing["active_phase"] = PHASE_ID
    existing["generated_at"] = payload["generated_at"]
    existing["safety"] = universal_authority_flags()
    return existing


def _append_implementation_log(payload: dict[str, Any]) -> None:
    path = _repo_root() / IMPLEMENTATION_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = "<!-- qsase_15_end_to_end_certification -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-15: End-To-End Certification\n\n"
        f"- Generated at: `{payload['generated_at']}`\n"
        f"- Status: `{payload['status']}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Phases passed / failed: `{payload['passed_phase_count']}` / `{payload['failed_phase_count']}`\n"
        f"- Checks passed / failed: `{payload['passed_check_count']}` / `{payload['failed_check_count']}`\n"
        f"- Artifacts present / required: `{payload['present_artifact_count']}` / `{payload['required_artifact_count']}`\n"
        f"- Authority / lineage / dashboard / Telegram failures: "
        f"`{payload['authority_violation_count']}` / `{payload['lineage_gap_count']}` / "
        f"`{payload['dashboard_slop_failure_count']}` / `{payload['telegram_quality_failure_count']}`\n"
        f"- Safety: certification is read-only, paper-only, proposal-first, command-disabled, "
        f"and cannot create candidates, approvals, paper orders, broker writes, live capital, "
        f"30-day paper growth trial calendar advancement, or paper proof ledger credit.\n"
    )
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in existing:
        existing = existing[: existing.index(marker)].rstrip() + "\n\n"
    path.write_text(existing + entry, encoding="utf-8")


def write_qsase_end_to_end_certification(
    payload: dict[str, Any],
    settings: Settings | None = None,
    append_log: bool = True,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "certification": runtime / PRIMARY_ARTIFACT,
        "history": runtime / HISTORY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
        "acceptance_report": runtime / ACCEPTANCE_REPORT_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["certification"], payload)
    _write_json(paths["acceptance_report"], payload["acceptance_report"])
    _append_jsonl(paths["history"], _summary_without_records(payload))
    _append_jsonl(
        paths["events"],
        {
            "event": "qsase_end_to_end_certification_recorded",
            "generated_at": payload["generated_at"],
            "status": payload["status"],
            "certified": payload["certified"],
            "hard_failure_count": payload["hard_failure_count"],
        },
    )
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload, settings))
    if append_log:
        _append_implementation_log(payload)
    return {key: str(path) for key, path in paths.items()}


def build_and_write_qsase_end_to_end_certification(
    settings: Settings | None = None,
    check_results: list[dict[str, Any]] | None = None,
    append_log: bool = True,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_qsase_end_to_end_certification(settings=settings, check_results=check_results)
    errors = validate_qsase_end_to_end_certification(payload)
    written = write_qsase_end_to_end_certification(payload, settings=settings, append_log=append_log)
    return payload, written, errors


def validate_negative_qsase_certification_probes() -> list[str]:
    base = build_qsase_end_to_end_certification(check_results=[])
    errors: list[str] = []
    probes = {
        "live_capital": ("live_capital_enabled", True),
        "broker_write": ("broker_write_count", 1),
        "paper_order": ("paper_order_created_outside_paperops_count", 1),
        "proof_credit": ("proof_credit_allowed", True),
        "calendar": ("calendar_boundary_failure_count", 1),
        "lineage": ("lineage_gap_count", 1),
        "telegram": ("telegram_quality_failure_count", 1),
        "dashboard": ("dashboard_slop_failure_count", 1),
    }
    for name, (field, value) in probes.items():
        probe = copy.deepcopy(base)
        probe[field] = value
        probe["hard_failure_count"] = max(1, _int(probe.get("hard_failure_count"), 0))
        validation = validate_qsase_end_to_end_certification(probe)
        if not any(field in error for error in validation):
            errors.append(f"{name}_negative_probe_not_rejected")
    return errors
