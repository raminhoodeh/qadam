from orchestrator import qadam_graph_pattern_discovery as graph
from orchestrator.research.discovery_coverage import build_discovery_coverage


def test_coverage_distinguishes_catalogue_membership_from_real_discovery_inputs():
    keys = ["rss", "bls", "missing_mapping", "alias", "telegram", "unavailable"]
    sources = [{"source_key": key} for key in keys]
    pairs = [{"source_key": key, "instrument": "SPY", "mapping_class": "broad_discovery_mapping"}
             for key in ["rss", "bls", "telegram", "unavailable"]]
    scores = [{"feature_inputs": [{"source_key": key, "fresh": key == "rss"}
                                   for key in ["rss", "bls", "telegram", "unavailable"]]}]
    collection = {"sources": [
        {"source_key": key, "collection_status": "collected", "observation_count": 2,
         "collection_evidence_state": "provider_observations"} for key in ["rss", "bls", "missing_mapping"]
    ] + [
        {"source_key": "alias", "collection_status": "derived_alias", "upstream_sources": ["rss"]},
        {"source_key": "telegram", "collection_status": "collected", "collection_evidence_state": "operational_only"},
        {"source_key": "unavailable", "collection_status": "needs_configuration"},
    ]}
    coverage = build_discovery_coverage(sources, [{"symbol": "SPY"}], pairs, scores, collection)
    rows = {row["source_key"]: row for row in coverage["sources"]}
    assert coverage["catalogue_source_count"] == 6
    assert coverage["expected_pair_count"] == 6
    assert coverage["evaluated_pair_count"] == 4
    assert coverage["unmapped_collected_source_keys"] == ["missing_mapping"]
    assert rows["rss"]["discovery_state"] == "fresh_input_in_pattern_research"
    assert rows["bls"]["discovery_state"] == "mapped_context_not_fresh_event_evidence"
    assert rows["alias"]["discovery_state"] == "derived_alias_not_independent_evidence"
    assert rows["telegram"]["discovery_state"] == "operational_connection_not_research_feed"
    assert rows["unavailable"]["discovery_state"] == "waiting_for_collection"
    assert coverage["pattern_research_grants_order_authority"] is False


def test_negative_control_does_not_count_as_discovery_coverage():
    coverage = build_discovery_coverage(
        [{"source_key": "rss"}], [{"symbol": "SPY"}],
        [{"source_key": "rss", "instrument": "SPY", "mapping_class": "negative_control"}],
        [{"negative_control": True, "feature_inputs": [{"source_key": "rss", "fresh": True}]}],
        {"sources": [{"source_key": "rss", "collection_status": "collected", "observation_count": 1}]},
    )
    assert coverage["unmapped_collected_source_keys"] == ["rss"]


def test_actionable_pattern_is_not_cut_before_actionability_ranking(monkeypatch, tmp_path):
    class Store:
        def __init__(self, settings):
            pass

        def append(self, records):
            return {"written": len(records), "duplicates": 0}

        def rebuild(self):
            return {"generation_id": "fixture"}

    scores = [{
        "instrument": f"TEST{i}", "strategy_family_id": "inactive", "raw_pattern_score": 0.9,
        "features": {}, "feature_inputs": [], "generated_at": "2026-09-24T17:00:00+00:00",
    } for i in range(25)]
    scores.append({
        "instrument": "SMH", "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "raw_pattern_score": 0.7,
        "features": {"paperability_context": 1, "current_market_price": 1, "volume_or_flow_context": 1},
        "feature_inputs": [], "generated_at": "2026-09-24T17:00:00+00:00",
    })
    documents = {
        "qsase_source_universe.json": {"sources": [{"source_key": "rss"}]},
        "qsase_trading_universe.json": {"instruments": [{"symbol": row["instrument"]} for row in scores]},
    }
    monkeypatch.setattr(graph, "runtime_dir", lambda settings: tmp_path)
    monkeypatch.setattr(graph, "read_json", lambda path: documents.get(path.name, {}))
    monkeypatch.setattr(graph, "read_jsonl", lambda path: scores if path.name == "qadam_pattern_score_v3_records.jsonl" else [])
    monkeypatch.setattr(graph, "_active_trigger_families", lambda runtime: {"semiconductor_policy_options_asymmetry"})
    monkeypatch.setattr(graph, "TemporalGraphStore", Store)
    monkeypatch.setattr(graph, "write_json_atomic", lambda *args: None)
    payload, errors = graph.build_graph_patterns(candidate_limit=1)
    assert not errors
    assert payload["candidates"][0]["instrument"] == "SMH"
    assert payload["considered_candidate_count"] == 26
    assert payload["deferred_candidate_count"] == 25
    assert payload["full_universe_search_scope"]["pair_count"] == 26
    all_candidates, errors = graph.build_graph_patterns()
    assert not errors
    assert all_candidates["candidate_count"] == 26
    assert all_candidates["deferred_candidate_count"] == 0
