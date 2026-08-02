from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
from types import SimpleNamespace

from orchestrator import paperops_lifecycle_mirror_freshness as freshness_module
from orchestrator.paperops_lifecycle_mirror_freshness import (
    build_paperops_lifecycle_mirror_freshness,
)
from orchestrator.qadam_dynamic_plan import PHASE_ORDER, program_status
from orchestrator.qadam_paper_lineage_and_proof import (
    _filter_current_execution_epoch,
    build_trade_lineage_record,
    stale_accepted_order_policy,
)
from orchestrator.paperops_alpaca_paper_post import _submission_identity_record
from orchestrator.paperops_paper_exit_path import _source_record_to_exit_candidate
from orchestrator.paperops_paper_lifecycle_poller import _source_record_to_poll_candidate
from orchestrator.paperops_qualified_setup_production import _v3_candidate_record
from orchestrator.paperops_autonomous_pass import COMMAND_SEQUENCE, run_command_sequence
from orchestrator.qadam_router_v3_paperops import (
    REQUIRED_PHASES_FOR_RELEASE,
    build_handoff,
    build_handoff_consumption_state,
    build_release_readiness,
    route_setup,
    validate_handoff_consumption_state,
)
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_ROUTER_STATE,
    EXPERIMENTAL_UNVALIDATED,
    VALIDATED_PAPER_STRATEGY,
    VALIDATED_ROUTER_STATE,
)

NOW = "2026-01-01T00:00:00+00:00"


def _phase_status(default: str = "passed") -> dict:
    return {"phases": {phase: {"state": default} for phase in REQUIRED_PHASES_FOR_RELEASE}}


def _release_inputs() -> dict:
    return {
        "phase_status": _phase_status(),
        "lock": {
            "status": "active",
            "paperops_watch_only_mode": True,
        },
        "approvals": {
            "strategy_version_approved": True,
            "risk_policy_version_approved": True,
            "risk_policy_version": "policy:test",
            "research_lock_release_approved": False,
        },
        "risk_policy": {"policy_version": "policy:test"},
        "edge_summary": {"validated_edge_count": 1},
        "shadow_promotion": {"promotion_ready": True},
        "paperops": {"safety": {"live_capital_enabled": False}},
    }


def _build_release(inputs: dict) -> dict:
    return build_release_readiness(
        inputs["phase_status"],
        inputs["lock"],
        inputs["approvals"],
        inputs["risk_policy"],
        inputs["edge_summary"],
        inputs["shadow_promotion"],
        inputs["paperops"],
        generated_at=NOW,
    )


def _effective_release() -> dict:
    inputs = _release_inputs()
    inputs["lock"] = {"status": "released", "paperops_watch_only_mode": False}
    inputs["approvals"]["research_lock_release_approved"] = True
    release = _build_release(inputs)
    assert release["release_effective"] is True
    return release


