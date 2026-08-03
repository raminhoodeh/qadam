from __future__ import annotations

from orchestrator.paperops_paper_lifecycle_poller import (
    _candidate_errors,
    _ledger_confirms_submitted_record,
    _source_record_to_poll_candidate,
    _source_record_errors,
)
from orchestrator.qadam_operator_exploratory_sleeve import (
    CLIENT_ORDER_PREFIX,
    IDEMPOTENCY_NAMESPACE,
    build_operator_exploratory_sleeve,
)


def _market_record(symbol: str, price: float, spread_bps: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "current_price": price,
        "rolling_volatility_20d": 0.02,
        "spread_bps": spread_bps,
        "provider": "alpaca_market_data_v2",
        "provider_label": "Alpaca Market Data IEX",
        "provider_backed": True,
        "read_only_market_data": True,
        "quote_actionable": True,
        "quote_state": "fresh_regular_session_quote",
        "quote_observed_at": "2026-08-03T13:40:00+00:00",
        "volume": 1000,
        "volume_ratio": 0.25,
    }


def _context() -> dict[str, object]:
    return {
        "recent_packets": [
            {
                "price_volume_context": {
                    "records": [
                        _market_record("SLV", 50.0, 4.0),
                        _market_record("XAR", 250.0, 20.0),
                        _market_record("USO", 120.0, 600.0),
                        _market_record("XLE", 60.0, 3.0),
                        _market_record("SMH", 500.0, 10.0),
                        _market_record("SPY", 750.0, 2.0),
                    ]
                }
            }
        ]
    }


def _requests() -> list[dict[str, object]]:
    return [
        {
            "exposure": "silver",
            "requested_symbol": "SLV",
            "approved_execution_proxies": [],
            "side": "buy",
            "allocation_usd": 1500.0,
        },
        {
            "exposure": "defence",
            "requested_symbol": "XAR",
            "approved_execution_proxies": [],
            "side": "buy",
            "allocation_usd": 1250.0,
        },
        {
            "exposure": "energy",
            "requested_symbol": "USO",
            "approved_execution_proxies": ["XLE"],
            "side": "buy",
            "allocation_usd": 1000.0,
        },
        {
            "exposure": "semiconductors",
            "requested_symbol": "SMH",
            "approved_execution_proxies": [],
            "side": "buy",
            "allocation_usd": 750.0,
        },
        {
            "exposure": "equity_hedge",
            "requested_symbol": "SPY",
            "approved_execution_proxies": [],
            "side": "sell",
            "allocation_usd": 500.0,
        },
    ]


def test_builds_five_leg_bracket_basket_with_liquid_energy_proxy() -> None:
    sleeve = build_operator_exploratory_sleeve(
        request_id="operator-test",
        requested_legs=_requests(),
        market_context_packet=_context(),
        explicit_operator_approval=True,
        generated_at="2026-08-03T13:40:30+00:00",
    )

    assert sleeve["status"] == "ready_for_guarded_paper_submission"
    assert sleeve["leg_count"] == 5
    assert sleeve["gross_notional_usd"] <= 5000.0
    assert sleeve["validation_errors"] == []
    assert [leg["execution_symbol"] for leg in sleeve["legs"]] == [
        "SLV",
        "XAR",
        "XLE",
        "SMH",
        "SPY",
    ]
    assert sleeve["legs"][2]["approved_proxy_used"] is True
    assert sleeve["legs"][4]["quantity"] == 1
    assert all(leg["order_request"]["order_class"] == "bracket" for leg in sleeve["legs"])
    assert all(leg["proof_credit_allowed"] is False for leg in sleeve["legs"])


def test_missing_explicit_operator_approval_fails_closed() -> None:
    sleeve = build_operator_exploratory_sleeve(
        request_id="operator-test",
        requested_legs=_requests(),
        market_context_packet=_context(),
        explicit_operator_approval=False,
        generated_at="2026-08-03T13:40:30+00:00",
    )

    assert sleeve["status"] == "blocked"
    assert "operator_sleeve_explicit_approval_missing" in sleeve["validation_errors"]


def test_lifecycle_accepts_durable_operator_sleeve_identity_without_proof() -> None:
    client_order_id = CLIENT_ORDER_PREFIX + "a" * 24
    record = {
        "status": "submitted_to_alpaca_paper",
        "alpaca_paper_post_succeeded": True,
        "idempotency_namespace": IDEMPOTENCY_NAMESPACE,
        "idempotency_key": client_order_id,
        "client_order_id": client_order_id,
        "source_idempotency_key": client_order_id,
        "evidence_class": "operator_exploratory_unvalidated",
        "proof_credit_allowed": False,
        "request_preview": {
            "method": "POST",
            "path": "/v2/orders",
            "symbol": "SLV",
            "side": "buy",
            "qty": "1",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": client_order_id,
            "base_url_exposed": False,
            "authorization_header_included": False,
            "raw_payload_exposed": False,
            "broker_identifier_exposed": False,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
        },
        "broker_receipt": {
            "broker_order_id_hash": "b" * 64,
            "broker_order_status": "accepted",
            "broker_order_identifier_exposed": False,
            "raw_broker_payload_stored": False,
            "raw_broker_payload_exposed": False,
            "authorization_header_exposed": False,
            "base_url_exposed": False,
            "secret_value_exposed": False,
        },
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
        "previously_submitted_to_alpaca_paper": True,
    }

    assert _source_record_errors(record) == []
    assert _ledger_confirms_submitted_record(
        record,
        submitted_client_order_ids={client_order_id},
        submitted_source_idempotency_keys={client_order_id},
    )

    record["source_record_origin"] = "paperops_2_durable_submission_identity"
    record["ledger_confirmed_submitted_paper_order"] = True
    candidate = _source_record_to_poll_candidate(record)
    assert candidate["eligible_for_lifecycle_poll"] is True
    assert candidate["proof_credit_allowed"] is False
    assert _candidate_errors(candidate) == []


def test_lifecycle_accepts_ledger_confirmed_durable_canonical_identity() -> None:
    client_order_id = "q7-6-stage-" + "a" * 24
    candidate = {
        "eligible_for_lifecycle_poll": True,
        "idempotency_namespace": "phase7_demo_proof",
        "client_order_id": client_order_id,
        "broker_order_id_hash": "b" * 64,
        "ledger_confirmed_submitted_paper_order": True,
        "source_record_origin": "paperops_2_durable_submission_identity",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "authorization_header_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }

    assert _candidate_errors(candidate) == []
