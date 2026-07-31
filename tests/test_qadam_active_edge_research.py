from __future__ import annotations

import json

import orchestrator.qadam_active_edge_research as active_research


def _write(tmp_path, name: str, payload: dict) -> None:
    (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")


def _runtime(tmp_path) -> None:
    _write(
        tmp_path,
        "qadam_power_market_edge_engine.json",
        {
            "provider_state": {
                "caiso_oasis": "provider_backed_live",
                "alpaca_iex": "provider_backed_live",
            },
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "proof_credit_count": 0,
            "live_capital_enabled": False,
            "current_pattern_score_count": 0,
            "backtest_hypothesis_count": 12,
            "validated_candidate_count": 0,
        },
    )
    _write(
        tmp_path,
        "qadam_power_market_edge_engine_checks.json",
        {"provider_backed_live_refresh": True, "safe_to_consume": True},
    )
    _write(
        tmp_path,
        "qadam_power_market_acquisition_manifest.json",
        {"resumable": True, "idempotent": True, "complete_job_count": 30, "remaining_job_count": 90},
    )
    _write(
        tmp_path,
        "qadam_power_market_backtest.json",
        {"point_in_time_safe": True, "cost_adjusted": True, "status": "complete_no_surviving_candidate"},
    )
    _write(
        tmp_path,
        "qadam_power_market_strategy_registry.json",
        {
            "automatic_strategy_admission_enabled": True,
            "automatic_risk_envelope_expansion_enabled": False,
            "strategies": [
                {
                    "strategy_family_id": "power_scarcity_congestion",
                    "admission_state": "research_sleeve_under_evidenced",
                }
            ],
        },
    )
    _write(tmp_path, "qadam_strategy_foundry_v3_checks.json", {"status": "passed"})
    _write(tmp_path, "qadam_akber_filter_v3_checks.json", {"status": "passed"})
    _write(
        tmp_path,
        "qadam_forward_shadow_checks.json",
        {
            "implementation_ready": True,
            "validation_error_count": 0,
            "eligible_hypothesis_count": 0,
            "trade_progression_eligible_hypothesis_count": 0,
            "counterfactual_observation_hypothesis_count": 0,
            "decision_count": 0,
            "outcome_count": 0,
        },
    )
    _write(
        tmp_path,
        "qadam_portfolio_risk_engine_checks.json",
        {"status": "passed", "validation_error_count": 0},
    )
    _write(
        tmp_path,
        "qadam_router_v3_paperops_checks.json",
        {"status": "passed", "validation_error_count": 0, "decision_count": 0},
    )
    _write(
        tmp_path,
        "qadam_router_v3_why_not_trading_now.json",
        {"status": "not_trading", "current_router_state": "watchlist"},
    )
    _write(
        tmp_path,
        "qadam_experimental_paper_policy.json",
        {"risk": {"risk_or_authority_mutation_allowed": False}},
    )
    _write(
        tmp_path,
        "qadam_operator_service_status.json",
        {
            "service_running": True,
            "services": [
                {
                    "service_id": "power_market_research",
                    "current_execution_allowed": True,
                    "circuit_breaker": {"state": "closed"},
                }
            ],
        },
    )
    _write(
        tmp_path,
        "qadam_operator_circuit_breakers.json",
        {"services": {"power_market_research": {"state": "closed"}}},
    )
    _write(
        tmp_path,
        "qadam_quantum_edge_wave_f_public_view.json",
        {
            "pattern_recognition": {
                "candidates": [
                    {"strategy_family_id": "power_scarcity_congestion"}
                ]
            },
            "trading_strategies": {"emerging_strategy_candidates": []},
        },
    )


def test_active_edge_research_is_operational_without_claiming_an_edge(
    tmp_path, monkeypatch
) -> None:
    _runtime(tmp_path)
    monkeypatch.setattr(active_research, "runtime_dir", lambda _settings=None: tmp_path)
    monkeypatch.setattr(active_research, "research_paths_are_ignored", lambda: True)

    payload = active_research.build_active_edge_research_certification()

    assert payload["status"] == "operational"
    assert payload["automatic_strategy_progression_operational"] is True
    assert payload["empirical_state"] == "hypotheses_tested_no_current_signal"
    assert payload["edge_proven"] is False
    assert payload["paper_order_created_count"] == 0


def test_active_edge_research_uses_authoritative_circuit_not_stale_status(
    tmp_path, monkeypatch
) -> None:
    _runtime(tmp_path)
    status = json.loads((tmp_path / "qadam_operator_service_status.json").read_text())
    status["services"][0]["circuit_breaker"] = {"state": "open"}
    _write(tmp_path, "qadam_operator_service_status.json", status)
    monkeypatch.setattr(active_research, "runtime_dir", lambda _settings=None: tmp_path)
    monkeypatch.setattr(active_research, "research_paths_are_ignored", lambda: True)

    payload = active_research.build_active_edge_research_certification()

    assert payload["status"] == "operational"


def test_active_edge_research_fails_closed_without_live_provider(
    tmp_path, monkeypatch
) -> None:
    _runtime(tmp_path)
    _write(
        tmp_path,
        "qadam_power_market_edge_engine_checks.json",
        {"provider_backed_live_refresh": False, "safe_to_consume": True},
    )
    monkeypatch.setattr(active_research, "runtime_dir", lambda _settings=None: tmp_path)
    monkeypatch.setattr(active_research, "research_paths_are_ignored", lambda: True)

    payload = active_research.build_active_edge_research_certification()

    assert payload["status"] == "blocked"
    assert "The mechanism research lane lacks a fresh real-provider input." in payload["blockers"]


def test_active_edge_research_requires_current_signal_to_reach_shadow_and_router(
    tmp_path, monkeypatch
) -> None:
    _runtime(tmp_path)
    power = json.loads((tmp_path / "qadam_power_market_edge_engine.json").read_text())
    power["current_pattern_score_count"] = 1
    _write(tmp_path, "qadam_power_market_edge_engine.json", power)
    monkeypatch.setattr(active_research, "runtime_dir", lambda _settings=None: tmp_path)
    monkeypatch.setattr(active_research, "research_paths_are_ignored", lambda: True)

    payload = active_research.build_active_edge_research_certification()

    assert payload["status"] == "blocked"
    assert any("not being observed forward" in blocker for blocker in payload["blockers"])

    shadow = json.loads((tmp_path / "qadam_forward_shadow_checks.json").read_text())
    shadow.update(
        {
            "eligible_hypothesis_count": 1,
            "counterfactual_observation_hypothesis_count": 1,
            "decision_count": 1,
        }
    )
    _write(tmp_path, "qadam_forward_shadow_checks.json", shadow)
    _write(
        tmp_path,
        "qadam_router_v3_paperops_checks.json",
        {"status": "passed", "validation_error_count": 0, "decision_count": 1},
    )

    payload = active_research.build_active_edge_research_certification()

    assert payload["status"] == "operational"
