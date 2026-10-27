import json

import pytest

from orchestrator import qadam_communications_policy as policy


def test_tracked_default_is_trade_fills_and_patterns_only(monkeypatch):
    monkeypatch.delenv("QADAM_COMMUNICATION_PROFILE", raising=False)
    assert policy.communications_profile() == "trades_and_patterns"
    assert policy.proactive_allowed("paper_fill")
    assert policy.proactive_allowed("pattern")
    for category in (
        "service_health", "strategy_status", "generic_daily_brief", "human_brief",
        "portfolio_digest", "codebase_upgrade", "submitted_paper_order", "unknown",
    ):
        assert not policy.proactive_allowed(category)


@pytest.mark.parametrize("content", ["missing", "{}", "null", "not-json"])
def test_missing_or_invalid_policy_fails_quiet_not_open(tmp_path, monkeypatch, content):
    monkeypatch.delenv("QADAM_COMMUNICATION_PROFILE", raising=False)
    path = tmp_path / "communications.json"
    if content != "missing":
        path.write_text(content)
    monkeypatch.setattr(policy, "POLICY_PATH", path)
    assert not policy.proactive_allowed("service_health")
    assert policy.proactive_allowed("paper_fill")


def test_preference_has_no_trading_or_monitoring_authority():
    config = json.loads(policy.POLICY_PATH.read_text())
    assert config["health_monitoring_remains_enabled"] is True
    assert config["self_healing_remains_enabled"] is True
    assert config["on_demand_replies_remain_enabled"] is True
    assert config["allowed_proactive_categories"] == ["paper_fill", "pattern"]


def test_only_substantive_changes_are_market_findings():
    before = {"question": "Does supply predict prices?", "stage": "queued", "quantum_summary": "old"}
    assert not policy.interesting_pattern_change(before, {**before, "stage": "approved", "quantum_summary": "new"})
    assert policy.interesting_pattern_change(before, {**before, "direction": "long"})
    assert policy.interesting_pattern_change(before, {**before, "validated": True})
