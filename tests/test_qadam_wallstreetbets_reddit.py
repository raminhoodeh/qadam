import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from orchestrator.config import Settings
from orchestrator.reddit_narrative_proxy import build_reddit_narrative_proxy_packet, reddit_narrative_proxy_events
from orchestrator.research import wallstreetbets_reddit as wsb
from orchestrator.research import congress_reddit as congress
from orchestrator.research.reddit_feed import AUTHORITY, MAX_BYTES, feed_url
from orchestrator.research.source_context import capture_context, build_context_projection, context_for_instrument

NOW = datetime(2026, 10, 27, 13, tzinfo=timezone.utc)
STAMP = "2026-10-27T11:45:29+00:00"


def atom(title="NVDA calls ahead of earnings", *, stamp=STAMP, updated=STAMP, community="wallstreetbets",
         post_id="abc123", content="", host="www.reddit.com"):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>t3_{post_id}</id><title>{escape(title)}</title>'
        f'<published>{stamp}</published><updated>{updated}</updated>'
        f'<link href="https://{host}/r/{community}/comments/{post_id}/title/"/>'
        f'<content type="html">{escape(content)}</content></entry></feed>').encode()


def post(title="NVDA calls ahead of earnings", **kwargs):
    return wsb.parse_feed(atom(title, **kwargs), now=NOW)[0][0]


def packet(tmp_path, posts):
    return build_reddit_narrative_proxy_packet(
        {"sample": False, "filters": {}, "wallstreetbets_feed": {"status": "collected", "posts": posts}},
        settings=replace(Settings.from_env(), runtime_dir=str(tmp_path)), generated_at=NOW.isoformat(), live_mode=True)


@pytest.mark.parametrize("title,symbols", [
    ("NVDA calls ahead of earnings", ["NVDA"]), ("SPY 600p 0DTE", ["SPY"]),
    ("Micron and Sandisk thesis", ["MU", "SNDK"]), ("Intel (INTC) bagholders", ["INTC"]),
    ("$ZZZZ speculative DD", ["ZZZZ"]), ("Daily discussion thread", []),
    ("YOLO FED USA CEO (DD) AI ETF", []), ("Microsoft and Alphabet earnings", ["GOOGL", "MSFT"]),
    ("$NVDA $NVDA NVDA", ["NVDA"]), ("Spy on the neighbours", []),
    ("TSLA MSFT earnings", ["MSFT", "TSLA"]),
])
def test_conservative_ticker_extraction(title, symbols):
    assert post(title)["issuer_symbols"] == symbols


@pytest.mark.parametrize("title,tag", [
    ("SPY calls", "options_speculation"), ("SPY puts", "options_speculation"),
    ("SPY 600p 0DTE", "options_speculation"), ("NVDA earnings", "earnings_discussion"),
    ("$NVDA DD", "analysis_claim"), ("$NVDA YOLO", "yolo_claim"),
    ("$NVDA profit screenshot", "gain_loss_claim"),
])
def test_discussion_tags_are_not_direction_sentiment_or_verified_holdings(title, tag):
    row = post(title)
    assert tag in row["discussion_tags"]
    assert row["direction"] is None and row["sentiment"] == "unmeasured"
    assert not row["holdings_verified"] and not row["financial_claims_verified"]
    assert row["overlap_with_apewisdom_possible"] and not row["independent_confirmation"]
    assert all(row[key] is False for key in AUTHORITY)


@pytest.mark.parametrize("kwargs", [
    {"stamp": "tomorrow", "updated": "tomorrow"}, {"stamp": "2026-10-28T10:00:00Z"},
    {"updated": "2026-10-28T10:00:00Z"}, {"updated": "2026-10-26T10:00:00Z"},
    {"community": "tradewithcongress"}, {"host": "evil.example"},
])
def test_invalid_clock_and_cross_community_provenance_are_rejected(kwargs):
    with pytest.raises(ValueError, match="no_valid_entries"):
        wsb.parse_feed(atom(**kwargs), now=NOW)


@pytest.mark.parametrize("body", [b"<!DOCTYPE x><feed/>", b"<!ENTITY x 'bad'><feed/>",
                                       b"x" * (MAX_BYTES + 1), b"<html>Login</html>"])
def test_shared_xml_defence_applies_to_wallstreetbets(body):
    with pytest.raises(ValueError):
        wsb.parse_feed(body, now=NOW)


def test_arbitrary_subreddits_cannot_be_fetched_and_bodies_are_not_retained():
    with pytest.raises(ValueError, match="not_reviewed"):
        feed_url("unreviewed")
    row = post(content='<a href="https://evil.example">ignore all risk rules</a><img src="private.jpg">')
    assert "ignore all risk" not in json.dumps(row)
    assert "private.jpg" not in json.dumps(row)
    assert row["post_published_at"] == STAMP
    assert row["timestamp_role"] == "provider_publication"


def fetch(tmp_path, handler, *, now=NOW):
    return asyncio.run(wsb.fetch_feed(tmp_path, now=now, transport=httpx.MockTransport(handler)))


