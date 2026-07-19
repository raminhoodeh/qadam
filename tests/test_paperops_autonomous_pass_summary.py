from __future__ import annotations

import json
from pathlib import Path

from orchestrator.paperops_autonomous_pass import build_paperops_autonomous_pass_summary


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_legacy_recovered_pass_fails_closed_without_modern_guard_results() -> None:
    summary = build_paperops_autonomous_pass_summary(
        _fixture("paperops_autonomous_pass_recovered.json"),
        generated_at="2026-05-28T17:16:05+00:00",
    )

    assert summary["status"] == "degraded"
    assert summary["blockers"] == []
    assert summary["states"]["paper_ops_cycle_state"] == "paper_cycle_full_paper_operational_ready"
    assert summary["paper_runtime"]["idle_reason"] == "no_fresh_eligible_candidate"
    assert summary["paper_runtime"]["idempotency_guard_message"] == (
        "idempotency guard active: existing paper submit already recorded"
    )
    assert "unusual_whales_api_key_missing" in summary["optional_gaps"]
    assert "unusual_whales_api_key_missing" not in summary["blockers"]
    assert summary["self_healing"]["enabled"] is True
    assert summary["self_healing"]["needs_repair"] is True
    assert summary["self_healing"]["codex_reprompt_required"] is True
    assert summary["self_healing"]["repair_prompt"] is not None
    assert summary["validation_errors"]


def test_blocked_pasted_state_keeps_optional_credentials_nonblocking() -> None:
    summary = build_paperops_autonomous_pass_summary(
        _fixture("paperops_autonomous_pass_blocked.json"),
        generated_at="2026-05-28T14:00:12+00:00",
    )

    assert summary["status"] == "blocked"
    assert "source_spine_available_not_ready" in summary["blockers"]
    assert "paper_operational_cycle_not_ready" in summary["blockers"]
    assert "unusual_whales_api_key_missing" in summary["optional_gaps"]
    assert "unusual_whales_api_key_missing" not in summary["blockers"]
    assert "paperops_autonomous_pass_optional_gap_promoted_to_blocker" not in (
        summary["validation_errors"]
    )
    assert summary["self_healing"]["needs_repair"] is True
    assert summary["self_healing"]["codex_reprompt_required"] is True
    assert "status:blocked" in summary["self_healing"]["trigger_reasons"]
    assert "blockers:paper_operational_cycle_not_ready,source_spine_available_not_ready" in (
        summary["self_healing"]["trigger_reasons"]
    )
    assert "force_trades" in summary["self_healing"]["forbidden_actions"]
    assert "enable_live_capital" in summary["self_healing"]["forbidden_actions"]
    assert "scripts/run_paperops_autonomous_pass.py" in summary["self_healing"]["repair_prompt"]
    assert "Self-heal repair requested" in "\n".join(summary["automation_report_lines"])


def test_optional_data_coverage_gaps_stay_optional() -> None:
    optional_gaps = [
        "unusual_whales_api_key_missing",
        "twitter_x_bearer_token_missing",
        "reddit_credentials_missing",
        "ais_maritime_credential_missing",
        "wingbits_api_key_missing",
        "un_comtrade_api_key_missing",
        "kalshi_credentials_missing",
        "stock_act_api_key_missing",
    ]
    command_results = _fixture("paperops_autonomous_pass_recovered.json")
    for result in command_results:
        if result["label"] == "paper_closeout":
            result["parsed"]["qadam_paper_closeout_optional_gaps"] = ",".join(optional_gaps)

    summary = build_paperops_autonomous_pass_summary(
        command_results,
        generated_at="2026-05-28T17:16:05+00:00",
    )

    assert set(optional_gaps) <= set(summary["optional_coverage_gaps"])
    assert set(optional_gaps).isdisjoint(set(summary["blockers"]))
    assert summary["status"] == "degraded"


def test_user_facing_report_uses_paper_growth_trial_language() -> None:
    summary = build_paperops_autonomous_pass_summary(
        _fixture("paperops_autonomous_pass_recovered.json"),
        generated_at="2026-05-28T17:16:05+00:00",
    )
    report = "\n".join(summary["automation_report_lines"])

    assert "30-day paper growth trial" in report
    assert "Paper proof ledger" in report
    assert "Phase 7" not in report
