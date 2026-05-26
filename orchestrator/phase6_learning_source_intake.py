"""Q6-2 read-only learning source intake.

This stage inventories eligible Phase 6 learning inputs from the Q5E guarded
paper lifecycle. It reads Phase 5 artifacts and Event Log refs, discovers
postmortem-due markers, and records source refs for later postmortem work. It
does not create postmortem drafts, approve learning, write a Knowledge Graph,
update scores, mutate policy, or alter Phase 5 source artifacts.
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


PHASE6_LEARNING_SOURCE_INTAKE_SCHEMA_VERSION = 1
PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT = "phase6_learning_source_intake.json"
PHASE6_LEARNING_SOURCE_INTAKE_HISTORY = "phase6_learning_source_intake_history.jsonl"
PHASE6_LEARNING_SOURCE_INTAKE_EVENT_LOG = "phase6_learning_source_intake_events.jsonl"
PHASE6_LEARNING_SOURCE_INTAKE_EVENT_TYPE = "phase6_learning_source_intake_recorded"
PHASE6_LEARNING_SOURCE_INTAKE_COMPONENT = "phase6_learning_source_intake"

TARGET_STRATEGY_FAMILY_KEY = "crude_oil_energy_security_disruption"
TARGET_SIGNAL_ID = "q5e-1-crude-oil-paper-sizing-evidence"

PHASE6_LEARNING_SOURCE_INTAKE_BOUNDARY = (
    "Q6-2 is read-only source intake. It can inventory postmortem-due markers "
    "and source refs for later review, but it cannot create a postmortem draft, "
    "cannot ingest learning state, cannot write learning data, cannot write a "
    "Knowledge Graph, cannot update model weights, cannot update trust scores, "
    "cannot mutate policy, cannot call broker POST routes, cannot call Alpaca "
    "POST routes, cannot call live endpoints, cannot enable live capital, and "
    "cannot count Phase 5 test trades toward Phase 7 proof."
)

SOURCE_REF_PATHS: dict[str, str] = {
    "phase6_readiness": "data/runtime/phase6_readiness.json",
    "phase6_artifact_schema": "docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-2026-05-24.md",
    "phase5_phase6_handoff": "data/runtime/phase5_phase6_handoff.json",
    "postmortem_due": "data/runtime/phase5_guarded_postmortem_due.json",
    "postmortem_due_event_log": "data/runtime/phase5_guarded_postmortem_due_events.jsonl",
    "closed_trade": "data/runtime/phase5_guarded_closed_trade.json",
    "closed_trade_event_log": "data/runtime/phase5_guarded_closed_trade_events.jsonl",
    "open_position": "data/runtime/phase5_guarded_open_position.json",
    "paper_order": "data/runtime/phase5_paper_order_staging_gate.json",
    "paper_order_event_log": "data/runtime/phase5_paper_order_staging_events.jsonl",
    "paper_submit_receipt": "data/runtime/phase5_guarded_paper_submit_receipt.json",
    "paper_submit_receipt_event_log": (
        "data/runtime/phase5_guarded_paper_submit_receipt_events.jsonl"
    ),
    "position_monitor": "data/runtime/phase5_position_monitor.json",
    "position_monitor_event_log": "data/runtime/phase5_position_monitor_events.jsonl",
    "signal_integrity": "data/runtime/signal_integrity_reviews.jsonl",
    "signal_review": "data/runtime/phase5_signal_review.json",
    "strategy_lead": "data/runtime/strategy_lead_shadow_packets.jsonl",
    "risk_agent": "data/runtime/phase5_risk_sizing_reviews.json",
    "risk_policy": "data/runtime/risk_policy_reviews.jsonl",
    "approval_policy": "data/runtime/phase5_approval_policy_decisions.json",
    "execution_policy": "data/runtime/execution_policy_reviews.jsonl",
    "execution_adapter": "data/runtime/phase5_execution_adapter_status.json",
    "yahoo_finance_context": "data/runtime/cockpit-status.json",
    "preference_shadow_context": "data/runtime/preference_shadow_context.json",
    "preference_provenance": "data/runtime/preference_provenance_source_quorum.json",
    "preference_source_promotion": "data/runtime/preference_source_promotion_decisions.json",
    "head_of_quant_annotations": "data/runtime/quantum_oracle_results.jsonl",
}

REQUIRED_SOURCE_KEYS: tuple[str, ...] = (
    "phase6_readiness",
    "phase5_phase6_handoff",
    "postmortem_due",
    "closed_trade",
    "paper_order",
    "paper_submit_receipt",
    "position_monitor",
    "risk_agent",
    "approval_policy",
    "execution_adapter",
    "signal_integrity",
)

OPTIONAL_SOURCE_KEYS: tuple[str, ...] = (
    "strategy_lead",
    "risk_policy",
    "execution_policy",
    "signal_review",
    "yahoo_finance_context",
    "preference_shadow_context",
    "preference_provenance",
    "preference_source_promotion",
    "head_of_quant_annotations",
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


def _read_jsonl(ref: str, settings: Settings | None = None) -> list[dict[str, Any]]:
    path = _path(ref, settings)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _exists(ref: str, settings: Settings | None = None) -> bool:
    return _path(ref, settings).exists()


def phase6_learning_source_intake_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT,
        runtime / PHASE6_LEARNING_SOURCE_INTAKE_HISTORY,
        runtime / PHASE6_LEARNING_SOURCE_INTAKE_EVENT_LOG,
    )


def _event_count(ref: str, settings: Settings | None = None) -> int:
    path = _path(ref, settings)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _select_record(records: list[dict[str, Any]], predicate: Any) -> dict[str, Any] | None:
    for record in reversed(records):
        if predicate(record):
            return record
    return None


def _source_record(
    key: str,
    *,
    settings: Settings,
    required: bool,
    status: str | None = None,
    selected_ref: str | None = None,
    record_count: int | None = None,
    event_log_ref: str | None = None,
    missing_reason: str | None = None,
) -> dict[str, Any]:
    ref = SOURCE_REF_PATHS[key]
    present = _exists(ref, settings)
    return {
        "source_key": key,
        "required": required,
        "present": present,
        "source_ref": ref,
        "status": status or ("present" if present else "missing"),
        "selected_ref": selected_ref,
        "record_count": int(record_count if record_count is not None else int(present)),
        "event_log_ref": event_log_ref,
        "event_log_event_count": _event_count(event_log_ref, settings) if event_log_ref else 0,
        "missing_reason": missing_reason if not present else None,
        "write_authority": False,
    }


def _postmortem_due_records(settings: Settings) -> list[dict[str, Any]]:
    due = _read_json(SOURCE_REF_PATHS["postmortem_due"], settings) or {}
    if not due:
        return []
    if due.get("status") != "postmortem_due":
        return []
    return [
        {
            "postmortem_due_ref": due.get("postmortem_due_ref"),
            "source_closed_trade_ref": due.get("source_closed_trade_ref"),
            "source_position_ref": due.get("source_position_ref"),
            "source_order_ref": due.get("source_order_ref"),
            "strategy_family_key": due.get("strategy_family_key"),
            "instrument": due.get("instrument"),
            "side": due.get("side"),
            "quantity": due.get("quantity"),
            "risk_size_gbp": due.get("risk_size_gbp"),
            "realized_pnl_gbp": due.get("realized_pnl_gbp"),
            "r_multiple": due.get("r_multiple"),
            "postmortem_due_at": due.get("postmortem_due_at"),
            "postmortem_status": due.get("postmortem_status"),
            "event_log_ref": SOURCE_REF_PATHS["postmortem_due_event_log"],
            "event_log_correlation_id": due.get("event_log_correlation_id"),
            "phase5_test_trade": True,
            "phase7_proof_credit_allowed": due.get("phase7_proof_credit_allowed") is True,
            "learning_write_created": False,
        }
    ]


def _target_signal_integrity(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["signal_integrity"], settings)
    return _select_record(
        records,
        lambda record: record.get("source_signal_id") == TARGET_SIGNAL_ID
        or record.get("instrument_focus") == "crude_oil_or_energy_transport",
    )


def _target_strategy_lead(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["strategy_lead"], settings)
    return _select_record(
        records,
        lambda record: record.get("watch_focus") == "crude_oil_or_energy_transport",
    ) or (records[-1] if records else None)


def _target_risk_policy(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["risk_policy"], settings)
    return _select_record(
        records,
        lambda record: record.get("instrument") in {"crude_oil", "USO options watch"},
    ) or (records[-1] if records else None)


def _target_execution_policy(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["execution_policy"], settings)
    return _select_record(
        records,
        lambda record: record.get("instrument") in {"crude_oil", "USO options watch"}
        or record.get("selected_venue") == "alpaca_paper",
    ) or (records[-1] if records else None)


def _target_quantum_annotation(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["head_of_quant_annotations"], settings)
    return records[-1].get("result") if records and isinstance(records[-1].get("result"), dict) else None


def _source_records(settings: Settings) -> list[dict[str, Any]]:
    risk_bundle = _read_json(SOURCE_REF_PATHS["risk_agent"], settings) or {}
    risk_reviews = risk_bundle.get("reviews", []) if isinstance(risk_bundle, dict) else []
    risk_review = _select_record(
        [record for record in risk_reviews if isinstance(record, dict)],
        lambda record: record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY,
    )

    approval_bundle = _read_json(SOURCE_REF_PATHS["approval_policy"], settings) or {}
    approval_records = approval_bundle.get("decisions", []) if isinstance(approval_bundle, dict) else []
    approval_record = _select_record(
        [record for record in approval_records if isinstance(record, dict)],
        lambda record: record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY,
    )

    staging_bundle = _read_json(SOURCE_REF_PATHS["paper_order"], settings) or {}
    staging_records = staging_bundle.get("records", []) if isinstance(staging_bundle, dict) else []
    staging_record = _select_record(
        [record for record in staging_records if isinstance(record, dict)],
        lambda record: record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY,
    )

    position_bundle = _read_json(SOURCE_REF_PATHS["position_monitor"], settings) or {}
    position_records = position_bundle.get("records", []) if isinstance(position_bundle, dict) else []

    submit_receipt = _read_json(SOURCE_REF_PATHS["paper_submit_receipt"], settings) or {}
    closed_trade = _read_json(SOURCE_REF_PATHS["closed_trade"], settings) or {}
    postmortem_due = _read_json(SOURCE_REF_PATHS["postmortem_due"], settings) or {}
    execution_adapter = _read_json(SOURCE_REF_PATHS["execution_adapter"], settings) or {}
    signal_review = _read_json(SOURCE_REF_PATHS["signal_review"], settings) or {}
    yahoo_context = _read_json(SOURCE_REF_PATHS["yahoo_finance_context"], settings) or {}
    preference_shadow = _read_json(SOURCE_REF_PATHS["preference_shadow_context"], settings) or {}
    preference_provenance = _read_json(SOURCE_REF_PATHS["preference_provenance"], settings) or {}
    preference_promotion = _read_json(SOURCE_REF_PATHS["preference_source_promotion"], settings) or {}
    signal_integrity = _target_signal_integrity(settings)
    strategy_lead = _target_strategy_lead(settings)
    risk_policy = _target_risk_policy(settings)
    execution_policy = _target_execution_policy(settings)
    quantum_annotation = _target_quantum_annotation(settings)

    return [
        _source_record(
            "phase6_readiness",
            settings=settings,
            required=True,
            status=str((_read_json(SOURCE_REF_PATHS["phase6_readiness"], settings) or {}).get("status")),
        ),
        _source_record(
            "phase5_phase6_handoff",
            settings=settings,
            required=True,
            status=str((_read_json(SOURCE_REF_PATHS["phase5_phase6_handoff"], settings) or {}).get("status")),
        ),
        _source_record(
            "postmortem_due",
            settings=settings,
            required=True,
            status=str(postmortem_due.get("status") or "missing"),
            selected_ref=postmortem_due.get("postmortem_due_ref"),
            event_log_ref=SOURCE_REF_PATHS["postmortem_due_event_log"],
        ),
        _source_record(
            "closed_trade",
            settings=settings,
            required=True,
            status=str(closed_trade.get("status") or "missing"),
            selected_ref=closed_trade.get("closed_trade_ref"),
            event_log_ref=SOURCE_REF_PATHS["closed_trade_event_log"],
        ),
        _source_record(
            "paper_order",
            settings=settings,
            required=True,
            status=str(staging_record.get("status") if staging_record else "missing_target_record"),
            selected_ref=str(staging_record.get("artifact_id")) if staging_record else None,
            record_count=len(staging_records),
            event_log_ref=SOURCE_REF_PATHS["paper_order_event_log"],
        ),
        _source_record(
            "paper_submit_receipt",
            settings=settings,
            required=True,
            status=str(submit_receipt.get("status") or "missing"),
            selected_ref=submit_receipt.get("broker_receipt_ref"),
            event_log_ref=SOURCE_REF_PATHS["paper_submit_receipt_event_log"],
        ),
        _source_record(
            "position_monitor",
            settings=settings,
            required=True,
            status=str(position_bundle.get("status") or "missing"),
            selected_ref=postmortem_due.get("source_closed_trade_ref"),
            record_count=len(position_records),
            event_log_ref=SOURCE_REF_PATHS["position_monitor_event_log"],
        ),
        _source_record(
            "signal_integrity",
            settings=settings,
            required=True,
            status=str(signal_integrity.get("status") if signal_integrity else "missing_target_record"),
            selected_ref=str(signal_integrity.get("review_id")) if signal_integrity else None,
            record_count=len(_read_jsonl(SOURCE_REF_PATHS["signal_integrity"], settings)),
        ),
        _source_record(
            "risk_agent",
            settings=settings,
            required=True,
            status=str(risk_review.get("status") if risk_review else "missing_target_record"),
            selected_ref=str(risk_review.get("artifact_id")) if risk_review else None,
            record_count=len(risk_reviews),
        ),
        _source_record(
            "approval_policy",
            settings=settings,
            required=True,
            status=str(approval_record.get("status") if approval_record else "missing_target_record"),
            selected_ref=str(approval_record.get("artifact_id")) if approval_record else None,
            record_count=len(approval_records),
        ),
        _source_record(
            "execution_adapter",
            settings=settings,
            required=True,
            status=str(execution_adapter.get("status") or "missing"),
            selected_ref="phase5:q5-5:execution-adapter:alpaca_paper",
        ),
        _source_record(
            "strategy_lead",
            settings=settings,
            required=False,
            status=str(strategy_lead.get("status") if strategy_lead else "missing_optional"),
            selected_ref=str(strategy_lead.get("packet_id")) if strategy_lead else None,
            record_count=len(_read_jsonl(SOURCE_REF_PATHS["strategy_lead"], settings)),
            missing_reason="strategy_lead_shadow_packet_optional_for_q6_2",
        ),
        _source_record(
            "risk_policy",
            settings=settings,
            required=False,
            status=str(risk_policy.get("status") if risk_policy else "missing_optional"),
            selected_ref=str(risk_policy.get("review_id")) if risk_policy else None,
            record_count=len(_read_jsonl(SOURCE_REF_PATHS["risk_policy"], settings)),
            missing_reason="risk_policy_jsonl_optional_context",
        ),
        _source_record(
            "execution_policy",
            settings=settings,
            required=False,
            status=str(execution_policy.get("status") if execution_policy else "missing_optional"),
            selected_ref=str(execution_policy.get("review_id")) if execution_policy else None,
            record_count=len(_read_jsonl(SOURCE_REF_PATHS["execution_policy"], settings)),
            missing_reason="execution_policy_jsonl_optional_context",
        ),
        _source_record(
            "signal_review",
            settings=settings,
            required=False,
            status=str(signal_review.get("status") or "missing_optional"),
            selected_ref="phase5:q5-12:signal-review:crude_oil_energy_security_disruption",
            record_count=len(signal_review.get("records", []) or []) if signal_review else 0,
            event_log_ref="data/runtime/phase5_signal_review_events.jsonl",
            missing_reason="signal_review_optional_visibility_context",
        ),
        _source_record(
            "yahoo_finance_context",
            settings=settings,
            required=False,
            status=str(yahoo_context.get("yahoo_finance", {}).get("status") or "deferred"),
            selected_ref="cockpit_status.yahoo_finance",
            missing_reason="yahoo_finance_context_optional_or_deferred",
        ),
        _source_record(
            "preference_shadow_context",
            settings=settings,
            required=False,
            status=str(preference_shadow.get("status") or "missing_optional"),
            selected_ref=str(preference_shadow.get("artifact_id")) if preference_shadow else None,
            missing_reason="preference_shadow_context_optional",
        ),
        _source_record(
            "preference_provenance",
            settings=settings,
            required=False,
            status=str(preference_provenance.get("status") or "missing_optional"),
            selected_ref=str(preference_provenance.get("artifact_id")) if preference_provenance else None,
            missing_reason="preference_provenance_optional",
        ),
        _source_record(
            "preference_source_promotion",
            settings=settings,
            required=False,
            status=str(preference_promotion.get("status") or "missing_optional"),
            selected_ref=str(preference_promotion.get("artifact_id")) if preference_promotion else None,
            missing_reason="preference_source_promotion_optional",
        ),
        _source_record(
            "head_of_quant_annotations",
            settings=settings,
            required=False,
            status=str(quantum_annotation.get("status") if quantum_annotation else "missing_optional"),
            selected_ref=str(quantum_annotation.get("result_id")) if quantum_annotation else None,
            record_count=len(_read_jsonl(SOURCE_REF_PATHS["head_of_quant_annotations"], settings)),
            missing_reason="head_of_quant_shadow_annotation_optional",
        ),
    ]


def _required_source_blockers(source_records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in source_records:
        if not record.get("required"):
            continue
        if record.get("present") is not True:
            blockers.append(f"required_source_missing:{record.get('source_key')}")
        if str(record.get("status") or "").startswith("missing"):
            blockers.append(f"required_source_target_missing:{record.get('source_key')}")
    return blockers


def _provenance_from_records(source_records: list[dict[str, Any]]) -> dict[str, Any]:
    refs = []
    for record in source_records:
        if record.get("present"):
            refs.append(str(record["source_ref"]))
        if record.get("event_log_ref") and int(record.get("event_log_event_count", 0) or 0) > 0:
            refs.append(str(record["event_log_ref"]))
    provenance = phase6_provenance(tuple(dict.fromkeys(refs)))
    provenance["execution_evidence_refs"] = [
        SOURCE_REF_PATHS["paper_order"],
        SOURCE_REF_PATHS["paper_submit_receipt"],
        SOURCE_REF_PATHS["closed_trade"],
        SOURCE_REF_PATHS["postmortem_due"],
        SOURCE_REF_PATHS["position_monitor"],
    ]
    provenance["market_context_refs"] = [
        SOURCE_REF_PATHS["signal_integrity"],
        SOURCE_REF_PATHS["yahoo_finance_context"],
        SOURCE_REF_PATHS["preference_shadow_context"],
        SOURCE_REF_PATHS["preference_provenance"],
    ]
    provenance["model_interpretation_refs"] = [
        SOURCE_REF_PATHS["strategy_lead"],
        SOURCE_REF_PATHS["head_of_quant_annotations"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REF_PATHS["risk_agent"],
        SOURCE_REF_PATHS["approval_policy"],
        SOURCE_REF_PATHS["execution_policy"],
        SOURCE_REF_PATHS["signal_review"],
    ]
    return provenance


def _learning_disabled_fields() -> dict[str, bool]:
    return {
        "postmortem_draft_created": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "phase5_source_artifact_mutation_allowed": False,
    }


def build_phase6_learning_source_intake(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    postmortem_due_records = _postmortem_due_records(settings)
    source_records = _source_records(settings)
    blockers = _required_source_blockers(source_records)
    if not postmortem_due_records:
        blockers.append("postmortem_due_marker_missing")
    optional_missing = [
        str(record["source_key"])
        for record in source_records
        if not record.get("required") and record.get("present") is not True
    ]
    status = "read_only" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-2"
    authority["boundary"] = PHASE6_LEARNING_SOURCE_INTAKE_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_learning_source_intake_schema_version": (
            PHASE6_LEARNING_SOURCE_INTAKE_SCHEMA_VERSION
        ),
        "artifact_type": "learning_source_inventory",
        "artifact_id": "phase6:q6-2:learning-source-intake",
        "phase": "Q6",
        "stage": "Q6-2",
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
        "event_contract": phase6_event_contract("artifact_schema"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance_from_records(source_records),
        "boundary": PHASE6_LEARNING_SOURCE_INTAKE_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_learning_disabled_fields(),
        "postmortem_due_count": len(postmortem_due_records),
        "postmortem_due_records": postmortem_due_records,
        "source_inventory_write_allowed": False,
        "source_ref_count": len(
            [record for record in source_records if record.get("present") is True]
        ),
        "source_records": source_records,
        "source_record_count": len(source_records),
        "required_source_count": len(REQUIRED_SOURCE_KEYS),
        "required_source_present_count": len(
            [
                record
                for record in source_records
                if record.get("required") and record.get("present") is True
            ]
        ),
        "optional_source_count": len(OPTIONAL_SOURCE_KEYS),
        "optional_source_present_count": len(
            [
                record
                for record in source_records
                if not record.get("required") and record.get("present") is True
            ]
        ),
        "optional_ref_missing_count": len(optional_missing),
        "missing_optional_refs": optional_missing,
        "missing_optional_refs_fail_open": False,
        "phase5_source_artifacts_mutated": False,
        "learning_input_inventory_only": True,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-3 Closed Trade And Outcome Schema",
    }
    artifact["validation_errors"] = validate_phase6_learning_source_intake(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_phase6_learning_source_intake(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_learning_source_intake_schema_version",
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
        "postmortem_due_count",
        "postmortem_due_records",
        "source_inventory_write_allowed",
        "source_ref_count",
        "source_records",
        "source_record_count",
        "required_source_count",
        "required_source_present_count",
        "optional_ref_missing_count",
        "missing_optional_refs",
        "missing_optional_refs_fail_open",
        "phase5_source_artifacts_mutated",
        "learning_input_inventory_only",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("learning_source_intake_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_learning_source_intake_schema_version") != (
        PHASE6_LEARNING_SOURCE_INTAKE_SCHEMA_VERSION
    ):
        errors.append("learning_source_intake_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-2"))
    if artifact.get("artifact_type") != "learning_source_inventory":
        errors.append("learning_source_intake_artifact_type_mismatch")
    if artifact.get("status") not in {"read_only", "blocked", "error"}:
        errors.append("learning_source_intake_status_invalid")
    if artifact.get("source_inventory_write_allowed") is not False:
        errors.append("source_inventory_write_allowed")
    for field, value in _learning_disabled_fields().items():
        if artifact.get(field) is not value:
            errors.append(f"learning_source_intake_write_enabled:{field}")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"learning_source_intake_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("learning_source_intake_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("learning_source_intake_unsafe_total_nonzero")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("missing_optional_refs_fail_open") is not False:
        errors.append("missing_optional_refs_fail_open")
    if artifact.get("phase5_source_artifacts_mutated") is not False:
        errors.append("phase5_source_artifacts_mutated")
    if artifact.get("learning_input_inventory_only") is not True:
        errors.append("learning_input_inventory_only_false")
    due_records = artifact.get("postmortem_due_records", [])
    if not isinstance(due_records, list):
        errors.append("postmortem_due_records_invalid")
        due_records = []
    if artifact.get("postmortem_due_count") != len(due_records):
        errors.append("postmortem_due_count_mismatch")
    if artifact.get("postmortem_due_count", 0) < 1:
        errors.append("postmortem_due_marker_missing")
    for record in due_records:
        if not isinstance(record, dict):
            errors.append("postmortem_due_record_invalid")
            continue
        if record.get("postmortem_status") != "postmortem_due":
            errors.append("postmortem_due_status_invalid")
        if record.get("phase7_proof_credit_allowed") is not False:
            errors.append("postmortem_due_phase7_credit_allowed")
        if record.get("learning_write_created") is not False:
            errors.append("postmortem_due_learning_write_created")
    source_records = artifact.get("source_records", [])
    if not isinstance(source_records, list):
        errors.append("source_records_invalid")
        source_records = []
    if artifact.get("source_record_count") != len(source_records):
        errors.append("source_record_count_mismatch")
    source_keys = {record.get("source_key") for record in source_records if isinstance(record, dict)}
    for key in REQUIRED_SOURCE_KEYS:
        if key not in source_keys:
            errors.append(f"required_source_record_missing:{key}")
    required_present = [
        record
        for record in source_records
        if isinstance(record, dict) and record.get("required") and record.get("present") is True
    ]
    if artifact.get("required_source_present_count") != len(required_present):
        errors.append("required_source_present_count_mismatch")
    if artifact.get("required_source_present_count") != artifact.get("required_source_count"):
        errors.append("required_source_missing")
    for record in source_records:
        if not isinstance(record, dict):
            continue
        if record.get("required") and record.get("present") is not True:
            errors.append(f"required_source_missing:{record.get('source_key')}")
        if record.get("write_authority") is not False:
            errors.append(f"source_record_write_authority:{record.get('source_key')}")
        ref = str(record.get("source_ref") or "")
        if ref.startswith("/") or ref.startswith("~"):
            errors.append(f"source_ref_local_path:{record.get('source_key')}")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "read_only" and blockers:
        errors.append("read_only_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "read-only source intake",
        "cannot create a postmortem draft",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot enable live capital",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("learning_source_intake_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("learning_source_intake_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("learning_source_intake_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("learning_source_intake_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_learning_source_intake_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_LEARNING_SOURCE_INTAKE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_LEARNING_SOURCE_INTAKE_EVENT_TYPE,
        PHASE6_LEARNING_SOURCE_INTAKE_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "source_ref_count": output.get("source_ref_count"),
            "required_source_present_count": output.get("required_source_present_count"),
            "optional_ref_missing_count": output.get("optional_ref_missing_count"),
            "learning_write_created": output.get("learning_write_created"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
            "phase5_source_artifacts_mutated": output.get("phase5_source_artifacts_mutated"),
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
    output["validation_errors"] = validate_phase6_learning_source_intake(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_learning_source_intake(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_learning_source_intake_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_learning_source_intake_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_learning_source_intake(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_learning_source_intake(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_LEARNING_SOURCE_INTAKE_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "source_ref_count": output.get("source_ref_count"),
        "required_source_present_count": output.get("required_source_present_count"),
        "optional_ref_missing_count": output.get("optional_ref_missing_count"),
        "learning_write_created": output.get("learning_write_created"),
        "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
        "phase5_source_artifacts_mutated": output.get("phase5_source_artifacts_mutated"),
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
