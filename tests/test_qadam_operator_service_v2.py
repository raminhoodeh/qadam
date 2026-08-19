from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os

import orchestrator.qadam_operator_service as operator_service
from orchestrator.config import Settings
from orchestrator.qadam_artifact_generations import ArtifactGenerationStore
from orchestrator.qadam_operator_ready_common import ROOT
from orchestrator.qadam_operator_dashboard import (
    FRESHNESS_SPECS,
    ROUTER_SCOREBOARD_ARTIFACT,
    SHADOW_STATE_ARTIFACT,
)
from orchestrator.qadam_operator_service import (
    INTEGRATION_PROBE_SERVICES,
    OPERATOR_BUILD_PATHS,
    RECEIPT_INDEX_ARTIFACT,
    SERVICE_DEFINITIONS,
    _append_receipt,
    _bounded_dispatch_order,
    _build_repair_queue,
    _freshness_deadline_priority,
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
    run_safe_operator_control_cycle,
    run_operator_integration_probe,
)
from orchestrator.qadam_resource_locks import RESOURCE_ORDER


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
        "qadam_strategy_foundry_v3_checks.json",
        "qadam_qeg_cycle_summary.json",
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


def test_operator_build_scope_includes_agent_prompts_and_contract_schemas() -> None:
    assert "agents" in OPERATOR_BUILD_PATHS
    assert "schemas" in OPERATOR_BUILD_PATHS
    assert "data/runtime" not in OPERATOR_BUILD_PATHS


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
    assert "dashboard_projection" in paperops.write_resources
    open_market_conversion = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "open_market_conversion"
    )
    assert open_market_conversion.command_sequence == (
        (
            "scripts/run_qadam_open_market_conversion.py",
            "--allow-network",
            "--no-paperops",
        ),
    )
    forward_shadow = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "forward_shadow"
    )
    assert forward_shadow.command_sequence == (
        ("scripts/run_qadam_forward_shadow.py", "--once", "--allow-network"),
    )


def test_all_service_resources_and_generation_artifacts_are_registered() -> None:
    registry = json.loads(
        (ROOT / "config" / "qadam_runtime_artifact_ownership.json").read_text(
            encoding="utf-8"
        )
    )
    records = {
        str(record["artifact"]): record for record in registry.get("artifacts", [])
    }
    for definition in SERVICE_DEFINITIONS:
        definition.resource_claims().validate()
        for resource in (*definition.write_resources, *definition.append_resources):
            assert resource in RESOURCE_ORDER
        for artifact in definition.generation_artifacts:
            assert artifact in records
            assert definition.service_id in records[artifact]["authorized_invokers"]
            assert records[artifact]["logical_resource"] in (
                *definition.write_resources,
                *definition.append_resources,
            )


def test_dispatch_stops_writers_when_live_storage_guard_is_active(
    tmp_path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(
        operator_service,
        "run_storage_maintenance",
        lambda *_args, **_kwargs: {
            "status": "disk_resource_pressure",
            "disk": {
                "measurement_source": "shutil.disk_usage_live_filesystem",
                "free_bytes": 1024,
                "minimum_free_bytes": 64 * 1024**3,
                "used_ratio": 0.99,
                "maximum_used_ratio": 0.90,
                "write_services_allowed": False,
            },
        },
    )

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("source_ingestion",),
        executor=_success_executor,
    )

    assert cycle["executed_count"] == 0
    assert cycle["storage_write_services_allowed"] is False
    assert cycle["receipts"][0]["skip_reason"] == "disk_resource_pressure"


def test_dispatch_continues_when_storage_maintenance_raises_but_disk_is_healthy(
    tmp_path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(
        operator_service,
        "run_storage_maintenance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("maintenance failed")),
    )
    monkeypatch.setattr(
        operator_service,
        "live_storage_health",
        lambda *_args, **_kwargs: {
            "measurement_source": "shutil.disk_usage_live_filesystem",
            "free_bytes": 250 * 1024**3,
            "minimum_free_bytes": 64 * 1024**3,
            "used_ratio": 0.72,
            "maximum_used_ratio": 0.90,
            "write_services_allowed": True,
        },
    )

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("source_ingestion",),
        executor=_success_executor,
    )

    assert cycle["executed_count"] == 1
    assert cycle["storage_write_services_allowed"] is True
    assert cycle["storage_status"] == "maintenance_failed"
    assert cycle["receipts"][0]["state"] == "completed"


