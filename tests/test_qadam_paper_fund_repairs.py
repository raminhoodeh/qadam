from datetime import datetime, timezone
import sqlite3

import pytest

from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_service import classify_failure, retry_policy
from orchestrator.qadam_outcome_attribution import cohort_metrics, reconstruct_closed_orders
from orchestrator.qadam_storage_retention import run_storage_maintenance, validate_storage_status
from orchestrator.qadam_operating_ledger import read_operating_health
from orchestrator.qadam_strategy_definition import version_hypothesis


def order(identity, side, qty, price, hour, epoch="epoch-1"):
    return {"order_id": identity, "client_order_id": identity, "instrument": "SPY",
            "direction": side, "filled_quantity": qty, "filled_avg_price": price,
            "filled_at": f"2026-09-01T{hour}:00:00Z", "paper_epoch_id": epoch,
            "broker_account_fingerprint": "paper-account", "account_currency": "USD"}


def test_exact_close_uses_earlier_entry_not_later_same_symbol():
    values = reconstruct_closed_orders([
        order("entry-1", "buy", 2, 100, "10"), order("exit-1", "sell", 2, 105, "11"),
        order("entry-2", "buy", 2, 110, "12"), order("exit-2", "sell", 2, 108, "13"),
    ])
    assert values["exit-1"]["realized_pnl"] == 10
    assert values["exit-2"]["realized_pnl"] == -4
    assert values["exit-1"]["allocations"][0]["entry_order_id"] == "entry-1"
    assert values["exit-1"]["net_return"] is None


def test_partial_exits_and_duplicate_mirror_rows_do_not_double_count():
    entry = order("entry", "buy", 3, 100, "10")
    values = reconstruct_closed_orders([
        entry, entry, order("exit-1", "sell", 1, 110, "11"),
        order("exit-2", "sell", 2, 105, "12"),
    ])
    assert sum(row["realized_pnl"] for row in values.values()) == 20


def test_missing_history_and_cross_epoch_cannot_fabricate_zero_pnl():
    values = reconstruct_closed_orders([
        order("entry", "buy", 2, 100, "10"),
        order("exit", "sell", 2, 100, "11", epoch="different"),
    ])
    assert values["exit"]["realized_pnl"] is None
    assert values["exit"]["accounting_status"] == "missing_entry_history"


def test_repeated_economic_event_is_one_outcome_and_unknown_costs_are_excluded():
    row = {"attribution_status": "exact_entry_decision", "independent_event_id": "event-1",
           "costs_measured": True, "net_return": 0.02, "entry_notional": 100,
           "cost_bps": 5.0, "cost_measurement_source": "fixture_execution_cost_receipt",
           "strategy_version": "v1", "paper_epoch_id": "epoch", "broker_account_fingerprint": "account"}
    metrics = cohort_metrics([row, row, {**row, "independent_event_id": "event-2", "costs_measured": False}])
    assert metrics["independent_outcome_count"] == 1
    assert metrics["raw_outcome_count"] == 3
    assert metrics["benchmark_comparison_available"] is False
    assert metrics["net_expectancy"] == 0.02
    assert cohort_metrics([{}])["net_expectancy"] is None
    unproven = {**row, "cost_measurement_source": None}
    assert cohort_metrics([unproven])["independent_outcome_count"] == 0


def test_control_plane_context_releases_connection(tmp_path):
    store = ControlPlaneStore(tmp_path / "ledger.sqlite3")
    with store.connect() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_missing_database_cannot_be_reported_healthy_or_created_by_healthcheck(tmp_path):
    assert read_operating_health(tmp_path)["status"] == "degraded"
    assert not (tmp_path / "qadam-control-plane.sqlite3").exists()


def test_strategy_version_ignores_daily_score_but_changes_with_rules():
    original = {"strategy_mapping": {"strategy_family_id": "defence"},
                "direction_horizon": {"direction": "long", "horizon": "3d"},
                "pattern_lineage": {"raw_research_score": 0.6, "evidence_profile": "event"}}
    changed_score = {**original, "pattern_lineage": {**original["pattern_lineage"], "raw_research_score": 0.7}}
    assert version_hypothesis(original)["strategy_version_id"] == version_hypothesis(changed_score)["strategy_version_id"]
    changed_rule = {**original, "direction_horizon": {"direction": "short", "horizon": "3d"}}
    assert version_hypothesis(original)["strategy_version_id"] != version_hypothesis(changed_rule)["strategy_version_id"]


