from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from orchestrator.qadam_portfolio_risk_engine import POLICY_VERSION
from orchestrator.qadam_router_v3_paperops import _assemble_setup, route_setup
from orchestrator.runtime.recovery_policy import classify_exception, classify_failure, retry_policy


NOW = "2026-09-10T18:00:00+00:00"


def records():
    hypothesis = {
        "hypothesis_id": "qeg:hypothesis", "evidence_class": "experimental_unvalidated",
        "experimental_tier": "discovery_micro", "strategy_version_id": "qeg:version",
        "candidate_identity_material": {"candidate_identity_id": "qeg:candidate"},
        "research_goal_lineage": {"research_goal_id": "qeg:goal"},
        "pattern_lineage": {"pattern_relationship_id": "qeg:pattern", "score_id": "score"},
        "instrument_proxy_mapping": {"execution_proxy": "NVDA"},
        "paperability": {"execution_proxy": "NVDA"},
        "direction_horizon": {"direction": "long", "horizon": "5d_forward"},
        "freshness": {"expires_at": "2026-09-11T18:00:00+00:00"},
    }
    akber = {
        "hypothesis_id": "qeg:hypothesis", "akber_result_id": "akber:result",
        "decision_generation_id": "generation", "evidence_digest": "digest",
        "decision": "pass", "current_trigger_sources": ["rss"],
        "stages": [{"stage": "catalyst", "state": "pass"}],
    }
    proposal = {
        **akber, "proposal_id": "risk:proposal", "generated_at": NOW,
        "instrument": "NVDA", "policy_version": POLICY_VERSION,
        "independent_market_confirmation_passed": True, "current_price": 218.25,
        "annualized_volatility": 0.43, "proposed_quantity": 1,
        "proposed_notional": 218.25, "maximum_loss_at_invalidation": 5.99,
        "paper_route": "guarded_alpaca_paper_via_paperops",
        "risk_approval_created": False, "expected_net_return": 0.0025,
        "shadow_evidence_id": "shadow:decision",
    }
    release = {
        "experimental_paper_release_effective": True,
        "experimental_policy_operator_approved": True,
        "experimental_risk_policy_operator_approved": True,
        "risk_policy_version": POLICY_VERSION,
    }
    return hypothesis, akber, proposal, release


def assemble(hypothesis, akber, proposal, release):
    return _assemble_setup(
        hypothesis, edge={}, score={}, akber=akber, shadow_decision={},
        shadow_outcome={}, shadow_promotion={}, risk_proposal=proposal,
        risk_state={"drawdown_context_complete": True, "daily_loss_pct": 0, "trailing_drawdown_pct": 0},
        qctrl={"status": "consultation_recorded"}, approvals={}, release=release,
        epoch={}, open_symbols=set(), consumed_signal_history=[], generated_at=NOW,
    )


def test_graph_candidate_with_bound_live_sizing_reaches_guarded_review():
    hypothesis, akber, proposal, release = records()
    assert "independent_market_confirmation" not in hypothesis["pattern_lineage"]
    setup = assemble(hypothesis, akber, proposal, release)
    assert setup["source_quorum_passed"]
    assert setup["source_quorum"]["market_confirmation_basis"] == "generation_bound_risk_market_context"
    decision = route_setup(setup, release, generated_at=NOW)
    assert decision["final_state"] == "experimental_paper_review_candidate"
    assert decision["paper_order_created"] is False


@pytest.mark.parametrize("field,value", [
    ("hypothesis_id", "another"), ("akber_result_id", "another"),
    ("decision_generation_id", "another"), ("evidence_digest", "another"),
    ("instrument", "SMH"), ("independent_market_confirmation_passed", False),
    ("current_price", 0), ("annualized_volatility", 0),
    ("generated_at", "2026-09-10T17:44:59+00:00"),
    ("generated_at", "2026-09-10T18:00:01+00:00"),
    ("paper_route", "direct_broker"),
])
def test_other_generation_stale_missing_or_unsafe_confirmation_cannot_pass(field, value):
    hypothesis, akber, proposal, release = records()
    proposal[field] = value
    setup = assemble(hypothesis, akber, proposal, release)
    assert not setup["source_quorum_passed"]
    assert not route_setup(setup, release, generated_at=NOW)["paperops_handoff_allowed"]


