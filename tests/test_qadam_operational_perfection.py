from __future__ import annotations

from orchestrator.qadam_operational_perfection import _akber_input_completeness


def test_canonical_akber_empty_queue_is_ready_not_incomplete() -> None:
    passed, reason, artifact, details = _akber_input_completeness(
        {"status": "akber_inputs_incomplete"},
        {
            "status": "passed",
            "implementation_ready": True,
            "input_count": 0,
            "valid_no_current_hypothesis_outcome": True,
            "router_eligible_with_missing_context_count": 0,
            "validation_error_count": 0,
        },
    )

    assert passed is True
    assert "no current hypotheses" in reason.lower()
    assert artifact == "qadam_akber_filter_v3_checks.json"
    assert details["contract"] == "canonical_akber_v3"


def test_canonical_akber_rejects_router_eligible_missing_context() -> None:
    passed, reason, _artifact, details = _akber_input_completeness(
        {},
        {
            "status": "passed",
            "implementation_ready": True,
            "input_count": 1,
            "valid_no_current_hypothesis_outcome": False,
            "router_eligible_with_missing_context_count": 1,
            "validation_error_count": 0,
        },
    )

    assert passed is False
    assert "incomplete" in reason.lower()
    assert details["router_eligible_with_missing_context_count"] == 1


def test_legacy_akber_contract_remains_a_fallback() -> None:
    passed, _reason, artifact, details = _akber_input_completeness(
        {"status": "akber_inputs_complete", "missing_input_counts": {}},
        {},
    )

    assert passed is True
    assert artifact == "qsase_akber_input_completeness.json"
    assert details["contract"] == "legacy_qsase_fallback"
