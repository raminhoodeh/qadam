from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os

import pytest

from orchestrator.config import Settings
from orchestrator.runtime import operator as op
from orchestrator.runtime.recovery import advance_recovery, verified_recovery_receipt
from orchestrator.runtime.scheduling import order_by_deadline_slack, output_refresh_due, _is_due
from orchestrator.qadam_artifact_generations import ArtifactGenerationStore, GenerationError
from orchestrator.qadam_permanent_operator_reliability import _generation_binding_record


@pytest.fixture
def environment(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), data_root=str(tmp_path))
    monkeypatch.setattr(op, "_git_output", lambda *_: "test-release")
    monkeypatch.setattr(op, "operator_service_contract_hash", lambda: "test-contract")
    (tmp_path / "cockpit-status.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat()}))
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


@pytest.mark.parametrize("age", [None, -60, 361, 1800])
def test_publication_repair_includes_expired_or_unknown_producer(environment, age):
    settings, runtime = environment
    path = runtime / "cockpit-status.json"
    if age is None:
        path.unlink()
    else:
        path.write_text(json.dumps({"generated_at": (
            datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()}))
    request = op.request_operator_full_heal(["public_status_publication"], settings)
    assert request["service_ids"] == ["dashboard_refresh", "public_status_publication"]


def test_publication_repair_reuses_a_current_local_projection(environment):
    request = op.request_operator_full_heal(["public_status_publication"], environment[0])
    assert request["service_ids"] == ["public_status_publication"]


def test_successful_transport_cannot_heal_an_expired_payload(environment, monkeypatch):
    settings, runtime = environment
    service = "public_status_publication"
    request = op.request_operator_full_heal([service], settings)
    path = runtime / "qadam_public_status_publication_receipt.json"
    def published(age):
        path.write_text(json.dumps({"status": "published", "published": True,
            "payload_generated_at": (datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()}))
    def cycle(_settings, **kwargs):
        kwargs["progress_callback"](service, receipt(request, service))
        return {"status": "passed"}
    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    published(900)
    failed = advance_recovery(request, settings)
    assert failed["status"] == "in_progress"
    assert failed["remaining_service_ids"] == [service]
    assert not failed["all_requested_services_revalidated"]
    published(0)
    passed = advance_recovery(op.pending_operator_full_heal_request(settings), settings)
    assert passed["status"] == "completed"


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


def test_calendar_skip_cannot_certify_conversion_evidence_repaired(environment):
    request = op.request_operator_full_heal(["open_market_conversion"], environment[0])
    skipped = receipt(request, "open_market_conversion", state="skipped", skip_reason="market_closed")
    assert not verified_recovery_receipt(skipped, request, "open_market_conversion")
    assert verified_recovery_receipt(receipt(request, "open_market_conversion"), request, "open_market_conversion")


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


def test_dependency_wait_does_not_exhaust_downstream_repair_campaign(environment, monkeypatch):
    settings, runtime = environment
    request = op.request_operator_full_heal(["portfolio_router_review"], settings)
    def cycle(_settings, **kwargs):
        kwargs["progress_callback"]("portfolio_router_review", receipt(
            request, "portfolio_router_review", state="failed", failure_class="dependency_unavailable"))
        return {"status": "passed"}
    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    for _ in range(4):
        result = advance_recovery(op.pending_operator_full_heal_request(settings), settings)
        assert result["status"] == "in_progress"
        assert result["failed_attempts_by_service"].get("portfolio_router_review", 0) == 0


@pytest.mark.parametrize("report_failure", [True, False])
def test_late_circuit_failure_invalidates_prior_recovery_success(environment, monkeypatch, report_failure):
    settings, runtime = environment
    service = "public_status_publication"
    request = op.request_operator_full_heal([service], settings)
    circuits = {}
    monkeypatch.setattr(op, "_circuit_breaker_state", lambda _: circuits)

    def cycle(_settings, **kwargs):
        kwargs["progress_callback"](service, receipt(request, service))
        circuits[service] = {"state": "open", "failure_class": "transient_provider_network"}
        if report_failure:
            kwargs["progress_callback"](service, receipt(request, service, state="failed"))
        return {"status": "completed_with_failures"}

    monkeypatch.setattr(op, "run_safe_operator_control_cycle", cycle)
    result = advance_recovery(request, settings)
    assert result["status"] == "in_progress"
    assert not result["all_requested_services_revalidated"]
    assert result["remaining_service_ids"] == [service]
    assert service not in result["completed_service_ids"]


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


@pytest.mark.parametrize("wait", [299, 300, 1800])
def test_waiting_repair_cannot_be_starved_by_repeating_projection(wait):
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    sequence = tuple(definitions[s] for s in (
        "dashboard_refresh", "qualitative_evidence_cycle", "learning_attribution",
        "execution_position_care", "guarded_paperops", "market_price_refresh", "paper_lifecycle_poll",
    ))
    successful = {d.service_id: {"completed_at": now.isoformat()} for d in sequence}
    successful["dashboard_refresh"] = {
        "completed_at": (now - timedelta(seconds=300)).isoformat(), "duration_seconds": 120}
    targets = {"qualitative_evidence_cycle", "learning_attribution"}
    ordered = [d.service_id for d in order_by_deadline_slack(
        sequence, successful, timestamp=now, recovery_targets=targets,
        recovery_started_at=(now - timedelta(seconds=wait)).isoformat(),
    )]
    assert ordered[:2] == ["execution_position_care", "guarded_paperops"]
    if wait >= 300:
        assert ordered.index("market_price_refresh") < ordered.index("qualitative_evidence_cycle")
        assert ordered.index("paper_lifecycle_poll") < ordered.index("qualitative_evidence_cycle")
        assert all(ordered.index(s) < ordered.index("dashboard_refresh") for s in targets)
    else:
        assert ordered.index("dashboard_refresh") < ordered.index("qualitative_evidence_cycle")
    assert set(ordered) == {d.service_id for d in sequence}


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


@pytest.mark.parametrize(
    "local_age,published_age,first",
    [
        (170, 650, "public_status_publication"),
        (170, None, "public_status_publication"),
        (170, 170, "dashboard_refresh"),
        (450, 650, "dashboard_refresh"),
        (-1, 650, "dashboard_refresh"),
        (None, 650, "dashboard_refresh"),
    ],
)
def test_completed_projection_is_published_before_another_slow_refresh(
    local_age, published_age, first
):
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    sequence = tuple(definitions[s] for s in (
        "source_ingestion", "dashboard_refresh", "public_status_publication"
    ))
    successful = {
        "source_ingestion": {"completed_at": now.isoformat()},
        "dashboard_refresh": {
            "completed_at": (now - timedelta(seconds=100)).isoformat(),
            "duration_seconds": 120,
        },
        "public_status_publication": {
            "completed_at": (now - timedelta(seconds=600)).isoformat(),
            "duration_seconds": 15,
        },
    }
    clocks = {
        "dashboard_refresh": (
            (now - timedelta(seconds=local_age)).isoformat() if local_age is not None else None
        ),
        "public_status_publication": (
            (now - timedelta(seconds=published_age)).isoformat()
            if published_age is not None else None
        ),
    }
    ordered = order_by_deadline_slack(
        sequence, successful, timestamp=now,
        recovery_targets={"source_ingestion"}, output_observed_at=clocks,
    )
    assert ordered[0].service_id == first
    assert {d.service_id for d in ordered} == {d.service_id for d in sequence}


def test_bounded_dispatch_delivers_pending_snapshot_before_rebuilding(environment, monkeypatch):
    settings, runtime = environment
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    sequence = tuple(definitions[s] for s in (
        "source_ingestion", "dashboard_refresh", "public_status_publication"
    ))
    successful = {
        "source_ingestion": {"completed_at": now.isoformat()},
        "dashboard_refresh": {
            "completed_at": (now - timedelta(seconds=100)).isoformat(),
            "duration_seconds": 120,
        },
        "public_status_publication": {
            "completed_at": (now - timedelta(seconds=650)).isoformat(),
            "duration_seconds": 15,
        },
    }
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: successful)
    monkeypatch.setattr(op, "_fair_dispatch_order", lambda *args, **kwargs: (sequence, 0))
    (runtime / "cockpit-status.json").write_text(json.dumps({
        "generated_at": (now - timedelta(seconds=170)).isoformat(),
    }))
    (runtime / "qadam_public_status_publication_receipt.json").write_text(json.dumps({
        "payload_generated_at": (now - timedelta(seconds=650)).isoformat(),
    }))
    executed = []

    def execute(definition, **kwargs):
        executed.append(definition.service_id)
        return {
            "state": "completed", "duration_seconds": 1, "command_results": [],
            "generation_ids": {}, "input_generation_ids": {},
            "input_generation_binding_complete": True, "mixed_generation_join_count": 0,
        }

    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    cycle = op.dispatch_due_jobs(settings, max_jobs=1, max_elapsed_seconds=120, executor=lambda *_a, **_k: {})
    assert executed == ["public_status_publication"]
    assert cycle["executed_count"] == 1
    dashboard = next(r for r in cycle["receipts"] if r["service_id"] == "dashboard_refresh")
    assert dashboard["skip_reason"] == "cycle_job_budget_exhausted"


def test_urgent_projection_is_due_before_cadence_and_publishes_before_research():
    now = datetime.now(timezone.utc)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    successful = {
        "dashboard_refresh": {
            "completed_at": (now - timedelta(seconds=170)).isoformat(), "duration_seconds": 40,
        },
        "public_status_publication": {"completed_at": now.isoformat()},
        "source_ingestion": {"completed_at": now.isoformat()},
    }
    dashboard = definitions["dashboard_refresh"]
    assert not _is_due(dashboard, successful["dashboard_refresh"], timestamp=now)
    assert output_refresh_due(
        dashboard, successful["dashboard_refresh"], timestamp=now,
        observed_at=successful["dashboard_refresh"]["completed_at"],
    )
    assert not output_refresh_due(
        dashboard, successful["dashboard_refresh"], timestamp=now, observed_at=now.isoformat()
    )
    sequence = [definitions[s] for s in ("source_ingestion", "dashboard_refresh", "public_status_publication")]
    assert [d.service_id for d in order_by_deadline_slack(
        sequence, successful, timestamp=now, recovery_targets={"source_ingestion"},
    )] == ["dashboard_refresh", "public_status_publication", "source_ingestion"]


def test_dispatch_rechecks_completed_projection_handoff_after_order_was_chosen(environment, monkeypatch):
    settings, runtime = environment
    now = datetime.now(timezone.utc)
    local = (now-timedelta(seconds=150)).isoformat()
    successful = {
        "dashboard_refresh": {"completed_at": now.isoformat(), "duration_seconds": 142},
        "public_status_publication": {"completed_at": now.isoformat(), "duration_seconds": 5},
    }
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: successful)
    (runtime / "cockpit-status.json").write_text(json.dumps({"generated_at": local}))
    (runtime / "qadam_public_status_publication_receipt.json").write_text(json.dumps({
        "payload_generated_at": (now-timedelta(seconds=1800)).isoformat()}))
    # Model a batch order chosen before a background projection finished.
    monkeypatch.setattr(op, "order_by_deadline_slack", lambda definitions, *_a, **_k: sorted(
        definitions, key=lambda d: d.service_id != "dashboard_refresh"))
    executed = []
    def execute(definition, **_kwargs):
        executed.append(definition.service_id)
        return {"state": "completed", "duration_seconds": 1, "command_results": [],
            "generation_ids": {}, "input_generation_ids": {},
            "input_generation_binding_complete": True, "mixed_generation_join_count": 0}
    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    cycle = op.dispatch_due_jobs(settings, service_ids=("dashboard_refresh", "public_status_publication"),
        max_jobs=1, max_elapsed_seconds=120, executor=lambda *_a, **_k: {})
    assert executed == ["public_status_publication"]
    refresh = next(r for r in cycle["receipts"] if r["service_id"] == "dashboard_refresh")
    assert refresh["skip_reason"] == "unpublished_projection_delivery_pending"


def test_dispatch_actually_refreshes_urgent_projection_without_force_due(environment, monkeypatch):
    settings, runtime = environment
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(seconds=170)).isoformat()
    successful = {
        "dashboard_refresh": {"completed_at": recent, "duration_seconds": 40},
        "public_status_publication": {"completed_at": now.isoformat()},
    }
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: successful)
    (runtime / "cockpit-status.json").write_text(json.dumps({"generated_at": recent}))
    (runtime / "qadam_public_status_publication_receipt.json").write_text(json.dumps({
        "payload_generated_at": recent, "published": True,
    }))
    executed = []

    def execute(definition, **kwargs):
        executed.append(definition.service_id)
        return {
            "state": "completed", "duration_seconds": 1, "command_results": [],
            "generation_ids": {}, "input_generation_ids": {},
            "input_generation_binding_complete": True, "mixed_generation_join_count": 0,
        }

    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    cycle = op.dispatch_due_jobs(
        settings, service_ids=("dashboard_refresh", "public_status_publication"),
        max_elapsed_seconds=120,
        executor=lambda *_a, **_k: {},
    )
    assert cycle["executed_count"] == 2
    assert executed == ["dashboard_refresh", "public_status_publication"]


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
        executor=lambda *_a, **_k: {},
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


