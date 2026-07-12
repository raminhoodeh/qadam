from dataclasses import replace

from orchestrator.qadam_quantum_edge_governance import (
    CURRENT_PUBLIC_LABELS,
    ROUTE_CONTRACT,
    TARGET_PUBLIC_LABELS,
    ZERO_AUTHORITY_FIELDS,
    build_quantum_edge_governance,
    negative_governance_probe_errors,
    quantum_research_authority,
    sample_quantum_research_candidate,
    validate_quantum_edge_governance,
    validate_quantum_research_candidate,
)


def test_wave_a_governance_allows_only_research_candidate_origination():
    payload = build_quantum_edge_governance()

    assert validate_quantum_edge_governance(payload) == []
    assert payload["authority"]["quantum_research_candidate_allowed"] is True
    assert all(payload["authority"][field] is False for field in ZERO_AUTHORITY_FIELDS)
    assert payload["research_candidate_is_trade_signal"] is False
    assert payload["hardware_activity_is_quantum_edge_proof"] is False


def test_wave_a_candidate_cannot_self_validate_or_create_downstream_authority():
    candidate = sample_quantum_research_candidate()
    assert validate_quantum_research_candidate(candidate) == []

    self_validated = replace(candidate, validation_contribution="quantum_strengthened")
    assert "quantum_candidate_cannot_self_validate" in validate_quantum_research_candidate(
        self_validated
    )

    authority = quantum_research_authority()
    authority["risk_approval_allowed"] = True
    escalated = replace(candidate, authority=authority)
    errors = validate_quantum_research_candidate(escalated)
    assert "quantum_candidate_authority_escalated:risk_approval_allowed" in errors


def test_wave_a_negative_probes_fail_closed():
    probes = negative_governance_probe_errors()

    assert probes["self_validation"]
    assert probes["strategy_authority"]
    assert probes["order_authority"]


def test_wave_a_preserves_routes_until_wave_f_label_migration():
    payload = build_quantum_edge_governance()

    assert payload["current_public_labels"] == CURRENT_PUBLIC_LABELS
    assert payload["target_public_labels"] == TARGET_PUBLIC_LABELS
    assert payload["route_contract"] == ROUTE_CONTRACT
    assert payload["label_migration_wave"] == "wave_f"
