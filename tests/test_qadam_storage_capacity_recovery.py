from datetime import datetime, timedelta, timezone
import gzip
import json

import pytest

from orchestrator.storage.control_plane import ControlPlaneStore, ControlPlaneError
from orchestrator.storage import telemetry_retention as retention
from orchestrator.runtime.recovery_policy import classify_failure


def populate(store, start=0, count=30):
    for i in range(start, start + count):
        store.record_service_run(run_id=f"run:{i}", service_id="source" if i else "rare",
                                 domain="research", status="completed", payload={"run": i, "text": "x" * 8000},
                                 started_at=f"2026-09-01T00:{i % 60:02}:00+00:00", completed_at=None)


def test_retention_restores_capacity_at_full_cap_and_preserves_authority(tmp_path):
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    populate(store)
    protected = {table: store.read_table(table) for table in (
        "execution_state", "positions", "canonical_orders", "decision_transactions", "handoffs")}
    with store.connect() as c:
        store.max_bytes = retention.capacity(c, store.max_bytes)["live_bytes"]
    with pytest.raises(ControlPlaneError, match="disk_ceiling"):
        populate(store, 30, 1)
    result = retention.maintain_service_runs(store, retain=5, trigger=10, batch_rows=7)
    assert result["archived_run_count"] == 24
    assert result["hot_service_run_count"] == 6  # includes latest run of quiet service
    assert result["reusable_bytes"] > 0
    assert result["write_capacity_available"]
    assert {table: store.read_table(table) for table in protected} == protected
    populate(store, 30, 1)
    archived = []
    for path in (tmp_path / "archive" / "control-plane-service-runs").glob("*.jsonl.gz"):
        with gzip.open(path, "rt") as stream:
            archived.extend(json.loads(line) for line in stream)
    assert {row["run_id"] for row in archived} == {f"run:{i}" for i in range(1, 25)}
    assert retention.maintain_service_runs(store, retain=5, trigger=10)["archived_run_count"] == 0


def test_repeated_growth_is_bounded_without_raising_cap(tmp_path):
    store = ControlPlaneStore(tmp_path / "control.sqlite3", max_bytes=1024 * 1024)
    for cycle in range(12):
        populate(store, cycle * 30, 30)
        result = retention.maintain_service_runs(store, retain=5, trigger=10)
        assert result["hot_service_run_count"] <= 6
        assert result["live_bytes"] < 700_000


def test_archive_failure_rolls_back_without_losing_rows(tmp_path, monkeypatch):
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    populate(store)
    before = store.read_table("service_runs")
    monkeypatch.setattr(retention, "_verify", lambda *_: (_ for _ in ()).throw(RuntimeError("corrupt archive")))
    with pytest.raises(RuntimeError, match="corrupt archive"):
        retention.maintain_service_runs(store, retain=5, trigger=10)
    assert store.read_table("service_runs") == before


def test_existing_archive_is_verified_before_any_delete(tmp_path):
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    populate(store)
    with store.connect() as c:
        rows = c.execute("SELECT * FROM service_runs WHERE rowid>1 ORDER BY rowid LIMIT 7").fetchall()
    path = retention.archive_batch(tmp_path / "archive" / "control-plane-service-runs", rows)
    path.write_bytes(b"damaged")
    with pytest.raises((OSError, RuntimeError)):
        retention.maintain_service_runs(store, retain=5, trigger=10, batch_rows=7)
    assert len(store.read_table("service_runs")) == 30


def test_dry_run_and_bounded_batches(tmp_path):
    store = ControlPlaneStore(tmp_path / "control.sqlite3")
    populate(store)
    assert retention.maintain_service_runs(store, apply=False, retain=5, trigger=10)["archived_run_count"] == 0
    result = retention.maintain_service_runs(store, retain=5, trigger=10, batch_rows=3, max_batches=1)
    assert result["archived_run_count"] == 3
    assert len(store.read_table("service_runs")) == 27


@pytest.mark.parametrize("diagnostic,expected", [
    ("paperops_lifecycle_poller_schema_version=1\nqadam_failure_class=transient_provider_network\nerror=paper_lifecycle_live_poll_incomplete", "transient_provider_network"),
    ("schema_version=1\nqadam_failure_class=code_defect", "code_defect"),
    ("schema_version=1\ncontrol_plane_disk_ceiling_exceeded", "storage_maintenance_due"),
    ("error=decision_dependency_circuit_open", "dependency_unavailable"),
    ("error=conversion_stage_failed:shadow", "dependency_unavailable"),
    ("schema_version=1\nConnectError", "transient_provider_network"),
    ("qadam_failure_class=transient_provider_network\nsafety violation", "safety_violation"),
    ("qadam_failure_class=transient_provider_network\nqadam_failure_class=credential_operator_action", "credential_operator_action"),
    ("qadam_failure_class=unknown", "code_defect"),
    ("error=schema_mismatch", "parser_schema_drift"),
])
def test_real_diagnostic_context_cannot_override_typed_failures(diagnostic, expected):
    assert classify_failure(diagnostic) == expected


def test_scheduler_routes_actual_lifecycle_stdout_to_retry(tmp_path, monkeypatch):
    from orchestrator.runtime import operator as op
    monkeypatch.setattr(op, "_service_revalidation_fingerprint", lambda *_: "input")
    monkeypatch.setattr(op, "_service_revalidation_identity", lambda *_: "build")
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "paper_lifecycle_poll")
    failure, retry = op._record_failure(tmp_path, definition, {
        "receipt_id": "poll", "completed_at": datetime.now(timezone.utc).isoformat(),
        "command_results": [{"returncode": 1, "stdout_tail":
                             "paperops_lifecycle_poller_schema_version=1\nqadam_failure_class=transient_provider_network\n"}],
    })
    assert failure == "transient_provider_network"
    assert retry["policy"]["automatic_retry_allowed"]


