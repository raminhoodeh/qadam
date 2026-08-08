from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_universe_contract import (
    build_universe_contract_from_inputs,
    validate_universe_contract,
)


def _inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    sources = []
    for index in range(41):
        key = "sec_edgar" if index == 0 else f"source_{index}"
        sources.append(
            {
                "source_key": key,
                "source_name": key,
                "freshness_status": "fresh" if index == 0 else "unknown",
                "provider_backed_observation": index == 0,
                "eligible_for_signal_review": index == 0,
                "supplemental_context_only": False,
                "sample_fixture": False,
                "trust_score": 0.8,
            }
        )
    instruments = []
    symbols = ["CL=F", "SI=F", "KALSHI:EVENTS", "POLYMARKET:EVENTS", "XAR"]
    symbols.extend(f"I{index}" for index in range(14))
    for symbol in symbols:
        instruments.append(
            {
                "symbol": symbol,
                "paper_route_available": symbol == "XAR",
                "backtest_gap_reason": None,
            }
        )
    history = {
        "rows": [
            {"source_key": source["source_key"], "status": "forward_only", "forward_only": True}
            for source in sources
        ]
    }
    strategy = {
        "strategies": [
            {
                "strategy_family_id": "defence_repricing_geopolitical_watch",
                "source_contribution": {"configured_sources": ["sec_edgar"]},
                "instrument_contribution": {"instruments": [{"symbol": "XAR"}]},
            }
        ]
    }
    ledger = {"submission_records": []}
    coverage = {"status": "complete"}
    return {"sources": sources}, {"instruments": instruments}, history, strategy, ledger, coverage


def test_context_symbols_never_become_alpaca_routes() -> None:
    state = build_universe_contract_from_inputs(
        *_inputs(), generated_at="2026-08-08T12:00:00+00:00"
    )
    assert validate_universe_contract(state) == []
    rows = {row["symbol"]: row for row in state["instrument_registry"]["instruments"]}
    assert rows["CL=F"]["guarded_paper_route_confirmed"] is False
    assert rows["KALSHI:EVENTS"]["route_state"] == "context_only_never_alpaca_symbol"
    assert rows["XAR"]["guarded_paper_route_confirmed"] is True
    assert state["source_contract"]["authority"] == authority_flags()


def test_sanitized_submission_proves_only_the_named_paper_route() -> None:
    inputs = list(_inputs())
    inputs[4] = {
        "submission_records": [
            {"symbol": "I0", "alpaca_paper_post_succeeded": True, "recorded_at": "now"}
        ]
    }
    state = build_universe_contract_from_inputs(*inputs, generated_at="2026-08-08T12:00:00+00:00")
    rows = {row["symbol"]: row for row in state["instrument_registry"]["instruments"]}
    assert rows["I0"]["route_state"] == "guarded_alpaca_paper_confirmed"
    assert rows["I1"]["route_state"] == "guarded_paper_route_unverified"
