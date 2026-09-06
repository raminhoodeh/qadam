from datetime import datetime, timedelta, timezone

from orchestrator.research.cache import AnalysisCache
from orchestrator.research.focus import latest_score_rows, rank_programmes


def test_frontier_single_flight_does_not_start_duplicate_paid_work(tmp_path):
    first, second = AnalysisCache(tmp_path, "frontier"), AnalysisCache(tmp_path, "frontier")
    with first.single_flight() as acquired:
        assert acquired is True
        with second.single_flight() as other:
            assert other is False
    with second.single_flight() as recovered:
        assert recovered is True


def test_cache_preserves_inference_time_and_invalidates_input_model_prompt_and_slot(tmp_path):
    cache = AnalysisCache(tmp_path, "frontier")
    now = datetime.now(timezone.utc)
    inputs = {"model": "model-1", "prompt": "prompt-v1", "evidence": "event-1"}
    key = cache.key(inputs, now)
    result = {"status": "accepted", "generated_at": now.isoformat(), "assessment": {"summary": "Observation"}}
    cache.put(key, result)
    reused = cache.get(key, datetime.now(timezone.utc))
    assert reused["generated_at"] == now.isoformat()
    assert reused["new_model_inference_performed"] is False
    for field in inputs:
        assert cache.key({**inputs, field: "changed"}, now) != key
    assert cache.key(inputs, now + timedelta(hours=3)) != key
    assert cache.get(key, now + timedelta(hours=4)) is None


def test_research_focus_uses_provider_coverage_not_just_high_score():
    now = "2026-09-06T00:00:00Z"
    scores = [{"strategy_family_id": name, "raw_pattern_score": value, "instrument": "SPY", "scoring_as_of": now}
              for name, value in [("no_data", .9), ("semi", .64), ("defence", .63), ("power", .5)]]
    capability = {"generated_at": now, "strategy_source_coverage": [
        {"strategy_family_id": name, "fresh_provider_backed_source_keys": ["provider:" + name]}
        for name in ("semi", "defence", "power")]}
    result = rank_programmes(scores, capability, as_of=now)
    assert result["selected_families"] == ["semi", "defence", "power"]
    assert result["risk_policy_changed"] is False
    assert result["subscription_cost_usd"] is None
    assert rank_programmes(scores, capability, as_of="2026-09-06T01:00:00Z")["selected_families"] == []


def test_new_lower_score_replaces_old_peak_and_invalid_times_are_not_current():
    row = {"strategy_family_id": "semi", "instrument": "SMH", "raw_pattern_score": .9,
           "scoring_as_of": "2026-09-06T01:00:00Z"}
    newer = {**row, "raw_pattern_score": .4, "scoring_as_of": "2026-09-06T02:00:00Z"}
    invalid = [{**row, "instrument": "SPY", "scoring_as_of": stamp} for stamp in
               (None, "2026-09-05T00:00:00Z", "2026-09-07T00:00:00Z", "2026-09-06T02:00:00")]
    assert latest_score_rows([newer, row, *invalid], as_of="2026-09-06T03:00:00Z") == [newer]


def test_frontier_context_retains_changed_evidence_even_with_same_score(tmp_path, monkeypatch):
    from orchestrator import qadam_hedge_fund_team_health as health
    now = "2026-09-06T02:00:00Z"
    score = {"strategy_family_id": "semi", "instrument": "SMH", "raw_pattern_score": .6,
             "scoring_as_of": now, "generated_at": now, "input_fingerprint": "old"}
    capability = {"generated_at": now, "strategy_source_coverage": [
        {"strategy_family_id": "semi", "fresh_provider_backed_source_keys": ["sec"]}]}
    monkeypatch.setattr(health, "now_iso", lambda: now)
    monkeypatch.setattr(health, "read_jsonl", lambda *args, **kwargs: [score])
    monkeypatch.setattr(health, "read_json", lambda path: capability if path.name == "qadam_source_capability_registry.json" else {})
    first = health._frontier_context(tmp_path, {})
    score["input_fingerprint"] = "new"
    second = health._frontier_context(tmp_path, {})
    assert first["highest_ranked_patterns"][0]["research_score"] == second["highest_ranked_patterns"][0]["research_score"]
    assert first != second
