from __future__ import annotations

from orchestrator.qadam_evidence_fit_certification import (
    evaluate_negative_safety_probe,
    run_negative_safety_probes,
)


def test_every_ef10_unsafe_probe_is_rejected() -> None:
    probes = run_negative_safety_probes()
    assert len(probes) == 11
    assert all(row["status"] == "passed" for row in probes)
    assert all(row["unsafe_payload_rejected"] is True for row in probes)


def test_safe_paper_only_inputs_are_not_misclassified_as_unsafe() -> None:
    assert evaluate_negative_safety_probe(
        "fixture_labeled_live",
        {"sample_or_fixture": False, "availability_state": "live_fresh"},
    ) is True
    assert evaluate_negative_safety_probe(
        "stale_source_trigger",
        {"freshness_status": "fresh", "trigger_state": "active"},
    ) is True
    assert evaluate_negative_safety_probe(
        "context_only_alpaca_order",
        {"instrument_role": "direct_paper_instrument", "route": "alpaca_paper"},
    ) is True
    assert evaluate_negative_safety_probe(
        "live_endpoint_enabled", {"live_capital_enabled": False}
    ) is True
