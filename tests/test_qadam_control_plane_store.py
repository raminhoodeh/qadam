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


def test_same_decision_generation_replay_ignores_runtime_timestamps(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    assert store.create_decision(transaction) is True

    replay = transaction.model_copy(
        update={
            "created_at": "2026-08-19T15:00:00+00:00",
            "updated_at": "2026-08-19T15:00:00+00:00",
        }
    )
    assert store.create_decision(replay) is False
    assert len(store.read_table("decision_transactions")) == 1


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
    assert restarted.pending_outbox("paperops_handoff_accepted") == pending
    assert restarted.integrity_report()["status"] == "passed"


def test_current_paperops_handoff_persists_risk_envelope_atomically(
    tmp_path: Path,
) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction().model_copy(
        update={"stage": "router_terminal", "evidence_class": "experimental_unvalidated"}
    )
    store.create_decision(transaction)
    payload = {
        "schema_version": "qadam_router_v3_paperops.v1",
        "paperops_handoff_id": "handoff-1",
        "router_decision_id": transaction.decision_id,
        "hypothesis_id": "hypothesis-1",
        "lineage": {
            "hypothesis_id": "hypothesis-1",
            "risk_proposal_id": "risk-1",
        },
        "evidence_class": "experimental_unvalidated",
        "proposed_notional_usd": 500.0,
        "maximum_loss_at_invalidation": 10.0,
        "duplicate_exposure_conflict": False,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "source_quorum_passed": True,
        "instrument_paperable": True,
        "qctrl_state": "pass",
        "route": "guarded_alpaca_paper_via_paperops",
        "live_capital_enabled": False,
    }

    assert store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=transaction.decision_id,
        candidate_identity=transaction.candidate_identity,
        idempotency_key=transaction.idempotency_key,
        payload=payload,
    )

    risk = store.read_table("risk_decisions")
    assert len(risk) == 1
    assert risk[0]["risk_decision_id"] == "risk-1"
    assert risk[0]["approved_notional"] == 500.0
    assert risk[0]["trading_lane"] == "discovery"
    assert len(store.pending_handoffs()) == 1

    with store.transaction() as connection:
        connection.execute("DELETE FROM risk_decisions WHERE risk_decision_id='risk-1'")
    repaired = store.ensure_pending_handoff_risk_decisions()
    assert repaired == {
        "checked_handoff_count": 1,
        "inserted_risk_decision_count": 1,
    }
    assert len(store.read_table("risk_decisions")) == 1


def test_current_paperops_handoff_without_hard_risk_evidence_rolls_back(
    tmp_path: Path,
) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction().model_copy(update={"stage": "router_terminal"})
    store.create_decision(transaction)
    payload = {
        "schema_version": "qadam_router_v3_paperops.v1",
        "lineage": {"risk_proposal_id": "risk-1"},
        "evidence_class": "experimental_unvalidated",
        "proposed_notional_usd": 500.0,
        "maximum_loss_at_invalidation": 0.0,
        "duplicate_exposure_conflict": False,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "source_quorum_passed": True,
        "instrument_paperable": True,
        "qctrl_state": "pass",
        "route": "guarded_alpaca_paper_via_paperops",
        "live_capital_enabled": False,
    }

    with pytest.raises(ControlPlaneError, match="maximum_loss_at_invalidation_missing"):
        store.accept_handoff(
            handoff_id="handoff-1",
            decision_id=transaction.decision_id,
            candidate_identity=transaction.candidate_identity,
            idempotency_key=transaction.idempotency_key,
            payload=payload,
        )

    assert store.read_table("handoffs") == []
    assert store.read_table("risk_decisions") == []


def test_replaying_current_decision_keeps_its_pending_handoff(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        payload={"route": "guarded_alpaca_paper_only"},
    )

    assert store.create_decision(transaction) is False
    assert store.get_handoff("handoff-1")["state"] == "accepted_for_paperops_review"
    assert len(store.pending_handoffs()) == 1