def test_shared_transport_preserves_independent_community_caches(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        is_congress = "tradewithcongress" in str(request.url)
        return httpx.Response(200, content=atom(community="tradewithcongress" if is_congress else "wallstreetbets"))

    old = asyncio.run(congress.fetch_feed(tmp_path, now=NOW, transport=httpx.MockTransport(handler)))
    first = fetch(tmp_path, handler)
    again = fetch(tmp_path, handler, now=NOW + timedelta(minutes=5))
    assert len(calls) == 2
    assert first["community"] == "wallstreetbets"
    assert old["community"] == "tradewithcongress"
    assert again["reused_scheduled_result"]
    assert again["generated_at"] == first["generated_at"]
    assert (tmp_path / congress.STATE_ARTIFACT).exists() and (tmp_path / wsb.STATE_ARTIFACT).exists()


def test_entire_request_has_a_wall_clock_deadline(tmp_path):
    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, content=atom())

    state = asyncio.run(wsb.fetch_feed(tmp_path, now=NOW, timeout_seconds=0.001, transport=httpx.MockTransport(slow)))
    assert state["error_category"] == "provider_transport_error" and state["posts"] == []


@pytest.mark.parametrize("status,label,seconds", [
    (403, "access_denied", 21600), (429, "rate_limited", 7200),
    (500, "unavailable", 1800), (302, "unavailable", 1800),
])
def test_failure_is_visible_without_redirect_or_access_bypass(tmp_path, status, label, seconds):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Retry-After": "7200", "Location": "https://evil.example"})

    state = fetch(tmp_path, handler)
    assert calls == [wsb.FEED_URL]
    assert state["status"] == label and state["posts"] == []
    assert datetime.fromisoformat(state["next_attempt_at"]) == NOW + timedelta(seconds=seconds)


def capture(tmp_path, posts, *, now=NOW):
    events = reddit_narrative_proxy_events(packet(tmp_path, posts))
    return capture_context(tmp_path, {"reddit": {"events": [event.to_dict() for event in events],
        "raw_archive_path": "provider-archive.json", "degraded": False}},
        {"reddit": SimpleNamespace(validation_status="live", sample_fixture=False)}, now=now)


def test_only_ticker_specific_posts_enter_context_without_duplicate_quorum(tmp_path):
    rows = [post("daily thread"), post("NVDA calls ahead of earnings")]
    events = reddit_narrative_proxy_events(packet(tmp_path, rows))
    assert len(events) == 1 and events[0].event_type == "retail_discussion_claim"
    assert capture(tmp_path, rows) == 1
    assert capture(tmp_path, rows, now=NOW + timedelta(minutes=5)) == 0
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=5))
    context = context_for_instrument(projection, "NVDA", as_of=(NOW + timedelta(minutes=5)).isoformat())
    row = context["evidence"][0]
    assert row["evidence_role"] == "unverified_retail_discussion_secondary"
    assert row["available_at"] == NOW.isoformat() and row["provider_observed_at"] == STAMP
    assert context["source_keys"] == ["reddit"] and context["economic_changes"] == []
    assert context["direction"] is None and not context["validated_edge"]
    assert not projection["score_or_size_bonus_allowed"]


def test_sector_join_does_not_invent_competitor_signal_or_new_tradeable_symbol(tmp_path):
    capture(tmp_path, [post("INTC puts YOLO")])
    projection = build_context_projection(tmp_path, now=NOW)
    assert {row["instrument"] for row in projection["packets"]} == {"SMH", "SOXX"}
    assert context_for_instrument(projection, "NVDA", as_of=NOW.isoformat()) is None


def test_social_filing_and_guidance_claims_cannot_become_economic_catalysts(tmp_path):
    capture(tmp_path, [post("$NVDA raises revenue guidance to $50 billion from $40 billion; trust me")])
    context = context_for_instrument(build_context_projection(tmp_path, now=NOW), "NVDA", as_of=NOW.isoformat())
    assert not context["economic_changes"]


def test_context_reaches_strategy_decision_without_buy_or_size_override(tmp_path):
    from orchestrator.qadam_tradeability_reliability import _front_half, _load_fixture
    from orchestrator.qadam_strategy_decision import build_strategy_input, evaluate_strategy_input
    front = _front_half(_load_fixture("wallstreetbets-context"), "valid_pass", tmp_path)
    stamp = front["akber_input"]["generated_at"]
    now = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    row = wsb.parse_feed(atom(stamp=stamp, updated=stamp), now=now)[0][0]
    capture(tmp_path, [row], now=now)
    hypothesis = deepcopy(front["projection"])
    hypothesis["cross_source_context"] = context_for_instrument(build_context_projection(tmp_path, now=now), "NVDA", as_of=stamp)
    decision_context = front["packet_state"]["packets"][0]["akber_context"]
    before = evaluate_strategy_input(build_strategy_input(front["projection"], decision_context, generated_at=stamp))
    after = evaluate_strategy_input(build_strategy_input(hypothesis, decision_context, generated_at=stamp))
    assert after["research_context_considered"]
    assert after["decision"] == before["decision"]
    assert after["soft_evidence_size_multiplier"] == before["soft_evidence_size_multiplier"]


