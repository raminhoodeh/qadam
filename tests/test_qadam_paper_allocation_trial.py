from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import sqlite3

import pytest

from orchestrator.qadam_experimental_paper_policy import default_policy, validate_policy
from orchestrator.qadam_portfolio_risk_engine import (
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_risk_router_alignment import _discovery_setup, _portfolio, _router_setup
from orchestrator.qadam_router_v3_paperops import route_setup


def test_reviewed_trial_expands_only_sizing_not_evidence(paper_allocation_trial):
    settings, module, _approval, _snapshot, now, _ledger = paper_allocation_trial
    policy = default_portfolio_policy(now.isoformat())
    risk = policy["risk_budget"]
    assert module.trial_status(settings)["state"] == "active"
    assert risk["max_gross_notional_pct_equity"] == 0.75
    assert risk["max_position_notional_usd"] == 5000
    assert risk["max_correlated_cluster_notional_pct_equity"] == 0.20
    assert risk["max_daily_loss_pct_equity"] == 0.02
    assert risk["max_risk_per_position_pct_equity"] == 0.005
    assert risk["max_trailing_drawdown_pct_equity"] == 0.60
    experimental = default_policy(generated_at=now.isoformat())
    assert validate_policy(experimental) == []
    assert experimental["risk"]["unestimated_discovery"]["maximum_notional_usd"] == 5000
    assert experimental["discovery_micro_admission"]["minimum_fresh_support_sources"] >= 1
    assert experimental["live_capital_enabled"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "expired",
        "not_started",
        "stale",
        "wrong_account",
        "wrong_epoch",
        "live",
        "bad_duration",
        "unapproved_limits",
    ],
)
def test_bad_or_expired_approval_cannot_expand_limits(paper_allocation_trial, fault):
    settings, module, approval, snapshot, now, _ledger = paper_allocation_trial
    if fault == "expired":
        at = approval["expires_at"]
    elif fault == "not_started":
        at = (now - timedelta(days=1)).isoformat()
    else:
        at = now.isoformat()
    if fault == "stale":
        snapshot["observed_at"] = (now - timedelta(seconds=181)).isoformat()
    if fault == "wrong_account":
        snapshot["broker_account_fingerprint"] = "other"
    if fault == "wrong_epoch":
        snapshot["paper_epoch_id"] = "other"
    if fault == "live":
        snapshot["mode"] = "live"
    if fault == "bad_duration":
        approval["expires_at"] = (now + timedelta(days=8)).isoformat()
    if fault == "unapproved_limits":
        approval["risk_overrides"] = {**module.RISK_OVERRIDES, "max_gross_notional_pct_equity": 1.5}
    module.POLICY_PATH.write_text(json.dumps(approval))
    (Path(settings.runtime_dir) / "alpaca_paper_mirror.json").write_text(
        json.dumps({"status": "ok", "snapshot": snapshot})
    )
    policy = default_portfolio_policy(at)
    assert "allocation_trial" not in policy
    assert policy["risk_budget"]["max_gross_notional_pct_equity"] == 0.40
    assert policy["risk_budget"]["maximum_concurrent_discovery_micro_positions"] == 3


def test_live_settings_never_get_trial(paper_allocation_trial):
    settings, module, *_ = paper_allocation_trial
    assert module.active_trial(replace(settings, mode="live", live_capital_enabled=True)) is None


def test_unknown_expectancy_can_size_larger_without_becoming_positive_expectancy(
    paper_allocation_trial,
):
    _settings, module, _approval, _snapshot, now, _ledger = paper_allocation_trial
    policy = default_portfolio_policy(now.isoformat())
    trial = module.active_trial()
    setup = {
        **_discovery_setup(),
        "expected_net_return": None,
        "expected_return_class": "unestimated_discovery_experiment",
        "uncertainty": 0.5,
        "allocation_trial_id": trial["trial_id"],
        "allocation_trial_approval_sha256": trial["approval_sha256"],
    }
    result = evaluate_position_size(setup, _portfolio(), policy, generated_at=now.isoformat())
    proposal = result["proposal"]
    assert result["rejection"] is None
    assert 250 < proposal["proposed_notional"] <= 5000
    assert proposal["maximum_loss_at_invalidation"] <= 125
    assert proposal["expected_net_return"] is None
    assert proposal["allocation_trial_id"] == trial["trial_id"]
    assert proposal["allocation_trial_sizing_comparison"]["baseline_notional_usd"] <= 250
    assert proposal["allocation_trial_sizing_comparison"]["comparison_order_allowed"] is False
    router = {
        **_router_setup(),
        "expected_net_return": None,
        "expected_net_return_positive_after_costs": None,
        "expected_return_class": "unestimated_discovery_experiment",
        "allocation_trial_id": trial["trial_id"],
        "allocation_trial_approval_sha256": trial["approval_sha256"],
        "proposed_notional_usd": proposal["proposed_notional"],
        "maximum_loss_at_invalidation": proposal["maximum_loss_at_invalidation"],
    }
    decision = route_setup(
        router, {"experimental_paper_release_effective": True}, generated_at=now.isoformat()
    )
    assert "expected_return_confirmation_not_reached" not in decision["hold_reasons"]
    assert decision["final_state"] == "experimental_paper_review_candidate"


