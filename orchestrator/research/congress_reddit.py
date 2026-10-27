"""Public congressional-trading discussion metadata, never verified order flow."""

from datetime import datetime
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from orchestrator.research.source_time import verified_timestamp
from orchestrator.research.reddit_feed import (
    AUTHORITY, MAX_BYTES as MAX_BYTES, MAX_POSTS as MAX_POSTS, POLL_SECONDS as POLL_SECONDS,
    feed_url, parse_posts, fetch_public_feed,
)

COMMUNITY = "tradewithcongress"
FEED_URL = feed_url(COMMUNITY)
STATE_ARTIFACT = "qadam_reddit_congress_feed_state.json"
VARIANT = "tradewithcongress_public_atom"
ACTORS = {
    "pelosi": "Nancy Pelosi", "ro khanna": "Ro Khanna", "lisa mcclain": "Lisa McClain",
    "laurel lee": "Laurel Lee", "michael mccaul": "Michael McCaul",
    "tommy tuberville": "Tommy Tuberville", "josh gottheimer": "Josh Gottheimer",
    "dan crenshaw": "Dan Crenshaw", "markwayne mullin": "Markwayne Mullin",
    "trump": "Donald Trump",
}
ISSUERS = {"nvidia": "NVDA", "intel": "INTC", "micron": "MU", "sandisk": "SNDK",
           "tsmc": "TSM", "lockheed": "LMT", "raytheon": "RTX"}
REFERENCE_HOSTS = {"disclosures-clerk.house.gov", "efd.senate.gov",
                   "www.capitoltrades.com", "capitoltrades.com",
                   "www.quiverquant.com", "quiverquant.com"}


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            try:
                parsed = urlsplit(href)
            except ValueError:
                return
            if (parsed.scheme == "https" and parsed.netloc in REFERENCE_HOSTS
                    and not parsed.username and not parsed.password and len(href) <= 500
                    and not parsed.query and not parsed.fragment):
                self.urls.add(href)


def _date_claim(title, label, *, transaction=False):
    # Never assign a filing date to the purchase described earlier in a title.
    text = re.split(r"\b(?:filed|disclosed|reported)\b", title, maxsplit=1, flags=re.I)[0] if transaction else title
    pattern = rf"\b{label}\b[^.!?;\n]{{0,90}}?\b(\d{{4}}-\d{{2}}-\d{{2}})\b"
    match = re.search(pattern, text, re.I)
    try:
        return datetime.strptime(match[1], "%Y-%m-%d").date().isoformat() if match else None
    except ValueError:
        return None


def _direction(title, actor):
    if not actor or "?" in title:
        return None
    text = title.lower().replace("\u2019", "'")
    # A position still held, or a retrospective performance chart, is not a new sale.
    text = re.sub(r"\b(?:not|never|hasn't|haven't|didn't)\s+(?:\w+\s+){0,2}(?:sold|bought|purchased|invested)\b", "", text)
    bought = bool(re.search(r"\b(?:bought|purchased|acquired|invested|picked up)\b", text))
    sold = bool(re.search(r"\b(?:sold|dumped|liquidated)\b", text))
    return "purchase_claim" if bought and not sold else "sale_claim" if sold and not bought else None


def parse_feed(body, *, now):
    posts, rejected = parse_posts(body, community=COMMUNITY, now=now, include_reference_html=True)
    for post in posts:
        title, stamp = post["title_excerpt"], post["observed_at"]
        tickers = set(re.findall(r"(?<![A-Za-z0-9])\$([A-Z]{1,5}(?:\.[A-Z])?)\b", title))
        tickers.update(re.findall(r"\(([A-Z]{1,5}(?:\.[A-Z])?)\)", title))
        tickers.update(symbol for name, symbol in ISSUERS.items() if re.search(rf"\b{re.escape(name)}\b", title, re.I))
        tickers.difference_update({"CEO", "USA", "USD", "ETF", "NYSE", "NASDAQ", "AI", "US"})
        actors = sorted({name for alias, name in ACTORS.items() if re.search(rf"\b{re.escape(alias)}\b", title, re.I)})
        actor = actors[0] if len(actors) == 1 else None
        side = _direction(title, actor) if len(tickers) == 1 else None
        transaction_date = _date_claim(title, r"(?:transaction date|traded|bought|purchased|sold|invested|picked up)", transaction=True)
        disclosure_date = _date_claim(title, r"(?:filed|disclosed|reported)")
        # Preserve incomplete date hints without inventing a year or a publication instant.
        hints = re.findall(r"\b(?:\d{1,2}/\d{1,2}(?:/\d{4})?|(?:Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*) \d{1,2}|last year)\b", title, re.I)
        lag = (datetime.fromisoformat(stamp).date() - datetime.fromisoformat(transaction_date).date()).days if transaction_date else None
        date_conflict = bool((lag is not None and lag < 0) or (
            disclosure_date and transaction_date and disclosure_date < transaction_date))
        links = _Links()
        links.feed(post.pop("_reference_html"))
        post.update({
            "issuer_symbols": sorted(tickers)[:8],
            "claimed_actor": actor, "claimed_transaction_side": None if date_conflict else side,
            "claimed_transaction_date": transaction_date, "claimed_disclosure_date": disclosure_date,
            "ambiguous_date_hints": hints[:4], "transaction_to_post_lag_days": lag,
            "claimed_dates_conflict": date_conflict,
            "reference_urls": sorted(links.urls)[:4], "references_verified": False,
            "primary_disclosure_verified": False, "source_variant": VARIANT,
            "content_is_untrusted": True, "financial_claims_verified": False,
            "origin_group": "congressional_disclosure_claims",
            "knowledge_boundary": "post_time_is_not_transaction_or_disclosure_time; first_seen_required",
            "current_transaction_signal": False, "historical_backfill_eligible": False,
            "sample": False, **AUTHORITY,
        })
    return posts, rejected


def public_status(state, *, now):
    result = {key: state.get(key) for key in (
        "generated_at", "status", "community", "feed_url", "last_success_at", "next_attempt_at",
        "post_count", "rejected_entry_count", "error_category", "http_status")}
    stamp = verified_timestamp(state.get("generated_at"))
    result["state_current"] = bool(stamp and 0 <= (now - datetime.fromisoformat(stamp)).total_seconds() <= 7200)
    result.update(status=state.get("status") or "not_polled", community=COMMUNITY, feed_url=FEED_URL)
    result.update(secondary_only=True, independently_verified_disclosure_count=0,
                  primary_source_quorum_allowed=False, live_capital_enabled=False)
    return result


async def fetch_feed(runtime, *, now=None, timeout_seconds=8.0, transport=None):
    """One bounded request on the existing source worker; no denied-access fallback."""
    return await fetch_public_feed(runtime, community=COMMUNITY, state_artifact=STATE_ARTIFACT,
        variant=VARIANT, schema_version="qadam_reddit_congress_feed.v1", parser=parse_feed,
        now=now, timeout_seconds=timeout_seconds, transport=transport)
