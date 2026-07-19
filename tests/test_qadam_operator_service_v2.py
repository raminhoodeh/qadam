from __future__ import annotations

from dataclasses import replace
import json

from orchestrator.config import Settings
from orchestrator.qadam_operator_service import (
    INTEGRATION_PROBE_SERVICES,
    SERVICE_DEFINITIONS,
    _service_runtime_record,
    _workers,
    dispatch_due_jobs,
    run_operator_integration_probe,
)


def _settings(tmp_path):
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _ready_runtime(tmp_path) -> None:
    generated_at = "2099-01-01T00:00:00+00:00"
    _write_json(
        tmp_path / "qadam_long_backtest_lock.json",
        {"status": "active", "paperops_watch_only_mode": True},
    )
    _write_json(
        tmp_path / "qadam_research_lock_release_readiness.json",
        {"release_effective": False},
    )
    for filename in (
        "qadam_point_in_time_evidence_checks.json",
        "qadam_pattern_score_v3_checks.json",
        "qadam_edge_registry_checks.json",
        "qadam_akber_filter_v3_checks.json",
    ):
        _write_json(tmp_path / filename, {"generated_at": generated_at, "status": "passed"})


def _success_executor(command: tuple[str, ...], _timeout: int):
    return {
        "returncode": 0,
        "stdout": f"executed={command[0]}",
        "stderr": "",
        "duration_seconds": 0.01,
        "timed_out": False,
    }


def test_service_registry_is_explicit_and_paperops_uses_only_canonical_wrapper() -> None:
    assert len(SERVICE_DEFINITIONS) >= 10
    assert len({definition.service_id for definition in SERVICE_DEFINITIONS}) == len(
        SERVICE_DEFINITIONS
    )
    for definition in SERVICE_DEFINITIONS:
        assert definition.command_sequence
        assert definition.timeout_seconds > 0
        assert definition.concurrency_group
        assert definition.lock_requirement
        assert definition.safety_mode
    paperops = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "guarded_paperops"
    )
    assert paperops.command_sequence == (("scripts/run_paperops_autonomous_pass.py",),)
    assert paperops.safe_retry_class == "no_automatic_retry"


def test_akber_waits_for_ordered_research_evidence_validation() -> None:
    validation = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "research_evidence_validation"
    )
    akber = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "akber_review"
    )
    assert validation.dependencies == ("pattern_scoring",)
    assert validation.command_sequence == (
        ("scripts/check_qadam_forward_labels.py",),
        ("scripts/check_qadam_statistical_backtest.py",),
        ("scripts/check_qadam_nonlinear_quantum_value.py",),
        ("scripts/check_qadam_edge_registry.py",),
    )
    assert akber.dependencies == ("research_evidence_validation",)
    assert akber.prerequisite_artifacts == ("qadam_edge_registry_checks.json",)


def test_no_eligible_lifecycle_skip_is_current_idle_not_stale() -> None:
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "paper_lifecycle_poll"
    )
    receipt = {
        "state": "skipped",
        "skip_reason": "no_eligible_work",
        "completed_at": "2099-01-01T00:00:00+00:00",
    }
    record = _service_runtime_record(
        definition,
        generated_at="2099-01-01T00:01:00+00:00",
        research_lock_active=True,
        release_effective=False,
        process_running=True,
        last_receipt=receipt,
        last_successful_receipt=None,
    )
    assert record["current_state"] == "idle_no_eligible_work"
    assert record["freshness"]["state"] == "fresh"


def test_research_lock_prevents_paperops_dispatch(tmp_path) -> None:
    _ready_runtime(tmp_path)
    called = []

    def executor(command: tuple[str, ...], timeout: int):
        called.append((command, timeout))
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("guarded_paperops",),
        executor=executor,
    )
    assert called == []
    assert cycle["paperops_invoked"] is False
    assert cycle["receipts"][0]["skip_reason"] == "research_lock"
    assert cycle["paper_order_created_count"] == 0
    assert cycle["broker_write_count"] == 0


def test_real_entrypoint_integration_probe_runs_every_required_service(tmp_path) -> None:
    _ready_runtime(tmp_path)
    commands = []

    def executor(command: tuple[str, ...], timeout: int):
        commands.append(command)
        return _success_executor(command, timeout)

    probe = run_operator_integration_probe(_settings(tmp_path), executor=executor)
    assert probe["status"] == "passed"
    assert probe["all_required_jobs_executed"] is True
    assert probe["executed_service_count"] == len(INTEGRATION_PROBE_SERVICES)
    assert set(probe["service_states"]) == set(INTEGRATION_PROBE_SERVICES)
    assert probe["paperops_invoked"] is False
    assert commands


def test_integration_probe_can_verify_and_close_repaired_research_circuit(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "akber_review": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )
    probe = run_operator_integration_probe(
        _settings(tmp_path), executor=_success_executor
    )
    assert probe["status"] == "passed"
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["akber_review"]["state"] == "closed"


def test_safe_retry_closes_after_idempotent_recovery(tmp_path) -> None:
    _ready_runtime(tmp_path)
    attempts = 0

    def executor(command: tuple[str, ...], _timeout: int):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": "provider network timeout",
                "duration_seconds": 0.01,
                "timed_out": False,
            }
        return _success_executor(command, _timeout)

    first = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("source_ingestion",),
        executor=executor,
    )
    assert first["failed_count"] == 1
    assert first["receipts"][0]["failure_class"] == "transient_provider_network"
    assert first["receipts"][0]["retry_scheduled"] is True

    second = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("source_ingestion",),
        executor=executor,
    )
    assert second["failed_count"] == 0
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["source_ingestion"]["state"] == "closed"


def test_interrupted_long_worker_is_resumable_without_duplicate_instance(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_workers.json",
        {
            "workers": {
                "historical_source_worker": {
                    "service_id": "historical_source_worker",
                    "receipt_id": "old",
                    "pid": 99999999,
                    "state": "running",
                    "concurrency_group": "historical_research",
                }
            }
        },
    )
    assert _workers(tmp_path)["historical_source_worker"]["state"] == "interrupted"
    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        integration_probe=True,
        service_ids=("historical_source_worker",),
        executor=_success_executor,
    )
    assert cycle["failed_count"] == 0
    assert cycle["receipts"][0]["state"] == "completed"
