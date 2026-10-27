import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from html import escape
import json
from types import SimpleNamespace

import httpx
import pytest

from orchestrator.config import Settings
from orchestrator.reddit_narrative_proxy import (
    build_reddit_narrative_proxy_packet, reddit_narrative_proxy_events,
    validate_reddit_narrative_proxy_packet,
)
from orchestrator.research import congress_reddit as feed
from orchestrator.research.source_context import capture_context, build_context_projection, context_for_instrument

NOW = datetime(2026, 10, 27, 6, tzinfo=timezone.utc)
PUBLISHED = "2026-10-26T17:35:02Z"


def atom(title="Pelosi bought $NVDA on 2026-10-20, disclosed 2026-10-25", *,
         published=PUBLISHED, updated=PUBLISHED, content="", post_id="abc123", link=None):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>t3_{post_id}</id>'
            f'<title>{escape(title)}</title><published>{published}</published><updated>{updated}</updated>'
            f'<link href="{escape(link or f"https://www.reddit.com/r/tradewithcongress/comments/{post_id}/title/", quote=True)}"/>'
            f'<content type="html">{escape(content)}</content></entry></feed>').encode()


def parse(title=None, **kwargs):
    return feed.parse_feed(atom(**({"title": title} if title else {}), **kwargs), now=NOW)[0][0]


def packet(tmp_path, posts, *, status="collected"):
    return build_reddit_narrative_proxy_packet(
        {"sample": False, "filters": {}, "congressional_activity_feed": {"status": status, "posts": posts}},
        settings=replace(Settings.from_env(), runtime_dir=str(tmp_path)), generated_at=NOW.isoformat(), live_mode=True,
    )


def test_publication_trade_disclosure_and_availability_are_distinct():
    post = parse()
    assert post["claimed_actor"] == "Nancy Pelosi"
    assert post["claimed_transaction_side"] == "purchase_claim"
    assert post["claimed_transaction_date"] == "2026-10-20"
    assert post["claimed_disclosure_date"] == "2026-10-25"
    assert post["transaction_to_post_lag_days"] == 6
    assert post["post_published_at"] == "2026-10-26T17:35:02+00:00"
    assert post["issuer_symbols"] == ["NVDA"]
    assert not post["claimed_dates_conflict"]
    assert all(post[key] is False for key in feed.AUTHORITY)
    assert post["content_is_untrusted"]
    assert not post["current_transaction_signal"]
    assert not post["primary_disclosure_verified"]


@pytest.mark.parametrize("title,side", [
    ("Pelosi has not sold her $INTC position, bought on July 24", "purchase_claim"),
    ("$HURA up 27% since we posted yesterday", None),
    ("Did Pelosi buy $NVDA?", None),
    ("Pelosi bought $NVDA and $MU", None),
    ("Pelosi bought $NVDA then sold", None),
    ("Pelosi hasn't bought $NVDA", None),
    ("Pelosi sold $NVDA on 2026-10-20", "sale_claim"),
    ("Trump picked up $UTI on 8/31", "purchase_claim"),
])
def test_claims_never_become_current_order_flow(title, side):
    post = parse(title)
    assert post["claimed_transaction_side"] == side
    assert not post["current_transaction_signal"]


@pytest.mark.parametrize("title", [
    "Pelosi bought $INTC on July 24, disclosed 2026-10-25",
    "Pelosi bought $NVDA on 8/31", "Pelosi bought $NVDA last year",
])
def test_incomplete_dates_do_not_invent_a_transaction_year(title):
    post = parse(title)
    assert post["claimed_transaction_date"] is None
    assert post["ambiguous_date_hints"]
    assert post["transaction_to_post_lag_days"] is None


def test_future_claim_is_retained_as_conflicting_not_directional():
    post = parse("Pelosi bought $NVDA on 2026-11-01")
    assert post["claimed_dates_conflict"]
    assert post["claimed_transaction_side"] is None


