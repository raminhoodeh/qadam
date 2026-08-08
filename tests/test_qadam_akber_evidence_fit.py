from __future__ import annotations

from orchestrator.qadam_akber_evidence_fit import (
    build_akber_evidence_fit_state,
    validate_akber_evidence_fit,
)


def test_evidence_fit_contract_distinguishes_watchlist_hold_veto_and_pass() -> None:
    state = build_akber_evidence_fit_state(generated_at="2026-08-08T12:00:00+00:00")
    assert validate_akber_evidence_fit(state) == []
    for probe in state["contract_probes"].values():
        assert probe["complete"]["decision"] == "pass"
        assert probe["inactive"]["decision"] == "watchlist_inactive_trigger"
        assert probe["missing_execution"]["decision"] == "hold_missing_context"
        assert probe["missing_execution"]["hard_vetoes"] == []
        assert probe["adverse_execution"]["decision"] == "veto"


def test_profile_ablation_keeps_execution_control_and_never_applies_changes() -> None:
    state = build_akber_evidence_fit_state(generated_at="2026-08-08T12:00:00+00:00")
    execution = [row for row in state["ablation"] if row["stage_removed"] == "execution"]
    assert len(execution) == 3
    assert all(row["execution_control_retained"] is True for row in execution)
    assert all(row["threshold_change_applied"] is False for row in state["proposals"])
