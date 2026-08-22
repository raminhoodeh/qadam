from datetime import datetime, timezone

from orchestrator.market_session_state import effective_market_session


def test_reported_open_clock_becomes_closed_after_session_end() -> None:
    result = effective_market_session(
        {
            "status": "ok",
            "is_open": True,
            "next_close": "2026-08-21T16:00:00-04:00",
            "next_open": "2026-08-24T09:30:00-04:00",
        },
        now=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
    )

    assert result == {
        "is_open": False,
        "status": "closed",
        "reason": "between_completed_close_and_next_open",
        "reported_is_open": True,
    }


def test_reported_open_clock_expires_after_next_session_begins() -> None:
    result = effective_market_session(
        {
            "status": "ok",
            "is_open": True,
            "next_close": "2026-08-21T16:00:00-04:00",
            "next_open": "2026-08-24T09:30:00-04:00",
        },
        now=datetime(2026, 8, 24, 14, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "unknown"
    assert result["reason"] == "reported_open_clock_expired"


def test_reported_closed_clock_expires_after_next_session_begins() -> None:
    result = effective_market_session(
        {
            "status": "closed",
            "is_open": False,
            "next_open": "2026-08-24T09:30:00-04:00",
        },
        now=datetime(2026, 8, 24, 14, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "unknown"
    assert result["reason"] == "reported_closed_clock_expired"
