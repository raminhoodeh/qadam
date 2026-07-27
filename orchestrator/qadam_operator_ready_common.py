"""Shared primitives for the operator-ready edge-engine program.

The helpers in this module are deliberately local and non-authoritative. They
provide atomic artifact writes, provenance hashes, read-only command probes,
and a common fail-closed authority contract for Wave 0.
"""

from __future__ import annotations

from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any, Iterable

from orchestrator.config import Settings

ROOT = Path(__file__).resolve().parents[1]

WAVE0_SCHEMA_VERSION = "qadam_operator_ready_wave0.v1"

AUTHORITY_FLAGS: dict[str, bool | int] = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "command_disabled": True,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_live_send_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "autonomous_code_edit_allowed": False,
    "policy_mutation_allowed": False,
}

FALSE_AUTHORITY_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
ZERO_AUTHORITY_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if type(value) is int and value == 0
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_dir(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    path = Path(active.runtime_dir)
    if not path.is_absolute():
        path = ROOT / path
    return path


def public_path(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return candidate.name


def json_dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        retryable_errors = {
            errno.EACCES,
            errno.EAGAIN,
            errno.EBUSY,
            errno.EDEADLK,
            errno.EPERM,
        }
        if hasattr(errno, "ESTALE"):
            retryable_errors.add(errno.ESTALE)
        for attempt in range(4):
            try:
                os.replace(temporary_path, path)
                break
            except OSError as exc:
                if exc.errno not in retryable_errors or attempt == 3:
                    raise
                time.sleep(0.05 * (2**attempt))
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            # Some filesystems do not support directory fsync. The file itself
            # was already flushed before the atomic replacement.
            pass
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json_dump(payload))


def append_jsonl_durable(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (canonical_json(payload) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def artifact_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "artifact": public_path(path),
            "exists": False,
            "size_bytes": 0,
            "modified_at": None,
            "sha256": None,
        }
    stat = path.stat()
    return {
        "artifact": public_path(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": file_sha256(path),
    }


def run_read_only_command(
    command: list[str],
    *,
    cwd: Path = ROOT,
    timeout_seconds: int = 20,
    output_line_limit: int = 200,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "not_verified",
            "returncode": None,
            "error_class": exc.__class__.__name__,
            "stdout_lines": [],
            "stderr_lines": [],
        }
    stdout = completed.stdout.splitlines()[-output_line_limit:]
    stderr = completed.stderr.splitlines()[-output_line_limit:]
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "error_class": None,
        "stdout_lines": stdout,
        "stderr_lines": stderr,
    }


def git_snapshot(repo: Path) -> dict[str, Any]:
    head = run_read_only_command(["git", "rev-parse", "HEAD"], cwd=repo)
    branch = run_read_only_command(["git", "branch", "--show-current"], cwd=repo)
    status = run_read_only_command(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo,
        output_line_limit=5000,
    )
    dirty_records: list[dict[str, str]] = []
    for line in status.get("stdout_lines", []):
        if len(line) < 3:
            continue
        dirty_records.append({"state": line[:2], "path": line[3:]})
    return {
        "repo": public_path(repo),
        "head": (head.get("stdout_lines") or [None])[-1],
        "branch": (branch.get("stdout_lines") or [None])[-1],
        "git_probe_status": (
            "passed"
            if all(item.get("status") == "passed" for item in (head, branch, status))
            else "not_verified"
        ),
        "dirty": bool(dirty_records),
        "dirty_file_count": len(dirty_records),
        "dirty_files": dirty_records,
    }


def authority_flags(**overrides: bool | int) -> dict[str, bool | int]:
    flags = dict(AUTHORITY_FLAGS)
    unknown = sorted(set(overrides) - set(flags))
    if unknown:
        raise ValueError(f"unknown authority override: {', '.join(unknown)}")
    flags.update(overrides)
    return flags


def validate_authority(flags: dict[str, Any], *, prefix: str = "authority") -> list[str]:
    errors: list[str] = []
    for key in FALSE_AUTHORITY_FIELDS:
        if flags.get(key) is not False:
            errors.append(f"{prefix}_forbidden_true:{key}")
    for key in ZERO_AUTHORITY_FIELDS:
        if type(flags.get(key)) is not int or flags.get(key) != 0:
            errors.append(f"{prefix}_forbidden_nonzero:{key}")
    for key in ("read_only", "paper_only", "proposal_first", "command_disabled"):
        if flags.get(key) is not True:
            errors.append(f"{prefix}_required_true:{key}")
    return sorted(set(errors))


def unique_errors(errors: Iterable[str]) -> list[str]:
    return sorted({str(error) for error in errors if str(error)})