@pytest.mark.parametrize("age,expected", [(3600, False), (10801, True)])
def test_exhausted_transient_budget_gets_only_a_low_frequency_probe(environment, monkeypatch, age, expected):
    _settings, runtime = environment
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "source_ingestion")
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "same")
    circuit = {
        "state": "open", "failure_class": "transient_provider_network",
        "automatic_revalidation_attempt_count": 3,
        "failure_fingerprint": "same", "last_failed_revalidation_fingerprint": "same",
        "last_failure_at": (now - timedelta(seconds=age)).isoformat(),
    }
    assert op._circuit_revalidation_allowed(runtime, definition, circuit)[0] is expected
    circuit["next_retry_at"] = (now + timedelta(hours=1)).isoformat()
    assert not op._circuit_revalidation_allowed(runtime, definition, circuit)[0]
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "new-input")
    assert not op._circuit_revalidation_allowed(runtime, definition, circuit)[0]
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "same")
    circuit["next_retry_at"] = None
    for failure_class in ("credential_operator_action", "safety_violation", "research_integrity_hold", "code_defect"):
        assert not op._circuit_revalidation_allowed(runtime, definition, {
            **circuit, "failure_class": failure_class,
        })[0]
    assert not op._circuit_revalidation_allowed(runtime, replace(definition, paperops_dependency=True), circuit)[0]


