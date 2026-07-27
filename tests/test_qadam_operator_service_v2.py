from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os

from orchestrator.config import Settings
from orchestrator.qadam_artifact_generations import ArtifactGenerationStore
from orchestrator.qadam_operator_service import (
    INTEGRATION_PROBE_SERVICES,
    RECEIPT_INDEX_ARTIFACT,
    SERVICE_DEFINITIONS,
    _append_receipt,
    _last_receipts,
    _last_successful_receipts,
    _lease_runtime_state,
    _record_failure,
    _publish_service_generations,
    _service_runtime_record,
    _workers,
    classify_failure,
    dispatch_due_jobs,
    operator_public_build_identity,
    repair_operator_service_circuit,
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


def test_public_build_identity_never_exposes_local_paths() -> None:
    projected = operator_public_build_identity(
        {
            "git_commit": "abc",
            "python_executable": "/private/local/python",
            "state_root": "/private/local/qadam/data",
            "working_directory": "/private/local/qadam",
        }
    )
    rendered = json.dumps(projected)
    assert "/private/local" not in rendered
    assert "python_executable" not in projected
    assert projected["python_executable_digest"]


def test_public_lease_state_digests_private_build_paths(tmp_path) -> None:
    _write_json(
        tmp_path / "qadam_operator_service_lease.json",
        {
            "status": "active",
            "owner_pid": os.getpid(),
            "expires_at": "2099-01-01T00:00:00+00:00",
            "build_identity": {
                "python_executable": "/private/local/python",
                "state_root": "/private/local/qadam/data",
                "working_directory": "/private/local/qadam",
            },
        },
    )

    state = _lease_runtime_state(tmp_path)
    rendered = json.dumps(state)
    assert "/private/local" not in rendered
    assert state["build_identity"]["state_root_digest"]


def test_generation_publication_respects_declared_resource_ownership(tmp_path) -> None:
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "research_evidence_validation"
    )
    for name in definition.generation_artifacts:
        _write_json(tmp_path / name, {"artifact": name})

    generations = _publish_service_generations(
        tmp_path,
        definition,
        [{"command": ["real-validation"]}],
    )

    assert set(generations) == {"label_plane", "edge_registry"}
    label = ArtifactGenerationStore(tmp_path, "label_plane").resolve_current()
    edge = ArtifactGenerationStore(tmp_path, "edge_registry").resolve_current()
    assert {row["name"] for row in label.manifest["files"]} == {
        "qadam_forward_labels_checks.json",
        "qadam_statistical_backtest_checks.json",
    }
    assert {row["name"] for row in edge.manifest["files"]} == {
        "qadam_edge_registry_checks.json",
        "qadam_nonlinear_quantum_value_checks.json",
    }
    assert label.manifest["producer"] == "research_evidence_validation"


def test_receipt_index_reconciles_legacy_ledger_and_suppresses_repeated_skips(
    tmp_path,
) -> None:
    completed = {
        "service_id": "pattern_scoring",
        "state": "completed",
        "generated_at": "2026-07-26T00:00:00+00:00",
        "completed_at": "2026-07-26T00:00:00+00:00",
    }
    skipped = {
        "service_id": "pattern_scoring",
        "state": "skipped",
        "skip_reason": "not_due",
        "detail": {"next_due_at": "2026-07-27T00:00:00+00:00"},
        "integration_probe": False,
        "generated_at": "2026-07-26T00:01:00+00:00",
    }
    ledger = tmp_path / "qadam_operator_service_receipts.jsonl"
    ledger.write_text(
        json.dumps(completed) + "\n" + json.dumps(skipped) + "\n",
        encoding="utf-8",
    )

    assert _last_receipts(tmp_path)["pattern_scoring"]["state"] == "skipped"
    assert _last_successful_receipts(tmp_path)["pattern_scoring"]["state"] == "completed"

    repeated = {**skipped, "generated_at": "2026-07-26T00:02:00+00:00"}
    original_size = ledger.stat().st_size
    _append_receipt(tmp_path, repeated)

    index = json.loads((tmp_path / RECEIPT_INDEX_ARTIFACT).read_text(encoding="utf-8"))
    assert ledger.stat().st_size == original_size
    assert index["receipt_count"] == 2
    assert index["suppressed_repeat_count"] == 1
    assert index["latest_receipts"]["pattern_scoring"]["generated_at"] == repeated["generated_at"]


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
    forward_shadow = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "forward_shadow"
    )
    assert forward_shadow.command_sequence == (
        ("scripts/run_qadam_forward_shadow.py", "--once", "--allow-network"),
    )


