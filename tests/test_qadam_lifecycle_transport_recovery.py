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
