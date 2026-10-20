from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from orchestrator.storage import recovery_backup as backup

NOW = datetime(2026, 10, 21, 14, tzinfo=timezone.utc)


def source(runtime, name=backup.DATABASES[0]):
    with sqlite3.connect(runtime / name) as db:
        db.execute("CREATE TABLE IF NOT EXISTS sentinel (value TEXT)")
        db.execute("INSERT INTO sentinel VALUES ('canonical record')")


def test_daily_backup_is_consistent_private_bounded_and_never_restores(tmp_path):
    source(tmp_path)
    source(tmp_path, backup.DATABASES[1])
    first = backup.maintain_recovery_backup(tmp_path, now=NOW)
    assert first["fresh"] and first["new_snapshot"]
    destination = tmp_path / backup.DIRECTORY / first["generation"] / backup.DATABASES[0]
    with sqlite3.connect(destination) as db:
        assert db.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert db.execute("SELECT value FROM sentinel").fetchone() == ("canonical record",)
    assert destination.stat().st_mode & 0o077 == 0
    assert not backup.maintain_recovery_backup(tmp_path, now=NOW + timedelta(hours=1))["new_snapshot"]
    for day in range(1, 5):
        result = backup.maintain_recovery_backup(tmp_path, now=NOW + timedelta(days=day))
        assert result["fresh"]
        assert not result["automatic_restore_allowed"]
        assert not result["off_host_disaster_recovery"]
    assert len(list((tmp_path / backup.DIRECTORY).iterdir())) == 3
    with sqlite3.connect(tmp_path / backup.DATABASES[0]) as db:
        assert db.execute("SELECT count(*) FROM sentinel").fetchone()[0] == 1


def test_interrupted_backup_preserves_previous_snapshot_and_uses_bounded_retry(tmp_path, monkeypatch):
    source(tmp_path)
    prior = backup.maintain_recovery_backup(tmp_path, now=NOW)
    def fail(*_):
        raise TimeoutError("interrupted")
    monkeypatch.setattr(backup, "_online_copy", fail)
    at = NOW + timedelta(days=1)
    result = backup.maintain_recovery_backup(tmp_path, now=at)
    assert result["status"] == "snapshot_failed"
    assert result["generation"] == prior["generation"]
    assert (tmp_path / backup.DIRECTORY / prior["generation"]).is_dir()
    assert not list((tmp_path / backup.DIRECTORY).glob(".partial-*"))
    assert backup.maintain_recovery_backup(tmp_path, now=at + timedelta(minutes=1))["status"] == "retry_scheduled"


def test_missing_snapshot_is_rebuilt_and_dry_run_does_not_write(tmp_path):
    source(tmp_path)
    assert backup.maintain_recovery_backup(tmp_path, now=NOW, apply=False)["status"] == "snapshot_due"
    assert not (tmp_path / backup.DIRECTORY).exists()
    first = backup.maintain_recovery_backup(tmp_path, now=NOW)
    (tmp_path / backup.DIRECTORY / first["generation"] / backup.DATABASES[0]).unlink()
    second = backup.maintain_recovery_backup(tmp_path, now=NOW + timedelta(seconds=1))
    assert second["new_snapshot"]


@pytest.mark.parametrize("failure", ["symlink", "oversized", "low_disk"])
def test_safety_boundaries_do_not_touch_source_or_escape_backup_root(tmp_path, monkeypatch, failure):
    from types import SimpleNamespace
    source(tmp_path)
    if failure == "symlink":
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (tmp_path / backup.DIRECTORY).symlink_to(elsewhere)
    elif failure == "oversized":
        monkeypatch.setattr(backup, "MAX_DATABASE_BYTES", 1)
    else:
        monkeypatch.setattr(backup.shutil, "disk_usage", lambda _: SimpleNamespace(free=1))
    result = backup.maintain_recovery_backup(tmp_path, now=NOW)
    assert result["status"] == "snapshot_failed"
    assert not result["fresh"]
    with sqlite3.connect(tmp_path / backup.DATABASES[0]) as db:
        assert db.execute("SELECT value FROM sentinel").fetchone() == ("canonical record",)


def test_corrupt_source_never_replaces_a_verified_snapshot(tmp_path):
    source(tmp_path)
    first = backup.maintain_recovery_backup(tmp_path, now=NOW)
    (tmp_path / backup.DATABASES[0]).write_bytes(b"not a SQLite database")
    result = backup.maintain_recovery_backup(tmp_path, now=NOW + timedelta(days=1))
    assert result["status"] == "snapshot_failed"
    assert result["generation"] == first["generation"]
    path = tmp_path / backup.DIRECTORY / first["generation"] / backup.DATABASES[0]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM sentinel").fetchone() == ("canonical record",)


def test_bad_auxiliary_metadata_is_rebuilt_without_corrupting_ledger(tmp_path):
    import json
    source(tmp_path)
    (tmp_path / backup.ARTIFACT).write_text(json.dumps({"databases": ["malformed"], "generation": "unknown"}))
    assert backup.maintain_recovery_backup(tmp_path, now=NOW)["fresh"]


def test_retained_valid_copy_can_repair_a_stale_auxiliary_status(tmp_path):
    import json
    source(tmp_path)
    result = backup.maintain_recovery_backup(tmp_path, now=NOW)
    result["status"] = "snapshot_failed"
    (tmp_path / backup.ARTIFACT).write_text(json.dumps(result))
    current = backup.maintain_recovery_backup(tmp_path, now=NOW + timedelta(minutes=1))
    assert current["status"] == "verified_local_snapshot"
    assert not current["new_snapshot"]
    assert json.loads((tmp_path / backup.ARTIFACT).read_text())["status"] == "verified_local_snapshot"