def test_storage_freeze_requires_two_fresh_consistent_reconciliations(tmp_path, monkeypatch):
    from orchestrator.execution.ledger import OperatingLedger
    ledger = OperatingLedger(store=ControlPlaneStore(tmp_path / "control.sqlite3"))
    monkeypatch.setattr(ledger, "assert_execution_owner", lambda: None)
    now = datetime.now(timezone.utc)
    incident = (now - timedelta(seconds=20)).isoformat()
    with ledger.store.transaction() as c:
        c.execute("UPDATE execution_state SET frozen=1, reason=?, updated_at=?",
                  ("pre_paperops_submission_reconciliation_storage_unavailable", incident))
    for i in range(2):
        stamp = (now - timedelta(seconds=10 - i)).isoformat()
        payload = json.dumps({"observed": {"mirror_observed_at": stamp, "position_protection_digest": "stable"}})
        with ledger.store.transaction() as c:
            c.execute("INSERT INTO reconciliation_runs(reconciliation_id,execution_owner_id,phase,status,expected_digest,observed_digest,blocker_count,payload_json,payload_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (f"rec:{i}", "test-owner", "pre", "passed", "same", "same", 0, payload, "fixture", stamp))
        ledger.clear_reconciliation_freeze(reconciliation_id=f"rec:{i}")
        assert bool(ledger.execution_state()["frozen"]) == (i == 0)
    assert not ledger._recoverable_freeze("pre_paperops_submission_reconciliation_failed:ControlPlaneError")
    assert not ledger._recoverable_freeze("operator_manual_stop")


def test_storage_monitor_includes_database_not_only_free_disk(tmp_path):
    from orchestrator.qadam_storage_retention import run_storage_maintenance
    store = ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3")
    populate(store, count=3)
    result = run_storage_maintenance(tmp_path, force=True)
    assert result["control_plane"]["write_capacity_available"]
    assert result["control_plane"]["hot_service_run_count"] == 3


def test_review_requires_exact_storage_receipt_and_keeps_execution_frozen(tmp_path, monkeypatch):
    from orchestrator.execution.ledger import OperatingLedger
    ledger = OperatingLedger(store=ControlPlaneStore(tmp_path / "control.sqlite3"))
    monkeypatch.setattr(ledger, "assert_execution_owner", lambda: None)
    with ledger.store.transaction() as c:
        c.execute("UPDATE execution_state SET frozen=1,reason=?,updated_at=?", (
            "pre_paperops_submission_reconciliation_failed:ControlPlaneError", "2026-09-11T11:36:33+00:00"))
    receipt = {"service_id": "guarded_paperops", "state": "failed", "receipt_id": "receipt:old",
               "started_at": "2026-09-11T11:35:25+00:00", "completed_at": "2026-09-11T11:37:00+00:00",
               "command_results": [{"returncode": 1, "command": ["scripts/run_paperops_autonomous_pass.py"],
                                    "stderr_tail": "ControlPlaneError: integrity_error"}]}
    assert not ledger.review_legacy_storage_freeze(receipt)
    receipt["command_results"][0]["stderr_tail"] = "ControlPlaneError: control_plane_disk_ceiling_exceeded"
    assert not ledger.review_legacy_storage_freeze({**receipt, "completed_at": "2026-09-10T11:37:00+00:00"})
    assert ledger.review_legacy_storage_freeze(receipt)
    assert ledger.execution_state()["frozen"] == 1
    assert ledger.execution_state()["reason"] == "pre_paperops_submission_reconciliation_storage_unavailable"
    assert not ledger.review_legacy_storage_freeze(receipt)


def test_old_failure_class_is_reinterpreted_not_cleared(tmp_path, monkeypatch):
    from orchestrator.runtime import operator as op
    monkeypatch.setattr(op, "operator_service_revalidation_identity", lambda *_: "new-build")
    circuits = {"paper_lifecycle_poll": {"state": "open", "failure_class": "parser_schema_drift",
                "failure_revalidation_identity": "old-build", "last_failure_at": "incident"}}
    (tmp_path / op.CIRCUIT_BREAKERS_ARTIFACT).write_text(json.dumps({"services": circuits}))
    receipt = {"service_id": "paper_lifecycle_poll", "state": "failed", "completed_at": "incident",
               "command_results": [{"returncode": 1, "stdout_tail": "schema_version=1\nqadam_failure_class=transient_provider_network\n"}]}
    (tmp_path / op.RECEIPTS_ARTIFACT).write_text(json.dumps(receipt) + "\n")
    assert len(op.reclassify_recorded_failures(tmp_path)) == 1
    circuit = op._circuit_breaker_state(tmp_path)["paper_lifecycle_poll"]
    assert circuit["state"] == "open"
    assert circuit["failure_class"] == "transient_provider_network"
    assert op.reclassify_recorded_failures(tmp_path) == []


@pytest.mark.parametrize("reason", ["safety_violation", "credential_operator_action", "research_integrity_hold"])
def test_reclassification_cannot_touch_protected_failures(tmp_path, monkeypatch, reason):
    from orchestrator.runtime import operator as op
    monkeypatch.setattr(op, "operator_service_revalidation_identity", lambda *_: "new-build")
    circuits = {"paper_lifecycle_poll": {"state": "open", "failure_class": reason,
                "failure_revalidation_identity": "old-build", "last_failure_at": "incident"}}
    (tmp_path / op.CIRCUIT_BREAKERS_ARTIFACT).write_text(json.dumps({"services": circuits}))
    assert op.reclassify_recorded_failures(tmp_path) == []
    assert op._circuit_breaker_state(tmp_path) == circuits
