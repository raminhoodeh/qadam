from __future__ import annotations

from copy import deepcopy

from orchestrator.paperops_alpaca_paper_post import (
    _evaluate_paper_order_exposure_guard,
)
from orchestrator.qadam_experimental_paper_policy import (
    VALIDATED_PAPER_STRATEGY,
    VALIDATED_ROUTER_STATE,
)
from orchestrator.qadam_router_v3_paperops import (
    _apply_batch_exposure_reservations,
    _durable_pending_submission_symbols,
    _idempotency_material,
    route_setup,
)


NOW = "2026-08-25T09:00:00+00:00"


def _broker_context() -> dict[str, object]:
    return {
        "clock": {"is_open": True},
        "account": {
            "status": "ACTIVE",
            "trading_blocked": False,
            "account_blocked": False,
        },
        "open_orders": [],
        "positions": [],
        "asset": {
            "status": "active",
            "tradable": True,
            "shortable": True,
            "easy_to_borrow": True,
        },
    }


def _setup(setup_id: str, score: float) -> dict[str, object]:
    return {
        "setup_id": setup_id,
        "evidence_class": VALIDATED_PAPER_STRATEGY,
        "candidate_identity_id": f"candidate:{setup_id}",
        "lineage": {
            "research_goal_id": f"research:{setup_id}",
            "score_id": f"score:{setup_id}",
            "edge_id": f"edge:{setup_id}",
            "hypothesis_id": f"hypothesis:{setup_id}",
            "akber_result_id": f"akber:{setup_id}",
            "shadow_evidence_id": f"shadow:{setup_id}",
            "risk_proposal_id": f"risk:{setup_id}",
        },
        "instrument": "NVDA",
        "execution_symbol": "NVDA",
        "market_family": "equity",
        "direction": "short",
        "horizon": "3d_forward",
        "research_score": score,
        "edge_promotion_class": "validated_research_edge",
        "fresh_catalyst_state": "confirmed",
        "current_trigger_state": "confirmed",
        "akber_decision": "pass",
        "source_quorum": {"passed": True, "independent_source_count": 3},
        "source_quorum_passed": True,
        "expected_net_return_positive_after_costs": True,
        "shadow_promotion_ready": True,
        "risk_proposal_complete": True,
        "proposed_quantity": 1,
        "proposed_notional_usd": 100.0,
        "maximum_loss_at_invalidation": 10.0,
        "risk_policy_version": "policy:test",
        "strategy_family_id": "strategy:test",
        "duplicate_exposure_conflict": False,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "qctrl_state": "pass",
        "instrument_paperable": True,
        "route": "guarded_alpaca_paper_via_paperops",
        "separately_governed_prediction_market_paper_route": False,
        "strategy_version_operator_approved": True,
        "risk_policy_operator_approved": True,
    }


def test_broker_guard_blocks_closed_market_and_duplicate_symbol() -> None:
    context = _broker_context()
    context["clock"] = {"is_open": False}
    result = _evaluate_paper_order_exposure_guard(
        {"symbol": "NVDA", "side": "sell", "qty": "1"}, **context
    )
    assert result["status"] == "blocked"
    assert result["checks"]["regular_session_open"] is False

    context = _broker_context()
    context["open_orders"] = [{"symbol": "NVDA", "status": "new"}]
    result = _evaluate_paper_order_exposure_guard(
        {"symbol": "NVDA", "side": "sell", "qty": "1"}, **context
    )
    assert result["status"] == "blocked"
    assert result["checks"]["no_pending_order_for_symbol"] is False


def test_broker_guard_allows_bounded_close_but_not_scale_in() -> None:
    context = _broker_context()
    context["positions"] = [{"symbol": "BNO", "qty": "2"}]
    close = _evaluate_paper_order_exposure_guard(
        {"symbol": "BNO", "side": "sell", "qty": "2"}, **context
    )
    assert close["status"] == "passed"
    assert close["position_intent"] == "close_long"

    scale_in = _evaluate_paper_order_exposure_guard(
        {"symbol": "BNO", "side": "buy", "qty": "1"}, **context
    )
    assert scale_in["status"] == "blocked"
    assert scale_in["checks"]["opening_exposure_not_already_held"] is False


def test_router_keeps_only_highest_scored_same_symbol_candidate() -> None:
    release = {"release_effective": True, "validated_paper_release_effective": True}
    setups = [_setup("low", 0.60), _setup("high", 0.75), _setup("middle", 0.68)]
    release_by_setup = {str(setup["setup_id"]): True for setup in setups}
    keys = {
        _idempotency_material(setup, release_effective=True)["idempotency_key"]
        for setup in setups
    }
    assert len(keys) == 3
    decisions = [
        route_setup(setup, release, generated_at=NOW) for setup in deepcopy(setups)
    ]
    assert all(decision["final_state"] == VALIDATED_ROUTER_STATE for decision in decisions)
    routed, conflict_count = _apply_batch_exposure_reservations(
        setups,
        decisions,
        release,
        generated_at=NOW,
        duplicate_keys=set(),
        release_effective_by_setup=release_by_setup,
    )
    accepted = [
        decision for decision in routed if decision["final_state"] == VALIDATED_ROUTER_STATE
    ]
    assert conflict_count == 2
    assert len(accepted) == 1
    assert accepted[0]["setup_id"] == "high"


def test_recent_submission_blocks_even_before_mirror_refresh() -> None:
    ledger = {
        "submission_records": [
            {
                "client_order_id": "q7-order",
                "submitted_at": "2026-08-25T08:59:00+00:00",
                "request_preview": {"symbol": "NVDA"},
            }
        ]
    }
    assert _durable_pending_submission_symbols([], ledger, generated_at=NOW) == {"NVDA"}
    orders = [{"client_order_id": "q7-order", "status": "filled"}]
    assert _durable_pending_submission_symbols(orders, ledger, generated_at=NOW) == set()
