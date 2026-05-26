"""Q7-0 Phase 7 Demo Proof re-entry and operating-rules gate.

This stage validates that Q6-17 certified Phase 6 for Phase 7 demo-proof
planning, then freezes the updated 30-day proof contract. It does not start the
proof harness, create proof trades, grant proof credit, call broker routes, or
enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_certification import (
    PHASE6_CERTIFICATION_RUNTIME_ARTIFACT,
    phase6_certification_paths,
    validate_phase6_certification,
)
from orchestrator.release_contract import (
    PAPER_ACCOUNT_BALANCE_GBP,
    PHASE7_HARNESS_DAY_COUNT as RELEASE_PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK as RELEASE_PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET as RELEASE_PHASE7_WEEKLY_PROOF_TRADE_TARGET,
)


PHASE7_READINESS_SCHEMA_VERSION = 1
PHASE7_READINESS_RUNTIME_ARTIFACT = "phase7_readiness.json"
PHASE7_READINESS_HISTORY = "phase7_readiness_history.jsonl"
PHASE7_READINESS_EVENT_LOG = "phase7_readiness_events.jsonl"
PHASE7_READINESS_EVENT_TYPE = "phase7_readiness_recorded"
PHASE7_READINESS_COMPONENT = "phase7_readiness"

PHASE7_HARNESS_DAY_COUNT = RELEASE_PHASE7_HARNESS_DAY_COUNT
PHASE7_WEEKLY_PROOF_TRADE_TARGET = RELEASE_PHASE7_WEEKLY_PROOF_TRADE_TARGET
PHASE7_MATURE_CLOSED_TRADE_BENCHMARK = RELEASE_PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
PHASE7_MAX_DRAWDOWN_FRACTION = 0.20
PHASE7_PAPER_ACCOUNT_STARTING_GBP = float(PAPER_ACCOUNT_BALANCE_GBP)

PHASE7_STAGE_SCOPE: tuple[dict[str, str], ...] = (
    {
        "stage": "Q7-1",
        "name": "Artifact Schema And Proof Authority Ledger",
        "authority": "schema_only",
    },
    {
        "stage": "Q7-2",
        "name": "30-Day Calendar Harness",
        "authority": "harness_scheduling_only",
    },
    {
        "stage": "Q7-3",
        "name": "Qualified Setup Ledger",
        "authority": "read_only_eligibility",
    },
    {
        "stage": "Q7-4",
        "name": "Weekly Proof Cadence Tracker",
        "authority": "cadence_accounting",
    },
    {
        "stage": "Q7-5",
        "name": "Test-Mode Auto-Approval Router",
        "authority": "test_mode_approval_only",
    },
    {
        "stage": "Q7-6",
        "name": "Proof Order Staging And Idempotency",
        "authority": "staging_only",
    },
    {
        "stage": "Q7-7",
        "name": "Guarded Alpaca Paper Submit Path",
        "authority": "paper_submit_only_after_q7_gates",
    },
    {
        "stage": "Q7-8",
        "name": "Proof Lifecycle Monitor",
        "authority": "paper_lifecycle_only",
    },
    {
        "stage": "Q7-9",
        "name": "Proof Postmortem Contract",
        "authority": "postmortem_required",
    },
    {
        "stage": "Q7-10",
        "name": "Performance Evaluator",
        "authority": "evaluation_only",
    },
    {
        "stage": "Q7-11",
        "name": "Drawdown And Risk Sentinel",
        "authority": "risk_halt_only",
    },
    {
        "stage": "Q7-12",
        "name": "Override Detector",
        "authority": "clean_sample_guard",
    },
    {
        "stage": "Q7-13",
        "name": "Source And Signal Funnel Evidence",
        "authority": "evidence_only",
    },
    {
        "stage": "Q7-14",
        "name": "100-Trade Maturity Tracker",
        "authority": "maturity_accounting",
    },
    {
        "stage": "Q7-15",
        "name": "Cockpit And Mission Control Visibility",
        "authority": "visibility_only",
    },
    {
        "stage": "Q7-16",
        "name": "Weekly Review Pack",
        "authority": "review_packet_only",
    },
    {
        "stage": "Q7-17",
        "name": "30-Day Demo Proof Certification",
        "authority": "certification_only",
    },
    {
        "stage": "Q7-18",
        "name": "Live Promotion Review Flow",
        "authority": "review_only",
    },
)

PHASE7_AUTHORITY_FLAGS: tuple[str, ...] = (
    "phase7_demo_proof_implementation_allowed",
    "phase7_harness_start_allowed",
    "phase7_qualified_setup_creation_allowed",
    "phase7_test_mode_auto_approval_allowed",
    "phase7_proof_order_staging_allowed",
    "phase7_proof_trade_submission_allowed",
    "phase7_proof_trade_execution_allowed",
    "phase7_proof_lifecycle_write_allowed",
    "phase7_postmortem_write_allowed",
    "phase7_performance_evaluation_write_allowed",
    "phase7_proof_credit_allowed",
    "phase7_live_promotion_review_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "manual_trade_level_override_allowed",
)

PHASE7_UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "paper_order_submitted_count",
    "proof_trade_created_count",
    "proof_trade_credit_count",
    "phase7_proof_credit_allowed_count",
    "manual_trade_level_override_count",
    "phase5_test_trade_reuse_count",
    "ui_inferred_readiness_count",
)

PHASE7_READINESS_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PHASE6_CERTIFICATION_RUNTIME_ARTIFACT}",
    "docs/qadam-phase-7-demo-proof-implementation-plan.md",
    "docs/qadam-master-implementation-plan.md",
)

PHASE7_READINESS_BOUNDARY = (
    "Q7-0 is a Phase 7 re-entry and operating-rules gate only. It can confirm "
    "Q6-17 certification and freeze the 30 consecutive calendar day demo-proof "
    "contract with three proof trades per proof week where qualified setups "
    "exist, but it cannot start the proof harness, cannot create qualified "
    "setups, cannot auto-approve trades, cannot stage or submit proof orders, "
    "cannot create proof trades, cannot grant Phase 7 proof credit, cannot "
    "reuse Phase 5 test trades as proof, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot write prediction-market or "
    "crypto-perps orders, cannot call live endpoints, cannot enable live "
    "capital, and cannot permit manual trade-level overrides."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _count(artifact: dict[str, Any], field: str) -> int:
    return int(artifact.get(field, 0) or 0)


def phase7_readiness_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_READINESS_RUNTIME_ARTIFACT,
        runtime / PHASE7_READINESS_HISTORY,
        runtime / PHASE7_READINESS_EVENT_LOG,
    )


def phase7_authority_defaults() -> dict[str, bool]:
    return {field: False for field in PHASE7_AUTHORITY_FLAGS}


def phase7_unsafe_counter_defaults() -> dict[str, int]:
    return {field: 0 for field in PHASE7_UNSAFE_COUNT_FIELDS}


def _authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_READINESS_SCHEMA_VERSION,
        "stage": "Q7-0",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "q7_1_artifact_schema_stage_allowed": True,
        **phase7_authority_defaults(),
        "boundary": PHASE7_READINESS_BOUNDARY,
    }


def _proof_contract() -> dict[str, Any]:
    return {
        "contract_schema_version": PHASE7_READINESS_SCHEMA_VERSION,
        "harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "consecutive_calendar_days_required": True,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "weekly_target_applies_only_where_qualified_setups_exist": True,
        "no_forced_trades": True,
        "qualified_setup_ledger_required": True,
        "weekly_target_formula": "min(3, qualified_setup_count)",
        "proof_week_definition": "days_1_7_8_14_15_21_22_28_and_partial_29_30",
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "phase5_test_trade_reuse_allowed": False,
        "q6_deferred_learning_counts_as_proof": False,
        "local_first_proof_storage_required": True,
        "manual_trade_level_override_allowed": False,
    }


def _provenance() -> dict[str, Any]:
    return {
        "source_refs": list(PHASE7_READINESS_SOURCE_REFS),
        "event_log_required": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "boundary": (
            "Q7-0 must be replayable from public-safe source refs and must not "
            "expose secrets, raw private payloads, local-only absolute paths, "
            "broker identifiers, or proof account credentials."
        ),
    }


def _source_posture() -> dict[str, Any]:
    return {
        "canonical_source_required": True,
        "supplemental_source_bypass_allowed": False,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_quorum_credit_allowed": False,
        "qctrl_role": "shadow_annotation_only",
        "private_world_model_role": "context_not_proof",
        "phase5_test_lifecycle_role": "excluded_from_phase7_proof",
        "phase6_deferred_learning_role": "context_not_proof",
    }


def _read_phase6_certification(settings: Settings) -> tuple[dict[str, Any], bool, list[str]]:
    cert_path, _, _ = phase6_certification_paths(settings)
    certification = _read_json(cert_path) or {}
    recorded = bool(certification)
    errors = validate_phase6_certification(certification) if recorded else ["phase6_certification_missing"]
    return certification, recorded, errors


def _unsafe_counts() -> dict[str, int]:
    return phase7_unsafe_counter_defaults()


def _blockers(
    *,
    certification: dict[str, Any],
    certification_recorded: bool,
    certification_errors: list[str],
    unsafe_counts: dict[str, int],
) -> list[str]:
    blockers: list[str] = []
    if not certification_recorded:
        blockers.append("phase6_certification_artifact_missing")
    if certification_errors:
        blockers.append("phase6_certification_validation_errors")
    if certification.get("status") != "certified":
        blockers.append("phase6_not_certified")
    if certification.get("stage_status") != "phase6_certified":
        blockers.append("phase6_stage_status_not_certified")
    if certification.get("phase6_certified") is not True:
        blockers.append("phase6_certified_not_true")
    if certification.get("phase6_exit_gate") is not True:
        blockers.append("phase6_exit_gate_not_true")
    if certification.get("phase7_demo_proof_planning_allowed") is not True:
        blockers.append("phase7_demo_proof_planning_not_allowed")
    if certification.get("phase7_proof_credit_allowed") is not False:
        blockers.append("phase7_proof_credit_already_allowed")
    if certification.get("phase5_test_trades_count_for_phase7") is not False:
        blockers.append("phase5_test_trades_count_for_phase7")
    if _count(certification, "certification_blocker_count") != 0:
        blockers.append("phase6_certification_blockers_present")
    if _count(certification, "input_gate_passed_count") != 17:
        blockers.append("phase6_input_gates_incomplete")
    if _count(certification, "input_gate_blocked_count") != 0:
        blockers.append("phase6_input_gates_blocked")
    if certification.get("learning_actions_review_satisfied") is not True:
        blockers.append("phase6_learning_actions_review_not_satisfied")
    if certification.get("reviewed_postmortem_coverage_satisfied") is not True:
        blockers.append("phase6_postmortem_coverage_not_satisfied")
    if certification.get("knowledge_graph_requirement_satisfied") is not True:
        blockers.append("phase6_knowledge_graph_requirement_not_satisfied")
    if certification.get("live_capital_enabled") is not False:
        blockers.append("live_capital_enabled")
    for field, value in unsafe_counts.items():
        if value != 0:
            blockers.append(f"unsafe_count_nonzero:{field}")
    return sorted(set(blockers))


def build_phase7_readiness(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    certification, certification_recorded, certification_errors = _read_phase6_certification(settings)
    unsafe_counts = _unsafe_counts()
    blockers = _blockers(
        certification=certification,
        certification_recorded=certification_recorded,
        certification_errors=certification_errors,
        unsafe_counts=unsafe_counts,
    )
    re_entry_gate_passed = not blockers
    artifact = {
        "schema_version": PHASE7_READINESS_SCHEMA_VERSION,
        "artifact_type": "phase7_readiness",
        "artifact_id": "phase7:q7-0:re-entry-operating-rules",
        "phase": "Q7",
        "stage": "Q7-0",
        "status": (
            "ready_for_q7_1_artifact_schema"
            if re_entry_gate_passed
            else "blocked_pending_phase6_certification"
        ),
        "readiness_state": (
            "phase7_demo_proof_re_entry_gate_passed"
            if re_entry_gate_passed
            else "phase7_demo_proof_re_entry_gate_blocked"
        ),
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(),
        "proof_contract": _proof_contract(),
        "source_posture": _source_posture(),
        "provenance": _provenance(),
        "boundary": PHASE7_READINESS_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        "phase6_certification_artifact_recorded": certification_recorded,
        "phase6_certification_validation_error_count": len(certification_errors),
        "phase6_certification_status": str(certification.get("status") or "missing"),
        "phase6_certification_stage_status": str(certification.get("stage_status") or "missing"),
        "phase6_certified": certification.get("phase6_certified") is True,
        "phase6_exit_gate": certification.get("phase6_exit_gate") is True,
        "phase6_input_gate_passed_count": _count(certification, "input_gate_passed_count"),
        "phase6_input_gate_blocked_count": _count(certification, "input_gate_blocked_count"),
        "phase6_certification_blocker_count": _count(certification, "certification_blocker_count"),
        "phase6_learning_approval_state": str(certification.get("approval_state") or "missing"),
        "phase6_reviewed_postmortem_coverage_satisfied": (
            certification.get("reviewed_postmortem_coverage_satisfied") is True
        ),
        "phase6_learning_actions_review_satisfied": (
            certification.get("learning_actions_review_satisfied") is True
        ),
        "phase6_knowledge_graph_requirement_satisfied": (
            certification.get("knowledge_graph_requirement_satisfied") is True
        ),
        "phase7_demo_proof_planning_allowed": (
            certification.get("phase7_demo_proof_planning_allowed") is True
        ),
        "phase7_proof_credit_allowed": (
            certification.get("phase7_proof_credit_allowed") is True
        ),
        "phase5_test_trades_count_for_phase7": (
            certification.get("phase5_test_trades_count_for_phase7") is True
        ),
        "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "phase7_consecutive_calendar_days_required": True,
        "phase7_weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "phase7_weekly_target_applies_only_where_qualified_setups_exist": True,
        "phase7_no_forced_trades": True,
        "phase7_qualified_setup_ledger_required": True,
        "phase7_weekly_target_formula": "min(3, qualified_setup_count)",
        "phase7_paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "phase7_max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "phase7_mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "phase7_statistical_immaturity_allowed": True,
        "phase7_local_first_proof_storage_required": True,
        "phase7_harness_started": False,
        "phase7_demo_day_count": 0,
        "phase7_qualified_setup_count": 0,
        "phase7_proof_trade_count": 0,
        "phase7_closed_proof_trade_count": 0,
        "phase7_re_entry_gate_passed": re_entry_gate_passed,
        "q7_1_artifact_schema_stage_allowed": re_entry_gate_passed,
        "phase7_controlled_stage_work_allowed": re_entry_gate_passed,
        "phase7_frozen_scope": deepcopy(list(PHASE7_STAGE_SCOPE)),
        "phase7_frozen_scope_count": len(PHASE7_STAGE_SCOPE),
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-1 Artifact Schema And Proof Authority Ledger",
    }
    artifact["validation_errors"] = validate_phase7_readiness(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_phase7_readiness(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "readiness_state",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "boundary",
        "phase6_certification_artifact_recorded",
        "phase6_certification_validation_error_count",
        "phase6_certification_status",
        "phase6_certification_stage_status",
        "phase6_certified",
        "phase6_exit_gate",
        "phase7_demo_proof_planning_allowed",
        "phase7_proof_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "phase7_harness_day_count",
        "phase7_weekly_proof_trade_target",
        "phase7_no_forced_trades",
        "phase7_re_entry_gate_passed",
        "q7_1_artifact_schema_stage_allowed",
        "phase7_controlled_stage_work_allowed",
        "phase7_frozen_scope",
        "phase7_frozen_scope_count",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_readiness_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_READINESS_SCHEMA_VERSION:
        errors.append("phase7_readiness_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_readiness":
        errors.append("phase7_readiness_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-0":
        errors.append("phase7_readiness_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_readiness_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_readiness_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_readiness_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_readiness_blocker_count_mismatch")
    if artifact.get("phase7_frozen_scope_count") != len(artifact.get("phase7_frozen_scope", [])):
        errors.append("phase7_readiness_scope_count_mismatch")
    if artifact.get("phase7_frozen_scope_count") != len(PHASE7_STAGE_SCOPE):
        errors.append("phase7_readiness_scope_incomplete")
    stage_names = {
        record.get("stage")
        for record in artifact.get("phase7_frozen_scope", [])
        if isinstance(record, dict)
    }
    if stage_names != {record["stage"] for record in PHASE7_STAGE_SCOPE}:
        errors.append("phase7_readiness_scope_stage_mismatch")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_readiness_authority_enabled:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"phase7_readiness_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_readiness_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_readiness_unsafe_total_nonzero")
    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_readiness_harness_day_count_mismatch")
    if artifact.get("phase7_consecutive_calendar_days_required") is not True:
        errors.append("phase7_readiness_consecutive_days_not_required")
    if artifact.get("phase7_weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("phase7_readiness_weekly_target_mismatch")
    if artifact.get("phase7_weekly_target_applies_only_where_qualified_setups_exist") is not True:
        errors.append("phase7_readiness_weekly_target_forces_trades")
    if artifact.get("phase7_no_forced_trades") is not True:
        errors.append("phase7_readiness_forced_trades_allowed")
    if artifact.get("phase7_qualified_setup_ledger_required") is not True:
        errors.append("phase7_readiness_qualified_setup_ledger_not_required")
    if artifact.get("phase7_weekly_target_formula") != "min(3, qualified_setup_count)":
        errors.append("phase7_readiness_weekly_target_formula_invalid")
    if float(artifact.get("phase7_paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_readiness_paper_account_starting_balance_invalid")
    if float(artifact.get("phase7_max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_readiness_drawdown_cap_invalid")
    if artifact.get("phase7_mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_readiness_mature_benchmark_mismatch")
    if artifact.get("phase7_statistical_immaturity_allowed") is not True:
        errors.append("phase7_readiness_statistical_immaturity_not_allowed")
    if artifact.get("phase7_local_first_proof_storage_required") is not True:
        errors.append("phase7_readiness_local_first_storage_not_required")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("phase7_harness_started") is not False:
        errors.append("phase7_readiness_harness_started")
    for field in (
        "phase7_demo_day_count",
        "phase7_qualified_setup_count",
        "phase7_proof_trade_count",
        "phase7_closed_proof_trade_count",
    ):
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"phase7_readiness_premature_count:{field}")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_readiness_proof_contract_missing")
        proof_contract = {}
    contract_checks = {
        "harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    }
    for field, expected in contract_checks.items():
        if proof_contract.get(field) != expected:
            errors.append(f"phase7_readiness_contract_mismatch:{field}")
    for field in (
        "consecutive_calendar_days_required",
        "weekly_target_applies_only_where_qualified_setups_exist",
        "no_forced_trades",
        "qualified_setup_ledger_required",
        "statistical_immaturity_allowed",
        "local_first_proof_storage_required",
    ):
        if proof_contract.get(field) is not True:
            errors.append(f"phase7_readiness_contract_missing_true:{field}")
    for field in (
        "phase5_test_trade_reuse_allowed",
        "q6_deferred_learning_counts_as_proof",
        "manual_trade_level_override_allowed",
    ):
        if proof_contract.get(field) is not False:
            errors.append(f"phase7_readiness_contract_forbidden:{field}")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_readiness_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        if str(ref).startswith("/"):
            errors.append("phase7_readiness_local_path_leak")
            break
    for field in ("raw_secret_exposed", "raw_payload_exposed", "local_path_exposed"):
        if provenance.get(field) is not False:
            errors.append(f"phase7_readiness_provenance_unsafe:{field}")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_readiness_source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("phase7_readiness_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_readiness_preference_quorum_credit_allowed")
    if source_posture.get("private_world_model_role") != "context_not_proof":
        errors.append("phase7_readiness_world_model_role_invalid")
    gate_passed = artifact.get("phase7_re_entry_gate_passed") is True
    if gate_passed:
        if artifact.get("status") != "ready_for_q7_1_artifact_schema":
            errors.append("phase7_readiness_status_not_ready")
        if artifact.get("readiness_state") != "phase7_demo_proof_re_entry_gate_passed":
            errors.append("phase7_readiness_state_not_passed")
        if blockers:
            errors.append("phase7_readiness_passed_with_blockers")
        for field in (
            "phase6_certification_artifact_recorded",
            "phase6_certified",
            "phase6_exit_gate",
            "phase7_demo_proof_planning_allowed",
            "phase6_reviewed_postmortem_coverage_satisfied",
            "phase6_learning_actions_review_satisfied",
            "phase6_knowledge_graph_requirement_satisfied",
            "q7_1_artifact_schema_stage_allowed",
            "phase7_controlled_stage_work_allowed",
        ):
            if artifact.get(field) is not True:
                errors.append(f"phase7_readiness_passed_missing_true:{field}")
        if artifact.get("phase6_certification_status") != "certified":
            errors.append("phase7_readiness_phase6_status_not_certified")
        if artifact.get("phase6_certification_stage_status") != "phase6_certified":
            errors.append("phase7_readiness_phase6_stage_status_invalid")
        if int(artifact.get("phase6_certification_validation_error_count", 0) or 0) != 0:
            errors.append("phase7_readiness_phase6_validation_errors")
        if int(artifact.get("phase6_certification_blocker_count", 0) or 0) != 0:
            errors.append("phase7_readiness_phase6_blockers")
        if int(artifact.get("phase6_input_gate_passed_count", 0) or 0) != 17:
            errors.append("phase7_readiness_phase6_input_gates_incomplete")
        if int(artifact.get("phase6_input_gate_blocked_count", 0) or 0) != 0:
            errors.append("phase7_readiness_phase6_input_gates_blocked")
    else:
        if artifact.get("status") != "blocked_pending_phase6_certification":
            errors.append("phase7_readiness_blocked_status_mismatch")
        if artifact.get("readiness_state") != "phase7_demo_proof_re_entry_gate_blocked":
            errors.append("phase7_readiness_blocked_state_mismatch")
        if not blockers:
            errors.append("phase7_readiness_blocked_without_blockers")
        if artifact.get("q7_1_artifact_schema_stage_allowed") is not False:
            errors.append("phase7_readiness_q7_1_allowed_while_blocked")
        if artifact.get("phase7_controlled_stage_work_allowed") is not False:
            errors.append("phase7_readiness_controlled_work_allowed_while_blocked")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "30 consecutive calendar day",
        "three proof trades per proof week where qualified setups exist",
        "cannot start the proof harness",
        "cannot create proof trades",
        "cannot grant Phase 7 proof credit",
        "cannot reuse Phase 5 test trades as proof",
        "cannot enable live capital",
        "cannot permit manual trade-level overrides",
    ):
        if phrase not in boundary:
            errors.append("phase7_readiness_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_readiness_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("phase7_readiness_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_readiness_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_readiness_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_READINESS_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_READINESS_EVENT_TYPE,
        PHASE7_READINESS_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "readiness_state": output.get("readiness_state"),
            "phase7_re_entry_gate_passed": output.get("phase7_re_entry_gate_passed"),
            "phase7_harness_day_count": output.get("phase7_harness_day_count"),
            "phase7_weekly_proof_trade_target": output.get(
                "phase7_weekly_proof_trade_target"
            ),
            "phase7_no_forced_trades": output.get("phase7_no_forced_trades"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase7_readiness(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase7_readiness(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_readiness_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_readiness_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_readiness(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_readiness(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE7_READINESS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "readiness_state": output.get("readiness_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase7_re_entry_gate_passed": output.get("phase7_re_entry_gate_passed"),
        "phase7_harness_day_count": output.get("phase7_harness_day_count"),
        "phase7_weekly_proof_trade_target": output.get("phase7_weekly_proof_trade_target"),
        "phase7_no_forced_trades": output.get("phase7_no_forced_trades"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "phase5_test_trades_count_for_phase7": output.get(
            "phase5_test_trades_count_for_phase7"
        ),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
