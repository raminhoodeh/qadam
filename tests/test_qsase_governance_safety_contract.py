from orchestrator.qsase_governance_safety_contract import (
    UNIVERSAL_AUTHORITY_FLAGS,
    build_qsase_governance_safety_contract,
    validate_negative_authority_probes,
    validate_qsase_calendar_boundary,
    validate_qsase_governance_safety_contract,
    validate_qsase_proof_boundary,
)


def test_qsase_governance_contract_has_all_false_universal_authority_flags():
    payload = build_qsase_governance_safety_contract()

    assert payload["authority"] == UNIVERSAL_AUTHORITY_FLAGS
    assert payload["authority_flag_count"] == len(UNIVERSAL_AUTHORITY_FLAGS)
    assert payload["authority_false_count"] == len(UNIVERSAL_AUTHORITY_FLAGS)
    assert payload["authority_violation_count"] == 0
    assert validate_qsase_governance_safety_contract(payload) == []


def test_qsase_governance_negative_authority_probes_fail_closed():
    assert validate_negative_authority_probes() == []


def test_qsase_governance_proof_and_calendar_boundaries_are_clean():
    payload = build_qsase_governance_safety_contract()

    assert validate_qsase_proof_boundary(payload) == []
    assert validate_qsase_calendar_boundary(payload) == []