def test_newer_decision_supersedes_prior_pending_handoff_atomically(
    tmp_path: Path,
) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    first = _transaction()
    store.create_decision(first)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=first.decision_id,
        candidate_identity=first.candidate_identity,
        idempotency_key=first.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "one"},
    )
    second = first.model_copy(
        update={
            "decision_id": "decision-2",
            "generation_id": "generation-2",
            "idempotency_key": "idempotency-2",
            "stage": "router_terminal",
        }
    )

    assert store.create_decision(second) is True

    assert store.get_handoff("handoff-1")["state"] == "superseded"
    assert store.pending_handoffs() == []
    receipts = store.read_table("handoff_receipts")
    assert [row["receipt_type"] for row in receipts] == ["superseded"]
    assert receipts[0]["payload"]["superseded_by_decision_id"] == "decision-2"
    assert store.integrity_report()["status"] == "passed"


def test_new_handoff_generation_replaces_old_pending_generation_once(
    tmp_path: Path,
) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    first = _transaction()
    store.create_decision(first)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=first.decision_id,
        candidate_identity=first.candidate_identity,
        idempotency_key=first.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "one"},
    )
    second = first.model_copy(
        update={
            "decision_id": "decision-2",
            "generation_id": "generation-2",
            "idempotency_key": "idempotency-2",
        }
    )
    store.create_decision(second)
    assert store.accept_handoff(
        handoff_id="handoff-2",
        decision_id=second.decision_id,
        candidate_identity=second.candidate_identity,
        idempotency_key=second.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "two"},
    )
    assert store.accept_handoff(
        handoff_id="handoff-2",
        decision_id=second.decision_id,
        candidate_identity=second.candidate_identity,
        idempotency_key=second.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "two"},
    ) is False

    pending = store.pending_handoffs()
    assert [row["handoff_id"] for row in pending] == ["handoff-2"]
    assert store.integrity_report()["status"] == "passed"


def test_stale_decision_replay_cannot_supersede_latest_handoff(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    first = _transaction()
    store.create_decision(first)
    second = first.model_copy(
        update={
            "decision_id": "decision-2",
            "generation_id": "generation-2",
            "idempotency_key": "idempotency-2",
        }
    )
    store.create_decision(second)
    store.accept_handoff(
        handoff_id="handoff-2",
        decision_id=second.decision_id,
        candidate_identity=second.candidate_identity,
        idempotency_key=second.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "two"},
    )

    assert store.create_decision(first) is False
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=first.decision_id,
        candidate_identity=first.candidate_identity,
        idempotency_key=first.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "one"},
    )

    assert store.get_handoff("handoff-1")["state"] == "superseded"
    assert store.get_handoff("handoff-2")["state"] == "accepted_for_paperops_review"
    assert [row["handoff_id"] for row in store.pending_handoffs()] == ["handoff-2"]


def test_handoff_replay_recovers_an_interrupted_outbox_projection(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    payload = {"route": "guarded_alpaca_paper_only"}
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=transaction.decision_id,
        candidate_identity=transaction.candidate_identity,
        idempotency_key=transaction.idempotency_key,
        payload=payload,
    )
    outbox = store.pending_outbox("paperops_handoff_accepted")[0]
    store.mark_outbox_published(outbox["event_id"])

    assert store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=transaction.decision_id,
        candidate_identity=transaction.candidate_identity,
        idempotency_key=transaction.idempotency_key,
        payload=payload,
    ) is False

    recovered = store.pending_outbox("paperops_handoff_accepted")
    assert [row["event_id"] for row in recovered] == [outbox["event_id"]]
    assert recovered[0]["last_error"] == "recovered_active_handoff_projection"
    assert store.integrity_report()["status"] == "passed"


