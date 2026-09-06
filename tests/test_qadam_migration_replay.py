import sqlite3

import pytest

from scripts.verify_qadam_refactor_migration import verify_migration
from orchestrator.storage import control_plane


def test_replay_migrates_only_copy_and_preserves_canonical_payloads(tmp_path, monkeypatch):
    migrations = control_plane.MIGRATIONS
    monkeypatch.setattr(control_plane, "MIGRATIONS", migrations[:4])
    source = control_plane.ControlPlaneStore(tmp_path / "original.sqlite3")
    with source.transaction() as connection:
        connection.execute("INSERT INTO operating_events VALUES ('id','fixture','fixture','recorded','{}','digest','2026-09-01T00:00:00+00:00')")
    monkeypatch.setattr(control_plane, "MIGRATIONS", migrations)
    report = verify_migration(source.path, tmp_path / "isolated")
    assert report["passed"] is True
    assert (report["before_schema_version"], report["after_schema_version"]) == (4, 5)
    assert report["tables"]["operating_events"]["row_count"] == 1
    assert report["production_writes"] == report["outbox_consumers_started"] == 0
    with sqlite3.connect(source.path) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 4


def test_replay_refuses_existing_destination(tmp_path):
    source = control_plane.ControlPlaneStore(tmp_path / "original.sqlite3")
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        verify_migration(source.path, destination)
    assert list(destination.iterdir()) == []
