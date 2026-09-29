from dataclasses import replace
from types import SimpleNamespace

import pytest

from orchestrator.config import Settings
from orchestrator.paper_portfolio_accounting import (
    accounting_snapshot_health,
    cash_position_reconciliation,
    equity_history_metrics,
)
from orchestrator.paper_account import (
    AlpacaReadOnlyPaperMirror, PaperAccountMirrorStore, initial_paper_account_snapshot,
)
from orchestrator.qadam_portfolio_risk_engine import (
    _current_portfolio_state, default_portfolio_policy, evaluate_position_size,
)
from orchestrator.qadam_reliability_critic import classify_reliability_snapshot, plan_safe_repairs
from tests.test_qadam_reliability_critic import _healthy_snapshot
from tests.test_qadam_portfolio_risk_engine import NOW, _portfolio, _setup


def row(equity, day=1, **kw):
    return {
        "equity_gbp": equity, "starting_balance_gbp": 100_000,
        "peak_equity_gbp": equity, "drawdown_pct": 0, "max_drawdown_pct": 0,
        "observed_at": f"2026-09-{day:02d}T15:00:00+00:00",
        "paper_epoch_id": "epoch", "broker_account_fingerprint": "account",
        "account_currency": "USD", "record_origin": "broker_mirror", **kw,
    }


def test_peak_survives_decline_and_recovery_above_initial_balance():
    rows = [row(100_000), row(120_000, 2), row(105_000, 3), row(110_000, 4)]
    result = equity_history_metrics(rows, rows[-1])
    assert result["peak_equity"] == 120_000
    assert result["drawdown_pct"] == pytest.approx(8.333333)
    assert result["max_drawdown_pct"] == 12.5


def test_persisted_peak_and_maximum_survive_compaction_and_restart():
    latest = row(110_000, peak_equity_gbp=120_000, max_drawdown_pct=12.5)
    result = equity_history_metrics([latest], latest)
    assert result["peak_equity"] == 120_000
    assert result["max_drawdown_pct"] == 12.5


@pytest.mark.parametrize("identity,value", [
    ("paper_epoch_id", "archived"), ("broker_account_fingerprint", "other"),
    ("account_currency", "GBP"), ("record_origin", "synthetic"),
    ("observed_at", "2099-01-01T00:00:00Z"),
])
def test_foreign_or_future_history_cannot_poison_peak(identity, value):
    latest = row(100_010, 2)
    result = equity_history_metrics([row(900_000, **{identity: value}), latest], latest)
    assert result["peak_equity"] == 100_010
    assert result["drawdown_pct"] == 0


def test_first_snapshot_below_baseline_and_zero_equity():
    assert equity_history_metrics([], row(90_000))["drawdown_pct"] == 10
    assert equity_history_metrics([], row(0))["drawdown_pct"] == 100


def test_nonfinite_history_is_not_silently_healthy():
    with pytest.raises(ValueError, match="history_equity_invalid"):
        equity_history_metrics([row(float("nan"))], row(100_000, 2))


def test_short_reconciliation_discloses_small_difference():
    result = cash_position_reconciliation(
        {"equity": 100131.17, "cash": 103101.93},
        [{"direction": "short", "market_value": 2970.89}],
    )
    assert result["signed_position_value"] == -2970.89
    assert result["unreconciled_difference"] == 0.13
    assert result["status"] == "within_mark_tolerance"


def test_cash_long_short_and_borrowing_reconcile():
    assert cash_position_reconciliation({"equity": 100, "cash": 100}, [])["status"] == "matched"
    assert cash_position_reconciliation({"equity": 100, "cash": -50}, [{"market_value": 150}])["status"] == "matched"
    assert cash_position_reconciliation({"equity": 100, "cash": 100}, [{"market_value": 30}, {"market_value": -30}])["status"] == "matched"
    assert cash_position_reconciliation({"equity": 100, "cash": 90}, [])["status"] == "mismatch"
    assert cash_position_reconciliation({"equity": 100}, [])["status"] == "unavailable"


def test_risk_engine_does_not_trust_old_current_only_peak():
    history = [row(120_000), row(105_000, 2)]
    result = _current_portfolio_state({"rows": []}, history, [], {}, generated_at=history[-1]["observed_at"])
    assert result["trailing_drawdown_pct"] == 0.125
    result = evaluate_position_size(_setup(), result, default_portfolio_policy(NOW), generated_at=NOW)
    assert result["proposal"] is None
    assert "trailing_drawdown_gate_breached" in result["rejection"]["rejection_reasons"]


