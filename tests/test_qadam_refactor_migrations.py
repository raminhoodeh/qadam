from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from orchestrator.storage import control_plane


def test_two_initializers_serialize_without_duplicate_migration_receipts(tmp_path):
    path = tmp_path / "control.sqlite3"
    with ThreadPoolExecutor(max_workers=2) as pool:
        stores = list(pool.map(lambda _: control_plane.ControlPlaneStore(path), range(2)))
    with stores[0].connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 5
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migration_failure_rolls_back_ddl_and_receipt(tmp_path, monkeypatch):
    store = control_plane.ControlPlaneStore(tmp_path / "control.sqlite3")
    monkeypatch.setattr(control_plane, "MIGRATIONS", (*control_plane.MIGRATIONS,
        (6, "CREATE TABLE never_committed (x TEXT); INSERT INTO missing_table VALUES (1);")))
    with pytest.raises(sqlite3.OperationalError):
        store.migrate()
    with store.connect() as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='never_committed'").fetchall() == []
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 5


def test_additive_upgrade_preserves_events_and_verified_backup(tmp_path, monkeypatch):
    migrations = control_plane.MIGRATIONS
    monkeypatch.setattr(control_plane, "MIGRATIONS", migrations[:4])
    store = control_plane.ControlPlaneStore(tmp_path / "control.sqlite3")
    with store.transaction() as connection:
        connection.execute("INSERT INTO operating_events VALUES ('id','fixture','fixture','recorded','{}','digest','2026-09-01T00:00:00+00:00')")
    backup = store.backup(tmp_path / "backup.sqlite3")
    monkeypatch.setattr(control_plane, "MIGRATIONS", migrations)
    store.migrate()
    store.migrate()
    with store.connect() as connection, sqlite3.connect(backup) as saved:
        assert connection.execute("SELECT * FROM operating_events").fetchone()[0] == saved.execute("SELECT * FROM operating_events").fetchone()[0]
        assert saved.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 4
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 5
        assert saved.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    # An older schema expectation explicitly refuses certification. Never restore
    # an old production portfolio as a way to roll back application code.
    monkeypatch.setattr(control_plane, "SCHEMA_VERSION", 4)
    assert store.integrity_report()["status"] != "passed"
