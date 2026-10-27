"""Small, explicit producer inputs; never borrow a running account's artifacts."""

from dataclasses import replace
import json

import pytest

from orchestrator.config import Settings
import orchestrator.qadam_edge_registry as edges
from orchestrator.qadam_wave_b_common import record_set_hash


@pytest.fixture(autouse=True)
def isolated_allocation_approval(tmp_path, monkeypatch):
    # Tests must never inherit a real account's temporary deployment approval.
    # Allocation tests explicitly install their own reviewed fixture below.
    from orchestrator import qadam_paper_allocation_trial as trial
    monkeypatch.setattr(trial, "POLICY_PATH", tmp_path / "isolated-allocation-approval.json")


@pytest.fixture
def paper_allocation_trial(tmp_path, monkeypatch, isolated_allocation_approval):
    from datetime import datetime, timedelta, timezone
    from orchestrator import qadam_paper_allocation_trial as trial
    from orchestrator.execution.ledger import OperatingLedger

    now = datetime.now(timezone.utc)
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path),
                       mode="paper", live_capital_enabled=False)
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(trial, "_now", lambda: now)
    path = tmp_path / "allocation-approval.json"
    monkeypatch.setattr(trial, "POLICY_PATH", path)
    policy = {"schema_version": trial.SCHEMA, "status": "active", "trial_id": "test-seven-day-allocation",
        "approval_source": "direct_user_request_2026-10-27", "approved_drawdown_from_start": 0.60,
        "paper_only": True, "live_capital_enabled": False,
        "starts_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now - timedelta(minutes=1) + timedelta(days=7)).isoformat(),
        "starting_equity_usd": 100000.0, "paper_epoch_id": "test-epoch",
        "broker_account_fingerprint": "sha256:test-paper-account",
        "risk_overrides": trial.RISK_OVERRIDES, "maximum_unestimated_notional_usd": 5000.0,
        "maximum_unestimated_planned_loss_usd": 125.0}
    path.write_text(json.dumps(policy))
    snapshot = {"mode": "paper", "account_currency": "USD", "equity": 100000.0, "cash": 100000.0,
        "observed_at": now.isoformat(), "paper_epoch_id": policy["paper_epoch_id"],
        "broker_account_fingerprint": policy["broker_account_fingerprint"]}
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({"status": "ok", "snapshot": snapshot}))
    (tmp_path / "paper_account_snapshots.jsonl").write_text(json.dumps(snapshot) + "\n")
    (tmp_path / "qsase_trading_universe.json").write_text(json.dumps({"instruments": [
        {"symbol": "XAR", "market_family": "defence"},
        {"symbol": "SMH", "market_family": "semiconductors"},
        {"symbol": "SOXX", "market_family": "semiconductors"},
        *[{"symbol": f"TEST{i}", "market_family": f"sector{i // 4}"} for i in range(20)],
    ]}))
    ledger = OperatingLedger(settings)
    return settings, trial, policy, snapshot, now, ledger


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
    monkeypatch.setattr(edges, "research_universe", lambda _runtime: {"all_strategy_rows": strategies})
    for name, payload in {
        edges.BACKTEST_MANIFEST_ARTIFACT: {"run_id": "fixture:rejected-run", "bulk_results": bulk, **lineage},
        edges.BACKTEST_SUMMARY_ARTIFACT: {"status": "complete_no_edge_found", "validated_edge_count": 0},
        edges.QUANTUM_SUMMARY_ARTIFACT: {"run_id": "fixture:comparison", "input_audit": lineage},
        edges.STRATEGY_UNIVERSE_ARTIFACT: {"all_strategy_rows": strategies},
    }.items():
        (runtime / name).write_text(json.dumps(payload), encoding="utf-8")
    return replace(Settings.from_env(), runtime_dir=str(runtime), data_root=str(tmp_path / "data"))