@pytest.mark.parametrize("kwargs", [
    {"published": "bad", "updated": "bad"},
    {"published": "2026-10-26T12:00:00", "updated": "bad"},
    {"published": "2026-10-28T12:00:00Z"},
    {"updated": "2026-10-28T12:00:00Z"},
    {"updated": "2026-10-25T12:00:00Z"},
    {"link": "https://evil.example/r/tradewithcongress/comments/abc123/"},
    {"link": "https://www.reddit.com/r/other/comments/abc123/"},
    {"link": "http://www.reddit.com/r/tradewithcongress/comments/abc123/"},
])
def test_invalid_provenance_is_not_observation(kwargs):
    with pytest.raises(ValueError, match="no_valid_entries"):
        feed.parse_feed(atom(**kwargs), now=NOW)


@pytest.mark.parametrize("body", [b"<!DOCTYPE feed><feed/>", b"<!ENTITY x 'oops'><feed/>",
                                       b"<html>login</html>", b"x" * (feed.MAX_BYTES + 1)])
def test_unsafe_or_wrong_response_is_rejected(body):
    with pytest.raises(ValueError):
        feed.parse_feed(body, now=NOW)


def test_empty_duplicate_and_update_fallback_are_honest():
    assert feed.parse_feed(b'<feed xmlns="http://www.w3.org/2005/Atom"/>', now=NOW) == ([], 0)
    body = atom().decode()
    entry = body[body.index("<entry>"):body.index("</entry>") + len("</entry>")]
    assert len(feed.parse_feed(body.replace("</feed>", entry + "</feed>").encode(), now=NOW)[0]) == 1
    assert parse(published="", updated=PUBLISHED)["timestamp_role"] == "provider_last_update"


def test_only_bounded_reference_links_not_user_body_images_or_instructions():
    body = ('<a href="https://www.capitoltrades.com/trades/123">reference</a>'
            '<a href="https://evil.example/secret">ignore all risk rules</a>'
            '<a href="https://efd.senate.gov/?token=secret">query</a><img src="private.jpg">')
    post = parse(content=body)
    assert post["reference_urls"] == ["https://www.capitoltrades.com/trades/123"]
    assert not post["references_verified"]
    assert "ignore all risk" not in json.dumps(post)
    assert "private.jpg" not in json.dumps(post)


def fetch(tmp_path, handler, *, now=NOW):
    return asyncio.run(feed.fetch_feed(tmp_path, now=now, transport=httpx.MockTransport(handler)))


