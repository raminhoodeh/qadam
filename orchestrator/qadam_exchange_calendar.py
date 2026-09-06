"""Provider calendar receipts, shared by exits and market-session diagnostics."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


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
                    and 0 <= (reference - observed).total_seconds() <= 21600
                    and receipt["start"] <= today <= receipt["end"]
                    and isinstance(receipt["sessions"], list) and receipt["sessions"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


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
