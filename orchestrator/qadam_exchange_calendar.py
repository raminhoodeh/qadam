"""Provider calendar receipts, shared by exits and market-session diagnostics."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
CALENDAR_MAX_AGE_SECONDS = 21600
CALENDAR_REFRESH_MARGIN_SECONDS = 900


def valid_calendar(receipt: dict, reference: datetime) -> bool:
    try:
        observed = datetime.fromisoformat(receipt["observed_at"])
        if observed.tzinfo is None or reference.tzinfo is None:
            return False
        observed = observed.astimezone(timezone.utc)
        sessions = receipt["sessions"]
        if not isinstance(sessions, list) or not sessions:
            return False
        dates = set()
        for row in sessions:
            date = datetime.fromisoformat(row["date"]).date().isoformat()
            opening, closing = (time.fromisoformat(row[key]) for key in ("open", "close"))
            if date in dates or opening >= closing or not receipt["start"] <= date <= receipt["end"]:
                return False
            dates.add(date)
        today = reference.astimezone(NEW_YORK).date().isoformat()
        return bool(receipt["provider"] == "alpaca_calendar_v2"
                    and 0 <= (reference - observed).total_seconds() <= CALENDAR_MAX_AGE_SECONDS
                    and receipt["start"] <= today <= receipt["end"]
                    and isinstance(receipt["sessions"], list) and receipt["sessions"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def calendar_cache_reusable(receipt: dict, reference: datetime) -> bool:
    return valid_calendar(receipt, reference) and valid_calendar(
        receipt, reference + timedelta(seconds=CALENDAR_REFRESH_MARGIN_SECONDS)
    )


def elapsed_market_seconds(start: datetime | None, end: datetime, receipt: dict) -> float | None:
    """Measure missed regular-session work, never grant trade-time freshness."""
    if start is None or start.tzinfo is None or not valid_calendar(receipt, end) or start > end:
        return None
    if start.astimezone(NEW_YORK).date().isoformat() < receipt["start"]:
        return None
    elapsed = 0.0
    for row in receipt["sessions"]:
        day = datetime.fromisoformat(row["date"]).date()
        opening = datetime.combine(day, time.fromisoformat(row["open"]), NEW_YORK)
        closing = datetime.combine(day, time.fromisoformat(row["close"]), NEW_YORK)
        elapsed += max(0.0, (min(end, closing) - max(start, opening)).total_seconds())
    return elapsed


def elapsed_sessions(start: datetime | None, end: datetime, receipt: dict) -> int | None:
    if start is None or not valid_calendar(receipt, end):
        return None
    first = start.astimezone(NEW_YORK).date().isoformat()
    if first < receipt["start"]:
        return None
    try:
        return sum(
            row["date"] > first
            and datetime.combine(datetime.fromisoformat(row["date"]).date(),
                                 time.fromisoformat(row["open"]), NEW_YORK) <= end
            for row in receipt["sessions"]
        )
    except (KeyError, ValueError, TypeError):
        return None


def calendar_phase(reference: datetime, receipt: dict) -> str | None:
    if not valid_calendar(receipt, reference):
        return None
    local = reference.astimezone(NEW_YORK)
    rows = [row for row in receipt["sessions"] if row.get("date") == local.date().isoformat()]
    if not rows:
        return "weekend" if local.weekday() >= 5 else "holiday"
    try:
        opening, closing = (time.fromisoformat(rows[0][key]) for key in ("open", "close"))
        current = local.time()
        if opening <= current < closing:
            return "regular"
        return "pre_market" if current < opening else "post_market"
    except (KeyError, ValueError, TypeError):
        return None