def test_control_cycle_publishes_scheduler_identity_before_dispatch(
    tmp_path, monkeypatch
) -> None:
    events: list[str] = []

    def publish(_settings):
        events.append("publish")
        return (
            {"status": {"service_running": True}},
            {
                "status": "passed",
                "integration_probe_passed": True,
                "paper_order_created_count": 0,
                "broker_write_count": 0,
            },
            [],
        )

    def dispatch(*_args, **_kwargs):
        events.append("dispatch")
        return {
            "status": "passed",
            "executed_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "skip_reasons": [],
        }

    monkeypatch.setattr(operator_service, "build_and_write_operator_service", publish)
    monkeypatch.setattr(operator_service, "dispatch_due_jobs", dispatch)
    monkeypatch.setattr(operator_service, "_record_real_operator_session", lambda *_a, **_k: None)

    import orchestrator.qadam_operator_dashboard as operator_dashboard
    import orchestrator.qadam_permanent_operator_reliability as reliability
    import orchestrator.qadam_research_supervisor as research_supervisor
    import orchestrator.qadam_self_healing_supervisor as self_healing

    monkeypatch.setattr(
        research_supervisor,
        "build_and_write_research_supervisor",
        lambda _settings: ({}, {}, []),
    )
    monkeypatch.setattr(
        self_healing,
        "build_and_write_self_healing_state",
        lambda _settings, perform_refresh=False: ({}, {}, []),
    )
    monkeypatch.setattr(
        operator_dashboard,
        "build_and_write_operator_dashboard",
        lambda _settings: ({}, {}, []),
    )
    monkeypatch.setattr(
        reliability,
        "build_permanent_reliability_certification",
        lambda _runtime: {"status": "passed"},
    )

    cycle = run_safe_operator_control_cycle(_settings(tmp_path))

    assert events[:2] == ["publish", "dispatch"]
    assert cycle["startup_projection_service_running"] is True
    assert cycle["startup_projection_status"] == "passed"


def test_bounded_dispatch_reserves_lifecycle_then_rotates_research(
    tmp_path,
    monkeypatch,
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(operator_service, "_market_is_open", lambda _timestamp: False)

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
    ] == ["paper_lifecycle_poll", "source_ingestion"]
    assert [
        receipt["service_id"] for receipt in second["receipts"] if receipt["state"] == "completed"
    ] == ["paper_lifecycle_poll", "historical_source_worker"]
    cursor = json.loads(
        (tmp_path / "qadam_operator_dispatch_cursor.json").read_text(encoding="utf-8")
    )
    assert cursor["last_executed_service_id"] == "historical_source_worker"
    assert cursor["next_service_id"] == "market_price_refresh"


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
    assert akber.command_sequence[-1] == (
        "scripts/check_qadam_akber_evidence_fit.py",
    )
    assert "qadam_akber_evidence_fit_checks.json" in akber.generation_artifacts


def test_evidence_fit_phases_6_to_8_are_wired_into_ordered_services() -> None:
    risk_router = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "portfolio_router_review"
    )
    trial = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "active_discovery_trial"
    )
    learning = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "learning_attribution"
    )

    assert risk_router.command_sequence[-1] == (
        "scripts/check_qadam_risk_router_alignment.py",
    )
    assert "qadam_router_root_cause_summary.json" in risk_router.generation_artifacts
    assert "qadam_active_discovery_trial_contract.json" not in trial.generation_artifacts
    assert "qadam_active_discovery_trial_status.json" in trial.generation_artifacts
    assert "qadam_active_discovery_trial_certification.json" in trial.generation_artifacts
    assert (
        "scripts/check_qadam_outcome_learning_promotion.py",
    ) in learning.command_sequence
    assert "qadam_strategy_version_registry.json" in learning.generation_artifacts


def test_pattern_scoring_builds_templates_before_pinned_historical_tape() -> None:
    scoring = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "pattern_scoring"
    )
    assert scoring.command_sequence == (
        ("scripts/check_qadam_pattern_score_v3.py",),
        ("scripts/run_qadam_pattern_score_tape.py", "--resume"),
    )
    assert "qadam_pattern_score_tape_checks.json" in scoring.generation_artifacts


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
    assert challenger.dependencies == ("pattern_scoring",)
    assert challenger.wake_on_dependency_advance is False


