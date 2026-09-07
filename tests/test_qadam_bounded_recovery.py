from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os

import pytest

from orchestrator.config import Settings
from orchestrator.runtime import operator as op
from orchestrator.runtime.recovery import advance_recovery, verified_recovery_receipt
from orchestrator.runtime.scheduling import order_by_deadline_slack
from orchestrator.qadam_artifact_generations import ArtifactGenerationStore, GenerationError
from orchestrator.qadam_permanent_operator_reliability import _generation_binding_record


@pytest.fixture
def environment(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), data_root=str(tmp_path))
    monkeypatch.setattr(op, "_git_output", lambda *_: "test-release")
    monkeypatch.setattr(op, "operator_service_contract_hash", lambda: "test-contract")
    return settings, tmp_path


def receipt(request, service_id, **updates):
    return {
        "receipt_id": service_id + "-receipt",
        "service_id": service_id,
        "state": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "operator_build_identity": {
            "git_commit": request["git_commit"],
            "service_contract_hash": request["operator_service_contract_hash"],
            "dirty_worktree": False,
        },
        **updates,
    }


def test_coalesces_without_resetting_progress_or_request_age(environment):
    settings, runtime = environment
    first = op.request_operator_full_heal(["source_ingestion"], settings)
    op._update_full_heal_request_state(
        runtime,
        first["request_id"],
        status="in_progress",
        completed_service_ids=["source_ingestion"],
    )
    second = op.request_operator_full_heal(["dashboard_refresh"], settings)
    assert second["request_id"] == first["request_id"]
    assert second["generated_at"] == first["generated_at"]
    assert second["completed_service_ids"] == ["source_ingestion"]
    assert set(second["service_ids"]) == {"source_ingestion", "dashboard_refresh"}
    assert second["requested_after_by_service"]["dashboard_refresh"] >= first["generated_at"]


@pytest.mark.parametrize(
    "change",
    [
        {"completed_at": "2000-01-01T00:00:00+00:00"},
        {"completed_at": "2099-01-01T00:00:00+00:00"},
        {"state": "worker_started"},
        {"state": "completed_pending_circuit_confirmation"},
        {"state": "skipped", "skip_reason": "resource_claim_busy"},
        {"operator_build_identity": {"git_commit": "other"}},
    ],
)
def test_recovery_does_not_certify_old_unfinished_or_other_build_work(environment, change):
    request = op.request_operator_full_heal(["source_ingestion"], environment[0])
    assert not verified_recovery_receipt(
        receipt(request, "source_ingestion", **change), request, "source_ingestion"
    )


def test_recovery_yields_resumes_and_includes_normal_work(environment, monkeypatch):
    settings, runtime = environment
    request = op.request_operator_full_heal(["source_ingestion", "dashboard_refresh"], settings)
    targets = []

    def cycle(_settings, **kwargs):
        selected = kwargs["recovery_service_ids"]
        targets.append(selected)
        assert kwargs.get("force_due") is not True
        assert kwargs.get("service_ids") is None  # Normal service scheduling is not suspended.
        assert kwargs["max_elapsed_seconds"] == 120
        service_id = selected[0]
        kwargs["progress_callback"](service_id, None)
        in_flight = op.read_json(runtime / op.FULL_HEAL_REQUEST_ARTIFACT)
        assert in_flight["current_service_ids"] == [service_id]
        row = receipt(request, service_id)
        kwargs["progress_callback"](service_id, row)
        return {"status": "passed", "dispatch_receipts": [row], "dispatch_failed_count": 0}

    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    first = advance_recovery(request, settings)
    assert first["status"] == "in_progress"
    assert first["remaining_service_ids"] == ["dashboard_refresh"]
    second = advance_recovery(op.pending_operator_full_heal_request(settings), settings)
    assert second["status"] == "completed"
    assert targets == [("source_ingestion", "dashboard_refresh"), ("dashboard_refresh",)]
    assert not second["all_services_currently_fresh"]
    assert second["canonical_paperops_submitted_order_count"] == 0


def test_crash_after_receipt_before_checkpoint_does_not_replay_completed_work(
    environment, monkeypatch
):
    settings, runtime = environment
    request = op.request_operator_full_heal(["source_ingestion"], settings)
    row = receipt(request, "source_ingestion")
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _runtime: {"source_ingestion": row})

    def cycle(_settings, **kwargs):
        assert kwargs["recovery_service_ids"] == ()
        return {"status": "passed"}

    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    assert advance_recovery(request, settings)["status"] == "completed"