def test_failed_cooldown_probe_keeps_circuit_open_and_schedules_next_probe(environment, monkeypatch):
    _settings, runtime = environment
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "source_ingestion")
    now = datetime.now(timezone.utc)
    op._write_circuit_breakers(runtime, {"source_ingestion": {
        "state": "open", "failure_class": "transient_provider_network",
        "automatic_revalidation_attempt_count": 3, "consecutive_failure_count": 8,
        "last_failure_at": (now - timedelta(hours=4)).isoformat(),
    }})
    monkeypatch.setattr(op, "classify_failure", lambda _: "transient_provider_network")
    op._record_failure(runtime, definition, {
        "receipt_id": "probe-failure", "completed_at": now.isoformat(),
        "circuit_revalidation": True, "command_results": [{"returncode": 1}],
    })
    circuit = op._circuit_breaker_state(runtime)["source_ingestion"]
    assert circuit["state"] == "open"
    assert circuit["automatic_revalidation_attempt_count"] == 4
    assert circuit["automatic_cooldown_probe_scheduled"]
    assert datetime.fromisoformat(circuit["next_retry_at"]) >= now + timedelta(hours=3)


def _dependency_repair_inputs(runtime, monkeypatch):
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "active_discovery_trial")
    now = datetime.now(timezone.utc)
    producer = {"state": "worker_completed", "integration_probe": False,
                "completed_at": (now - timedelta(seconds=60)).isoformat(),
                "generation_ids": {"learning_plane": "repaired-generation"},
                "input_generation_binding_complete": True,
                "operator_build_identity": {"git_commit": "reviewed-release", "dirty_worktree": False,
                                            "service_contract_hash": "test-contract"}}
    circuit = {"state": "open", "failure_class": "dependency_unavailable",
               "automatic_revalidation_attempt_count": 3, "consecutive_failure_count": 6,
               "failure_fingerprint": "failed-input",
               "last_failure_at": (now - timedelta(seconds=300)).isoformat(),
               "next_retry_at": (now + timedelta(hours=3)).isoformat()}
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: {"portfolio_router_review": producer})
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "repaired-input")
    monkeypatch.setattr(op, "_service_revalidation_identity", lambda *_: "reviewed-executable")
    return definition, circuit, producer, now