def test_strategy_registration_is_idempotent_and_cannot_backdate(tmp_path):
    from dataclasses import replace
    from orchestrator.config import Settings
    from orchestrator.qadam_operating_ledger import OperatingLedger
    from orchestrator.qadam_control_plane_store import ControlPlaneError
    from orchestrator.qadam_forward_tournament import forward_tournament
    ledger = OperatingLedger(replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path)))
    hypothesis = version_hypothesis({"generated_at": "2000-01-01T00:00:00Z"})
    before = datetime.now(timezone.utc)
    ledger.register_strategy_definition(hypothesis)
    ledger.register_strategy_definition(hypothesis)
    tournament, registry = forward_tournament(tmp_path, [], generated_at=datetime.now(timezone.utc).isoformat())
    assert tournament["candidate_count"] == 1
    assert datetime.fromisoformat(registry["freezes"][0]["registered_at"]) >= before
    with pytest.raises(ControlPlaneError, match="strategy_definition_version_mismatch"):
        ledger.register_strategy_definition({**hypothesis, "strategy_definition": {"different": True}})


def test_sqlite_io_is_not_disk_exhaustion():
    failure = classify_failure("sqlite3.OperationalError: disk I/O error")
    assert failure == "database_io_unavailable"
    assert retry_policy(failure)["automatic_retry_allowed"] is True
    assert retry_policy(failure)["broker_write_retry_allowed"] is False
    assert retry_policy(failure, attempt_count=3)["automatic_retry_allowed"] is False
    assert classify_failure("no space left on device") == "disk_resource_pressure"


def test_generation_backlog_does_not_falsely_report_disk_exhaustion(tmp_path, monkeypatch):
    import orchestrator.qadam_storage_retention as storage
    monkeypatch.setattr(storage, "prune_research_generations", lambda *a, **k: {})
    root = tmp_path / ".qadam_generations" / "point_in_time_evidence" / "generations"
    for i in range(5):
        (root / str(i)).mkdir(parents=True)
    status = run_storage_maintenance(tmp_path, apply=True)
    assert len(list(root.iterdir())) == 3
    assert not validate_storage_status(status)
    assert datetime.fromisoformat(status["generated_at"]) <= datetime.now(timezone.utc)


def test_exchange_holidays_and_early_close_do_not_count_as_weekdays():
    from orchestrator.qadam_exchange_calendar import calendar_phase, elapsed_sessions
    end = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)
    receipt = {"provider": "alpaca_calendar_v2", "observed_at": end.isoformat(),
               "start": "2026-09-01", "end": "2026-09-30",
               "sessions": [{"date": "2026-09-04", "open": "09:30", "close": "16:00"},
                            {"date": "2026-09-08", "open": "09:30", "close": "16:00"}]}
    assert calendar_phase(end, receipt) == "holiday"
    assert elapsed_sessions(datetime(2026, 9, 4, 15, tzinfo=timezone.utc), end, receipt) == 0
    assert elapsed_sessions(datetime(2026, 9, 4, 15, tzinfo=timezone.utc), end, {}) is None
    receipt["sessions"].append({"date": "2026-09-07", "open": "09:30", "close": "10:00"})
    assert calendar_phase(end, receipt) == "post_market"


def test_six_slot_comparison_is_budget_neutral_and_does_not_change_policy():
    from copy import deepcopy
    from orchestrator.qadam_portfolio_risk_engine import default_portfolio_policy, discovery_capacity_review
    policy = default_portfolio_policy(datetime.now(timezone.utc).isoformat())
    before = deepcopy(policy)
    result = discovery_capacity_review(policy, {"open_discovery_micro_exposure_count": 2})
    assert result["challenger_slots"] * result["challenger_per_slot_notional_usd"] == result["current_slots"] * result["current_per_slot_notional_usd"]
    assert result["policy_applied"] is False
    assert policy == before


def test_only_exact_registered_forward_learning_is_consumed_by_next_hypothesis():
    from orchestrator.qadam_strategy_foundry_v3 import apply_matched_forward_learning
    now = datetime.now(timezone.utc).isoformat()
    hypothesis = {"strategy_version_id": "v1", "evidence_class": "experimental_unvalidated",
                  "experimental_tier": "discovery_micro", "expected_edge_range": {"net_expectancy": None}}
    proposal = {"strategy_version_id": "v1", "promotion_proposal_id": "p1", "generated_at": now,
                "automatic_paper_admission_recommended": True, "risk_envelope_unchanged": True,
                "blockers": [], "forward_evaluation": {"eligible_for_emerging_review": True,
                "registered_at": now, "independent_outcome_count": 20,
                "conservative_return_bound": 0.001, "blockers": []}}
    result = apply_matched_forward_learning(hypothesis, [proposal], generated_at=now)
    assert result["expected_edge_range"]["net_expectancy"] == 0.001
    assert result["experimental_tier"] == "discovery_micro"
    assert result["applied_forward_learning"]["risk_envelope_changed"] is False
    assert hypothesis["expected_edge_range"]["net_expectancy"] is None
    assert apply_matched_forward_learning(hypothesis, [{**proposal, "strategy_version_id": "other"}], generated_at=now) == hypothesis
    negative = {**hypothesis, "expected_edge_range": {"net_expectancy": -0.01}}
    assert apply_matched_forward_learning(negative, [proposal], generated_at=now) == negative
