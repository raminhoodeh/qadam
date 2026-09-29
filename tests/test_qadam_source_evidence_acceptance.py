import pytest

from orchestrator.tradingview_mcp_adapter import TRADINGVIEW_MCP_CONNECTION_STATES
from scripts.check_source_evidence_acceptance import _tradingview_contract_errors


def adapter(state="live_supplemental"):
    return {
        "tradingview_mcp_adapter_check": "ok",
        "tradingview_mcp_connection_state": state,
        "tradingview_mcp_connected": str(state == "live_supplemental"),
        "tradingview_mcp_live_calls_enabled": str(state not in {"disabled", "sample_only"}),
        "tradingview_mcp_canonical_sample_count": "0",
        **{f"tradingview_mcp_{field}": "False" for field in (
            "source_quorum_credit_allowed", "execution_allowed", "paper_order_allowed", "broker_write_allowed",
        )},
    }


@pytest.mark.parametrize("state", TRADINGVIEW_MCP_CONNECTION_STATES)
def test_truthful_read_only_adapter_states_are_accepted(state):
    assert _tradingview_contract_errors(adapter(state)) == []


@pytest.mark.parametrize("field,value", [
    ("connection_state", "unknown"), ("connected", "False"),
    ("live_calls_enabled", "False"), ("canonical_sample_count", "1"),
    ("source_quorum_credit_allowed", "True"), ("execution_allowed", "True"),
    ("paper_order_allowed", "True"), ("broker_write_allowed", "True"),
])
def test_live_state_does_not_relax_evidence_or_authority_contract(field, value):
    assert _tradingview_contract_errors({**adapter(), f"tradingview_mcp_{field}": value})


def test_missing_contract_is_rejected():
    assert _tradingview_contract_errors({})