def _complete_setup() -> dict:
    return {
        "setup_id": "setup:test",
        "evidence_class": VALIDATED_PAPER_STRATEGY,
        "candidate_identity_id": "candidate:test",
        "lineage": {
            "research_goal_id": "research-goal:test",
            "score_id": "score:test",
            "edge_id": "edge:test",
            "hypothesis_id": "hypothesis:test",
            "akber_result_id": "akber:test",
            "shadow_evidence_id": "shadow:test",
            "risk_proposal_id": "risk:test",
        },
        "instrument": "TEST",
        "market_family": "equity",
        "direction": "long",
        "horizon": "3d_forward",
        "edge_promotion_class": "validated_research_edge",
        "fresh_catalyst_state": "confirmed",
        "akber_decision": "pass",
        "source_quorum": {"passed": True, "independent_source_count": 3},
        "source_quorum_passed": True,
        "expected_net_return_positive_after_costs": True,
        "shadow_promotion_ready": True,
        "risk_proposal_complete": True,
        "proposed_quantity": 10,
        "proposed_notional_usd": 1_000.0,
        "maximum_loss_at_invalidation": 100.0,
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


def _complete_handoff() -> dict:
    return {
        "evidence_class": VALIDATED_PAPER_STRATEGY,
        "edge_claim_allowed": True,
        "edge_validation_status": "validated_under_frozen_policy",
        "paperops_handoff_id": "handoff:test",
        "router_decision_id": "router:test",
        "candidate_identity_id": "candidate:test",
        "route": "guarded_alpaca_paper_via_paperops",
        "lineage": {
            "research_goal_id": "research-goal:test",
            "score_id": "score:test",
            "edge_id": "edge:test",
            "hypothesis_id": "hypothesis:test",
            "akber_result_id": "akber:test",
            "shadow_evidence_id": "shadow:test",
            "risk_proposal_id": "risk:test",
        },
        "idempotency_material": {"idempotency_key": "idempotency:test"},
    }


def _complete_execution_identity() -> dict:
    handoff = _complete_handoff()
    return {
        "paperops_handoff_id": handoff["paperops_handoff_id"],
        "router_decision_id": handoff["router_decision_id"],
        "v3_consumption_receipt_id": "receipt:test",
        "complete_v3_lineage": handoff["lineage"],
        "accepted_v3_handoff_verified": True,
        "source_router_idempotency_key": handoff["idempotency_material"]["idempotency_key"],
        "source_idempotency_key": "q7-6-stage-source-test",
        "idempotency_key": "q7-6-stage-client-test",
        "client_order_id": "q7-6-stage-client-test",
        "submitted_at": "2025-12-31T23:50:00+00:00",
        "qty": "10",
    }


def _complete_guarded_close() -> dict:
    return {
        "status": "paper_exit_close_recorded",
        "paper_position_close_succeeded": True,
        "sanitized_http_status": 200,
        "recorded_at": NOW,
        "paperops_handoff_id": "handoff:test",
        "router_decision_id": "router:test",
        "v3_consumption_receipt_id": "receipt:test",
        "accepted_v3_handoff_verified": True,
        "request_fingerprint": "close:test",
    }


def test_release_checker_never_recommends_with_maturing_phase() -> None:
    inputs = _release_inputs()
    inputs["phase_status"]["phases"]["OR-8"]["state"] = "evidence_maturing"
    release = _build_release(inputs)
    assert release["release_recommended"] is False
    assert release["release_performed"] is False
    assert release["self_healing_release_allowed"] is False
    assert "OR-8" in release["nonpassing_phases"]


def test_release_recommendation_still_requires_explicit_operator_action() -> None:
    release = _build_release(_release_inputs())
    assert release["release_recommended"] is True
    assert release["release_effective"] is False
    assert release["release_performed"] is False
    assert release["research_lock_active"] is True
    assert release["status"] == "release_recommended_operator_action_required"


def test_router_missing_lineage_repairs_and_active_lock_blocks_clean_setup() -> None:
    setup = _complete_setup()
    setup["lineage"]["edge_id"] = None
    repaired = route_setup(setup, _effective_release(), generated_at=NOW)
    assert repaired["final_state"] == "repair-requested"
    assert repaired["paperops_handoff_allowed"] is False

    blocked_release = _build_release(_release_inputs())
    blocked = route_setup(_complete_setup(), blocked_release, generated_at=NOW)
    assert blocked["final_state"] == "blocked-safety-boundary"
    assert blocked["paper_order_created"] is False


def test_akber_veto_records_unreached_downstream_lineage_without_false_repair() -> None:
    setup = _complete_setup()
    setup["evidence_class"] = EXPERIMENTAL_UNVALIDATED
    setup["lineage"].pop("edge_id")
    setup["lineage"]["pattern_relationship_id"] = "pattern:test"
    setup["lineage"]["shadow_evidence_id"] = None
    setup["lineage"]["risk_proposal_id"] = None
    setup["akber_decision"] = "veto"
    setup["expected_net_return_positive_after_costs"] = False
    setup["decision_time_shadow_snapshot_ready"] = False
    setup["risk_proposal_complete"] = False

    decision = route_setup(
        setup,
        {"experimental_paper_release_effective": True},
        generated_at=NOW,
    )

    assert decision["final_state"] == "reject"
    assert decision["repair_reasons"] == []
    assert {row["field"] for row in decision["lineage_not_reached"]} == {
        "shadow_evidence_id",
        "risk_proposal_id",
    }


def test_router_holds_when_return_confirmation_stage_has_not_been_reached() -> None:
    setup = _complete_setup()
    setup["expected_net_return_positive_after_costs"] = False
    setup["risk_proposal_complete"] = False

    decision = route_setup(setup, _effective_release(), generated_at=NOW)

    assert decision["final_state"] == "hold"
    assert decision["hard_vetoes"] == []
    assert "expected_return_confirmation_not_reached" in decision["hold_reasons"]
    assert "risk_proposal_incomplete" in decision["hold_reasons"]


def test_router_rejects_confirmed_nonpositive_return_after_complete_risk_review() -> None:
    setup = _complete_setup()
    setup["expected_net_return_positive_after_costs"] = False

    decision = route_setup(setup, _effective_release(), generated_at=NOW)

    assert decision["final_state"] == "reject"
    assert "expected_return_not_positive_after_costs" in decision["hard_vetoes"]


def test_only_clean_candidate_builds_guarded_handoff_not_order() -> None:
    setup = _complete_setup()
    decision = route_setup(setup, _effective_release(), generated_at=NOW)
    assert decision["final_state"] == VALIDATED_ROUTER_STATE
    assert decision["paperops_handoff_allowed"] is True
    handoff = build_handoff(decision, setup)
    assert handoff["route"] == "guarded_alpaca_paper_via_paperops"
    assert handoff["paperops_handoff_is_not_order"] is True
    assert handoff["paper_order_created"] is False
    assert handoff["broker_write_count"] == 0


def test_canonical_consumer_accepts_clean_fresh_handoff_with_receipt() -> None:
    setup = _complete_setup()
    release = _effective_release()
    decision = route_setup(setup, release, generated_at=NOW)
    handoff = build_handoff(decision, setup)
    state = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=NOW,
    )

    assert validate_handoff_consumption_state(state) == []
    assert state["receipt_count"] == 1
    assert state["accepted_handoff_count"] == 1
    assert state["rejected_handoff_count"] == 0
    assert state["guarded_paperops_command_sequence_allowed"] is True
    assert state["receipts"][0]["status"] == ("accepted_for_guarded_paperops_sequence")
    assert state["paper_order_created_count"] == 0
    assert state["broker_write_count"] == 0