def test_failed_old_worker_releases_current_generation_for_retry(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    first = _transaction()
    store.create_decision(first)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id=first.decision_id,
        candidate_identity=first.candidate_identity,
        idempotency_key=first.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "one"},
    )
    claim = store.claim_outbox(
        topic="paperops_handoff_accepted",
        worker_id="worker-old",
    )
    assert claim is not None
    second = first.model_copy(
        update={
            "decision_id": "decision-2",
            "generation_id": "generation-2",
            "idempotency_key": "idempotency-2",
        }
    )
    store.create_decision(second)
    assert store.accept_handoff(
        handoff_id="handoff-2",
        decision_id=second.decision_id,
        candidate_identity=second.candidate_identity,
        idempotency_key=second.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "two"},
    ) is False
    assert store.get_handoff("handoff-2") is None

    assert store.release_outbox_claim(claim["event_id"], error="network_failure")
    assert store.accept_handoff(
        handoff_id="handoff-2",
        decision_id=second.decision_id,
        candidate_identity=second.candidate_identity,
        idempotency_key=second.idempotency_key,
        payload={"route": "guarded_alpaca_paper_only", "generation": "two"},
    )

    assert store.get_handoff("handoff-1")["state"] == "superseded"
    assert store.get_handoff("handoff-2")["state"] == "accepted_for_paperops_review"
    assert [row["handoff_id"] for row in store.pending_handoffs()] == ["handoff-2"]
    assert store.integrity_report()["status"] == "passed"


def test_outbox_lease_prevents_concurrent_claim_and_can_retry(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        payload={"route": "guarded_alpaca_paper_only"},
    )

    first = store.claim_outbox(
        topic="paperops_handoff_accepted",
        worker_id="worker-1",
    )
    assert first is not None
    assert first["status"] == "processing"
    assert store.claim_outbox(
        topic="paperops_handoff_accepted",
        worker_id="worker-2",
    ) is None

    assert store.release_outbox_claim(first["event_id"], error="network_interrupted")
    retry = store.claim_outbox(
        topic="paperops_handoff_accepted",
        worker_id="worker-2",
    )
    assert retry is not None
    assert retry["event_id"] == first["event_id"]
    store.mark_outbox_published(retry["event_id"])
    assert store.pending_outbox("paperops_handoff_accepted") == []


def test_broker_submission_closes_handoff_and_outbox_atomically(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        payload={"route": "guarded_alpaca_paper_only"},
    )
    claim = store.claim_outbox(
        topic="paperops_handoff_accepted",
        worker_id="worker-1",
        aggregate_id="handoff-1",
    )
    assert claim is not None
    receipt = {
        "paperops_handoff_id": "handoff-1",
        "status": "submitted_to_alpaca_paper",
        "broker_order_id_hash": "broker-hash-1",
    }

    first = store.record_broker_submission(
        receipt_id="submission-receipt-1",
        handoff_id="handoff-1",
        receipt_payload=receipt,
        broker_event_id="broker-event-1",
        broker_order_id="broker-hash-1",
        broker_event_payload=receipt,
    )
    replay = store.record_broker_submission(
        receipt_id="submission-receipt-1",
        handoff_id="handoff-1",
        receipt_payload=receipt,
        broker_event_id="broker-event-1",
        broker_order_id="broker-hash-1",
        broker_event_payload=receipt,
    )

    assert first == {"receipt_inserted": True, "broker_event_inserted": True}
    assert replay == {"receipt_inserted": False, "broker_event_inserted": False}
    assert store.get_handoff("handoff-1")["state"] == "consumed"
    assert store.pending_outbox("paperops_handoff_accepted") == []
    assert len(store.read_table("handoff_receipts")) == 1
    assert len(store.read_table("broker_events")) == 1
    integrity = store.integrity_report()
    assert integrity["status"] == "passed"
    assert integrity["blocker_count"] == 0


def test_integrity_blocks_an_accepted_handoff_without_active_outbox(tmp_path: Path) -> None:
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    transaction = _transaction()
    store.create_decision(transaction)
    store.accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        payload={"route": "guarded_alpaca_paper_only"},
    )
    outbox = store.pending_outbox("paperops_handoff_accepted")[0]
    store.mark_outbox_published(outbox["event_id"])

    integrity = store.integrity_report()

    assert integrity["status"] == "blocked"
    assert "accepted_handoff_without_active_outbox" in integrity["blockers"]


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
