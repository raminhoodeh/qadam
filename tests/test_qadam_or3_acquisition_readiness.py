from __future__ import annotations

import json

from orchestrator.qadam_dynamic_plan import PHASE_DEPENDENCIES, PHASE_ORDER
from orchestrator.qadam_or3_acquisition_readiness import (
    ALLOWED_MATRIX_STATES,
    _parse_fred,
    _parse_usgs,
    _parse_yahoo,
    build_pilot_manifest,
    build_provider_terms_review,
    build_purchase_matrix,
    build_source_matrix,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def test_or2r_is_a_mandatory_phase_between_or2_and_or3() -> None:
    assert PHASE_ORDER.index("OR-2") < PHASE_ORDER.index("OR-2R") < PHASE_ORDER.index("OR-3")
    assert PHASE_DEPENDENCIES["OR-2R"] == ["OR-2"]
    assert PHASE_DEPENDENCIES["OR-3"] == ["OR-2R"]


def test_or2r_matrices_cover_the_whole_declared_universe() -> None:
    purchase = build_purchase_matrix()
    sources = build_source_matrix()
    assert purchase["instrument_count"] == 19
    assert len({row["symbol"] for row in purchase["rows"]}) == 19
    assert sources["source_count"] == 41
    assert len({row["source_key"] for row in sources["rows"]}) == 41
    for matrix in (purchase, sources):
        for row in matrix["rows"]:
            assert row["status"] in ALLOWED_MATRIX_STATES
            assert row["system_review_complete"] is True
            assert row["purchase_performed"] is False
            assert row["terms_accepted_by_automation"] is False
            assert row["authority"] == authority_flags()


def test_provider_terms_review_is_complete_and_fail_closed() -> None:
    review = build_provider_terms_review()
    assert review["source_count"] == 41
    assert sum(review["classification_counts"].values()) == 41
    assert set(review["classification_counts"]) == {
        "historical_approved",
        "forward_only",
        "excluded",
    }
    by_key = {row["source_key"]: row for row in review["sources"]}
    assert by_key["fred"]["classification"] == "excluded"
    assert by_key["stock_act"]["classification"] == "historical_approved"
    assert "non-commercial" in by_key["stock_act"]["licensing_summary"]
    assert review["future_commercial_relicense_required"] is True


def test_prediction_market_credentials_are_described_truthfully() -> None:
    purchase = build_purchase_matrix()
    by_symbol = {row["symbol"]: row for row in purchase["rows"]}
    assert "direct Kalshi keypair not verified" in by_symbol["KALSHI:EVENTS"]["credential_class"]
    assert "no API key required" in by_symbol["POLYMARKET:EVENTS"]["credential_class"]
    assert by_symbol["CL=F"]["operator_approval_complete"] is True
    assert by_symbol["SI=F"]["operator_approval_complete"] is True
    assert by_symbol["CL=F"]["databento_quote_usd"] == 10.27749488
    assert by_symbol["SI=F"]["download_authorized"] is True


def test_pilot_manifest_spans_two_source_categories_and_market_families() -> None:
    manifest = build_pilot_manifest()
    source_jobs = [job for job in manifest["jobs"] if job["record_path"] == "source_event"]
    price_jobs = [job for job in manifest["jobs"] if job["record_path"] == "price_bar"]
    assert len({job["source_category"] for job in source_jobs}) >= 2
    assert len({job["market_family"] for job in price_jobs}) >= 2
    assert manifest["fixture_fallback_allowed"] is False
    assert all(job["evidence_eligible"] is False for job in manifest["jobs"])


def test_pilot_parsers_preserve_event_and_availability_time_without_evidence_credit() -> None:
    metadata = {"retrieved_at": "2026-07-17T00:00:00+00:00"}
    fred = _parse_fred(
        b"observation_date,DGS10\n2024-01-02,3.95\n",
        metadata,
        {"dataset": "DGS10"},
    )
    usgs_payload = {
        "features": [
            {
                "id": "event-1",
                "properties": {
                    "time": 1704067200000,
                    "updated": 1704067260000,
                    "mag": 6.1,
                    "place": "Test place",
                },
            }
        ]
    }
    usgs = _parse_usgs([json.dumps(usgs_payload).encode("utf-8")], metadata)
    yahoo_payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [1704205800],
                    "indicators": {
                        "quote": [
                            {
                                "open": [70.0],
                                "high": [71.0],
                                "low": [69.0],
                                "close": [70.5],
                                "volume": [100],
                            }
                        ],
                        "adjclose": [{"adjclose": [70.5]}],
                    },
                }
            ],
        }
    }
    yahoo = _parse_yahoo(
        json.dumps(yahoo_payload).encode("utf-8"),
        metadata,
        {"instrument": "USO", "market_family": "crude_oil", "provider": "yahoo"},
    )
    for row in [*fred, *usgs, *yahoo]:
        assert row["observed_at"] <= row["available_at"]
        assert row["evidence_eligible"] is False
        assert row["proof_eligible"] is False