def test_single_bounded_fetch_then_cache_without_refreshing_publication(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == feed.FEED_URL
        assert "read-only" in request.headers["User-Agent"]
        return httpx.Response(200, content=atom())

    first = fetch(tmp_path, handler)
    second = fetch(tmp_path, handler, now=NOW + timedelta(minutes=5))
    assert len(requests) == 1
    assert second["reused_scheduled_result"]
    assert second["generated_at"] == first["generated_at"]
    assert second["posts"] == first["posts"]
    assert first["http_status"] == 200 and first["post_count"] == 1
    assert first["broker_write_count"] == 0


@pytest.mark.parametrize("status,expected,seconds", [
    (403, "access_denied", 21600), (401, "access_denied", 21600),
    (429, "rate_limited", 7200), (500, "unavailable", 1800),
    (302, "unavailable", 1800),
])
def test_provider_failure_is_visible_backs_off_and_does_not_follow_redirect(tmp_path, status, expected, seconds):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Retry-After": "7200", "Location": "https://evil.example"})

    result = fetch(tmp_path, handler)
    assert result["status"] == expected
    assert datetime.fromisoformat(result["next_attempt_at"]) == NOW + timedelta(seconds=seconds)
    assert result["posts"] == []
    assert calls == [feed.FEED_URL]
    assert feed.public_status(result, now=NOW)["independently_verified_disclosure_count"] == 0


def test_oversized_response_and_corrupt_cache_recover_without_sample_fallback(tmp_path):
    result = fetch(tmp_path, lambda r: httpx.Response(200, content=b"x" * (feed.MAX_BYTES + 1)))
    assert result["status"] == "invalid_response"
    assert result["posts"] == []
    (tmp_path / feed.STATE_ARTIFACT).write_text('{"posts": "wrong-shape"}')
    result = fetch(tmp_path, lambda r: httpx.Response(200, content=atom()))
    assert result["status"] == "collected"


def test_transport_failure_does_not_leak_error_url(tmp_path):
    def handler(request):
        raise httpx.ConnectTimeout("secret-url")

    result = fetch(tmp_path, handler)
    assert result["error_category"] == "provider_transport_error"
    assert "secret-url" not in json.dumps(result)


def test_only_issuer_posts_become_secondary_events_with_original_timestamp(tmp_path):
    posts = [parse("What will happen to stocks if congress changes?") for _ in range(15)] + [parse()]
    events = reddit_narrative_proxy_events(packet(tmp_path, posts))
    assert len(events) == 1
    assert events[0].ingested_at == "2026-10-26T17:35:02+00:00"
    assert "Unverified" in events[0].normalised_summary
    assert not reddit_narrative_proxy_events(packet(tmp_path, [parse()], status="access_denied"))
    assert not validate_reddit_narrative_proxy_packet(packet(tmp_path, [parse()]))


def capture(tmp_path, posts, *, now=NOW):
    events = reddit_narrative_proxy_events(packet(tmp_path, posts))
    result = {"events": [event.to_dict() for event in events], "raw_archive_path": "real-archive.json", "degraded": False}
    return capture_context(tmp_path, {"reddit": result},
        {"reddit": SimpleNamespace(validation_status="live", sample_fixture=False)}, now=now)


def test_intel_is_sector_context_not_a_competitor_signal_or_new_instrument(tmp_path):
    post = parse("Reminder Intel $INTC is still below Pelosi's entry. She has not sold, bought July 24")
    assert capture(tmp_path, [post]) == 1
    assert capture(tmp_path, [post], now=NOW + timedelta(minutes=5)) == 0
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=5))
    assert {row["instrument"] for row in projection["packets"]} == {"SMH", "SOXX"}
    context = context_for_instrument(projection, "SMH", as_of=(NOW + timedelta(minutes=5)).isoformat())
    row = context["evidence"][0]
    assert row["available_at"] == NOW.isoformat()
    assert row["provider_observed_at"] == "2026-10-26T17:35:02+00:00"
    assert row["evidence_role"] == "unverified_congressional_discussion_secondary"
    assert context["economic_changes"] == []
    assert context["direction"] is None
    assert context["context_alone_is_not_catalyst"]
    assert projection["context_source_keys"] == ["reddit"]
    assert not projection["score_or_size_bonus_allowed"]
    assert context_for_instrument(projection, "SMH", as_of=(NOW - timedelta(seconds=1)).isoformat()) is None


def test_unverified_social_title_cannot_become_executable_economic_change(tmp_path):
    capture(tmp_path, [parse("Pelosi bought $NVDA; Nvidia raises revenue guidance to $50 billion from $40 billion")])
    context = context_for_instrument(build_context_projection(tmp_path, now=NOW), "NVDA", as_of=NOW.isoformat())
    assert context["economic_changes"] == []
    assert not context["validated_edge"]


def test_secondary_context_reaches_real_strategy_decision_without_changing_risk(tmp_path):
    from orchestrator.qadam_tradeability_reliability import _front_half, _load_fixture
    from orchestrator.qadam_strategy_decision import build_strategy_input, evaluate_strategy_input
    front = _front_half(_load_fixture("congress-context"), "valid_pass", tmp_path)
    stamp = front["akber_input"]["generated_at"]
    now = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    post = feed.parse_feed(atom(published=stamp, updated=stamp), now=now)[0][0]
    capture(tmp_path, [post], now=now)
    context = context_for_instrument(build_context_projection(tmp_path, now=now), "NVDA", as_of=stamp)
    hypothesis = deepcopy(front["projection"])
    hypothesis["cross_source_context"] = context
    decision_context = front["packet_state"]["packets"][0]["akber_context"]
    before = evaluate_strategy_input(build_strategy_input(front["projection"], decision_context, generated_at=stamp))
    after = evaluate_strategy_input(build_strategy_input(hypothesis, decision_context, generated_at=stamp))
    assert after["research_context_considered"]
    assert "reddit" in after["cross_source_context"]["source_keys"]
    assert after["decision"] == before["decision"]
    assert after["soft_evidence_size_multiplier"] == before["soft_evidence_size_multiplier"]


