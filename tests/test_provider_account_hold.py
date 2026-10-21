from dataclasses import replace

import pytest

from orchestrator.config import Settings
from orchestrator.intelligence import gemini_credential_probe
from orchestrator.research.provider_access import record_gemini_account_hold


def test_operator_suspension_hold_prevents_all_gemini_requests(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    record_gemini_account_hold(settings, reason="project_suspension_reported")
    monkeypatch.setattr("orchestrator.intelligence._http_json_probe",
                        lambda *a, **k: pytest.fail("Suspended account must not be probed"))
    monkeypatch.setattr("orchestrator.qadam_hedge_fund_team_health._default_json_request",
                        lambda *a, **k: pytest.fail("Suspended account must not generate"))
    from orchestrator.qadam_hedge_fund_team_health import run_frontier_strategy_lead_assessment
    assert gemini_credential_probe(settings, live=True)["probe_status"] == "account_held"
    result = run_frontier_strategy_lead_assessment({}, settings)
    assert result["reason"] == "gemini_account_action_required"
    assert result["automatic_retry_allowed"] is False


def test_unreadable_hold_fails_closed_and_only_reviewed_release_reenables(tmp_path):
    from orchestrator.research.provider_access import ARTIFACT, gemini_account_hold
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    (tmp_path / ARTIFACT).write_text("{}")
    assert gemini_account_hold(settings)["status"] == "held"
    record_gemini_account_hold(settings, reason="operator_verified_provider_restored", release_reviewed=True)
    assert gemini_account_hold(settings) is None
