from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_visibility import build_qualitative_visibility


def _settings(tmp_path: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(tmp_path))


def _write_inputs(tmp_path: Path) -> None:
    store = AtomicArtifactStore(tmp_path)
    store.write_json(
        "qadam_external_acquisition_status.json",
        {"document_count": 66},
    )
    store.write_json(
        "qadam_external_evidence_provenance_audit.json",
        {"research_eligible_count": 64},
    )
    store.write_json(
        "qadam_qualitative_claim_summary.json",
        {"accepted_claim_count": 2},
    )
    store.write_json(
        "qadam_qualitative_graph_summary.json",
        {
            "record_type_counts": {
                "affects": 7,
                "derived_from": 2,
                "maps_to_strategy": 3,
                "mentions": 2,
                "published_by": 66,
            }
        },
    )
    store.write_json(
        "qadam_qualitative_forward_window_status.json",
        {"pending_window_count": 7},
    )
    store.write_json(
        "qadam_qualitative_backtest_summary.json",
        {"label_count": 0, "candidate_count": 0},
    )
    store.write_json(
        "qadam_prediction_market_research.json",
        {
            "contract_count": 491,
            "disagreement_record_count": 30,
            "liquidity_qualified_disagreement_count": 0,
        },
    )
    store.write_json(
        "qadam_lane_conversion_funnel.json",
        {"contribution_count": 3, "a4_nomination_count": 1},
    )
    store.write_json(
        "qadam_qualitative_paper_eligibility.json",
        {"paper_review_eligible_count": 0},
    )
    store.write_jsonl(
        "qadam_router_v3_decisions.jsonl",
        [{"final_state": "hold"}],
    )


def test_qualitative_visibility_uses_canonical_producer_fields_and_dedupes(
    tmp_path: Path,
) -> None:
    _write_inputs(tmp_path)
    settings = _settings(tmp_path)

    first, first_errors = build_qualitative_visibility(settings)
    assert first_errors == []
    assert first["dashboard"]["research_eligible_document_count"] == 64
    assert first["dashboard"]["graph_relationship_count"] == 80
    assert first["dashboard"]["prediction_disagreement_count"] == 30
    assert first["communications"]["status"] == "material_update_candidate"
    assert first["communications"]["live_send_allowed"] is False

    second, second_errors = build_qualitative_visibility(settings)
    assert second_errors == []
    assert second["communications"]["status"] == "quiet_no_material_change"
    assert second["communications"]["message_candidate"] is None
