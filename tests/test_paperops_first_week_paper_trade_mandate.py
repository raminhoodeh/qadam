from __future__ import annotations

from datetime import date

from orchestrator.config import Settings
import orchestrator.paperops_alpaca_paper_post as paper_post
import orchestrator.paperops_first_week_paper_trade_mandate as mandate


def _settings() -> Settings:
    return Settings.from_env()


def test_first_week_mandate_builds_three_paper_only_orders(monkeypatch) -> None:
    monkeypatch.setattr(mandate, "_local_date", lambda settings: date(2026, 5, 28))
    monkeypatch.setattr(mandate, "_submitted_source_keys", lambda settings: set())

    artifact = mandate.build_first_week_paper_trade_mandate(settings=_settings())

    assert artifact["status"] == "active_ready_for_paper_orders"
    assert artifact["active"] is True
    assert artifact["day_number"] == 1
    assert artifact["daily_target_trade_count"] == 3
    assert artifact["minimum_notional_usd"] == 6000.0
    assert artifact["daily_ready_submit_count"] == 3
    assert artifact["daily_submitted_count"] == 0
    assert artifact["paper_only"] is True
    assert artifact["live_capital_enabled"] is False
    assert artifact["proof_credit_allowed"] is False
    assert artifact["validation_errors"] == []

    for record in artifact["mandate_records"]:
        assert record["selected_venue"] == "alpaca_paper"
        assert record["notional_usd"] >= 6000.0
        assert record["paper_only"] is True
        assert record["live_capital_enabled"] is False
        assert record["proof_credit_allowed"] is False


def test_first_week_mandate_marks_existing_slots_submitted(monkeypatch) -> None:
    submitted = {"paperops-fwpt-20260528-01", "paperops-fwpt-20260528-02"}
    monkeypatch.setattr(mandate, "_local_date", lambda settings: date(2026, 5, 28))
    monkeypatch.setattr(mandate, "_submitted_source_keys", lambda settings: submitted)

    artifact = mandate.build_first_week_paper_trade_mandate(settings=_settings())

    assert artifact["daily_submitted_count"] == 2
    assert artifact["daily_ready_submit_count"] == 1
    assert artifact["daily_remaining_submit_count"] == 1
    assert [record["status"] for record in artifact["mandate_records"]] == [
        "already_submitted",
        "already_submitted",
        "ready_for_paperops2_submit",
    ]
    assert artifact["validation_errors"] == []


def test_mandate_candidate_uses_notional_order_body(monkeypatch) -> None:
    monkeypatch.setattr(mandate, "_local_date", lambda settings: date(2026, 5, 28))
    monkeypatch.setattr(mandate, "_submitted_source_keys", lambda settings: set())
    source = mandate.build_first_week_paper_trade_mandate(settings=_settings())

    candidate = paper_post._mandate_record_to_submit_candidate(
        source["mandate_records"][0],
        source=source,
    )
    body = paper_post._alpaca_post_body(candidate["request_preview"])

    assert candidate["eligible_for_paper_post"] is True
    assert candidate["source_family"] == "paperops_first_week_paper_trade_mandate"
    assert candidate["idempotency_key"].startswith("paperops-fwpt-20260528")
    assert body["notional"] == "6000.00"
    assert "qty" not in body
    assert body["client_order_id"].startswith("paperops-fwpt-20260528")


def test_first_week_mandate_outside_window_does_not_create_orders(monkeypatch) -> None:
    monkeypatch.setattr(mandate, "_local_date", lambda settings: date(2026, 6, 5))
    monkeypatch.setattr(mandate, "_submitted_source_keys", lambda settings: set())

    artifact = mandate.build_first_week_paper_trade_mandate(settings=_settings())

    assert artifact["status"] == "outside_first_week_window"
    assert artifact["active"] is False
    assert artifact["daily_decision_count"] == 0
    assert artifact["daily_ready_submit_count"] == 0
    assert artifact["mandate_records"] == []
    assert artifact["validation_errors"] == []
