"""Bounded online SQLite recovery snapshots owned by existing storage maintenance.

Backups are not automatic restore authority. Restored trading state must first
be reconciled with the broker; a local backup is not off-host disaster recovery.
"""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time

from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic

ARTIFACT = "qadam_recovery_backup_status.json"
DIRECTORY = ".qadam_recovery_backups"
DATABASES = ("qadam-control-plane.sqlite3", "qadam-trade-delivery.sqlite3")
INTERVAL_SECONDS = 24 * 60 * 60
RETRY_SECONDS = 30 * 60
MAX_DATABASE_BYTES = 512 * 1024**2
MAX_BACKUP_SECONDS = 30
RETAIN_GENERATIONS = 3
TOTAL_BUDGET_BYTES = (RETAIN_GENERATIONS + 1) * len(DATABASES) * MAX_DATABASE_BYTES


def _prune_generations(root, *, preserve=None):
    complete = sorted((entry for entry in root.iterdir() if entry.is_dir() and not entry.is_symlink()
        and re.fullmatch(r"\d{8}T\d{12}Z", entry.name)), key=lambda entry: entry.name, reverse=True)
    keep = {entry.name for entry in complete[:RETAIN_GENERATIONS]}
    if preserve and preserve not in keep and any(entry.name == preserve for entry in complete):
        keep = {entry.name for entry in complete[:RETAIN_GENERATIONS - 1]} | {preserve}
    for entry in complete:
        if entry.name not in keep:
            shutil.rmtree(entry)


def _stamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except ValueError:
        return None


def _online_copy(source, target, deadline):
    reader = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    writer = sqlite3.connect(target, timeout=1)
    try:
        page_size = reader.execute("PRAGMA page_size").fetchone()[0]
        def progress(_status, remaining, total):
            if time.monotonic() > deadline or total * page_size > MAX_DATABASE_BYTES:
                raise TimeoutError("recovery_snapshot_budget_exhausted")
        reader.backup(writer, pages=256, progress=progress, sleep=.01)
        if target.stat().st_size > MAX_DATABASE_BYTES:
            raise ValueError("recovery_snapshot_size_budget_exhausted")
        writer.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        if writer.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("recovery_snapshot_integrity_failed")
    finally:
        writer.close()
        reader.close()
    os.chmod(target, 0o600)
    with target.open("rb") as handle:
        os.fsync(handle.fileno())


def maintain_recovery_backup(runtime: Path, *, now=None, apply=True):
    now = now or datetime.now(timezone.utc)
    path = runtime / ARTIFACT
    previous = read_json(path)
    root = runtime / DIRECTORY
    last = _stamp(previous.get("last_verified_at"))
    generation = previous.get("generation")
    valid_name = isinstance(generation, str) and re.fullmatch(r"\d{8}T\d{12}Z", generation)
    receipts = previous.get("databases") or []
    if not isinstance(receipts, list) or any(not isinstance(row, dict) for row in receipts):
        receipts = []
    required = {name for name in DATABASES if (runtime / name).is_file()}
    present = bool(valid_name and not root.is_symlink() and not (root / generation).is_symlink()
        and DATABASES[0] in required and {row.get("name") for row in receipts} == required
        and receipts and all(row.get("name") in DATABASES and type(row.get("bytes")) is int
            and (root / generation / row["name"]).is_file()
            and not (root / generation / row["name"]).is_symlink()
            and (root / generation / row["name"]).stat().st_size == row["bytes"] for row in receipts))
    if last and 0 <= (now - last).total_seconds() < INTERVAL_SECONDS and present:
        current = {**previous, "status": "verified_local_snapshot", "fresh": True, "new_snapshot": False}
        if apply and previous.get("status") != current["status"]:
            write_json_atomic(path, current)
        return current
    next_retry = _stamp(previous.get("next_retry_at"))
    if next_retry and now < next_retry:
        return {**previous, "status": "retry_scheduled", "fresh": False, "new_snapshot": False}
    if not apply:
        return {"status": "snapshot_due", "fresh": False, "new_snapshot": False}
    candidate = None
    result = {"schema_version": "qadam-local-recovery-backup.1", "generated_at": now.isoformat(),
        "last_verified_at": previous.get("last_verified_at"), "generation": previous.get("generation"),
        "databases": previous.get("databases", []), "fresh": False, "new_snapshot": False,
        "retained_generation_limit": RETAIN_GENERATIONS, "maximum_database_bytes": MAX_DATABASE_BYTES,
        "automatic_restore_allowed": False, "off_host_disaster_recovery": False, "broker_write_count": 0}
    try:
        if root.is_symlink():
            raise ValueError("recovery_backup_directory_symlink_forbidden")
        root.mkdir(mode=0o700, exist_ok=True)
        sources = [runtime / name for name in DATABASES if (runtime / name).exists()]
        if not sources or not (runtime / DATABASES[0]).is_file():
            raise ValueError("canonical_ledger_missing")
        if any(source.is_symlink() or source.stat().st_size > MAX_DATABASE_BYTES for source in sources):
            raise ValueError("recovery_source_outside_budget_or_symlink")
        _prune_generations(root, preserve=generation if valid_name else None)
        existing_bytes = 0
        for entry in root.iterdir():
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.name.startswith(".partial-") and now.timestamp() - entry.stat().st_mtime > 3600:
                shutil.rmtree(entry)
                continue
            existing_bytes += sum((entry / name).lstat().st_size for name in DATABASES if (entry / name).exists())
        if existing_bytes + sum(source.stat().st_size for source in sources) > TOTAL_BUDGET_BYTES:
            raise ValueError("recovery_snapshot_retention_budget_exhausted")
        # Keep the trading reserve intact even while both old and new copies exist.
        if shutil.disk_usage(runtime).free < 64 * 1024**3 + 2 * sum(source.stat().st_size for source in sources):
            raise ValueError("recovery_backup_would_consume_trading_reserve")
        candidate = Path(tempfile.mkdtemp(prefix=".partial-", dir=root))
        deadline = time.monotonic() + MAX_BACKUP_SECONDS
        rows = []
        for source in sources:
            target = candidate / source.name
            _online_copy(source, target, deadline)
            rows.append({"name": source.name, "bytes": target.stat().st_size, "quick_check": "ok"})
        name = now.strftime("%Y%m%dT%H%M%S%fZ")
        os.rename(candidate, root / name)
        candidate = None
        # Collect only this module's complete, strictly named generations.
        _prune_generations(root, preserve=generation if valid_name else None)
        result.update(status="verified_local_snapshot", fresh=True, new_snapshot=True,
            last_verified_at=now.isoformat(), generation=name, databases=rows, next_retry_at=None,
            verification_basis="sqlite_quick_check_at_creation_size_and_presence_between_runs")
    except (OSError, sqlite3.Error, ValueError, TimeoutError) as error:
        result.update(status="snapshot_failed", error_type=type(error).__name__,
            next_retry_at=(now + timedelta(seconds=RETRY_SECONDS)).isoformat())
    finally:
        if candidate is not None:
            shutil.rmtree(candidate, ignore_errors=True)
    write_json_atomic(path, result)
    return result
