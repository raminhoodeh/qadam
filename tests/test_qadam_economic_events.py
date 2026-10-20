import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from orchestrator.research.economic_events import (
    VERSION, classify_event, extract_changes, instrument_interpretation,
)
from orchestrator.research.source_context import capture_context, build_context_projection
from orchestrator.research.sec_content import enrich_recent_filing, filing_candidate, extract_filing_quotes
from orchestrator.research.source_payloads import provider_records
from orchestrator.research.focus import rank_programmes
from orchestrator.qadam_trigger_factory import build_event_triggers
from orchestrator.qadam_strategy_translation import resolve_direction

NOW = datetime(2026, 10, 21, 14, tzinfo=timezone.utc)
SEMIS = "semiconductor_policy_options_asymmetry"
ENERGY = "crude_oil_energy_security_disruption"


@pytest.mark.parametrize("text,impact,metric", [
    ("NVIDIA raised revenue guidance from $30 billion to $32 billion.", "positive", "guidance"),
    ("NVIDIA cut revenue guidance from $32 billion to $30 billion.", "negative", "guidance"),
    ("TSMC margins declined from 55% to 50%.", "negative", "margin"),
    ("Micron orders increased from 10 million to 12 million.", "positive", "orders"),
    ("NVIDIA may raise revenue guidance.", "unresolved", "guidance"),
    ("NVIDIA did not raise revenue guidance.", "unresolved", "guidance"),
    ("NVIDIA denied a cut in revenue guidance.", "unresolved", "guidance"),
    ("NVIDIA revenue guidance is unchanged.", "unresolved", "guidance"),
    ("NVIDIA increased capex from $3 billion to $4 billion.", "unresolved", "capex"),
    ("TSMC capacity expanded.", "unresolved", "capacity"),
    ("NVIDIA inventories grew.", "unresolved", "inventory"),
    ("NVIDIA increased cost guidance.", "unresolved", "guidance"),
])
def test_financial_metric_is_not_generic_sentiment(text, impact, metric):
    feature, = extract_changes(text, family="semiconductors")
    assert feature["metric"] == metric
    assert feature["economic_impact"] == impact
    span = feature["supporting_span"]
    assert text[span["start"]:span["end"]] == span["text"]
    assert feature["expected_return"] is None
    assert feature["extraction_probability"] is None
    assert not feature["paper_order_allowed"]


@pytest.mark.parametrize("text,impact,shock", [
    ("Crude oil production fell from 5 million to 4 million.", "positive", "reported_physical_supply_change"),
    ("Crude oil production resumed.", "negative", "reported_physical_supply_change"),
    ("Oil demand fell.", "negative", "reported_demand_change"),
    ("Oil demand increased.", "positive", "reported_demand_change"),
    ("Oil production could fall.", "unresolved", "reported_physical_supply_change"),
    ("Oil production did not fall.", "unresolved", "reported_physical_supply_change"),
])
def test_energy_separates_supply_loss_normalization_and_demand(text, impact, shock):
    feature, = extract_changes(text, family="energy_supply")
    assert feature["economic_impact"] == impact
    assert feature["shock_type"] == shock


def test_numeric_comparison_is_same_statement_not_consensus_or_mixed_units():
    row, = extract_changes("NVIDIA revenue increased from $30 billion to $33 billion.", family="semiconductors")
    assert row["comparison"]["relative_change"] == pytest.approx(.1)
    assert row["comparison"]["delta"] == 3
    assert row["comparison"]["consensus_surprise"] is None
    mixed, = extract_changes("NVIDIA revenue increased from $3 million to $4 billion.", family="semiconductors")
    assert mixed["comparison"]["delta"] is None
    assert mixed["comparison"]["basis"] == "incompatible_or_unspecified_units"


def test_issuer_change_not_transferred_to_competitor_or_etf():
    classification = classify_event(SEMIS, "NVIDIA raised revenue guidance.")
    assert instrument_interpretation(classification, "NVDA")["direction_clue"] == "positive_for_strategy_expression"
    assert not instrument_interpretation(classification, "TSM")["eligible_subject"]
    assert instrument_interpretation(classification, "SMH")["direction_clue"] == "ambiguous"
    assert instrument_interpretation(classification, "SMH")["market_confirmation_required"]
    unknown = classify_event(SEMIS, "Qualcomm revenue increased.")
    assert instrument_interpretation(unknown, "NVDA")["direction_clue"] == "ambiguous"
    assert instrument_interpretation(unknown, "NVDA")["market_confirmation_required"]


