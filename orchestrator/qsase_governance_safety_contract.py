"""QSASE doctrine, document hierarchy, and governance safety contract.

QSASE-0 is a governance layer. It may write QSASE safety/readout artifacts, but
it must not create candidates, approvals, orders, broker writes, live-capital
authority, proof credit, or simulated calendar progress.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qsase_governance_safety_contract.v1"
PHASE_ID = "qsase_0_doctrine_document_hierarchy_safety_contract"
PHASE_NAME = "QSASE-0: Doctrine, Document Hierarchy, And Safety Contract"
PRIMARY_ARTIFACT = "qsase_governance_safety_contract.json"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

ARTIFACT_FILES = {
    "governance_contract": PRIMARY_ARTIFACT,
    "history": "qsase_governance_safety_contract_history.jsonl",
    "events": "qsase_governance_safety_contract_events.jsonl",
    "authority_flag_audit": "qsase_authority_flag_audit.json",
    "authority_violations": "qsase_authority_violations.jsonl",
    "governance_review_queue": "qsase_governance_review_queue.json",
    "policy_mutation_blockers": "qsase_policy_mutation_blockers.json",
    "proof_boundary_audit": "qsase_proof_boundary_audit.json",
    "calendar_boundary_audit": "qsase_calendar_boundary_audit.json",
    "document_hierarchy": "qsase_doctrine_document_hierarchy.json",
    "dashboard_summary": "qsase_governance_dashboard_summary.json",
}

RUNTIME_SOURCE_FILES = {
    "paperops_autonomous_pass_summary": "paperops_autonomous_pass_summary.json",
    "qsase_phase0_paperops_reliability_baseline": "qsase_phase0_paperops_reliability_baseline.json",
    "phase7_proof_lifecycle_monitor": "phase7_proof_lifecycle_monitor.json",
    "paperops_paper_lifecycle_poller": "paperops_paper_lifecycle_poller.json",
    "cockpit_status": "cockpit-status.json",
}

CANONICAL_DOCUMENTS = [
    {
        "path": "docs/qadam-qsase-implementation-plan.md",
        "role": "QSASE implementation source of truth and phase contract",
        "hierarchy_level": 0,
    },
    {
        "path": "docs/qadam-user-guide.md",
        "role": "User-facing dashboard and visibility contract",
        "hierarchy_level": 1,
    },
    {
        "path": "docs/qadam-foundational-architecture-plan.md",
        "role": "Qadam architecture and system-role doctrine",
        "hierarchy_level": 2,
    },
    {
        "path": "docs/qadam-paper-operational-mode-plan.md",
        "role": "Paper-only operating boundary",
        "hierarchy_level": 3,
    },
    {
        "path": "docs/qadam-phase-7-demo-proof-implementation-plan.md",
        "role": "30-day paper growth trial and paper proof ledger boundary",
        "hierarchy_level": 4,
    },
    {
        "path": "docs/qadam-resource-registry.md",
        "role": "Source and resource registry reference",
        "hierarchy_level": 5,
    },
]

UNIVERSAL_AUTHORITY_FLAGS = {
    "live_capital_enabled": False,
    "live_broker_endpoint_allowed": False,
    "broker_write_allowed": False,
    "broker_live_write_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "qualified_setup_created": False,
    "trade_candidate_created": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "llm_order_authority": False,
    "local_llm_order_authority": False,
    "frontier_llm_order_authority": False,
    "quantum_order_authority": False,
    "quantum_job_authority": False,
    "qctrl_bypass_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "model_weight_mutation_allowed": False,
    "model_weight_update_created": False,
    "source_trust_mutation_allowed": False,
    "trust_score_update_created": False,
    "source_promotion_allowed": False,
    "policy_mutation_allowed": False,
    "policy_mutation_created": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "secret_read_allowed": False,
    "secret_write_allowed": False,
    "dashboard_write_authority_allowed": False,
    "notification_command_authority_allowed": False,
    "backtest_to_proof_allowed": False,
    "shadow_to_proof_allowed": False,
}

VIOLATION_TYPES_BY_FIELD = {
    "live_capital_enabled": "live_capital_enabled",
    "live_broker_endpoint_allowed": "live_broker_endpoint_detected",
    "broker_write_allowed": "broker_write_authority_detected",
    "broker_live_write_allowed": "live_broker_endpoint_detected",
    "paper_order_allowed": "paper_order_created_outside_paperops",
    "paper_order_created": "paper_order_created_outside_paperops",
    "qualified_setup_created": "qualified_setup_created_outside_paperops",
    "trade_candidate_created": "qualified_setup_created_outside_paperops",
    "risk_approval_allowed": "risk_approval_created_outside_risk_agent",
    "risk_approval_created": "risk_approval_created_outside_risk_agent",
    "execution_approval_allowed": "execution_approval_created_outside_execution_policy",
    "execution_approval_created": "execution_approval_created_outside_execution_policy",
    "telegram_command_path_enabled": "telegram_command_path_enabled",
    "telegram_trade_command_enabled": "telegram_inbound_command_executed",
    "llm_order_authority": "llm_order_authority_detected",
    "local_llm_order_authority": "llm_order_authority_detected",
    "frontier_llm_order_authority": "llm_order_authority_detected",
    "quantum_order_authority": "quantum_order_authority_detected",
    "quantum_job_authority": "quantum_order_authority_detected",
    "qctrl_bypass_allowed": "qctrl_bypass_detected",
    "strategy_mutation_allowed": "strategy_mutation_without_approval",
    "strategy_mutation_created": "strategy_mutation_without_approval",
    "model_weight_mutation_allowed": "model_weight_mutation_without_approval",
    "model_weight_update_created": "model_weight_mutation_without_approval",
    "source_trust_mutation_allowed": "trust_score_mutation_without_approval",
    "trust_score_update_created": "trust_score_mutation_without_approval",
    "source_promotion_allowed": "source_promotion_without_governance",
    "policy_mutation_allowed": "strategy_mutation_without_approval",
    "policy_mutation_created": "strategy_mutation_without_approval",
    "proof_credit_allowed": "proof_credit_granted_without_paper_lifecycle",
    "paper_proof_ledger_write_allowed": "proof_credit_granted_without_paper_lifecycle",
    "simulated_elapsed_time_allowed": "simulated_elapsed_time_detected",
    "secret_read_allowed": "secret_exposure_detected",
    "secret_write_allowed": "secret_exposure_detected",
    "dashboard_write_authority_allowed": "dashboard_write_authority_detected",
    "notification_command_authority_allowed": "notification_command_authority_detected",
    "backtest_to_proof_allowed": "proof_credit_granted_without_paper_lifecycle",
    "shadow_to_proof_allowed": "proof_credit_granted_without_paper_lifecycle",
}

POLICY_MUTATION_SURFACES = [
    "strategy_weights",
    "strategy_family_definitions",
    "akber_filter_thresholds",
    "model_weights",
    "source_trust_scores",
    "source_promotion",
    "risk_policy",
    "execution_policy",
    "paperops_gates",
    "proof_standards",
]


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


def _runtime_paths(runtime_dir: Path) -> dict[str, Path]:
    return {key: runtime_dir / filename for key, filename in RUNTIME_SOURCE_FILES.items()}


def _file_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
            "exists": False,
            "size_bytes": 0,
        }
    stat = path.stat()
    return {
        "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime": _iso(datetime.fromtimestamp(stat.st_mtime, timezone.utc)),
    }


def _int(value: Any) -> int:
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
            return 0
    return 0


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _contract_source_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime_dir = _runtime_dir(settings)
    paths = _runtime_paths(runtime_dir)
    return {
        "runtime_dir": str(runtime_dir),
        "sources": {key: _read_json(path) for key, path in paths.items()},
        "source_artifacts": {key: _file_snapshot(path) for key, path in paths.items()},
    }


def universal_authority_flags() -> dict[str, bool]:
    return dict(UNIVERSAL_AUTHORITY_FLAGS)


def fail_closed_authority_violation(
    violation_type: str,
    offending_field: str,
    source_artifact: str,
    observed_value: Any,
    recommended_next_action: str = "block_and_require_governance_review",
) -> dict[str, Any]:
    return {
        "status": "blocked_authority_boundary_violation",
        "violation_type": violation_type,
        "offending_field": offending_field,
        "source_artifact": source_artifact,
        "observed_value": observed_value,
        "recommended_next_action": recommended_next_action,
        "repair_or_governance_required": True,
    }


def detect_qsase_authority_violations(context: dict[str, Any]) -> list[dict[str, Any]]:
    authority = context.get("authority")
    if not isinstance(authority, dict):
        authority = {}
    violations: list[dict[str, Any]] = []

    for field, expected in UNIVERSAL_AUTHORITY_FLAGS.items():
        if field not in authority:
            violations.append(
                fail_closed_authority_violation(
                    "missing_universal_authority_flag",
                    field,
                    "qsase_governance_safety_contract",
                    "missing",
                    "restore_universal_authority_flag_before_progressing_qsase",
                )
            )
            continue
        if authority[field] is not expected:
            violations.append(
                fail_closed_authority_violation(
                    VIOLATION_TYPES_BY_FIELD.get(field, "authority_boundary_violation"),
                    field,
                    "qsase_governance_safety_contract",
                    authority[field],
                )
            )

    sources = context.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    summary = sources.get("paperops_autonomous_pass_summary")
    if not isinstance(summary, dict):
        summary = {}
    summary_safety = summary.get("safety")
    if not isinstance(summary_safety, dict):
        summary_safety = {}
    paper_growth_trial = summary.get("paper_growth_trial")
    if not isinstance(paper_growth_trial, dict):
        paper_growth_trial = {}

    runtime_checks = {
        "live_capital_enabled": summary_safety.get("live_capital_enabled"),
        "broker_post_called_count": summary_safety.get("broker_post_called_count"),
        "alpaca_post_called_count": summary_safety.get("alpaca_post_called_count"),
        "command_path_enabled_count": summary_safety.get("command_path_enabled_count"),
        "notification_live_send_allowed_count": summary_safety.get(
            "notification_live_send_allowed_count"
        ),
        "phase7_proof_credit_allowed": summary_safety.get("phase7_proof_credit_allowed"),
        "backfill_used": paper_growth_trial.get("backfill_used"),
        "simulated_time_used": paper_growth_trial.get("simulated_time_used"),
    }
    count_violation_fields = {
        "broker_post_called_count": "broker_write_authority_detected",
        "alpaca_post_called_count": "broker_write_authority_detected",
        "command_path_enabled_count": "telegram_command_path_enabled",
        "notification_live_send_allowed_count": "notification_command_authority_detected",
    }
    for field, value in runtime_checks.items():
        if field in count_violation_fields and _int(value) > 0:
            violations.append(
                fail_closed_authority_violation(
                    count_violation_fields[field],
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    value,
                )
            )
        elif field == "live_capital_enabled" and value is True:
            violations.append(
                fail_closed_authority_violation(
                    "live_capital_enabled",
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    value,
                )
            )
        elif field == "phase7_proof_credit_allowed" and value is True:
            violations.append(
                fail_closed_authority_violation(
                    "proof_credit_granted_without_paper_lifecycle",
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    value,
                )
            )
        elif field == "backfill_used" and value is True:
            violations.append(
                fail_closed_authority_violation(
                    "simulated_elapsed_time_detected",
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    value,
                    "preserve_real_calendar_and_remove_backfilled_proof_claim",
                )
            )
        elif field == "simulated_time_used" and value is True:
            violations.append(
                fail_closed_authority_violation(
                    "simulated_elapsed_time_detected",
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    value,
                    "preserve_real_calendar_and_remove_simulated_elapsed_time",
                )
            )
    return violations


def build_qsase_authority_flag_audit(context: dict[str, Any]) -> dict[str, Any]:
    authority = context.get("authority")
    if not isinstance(authority, dict):
        authority = {}
    violations = detect_qsase_authority_violations(context)
    false_count = sum(1 for flag in UNIVERSAL_AUTHORITY_FLAGS if authority.get(flag) is False)
    missing_flags = [flag for flag in UNIVERSAL_AUTHORITY_FLAGS if flag not in authority]
    true_flags = [flag for flag in UNIVERSAL_AUTHORITY_FLAGS if authority.get(flag) is True]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_authority_flag_audit",
        "status": "authority_flags_ready" if not violations else "blocked_authority_boundary_violation",
        "authority_flag_count": len(UNIVERSAL_AUTHORITY_FLAGS),
        "authority_false_count": false_count,
        "authority_true_count": len(true_flags),
        "authority_missing_count": len(missing_flags),
        "authority_true_flags": true_flags,
        "authority_missing_flags": missing_flags,
        "authority_violation_count": len(violations),
        "fail_closed": True,
        "violations": violations,
    }


def build_qsase_document_hierarchy(now: datetime | None = None) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    documents: list[dict[str, Any]] = []
    missing: list[str] = []
    for record in CANONICAL_DOCUMENTS:
        path = _repo_root() / record["path"]
        exists = path.exists()
        if not exists:
            missing.append(record["path"])
        documents.append({**record, "exists": exists})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_doctrine_document_hierarchy",
        "generated_at": generated_at,
        "status": "document_hierarchy_ready" if not missing else "blocked_missing_doctrine_document",
        "doctrine": {
            "qadam_evolution_not_separate_product": True,
            "operational_self_awareness_not_sentience": True,
            "intelligence_expands_authority_does_not": True,
            "proposal_first": True,
            "paper_only": True,
            "real_calendar_required": True,
            "paper_proof_ledger_requires_real_guarded_paper_lifecycle": True,
        },
        "document_hierarchy": documents,
        "missing_document_count": len(missing),
        "missing_documents": missing,
    }


def build_qsase_governance_review_queue(
    context: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    violations = detect_qsase_authority_violations(context)
    review_records = []
    for index, violation in enumerate(violations, start=1):
        review_records.append(
            {
                "review_id": f"qsase-0-governance-review-{index:03d}",
                "proposal_id": None,
                "proposal_type": "authority_violation",
                "target_surface": violation["source_artifact"],
                "evidence_refs": [violation["source_artifact"]],
                "supporting_evidence_count": 1,
                "contradicting_evidence_count": 0,
                "real_paper_evidence_count": 0,
                "shadow_evidence_count": 0,
                "backtest_evidence_count": 0,
                "overfit_risk": "not_applicable",
                "source_noise_risk": "not_applicable",
                "regime_bias_risk": "not_applicable",
                "paperability_state": "blocked_authority_boundary_violation",
                "risk_review_required": True,
                "approval_state": "pending_review",
                "approved_by": None,
                "approved_at": None,
                "apply_module_required": True,
                "applied": False,
                "rollback_plan_ref": None,
                "authority_flags": universal_authority_flags(),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_governance_review_queue",
        "generated_at": generated_at,
        "status": "governance_review_queue_empty"
        if not review_records
        else "governance_review_required",
        "governance_review_queue_count": len(review_records),
        "proposal_pending_review_count": len(review_records),
        "proposal_approved_count": 0,
        "proposal_applied_count": 0,
        "review_records": review_records,
        "authority": universal_authority_flags(),
    }


def build_qsase_policy_mutation_blockers(now: datetime | None = None) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    blockers = [
        {
            "surface": surface,
            "status": "blocked_pending_governance_apply_module",
            "proposal_allowed": True,
            "mutation_allowed": False,
            "approval_required": True,
            "separate_apply_module_required": True,
            "applied": False,
        }
        for surface in POLICY_MUTATION_SURFACES
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_policy_mutation_blockers",
        "generated_at": generated_at,
        "status": "policy_mutations_blocked_by_default",
        "blocker_count": len(blockers),
        "proposal_first": True,
        "approval_required_for_mutation": True,
        "separate_apply_module_required": True,
        "proposal_applied_count": 0,
        "blockers": blockers,
        "authority": universal_authority_flags(),
    }


def build_qsase_proof_boundary_audit(
    context: dict[str, Any],
    authority: dict[str, bool],
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    sources = context.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    summary = sources.get("paperops_autonomous_pass_summary")
    if not isinstance(summary, dict):
        summary = {}
    proof_ledger = summary.get("paper_proof_ledger")
    if not isinstance(proof_ledger, dict):
        proof_ledger = {}
    summary_safety = summary.get("safety")
    if not isinstance(summary_safety, dict):
        summary_safety = {}
    violations: list[dict[str, Any]] = []
    proof_flags = {
        "proof_credit_allowed": authority.get("proof_credit_allowed"),
        "paper_proof_ledger_write_allowed": authority.get("paper_proof_ledger_write_allowed"),
        "backtest_to_proof_allowed": authority.get("backtest_to_proof_allowed"),
        "shadow_to_proof_allowed": authority.get("shadow_to_proof_allowed"),
        "phase7_proof_credit_allowed": summary_safety.get("phase7_proof_credit_allowed"),
    }
    for field, value in proof_flags.items():
        if value is True:
            violations.append(
                fail_closed_authority_violation(
                    "proof_credit_granted_without_paper_lifecycle",
                    field,
                    "qsase_proof_boundary_audit",
                    value,
                    "remove_proof_credit_authority_and_require_real_guarded_paper_lifecycle",
                )
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_proof_boundary_audit",
        "generated_at": generated_at,
        "status": "proof_boundary_ready" if not violations else "blocked_authority_boundary_violation",
        "actual_calendar_required": True,
        "paper_proof_ledger_write_allowed": False,
        "proof_credit_allowed": False,
        "shadow_to_proof_allowed": False,
        "backtest_to_proof_allowed": False,
        "paper_proof_ledger": {
            "closed_proof_trade_count": _int(proof_ledger.get("closed_proof_trade_count")),
            "qualified_setup_count": _int(proof_ledger.get("qualified_setup_count")),
            "submitted_paper_order_count": _int(proof_ledger.get("submitted_paper_order_count")),
        },
        "proof_boundary_violation_count": len(violations),
        "violations": violations,
        "authority": universal_authority_flags(),
    }


def build_qsase_calendar_boundary_audit(
    context: dict[str, Any],
    authority: dict[str, bool],
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    sources = context.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    summary = sources.get("paperops_autonomous_pass_summary")
    if not isinstance(summary, dict):
        summary = {}
    paper_growth_trial = summary.get("paper_growth_trial")
    if not isinstance(paper_growth_trial, dict):
        paper_growth_trial = {}
    violations: list[dict[str, Any]] = []
    if authority.get("simulated_elapsed_time_allowed") is True:
        violations.append(
            fail_closed_authority_violation(
                "simulated_elapsed_time_detected",
                "simulated_elapsed_time_allowed",
                "qsase_calendar_boundary_audit",
                True,
            )
        )
    for field in ("backfill_used", "simulated_time_used"):
        if paper_growth_trial.get(field) is True:
            violations.append(
                fail_closed_authority_violation(
                    "simulated_elapsed_time_detected",
                    field,
                    RUNTIME_SOURCE_FILES["paperops_autonomous_pass_summary"],
                    True,
                    "preserve_actual_30_day_paper_growth_trial_calendar",
                )
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_calendar_boundary_audit",
        "generated_at": generated_at,
        "status": "calendar_boundary_ready" if not violations else "blocked_authority_boundary_violation",
        "actual_calendar_required": True,
        "backfill_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "historical_backtests_remain_historical": True,
        "shadow_replays_remain_shadow": True,
        "paper_growth_trial": {
            "run_day": paper_growth_trial.get("run_day"),
            "run_state": paper_growth_trial.get("run_state"),
            "actual_calendar_run": paper_growth_trial.get("actual_calendar_run"),
            "backfill_used": paper_growth_trial.get("backfill_used"),
            "simulated_time_used": paper_growth_trial.get("simulated_time_used"),
            "completed_calendar_day_count": paper_growth_trial.get("completed_calendar_day_count"),
        },
        "calendar_boundary_violation_count": len(violations),
        "violations": violations,
        "authority": universal_authority_flags(),
    }


def build_qsase_governance_dashboard_summary(
    contract: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = _iso(now or _now())
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_governance_dashboard_summary",
        "generated_at": generated_at,
        "status": contract.get("status"),
        "title": "Safety Status",
        "rows": [
            {"label": "Mode", "value": "paper-only"},
            {"label": "QSASE authority", "value": "research and proposals only"},
            {"label": "Dashboard", "value": "read-only"},
            {"label": "Telegram", "value": "review-only"},
            {"label": "Broker writes", "value": "no"},
            {"label": "Live capital", "value": "off"},
            {"label": "Proof", "value": "paper proof ledger only"},
            {"label": "Violations", "value": str(contract.get("authority_violation_count", 0))},
        ],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "authority": universal_authority_flags(),
    }


def build_qsase_governance_safety_contract(
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated = now or _now()
    generated_at = _iso(generated)
    context = _contract_source_context(settings)
    authority = universal_authority_flags()
    context["authority"] = authority
    authority_violations = detect_qsase_authority_violations(context)
    authority_audit = build_qsase_authority_flag_audit(context)
    proof_boundary = build_qsase_proof_boundary_audit(context, authority, generated)
    calendar_boundary = build_qsase_calendar_boundary_audit(context, authority, generated)
    document_hierarchy = build_qsase_document_hierarchy(generated)
    governance_review_queue = build_qsase_governance_review_queue(context, generated)
    policy_mutation_blockers = build_qsase_policy_mutation_blockers(generated)
    status = "governance_safety_ready"
    if (
        authority_violations
        or proof_boundary["proof_boundary_violation_count"]
        or calendar_boundary["calendar_boundary_violation_count"]
        or document_hierarchy["missing_document_count"]
    ):
        status = "blocked_authority_boundary_violation"
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "qsase:0:governance-safety-contract",
        "artifact_type": "qsase_governance_safety_contract",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "status": status,
        "generated_at": generated_at,
        "boundary": "QSASE expands research intelligence, not trading authority.",
        "mode": {
            "paper_only": True,
            "dashboard_read_only": True,
            "telegram_review_only": True,
            "live_capital_enabled": False,
        },
        "doctrine": document_hierarchy["doctrine"],
        "document_hierarchy": document_hierarchy["document_hierarchy"],
        "authority_classes": {
            "analysis_authority": True,
            "proposal_authority": True,
            "review_handoff_authority": True,
            "execution_authority": False,
            "mutation_authority": False,
        },
        "authority_audit": {
            "authority_flag_count": authority_audit["authority_flag_count"],
            "authority_false_count": authority_audit["authority_false_count"],
            "authority_violation_count": authority_audit["authority_violation_count"],
            "fail_closed": True,
        },
        "proposal_policy": {
            "proposal_first": True,
            "approval_required_for_mutation": True,
            "separate_apply_module_required": True,
            "proposal_applied_count": 0,
        },
        "proof_policy": {
            "actual_calendar_required": True,
            "backfill_allowed": False,
            "shadow_to_proof_allowed": False,
            "backtest_to_proof_allowed": False,
            "paper_proof_ledger_write_allowed": False,
        },
        "authority": authority,
        "authority_flag_count": authority_audit["authority_flag_count"],
        "authority_false_count": authority_audit["authority_false_count"],
        "authority_violation_count": len(authority_violations),
        "governance_review_queue_count": governance_review_queue["governance_review_queue_count"],
        "proposal_pending_review_count": governance_review_queue["proposal_pending_review_count"],
        "proposal_approved_count": governance_review_queue["proposal_approved_count"],
        "proposal_applied_count": governance_review_queue["proposal_applied_count"],
        "paper_order_created_count": 0,
        "paper_order_created_outside_paperops_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "telegram_command_path_enabled": False,
        "qctrl_bypass_allowed": False,
        "secret_exposure_detected": False,
        "simulated_elapsed_time_detected": False,
        "authority_violations": authority_violations,
        "authority_flag_audit": authority_audit,
        "proof_boundary_audit": proof_boundary,
        "calendar_boundary_audit": calendar_boundary,
        "governance_review_queue": governance_review_queue,
        "policy_mutation_blockers": policy_mutation_blockers,
        "source_artifacts": context["source_artifacts"],
        "validation_errors": [],
    }
    contract["dashboard_safe_summary"] = build_qsase_governance_dashboard_summary(
        contract,
        generated,
    )
    return contract


def validate_qsase_governance_safety_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qsase_governance_safety_contract":
        errors.append("artifact_type_mismatch")
    if payload.get("phase_id") != PHASE_ID:
        errors.append("phase_id_mismatch")
    mode = payload.get("mode")
    if not isinstance(mode, dict):
        errors.append("mode_missing")
        mode = {}
    required_true_mode = ("paper_only", "dashboard_read_only", "telegram_review_only")
    for field in required_true_mode:
        if mode.get(field) is not True:
            errors.append(f"mode_{field}_must_be_true")
    if mode.get("live_capital_enabled") is not False:
        errors.append("mode_live_capital_enabled_must_be_false")
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority_missing")
        authority = {}
    for field, expected in UNIVERSAL_AUTHORITY_FLAGS.items():
        if field not in authority:
            errors.append(f"authority_missing:{field}")
        elif authority[field] is not expected:
            errors.append(f"authority_unsafe_true:{field}")
    authority_audit = payload.get("authority_audit")
    if not isinstance(authority_audit, dict):
        errors.append("authority_audit_missing")
        authority_audit = {}
    if authority_audit.get("authority_flag_count") != len(UNIVERSAL_AUTHORITY_FLAGS):
        errors.append("authority_flag_count_mismatch")
    if authority_audit.get("authority_false_count") != len(UNIVERSAL_AUTHORITY_FLAGS):
        errors.append("authority_false_count_mismatch")
    if authority_audit.get("fail_closed") is not True:
        errors.append("authority_audit_fail_closed_missing")
    if payload.get("authority_violation_count") != 0 and payload.get("status") != (
        "blocked_authority_boundary_violation"
    ):
        errors.append("authority_violations_must_fail_closed")
    forbidden_summary_truths = (
        "proof_credit_allowed",
        "live_capital_enabled",
        "telegram_command_path_enabled",
        "qctrl_bypass_allowed",
        "secret_exposure_detected",
        "simulated_elapsed_time_detected",
    )
    for field in forbidden_summary_truths:
        if payload.get(field) is not False:
            errors.append(f"summary_unsafe_true:{field}")
    forbidden_count_fields = (
        "paper_order_created_count",
        "paper_order_created_outside_paperops_count",
        "broker_write_count",
        "proposal_applied_count",
    )
    for field in forbidden_count_fields:
        if _int(payload.get(field)) != 0:
            errors.append(f"summary_count_must_be_zero:{field}")
    proof_policy = payload.get("proof_policy")
    if not isinstance(proof_policy, dict):
        errors.append("proof_policy_missing")
        proof_policy = {}
    for field in (
        "backfill_allowed",
        "shadow_to_proof_allowed",
        "backtest_to_proof_allowed",
        "paper_proof_ledger_write_allowed",
    ):
        if proof_policy.get(field) is not False:
            errors.append(f"proof_policy_{field}_must_be_false")
    if proof_policy.get("actual_calendar_required") is not True:
        errors.append("proof_policy_actual_calendar_required_missing")
    dashboard_summary = payload.get("dashboard_safe_summary")
    if not isinstance(dashboard_summary, dict):
        errors.append("dashboard_safe_summary_missing")
    else:
        if dashboard_summary.get("public_safe") is not True:
            errors.append("dashboard_summary_public_safe_missing")
        if dashboard_summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_command_disabled_missing")
        if dashboard_summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
    document_hierarchy = payload.get("document_hierarchy")
    if not isinstance(document_hierarchy, list) or not document_hierarchy:
        errors.append("document_hierarchy_missing")
    else:
        missing_docs = [doc.get("path") for doc in document_hierarchy if not doc.get("exists")]
        if missing_docs:
            errors.append(f"document_hierarchy_missing_documents:{','.join(missing_docs)}")
    return errors


def load_qsase_governance_safety_contract(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / PRIMARY_ARTIFACT)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def build_qsase_phase_implementation_status(contract: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": contract["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "authority_flag_count": contract["authority_flag_count"],
        "authority_false_count": contract["authority_false_count"],
        "authority_violation_count": contract["authority_violation_count"],
        "governance_review_queue_count": contract["governance_review_queue_count"],
        "proposal_applied_count": contract["proposal_applied_count"],
        "paper_order_created_count": contract["paper_order_created_count"],
        "broker_write_count": contract["broker_write_count"],
        "proof_credit_allowed": contract["proof_credit_allowed"],
        "live_capital_enabled": contract["live_capital_enabled"],
        "telegram_command_path_enabled": contract["telegram_command_path_enabled"],
        "qctrl_bypass_allowed": contract["qctrl_bypass_allowed"],
        "secret_exposure_detected": contract["secret_exposure_detected"],
        "simulated_elapsed_time_detected": contract["simulated_elapsed_time_detected"],
        "paper_only": True,
        "proposal_first": True,
        "read_only_where_applicable": True,
        "fail_closed": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": contract["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": contract["authority"],
    }


def _append_implementation_log(contract: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8")
        if log_path.exists()
        else "# QSASE Implementation Log\n"
    )
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-0: Doctrine, Document Hierarchy, And Safety Contract\n\n"
        f"- Generated at: `{contract.get('generated_at')}`\n"
        f"- Status: `{contract.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Authority flags: `{contract.get('authority_false_count')}`/"
        f"`{contract.get('authority_flag_count')}` false\n"
        f"- Authority violations: `{contract.get('authority_violation_count')}`\n"
        f"- Boundaries: paper-only, proposal-first, read-only dashboard, review-only Telegram, "
        f"no proof credit, no live capital, no broker writes, no simulated elapsed time.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_qsase_governance_safety_contract(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    artifact_payloads = {
        "governance_contract": payload,
        "authority_flag_audit": payload["authority_flag_audit"],
        "governance_review_queue": payload["governance_review_queue"],
        "policy_mutation_blockers": payload["policy_mutation_blockers"],
        "proof_boundary_audit": payload["proof_boundary_audit"],
        "calendar_boundary_audit": payload["calendar_boundary_audit"],
        "document_hierarchy": {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_doctrine_document_hierarchy",
            "generated_at": payload["generated_at"],
            "status": "document_hierarchy_ready",
            "doctrine": payload["doctrine"],
            "document_hierarchy": payload["document_hierarchy"],
        },
        "dashboard_summary": payload["dashboard_safe_summary"],
    }
    for artifact_key, artifact_payload in artifact_payloads.items():
        path = runtime_dir / ARTIFACT_FILES[artifact_key]
        _write_json(path, artifact_payload)
        written[artifact_key] = str(path)

    violations_path = runtime_dir / ARTIFACT_FILES["authority_violations"]
    _write_jsonl(violations_path, payload["authority_violations"])
    written["authority_violations"] = str(violations_path)

    status_path = runtime_dir / PHASE_STATUS_ARTIFACT
    _write_json(status_path, build_qsase_phase_implementation_status(payload))
    written["phase_status"] = str(status_path)

    if append_history:
        history_path = runtime_dir / ARTIFACT_FILES["history"]
        event_path = runtime_dir / ARTIFACT_FILES["events"]
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "authority_flag_count": payload["authority_flag_count"],
                "authority_false_count": payload["authority_false_count"],
                "authority_violation_count": payload["authority_violation_count"],
            },
        )
        _append_jsonl(
            event_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_governance_safety_contract_written",
                "status": payload["status"],
                "authority_violation_count": payload["authority_violation_count"],
                "paper_only": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(event_path)

    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)

    return written


def build_and_write_qsase_governance_safety_contract(
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_qsase_governance_safety_contract(settings)
    errors = validate_qsase_governance_safety_contract(payload)
    payload["validation_errors"] = errors
    written = write_qsase_governance_safety_contract(
        payload,
        settings,
        append_history=append_history,
        append_log=append_log,
    )
    return payload, written, errors


def validate_qsase_proof_boundary(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    proof_boundary = payload.get("proof_boundary_audit")
    if not isinstance(proof_boundary, dict):
        errors.append("proof_boundary_audit_missing")
        return errors
    for field in (
        "paper_proof_ledger_write_allowed",
        "proof_credit_allowed",
        "shadow_to_proof_allowed",
        "backtest_to_proof_allowed",
    ):
        if proof_boundary.get(field) is not False:
            errors.append(f"proof_boundary_{field}_must_be_false")
    if proof_boundary.get("actual_calendar_required") is not True:
        errors.append("proof_boundary_actual_calendar_required_missing")
    if _int(proof_boundary.get("proof_boundary_violation_count")) != 0:
        errors.append("proof_boundary_violations_present")
    return errors


def validate_qsase_calendar_boundary(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    calendar_boundary = payload.get("calendar_boundary_audit")
    if not isinstance(calendar_boundary, dict):
        errors.append("calendar_boundary_audit_missing")
        return errors
    if calendar_boundary.get("actual_calendar_required") is not True:
        errors.append("calendar_boundary_actual_calendar_required_missing")
    if calendar_boundary.get("backfill_allowed") is not False:
        errors.append("calendar_boundary_backfill_allowed_must_be_false")
    if calendar_boundary.get("simulated_elapsed_time_allowed") is not False:
        errors.append("calendar_boundary_simulated_elapsed_time_allowed_must_be_false")
    trial = calendar_boundary.get("paper_growth_trial")
    if isinstance(trial, dict):
        if trial.get("backfill_used") is True:
            errors.append("calendar_boundary_backfill_used_detected")
        if trial.get("simulated_time_used") is True:
            errors.append("calendar_boundary_simulated_time_used_detected")
    if _int(calendar_boundary.get("calendar_boundary_violation_count")) != 0:
        errors.append("calendar_boundary_violations_present")
    return errors


def validate_negative_authority_probes() -> list[str]:
    errors: list[str] = []
    base = build_qsase_governance_safety_contract()
    for field in UNIVERSAL_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority"][field] = True
        probe["authority_audit"] = build_qsase_authority_flag_audit(
            {"authority": probe["authority"], "sources": {}}
        )
        probe["authority_violation_count"] = probe["authority_audit"]["authority_violation_count"]
        probe["status"] = "governance_safety_ready"
        probe_errors = validate_qsase_governance_safety_contract(probe)
        if not any(field in error for error in probe_errors):
            errors.append(f"negative_probe_failed_to_reject:{field}")
    probe = copy.deepcopy(base)
    probe["authority"].pop("live_capital_enabled", None)
    probe_errors = validate_qsase_governance_safety_contract(probe)
    if not any("authority_missing:live_capital_enabled" == error for error in probe_errors):
        errors.append("negative_probe_failed_to_reject_missing_live_capital_enabled")
    probe = copy.deepcopy(base)
    probe["paper_order_created_count"] = 1
    probe_errors = validate_qsase_governance_safety_contract(probe)
    if not any("paper_order_created_count" in error for error in probe_errors):
        errors.append("negative_probe_failed_to_reject_paper_order_created_count")
    return errors
