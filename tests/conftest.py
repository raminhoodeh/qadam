"""Small, explicit producer inputs; never borrow a running account's artifacts."""

from dataclasses import replace
import json

import pytest

from orchestrator.config import Settings
import orchestrator.qadam_edge_registry as edges
from orchestrator.qadam_wave_b_common import record_set_hash


@pytest.fixture
def rejected_edge_fixture(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    research = tmp_path / "data/research/statistical_backtests"
    research.mkdir(parents=True)
    monkeypatch.setattr(edges, "ROOT", tmp_path)
    records = [
        {
            "hypothesis_id": f"fixture:hypothesis:{index}",
            "strategy_family_id": f"fixture_strategy_{index}",
            "instrument": f"TEST{index}",
            "horizon": "1d_forward",
            "method_id": "lead_lag_event_study",
            "historical_edge_candidate": False,
            "false_discovery_adjusted_state": "not_significant",
            "adjusted_p_value": 0.9,
            "rejection_reasons": ["false_discovery_adjustment_not_validated"],
            "holdout_metrics": {"trade_count": 10, "mean_net_return": -0.01},
            "independent_row_count": 10,
        }
        for index in range(4)
    ]
    bulk = {"written": True}
    for name, rows in (("result", records), ("fold", [])):
        path = research / f"{name}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        bulk.update({
            f"{name}_path": str(path.relative_to(tmp_path)),
            f"{name}_count": len(rows),
            f"{name}_record_set_hash": record_set_hash(rows),
        })
    lineage = {"score_dataset_hash": "a" * 64, "label_dataset_hash": "b" * 64}
    strategies = [
        {"strategy_family_id": f"fixture_strategy_{index}", "watched_markets": [{"symbol": f"TEST{index}"}]}
        for index in range(4)
    ] + [{"strategy_family_id": "prediction_market_geopolitical_dislocation", "watched_markets": []}]
    for name, payload in {
        edges.BACKTEST_MANIFEST_ARTIFACT: {"run_id": "fixture:rejected-run", "bulk_results": bulk, **lineage},
        edges.BACKTEST_SUMMARY_ARTIFACT: {"status": "complete_no_edge_found", "validated_edge_count": 0},
        edges.QUANTUM_SUMMARY_ARTIFACT: {"run_id": "fixture:comparison", "input_audit": lineage},
        edges.STRATEGY_UNIVERSE_ARTIFACT: {"all_strategy_rows": strategies},
    }.items():
        (runtime / name).write_text(json.dumps(payload), encoding="utf-8")
    return replace(Settings.from_env(), runtime_dir=str(runtime), data_root=str(tmp_path / "data"))
