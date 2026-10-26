import httpx
import pytest

from orchestrator import paperops_paper_lifecycle_poller as poller
from orchestrator.runtime.recovery_policy import classify_failure
from scripts.check_paperops_paper_lifecycle_poller import (
    _live_poll_errors,
    _live_poll_failure_class,
)


@pytest.mark.parametrize("target,status,expected", [
    ("order", 401, "credential_operator_action"),
    ("order", 429, "rate_limit"),
    ("order", 503, "transient_provider_network"),
    ("position", 403, "credential_operator_action"),
    ("position", 500, "transient_provider_network"),
    ("position", 404, None),
    ("position", 200, None),
])
def test_broker_read_failure_is_not_a_closed_position(monkeypatch, target, status, expected):
    calls = []

    def respond(request):
        calls.append(request.method)
        position = "/positions/" in request.url.path
        code = status if position == (target == "position") else 200
        body = {"symbol": "NVDA", "qty": "1"} if position else {
            "symbol": "NVDA", "status": "filled", "filled_qty": "1",
        }
        return httpx.Response(code, json=body)

    client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setattr(poller, "_headers", lambda _: {})
    monkeypatch.setattr(poller, "_orders_url", lambda _: "https://paper.test/v2/orders")
    result = poller._poll_candidate(settings=None, candidate={"client_order_id": "test", "symbol": "NVDA"})
    assert set(calls) == {"GET"}
    assert result["failure_class"] == expected
    if expected:
        assert result["order_get_succeeded"] is False
        assert poller._lifecycle_mirror_record(result) is None
        artifact = {"status": "paper_lifecycle_poll_failed_sanitized", "poll_result_records": [result]}
        assert _live_poll_errors(artifact, requested=True)
        failure = _live_poll_failure_class(artifact)
        assert failure == expected
        assert classify_failure(f"qadam_failure_class={failure}") == expected
    else:
        assert result["order_get_succeeded"] is True
        assert result["position_get_succeeded"] is (status == 200)


@pytest.mark.parametrize("status,failed,valid", [
    ("paper_lifecycle_poll_recorded", 0, True),
    ("ready_no_submitted_paper_orders", 0, True),
    ("paper_lifecycle_poll_failed_sanitized", 1, False),
    ("paper_lifecycle_poll_recorded", 1, False),
    ("blocked_missing_alpaca_paper_credentials", 0, False),
    ("ready_pending_explicit_poll", 0, False),
])
def test_requested_poll_requires_success_not_just_valid_schema(status, failed, valid):
    artifact = {"status": status, "paper_order_poll_failed_count": failed}
    assert (not _live_poll_errors(artifact, requested=True)) is valid
    assert not _live_poll_errors(artifact, requested=False)


def test_transient_read_never_hides_credential_failure():
    artifact = {"poll_result_records": [
        {"failure_class": "transient_provider_network"},
        {"failure_class": "credential_operator_action"},
    ]}
    assert _live_poll_failure_class(artifact) == "credential_operator_action"


@pytest.mark.parametrize("case", ["verified", "manual_entry_hold", "unknown_error", "wrong_symbol",
                                   "wrong_hash", "stale", "unprotected", "corrupt_canonical"])
def test_known_order_get_recovery_uses_canonical_truth_not_invalid_post_summary(tmp_path, monkeypatch, case):
    from datetime import datetime, timedelta, timezone
    from tests.test_qadam_operating_ledger import _settings, _persist_ready_lineage, _activate, _candidate
    from orchestrator.execution.ledger import OperatingLedger

    settings = _settings(tmp_path)
    research = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(research)
    _activate(monkeypatch, ledger)
    order = ledger.prepare_order(_candidate())
    ledger.mark_order_submitting(order["order_key"])
    ledger.record_order_result(order_key=order["order_key"], succeeded=True,
        receipt={"broker_order_id_hash": "known-broker-hash", "broker_order_status": "accepted"},
        failure_class=None, post_attempted=True)
    if case == "manual_entry_hold":
        ledger.set_execution_frozen(reason="operator_manual_stop")
    ledger.record_direct_reconciliation(phase="incident_recovery", expected={}, observed={
        "mirror_observed_at": (datetime.now(timezone.utc) - timedelta(seconds=181 if case == "stale" else 0)).isoformat(),
        "position_protection_digest": None if case == "unprotected" else "protected",
    }, blockers=[])
    if case == "corrupt_canonical":
        with ledger.store.transaction() as db:
            db.execute("UPDATE canonical_orders SET payload_sha256='wrong'")
    candidates = [{"client_order_id": order["order_key"], "symbol": "WRONG" if case == "wrong_symbol" else "XAR",
                   "broker_order_id_hash": "wrong" if case == "wrong_hash" else "known-broker-hash"}]
    errors = ["unknown_error"] if case == "unknown_error" else [
        "paperops_alpaca_immediate_post_reconciliation_failed", "paperops_alpaca_success_status_invalid"]
    result = poller._canonical_readonly_poll_authority(settings, candidates, errors)
    assert result["verified"] is (case in {"verified", "manual_entry_hold"})
    if result["verified"]:
        assert result["broker_post_allowed"] is False
