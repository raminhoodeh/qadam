import json

from orchestrator.runtime import operator
from orchestrator.runtime.services import SERVICE_DEFINITIONS


def test_truncated_paperops_failure_uses_bound_reason_and_bounded_revalidation(tmp_path, monkeypatch):
    definition = next(row for row in SERVICE_DEFINITIONS if row.service_id == "guarded_paperops")
    monkeypatch.setattr(operator, "_service_revalidation_fingerprint", lambda *args: "fixture-fingerprint")
    monkeypatch.setattr(operator, "_service_revalidation_identity", lambda *args: "fixture-build")
    receipt = {"receipt_id": "fixture-failed-pass", "completed_at": "2026-09-07T00:00:00+00:00",
        "command_results": [{"returncode": 1, "stdout_tail": "validation_errors=execution_not_frozen",
            "stderr_tail": "", "work_result": {"status": "blocked",
                "reason": "pre_paperops_submission_paper_mirror_refresh_failed"}}]}
    failure, retry = operator._record_failure(tmp_path, definition, receipt)
    assert failure == "transient_provider_network"
    assert retry["retry_scheduled"] is True
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    circuit = circuits["services"]["guarded_paperops"]
    assert circuit["state"] == "open"
    assert circuit["automatic_retry_allowed"] is False
    # Recovery uses the existing guarded revalidation contract, not a direct
    # resubmission of a possibly accepted broker request.
    assert operator.service_recovery_contract_errors(definition) == []
    for attempt in range(operator.MAX_AUTOMATIC_STABILITY_REVALIDATIONS):
        _, retry = operator._record_failure(tmp_path, definition,
            {**receipt, "receipt_id": f"fixture-revalidation-{attempt}", "circuit_revalidation": True})
    assert retry["retry_scheduled"] is False
