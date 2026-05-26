"""Q7-9 Phase 7 Demo Proof postmortem contract.

This stage records postmortem-due coverage for closed Phase 7 proof trades and
defines the packet contract each closed proof trade must satisfy. It can create
local due markers and packet templates, but it cannot approve postmortems,
write learning data, mutate strategy/policy, grant proof credit, or enable
live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_postmortem_packets import (
    ALLOWED_ASSERTION_KINDS,
    ASSERTION_REQUIRED_FIELDS,
    POSTMORTEM_PACKET_SECTIONS,
)
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
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


PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION = 1
PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT = "phase7_proof_postmortem_contract.json"
PHASE7_PROOF_POSTMORTEM_HISTORY = "phase7_proof_postmortem_contract_history.jsonl"
PHASE7_PROOF_POSTMORTEM_EVENT_LOG = "phase7_proof_postmortem_contract_events.jsonl"
PHASE7_PROOF_POSTMORTEM_EVENT_TYPE = PHASE7_EVENT_TYPES["postmortem"]
PHASE7_PROOF_POSTMORTEM_COMPONENT = "phase7_proof_postmortem_contract"
PHASE7_POSTMORTEM_DUE_WITHIN_HOURS = 24

PHASE7_PROOF_POSTMORTEM_BOUNDARY = (
    "Q7-9 records Phase 7 proof postmortem due markers and packet templates "
    "only from Q7-8 closed proof trades. It can require a 24 hour postmortem "
    "packet window, source-cited packet sections, missing/late/reviewed/"
    "deferred tracking, and certification blocking for missing coverage, but "
    "it cannot approve postmortems, cannot write learning data, cannot write a "
    "Knowledge Graph, cannot mutate policy or strategies, cannot call broker "
    "POST routes, cannot call Alpaca POST routes, cannot write prediction-"
    "market or crypto-perps orders, cannot grant Phase 7 proof credit, cannot "
    "enable live capital, and cannot permit manual trade-level overrides."
)

PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_8_lifecycle_artifact_valid",
    "q7_9_postmortem_stage_allowed",
    "source_closed_trade_present",
    "source_lifecycle_refs_present",
    "source_setup_ref_present",
    "postmortem_due_marker_created",
    "postmortem_packet_template_created",
    "postmortem_due_within_24h",
    "all_required_sections_declared",
    "assertion_source_refs_required",
    "narrative_only_blocked",
    "missing_late_review_deferred_tracking_enabled",
    "certification_blocks_missing_coverage",
    "no_postmortem_approval",
    "no_learning_write",
    "no_knowledge_graph_write",
    "no_model_or_trust_update",
    "no_policy_or_strategy_mutation",
    "no_broker_post",
    "no_alpaca_post",
    "no_live_endpoint",
    "no_live_capital",
    "proof_credit_disabled",
    "manual_override_disabled",
    "market_writes_disabled",
    "public_safe",
)

PHASE7_POSTMORTEM_WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "postmortem_approved",
    "learning_write_allowed",
    "learning_write_created",
    "knowledge_graph_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase7_proof_credit_allowed",
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


def phase7_proof_postmortem_contract_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT,
        runtime / PHASE7_PROOF_POSTMORTEM_HISTORY,
        runtime / PHASE7_PROOF_POSTMORTEM_EVENT_LOG,
    )


def _proof_lifecycle(settings: Settings) -> dict[str, Any]:
    lifecycle_path, _, _ = phase7_proof_lifecycle_monitor_paths(settings)
    if lifecycle_path.exists():
        return _read_json(lifecycle_path)
    return build_phase7_proof_lifecycle_monitor(settings=settings)


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in PHASE7_POSTMORTEM_WRITE_DISABLED_FIELDS}


def _section_contracts() -> list[dict[str, Any]]:
    return [
        {
            "section_key": section_key,
            "required": True,
            "source_refs_or_hypothesis_required": True,
            "uncited_conclusion_allowed": False,
            "minimum_assertion_count_for_submitted_packet": 1,
            "allowed_assertion_kinds": list(ALLOWED_ASSERTION_KINDS),
            "template_may_be_empty_until_packet_submitted": True,
            "write_authority": False,
        }
        for section_key in POSTMORTEM_PACKET_SECTIONS
    ]


def _postmortem_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "source_lifecycle_required": True,
        "closed_trade_required": True,
        "postmortem_due_marker_required": True,
        "postmortem_packet_required_for_every_closed_trade": True,
        "postmortem_due_within_hours": PHASE7_POSTMORTEM_DUE_WITHIN_HOURS,
        "missing_late_review_deferred_tracking_required": True,
        "reviewed_or_explicitly_deferred_required_for_certification": True,
        "certification_blocks_missing_postmortem_coverage": True,
        "q6_packet_sections_reused": True,
        "assertion_source_refs_required": True,
        "hypothesis_marker_required_when_uncited": True,
        "uncited_conclusion_allowed": False,
        "narrative_only_allowed": False,
        "postmortem_approval_allowed": False,
        "learning_write_allowed": False,
        "knowledge_graph_write_allowed": False,
        "model_weight_update_allowed": False,
        "trust_score_update_allowed": False,
        "policy_mutation_allowed": False,
        "strategy_mutation_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(stage_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    for field in (
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
    ):
        defaults[field] = stage_recorded
    return {
        "authority_schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "stage": "Q7-9",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 5 if stage_recorded else 0,
        "explicit_authority_grants": (
            [
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
                "phase7_proof_lifecycle_write_allowed",
                "phase7_postmortem_write_allowed",
            ]
            if stage_recorded
            else []
        ),
        "q7_10_performance_evaluator_stage_allowed": stage_recorded,
        **defaults,
        "boundary": PHASE7_PROOF_POSTMORTEM_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
            "orchestrator/phase6_postmortem_packets.py",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_proof_lifecycle_monitor.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-8-proof-lifecycle-monitor-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}"
    ]
    provenance["proof_lifecycle_refs"] = [
        f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(lifecycle: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    lifecycle_errors = validate_phase7_proof_lifecycle_monitor(lifecycle)
    if lifecycle_errors:
        blockers.append("phase7_proof_lifecycle_validation_errors")
    if lifecycle.get("proof_lifecycle_monitor_recorded") is not True:
        blockers.append("phase7_proof_lifecycle_monitor_not_recorded")
    if lifecycle.get("q7_9_proof_postmortem_contract_stage_allowed") is not True:
        blockers.append("q7_9_proof_postmortem_contract_stage_not_allowed")
    if lifecycle.get("failed_reconciliation_count", 0) not in {0, None}:
        blockers.append("phase7_lifecycle_failed_reconciliation")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if lifecycle.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _closed_lifecycle_records(lifecycle: dict[str, Any]) -> list[dict[str, Any]]:
    records = lifecycle.get("closed_trade_records", [])
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("closed_trade_recorded") is True
        and record.get("lifecycle_state") == "closed_trade"
    ]


def _due_by(generated_at: str) -> str:
    try:
        base = datetime.fromisoformat(generated_at)
    except ValueError:
        base = datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return (base + timedelta(hours=PHASE7_POSTMORTEM_DUE_WITHIN_HOURS)).isoformat()


def _packet_template(closed_record: dict[str, Any]) -> dict[str, Any]:
    source_lifecycle_ref = str(closed_record.get("artifact_id") or "")
    source_closed_trade_ref = str(closed_record.get("closed_trade_ref") or "")
    return {
        "template_only": True,
        "packet_state": "postmortem_due_template_not_submitted",
        "source_lifecycle_event_ref": source_lifecycle_ref,
        "source_closed_trade_ref": source_closed_trade_ref,
        "source_setup_record_id": closed_record.get("source_setup_record_id"),
        "source_auto_approval_decision_id": closed_record.get(
            "source_auto_approval_decision_id"
        ),
        "source_staged_order_artifact_id": closed_record.get(
            "source_staged_order_artifact_id"
        ),
        "source_order_ref": closed_record.get("submitted_order_ref"),
        "source_broker_receipt_ref": closed_record.get("broker_receipt_ref"),
        "narrative_only": False,
        "narrative_body": None,
        "sections": [
            {
                "section_key": section_key,
                "required": True,
                "assertions": [],
                "assertion_count": 0,
                "source_refs_or_hypothesis_required": True,
                "uncited_conclusion_allowed": False,
                "minimum_assertion_count_for_submitted_packet": 1,
            }
            for section_key in POSTMORTEM_PACKET_SECTIONS
        ],
        "write_authority": False,
        **_disabled_write_fields(),
    }


def _postmortem_record(
    closed_record: dict[str, Any],
    *,
    stage_recorded: bool,
    lifecycle_errors: list[str],
    generated_at: str,
) -> dict[str, Any]:
    source_closed_trade_ref = str(closed_record.get("closed_trade_ref") or "").strip()
    source_lifecycle_ref = str(closed_record.get("artifact_id") or "").strip()
    due_marker_created = stage_recorded and bool(source_closed_trade_ref and source_lifecycle_ref)
    postmortem_due_by = _due_by(generated_at)
    packet_template = _packet_template(closed_record)
    checks = [
        _check("q7_8_lifecycle_artifact_valid", not lifecycle_errors, detail=lifecycle_errors),
        _check("q7_9_postmortem_stage_allowed", stage_recorded),
        _check("source_closed_trade_present", closed_record.get("closed_trade_recorded") is True),
        _check(
            "source_lifecycle_refs_present",
            bool(source_lifecycle_ref)
            and bool(source_closed_trade_ref)
            and bool(str(closed_record.get("submitted_order_ref") or "").strip())
            and bool(str(closed_record.get("broker_receipt_ref") or "").strip()),
        ),
        _check(
            "source_setup_ref_present",
            bool(str(closed_record.get("source_setup_record_id") or "").strip()),
        ),
        _check("postmortem_due_marker_created", due_marker_created),
        _check("postmortem_packet_template_created", isinstance(packet_template, dict)),
        _check("postmortem_due_within_24h", True),
        _check("all_required_sections_declared", True),
        _check("assertion_source_refs_required", True),
        _check("narrative_only_blocked", True),
        _check("missing_late_review_deferred_tracking_enabled", True),
        _check("certification_blocks_missing_coverage", True),
        _check("no_postmortem_approval", True),
        _check("no_learning_write", True),
        _check("no_knowledge_graph_write", True),
        _check("no_model_or_trust_update", True),
        _check("no_policy_or_strategy_mutation", True),
        _check("no_broker_post", True),
        _check("no_alpaca_post", True),
        _check("no_live_endpoint", True),
        _check("no_live_capital", True),
        _check("proof_credit_disabled", True),
        _check("manual_override_disabled", True),
        _check("market_writes_disabled", True),
        _check("public_safe", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    ready = due_marker_created and not failed_checks
    key = _safe_key(source_closed_trade_ref or source_lifecycle_ref or "unknown")
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "proof_postmortem_schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "artifact_type": "proof_postmortem_packet",
        "artifact_id": f"phase7:q7-9:proof-postmortem:{key}",
        "phase": "Q7",
        "stage": "Q7-9",
        "status": "postmortem_due" if ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "postmortem_state": "postmortem_due" if ready else "blocked_not_due",
        "source_q7_8_artifact_id": closed_record.get("artifact_id"),
        "source_lifecycle_event_ref": source_lifecycle_ref if ready else None,
        "source_closed_trade_ref": source_closed_trade_ref if ready else None,
        "source_setup_record_id": closed_record.get("source_setup_record_id"),
        "source_auto_approval_decision_id": closed_record.get(
            "source_auto_approval_decision_id"
        ),
        "source_staged_order_artifact_id": closed_record.get(
            "source_staged_order_artifact_id"
        ),
        "source_submitted_order_ref": closed_record.get("submitted_order_ref"),
        "source_broker_receipt_ref": closed_record.get("broker_receipt_ref"),
        "idempotency_key": closed_record.get("idempotency_key"),
        "idempotency_namespace": closed_record.get("idempotency_namespace"),
        "postmortem_due_marker_created": ready,
        "postmortem_due_at": generated_at if ready else None,
        "postmortem_due_by": postmortem_due_by if ready else None,
        "postmortem_due_within_hours": PHASE7_POSTMORTEM_DUE_WITHIN_HOURS,
        "postmortem_packet_required": ready,
        "postmortem_packet_template_created": ready,
        "postmortem_packet_submitted": False,
        "postmortem_reviewed": False,
        "postmortem_explicitly_deferred": False,
        "postmortem_late": False,
        "postmortem_missing": False if ready else True,
        "postmortem_coverage_state": (
            "due_marker_created_packet_pending" if ready else "missing_coverage"
        ),
        "certification_blocked_by_missing_postmortem": False if ready else True,
        "packet_payload": packet_template if ready else None,
        "packet_section_count": len(POSTMORTEM_PACKET_SECTIONS) if ready else 0,
        "required_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "assertion_source_refs_required": True,
        "uncited_conclusion_allowed": False,
        "narrative_only_allowed": False,
        "review_required": True,
        "deferred_review_allowed_with_explicit_reason": True,
        "postmortem_approved": False,
        "learning_write_allowed": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "phase7_proof_credit_allowed": False,
        "proof_trade_credit_count": 0,
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
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "required_checks": list(PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if ready else failed_checks,
        "blocked_reason_count": 0 if ready else len(failed_checks),
    }


def _postmortem_records(
    lifecycle: dict[str, Any],
    *,
    stage_recorded: bool,
) -> list[dict[str, Any]]:
    lifecycle_errors = validate_phase7_proof_lifecycle_monitor(lifecycle)
    generated_at = _now()
    return [
        _postmortem_record(
            record,
            stage_recorded=stage_recorded,
            lifecycle_errors=lifecycle_errors,
            generated_at=generated_at,
        )
        for record in _closed_lifecycle_records(lifecycle)
    ]


def build_phase7_proof_postmortem_contract(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    lifecycle = _proof_lifecycle(settings)
    blockers = _preflight_blockers(lifecycle)
    stage_recorded = not blockers
    records = _postmortem_records(lifecycle, stage_recorded=stage_recorded)
    due_records = [
        record for record in records if record.get("postmortem_due_marker_created") is True
    ]
    template_records = [
        record for record in due_records if record.get("postmortem_packet_template_created") is True
    ]
    submitted_records = [
        record for record in records if record.get("postmortem_packet_submitted") is True
    ]
    reviewed_records = [
        record for record in records if record.get("postmortem_reviewed") is True
    ]
    deferred_records = [
        record for record in records if record.get("postmortem_explicitly_deferred") is True
    ]
    late_records = [record for record in records if record.get("postmortem_late") is True]
    missing_records = [
        record for record in records if record.get("postmortem_missing") is True
    ]
    closed_trade_count = _int(lifecycle.get("closed_proof_trade_count"))
    missing_coverage_count = max(0, closed_trade_count - len(due_records)) + len(
        missing_records
    )
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    for field in (
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
    ):
        authority_defaults[field] = stage_recorded
    status = "ready_no_closed_trades"
    stage_status = "proof_postmortem_contract_ready_no_closed_trades"
    if due_records:
        status = "postmortem_due_markers_recorded"
        stage_status = "proof_postmortem_due_markers_recorded"
    if missing_coverage_count:
        status = "blocked_missing_postmortem_coverage"
        stage_status = "proof_postmortem_missing_coverage"
    if not stage_recorded:
        status = "blocked"
        stage_status = "proof_postmortem_contract_blocked"
    artifact = {
        "schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_proof_postmortem_contract",
        "artifact_id": "phase7:q7-9:proof-postmortem-contract",
        "phase": "Q7",
        "stage": "Q7-9",
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
        "authority_ledger": _authority_ledger(stage_recorded),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "postmortem_policy": _postmortem_policy(),
        "packet_sections": list(POSTMORTEM_PACKET_SECTIONS),
        "packet_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "required_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "section_contracts": _section_contracts(),
        "assertion_required_fields": list(ASSERTION_REQUIRED_FIELDS),
        "allowed_assertion_kinds": list(ALLOWED_ASSERTION_KINDS),
        "assertion_source_refs_required": True,
        "uncited_conclusion_allowed": False,
        "narrative_only_allowed": False,
        "hypothesis_marker_required_when_uncited": True,
        "postmortem_due_within_hours": PHASE7_POSTMORTEM_DUE_WITHIN_HOURS,
        "postmortem_records": records,
        "postmortem_due_records": due_records,
        "postmortem_packet_template_records": template_records,
        "postmortem_packet_submitted_records": submitted_records,
        "postmortem_reviewed_records": reviewed_records,
        "postmortem_explicitly_deferred_records": deferred_records,
        "postmortem_late_records": late_records,
        "postmortem_missing_records": missing_records,
        "boundary": PHASE7_PROOF_POSTMORTEM_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        **_disabled_write_fields(),
        "source_lifecycle_artifact_id": lifecycle.get("artifact_id"),
        "source_lifecycle_status": lifecycle.get("status"),
        "source_lifecycle_stage_status": lifecycle.get("stage_status"),
        "source_proof_trade_count": _int(lifecycle.get("proof_trade_count")),
        "source_closed_proof_trade_count": closed_trade_count,
        "source_lifecycle_event_count": _int(lifecycle.get("lifecycle_event_count")),
        "source_failed_reconciliation_count": _int(
            lifecycle.get("failed_reconciliation_count")
        ),
        "q7_9_proof_postmortem_contract_stage_allowed": (
            lifecycle.get("q7_9_proof_postmortem_contract_stage_allowed") is True
        ),
        "q7_10_performance_evaluator_stage_allowed": stage_recorded,
        "proof_postmortem_contract_recorded": stage_recorded,
        "postmortem_record_count": len(records),
        "postmortem_due_count": len(due_records),
        "postmortem_due_marker_created_count": len(due_records),
        "postmortem_packet_required_count": closed_trade_count,
        "postmortem_packet_template_count": len(template_records),
        "postmortem_packet_submitted_count": len(submitted_records),
        "postmortem_reviewed_count": len(reviewed_records),
        "postmortem_explicitly_deferred_count": len(deferred_records),
        "postmortem_late_count": len(late_records),
        "postmortem_missing_count": len(missing_records),
        "closed_trade_without_postmortem_coverage_count": missing_coverage_count,
        "phase7_certification_blocked_by_missing_postmortem": (
            missing_coverage_count > 0
        ),
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "paper_order_submitted_count": _int(lifecycle.get("paper_order_submitted_count")),
        "proof_trade_created_count": _int(lifecycle.get("proof_trade_created_count")),
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-10 Performance Evaluator",
    }
    artifact["validation_errors"] = validate_phase7_proof_postmortem_contract(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "proof_postmortem_contract_validation_error"
    return artifact


def _section_keys(sections: Any) -> set[str]:
    if not isinstance(sections, list):
        return set()
    return {
        str(section.get("section_key"))
        for section in sections
        if isinstance(section, dict) and section.get("section_key")
    }


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in PHASE7_POSTMORTEM_WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def validate_phase7_postmortem_packet_payload(
    packet: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["phase7_postmortem_packet_invalid"]
    if not packet.get("source_lifecycle_event_ref"):
        errors.append("phase7_postmortem_packet_missing_lifecycle_ref")
    if not packet.get("source_closed_trade_ref"):
        errors.append("phase7_postmortem_packet_missing_closed_trade_ref")
    if not packet.get("source_setup_record_id"):
        errors.append("phase7_postmortem_packet_missing_setup_ref")
    if packet.get("narrative_only") is True:
        errors.append("phase7_postmortem_narrative_only_packet")
    if packet.get("narrative_body") and not packet.get("sections"):
        errors.append("phase7_postmortem_narrative_only_packet")
    if packet.get("write_authority") is not False:
        errors.append("phase7_postmortem_packet_write_authority")
    errors.extend(_write_disabled_errors("phase7_postmortem_packet", packet))

    sections = packet.get("sections")
    if not isinstance(sections, list):
        errors.append("phase7_postmortem_packet_sections_invalid")
        sections = []
    required_sections = set(POSTMORTEM_PACKET_SECTIONS)
    present_sections = _section_keys(sections)
    for section_key in sorted(required_sections - present_sections):
        errors.append(f"phase7_postmortem_packet_required_section_missing:{section_key}")
    template_only = packet.get("template_only") is True
    for section in sections:
        if not isinstance(section, dict):
            errors.append("phase7_postmortem_packet_section_invalid")
            continue
        section_key = str(section.get("section_key") or "")
        if section_key not in required_sections:
            errors.append(f"phase7_postmortem_packet_unknown_section:{section_key}")
        if section.get("uncited_conclusion_allowed") is not False:
            errors.append(
                f"phase7_postmortem_section_uncited_conclusion_allowed:{section_key}"
            )
        assertions = section.get("assertions")
        if not isinstance(assertions, list):
            errors.append(f"phase7_postmortem_section_assertions_invalid:{section_key}")
            assertions = []
        if not template_only and not assertions:
            errors.append(f"phase7_postmortem_section_assertions_missing:{section_key}")
        if section.get("assertion_count") is not None and section.get(
            "assertion_count"
        ) != len(assertions):
            errors.append(
                f"phase7_postmortem_section_assertion_count_mismatch:{section_key}"
            )
        for assertion in assertions:
            if not isinstance(assertion, dict):
                errors.append(f"phase7_postmortem_packet_assertion_invalid:{section_key}")
                continue
            for field in ASSERTION_REQUIRED_FIELDS:
                if field not in assertion:
                    errors.append(
                        f"phase7_postmortem_packet_assertion_missing_field:{section_key}:{field}"
                    )
            assertion_kind = str(assertion.get("assertion_kind") or "")
            if assertion_kind not in ALLOWED_ASSERTION_KINDS:
                errors.append(
                    f"phase7_postmortem_packet_assertion_kind_invalid:{section_key}:{assertion_kind}"
                )
            source_refs = assertion.get("source_refs", [])
            if not isinstance(source_refs, list):
                errors.append(
                    f"phase7_postmortem_packet_assertion_source_refs_invalid:{section_key}"
                )
                source_refs = []
            is_hypothesis = assertion.get("is_hypothesis") is True
            if is_hypothesis:
                if not assertion.get("hypothesis_reason"):
                    errors.append(
                        f"phase7_postmortem_packet_hypothesis_reason_missing:{section_key}"
                    )
                if assertion.get("review_required") is not True:
                    errors.append(
                        f"phase7_postmortem_packet_hypothesis_review_not_required:{section_key}"
                    )
            else:
                if not source_refs:
                    errors.append(
                        f"phase7_postmortem_packet_assertion_source_refs_missing:{section_key}"
                    )
                if assertion.get("conclusion") is True and not source_refs:
                    errors.append("phase7_postmortem_uncited_conclusion")
            for ref in source_refs:
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(
                        f"phase7_postmortem_packet_assertion_source_ref_invalid:{section_key}"
                    )
                    continue
                if _has_local_path(ref):
                    errors.append("phase7_postmortem_packet_assertion_local_source_ref")
                if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
                    errors.append("phase7_postmortem_packet_assertion_secret_ref")
    return sorted(set(errors))


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("proof_postmortem_contract_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_postmortem_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-9":
        errors.append("phase7_postmortem_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_postmortem_authority_count_mismatch")
    expected_grants = 5 if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_postmortem_explicit_authority_grant_count_invalid")
    expected_true = {
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_postmortem_write_allowed",
    }
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_postmortem_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_postmortem_ledger_authority_invalid:{field}")
    allowed_count_fields = {"paper_order_submitted_count", "proof_trade_created_count"}
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("paper_order_submitted_count")):
                errors.append(f"phase7_postmortem_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("source_proof_trade_count")):
                errors.append(f"phase7_postmortem_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_postmortem_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        _int(artifact.get(field))
        for field in PHASE7_UNSAFE_COUNT_FIELDS
        if field not in allowed_count_fields
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_postmortem_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_postmortem_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("postmortem_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_postmortem_policy_missing"]
    for field in (
        "source_lifecycle_required",
        "closed_trade_required",
        "postmortem_due_marker_required",
        "postmortem_packet_required_for_every_closed_trade",
        "missing_late_review_deferred_tracking_required",
        "reviewed_or_explicitly_deferred_required_for_certification",
        "certification_blocks_missing_postmortem_coverage",
        "q6_packet_sections_reused",
        "assertion_source_refs_required",
        "hypothesis_marker_required_when_uncited",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_postmortem_policy_missing_true:{field}")
    for field in (
        "uncited_conclusion_allowed",
        "narrative_only_allowed",
        "postmortem_approval_allowed",
        "learning_write_allowed",
        "knowledge_graph_write_allowed",
        "model_weight_update_allowed",
        "trust_score_update_allowed",
        "policy_mutation_allowed",
        "strategy_mutation_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"phase7_postmortem_policy_forbidden:{field}")
    if policy.get("postmortem_due_within_hours") != PHASE7_POSTMORTEM_DUE_WITHIN_HOURS:
        errors.append("phase7_postmortem_policy_due_window_invalid")
    return errors


def _postmortem_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ready = record.get("postmortem_due_marker_created") is True
    if record.get("artifact_type") != "proof_postmortem_packet":
        errors.append("phase7_postmortem_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-9":
        errors.append("phase7_postmortem_record_phase_stage_invalid")
    if tuple(record.get("required_checks", ())) != PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS:
        errors.append("phase7_postmortem_record_required_checks_invalid")
    if ready:
        if record.get("status") != "postmortem_due":
            errors.append("phase7_postmortem_record_status_invalid")
        if record.get("postmortem_state") != "postmortem_due":
            errors.append("phase7_postmortem_state_invalid")
        for field in (
            "source_q7_8_artifact_id",
            "source_lifecycle_event_ref",
            "source_closed_trade_ref",
            "source_setup_record_id",
            "source_submitted_order_ref",
            "source_broker_receipt_ref",
            "postmortem_due_at",
            "postmortem_due_by",
        ):
            if not str(record.get(field) or "").strip():
                errors.append(f"phase7_postmortem_record_missing:{field}")
        if record.get("postmortem_packet_required") is not True:
            errors.append("phase7_postmortem_packet_not_required")
        if record.get("postmortem_packet_template_created") is not True:
            errors.append("phase7_postmortem_packet_template_missing")
        if record.get("postmortem_due_within_hours") != (
            PHASE7_POSTMORTEM_DUE_WITHIN_HOURS
        ):
            errors.append("phase7_postmortem_due_window_invalid")
        if record.get("postmortem_missing") is not False:
            errors.append("phase7_postmortem_record_missing_coverage")
        if record.get("certification_blocked_by_missing_postmortem") is not False:
            errors.append("phase7_postmortem_record_blocks_certification")
    else:
        if record.get("status") != "blocked":
            errors.append("phase7_postmortem_blocked_record_status_invalid")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_postmortem_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("phase7_postmortem_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_postmortem_record_failed_count_mismatch")
    blocked_reasons = record.get("blocked_reasons", [])
    if not isinstance(blocked_reasons, list):
        errors.append("phase7_postmortem_record_blocked_reasons_not_list")
        blocked_reasons = []
    if record.get("blocked_reason_count") != len(blocked_reasons):
        errors.append("phase7_postmortem_record_blocked_reason_count_mismatch")
    if ready and failed_checks:
        errors.append("phase7_postmortem_ready_record_has_failed_checks")
    packet = record.get("packet_payload")
    if ready:
        if not isinstance(packet, dict):
            errors.append("phase7_postmortem_packet_payload_missing")
        else:
            errors.extend(
                f"phase7_postmortem_packet:{error}"
                for error in validate_phase7_postmortem_packet_payload(packet, {})
            )
            if packet.get("template_only") is not True and record.get(
                "postmortem_packet_submitted"
            ) is not True:
                errors.append("phase7_postmortem_packet_template_state_invalid")
    if record.get("postmortem_approved") is not False:
        errors.append("phase7_postmortem_record_approved")
    for field in PHASE7_POSTMORTEM_WRITE_DISABLED_FIELDS:
        if record.get(field) is not False:
            errors.append(f"phase7_postmortem_record_write_enabled:{field}")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_postmortem_record_forbidden:{field}")
    for count_field in (
        "proof_trade_credit_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
    ):
        if _int(record.get(count_field)) != 0:
            errors.append(f"phase7_postmortem_record_count_nonzero:{count_field}")
    return errors


def validate_phase7_proof_postmortem_contract(artifact: dict[str, Any]) -> list[str]:
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
        "postmortem_policy",
        "packet_sections",
        "section_contracts",
        "assertion_required_fields",
        "allowed_assertion_kinds",
        "assertion_source_refs_required",
        "uncited_conclusion_allowed",
        "narrative_only_allowed",
        "hypothesis_marker_required_when_uncited",
        "postmortem_due_within_hours",
        "postmortem_records",
        "postmortem_due_records",
        "postmortem_packet_template_records",
        "postmortem_packet_submitted_records",
        "postmortem_reviewed_records",
        "postmortem_explicitly_deferred_records",
        "postmortem_late_records",
        "postmortem_missing_records",
        "boundary",
        "source_lifecycle_status",
        "source_proof_trade_count",
        "source_closed_proof_trade_count",
        "source_lifecycle_event_count",
        "source_failed_reconciliation_count",
        "q7_9_proof_postmortem_contract_stage_allowed",
        "q7_10_performance_evaluator_stage_allowed",
        "proof_postmortem_contract_recorded",
        "postmortem_record_count",
        "postmortem_due_count",
        "postmortem_due_marker_created_count",
        "postmortem_packet_required_count",
        "postmortem_packet_template_count",
        "postmortem_packet_submitted_count",
        "postmortem_reviewed_count",
        "postmortem_explicitly_deferred_count",
        "postmortem_late_count",
        "postmortem_missing_count",
        "closed_trade_without_postmortem_coverage_count",
        "phase7_certification_blocked_by_missing_postmortem",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_postmortem_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION:
        errors.append("phase7_postmortem_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_postmortem_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_proof_postmortem_contract":
        errors.append("phase7_postmortem_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-9":
        errors.append("phase7_postmortem_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_postmortem_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_postmortem_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_postmortem_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_postmortem_blocker_count_mismatch")
    stage_recorded = artifact.get("proof_postmortem_contract_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_closed_trades",
            "postmortem_due_markers_recorded",
            "blocked_missing_postmortem_coverage",
        }:
            errors.append("phase7_postmortem_status_invalid")
        if artifact.get("stage_status") not in {
            "proof_postmortem_contract_ready_no_closed_trades",
            "proof_postmortem_due_markers_recorded",
            "proof_postmortem_missing_coverage",
        }:
            errors.append("phase7_postmortem_stage_status_invalid")
        if blockers:
            errors.append("phase7_postmortem_recorded_with_blockers")
        if artifact.get("q7_10_performance_evaluator_stage_allowed") is not True:
            errors.append("q7_10_performance_evaluator_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_postmortem_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_postmortem_blocked_without_blockers")
        if artifact.get("q7_10_performance_evaluator_stage_allowed") is not False:
            errors.append("q7_10_stage_allowed_while_blocked")
    if artifact.get("q7_9_proof_postmortem_contract_stage_allowed") is not True:
        errors.append("q7_9_proof_postmortem_contract_not_allowed")
    if artifact.get("source_lifecycle_status") not in {
        "ready_no_lifecycle_events",
        "proof_lifecycle_events_recorded",
        "blocked_reconciliation_failure",
    }:
        errors.append("phase7_postmortem_source_lifecycle_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    errors.extend(_write_disabled_errors("phase7_postmortem_contract", artifact))
    if artifact.get("packet_sections") != list(POSTMORTEM_PACKET_SECTIONS):
        errors.append("phase7_postmortem_packet_sections_mismatch")
    if artifact.get("packet_section_count") != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("phase7_postmortem_packet_section_count_mismatch")
    if artifact.get("required_section_count") != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("phase7_postmortem_required_section_count_mismatch")
    if artifact.get("assertion_required_fields") != list(ASSERTION_REQUIRED_FIELDS):
        errors.append("phase7_postmortem_assertion_required_fields_mismatch")
    if artifact.get("allowed_assertion_kinds") != list(ALLOWED_ASSERTION_KINDS):
        errors.append("phase7_postmortem_allowed_assertion_kinds_mismatch")
    if artifact.get("assertion_source_refs_required") is not True:
        errors.append("phase7_postmortem_assertion_refs_not_required")
    if artifact.get("uncited_conclusion_allowed") is not False:
        errors.append("phase7_postmortem_uncited_conclusion_allowed")
    if artifact.get("narrative_only_allowed") is not False:
        errors.append("phase7_postmortem_narrative_only_allowed")
    if artifact.get("hypothesis_marker_required_when_uncited") is not True:
        errors.append("phase7_postmortem_hypothesis_marker_not_required")
    if artifact.get("postmortem_due_within_hours") != (
        PHASE7_POSTMORTEM_DUE_WITHIN_HOURS
    ):
        errors.append("phase7_postmortem_due_window_mismatch")
    section_contracts = artifact.get("section_contracts", [])
    if not isinstance(section_contracts, list):
        errors.append("phase7_postmortem_section_contracts_invalid")
        section_contracts = []
    if _section_keys(section_contracts) != set(POSTMORTEM_PACKET_SECTIONS):
        errors.append("phase7_postmortem_section_contracts_mismatch")
    for section in section_contracts:
        if not isinstance(section, dict):
            errors.append("phase7_postmortem_section_contract_invalid")
            continue
        section_key = section.get("section_key")
        if section.get("required") is not True:
            errors.append(f"phase7_postmortem_section_contract_not_required:{section_key}")
        if section.get("source_refs_or_hypothesis_required") is not True:
            errors.append(f"phase7_postmortem_section_refs_not_required:{section_key}")
        if section.get("uncited_conclusion_allowed") is not False:
            errors.append(
                f"phase7_postmortem_section_uncited_conclusion_allowed:{section_key}"
            )
        if section.get("write_authority") is not False:
            errors.append(f"phase7_postmortem_section_write_authority:{section_key}")

    records = artifact.get("postmortem_records", [])
    if not isinstance(records, list):
        errors.append("phase7_postmortem_records_not_list")
        records = []
    for record in records:
        if isinstance(record, dict):
            errors.extend(_postmortem_record_errors(record))
        else:
            errors.append("phase7_postmortem_record_invalid")
    due_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("postmortem_due_marker_created") is True
    ]
    template_records = [
        record
        for record in due_records
        if record.get("postmortem_packet_template_created") is True
    ]
    submitted_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("postmortem_packet_submitted") is True
    ]
    reviewed_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("postmortem_reviewed") is True
    ]
    deferred_records = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("postmortem_explicitly_deferred") is True
    ]
    late_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("postmortem_late") is True
    ]
    missing_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("postmortem_missing") is True
    ]
    if artifact.get("postmortem_due_records") != due_records:
        errors.append("phase7_postmortem_due_records_mismatch")
    if artifact.get("postmortem_packet_template_records") != template_records:
        errors.append("phase7_postmortem_template_records_mismatch")
    if artifact.get("postmortem_packet_submitted_records") != submitted_records:
        errors.append("phase7_postmortem_submitted_records_mismatch")
    if artifact.get("postmortem_reviewed_records") != reviewed_records:
        errors.append("phase7_postmortem_reviewed_records_mismatch")
    if artifact.get("postmortem_explicitly_deferred_records") != deferred_records:
        errors.append("phase7_postmortem_deferred_records_mismatch")
    if artifact.get("postmortem_late_records") != late_records:
        errors.append("phase7_postmortem_late_records_mismatch")
    if artifact.get("postmortem_missing_records") != missing_records:
        errors.append("phase7_postmortem_missing_records_mismatch")
    closed_trade_count = _int(artifact.get("source_closed_proof_trade_count"))
    if artifact.get("postmortem_record_count") != len(records):
        errors.append("phase7_postmortem_record_count_mismatch")
    if artifact.get("postmortem_due_count") != len(due_records):
        errors.append("phase7_postmortem_due_count_mismatch")
    if artifact.get("postmortem_due_marker_created_count") != len(due_records):
        errors.append("phase7_postmortem_due_marker_count_mismatch")
    if artifact.get("postmortem_packet_required_count") != closed_trade_count:
        errors.append("phase7_postmortem_packet_required_count_mismatch")
    if artifact.get("postmortem_packet_template_count") != len(template_records):
        errors.append("phase7_postmortem_packet_template_count_mismatch")
    if artifact.get("postmortem_packet_submitted_count") != len(submitted_records):
        errors.append("phase7_postmortem_packet_submitted_count_mismatch")
    if artifact.get("postmortem_reviewed_count") != len(reviewed_records):
        errors.append("phase7_postmortem_reviewed_count_mismatch")
    if artifact.get("postmortem_explicitly_deferred_count") != len(deferred_records):
        errors.append("phase7_postmortem_deferred_count_mismatch")
    if artifact.get("postmortem_late_count") != len(late_records):
        errors.append("phase7_postmortem_late_count_mismatch")
    if artifact.get("postmortem_missing_count") != len(missing_records):
        errors.append("phase7_postmortem_missing_count_mismatch")
    missing_coverage_count = max(0, closed_trade_count - len(due_records)) + len(
        missing_records
    )
    if artifact.get("closed_trade_without_postmortem_coverage_count") != (
        missing_coverage_count
    ):
        errors.append("phase7_postmortem_missing_coverage_count_mismatch")
    if closed_trade_count != len(due_records):
        errors.append("phase7_postmortem_due_count_not_equal_closed_trade_count")
    if missing_coverage_count:
        if artifact.get("phase7_certification_blocked_by_missing_postmortem") is not True:
            errors.append("phase7_postmortem_missing_coverage_not_blocking_certification")
    else:
        if artifact.get("phase7_certification_blocked_by_missing_postmortem") is not False:
            errors.append("phase7_postmortem_certification_blocked_without_missing")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_postmortem_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_performance_evaluation_write_allowed",
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
            errors.append(f"phase7_postmortem_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_postmortem_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_postmortem_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != (
        PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
    ):
        errors.append("phase7_postmortem_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("phase7_postmortem_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_postmortem_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_postmortem_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_postmortem_qctrl_role_invalid")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_postmortem_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_postmortem_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_postmortem_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("phase7_postmortem_proof_contract_manual_override_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_postmortem_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_postmortem_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_postmortem_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_postmortem_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records Phase 7 proof postmortem due markers",
        "24 hour postmortem packet window",
        "source-cited packet sections",
        "cannot approve postmortems",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_postmortem_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_postmortem_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_postmortem_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_proof_postmortem_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_PROOF_POSTMORTEM_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    records = [
        record
        for record in output.get("postmortem_records", []) or []
        if isinstance(record, dict)
    ]
    if records:
        for record in records:
            entry = log.write(
                PHASE7_PROOF_POSTMORTEM_EVENT_TYPE,
                PHASE7_PROOF_POSTMORTEM_COMPONENT,
                {
                    "artifact_id": record.get("artifact_id"),
                    "status": record.get("status"),
                    "postmortem_state": record.get("postmortem_state"),
                    "source_lifecycle_event_ref": record.get(
                        "source_lifecycle_event_ref"
                    ),
                    "source_closed_trade_ref": record.get("source_closed_trade_ref"),
                    "source_setup_record_id": record.get("source_setup_record_id"),
                    "postmortem_due_marker_created": record.get(
                        "postmortem_due_marker_created"
                    ),
                    "postmortem_due_by": record.get("postmortem_due_by"),
                    "postmortem_packet_submitted": record.get(
                        "postmortem_packet_submitted"
                    ),
                    "postmortem_reviewed": record.get("postmortem_reviewed"),
                    "postmortem_explicitly_deferred": record.get(
                        "postmortem_explicitly_deferred"
                    ),
                    "phase7_proof_credit_allowed": record.get(
                        "phase7_proof_credit_allowed"
                    ),
                    "live_capital_enabled": record.get("live_capital_enabled"),
                },
            )
            record["event_log_written"] = True
            record["event_log_path"] = str(log.path)
            record["event_log_correlation_id"] = entry.correlation_id
            record["event_log_created_at"] = entry.created_at
            entries.append(entry)
        output["postmortem_records"] = records
        output["postmortem_due_records"] = [
            record
            for record in records
            if record.get("postmortem_due_marker_created") is True
        ]
        output["postmortem_packet_template_records"] = [
            record
            for record in output["postmortem_due_records"]
            if record.get("postmortem_packet_template_created") is True
        ]
        output["postmortem_packet_submitted_records"] = [
            record for record in records if record.get("postmortem_packet_submitted") is True
        ]
        output["postmortem_reviewed_records"] = [
            record for record in records if record.get("postmortem_reviewed") is True
        ]
        output["postmortem_explicitly_deferred_records"] = [
            record
            for record in records
            if record.get("postmortem_explicitly_deferred") is True
        ]
        output["postmortem_late_records"] = [
            record for record in records if record.get("postmortem_late") is True
        ]
        output["postmortem_missing_records"] = [
            record for record in records if record.get("postmortem_missing") is True
        ]
    else:
        entry = log.write(
            PHASE7_PROOF_POSTMORTEM_EVENT_TYPE,
            PHASE7_PROOF_POSTMORTEM_COMPONENT,
            {
                "artifact_id": output.get("artifact_id"),
                "status": output.get("status"),
                "stage_status": output.get("stage_status"),
                "source_closed_proof_trade_count": output.get(
                    "source_closed_proof_trade_count"
                ),
                "postmortem_due_count": output.get("postmortem_due_count"),
                "postmortem_missing_count": output.get("postmortem_missing_count"),
                "postmortem_late_count": output.get("postmortem_late_count"),
                "postmortem_reviewed_count": output.get("postmortem_reviewed_count"),
                "postmortem_explicitly_deferred_count": output.get(
                    "postmortem_explicitly_deferred_count"
                ),
                "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
                "live_capital_enabled": output.get("live_capital_enabled"),
                "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
                "recommended_next_stage": output.get("recommended_next_stage"),
                "boundary": output.get("boundary"),
            },
        )
        entries.append(entry)
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["event_log_correlation_id"] = entries[-1].correlation_id if entries else None
    output["event_log_created_at"] = entries[-1].created_at if entries else None
    output["validation_errors"] = validate_phase7_proof_postmortem_contract(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_postmortem_contract_validation_error"
    return output, entries


def write_phase7_proof_postmortem_contract(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = (
        phase7_proof_postmortem_contract_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_proof_postmortem_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_proof_postmortem_contract(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "proof_postmortem_contract_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_proof_postmortem_contract(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_postmortem_contract_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_closed_proof_trade_count": output.get("source_closed_proof_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_packet_template_count": output.get(
            "postmortem_packet_template_count"
        ),
        "postmortem_packet_submitted_count": output.get(
            "postmortem_packet_submitted_count"
        ),
        "postmortem_reviewed_count": output.get("postmortem_reviewed_count"),
        "postmortem_explicitly_deferred_count": output.get(
            "postmortem_explicitly_deferred_count"
        ),
        "postmortem_late_count": output.get("postmortem_late_count"),
        "postmortem_missing_count": output.get("postmortem_missing_count"),
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
