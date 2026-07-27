"""Canonical local-state resolution and unattended-runtime preflight."""

from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_state_root.v1"
CHECK_ARTIFACT = "qadam_state_root_preflight.json"
MINIMUM_FREE_BYTES = 10 * 1024**3


def resolve_state_root(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    path = Path(active.state_root).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or result.stderr).strip()


def _git_ignored(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        return True
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", str(relative)],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def _atomic_and_lock_probe(root: Path) -> tuple[bool, bool, str | None]:
    root.mkdir(parents=True, exist_ok=True)
    probe = Path(tempfile.mkdtemp(prefix=".qadam-state-probe-", dir=root))
    atomic_ok = False
    lock_ok = False
    error: str | None = None
    try:
        source = probe / "source"
        target = probe / "target"
        source.write_text("qadam-state-probe", encoding="utf-8")
        os.replace(source, target)
        atomic_ok = target.read_text(encoding="utf-8") == "qadam-state-probe"
        with (probe / "lease.lock").open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_ok = True
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        error = f"{type(exc).__name__}:{exc.errno}:{exc}"
    finally:
        shutil.rmtree(probe, ignore_errors=True)
    return atomic_ok, lock_ok, error


def build_state_root_preflight(settings: Settings | None = None) -> dict[str, Any]:
    active = settings or Settings.from_env()
    root = resolve_state_root(active)
    runtime = runtime_dir(active).resolve()
    research = Path(active.data_root).expanduser()
    if not research.is_absolute():
        research = ROOT / research
    research = (research / "research").resolve()
    atomic_ok, lock_ok, probe_error = _atomic_and_lock_probe(root)
    disk = shutil.disk_usage(root)
    flags = _command_output(["ls", "-ldO", str(root)]).lower()
    filesystem_type = _command_output(["stat", "-f", "%T", str(root)])
    blockers: list[str] = []
    warnings: list[str] = []
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        blockers.append("state_root_not_read_write_accessible")
    if not atomic_ok:
        blockers.append("state_root_atomic_replace_probe_failed")
    if not lock_ok:
        blockers.append("state_root_advisory_lock_probe_failed")
    if "dataless" in flags or "offline" in flags:
        blockers.append("state_root_cloud_placeholder_detected")
    if not _git_ignored(runtime) or not _git_ignored(research):
        blockers.append("hot_state_path_is_git_trackable")
    if disk.free < MINIMUM_FREE_BYTES:
        blockers.append("state_root_disk_below_hard_safety_floor")
    elif disk.free / max(disk.total, 1) < 0.05:
        warnings.append("state_root_disk_below_five_percent_free")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_state_root_preflight",
        "generated_at": now_iso(),
        "status": "passed" if not blockers else "blocked",
        "state_root": str(root),
        "runtime_root": str(runtime),
        "research_root": str(research),
        "filesystem_type": filesystem_type,
        "filesystem_flags": flags,
        "read_write_accessible": os.access(root, os.R_OK | os.W_OK | os.X_OK),
        "atomic_replace_supported": atomic_ok,
        "advisory_lock_supported": lock_ok,
        "git_ignored_runtime": _git_ignored(runtime),
        "git_ignored_research": _git_ignored(research),
        "cloud_placeholder_detected": "dataless" in flags or "offline" in flags,
        "disk_total_bytes": disk.total,
        "disk_used_bytes": disk.used,
        "disk_free_bytes": disk.free,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "probe_error": probe_error,
        "blockers": blockers,
        "warnings": warnings,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, payload)
    return payload


def tree_digest(root: Path) -> dict[str, Any]:
    """Return a resumable inventory digest without loading file contents."""

    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            stat = path.stat()
            relative = str(path.relative_to(root))
            digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
            file_count += 1
            byte_count += stat.st_size
    return {
        "root": str(root),
        "file_count": file_count,
        "byte_count": byte_count,
        "inventory_sha256": digest.hexdigest(),
    }