def test_routine_pattern_refresh_does_not_retrigger_weekly_challenger() -> None:
    challenger = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "challenger_research"
    )
    successful = {
        "pattern_scoring": {"completed_at": "2026-07-27T13:05:00+00:00"},
        "challenger_research": {"completed_at": "2026-07-27T13:00:00+00:00"},
    }

    assert operator_service._dependency_advanced(challenger, successful, set()) is False


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


def test_external_resource_contention_defers_without_failure_or_circuit(
    tmp_path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)

    class BusyLease:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            raise operator_service.ResourceLockBusy(
                resource="dashboard_projection",
                service_id="dashboard_refresh",
                timeout_seconds=0.01,
            )

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(operator_service, "ResourceLease", BusyLease)
    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        service_ids=("dashboard_refresh",),
        executor=_success_executor,
    )

    assert cycle["failed_count"] == 0
    assert cycle["executed_count"] == 0
    assert cycle["receipts"][0]["state"] == "skipped"
    assert cycle["receipts"][0]["skip_reason"] == "resource_claim_busy"
    circuits_path = tmp_path / "qadam_operator_circuit_breakers.json"
    if circuits_path.exists():
        circuits = json.loads(circuits_path.read_text(encoding="utf-8"))
        assert circuits.get("open_circuit_count", 0) == 0


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


def test_dashboard_refresh_rebuilds_vnext_before_qsase_without_router_v2() -> None:
    dashboard = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "dashboard_refresh"
    )

    assert dashboard.command_sequence[:3] == (
        ("scripts/check_qadam_dashboard_vnext.py",),
        ("scripts/check_qadam_evidence_fit_visibility.py",),
        ("scripts/check_qsase_dashboard_view_model.py",),
    )
    assert ("scripts/check_qadam_router_v2_paperops_handoff.py",) not in (
        dashboard.command_sequence
    )


def test_shadow_and_router_freshness_allow_bounded_challenger_serialization() -> None:
    assert FRESHNESS_SPECS[SHADOW_STATE_ARTIFACT] == 15 * 60
    assert FRESHNESS_SPECS[ROUTER_SCOREBOARD_ARTIFACT] == 15 * 60


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
        ("scripts/check_qadam_lifecycle_control_plane.py",),
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
    assert (
        classify_failure("error=market_clock_refresh_failed")
        == "transient_provider_network"
    )
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
        classify_failure("validation_error=score_tape_input_snapshot_unstable:alignment")
        == "concurrent_artifact_access"
    )
    assert (
        classify_failure("completed_score_tape_partition_immutable_mismatch:scores.jsonl")
        == "research_integrity_hold"
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


def test_dashboard_refresh_keeps_self_certification_out_of_dispatch_graph() -> None:
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh"
    )
    commands = [command[0] for command in definition.command_sequence]

    assert "scripts/check_qadam_clean_broker_account_preflight.py" in commands
    clean_preflight_command = next(
        command
        for command in definition.command_sequence
        if command[0] == "scripts/check_qadam_clean_broker_account_preflight.py"
    )
    assert clean_preflight_command == (
        "scripts/check_qadam_clean_broker_account_preflight.py",
        "--report-only",
    )
    assert "scripts/publish_qadam_public_status.py" not in commands
    assert "scripts/check_qadam_permanent_operator_reliability.py" not in commands
    assert "scripts/check_qadam_active_edge_research.py" not in commands
    assert "scripts/check_qadam_catc_dashboard_projection.py" in commands
    assert not any(
        item.service_id == "reliability_certification" for item in SERVICE_DEFINITIONS
    )
    publication = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "public_status_publication"
    )
    assert publication.dependencies == ("dashboard_refresh",)
    assert publication.command_sequence[0] == ("scripts/publish_qadam_public_status.py",)


def test_stale_derived_certification_does_not_create_circular_repair(tmp_path) -> None:
    _write_json(
        tmp_path / "qadam_operator_dashboard_freshness.json",
        {
            "records": [
                {
                    "artifact": "data/runtime/qadam_operator_ready_edge_engine_certification.json",
                    "freshness_state": "stale",
                },
                {
                    "artifact": "data/runtime/qadam_permanent_operator_reliability_status.json",
                    "freshness_state": "stale",
                },
                {
                    "artifact": "data/runtime/qadam_operator_service_status.json",
                    "freshness_state": "stale",
                },
            ]
        },
    )
    _write_json(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {}})

    queue = _build_repair_queue(
        tmp_path,
        service_installed=True,
        process_running=True,
        generated_at="2026-01-01T00:00:00+00:00",
    )

    assert queue["status"] == "repair_queue_clear"
    assert queue["open_request_count"] == 0