def test_coalesced_scope_during_repair_is_not_lost(environment, monkeypatch):
    settings, runtime = environment
    request = op.request_operator_full_heal(["source_ingestion"], settings)

    def cycle(_settings, **kwargs):
        kwargs["progress_callback"]("source_ingestion", receipt(request, "source_ingestion"))
        op.request_operator_full_heal(["dashboard_refresh"], settings)
        return {"status": "passed"}

    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    result = advance_recovery(request, settings)
    assert result["status"] == "in_progress"
    assert result["remaining_service_ids"] == ["dashboard_refresh"]


def test_deadline_slack_rescues_publication_before_research_replay():
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    sequence = tuple(
        definitions[x]
        for x in ("source_ingestion", "dashboard_refresh", "public_status_publication")
    )
    successful = {
        "source_ingestion": {"completed_at": now.isoformat(), "duration_seconds": 60},
        "dashboard_refresh": {
            "completed_at": (now - timedelta(seconds=100)).isoformat(),
            "duration_seconds": 40,
        },
        "public_status_publication": {
            "completed_at": (now - timedelta(seconds=475)).isoformat(),
            "duration_seconds": 15,
        },
    }
    ordered = order_by_deadline_slack(
        sequence, successful, timestamp=now, recovery_targets={"source_ingestion"}
    )
    assert ordered[0].service_id == "public_status_publication"
    assert ordered[1].service_id == "source_ingestion"


def test_publication_priority_uses_payload_age_not_successful_send_time():
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    sequence = tuple(definitions[x] for x in (
        "source_ingestion", "dashboard_refresh", "public_status_publication"
    ))
    successful = {d.service_id: {"completed_at": now.isoformat()} for d in sequence}
    clocks = {
        "dashboard_refresh": now.isoformat(),
        "public_status_publication": (now - timedelta(seconds=450)).isoformat(),
    }
    ordered = order_by_deadline_slack(
        sequence, successful, timestamp=now, recovery_targets={"source_ingestion"},
        output_observed_at=clocks,
    )
    assert ordered[0].service_id == "public_status_publication"
    clocks["dashboard_refresh"] = clocks["public_status_publication"]
    ordered = order_by_deadline_slack(
        sequence, successful, timestamp=now, output_observed_at=clocks
    )
    assert [d.service_id for d in ordered[:2]] == ["dashboard_refresh", "public_status_publication"]


@pytest.mark.parametrize("age,expected", [(20, "fresh"), (601, "stale"), (-1, "stale"), (None, "not_run")])
def test_publication_health_cannot_hide_old_missing_or_future_payload(age, expected):
    now = datetime.now(timezone.utc)
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "public_status_publication")
    row = op._service_runtime_record(
        definition, generated_at=now.isoformat(), research_lock_active=False,
        release_effective=True, process_running=True,
        last_successful_receipt={"completed_at": now.isoformat()},
        output_freshness_required=True,
        output_observed_at=(now - timedelta(seconds=age)).isoformat() if age is not None else None,
    )
    assert row["freshness"]["state"] == expected
    assert row["freshness"]["stale_after_seconds"] == 600


@pytest.mark.parametrize(
    "state,expected", [("market_closed", True), ("not_due", False), ("resource_claim_busy", False)]
)
def test_closed_market_join_not_required_but_other_skips_are_not_proof(state, expected):
    now = datetime.now(timezone.utc)
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "open_market_conversion")
    result, errors = _generation_binding_record(
        definition,
        successful_receipt={},
        latest_receipt={
            "state": "skipped",
            "skip_reason": state,
            "generated_at": now.isoformat(),
        },
        now=now,
    )
    assert result["binding_complete"] is expected
    assert bool(errors) is not expected


def test_market_closed_does_not_hide_a_previous_bad_join():
    now = datetime.now(timezone.utc)
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "open_market_conversion")
    result, errors = _generation_binding_record(
        definition,
        successful_receipt={"input_generation_binding_complete": False},
        latest_receipt={
            "state": "skipped",
            "skip_reason": "market_closed",
            "generated_at": now.isoformat(),
        },
        now=now,
    )
    assert not result["binding_complete"]
    assert errors


def test_generation_copy_does_not_copy_os_metadata(tmp_path, monkeypatch):
    import shutil

    source = tmp_path / "input.json"
    source.write_text('{"value":1}')
    monkeypatch.setattr(
        shutil, "copy2", lambda *_: (_ for _ in ()).throw(PermissionError("metadata denied"))
    )
    store = ArtifactGenerationStore(tmp_path, "source_lake")
    reference = store.publish_files({source.name: source}, producer="test")
    store.validate_reference(reference)
    assert (reference.path / source.name).read_bytes() == source.read_bytes()