def test_bounded_dispatch_rotates_after_last_execution_to_prevent_starvation(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)

    first = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        executor=_success_executor,
        max_jobs=2,
    )
    second = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        executor=_success_executor,
        max_jobs=2,
    )

    assert [
        receipt["service_id"] for receipt in first["receipts"] if receipt["state"] == "completed"
    ] == ["source_ingestion", "historical_source_worker"]
    assert [
        receipt["service_id"] for receipt in second["receipts"] if receipt["state"] == "completed"
    ] == ["pattern_scoring", "research_evidence_validation"]
    cursor = json.loads(
        (tmp_path / "qadam_operator_dispatch_cursor.json").read_text(encoding="utf-8")
    )
    assert cursor["last_executed_service_id"] == "research_evidence_validation"
    assert cursor["next_service_id"] == "akber_review"


def test_akber_waits_for_ordered_research_evidence_validation() -> None:
    validation = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "research_evidence_validation"
    )
    akber = next(
        definition for definition in SERVICE_DEFINITIONS if definition.service_id == "akber_review"
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


def test_challenger_shares_score_plane_concurrency_group() -> None:
    scoring = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "pattern_scoring"
    )
    challenger = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "challenger_research"
    )

    assert challenger.concurrency_group == scoring.concurrency_group == "research_cpu"


def test_running_challenger_blocks_score_plane_rebuild(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_workers.json",
        {
            "workers": {
                "challenger_research": {
                    "service_id": "challenger_research",
                    "state": "running",
                    "pid": os.getpid(),
                    "concurrency_group": "research_cpu",
                }
            }
        },
    )
    called = []

    def executor(command: tuple[str, ...], timeout: int):
        called.append((command, timeout))
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("pattern_scoring",),
        executor=executor,
    )

    assert called == []
    assert cycle["receipts"][0]["skip_reason"] == "resource_claim_busy"
    assert cycle["receipts"][0]["detail"]["conflicting_services"] == ["challenger_research"]
    assert cycle["receipts"][0]["detail"]["resource_claims"]["writes"] == ["score_plane"]


def test_newer_pattern_scores_force_validation_before_its_cadence_is_due(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    receipts = [
        {
            "service_id": "research_evidence_validation",
            "state": "completed",
            "completed_at": "2099-01-01T00:00:00+00:00",
        },
        {
            "service_id": "pattern_scoring",
            "state": "completed",
            "completed_at": "2099-01-01T00:01:00+00:00",
        },
    ]
    (tmp_path / "qadam_operator_service_receipts.jsonl").write_text(
        "".join(json.dumps(receipt) + "\n" for receipt in receipts),
        encoding="utf-8",
    )
    commands = []

    def executor(command: tuple[str, ...], timeout: int):
        commands.append(command)
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("research_evidence_validation",),
        executor=executor,
    )

    assert cycle["completed_count"] == 1
    assert commands[0] == ("scripts/check_qadam_forward_labels.py",)


def test_dashboard_refresh_rebuilds_router_and_vnext_before_qsase() -> None:
    dashboard = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "dashboard_refresh"
    )

    assert dashboard.command_sequence[:3] == (
        ("scripts/check_qadam_router_v2_paperops_handoff.py",),
        ("scripts/check_qadam_dashboard_vnext.py",),
        ("scripts/check_qsase_dashboard_view_model.py",),
    )


def test_no_eligible_paperops_skip_is_current_idle_not_stale() -> None:
    definition = next(item for item in SERVICE_DEFINITIONS if item.service_id == "guarded_paperops")
    receipt = {
        "state": "skipped",
        "skip_reason": "no_eligible_work",
        "completed_at": "2099-01-01T00:00:00+00:00",
    }
    record = _service_runtime_record(
        definition,
        generated_at="2099-01-01T00:01:00+00:00",
        research_lock_active=False,
        release_effective=True,
        process_running=True,
        last_receipt=receipt,
        last_successful_receipt=None,
    )
    assert record["current_state"] == "idle_no_eligible_work"
    assert record["freshness"]["state"] == "fresh"


def test_lifecycle_reconciliation_runs_when_the_paper_account_is_idle(tmp_path) -> None:
    _ready_runtime(tmp_path)
    commands = []

    def executor(command: tuple[str, ...], timeout: int):
        commands.append(command)
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("paper_lifecycle_poll",),
        executor=executor,
    )

    assert cycle["completed_count"] == 1
    assert commands == [
        ("scripts/check_paperops_paper_lifecycle_poller.py", "--poll-paper-orders"),
        ("scripts/check_qadam_paper_lineage_and_proof.py",),
    ]


def test_closed_market_skip_is_current_idle_not_stale() -> None:
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "market_price_refresh"
    )
    receipt = {
        "state": "skipped",
        "skip_reason": "market_closed",
        "generated_at": "2099-01-01T00:00:00+00:00",
    }
    record = _service_runtime_record(
        definition,
        generated_at="2099-01-01T00:01:00+00:00",
        research_lock_active=False,
        release_effective=True,
        process_running=True,
        last_receipt=receipt,
        last_successful_receipt=None,
    )
    assert record["current_state"] == "idle_market_closed"
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