def test_canonical_consumer_rejects_stale_locked_and_duplicate_handoffs() -> None:
    setup = _complete_setup()
    release = _effective_release()
    decision = route_setup(setup, release, generated_at=NOW)
    handoff = build_handoff(decision, setup)
    handoff["generated_at"] = "2025-12-31T23:00:00+00:00"
    state = build_handoff_consumption_state(
        [handoff, handoff],
        [decision],
        release,
        {"status": "active", "paperops_watch_only_mode": True},
        generated_at=NOW,
    )

    assert validate_handoff_consumption_state(state) == []
    assert state["accepted_handoff_count"] == 0
    assert state["rejected_handoff_count"] == 2
    assert state["guarded_paperops_command_sequence_allowed"] is False
    reasons = {
        reason for rejection in state["rejections"] for reason in rejection["rejection_reasons"]
    }
    assert "handoff_stale" in reasons
    assert "research_lock_active" in reasons
    assert "duplicate_handoff_id_in_batch" in reasons
    assert "duplicate_idempotency_key_in_batch" in reasons


def test_canonical_consumer_rejects_live_route_and_reused_idempotency() -> None:
    setup = _complete_setup()
    release = _effective_release()
    decision = route_setup(setup, release, generated_at=NOW)
    handoff = build_handoff(decision, setup)
    handoff["route"] = "alpaca_live"
    key = handoff["idempotency_material"]["idempotency_key"]
    state = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=NOW,
        submitted_idempotency_keys={key},
    )

    assert validate_handoff_consumption_state(state) == []
    assert state["accepted_handoff_count"] == 0
    assert state["guarded_paperops_command_sequence_allowed"] is False
    reasons = set(state["rejections"][0]["rejection_reasons"])
    assert "route_not_guarded_alpaca_paper" in reasons
    assert "idempotency_key_already_submitted" in reasons


