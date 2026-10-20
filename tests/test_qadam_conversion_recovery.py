from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore, GenerationError
from orchestrator.runtime import operator
from orchestrator.runtime.generation_publication import MAX_CAPTURE_ATTEMPTS, publish_owned_outputs
from orchestrator.runtime.services import (
    SERVICE_DEFINITIONS, automatic_recovery_permitted, worker_execution_permitted,
)
from tests.test_qadam_operator_service_v2 import _settings, _success_executor, _write_json


def _conversion():
    return next(row for row in SERVICE_DEFINITIONS if row.service_id == "open_market_conversion")


def _failed_receipt(index=0, *, revalidation=False):
    return {"receipt_id": f"failure:{index}", "service_id": "open_market_conversion",
            "completed_at": datetime.now(timezone.utc).isoformat(), "circuit_revalidation": revalidation,
            "revalidation_fingerprint": "repair-build", "command_results": [
                {"returncode": 74, "stderr_tail":
                 "GenerationError: generation_source_changed_during_copy:qadam_improvement_pipeline_dashboard.json"}]}


def test_conversion_never_reads_foreign_mutable_artifacts(monkeypatch, tmp_path):
    import orchestrator.qadam_artifact_generations as generations
    _settings(tmp_path)
    foreign = tmp_path / "qadam_improvement_pipeline_dashboard.json"
    _write_json(foreign, {"version": "verified"})
    store = ArtifactGenerationStore(tmp_path, "learning_plane")
    old = store.publish_files({foreign.name: foreign}, producer="learning_attribution")
    _write_json(foreign, {"version": "concurrent_unpublished"})
    original_copy = generations.shutil.copyfile

    def copying(source, target):
        assert source != foreign, "conversion must not read another producer's live file"
        return original_copy(source, target)

    monkeypatch.setattr(generations.shutil, "copyfile", copying)
    result = operator._publish_service_generations(tmp_path, _conversion(), [{"command": ["fixture"]}])
    current = store.resolve_current()
    assert "learning_plane" in result
    assert json.loads((current.path / foreign.name).read_text()) == {"version": "verified"}
    assert current.manifest["provenance"]["carried_forward_generation_id"] == old.generation_id
    assert foreign.name not in current.manifest["provenance"]["changed_artifacts"]
    store.validate_reference(old)


