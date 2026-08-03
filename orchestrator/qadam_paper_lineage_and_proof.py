"""OR-16 paper lifecycle, proof eligibility, and learning attribution.

Broker mirrors are classified separately from Qadam-origin paper trades. Proof
eligibility requires a real closed Qadam-origin trade with complete lineage and
a completed postmortem; this module audits eligibility but grants no credit.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    EXPERIMENTAL_UNVALIDATED,
    VALIDATED_PAPER_STRATEGY,
    evidence_class,
    validate_class_lineage,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_paper_epoch import is_clean_epoch_kind, read_current_epoch
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, stable_id

SCHEMA_VERSION = "qadam_paper_lineage_and_proof.v1"
PHASE_ID = "OR-16"

LIFECYCLE_ARTIFACT = "qadam_paper_lifecycle_v3.json"
LINEAGE_ARTIFACT = "qadam_paper_trade_lineage.jsonl"
POSTMORTEMS_ARTIFACT = "qadam_paper_postmortems_v3.jsonl"
PROOF_ARTIFACT = "qadam_paper_proof_eligibility.json"
ATTRIBUTION_ARTIFACT = "qadam_learning_attribution_v3.jsonl"
PERFORMANCE_ARTIFACT = "qadam_paper_performance_summary.json"
CHECK_ARTIFACT = "qadam_paper_lineage_and_proof_checks.json"

PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
HANDOFF_ARTIFACT = "qadam_paperops_handoff_v3.jsonl"
ACCEPTED_HANDOFF_ARTIFACT = "qadam_paperops_handoff_v3_accepted.jsonl"
HANDOFF_RECEIPTS_ARTIFACT = "qadam_paperops_handoff_v3_consumption_receipts.jsonl"
PAPEROPS_SUBMISSION_LEDGER_ARTIFACT = "paperops_alpaca_paper_post_submission_ledger.json"
PAPEROPS_LIFECYCLE_POLLER_ARTIFACT = "paperops_paper_lifecycle_poller.json"
PAPEROPS_EXIT_PATH_ARTIFACT = "paperops_paper_exit_path.json"
PAPEROPS_EXIT_PATH_HISTORY_ARTIFACT = "paperops_paper_exit_path_history.jsonl"
PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT = "paperops_close_to_ledger.json"
PHASE6_POSTMORTEM_ANALYSIS_ARTIFACT = "phase6_postmortem_analysis_packets.json"
PHASE6_POSTMORTEM_DRAFT_ARTIFACT = "phase6_postmortem_draft.json"
ROUTER_DECISIONS_ARTIFACT = "qadam_router_v3_decisions.jsonl"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
SHADOW_OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
SHADOW_CALIBRATION_ARTIFACT = "qadam_shadow_calibration.json"
RISK_REJECTIONS_ARTIFACT = "qadam_risk_rejections.jsonl"
FOUNDRY_REJECTIONS_ARTIFACT = "qadam_strategy_hypothesis_rejections_v3.jsonl"
RELEASE_READINESS_ARTIFACT = "qadam_research_lock_release_readiness.json"
EDGE_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
SOURCE_OPERATIONAL_ARTIFACT = "qadam_source_operational_state.jsonl"
APPLIED_VERSIONS_ARTIFACT = "qadam_applied_learning_versions.jsonl"

STALE_ACCEPTED_SECONDS = 90 * 60
RECONCILIATION_SECONDS = 4 * 60 * 60

LIFECYCLE_STATES = {
    "staged",
    "submitted",
    "accepted",
    "partially_filled",
    "filled",
    "open",
    "exit_requested",
    "closed",
    "cancelled",
    "rejected",
    "expired",
    "reconciliation_required",
    "postmortem_complete",
}

ORIGIN_CLASSES = {
    "qadam_origin_complete_lineage",
    "qadam_origin_incomplete_lineage",
    "external_manual_paper_record",
    "mirror_only_historical_record",
}

COMMON_PROOF_LINEAGE_FIELDS = (
    "research_goal_id",
    "source_evidence_id",
    "strategy_hypothesis_id",
    "akber_result_id",
    "shadow_evidence_id",
    "risk_proposal_id",
    "router_decision_id",
    "paperops_handoff_id",
    "idempotency_key",
)

ATTRIBUTION_COMPONENTS = (
    "source_evidence",
    "local_model_contribution",
    "frontier_model_contribution",
    "nonlinear_quantum_review",
    "strategy_hypothesis",
    "akber_stages",
    "router_decision",
    "portfolio_risk_decision",
    "paperops_broker_execution",
    "exit_decision",
    "provider_system_reliability",
)

CHAMPION_CHALLENGER_STATES = {
    "proposed",
    "approved-for-research",
    "backtested",
    "shadowing",
    "approved-for-paper",
    "rejected",
    "degraded",
    "retired",
}

def _record_key(record: dict[str, Any]) -> str:
    return str(
        record.get("order_id")
        or record.get("trade_id")
        or record.get("position_id")
        or record.get("client_order_id")
        or ""
    ).strip()


def _is_protective_exit_order(order: dict[str, Any]) -> bool:
    return bool(
        order.get("protective_exit_leg") is True
        or str(order.get("position_intent") or "").lower()
        in {"buy_to_close", "sell_to_close"}
    )


def _record_epoch_id(record: dict[str, Any]) -> str:
    return str(record.get("paper_epoch_id") or "").strip()


def _filter_current_execution_epoch(
    records: list[dict[str, Any]],
    *,
    current_epoch: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Exclude archived or unlabelled execution rows once a clean epoch is active."""

    if not is_clean_epoch_kind(current_epoch.get("paper_epoch_kind")):
        return records, []
    epoch_id = str(current_epoch.get("paper_epoch_id") or "").strip()
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in records:
        if epoch_id and _record_epoch_id(record) == epoch_id:
            included.append(record)
        else:
            excluded.append(record)
    return included, excluded


