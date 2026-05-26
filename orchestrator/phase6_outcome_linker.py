"""Q6-8 outcome linker.

This stage builds a durable reference graph across the Q5E paper lifecycle,
the Q6 outcome/postmortem artifacts, and supplemental context. It links refs
only: no source payloads are copied, no learning writes are approved, and no
Phase 5 source artifact is mutated.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_UNSAFE_COUNT_FIELDS,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)
from orchestrator.phase6_closed_trade_outcome import (
    PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT,
    validate_phase6_closed_trade_outcome,
)
from orchestrator.phase6_learning_source_intake import (
    PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT,
    TARGET_STRATEGY_FAMILY_KEY,
    validate_phase6_learning_source_intake,
)
from orchestrator.phase6_postmortem_reducer import (
    PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT,
    validate_phase6_postmortem_reducer,
)


PHASE6_OUTCOME_LINKER_SCHEMA_VERSION = 1
PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT = "phase6_outcome_links.json"
PHASE6_OUTCOME_LINKER_HISTORY = "phase6_outcome_links_history.jsonl"
PHASE6_OUTCOME_LINKER_EVENT_LOG = "phase6_outcome_links_events.jsonl"
PHASE6_OUTCOME_LINKER_EVENT_TYPE = "phase6_postmortem_review_recorded"
PHASE6_OUTCOME_LINKER_COMPONENT = "phase6_outcome_linker"

SOURCE_OUTCOME_REF = f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}"
SOURCE_INTAKE_REF = f"data/runtime/{PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT}"
SOURCE_REVIEW_REF = f"data/runtime/{PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT}"
SOURCE_DRY_RUN_REF = "data/runtime/phase5_alpaca_paper_dry_run.json"
SOURCE_DRY_RUN_EVENT_LOG_REF = "data/runtime/phase5_alpaca_paper_dry_run_events.jsonl"

REQUIRED_LINK_KEYS: tuple[str, ...] = (
    "closed_trade_outcome",
    "source_context",
    "postmortem_review",
    "signal_integrity",
    "risk_agent",
    "approval_policy",
    "execution_policy",
    "staged_order",
    "dry_run_receipt",
    "local_broker_receipt",
    "position_monitor",
    "postmortem_due_marker",
)

OPTIONAL_LINK_KEYS: tuple[str, ...] = (
    "strategy_lead",
    "risk_policy",
    "signal_review",
    "execution_adapter",
    "yahoo_finance_context",
    "preference_shadow_context",
    "preference_provenance",
    "preference_source_promotion",
    "quantum_shadow_annotation",
)

SOURCE_RECORD_LINKS: dict[str, tuple[str, str]] = {
    "signal_integrity": ("signal_integrity", "signal-integrity-review"),
    "risk_agent": ("risk_agent", "risk-agent-sizing-review"),
    "approval_policy": ("approval_policy", "approval-policy-decision"),
    "execution_policy": ("execution_policy", "execution-policy-review"),
    "staged_order": ("paper_order", "staged-paper-order"),
    "local_broker_receipt": ("paper_submit_receipt", "local-broker-receipt"),
    "position_monitor": ("position_monitor", "position-monitor-reconciliation"),
    "postmortem_due_marker": ("postmortem_due", "postmortem-due-marker"),
    "strategy_lead": ("strategy_lead", "strategy-lead-shadow-context"),
    "risk_policy": ("risk_policy", "risk-policy-review"),
    "signal_review": ("signal_review", "signal-review-governance"),
    "execution_adapter": ("execution_adapter", "execution-adapter-status"),
    "yahoo_finance_context": ("yahoo_finance_context", "supplemental-yahoo-context"),
    "preference_shadow_context": (
        "preference_shadow_context",
        "supplemental-preference-shadow-context",
    ),
    "preference_provenance": (
        "preference_provenance",
        "supplemental-preference-provenance",
    ),
    "preference_source_promotion": (
        "preference_source_promotion",
        "supplemental-preference-source-promotion",
    ),
    "quantum_shadow_annotation": (
        "head_of_quant_annotations",
        "quantum-shadow-annotation",
    ),
}

PHASE6_OUTCOME_LINKER_BOUNDARY = (
    "Q6-8 creates durable reference-only outcome links. It can connect the "
    "closed trade outcome to source, strategy, risk, execution, staged order, "
    "dry-run, broker-receipt, position, postmortem, Yahoo, Preference/PREF, "
    "and quantum shadow refs, but it cannot copy private payloads, cannot "
    "approve a postmortem, cannot approve learning actions, cannot write "
    "learning data, cannot write a Knowledge Graph, cannot update model "
    "weights, cannot update trust scores, cannot mutate policy, cannot mutate "
    "strategies, cannot mutate Phase 5 source artifacts, cannot call broker "
    "POST routes, cannot call Alpaca POST routes, cannot call live endpoints, "
    "cannot enable live capital, and cannot count Phase 5 test trades toward "
    "Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "postmortem_approved",
    "learning_write_allowed",
    "learning_write_created",
    "knowledge_graph_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _event_count(ref: str, settings: Settings | None = None) -> int:
    path = _path(ref, settings)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_outcome_linker_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT,
        runtime / PHASE6_OUTCOME_LINKER_HISTORY,
        runtime / PHASE6_OUTCOME_LINKER_EVENT_LOG,
    )


def _source_records_by_key(source_intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("source_key")): record
        for record in _list(source_intake.get("source_records"))
        if isinstance(record, dict) and record.get("source_key")
    }


def _safe_link_record(
    *,
    link_key: str,
    link_role: str,
    required: bool,
    source_ref: str | None,
    selected_ref: str | None,
    source_status: str | None,
    present: bool,
    event_log_ref: str | None = None,
    event_log_event_count: int = 0,
    missing_reason: str | None = None,
) -> dict[str, Any]:
    optional_missing = not required and not present
    return {
        "link_key": link_key,
        "link_role": link_role,
        "required": required,
        "present": present,
        "source_ref": source_ref,
        "selected_ref": selected_ref,
        "source_status": source_status,
        "event_log_ref": event_log_ref,
        "event_log_event_count": event_log_event_count,
        "missing_reason": missing_reason,
        "safe_missing_optional_context": optional_missing,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "local_path_exposed": False,
        "secret_ref_exposed": False,
        "write_authority": False,
    }


def _missing_link(link_key: str, link_role: str, *, required: bool) -> dict[str, Any]:
    return _safe_link_record(
        link_key=link_key,
        link_role=link_role,
        required=required,
        source_ref=None,
        selected_ref=None,
        source_status="missing",
        present=False,
        missing_reason="source_record_missing",
    )


def _source_record_link(
    link_key: str,
    source_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_key, link_role = SOURCE_RECORD_LINKS[link_key]
    required = link_key in REQUIRED_LINK_KEYS
    record = source_records.get(source_key)
    if not record:
        return _missing_link(link_key, link_role, required=required)
    present = bool(record.get("present")) and bool(record.get("source_ref"))
    selected_ref = record.get("selected_ref")
    return _safe_link_record(
        link_key=link_key,
        link_role=link_role,
        required=required,
        source_ref=record.get("source_ref") if isinstance(record.get("source_ref"), str) else None,
        selected_ref=selected_ref if isinstance(selected_ref, str) else None,
        source_status=str(record.get("status") or "unknown"),
        present=present,
        event_log_ref=(
            record.get("event_log_ref") if isinstance(record.get("event_log_ref"), str) else None
        ),
        event_log_event_count=int(record.get("event_log_event_count", 0) or 0),
        missing_reason=record.get("missing_reason") if not present else None,
    )


def _target_record(records: Any) -> dict[str, Any] | None:
    if not isinstance(records, list):
        return None
    for record in records:
        if not isinstance(record, dict):
            continue
        artifact_id = str(record.get("artifact_id") or "")
        family = str(record.get("strategy_family_key") or "")
        if TARGET_STRATEGY_FAMILY_KEY in artifact_id or family == TARGET_STRATEGY_FAMILY_KEY:
            return record
    return None


def _dry_run_link(settings: Settings | None = None) -> dict[str, Any]:
    dry_run = _read_json(SOURCE_DRY_RUN_REF, settings) or {}
    record = _target_record(dry_run.get("records"))
    if not record:
        return _missing_link("dry_run_receipt", "alpaca-paper-dry-run-receipt", required=True)
    selected_ref = record.get("dry_run_receipt_ref") or record.get("artifact_id")
    status = record.get("receipt_state") or record.get("status")
    return _safe_link_record(
        link_key="dry_run_receipt",
        link_role="alpaca-paper-dry-run-receipt",
        required=True,
        source_ref=SOURCE_DRY_RUN_REF,
        selected_ref=selected_ref if isinstance(selected_ref, str) else None,
        source_status=str(status or "unknown"),
        present=bool(selected_ref),
        event_log_ref=SOURCE_DRY_RUN_EVENT_LOG_REF,
        event_log_event_count=_event_count(SOURCE_DRY_RUN_EVENT_LOG_REF, settings),
    )


def _manual_links(
    *,
    outcome: dict[str, Any],
    review: dict[str, Any],
    source_intake: dict[str, Any],
) -> list[dict[str, Any]]:
    outcome_record = _list(outcome.get("outcome_records"))[0] if outcome.get("outcome_records") else {}
    outcome_ref = outcome_record.get("outcome_ref") if isinstance(outcome_record, dict) else None
    return [
        _safe_link_record(
            link_key="closed_trade_outcome",
            link_role="closed-trade-outcome",
            required=True,
            source_ref=SOURCE_OUTCOME_REF,
            selected_ref=outcome_ref if isinstance(outcome_ref, str) else None,
            source_status=str(outcome.get("outcome_status") or outcome.get("status") or "unknown"),
            present=bool(outcome_ref),
            event_log_ref=(
                outcome.get("event_log_path") if isinstance(outcome.get("event_log_path"), str) else None
            ),
            event_log_event_count=int(outcome.get("event_log_event_count", 0) or 0),
        ),
        _safe_link_record(
            link_key="source_context",
            link_role="phase6-learning-source-intake",
            required=True,
            source_ref=SOURCE_INTAKE_REF,
            selected_ref=(
                source_intake.get("artifact_id")
                if isinstance(source_intake.get("artifact_id"), str)
                else None
            ),
            source_status=str(source_intake.get("status") or "unknown"),
            present=bool(source_intake.get("artifact_id")),
            event_log_ref=(
                source_intake.get("event_log_path")
                if isinstance(source_intake.get("event_log_path"), str)
                else None
            ),
            event_log_event_count=int(source_intake.get("event_log_event_count", 0) or 0),
        ),
        _safe_link_record(
            link_key="postmortem_review",
            link_role="q6-7-reduced-postmortem-review",
            required=True,
            source_ref=SOURCE_REVIEW_REF,
            selected_ref=review.get("artifact_id") if isinstance(review.get("artifact_id"), str) else None,
            source_status=str(review.get("status") or "unknown"),
            present=bool(review.get("artifact_id")),
            event_log_ref=(
                review.get("event_log_path") if isinstance(review.get("event_log_path"), str) else None
            ),
            event_log_event_count=int(review.get("event_log_event_count", 0) or 0),
        ),
    ]


def _build_links(
    *,
    outcome: dict[str, Any],
    review: dict[str, Any],
    source_intake: dict[str, Any],
    settings: Settings,
) -> list[dict[str, Any]]:
    source_records = _source_records_by_key(source_intake)
    links = _manual_links(outcome=outcome, review=review, source_intake=source_intake)
    for link_key in (
        "signal_integrity",
        "risk_agent",
        "approval_policy",
        "execution_policy",
        "staged_order",
    ):
        links.append(_source_record_link(link_key, source_records))
    links.append(_dry_run_link(settings))
    for link_key in (
        "local_broker_receipt",
        "position_monitor",
        "postmortem_due_marker",
        "strategy_lead",
        "risk_policy",
        "signal_review",
        "execution_adapter",
        "yahoo_finance_context",
        "preference_shadow_context",
        "preference_provenance",
        "preference_source_promotion",
        "quantum_shadow_annotation",
    ):
        links.append(_source_record_link(link_key, source_records))
    return links


def _source_refs_from_links(links: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for link in links:
        for ref in (link.get("source_ref"), link.get("event_log_ref")):
            if isinstance(ref, str) and ref and ref not in refs:
                refs.append(ref)
    return refs


def _provenance(links: list[dict[str, Any]]) -> dict[str, Any]:
    refs = tuple(_source_refs_from_links(links))
    provenance = phase6_provenance(refs)
    provenance["execution_evidence_refs"] = [
        ref
        for ref in refs
        if any(
            marker in ref
            for marker in (
                "paper_order",
                "alpaca_paper_dry_run",
                "paper_submit",
                "position_monitor",
                "closed_trade",
                "postmortem_due",
            )
        )
    ]
    provenance["market_context_refs"] = [
        ref
        for ref in refs
        if any(marker in ref for marker in ("cockpit-status", "preference_"))
    ]
    provenance["model_interpretation_refs"] = [
        ref for ref in refs if "quantum_oracle_results" in ref
    ]
    provenance["governance_refs"] = [
        ref
        for ref in refs
        if any(marker in ref for marker in ("approval_policy", "signal_review", "reduced_review"))
    ]
    return provenance


def _count_links(links: list[dict[str, Any]], *, required: bool, present: bool) -> int:
    return len(
        [
            link
            for link in links
            if link.get("required") is required and link.get("present") is present
        ]
    )


def build_phase6_outcome_linker(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    outcome = _read_json(SOURCE_OUTCOME_REF, settings) or {}
    source_intake = _read_json(SOURCE_INTAKE_REF, settings) or {}
    review = _read_json(SOURCE_REVIEW_REF, settings) or {}
    blockers: list[str] = []
    outcome_errors = validate_phase6_closed_trade_outcome(outcome) if outcome else []
    source_intake_errors = (
        validate_phase6_learning_source_intake(source_intake) if source_intake else []
    )
    review_errors = validate_phase6_postmortem_reducer(review) if review else []
    if not outcome:
        blockers.append("closed_trade_outcome_missing")
    elif outcome.get("status") != "read_only":
        blockers.append("closed_trade_outcome_not_read_only")
    if not source_intake:
        blockers.append("learning_source_intake_missing")
    elif source_intake.get("status") != "read_only":
        blockers.append("learning_source_intake_not_read_only")
    if not review:
        blockers.append("postmortem_review_missing")
    elif review.get("status") != "pending_review":
        blockers.append("postmortem_review_not_pending")
    if outcome_errors:
        blockers.append("closed_trade_outcome_validation_errors")
    if source_intake_errors:
        blockers.append("learning_source_intake_validation_errors")
    if review_errors:
        blockers.append("postmortem_review_validation_errors")

    links = (
        _build_links(
            outcome=outcome,
            review=review,
            source_intake=source_intake,
            settings=settings,
        )
        if not blockers
        else []
    )
    missing_required_links = [
        str(link.get("link_key"))
        for link in links
        if link.get("required") is True and link.get("present") is not True
    ]
    if missing_required_links:
        blockers.append("required_links_missing")
    status = "linked" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-8"
    authority["boundary"] = PHASE6_OUTCOME_LINKER_BOUNDARY
    outcome_records = _list(outcome.get("outcome_records"))
    outcome_record = outcome_records[0] if outcome_records and isinstance(outcome_records[0], dict) else {}
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_outcome_linker_schema_version": PHASE6_OUTCOME_LINKER_SCHEMA_VERSION,
        "artifact_type": "outcome_link",
        "artifact_id": "phase6:q6-8:outcome-link:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-8",
        "status": status,
        "generated_at": generated_at,
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
        "event_contract": phase6_event_contract("postmortem_review"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(links),
        "boundary": PHASE6_OUTCOME_LINKER_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "source_trade_ref": outcome.get("closed_trade_ref"),
        "source_outcome_ref": outcome_record.get("outcome_ref"),
        "source_outcome_artifact_ref": SOURCE_OUTCOME_REF,
        "source_review_ref": SOURCE_REVIEW_REF,
        "source_review_state": review.get("review_state"),
        "source_review_status": review.get("status"),
        "source_context_ref": SOURCE_INTAKE_REF,
        "source_context_status": source_intake.get("status"),
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "link_write_allowed": False,
        "learning_write_allowed": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "postmortem_approved": False,
        "approval_state": "not_requested",
        "approval_logged": False,
        "learning_action_count": 0,
        "learning_action_approved_count": 0,
        "complete_outcome_link_created": status == "linked",
        "required_link_keys": list(REQUIRED_LINK_KEYS),
        "optional_link_keys": list(OPTIONAL_LINK_KEYS),
        "link_records": links,
        "linked_ref_count": len(links),
        "required_link_count": len(REQUIRED_LINK_KEYS),
        "required_link_present_count": _count_links(links, required=True, present=True),
        "missing_required_link_count": len(missing_required_links),
        "missing_required_links": missing_required_links,
        "optional_link_count": len(OPTIONAL_LINK_KEYS),
        "optional_link_present_count": _count_links(links, required=False, present=True),
        "missing_optional_link_count": _count_links(links, required=False, present=False),
        "missing_optional_links": [
            str(link.get("link_key"))
            for link in links
            if link.get("required") is False and link.get("present") is not True
        ],
        "reference_only_link_count": len([link for link in links if link.get("reference_only") is True]),
        "raw_payload_copied_count": 0,
        "private_payload_copied_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "source_artifact_mutation_allowed": False,
        "source_artifacts_mutated": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-9 Learning Approval Ledger",
    }
    artifact["validation_errors"] = validate_phase6_outcome_linker(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def _source_ref_errors(prefix: str, source_ref: Any, selected_ref: Any = None) -> list[str]:
    errors: list[str] = []
    refs = [source_ref]
    if selected_ref and isinstance(selected_ref, str) and selected_ref.startswith("data/"):
        refs.append(selected_ref)
    for ref in refs:
        if ref is None:
            continue
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{prefix}_source_ref_invalid")
            continue
        if _has_local_path(ref):
            errors.append(f"{prefix}_local_source_ref")
        if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
            errors.append(f"{prefix}_secret_source_ref")
    return errors


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def validate_phase6_outcome_linker(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_outcome_linker_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "source_trade_ref",
        "source_outcome_ref",
        "source_outcome_artifact_ref",
        "source_review_ref",
        "source_review_state",
        "source_context_ref",
        "source_context_status",
        "link_write_allowed",
        "learning_write_allowed",
        "learning_write_created",
        "knowledge_graph_write_created",
        "postmortem_approved",
        "approval_state",
        "approval_logged",
        "learning_action_count",
        "learning_action_approved_count",
        "complete_outcome_link_created",
        "required_link_keys",
        "optional_link_keys",
        "link_records",
        "linked_ref_count",
        "required_link_count",
        "required_link_present_count",
        "missing_required_link_count",
        "missing_required_links",
        "optional_link_count",
        "optional_link_present_count",
        "missing_optional_link_count",
        "missing_optional_links",
        "reference_only_link_count",
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("outcome_linker_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_outcome_linker_schema_version") != PHASE6_OUTCOME_LINKER_SCHEMA_VERSION:
        errors.append("outcome_linker_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-8"))
    if artifact.get("artifact_type") != "outcome_link":
        errors.append("outcome_linker_artifact_type_mismatch")
    if artifact.get("status") not in {"linked", "blocked", "error"}:
        errors.append("outcome_linker_status_invalid")
    if artifact.get("source_trade_ref") != "q5e7-closed-trade-crude_oil_energy_security_disruption":
        errors.append("source_trade_ref_invalid")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if artifact.get("source_outcome_artifact_ref") != SOURCE_OUTCOME_REF:
        errors.append("source_outcome_artifact_ref_invalid")
    if artifact.get("source_review_ref") != SOURCE_REVIEW_REF:
        errors.append("source_review_ref_invalid")
    if artifact.get("source_review_state") != "review_required":
        errors.append("source_review_state_invalid")
    if artifact.get("source_context_ref") != SOURCE_INTAKE_REF:
        errors.append("source_context_ref_invalid")
    if artifact.get("source_context_status") != "read_only":
        errors.append("source_context_status_invalid")
    if artifact.get("link_write_allowed") is not False:
        errors.append("link_write_allowed")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    if artifact.get("learning_write_created") is not False:
        errors.append("learning_write_created")
    errors.extend(_write_disabled_errors("outcome_linker", artifact))
    if artifact.get("postmortem_approved") is not False:
        errors.append("postmortem_approved")
    if artifact.get("approval_state") != "not_requested":
        errors.append("approval_state_invalid")
    if artifact.get("approval_logged") is not False:
        errors.append("approval_logged")
    if artifact.get("learning_action_count") != 0:
        errors.append("learning_action_count_nonzero")
    if artifact.get("learning_action_approved_count") != 0:
        errors.append("learning_action_approved_count_nonzero")
    if artifact.get("complete_outcome_link_created") is not True:
        errors.append("complete_outcome_link_not_created")
    if set(_list(artifact.get("required_link_keys"))) != set(REQUIRED_LINK_KEYS):
        errors.append("required_link_keys_invalid")
    if set(_list(artifact.get("optional_link_keys"))) != set(OPTIONAL_LINK_KEYS):
        errors.append("optional_link_keys_invalid")

    records = artifact.get("link_records", [])
    if not isinstance(records, list):
        errors.append("link_records_invalid")
        records = []
    if artifact.get("linked_ref_count") != len(records):
        errors.append("linked_ref_count_mismatch")
    if artifact.get("linked_ref_count") < len(REQUIRED_LINK_KEYS):
        errors.append("linked_ref_count_too_low")
    seen_keys: set[str] = set()
    required_present = 0
    optional_present = 0
    missing_required: list[str] = []
    missing_optional: list[str] = []
    reference_only_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("link_record_invalid")
            continue
        link_key = str(record.get("link_key") or "")
        seen_keys.add(link_key)
        required = record.get("required") is True
        present = record.get("present") is True
        if link_key in REQUIRED_LINK_KEYS and not required:
            errors.append(f"required_link_not_required:{link_key}")
        if link_key in OPTIONAL_LINK_KEYS and required:
            errors.append(f"optional_link_marked_required:{link_key}")
        if link_key not in set(REQUIRED_LINK_KEYS) | set(OPTIONAL_LINK_KEYS):
            errors.append(f"link_key_unknown:{link_key}")
        if not record.get("link_role"):
            errors.append(f"link_role_missing:{link_key}")
        if present:
            if required:
                required_present += 1
            else:
                optional_present += 1
            if not record.get("source_ref"):
                errors.append(f"link_source_ref_missing:{link_key}")
            if not record.get("selected_ref"):
                errors.append(f"link_selected_ref_missing:{link_key}")
        elif required:
            missing_required.append(link_key)
        else:
            missing_optional.append(link_key)
            if record.get("safe_missing_optional_context") is not True:
                errors.append(f"optional_missing_not_safe:{link_key}")
            if not record.get("missing_reason"):
                errors.append(f"optional_missing_reason_missing:{link_key}")
        if record.get("reference_only") is not True:
            errors.append(f"link_not_reference_only:{link_key}")
        else:
            reference_only_count += 1
        if record.get("raw_payload_copied") is not False:
            errors.append(f"raw_payload_copied:{link_key}")
            raw_payload_count += 1
        if record.get("private_payload_copied") is not False:
            errors.append(f"private_payload_copied:{link_key}")
            private_payload_count += 1
        if record.get("write_authority") is not False:
            errors.append(f"link_write_authority:{link_key}")
        if record.get("local_path_exposed") is not False:
            errors.append(f"link_local_path_flag:{link_key}")
            local_path_count += 1
        if record.get("secret_ref_exposed") is not False:
            errors.append(f"link_secret_ref_flag:{link_key}")
            secret_ref_count += 1
        ref_errors = _source_ref_errors(
            f"link:{link_key}",
            record.get("source_ref"),
            record.get("selected_ref"),
        )
        errors.extend(ref_errors)
        if any(error.endswith("_local_source_ref") for error in ref_errors):
            local_path_count += 1
        if any(error.endswith("_secret_source_ref") for error in ref_errors):
            secret_ref_count += 1
        for forbidden in ("payload", "raw_payload", "private_payload", "secret_value"):
            if forbidden in record:
                errors.append(f"link_payload_field_forbidden:{link_key}:{forbidden}")
    if seen_keys != set(REQUIRED_LINK_KEYS) | set(OPTIONAL_LINK_KEYS):
        errors.append("link_key_set_mismatch")
    if artifact.get("required_link_count") != len(REQUIRED_LINK_KEYS):
        errors.append("required_link_count_invalid")
    if artifact.get("optional_link_count") != len(OPTIONAL_LINK_KEYS):
        errors.append("optional_link_count_invalid")
    if artifact.get("required_link_present_count") != required_present:
        errors.append("required_link_present_count_mismatch")
    if artifact.get("optional_link_present_count") != optional_present:
        errors.append("optional_link_present_count_mismatch")
    if artifact.get("missing_required_link_count") != len(missing_required):
        errors.append("missing_required_link_count_mismatch")
    if set(_list(artifact.get("missing_required_links"))) != set(missing_required):
        errors.append("missing_required_links_mismatch")
    if artifact.get("missing_optional_link_count") != len(missing_optional):
        errors.append("missing_optional_link_count_mismatch")
    if set(_list(artifact.get("missing_optional_links"))) != set(missing_optional):
        errors.append("missing_optional_links_mismatch")
    if missing_required:
        errors.append("required_links_missing")
    if artifact.get("reference_only_link_count") != reference_only_count:
        errors.append("reference_only_link_count_mismatch")
    if artifact.get("reference_only_link_count") != len(records):
        errors.append("reference_only_link_count_invalid")
    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("raw_payload_copied_count") != 0:
        errors.append("raw_payload_copied_count_nonzero")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != 0:
        errors.append("private_payload_copied_count_nonzero")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("local_path_exposed_count") != 0:
        errors.append("local_path_exposed_count_nonzero")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != 0:
        errors.append("secret_ref_exposed_count_nonzero")
    if artifact.get("source_artifact_mutation_allowed") is not False:
        errors.append("source_artifact_mutation_allowed")
    if artifact.get("source_artifacts_mutated") is not False:
        errors.append("source_artifacts_mutated")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"outcome_linker_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("outcome_linker_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("outcome_linker_unsafe_total_nonzero")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "linked" and blockers:
        errors.append("linked_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "reference-only outcome links",
        "cannot copy private payloads",
        "cannot approve a postmortem",
        "cannot approve learning actions",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot mutate Phase 5 source artifacts",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("outcome_linker_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("outcome_linker_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("outcome_linker_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("outcome_linker_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_outcome_linker_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_OUTCOME_LINKER_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_OUTCOME_LINKER_EVENT_TYPE,
        PHASE6_OUTCOME_LINKER_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "source_trade_ref": output.get("source_trade_ref"),
            "source_outcome_ref": output.get("source_outcome_ref"),
            "source_review_state": output.get("source_review_state"),
            "linked_ref_count": output.get("linked_ref_count"),
            "required_link_present_count": output.get("required_link_present_count"),
            "missing_required_link_count": output.get("missing_required_link_count"),
            "missing_optional_link_count": output.get("missing_optional_link_count"),
            "reference_only_link_count": output.get("reference_only_link_count"),
            "link_write_allowed": output.get("link_write_allowed"),
            "learning_write_created": output.get("learning_write_created"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
            "source_artifacts_mutated": output.get("source_artifacts_mutated"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase6_outcome_linker(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_outcome_linker(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_outcome_linker_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_outcome_linker_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_outcome_linker(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_outcome_linker(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_OUTCOME_LINKER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_trade_ref": output.get("source_trade_ref"),
        "source_outcome_ref": output.get("source_outcome_ref"),
        "source_review_state": output.get("source_review_state"),
        "linked_ref_count": output.get("linked_ref_count"),
        "required_link_present_count": output.get("required_link_present_count"),
        "missing_required_link_count": output.get("missing_required_link_count"),
        "missing_optional_link_count": output.get("missing_optional_link_count"),
        "reference_only_link_count": output.get("reference_only_link_count"),
        "link_write_allowed": output.get("link_write_allowed"),
        "learning_write_created": output.get("learning_write_created"),
        "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
        "source_artifacts_mutated": output.get("source_artifacts_mutated"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
