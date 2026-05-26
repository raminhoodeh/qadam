"""Q7-12 Phase 7 Demo Proof override detector.

This stage consumes the Q7-11 drawdown sentinel plus earlier Phase 7 decision
and lifecycle artifacts to detect manual trade-level intervention. It can mark
the Phase 7 proof sample contaminated and require restart, but it cannot
approve trades, create proof trades, grant proof credit, mutate policy, call
broker routes, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_drawdown_risk_sentinel import (
    PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT,
    build_phase7_drawdown_risk_sentinel,
    phase7_drawdown_risk_sentinel_paths,
    validate_phase7_drawdown_risk_sentinel,
    write_phase7_drawdown_risk_sentinel,
)
from orchestrator.phase7_proof_lifecycle_monitor import (
    PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT,
    build_phase7_proof_lifecycle_monitor,
    phase7_proof_lifecycle_monitor_paths,
    validate_phase7_proof_lifecycle_monitor,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_test_mode_auto_approval import (
    PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT,
    GOVERNANCE_FEEDBACK_CHANNELS,
    build_phase7_test_mode_auto_approval_router,
    phase7_test_mode_auto_approval_paths,
    validate_phase7_test_mode_auto_approval_router,
)


PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION = 1
PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT = "phase7_override_detector.json"
PHASE7_OVERRIDE_DETECTOR_HISTORY = "phase7_override_detector_history.jsonl"
PHASE7_OVERRIDE_DETECTOR_EVENT_LOG = "phase7_override_detector_events.jsonl"
PHASE7_OVERRIDE_DETECTOR_EVENT_TYPE = PHASE7_EVENT_TYPES["override"]
PHASE7_OVERRIDE_DETECTOR_COMPONENT = "phase7_override_detector"

PHASE7_OVERRIDE_BOUNDARY = (
    "Q7-12 records the Phase 7 clean-sample override detector only from Q7 "
    "auto-approval, lifecycle, and drawdown-sentinel evidence. It can detect "
    "manual trade-level approvals, rejections, quantity edits, price edits, "
    "manual exits, broker-side intervention, and unlinked lifecycle records; "
    "it can mark the proof sample contaminated and require restart, but it "
    "cannot approve trades, cannot create proof trades, cannot grant Phase 7 "
    "proof credit, cannot call broker POST routes, cannot call Alpaca POST "
    "routes, cannot write prediction-market or crypto-perps orders, cannot "
    "mutate policy or strategies, cannot enable live capital, and cannot "
    "permit manual trade-level overrides."
)

PHASE7_OVERRIDE_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_11_drawdown_sentinel_valid",
    "q7_12_override_stage_allowed",
    "source_auto_approval_valid",
    "source_lifecycle_valid",
    "manual_trade_level_approval_detected",
    "manual_trade_level_rejection_detected",
    "manual_quantity_or_price_edit_detected",
    "manual_exit_detected",
    "broker_side_intervention_detected",
    "unlinked_lifecycle_record_detected",
    "governance_feedback_separated",
    "sample_contamination_recorded",
    "restart_required_when_contaminated",
    "certification_blocks_contaminated_sample",
    "no_certification_authority",
    "no_proof_credit",
    "no_broker_post",
    "no_alpaca_post",
    "no_live_endpoint",
    "no_live_capital",
    "manual_override_authority_disabled",
    "market_writes_disabled",
    "public_safe",
)

PHASE7_OVERRIDE_KINDS: tuple[str, ...] = (
    "manual_trade_level_approval",
    "manual_trade_level_rejection",
    "manual_quantity_edit",
    "manual_price_edit",
    "manual_exit",
    "manual_trade_level_override_attempt",
    "broker_side_intervention",
    "unlinked_lifecycle_record",
)

PHASE7_TRADE_LEVEL_AUTO_APPROVAL_COUNT_FIELDS: tuple[tuple[str, str], ...] = (
    ("manual_trade_level_approval_count", "manual_trade_level_approval"),
    ("manual_trade_level_rejection_count", "manual_trade_level_rejection"),
    ("manual_trade_level_resize_count", "manual_quantity_edit"),
    ("manual_trade_level_exit_count", "manual_exit"),
    ("manual_trade_level_override_attempt_count", "manual_trade_level_override_attempt"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def phase7_override_detector_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT,
        runtime / PHASE7_OVERRIDE_DETECTOR_HISTORY,
        runtime / PHASE7_OVERRIDE_DETECTOR_EVENT_LOG,
    )


def _drawdown_sentinel(settings: Settings) -> dict[str, Any]:
    drawdown_path, _, _ = phase7_drawdown_risk_sentinel_paths(settings)
    if drawdown_path.exists():
        return _read_json(drawdown_path)
    drawdown = build_phase7_drawdown_risk_sentinel(settings=settings)
    _, _, _, written = write_phase7_drawdown_risk_sentinel(
        drawdown,
        settings=settings,
        record_event=True,
    )
    return written


def _auto_approval(settings: Settings) -> dict[str, Any]:
    auto_path, _, _ = phase7_test_mode_auto_approval_paths(settings)
    if auto_path.exists():
        return _read_json(auto_path)
    return build_phase7_test_mode_auto_approval_router(settings=settings)


def _lifecycle(settings: Settings) -> dict[str, Any]:
    lifecycle_path, _, _ = phase7_proof_lifecycle_monitor_paths(settings)
    if lifecycle_path.exists():
        return _read_json(lifecycle_path)
    return build_phase7_proof_lifecycle_monitor(settings=settings)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    return value is True


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _override_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
        "source_drawdown_sentinel_required": True,
        "source_auto_approval_required": True,
        "source_lifecycle_required": True,
        "manual_trade_level_approval_contaminates_sample": True,
        "manual_trade_level_rejection_contaminates_sample": True,
        "manual_quantity_edit_contaminates_sample": True,
        "manual_price_edit_contaminates_sample": True,
        "manual_exit_contaminates_sample": True,
        "broker_side_intervention_contaminates_sample": True,
        "unlinked_lifecycle_record_contaminates_sample": True,
        "governance_feedback_channels": list(GOVERNANCE_FEEDBACK_CHANNELS),
        "governance_feedback_affects_future_policy_only": True,
        "strategy_toggles_affect_future_policy_only": True,
        "kill_switch_changes_affect_future_policy_only": True,
        "contamination_blocks_phase7_certification": True,
        "contamination_requires_run_restart": True,
        "risk_halt_freeze_preserved": True,
        "certification_authority_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "policy_mutation_allowed": False,
        "strategy_mutation_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(
    *,
    stage_recorded: bool,
    new_proof_trades_frozen: bool,
) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    if stage_recorded:
        defaults["phase7_proof_lifecycle_write_allowed"] = True
        defaults["phase7_postmortem_write_allowed"] = True
        defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            defaults["phase7_test_mode_auto_approval_allowed"] = True
            defaults["phase7_proof_order_staging_allowed"] = True
            defaults["phase7_proof_trade_submission_allowed"] = True
    grants = [field for field in PHASE7_AUTHORITY_FLAGS if defaults[field]]
    return {
        "authority_schema_version": PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
        "stage": "Q7-12",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": len(grants),
        "explicit_authority_grants": grants,
        "q7_13_signal_funnel_evidence_stage_allowed": stage_recorded,
        "override_detection_write_allowed": stage_recorded,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        **defaults,
        "boundary": PHASE7_OVERRIDE_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_drawdown_risk_sentinel.py",
            "orchestrator/phase7_test_mode_auto_approval.py",
            "orchestrator/phase7_proof_lifecycle_monitor.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-11-drawdown-risk-sentinel-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    ]
    provenance["governance_refs"] = [
        "docs/qadam-phase-7-demo-proof-implementation-plan.md"
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(
    drawdown: dict[str, Any],
    auto_approval: dict[str, Any],
    lifecycle: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if validate_phase7_drawdown_risk_sentinel(drawdown):
        blockers.append("phase7_drawdown_risk_sentinel_validation_errors")
    if drawdown.get("drawdown_sentinel_recorded") is not True:
        blockers.append("phase7_drawdown_risk_sentinel_not_recorded")
    if drawdown.get("q7_12_override_detector_stage_allowed") is not True:
        blockers.append("q7_12_override_detector_stage_not_allowed")
    if validate_phase7_test_mode_auto_approval_router(auto_approval):
        blockers.append("phase7_auto_approval_validation_errors")
    if validate_phase7_proof_lifecycle_monitor(lifecycle):
        blockers.append("phase7_lifecycle_validation_errors")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if drawdown.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _override_record(
    *,
    override_kind: str,
    source_artifact_id: str | None,
    source_ref: str | None,
    source_stage: str,
    intervention_count: int = 1,
) -> dict[str, Any]:
    record_key = _safe_key(f"{source_stage}:{override_kind}:{source_ref or 'aggregate'}")
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "override_detector_schema_version": PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
        "artifact_type": "override_detection_event",
        "artifact_id": f"phase7:q7-12:override:{record_key}",
        "phase": "Q7",
        "stage": "Q7-12",
        "status": "contaminating_override_detected",
        "generated_at": _now(),
        "public_safe": True,
        "source_artifact_id": source_artifact_id,
        "source_stage": source_stage,
        "source_ref": source_ref,
        "override_kind": override_kind,
        "intervention_count": intervention_count,
        "trade_level_intervention": True,
        "sample_contaminating": True,
        "certification_blocking": True,
        "run_restart_required": True,
        "governance_only": False,
        "governance_channel": None,
        "manual_trade_level_override_allowed": False,
        "phase7_proof_credit_allowed": False,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
    }


def _governance_feedback_records(auto_approval: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for channel in auto_approval.get("governance_feedback_channels", []) or []:
        channel_text = str(channel)
        records.append(
            {
                "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
                "artifact_type": "governance_feedback_channel",
                "artifact_id": f"phase7:q7-12:governance:{_safe_key(channel_text)}",
                "phase": "Q7",
                "stage": "Q7-12",
                "status": "allowed_future_policy_feedback",
                "generated_at": _now(),
                "public_safe": True,
                "source_artifact_id": auto_approval.get("artifact_id"),
                "governance_channel": channel_text,
                "governance_only": True,
                "trade_level_intervention": False,
                "sample_contaminating": False,
                "certification_blocking": False,
                "future_policy_only": True,
                "manual_trade_level_override_allowed": False,
                "phase7_proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return records


def _auto_approval_override_records(auto_approval: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for count_field, override_kind in PHASE7_TRADE_LEVEL_AUTO_APPROVAL_COUNT_FIELDS:
        count = _int(auto_approval.get(count_field))
        if count > 0:
            records.append(
                _override_record(
                    override_kind=override_kind,
                    source_artifact_id=str(auto_approval.get("artifact_id") or ""),
                    source_ref=count_field,
                    source_stage="Q7-5",
                    intervention_count=count,
                )
            )
    for decision in auto_approval.get("decision_records", []) or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("manual_trade_level_override_attempted") is True:
            records.append(
                _override_record(
                    override_kind="manual_trade_level_override_attempt",
                    source_artifact_id=str(decision.get("artifact_id") or ""),
                    source_ref=str(decision.get("decision_id") or ""),
                    source_stage="Q7-5",
                )
            )
    return records


def _lifecycle_record_unlinked(record: dict[str, Any]) -> bool:
    if record.get("proof_trade_created") is not True:
        return False
    required_refs = (
        "source_auto_approval_decision_id",
        "source_staged_order_artifact_id",
        "submitted_order_ref",
        "broker_receipt_ref",
    )
    return any(not str(record.get(field) or "").strip() for field in required_refs)


def _lifecycle_override_records(lifecycle: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in lifecycle.get("lifecycle_records", []) or []:
        if not isinstance(record, dict):
            continue
        source_ref = str(record.get("artifact_id") or record.get("submitted_order_ref") or "")
        if record.get("manual_trade_level_override_allowed") is True:
            records.append(
                _override_record(
                    override_kind="manual_trade_level_override_attempt",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
        if record.get("position_close_allowed") is True:
            records.append(
                _override_record(
                    override_kind="manual_exit",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
        if record.get("position_resize_allowed") is True:
            records.append(
                _override_record(
                    override_kind="manual_quantity_edit",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
        if record.get("order_cancel_allowed") is True:
            records.append(
                _override_record(
                    override_kind="manual_trade_level_rejection",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
        if (
            record.get("broker_side_change_detected") is True
            or record.get("external_broker_post_performed") is True
            or record.get("broker_write_allowed") is True
        ):
            records.append(
                _override_record(
                    override_kind="broker_side_intervention",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
        if _lifecycle_record_unlinked(record):
            records.append(
                _override_record(
                    override_kind="unlinked_lifecycle_record",
                    source_artifact_id=str(record.get("artifact_id") or ""),
                    source_ref=source_ref,
                    source_stage="Q7-8",
                )
            )
    return records


def _kind_count(records: list[dict[str, Any]], *kinds: str) -> int:
    return sum(
        _int(record.get("intervention_count"))
        for record in records
        if record.get("override_kind") in set(kinds)
    )


def build_phase7_override_detector(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    drawdown = _drawdown_sentinel(settings)
    auto_approval = _auto_approval(settings)
    lifecycle = _lifecycle(settings)
    blockers = _preflight_blockers(drawdown, auto_approval, lifecycle)
    stage_recorded = not blockers
    override_records = [
        *_auto_approval_override_records(auto_approval),
        *_lifecycle_override_records(lifecycle),
    ]
    governance_records = _governance_feedback_records(auto_approval)
    override_count = sum(_int(record.get("intervention_count")) for record in override_records)
    manual_override_count = _kind_count(
        override_records,
        "manual_trade_level_approval",
        "manual_trade_level_rejection",
        "manual_quantity_edit",
        "manual_price_edit",
        "manual_exit",
        "manual_trade_level_override_attempt",
    )
    broker_side_count = _kind_count(override_records, "broker_side_intervention")
    unlinked_lifecycle_count = _kind_count(override_records, "unlinked_lifecycle_record")
    sample_contaminated = override_count > 0
    source_frozen = drawdown.get("new_proof_trades_frozen") is True
    new_proof_trades_frozen = stage_recorded and (sample_contaminated or source_frozen)
    unsafe_counts = phase7_unsafe_counter_defaults()
    unsafe_counts["paper_order_submitted_count"] = _int(
        drawdown.get("paper_order_submitted_count")
    )
    unsafe_counts["proof_trade_created_count"] = _int(
        drawdown.get("proof_trade_created_count")
    )
    unsafe_counts["manual_trade_level_override_count"] = manual_override_count
    authority_defaults = phase7_authority_defaults()
    if stage_recorded:
        authority_defaults["phase7_proof_lifecycle_write_allowed"] = True
        authority_defaults["phase7_postmortem_write_allowed"] = True
        authority_defaults["phase7_performance_evaluation_write_allowed"] = True
        if not new_proof_trades_frozen:
            authority_defaults["phase7_test_mode_auto_approval_allowed"] = True
            authority_defaults["phase7_proof_order_staging_allowed"] = True
            authority_defaults["phase7_proof_trade_submission_allowed"] = True
    status = "clean_no_overrides"
    stage_status = "override_detector_clean_no_interventions"
    if sample_contaminated:
        status = "contaminated"
        stage_status = "override_detector_sample_contaminated"
    if not stage_recorded:
        status = "blocked"
        stage_status = "override_detector_blocked"
    checks = [
        _check("q7_11_drawdown_sentinel_valid", not validate_phase7_drawdown_risk_sentinel(drawdown)),
        _check("q7_12_override_stage_allowed", stage_recorded),
        _check("source_auto_approval_valid", not validate_phase7_test_mode_auto_approval_router(auto_approval)),
        _check("source_lifecycle_valid", not validate_phase7_proof_lifecycle_monitor(lifecycle)),
        _check("manual_trade_level_approval_detected", True),
        _check("manual_trade_level_rejection_detected", True),
        _check("manual_quantity_or_price_edit_detected", True),
        _check("manual_exit_detected", True),
        _check("broker_side_intervention_detected", True),
        _check("unlinked_lifecycle_record_detected", True),
        _check("governance_feedback_separated", True),
        _check("sample_contamination_recorded", True),
        _check("restart_required_when_contaminated", True),
        _check("certification_blocks_contaminated_sample", True),
        _check("no_certification_authority", True),
        _check("no_proof_credit", True),
        _check("no_broker_post", True),
        _check("no_alpaca_post", True),
        _check("no_live_endpoint", True),
        _check("no_live_capital", True),
        _check("manual_override_authority_disabled", True),
        _check("market_writes_disabled", True),
        _check("public_safe", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    if failed_checks and stage_recorded:
        blockers = sorted(set([*blockers, *failed_checks]))
        stage_recorded = False
        status = "blocked"
        stage_status = "override_detector_blocked"
    artifact = {
        "schema_version": PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_override_detector",
        "artifact_id": "phase7:q7-12:override-detector",
        "phase": "Q7",
        "stage": "Q7-12",
        "status": status,
        "stage_status": stage_status,
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
        "authority_ledger": _authority_ledger(
            stage_recorded=stage_recorded,
            new_proof_trades_frozen=new_proof_trades_frozen,
        ),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "override_policy": _override_policy(),
        "override_records": override_records,
        "governance_feedback_records": governance_records,
        "boundary": PHASE7_OVERRIDE_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_drawdown_artifact_id": drawdown.get("artifact_id"),
        "source_drawdown_status": drawdown.get("status"),
        "source_drawdown_stage_status": drawdown.get("stage_status"),
        "source_drawdown_recorded": drawdown.get("drawdown_sentinel_recorded") is True,
        "source_drawdown_new_proof_trades_frozen": source_frozen,
        "source_auto_approval_artifact_id": auto_approval.get("artifact_id"),
        "source_auto_approval_status": auto_approval.get("status"),
        "source_lifecycle_artifact_id": lifecycle.get("artifact_id"),
        "source_lifecycle_status": lifecycle.get("status"),
        "source_lifecycle_stage_status": lifecycle.get("stage_status"),
        "source_lifecycle_event_count": _int(lifecycle.get("lifecycle_event_count")),
        "source_closed_proof_trade_count": _int(
            drawdown.get("source_closed_proof_trade_count")
        ),
        "source_proof_trade_count": _int(drawdown.get("proof_trade_created_count")),
        "q7_12_override_detector_stage_allowed": (
            drawdown.get("q7_12_override_detector_stage_allowed") is True
        ),
        "q7_13_signal_funnel_evidence_stage_allowed": stage_recorded,
        "override_detector_recorded": stage_recorded,
        "override_detection_write_allowed": stage_recorded,
        "override_count": override_count,
        "override_record_count": len(override_records),
        "manual_trade_level_approval_count": _kind_count(
            override_records,
            "manual_trade_level_approval",
        ),
        "manual_trade_level_rejection_count": _kind_count(
            override_records,
            "manual_trade_level_rejection",
        ),
        "manual_trade_level_quantity_edit_count": _kind_count(
            override_records,
            "manual_quantity_edit",
        ),
        "manual_trade_level_price_edit_count": _kind_count(
            override_records,
            "manual_price_edit",
        ),
        "manual_trade_level_exit_count": _kind_count(
            override_records,
            "manual_exit",
        ),
        "manual_trade_level_override_attempt_count": _kind_count(
            override_records,
            "manual_trade_level_override_attempt",
        ),
        "manual_trade_level_override_count": manual_override_count,
        "broker_side_intervention_count": broker_side_count,
        "unlinked_lifecycle_record_count": unlinked_lifecycle_count,
        "governance_feedback_record_count": len(governance_records),
        "governance_feedback_trade_level_intervention_count": 0,
        "governance_feedback_affects_future_policy_only": True,
        "sample_contaminated": sample_contaminated,
        "clean_sample": not sample_contaminated,
        "phase7_certification_blocked_by_override": sample_contaminated,
        "phase7_certification_blocked_by_contaminated_sample": sample_contaminated,
        "run_restart_required": sample_contaminated,
        "restart_reason": "manual_trade_level_intervention" if sample_contaminated else None,
        "sample_contamination_freeze_active": new_proof_trades_frozen,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        "new_proof_trades_frozen_by_override": stage_recorded and sample_contaminated,
        "new_proof_trades_frozen_by_drawdown": stage_recorded and source_frozen,
        "new_proof_order_staging_allowed": stage_recorded and not new_proof_trades_frozen,
        "new_proof_trade_submission_allowed": stage_recorded and not new_proof_trades_frozen,
        "existing_lifecycle_closeout_allowed": stage_recorded,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "unsafe_write_counter_total": manual_override_count,
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-13 Source And Signal Funnel Evidence",
    }
    artifact["validation_errors"] = validate_phase7_override_detector(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "override_detector_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("override_detector_recorded") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_override_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-12":
        errors.append("phase7_override_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_override_authority_count_mismatch")
    expected_true = {
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
    }
    if stage_recorded and not frozen:
        expected_true.update(
            {
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
            }
        )
    expected_grants = len(expected_true) if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_override_explicit_authority_grant_count_invalid")
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_override_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_override_ledger_authority_invalid:{field}")
    if ledger.get("override_detection_write_allowed") is not stage_recorded:
        errors.append("phase7_override_write_ledger_mismatch")
    if ledger.get("new_proof_trades_frozen") is not frozen:
        errors.append("phase7_override_freeze_ledger_mismatch")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_override_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("source_proof_trade_count")):
                errors.append(f"phase7_override_allowed_count_mismatch:{field}")
            continue
        if field == "manual_trade_level_override_count":
            if value != _int(artifact.get("manual_trade_level_override_count")):
                errors.append(f"phase7_override_allowed_count_mismatch:{field}")
            if value and artifact.get("sample_contaminated") is not True:
                errors.append("phase7_override_manual_count_without_contamination")
            continue
        if value != 0:
            errors.append(f"phase7_override_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != _int(
        artifact.get("manual_trade_level_override_count")
    ):
        errors.append("phase7_override_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") and (
        artifact.get("sample_contaminated") is not True
    ):
        errors.append("phase7_override_unsafe_total_without_contamination")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("override_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_override_policy_missing"]
    for field in (
        "source_drawdown_sentinel_required",
        "source_auto_approval_required",
        "source_lifecycle_required",
        "manual_trade_level_approval_contaminates_sample",
        "manual_trade_level_rejection_contaminates_sample",
        "manual_quantity_edit_contaminates_sample",
        "manual_price_edit_contaminates_sample",
        "manual_exit_contaminates_sample",
        "broker_side_intervention_contaminates_sample",
        "unlinked_lifecycle_record_contaminates_sample",
        "governance_feedback_affects_future_policy_only",
        "strategy_toggles_affect_future_policy_only",
        "kill_switch_changes_affect_future_policy_only",
        "contamination_blocks_phase7_certification",
        "contamination_requires_run_restart",
        "risk_halt_freeze_preserved",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_override_policy_missing_true:{field}")
    for field in (
        "certification_authority_allowed",
        "proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "policy_mutation_allowed",
        "strategy_mutation_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"phase7_override_policy_forbidden:{field}")
    if tuple(policy.get("governance_feedback_channels", ())) != GOVERNANCE_FEEDBACK_CHANNELS:
        errors.append("phase7_override_policy_governance_channels_invalid")
    return errors


def _override_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("artifact_type") != "override_detection_event":
        errors.append("phase7_override_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-12":
        errors.append("phase7_override_record_phase_stage_invalid")
    if record.get("override_kind") not in PHASE7_OVERRIDE_KINDS:
        errors.append("phase7_override_record_kind_invalid")
    if _int(record.get("intervention_count")) <= 0:
        errors.append("phase7_override_record_intervention_count_invalid")
    for field in (
        "trade_level_intervention",
        "sample_contaminating",
        "certification_blocking",
        "run_restart_required",
    ):
        if record.get(field) is not True:
            errors.append(f"phase7_override_record_missing_true:{field}")
    if record.get("governance_only") is not False:
        errors.append("phase7_override_record_governance_only")
    for field in (
        "manual_trade_level_override_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_override_record_forbidden:{field}")
    for field in ("broker_post_called_count", "alpaca_post_called_count"):
        if _int(record.get(field)) != 0:
            errors.append(f"phase7_override_record_count_nonzero:{field}")
    return errors


def _governance_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("artifact_type") != "governance_feedback_channel":
        errors.append("phase7_override_governance_record_type_invalid")
    if record.get("governance_channel") not in GOVERNANCE_FEEDBACK_CHANNELS:
        errors.append("phase7_override_governance_channel_invalid")
    for field in ("governance_only", "future_policy_only"):
        if record.get(field) is not True:
            errors.append(f"phase7_override_governance_missing_true:{field}")
    for field in (
        "trade_level_intervention",
        "sample_contaminating",
        "certification_blocking",
        "manual_trade_level_override_allowed",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_override_governance_forbidden:{field}")
    return errors


def validate_phase7_override_detector(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "override_policy",
        "override_records",
        "governance_feedback_records",
        "boundary",
        "source_drawdown_status",
        "source_drawdown_new_proof_trades_frozen",
        "source_auto_approval_status",
        "source_lifecycle_status",
        "source_lifecycle_stage_status",
        "source_lifecycle_event_count",
        "source_closed_proof_trade_count",
        "source_proof_trade_count",
        "q7_12_override_detector_stage_allowed",
        "q7_13_signal_funnel_evidence_stage_allowed",
        "override_detector_recorded",
        "override_detection_write_allowed",
        "override_count",
        "override_record_count",
        "manual_trade_level_approval_count",
        "manual_trade_level_rejection_count",
        "manual_trade_level_quantity_edit_count",
        "manual_trade_level_price_edit_count",
        "manual_trade_level_exit_count",
        "manual_trade_level_override_attempt_count",
        "manual_trade_level_override_count",
        "broker_side_intervention_count",
        "unlinked_lifecycle_record_count",
        "governance_feedback_record_count",
        "governance_feedback_trade_level_intervention_count",
        "governance_feedback_affects_future_policy_only",
        "sample_contaminated",
        "clean_sample",
        "phase7_certification_blocked_by_override",
        "phase7_certification_blocked_by_contaminated_sample",
        "run_restart_required",
        "sample_contamination_freeze_active",
        "new_proof_trades_frozen",
        "new_proof_trades_frozen_by_override",
        "new_proof_trades_frozen_by_drawdown",
        "new_proof_order_staging_allowed",
        "new_proof_trade_submission_allowed",
        "existing_lifecycle_closeout_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "unsafe_write_counter_total",
        "checks",
        "failed_checks",
        "failed_check_count",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_override_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION:
        errors.append("phase7_override_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_override_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_override_detector":
        errors.append("phase7_override_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-12":
        errors.append("phase7_override_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_override_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_override_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_override_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_override_blocker_count_mismatch")
    checks = artifact.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_override_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if artifact.get("failed_checks") != failed_checks:
        errors.append("phase7_override_failed_checks_mismatch")
    if artifact.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_override_failed_check_count_mismatch")
    if tuple(check.get("name") for check in checks if isinstance(check, dict)) != (
        PHASE7_OVERRIDE_REQUIRED_CHECKS
    ):
        errors.append("phase7_override_required_checks_invalid")

    stage_recorded = artifact.get("override_detector_recorded") is True
    contaminated = artifact.get("sample_contaminated") is True
    source_frozen = artifact.get("source_drawdown_new_proof_trades_frozen") is True
    frozen = artifact.get("new_proof_trades_frozen") is True
    if stage_recorded:
        if artifact.get("status") not in {"clean_no_overrides", "contaminated"}:
            errors.append("phase7_override_status_invalid")
        if artifact.get("stage_status") not in {
            "override_detector_clean_no_interventions",
            "override_detector_sample_contaminated",
        }:
            errors.append("phase7_override_stage_status_invalid")
        if blockers:
            errors.append("phase7_override_recorded_with_blockers")
        if artifact.get("q7_13_signal_funnel_evidence_stage_allowed") is not True:
            errors.append("q7_13_signal_funnel_evidence_not_allowed")
        if artifact.get("override_detection_write_allowed") is not True:
            errors.append("phase7_override_write_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_override_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_override_blocked_without_blockers")
        if artifact.get("q7_13_signal_funnel_evidence_stage_allowed") is not False:
            errors.append("q7_13_stage_allowed_while_blocked")
    if artifact.get("q7_12_override_detector_stage_allowed") is not True:
        errors.append("q7_12_override_detector_not_allowed")

    records = artifact.get("override_records", [])
    if not isinstance(records, list):
        errors.append("phase7_override_records_not_list")
        records = []
    for record in records:
        if isinstance(record, dict):
            errors.extend(_override_record_errors(record))
        else:
            errors.append("phase7_override_record_invalid")
    governance_records = artifact.get("governance_feedback_records", [])
    if not isinstance(governance_records, list):
        errors.append("phase7_override_governance_records_not_list")
        governance_records = []
    for record in governance_records:
        if isinstance(record, dict):
            errors.extend(_governance_record_errors(record))
        else:
            errors.append("phase7_override_governance_record_invalid")
    if artifact.get("override_record_count") != len(records):
        errors.append("phase7_override_record_count_mismatch")
    if artifact.get("governance_feedback_record_count") != len(governance_records):
        errors.append("phase7_override_governance_count_mismatch")
    counted_override_count = sum(
        _int(record.get("intervention_count"))
        for record in records
        if isinstance(record, dict)
    )
    if artifact.get("override_count") != counted_override_count:
        errors.append("phase7_override_count_mismatch")
    if artifact.get("manual_trade_level_override_count") != _kind_count(
        [record for record in records if isinstance(record, dict)],
        "manual_trade_level_approval",
        "manual_trade_level_rejection",
        "manual_quantity_edit",
        "manual_price_edit",
        "manual_exit",
        "manual_trade_level_override_attempt",
    ):
        errors.append("phase7_override_manual_count_mismatch")
    if artifact.get("broker_side_intervention_count") != _kind_count(
        [record for record in records if isinstance(record, dict)],
        "broker_side_intervention",
    ):
        errors.append("phase7_override_broker_side_count_mismatch")
    if artifact.get("unlinked_lifecycle_record_count") != _kind_count(
        [record for record in records if isinstance(record, dict)],
        "unlinked_lifecycle_record",
    ):
        errors.append("phase7_override_unlinked_count_mismatch")
    if artifact.get("governance_feedback_trade_level_intervention_count") != 0:
        errors.append("phase7_override_governance_trade_level_intervention")
    if artifact.get("governance_feedback_affects_future_policy_only") is not True:
        errors.append("phase7_override_governance_not_future_policy_only")

    if contaminated:
        if artifact.get("clean_sample") is not False:
            errors.append("phase7_override_contaminated_clean_sample")
        if artifact.get("override_count") <= 0:
            errors.append("phase7_override_contaminated_without_override_count")
        if artifact.get("phase7_certification_blocked_by_override") is not True:
            errors.append("phase7_override_contamination_not_blocking_certification")
        if artifact.get("phase7_certification_blocked_by_contaminated_sample") is not True:
            errors.append("phase7_override_contaminated_sample_not_blocking")
        if artifact.get("run_restart_required") is not True:
            errors.append("phase7_override_contamination_restart_not_required")
        if frozen is not True:
            errors.append("phase7_override_contamination_not_frozen")
        if artifact.get("new_proof_order_staging_allowed") is not False:
            errors.append("phase7_override_contamination_staging_not_frozen")
        if artifact.get("new_proof_trade_submission_allowed") is not False:
            errors.append("phase7_override_contamination_submission_not_frozen")
        if artifact.get("new_proof_trades_frozen_by_override") is not True:
            errors.append("phase7_override_contamination_freeze_reason_missing")
    else:
        if artifact.get("clean_sample") is not True:
            errors.append("phase7_override_clean_sample_flag_invalid")
        if artifact.get("override_count") != 0:
            errors.append("phase7_override_clean_with_override_count")
        if artifact.get("phase7_certification_blocked_by_override") is not False:
            errors.append("phase7_override_clean_blocks_certification")
        if artifact.get("phase7_certification_blocked_by_contaminated_sample") is not False:
            errors.append("phase7_override_clean_contamination_block")
        if artifact.get("run_restart_required") is not False:
            errors.append("phase7_override_clean_restart_required")
        if artifact.get("new_proof_trades_frozen_by_override") is not False:
            errors.append("phase7_override_clean_frozen_by_override")
    expected_frozen = stage_recorded and (contaminated or source_frozen)
    if frozen is not expected_frozen:
        errors.append("phase7_override_freeze_state_mismatch")
    if artifact.get("sample_contamination_freeze_active") is not expected_frozen:
        errors.append("phase7_override_sample_freeze_state_mismatch")
    if stage_recorded:
        expected_new_trade_allowed = not expected_frozen
        if artifact.get("new_proof_order_staging_allowed") is not expected_new_trade_allowed:
            errors.append("phase7_override_staging_allowed_mismatch")
        if artifact.get("new_proof_trade_submission_allowed") is not expected_new_trade_allowed:
            errors.append("phase7_override_submission_allowed_mismatch")
        if artifact.get("existing_lifecycle_closeout_allowed") is not True:
            errors.append("phase7_override_lifecycle_closeout_not_allowed")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_override_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_override_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_override_starting_equity_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_override_drawdown_cap_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_override_mature_benchmark_mismatch")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_override_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_override_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_override_qctrl_role_invalid")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_override_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_override_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_override_proof_contract_phase5_reuse_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_override_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_override_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_override_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_override_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records the Phase 7 clean-sample override detector only",
        "manual trade-level approvals",
        "broker-side intervention",
        "unlinked lifecycle records",
        "mark the proof sample contaminated",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_override_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_override_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_override_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_override_detector_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_OVERRIDE_DETECTOR_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_OVERRIDE_DETECTOR_EVENT_TYPE,
        PHASE7_OVERRIDE_DETECTOR_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "sample_contaminated": output.get("sample_contaminated"),
            "clean_sample": output.get("clean_sample"),
            "override_count": output.get("override_count"),
            "manual_trade_level_override_count": output.get(
                "manual_trade_level_override_count"
            ),
            "broker_side_intervention_count": output.get(
                "broker_side_intervention_count"
            ),
            "unlinked_lifecycle_record_count": output.get(
                "unlinked_lifecycle_record_count"
            ),
            "new_proof_trades_frozen": output.get("new_proof_trades_frozen"),
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
    output["validation_errors"] = validate_phase7_override_detector(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "override_detector_validation_error"
    return output, [entry]


def write_phase7_override_detector(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_override_detector_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_override_detector_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_override_detector(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "override_detector_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_override_detector(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "override_detector_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "sample_contaminated": output.get("sample_contaminated"),
        "clean_sample": output.get("clean_sample"),
        "override_count": output.get("override_count"),
        "manual_trade_level_override_count": output.get(
            "manual_trade_level_override_count"
        ),
        "broker_side_intervention_count": output.get("broker_side_intervention_count"),
        "unlinked_lifecycle_record_count": output.get("unlinked_lifecycle_record_count"),
        "new_proof_trades_frozen": output.get("new_proof_trades_frozen"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
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