def test_verified_dependency_repair_wakes_exhausted_readonly_consumer(environment, monkeypatch):
    _settings, runtime = environment
    definition, circuit, _producer, _now = _dependency_repair_inputs(runtime, monkeypatch)
    assert op._circuit_revalidation_allowed(runtime, definition, circuit)[0]


@pytest.mark.parametrize("fault", [
    "unchanged_input", "old_producer", "future_producer", "stale_producer", "probe",
    "dirty_producer", "wrong_contract", "missing_generation", "unbound_input",
    "producer_circuit", "network", "safety", "credentials", "execution_service",
])
def test_dependency_wakeup_needs_actual_safe_fresh_producer_evidence(environment, monkeypatch, fault):
    _settings, runtime = environment
    definition, circuit, producer, now = _dependency_repair_inputs(runtime, monkeypatch)
    if fault == "unchanged_input":
        monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "failed-input")
    elif fault == "old_producer":
        producer["completed_at"] = (now - timedelta(seconds=301)).isoformat()
    elif fault == "future_producer":
        producer["completed_at"] = (now + timedelta(seconds=1)).isoformat()
    elif fault == "stale_producer":
        circuit["last_failure_at"] = (now - timedelta(hours=3)).isoformat()
        producer["completed_at"] = (now - timedelta(hours=1)).isoformat()
    elif fault == "probe":
        producer["integration_probe"] = True
    elif fault == "dirty_producer":
        producer["operator_build_identity"]["dirty_worktree"] = True
    elif fault == "wrong_contract":
        producer["operator_build_identity"]["service_contract_hash"] = "other-contract"
    elif fault == "missing_generation":
        producer["generation_ids"] = {}
    elif fault == "unbound_input":
        producer["input_generation_binding_complete"] = False
    elif fault == "producer_circuit":
        op._write_circuit_breakers(runtime, {"portfolio_router_review": {"state": "open"}})
    elif fault in {"network", "safety", "credentials"}:
        circuit["failure_class"] = {"network": "transient_provider_network", "safety": "safety_violation",
                                    "credentials": "credential_operator_action"}[fault]
    elif fault == "execution_service":
        definition = replace(definition, paperops_dependency=True)
    assert not op._circuit_revalidation_allowed(runtime, definition, circuit)[0]