@pytest.mark.parametrize("change", ["no_trigger", "policy_version", "unapproved", "loss", "qctrl", "duplicate"])
def test_repaired_mapping_preserves_other_gates(change):
    hypothesis, akber, proposal, release = records()
    if change == "no_trigger":
        akber["current_trigger_sources"] = []
    if change == "policy_version":
        release["risk_policy_version"] = "old-policy"
    if change == "unapproved":
        release["experimental_risk_policy_operator_approved"] = False
    setup = assemble(hypothesis, akber, proposal, release)
    if change == "loss":
        setup["expected_net_return_positive_after_costs"] = False
    if change == "qctrl":
        setup["qctrl_state"] = "hold"
    if change == "duplicate":
        setup["duplicate_exposure_conflict"] = True
    assert not route_setup(setup, release, generated_at=NOW)["paperops_handoff_allowed"]


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadError, httpx.ReadTimeout, httpx.RemoteProtocolError])
def test_transport_exceptions_remain_retryable_across_checker_boundary(error):
    failure = classify_exception(error("secret URL must not be logged"))
    assert failure == "transient_provider_network"
    assert classify_failure(f"qadam_failure_class={failure}") == failure
    assert retry_policy(failure)["automatic_retry_allowed"]
    assert not retry_policy(failure, attempt_count=3)["automatic_retry_allowed"]
    assert not retry_policy(failure)["broker_write_retry_allowed"]


@pytest.mark.parametrize("status,expected", [(401, "credential_operator_action"), (403, "credential_operator_action"), (429, "rate_limit"), (503, "transient_provider_network"), (400, "code_defect")])
def test_http_status_does_not_masquerade_as_network_failure(status, expected):
    response = httpx.Response(status, request=httpx.Request("GET", "https://example.test"))
    failure = classify_exception(httpx.HTTPStatusError("redacted", request=response.request, response=response))
    assert failure == expected
    assert classify_failure(f"qadam_failure_class={failure}") == failure


def test_actual_connect_error_recovers_without_erasing_safety_failure():
    message = "alpaca_paper_mirror_live_error=ConnectError"
    assert classify_failure(message) == "transient_provider_network"
    assert classify_failure(message + "\nsafety violation") == "safety_violation"
    assert classify_exception(ValueError("redacted")) == "code_defect"


def test_real_failure_receipt_enters_bounded_scheduler_recovery(tmp_path, monkeypatch):
    from orchestrator.runtime import operator as op

    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "market_price_refresh")
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "unchanged")
    monkeypatch.setattr(op, "_service_revalidation_identity", lambda *_: "build")
    op._record_failure(tmp_path, definition, {
        "receipt_id": "network-read", "completed_at": (now - timedelta(minutes=10)).isoformat(),
        "command_results": [{"returncode": 1, "stdout_tail": "alpaca_paper_mirror_live_error=ConnectError"}],
    })
    circuit = op._circuit_breaker_state(tmp_path)["market_price_refresh"]
    assert circuit["failure_class"] == "transient_provider_network"
    assert circuit["automatic_retry_allowed"]


def test_router_revalidates_approval_instead_of_reusing_obsolete_projection(tmp_path, monkeypatch):
    from orchestrator import qadam_guarded_paper_launch as launch
    from orchestrator import qadam_router_v3_paperops as router

    (tmp_path / router.EXPERIMENTAL_RELEASE_ARTIFACT).write_text(json.dumps({
        "experimental_paper_release_effective": True, "risk_policy_version": "old-policy",
    }))
    monkeypatch.setattr(router, "runtime_dir", lambda *_: tmp_path)
    monkeypatch.setattr(router.ControlPlaneStore, "from_settings", lambda *_: type("Store", (), {"consumed_signal_history": lambda self: []})())
    expected = records()[-1]
    calls = []
    def revalidate(settings=None):
        calls.append(True)
        return deepcopy(expected)
    monkeypatch.setattr(launch, "build_current_experimental_release_state", revalidate)
    state = router.build_router_v3_state(generated_at=NOW)
    assert calls == [True]
    assert state["release"]["risk_policy_version"] == POLICY_VERSION
    expected.update(experimental_paper_release_effective=False, experimental_risk_policy_operator_approved=False)
    state = router.build_router_v3_state(generated_at=NOW)
    assert not state["release"]["experimental_paper_release_effective"]
    assert not state["release"]["experimental_risk_policy_operator_approved"]