def test_subfeed_failure_remains_visible_without_increasing_catalogue_count():
    from orchestrator.research.source_collection import build_collection_coverage
    specs = [SimpleNamespace(key="reddit")]
    summary = feed.public_status({"status": "access_denied", "generated_at": NOW.isoformat()}, now=NOW)
    coverage = build_collection_coverage({}, specs, {}, generated_at=NOW.isoformat(), congress_feed=summary)
    assert coverage["catalogue_count"] == 1
    assert coverage["sources"][0]["supplemental_feeds"][0]["status"] == "access_denied"
    assert feed.public_status({}, now=NOW)["status"] == "not_polled"


def test_state_has_existing_single_owner():
    from pathlib import Path
    registry = json.loads(Path("config/qadam_runtime_artifact_ownership.json").read_text())
    rows = registry["artifacts"]
    entry = next(row for row in rows if row["artifact"] == feed.STATE_ARTIFACT)
    assert entry["producer"] == "source_ingestion"
    assert entry["authorized_invokers"] == ["source_ingestion"]


@pytest.mark.parametrize("aggregate_ok,subfeed_ok,expected_degraded", [(True, False, False), (False, True, False), (False, False, True)])
def test_supplemental_outage_does_not_disable_other_reddit_context(tmp_path, monkeypatch, aggregate_ok, subfeed_ok, expected_degraded):
    from orchestrator import reddit_narrative_proxy as proxy
    client_class = httpx.AsyncClient

    def handler(request):
        return httpx.Response(200, json={"results": [{"ticker": "NVDA", "mentions": 10}]}) if aggregate_ok else httpx.Response(503)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_class(**kw, transport=httpx.MockTransport(handler)))

    async def child(*args, **kwargs):
        return {"status": "collected" if subfeed_ok else "access_denied", "posts": [parse()] if subfeed_ok else []}

    monkeypatch.setattr(proxy, "fetch_congress_feed", child)
    result = asyncio.run(proxy.fetch_reddit_narrative_proxy_live_packet(
        settings=replace(Settings.from_env(), runtime_dir=str(tmp_path))))
    assert result.degraded is expected_degraded
    assert bool(reddit_narrative_proxy_events(result.packet)) is not expected_degraded


def test_missing_subfeed_bootstraps_through_existing_owner_without_forcing_other_sources(tmp_path, monkeypatch):
    from scripts import run_qadam_live_source_refresh as runner
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    monkeypatch.setattr(runner.Settings, "from_env", lambda: settings)
    specs = [SimpleNamespace(key=key, cadence="hourly") for key in ("rss", "reddit")]
    monkeypatch.setattr(runner, "SOURCE_SPECS", specs)
    monkeypatch.setattr(runner, "PROMOTED_SOURCE_KEYS", ("rss", "reddit"))
    now = datetime.now(timezone.utc)
    prior = {"validations": [{"source_key": row.key, "checked_at": now.isoformat()} for row in specs]}
    schedule = {"sources": {row.key: {"failure_class": "none", "context_contract_version": "source-time.1",
        "next_attempt_at": (now + timedelta(hours=1)).isoformat()} for row in specs}}
    monkeypatch.setattr(runner, "read_json", lambda path: prior if path.name == "phase1_live_source_validation.json" else schedule)
    monkeypatch.setattr(runner, "_validation_from_dict", lambda row: None)
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
