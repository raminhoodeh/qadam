from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from orchestrator.config import Settings
import orchestrator.qadam_trade_delivery as module

NOW = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(
        module, "secret_value", lambda key, _: "bot" if key == "TELEGRAM_BOT_TOKEN" else "group"
    )
    settings = replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
        telegram_trade_group_notifications_enabled=True,
        telegram_trade_group_notifications_dry_run=False,
    )
    (tmp_path / "alpaca_paper_mirror.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "snapshot": {
                    "observed_at": NOW.isoformat(),
                    "paper_epoch_id": "epoch",
                    "mode": "paper",
                    "account_currency": "USD",
                },
            }
        )
    )
    order = {
        "paper_epoch_id": "epoch",
        "record_origin": "broker_mirror",
        "status": "filled",
        "filled_at": (NOW - timedelta(minutes=5)).isoformat(),
        "instrument": "NVDA",
        "broker_order_id_hash": "hash",
        "filled_quantity": 13,
        "filled_avg_price": 229.966923,
        "account_currency": "USD",
        "position_intent": "sell_to_open",
    }
    (tmp_path / "paper_orders.jsonl").write_text(json.dumps(order) + "\n")
    (tmp_path / "qadam_operator_service_status.json").write_text(
        json.dumps({"generated_at": NOW.isoformat(), "operational_ready": True, "services": []})
    )
    (tmp_path / "qadam_hedge_fund_team_health.json").write_text(
        json.dumps({"generated_at": NOW.isoformat(), "status": "passed"})
    )
    return settings, tmp_path


def sent(*_):
    return {"ok": True, "result": {"message_id": 123, "chat": {"id": "group"}}}


def test_fill_sent_once_after_restart_correct_currency_and_short(setup):
    settings, path = setup
    messages = []

    def sender(*args):
        messages.append(args[-1])
        return sent()

    first = module.run_trade_delivery(settings, now=NOW, sender=sender)
    second = module.run_trade_delivery(settings, now=NOW + timedelta(seconds=30), sender=sender)
    assert first["status"] == second["status"] == "healthy"
    assert len(messages) == 1
    assert "opened a short, 13 NVDA at USD 229.97" in messages[0]
    assert "GBP" not in messages[0]
    assert first["broker_write_count"] == 0
    with sqlite3.connect(path / module.DB_ARTIFACT) as db:
        assert db.execute("SELECT message_id FROM deliveries").fetchone()[0] == 123


@pytest.mark.parametrize(
    "response", [{"ok": True}, {"ok": True, "result": {"message_id": 1, "chat": {"id": "wrong"}}}]
)
def test_incomplete_or_wrong_destination_receipt_not_success(setup, response):
    settings, _ = setup
    report = module.run_trade_delivery(settings, now=NOW, sender=lambda *_: response)
    assert report["status"] == "needs_attention"
    assert report["delivery_counts"]["uncertain"] == 1


def test_timeout_and_interrupted_send_never_blindly_duplicate(setup):
    settings, path = setup
    calls = []

    def timeout(*_):
        calls.append(1)
        raise TimeoutError("may already have delivered")

    module.run_trade_delivery(settings, now=NOW, sender=timeout)
    report = module.run_trade_delivery(settings, now=NOW + timedelta(seconds=60), sender=timeout)
    assert len(calls) == 1
    assert report["delivery_counts"]["uncertain"] == 1
    with sqlite3.connect(path / module.DB_ARTIFACT) as db:
        db.execute("UPDATE deliveries SET state='sending'")
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=90), sender=timeout)
    assert len(calls) == 1


def test_rate_limit_backoff_recovers_without_recreating_event(setup):
    settings, _ = setup
    calls = []

    def sender(*_):
        calls.append(1)
        return (
            {"ok": False, "error_code": 429, "parameters": {"retry_after": 120}}
            if len(calls) == 1
            else sent()
        )

    assert (
        module.run_trade_delivery(settings, now=NOW, sender=sender)["delivery_counts"]["retry"] == 1
    )
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=30), sender=sender)
    assert len(calls) == 1
    assert (
        module.run_trade_delivery(settings, now=NOW + timedelta(seconds=120), sender=sender)[
            "status"
        ]
        == "healthy"
    )
    assert len(calls) == 2