def test_old_strategy_cannot_get_new_sizing_without_trial_version(paper_allocation_trial):
    _s, _m, _a, _snap, now, _l = paper_allocation_trial
    result = evaluate_position_size(
        _discovery_setup(),
        _portfolio(),
        default_portfolio_policy(now.isoformat()),
        generated_at=now.isoformat(),
    )
    assert result["proposal"] is None
    assert (
        "allocation_trial_strategy_version_refresh_required"
        in result["rejection"]["rejection_reasons"]
    )


@pytest.mark.parametrize("fault", ["negative_expectancy", "missing_spread", "stale_market"])
def test_aggressive_sizing_cannot_override_missing_or_adverse_evidence(
    paper_allocation_trial, fault
):
    _settings, module, _approval, _snapshot, now, _ledger = paper_allocation_trial
    trial = module.active_trial()
    setup = {
        **_discovery_setup(),
        "uncertainty": 0.5,
        "allocation_trial_id": trial["trial_id"],
        "allocation_trial_approval_sha256": trial["approval_sha256"],
    }
    if fault == "negative_expectancy":
        setup["expected_net_return"] = -0.01
    elif fault == "missing_spread":
        setup["liquidity"]["spread_bps"] = None
    else:
        setup["market_context_fresh"] = False
    result = evaluate_position_size(
        setup, _portfolio(), default_portfolio_policy(now.isoformat()), generated_at=now.isoformat()
    )
    assert result["proposal"] is None


def test_live_alignment_probes_use_the_reviewed_trial_envelope(paper_allocation_trial):
    from orchestrator.qadam_risk_router_alignment import (
        build_risk_router_alignment_state,
        validate_risk_router_alignment,
    )

    settings, _m, _a, _s, now, _l = paper_allocation_trial
    state = build_risk_router_alignment_state(settings, generated_at=now.isoformat())
    assert validate_risk_router_alignment(state) == []


def test_trial_preserves_base_amendment_and_signal_deduplication(paper_allocation_trial):
    from orchestrator.qadam_experimental_policy_amendment import _base_amendment_risk
    from orchestrator.qadam_strategy_definition import version_hypothesis
    from orchestrator.qadam_forward_shadow import economic_signal_identity_for_hypothesis

    _s, module, _a, _snap, now, _l = paper_allocation_trial
    policy = default_policy(now.isoformat())
    assert policy["risk"]["maximum_concurrent_discovery_micro_positions"] == 16
    assert _base_amendment_risk(policy)["maximum_concurrent_discovery_micro_positions"] == 3
    trial = module.active_trial()
    hypothesis = {
        "strategy_mapping": {"strategy_family_id": "semiconductor_policy_options_asymmetry"},
        "direction_horizon": {"direction": "long", "horizon": "5d_forward"},
        "instrument_proxy_mapping": {"execution_proxy": "SMH"},
        "pattern_lineage": {"operating_date": now.date().isoformat()},
        "risk_concept": {"risk_multiplier": 0.1},
    }
    baseline = version_hypothesis(hypothesis)
    expanded = version_hypothesis(
        {
            **hypothesis,
            "risk_concept": {
                "risk_multiplier": 1.0,
                "allocation_trial_id": trial["trial_id"],
                "allocation_trial_approval_sha256": trial["approval_sha256"],
            },
        }
    )
    assert baseline["strategy_version_id"] != expanded["strategy_version_id"]
    assert economic_signal_identity_for_hypothesis(
        baseline
    ) == economic_signal_identity_for_hypothesis(expanded)


def test_existing_admission_approval_survives_reviewed_sizing_overlay(paper_allocation_trial):
    from orchestrator.qadam_experimental_policy_amendment import (
        build_policy_amendment,
        validate_policy_amendment,
    )

    _s, _module, _a, _snap, now, _l = paper_allocation_trial
    baseline = default_policy((now - timedelta(days=1)).isoformat(), include_trial=False)
    expanded = default_policy(now.isoformat())
    previous = {"policy_version": "original-admission-version"}
    approval = {
        "experimental_paper_mandate_approved": True,
        "live_capital_release": False,
        "paper_epoch_id": "test-epoch",
        "policy_version": previous["policy_version"],
    }
    epoch = {
        "paper_epoch_id": "test-epoch",
        "experimental_paper_release_policy_version": previous["policy_version"],
        "paper_growth_trial_started_at": "2026-07-19T00:00:00+00:00",
    }
    calendar = {
        "trial_started_at": epoch["paper_growth_trial_started_at"],
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
    }
    amendment = build_policy_amendment(
        previous_policy=previous,
        amended_policy=baseline,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="original-hash",
        explicit_operator_approval=True,
    )
    assert (
        validate_policy_amendment(
            amendment,
            policy=expanded,
            release_approval=approval,
            paper_epoch=epoch,
            trial_calendar=calendar,
            previous_approval_sha256="original-hash",
        )
        == []
    )
    expanded["risk"]["maximum_concurrent_discovery_micro_positions"] = 99
    assert validate_policy_amendment(
        amendment,
        policy=expanded,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="original-hash",
    )