def test_stale_material_evidence_still_creates_repair_request(tmp_path) -> None:
    _write_json(
        tmp_path / "qadam_operator_dashboard_freshness.json",
        {
            "records": [
                {
                    "artifact": "data/runtime/qadam_edge_registry_summary.json",
                    "freshness_state": "stale",
                }
            ]
        },
    )
    _write_json(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {}})

    queue = _build_repair_queue(
        tmp_path,
        service_installed=True,
        process_running=True,
        generated_at="2026-01-01T00:00:00+00:00",
    )

    assert queue["status"] == "repair_queue_open"
    assert queue["open_request_count"] == 1
    assert queue["requests"][0]["category"] == "stale_artifact"


def test_retired_service_circuit_is_pruned_from_canonical_state(tmp_path) -> None:
    services = {
        "dashboard_refresh": {"state": "closed"},
        "reliability_certification": {
            "state": "open",
            "failure_class": "code_defect",
        },
    }

    operator_service._write_circuit_breakers(tmp_path, services)

    payload = json.loads(
        (tmp_path / "qadam_operator_circuit_breakers.json").read_text(encoding="utf-8")
    )
    assert payload["open_circuit_count"] == 0
    assert "reliability_certification" not in payload["services"]


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


def test_half_open_confirmation_survives_new_input_generations(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "code_defect",
                    "failure_fingerprint": "superseded-failure",
                    "consecutive_failure_count": 1,
                }
            }
        },
    )
    generation_pointer = tmp_path / ".qadam_generations" / "source_lake" / "current.json"
    generation_pointer.parent.mkdir(parents=True, exist_ok=True)

    states = []
    for generation_id in ("source-1", "source-2", "source-3"):
        _write_json(
            generation_pointer,
            {
                "generation_id": generation_id,
                "manifest_sha256": f"manifest-{generation_id}",
            },
        )
        cycle = dispatch_due_jobs(
            _settings(tmp_path),
            service_ids=("dashboard_refresh",),
            executor=_success_executor,
        )
        states.append(cycle["receipts"][0]["state"])

    assert states == [
        "completed_pending_circuit_confirmation",
        "completed_pending_circuit_confirmation",
        "completed",
    ]
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "closed"


def test_half_open_budget_skip_preserves_confirmation_progress(tmp_path) -> None:
    _ready_runtime(tmp_path)
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "half_open",
                    "failure_class": "code_defect",
                    "consecutive_failure_count": 2,
                    "revalidation_fingerprint": operator_service._service_revalidation_identity(
                        next(
                            item
                            for item in SERVICE_DEFINITIONS
                            if item.service_id == "dashboard_refresh"
                        )
                    ),
                    "revalidation_success_count": 1,
                }
            }
        },
    )

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("source_ingestion", "dashboard_refresh"),
        force_due=True,
        max_jobs=1,
        executor=_success_executor,
    )

    dashboard = next(
        receipt for receipt in cycle["receipts"] if receipt["service_id"] == "dashboard_refresh"
    )
    assert dashboard["state"] == "skipped"
    assert dashboard["skip_reason"] == "cycle_job_budget_exhausted"
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "half_open"
    assert circuits["services"]["dashboard_refresh"]["revalidation_success_count"] == 1


def test_bounded_cycle_reserves_capacity_for_paper_lifecycle(tmp_path) -> None:
    _ready_runtime(tmp_path)

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        force_due=True,
        max_jobs=4,
        executor=_success_executor,
    )

    lifecycle = next(
        receipt
        for receipt in cycle["receipts"]
        if receipt["service_id"] == "paper_lifecycle_poll"
    )
    assert lifecycle.get("skip_reason") != "cycle_job_budget_exhausted"
    assert lifecycle["state"] in {"completed", "skipped"}