def test_generation_copy_race_never_advances_pointer(tmp_path, monkeypatch):
    import shutil

    source = tmp_path / "input.json"
    source.write_text('{"value":1}')
    store = ArtifactGenerationStore(tmp_path, "source_lake")
    reference = store.publish_files({source.name: source}, producer="test")
    source.write_text('{"value":2}')
    original = shutil.copyfile

    def mutate(src, dst):
        source.write_text('{"value":3}')
        return original(src, dst)

    monkeypatch.setattr(shutil, "copyfile", mutate)
    with pytest.raises(GenerationError, match="source_changed_during_copy"):
        store.publish_files({source.name: source}, producer="test")
    assert store.resolve_current().generation_id == reference.generation_id


def test_scheduler_uses_provider_holiday_calendar(environment):
    _settings, runtime = environment
    now = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)
    (runtime / "alpaca_paper_mirror.json").write_text(
        json.dumps(
            {
                "market_calendar": {
                    "provider": "alpaca_calendar_v2",
                    "observed_at": now.isoformat(),
                    "start": "2026-09-01",
                    "end": "2026-09-30",
                    "sessions": [{"date": "2026-09-08", "open": "09:30", "close": "16:00"}],
                }
            }
        )
    )
    assert not op._scheduled_market_is_open(now, runtime)


@pytest.mark.parametrize("maintenance", [False, True])
def test_scheduler_yields_after_complete_service_not_in_middle(
    environment, monkeypatch, maintenance
):
    settings, runtime = environment
    clock = [0.0]
    monkeypatch.setattr(op.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(op, "maintenance_request_active", lambda _r: maintenance and clock[0] > 0)

    def execute(*args, **kwargs):
        clock[0] += 121
        return {
            "state": "completed",
            "duration_seconds": 121,
            "command_results": [],
            "generation_ids": {},
            "input_generation_ids": {},
            "input_generation_binding_complete": True,
            "mixed_generation_join_count": 0,
        }

    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    cycle = op.dispatch_due_jobs(
        settings,
        service_ids=("source_ingestion", "execution_context"),
        max_elapsed_seconds=120,
        force_due=True,
    )
    assert cycle["executed_count"] == 1
    assert cycle["receipts"][0]["state"] == "completed"
    assert cycle["receipts"][1]["skip_reason"] == (
        "maintenance_requested" if maintenance else "cycle_time_budget_exhausted"
    )
    assert cycle["yield_boundary"] == "completed_service_only"


def test_broken_research_service_does_not_prevent_other_safe_repairs():
    from orchestrator.qadam_reliability_critic import plan_safe_repairs

    snapshot = {
        "circuits": {"services": {"qualitative_evidence_cycle": {"failure_class": "code_defect"}}}
    }
    classification = {
        "blockers": [
            {
                "code": "operator_service_circuit_open",
                "service_id": "qualitative_evidence_cycle",
                "safe_auto_repair_allowed": False,
            },
            {
                "code": "operator_service_stale",
                "service_id": "source_ingestion",
                "safe_auto_repair_allowed": True,
            },
        ]
    }
    actions = plan_safe_repairs(snapshot, classification)
    assert actions[0]["service_ids"] == ["source_ingestion"]
    snapshot["circuits"]["services"]["qualitative_evidence_cycle"]["failure_class"] = (
        "safety_violation"
    )
    assert plan_safe_repairs(snapshot, classification) == []


def test_worker_completion_retains_launch_build_not_later_checkout(environment):
    _settings, runtime = environment
    (runtime / op.WORKERS_ARTIFACT).write_text(
        json.dumps(
            {
                "workers": {
                    "historical_source_worker": {
                        "receipt_id": "worker-1",
                        "pid": os.getpid(),
                        "operator_build_identity": {"git_commit": "launch-sha"},
                    }
                }
            }
        )
    )
    row = {
        "service_id": "historical_source_worker",
        "receipt_id": "worker-1",
        "worker_pid": os.getpid(),
        "state": "worker_completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    op._append_receipt(runtime, row)
    assert row["operator_build_identity"] == {"git_commit": "launch-sha"}


def test_service_commands_share_one_timeout_not_one_timeout_each(environment, monkeypatch):
    _settings, runtime = environment
    clock = [0.0]
    monkeypatch.setattr(op.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(op, "_resolve_input_generation_ids", lambda *_: {})
    published = []
    monkeypatch.setattr(op, "_publish_service_generations", lambda *_: published.append(True))
    definition = replace(next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "execution_context"),
                         timeout_seconds=10, command_sequence=(("scripts/check_qadam_execution_context.py",),) * 3)
    timeouts = []

    def executor(_command, timeout):
        timeouts.append(timeout)
        clock[0] += 8
        return {"returncode": 0}

    result = op._execute_service_synchronously(definition, runtime=runtime, executor=executor)
    assert timeouts == [10, 2]
    assert result["state"] == "failed"
    assert result["command_results"][-1]["stderr_tail"] == "service_execution_deadline_exceeded"
    assert published == []
