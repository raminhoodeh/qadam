from __future__ import annotations

from orchestrator.qadam_backtest_completion import (
    ABSOLUTE_TRADE_CEILING_USD,
    CANONICAL_INSTRUMENT_COUNT,
    CANONICAL_SOURCE_COUNT,
    CORE_STRATEGIES,
    METHODS,
    PHASES,
    PRIOR_ATTEMPT_FAMILY_COUNT,
    PRIOR_HISTORICAL_CANDIDATE_COUNT,
    _prior_attempt_family_freeze_errors,
    _prior_attempt_family_freeze_payload,
    _policy_errors,
    validate_phase,
)
from orchestrator.qadam_operator_ready_common import read_json, read_jsonl, runtime_dir


def test_all_qbc_phases_validate() -> None:
    assert len(PHASES) == 19
    assert {phase: validate_phase(phase) for phase in PHASES} == {phase: [] for phase in PHASES}


def test_prior_attempt_family_freeze_is_independent_of_mutable_focus_counts() -> None:
    payload = _prior_attempt_family_freeze_payload(
        "2026-07-29T00:00:00+00:00", "historical-focus-run"
    )
    assert _prior_attempt_family_freeze_errors(payload) == []
    assert payload["frozen_result"]["attempted_hypothesis_count"] == PRIOR_ATTEMPT_FAMILY_COUNT
    assert (
        payload["frozen_result"]["historical_candidate_count"] == PRIOR_HISTORICAL_CANDIDATE_COUNT
    )

    payload["frozen_result"]["attempted_hypothesis_count"] = 0
    assert "prior_attempt_family_freeze_result_mismatch" in (
        _prior_attempt_family_freeze_errors(payload)
    )


def test_roles_and_strategy_method_matrix_are_complete() -> None:
    runtime = runtime_dir()
    roles = read_json(runtime / "qadam_source_empirical_role_registry.json")
    matrix = read_json(runtime / "qadam_strategy_backtest_application_matrix.json")
    assert roles["source_count"] == CANONICAL_SOURCE_COUNT
    assert roles["instrument_count"] == CANONICAL_INSTRUMENT_COUNT
    assert roles["generic_missing_count"] == 0
    assert matrix["strategy_family_count"] == len(CORE_STRATEGIES)
    assert matrix["recommended_method_count"] == len(METHODS)
    assert matrix["application_count"] == len(CORE_STRATEGIES) * len(METHODS)


def test_every_terminal_result_has_one_proposal_only_strategy_impact() -> None:
    runtime = runtime_dir()
    summary = read_json(runtime / "qadam_backtest_completion_results_summary.json")
    impacts = read_jsonl(runtime / "qadam_backtest_strategy_impact.jsonl")
    assert len(impacts) == summary["current_registered_result_count"]
    assert len({row["backtest_result_id"] for row in impacts}) == len(impacts)
    assert all(row["authority"] == "proposal_only" for row in impacts)
    assert all(row["paper_canary_eligible"] is False for row in impacts)


def test_autonomous_governance_is_signed_and_inside_parent_ceiling() -> None:
    runtime = runtime_dir()
    admission = read_json(runtime / "qadam_autonomous_strategy_admission_policy.json")
    risk = read_json(runtime / "qadam_adaptive_paper_risk_policy.json")
    assert _policy_errors(admission) == []
    assert _policy_errors(risk) == []
    assert risk["absolute_per_trade_notional_usd"] == ABSOLUTE_TRADE_CEILING_USD
    assert [tier["max_notional_usd"] for tier in risk["tiers"]] == [
        0.0,
        500.0,
        1250.0,
        2500.0,
        5000.0,
    ]
    assert admission["signature_actor"] == "python_autonomous_governance_engine"
    assert risk["llm_or_quantum_signature_allowed"] is False


def test_no_edge_is_a_safe_passing_cash_state() -> None:
    runtime = runtime_dir()
    certification = read_json(runtime / "qadam_backtest_completion_certification.json")
    canary = read_json(runtime / "qadam_paper_canary_registry.json")
    statistical = read_json(runtime / "qadam_statistical_backtest_checks.json")
    assert certification["status"] == "passed"
    assert certification["certification_state"] == "complete_no_edge_found"
    assert certification["profitability_certified"] is False
    assert statistical["negative_control_promotion_gate_breach_count"] == 0
    assert canary["status"] == "no_eligible_paper_canary_cash_preserved"
    assert canary["paper_order_created_count"] == 0
    assert canary["broker_write_count"] == 0
    assert canary["proof_credit_created_count"] == 0
    assert canary["live_capital_enabled"] is False


def test_unavailable_history_and_real_time_are_never_fabricated() -> None:
    runtime = runtime_dir()
    maturity = read_json(runtime / "qadam_backtest_completion_forward_maturity.json")
    provider = read_json(runtime / "qadam_backtest_completion_provider_gate.json")
    assert maturity["status"] == "forward_evidence_maturing"
    assert maturity["simulated_elapsed_days"] == 0
    assert all(row["capture_active"] or row["operator_blocker"] for row in maturity["records"])
    assert provider["stock_act"]["fake_exact_notional_created_count"] == 0
    assert provider["kalshi"]["direct_instrument_eligible"] is False
    assert provider["polymarket"]["direct_instrument_eligible"] is False
    assert provider["unusual_whales"]["single_current_call_counts_as_history"] is False


def test_dashboard_enrichment_preserves_the_existing_route_shell() -> None:
    dashboard_javascript = (
        runtime_dir().parents[1] / "landing-page-repo" / "dashboard.js"
    ).read_text(encoding="utf-8")
    dashboard_stylesheet = (runtime_dir().parents[1] / "landing-page-repo" / "auth.css").read_text(
        encoding="utf-8"
    )
    assert "function renderQsaseBacktestCompletionContext" in dashboard_javascript
    assert "data-qadam-backtest-context" in dashboard_javascript
    assert ".qsase-backtest-context" in dashboard_stylesheet
