from __future__ import annotations

import json
from pathlib import Path
import pytest
from orchestrator import qadam_backtest_completion as qbc

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
from orchestrator.qadam_operator_ready_common import read_json, read_jsonl


@pytest.fixture
def qbc_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(qbc, "runtime_dir", lambda _settings=None: tmp_path)
    (tmp_path / "qadam_full_universe_gap_closure_matrix.json").write_text(json.dumps({
        "source_count": 2, "instrument_count": 2,
        "sources": [{"source_key": key, "closure_state": "forward_only"} for key in ("eia", "gdelt")],
        "instruments": [{"instrument": key, "closure_state": "forward_only"} for key in ("SPY", "XLE")],
    }))
    (tmp_path / "qadam_portfolio_policy.json").write_text(json.dumps({"risk_budget": {"max_position_notional_usd": 5000}}))
    qbc.build_all()
    return tmp_path


def test_incomplete_fixture_cannot_certify_all_historical_phases(qbc_runtime) -> None:
    assert len(PHASES) == 19
    errors = {phase: validate_phase(phase) for phase in PHASES}
    assert "baseline_source_count_mismatch" in errors["QBC-0"]
    assert read_json(qbc_runtime / qbc.CERTIFICATION_ARTIFACT)["status"] == "blocked"


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


def test_roles_and_strategy_method_matrix_are_complete(qbc_runtime) -> None:
    runtime = qbc_runtime
    roles = read_json(runtime / "qadam_source_empirical_role_registry.json")
    matrix = read_json(runtime / "qadam_strategy_backtest_application_matrix.json")
    assert roles["source_count"] == 2
    assert roles["instrument_count"] == 2
    assert CANONICAL_SOURCE_COUNT == 41 and CANONICAL_INSTRUMENT_COUNT == 19
    assert roles["generic_missing_count"] == 0
    assert matrix["strategy_family_count"] == len(CORE_STRATEGIES)
    assert matrix["recommended_method_count"] == len(METHODS)
    assert matrix["application_count"] == len(CORE_STRATEGIES) * len(METHODS)


def test_every_terminal_result_has_one_proposal_only_strategy_impact(qbc_runtime) -> None:
    runtime = qbc_runtime
    summary = read_json(runtime / "qadam_backtest_completion_results_summary.json")
    impacts = read_jsonl(runtime / "qadam_backtest_strategy_impact.jsonl")
    assert len(impacts) == summary["current_registered_result_count"]
    assert len({row["backtest_result_id"] for row in impacts}) == len(impacts)
    assert all(row["authority"] == "proposal_only" for row in impacts)
    assert all(row["paper_canary_eligible"] is False for row in impacts)


def test_autonomous_governance_is_signed_and_inside_parent_ceiling(qbc_runtime) -> None:
    runtime = qbc_runtime
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


def test_missing_history_preserves_cash_without_claiming_completion(qbc_runtime) -> None:
    runtime = qbc_runtime
    certification = read_json(runtime / "qadam_backtest_completion_certification.json")
    canary = read_json(runtime / "qadam_paper_canary_registry.json")
    assert certification["status"] == "blocked"
    assert certification["certification_state"] == "blocked"
    assert certification["profitability_certified"] is False
    assert canary["status"] == "no_eligible_paper_canary_cash_preserved"
    assert canary["paper_order_created_count"] == 0
    assert canary["broker_write_count"] == 0
    assert canary["proof_credit_created_count"] == 0
    assert canary["live_capital_enabled"] is False


def test_unavailable_history_and_real_time_are_never_fabricated(qbc_runtime) -> None:
    runtime = qbc_runtime
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
        Path(__file__).resolve().parents[1] / "landing-page-repo" / "dashboard.js"
    ).read_text(encoding="utf-8")
    dashboard_stylesheet = (Path(__file__).resolve().parents[1] / "landing-page-repo" / "auth.css").read_text(
        encoding="utf-8"
    )
    assert "function renderQsaseBacktestCompletionContext" in dashboard_javascript
    assert "data-qadam-backtest-context" in dashboard_javascript
    assert ".qsase-backtest-context" in dashboard_stylesheet
