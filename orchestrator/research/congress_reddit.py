"""Public congressional-trading discussion metadata, never verified order flow."""

from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic
from orchestrator.research.source_time import retry_after_seconds, verified_timestamp

COMMUNITY = "tradewithcongress"
FEED_URL = f"https://www.reddit.com/r/{COMMUNITY}/new/.rss?limit=25"
STATE_ARTIFACT = "qadam_reddit_congress_feed_state.json"
VARIANT = "tradewithcongress_public_atom"
MAX_BYTES = 524288
MAX_POSTS = 25
POLL_SECONDS = 1800
ATOM = "{http://www.w3.org/2005/Atom}"
AUTHORITY = {
    "source_quorum_credit_allowed": False, "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False, "execution_allowed": False,
    "paper_order_allowed": False, "broker_write_allowed": False,
    "live_capital_enabled": False, "proof_credit_allowed": False,
}
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
    if len(body) > MAX_BYTES or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("reddit_feed_unsafe_or_oversized_xml")
    root = ET.fromstring(body)
    if root.tag != ATOM + "feed":
        raise ValueError("reddit_atom_feed_required")
    posts, seen = [], set()
    entries = root.findall(ATOM + "entry")
    rejected = 0
    for entry in entries[:MAX_POSTS]:
        link = entry.find(ATOM + "link")
        try:
            parsed = urlsplit(link.get("href", "") if link is not None else "")
        except ValueError:
            rejected += 1
            continue
        match = re.fullmatch(r"/r/tradewithcongress/comments/([a-z0-9]+)(?:/[^/]+)?/?", parsed.path)
        post_id = entry.findtext(ATOM + "id", "")
        published = verified_timestamp(entry.findtext(ATOM + "published"))
        updated = verified_timestamp(entry.findtext(ATOM + "updated"))
        stamp = published or updated
        title = " ".join(re.sub(r"<[^>]*>", " ", unescape(entry.findtext(ATOM + "title", ""))).split())[:400]
        if (parsed.scheme != "https" or parsed.netloc not in {"www.reddit.com", "reddit.com"}
                or not match or post_id != f"t3_{match[1]}" or not title or not stamp
                or datetime.fromisoformat(stamp) > now + timedelta(minutes=5)
                or (updated and datetime.fromisoformat(updated) > now + timedelta(minutes=5))
                or (published and updated and datetime.fromisoformat(updated) < datetime.fromisoformat(published))):
            rejected += 1
            continue
        if post_id in seen:
            continue
        seen.add(post_id)
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
        links.feed(entry.findtext(ATOM + "content", "")[:16384])
        posts.append({
            "record_id": post_id, "community": COMMUNITY,
            "url": f"https://www.reddit.com/r/{COMMUNITY}/comments/{match[1]}/",
            "title_excerpt": title, "issuer_symbols": sorted(tickers)[:8],
            "claimed_actor": actor, "claimed_transaction_side": None if date_conflict else side,
            "claimed_transaction_date": transaction_date, "claimed_disclosure_date": disclosure_date,
            "ambiguous_date_hints": hints[:4], "transaction_to_post_lag_days": lag,
            "claimed_dates_conflict": date_conflict,
            "post_published_at": published, "post_updated_at": updated,
            "observed_at": stamp,
            "timestamp_role": "provider_publication" if published else "provider_last_update",
            "reference_urls": sorted(links.urls)[:4], "references_verified": False,
            "primary_disclosure_verified": False, "source_variant": VARIANT,
            "content_is_untrusted": True, "financial_claims_verified": False,
            "origin_group": "congressional_disclosure_claims",
            "knowledge_boundary": "post_time_is_not_transaction_or_disclosure_time; first_seen_required",
            "current_transaction_signal": False, "historical_backfill_eligible": False,
            "sample": False, **AUTHORITY,
        })
    if entries and not posts and rejected:
        raise ValueError("reddit_feed_no_valid_entries")
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
    import httpx

    now = now or datetime.now(timezone.utc)
    path = runtime / STATE_ARTIFACT
    prior = read_json(path) if path.exists() and path.stat().st_size <= MAX_BYTES else {}
    if not isinstance(prior, dict):
        prior = {}
    due = verified_timestamp(prior.get("next_attempt_at"))
    previous = verified_timestamp(prior.get("generated_at"))
    valid_cache = (prior.get("schema_version") == "qadam_reddit_congress_feed.v1"
                   and prior.get("feed_url") == FEED_URL and prior.get("source_variant") == VARIANT
                   and prior.get("status") in {"collected", "collected_empty", "access_denied", "rate_limited", "invalid_response", "unavailable"}
                   and isinstance(prior.get("posts"), list) and len(prior["posts"]) <= MAX_POSTS
                   and prior.get("post_count") == len(prior["posts"]))
    if (valid_cache and due and previous and 0 <= (now - datetime.fromisoformat(previous)).total_seconds() <= 86400
            and now < datetime.fromisoformat(due) <= now + timedelta(days=1)):
        return {**prior, "reused_scheduled_result": True}
    state = {"schema_version": "qadam_reddit_congress_feed.v1", "generated_at": now.isoformat(),
             "community": COMMUNITY, "feed_url": FEED_URL, "source_variant": VARIANT,
             "posts": [], "post_count": 0, "last_success_at": prior.get("last_success_at"),
             "status": "unavailable", "error_category": None, "http_status": None,
             "commercial_use_requires_terms_review": True, "broker_write_count": 0,
             "new_api_or_scheduler_created": False, **AUTHORITY}
    delay = POLL_SECONDS
    try:
        async with httpx.AsyncClient(timeout=min(8.0, timeout_seconds), follow_redirects=False, transport=transport) as client:
            async with client.stream("GET", FEED_URL, headers={
                "User-Agent": "QadamResearch/1.0 (read-only paper research feed)",
                "Accept": "application/atom+xml",
            }) as response:
                state["http_status"] = response.status_code
                if response.status_code in {401, 403}:
                    state.update(status="access_denied", error_category="provider_permission_required")
                    delay = 6 * 3600
                elif response.status_code == 429:
                    state.update(status="rate_limited", error_category="provider_rate_limit")
                    delay = max(3600, retry_after_seconds(response.headers.get("Retry-After"), now=now) or 0)
                else:
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_BYTES:
                            raise ValueError("reddit_feed_response_too_large")
                        body.extend(chunk)
                    posts, rejected = parse_feed(bytes(body), now=now)
                    state.update(status="collected" if posts else "collected_empty", posts=posts,
                                 post_count=len(posts), rejected_entry_count=rejected,
                                 last_success_at=now.isoformat())
    except (ValueError, ET.ParseError):
        state.update(status="invalid_response", error_category="provider_contract")
        delay = 6 * 3600
    except httpx.HTTPStatusError:
        state.update(status="unavailable", error_category="provider_http_error")
    except httpx.HTTPError:
        state.update(status="unavailable", error_category="provider_transport_error")
    state["next_attempt_at"] = (now + timedelta(seconds=delay)).isoformat()
    write_json_atomic(path, state)
    return state
