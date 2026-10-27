"""Bounded public Atom metadata transport shared by reviewed Reddit communities."""

import asyncio
from datetime import datetime, timedelta, timezone
from html import unescape
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic
from orchestrator.research.source_time import retry_after_seconds, verified_timestamp

MAX_BYTES = 524288
MAX_POSTS = 25
POLL_SECONDS = 1800
ATOM = "{http://www.w3.org/2005/Atom}"
COMMUNITIES = {"tradewithcongress", "wallstreetbets"}
AUTHORITY = {
    "source_quorum_credit_allowed": False, "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False, "execution_allowed": False,
    "paper_order_allowed": False, "broker_write_allowed": False,
    "live_capital_enabled": False, "proof_credit_allowed": False,
}


def feed_url(community):
    if community not in COMMUNITIES:
        raise ValueError("reddit_community_not_reviewed")
    return f"https://www.reddit.com/r/{community}/new/.rss?limit=25"


def parse_posts(body, *, community, now, include_reference_html=False):
    feed_url(community)
    if len(body) > MAX_BYTES or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("reddit_feed_unsafe_or_oversized_xml")
    root = ET.fromstring(body)
    if root.tag != ATOM + "feed":
        raise ValueError("reddit_atom_feed_required")
    posts, seen, rejected = [], set(), 0
    entries = root.findall(ATOM + "entry")
    for entry in entries[:MAX_POSTS]:
        link = entry.find(ATOM + "link")
        try:
            parsed = urlsplit(link.get("href", "") if link is not None else "")
        except ValueError:
            rejected += 1
            continue
        match = re.fullmatch(rf"/r/{community}/comments/([a-z0-9]+)(?:/[^/]+)?/?", parsed.path)
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
        post = {"record_id": post_id, "community": community,
            "url": f"https://www.reddit.com/r/{community}/comments/{match[1]}/",
            "title_excerpt": title, "post_published_at": published, "post_updated_at": updated,
            "observed_at": stamp,
            "timestamp_role": "provider_publication" if published else "provider_last_update"}
        if include_reference_html:
            # Transient link extraction only; callers must not persist this field.
            post["_reference_html"] = entry.findtext(ATOM + "content", "")[:16384]
        posts.append(post)
    if entries and not posts and rejected:
        raise ValueError("reddit_feed_no_valid_entries")
    return posts, rejected


async def fetch_public_feed(runtime, *, community, state_artifact, variant, schema_version,
                            parser, now=None, timeout_seconds=8.0, transport=None):
    """One bounded request, independent cooldown, no access-denial workaround."""
    import httpx

    now = now or datetime.now(timezone.utc)
    url = feed_url(community)
    path = runtime / state_artifact
    prior = read_json(path) if path.exists() and path.stat().st_size <= MAX_BYTES else {}
    due = verified_timestamp(prior.get("next_attempt_at"))
    previous = verified_timestamp(prior.get("generated_at"))
    valid_cache = (prior.get("schema_version") == schema_version
        and prior.get("feed_url") == url and prior.get("source_variant") == variant
        and prior.get("status") in {"collected", "collected_empty", "access_denied", "rate_limited", "invalid_response", "unavailable"}
        and isinstance(prior.get("posts"), list) and len(prior["posts"]) <= MAX_POSTS
        and prior.get("post_count") == len(prior["posts"])
        and all(isinstance(post, dict) and post.get("source_variant") == variant
                and post.get("community") == community for post in prior["posts"]))
    if (valid_cache and due and previous and 0 <= (now - datetime.fromisoformat(previous)).total_seconds() <= 86400
            and now < datetime.fromisoformat(due) <= now + timedelta(days=1)):
        return {**prior, "reused_scheduled_result": True}
    state = {"schema_version": schema_version, "generated_at": now.isoformat(),
        "community": community, "feed_url": url, "source_variant": variant,
        "posts": [], "post_count": 0, "last_success_at": prior.get("last_success_at"),
        "status": "unavailable", "error_category": None, "http_status": None,
        "commercial_use_requires_terms_review": True, "broker_write_count": 0,
        "new_api_or_scheduler_created": False, **AUTHORITY}
    delay = POLL_SECONDS
    try:
        async with asyncio.timeout(min(8.0, timeout_seconds)), httpx.AsyncClient(
                timeout=min(8.0, timeout_seconds), follow_redirects=False, transport=transport) as client:
            async with client.stream("GET", url, headers={
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
                    posts, rejected = parser(bytes(body), now=now)
                    state.update(status="collected" if posts else "collected_empty", posts=posts,
                        post_count=len(posts), rejected_entry_count=rejected, last_success_at=now.isoformat())
    except (ValueError, ET.ParseError):
        state.update(status="invalid_response", error_category="provider_contract")
        delay = 6 * 3600
    except httpx.HTTPStatusError:
        state.update(status="unavailable", error_category="provider_http_error")
    except (httpx.HTTPError, TimeoutError):
        state.update(status="unavailable", error_category="provider_transport_error")
    state["next_attempt_at"] = (now + timedelta(seconds=delay)).isoformat()
    write_json_atomic(path, state)
    return state