def test_accepted_v3_handoff_maps_into_existing_pt3_without_order_creation() -> None:
    setup = _complete_setup()
    release = _effective_release()
    decision = route_setup(setup, release, generated_at=NOW)
    handoff = build_handoff(decision, setup)
    state = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=NOW,
    )
    candidate = _v3_candidate_record(
        accepted_record=state["accepted_handoffs"][0],
        paper_mode={
            "status": "enabled_pending_downstream_gates",
            "paper_operational_mode_effective": True,
            "paper_operational_flag_disabled": False,
        },
        demo_run={"run_state": "active", "actual_calendar_run": True},
    )

    assert candidate["source_phase"] == "OR-15"
    assert candidate["paperops_handoff_id"] == handoff["paperops_handoff_id"]
    assert candidate["qualified_setup"] is True
    assert candidate["all_required_gates_passed"] is True
    assert candidate["paper_order_submission_allowed"] is False
    assert candidate["broker_post_called"] is False
    assert candidate["proof_credit_allowed"] is False


def test_canonical_wrapper_skips_submit_runner_without_accepted_v3_handoff(
    monkeypatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("orchestrator.paperops_autonomous_pass.subprocess.run", fake_run)
    results = run_command_sequence(
        repo_root=Path("."),
        python_executable="python",
        allow_new_paper_submission=False,
    )

    skipped = next(record for record in results if record["label"] == "active_automation_execute")
    assert skipped["skipped_by_router_v3_handoff_boundary"] is True
    assert skipped["parsed"]["paperops_active_runner_submitted_paper_order_count"] == "0"
    assert not any("run_active_paper_trading_automation.py" in command for command in calls)


def test_canonical_wrapper_records_child_timeout_without_crashing(monkeypatch) -> None:
    calls = 0

    def fake_run(command, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="partial=1")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("orchestrator.paperops_autonomous_pass.subprocess.run", fake_run)
    results = run_command_sequence(
        repo_root=Path("."),
        python_executable="python",
        allow_new_paper_submission=False,
    )

    first = results[0]
    assert first["returncode"] == 124
    assert first["timed_out"] is True
    assert first["ok"] is False
    assert first["parsed"]["partial"] == "1"
    assert len(results) == len(COMMAND_SEQUENCE)


def test_duplicate_exposure_and_prediction_market_fail_closed() -> None:
    setup = _complete_setup()
    setup["duplicate_exposure_conflict"] = True
    duplicate = route_setup(setup, _effective_release(), generated_at=NOW)
    assert duplicate["final_state"] == "reject"
    assert "duplicate_exposure_conflict" in duplicate["hard_vetoes"]

    prediction = _complete_setup()
    prediction["market_family"] = "prediction_market"
    prediction_result = route_setup(prediction, _effective_release(), generated_at=NOW)
    assert prediction_result["final_state"] == "reject"
    assert "prediction_market_context_only" in prediction_result["hard_vetoes"]


def test_zero_edge_experimental_setup_reaches_only_experimental_review_state() -> None:
    setup = _complete_setup()
    setup.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "paper_trade_purpose": (
                "Collect a real forward Alpaca Paper outcome without claiming a validated edge."
            ),
            "edge_id": None,
            "edge_promotion_class": None,
            "shadow_promotion_ready": False,
            "decision_time_shadow_snapshot_ready": True,
            "expires_at": "2026-01-04T00:00:00+00:00",
            "invalidation": ["source relationship reverses"],
        }
    )
    setup["lineage"]["edge_id"] = None
    setup["lineage"]["pattern_relationship_id"] = "pattern:test"
    release = {
        "experimental_paper_release_effective": True,
        "validated_paper_release_effective": False,
    }

    decision = route_setup(setup, release, generated_at=NOW)
    assert decision["final_state"] == EXPERIMENTAL_ROUTER_STATE
    assert decision["evidence_class"] == EXPERIMENTAL_UNVALIDATED
    handoff = build_handoff(decision, setup)
    assert handoff["lineage"]["edge_id"] is None
    assert handoff["lineage"]["pattern_relationship_id"] == "pattern:test"
    assert handoff["edge_claim_allowed"] is False
    assert handoff["proof_credit_allowed"] is False


