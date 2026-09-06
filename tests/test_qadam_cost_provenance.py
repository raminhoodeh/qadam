import pytest

from orchestrator.contracts.costs import cost_evidence
from orchestrator.qadam_outcome_learning_promotion import build_outcome_records, build_attribution_ledger


@pytest.mark.parametrize("value", [None, True, -1, float("nan"), float("inf")])
def test_invalid_costs_are_unavailable(value):
    assert cost_evidence({"cost_bps": value})["state"] == "unavailable"


def test_number_alone_is_not_measurement():
    assert cost_evidence({"cost_bps": 0})["state"] == "unavailable"
    assert cost_evidence({"cost_bps": 0, "costs_measured": True,
                          "cost_measurement_source": "fee-receipt:1"})["state"] == "measured"


def test_real_shadow_producer_preserves_modelled_costs_through_attribution():
    source = {"outcome_id": "outcome:1", "cost_bps": 5.0,
              "cost_model_version": "matched-forward.1",
              "costs_are_modelled_not_live_execution_costs": True}
    rows = build_outcome_records([], [source], [], generated_at="2026-09-06T00:00:00Z")
    costs = build_attribution_ledger(rows, {}, generated_at="2026-09-06T00:00:00Z")[0]["components"]["costs"]
    assert costs["state"] == "modelled"
    assert costs["cost_bps"] == 5.0
    assert costs["live_performance_proven"] is False
