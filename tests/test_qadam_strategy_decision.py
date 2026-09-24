from dataclasses import replace

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_strategy_decision import (
    OPTIONAL_FIELDS, REQUIRED_FIELDS, POLICY_VERSION,
    build_strategy_input, evaluate_strategy_input, current_decision,
    build_and_write_strategy_decision,
)
from orchestrator.qadam_tradeability_reliability import _load_fixture, _front_half, _valid_full_journey
from orchestrator.qadam_portfolio_risk_engine import evaluate_position_size, default_portfolio_policy


def _input(tmp_path):
    front = _front_half(_load_fixture("retirement"), "valid_pass", tmp_path)
    return front["akber_input"]


def test_optional_missingness_is_not_a_six_stage_veto(tmp_path):
    row = _input(tmp_path)
    for key in OPTIONAL_FIELDS:
        row["evidence"][key].update(available=False, state="missing")
    result = evaluate_strategy_input(row)
    assert result["decision"] == "pass"
    assert 0 < result["soft_evidence_size_multiplier"] < 1
    assert result["stages"] == []
    assert result["akber_stages_evaluated"] is False
    assert current_decision(result)


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_required_execution_evidence_cannot_be_fabricated(tmp_path, field):
    front = _front_half(_load_fixture("missing"), "valid_pass", tmp_path)
    context = front["packet_state"]["packets"][0]["akber_context"]
    context[field] = True  # Not provider-backed merely because a boolean says so.
    row = build_strategy_input(front["projection"], context,
                               generated_at=front["akber_input"]["generated_at"])
    result = evaluate_strategy_input(row)
    assert result["decision"] != "pass"
    assert field in result["missing_critical_context"]


def test_legacy_pass_cannot_become_current_authority(tmp_path):
    result = evaluate_strategy_input(_input(tmp_path))
    archived = {**result, "policy_version": "akber-v4-layered-paper.2-bounded-unknown-expectancy"}
    assert not current_decision(archived)
    assert not current_decision({"decision": "pass", "router_eligible": True})
    assert current_decision(result)


def test_broker_disabled_chain_reaches_paperops_with_no_akber(tmp_path, monkeypatch):
    import orchestrator.qadam_akber_filter_v3 as legacy
    monkeypatch.setattr(legacy, "evaluate_akber_input", lambda *_: pytest.fail("Retired evaluator called"))
    result = _valid_full_journey(_load_fixture("no-akber"), tmp_path)
    assert result["actual"] == "accepted_for_guarded_paperops_sequence"
    assert result["accepted_handoff_count"] == 1


def test_no_hypothesis_does_not_need_akber_replay(tmp_path):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    store = AtomicArtifactStore(tmp_path)
    store.write_json("qadam_canonical_tradeability_foundry_summary.json",
                     {"implementation_complete": True, "hypothesis_count": 0})
    store.write_jsonl("qadam_akber_filter_v3_results.jsonl", [{"decision": "veto"}])
    state, checks, errors = build_and_write_strategy_decision(settings)
    assert errors == []
    assert state["results"] == []
    assert checks["valid_no_current_hypothesis_outcome"] is True
    assert checks["policy_version"] == POLICY_VERSION
    assert checks["broker_write_count"] == 0


def test_old_approval_does_not_satisfy_portfolio_risk():
    result = evaluate_position_size(
        {"setup_id": "archived", "akber_decision": "pass"}, {}, default_portfolio_policy("2026-09-24T10:00:00+00:00"),
        generated_at="2026-09-24T10:00:00+00:00",
    )
    assert result["proposal"] is None
    assert "current_qadam_strategy_decision_missing" in result["rejection"]["rejection_reasons"]


def test_queued_handoff_requires_current_owner_and_policy(tmp_path):
    from orchestrator.qadam_router_v3_paperops import _handoff_consumption_errors
    fixture = _load_fixture("queued-retirement")
    journey = _valid_full_journey(fixture, tmp_path)
    assert journey["accepted_handoff_count"] == 1
    handoff = dict(journey["handoff"])
    handoff.pop("strategy_decision_policy")
    errors = _handoff_consumption_errors(
        handoff, journey["decision"], {}, {},
        generated_at=fixture["generated_at"], duplicate_handoff_id=False,
        duplicate_idempotency_key=False, submitted_idempotency_keys=set(),
    )
    assert "retired_or_missing_strategy_decision_authority" in errors


def test_mixed_packet_generation_cannot_create_current_decision(tmp_path):
    front = _front_half(_load_fixture("lineage-retirement"), "valid_pass", tmp_path)
    store = AtomicArtifactStore(tmp_path)
    store.write_json("qadam_canonical_tradeability_foundry_summary.json",
                     {"implementation_complete": True, "hypothesis_count": 1})
    store.write_jsonl("qadam_strategy_hypotheses_v3.jsonl", [front["projection"]])
    packet = {**front["packet_state"]["packets"][0], "decision_generation_id": "other-generation"}
    store.write_jsonl("qadam_decision_evidence_packets.jsonl", [packet])
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    state, checks, errors = build_and_write_strategy_decision(settings)
    assert any("decision_packet_lineage" in error for error in errors)
    assert state["results"] == []
    assert checks["safe_to_consume"] is False
