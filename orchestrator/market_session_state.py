"""Derive an effective market session from a possibly stale broker clock."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_market_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def effective_market_session(
    market_clock: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Correct a broker clock captured immediately before a session boundary."""

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    reported_is_open = market_clock.get("is_open")
    reported_status = str(market_clock.get("status") or "").lower()
    next_close = parse_market_timestamp(market_clock.get("next_close"))
    next_open = parse_market_timestamp(market_clock.get("next_open"))

    if reported_is_open is True:
        if next_close and current >= next_close:
            if next_open and current < next_open:
                return {
                    "is_open": False,
                    "status": "closed",
                    "reason": "between_completed_close_and_next_open",
                    "reported_is_open": True,
                }
            return {
                "is_open": None,
                "status": "unknown",
                "reason": "reported_open_clock_expired",
                "reported_is_open": True,
            }
        return {
            "is_open": True,
            "status": "open",
            "reason": "reported_open_clock_current",
            "reported_is_open": True,
        }

    if reported_is_open is False or reported_status in {"closed", "market_closed"}:
        if next_open and current >= next_open:
            return {
                "is_open": None,
                "status": "unknown",
                "reason": "reported_closed_clock_expired",
                "reported_is_open": reported_is_open,
            }
        return {
            "is_open": False,
            "status": "closed",
            "reason": "reported_closed_clock_current",
            "reported_is_open": reported_is_open,
        }

    return {
        "is_open": None,
        "status": "unknown",
        "reason": "market_clock_state_unavailable",
        "reported_is_open": reported_is_open,
    }
