from __future__ import annotations

from collections import namedtuple
from datetime import datetime, timedelta, timezone
import gzip
import json
import os

import orchestrator.qadam_storage_retention as storage
from orchestrator.qadam_operator_ready_common import file_sha256


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_live_storage_health_uses_filesystem_not_cached_artifact(
    tmp_path, monkeypatch
) -> None:
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(
        storage.shutil,
        "disk_usage",
        lambda _path: usage(100 * 1024**3, 98 * 1024**3, 2 * 1024**3),
    )
    _write_json(
        tmp_path / "qadam_backfill_cost_and_rate_limit_state.json",
        {
            "historical_data_budget_remaining_usd": 100,
            "disk_free_bytes": 500 * 1024**3,
        },
    )

    health = storage.live_storage_health(tmp_path)
    budget_available, budget = storage.provider_budget_available(tmp_path)

    assert health["measurement_source"] == "shutil.disk_usage_live_filesystem"
    assert health["free_bytes"] == 2 * 1024**3
    assert health["write_services_allowed"] is False
    assert budget_available is True
    assert budget["cached_disk_value_ignored"] is True


def test_research_retention_keeps_referenced_score_and_label_generation(tmp_path) -> None:
    runtime = tmp_path / "data" / "runtime"
    score_root = tmp_path / "data" / "research" / "pattern_score_tape"
    label_root = tmp_path / "data" / "research" / "forward_labels"
    runtime.mkdir(parents=True)
    protected_score = score_root / "strategy=kept" / "scores.jsonl"
    orphan_score = score_root / "strategy=orphan" / "scores.jsonl"
    protected_score.parent.mkdir(parents=True)
    orphan_score.parent.mkdir(parents=True)
    protected_score.write_text('{"score_id":"kept"}\n', encoding="utf-8")
    orphan_score.write_text('{"score_id":"orphan"}\n', encoding="utf-8")
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
    os.utime(orphan_score, (old, old))
    partition = {
        "partition_id": "score-tape-partition:kept",
        "status": "complete",
        "dataset_path": str(protected_score.relative_to(tmp_path)),
        "dataset_sha256": file_sha256(protected_score),
        "record_set_hash": "records:kept",
        "row_count": 1,
    }
    _write_json(
        runtime / "qadam_pattern_score_tape_manifest.json",
        {"status": "complete_with_classified_gaps", "partitions": [partition]},
    )
    protected_label_name = f"score_tape={storage._score_plane_hash([partition])[:16]}"
    (label_root / protected_label_name).mkdir(parents=True)
    (label_root / "score_tape=obsolete").mkdir(parents=True)
    (label_root / "score_tape=obsolete" / "labels.jsonl").write_text(
        "{}\n", encoding="utf-8"
    )

    result = storage.prune_research_generations(runtime, apply=True)

    assert result["obsolete_score_file_count"] == 1
    assert result["obsolete_label_root_count"] == 1
    assert protected_score.is_file()
    assert not orphan_score.exists()
    assert (label_root / protected_label_name).is_dir()
    assert (label_root / "score_tape=obsolete").is_dir()
    assert result["deferred_label_root_count"] == 1
    assert result["label_cleanup_mode"] == "supervised_no_cloud_hydration"


def test_research_enumeration_does_not_enter_cloud_dataless_directory(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "pattern_score_tape"
    local = root / "local"
    cloud = root / "cloud"
    local.mkdir(parents=True)
    cloud.mkdir(parents=True)
    (local / "scores.jsonl").write_text("{}\n", encoding="utf-8")
    (cloud / "scores.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        storage,
        "_directory_is_dataless",
        lambda path: path == cloud,
    )

    matches = storage._research_files_without_cloud_hydration(root, "scores.jsonl")

    assert matches == [local / "scores.jsonl"]


def test_telemetry_rotation_archives_only_removed_prefix(
    tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    path = runtime / "operator_inbox_history.jsonl"
    records = [json.dumps({"index": index}) + "\n" for index in range(5)]
    path.write_text("".join(records), encoding="utf-8")
    monkeypatch.setitem(
        storage.TELEMETRY_LOG_POLICIES,
        "operator_inbox_history.jsonl",
        (1, 2),
    )

    result = storage.rotate_runtime_telemetry(runtime, apply=True)

    assert result["rotation_count"] == 1
    assert path.read_text(encoding="utf-8") == "".join(records[-2:])
    archive = tmp_path / result["rotations"][0]["archive"]
    with gzip.open(archive, "rt", encoding="utf-8") as handle:
        assert handle.read() == "".join(records[:-2])


def test_operator_telemetry_policies_cover_self_generated_growth_logs() -> None:
    assert storage.TELEMETRY_LOG_POLICIES["qadam_operator_service_receipts.jsonl"] == (
        64 * 1024**2,
        5000,
    )
    assert storage.TELEMETRY_LOG_POLICIES["qadam_operator_session_ledger.jsonl"] == (
        32 * 1024**2,
        1000,
    )
    assert storage.TELEMETRY_LOG_POLICIES["qadam_resource_lock_events.jsonl"] == (
        64 * 1024**2,
        5000,
    )
    assert storage.TELEMETRY_LOG_POLICIES["qadam_storage_maintenance_ledger.jsonl"] == (
        32 * 1024**2,
        1000,
    )


def test_storage_maintenance_failure_preserves_live_disk_authority_and_records_diagnostic(
    tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    monkeypatch.setattr(
        storage,
        "collect_artifact_generations",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("retention failed")),
    )

    result = storage.run_storage_maintenance(runtime, force=True, apply=True)

    assert result["status"] == "maintenance_failed"
    assert result["disk"]["write_services_allowed"] is True
    assert result["disk"]["reason"] == "storage_maintenance_failed"
    assert result["disk"]["maintenance_degraded"] is True
    assert result["maintenance_error"]["error_type"] == "OSError"
    persisted = json.loads(
        (runtime / storage.STATUS_ARTIFACT).read_text(encoding="utf-8")
    )
    assert persisted["status"] == "maintenance_failed"


def test_storage_maintenance_failure_still_blocks_writers_under_real_disk_pressure(
    tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    monkeypatch.setattr(
        storage,
        "collect_artifact_generations",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("retention failed")),
    )
    monkeypatch.setattr(
        storage,
        "live_storage_health",
        lambda *_args, **_kwargs: {
            "measurement_source": "shutil.disk_usage_live_filesystem",
            "free_bytes": 32 * 1024**3,
            "minimum_free_bytes": 64 * 1024**3,
            "used_ratio": 0.95,
            "maximum_used_ratio": 0.90,
            "stop_threshold_crossed": True,
            "recovery_threshold_met": False,
            "pressure_active": True,
            "write_services_allowed": False,
        },
    )

    result = storage.run_storage_maintenance(runtime, force=True, apply=True)

    assert result["status"] == "maintenance_failed"
    assert result["disk"]["pressure_active"] is True
    assert result["disk"]["write_services_allowed"] is False
    assert result["disk"]["maintenance_degraded"] is True