def test_explicit_force_can_certify_idle_canonical_paperops_route(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(tmp_path / "qadam_long_backtest_lock.json", {"status": "released"})
    _write_json(
        tmp_path / "qadam_experimental_paper_release_readiness.json",
        {"experimental_paper_release_effective": True},
    )
    _append_receipt(
        tmp_path,
        {
            "service_id": "portfolio_router_review",
            "state": "completed",
            "generated_at": "2099-01-01T00:00:00+00:00",
            "completed_at": "2099-01-01T00:00:00+00:00",
        },
    )
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

    assert [command for command, _timeout in called] == [
        ("scripts/run_paperops_autonomous_pass.py",)
    ]
    assert cycle["paperops_invoked"] is True
    assert cycle["failed_count"] == 0
    assert cycle["receipts"][0]["input_generation_binding_complete"] is False
    assert cycle["receipts"][0]["mixed_generation_join_count"] == 0


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
    first_probe = run_operator_integration_probe(_settings(tmp_path), executor=_success_executor)
    assert first_probe["status"] == "blocked"
    second_probe = run_operator_integration_probe(_settings(tmp_path), executor=_success_executor)
    assert second_probe["status"] == "blocked"
    probe = run_operator_integration_probe(_settings(tmp_path), executor=_success_executor)
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


def test_metric_counts_are_not_misclassified_as_http_credentials() -> None:
    assert classify_failure("paired_score_label_count=40126") == "code_defect"
    assert classify_failure("cockpit_status_forbidden_action_count=9") == "code_defect"
    assert classify_failure("transport_error:HTTPError") == "transient_provider_network"
    assert classify_failure("status code 401") == "credential_operator_action"
    assert (
        classify_failure("error=backtest_negative_control_promotion_gate_breach")
        == "research_integrity_hold"
    )
    assert (
        classify_failure("OSError: [Errno 11] Resource deadlock avoided")
        == "concurrent_artifact_access"
    )
    assert (
        classify_failure("public_status_reason=receiver_not_configured")
        == "optional_transport_unconfigured"
    )


def test_failure_class_uses_only_the_command_that_failed(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "parser_schema_drift",
                    "consecutive_failure_count": 4,
                }
            }
        },
    )
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh"
    )
    receipt = {
        "receipt_id": "operator-receipt:test-dashboard-failure",
        "completed_at": "2099-01-01T00:00:00+00:00",
        "command_results": [
            {
                "returncode": 0,
                "stdout_tail": "schema_status=passed forbidden_action_count=9",
                "stderr_tail": "",
                "evidence_hold_accepted": False,
            },
            {
                "returncode": 1,
                "stdout_tail": "transport_error:HTTPError:http_status_503",
                "stderr_tail": "",
                "evidence_hold_accepted": False,
            },
        ],
    }
    failure_class, retry = _record_failure(tmp_path, definition, receipt)
    assert failure_class == "transient_provider_network"
    assert retry["retry_scheduled"] is True
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["consecutive_failure_count"] == 1


def test_optional_public_status_503_does_not_stop_local_dashboard_refresh(tmp_path) -> None:
    _ready_runtime(tmp_path)

    def executor(command: tuple[str, ...], timeout: int):
        if command[0] == "scripts/publish_qadam_public_status.py":
            return {
                "returncode": 1,
                "stdout": (
                    "public_status_publish_status=degraded\n"
                    "public_status_published=False\n"
                    "public_status_reason=transport_error:HTTPError:http_status_503\n"
                ),
                "stderr": "",
                "duration_seconds": 0.01,
                "timed_out": False,
            }
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("dashboard_refresh", "public_status_publication"),
        executor=executor,
    )
    assert cycle["failed_count"] == 0
    dashboard = next(
        receipt for receipt in cycle["receipts"] if receipt["service_id"] == "dashboard_refresh"
    )
    publication = next(
        receipt
        for receipt in cycle["receipts"]
        if receipt["service_id"] == "public_status_publication"
    )
    assert dashboard["state"] == "completed"
    assert publication["state"] == "completed_with_transport_hold"
    publish = next(
        row
        for row in publication["command_results"]
        if row["command"][-1] == "scripts/publish_qadam_public_status.py"
    )
    assert publish["optional_transport_hold_accepted"] is True


