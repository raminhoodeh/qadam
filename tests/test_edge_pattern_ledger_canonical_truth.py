from __future__ import annotations

from orchestrator.edge_pattern_ledger import build_edge_pattern_ledger


def _edge_tracker() -> dict:
    sleeves = [
        {
            "key": f"sleeve-{index}",
            "label": f"Sleeve {index}",
            "watched_instruments": [{"symbol": f"TEST{index}"}],
        }
        for index in range(5)
    ]
    return {
        "source_scan": {
            "mode": "all_sources_every_sleeve",
            "total_source_count": 41,
            "signal_review_eligible_source_count": 12,
        },
        "source_universe": {"source_count": 41},
        "watched_instrument_count": 21,
        "sleeves": sleeves,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }


def test_canonical_registry_prevents_legacy_checklist_from_claiming_an_edge() -> None:
    payload = build_edge_pattern_ledger(
        edge_tracker=_edge_tracker(),
        cognition={
            "evidence_packets": [{}],
            "hypotheses": [{}],
            "strategy_lead_packets": [{}],
            "market_context": {"packet_count": 1},
            "signal_integrity": {"status": "ok"},
        },
        trade_layer={"candidates": [{}], "blocked": []},
        quantum_oracle={
            "status": "ok",
            "latest_local_simulation_mode": "qiskit_aer_local_circuit",
            "result_count": 1,
        },
        qctrl_fire_opal_ibm={"status": "device_probe_recorded"},
        canonical_edge_registry={
            "artifact_type": "qadam_edge_registry_v3",
            "generated_at": "2026-07-20T00:00:00+00:00",
            "status": "empty_no_relationship_survived_promotion",
            "validated_edge_count": 0,
        },
        canonical_quantum_evidence={
            "status": (
                "complete_matched_comparisons_and_ibm_hardware_no_proven_quantum_value"
            ),
            "hardware_used": True,
            "hardware_experiment_status": "completed",
            "comparison_count": 175,
            "quantum_value_state": "not_proven",
        },
        generated_at="2026-07-20T00:00:00+00:00",
    )

    assert payload["status"] == "candidate_edges_under_observation"
    assert payload["validated_edge_count"] == 0
    assert (
        payload["canonical_edge_registry"]["role"]
        == "sole_authority_for_validated_edge_count"
    )
    assert payload["quantum_review"]["hardware_used"] is True
    assert payload["quantum_review"]["quantum_value_state"] == "not_proven"
    market_confirmation = next(
        row for row in payload["criteria"] if row["key"] == "market_confirmation"
    )
    assert market_confirmation["passed"] is False