def _budget_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE positions(instrument,quantity,current_price,state)")
    db.execute("CREATE TABLE canonical_orders(order_key,instrument,side,payload_json,state)")
    return db


def _reserve(db, i, notional):
    db.execute(
        "INSERT INTO canonical_orders VALUES (?,?,?,?,?)",
        (
            str(i),
            f"TEST{i}",
            "buy",
            json.dumps(
                {"purpose": "canonical_position_entry", "candidate": {"notional_usd": notional}}
            ),
            "prepared",
        ),
    )


def _assert_budget(fixture, db, **kwargs):
    settings, module, *_ = fixture
    trial = module.active_trial()
    module.assert_entry_budget(
        db,
        settings,
        trial_id=trial["trial_id"],
        approval_sha256=trial["approval_sha256"],
        instrument=kwargs.pop("instrument", "XAR"),
        side="buy",
        notional=kwargs.pop("notional", 5000),
        order_key="new",
        **kwargs,
    )


def test_queued_orders_reserve_capital_before_fill(paper_allocation_trial):
    with _budget_db() as db:
        for i in range(14):
            _reserve(db, i, 5000)
        _assert_budget(paper_allocation_trial, db)
        _reserve(db, 14, 5000)
        with pytest.raises(ValueError, match="gross_limit"):
            _assert_budget(paper_allocation_trial, db)


def test_position_slots_cannot_be_bypassed_with_small_orders(paper_allocation_trial):
    with _budget_db() as db:
        for i in range(16):
            _reserve(db, i, 100)
        with pytest.raises(ValueError, match="position_count_limit"):
            _assert_budget(paper_allocation_trial, db, notional=100)


def test_cash_reserve_and_cluster_caps_are_enforced(paper_allocation_trial):
    settings, module, _approval, snapshot, _now, _ledger = paper_allocation_trial
    snapshot["cash"] = 29000
    (Path(settings.runtime_dir) / "alpaca_paper_mirror.json").write_text(
        json.dumps({"status": "ok", "snapshot": snapshot})
    )
    with _budget_db() as db:
        with pytest.raises(ValueError, match="cash_reserve"):
            _assert_budget(paper_allocation_trial, db)
    snapshot["cash"] = 100000
    (Path(settings.runtime_dir) / "alpaca_paper_mirror.json").write_text(
        json.dumps({"status": "ok", "snapshot": snapshot})
    )
    with _budget_db() as db:
        db.execute("INSERT INTO positions VALUES ('SMH',35,500,'open')")
        with pytest.raises(ValueError, match="cluster_limit"):
            _assert_budget(paper_allocation_trial, db, instrument="SOXX")


def test_two_percent_daily_loss_still_blocks(paper_allocation_trial):
    settings, _module, _approval, snapshot, _now, _ledger = paper_allocation_trial
    snapshot.update(equity=98000, cash=98000)
    (Path(settings.runtime_dir) / "alpaca_paper_mirror.json").write_text(
        json.dumps({"status": "ok", "snapshot": snapshot})
    )
    with _budget_db() as db:
        with pytest.raises(ValueError, match="daily_loss_limit"):
            _assert_budget(paper_allocation_trial, db)


def test_drawdown_freeze_survives_equity_recovery_and_restart(paper_allocation_trial):
    settings, module, _approval, snapshot, _now, ledger = paper_allocation_trial
    snapshot.update(equity=40000, cash=40000)
    path = Path(settings.runtime_dir) / "alpaca_paper_mirror.json"
    path.write_text(json.dumps({"status": "ok", "snapshot": snapshot}))
    assert module.trial_status(settings)["state"] == "drawdown_breached"
    ledger._record_allocation_trial_breach()
    snapshot.update(equity=100000, cash=100000)
    path.write_text(json.dumps({"status": "ok", "snapshot": snapshot}))
    assert module.trial_status(settings)["state"] == "drawdown_frozen"
    with _budget_db() as db:
        with pytest.raises(ValueError, match="entry_hold:drawdown_frozen"):
            module.assert_entry_budget(
                db,
                settings,
                trial_id=None,
                approval_sha256=None,
                instrument="XAR",
                side="buy",
                notional=500,
                order_key="new",
            )


def test_expired_or_changed_approval_blocks_queued_trial_entry(paper_allocation_trial, monkeypatch):
    settings, module, approval, _snapshot, _now, _ledger = paper_allocation_trial
    with _budget_db() as db:
        with pytest.raises(ValueError, match="approval_changed"):
            module.assert_entry_budget(
                db,
                settings,
                trial_id=approval["trial_id"],
                approval_sha256="old",
                instrument="XAR",
                side="buy",
                notional=500,
                order_key="new",
            )
        monkeypatch.setattr(module, "_now", lambda: module._stamp(approval["expires_at"]))
        with pytest.raises(ValueError, match="trial_not_active"):
            module.assert_entry_budget(
                db,
                settings,
                trial_id=approval["trial_id"],
                approval_sha256="old",
                instrument="XAR",
                side="buy",
                notional=500,
                order_key="new",
            )
