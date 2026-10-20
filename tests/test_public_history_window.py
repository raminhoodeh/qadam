import json

from orchestrator.presentation.bounded import bounded_operator_dashboard


def test_public_history_is_bounded_and_totals_and_open_positions_survive():
    records = [{"id": i, "detail": "x" * 1000} for i in range(1000)]
    source = {"views": {
        "learn/outcomes": {"counts": {"learnable_event_count": 1000}, "events": records,
            "learning_events": records, "repositories": {"learning_reviews": {
                "count": 1000, "records": records}}},
        "fund/portfolio": {"positions": [{"symbol": "TEST", "qty": 3}]},
    }}
    bounded = bounded_operator_dashboard(source)
    view = bounded["views"]["learn/outcomes"]
    assert len(view["events"]) == 50
    assert view["counts"]["learnable_event_count"] == 1000
    assert view["repositories"]["learning_reviews"]["count"] == 1000
    assert view["repositories"]["learning_reviews"]["visible_count"] == 50
    assert view["display_window"]["truncated"] is True
    assert len(source["views"]["learn/outcomes"]["events"]) == 1000
    assert bounded["views"]["fund/portfolio"] == source["views"]["fund/portfolio"]
    assert len(json.dumps(bounded)) < len(json.dumps(source)) / 10
