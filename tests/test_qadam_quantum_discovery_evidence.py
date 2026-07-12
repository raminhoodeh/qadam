from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_quantum_discovery_evidence import (
    ZERO_AUTHORITY_FIELDS,
    build_chronological_split,
    build_point_in_time_feature,
    build_point_in_time_foundation,
    immutable_content_hash,
    validate_chronological_split,
    validate_point_in_time_feature,
    validate_point_in_time_foundation,
)


def _feature(index: int = 0):
    cutoff = datetime(2025, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=index)
    return build_point_in_time_feature(
        provider="provider-test",
        source_key="source-test",
        source_artifact_ref=f"research://source-test/{index}",
        raw_content={"event": index, "reading": index / 10},
        event_time=(cutoff - timedelta(hours=3)).isoformat(),
        publication_time=(cutoff - timedelta(hours=2)).isoformat(),
        ingestion_time=(cutoff - timedelta(hours=1)).isoformat(),
        source_vintage=(cutoff - timedelta(hours=2)).isoformat(),
        market_symbol="BNO",
        market_timestamp=(cutoff - timedelta(minutes=30)).isoformat(),
        as_of=cutoff.isoformat(),
        feature_name="route_stress",
        feature_value=index / 10,
        parser_version="parser-test.v1",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_point_in_time_feature_is_deterministic_label_blind_and_public_safe():
    first = _feature().to_dict()
    second = _feature().to_dict()

    assert first == second
    assert first["available_at"] == first["ingestion_time"]
    assert len(first["source_artifact_hash"]) == 64
    assert "raw_content" not in first
    assert first["future_labels_present"] is False
    assert first["proof_eligible"] is False
    assert validate_point_in_time_feature(first) == []
    assert all(first["authority"][field] is False for field in ZERO_AUTHORITY_FIELDS)
    assert immutable_content_hash(b"raw-provider-payload") == immutable_content_hash(
        b"raw-provider-payload"
    )


def test_point_in_time_feature_rejects_future_labels_and_revised_future_data():
    kwargs = {
        "provider": "provider-test",
        "source_key": "source-test",
        "source_artifact_ref": "research://source-test/event",
        "event_time": "2025-01-01T09:00:00+00:00",
        "publication_time": "2025-01-01T10:00:00+00:00",
        "ingestion_time": "2025-01-01T11:00:00+00:00",
        "source_vintage": "2025-01-01T10:00:00+00:00",
        "market_symbol": "BNO",
        "market_timestamp": "2025-01-01T11:30:00+00:00",
        "as_of": "2025-01-01T12:00:00+00:00",
        "feature_name": "route_stress",
        "feature_value": 0.5,
        "parser_version": "parser-test.v1",
    }
    with pytest.raises(ValueError, match="future_label_key"):
        build_point_in_time_feature(raw_content={"future_return": 0.2}, **kwargs)
    with pytest.raises(ValueError, match="source_vintage_after_cutoff"):
        build_point_in_time_feature(
            raw_content={"reading": 0.5},
            **{**kwargs, "source_vintage": "2025-01-02T12:00:00+00:00"},
        )


def test_missing_feature_requires_a_typed_reason():
    feature = _feature().to_dict()
    feature["feature_value"] = None
    feature["missingness_reason"] = None
    assert "missing_feature_requires_reason" in validate_point_in_time_feature(feature)


def test_chronological_split_is_deterministic_purged_embargoed_and_disjoint():
    records = [_feature(index).to_dict() for index in range(20)]
    first = build_chronological_split(
        records,
        outcome_window_seconds=86_400,
        embargo_seconds=86_400,
    )
    second = build_chronological_split(
        list(reversed(records)),
        outcome_window_seconds=86_400,
        embargo_seconds=86_400,
    )

    assert first == second
    assert first["purge_applied"] is True
    assert first["embargo_applied"] is True
    assert first["partition_counts"]["train"] > 0
    assert first["partition_counts"]["validation"] > 0
    assert first["partition_counts"]["untouched_holdout"] > 0
    assert validate_chronological_split(first) == []


def test_split_rejects_authority_escalation():
    split = build_chronological_split(
        [_feature(index).to_dict() for index in range(20)],
        outcome_window_seconds=86_400,
        embargo_seconds=86_400,
    )
    split["authority"]["paper_order_allowed"] = True
    assert "split_authority_escalated:paper_order_allowed" in validate_chronological_split(
        split
    )


def test_runtime_foundation_reports_real_provider_history_gap(tmp_path: Path):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    _write_json(
        tmp_path / "qadam_point_in_time_alignment_summary.json",
        {
            "status": "alignment_ready_evidence_maturing",
            "relationship_count": 779,
            "classified_window_count": 6232,
            "eligible_forward_score_input_count": 0,
            "leakage_violation_count": 0,
        },
    )
    _write_json(
        tmp_path / "qadam_leakage_audit_v2.json",
        {
            "status": "passed_zero_eligible_leakage",
            "input_record_count": 6232,
            "leakage_violation_count": 0,
            "forward_label_requires_outcome_available_strictly_after_decision": True,
        },
    )
    _write_json(
        tmp_path / "qadam_backfill_coverage.json",
        {
            "status": "evidence_maturing",
            "total_partition_count": 450,
            "completed_partition_count": 0,
            "remaining_partition_count": 429,
            "provider_row_count": 0,
            "provider_history_certified_complete": False,
        },
    )
    _write_json(
        tmp_path / "qadam_source_backfill_manifest.json",
        {"status": "planned_with_provider_validation_gaps", "jobs": []},
    )
    _write_json(
        tmp_path / "qadam_price_backfill_manifest.json",
        {"status": "ready_for_explicit_provider_run", "jobs": []},
    )

    foundation = build_point_in_time_foundation(settings)

    assert foundation["implementation_contract_ready"] is True
    assert foundation["empirical_evidence_ready"] is False
    assert "no_eligible_point_in_time_windows" in foundation["blockers"]
    assert "provider_backfill_has_no_rows" in foundation["blockers"]
    assert foundation["invented_evidence_count"] == 0
    assert validate_point_in_time_foundation(foundation) == []
