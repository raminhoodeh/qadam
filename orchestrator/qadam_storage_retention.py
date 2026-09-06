"""Bounded, fail-closed storage maintenance for the unattended Qadam operator."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import fcntl
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any, BinaryIO

from orchestrator.qadam_artifact_generations import ArtifactGenerationStore
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    read_json,
    sha256_text,
)

SCHEMA_VERSION = "qadam_storage_retention.v1"
STATUS_ARTIFACT = "qadam_storage_retention_status.json"
MAINTENANCE_LEDGER_ARTIFACT = "qadam_storage_maintenance_ledger.jsonl"
LOCK_FILENAME = ".qadam_storage_retention.lock"

MIN_FREE_BYTES = 64 * 1024**3
RECOVERY_FREE_BYTES = 96 * 1024**3
MAX_USED_RATIO = 0.90
RECOVERY_USED_RATIO = 0.85
MAINTENANCE_INTERVAL_SECONDS = 3600
RETAIN_GENERATIONS = 3
ORPHAN_GRACE_SECONDS = 3600
TELEMETRY_ARCHIVE_MAX_AGE_DAYS = 90
TELEMETRY_ARCHIVE_MAX_BYTES = 2 * 1024**3
UF_DATALESS = getattr(stat, "UF_DATALESS", 0x40000000)

# These are replayable operational projections, not canonical source, trade,
# order, proof, or research datasets. Their removed prefix is compressed before
# the recent live tail is atomically replaced.
TELEMETRY_LOG_POLICIES: dict[str, tuple[int, int]] = {
    "operator_inbox_history.jsonl": (64 * 1024**2, 500),
    "evidence_packet_runtime_history.jsonl": (64 * 1024**2, 500),
    "paper_operational_cycle_history.jsonl": (64 * 1024**2, 250),
    "phase5_signal_corroboration_refresh_history.jsonl": (64 * 1024**2, 250),
    "qadam_operator_service_receipts.jsonl": (64 * 1024**2, 5000),
    "qadam_operator_session_ledger.jsonl": (32 * 1024**2, 1000),
    "qadam_resource_lock_events.jsonl": (64 * 1024**2, 5000),
    "qadam_storage_maintenance_ledger.jsonl": (32 * 1024**2, 1000),
}


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _allocated_bytes(path: Path) -> int:
    try:
        return int(path.stat().st_blocks) * 512
    except OSError:
        return 0


def _directory_is_dataless(path: Path) -> bool:
    try:
        return bool(getattr(path.stat(), "st_flags", 0) & UF_DATALESS)
    except OSError:
        return True


def _research_files_without_cloud_hydration(root: Path, filename: str) -> list[Path]:
    """Enumerate local research files without entering iCloud placeholders."""

    matches: list[Path] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if not _directory_is_dataless(current_path / name)
        ]
        if filename in files:
            matches.append(current_path / filename)
    return matches


def live_storage_health(runtime: Path, *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Measure the live filesystem and apply hysteresis after pressure."""

    runtime = runtime.resolve()
    usage = shutil.disk_usage(runtime)
    used_ratio = (usage.used / usage.total) if usage.total else 1.0
    prior_pressure = bool((previous or {}).get("pressure_active"))
    stop_threshold_crossed = usage.free < MIN_FREE_BYTES or used_ratio >= MAX_USED_RATIO
    recovery_threshold_met = (
        usage.free >= RECOVERY_FREE_BYTES and used_ratio <= RECOVERY_USED_RATIO
    )
    pressure_active = stop_threshold_crossed or (
        prior_pressure and not recovery_threshold_met
    )
    return {
        "measured_at": now_iso(),
        "measurement_source": "shutil.disk_usage_live_filesystem",
        "filesystem_path": str(runtime),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_ratio": round(used_ratio, 8),
        "minimum_free_bytes": MIN_FREE_BYTES,
        "recovery_free_bytes": RECOVERY_FREE_BYTES,
        "maximum_used_ratio": MAX_USED_RATIO,
        "recovery_used_ratio": RECOVERY_USED_RATIO,
        "stop_threshold_crossed": stop_threshold_crossed,
        "recovery_threshold_met": recovery_threshold_met,
        "pressure_active": pressure_active,
        "write_services_allowed": not pressure_active,
    }