def test_bounded_order_reserves_execution_before_stale_research() -> None:
    timestamp = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    generic = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "source_ingestion"
    )
    shadow = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "forward_shadow"
    )
    ordered = _bounded_dispatch_order(
        (generic, shadow),
        {
            generic.service_id: {
                "completed_at": (timestamp - timedelta(minutes=20)).isoformat()
            },
            shadow.service_id: {
                "completed_at": (timestamp - timedelta(minutes=11)).isoformat()
            },
        },
        timestamp=timestamp,
    )

    assert ordered[0].service_id == "forward_shadow"


def test_bounded_order_preserves_execution_reservation_before_research_rotation() -> None:
    timestamp = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    generic = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "source_ingestion"
    )
    shadow = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "forward_shadow"
    )
    ordered = _bounded_dispatch_order(
        (generic, shadow),
        {
            generic.service_id: {
                "completed_at": (timestamp - timedelta(minutes=20)).isoformat()
            },
            shadow.service_id: {
                "completed_at": (timestamp - timedelta(minutes=2)).isoformat()
            },
        },
        timestamp=timestamp,
    )

    assert [definition.service_id for definition in ordered] == [
        "forward_shadow",
        "source_ingestion",
    ]


def test_bounded_order_elevates_near_stale_decision_chain() -> None:
    timestamp = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    dashboard = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "dashboard_refresh"
    )
    akber = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "akber_review"
    )
    ordered = _bounded_dispatch_order(
        (dashboard, akber),
        {
            dashboard.service_id: {
                "completed_at": (timestamp - timedelta(minutes=2)).isoformat()
            },
            akber.service_id: {
                "completed_at": (timestamp - timedelta(minutes=11)).isoformat()
            },
        },
        timestamp=timestamp,
    )

    assert akber.freshness_deadline_seconds == 15 * 60
    assert ordered[0].service_id == "akber_review"


def test_public_dashboard_refresh_chain_has_pre_stale_deadlines() -> None:
    definitions = {
        definition.service_id: definition for definition in SERVICE_DEFINITIONS
    }

    assert definitions["dashboard_refresh"].freshness_deadline_seconds == 6 * 60
    assert definitions["public_status_publication"].freshness_deadline_seconds == 8 * 60
    assert definitions["public_status_publication"].latency_sensitive is True
    assert definitions["public_status_publication"].dependencies == (
        "dashboard_refresh",
    )


def test_expired_freshness_deadline_matches_latency_sensitive_priority() -> None:
    timestamp = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    dashboard = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "dashboard_refresh"
    )
    market = next(
        definition
        for definition in SERVICE_DEFINITIONS
        if definition.service_id == "market_price_refresh"
    )

    assert _freshness_deadline_priority(
        dashboard,
        {
            dashboard.service_id: {
                "completed_at": (timestamp - timedelta(minutes=6)).isoformat()
            }
        },
        timestamp=timestamp,
    ) == _freshness_deadline_priority(
        market,
        {},
        timestamp=timestamp,
    ) == 0


def test_transient_consistency_circuit_revalidates_same_stable_fingerprint(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh"
    )
    fingerprint = operator_service._service_revalidation_fingerprint(
        tmp_path,
        definition,
    )
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "concurrent_artifact_access",
                    "failure_fingerprint": fingerprint,
                    "last_failed_revalidation_fingerprint": fingerprint,
                    "automatic_revalidation_attempt_count": 0,
                    "next_retry_at": "2000-01-01T00:00:00+00:00",
                }
            }
        },
    )

    states = []
    receipts = []
    for _index in range(3):
        cycle = dispatch_due_jobs(
            _settings(tmp_path),
            service_ids=("dashboard_refresh",),
            executor=_success_executor,
        )
        receipt = cycle["receipts"][0]
        receipts.append(receipt)
        states.append(receipt["state"])

    assert states == [
        "completed_pending_circuit_confirmation",
        "completed_pending_circuit_confirmation",
        "completed",
    ]
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["dashboard_refresh"]["state"] == "closed"
    assert (
        circuits["services"]["dashboard_refresh"][
            "automatic_revalidation_attempt_count"
        ]
        == 0
    )
    assert all(receipt_state != "worker_started" for receipt_state in states)
    assert all(receipt["paper_order_created_count"] == 0 for receipt in receipts)
    assert all(receipt["broker_write_count"] == 0 for receipt in receipts)