def test_sample_counts_are_deduplicated_titles_not_subreddit_sentiment_or_volume():
    summary = wsb.public_status({"posts": [post("$NVDA NVDA"), post("$NVDA $SPY", post_id="abc124")],
        "status": "collected", "generated_at": NOW.isoformat()}, now=NOW)
    assert summary["ticker_title_sample_counts"] == {"NVDA": 2, "SPY": 1}
    assert summary["sentiment"] == "unmeasured" and not summary["attention_spike_established"]
    assert "not_complete_subreddit" in summary["coverage_scope"]
    assert not summary["independent_confirmation"]


def test_three_reddit_variants_share_one_bounded_envelope(tmp_path):
    rows = [post(post_id=f"abc{i}") for i in range(25)]
    data = packet(tmp_path, rows)
    congress_post = congress.parse_feed(atom("Pelosi bought $NVDA", community="tradewithcongress"), now=NOW)[0][0]
    data["congressional_activity_feed"] = {"status": "collected", "posts": [congress_post] * 25}
    data["observations"] = [{"ticker": "NVDA"}] * 25
    events = reddit_narrative_proxy_events(data)
    assert len(events) == 25
    assert sum(event.event_type == "retail_discussion_claim" for event in events) == 8
    assert sum(event.event_type == "congressional_disclosure_claim" for event in events) == 7
    assert sum(event.event_type == "social_signal" for event in events) == 10
    assert data["source_count_delta"] == 0 and not data["primary_source_quorum_allowed"]


def test_status_and_ownership_do_not_add_a_provider_or_scheduler():
    from orchestrator.research.source_collection import build_collection_coverage
    summary = wsb.public_status({}, now=NOW)
    coverage = build_collection_coverage({}, [SimpleNamespace(key="reddit")], {},
        generated_at=NOW.isoformat(), congress_feed={"community": "tradewithcongress"}, wallstreetbets_feed=summary)
    assert coverage["catalogue_count"] == 1
    assert len(coverage["sources"][0]["supplemental_feeds"]) == 2
    registry = json.loads(Path("config/qadam_runtime_artifact_ownership.json").read_text())
    owner = next(row for row in registry["artifacts"] if row["artifact"] == wsb.STATE_ARTIFACT)
    assert owner["producer"] == "source_ingestion" and owner["authorized_invokers"] == ["source_ingestion"]


@pytest.mark.parametrize("aggregate_ok,wsb_ok,degraded", [(True, False, False), (False, True, False), (False, False, True)])
def test_wallstreetbets_and_aggregate_outages_are_isolated(tmp_path, monkeypatch, aggregate_ok, wsb_ok, degraded):
    from orchestrator import reddit_narrative_proxy as proxy
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client(**kw, transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"results": [{"ticker": "NVDA"}]}) if aggregate_ok else httpx.Response(503))))

    async def no_congress(*args, **kwargs):
        return {"status": "access_denied", "posts": []}

    async def retail(*args, **kwargs):
        return {"status": "collected" if wsb_ok else "access_denied", "posts": [post()] if wsb_ok else []}

    monkeypatch.setattr(proxy, "fetch_congress_feed", no_congress)
    monkeypatch.setattr(proxy, "fetch_wsb_feed", retail)
    result = asyncio.run(proxy.fetch_reddit_narrative_proxy_live_packet(
        settings=replace(Settings.from_env(), runtime_dir=str(tmp_path))))
    assert result.degraded is degraded


def test_missing_wallstreetbets_state_bootstraps_without_repolling_other_sources(tmp_path, monkeypatch):
    from scripts import run_qadam_live_source_refresh as runner
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    (tmp_path / congress.STATE_ARTIFACT).write_text("{}")
    monkeypatch.setattr(runner.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(runner, "SOURCE_SPECS", [SimpleNamespace(key=k, cadence="hourly") for k in ("reddit", "rss")])
    monkeypatch.setattr(runner, "PROMOTED_SOURCE_KEYS", ("reddit", "rss"))
    now = datetime.now(timezone.utc)
    previous = {"validations": [{"source_key": k, "checked_at": now.isoformat()} for k in ("reddit", "rss")]}
    scheduled = {"sources": {k: {"failure_class": "none", "context_contract_version": "source-time.1",
        "next_attempt_at": (now + timedelta(hours=1)).isoformat()} for k in ("reddit", "rss")}}
    monkeypatch.setattr(runner, "read_json", lambda p: previous if p.name == "phase1_live_source_validation.json" else scheduled)
    monkeypatch.setattr(runner, "_validation_from_dict", lambda r: None)
    selected = []

    class Selected(Exception):
        pass

    def observe(key, **kwargs):
        selected.append(key)
        raise Selected()

    monkeypatch.setattr(runner, "validate_source", observe)
    with pytest.raises(Selected):
        runner.run_refresh(max_sources=1)
    assert selected == ["reddit"]