@pytest.mark.parametrize("text", ["Natural gas production fell.", "Crude oil refinery production fell."])
def test_other_commodities_and_refining_are_not_mechanically_oil_supply_shocks(text):
    row, = extract_changes(text, family="energy_supply")
    assert row["economic_impact"] == "unresolved"
    assert row["shock_type"] == "commodity_or_refining_basis_requires_interpretation"


def trigger_inputs(text, *, symbols=None, family=SEMIS):
    goal = {"goal_id": "g1", "origin": "live_source", "created_at": NOW.isoformat(),
            "hypothesis": text, "source_event_refs": ["rss:e1"]}
    market = {"recent_packets": [{"research_goal_id": "g1", "research_goal_origin": "live_source",
        "market_channel": "semiconductors" if family == SEMIS else "energy_transport",
        "watched_instruments": symbols or ["NVDA", "TSM", "SMH"], "generated_at": NOW.isoformat(),
        "source_taxonomy": [{"source_key": "rss", "observed_in_goal": True}], "hypothesis": text}]}
    contract = {"sources": [{"source_key": "rss", "canonical_source_key": "rss",
        "availability_state": "live_fresh", "allowed_roles": ["current_trigger"], "trust_score": .78}]}
    return market, [goal], contract


def test_live_event_path_uses_economic_direction_and_issuer_scope():
    market, goals, contract = trigger_inputs("NVIDIA semiconductor revenue guidance increased from $30 billion to $32 billion.")
    events, rejected = build_event_triggers(market, goals, contract, generated_at=NOW.isoformat())
    assert not rejected
    assert events[0]["affected_instruments"] == ["NVDA", "SMH"]
    score = {"score_id": "score1", "strategy_family_id": SEMIS,
             "instrument": "NVDA", "direction_hypothesis": "conditional_policy_asymmetry"}
    result = resolve_direction(score, events, [], [], generated_at=NOW.isoformat())
    assert result["actionable_direction"] == "long"
    result = resolve_direction({**score, "instrument": "SMH"}, events, [], [], generated_at=NOW.isoformat())
    assert result["actionable_direction"] == "abstain_direction_unresolved"
    assert events[0]["causal_classification"]["classifier"] == VERSION


def test_negated_change_cannot_fall_through_to_legacy_keyword_buy():
    inputs = trigger_inputs("NVIDIA semiconductor revenue guidance did not increase.")
    events, rejected = build_event_triggers(*inputs, generated_at=NOW.isoformat())
    assert events == []
    assert rejected[0]["reasons"] == ["cited_economic_change_negated_or_unchanged"]


def test_mixed_economic_clauses_not_outvoted_by_positive_words():
    row = classify_event(SEMIS, "NVIDIA revenue increased. NVIDIA margins declined.")
    assert row["direction_clue"] == "ambiguous"


def test_context_features_have_durable_first_seen_and_no_score_or_size_bonus(tmp_path):
    event = {"normalised_summary": "NVIDIA raised revenue guidance from $30 billion to $32 billion.",
        "ingested_at": NOW.isoformat(), "raw_payload": {"record_id": "actual-report"}}
    captured = {"rss": {"events": [event], "raw_archive_path": "raw-archive.json", "degraded": False}}
    validations = {"rss": SimpleNamespace(validation_status="live", sample_fixture=False)}
    assert capture_context(tmp_path, captured, validations, now=NOW) == 1
    assert capture_context(tmp_path, captured, validations, now=NOW + timedelta(minutes=1)) == 0
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=1))
    packet = next(row for row in projection["packets"] if row["instrument"] == "NVDA")
    feature, = packet["economic_changes"]
    assert feature["available_at"] == NOW.isoformat()
    assert feature["receipt_ref"] in packet["receipt_refs"]
    assert feature["comparison"]["current_value"] == 32
    assert packet["expected_return"] is None
    assert projection["score_or_size_bonus_allowed"] is False
    tsm = next(row for row in projection["packets"] if row["instrument"] == "TSM")
    assert tsm["economic_changes"] == []