def test_dependency_wakeup_requires_three_real_successful_checks_before_closing(environment, monkeypatch):
    from tests.test_qadam_operator_service_v2 import _settings

    _unused, runtime = environment
    settings = _settings(runtime)
    definition, circuit, _producer, _now = _dependency_repair_inputs(runtime, monkeypatch)
    op._write_circuit_breakers(runtime, {definition.service_id: circuit})
    calls = []

    def execute(*args, **kwargs):
        calls.append(True)
        return {"state": "completed", "duration_seconds": 0.01, "command_results": [],
                "generation_ids": {"dashboard_projection": "checked"}, "input_generation_ids": {},
                "input_generation_binding_complete": True, "mixed_generation_join_count": 0}

    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    for expected in (1, 2, 3):
        cycle = op.dispatch_due_jobs(settings, service_ids=(definition.service_id,),
                                    recovery_service_ids=(definition.service_id,),
                                    executor=lambda *_: {"returncode": 0})
        state = op._circuit_breaker_state(runtime)[definition.service_id]
        assert state["state"] == ("closed" if expected == 3 else "half_open"), cycle["receipts"]
        assert state["revalidation_success_count"] == expected
        assert cycle["receipts"][0]["broker_write_count"] == 0
    assert len(calls) == 3


def test_failed_dependency_probe_needs_another_real_producer_completion(environment, monkeypatch):
    _settings, runtime = environment
    definition, circuit, _producer, now = _dependency_repair_inputs(runtime, monkeypatch)
    op._write_circuit_breakers(runtime, {definition.service_id: circuit})
    monkeypatch.setattr(op, "classify_failure", lambda _: "dependency_unavailable")
    op._record_failure(runtime, definition, {
        "receipt_id": "failed-dependency-probe", "completed_at": now.isoformat(),
        "circuit_revalidation": True, "command_results": [{"returncode": 1}],
    })
    current = op._circuit_breaker_state(runtime)[definition.service_id]
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "another-file-touch")
    assert current["state"] == "open"
    assert not op._circuit_revalidation_allowed(runtime, definition, current)[0]


