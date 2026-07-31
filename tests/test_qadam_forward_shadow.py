from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.qadam_forward_shadow import (
    OUTCOME_GRACE_SECONDS,
    build_forward_shadow_state_from_inputs,
    complete_shadow_outcome,
    complete_shadow_outcome_from_observation,
    extract_runtime_price_observations,
    freeze_shadow_decision,
    validate_forward_shadow_state,
)


def _timestamp(day: int, hour: int = 0) -> str:
    return datetime(2026, 1, day, hour, tzinfo=timezone.utc).isoformat()


def _hypothesis(index: int = 1, *, edge_id: str = "edge:test") -> dict:
    return {
        "hypothesis_id": f"hypothesis:{index}",
        "hypothesis_state": "shadow_only",
        "edge_lineage": {"edge_id": edge_id},
        "research_goal_lineage": {"research_goal_id": f"goal:{index}"},
        "candidate_identity_material": {"candidate_identity_id": f"candidate:{index}"},
        "instrument_proxy_mapping": {
            "observed_instrument": "SPY",
            "execution_proxy": "SPY",
        },
        "direction_horizon": {"direction": "long", "horizon": "1d_forward"},
        "expected_edge_range": {
            "net_expectancy": 0.01,
            "confidence_distribution": {"lower": -0.005, "upper": 0.025},
        },
    }


def _akber_result(
    hypothesis_id: str,
    decision: str,
    *,
    router_eligible: bool = False,
) -> dict:
    return {
        "hypothesis_id": hypothesis_id,
        "akber_result_id": f"akber:{decision}:{hypothesis_id}",
        "akber_input_id": f"akber-input:{hypothesis_id}",
        "decision": decision,
        "router_eligible": router_eligible,
    }


def _observation(observed_at: str, price: float, *, sample: bool = False) -> dict:
    return {
        "observation_id": f"price:{observed_at}:{price}",
        "instrument": "SPY",
        "price": price,
        "observed_at": observed_at,
        "available_at": observed_at,
        "provider": "alpaca_market_data_v2",
        "provider_backed": True,
        "origin_class": "live_read_only_provider_call",
        "sample": sample,
        "fixture": False,
        "read_only_market_data": True,
        "broker_endpoint_used": False,
    }


def _supervisor_heartbeat(at: str) -> dict:
    return {
        "generated_at": at,
        "status": "idle_ready",
        "current_phase": "OR-13",
        "service_id": "continuous_forward_shadow",
    }


def _shadow_heartbeat(at: str) -> dict:
    return {"generated_at": at, "status": "running", "supervised_by": "OR-1"}


def test_frozen_provider_decision_cannot_be_scored_before_real_horizon() -> None:
    decision_at = _timestamp(1)
    decision = freeze_shadow_decision(
        _hypothesis(),
        None,
        decision_at=decision_at,
        entry_observation=_observation(decision_at, 100.0),
        require_entry_observation=True,
    )

    with pytest.raises(ValueError, match="before_horizon"):
        complete_shadow_outcome(
            decision,
            outcome_available_at=_timestamp(1, 12),
            gross_return=0.01,
            cost_bps=5.0,
        )

    outcome = complete_shadow_outcome_from_observation(decision, _observation(_timestamp(2), 101.0))
    assert outcome["real_elapsed_seconds"] == 86_400.0
    assert outcome["net_return"] == 0.0095
    assert outcome["forecast_range_hit"] is True
    assert outcome["paper_order_created"] is False
    assert outcome["proof_eligible"] is False


def test_sample_or_fixture_price_cannot_start_production_shadow() -> None:
    with pytest.raises(ValueError, match="provider_backed_entry_observation_required"):
        freeze_shadow_decision(
            _hypothesis(),
            None,
            decision_at=_timestamp(1),
            entry_observation=_observation(_timestamp(1), 100.0, sample=True),
            require_entry_observation=True,
        )