def test_discovery_micro_setup_reaches_guarded_review_only_below_its_cap() -> None:
    setup = _complete_setup()
    setup.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "experimental_tier": DISCOVERY_MICRO_TIER,
            "paper_trade_purpose": "Collect one bounded forward paper observation.",
            "edge_id": None,
            "edge_promotion_class": None,
            "shadow_promotion_ready": False,
            "decision_time_shadow_snapshot_ready": True,
            "expires_at": "2026-01-04T00:00:00+00:00",
            "invalidation": ["source relationship reverses"],
            "proposed_notional_usd": 500.0,
        }
    )
    setup["lineage"]["edge_id"] = None
    setup["lineage"]["pattern_relationship_id"] = "pattern:micro"
    release = {
        "experimental_paper_release_effective": True,
        "validated_paper_release_effective": False,
    }

    decision = route_setup(setup, release, generated_at=NOW)
    handoff = build_handoff(decision, setup)

    assert decision["final_state"] == EXPERIMENTAL_ROUTER_STATE
    assert decision["experimental_tier"] == DISCOVERY_MICRO_TIER
    assert handoff["experimental_tier"] == DISCOVERY_MICRO_TIER
    assert handoff["paper_order_created"] is False
    assert handoff["proof_credit_allowed"] is False


def test_discovery_micro_setup_above_five_hundred_dollars_is_rejected() -> None:
    setup = _complete_setup()
    setup.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "experimental_tier": DISCOVERY_MICRO_TIER,
            "edge_id": None,
            "decision_time_shadow_snapshot_ready": True,
            "proposed_notional_usd": 500.01,
        }
    )
    setup["lineage"]["edge_id"] = None
    setup["lineage"]["pattern_relationship_id"] = "pattern:micro"

    decision = route_setup(
        setup,
        {"experimental_paper_release_effective": True},
        generated_at=NOW,
    )

    assert decision["final_state"] == "reject"
    assert "discovery_micro_notional_above_ceiling" in decision["hard_vetoes"]


def test_experimental_setup_without_shadow_snapshot_is_held() -> None:
    setup = _complete_setup()
    setup["evidence_class"] = EXPERIMENTAL_UNVALIDATED
    setup["lineage"]["edge_id"] = None
    setup["lineage"]["pattern_relationship_id"] = "pattern:test"
    setup["decision_time_shadow_snapshot_ready"] = False
    decision = route_setup(
        setup,
        {"experimental_paper_release_effective": True},
        generated_at=NOW,
    )
    assert decision["final_state"] == "hold"
    assert "decision_time_shadow_snapshot_missing" in decision["hold_reasons"]


def test_mirror_record_is_classified_and_never_proof_eligible() -> None:
    order = {
        "order_id": "mirror:test",
        "instrument": "TEST",
        "status": "filled",
        "submitted_at": "2025-12-31T23:59:00+00:00",
        "filled_at": "2025-12-31T23:59:30+00:00",
        "boundary": "Mirrored paper order only. Qadam did not place this order.",
    }
    trade = {
        "trade_id": "mirror:test",
        "instrument": "TEST",
        "opened_at": "2025-12-31T23:59:30+00:00",
        "closed_at": NOW,
        "postmortem_status": "postmortem_complete",
        "boundary": "Filled paper order mirrored for postmortem only.",
    }
    record = build_trade_lineage_record(order, trade, {}, {}, generated_at=NOW)
    assert record["broker_record_origin_class"] == "mirror_only_historical_record"
    assert record["current_lifecycle_state"] == "filled"
    assert record["metrics"]["real_close_verified"] is False
    assert record["proof_eligible"] is False
    assert record["proof_credit_granted"] is False