def provider_budget_available(runtime: Path) -> tuple[bool, dict[str, Any]]:
    """Read monetary provider limits without trusting cached disk telemetry."""

    budget = read_json(runtime.resolve() / "qadam_backfill_cost_and_rate_limit_state.json")
    remaining = budget.get("historical_data_budget_remaining_usd")
    exhausted = False
    if remaining is not None:
        try:
            exhausted = float(remaining) <= 0
        except (TypeError, ValueError):
            exhausted = True
    return not exhausted, {
        "remaining_usd": remaining,
        "budget_artifact_present": bool(budget),
        "cached_disk_value_ignored": "disk_free_bytes" in budget,
    }


def _score_plane_hash(partitions: list[dict[str, Any]]) -> str:
    material = [
        {
            "partition_id": row.get("partition_id"),
            "dataset_path": row.get("dataset_path"),
            "dataset_sha256": row.get("dataset_sha256"),
            "record_set_hash": row.get("record_set_hash"),
            "row_count": row.get("row_count"),
        }
        for row in partitions
    ]
    return sha256_text(canonical_json(material))


def _score_manifests(runtime: Path) -> list[tuple[str, dict[str, Any]]]:
    manifests: list[tuple[str, dict[str, Any]]] = []
    generation_root = (
        runtime
        / ".qadam_generations"
        / "score_plane"
        / "generations"
    )
    if generation_root.is_dir():
        generation_paths = sorted(
            (path for path in generation_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for generation_path in generation_paths:
            path = generation_path / "qadam_pattern_score_tape_manifest.json"
            payload = read_json(path)
            if payload:
                manifests.append((f"generation:{generation_path.name}", payload))
    current = read_json(runtime / "qadam_pattern_score_tape_manifest.json")
    if current:
        manifests.append(("runtime_current", current))
    return manifests


def _protected_research_paths(runtime: Path) -> tuple[set[Path], set[str], list[str]]:
    repo_root = runtime.parent.parent.resolve()
    score_root = (runtime.parent / "research" / "pattern_score_tape").resolve()
    label_root = (runtime.parent / "research" / "forward_labels").resolve()
    protected_scores: set[Path] = set()
    protected_label_roots: set[str] = set()
    manifest_sources: list[str] = []
    checksum_cache: dict[Path, str | None] = {}

    for source, manifest in _score_manifests(runtime):
        partitions = [
            row
            for row in manifest.get("partitions", [])
            if isinstance(row, dict)
            and row.get("status") == "complete"
            and int(row.get("row_count") or 0) > 0
        ]
        if not partitions:
            continue
        valid_paths: list[Path] = []
        for partition in partitions:
            relative = str(partition.get("dataset_path") or "")
            path = (repo_root / relative).resolve()
            if not path.is_relative_to(score_root):
                raise RuntimeError(f"score_dataset_outside_research_root:{relative}")
            if not path.is_file():
                raise RuntimeError(f"protected_score_dataset_missing:{relative}")
            actual = checksum_cache.setdefault(path, file_sha256(path))
            if actual != partition.get("dataset_sha256"):
                raise RuntimeError(f"protected_score_dataset_checksum_mismatch:{relative}")
            valid_paths.append(path)
        protected_scores.update(valid_paths)
        protected_label_roots.add(f"score_tape={_score_plane_hash(partitions)[:16]}")
        manifest_sources.append(source)

    label_manifest = read_json(runtime / "qadam_forward_label_manifest.json")
    for partition in label_manifest.get("partitions", []):
        if not isinstance(partition, dict):
            continue
        relative = str(partition.get("dataset_path") or "")
        if not relative:
            continue
        path = (repo_root / relative).resolve()
        if not path.is_relative_to(label_root):
            raise RuntimeError(f"label_dataset_outside_research_root:{relative}")
        try:
            protected_label_roots.add(path.relative_to(label_root).parts[0])
        except (ValueError, IndexError):
            raise RuntimeError(f"label_dataset_root_invalid:{relative}") from None

    return protected_scores, protected_label_roots, manifest_sources


def _remove_empty_parents(path: Path, *, stop: Path) -> None:
    current = path.parent
    while current != stop and current.is_relative_to(stop):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def prune_research_generations(runtime: Path, *, apply: bool = True) -> dict[str, Any]:
    """Delete only score and label datasets no retained manifest can reference."""

    runtime = runtime.resolve()
    score_root = (runtime.parent / "research" / "pattern_score_tape").resolve()
    label_root = (runtime.parent / "research" / "forward_labels").resolve()
    protected_scores, protected_label_roots, manifest_sources = _protected_research_paths(
        runtime
    )
    existing_score_files = (
        _research_files_without_cloud_hydration(score_root, "scores.jsonl")
        if score_root.is_dir()
        else []
    )
    existing_label_roots = (
        [path for path in label_root.iterdir() if path.is_dir()]
        if label_root.is_dir()
        else []
    )
    if not protected_scores:
        if existing_score_files or existing_label_roots:
            raise RuntimeError("no_verified_score_generation_available_for_retention")
        return {
            "status": "not_initialized",
            "manifest_sources": [],
            "protected_score_file_count": 0,
            "protected_label_roots": [],
            "obsolete_score_file_count": 0,
            "obsolete_label_root_count": 0,
            "removed_allocated_bytes": 0,
        }
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_GRACE_SECONDS)
    score_candidates: list[Path] = []
    if existing_score_files:
        for path in existing_score_files:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if path.resolve() not in protected_scores and modified <= cutoff:
                score_candidates.append(path)
    label_candidates = [
        path for path in existing_label_roots if path.name not in protected_label_roots
    ]

    removed_bytes = 0
    # Forward-label roots can contain millions of cloud-offloaded date/horizon
    # placeholders. Recursive deletion would hydrate them and block the operator.
    # Keep automatic maintenance bounded and leave these immutable roots for the
    # explicit supervised cleanup path.
    deferred_label_roots = label_candidates
    if apply:
        for path in score_candidates:
            removed_bytes += _allocated_bytes(path)
            path.unlink()
            _remove_empty_parents(path, stop=score_root)
    return {
        "status": "applied" if apply else "preview",
        "manifest_sources": manifest_sources,
        "protected_score_file_count": len(protected_scores),
        "protected_label_roots": sorted(protected_label_roots),
        "obsolete_score_file_count": len(score_candidates),
        "obsolete_label_root_count": len(label_candidates),
        "deferred_label_root_count": len(deferred_label_roots),
        "deferred_label_roots": [path.name for path in deferred_label_roots],
        "label_cleanup_mode": "supervised_no_cloud_hydration",
        "removed_allocated_bytes": removed_bytes if apply else 0,
    }


def _hash_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _rotate_jsonl_prefix(
    runtime: Path,
    path: Path,
    *,
    retain_lines: int,
) -> dict[str, Any] | None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_dir = runtime / "archive" / "operator-retention" / path.name
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{timestamp}.jsonl.gz"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{archive_path.name}.", suffix=".tmp", dir=archive_dir
    )
    os.close(descriptor)
    temporary_archive = Path(temporary_name)
    tail: deque[bytes] = deque()
    dropped_hash = hashlib.sha256()
    dropped_count = 0
    original_size = path.stat().st_size
    original_lines = 0
    try:
        with path.open("rb") as source, gzip.open(
            temporary_archive, "wb", compresslevel=6
        ) as archive:
            for line in source:
                original_lines += 1
                tail.append(line)
                if len(tail) > retain_lines:
                    dropped = tail.popleft()
                    archive.write(dropped)
                    dropped_hash.update(dropped)
                    dropped_count += 1
        if dropped_count == 0:
            temporary_archive.unlink(missing_ok=True)
            return None
        with temporary_archive.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary_archive, archive_path)

        live_descriptor, live_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(live_descriptor, "wb") as live:
                for line in tail:
                    live.write(line)
                live.flush()
                os.fsync(live.fileno())
            os.replace(live_name, path)
        finally:
            Path(live_name).unlink(missing_ok=True)

        with gzip.open(archive_path, "rb") as restored:
            restored_sha = _hash_stream(restored)
        if restored_sha != dropped_hash.hexdigest():
            raise RuntimeError(f"telemetry_archive_verification_failed:{path.name}")
        return {
            "source": path.name,
            "archive": str(archive_path.relative_to(runtime.parent.parent)),
            "original_size_bytes": original_size,
            "original_line_count": original_lines,
            "archived_line_count": dropped_count,
            "retained_live_line_count": len(tail),
            "archive_size_bytes": archive_path.stat().st_size,
            "archive_decompression_sha256": restored_sha,
        }
    finally:
        temporary_archive.unlink(missing_ok=True)


