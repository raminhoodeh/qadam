"""Migrate an isolated SQLite backup; never open the source database for writing."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator.storage.control_plane import ControlPlaneStore  # noqa: E402


def _identifier(value):
    return '"' + value.replace('"', '""') + '"'


def _fingerprints(connection):
    results = {}
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name!='schema_migrations' ORDER BY name"
    ).fetchall()
    for (table,) in tables:
        columns = connection.execute(f"PRAGMA table_info({_identifier(table)})").fetchall()
        keys = [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]]
        order = ",".join(_identifier(key) for key in keys) or "rowid"
        digest = sha256(json.dumps([row[1] for row in columns]).encode())
        count = 0
        for row in connection.execute(f"SELECT * FROM {_identifier(table)} ORDER BY {order}"):
            encoded = json.dumps(list(row), separators=(",", ":"),
                                 default=lambda value: {"blob_hex": value.hex()}).encode()
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            count += 1
        results[table] = {"row_count": count, "sha256": digest.hexdigest()}
    return results


def verify_migration(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(strict=True), destination.resolve()
    # A fresh, explicitly named private directory prevents overwriting any state.
    destination.mkdir(mode=0o700)
    target = destination / "isolated-control-plane.sqlite3"
    started = time.monotonic()

    def progress(*_args):
        if time.monotonic() - started > 60:
            raise TimeoutError("read_only_backup_deadline_exceeded")

    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
        original.execute("PRAGMA query_only=ON")
        if original.execute("PRAGMA page_count").fetchone()[0] * original.execute("PRAGMA page_size").fetchone()[0] > 512 * 1024 * 1024:
            raise ValueError("backup_exceeds_reviewed_512MiB_budget")
        with closing(sqlite3.connect(target)) as snapshot:
            original.backup(snapshot, pages=256, progress=progress, sleep=.02)
    target.chmod(0o600)
    with closing(sqlite3.connect(target)) as connection:
        before = _fingerprints(connection)
        migrations = connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
        integrity_before = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys_before = connection.execute("PRAGMA foreign_key_check").fetchall()
    store = ControlPlaneStore(target)
    store.migrate()
    with closing(sqlite3.connect(target)) as connection:
        after = _fingerprints(connection)
        migrated = connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
        integrity_after = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys_after = connection.execute("PRAGMA foreign_key_check").fetchall()
    unchanged = before == after
    prior_receipts_unchanged = migrated[:len(migrations)] == migrations
    return {
        "kind": "isolated_actual_ledger_migration_replay",
        "passed": unchanged and prior_receipts_unchanged and integrity_before == integrity_after == "ok"
                  and not foreign_keys_before and not foreign_keys_after,
        "source_open_mode": "read_only", "production_writes": 0,
        "broker_calls": 0, "notification_calls": 0, "outbox_consumers_started": 0,
        "before_schema_version": max(row[0] for row in migrations),
        "after_schema_version": max(row[0] for row in migrated),
        "table_rows_and_payloads_unchanged": unchanged,
        "prior_migration_receipts_unchanged": prior_receipts_unchanged,
        "integrity_before": integrity_before, "integrity_after": integrity_after,
        "foreign_key_error_count_before": len(foreign_keys_before),
        "foreign_key_error_count_after": len(foreign_keys_after),
        "tables": after, "snapshot_bytes": target.stat().st_size,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    report = verify_migration(args.source, args.destination)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