def test_old_epoch_or_archived_fill_not_replayed(setup):
    settings, path = setup
    order = json.loads((path / "paper_orders.jsonl").read_text())
    order["paper_epoch_id"] = "old"
    (path / "paper_orders.jsonl").write_text(json.dumps(order))
    assert module.run_trade_delivery(settings, now=NOW, sender=sent)["delivery_counts"] == {}


def test_health_degradation_and_recovery_are_sustained_and_deduplicated(setup):
    settings, path = setup
    messages = []

    def sender(*args):
        messages.append(args[-1])
        return sent()

    status = {
        "generated_at": NOW.isoformat(),
        "operational_ready": False,
        "services": [
            {"service_id": "active_discovery_trial", "circuit_breaker": {"state": "open"}}
        ],
    }
    (path / "qadam_operator_service_status.json").write_text(json.dumps(status))
    module.run_trade_delivery(settings, now=NOW, sender=sender)
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=120), sender=sender)
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=150), sender=sender)
    assert sum("needs attention" in text for text in messages) == 1
    status.update(
        operational_ready=True, services=[], generated_at=(NOW + timedelta(seconds=180)).isoformat()
    )
    (path / "qadam_operator_service_status.json").write_text(json.dumps(status))
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=180), sender=sender)
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=300), sender=sender)
    assert sum("checks recovered" in text for text in messages) == 1


@pytest.mark.parametrize("fault", [None, "other_role", "provider", "pipeline", "validation"])
def test_intentional_frontier_hold_is_advisory_only_when_independent_work_is_healthy(setup, fault):
    _settings, path = setup
    team = {"generated_at": NOW.isoformat(), "status": "degraded",
        "required_role_count": 4, "healthy_required_role_count": 3,
        "validation_error_count": 0,
        "blockers": ["team_role_degraded:frontier_strategy_lead"],
        "team": {role: {"status": "healthy_work_verified"} for role in (
            "python_coo", "local_research_analyst", "head_of_quant")},
        "trading_pipeline": {"status": "healthy", "stage_count": 10, "healthy_stage_count": 10}}
    team["team"]["frontier_strategy_lead"] = {"status": "degraded", "operator_action_required": True,
                                               "provider_status": "account_held"}
    if fault == "other_role":
        team["team"]["local_research_analyst"]["status"] = "failed"
    elif fault == "provider":
        team["team"]["frontier_strategy_lead"]["provider_status"] = "unexpected_failure"
    elif fault == "pipeline":
        team["trading_pipeline"]["status"] = "degraded"
    elif fault == "validation":
        team["validation_error_count"] = 1
    (path / "qadam_hedge_fund_team_health.json").write_text(json.dumps(team))
    with module._connect(path / module.DB_ARTIFACT) as db:
        module._set_meta(db, "health_notified", "prior_failure")
        module._collect_health(db, path, NOW)
        module._collect_health(db, path, NOW + timedelta(seconds=120))
        body = db.execute("SELECT body FROM deliveries WHERE kind='service_health'").fetchone()[0]
        if fault:
            assert "needs attention" in body
        else:
            assert "checks recovered" in body
            assert "Gemini remains intentionally account-held" in body


def test_monitor_cannot_call_itself_healthy_when_stale(setup):
    settings, path = setup
    module.run_trade_delivery(settings, now=NOW, sender=sent)
    assert module.trade_delivery_health(path, NOW)["healthy"]
    assert not module.trade_delivery_health(path, NOW + timedelta(minutes=4))["healthy"]


