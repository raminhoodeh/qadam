from __future__ import annotations

from orchestrator.qadam_evidence_gate_alignment import (
    build_evidence_gate_alignment_from_inputs,
    validate_evidence_gate_alignment,
)
from orchestrator.qadam_experimental_paper_policy import default_policy
from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_portfolio_risk_engine import default_portfolio_policy

NOW = "2026-08-03T12:00:00+00:00"


def _inputs() -> dict:
    hypothesis = {
        "hypothesis_id": "hypothesis:test",
        "experimental_tier": "discovery_micro",
        "pattern_lineage": {
            "evidence_profile": "event_catalyst",
            "provider_availability_is_not_trigger": True,
            "fresh_trigger_sources": [],
        },
    }
    akber_input = {
        "akber_input_id": "akber-input:test",
        "experimental_tier": "discovery_micro",
        "evidence_profile": "event_catalyst",
        "required_context_fields": [
            "source_price_context",
            "fresh_catalyst",
            "volatility_context",
            "risk_reward_context",
            "invalidation_clarity",
            "liquidity_and_spread",
            "paperability_proxy",
        ],
        "confirmation_alternatives": [
            "volume_or_flow_confirmation",
            "technical_confirmation",
            "pricing_gap_evidence",
            "nonlinear_quantum_review",
        ],
        "missing_context_reasons": [],
    }
    akber_result = {
        "akber_result_id": "akber-result:test",
        "decision": "pass",
        "evidence_profile": "event_catalyst",
        "missing_critical_context_count": 0,
        "current_trigger_sources": ["rss"],
        "confirmation_alternative_satisfied": True,
    }
    replay = [{"replay_id": "replay:test"}]
    ablations = [
        {
            "stage_removed": "confirmation",
            "delta": {"expectancy_change": -0.001},
        },
        {
            "stage_removed": "execution",
            "delta": {"expectancy_change": -0.001, "drawdown_change": -0.1},
        },
    ]
    checks = {
        "net_historical_contribution_measurable": True,
        "historical_filter_metrics": {"expectancy_change": 0.002},
    }
    manifest = {
        "status": "complete",
        "run_id": "backtest:test",
        "bulk_results": {"result_count": 10, "fold_count": 30},
    }
    return {
        "policy": default_policy(NOW),
        "backtest_manifest": manifest,
        "hypotheses": [hypothesis],
        "akber_inputs": [akber_input],
        "akber_results": [akber_result],
        "akber_replay": replay,
        "akber_ablations": ablations,
        "akber_checks": checks,
        "risk_policy": default_portfolio_policy(NOW),
        "generated_at": NOW,
    }


def test_aligned_gate_uses_backtest_and_preserves_safety() -> None:
    record = build_evidence_gate_alignment_from_inputs(**_inputs())

    assert validate_evidence_gate_alignment(record) == []
    assert record["status"] == "passed"
    assert record["backtest_usage"]["used"] is True
    assert record["current_alignment"]["unsafe_pass_count"] == 0
    assert all(record["risk_context_alignment"]["checks"].values())
    assert record["risk_context_alignment"]["numeric_risk_envelope_changed"] is False
    assert all(record["retained_safety_controls"].values())
    assert record["authority"] == authority_flags()


def test_provider_status_as_trigger_fails_closed() -> None:
    inputs = _inputs()
    inputs["hypotheses"][0]["pattern_lineage"]["provider_availability_is_not_trigger"] = False
    record = build_evidence_gate_alignment_from_inputs(**inputs)

    assert record["status"] == "blocked"
    assert any("provider_status_became_trigger" in error for error in record["blockers"])