def rotate_runtime_telemetry(runtime: Path, *, apply: bool = True) -> dict[str, Any]:
    rotations: list[dict[str, Any]] = []
    candidates: list[str] = []
    for filename, (threshold, retain_lines) in TELEMETRY_LOG_POLICIES.items():
        path = runtime / filename
        if not path.is_file() or path.stat().st_size <= threshold:
            continue
        candidates.append(filename)
        if apply:
            record = _rotate_jsonl_prefix(runtime, path, retain_lines=retain_lines)
            if record:
                rotations.append(record)
                if filename == "qadam_operator_service_receipts.jsonl":
                    (runtime / "qadam_operator_service_receipt_index.json").unlink(
                        missing_ok=True
                    )
    return {
        "status": "applied" if apply else "preview",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "rotation_count": len(rotations),
        "rotations": rotations,
    }


def prune_telemetry_archives(runtime: Path, *, apply: bool = True) -> dict[str, Any]:
    root = runtime / "archive" / "operator-retention"
    if not root.is_dir():
        return {"candidate_count": 0, "removed_count": 0, "removed_bytes": 0}
    files = sorted(
        (path for path in root.rglob("*.gz") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=TELEMETRY_ARCHIVE_MAX_AGE_DAYS)
    total = sum(path.stat().st_size for path in files)
    candidates: list[Path] = []
    remaining = total
    for path in files:
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified < cutoff or remaining > TELEMETRY_ARCHIVE_MAX_BYTES:
            candidates.append(path)
            remaining -= path.stat().st_size
    removed_bytes = 0
    if apply:
        for path in candidates:
            removed_bytes += path.stat().st_size
            path.unlink()
    return {
        "candidate_count": len(candidates),
        "removed_count": len(candidates) if apply else 0,
        "removed_bytes": removed_bytes,
        "retention_days": TELEMETRY_ARCHIVE_MAX_AGE_DAYS,
        "maximum_archive_bytes": TELEMETRY_ARCHIVE_MAX_BYTES,
    }


def collect_artifact_generations(runtime: Path, *, apply: bool = True) -> dict[str, Any]:
    root = runtime / ".qadam_generations"
    removed: dict[str, list[str]] = {}
    if not root.is_dir():
        return {"removed_generation_count": 0, "removed_by_resource": removed}
    for resource_path in sorted(path for path in root.iterdir() if path.is_dir()):
        if apply:
            generation_ids = ArtifactGenerationStore(runtime, resource_path.name).collect(
                retain=RETAIN_GENERATIONS
            )
        else:
            generation_ids = []
        if generation_ids:
            removed[resource_path.name] = generation_ids
    return {
        "removed_generation_count": sum(len(values) for values in removed.values()),
        "removed_by_resource": removed,
    }


def run_storage_maintenance(
    runtime: Path,
    *,
    force: bool = False,
    apply: bool = True,
) -> dict[str, Any]:
    runtime = runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    store = AtomicArtifactStore(runtime)
    lock_path = runtime / LOCK_FILENAME
    previous = read_json(runtime / STATUS_ARTIFACT)
    disk_before = live_storage_health(runtime, previous=previous.get("disk"))
    previous_at = _parse_timestamp(previous.get("last_maintenance_at"))
    due = (
        force
        or disk_before["pressure_active"]
        or previous_at is None
        or (datetime.now(timezone.utc) - previous_at).total_seconds()
        >= MAINTENANCE_INTERVAL_SECONDS
    )
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {
                **previous,
                "generated_at": now_iso(),
                "status": "maintenance_already_active",
                "disk": disk_before,
            }
        try:
            maintenance_error: dict[str, str] | None = None
            if due:
                try:
                    generations = collect_artifact_generations(runtime, apply=apply)
                    research = prune_research_generations(runtime, apply=apply)
                    telemetry = rotate_runtime_telemetry(runtime, apply=apply)
                    archives = prune_telemetry_archives(runtime, apply=apply)
                    last_maintenance_at = now_iso()
                except Exception as exc:  # noqa: BLE001 - fail closed across maintenance steps
                    maintenance_error = {
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    }
                    generations = {"status": "maintenance_failed"}
                    research = {"status": "maintenance_failed"}
                    telemetry = {"status": "maintenance_failed", "rotation_count": 0}
                    archives = {"status": "maintenance_failed", "removed_count": 0}
                    last_maintenance_at = previous.get("last_maintenance_at")
            else:
                # Producers can publish between hourly deep cleanups. Collect only
                # unleased projection generations here; keep research cleanup hourly.
                try:
                    generations = collect_artifact_generations(runtime, apply=apply)
                except Exception as exc:  # noqa: BLE001 - report bounded maintenance failure
                    maintenance_error = {"error_type": type(exc).__name__, "error": str(exc)[:500]}
                    generations = {"status": "maintenance_failed"}
                research = {"status": "not_due"}
                telemetry = {"status": "not_due", "rotation_count": 0}
                archives = {"removed_count": 0}
                last_maintenance_at = previous.get("last_maintenance_at")
            disk_after = live_storage_health(runtime, previous=disk_before)
            if maintenance_error is not None:
                disk_after = {
                    **disk_after,
                    "reason": "storage_maintenance_failed",
                    "maintenance_degraded": True,
                }
            status = {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_storage_retention_status",
                "generated_at": now_iso(),
                "last_maintenance_at": last_maintenance_at,
                "status": (
                    "maintenance_failed"
                    if maintenance_error is not None
                    else (
                        "healthy"
                        if disk_after["write_services_allowed"]
                        else "disk_resource_pressure"
                    )
                ),
                "maintenance_due": due,
                "maintenance_applied": bool(due and apply),
                "disk": disk_after,
                "artifact_generations": generations,
                "research_generations": research,
                "telemetry": telemetry,
                "telemetry_archives": archives,
                "maintenance_error": maintenance_error,
                "protected_boundaries": [
                    "provider_raw_and_normalized_data",
                    "canonical_source_price_alignment",
                    "statistical_and_quantum_research_results",
                    "paper_orders_positions_trades_and_proof",
                    "authority_and_safety_state",
                ],
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "authority": authority_flags(),
            }
            store.write_json(STATUS_ARTIFACT, status)
            if due and apply:
                append_jsonl_durable(
                    runtime / MAINTENANCE_LEDGER_ARTIFACT,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_storage_maintenance_event",
                        "generated_at": status["generated_at"],
                        "status": status["status"],
                        "artifact_generations": generations,
                        "research_generations": research,
                        "telemetry_rotation_count": telemetry.get("rotation_count", 0),
                        "telemetry_archive_removed_count": archives.get(
                            "removed_count", 0
                        ),
                        "disk_free_bytes": disk_after["free_bytes"],
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "authority": authority_flags(),
                    },
                )
            return status
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def validate_storage_status(status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    disk = status.get("disk") if isinstance(status.get("disk"), dict) else {}
    if disk.get("measurement_source") != "shutil.disk_usage_live_filesystem":
        errors.append("storage_disk_measurement_not_live")
    if disk.get("write_services_allowed") is not True:
        errors.append("storage_write_services_blocked")
    if status.get("status") == "maintenance_failed":
        errors.append("storage_maintenance_failed")
    if status.get("paper_order_created_count") != 0:
        errors.append("storage_maintenance_created_paper_order")
    if status.get("broker_write_count") != 0:
        errors.append("storage_maintenance_created_broker_write")
    generation_root = Path(str(disk.get("filesystem_path") or ".")) / ".qadam_generations"
    if generation_root.is_dir():
        for resource in generation_root.iterdir():
            generations = resource / "generations"
            if generations.is_dir():
                # Extra generations may be current or reader-leased. Count alone
                # cannot establish a maintenance failure or disk exhaustion.
                paths = [path for path in generations.iterdir() if path.is_dir()]
                if len(paths) > RETAIN_GENERATIONS and status.get("maintenance_error"):
                    errors.append(f"storage_generation_retention_exceeded:{resource.name}")
    return errors