def test_stale_broker_care_alerts_even_with_green_scheduler(setup, monkeypatch):
    settings, path = setup
    (path / "qadam-control-plane.sqlite3").touch()
    monkeypatch.setattr("orchestrator.execution.ledger.read_operating_health",
                        lambda *a: {"status": "degraded", "blockers": ["broker_reconciliation_cadence_missed"]})
    messages = []
    def sender(*args):
        messages.append(args[-1])
        return sent()
    module.run_trade_delivery(settings, now=NOW, sender=sender)
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=120), sender=sender)
    module.run_trade_delivery(settings, now=NOW + timedelta(seconds=150), sender=sender)
    assert sum("canonical broker reconciliation" in message for message in messages) == 1


def _advisory(db, key, kind, state, created_at, *, target="group", message_id=None):
    module._enqueue(db, key, kind, "Preserved historical advisory", created_at.timestamp())
    db.execute("UPDATE deliveries SET state=?,target_hash=?,message_id=?,error=?,next_at=? WHERE event_key=?",
        (state, module._hash(target), message_id, "original_unknown_receipt", NOW.timestamp() + 600, key))


def test_later_confirmed_health_update_supersedes_old_advisories_without_rewriting_receipts(setup):
    settings, path = setup
    module.run_trade_delivery(settings, now=NOW, sender=sent)
    with module._connect(path / module.DB_ARTIFACT) as db:
        for index, state in enumerate(("uncertain", "retry", "pending", "failed")):
            _advisory(db, "old" + str(index), "service_health", state, NOW - timedelta(minutes=10))
        _advisory(db, "confirmed-newer", "service_health", "delivered", NOW - timedelta(minutes=1), message_id=555)
    report = module.run_trade_delivery(settings, now=NOW + timedelta(seconds=30),
        sender=lambda *_: pytest.fail("Do not replay old uncertain or superseded status messages"))
    assert report["status"] == "healthy"
    assert report["superseded_advisory_count"] == 4
    assert report["unresolved_count"] == 0
    assert report["delivery_counts"]["uncertain"] == 1
    assert "uncertain" not in report["active_delivery_counts"]
    with module._connect(path / module.DB_ARTIFACT) as db:
        assert db.execute("SELECT state,error,message_id FROM deliveries WHERE event_key='old0'").fetchone()[:] == (
            "uncertain", "original_unknown_receipt", None)
        assert db.execute("SELECT count(*) FROM advisory_supersessions").fetchone()[0] == 4
        # Losing the confirming receipt revokes the derived supersession.
        db.execute("UPDATE deliveries SET state='uncertain' WHERE event_key='confirmed-newer'")
        assert module._active_delivery_counts(db, NOW)["uncertain"] == 2
    assert module.trade_delivery_health(path, NOW + timedelta(seconds=30))["healthy"]
    assert module.trade_delivery_health(path, NOW + timedelta(minutes=4))["safe_refresh_allowed"]


@pytest.mark.parametrize("kind,new_state,target,message_id,delta", [
    ("paper_fill", "delivered", "group", 555, -60),
    ("service_health", "uncertain", "group", None, -60),
    ("service_health", "delivered", "other-chat", 555, -60),
    ("service_health", "delivered", "group", None, -60),
    ("service_health", "delivered", "group", 555, -1200),
    ("service_health", "delivered", "group", 555, 60),
])
def test_uncertain_fills_and_unconfirmed_or_wrong_target_status_cannot_be_superseded(
    setup, kind, new_state, target, message_id, delta
):
    settings, path = setup
    module.run_trade_delivery(settings, now=NOW, sender=sent)
    with module._connect(path / module.DB_ARTIFACT) as db:
        _advisory(db, "original", kind, "uncertain", NOW - timedelta(minutes=10))
        _advisory(db, "newer", "service_health", new_state, NOW + timedelta(seconds=delta),
                  target=target, message_id=message_id)
    report = module.run_trade_delivery(settings, now=NOW, sender=lambda *_: pytest.fail("Never retry an uncertain send"))
    assert report["status"] == "needs_attention"
    assert report["superseded_advisory_count"] == 0
    assert report["active_delivery_counts"]["uncertain"] >= 1


