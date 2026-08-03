from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.qadam_paper_lifecycle_proof_boundary import _order_lifecycle_state
from orchestrator.qadam_paper_lineage_and_proof import build_trade_lineage_record


NOW = "2026-08-03T14:00:00+00:00"


def test_held_protective_exit_is_healthy_not_cancel_replace_needed() -> None:
    state, action, stale, _age = _order_lifecycle_state(
        {
            "order_id": "stop:test",
            "instrument": "SLV",
            "status": "held",
            "submitted_at": "2026-08-03T13:45:00+00:00",
            "position_intent": "sell_to_close",
            "protective_exit_leg": True,
        },
        None,
        datetime.fromisoformat(NOW).astimezone(timezone.utc),
    )

    assert state == "accepted"
    assert action == "monitor_broker_held_protective_exit_until_sibling_or_position_resolves"
    assert stale is False


def test_position_only_lineage_records_have_distinct_stable_ids() -> None:
    first = build_trade_lineage_record(
        {},
        {},
        {
            "position_id": "position:one",
            "instrument": "SLV",
            "direction": "long",
            "status": "open_position",
            "updated_at": NOW,
        },
        {},
        generated_at=NOW,
        paper_epoch_id="paper-epoch:test",
    )
    second = build_trade_lineage_record(
        {},
        {},
        {
            "position_id": "position:two",
            "instrument": "SMH",
            "direction": "long",
            "status": "open_position",
            "updated_at": NOW,
        },
        {},
        generated_at=NOW,
        paper_epoch_id="paper-epoch:test",
    )

    assert first["broker_record_id"] == "position:one"
    assert first["position_id"] == "position:one"
    assert first["instrument"] == "SLV"
    assert first["current_lifecycle_state"] == "open"
    assert first["lineage_record_id"] != second["lineage_record_id"]
    assert first["proof_eligible"] is False
    assert second["proof_eligible"] is False


def test_operator_exploratory_order_is_external_and_never_proof_eligible() -> None:
    record = build_trade_lineage_record(
        {
            "order_id": "order:operator",
            "instrument": "SLV",
            "direction": "buy",
            "status": "filled",
            "submitted_at": "2026-08-03T13:45:00+00:00",
            "filled_at": "2026-08-03T13:45:01+00:00",
        },
        {},
        {},
        {},
        generated_at=NOW,
        execution_identity={
            "idempotency_namespace": "operator_exploratory_sleeve",
            "source_family": "operator_exploratory_sleeve",
            "evidence_class": "operator_exploratory_unvalidated",
        },
        paper_epoch_id="paper-epoch:test",
    )

    assert record["broker_record_origin_class"] == "external_manual_paper_record"
    assert record["proof_eligible"] is False
    assert record["proof_credit_granted"] is False
