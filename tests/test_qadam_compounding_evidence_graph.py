from __future__ import annotations

from dataclasses import replace
import json
import sqlite3

import pytest

import orchestrator.qadam_temporal_graph_store as graph_store_module
from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import build_akber_input, evaluate_akber_input
from orchestrator.qadam_decision_evidence_packets import (
    build_decision_evidence_packets_from_inputs,
)
from orchestrator.qadam_multi_setup_paperops import audit_multi_setup_records
from orchestrator.qadam_graph_active_discovery import _qeg_hypothesis
from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
from orchestrator.qadam_qeg_reliability import _trial_state, evaluate_graph_storage
from orchestrator.qadam_qeg_visibility import (
    build_qeg_telegram_projection,
    validate_qeg_dashboard_payload,
)
from orchestrator.qadam_strategy_foundry_v4 import _provisional_net_expectancy
from orchestrator.qadam_resource_locks import RESOURCE_ORDER
from orchestrator.qadam_temporal_graph_contracts import (
    build_edge,
    build_node,
    validate_negative_probes,
    validate_record,
)
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore


def _settings(tmp_path) -> Settings:
    runtime = tmp_path / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    return replace(
        Settings.from_env(),
        runtime_dir=str(runtime),
        data_root=str(tmp_path / "data"),
        state_root=str(tmp_path / "data"),
    )


def test_temporal_contract_rejects_authority_and_future_leakage() -> None:
    node = build_node(
        "source_observation",
        "unit-observation",
        layer="observed",
        evidence_state="provider_backed",
        payload={"provider": "unit"},
        generated_at="2026-08-12T10:00:00+00:00",
        available_at="2026-08-12T09:59:00+00:00",
    )

    assert validate_record(node) == []
    assert validate_negative_probes() == []


def test_graph_rebuild_is_deterministic_and_append_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(graph_store_module, "GRAPH_MIN_FREE_BYTES", 1)
    monkeypatch.setattr(graph_store_module, "GRAPH_SOFT_LIMIT_BYTES", 10**12)
    monkeypatch.setattr(graph_store_module, "GRAPH_HARD_LIMIT_BYTES", 10**12)
    store = TemporalGraphStore(_settings(tmp_path))
    node = build_node(
        "instrument",
        "TEST",
        layer="observed",
        evidence_state="provider_backed",
        payload={"symbol": "TEST"},
        generated_at="2026-08-12T10:00:00+00:00",
    )

    assert store.append([node]) == {"written": 1, "duplicates": 0}
    assert store.append([node]) == {"written": 0, "duplicates": 1}
    first = store.rebuild()
    second = store.rebuild()

    assert first["generation_id"] == second["generation_id"]
    assert first["logical_record_set_hash"] == second["logical_record_set_hash"]
    assert second["node_count"] == 1