def test_complete_qadam_origin_can_be_eligible_but_never_gets_credit() -> None:
    handoff = _complete_handoff()
    order = {
        "order_id": "qadam:test",
        "paperops_handoff_id": "handoff:test",
        "instrument": "TEST",
        "direction": "buy",
        "status": "filled",
        "submitted_at": "2025-12-31T23:50:00+00:00",
        "filled_at": "2025-12-31T23:51:00+00:00",
        "filled_avg_price": 100.0,
        "boundary": "Guarded Alpaca Paper order mirrored after Qadam submission.",
    }
    trade = {
        "trade_id": "qadam:test",
        "instrument": "TEST",
        "direction": "buy",
        "opened_at": "2025-12-31T23:51:00+00:00",
        "closed_at": NOW,
        "postmortem_status": "postmortem_complete",
        "realized_net_pnl": 20.0,
        "exit_price": 102.0,
        "exit_reason": "invalidation_or_target_reached",
        "maximum_adverse_excursion": -5.0,
        "maximum_favourable_excursion": 25.0,
        "boundary": "Qadam-origin guarded paper trade.",
    }
    record = build_trade_lineage_record(
        order,
        trade,
        {},
        handoff,
        generated_at=NOW,
        accepted_v3_handoff_verified=True,
        execution_identity=_complete_execution_identity(),
        guarded_close_evidence=_complete_guarded_close(),
    )
    assert record["broker_record_origin_class"] == "qadam_origin_complete_lineage"
    assert record["lineage_complete"] is True
    assert record["current_lifecycle_state"] == "postmortem_complete"
    assert record["proof_eligible"] is True
    assert record["proof_credit_granted"] is False


def test_experimental_closed_trade_becomes_forward_outcome_not_edge_credit() -> None:
    handoff = _complete_handoff()
    handoff.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "edge_claim_allowed": False,
            "edge_validation_status": "not_yet_validated",
        }
    )
    handoff["lineage"].pop("edge_id")
    handoff["lineage"]["pattern_relationship_id"] = "pattern:test"
    execution_identity = _complete_execution_identity()
    execution_identity["complete_v3_lineage"] = handoff["lineage"]
    record = build_trade_lineage_record(
        {
            "order_id": "qadam:experimental",
            "paperops_handoff_id": "handoff:test",
            "instrument": "TEST",
            "direction": "buy",
            "status": "filled",
            "submitted_at": "2025-12-31T23:50:00+00:00",
            "filled_at": "2025-12-31T23:51:00+00:00",
            "filled_avg_price": 100.0,
            "boundary": "Guarded Alpaca Paper order.",
        },
        {
            "trade_id": "qadam:experimental",
            "instrument": "TEST",
            "direction": "buy",
            "opened_at": "2025-12-31T23:51:00+00:00",
            "closed_at": NOW,
            "postmortem_status": "postmortem_complete",
            "realized_net_pnl": 20.0,
            "exit_price": 102.0,
            "exit_reason": "invalidation_or_target_reached",
            "maximum_adverse_excursion": -5.0,
            "maximum_favourable_excursion": 25.0,
            "boundary": "Real experimental paper outcome.",
        },
        {},
        handoff,
        generated_at=NOW,
        accepted_v3_handoff_verified=True,
        execution_identity=execution_identity,
        guarded_close_evidence=_complete_guarded_close(),
    )
    assert record["proof_eligible"] is True
    assert record["proof_tiers"]["broker_execution_fact"] is True
    assert record["proof_tiers"]["experimental_forward_outcome"] is True
    assert record["proof_tiers"]["validated_edge_evidence"] is False
    assert record["proof_tiers"]["validated_edge_credit"] is False


def test_experimental_clean_epoch_filters_legacy_execution_rows() -> None:
    records = [
        {"order_id": "legacy", "paper_epoch_id": "paper-epoch:old"},
        {"order_id": "current", "paper_epoch_id": "paper-epoch:new"},
    ]
    included, excluded = _filter_current_execution_epoch(
        records,
        current_epoch={
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_epoch_id": "paper-epoch:new",
        },
    )
    assert [row["order_id"] for row in included] == ["current"]
    assert [row["order_id"] for row in excluded] == ["legacy"]


