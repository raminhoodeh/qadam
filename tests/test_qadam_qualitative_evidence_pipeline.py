from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_prediction_market_research import build_prediction_market_research
from orchestrator.qadam_qualitative_pattern_lab import run_qualitative_pattern_lab
from orchestrator.qadam_qualitative_strategy_bridge import build_qualitative_strategy_bridge


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(tmp_path))


def _labels() -> list[dict[str, object]]:
    return [
        {
            "label_id": f"label-{index:02d}",
            "claim_id": f"claim-{index:02d}",
            "claim_type": "supply_constraint",
            "instrument_symbol": "USO",
            "horizon": "3d",
            "decision_time": f"2025-{1 + index // 28:02d}-{1 + index % 28:02d}T12:00:00+00:00",
            "forward_return": 0.02,
            "independence_cluster": "issuer_a" if index % 2 else "issuer_b",
            "point_in_time_safe": True,
        }
        for index in range(24)
    ]


def test_qualitative_pattern_requires_mature_labels(tmp_path: Path) -> None:
    result, errors = run_qualitative_pattern_lab(_settings(tmp_path))
    assert errors == []
    assert result["summary"]["candidate_count"] == 0
    assert result["rejections"][0]["rejection_reasons"] == [
        "no_mature_point_in_time_forward_labels"
    ]


def test_qualitative_pattern_and_strategy_positive_path(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = AtomicArtifactStore(tmp_path)
    store.write_jsonl("qadam_qualitative_label_manifest.jsonl", _labels())
    result, errors = run_qualitative_pattern_lab(settings)
    assert errors == []
    assert result["summary"]["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["holdout_state"] == "passed"
    assert candidate["net_expectancy"] > 0
    assert candidate["strategy_nomination_allowed"] is True

    shutil.copy(
        ROOT / "data/runtime/qadam_strategy_evidence_map_v3.json",
        tmp_path / "qadam_strategy_evidence_map_v3.json",
    )
    store.write_jsonl("qadam_qualitative_claims.jsonl", [])
    store.write_jsonl("qadam_qualitative_claim_challenges.jsonl", [])
    bridge, bridge_errors = build_qualitative_strategy_bridge(settings)
    assert bridge_errors == []
    assert bridge["summary"]["canonical_strategy_draft_count"] == 1
    assert bridge["impacts"][0]["canonical_draft"]["hypothesis_state"] == "ready_for_akber_review"
    assert bridge["impacts"][0]["authority"]["paper_order_allowed"] is False


def test_prediction_market_research_writes_separate_truth_artifacts(
    tmp_path: Path,
) -> None:
    result, errors = build_prediction_market_research(_settings(tmp_path))
    assert errors == []
    assert result["direct_prediction_market_trade_allowed"] is False
    for name in (
        "qadam_prediction_market_paper_registry.json",
        "qadam_prediction_contracts.jsonl",
        "qadam_prediction_market_quality.json",
        "qadam_prediction_market_consistency_records.jsonl",
        "qadam_prediction_market_cross_asset_signals.jsonl",
        "qadam_prediction_market_intelligence_summary.json",
    ):
        assert (tmp_path / name).is_file()
    summary = json.loads(
        (tmp_path / "qadam_prediction_market_intelligence_summary.json").read_text()
    )
    assert summary["direct_prediction_market_trade_allowed"] is False
    assert summary["strategy_nomination_count"] == 0