def test_graph_append_deduplicates_unchanged_projection_time(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(graph_store_module, "GRAPH_MIN_FREE_BYTES", 1)
    monkeypatch.setattr(graph_store_module, "GRAPH_SOFT_LIMIT_BYTES", 10**12)
    monkeypatch.setattr(graph_store_module, "GRAPH_HARD_LIMIT_BYTES", 10**12)
    store = TemporalGraphStore(_settings(tmp_path))
    first = build_node(
        "source_observation",
        "stable-observation",
        node_id="source-observation:stable",
        layer="observed",
        evidence_state="provider_backed",
        payload={"provider": "test", "published_at": "2026-08-01T00:00:00+00:00"},
        generated_at="2026-08-01T00:01:00+00:00",
        available_at="2026-08-01T00:01:00+00:00",
    )
    second = build_node(
        "source_observation",
        "stable-observation",
        node_id="source-observation:stable",
        layer="observed",
        evidence_state="provider_backed",
        payload={"provider": "test", "published_at": "2026-08-01T00:00:00+00:00"},
        generated_at="2026-08-01T00:02:00+00:00",
        available_at="2026-08-01T00:02:00+00:00",
    )

    assert store.append([first]) == {"written": 1, "duplicates": 0}
    assert store.append([second]) == {"written": 0, "duplicates": 1}


def test_graph_rebuild_rejects_dangling_edge(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(graph_store_module, "GRAPH_MIN_FREE_BYTES", 1)
    monkeypatch.setattr(graph_store_module, "GRAPH_SOFT_LIMIT_BYTES", 10**12)
    monkeypatch.setattr(graph_store_module, "GRAPH_HARD_LIMIT_BYTES", 10**12)
    store = TemporalGraphStore(_settings(tmp_path))
    source = build_node(
        "source_observation",
        "source-a",
        node_id="source:a",
        layer="observed",
        evidence_state="provider_backed",
        payload={"provider": "test"},
    )
    dangling = build_edge(
        "supports",
        source["node_id"],
        "pattern:missing",
        layer="inferred",
        evidence_state="research_only",
    )
    store.append([source, dangling])

    with pytest.raises(sqlite3.IntegrityError):
        store.rebuild()


def test_graph_write_hard_stops_before_disk_ceiling(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(graph_store_module, "GRAPH_MIN_FREE_BYTES", 1)
    monkeypatch.setattr(graph_store_module, "GRAPH_SOFT_LIMIT_BYTES", 10**12)
    monkeypatch.setattr(graph_store_module, "GRAPH_HARD_LIMIT_BYTES", 1)
    store = TemporalGraphStore(_settings(tmp_path))
    node = build_node(
        "instrument",
        "TOO-LARGE",
        layer="observed",
        evidence_state="provider_backed",
        payload={"symbol": "TOO-LARGE"},
    )

    with pytest.raises(RuntimeError, match="graph_storage_hard_ceiling_hold"):
        store.append([node])
    assert list(store.iter_events()) == []


def test_qeg_telegram_suppresses_unchanged_material_state(tmp_path) -> None:
    settings = _settings(tmp_path)
    dashboard = {
        "sections": {
            "overview": {"validated_edge_count": 0, "strategy_version_count": 0},
            "patterns": {
                "rows": [
                    {
                        "pattern_relationship_id": "pattern:one",
                        "research_question": "Does one source precede TEST?",
                        "research_rank": 0.42,
                        "actionability_rank": 0.31,
                        "current_trigger_active": False,
                        "status": "research_relationship",
                        "support_count": 1,
                        "evidence_path": [{"source_key": "source-one"}],
                        "next_destination": "collect independent evidence",
                    }
                ]
            },
            "quantum": {
                "comparison_count": 1,
                "predictive_conclusion": "classical_preferred",
                "incremental_mean_net_return": -0.001,
                "strategy_evidence_changed": False,
            },
            "decision": {"paper_review_candidate_count": 0, "final_state_counts": {}},
            "learning": {"matured_record_count": 0},
        }
    }
    runtime = tmp_path / "runtime"
    (runtime / "qadam_qeg_dashboard_projection.json").write_text(
        json.dumps(dashboard), encoding="utf-8"
    )

    first, first_errors = build_qeg_telegram_projection(settings)
    second, second_errors = build_qeg_telegram_projection(settings)

    assert first_errors == []
    assert first["status"] == "candidate_ready"
    assert first["message"]
    assert second_errors == []
    assert second["status"] == "suppressed_no_material_change"
    assert second["message"] is None
    assert second["delivery_attempted"] is False


def test_qeg_dashboard_is_read_only_and_rank_is_not_probability() -> None:
    sections = {
        "overview": {"source_count": 41, "instrument_count": 19},
        "data_sources": {},
        "trading_universe": {},
        "patterns": {"rows": [{"research_rank_type": "research_rank_not_profit_probability"}]},
        "quantum": {},
        "strategies": {},
        "decision": {},
        "orders": {"canonical_wrapper_only": True},
        "learning": {},
        "system": {},
    }
    payload = {
        "sections": sections,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "paper_order_created": False,
    }

    assert validate_qeg_dashboard_payload(payload) == []
    payload["paper_order_created"] = True
    assert "qeg_dashboard_authority_violation" in validate_qeg_dashboard_payload(payload)


def test_qeg_operator_order_preserves_canonical_paperops_route() -> None:
    services = {definition.service_id: definition for definition in SERVICE_DEFINITIONS}

    assert services["qeg_evidence_cycle"].dependencies == ("akber_review",)
    assert "qeg_evidence_cycle" in services["canonical_tradeability"].dependencies
    assert "qualitative_evidence_cycle" in services["canonical_tradeability"].dependencies
    assert services["forward_shadow"].dependencies == ("canonical_tradeability",)
    assert "scripts/check_qadam_multi_setup_paperops.py" in {
        command[0] for command in services["portfolio_router_review"].command_sequence
    }
    assert services["guarded_paperops"].command_sequence == (
        ("scripts/run_paperops_autonomous_pass.py",),
    )
    assert services["open_market_conversion"].command_sequence[0][-1] == "--no-paperops"
    assert "dashboard_projection" in services["guarded_paperops"].write_resources
    assert RESOURCE_ORDER.index("temporal_graph") < RESOURCE_ORDER.index("learning_plane")


def test_qeg_hypothesis_preserves_executable_evidence_context() -> None:
    strategy = {
        "strategy_version_id": "strategy-version:one",
        "pattern_relationship_id": "pattern:one",
        "research_goal_id": "research-goal:one",
        "experiment_id": "experiment:one",
        "score_id": "score:one",
        "evidence_hash": "evidence-hash:one",
        "evidence_class": "experimental_unvalidated",
        "contract": {
            "strategy_family_id": "semiconductor_policy_options_asymmetry",
            "destination": "core_family_refinement",
            "instrument": "SMH",
            "execution_proxy": "SMH",
            "entry_rule": "fresh event plus current market confirmation",
            "invalidation_rule": "event reverses or market confirmation fails",
            "exit_rule": "time horizon or invalidation",
            "time_horizon": "5d_forward",
            "maximum_notional_usd": 1000.0,
            "experimental_economics": {
                "provisional_net_expectancy_after_costs": 0.0053,
                "source_hypothesis_id": "backtest-hypothesis:one",
                "source_method_id": "lead_lag_event_study",
                "source_rejection_reasons": [
                    "false_discovery_adjusted_result_not_significant"
                ],
                "expected_reward_to_risk": 1.5,
            },
        },
    }
    candidate = {
        "pattern_relationship_id": "pattern:one",
        "score_id": "score:one",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "strategy_label": "Semiconductor policy options asymmetry",
        "instrument": "SMH",
        "horizon": "5d_forward",
        "research_rank": 0.73,
        "evidence_profile": "semiconductor_policy",
        "source_path": [
            {
                "source_key": "sec_edgar",
                "fresh": True,
                "quorum_eligible": True,
            },
            {
                "source_key": "stale_support",
                "fresh": False,
                "quorum_eligible": True,
            },
        ],
        "economic_mechanism": "Policy news can precede sector repricing.",
        "latest_observation_at": "2026-08-14T14:00:00+00:00",
    }
    direction = {
        "actionable_direction": "long",
        "direction_resolution_id": "direction:one",
    }
    admission = {"admission_decision_id": "admission:one"}

    hypothesis = _qeg_hypothesis(
        strategy,
        candidate,
        direction,
        admission,
        generated_at="2026-08-14T14:01:00+00:00",
    )

    assert hypothesis["pattern_lineage"]["raw_research_score"] == 0.73
    assert hypothesis["pattern_lineage"]["fresh_support_sources"] == ["sec_edgar"]
    assert hypothesis["pattern_lineage"]["source_confirmation_mode"] == (
        "profile_specific_current_trigger_plus_one_live_market_confirmation"
    )
    assert hypothesis["expected_edge_range"]["net_expectancy"] == 0.0053
    assert hypothesis["expected_edge_range"]["not_a_validated_expectancy"] is True
    assert hypothesis["risk_concept"]["expected_reward_to_risk"] == 1.5
    assert hypothesis["risk_concept"]["absolute_notional_ceiling_usd"] == 1000.0
    assert hypothesis["paperability"]["paper_order_allowed"] is False


def test_provisional_expectancy_preserves_historical_direction() -> None:
    positive_result = {"mean_net_return": 0.02}
    negative_result = {"mean_net_return": -0.02}

    assert _provisional_net_expectancy(positive_result, "long") == 0.005
    assert _provisional_net_expectancy(positive_result, "short") is None
    assert _provisional_net_expectancy(negative_result, "short") == 0.005
    assert _provisional_net_expectancy(negative_result, "long") is None


def test_discovery_micro_reaches_akber_with_collectable_live_evidence() -> None:
    generated_at = "2026-08-14T14:01:00+00:00"
    strategy = {
        "strategy_version_id": "strategy-version:one",
        "pattern_relationship_id": "pattern:one",
        "research_goal_id": "research-goal:one",
        "experiment_id": "experiment:one",
        "score_id": "score:one",
        "evidence_hash": "evidence-hash:one",
        "evidence_class": "experimental_unvalidated",
        "contract": {
            "strategy_family_id": "semiconductor_policy_options_asymmetry",
            "destination": "core_family_refinement",
            "instrument": "SMH",
            "execution_proxy": "SMH",
            "entry_rule": "fresh event plus current market confirmation",
            "invalidation_rule": "event reverses or market confirmation fails",
            "exit_rule": "time horizon or invalidation",
            "time_horizon": "5d_forward",
            "maximum_notional_usd": 1000.0,
            "experimental_economics": {
                "provisional_net_expectancy_after_costs": 0.0053,
                "expected_reward_to_risk": 1.5,
            },
        },
    }
    candidate = {
        "pattern_relationship_id": "pattern:one",
        "score_id": "score:one",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "strategy_label": "Semiconductor policy options asymmetry",
        "instrument": "SMH",
        "horizon": "5d_forward",
        "research_rank": 0.73,
        "evidence_profile": "event_catalyst",
        "source_path": [
            {"source_key": "sec_edgar", "fresh": True, "quorum_eligible": True}
        ],
        "economic_mechanism": "Policy news can precede sector repricing.",
        "latest_observation_at": generated_at,
    }
    direction = {
        "actionable_direction": "long",
        "direction_resolution_id": "direction:one",
        "evidence_ids": ["trigger:one"],
        "generated_at": generated_at,
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "instrument": "SMH",
    }
    hypothesis = _qeg_hypothesis(
        strategy,
        candidate,
        direction,
        {"admission_decision_id": "admission:one"},
        generated_at=generated_at,
    )
    market_record = {
        "symbol": "SMH",
        "last_close": 300.0,
        "current_price": 301.0,
        "previous_close": 299.0,
        "percent_move": 0.67,
        "volume_ratio": 1.1,
        "rolling_volatility_20d": 0.02,
        "annualized_volatility": 0.317,
        "spread_bps": 2.5,
        "provider_backed": True,
        "market_state": "provider_latest_read_only_observation",
        "session_state": "regular_session",
        "quote_actionable": True,
        "trade_actionable": True,
        "available_at": generated_at,
        "quote_observed_at": generated_at,
    }
    current_artifacts = {
        "market_context": {
            "recent_packets": [
                {
                    "packet_id": "market-packet:one",
                    "packet_role": "universal_current_market_context",
                    "generated_at": generated_at,
                    "watched_instruments": ["SMH"],
                    "price_volume_context": {
                        "provider": "alpaca_market_data_v2",
                        "status": "ok",
                        "records": [market_record],
                    },
                    "technical_context": {"status": "unavailable", "records": []},
                    "orderflow_context": {"status": "unavailable", "records": []},
                }
            ]
        },
        "signal_integrity_reviews": [],
        "alpaca_mirror": {
            "status": "ok",
            "snapshot": {
                "mode": "paper",
                "connection_status": "alpaca_paper_readonly_connected",
                "observed_at": generated_at,
            },
            "write_authority": False,
        },
        "tradingview_status": {},
        "tradingview_context": {},
        "bookmap_context": {"sample": True},
        "nonlinear_comparisons": [],
    }
    trigger = {
        "trigger_id": "trigger:one",
        "trigger_state": "active",
        "available_at": generated_at,
        "source_keys": ["sec_edgar"],
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "affected_instruments": ["SMH"],
        "authority": authority_flags(),
    }

    packet_state = build_decision_evidence_packets_from_inputs(
        [hypothesis],
        [direction],
        [trigger],
        [],
        [],
        current_artifacts,
        generated_at=generated_at,
    )

    assert packet_state["rejections"] == []
    packet = packet_state["packets"][0]
    context = dict(packet["akber_context"])
    context["_decision_evidence_packet_id"] = packet["decision_evidence_packet_id"]
    context["_decision_generation_id"] = packet["decision_generation_id"]
    akber_input = build_akber_input(
        hypothesis,
        context,
        generated_at=generated_at,
        strict_provenance=True,
    )
    result = evaluate_akber_input(akber_input)

    assert akber_input["missing_critical_context"] == []
    assert result["decision"] == "pass"
    assert result["router_eligible"] is True
    assert result["akber_pass_is_execution_approval"] is False


def test_qeg_trial_counts_real_market_days_only(tmp_path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "qadam_qeg_active_discovery_trial.json").write_text(
        json.dumps({"started_at": "2026-08-10T00:00:00+00:00"}), encoding="utf-8"
    )
    receipts = [
        {
            "receipt_id": "eligible-one",
            "service_id": "qeg_evidence_cycle",
            "state": "completed",
            "completed_at": "2026-08-11T15:00:00+00:00",
        },
        {
            "receipt_id": "same-day",
            "service_id": "qeg_evidence_cycle",
            "state": "completed",
            "completed_at": "2026-08-11T16:00:00+00:00",
        },
        {
            "receipt_id": "outside-session",
            "service_id": "qeg_evidence_cycle",
            "state": "completed",
            "completed_at": "2026-08-12T01:00:00+00:00",
        },
        {
            "receipt_id": "wrong-service",
            "service_id": "dashboard_refresh",
            "state": "completed",
            "completed_at": "2026-08-12T15:00:00+00:00",
        },
    ]
    (runtime / "qadam_operator_service_receipts.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in receipts), encoding="utf-8"
    )

    trial = _trial_state(runtime)

    assert trial["completed_real_market_day_count"] == 1
    assert trial["simulated_elapsed_day_count"] == 0
    assert trial["backfilled_elapsed_day_count"] == 0
    assert trial["paper_growth_trial_calendar_advanced"] is False


def test_multi_setup_audit_rejects_duplicate_handoff_identity() -> None:
    decisions = [
        {"decision_id": "decision-one", "final_state": "paper-review-candidate"},
        {"decision_id": "decision-two", "final_state": "paper-review-candidate"},
    ]
    handoffs = [
        {
            "router_decision_id": "decision-one",
            "candidate_identity_id": "same-candidate",
            "idempotency_key": "same-key",
            "research_goal_id": "goal-one",
        },
        {
            "router_decision_id": "decision-two",
            "candidate_identity_id": "same-candidate",
            "idempotency_key": "same-key",
            "research_goal_id": "goal-two",
        },
    ]

    _metrics, errors = audit_multi_setup_records(decisions, handoffs)

    assert "duplicate_handoff_candidate_identity" in errors
    assert "duplicate_handoff_idempotency_key" in errors


def test_storage_policy_hard_stop_is_fail_closed() -> None:
    state = evaluate_graph_storage(graph_bytes=20 * 1024**3, free_bytes=1)

    assert state["hard_stop_active"] is True
    assert state["graph_writes_allowed"] is False