@pytest.mark.parametrize("status,blocked", [("mismatch", True), ("unavailable", True), ("within_mark_tolerance", False), ("matched", False)])
def test_risk_rejects_material_mismatch_but_not_disclosed_small_difference(status, blocked):
    portfolio = {**_portfolio(), "cash_position_reconciliation_status": status}
    result = evaluate_position_size(_setup(), portfolio, default_portfolio_policy(NOW), generated_at=NOW)
    assert (result["proposal"] is None) == blocked
    if blocked:
        assert "broker_cash_position_reconciliation_failed" in result["rejection"]["rejection_reasons"]


def test_health_recomputes_reconciliation_arithmetic():
    reference = row(100_000, cash_gbp=103_000)
    reconciliation = cash_position_reconciliation(reference, [{"market_value": -3000}])
    reference["portfolio_accounting"] = {"cash_position_reconciliation": reconciliation}
    assert accounting_snapshot_health([], reference)["healthy"]
    reconciliation["cash_plus_positions"] = 100_050
    assert "cash_position_reconciliation_arithmetic_mismatch" in accounting_snapshot_health([], reference)["errors"]


def test_health_rejects_current_only_peak_and_critic_requests_bounded_refresh():
    history = [row(120_000), row(105_000, 2)]
    health = accounting_snapshot_health(history, history[-1])
    assert not health["healthy"]
    assert "historical_peak_equity_mismatch" in health["errors"]
    snapshot = _healthy_snapshot()
    snapshot["portfolio_accounting"] = health
    classification = classify_reliability_snapshot(snapshot)
    assert not classification["healthy"]
    actions = plan_safe_repairs(snapshot, classification)
    assert any("paper_lifecycle_poll" in action.get("service_ids", []) for action in actions)


def test_sync_persists_historical_metrics_with_existing_store(tmp_path, monkeypatch):
    import orchestrator.paper_account as account_module

    settings = replace(Settings.from_env(), runtime_dir=tmp_path)
    account = {"id": "paper-account", "equity": "110000", "cash": "110000", "currency": "USD"}
    epoch = {"paper_epoch_id": "epoch", "starting_balance": 100_000, "account_currency": "USD"}
    monkeypatch.setattr(account_module, "read_current_epoch", lambda _: epoch)
    monkeypatch.setattr(account_module, "_now", lambda: "2026-09-03T15:00:00+00:00")
    store = PaperAccountMirrorStore(settings=settings)
    initial = initial_paper_account_snapshot(settings)
    previous = replace(initial, observed_at="2026-09-02T15:00:00+00:00", equity_gbp=120_000,
                       equity=120_000, current_balance_gbp=120_000, current_balance=120_000,
                       peak_equity=120_000, peak_equity_gbp=120_000,
                       record_origin="broker_mirror",
                       broker_account_fingerprint=account_module.broker_account_fingerprint(account))
    store.write_snapshot(previous, log_event=False)
    mirror = AlpacaReadOnlyPaperMirror(settings=settings, store=store, event_log=SimpleNamespace(write=lambda *a, **kw: None))
    monkeypatch.setattr(mirror, "fetch", lambda: {"account": account, "positions": [], "orders": [], "clock": {}, "portfolio_history": {}})
    mirror.sync()
    latest = store.latest_snapshot()
    assert latest.peak_equity == 120_000
    assert latest.drawdown_pct == pytest.approx(8.333333)
    assert latest.max_drawdown_pct == pytest.approx(8.333333)
    assert latest.portfolio_accounting["cash_position_reconciliation"]["status"] == "matched"
    assert accounting_snapshot_health([r.to_dict() for r in store.read_snapshots()], latest.to_dict())["healthy"]


def test_material_pair_difference_retries_once_and_preserves_discrepancy(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    monkeypatch.setattr(mirror, "_fetch_order_history", lambda: ([], {}))
    monkeypatch.setattr(mirror, "_calendar_receipt", lambda: {})
    calls = []

    def get(path, **kw):
        calls.append(path)
        return {"/account": {"equity": "100000", "cash": "101000"}, "/positions": []}.get(path, {})

    monkeypatch.setattr(mirror, "_get", get)
    payload = mirror.fetch()
    assert calls.count("/account") == calls.count("/positions") == 2
    assert payload["accounting_pair_retried"] is True
    assert cash_position_reconciliation(payload["account"], payload["positions"])["status"] == "mismatch"