def test_dashboard_refresh_updates_dependencies_before_final_certification() -> None:
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh"
    )
    commands = [command[0] for command in definition.command_sequence]

    assert commands.index("scripts/check_qadam_clean_broker_account_preflight.py") < commands.index(
        "scripts/check_qadam_autonomous_experimental_paper_epoch.py"
    )
    assert "scripts/publish_qadam_public_status.py" not in commands
    assert commands.index("scripts/check_qadam_operator_service.py") < commands.index(
        "scripts/check_qadam_operator_soak_v3.py"
    )
    assert commands.index("scripts/check_qadam_operator_soak_v3.py") < commands.index(
        "scripts/check_qadam_autonomous_experimental_paper_epoch.py"
    )
    publication = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "public_status_publication"
    )
    assert publication.dependencies == ("dashboard_refresh",)
    assert publication.command_sequence[0] == ("scripts/publish_qadam_public_status.py",)


def test_pattern_scoring_continues_while_validation_promotion_is_quarantined(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "research_evidence_validation": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )
    called = []

    def executor(command: tuple[str, ...], timeout: int):
        called.append((command, timeout))
        return _success_executor(command, timeout)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("source_ingestion", "pattern_scoring"),
        executor=executor,
    )
    assert called
    scoring = next(
        receipt for receipt in cycle["receipts"] if receipt["service_id"] == "pattern_scoring"
    )
    assert scoring["state"] == "completed"


def test_explicit_safe_circuit_repair_closes_only_after_success(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )
    result = repair_operator_service_circuit(
        "dashboard_refresh",
        _settings(tmp_path),
        executor=_success_executor,
    )
    assert result["status"] == "repaired"
    assert result["paper_order_created_count"] == 0
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "closed"
    assert result["verification_pass_count"] == 3


def test_changed_safe_circuit_revalidates_three_times_before_reopening_pipeline(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )

    first = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("dashboard_refresh",),
        executor=_success_executor,
    )
    assert first["receipts"][0]["state"] == ("completed_pending_circuit_confirmation")
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "half_open"

    second = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("dashboard_refresh",),
        executor=_success_executor,
    )
    assert second["receipts"][0]["state"] == ("completed_pending_circuit_confirmation")
    third = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("dashboard_refresh",),
        executor=_success_executor,
    )
    assert third["receipts"][0]["state"] == "completed"
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "closed"


def test_explicit_repair_can_revalidate_interrupted_challenger(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "challenger_research": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )

    result = repair_operator_service_circuit(
        "challenger_research",
        _settings(tmp_path),
        executor=_success_executor,
    )

    assert result["status"] == "repaired"
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["challenger_research"]["state"] == "closed"


def test_explicit_circuit_repair_rejects_paperops(tmp_path) -> None:
    _ready_runtime(tmp_path)
    try:
        repair_operator_service_circuit(
            "guarded_paperops",
            _settings(tmp_path),
            executor=_success_executor,
        )
    except ValueError as exc:
        assert str(exc) == "operator_circuit_repair_service_not_permitted"
    else:
        raise AssertionError("guarded PaperOps circuit repair must fail closed")


def test_explicit_confirmed_paperops_repair_requires_three_real_passes(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(tmp_path / "qadam_long_backtest_lock.json", {"status": "released"})
    _write_json(
        tmp_path / "qadam_experimental_paper_release_readiness.json",
        {"experimental_paper_release_effective": True},
    )
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "guarded_paperops": {
                    "state": "open",
                    "failure_class": "transient_provider_network",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )
    calls = []

    def executor(command: tuple[str, ...], timeout: int):
        calls.append((command, timeout))
        return _success_executor(command, timeout)

    result = repair_operator_service_circuit(
        "guarded_paperops",
        _settings(tmp_path),
        executor=executor,
        explicit_guarded_paperops_confirmation=True,
    )

    assert result["status"] == "repaired"
    assert result["verification_pass_count"] == 3
    assert [command for command, _timeout in calls] == [
        ("scripts/run_paperops_autonomous_pass.py",),
        ("scripts/run_paperops_autonomous_pass.py",),
        ("scripts/run_paperops_autonomous_pass.py",),
    ]
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["guarded_paperops"]["state"] == "closed"


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


def test_competing_circuit_updates_preserve_each_service(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {}})

    def record(service_id: str) -> None:
        definition = next(
            item for item in SERVICE_DEFINITIONS if item.service_id == service_id
        )
        _record_failure(
            tmp_path,
            definition,
            {
                "receipt_id": f"stress:{service_id}",
                "completed_at": "2026-07-27T00:00:00+00:00",
                "command_results": [
                    {
                        "returncode": 1,
                        "stdout_tail": "Traceback: deterministic stress defect",
                        "stderr_tail": "",
                    }
                ],
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(record, ("source_ingestion", "dashboard_refresh")))

    payload = json.loads(
        (tmp_path / "qadam_operator_circuit_breakers.json").read_text(encoding="utf-8")
    )
    assert sorted(payload["services"]) == ["dashboard_refresh", "source_ingestion"]