def _hash_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    return sha256(text.encode("utf-8")).hexdigest() if text else None


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _accepted_source_handoff(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source_handoff")
    return source if isinstance(source, dict) else {}


def _accepted_handoff_verified(
    accepted_record: dict[str, Any], receipt_by_id: dict[str, dict[str, Any]]
) -> bool:
    handoff = _accepted_source_handoff(accepted_record)
    receipt_id = str(accepted_record.get("consumption_receipt_id") or "")
    receipt = receipt_by_id.get(receipt_id, {})
    return bool(
        handoff
        and receipt_id
        and receipt.get("accepted") is True
        and receipt.get("status") == "accepted_for_guarded_paperops_sequence"
        and receipt.get("paperops_handoff_id") == handoff.get("paperops_handoff_id")
        and receipt.get("router_decision_id") == handoff.get("router_decision_id")
        and receipt.get("idempotency_key")
        == handoff.get("idempotency_material", {}).get("idempotency_key")
        and handoff.get("route") == "guarded_alpaca_paper_via_paperops"
    )


def _execution_identity_index(
    submission_records: list[dict[str, Any]],
    lifecycle_records: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_broker_hash: dict[str, dict[str, Any]] = {}
    by_client_hash: dict[str, dict[str, Any]] = {}
    for record in [*submission_records, *lifecycle_records]:
        if not isinstance(record, dict):
            continue
        broker_hash = str(record.get("broker_order_id_hash") or "")
        client_hash = str(record.get("client_order_id_hash") or "")
        if broker_hash:
            by_broker_hash[broker_hash] = {**by_broker_hash.get(broker_hash, {}), **record}
        if client_hash:
            by_client_hash[client_hash] = {**by_client_hash.get(client_hash, {}), **record}
    return by_broker_hash, by_client_hash


def _matching_execution_identity(
    order: dict[str, Any],
    trade: dict[str, Any],
    *,
    by_broker_hash: dict[str, dict[str, Any]],
    by_client_hash: dict[str, dict[str, Any]],
    previous: dict[str, Any],
) -> dict[str, Any]:
    broker_hashes = {
        value
        for value in (
            _hash_identifier(order.get("order_id")),
            _hash_identifier(trade.get("trade_id")),
            str(order.get("broker_order_id_hash") or "") or None,
            str(trade.get("broker_order_id_hash") or "") or None,
        )
        if value
    }
    for broker_hash in broker_hashes:
        if broker_hash in by_broker_hash:
            return dict(by_broker_hash[broker_hash])
    client_hashes = {
        value
        for value in (
            _hash_identifier(order.get("client_order_id")),
            _hash_identifier(trade.get("client_order_id")),
            str(order.get("client_order_id_hash") or "") or None,
            str(trade.get("client_order_id_hash") or "") or None,
        )
        if value
    }
    for client_hash in client_hashes:
        if client_hash in by_client_hash:
            return dict(by_client_hash[client_hash])
    prior = previous.get("execution_identity")
    return dict(prior) if isinstance(prior, dict) else {}


def _pseudo_handoff_from_execution(identity: dict[str, Any]) -> dict[str, Any]:
    lineage = _safe_dict(identity.get("complete_v3_lineage"))
    if not lineage:
        return {}
    return {
        "paperops_handoff_id": identity.get("paperops_handoff_id"),
        "router_decision_id": identity.get("router_decision_id"),
        "lineage": lineage,
        "idempotency_material": {
            "idempotency_key": identity.get("source_router_idempotency_key")
            or identity.get("source_idempotency_key")
            or identity.get("idempotency_key")
        },
        "route": "guarded_alpaca_paper_via_paperops",
    }


def _close_record_index(
    current_exit: dict[str, Any], exit_history: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for payload in [current_exit, *exit_history]:
        if not isinstance(payload, dict):
            continue
        records.extend(
            record
            for record in payload.get("selected_exit_records", []) or []
            if isinstance(record, dict)
        )
    by_broker_hash: dict[str, dict[str, Any]] = {}
    by_client_hash: dict[str, dict[str, Any]] = {}
    for record in records:
        broker_hash = str(record.get("broker_order_id_hash") or "")
        client_hash = str(record.get("client_order_id_hash") or "")
        if broker_hash:
            by_broker_hash[broker_hash] = record
        if client_hash:
            by_client_hash[client_hash] = record
    return by_broker_hash, by_client_hash


def _matching_close_record(
    order: dict[str, Any],
    trade: dict[str, Any],
    execution_identity: dict[str, Any],
    *,
    by_broker_hash: dict[str, dict[str, Any]],
    by_client_hash: dict[str, dict[str, Any]],
    previous: dict[str, Any],
) -> dict[str, Any]:
    broker_hashes = {
        value
        for value in (
            _hash_identifier(order.get("order_id")),
            _hash_identifier(trade.get("trade_id")),
            str(execution_identity.get("broker_order_id_hash") or "") or None,
        )
        if value
    }
    for broker_hash in broker_hashes:
        if broker_hash in by_broker_hash:
            return dict(by_broker_hash[broker_hash])
    client_hashes = {
        value
        for value in (
            str(execution_identity.get("client_order_id_hash") or "") or None,
            _hash_identifier(execution_identity.get("client_order_id")),
        )
        if value
    }
    for client_hash in client_hashes:
        if client_hash in by_client_hash:
            return dict(by_client_hash[client_hash])
    prior = previous.get("guarded_close_evidence")
    return dict(prior) if isinstance(prior, dict) else {}


def _guarded_close_verified(record: dict[str, Any]) -> bool:
    try:
        status_code = int(record.get("sanitized_http_status") or 0)
    except (TypeError, ValueError):
        status_code = 0
    return bool(
        record.get("status") == "paper_exit_close_recorded"
        and record.get("paper_position_close_succeeded") is True
        and 200 <= status_code < 300
        and record.get("accepted_v3_handoff_verified") is True
        and record.get("paperops_handoff_id")
        and record.get("v3_consumption_receipt_id")
    )


def _lineage_from_handoff(handoff: dict[str, Any]) -> dict[str, Any]:
    source = handoff.get("lineage") if isinstance(handoff.get("lineage"), dict) else {}
    idempotency = (
        handoff.get("idempotency_material")
        if isinstance(handoff.get("idempotency_material"), dict)
        else {}
    )
    return {
        "research_goal_id": source.get("research_goal_id"),
        "source_evidence_id": source.get("score_id"),
        "score_id": source.get("score_id"),
        "edge_id": source.get("edge_id"),
        "pattern_relationship_id": source.get("pattern_relationship_id"),
        "evidence_class": handoff.get("evidence_class"),
        "strategy_hypothesis_id": source.get("hypothesis_id"),
        "akber_result_id": source.get("akber_result_id"),
        "shadow_evidence_id": source.get("shadow_evidence_id"),
        "risk_proposal_id": source.get("risk_proposal_id"),
        "router_decision_id": handoff.get("router_decision_id"),
        "paperops_handoff_id": handoff.get("paperops_handoff_id"),
        "candidate_identity_id": handoff.get("candidate_identity_id"),
        "idempotency_key": idempotency.get("idempotency_key"),
        "applied_learning_version_ids": source.get("applied_learning_version_ids", []),
        "stage1_learning_input_version": source.get("stage1_learning_input_version"),
    }


def _match_handoff(
    order: dict[str, Any],
    trade: dict[str, Any],
    handoffs_by_id: dict[str, dict[str, Any]],
    handoffs_by_idempotency: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    handoff_id = order.get("paperops_handoff_id") or trade.get("paperops_handoff_id")
    if handoff_id and str(handoff_id) in handoffs_by_id:
        return handoffs_by_id[str(handoff_id)]
    key = (
        order.get("idempotency_key") or order.get("client_order_id") or trade.get("idempotency_key")
    )
    return handoffs_by_idempotency.get(str(key), {}) if key else {}


def _direct_lineage(order: dict[str, Any], trade: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "research_goal_id": ("research_goal_id",),
        "source_evidence_id": ("source_evidence_id", "score_id"),
        "score_id": ("score_id",),
        "edge_id": ("edge_id",),
        "pattern_relationship_id": ("pattern_relationship_id",),
        "evidence_class": ("evidence_class",),
        "strategy_hypothesis_id": ("strategy_hypothesis_id", "hypothesis_id"),
        "akber_result_id": ("akber_result_id",),
        "shadow_evidence_id": ("shadow_evidence_id", "shadow_outcome_id"),
        "risk_proposal_id": ("risk_proposal_id",),
        "router_decision_id": ("router_decision_id",),
        "paperops_handoff_id": ("paperops_handoff_id",),
        "candidate_identity_id": ("candidate_identity_id",),
        "idempotency_key": ("idempotency_key", "client_order_id"),
        "applied_learning_version_ids": ("applied_learning_version_ids",),
        "stage1_learning_input_version": ("stage1_learning_input_version",),
    }
    lineage: dict[str, Any] = {}
    for target, fields in aliases.items():
        value = None
        for source in (order, trade):
            for field in fields:
                if source.get(field):
                    value = source.get(field)
                    break
            if value:
                break
        lineage[target] = value
    return lineage


def classify_broker_origin(
    order: dict[str, Any],
    trade: dict[str, Any],
    handoff: dict[str, Any],
    *,
    accepted_v3_handoff_verified: bool = False,
    execution_identity: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], list[str]]:
    execution_identity = execution_identity or {}
    direct = _direct_lineage(order, trade)
    from_handoff = _lineage_from_handoff(handoff) if handoff else {}
    lineage = {
        field: direct.get(field) or from_handoff.get(field)
        for field in set(direct) | set(from_handoff)
    }
    boundary = f"{order.get('boundary', '')} {trade.get('boundary', '')}".lower()
    declared_origin = str(order.get("origin_class") or trade.get("origin_class") or "").lower()
    client_order_id = str(order.get("client_order_id") or "").lower()
    qadam_origin = bool(
        handoff
        or execution_identity.get("paperops_handoff_id")
        or order.get("qadam_origin") is True
        or trade.get("qadam_origin") is True
        or declared_origin == "qadam_origin_paper"
        or client_order_id.startswith("qadam-")
        or client_order_id.startswith("qadam:")
    )
    external_manual = (
        declared_origin in {"operator", "manual", "external_manual"}
        or "manual paper" in boundary
        or "operator placed" in boundary
        or execution_identity.get("idempotency_namespace")
        == "operator_exploratory_sleeve"
        or execution_identity.get("source_family") == "operator_exploratory_sleeve"
        or execution_identity.get("evidence_class")
        == "operator_exploratory_unvalidated"
    )
    lineage_class = evidence_class(
        {"evidence_class": lineage.get("evidence_class") or handoff.get("evidence_class")}
    )
    class_lineage = {
        "research_goal_id": lineage.get("research_goal_id"),
        "score_id": lineage.get("score_id"),
        "edge_id": lineage.get("edge_id"),
        "pattern_relationship_id": lineage.get("pattern_relationship_id"),
        "hypothesis_id": lineage.get("strategy_hypothesis_id"),
        "akber_result_id": lineage.get("akber_result_id"),
        "shadow_evidence_id": lineage.get("shadow_evidence_id"),
        "risk_proposal_id": lineage.get("risk_proposal_id"),
    }
    missing = [field for field in COMMON_PROOF_LINEAGE_FIELDS if not lineage.get(field)]
    missing.extend(validate_class_lineage(lineage_class, class_lineage))
    if qadam_origin and not accepted_v3_handoff_verified:
        missing.append("accepted_v3_handoff_verification")
    if qadam_origin and not missing and accepted_v3_handoff_verified:
        origin = "qadam_origin_complete_lineage"
    elif qadam_origin:
        origin = "qadam_origin_incomplete_lineage"
    elif external_manual:
        origin = "external_manual_paper_record"
    else:
        origin = "mirror_only_historical_record"
    return origin, lineage, missing


def _state_event(state: str, observed_at: Any, source: str) -> dict[str, Any]:
    return {
        "state": state,
        "observed_at": observed_at,
        "source": source,
    }


def _lifecycle_history(
    order: dict[str, Any],
    trade: dict[str, Any],
    position: dict[str, Any],
    *,
    execution_identity: dict[str, Any] | None = None,
    guarded_close_evidence: dict[str, Any] | None = None,
    postmortem_complete: bool = False,
) -> tuple[list[dict[str, Any]], str, str | None]:
    execution_identity = execution_identity or {}
    guarded_close_evidence = guarded_close_evidence or {}
    events: list[dict[str, Any]] = []
    staged_at = order.get("staged_at") or execution_identity.get("staged_at")
    submitted_at = order.get("submitted_at") or execution_identity.get("submitted_at")
    if staged_at:
        events.append(_state_event("staged", staged_at, "guarded_paperops"))
    if submitted_at:
        events.append(_state_event("submitted", submitted_at, "alpaca_paper_submit"))
    status = str(order.get("status") or "").lower()
    status_map = {
        "new": "accepted",
        "accepted": "accepted",
        "partially_filled": "partially_filled",
        "filled": "filled",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "rejected": "rejected",
        "expired": "expired",
        "pending_cancel": "exit_requested",
        "pending_replace": "exit_requested",
    }
    if status == "held" and _is_protective_exit_order(order):
        events.append(
            _state_event(
                "accepted",
                order.get("updated_at") or order.get("submitted_at"),
                "paper_order_protective_exit",
            )
        )
    elif status in status_map:
        observed_at = order.get("filled_at") if status == "filled" else order.get("updated_at")
        events.append(_state_event(status_map[status], observed_at, "paper_order"))
    elif order and status not in {"", "pending", "pending_new", "submitted"}:
        events.append(
            _state_event("reconciliation_required", order.get("updated_at"), "paper_order")
        )
    if position:
        events.append(
            _state_event(
                "open",
                position.get("opened_at") or position.get("updated_at"),
                "paper_position",
            )
        )
    if guarded_close_evidence and not _guarded_close_verified(guarded_close_evidence):
        events.append(
            _state_event(
                "exit_requested",
                guarded_close_evidence.get("paper_position_close_requested_at")
                or guarded_close_evidence.get("recorded_at"),
                "guarded_paper_exit",
            )
        )
    if _guarded_close_verified(guarded_close_evidence):
        close_receipt = _safe_dict(guarded_close_evidence.get("broker_close_receipt"))
        events.append(
            _state_event(
                "closed",
                close_receipt.get("paper_position_close_requested_at")
                or guarded_close_evidence.get("paper_position_close_requested_at")
                or guarded_close_evidence.get("recorded_at"),
                "guarded_paper_exit_receipt",
            )
        )
    if postmortem_complete:
        events.append(
            _state_event(
                "postmortem_complete",
                trade.get("postmortem_completed_at") or guarded_close_evidence.get("recorded_at"),
                "qadam_postmortem_v3",
            )
        )
    if not events:
        events.append(_state_event("reconciliation_required", None, "origin_audit"))
    deduped: list[dict[str, Any]] = []
    for event in events:
        if deduped and deduped[-1]["state"] == event["state"]:
            deduped[-1] = event
        else:
            deduped.append(event)
    events = deduped
    current = str(events[-1]["state"])
    reconciliation_reason = (
        "unknown_or_incomplete_broker_lifecycle_state"
        if current == "reconciliation_required"
        else None
    )
    return events, current, reconciliation_reason


def stale_accepted_order_policy(order: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    status = str(order.get("status") or "").lower()
    submitted = parse_timestamp(order.get("submitted_at"))
    generated = parse_timestamp(generated_at)
    age_seconds = (
        int((generated - submitted).total_seconds())
        if submitted is not None and generated is not None
        else None
    )
    if status == "held" and _is_protective_exit_order(order):
        action = "monitor_broker_held_protective_exit"
    elif status not in {"new", "accepted", "open", "pending_new", "submitted"}:
        action = "no_action_terminal_or_nonaccepted_state"
    elif age_seconds is None:
        action = "no_action_reconciliation_required_missing_timestamp"
    elif age_seconds <= STALE_ACCEPTED_SECONDS:
        action = "wait"
    elif age_seconds <= RECONCILIATION_SECONDS:
        action = "cancel_replace_proposal"
    else:
        action = "no_action_reconciliation_required"
    return {
        "policy_version": "qadam-stale-accepted-paper-order.1-frozen",
        "age_seconds": age_seconds,
        "wait_until_seconds": STALE_ACCEPTED_SECONDS,
        "reconciliation_after_seconds": RECONCILIATION_SECONDS,
        "action": action,
        "action_is_proposal_only": action == "cancel_replace_proposal",
        "automatic_cancel_allowed": False,
        "automatic_replace_allowed": False,
        "broker_write_allowed": False,
    }


def _trade_metrics(
    order: dict[str, Any],
    trade: dict[str, Any],
    lineage: dict[str, Any],
    *,
    execution_identity: dict[str, Any] | None = None,
    guarded_close_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    execution_identity = execution_identity or {}
    guarded_close_evidence = guarded_close_evidence or {}
    real_close = _guarded_close_verified(guarded_close_evidence)
    opened = parse_timestamp(trade.get("opened_at") or order.get("filled_at"))
    close_receipt = _safe_dict(guarded_close_evidence.get("broker_close_receipt"))
    closed = parse_timestamp(
        close_receipt.get("paper_position_close_requested_at")
        or guarded_close_evidence.get("paper_position_close_requested_at")
        or guarded_close_evidence.get("recorded_at")
        or (trade.get("closed_at") if real_close else None)
    )
    holding_seconds = (
        (closed - opened).total_seconds()
        if opened is not None and closed is not None and closed >= opened
        else None
    )
    realized = trade.get("realized_net_pnl") if real_close else None
    if realized is None and real_close:
        realized = trade.get("realized_pnl_gbp")
    entry_price = order.get("filled_avg_price") or trade.get("entry_price")
    exit_price = trade.get("exit_price") or guarded_close_evidence.get("exit_price")
    quantity = safe_float(
        order.get("filled_quantity") or order.get("quantity") or execution_identity.get("qty"),
        0.0,
    )
    direction = str(trade.get("direction") or order.get("direction") or "").lower()
    if (
        realized is None
        and real_close
        and entry_price is not None
        and exit_price is not None
        and quantity > 0
    ):
        multiplier = -1.0 if direction in {"sell", "short", "down"} else 1.0
        realized = (safe_float(exit_price) - safe_float(entry_price)) * quantity * multiplier
    expected_price = (
        order.get("arrival_price")
        or order.get("expected_fill_price")
        or execution_identity.get("expected_fill_price")
    )
    fill_price = order.get("filled_avg_price") or trade.get("entry_price")
    slippage = (
        safe_float(fill_price) - safe_float(expected_price)
        if expected_price is not None and fill_price is not None
        else None
    )
    realized_value = safe_float(realized) if realized is not None else None
    if realized_value is None or not lineage.get("edge_id"):
        calibration = "not_measurable"
    elif direction in {"buy", "long", "up"}:
        calibration = "direction_supported" if realized_value > 0 else "direction_not_supported"
    elif direction in {"sell", "short", "down"}:
        calibration = "direction_supported" if realized_value > 0 else "direction_not_supported"
    else:
        calibration = "not_measurable"
    return {
        "realized_net_pnl": realized_value,
        "currency": "GBP" if trade.get("realized_pnl_gbp") is not None else trade.get("currency"),
        "slippage_per_unit": round(slippage, 10) if slippage is not None else None,
        "holding_period_seconds": holding_seconds,
        "entry_price": safe_float(entry_price) if entry_price is not None else None,
        "exit_price": safe_float(exit_price) if exit_price is not None else None,
        "filled_quantity": quantity if quantity > 0 else None,
        "maximum_adverse_excursion": trade.get("maximum_adverse_excursion"),
        "maximum_favourable_excursion": trade.get("maximum_favourable_excursion"),
        "exit_reason": trade.get("exit_reason") or trade.get("close_reason"),
        "edge_calibration": calibration,
        "metrics_missing": [
            field
            for field, value in (
                ("realized_net_pnl", realized_value),
                ("slippage_per_unit", slippage),
                ("maximum_adverse_excursion", trade.get("maximum_adverse_excursion")),
                ("maximum_favourable_excursion", trade.get("maximum_favourable_excursion")),
            )
            if value is None
        ],
        "real_close_verified": real_close,
        "mirror_reported_realized_pnl": trade.get("realized_pnl_gbp") if not real_close else None,
    }


def _postmortem_completion(
    trade: dict[str, Any],
    metrics: dict[str, Any],
    *,
    guarded_close_verified: bool,
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not guarded_close_verified:
        missing.append("verified_guarded_close")
    for field in (
        "realized_net_pnl",
        "holding_period_seconds",
        "exit_reason",
        "maximum_adverse_excursion",
        "maximum_favourable_excursion",
    ):
        if metrics.get(field) is None:
            missing.append(field)
    source_complete = str(trade.get("postmortem_status") or "").lower() == "postmortem_complete"
    if not source_complete:
        missing.append("postmortem_review_complete")
    return not missing, missing


def build_trade_lineage_record(
    order: dict[str, Any],
    trade: dict[str, Any],
    position: dict[str, Any],
    handoff: dict[str, Any],
    *,
    generated_at: str,
    accepted_v3_handoff_verified: bool = False,
    execution_identity: dict[str, Any] | None = None,
    guarded_close_evidence: dict[str, Any] | None = None,
    paper_epoch_id: str | None = None,
) -> dict[str, Any]:
    execution_identity = execution_identity or {}
    guarded_close_evidence = guarded_close_evidence or {}
    accepted = bool(
        accepted_v3_handoff_verified
        or execution_identity.get("accepted_v3_handoff_verified") is True
    )
    origin, lineage, missing_lineage = classify_broker_origin(
        order,
        trade,
        handoff,
        accepted_v3_handoff_verified=accepted,
        execution_identity=execution_identity,
    )
    metrics = _trade_metrics(
        order,
        trade,
        lineage,
        execution_identity=execution_identity,
        guarded_close_evidence=guarded_close_evidence,
    )
    real_closed = _guarded_close_verified(guarded_close_evidence)
    postmortem_complete, postmortem_missing = _postmortem_completion(
        trade,
        metrics,
        guarded_close_verified=real_closed,
    )
    history, current_state, reconciliation_reason = _lifecycle_history(
        order,
        trade,
        position,
        execution_identity=execution_identity,
        guarded_close_evidence=guarded_close_evidence,
        postmortem_complete=postmortem_complete,
    )
    nonproof_origin = origin != "qadam_origin_complete_lineage"
    boundary = f"{order.get('boundary', '')} {trade.get('boundary', '')}".lower()
    nonproof_marker_present = any(
        marker in boundary for marker in ("backtest", "shadow", "fixture", "synthetic")
    )
    proof_checks = {
        "real_closed_paper_trade": real_closed,
        "qadam_origin_complete_lineage": origin == "qadam_origin_complete_lineage",
        "complete_source_to_execution_lineage": not missing_lineage,
        "accepted_v3_handoff_verified": accepted,
        "postmortem_complete": postmortem_complete,
        "verified_guarded_exit": real_closed,
        "guarded_alpaca_paper_route": handoff.get("route") == "guarded_alpaca_paper_via_paperops",
        "not_backtest_shadow_fixture_or_mirror": (
            not nonproof_origin and not nonproof_marker_present
        ),
    }
    proof_eligible = all(proof_checks.values())
    lineage_evidence_class = evidence_class(lineage)
    broker_execution_fact = bool(
        accepted
        and origin == "qadam_origin_complete_lineage"
        and not nonproof_marker_present
        and current_state
        in {
            "submitted",
            "accepted",
            "partially_filled",
            "filled",
            "open",
            "exit_requested",
            "closed",
            "postmortem_complete",
        }
    )
    experimental_forward_outcome = bool(
        lineage_evidence_class == EXPERIMENTAL_UNVALIDATED and proof_eligible
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_trade_lineage",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "paper_epoch_id": paper_epoch_id,
        "lineage_record_id": stable_id(
            "paper-trade-lineage-v3",
            _record_key(order) or _record_key(trade) or _record_key(position),
        ),
        "broker_record_id": _record_key(order) or _record_key(trade) or _record_key(position),
        "order_id": order.get("order_id"),
        "trade_id": trade.get("trade_id"),
        "position_id": position.get("position_id"),
        "instrument": trade.get("instrument") or order.get("instrument") or position.get("instrument"),
        "direction": trade.get("direction") or order.get("direction") or position.get("direction"),
        "evidence_class": lineage_evidence_class,
        "broker_record_origin_class": origin,
        "canonical_origin_class": (
            "qadam_origin_paper"
            if origin.startswith("qadam_origin")
            else ("operator" if origin == "external_manual_paper_record" else "broker_mirror")
        ),
        "lineage": lineage,
        "missing_lineage": missing_lineage,
        "lineage_complete": not missing_lineage,
        "execution_identity": execution_identity,
        "guarded_close_evidence": guarded_close_evidence,
        "accepted_v3_handoff_verified": accepted,
        "lifecycle_history": history,
        "current_lifecycle_state": current_state,
        "reconciliation_required": current_state == "reconciliation_required",
        "reconciliation_reason": reconciliation_reason,
        "stale_accepted_order_policy": stale_accepted_order_policy(
            order, generated_at=generated_at
        ),
        "metrics": metrics,
        "postmortem_complete": postmortem_complete,
        "postmortem_missing_requirements": postmortem_missing,
        "proof_checks": proof_checks,
        "proof_eligible": proof_eligible,
        "proof_tiers": {
            "broker_execution_fact": broker_execution_fact,
            "experimental_forward_outcome": experimental_forward_outcome,
            "validated_edge_evidence": False,
            "validated_edge_credit": False,
        },
        "proof_ineligible_reasons": [
            name for name, passed in proof_checks.items() if passed is not True
        ],
        "proof_credit_granted": False,
        "validated_edge_evidence_granted": False,
        "validated_edge_credit_granted": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }


def _postmortem(record: dict[str, Any], trade: dict[str, Any], generated_at: str) -> dict[str, Any]:
    origin = record.get("broker_record_origin_class")
    if origin == "mirror_only_historical_record":
        state = "mirror_only_not_qadam_postmortem"
    elif record.get("current_lifecycle_state") not in {
        "closed",
        "postmortem_complete",
    }:
        state = "not_due_trade_not_closed"
    elif record.get("postmortem_complete") is not True:
        state = "postmortem_due"
    else:
        state = "postmortem_complete"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_postmortem_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "postmortem_id": stable_id("paper-postmortem-v3", record.get("trade_id")),
        "trade_id": record.get("trade_id"),
        "lineage_record_id": record.get("lineage_record_id"),
        "lineage": record.get("lineage"),
        "evidence_class": record.get("evidence_class"),
        "proof_tiers": record.get("proof_tiers"),
        "origin_class": origin,
        "state": state,
        "completion_requirements_missing": record.get("postmortem_missing_requirements", []),
        "metrics": record.get("metrics"),
        "entry_thesis": trade.get("entry_thesis")
        or "Use the linked strategy hypothesis and Research Goal as the entry thesis.",
        "exit_reason": record.get("metrics", {}).get("exit_reason"),
        "what_worked": trade.get("what_worked"),
        "what_failed": trade.get("what_failed"),
        "calibration": record.get("metrics", {}).get("edge_calibration"),
        "learning_attribution_allowed": (
            origin == "qadam_origin_complete_lineage"
            and record.get("metrics", {}).get("real_close_verified") is True
        ),
        "proposal_only": True,
        "approved": False,
        "applied": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def _component(state: str, reason: str, refs: list[str] | None = None) -> dict[str, Any]:
    return {"state": state, "reason": reason, "evidence_refs": refs or []}


def _empty_components(reason: str) -> dict[str, Any]:
    return {
        component: _component("not_attributable", reason) for component in ATTRIBUTION_COMPONENTS
    }


def _learning_record_from_trade(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    origin = str(record.get("broker_record_origin_class"))
    real_closed = record.get("metrics", {}).get("real_close_verified") is True
    if origin == "qadam_origin_complete_lineage" and real_closed:
        outcome_type = "qadam_paper_trade_outcome"
        champion_state = "proposed"
        reason = "A complete Qadam-origin outcome is available for reviewed attribution."
    elif origin == "qadam_origin_complete_lineage":
        outcome_type = "qadam_paper_lifecycle_in_progress"
        champion_state = "approved-for-paper"
        reason = (
            "The Qadam-origin paper trade is attributable but has not completed a verified exit."
        )
    elif origin == "qadam_origin_incomplete_lineage":
        outcome_type = "qadam_incomplete_lineage_outcome"
        champion_state = "degraded"
        reason = "The outcome cannot calibrate Qadam until its lineage is repaired."
    elif origin == "external_manual_paper_record":
        outcome_type = "external_manual_paper_outcome"
        champion_state = "rejected"
        reason = "An operator-origin paper outcome is excluded from autonomous edge claims."
    else:
        outcome_type = "mirror_only_historical_outcome"
        champion_state = "rejected"
        reason = "The broker mirror is historical context and is not attributable to Qadam."
    components = _empty_components(reason)
    if origin == "qadam_origin_complete_lineage":
        lineage = record.get("lineage", {})
        execution_state = "measurable" if real_closed else "monitoring"
        components.update(
            {
                "source_evidence": _component(
                    "measurable", "Source evidence is linked.", [lineage.get("source_evidence_id")]
                ),
                "strategy_hypothesis": _component(
                    "measurable",
                    "The strategy hypothesis is linked.",
                    [lineage.get("strategy_hypothesis_id")],
                ),
                "local_model_contribution": _component(
                    "linked_for_review",
                    "The Research Goal identifies the local research lane; contribution remains observational until the postmortem is complete.",
                    [lineage.get("research_goal_id")],
                ),
                "frontier_model_contribution": _component(
                    "linked_for_review",
                    "The strategy hypothesis carries the frontier review context without granting it execution authority.",
                    [lineage.get("strategy_hypothesis_id")],
                ),
                "nonlinear_quantum_review": _component(
                    "linked_for_review",
                    "Nonlinear and quantum usefulness is attributed through the linked edge, not assumed from trade performance alone.",
                    [lineage.get("edge_id")],
                ),
                "akber_stages": _component(
                    "measurable", "Akber result is linked.", [lineage.get("akber_result_id")]
                ),
                "router_decision": _component(
                    "measurable", "Router decision is linked.", [lineage.get("router_decision_id")]
                ),
                "portfolio_risk_decision": _component(
                    "measurable", "Risk proposal is linked.", [lineage.get("risk_proposal_id")]
                ),
                "paperops_broker_execution": _component(
                    execution_state,
                    "Paper execution is linked; complete quality attribution requires a verified guarded exit.",
                    [record.get("order_id")],
                ),
                "exit_decision": _component(
                    "measurable" if real_closed else "pending",
                    "The guarded exit receipt is verified."
                    if real_closed
                    else "No verified guarded exit receipt exists yet.",
                    [record.get("guarded_close_evidence", {}).get("request_fingerprint")],
                ),
                "provider_system_reliability": _component(
                    "observed",
                    "The submission and lifecycle readback path retained a sanitized broker identity.",
                    [record.get("execution_identity", {}).get("v3_consumption_receipt_id")],
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_attribution_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "attribution_id": stable_id(
            "learning-attribution-v3", outcome_type, record.get("lineage_record_id")
        ),
        "outcome_type": outcome_type,
        "source_record_id": record.get("lineage_record_id"),
        "origin_class": origin,
        "lineage": record.get("lineage"),
        "outcome_metrics": record.get("metrics"),
        "component_attribution": components,
        "champion_challenger": {
            "state": champion_state,
            "proposal_type": (
                "paper_lifecycle_repair_proposal"
                if origin == "qadam_origin_incomplete_lineage"
                else "strategy_evidence_review_proposal"
            ),
            "reason": reason,
            "proposal_only": True,
            "approved": False,
            "applied": False,
        },
        "source_trust_mutated": False,
        "strategy_weight_mutated": False,
        "threshold_mutated": False,
        "risk_policy_mutated": False,
        "authority_mutated": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def _research_attribution(
    *,
    outcome_type: str,
    source_record_id: str,
    champion_state: str,
    reason: str,
    generated_at: str,
    refs: list[str],
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    components = _empty_components(reason)
    components["provider_system_reliability"] = _component(
        "blocked" if champion_state == "degraded" else "observed", reason, refs
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_attribution_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "attribution_id": stable_id("learning-attribution-v3", outcome_type, source_record_id),
        "outcome_type": outcome_type,
        "source_record_id": source_record_id,
        "origin_class": "qadam_runtime",
        "lineage": lineage or {},
        "outcome_metrics": {},
        "component_attribution": components,
        "champion_challenger": {
            "state": champion_state,
            "proposal_type": "research_repair_proposal",
            "reason": reason,
            "proposal_only": True,
            "approved": False,
            "applied": False,
        },
        "source_trust_mutated": False,
        "strategy_weight_mutated": False,
        "threshold_mutated": False,
        "risk_policy_mutated": False,
        "authority_mutated": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def _drift_states(
    source_records: list[dict[str, Any]],
    shadow_calibration: dict[str, Any],
    edge_summary: dict[str, Any],
    qadam_records: list[dict[str, Any]],
) -> dict[str, Any]:
    source_count = len(source_records)
    stale_count = sum(
        str(record.get("freshness_state") or "") != "fresh" for record in source_records
    )
    slippage_values = [
        safe_float(record.get("metrics", {}).get("slippage_per_unit"))
        for record in qadam_records
        if record.get("metrics", {}).get("slippage_per_unit") is not None
    ]
    calibrated_count = sum(
        record.get("metrics", {}).get("edge_calibration")
        in {"direction_supported", "direction_not_supported"}
        for record in qadam_records
    )
    return {
        "calibration_drift": {
            "state": "not_measurable"
            if safe_float(shadow_calibration.get("completed_outcome_count")) == 0
            else "monitoring",
            "completed_shadow_outcome_count": shadow_calibration.get("completed_outcome_count", 0),
            "completed_qadam_outcome_count": len(qadam_records),
            "calibrated_qadam_outcome_count": calibrated_count,
            "automatic_threshold_change_allowed": False,
        },
        "edge_decay": {
            "state": "not_measurable_no_validated_edge"
            if safe_float(edge_summary.get("validated_edge_count")) == 0
            else "monitoring",
            "validated_edge_count": edge_summary.get("validated_edge_count", 0),
            "automatic_strategy_retirement_allowed": False,
        },
        "source_drift": {
            "state": (
                "degraded"
                if source_count and stale_count
                else "stable"
                if source_count
                else "not_measurable"
            ),
            "source_count": source_count,
            "nonfresh_source_count": stale_count,
            "nonfresh_ratio": round(stale_count / source_count, 8) if source_count else None,
        },
        "execution_drift": {
            "state": "not_measurable_no_qadam_origin_trades" if not qadam_records else "monitoring",
            "qadam_origin_complete_trade_count": len(qadam_records),
            "measured_slippage_count": len(slippage_values),
            "mean_slippage_per_unit": (
                round(sum(slippage_values) / len(slippage_values), 10) if slippage_values else None
            ),
            "automatic_execution_policy_change_allowed": False,
        },
    }


def build_paper_lineage_and_proof_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    current_epoch = read_current_epoch(settings)
    all_orders = read_jsonl(runtime / PAPER_ORDERS_ARTIFACT)
    all_positions = read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT)
    all_trades = read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT)
    orders, excluded_orders = _filter_current_execution_epoch(
        all_orders, current_epoch=current_epoch
    )
    positions, excluded_positions = _filter_current_execution_epoch(
        all_positions, current_epoch=current_epoch
    )
    trades, excluded_trades = _filter_current_execution_epoch(
        all_trades, current_epoch=current_epoch
    )
    active_epoch_id = str(current_epoch.get("paper_epoch_id") or "").strip() or None
    accepted_handoffs = read_jsonl(runtime / ACCEPTED_HANDOFF_ARTIFACT)
    handoff_receipts = read_jsonl(runtime / HANDOFF_RECEIPTS_ARTIFACT)
    submission_ledger = read_json(runtime / PAPEROPS_SUBMISSION_LEDGER_ARTIFACT)
    lifecycle_poller = read_json(runtime / PAPEROPS_LIFECYCLE_POLLER_ARTIFACT)
    exit_path = read_json(runtime / PAPEROPS_EXIT_PATH_ARTIFACT)
    exit_history = read_jsonl(runtime / PAPEROPS_EXIT_PATH_HISTORY_ARTIFACT)
    close_to_ledger = read_json(runtime / PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT)
    prior_lineage_records = read_jsonl(runtime / LINEAGE_ARTIFACT)
    router_decisions = read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    shadow_outcomes = read_jsonl(runtime / SHADOW_OUTCOMES_ARTIFACT)
    risk_rejections = read_jsonl(runtime / RISK_REJECTIONS_ARTIFACT)
    foundry_rejections = read_jsonl(runtime / FOUNDRY_REJECTIONS_ARTIFACT)
    release = read_json(runtime / RELEASE_READINESS_ARTIFACT)
    shadow_calibration = read_json(runtime / SHADOW_CALIBRATION_ARTIFACT)
    edge_summary = read_json(runtime / EDGE_SUMMARY_ARTIFACT)
    source_operational = read_jsonl(runtime / SOURCE_OPERATIONAL_ARTIFACT)
    applied_versions = [
        record
        for record in read_jsonl(runtime / APPLIED_VERSIONS_ARTIFACT)
        if record.get("decision_state") == "applied"
        and isinstance(record.get("approval"), dict)
        and record.get("approval", {}).get("approved") is True
    ]
    receipt_by_id = {
        str(record.get("consumption_receipt_id")): record
        for record in handoff_receipts
        if record.get("consumption_receipt_id")
    }
    accepted_by_handoff_id: dict[str, dict[str, Any]] = {}
    accepted_verified_by_handoff_id: dict[str, bool] = {}
    for accepted_record in accepted_handoffs:
        source_handoff = _accepted_source_handoff(accepted_record)
        handoff_id = str(source_handoff.get("paperops_handoff_id") or "")
        if not handoff_id:
            continue
        accepted_by_handoff_id[handoff_id] = source_handoff
        accepted_verified_by_handoff_id[handoff_id] = _accepted_handoff_verified(
            accepted_record, receipt_by_id
        )
    submission_records = [
        record
        for record in submission_ledger.get("submission_records", []) or []
        if isinstance(record, dict)
    ]
    lifecycle_records = [
        record
        for record in lifecycle_poller.get("lifecycle_mirror_records", []) or []
        if isinstance(record, dict)
    ]
    execution_by_broker_hash, execution_by_client_hash = _execution_identity_index(
        submission_records, lifecycle_records
    )
    close_by_broker_hash, close_by_client_hash = _close_record_index(exit_path, exit_history)
    prior_by_broker_record_id = {
        str(record.get("broker_record_id")): record
        for record in prior_lineage_records
        if record.get("broker_record_id")
    }
    orders_by_id = {_record_key(record): record for record in orders if _record_key(record)}
    trades_by_id = {_record_key(record): record for record in trades if _record_key(record)}
    positions_by_id = {_record_key(record): record for record in positions if _record_key(record)}
    record_ids = sorted(set(orders_by_id) | set(trades_by_id) | set(positions_by_id))
    lineage_records: list[dict[str, Any]] = []
    trade_by_lineage_id: dict[str, dict[str, Any]] = {}
    for record_id in record_ids:
        order = orders_by_id.get(record_id, {})
        trade = trades_by_id.get(record_id, {})
        position = positions_by_id.get(record_id, {})
        previous = prior_by_broker_record_id.get(record_id, {})
        execution_identity = _matching_execution_identity(
            order,
            trade,
            by_broker_hash=execution_by_broker_hash,
            by_client_hash=execution_by_client_hash,
            previous=previous,
        )
        handoff_id = str(
            execution_identity.get("paperops_handoff_id")
            or previous.get("lineage", {}).get("paperops_handoff_id")
            or ""
        )
        handoff = accepted_by_handoff_id.get(handoff_id, {})
        if not handoff:
            handoff = _pseudo_handoff_from_execution(execution_identity)
        accepted_verified = bool(
            accepted_verified_by_handoff_id.get(handoff_id)
            or execution_identity.get("accepted_v3_handoff_verified") is True
            or previous.get("accepted_v3_handoff_verified") is True
        )
        guarded_close_evidence = _matching_close_record(
            order,
            trade,
            execution_identity,
            by_broker_hash=close_by_broker_hash,
            by_client_hash=close_by_client_hash,
            previous=previous,
        )
        record = build_trade_lineage_record(
            order,
            trade,
            position,
            handoff,
            generated_at=generated,
            accepted_v3_handoff_verified=accepted_verified,
            execution_identity=execution_identity,
            guarded_close_evidence=guarded_close_evidence,
            paper_epoch_id=active_epoch_id,
        )
        lineage_records.append(record)
        trade_by_lineage_id[str(record["lineage_record_id"])] = trade
    postmortems = [
        _postmortem(
            record,
            trade_by_lineage_id.get(str(record["lineage_record_id"]), {}),
            generated,
        )
        for record in lineage_records
        if record.get("current_lifecycle_state") in {"closed", "postmortem_complete"}
        or trade_by_lineage_id.get(str(record["lineage_record_id"]), {}).get("closed_at")
    ]
    state_counts = Counter(record.get("current_lifecycle_state") for record in lineage_records)
    origin_counts = Counter(record.get("broker_record_origin_class") for record in lineage_records)
    verified_guarded_closed_records = [
        record
        for record in lineage_records
        if record.get("metrics", {}).get("real_close_verified") is True
    ]
    reconciliation_count = sum(
        record.get("current_lifecycle_state") == "reconciliation_required"
        for record in lineage_records
    )
    ambiguous_count = sum(
        record.get("current_lifecycle_state") not in LIFECYCLE_STATES
        or record.get("broker_record_origin_class") not in ORIGIN_CLASSES
        or (
            record.get("current_lifecycle_state") == "reconciliation_required"
            and not record.get("reconciliation_reason")
        )
        for record in lineage_records
    )
    lifecycle = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "paper_epoch_id": active_epoch_id,
        "paper_epoch_kind": current_epoch.get("paper_epoch_kind") or "legacy_test",
        "epoch_filter_active": is_clean_epoch_kind(current_epoch.get("paper_epoch_kind")),
        "excluded_prior_epoch_order_count": len(excluded_orders),
        "excluded_prior_epoch_position_count": len(excluded_positions),
        "excluded_prior_epoch_trade_count": len(excluded_trades),
        "status": "ready" if ambiguous_count == 0 else "reconciliation_required",
        "broker_record_count": len(lineage_records),
        "order_record_count": len(orders),
        "position_record_count": len(positions),
        "closed_trade_record_count": len(verified_guarded_closed_records),
        "broker_fill_mirror_projection_count": len(trades),
        "state_counts": dict(sorted(state_counts.items(), key=lambda item: str(item[0]))),
        "origin_counts": dict(sorted(origin_counts.items(), key=lambda item: str(item[0]))),
        "ambiguous_order_count": ambiguous_count,
        "reconciliation_required_count": reconciliation_count,
        "every_record_has_origin_class": len(lineage_records)
        == sum(
            record.get("broker_record_origin_class") in ORIGIN_CLASSES for record in lineage_records
        ),
        "stale_accepted_order_policy": {
            "policy_version": "qadam-stale-accepted-paper-order.1-frozen",
            "wait_until_seconds": STALE_ACCEPTED_SECONDS,
            "cancel_replace_proposal_until_seconds": RECONCILIATION_SECONDS,
            "older_order_action": "no_action_reconciliation_required",
            "automatic_cancel_allowed": False,
            "automatic_replace_allowed": False,
        },
        "required_lifecycle_states": sorted(LIFECYCLE_STATES),
        "accepted_v3_handoff_count": sum(accepted_verified_by_handoff_id.values()),
        "durable_submission_identity_count": len(submission_records),
        "guarded_close_record_count": len(close_by_broker_hash),
        "close_to_ledger_status": close_to_ledger.get("status", "not_run"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    proof_eligible_records = [record for record in lineage_records if record.get("proof_eligible")]
    proof = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_proof_eligibility",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "paper_epoch_id": active_epoch_id,
        "paper_epoch_kind": current_epoch.get("paper_epoch_kind") or "legacy_test",
        "status": "ready_no_eligible_qadam_trade"
        if not proof_eligible_records
        else "eligible_records_available_for_separate_credit_review",
        "closed_paper_trade_count": len(verified_guarded_closed_records),
        "broker_fill_mirror_projection_count": len(trades),
        "qadam_origin_complete_lineage_count": origin_counts.get(
            "qadam_origin_complete_lineage", 0
        ),
        "qadam_origin_incomplete_lineage_count": origin_counts.get(
            "qadam_origin_incomplete_lineage", 0
        ),
        "external_manual_paper_record_count": origin_counts.get("external_manual_paper_record", 0),
        "mirror_only_historical_record_count": origin_counts.get(
            "mirror_only_historical_record", 0
        ),
        "proof_eligible_count": len(proof_eligible_records),
        "broker_execution_fact_count": sum(
            record.get("proof_tiers", {}).get("broker_execution_fact") is True
            for record in lineage_records
        ),
        "experimental_forward_outcome_count": sum(
            record.get("proof_tiers", {}).get("experimental_forward_outcome") is True
            for record in lineage_records
        ),
        "validated_edge_evidence_count": 0,
        "validated_edge_credit_count": 0,
        "proof_eligible_lineage_record_ids": [
            record.get("lineage_record_id") for record in proof_eligible_records
        ],
        "mirror_record_backfill_proof_credit_count": 0,
        "backtest_proof_credit_count": 0,
        "shadow_proof_credit_count": 0,
        "fixture_proof_credit_count": 0,
        "proof_credit_created_count": 0,
        "eligibility_is_not_credit": True,
        "proof_requires_real_closed_qadam_origin_trade_with_complete_lineage": True,
        "authority": authority_flags(),
    }
    learning = [_learning_record_from_trade(record, generated) for record in lineage_records]
    for record in foundry_rejections:
        learning.append(
            _research_attribution(
                outcome_type="strategy_hypothesis_rejected",
                source_record_id=str(record.get("rejection_id") or "unknown"),
                champion_state="rejected",
                reason="The hypothesis was rejected before Akber because edge evidence was incomplete.",
                generated_at=generated,
                refs=[str(record.get("score_id") or record.get("edge_id") or "")],
            )
        )
    for record in akber_results:
        decision = str(record.get("decision") or "unknown")
        learning.append(
            _research_attribution(
                outcome_type=f"akber_{decision}",
                source_record_id=str(record.get("akber_result_id") or "unknown"),
                champion_state="approved-for-research" if decision == "pass" else "degraded",
                reason=str(record.get("plain_english_explanation") or "Akber decision recorded."),
                generated_at=generated,
                refs=[str(record.get("hypothesis_id") or "")],
                lineage={
                    "applied_learning_version_ids": record.get("applied_learning_version_ids", []),
                    "stage1_learning_input_version": record.get("stage1_learning_input_version"),
                },
            )
        )
    for record in router_decisions:
        state = str(record.get("final_state") or "unknown")
        learning.append(
            _research_attribution(
                outcome_type=f"router_{state}",
                source_record_id=str(record.get("router_decision_id") or "unknown"),
                champion_state=(
                    "approved-for-paper" if state == "paper-review-candidate" else "degraded"
                ),
                reason=str(record.get("final_reason") or "Router decision recorded."),
                generated_at=generated,
                refs=[str(record.get("setup_id") or "")],
                lineage=record.get("lineage") if isinstance(record.get("lineage"), dict) else {},
            )
        )
    for record in shadow_outcomes:
        learning.append(
            _research_attribution(
                outcome_type="forward_shadow_outcome",
                source_record_id=str(record.get("outcome_id") or "unknown"),
                champion_state="shadowing",
                reason="A real-time no-order shadow outcome was observed.",
                generated_at=generated,
                refs=[str(record.get("decision_id") or "")],
            )
        )
    for record in risk_rejections:
        learning.append(
            _research_attribution(
                outcome_type="portfolio_risk_rejection",
                source_record_id=str(record.get("rejection_id") or "unknown"),
                champion_state="rejected",
                reason="Portfolio risk rejected the setup before PaperOps.",
                generated_at=generated,
                refs=[str(record.get("setup_id") or "")],
            )
        )
    if release.get("blockers"):
        learning.append(
            _research_attribution(
                outcome_type="operational_release_blocked",
                source_record_id="research-lock-release-readiness",
                champion_state="degraded",
                reason="Research evidence or explicit approvals are incomplete; PaperOps remains watch-only.",
                generated_at=generated,
                refs=[str(blocker) for blocker in release.get("blockers", [])[:12]],
            )
        )
    qadam_complete_records = [
        record
        for record in lineage_records
        if record.get("broker_record_origin_class") == "qadam_origin_complete_lineage"
    ]
    qadam_closed_records = [
        record
        for record in qadam_complete_records
        if record.get("metrics", {}).get("real_close_verified") is True
    ]
    qadam_realized = [
        record.get("metrics", {}).get("realized_net_pnl")
        for record in qadam_closed_records
        if record.get("metrics", {}).get("realized_net_pnl") is not None
    ]
    drift = _drift_states(
        source_operational,
        shadow_calibration,
        edge_summary,
        qadam_closed_records,
    )
    performance = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_performance_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "paper_epoch_id": active_epoch_id,
        "paper_epoch_kind": current_epoch.get("paper_epoch_kind") or "legacy_test",
        "status": "not_measurable_no_qadam_origin_outcomes"
        if not qadam_closed_records
        else "qadam_origin_performance_available",
        "qadam_origin_complete_trade_count": len(qadam_complete_records),
        "qadam_origin_verified_closed_trade_count": len(qadam_closed_records),
        "qadam_origin_incomplete_trade_count": origin_counts.get(
            "qadam_origin_incomplete_lineage", 0
        ),
        "mirror_only_historical_trade_count": origin_counts.get("mirror_only_historical_record", 0),
        "qadam_realized_net_pnl": round(sum(safe_float(value) for value in qadam_realized), 10)
        if qadam_realized
        else None,
        "qadam_win_count": sum(safe_float(value) > 0 for value in qadam_realized),
        "qadam_loss_count": sum(safe_float(value) < 0 for value in qadam_realized),
        "performance_claim_allowed": bool(qadam_closed_records and qadam_realized),
        "mirror_pnl_included_in_qadam_performance": False,
        "drift_states": drift,
        "learning_attribution_record_count": len(learning),
        "learning_outputs_proposal_only": True,
        "observed_preexisting_applied_learning_version_count": len(applied_versions),
        "applied_learning_update_count": 0,
        "proof_credit_created_count": 0,
        "paper_order_created_count": 0,
        "authority": authority_flags(),
    }
    return {
        "lifecycle": lifecycle,
        "lineage": lineage_records,
        "postmortems": postmortems,
        "proof": proof,
        "learning": learning,
        "performance": performance,
    }


def validate_paper_lineage_and_proof_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lineage = state["lineage"]
    lifecycle_epoch_id = state["lifecycle"].get("paper_epoch_id")
    if state["lifecycle"].get("broker_record_count") != len(lineage):
        errors.append("paper_lifecycle_record_count_mismatch")
    if state["lifecycle"].get("ambiguous_order_count") != 0:
        errors.append("paper_lifecycle_ambiguous_order_present")
    record_ids: set[str] = set()
    for record in lineage:
        record_id = str(record.get("lineage_record_id") or "")
        if not record_id or record_id in record_ids:
            errors.append("paper_lineage_id_missing_or_duplicate")
        record_ids.add(record_id)
        if state["lifecycle"].get("epoch_filter_active") is True and (
            not lifecycle_epoch_id or record.get("paper_epoch_id") != lifecycle_epoch_id
        ):
            errors.append(f"paper_lineage_epoch_mismatch:{record_id}")
        origin = record.get("broker_record_origin_class")
        if origin not in ORIGIN_CLASSES:
            errors.append(f"paper_lineage_origin_invalid:{record_id}")
        if record.get("current_lifecycle_state") not in LIFECYCLE_STATES:
            errors.append(f"paper_lifecycle_state_invalid:{record_id}")
        if not record.get("lifecycle_history"):
            errors.append(f"paper_lifecycle_history_missing:{record_id}")
        proof_checks = record.get("proof_checks")
        proof_checks = proof_checks if isinstance(proof_checks, dict) else {}
        expected_eligible = bool(proof_checks) and all(proof_checks.values())
        if record.get("proof_eligible") is not expected_eligible:
            errors.append(f"paper_proof_eligibility_mismatch:{record_id}")
        if record.get("proof_eligible") is True and origin != "qadam_origin_complete_lineage":
            errors.append(f"non_qadam_origin_proof_eligible:{record_id}")
        if (
            origin == "qadam_origin_complete_lineage"
            and record.get("accepted_v3_handoff_verified") is not True
        ):
            errors.append(f"qadam_complete_origin_without_accepted_handoff:{record_id}")
        if record.get("current_lifecycle_state") in {"closed", "postmortem_complete"} and (
            record.get("metrics", {}).get("real_close_verified") is not True
        ):
            errors.append(f"paper_lifecycle_closed_without_guarded_exit:{record_id}")
        if record.get("proof_eligible") is True:
            if record.get("accepted_v3_handoff_verified") is not True:
                errors.append(f"paper_proof_without_accepted_handoff:{record_id}")
            if record.get("metrics", {}).get("real_close_verified") is not True:
                errors.append(f"paper_proof_without_verified_guarded_exit:{record_id}")
            if record.get("postmortem_complete") is not True:
                errors.append(f"paper_proof_without_complete_postmortem:{record_id}")
        if origin == "mirror_only_historical_record" and record.get("proof_eligible") is True:
            errors.append(f"mirror_record_proof_eligible:{record_id}")
        if record.get("proof_credit_granted") is not False:
            errors.append(f"paper_proof_credit_granted:{record_id}")
        tiers = record.get("proof_tiers")
        tiers = tiers if isinstance(tiers, dict) else {}
        if tiers.get("experimental_forward_outcome") is True and (
            record.get("evidence_class") != EXPERIMENTAL_UNVALIDATED
            or record.get("proof_eligible") is not True
        ):
            errors.append(f"experimental_outcome_tier_invalid:{record_id}")
        if tiers.get("validated_edge_evidence") is not False:
            errors.append(f"lineage_granted_validated_edge_evidence:{record_id}")
        if tiers.get("validated_edge_credit") is not False:
            errors.append(f"lineage_granted_validated_edge_credit:{record_id}")
        if record.get("paper_order_created") is not False:
            errors.append(f"paper_lineage_created_order:{record_id}")
        stale_policy = record.get("stale_accepted_order_policy", {})
        if stale_policy.get("automatic_cancel_allowed") is not False:
            errors.append(f"paper_lifecycle_automatic_cancel_allowed:{record_id}")
        if stale_policy.get("automatic_replace_allowed") is not False:
            errors.append(f"paper_lifecycle_automatic_replace_allowed:{record_id}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="paper_lineage"))
    proof = state["proof"]
    for field in (
        "mirror_record_backfill_proof_credit_count",
        "backtest_proof_credit_count",
        "shadow_proof_credit_count",
        "fixture_proof_credit_count",
        "proof_credit_created_count",
        "validated_edge_evidence_count",
        "validated_edge_credit_count",
    ):
        if proof.get(field) != 0:
            errors.append(f"paper_proof_forbidden_count_nonzero:{field}")
    if proof.get("eligibility_is_not_credit") is not True:
        errors.append("paper_proof_eligibility_credit_boundary_missing")
    if proof.get("proof_eligible_count") != sum(
        record.get("proof_eligible") is True for record in lineage
    ):
        errors.append("paper_proof_eligible_count_mismatch")
    for record in state["postmortems"]:
        if record.get("proof_credit_granted") is not False:
            errors.append("paper_postmortem_granted_proof_credit")
        if record.get("state") == "postmortem_complete" and record.get(
            "completion_requirements_missing"
        ):
            errors.append("paper_postmortem_complete_with_missing_requirements")
        if record.get("proposal_only") is not True or record.get("applied") is not False:
            errors.append("paper_postmortem_not_inert_proposal")
        errors.extend(validate_authority(record.get("authority", {}), prefix="paper_postmortem"))
    for record in state["learning"]:
        components = record.get("component_attribution")
        if not isinstance(components, dict) or set(components) != set(ATTRIBUTION_COMPONENTS):
            errors.append("learning_attribution_component_contract_incomplete")
        champion = record.get("champion_challenger", {})
        if champion.get("state") not in CHAMPION_CHALLENGER_STATES:
            errors.append("learning_champion_challenger_state_invalid")
        if champion.get("proposal_only") is not True or champion.get("applied") is not False:
            errors.append("learning_output_not_inert_proposal")
        for field in (
            "source_trust_mutated",
            "strategy_weight_mutated",
            "threshold_mutated",
            "risk_policy_mutated",
            "authority_mutated",
            "paper_order_created",
            "proof_credit_granted",
        ):
            if record.get(field) is not False:
                errors.append(f"learning_unsafe_mutation:{field}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="learning_v3"))
    performance = state["performance"]
    if performance.get("mirror_pnl_included_in_qadam_performance") is not False:
        errors.append("mirror_pnl_included_in_qadam_performance")
    for field in (
        "applied_learning_update_count",
        "proof_credit_created_count",
        "paper_order_created_count",
    ):
        if performance.get(field) != 0:
            errors.append(f"paper_performance_forbidden_count_nonzero:{field}")
    for payload, prefix in (
        (state["lifecycle"], "paper_lifecycle"),
        (proof, "paper_proof"),
        (performance, "paper_performance"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_paper_lineage_and_proof(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_paper_lineage_and_proof_state(settings)
    store.write_json(LIFECYCLE_ARTIFACT, state["lifecycle"])
    store.write_jsonl(LINEAGE_ARTIFACT, state["lineage"])
    store.write_jsonl(POSTMORTEMS_ARTIFACT, state["postmortems"])
    store.write_json(PROOF_ARTIFACT, state["proof"])
    store.write_jsonl(ATTRIBUTION_ARTIFACT, state["learning"])
    store.write_json(PERFORMANCE_ARTIFACT, state["performance"])
    errors = validate_paper_lineage_and_proof_state(state)
    qadam_complete_count = state["proof"]["qadam_origin_complete_lineage_count"]
    proof_eligible_count = state["proof"]["proof_eligible_count"]
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lineage_and_proof_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "evidence_maturing"
        if not errors and proof_eligible_count == 0
        else ("passed" if not errors else "blocked"),
        "implementation_ready": not errors,
        "broker_record_count": len(state["lineage"]),
        "ambiguous_order_count": state["lifecycle"]["ambiguous_order_count"],
        "reconciliation_required_count": state["lifecycle"]["reconciliation_required_count"],
        "every_record_has_origin_class": state["lifecycle"]["every_record_has_origin_class"],
        "qadam_origin_complete_lineage_count": qadam_complete_count,
        "qadam_origin_verified_closed_trade_count": state["performance"][
            "qadam_origin_verified_closed_trade_count"
        ],
        "accepted_v3_handoff_count": state["lifecycle"]["accepted_v3_handoff_count"],
        "durable_submission_identity_count": state["lifecycle"][
            "durable_submission_identity_count"
        ],
        "mirror_only_historical_record_count": state["proof"][
            "mirror_only_historical_record_count"
        ],
        "proof_eligible_count": proof_eligible_count,
        "mirror_record_backfill_proof_credit_count": 0,
        "proof_credit_created_count": 0,
        "learning_attribution_record_count": len(state["learning"]),
        "applied_learning_update_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
