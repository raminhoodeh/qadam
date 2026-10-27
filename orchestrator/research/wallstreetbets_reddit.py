"""Sampled retail-discussion leads; neither verified holdings nor trade advice."""

from collections import Counter
from datetime import datetime
import re

from orchestrator.research.reddit_feed import AUTHORITY, feed_url, parse_posts, fetch_public_feed
from orchestrator.research.source_time import verified_timestamp

COMMUNITY = "wallstreetbets"
FEED_URL = feed_url(COMMUNITY)
STATE_ARTIFACT = "qadam_reddit_wallstreetbets_feed_state.json"
VARIANT = "wallstreetbets_public_atom"
BARE_TICKERS = {"NVDA", "SMH", "SOXX", "TSM", "MU", "SNDK", "SPY", "QQQ", "TLT", "BNO", "USO",
                "XLE", "XAR", "ITA", "LMT", "RTX", "SLV", "SIL", "GLD", "XME", "INTC", "AMD", "AVGO", "ASML", "AMAT", "LRCX"}
ISSUERS = {"nvidia": "NVDA", "intel": "INTC", "micron": "MU", "sandisk": "SNDK", "tsmc": "TSM",
           "tesla": "TSLA", "microsoft": "MSFT", "alphabet": "GOOGL", "netflix": "NFLX", "palantir": "PLTR"}
BARE_TICKERS |= set(ISSUERS.values())


def parse_feed(body, *, now):
    posts, rejected = parse_posts(body, community=COMMUNITY, now=now)
    for post in posts:
        title = post["title_excerpt"]
        symbols = set(re.findall(r"(?<![A-Za-z0-9])\$([A-Z]{1,5}(?:\.[A-Z])?)\b", title))
        symbols.update(re.findall(r"\(([A-Z]{1,5}(?:\.[A-Z])?)\)", title))
        symbols.update(symbol for symbol in BARE_TICKERS if re.search(rf"\b{symbol}\b", title))
        symbols.update(symbol for name, symbol in ISSUERS.items() if re.search(rf"\b{name}\b", title, re.I))
        symbols.difference_update({"CEO", "USA", "USD", "ETF", "NYSE", "NASDAQ", "AI", "US", "DD", "YOLO", "FED"})
        tags = [tag for tag, pattern in {
            "options_speculation": r"\b(?:calls?|puts?|options?|0dte)\b|\b\d+(?:\.\d+)?[cp]\b",
            "earnings_discussion": r"\bearnings?\b", "analysis_claim": r"\b(?:DD|due diligence|thesis|analysis)\b",
            "gain_loss_claim": r"\b(?:gain|loss|profit|baghold\w*)\b", "yolo_claim": r"\byolo\b",
        }.items() if re.search(pattern, title, re.I)]
        post.update(issuer_symbols=sorted(symbols)[:8], source_variant=VARIANT,
            discussion_tags=tags, direction=None, sentiment="unmeasured",
            financial_claims_verified=False, content_is_untrusted=True, holdings_verified=False,
            origin_group="reddit_retail_attention_shared_with_aggregate",
            overlap_with_apewisdom_possible=True, independent_confirmation=False,
            coverage_scope="latest_25_submission_titles_not_complete_subreddit",
            current_transaction_signal=False, historical_backfill_eligible=False,
            sample=False, **AUTHORITY)
    return posts, rejected


async def fetch_feed(runtime, *, now=None, timeout_seconds=8.0, transport=None):
    return await fetch_public_feed(runtime, community=COMMUNITY, state_artifact=STATE_ARTIFACT,
        variant=VARIANT, schema_version="qadam_reddit_wallstreetbets_feed.v1", parser=parse_feed,
        now=now, timeout_seconds=timeout_seconds, transport=transport)


def public_status(state, *, now):
    result = {key: state.get(key) for key in (
        "generated_at", "status", "last_success_at", "next_attempt_at", "post_count",
        "rejected_entry_count", "error_category", "http_status")}
    stamp = verified_timestamp(state.get("generated_at"))
    counts = Counter(symbol for post in state.get("posts", []) if isinstance(post, dict)
                     for symbol in set(post.get("issuer_symbols", [])))
    result.update(status=state.get("status") or "not_polled", community=COMMUNITY, feed_url=FEED_URL,
        state_current=bool(stamp and 0 <= (now - datetime.fromisoformat(stamp)).total_seconds() <= 7200),
        ticker_title_sample_counts=dict(counts.most_common(10)),
        coverage_scope="latest_25_submission_titles_not_complete_subreddit", sentiment="unmeasured",
        attention_spike_established=False, secondary_only=True, independent_confirmation=False,
        overlap_with_apewisdom_possible=True, primary_source_quorum_allowed=False, live_capital_enabled=False)
    return result