def test_shadow_marker_blocks_proof_even_with_complete_qadam_lineage() -> None:
    handoff = _complete_handoff()
    order = {
        "order_id": "shadow:test",
        "paperops_handoff_id": "handoff:test",
        "instrument": "TEST",
        "status": "filled",
        "filled_at": "2025-12-31T23:59:00+00:00",
        "boundary": "Shadow fixture record.",
    }
    trade = {
        "trade_id": "shadow:test",
        "instrument": "TEST",
        "closed_at": NOW,
        "postmortem_status": "postmortem_complete",
        "boundary": "Synthetic shadow outcome.",
    }
    record = build_trade_lineage_record(
        order,
        trade,
        {},
        handoff,
        generated_at=NOW,
        accepted_v3_handoff_verified=True,
        execution_identity=_complete_execution_identity(),
        guarded_close_evidence=_complete_guarded_close(),
    )
    assert record["lineage_complete"] is True
    assert record["proof_eligible"] is False
    assert record["proof_checks"]["not_backtest_shadow_fixture_or_mirror"] is False


def test_unaccepted_handoff_is_qadam_incomplete_and_cannot_receive_proof() -> None:
    record = build_trade_lineage_record(
        {
            "order_id": "qadam:unaccepted",
            "instrument": "TEST",
            "status": "filled",
            "submitted_at": "2025-12-31T23:50:00+00:00",
            "filled_at": "2025-12-31T23:51:00+00:00",
        },
        {
            "trade_id": "qadam:unaccepted",
            "instrument": "TEST",
            "closed_at": NOW,
            "postmortem_status": "postmortem_complete",
        },
        {},
        _complete_handoff(),
        generated_at=NOW,
    )
    assert record["broker_record_origin_class"] == "qadam_origin_incomplete_lineage"
    assert "accepted_v3_handoff_verification" in record["missing_lineage"]
    assert record["proof_eligible"] is False


def test_filled_qadam_order_is_not_closed_without_guarded_exit() -> None:
    handoff = _complete_handoff()
    record = build_trade_lineage_record(
        {
            "order_id": "qadam:filled-only",
            "instrument": "TEST",
            "status": "filled",
            "submitted_at": "2025-12-31T23:50:00+00:00",
            "filled_at": "2025-12-31T23:51:00+00:00",
        },
        {
            "trade_id": "qadam:filled-only",
            "instrument": "TEST",
            "closed_at": NOW,
            "postmortem_status": "postmortem_complete",
        },
        {},
        handoff,
        generated_at=NOW,
        accepted_v3_handoff_verified=True,
        execution_identity=_complete_execution_identity(),
    )
    assert record["broker_record_origin_class"] == "qadam_origin_complete_lineage"
    assert record["current_lifecycle_state"] == "filled"
    assert record["metrics"]["real_close_verified"] is False
    assert record["proof_eligible"] is False


def test_v3_submission_identity_survives_into_poll_and_exit_lineage() -> None:
    identity = _complete_execution_identity()
    post_record = {
        **identity,
        "source_family": "paperops_pt4_staged_order",
        "source_phase": "PT-4",
        "instrument": "TEST",
        "selected_venue": "alpaca_paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "alpaca_paper_post_succeeded": True,
        "idempotency_namespace": "phase7_demo_proof",
        "request_preview": {
            "method": "POST",
            "path": "/v2/orders",
            "symbol": "TEST",
            "side": "buy",
            "qty": "10",
            "notional": "",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": identity["client_order_id"],
            "source_idempotency_key": identity["source_idempotency_key"],
            "base_url_exposed": False,
            "authorization_header_included": False,
            "raw_payload_exposed": False,
            "broker_identifier_exposed": False,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
        },
        "broker_receipt": {
            "submitted_at": identity["submitted_at"],
            "broker_order_status": "new",
            "broker_client_order_id": identity["client_order_id"],
            "broker_order_id_hash": "broker-hash-test",
            "broker_order_identifier_exposed": False,
            "raw_broker_payload_stored": False,
            "raw_broker_payload_exposed": False,
            "authorization_header_exposed": False,
            "base_url_exposed": False,
            "secret_value_exposed": False,
        },
        "status": "submitted_to_alpaca_paper",
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }
    durable = _submission_identity_record(post_record)
    assert durable is not None
    assert durable["accepted_v3_handoff_verified"] is True
    poll = _source_record_to_poll_candidate(durable)
    assert poll["paperops_handoff_id"] == "handoff:test"
    assert poll["complete_v3_lineage"]["edge_id"] == "edge:test"
    lifecycle_record = {
        **poll,
        "record_type": "paperops_q7_lifecycle_readback_record",
        "lifecycle_state": "open_position",
        "position_echo_present": True,
        "counts_as_phase7_proof_credit": False,
        "q7_lifecycle_mutation_performed": False,
        "postmortem_due_marker_created": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
    }
    exit_candidate = _source_record_to_exit_candidate(lifecycle_record)
    assert exit_candidate["paperops_handoff_id"] == "handoff:test"
    assert exit_candidate["accepted_v3_handoff_verified"] is True
    assert exit_candidate["complete_v3_lineage"]["risk_proposal_id"] == "risk:test"


