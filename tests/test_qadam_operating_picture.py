from orchestrator.presentation.operating_picture import build_picture


def test_telegram_reads_same_generation_and_does_not_refresh_stale_evidence(tmp_path):
    from orchestrator.presentation.generations import publish_projection
    from orchestrator.presentation.operating_picture import read_shared_brief
    receipt = publish_projection(tmp_path, {"qsase_dashboard_status.json": {"operating_picture": {
        "dimensions": [{"key": "evidence", "observed_at": "2026-09-06T12:00:00Z", "value": 10},
                       {"key": "economics", "observed_at": "2026-09-06T12:00:00Z", "value": 0}]}}})
    current = read_shared_brief(tmp_path, "2026-09-06T12:10:00Z")
    assert current["generation_id"] == receipt["generation_id"]
    assert "10 provider-backed" in current["text"]
    old = read_shared_brief(tmp_path, "2026-09-07T12:10:00Z")
    assert "10 provider-backed" not in old["text"]
    assert "stale or unavailable" in old["text"]


def test_fresh_system_is_not_live_coverage_or_profitability():
    now = "2026-09-01T14:00:00+00:00"
    result = build_picture(operator={"generated_at": now, "status": "running", "open_circuit_count": 0},
        capability={"generated_at": now, "counts": {"catalogue": 41, "provider_backed_current": 10}},
        router={"generated_at": now, "current_router_state": "idle", "handoff_count": 0},
        tournament={}, ledger={}, generated_at=now)
    assert result["dimensions"][0]["value"] == "running"
    assert result["dimensions"][1]["value"] == 10
    assert result["dimensions"][1]["catalogue_count"] == 41
    assert result["dimensions"][3]["value"] is None
    assert result["health_implies_profitability"] is False
    assert result["research_economics"]["model_expense_usd"] is None


def test_stale_or_future_reports_cannot_claim_current_work():
    for observed in ("2026-08-01T00:00:00Z", "2026-10-01T00:00:00Z"):
        result = build_picture(operator={"generated_at": observed, "status": "running"},
            capability={}, router={}, tournament={}, ledger={}, generated_at="2026-09-01T00:00:00Z")
        assert result["dimensions"][0]["state"] == "stale_or_unavailable"
        assert result["dimensions"][0]["value"] is None
        assert result["paper_order_allowed"] is False
