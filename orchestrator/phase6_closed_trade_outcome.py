"""Q6-3 closed-trade outcome normalization.

This stage turns the Q5E guarded closed-trade lifecycle into a canonical
Phase 6 outcome record. It is still read-only: it separates local lifecycle
state from broker truth, records unknown/deferred postmortem fields, and does
not write learning state, Knowledge Graph entries, model weights, trust scores,
policy, broker routes, or Phase 5 source artifacts.
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
from orchestrator.phase6_learning_source_intake import (
    PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT,
    SOURCE_REF_PATHS,
    TARGET_SIGNAL_ID,
    TARGET_STRATEGY_FAMILY_KEY,
    validate_phase6_learning_source_intake,
)


PHASE6_CLOSED_TRADE_OUTCOME_SCHEMA_VERSION = 1
PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT = "phase6_closed_trade_outcome.json"
PHASE6_CLOSED_TRADE_OUTCOME_HISTORY = "phase6_closed_trade_outcome_history.jsonl"
PHASE6_CLOSED_TRADE_OUTCOME_EVENT_LOG = "phase6_closed_trade_outcome_events.jsonl"
PHASE6_CLOSED_TRADE_OUTCOME_EVENT_TYPE = "phase6_closed_trade_outcome_recorded"
PHASE6_CLOSED_TRADE_OUTCOME_COMPONENT = "phase6_closed_trade_outcome"

SOURCE_INTAKE_REF = f"data/runtime/{PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT}"

PHASE6_CLOSED_TRADE_OUTCOME_BOUNDARY = (
    "Q6-3 normalizes a closed paper-trade outcome as read-only evidence. It "
    "can cite local lifecycle, risk, execution, receipt, market, and source "
    "context, but it cannot create a postmortem draft, cannot write learning "
    "data, cannot write a Knowledge Graph, cannot update model weights, cannot "
    "update trust scores, cannot mutate policy, cannot treat local guarded "
    "lifecycle state as broker fill truth, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot call live endpoints, cannot enable "
    "live capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

UNKNOWN_FIELD_SENTINELS: tuple[str, ...] = (
    "actual_catalyst",
    "broker_fill_id",
    "broker_fill_price",
    "broker_fill_timestamp",
    "postmortem_root_cause",
)

DEFERRED_FIELD_SENTINELS: tuple[str, ...] = (
    "actual_catalyst",
    "pricing_read",
    "regime_read",
    "execution_quality_assessment",
    "source_quality_assessment",
    "learning_actions",
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


def _event_count(ref: str, settings: Settings | None = None) -> int:
    path = _path(ref, settings)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def phase6_closed_trade_outcome_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT,
        runtime / PHASE6_CLOSED_TRADE_OUTCOME_HISTORY,
        runtime / PHASE6_CLOSED_TRADE_OUTCOME_EVENT_LOG,
    )


def _select_record(records: list[dict[str, Any]], predicate: Any) -> dict[str, Any] | None:
    for record in reversed(records):
        if predicate(record):
            return record
    return None


def _target_signal_integrity(settings: Settings) -> dict[str, Any] | None:
    records = _read_jsonl(SOURCE_REF_PATHS["signal_integrity"], settings)
    return _select_record(
        records,
        lambda record: record.get("source_signal_id") == TARGET_SIGNAL_ID
        or record.get("instrument_focus") == "crude_oil_or_energy_transport",
    )


def _target_bundle_record(
    bundle: dict[str, Any],
    key: str,
    *,
    target_family: str = TARGET_STRATEGY_FAMILY_KEY,
) -> dict[str, Any] | None:
    records = bundle.get(key, []) if isinstance(bundle, dict) else []
    if not isinstance(records, list):
        return None
    return _select_record(
        [record for record in records if isinstance(record, dict)],
        lambda record: record.get("strategy_family_key") == target_family,
    )


def _target_position_monitor_record(
    position_bundle: dict[str, Any],
    closed_trade_ref: str | None,
) -> dict[str, Any] | None:
    records = position_bundle.get("records", []) if isinstance(position_bundle, dict) else []
    if not isinstance(records, list):
        return None
    return _select_record(
        [record for record in records if isinstance(record, dict)],
        lambda record: record.get("closed_trade_ref") == closed_trade_ref
        or record.get("artifact_id", "").endswith(str(closed_trade_ref or "")),
    )


def _target_execution_adapter(
    execution_bundle: dict[str, Any],
    venue_key: str | None,
) -> dict[str, Any] | None:
    records = execution_bundle.get("statuses", []) if isinstance(execution_bundle, dict) else []
    if not isinstance(records, list):
        return None
    return _select_record(
        [record for record in records if isinstance(record, dict)],
        lambda record: record.get("venue_key") == venue_key
        or record.get("artifact_id") == "phase5:q5-5:execution-adapter:alpaca_paper",
    )


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _outcome_bucket(realized_pnl_gbp: float | None) -> str:
    if realized_pnl_gbp is None:
        return "unknown"
    if realized_pnl_gbp > 0:
        return "positive"
    if realized_pnl_gbp < 0:
        return "negative"
    return "flat"


def _learning_disabled_fields() -> dict[str, bool]:
    return {
        "postmortem_draft_created": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "phase5_source_artifact_mutation_allowed": False,
        "phase5_source_artifacts_mutated": False,
        "broker_truth_accepted_as_fill_truth": False,
    }


def _provenance() -> dict[str, Any]:
    source_refs = (
        SOURCE_INTAKE_REF,
        SOURCE_REF_PATHS["closed_trade"],
        SOURCE_REF_PATHS["closed_trade_event_log"],
        SOURCE_REF_PATHS["postmortem_due"],
        SOURCE_REF_PATHS["postmortem_due_event_log"],
        SOURCE_REF_PATHS["paper_order"],
        SOURCE_REF_PATHS["paper_order_event_log"],
        SOURCE_REF_PATHS["paper_submit_receipt"],
        SOURCE_REF_PATHS["paper_submit_receipt_event_log"],
        SOURCE_REF_PATHS["position_monitor"],
        SOURCE_REF_PATHS["position_monitor_event_log"],
        SOURCE_REF_PATHS["risk_agent"],
        SOURCE_REF_PATHS["approval_policy"],
        SOURCE_REF_PATHS["execution_adapter"],
        SOURCE_REF_PATHS["signal_integrity"],
        SOURCE_REF_PATHS["yahoo_finance_context"],
        SOURCE_REF_PATHS["preference_shadow_context"],
        SOURCE_REF_PATHS["preference_provenance"],
        SOURCE_REF_PATHS["preference_source_promotion"],
        SOURCE_REF_PATHS["head_of_quant_annotations"],
    )
    provenance = phase6_provenance(source_refs)
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
        SOURCE_REF_PATHS["preference_source_promotion"],
    ]
    provenance["model_interpretation_refs"] = [
        SOURCE_REF_PATHS["head_of_quant_annotations"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REF_PATHS["risk_agent"],
        SOURCE_REF_PATHS["approval_policy"],
        SOURCE_REF_PATHS["execution_adapter"],
    ]
    return provenance


def _build_outcome_record(settings: Settings) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    source_intake = _read_json(SOURCE_INTAKE_REF, settings) or {}
    closed_trade = _read_json(SOURCE_REF_PATHS["closed_trade"], settings) or {}
    postmortem_due = _read_json(SOURCE_REF_PATHS["postmortem_due"], settings) or {}
    receipt = _read_json(SOURCE_REF_PATHS["paper_submit_receipt"], settings) or {}
    staging_bundle = _read_json(SOURCE_REF_PATHS["paper_order"], settings) or {}
    risk_bundle = _read_json(SOURCE_REF_PATHS["risk_agent"], settings) or {}
    approval_bundle = _read_json(SOURCE_REF_PATHS["approval_policy"], settings) or {}
    execution_bundle = _read_json(SOURCE_REF_PATHS["execution_adapter"], settings) or {}
    position_bundle = _read_json(SOURCE_REF_PATHS["position_monitor"], settings) or {}
    cockpit = _read_json(SOURCE_REF_PATHS["yahoo_finance_context"], settings) or {}
    preference_shadow = _read_json(SOURCE_REF_PATHS["preference_shadow_context"], settings) or {}
    preference_provenance = _read_json(SOURCE_REF_PATHS["preference_provenance"], settings) or {}
    preference_promotion = _read_json(SOURCE_REF_PATHS["preference_source_promotion"], settings) or {}

    if not source_intake:
        blockers.append("source_intake_missing")
    elif source_intake.get("status") != "read_only":
        blockers.append("source_intake_not_read_only")
    if not closed_trade or closed_trade.get("status") != "closed_trade":
        blockers.append("closed_trade_missing")
    if not postmortem_due or postmortem_due.get("status") != "postmortem_due":
        blockers.append("postmortem_due_missing")
    if not receipt or receipt.get("status") != "submitted_paper_order":
        blockers.append("paper_submit_receipt_missing")

    closed_trade_ref = closed_trade.get("closed_trade_ref")
    staging_record = _target_bundle_record(staging_bundle, "records")
    risk_record = _target_bundle_record(risk_bundle, "reviews")
    approval_record = _target_bundle_record(approval_bundle, "decisions")
    position_record = _target_position_monitor_record(position_bundle, closed_trade_ref)
    execution_record = _target_execution_adapter(
        execution_bundle,
        str(receipt.get("selected_venue") or staging_record.get("selected_venue"))
        if staging_record
        else str(receipt.get("selected_venue") or ""),
    )
    signal_integrity = _target_signal_integrity(settings)

    if not staging_record:
        blockers.append("staged_paper_order_missing")
    if not risk_record:
        blockers.append("risk_record_missing")
    if not approval_record:
        blockers.append("approval_policy_record_missing")
    if not execution_record:
        blockers.append("execution_adapter_record_missing")
    if not signal_integrity:
        blockers.append("signal_integrity_record_missing")

    if blockers:
        return None, blockers

    realized_pnl_gbp = _float_or_none(closed_trade.get("realized_pnl_gbp"))
    outcome_ref = f"q6-3-outcome-{closed_trade_ref}"
    deferred_fields = list(DEFERRED_FIELD_SENTINELS)
    unknown_fields = list(UNKNOWN_FIELD_SENTINELS)
    market_confirmation_policy = signal_integrity.get("market_confirmation_policy", {})
    preference_policy = signal_integrity.get("preference_context_policy", {})
    yahoo_status = cockpit.get("yahoo_finance", {}) if isinstance(cockpit, dict) else {}
    preference_status = cockpit.get("preference_mcp", {}) if isinstance(cockpit, dict) else {}

    record = {
        "outcome_ref": outcome_ref,
        "source_closed_trade_ref": closed_trade_ref,
        "source_postmortem_due_ref": postmortem_due.get("postmortem_due_ref"),
        "source_order_ref": closed_trade.get("source_order_ref") or receipt.get("submitted_order_ref"),
        "source_position_ref": closed_trade.get("source_position_ref"),
        "source_receipt_ref": receipt.get("broker_receipt_ref"),
        "strategy_family_key": closed_trade.get("strategy_family_key"),
        "instrument": closed_trade.get("instrument"),
        "side": closed_trade.get("side"),
        "quantity": closed_trade.get("quantity"),
        "thesis": {
            "strategy_family_key": approval_record.get("strategy_family_key"),
            "primary_instrument": approval_record.get("primary_instrument"),
            "expected_catalyst_classes": _list_or_empty(approval_record.get("catalyst_classes")),
            "expected_catalyst_status": "source_classes_available_specific_event_deferred",
            "expected_catalyst": None,
            "actual_catalyst_status": "unknown_pending_postmortem_analysis",
            "actual_catalyst": None,
        },
        "entry_state": {
            "submitted_at": receipt.get("submitted_at"),
            "opened_at": closed_trade.get("opened_at"),
            "entry_price": closed_trade.get("entry_price"),
            "submitted_order_ref": receipt.get("submitted_order_ref"),
            "position_ref": closed_trade.get("source_position_ref"),
            "local_lifecycle_state": "submitted_then_opened_local_guarded_lifecycle",
        },
        "exit_state": {
            "closed_at": closed_trade.get("closed_at"),
            "exit_price": closed_trade.get("exit_price"),
            "close_reason": closed_trade.get("close_reason"),
            "closed_trade_state": closed_trade.get("closed_trade_state"),
            "postmortem_status": postmortem_due.get("postmortem_status"),
        },
        "sizing": {
            "risk_decision": risk_record.get("risk_decision"),
            "paper_size_eligible": risk_record.get("paper_size_eligible"),
            "risk_score": risk_record.get("risk_score"),
            "proposed_risk_gbp": risk_record.get("proposed_risk_gbp"),
            "risk_size_gbp": closed_trade.get("risk_size_gbp"),
            "max_loss_gbp": staging_record.get("max_loss_gbp"),
            "notional_gbp": receipt.get("notional_gbp"),
            "quantity": closed_trade.get("quantity"),
            "r_multiple": closed_trade.get("r_multiple"),
            "realized_pnl_gbp": realized_pnl_gbp,
        },
        "risk_decision": {
            "risk_record_ref": risk_record.get("artifact_id"),
            "status": risk_record.get("status"),
            "risk_decision": risk_record.get("risk_decision"),
            "market_confirmation_policy": risk_record.get("market_confirmation_policy"),
            "source_summary": risk_record.get("source_summary"),
            "invalidation_conditions": _list_or_empty(risk_record.get("invalidation_conditions")),
            "no_trade_conditions": _list_or_empty(risk_record.get("no_trade_conditions")),
        },
        "execution_path": {
            "selected_venue": receipt.get("selected_venue") or staging_record.get("selected_venue"),
            "broker_adapter": receipt.get("broker_adapter"),
            "path_key": receipt.get("path_key"),
            "order_type": receipt.get("order_type") or staging_record.get("order_type"),
            "time_in_force": receipt.get("time_in_force") or staging_record.get("time_in_force"),
            "idempotency_key": receipt.get("idempotency_key") or staging_record.get("idempotency_key"),
            "staging_state": staging_record.get("order_state"),
            "receipt_state": receipt.get("broker_receipt_state"),
            "execution_adapter_read_health": execution_record.get("read_health"),
            "execution_adapter_write_health": execution_record.get("write_health"),
            "permission_scope": execution_record.get("permission_scope"),
        },
        "receipt_and_prewrite_refs": {
            "paper_order_event_log_ref": SOURCE_REF_PATHS["paper_order_event_log"],
            "paper_order_event_count": _event_count(SOURCE_REF_PATHS["paper_order_event_log"], settings),
            "paper_submit_receipt_event_log_ref": SOURCE_REF_PATHS["paper_submit_receipt_event_log"],
            "paper_submit_receipt_event_count": _event_count(
                SOURCE_REF_PATHS["paper_submit_receipt_event_log"],
                settings,
            ),
            "closed_trade_event_log_ref": SOURCE_REF_PATHS["closed_trade_event_log"],
            "closed_trade_event_count": _event_count(SOURCE_REF_PATHS["closed_trade_event_log"], settings),
            "postmortem_due_event_log_ref": SOURCE_REF_PATHS["postmortem_due_event_log"],
            "postmortem_due_event_count": _event_count(
                SOURCE_REF_PATHS["postmortem_due_event_log"],
                settings,
            ),
            "event_log_prewrite_ready": staging_record.get("event_log_prewrite_ready"),
            "event_log_prewrite_fingerprint": staging_record.get("event_log_prewrite_fingerprint"),
            "broker_receipt_ref": receipt.get("broker_receipt_ref"),
            "broker_receipt_state": receipt.get("broker_receipt_state"),
        },
        "market_context": {
            "signal_integrity_ref": signal_integrity.get("review_id"),
            "signal_integrity_status": signal_integrity.get("status"),
            "integrity_score": signal_integrity.get("integrity_score"),
            "source_count": signal_integrity.get("source_count"),
            "market_confirmation_status": market_confirmation_policy.get("status"),
            "market_confirmation_pricing_gap": market_confirmation_policy.get("pricing_gap"),
            "market_confirmation_providers": _list_or_empty(
                market_confirmation_policy.get("providers")
            ),
            "uses_yahoo_finance": market_confirmation_policy.get("uses_yahoo_finance"),
            "yahoo_finance_status": yahoo_status.get("status"),
            "yahoo_finance_enabled": yahoo_status.get("enabled"),
            "yahoo_finance_degraded_reason": yahoo_status.get("degraded_reason"),
            "preference_context_status": preference_policy.get("status"),
            "preference_shadow_context_status": preference_shadow.get("status"),
            "preference_provenance_status": preference_provenance.get("status"),
            "preference_source_promotion_status": preference_promotion.get("status"),
            "preference_mcp_status": preference_status.get("status"),
        },
        "source_context": {
            "learning_source_intake_ref": SOURCE_INTAKE_REF,
            "learning_source_intake_status": source_intake.get("status"),
            "learning_source_intake_source_ref_count": source_intake.get("source_ref_count"),
            "required_source_present_count": source_intake.get("required_source_present_count"),
            "required_source_count": source_intake.get("required_source_count"),
            "optional_source_present_count": source_intake.get("optional_source_present_count"),
            "approval_policy_ref": approval_record.get("artifact_id"),
            "risk_record_ref": risk_record.get("artifact_id"),
            "execution_adapter_ref": execution_record.get("artifact_id"),
            "position_monitor_ref": position_record.get("artifact_id") if position_record else None,
        },
        "invalidation": {
            "staged_order_invalidation": staging_record.get("invalidation"),
            "risk_invalidation_conditions": _list_or_empty(risk_record.get("invalidation_conditions")),
            "cancellation_conditions": _list_or_empty(staging_record.get("cancellation_conditions")),
            "deferred_postmortem_invalidation_read": True,
        },
        "realized_outcome": {
            "realized_pnl_gbp": realized_pnl_gbp,
            "r_multiple": closed_trade.get("r_multiple"),
            "outcome_bucket": _outcome_bucket(realized_pnl_gbp),
            "postmortem_status": postmortem_due.get("postmortem_status"),
            "phase5_test_trade": True,
            "phase7_proof_credit_allowed": False,
        },
        "truth_partition": {
            "local_lifecycle": {
                "source": "q5e_guarded_local_lifecycle",
                "closed_trade_created": closed_trade.get("closed_trade_created"),
                "closed_trade_state": closed_trade.get("closed_trade_state"),
                "postmortem_due_marker_created": postmortem_due.get(
                    "postmortem_due_marker_created"
                ),
                "local_lifecycle_state": "closed_trade_recorded",
            },
            "broker_truth": {
                "source": "broker_truth_not_available_for_q6_3",
                "broker_post_called": closed_trade.get("broker_post_called"),
                "alpaca_post_called": closed_trade.get("alpaca_post_called"),
                "external_broker_post_performed": closed_trade.get(
                    "external_broker_post_performed"
                ),
                "broker_receipt_state": receipt.get("broker_receipt_state"),
                "broker_order_identifier_exposed": closed_trade.get(
                    "broker_order_identifier_exposed"
                ),
                "broker_truth_accepted_as_fill_truth": False,
            },
            "distinction": (
                "Closed-trade state is a local guarded paper lifecycle marker. "
                "It is not a broker fill assertion."
            ),
        },
        "deferred_fields": deferred_fields,
        "deferred_field_count": len(deferred_fields),
        "unknown_fields": unknown_fields,
        "unknown_field_count": len(unknown_fields),
        "write_authority": False,
    }
    return record, blockers


def build_phase6_closed_trade_outcome(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    source_intake = _read_json(SOURCE_INTAKE_REF, settings) or {}
    source_intake_errors = (
        validate_phase6_learning_source_intake(source_intake) if source_intake else []
    )
    outcome_record, blockers = _build_outcome_record(settings)
    if source_intake_errors:
        blockers.append("source_intake_validation_errors")
    outcome_records = [outcome_record] if outcome_record else []
    status = "read_only" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-3"
    authority["boundary"] = PHASE6_CLOSED_TRADE_OUTCOME_BOUNDARY
    closed_trade_ref = outcome_record.get("source_closed_trade_ref") if outcome_record else None
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_closed_trade_outcome_schema_version": (
            PHASE6_CLOSED_TRADE_OUTCOME_SCHEMA_VERSION
        ),
        "artifact_type": "closed_trade_outcome",
        "artifact_id": "phase6:q6-3:closed-trade-outcome:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-3",
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
        "provenance": _provenance(),
        "boundary": PHASE6_CLOSED_TRADE_OUTCOME_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_learning_disabled_fields(),
        "closed_trade_ref": closed_trade_ref,
        "outcome_status": (
            "closed_trade_outcome_normalized" if outcome_record else "blocked_missing_outcome"
        ),
        "learning_write_allowed": False,
        "outcome_record_count": len(outcome_records),
        "outcome_records": outcome_records,
        "source_intake_ref": SOURCE_INTAKE_REF,
        "source_intake_status": source_intake.get("status"),
        "source_intake_validation_error_count": len(source_intake_errors),
        "local_lifecycle_state_count": len(
            [
                record
                for record in outcome_records
                if record.get("truth_partition", {})
                .get("local_lifecycle", {})
                .get("local_lifecycle_state")
            ]
        ),
        "broker_truth_separated": True,
        "unknown_field_count": sum(
            int(record.get("unknown_field_count", 0) or 0) for record in outcome_records
        ),
        "deferred_field_count": sum(
            int(record.get("deferred_field_count", 0) or 0) for record in outcome_records
        ),
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-4 Postmortem Packet Contract",
    }
    artifact["validation_errors"] = validate_phase6_closed_trade_outcome(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_phase6_closed_trade_outcome(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_closed_trade_outcome_schema_version",
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
        "closed_trade_ref",
        "outcome_status",
        "learning_write_allowed",
        "outcome_record_count",
        "outcome_records",
        "source_intake_ref",
        "source_intake_status",
        "broker_truth_separated",
        "unknown_field_count",
        "deferred_field_count",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("closed_trade_outcome_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_closed_trade_outcome_schema_version") != (
        PHASE6_CLOSED_TRADE_OUTCOME_SCHEMA_VERSION
    ):
        errors.append("closed_trade_outcome_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-3"))
    if artifact.get("artifact_type") != "closed_trade_outcome":
        errors.append("closed_trade_outcome_artifact_type_mismatch")
    if artifact.get("status") not in {"read_only", "blocked", "error"}:
        errors.append("closed_trade_outcome_status_invalid")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    for field, value in _learning_disabled_fields().items():
        if artifact.get(field) is not value:
            errors.append(f"closed_trade_outcome_write_enabled:{field}")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"closed_trade_outcome_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("closed_trade_outcome_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("closed_trade_outcome_unsafe_total_nonzero")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("broker_truth_separated") is not True:
        errors.append("broker_truth_not_separated")
    outcome_records = artifact.get("outcome_records", [])
    if not isinstance(outcome_records, list):
        errors.append("outcome_records_invalid")
        outcome_records = []
    if artifact.get("outcome_record_count") != len(outcome_records):
        errors.append("outcome_record_count_mismatch")
    if artifact.get("outcome_record_count", 0) < 1:
        errors.append("closed_trade_outcome_record_missing")
    unknown_total = 0
    deferred_total = 0
    for record in outcome_records:
        if not isinstance(record, dict):
            errors.append("outcome_record_invalid")
            continue
        if record.get("source_closed_trade_ref") != artifact.get("closed_trade_ref"):
            errors.append("closed_trade_ref_mismatch")
        if record.get("write_authority") is not False:
            errors.append("outcome_record_write_authority")
        for field in (
            "thesis",
            "entry_state",
            "exit_state",
            "sizing",
            "risk_decision",
            "execution_path",
            "receipt_and_prewrite_refs",
            "market_context",
            "source_context",
            "invalidation",
            "realized_outcome",
            "truth_partition",
        ):
            if not isinstance(record.get(field), dict):
                errors.append(f"outcome_record_section_missing:{field}")
        thesis = record.get("thesis", {}) if isinstance(record.get("thesis"), dict) else {}
        if thesis.get("actual_catalyst") is not None:
            errors.append("actual_catalyst_invented")
        if thesis.get("actual_catalyst_status") != "unknown_pending_postmortem_analysis":
            errors.append("actual_catalyst_not_marked_unknown")
        if thesis.get("expected_catalyst") is not None:
            errors.append("expected_catalyst_specific_event_invented")
        if not _list_or_empty(thesis.get("expected_catalyst_classes")):
            errors.append("expected_catalyst_classes_missing")
        truth_partition = (
            record.get("truth_partition", {})
            if isinstance(record.get("truth_partition"), dict)
            else {}
        )
        local_lifecycle = truth_partition.get("local_lifecycle", {})
        broker_truth = truth_partition.get("broker_truth", {})
        if not isinstance(local_lifecycle, dict) or not isinstance(broker_truth, dict):
            errors.append("truth_partition_invalid")
        else:
            if local_lifecycle.get("local_lifecycle_state") != "closed_trade_recorded":
                errors.append("local_lifecycle_state_missing")
            if broker_truth.get("broker_truth_accepted_as_fill_truth") is not False:
                errors.append("broker_truth_accepted_as_fill_truth")
            if broker_truth.get("broker_post_called") is not False:
                errors.append("broker_post_called_in_outcome")
            if broker_truth.get("external_broker_post_performed") is not False:
                errors.append("external_broker_post_performed_in_outcome")
        realized_outcome = (
            record.get("realized_outcome", {})
            if isinstance(record.get("realized_outcome"), dict)
            else {}
        )
        if realized_outcome.get("phase7_proof_credit_allowed") is not False:
            errors.append("outcome_phase7_proof_credit_allowed")
        if realized_outcome.get("phase5_test_trade") is not True:
            errors.append("outcome_phase5_test_trade_not_marked")
        unknown_fields = record.get("unknown_fields", [])
        deferred_fields = record.get("deferred_fields", [])
        if not isinstance(unknown_fields, list) or not unknown_fields:
            errors.append("unknown_fields_missing")
            unknown_fields = []
        if not isinstance(deferred_fields, list) or not deferred_fields:
            errors.append("deferred_fields_missing")
            deferred_fields = []
        if record.get("unknown_field_count") != len(unknown_fields):
            errors.append("unknown_field_count_mismatch")
        if record.get("deferred_field_count") != len(deferred_fields):
            errors.append("deferred_field_count_mismatch")
        for field in UNKNOWN_FIELD_SENTINELS:
            if field not in unknown_fields:
                errors.append(f"unknown_field_sentinel_missing:{field}")
        for field in DEFERRED_FIELD_SENTINELS:
            if field not in deferred_fields:
                errors.append(f"deferred_field_sentinel_missing:{field}")
        unknown_total += len(unknown_fields)
        deferred_total += len(deferred_fields)
    if artifact.get("unknown_field_count") != unknown_total:
        errors.append("artifact_unknown_field_count_mismatch")
    if artifact.get("deferred_field_count") != deferred_total:
        errors.append("artifact_deferred_field_count_mismatch")
    if artifact.get("source_intake_status") != "read_only":
        errors.append("source_intake_not_read_only")
    if int(artifact.get("source_intake_validation_error_count", 0) or 0) != 0:
        errors.append("source_intake_validation_errors")
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
        "normalizes a closed paper-trade outcome",
        "cannot create a postmortem draft",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot treat local guarded lifecycle state as broker fill truth",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("closed_trade_outcome_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("closed_trade_outcome_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("closed_trade_outcome_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("closed_trade_outcome_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_closed_trade_outcome_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_CLOSED_TRADE_OUTCOME_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_CLOSED_TRADE_OUTCOME_EVENT_TYPE,
        PHASE6_CLOSED_TRADE_OUTCOME_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "closed_trade_ref": output.get("closed_trade_ref"),
            "outcome_status": output.get("outcome_status"),
            "outcome_record_count": output.get("outcome_record_count"),
            "broker_truth_separated": output.get("broker_truth_separated"),
            "unknown_field_count": output.get("unknown_field_count"),
            "deferred_field_count": output.get("deferred_field_count"),
            "learning_write_allowed": output.get("learning_write_allowed"),
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
    output["validation_errors"] = validate_phase6_closed_trade_outcome(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_closed_trade_outcome(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_closed_trade_outcome_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_closed_trade_outcome_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_closed_trade_outcome(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_closed_trade_outcome(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_CLOSED_TRADE_OUTCOME_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "closed_trade_ref": output.get("closed_trade_ref"),
        "outcome_status": output.get("outcome_status"),
        "outcome_record_count": output.get("outcome_record_count"),
        "broker_truth_separated": output.get("broker_truth_separated"),
        "unknown_field_count": output.get("unknown_field_count"),
        "deferred_field_count": output.get("deferred_field_count"),
        "learning_write_allowed": output.get("learning_write_allowed"),
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