def test_disabled_mode_cannot_send(setup):
    settings, _ = setup
    settings = replace(settings, live_capital_enabled=True)

    def forbidden(*_):
        raise AssertionError("Must not send in live-capital mode")

    assert (
        module.run_trade_delivery(settings, now=NOW, sender=forbidden)["status"]
        == "needs_attention"
    )


def test_rate_limit_retries_are_bounded(setup):
    settings, path = setup

    def response(*_):
        return {"ok": False, "error_code": 429}

    for _ in range(module.MAX_ATTEMPTS + 1):
        module.run_trade_delivery(settings, now=NOW, sender=response)
        with sqlite3.connect(path / module.DB_ARTIFACT) as db:
            db.execute("UPDATE deliveries SET next_at=0")
    with sqlite3.connect(path / module.DB_ARTIFACT) as db:
        assert db.execute("SELECT state,attempts FROM deliveries").fetchone() == (
            "failed",
            module.MAX_ATTEMPTS,
        )


def test_missing_telegram_menu_recovers_with_backoff(setup, monkeypatch):
    from orchestrator import qadam_telegram_readonly_interface as interface
    settings, _ = setup
    monkeypatch.setattr(interface, "secret_value", lambda *_: "configured")
    calls = []
    def register(**_):
        calls.append(1)
        return {"registered": len(calls) > 1, "status": "registered" if len(calls) > 1 else "provider_error"}
    monkeypatch.setattr(interface, "register_readonly_commands", register)
    assert not interface.ensure_readonly_commands(settings, now=NOW)["registered"]
    assert not interface.ensure_readonly_commands(settings, now=NOW+timedelta(seconds=30))["registered"]
    assert len(calls) == 1
    assert interface.ensure_readonly_commands(settings, now=NOW+timedelta(minutes=15))["registered"]
    assert interface.ensure_readonly_commands(settings, now=NOW+timedelta(minutes=30))["registered"]
    assert len(calls) == 2


def test_submission_receipt_rejects_missing_destination_and_suppresses_uncertain_retry(
    setup, monkeypatch
):
    from orchestrator import telegram_trade_notifications as submissions

    settings, path = setup
    monkeypatch.setattr(
        submissions,
        "secret_value",
        lambda key, _: "token" if key == "TELEGRAM_BOT_TOKEN" else "group",
    )
    from types import SimpleNamespace

    monkeypatch.setattr(submissions, "secret_status", lambda *_: SimpleNamespace(configured=True))
    monkeypatch.setattr(
        submissions,
        "_portfolio_snapshot",
        lambda _: {
            "currency": "USD",
            "portfolio_value_gbp": 100100,
            "total_pnl_gbp": 100,
            "performance_pct": 0.1,
            "cash_gbp": 99700,
        },
    )
    record = {
        "status": "submitted_to_alpaca_paper",
        "request_preview": {
            "symbol": "NVDA",
            "qty": 13,
            "side": "sell",
            "client_order_id": "only-once",
        },
        "broker_receipt": {"broker_order_id_hash": "hash", "broker_order_status": "pending_new"},
    }
    (path / "paperops_alpaca_paper_post.json").write_text(
        json.dumps({"status": "submitted_to_alpaca_paper", "selected_post_records": [record]})
    )
    sends = []

    def incomplete(*args):
        sends.append(args)
        return {"ok": True, "result": {"message_id": 42}}

    monkeypatch.setattr(submissions, "_telegram_send", incomplete)
    first = submissions.build_telegram_trade_notifications(settings, send_requested=True)
    second = submissions.build_telegram_trade_notifications(settings, send_requested=True)
    assert len(sends) == 1
    assert first["live_send_succeeded_count"] == second["live_send_succeeded_count"] == 0
    assert first["records"][0]["status"] == "delivery_uncertain"
    assert "USD 100,100.00" in first["records"][0]["message_preview"]["body"]
