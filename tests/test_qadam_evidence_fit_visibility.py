from __future__ import annotations

from orchestrator.qadam_evidence_fit_visibility import (
    build_conversion_funnel,
    build_evidence_fit_visibility_state,
    validate_evidence_fit_visibility,
)


NOW = "2026-08-08T12:00:00+00:00"


def test_current_evidence_fit_projection_is_public_safe_and_complete() -> None:
    state = build_evidence_fit_visibility_state(generated_at=NOW)
    dashboard = state["dashboard"]
    assert dashboard["registered_source_count"] == 41
    assert dashboard["watched_instrument_count"] == 19
    assert set(dashboard["areas"]) == {
        "sources",
        "universe",
        "patterns",
        "strategies",
        "decision",
        "orders",
        "learning",
    }
    assert len(state["funnel"]["stages"]) == 9
    assert dashboard["authority"]["paper_order_allowed"] is False
    assert state["latest_notification"]["live_send_allowed"] is False
    assert validate_evidence_fit_visibility(state) == []


def test_inactive_trigger_cannot_create_a_paper_handoff() -> None:
    funnel = build_conversion_funnel(
        source_contract={
            "source_count": 41,
            "availability_counts": {"live_fresh": 10},
        },
        instrument_registry={"instrument_count": 19},
        trigger_summary={
            "active_event_trigger_count": 0,
            "active_regime_count": 0,
            "active_market_dislocation_count": 0,
        },
        directions=[{"actionable_direction": "abstain"}],
        hypotheses=[],
        akber_results=[],
        router_decisions=[],
        router_root={"primary_root_cause": "no_real_trigger"},
        trial_funnel=[{"paper_handoffs": 0, "risk_proposals": 0}],
        paper_lineage=[],
        generated_at=NOW,
    )
    assert funnel["stages"][2] == {
        "stage": "triggers",
        "label": "Active triggers",
        "count": 0,
    }
    assert funnel["current_handoff_count"] == 0
    assert funnel["paper_order_created"] is False
    assert funnel["broker_write_count"] == 0


def test_duplicate_notification_has_no_body_or_send_authority() -> None:
    state = build_evidence_fit_visibility_state(generated_at=NOW)
    notification = state["latest_notification"]
    notification["status"] = "duplicate_suppressed"
    notification["body"] = None
    assert notification["live_send_attempted"] is False
    assert notification["live_send_allowed"] is False
    assert validate_evidence_fit_visibility(state) == []