def test_supervised_cycles_freeze_then_complete_without_mutating_decision() -> None:
    first_at = _timestamp(1)
    first = build_forward_shadow_state_from_inputs(
        [_hypothesis()],
        [],
        [],
        [],
        [],
        [],
        [_observation(first_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(first_at),
        {},
        generated_at=first_at,
        supervised_cycle=True,
    )
    assert len(first["decisions"]) == 1
    assert first["outcomes"] == []
    frozen_hash = first["decisions"][0]["frozen_decision_hash"]

    second_at = _timestamp(2)
    second = build_forward_shadow_state_from_inputs(
        [_hypothesis()],
        [],
        [],
        first["decisions"],
        [],
        [],
        [
            _observation(first_at, 100.0),
            _observation(second_at, 101.0),
        ],
        {"supervisor_installed": True},
        _supervisor_heartbeat(second_at),
        _shadow_heartbeat(second_at),
        generated_at=second_at,
    )
    assert len(second["decisions"]) == 1
    assert len(second["outcomes"]) == 1
    assert second["decisions"][0]["lifecycle_state"] == "completed"
    assert second["decisions"][0]["frozen_decision_hash"] == frozen_hash
    assert validate_forward_shadow_state(second) == []


@pytest.mark.parametrize(
    ("decision", "basis"),
    [
        ("hold_missing_context", "akber_hold_counterfactual_observation"),
        ("veto", "akber_veto_counterfactual_observation"),
    ],
)
def test_akber_hold_and_veto_are_observed_without_promotion_authority(
    decision: str,
    basis: str,
) -> None:
    generated_at = _timestamp(1)
    hypothesis = _hypothesis()
    hypothesis["hypothesis_state"] = "ready_for_akber_review"
    result = _akber_result(hypothesis["hypothesis_id"], decision)
    bundle = build_forward_shadow_state_from_inputs(
        [hypothesis],
        [],
        [result],
        [],
        [],
        [],
        [_observation(generated_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )

    assert bundle["state"]["eligible_hypothesis_count"] == 1
    assert bundle["state"]["trade_progression_eligible_hypothesis_count"] == 0
    assert bundle["state"]["counterfactual_observation_hypothesis_count"] == 1
    shadow = bundle["decisions"][0]
    assert shadow["eligibility_basis"] == basis
    assert shadow["counterfactual_observation_only"] is True
    assert shadow["promotion_evidence_allowed"] is False
    assert shadow["paper_order_created"] is False
    assert validate_forward_shadow_state(bundle) == []


def test_akber_pass_shadow_remains_the_only_router_progression_evidence() -> None:
    generated_at = _timestamp(1)
    hypothesis = _hypothesis()
    hypothesis["hypothesis_state"] = "ready_for_akber_review"
    result = _akber_result(
        hypothesis["hypothesis_id"],
        "pass",
        router_eligible=True,
    )
    bundle = build_forward_shadow_state_from_inputs(
        [hypothesis],
        [],
        [result],
        [],
        [],
        [],
        [_observation(generated_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )

    assert bundle["state"]["trade_progression_eligible_hypothesis_count"] == 1
    assert bundle["state"]["counterfactual_observation_hypothesis_count"] == 0
    assert bundle["decisions"][0]["promotion_evidence_allowed"] is True


def test_refreshed_hypothesis_identity_does_not_duplicate_same_economic_signal() -> None:
    generated_at = _timestamp(1)
    first_hypothesis = _hypothesis(1)
    first = build_forward_shadow_state_from_inputs(
        [first_hypothesis],
        [],
        [],
        [],
        [],
        [],
        [_observation(generated_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )
    refreshed_hypothesis = _hypothesis(2)
    refreshed = build_forward_shadow_state_from_inputs(
        [refreshed_hypothesis],
        [],
        [],
        first["decisions"],
        [],
        [],
        [_observation(generated_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )

    assert len(refreshed["decisions"]) == 1
    assert refreshed["decisions"][0]["hypothesis_id"] == first_hypothesis["hypothesis_id"]
    assert refreshed["state"]["reconciled_semantic_duplicate_decision_count"] == 0


def test_existing_semantic_duplicates_are_retained_but_only_first_can_mature() -> None:
    generated_at = _timestamp(1)
    first = freeze_shadow_decision(
        _hypothesis(1),
        None,
        decision_at=generated_at,
        entry_observation=_observation(generated_at, 100.0),
        require_entry_observation=True,
    )
    duplicate = deepcopy(first)
    duplicate["decision_id"] = "forward-shadow-decision:legacy-duplicate"
    duplicate["hypothesis_id"] = "hypothesis:refreshed"
    duplicate["candidate_identity_id"] = "candidate:refreshed"
    bundle = build_forward_shadow_state_from_inputs(
        [_hypothesis(3)],
        [],
        [],
        [first, duplicate],
        [],
        [],
        [_observation(generated_at, 100.0)],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )

    assert len(bundle["decisions"]) == 2
    assert bundle["state"]["reconciled_semantic_duplicate_decision_count"] == 1
    superseded = [
        row
        for row in bundle["decisions"]
        if row["lifecycle_state"] == "superseded_logical_duplicate"
    ]
    assert len(superseded) == 1
    assert superseded[0]["promotion_evidence_allowed"] is False
    assert superseded[0]["logical_duplicate_of_decision_id"] == first["decision_id"]
    assert validate_forward_shadow_state(bundle) == []


def test_unavailable_outcome_expires_with_typed_reason_after_real_grace() -> None:
    decision_at = _timestamp(1)
    decision = freeze_shadow_decision(
        _hypothesis(),
        None,
        decision_at=decision_at,
        entry_observation=_observation(decision_at, 100.0),
        require_entry_observation=True,
    )
    expiry = (
        datetime.fromisoformat(_timestamp(2)) + timedelta(seconds=OUTCOME_GRACE_SECONDS + 1)
    ).isoformat()
    bundle = build_forward_shadow_state_from_inputs(
        [_hypothesis()],
        [],
        [],
        [decision],
        [],
        [],
        [],
        {"supervisor_installed": True},
        _supervisor_heartbeat(expiry),
        _shadow_heartbeat(expiry),
        generated_at=expiry,
    )
    expired = bundle["decisions"][0]
    assert expired["lifecycle_state"] == "expired_unscored"
    assert expired["typed_expiry_reason"]
    assert validate_forward_shadow_state(bundle) == []


def test_promotion_requires_independent_real_signals_elapsed_time_and_power() -> None:
    decisions: list[dict] = []
    outcomes: list[dict] = []
    for index in range(20):
        decision_at = (
            datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
        ).isoformat()
        outcome_at = (datetime(2026, 1, 2, tzinfo=timezone.utc) + timedelta(days=index)).isoformat()
        hypothesis = _hypothesis(index, edge_id=f"edge:{index % 2}")
        hypothesis["signal_observation_date"] = decision_at
        decision = freeze_shadow_decision(
            hypothesis,
            None,
            decision_at=decision_at,
            entry_observation=_observation(decision_at, 100.0),
            require_entry_observation=True,
        )
        decisions.append(decision)
        outcomes.append(
            complete_shadow_outcome(
                decision,
                outcome_available_at=outcome_at,
                gross_return=0.01 + (index * 0.00002),
                cost_bps=5.0,
            )
        )
    generated_at = _timestamp(21)
    bundle = build_forward_shadow_state_from_inputs(
        [_hypothesis(index, edge_id=f"edge:{index % 2}") for index in range(20)],
        [],
        [],
        decisions,
        outcomes,
        [],
        [],
        {"supervisor_installed": True},
        _supervisor_heartbeat(generated_at),
        _shadow_heartbeat(generated_at),
        generated_at=generated_at,
    )
    assert bundle["promotion"]["promotion_ready"] is True
    assert bundle["promotion"]["completed_signal_count"] == 20
    assert bundle["promotion"]["independent_edge_count"] == 2
    assert bundle["promotion"]["real_elapsed_days"] >= 10
    assert bundle["promotion"]["estimated_power"] >= 0.8
    assert validate_forward_shadow_state(bundle) == []


def test_zero_eligible_hypotheses_is_truthful_idle_not_forward_evidence() -> None:
    generated_at = _timestamp(1)
    bundle = build_forward_shadow_state_from_inputs(
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        {"supervisor_installed": False},
        _supervisor_heartbeat(generated_at),
        _shadow_heartbeat(generated_at),
        generated_at=generated_at,
    )
    assert bundle["state"]["valid_no_eligible_hypothesis_outcome"] is True
    assert bundle["state"]["shadow_service_cycle_fresh"] is True
    assert bundle["state"]["shadow_service_running"] is False
    assert bundle["promotion"]["promotion_ready"] is False
    assert bundle["promotion"]["historical_replay_can_satisfy_forward_requirement"] is False


def test_operator_service_is_recognized_as_continuous_shadow_scheduler() -> None:
    generated_at = _timestamp(1)
    bundle = build_forward_shadow_state_from_inputs(
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        {"operator_scheduler_active": False},
        {},
        {},
        generated_at=generated_at,
        supervised_cycle=True,
    )
    assert bundle["state"]["scheduler_owner"] == "qadam_operator_service"
    assert bundle["state"]["continuous_scheduler_installed"] is True
    assert bundle["state"]["shadow_service_running"] is True
    assert bundle["heartbeat"]["supervised_by"] == "qadam_operator_service"


def test_runtime_market_context_rejects_supplemental_sample_prices() -> None:
    generated_at = _timestamp(1)
    context = {
        "recent_packets": [
            {
                "generated_at": generated_at,
                "price_volume_context": {
                    "provider": "yahoo_finance",
                    "canonical_source": False,
                    "records": [
                        {
                            "symbol": "SPY",
                            "last_close": 100.0,
                            "market_state": "sample_closed",
                        }
                    ],
                },
            }
        ]
    }
    accepted, rejected = extract_runtime_price_observations(context, generated_at=generated_at)
    assert accepted == []
    assert len(rejected) == 1
    assert "not_provider_backed" in rejected[0]["reasons"]


def test_validator_rejects_shadow_proof_credit() -> None:
    generated_at = _timestamp(1)
    bundle = build_forward_shadow_state_from_inputs(
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        {"supervisor_installed": False},
        _supervisor_heartbeat(generated_at),
        _shadow_heartbeat(generated_at),
        generated_at=generated_at,
    )
    unsafe = deepcopy(bundle)
    unsafe["state"]["proof_credit_count"] = 1
    assert "shadow_forbidden_count_nonzero:proof_credit_count" in validate_forward_shadow_state(
        unsafe
    )
