from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.qadam_control_plane_store import ControlPlaneError, ControlPlaneStore
from orchestrator.qadam_decision_transaction import (
    DecisionTransaction,
    Direction,
    PaperOpsHandoffRecord,
)


def _transaction() -> DecisionTransaction:
    timestamp = datetime.now(timezone.utc).isoformat()
    return DecisionTransaction(
        decision_id="decision-1",
        generation_id="generation-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        research_goal_id="goal-1",
        evidence_class="discovery_micro",
        strategy_id="strategy-1",
        strategy_version="v1",
        instrument="XAR",
        direction=Direction.LONG,
        stage="trigger_compiled",
        created_at=timestamp,
        updated_at=timestamp,
        trigger={"trigger_id": "trigger-1"},
    )


def test_empty_projection_cannot_erase_handoff_or_receipt(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    assert store.create_decision(transaction) is True
    assert store.create_decision(transaction) is False
    handoff = PaperOpsHandoffRecord(
        handoff_id="handoff-1",
        decision_id=transaction.decision_id,
        candidate_identity=transaction.candidate_identity,
        idempotency_key=transaction.idempotency_key,
        route="guarded_alpaca_paper_only",
        state="accepted_for_paperops_review",
        created_at=transaction.created_at,
        payload={"instrument": "XAR"},
    )
    assert store.accept_handoff(
        handoff_id=handoff.handoff_id,
        decision_id=handoff.decision_id,
        candidate_identity=handoff.candidate_identity,
        idempotency_key=handoff.idempotency_key,
        payload=handoff.model_dump(mode="json"),
        created_at=handoff.created_at,
    )
    assert store.record_handoff_receipt(
        receipt_id="receipt-1",
        handoff_id="handoff-1",
        receipt_type="consumed",
        payload={"handoff_id": "handoff-1", "state": "consumed"},
    )

    projection = tmp_path / "accepted.jsonl"
    projection.write_text("", encoding="utf-8")
    assert len(store.read_table("handoffs")) == 1
    assert len(store.read_table("handoff_receipts")) == 1
    assert store.rebuild_jsonl_projection(table="handoffs", destination=projection) == 1
    assert projection.read_text(encoding="utf-8").strip()


def test_idempotency_collision_fails_closed(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    with pytest.raises(ControlPlaneError, match="immutable_identity_collision"):
        store.create_decision(
            transaction.model_copy(update={"strategy_version": "v2"})
        )


def test_restart_preserves_pending_outbox_once(tmp_path: Path) -> None:
    path = tmp_path / "control.sqlite3"
    store = ControlPlaneStore(path)
    transaction = _transaction()
    store.create_decision(transaction)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        payload={"route": "guarded_alpaca_paper_only"},
    )
    restarted = ControlPlaneStore(path)
    pending = restarted.pending_outbox("paperops_handoff_accepted")
    assert len(pending) == 1
    restarted.mark_outbox_published(pending[0]["event_id"])
    restarted.mark_outbox_published(pending[0]["event_id"])
    assert restarted.pending_outbox("paperops_handoff_accepted") == []
    assert restarted.integrity_report()["status"] == "passed"


def test_repair_request_can_resolve_without_deleting_evidence(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    assert store.record_repair_request(
        request_id="repair-1",
        domain="execution",
        fingerprint="fingerprint-1",
        status="open",
        payload={"error": "mapping_defect"},
    )
    assert store.set_repair_request_status(
        fingerprint="fingerprint-1",
        status="resolved",
    )
    rows = store.read_table("repair_requests")
    assert len(rows) == 1
    assert rows[0]["status"] == "resolved"
    assert rows[0]["payload"]["error"] == "mapping_defect"
