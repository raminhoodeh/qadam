from __future__ import annotations

from orchestrator.qadam_risk_router_alignment import (
    _router_setup,
    build_risk_router_alignment_state,
    validate_risk_router_alignment,
)
from orchestrator.qadam_router_v3_paperops import route_setup


def test_risk_router_alignment_contract_passes_without_changing_envelope() -> None:
    state = build_risk_router_alignment_state(
        generated_at="2026-08-08T12:00:00+00:00"
    )
    assert validate_risk_router_alignment(state) == []
    proposal = state["contract_probes"]["single_source_with_confirmation"][
        "proposal"
    ]
    assert proposal["evidence_channel_concentration_haircut"] == 0.5
    assert proposal["paper_order_created"] is False


def test_missing_spread_and_duplicate_exposure_have_one_correct_semantic() -> None:
    state = build_risk_router_alignment_state(
        generated_at="2026-08-08T12:00:00+00:00"
    )
    reasons = state["contract_probes"]["missing_spread"]["rejection"][
        "rejection_reasons"
    ]
    assert "execution_context_missing" in reasons
    assert "spread_exceeds_frozen_maximum" not in reasons
    duplicate = state["contract_probes"]["duplicate_exposure"]
    assert duplicate["final_state"] == "reject"
    assert duplicate["primary_root_cause"] == "duplicate_exposure_conflict"


def test_akber_hold_precedes_downstream_policy_consequences() -> None:
    setup = _router_setup()
    setup.update(
        {
            "akber_decision": "hold_missing_context",
            "risk_proposal_complete": False,
            "strategy_version_operator_approved": False,
            "risk_policy_operator_approved": False,
        }
    )
    decision = route_setup(
        setup,
        {"experimental_paper_release_effective": True},
        generated_at="2026-08-08T12:00:00+00:00",
    )

    assert decision["final_state"] == "hold"
    assert decision["primary_root_cause"] == "akber_hold"
    assert "risk_policy_not_approved" in decision["hold_reasons"]