@pytest.mark.parametrize("worker_pid,explicit_null,allowed", [(42, False, True), (None, False, False),
                                                          (42, True, False)])
def test_legacy_worker_receipt_needs_worker_provenance_when_probe_field_absent(
    environment, monkeypatch, worker_pid, explicit_null, allowed,
):
    _settings, runtime = environment
    definition, circuit, producer, _now = _dependency_repair_inputs(runtime, monkeypatch)
    producer.pop("integration_probe")
    producer["worker_pid"] = worker_pid
    if explicit_null:
        producer["integration_probe"] = None
    assert op._circuit_revalidation_allowed(runtime, definition, circuit)[0] is allowed


def test_new_worker_completion_explicitly_records_real_work_not_a_probe(environment, monkeypatch):
    settings, runtime = environment
    service_id = "active_discovery_trial"
    receipt_id = "real-worker-fixture"
    (runtime / op.WORKERS_ARTIFACT).write_text(json.dumps({"workers": {service_id: {
        "receipt_id": receipt_id, "pid": os.getpid(), "state": "running",
        "operator_build_identity": {"git_commit": "test-release", "service_contract_hash": "test-contract",
                                    "dirty_worktree": False},
    }}}))
    monkeypatch.setattr(op, "_execute_service_synchronously", lambda *a, **k: {
        "state": "completed", "duration_seconds": 0.01, "command_results": [],
        "generation_ids": {"dashboard_projection": "checked"}, "input_generation_ids": {},
        "input_generation_binding_complete": True, "mixed_generation_join_count": 0,
    })
    assert op.execute_registered_worker(service_id, receipt_id, settings) == 0
    completed = op._last_receipts(runtime)[service_id]
    assert completed["integration_probe"] is False
    assert completed["worker_pid"] == os.getpid()
