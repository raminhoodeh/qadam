"""Bridge the active V3 decision path into canonical CATC transactions."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_decision_transaction import (
    DecisionTransaction,
    Direction,
    GateDecision,
    GateSeverity,
    GateState,
    PrimaryBlocker,
    RouterState,
)
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir

SCHEMA_VERSION = "qadam_control_plane_bridge.v1"

ROUTER_STATE_MAP = {
    "reject": RouterState.REJECT,
    "watchlist": RouterState.WATCHLIST,
    "shadow-only": RouterState.SHADOW_ONLY,
    "hold": RouterState.HOLD,
    "repair-requested": RouterState.REPAIR_REQUESTED,
    "blocked-safety-boundary": RouterState.BLOCKED_SAFETY_BOUNDARY,
    "paper-review-candidate": RouterState.PAPER_REVIEW_CANDIDATE,
    "experimental-paper-review-candidate": RouterState.PAPER_REVIEW_CANDIDATE,
    "validated_paper_review_candidate": RouterState.PAPER_REVIEW_CANDIDATE,
    "experimental_paper_review_candidate": RouterState.PAPER_REVIEW_CANDIDATE,
}


def _blocker_class(reason: str, final_state: str) -> str:
    lowered = reason.lower()
    if final_state == "blocked-safety-boundary" or any(
        token in lowered for token in ("safety", "live_capital", "route_not_released")
    ):
        return "safety"
    if "duplicate" in lowered or "idempotency" in lowered:
        return "duplicate"
    if any(token in lowered for token in ("drawdown", "risk_budget", "daily_loss")):
        return "risk"
    if any(token in lowered for token in ("lineage", "schema", "contract", "mapping")):
        return "contract_defect"
    if any(token in lowered for token in ("market_closed", "outside_regular_session")):
        return "market_session"
    if any(token in lowered for token in ("provider", "quote", "context_expired")):
        return "provider"
    return "investment"


def _primary_blocker(decision: dict[str, Any]) -> PrimaryBlocker | None:
    final_state = str(decision.get("final_state") or "hold")
    if final_state in {
        "paper-review-candidate",
        "experimental-paper-review-candidate",
        "validated_paper_review_candidate",
        "experimental_paper_review_candidate",
    }:
        return None
    reason = str(decision.get("primary_root_cause") or final_state or "decision_hold")
    consequences = [
        *[str(value) for value in decision.get("repair_reasons", [])],
        *[str(value) for value in decision.get("hard_vetoes", [])],
        *[str(value) for value in decision.get("hold_reasons", [])],
    ]
    consequences = [value for value in dict.fromkeys(consequences) if value != reason]
    return PrimaryBlocker(
        blocker_code=reason,
        blocker_class=_blocker_class(reason, final_state),
        summary=str(decision.get("final_reason") or reason.replace("_", " ").capitalize()),
        retryable=any(
            token in reason.lower()
            for token in ("market_closed", "provider", "quote", "stale", "not_reached")
        ),
        dependent_consequences=tuple(consequences),
    )


def _gate_decisions(decision: dict[str, Any]) -> tuple[GateDecision, ...]:
    snapshot = decision.get("gate_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    rows: list[GateDecision] = []
    for sequence, (name, value) in enumerate(sorted(snapshot.items())):
        if name == "route":
            passed = value == "guarded_alpaca_paper_via_paperops"
        elif name == "qctrl_state":
            passed = value in {"pass", "passed", "not_required"}
        elif name in {
            "duplicate_exposure_conflict",
            "same_signal_reentry_conflict",
            "drawdown_breached",
        }:
            passed = value is False
        else:
            passed = value is True
        rows.append(
            GateDecision(
                gate_decision_id=f"{decision.get('router_decision_id')}:{name}",
                gate_name=name,
                sequence=sequence,
                state=GateState.PASS if passed else GateState.HOLD,
                severity=GateSeverity.HARD,
                measured_value=value if isinstance(value, (float, int, str, bool)) else None,
                threshold=True,
                explanation=(
                    f"Router gate '{name}' passed."
                    if passed
                    else f"Router gate '{name}' did not pass in this decision generation."
                ),
                size_haircut=1.0,
            )
        )
    return tuple(rows)


def _transaction(
    decision: dict[str, Any],
    setup: dict[str, Any] | None,
) -> DecisionTransaction:
    setup = setup or {}
    lineage = decision.get("lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    idempotency = decision.get("idempotency_material")
    idempotency = idempotency if isinstance(idempotency, dict) else {}
    raw_direction = str(decision.get("direction") or "abstain").lower()
    direction = Direction.LONG if raw_direction in {"long", "buy"} else (
        Direction.SHORT if raw_direction in {"short", "sell"} else Direction.ABSTAIN
    )
    final_state = str(decision.get("final_state") or "hold")
    timestamp = str(decision.get("generated_at") or now_iso())
    return DecisionTransaction(
        decision_id=str(decision.get("router_decision_id")),
        generation_id=str(
            decision.get("router_execution_generation_id")
            or decision.get("decision_generation_id")
            or "legacy-generation-unknown"
        ),
        candidate_identity=str(
            decision.get("candidate_identity_id") or decision.get("setup_id")
        ),
        idempotency_key=str(
            idempotency.get("idempotency_key")
            or f"decision-only:{decision.get('router_decision_id')}"
        ),
        research_goal_id=str(
            lineage.get("research_goal_id") or setup.get("research_goal_id") or "research-goal-unknown"
        ),
        evidence_class=str(decision.get("evidence_class") or "unclassified"),
        strategy_id=str(
            setup.get("strategy_family_id")
            or lineage.get("strategy_family_id")
            or "strategy-unclassified"
        ),
        strategy_version=str(
            lineage.get("strategy_version_id")
            or setup.get("strategy_version_id")
            or "strategy-version-unclassified"
        ),
        instrument=str(decision.get("execution_symbol") or decision.get("instrument")),
        direction=direction,
        stage="router_terminal",
        created_at=timestamp,
        updated_at=timestamp,
        trigger={
            "setup_id": decision.get("setup_id"),
            "hypothesis_id": decision.get("hypothesis_id"),
            "lineage": lineage,
        },
        economic_signal_identity_id=decision.get("economic_signal_identity_id"),
        evidence_digest=decision.get("evidence_digest"),
        decision_policy_versions=(
            setup.get("decision_policy_versions")
            if isinstance(setup.get("decision_policy_versions"), dict)
            else {}
        ),
        market_judgment=(
            decision.get("market_judgment")
            if isinstance(decision.get("market_judgment"), dict)
            else {}
        ),
        uncertainty_actions=tuple(
            value
            for value in decision.get("uncertainty_actions", [])
            if isinstance(value, dict)
        ),
        adaptive_size=(
            decision.get("adaptive_size")
            if isinstance(decision.get("adaptive_size"), dict)
            else {}
        ),
        delayed_entry=(
            decision.get("delayed_entry")
            if isinstance(decision.get("delayed_entry"), dict)
            else {}
        ),
        signal_lifecycle={
            "economic_signal_identity_id": decision.get("economic_signal_identity_id"),
            "evidence_digest": decision.get("evidence_digest"),
            "state": decision.get("decision_consequence") or final_state,
        },
        gate_decisions=_gate_decisions(decision),
        primary_blocker=_primary_blocker(decision),
        router_state=ROUTER_STATE_MAP.get(final_state, RouterState.HOLD),
    )


def persist_router_state(
    state: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    store = ControlPlaneStore.from_settings(settings)
    setup_by_id = {
        str(row.get("setup_id") or ""): row
        for row in state.get("setups", [])
        if isinstance(row, dict)
    }
    inserted_decisions = 0
    inserted_gates = 0
    errors: list[str] = []
    for decision in state.get("decisions", []):
        try:
            transaction = _transaction(
                decision,
                setup_by_id.get(str(decision.get("setup_id") or "")),
            )
            inserted_decisions += int(store.create_decision(transaction))
            for gate in transaction.gate_decisions:
                inserted_gates += int(
                    store.record_gate_decision(
                        gate_decision_id=gate.gate_decision_id,
                        decision_id=transaction.decision_id,
                        gate_name=gate.gate_name,
                        sequence=gate.sequence,
                        state=gate.state.value,
                        severity=gate.severity.value,
                        payload=gate.model_dump(mode="json"),
                        created_at=transaction.created_at,
                    )
                )
        except Exception as exc:  # noqa: BLE001 - bridge defects fail the migration checker
            errors.append(
                f"router_transaction:{decision.get('router_decision_id')}:{type(exc).__name__}:{str(exc)[:300]}"
            )
    integrity = store.integrity_report()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": "passed" if not errors and integrity["status"] == "passed" else "blocked",
        "decision_count": len(state.get("decisions", [])),
        "inserted_decision_count": inserted_decisions,
        "inserted_gate_count": inserted_gates,
        "validation_errors": errors,
        "integrity": integrity,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }


def persist_handoff_consumption(
    consumer: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    store = ControlPlaneStore.from_settings(settings)
    submission_ledger = read_json(runtime / "paperops_alpaca_paper_post_submission_ledger.json")
    submitted_keys = {
        str(value)
        for value in submission_ledger.get("submitted_source_idempotency_keys", [])
        if str(value)
    }
    reconciled = store.reconcile_submitted_idempotency_keys(submitted_keys)
    expired = store.expire_stale_handoffs()
    inserted_handoffs = 0
    inserted_receipts = 0
    errors: list[str] = []
    for accepted in consumer.get("accepted_handoffs", []):
        source = accepted.get("source_handoff")
        source = source if isinstance(source, dict) else {}
        try:
            inserted_handoffs += int(
                store.accept_handoff(
                    handoff_id=str(source.get("paperops_handoff_id")),
                    decision_id=str(source.get("router_decision_id")),
                    candidate_identity=str(source.get("candidate_identity_id")),
                    idempotency_key=str(
                        (source.get("idempotency_material") or {}).get("idempotency_key")
                    ),
                    payload=source,
                    created_at=str(source.get("generated_at") or accepted.get("generated_at") or now_iso()),
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"accepted_handoff:{source.get('paperops_handoff_id')}:{type(exc).__name__}:{str(exc)[:300]}"
            )
    for receipt in consumer.get("receipts", []):
        handoff_id = str(receipt.get("paperops_handoff_id") or "")
        if not handoff_id or receipt.get("accepted") is not True:
            continue
        try:
            inserted_receipts += int(
                store.record_handoff_receipt(
                    receipt_id=str(receipt.get("consumption_receipt_id")),
                    handoff_id=handoff_id,
                    receipt_type=str(receipt.get("status") or "reviewed"),
                    payload=receipt,
                    created_at=str(receipt.get("generated_at") or now_iso()),
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"handoff_receipt:{receipt.get('consumption_receipt_id')}:{type(exc).__name__}:{str(exc)[:300]}"
            )
    try:
        risk_reconciliation = store.ensure_pending_handoff_risk_decisions()
    except Exception as exc:  # noqa: BLE001
        risk_reconciliation = {
            "checked_handoff_count": 0,
            "inserted_risk_decision_count": 0,
        }
        errors.append(
            f"pending_handoff_risk_reconciliation:{type(exc).__name__}:{str(exc)[:300]}"
        )
    projections = store.write_paperops_projections(
        accepted_path=runtime / "qadam_paperops_handoff_v3_accepted.jsonl",
        receipts_path=runtime / "qadam_paperops_handoff_v3_consumption_receipts.jsonl",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "inserted_handoff_count": inserted_handoffs,
        "inserted_receipt_count": inserted_receipts,
        "pending_handoff_risk_reconciliation": risk_reconciliation,
        "reconciled_submitted_handoff_count": reconciled,
        "expired_stale_handoff_count": expired,
        "pending_handoff_ids": projections.get("accepted_handoff_ids", []),
        "projection_counts": projections,
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }


__all__ = ["persist_handoff_consumption", "persist_router_state"]
