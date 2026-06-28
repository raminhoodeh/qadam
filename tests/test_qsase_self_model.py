from orchestrator.qsase_self_model import (
    SELF_MODEL_AUTHORITY_FLAGS,
    build_qsase_self_model,
    validate_negative_self_model_probes,
    validate_qsase_self_model,
)


def test_qsase_self_model_has_required_roles_and_false_authority_flags():
    payload = build_qsase_self_model()
    role_keys = {role["role_key"] for role in payload["architecture_roles"]}

    assert "python_coo" in role_keys
    assert "local_gemma_research_analyst" in role_keys
    assert "frontier_gemini_strategy_lead" in role_keys
    assert "ibm_quantum_gates_oracle" in role_keys
    assert payload["authority_flags"] == SELF_MODEL_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert validate_qsase_self_model(payload) == []


def test_qsase_self_model_keeps_models_quantum_dashboard_and_telegram_non_authoritative():
    payload = build_qsase_self_model()

    assert payload["model_outputs_are_approvals"] is False
    assert payload["quantum_outputs_are_approvals"] is False
    assert payload["dashboard_and_telegram_are_authority"] is False
    assert payload["model_health"]["model_output_can_approve_trades"] is False
    assert payload["quantum_health"]["quantum_can_approve_execution"] is False
    assert payload["telegram_state"]["telegram_changes_trading_authority"] is False


def test_qsase_self_model_why_not_trading_now_and_negative_probes():
    payload = build_qsase_self_model()

    assert payload["why_not_trading_now"]["reason"]
    assert payload["why_not_trading_now"]["blocking_layer"] == "paperops"
    assert validate_negative_self_model_probes() == []
