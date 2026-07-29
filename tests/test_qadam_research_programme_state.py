import json

from orchestrator.qadam_research_programme_state import (
    build_research_programme_state,
    refresh_research_programme_state,
    validate_research_programme_state,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_research_programme_state_skips_blocked_queue_head(tmp_path):
    _write_json(
        tmp_path / "qadam_stock_act_detail_coverage.json",
        {
            "generated_at": "2026-07-29T00:00:00+00:00",
            "transaction_detail_signal_backtestable": False,
            "parsed_transaction_detail_count": 0,
            "transaction_detail_state": ("terminally_classified_not_present_in_acquired_archive"),
        },
    )
    _write_json(
        tmp_path / "qadam_unusual_whales_history_coverage.json",
        {
            "generated_at": "2026-07-29T00:00:00+00:00",
            "historical_backtest_allowed": False,
            "backtest_eligible_record_count": 0,
        },
    )
    _write_json(
        tmp_path / "qadam_unusual_whales_forward_capture_status.json",
        {
            "generated_at": "2026-07-29T00:00:00+00:00",
            "capture_running": False,
        },
    )
    _write_json(
        tmp_path / "qadam_focus_provider_contracts.json",
        {
            "generated_at": "2026-07-29T00:00:00+00:00",
            "providers": [
                {"provider": "kalshi", "state": "approved_bounded_capture"},
                {"provider": "polymarket", "state": "approved_bounded_capture"},
            ],
        },
    )
    queue = {
        "queue": [
            {
                "rank": 1,
                "programme_id": "programme-b-stock-act-sector-repricing",
                "question": "Does STOCK Act detail improve sector timing?",
            },
            {
                "rank": 2,
                "programme_id": "programme-c-unusual-whales-confirmation",
                "question": "Does options flow improve macro timing?",
            },
            {
                "rank": 3,
                "programme_id": "programme-a-prediction-market-disagreement",
                "question": "Does prediction-market disagreement lead repricing?",
            },
        ]
    }

    payload = build_research_programme_state(
        tmp_path,
        queue,
        generated_at="2026-07-29T04:00:00+00:00",
    )

    validate_research_programme_state(payload)
    assert payload["status"] == "runnable_focus_selected"
    assert payload["active_count"] == 1
    assert payload["blocked_external_data_count"] == 2
    assert payload["selected_programme"]["programme_id"] == (
        "programme-a-prediction-market-disagreement"
    )
    assert payload["selected_programme"]["rank"] == 3
    assert payload["programmes"][0]["state"] == "blocked_external_data"
    assert payload["programmes"][1]["state"] == "blocked_external_data"


def test_research_programme_state_rejects_blocked_selection(tmp_path):
    payload = build_research_programme_state(
        tmp_path,
        {
            "queue": [
                {
                    "rank": 1,
                    "programme_id": "programme-b-stock-act-sector-repricing",
                    "question": "Does STOCK Act detail improve sector timing?",
                }
            ]
        },
        generated_at="2026-07-29T04:00:00+00:00",
    )
    payload["selected_programme"] = dict(payload["programmes"][0])

    try:
        validate_research_programme_state(payload)
    except ValueError as exc:
        assert "non-runnable" in str(exc)
    else:
        raise AssertionError("Blocked research programme passed selection validation")


def test_research_programme_state_rejects_authority_escalation(tmp_path):
    payload = build_research_programme_state(
        tmp_path,
        {"queue": []},
        generated_at="2026-07-29T04:00:00+00:00",
    )
    payload["authority"]["paper_order_allowed"] = True

    try:
        validate_research_programme_state(payload)
    except ValueError as exc:
        assert "authority invalid" in str(exc)
    else:
        raise AssertionError("Research programme authority escalation passed validation")


def test_refresh_updates_durable_queue_and_next_work(tmp_path):
    _write_json(
        tmp_path / "qadam_focus_provider_contracts.json",
        {
            "generated_at": "2026-07-29T00:00:00+00:00",
            "providers": [
                {"provider": "kalshi", "state": "approved_bounded_capture"},
                {"provider": "polymarket", "state": "approved_bounded_capture"},
            ],
        },
    )
    _write_json(
        tmp_path / "qadam_stock_act_detail_coverage.json",
        {
            "transaction_detail_signal_backtestable": False,
            "parsed_transaction_detail_count": 0,
            "transaction_detail_state": ("terminally_classified_not_present_in_acquired_archive"),
        },
    )
    queue_path = tmp_path / "qadam_value_of_information_queue.json"
    _write_json(
        queue_path,
        {
            "status": "ranked_after_no_surviving_edge",
            "queue": [
                {
                    "rank": 1,
                    "programme_id": "programme-b-stock-act-sector-repricing",
                    "question": "Does STOCK Act detail improve sector timing?",
                },
                {
                    "rank": 2,
                    "programme_id": "programme-a-prediction-market-disagreement",
                    "question": "Does prediction-market disagreement lead repricing?",
                },
            ],
        },
    )
    post_path = tmp_path / "qadam_post_backtest_decision.json"
    _write_json(
        post_path,
        {
            "status": "remain_in_cash_and_improve_information_value",
            "next_test": "Does STOCK Act detail improve sector timing?",
        },
    )

    state = refresh_research_programme_state(
        tmp_path,
        generated_at="2026-07-29T04:00:00+00:00",
    )

    refreshed_queue = json.loads(queue_path.read_text(encoding="utf-8"))
    refreshed_post = json.loads(post_path.read_text(encoding="utf-8"))
    assert state["selected_programme"]["programme_id"] == (
        "programme-a-prediction-market-disagreement"
    )
    assert refreshed_queue["selected_programme_id"] == (
        "programme-a-prediction-market-disagreement"
    )
    assert refreshed_queue["queue"][0]["state"] == "blocked_external_data"
    assert refreshed_post["next_test"] == ("Does prediction-market disagreement lead repricing?")
    assert refreshed_post["next_programme_state"] == "active"
    assert refreshed_post["blocked_programmes_are_not_active_questions"] is True