def test_distinct_owners_merge_only_their_declared_outputs(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write_json(a, {"a": 1})
    _write_json(b, {"b": 1})
    store = ArtifactGenerationStore(tmp_path, "learning_plane")
    first = publish_owned_outputs(store, {a.name: a}, producer="a", provenance={})
    assert {row["name"] for row in first.manifest["files"]} == {a.name}
    publish_owned_outputs(store, {b.name: b}, producer="b", provenance={})
    _write_json(a, {"a": 2})
    _write_json(b, {"b": "unpublished"})
    current = publish_owned_outputs(store, {a.name: a}, producer="a", provenance={})
    assert json.loads((current.path / a.name).read_text()) == {"a": 2}
    assert json.loads((current.path / b.name).read_text()) == {"b": 1}


@pytest.mark.parametrize("continuous_churn", [False, True])
def test_capture_race_retries_bytes_only_and_preserves_last_good_pointer(monkeypatch, tmp_path, continuous_churn):
    import orchestrator.qadam_artifact_generations as generations
    source = tmp_path / "owned.json"
    _write_json(source, {"version": 0})
    store = ArtifactGenerationStore(tmp_path, "learning_plane")
    old = store.publish_files({source.name: source}, producer="owner")
    _write_json(source, {"version": 1})
    attempts = []
    original_copy = generations.shutil.copyfile

    def racing_copy(origin, target):
        if origin == source:
            attempts.append(origin)
            if continuous_churn or len(attempts) == 1:
                _write_json(source, {"race": len(attempts)})
        return original_copy(origin, target)

    monkeypatch.setattr(generations.shutil, "copyfile", racing_copy)
    if continuous_churn:
        with pytest.raises(GenerationError, match="generation_source_changed_during_copy"):
            publish_owned_outputs(store, {source.name: source}, producer="owner", provenance={})
        assert len(attempts) == MAX_CAPTURE_ATTEMPTS
        assert store.resolve_current().generation_id == old.generation_id
    else:
        current = publish_owned_outputs(store, {source.name: source}, producer="owner", provenance={})
        assert len(attempts) == 2
        assert json.loads((current.path / source.name).read_text()) == {"race": 1}
    assert not list(store.staging.iterdir())
    store.validate_reference(old)


def test_invalid_previous_generation_is_not_silently_bootstrapped(tmp_path):
    source = tmp_path / "owned.json"
    _write_json(source, {"version": 0})
    store = ArtifactGenerationStore(tmp_path, "learning_plane")
    old = store.publish_files({source.name: source}, producer="owner")
    _write_json(old.path / source.name, {"tampered": True})
    with pytest.raises(GenerationError, match="generation_file_checksum_mismatch"):
        publish_owned_outputs(store, {source.name: source}, producer="owner", provenance={})


def test_dashboard_refresh_cannot_rewrite_learning_owned_artifacts(monkeypatch, tmp_path):
    from orchestrator import qadam_operator_dashboard as dashboard
    settings = _settings(tmp_path)
    state = dashboard.build_operator_dashboard_state(settings)
    protected = ("qadam_learning_cycle_dashboard.json", "qadam_learning_cycle_events.jsonl",
                 "qadam_improvement_pipeline_dashboard.json", "qadam_improvement_proposals_v3.jsonl")
    before = {}
    for name in protected:
        _write_json(tmp_path / name, {"canonical_owner": "learning_attribution", "version": "frozen"})
        before[name] = (tmp_path / name).read_bytes()
    monkeypatch.setattr(dashboard, "build_operator_dashboard_state", lambda settings: state)
    published, _, _ = dashboard.build_and_write_operator_dashboard(settings)
    assert published["learning_cycle"] and published["improvement_pipeline"]
    for name in protected:
        assert (tmp_path / name).read_bytes() == before[name]


@pytest.mark.parametrize("command", [
    ("scripts/run_qadam_open_market_conversion.py", "--allow-network"),
    ("unsafe.py", "--no-paperops"),
    ("scripts/run_qadam_open_market_conversion.py", "--allow-network", "--no-paperops", "--extra"),
    ("scripts/run_paperops_autonomous_pass.py", "--no-paperops"),
])
def test_automatic_recovery_rejects_any_expanded_conversion_command(command):
    definition = replace(_conversion(), command_sequence=(command,))
    assert not automatic_recovery_permitted(definition)
    assert not worker_execution_permitted(definition)
    assert not automatic_recovery_permitted(replace(definition, paperops_dependency=False))
    assert operator.service_recovery_contract_errors(definition)


def test_broker_writer_does_not_gain_automatic_retry_authority(tmp_path):
    guarded = next(row for row in SERVICE_DEFINITIONS if row.service_id == "guarded_paperops")
    assert not automatic_recovery_permitted(guarded)
    _, retry = operator._record_failure(tmp_path, guarded, _failed_receipt())
    assert retry["policy"]["automatic_retry_allowed"] is False
    circuit = operator._circuit_breaker_state(tmp_path)["guarded_paperops"]
    assert operator._circuit_revalidation_allowed(tmp_path, guarded, circuit)[0] is False


def test_transient_conversion_failure_gets_backoff_without_a_manual_reset(tmp_path):
    _, retry = operator._record_failure(tmp_path, _conversion(), _failed_receipt())
    circuit = operator._circuit_breaker_state(tmp_path)["open_market_conversion"]
    assert retry["retry_scheduled"] is True
    assert retry["policy"]["automatic_retry_allowed"] is True
    assert circuit["state"] == "closed_retry_scheduled"
    assert circuit["backoff_seconds"] == 5
    assert circuit["next_retry_at"]


def test_existing_conversion_circuit_recovers_through_three_scheduled_passes(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _write_json(tmp_path / "qadam_long_backtest_lock.json", {"status": "inactive"})
    _write_json(tmp_path / "qadam_research_lock_release_readiness.json", {"release_effective": True})
    monkeypatch.setattr(operator, "_scheduled_market_is_open", lambda *args: True)
    for dependency in _conversion().dependencies:
        operator._append_receipt(tmp_path, {"receipt_id": dependency, "service_id": dependency,
                                           "state": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
    fingerprint = operator._service_revalidation_fingerprint(tmp_path, _conversion())
    _write_json(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {"open_market_conversion": {
        "state": "open", "failure_class": "concurrent_artifact_access", "failure_fingerprint": fingerprint,
        "last_failed_revalidation_fingerprint": fingerprint, "automatic_revalidation_attempt_count": 0,
        "next_retry_at": "2000-01-01T00:00:00+00:00"}}})
    states, commands = [], []

    def execute(command, timeout):
        commands.append(command)
        return _success_executor(command, timeout)

    for _ in range(3):
        cycle = operator.dispatch_due_jobs(settings, service_ids=("open_market_conversion",), executor=execute)
        states.append(cycle["receipts"][0]["state"])
    assert states == ["completed_pending_circuit_confirmation", "completed_pending_circuit_confirmation", "completed"]
    assert commands == list(_conversion().command_sequence) * 3
    assert operator._circuit_breaker_state(tmp_path)["open_market_conversion"]["state"] == "closed"
    assert not (tmp_path / "qadam_operator_full_heal_request.json").exists()


@pytest.mark.parametrize("failure", ["credential_operator_action", "safety_violation", "research_integrity_hold", "code_defect"])
def test_protected_conversion_failures_do_not_qualify_for_automatic_revalidation(tmp_path, failure):
    circuit = {"state": "half_open", "failure_class": failure, "automatic_revalidation_attempt_count": 0,
               "next_retry_at": "2000-01-01T00:00:00+00:00"}
    assert operator._circuit_revalidation_allowed(tmp_path, _conversion(), circuit)[0] is False


def test_worker_revalidation_metadata_enforces_bounded_failures(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    for index in range(5):
        operator._record_failure(tmp_path, _conversion(), _failed_receipt(index))
    initial = operator._circuit_breaker_state(tmp_path)["open_market_conversion"]
    assert initial["state"] == "open"
    failure = {"state": "failed", "duration_seconds": 0.01,
               "command_results": _failed_receipt()["command_results"], "generation_ids": {},
               "input_generation_ids": {}, "input_generation_binding_complete": True, "mixed_generation_join_count": 0}
    monkeypatch.setattr(operator, "_execute_service_synchronously", lambda *args, **kwargs: failure)
    for index in range(3):
        run_id = f"worker-repair:{index}"
        operator._set_worker_record(tmp_path, "open_market_conversion", {
            "service_id": "open_market_conversion", "receipt_id": run_id, "state": "running",
            "circuit_revalidation": True, "revalidation_fingerprint": "repair-build"})
        assert operator.execute_registered_worker("open_market_conversion", run_id, settings) == 1
    circuit = operator._circuit_breaker_state(tmp_path)["open_market_conversion"]
    assert circuit["automatic_revalidation_attempt_count"] == 3
    assert circuit["automatic_cooldown_probe_scheduled"] is True
    assert datetime.fromisoformat(circuit["next_retry_at"]) > datetime.now(timezone.utc) + timedelta(hours=2)
    assert operator._circuit_revalidation_allowed(tmp_path, _conversion(), circuit)[0] is False


def test_worker_success_retains_exact_repair_identity(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    _write_json(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {"open_market_conversion": {
        "state": "half_open", "failure_class": "concurrent_artifact_access", "revalidation_success_count": 2,
        "revalidation_fingerprint": "repair-build"}}})
    operator._set_worker_record(tmp_path, "open_market_conversion", {
        "service_id": "open_market_conversion", "receipt_id": "worker-ok", "state": "running",
        "circuit_revalidation": True, "revalidation_fingerprint": "repair-build"})
    result = {"state": "completed", "duration_seconds": 0.01, "command_results": [], "generation_ids": {},
              "input_generation_ids": {}, "input_generation_binding_complete": True, "mixed_generation_join_count": 0}
    monkeypatch.setattr(operator, "_execute_service_synchronously", lambda *args, **kwargs: result)
    assert operator.execute_registered_worker("open_market_conversion", "worker-ok", settings) == 0
    circuit = operator._circuit_breaker_state(tmp_path)["open_market_conversion"]
    assert circuit["state"] == "closed"
    assert circuit["revalidation_fingerprint"] == "repair-build"


def test_exhausted_safe_conversion_retries_allow_a_bounded_cooldown_probe(tmp_path):
    circuit = {"state": "open", "failure_class": "concurrent_artifact_access",
               "last_failure_at": (datetime.now(timezone.utc)-timedelta(hours=4)).isoformat(),
               "automatic_revalidation_attempt_count": operator.MAX_AUTOMATIC_STABILITY_REVALIDATIONS,
               "next_retry_at": "2000-01-01T00:00:00+00:00"}
    assert operator._circuit_revalidation_allowed(tmp_path, _conversion(), circuit)[0] is True
    assert operator._circuit_revalidation_allowed(tmp_path, _conversion(),
                                                 {**circuit, "failure_class": "safety_violation"})[0] is False


def test_worker_launch_persists_revalidation_metadata_before_process_start(monkeypatch, tmp_path):
    import os
    from types import SimpleNamespace
    seen = []

    def start(*args, **kwargs):
        seen.append(json.loads((tmp_path / "qadam_operator_workers.json").read_text())["workers"]["open_market_conversion"])
        return SimpleNamespace(pid=os.getpid())

    monkeypatch.setattr(operator.subprocess, "Popen", start)
    operator._launch_resumable_worker(tmp_path, _conversion(), receipt_id="launch-fixture",
                                     circuit_revalidation=True, revalidation_fingerprint="repair-build")
    assert seen[0]["circuit_revalidation"] is True
    assert seen[0]["revalidation_fingerprint"] == "repair-build"


def test_overdue_conversion_recovery_cannot_outrank_broker_position_care():
    from orchestrator.runtime.scheduling import order_by_deadline_slack
    now = datetime.now(timezone.utc)
    care = next(row for row in SERVICE_DEFINITIONS if row.service_id == "guarded_paperops")
    conversion = _conversion()
    successful = {
        conversion.service_id: {"completed_at": (now-timedelta(hours=2)).isoformat()},
        care.service_id: {"completed_at": (now-timedelta(seconds=45)).isoformat()},
    }
    ordered = order_by_deadline_slack((conversion, care), successful, timestamp=now,
                                     recovery_targets=(conversion.service_id,))
    assert [row.service_id for row in ordered] == [care.service_id, conversion.service_id]