def test_transient_consistency_same_fingerprint_revalidation_is_bounded(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    definition = next(
        item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh"
    )
    fingerprint = operator_service._service_revalidation_fingerprint(
        tmp_path,
        definition,
    )
    _write_json(
        tmp_path / "qadam_operator_circuit_breakers.json",
        {
            "services": {
                "dashboard_refresh": {
                    "state": "open",
                    "failure_class": "concurrent_artifact_access",
                    "failure_fingerprint": fingerprint,
                    "last_failed_revalidation_fingerprint": fingerprint,
                    "automatic_revalidation_attempt_count": 3,
                    "next_retry_at": "2000-01-01T00:00:00+00:00",
                }
            }
        },
    )

    cycle = dispatch_due_jobs(
        _settings(tmp_path),
        service_ids=("dashboard_refresh",),
        executor=_success_executor,
    )
    assert cycle["receipts"][0]["state"] == "skipped"
    assert cycle["receipts"][0]["skip_reason"] == "circuit_breaker_open"


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


def test_explicit_open_market_repair_is_broker_disabled(tmp_path) -> None:
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
                "open_market_conversion": {
                    "state": "open",
                    "failure_class": "code_defect",
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
        "open_market_conversion",
        _settings(tmp_path),
        executor=executor,
        explicit_open_market_conversion_confirmation=True,
    )

    assert result["status"] == "repaired"
    assert result["verification_pass_count"] == 3
    assert all("--no-paperops" in command for command, _timeout in calls)
    circuits = json.loads((tmp_path / "qadam_operator_circuit_breakers.json").read_text())
    assert circuits["services"]["open_market_conversion"]["state"] == "closed"


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


def test_finished_worker_reconciles_terminal_receipt_instead_of_interruption(
    tmp_path,
) -> None:
    _ready_runtime(tmp_path)
    receipt_id = "operator-receipt:completed-worker"
    _write_json(
        tmp_path / "qadam_operator_workers.json",
        {
            "workers": {
                "challenger_research": {
                    "service_id": "challenger_research",
                    "receipt_id": receipt_id,
                    "pid": 99999999,
                    "state": "running",
                    "concurrency_group": "historical_research",
                }
            }
        },
    )
    _append_receipt(
        tmp_path,
        {
            "schema_version": operator_service.SCHEMA_VERSION,
            "artifact_type": "qadam_operator_service_receipt",
            "receipt_id": receipt_id,
            "generated_at": "2026-07-30T06:00:00+00:00",
            "completed_at": "2026-07-30T06:00:00+00:00",
            "service_id": "challenger_research",
            "state": "worker_completed",
        },
    )

    worker = _workers(tmp_path)["challenger_research"]

    assert worker["state"] == "worker_completed"
    assert worker["exit_code"] == 0
    assert worker["why"] == "terminal_receipt_reconciled_after_worker_exit"


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


def test_dashboard_refresh_uses_one_quantum_projection_without_optional_health_chain() -> None:
    service = next(
        row for row in SERVICE_DEFINITIONS if row.service_id == "dashboard_refresh"
    )
    commands = [command[0] for command in service.command_sequence]
    retired = [
        "scripts/check_qadam_wave_f_public_view.py",
        "scripts/check_qadam_wave_g_hybrid_loop.py",
        "scripts/check_qadam_wave_h_crude_oil_certification.py",
    ]
    assert "scripts/check_qadam_quantum_edge_page_view_model.py" in commands
    assert all(command not in commands for command in retired)


def test_dashboard_refresh_updates_operator_health_before_export() -> None:
    service = next(
        row for row in SERVICE_DEFINITIONS if row.service_id == "dashboard_refresh"
    )
    commands = [command[0] for command in service.command_sequence]

    assert commands.index("scripts/check_qadam_operator_service.py") < commands.index(
        "scripts/export_cockpit_status.py"
    )
    assert (
        "scripts/check_qadam_operator_service.py",
        "--report-only",
    ) in service.command_sequence


def test_dashboard_integration_probe_does_not_recurse_into_operator_certification() -> None:
    service = next(
        row for row in SERVICE_DEFINITIONS if row.service_id == "dashboard_refresh"
    )

    assert service.integration_probe_command_sequence
    assert all(
        command[0] != "scripts/check_qadam_operator_service.py"
        for command in service.integration_probe_command_sequence
    )
    assert service.integration_probe_command_sequence[-1] == (
        "scripts/export_cockpit_status.py",
        "--no-landing-copy",
    )