def test_stale_accepted_order_policy_proposes_but_never_cancels() -> None:
    policy = stale_accepted_order_policy(
        {
            "status": "accepted",
            "submitted_at": "2025-12-31T22:00:00+00:00",
        },
        generated_at=NOW,
    )
    assert policy["action"] == "cancel_replace_proposal"
    assert policy["automatic_cancel_allowed"] is False
    assert policy["automatic_replace_allowed"] is False
    assert policy["broker_write_allowed"] is False


def test_fresh_zero_position_mirror_reconciles_legacy_close_without_order_poll(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        freshness_module,
        "_paper_mirror_state",
        lambda _settings: (
            datetime.fromisoformat("2026-01-01T00:05:00+00:00"),
            "connected",
            0,
        ),
    )
    result = build_paperops_lifecycle_mirror_freshness(
        settings=SimpleNamespace(runtime_dir=Path("unused")),
        exit_path={
            "selected_exit_records": [
                {
                    "status": "paper_exit_close_recorded",
                    "paper_position_close_succeeded": True,
                    "sanitized_http_status": 200,
                    "paper_position_close_requested_at": NOW,
                    "symbol": "TEST",
                }
            ]
        },
        lifecycle_poller={"poll_result_records": [], "broker_get_called_count": 0},
        generated_at="2026-01-01T00:06:00+00:00",
    )
    assert result["status"] == "fresh_zero_open_positions_after_latest_close"
    assert result["fresh_after_latest_close"] is True
    assert result["lifecycle_fresh_after_latest_close"] is False
    assert result["paper_mirror_fresh_after_latest_close"] is True
    assert result["zero_open_position_reconciliation_used"] is True


def test_open_position_mirror_cannot_replace_missing_post_close_order_poll(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        freshness_module,
        "_paper_mirror_state",
        lambda _settings: (
            datetime.fromisoformat("2026-01-01T00:05:00+00:00"),
            "connected",
            1,
        ),
    )
    result = build_paperops_lifecycle_mirror_freshness(
        settings=SimpleNamespace(runtime_dir=Path("unused")),
        exit_path={
            "selected_exit_records": [
                {
                    "status": "paper_exit_close_recorded",
                    "paper_position_close_succeeded": True,
                    "sanitized_http_status": 200,
                    "paper_position_close_requested_at": NOW,
                    "symbol": "TEST",
                }
            ]
        },
        lifecycle_poller={"poll_result_records": [], "broker_get_called_count": 0},
        generated_at="2026-01-01T00:06:00+00:00",
    )
    assert result["status"] == "waiting_lifecycle_refresh"
    assert result["fresh_after_latest_close"] is False
    assert result["zero_open_position_reconciliation_used"] is False


def test_wave_d_status_reflects_missing_qadam_origin_outcomes() -> None:
    phases = {phase: {"state": "not_started"} for phase in PHASE_ORDER}
    for phase in PHASE_ORDER[:8]:
        phases[phase]["state"] = "passed"
    for index in range(17):
        phases[f"OR-{index}"]["state"] = "passed"
    for phase in (
        "OR-3",
        "OR-6",
        "OR-7",
        "OR-8",
        "OR-9",
        "OR-12",
        "OR-13",
        "OR-16",
    ):
        phases[phase]["state"] = "evidence_maturing"
    assert program_status(phases) == "wave_d_evidence_maturing"
