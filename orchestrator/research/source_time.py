"""Provider clocks are evidence; a download clock is only local availability."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import re


def verified_timestamp(value, *, naive_utc=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                return None
            seconds = value / 1000 if value > 10_000_000_000 else value
            stamp = datetime.fromtimestamp(seconds, timezone.utc)
        else:
            text = str(value).strip()
            if re.fullmatch(r"\d{8}T\d{6}Z", text):
                stamp = datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                return None  # Reference dates do not identify a publication instant.
            else:
                # AISSTREAM time_utc uses Go's nanosecond UTC format.
                text = re.sub(r" (\+\d{4})$", r"\1", text.removesuffix(" UTC"))
                try:
                    stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
                except ValueError:
                    stamp = parsedate_to_datetime(text)
            if stamp.tzinfo is None:
                if not naive_utc:
                    return None
                stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp.year < 1970:
            return None
        return stamp.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def temporal_fields(source_key, record):
    # Never descend into suggested prediction-market matches or use a trade date
    # as the time at which a disclosure could have been known.
    for field in ("published_at", "publication_date", "filed_at", "filedAt",
                  "observed_at", "event_timestamp", "updated_at", "updated_time",
                  "created_at", "created_time", "timestamp", "time"):
        stamp = verified_timestamp(record.get(field), naive_utc=source_key == "space_track_celestrak")
        if stamp:
            return stamp, field
    return None, None


def retry_after_seconds(value, *, now):
    try:
        delay = float(value)
        if math.isfinite(delay) and delay >= 0:
            return min(86400, math.ceil(delay))
    except (ValueError, TypeError):
        stamp = verified_timestamp(value)
        if stamp:
            return min(86400, max(0, math.ceil((datetime.fromisoformat(stamp) - now).total_seconds())))
    return None