def sec_index():
    return {"cik": "1045810", "name": "NVIDIA", "tickers": ["NVDA"], "filings": {"recent": {
        "accessionNumber": ["0001045810-26-000001"], "acceptanceDateTime": [NOW.isoformat()],
        "primaryDocument": ["nvda-report.htm"], "form": ["10-Q"], "filingDate": ["2026-10-21"]}}}


@pytest.mark.parametrize("filename", ["../escape.htm", "https://evil.com/report.htm", "a.htm?url=x", "report.pdf"])
def test_sec_never_follows_untrusted_filename_or_backdates_old_report(filename):
    payload = sec_index()
    payload["filings"]["recent"]["primaryDocument"] = [filename]
    assert filing_candidate(payload, now=NOW) is None
    assert filing_candidate(sec_index(), now=NOW + timedelta(days=4)) is None
    assert filing_candidate(sec_index(), now=NOW - timedelta(seconds=1)) is None


def test_sec_strips_scripts_and_keeps_actual_financial_quote():
    html = "<script>NVIDIA revenue increased from 1 million to 2 million.</script><p>Our revenue increased from $30 billion to $32 billion.</p>"
    assert extract_filing_quotes(html, ["NVDA"]) == ["Our revenue increased from $30 billion to $32 billion."]


@pytest.mark.parametrize("status", [200, 403, 429, 302])
def test_sec_bounded_optional_content_cache_and_failure_does_not_poison_index(tmp_path, status):
    calls = []
    def respond(request):
        calls.append(str(request.url))
        assert request.url.host == "www.sec.gov"
        return httpx.Response(status, headers={"content-type": "text/html", "Retry-After": "3600"},
            text="<p>NVIDIA revenue increased from $30 billion to $32 billion.</p>")
    async def run():
        payload = sec_index()
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            for _ in range(2):
                await enrich_recent_filing(client, payload, headers={"User-Agent": "Qadam research admin@example.org"}, runtime=tmp_path, now=NOW)
        return payload
    payload = asyncio.run(run())
    assert len(calls) == 1
    rows = provider_records("sec_edgar", payload)
    if status == 200:
        assert rows[0]["filing_content_verified"]
        assert rows[0]["observed_at"] == NOW.isoformat()
        assert rows[0]["issuer_symbols"] == ["NVDA"]
    else:
        assert payload["_qadam_filing_content_status"] == "document_unavailable"
        assert len(rows) == 1
        assert not rows[0].get("filing_content_verified")


def test_sec_oversized_document_is_not_partial_evidence(tmp_path):
    async def run():
        payload = sec_index()
        transport = httpx.MockTransport(lambda _: httpx.Response(200,
            headers={"content-type": "text/html"}, content=b"x" * 2_000_001))
        async with httpx.AsyncClient(transport=transport) as client:
            await enrich_recent_filing(client, payload, headers={"User-Agent": "Qadam admin@example.org"}, runtime=tmp_path, now=NOW)
        return payload
    payload = asyncio.run(run())
    assert payload["_qadam_filing_content"]["quotes"] == []
    assert payload["_qadam_filing_content"]["error_type"] == "filing_exceeds_bounded_content_budget"


def test_competency_focus_prioritizes_obtainable_semis_energy_not_highest_score():
    families = ["other", SEMIS, ENERGY, "no_access"]
    scores = [{"strategy_family_id": name, "instrument": "SPY", "scoring_as_of": NOW.isoformat(), "raw_pattern_score": .99 if name == "other" else .5} for name in families]
    capability = {"generated_at": NOW.isoformat(), "strategy_source_coverage": [
        {"strategy_family_id": name, "fresh_provider_backed_source_keys": ["rss"]} for name in families[:3]]}
    result = rank_programmes(scores, capability, as_of=NOW.isoformat())
    assert result["selected_families"] == [SEMIS, ENERGY, "other"]
    assert result["other_programmes_retained"] and not result["risk_policy_changed"]
    assert rank_programmes(scores, capability, as_of=(NOW + timedelta(hours=1)).isoformat())["selected_families"] == []
