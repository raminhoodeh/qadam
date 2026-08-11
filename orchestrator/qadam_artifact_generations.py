"""Immutable generation storage for Qadam research artifacts."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, BinaryIO, Iterable, Mapping

from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    sha256_json,
    write_json_atomic,
)
from orchestrator.qadam_resource_locks import ResourceClaims, ResourceLease

SCHEMA_VERSION = "qadam_artifact_generations.v1"
GENERATION_ROOT = ".qadam_generations"


class GenerationError(RuntimeError):
    """Raised when an immutable artifact generation is incomplete or invalid."""


def _safe_component(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in value.strip()
    ).strip("-")
    if not normalized:
        raise ValueError("generation_resource_name_invalid")
    return normalized


def _hash_file(path: Path) -> str:
    digest = file_sha256(path)
    if digest is None:
        raise GenerationError(f"generation_file_unreadable:{path.name}")
    return digest


@dataclass(frozen=True)
class GenerationReference:
    resource: str
    generation_id: str
    path: Path
    manifest: dict[str, Any]


class GenerationLease(AbstractContextManager[GenerationReference]):
    """Hold a shared lease while one immutable generation is being read."""

    def __init__(self, store: "ArtifactGenerationStore", reference: GenerationReference):
        self.store = store
        self.reference = reference
        self._handle: BinaryIO | None = None

    def __enter__(self) -> GenerationReference:
        lease_path = self.reference.path / ".reader.lock"
        self._handle = lease_path.open("a+b")
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_SH)
        self.store.validate_reference(self.reference)
        return self.reference

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._handle is not None:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._handle.close()
                self._handle = None


class ArtifactGenerationStore:
    """Publish and resolve complete immutable generations under one resource."""

    def __init__(self, runtime: Path, resource: str):
        self.runtime = runtime.resolve()
        self.resource = _safe_component(resource)
        self.root = self.runtime / GENERATION_ROOT / self.resource
        self.generations = self.root / "generations"
        self.staging = self.root / "staging"
        self.current_path = self.root / "current.json"
        self.publish_lock_path = self.root / ".publish.lock"
        self.generations.mkdir(parents=True, exist_ok=True)
        self.staging.mkdir(parents=True, exist_ok=True)

    def _publish_lock(self) -> BinaryIO:
        self.publish_lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.publish_lock_path.open("a+b")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def publish_files(
        self,
        files: Mapping[str, Path],
        *,
        producer: str,
        provenance: Mapping[str, Any] | None = None,
        copy_mode: str = "copy",
    ) -> GenerationReference:
        """Copy or hardlink files into a complete immutable generation."""

        if not files:
            raise ValueError("generation_requires_files")
        normalized: dict[str, Path] = {}
        for name, source in files.items():
            if Path(name).name != name:
                raise ValueError("generation_file_name_must_be_basename")
            source_path = source.resolve()
            if not source_path.is_file():
                raise GenerationError(f"generation_source_missing:{name}")
            normalized[name] = source_path

        identity = {
            "resource": self.resource,
            "producer": producer,
            "files": {
                name: {
                    "source": str(path),
                    "size": path.stat().st_size,
                    "sha256": _hash_file(path),
                }
                for name, path in sorted(normalized.items())
            },
            "provenance": dict(provenance or {}),
        }
        generation_id = sha256_json(identity)[:24]
        destination = self.generations / generation_id
        lock = self._publish_lock()
        try:
            if not destination.exists():
                staging_path = Path(
                    tempfile.mkdtemp(
                        prefix=f".{generation_id}.",
                        dir=self.staging,
                    )
                )
                try:
                    records: list[dict[str, Any]] = []
                    for name, source in sorted(normalized.items()):
                        target = staging_path / name
                        if copy_mode == "hardlink":
                            try:
                                os.link(source, target)
                            except OSError:
                                shutil.copy2(source, target)
                        elif copy_mode == "copy":
                            shutil.copy2(source, target)
                        else:
                            raise ValueError("unsupported_generation_copy_mode")
                        with target.open("rb") as handle:
                            os.fsync(handle.fileno())
                        records.append(
                            {
                                "name": name,
                                "size_bytes": target.stat().st_size,
                                "sha256": _hash_file(target),
                                "source_path": str(source),
                            }
                        )
                    manifest = {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_artifact_generation_manifest",
                        "generated_at": now_iso(),
                        "resource": self.resource,
                        "generation_id": generation_id,
                        "producer": producer,
                        "status": "complete",
                        "file_count": len(records),
                        "files": records,
                        "provenance": dict(provenance or {}),
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "authority": authority_flags(),
                    }
                    write_json_atomic(staging_path / "manifest.json", manifest)
                    write_json_atomic(
                        staging_path / "completion.json",
                        {
                            "schema_version": SCHEMA_VERSION,
                            "artifact_type": "qadam_artifact_generation_completion",
                            "generated_at": now_iso(),
                            "resource": self.resource,
                            "generation_id": generation_id,
                            "manifest_sha256": _hash_file(staging_path / "manifest.json"),
                            "complete": True,
                            "paper_order_created_count": 0,
                            "broker_write_count": 0,
                            "authority": authority_flags(),
                        },
                    )
                    directory_descriptor = os.open(staging_path, os.O_RDONLY)
                    try:
                        os.fsync(directory_descriptor)
                    finally:
                        os.close(directory_descriptor)
                    os.replace(staging_path, destination)
                finally:
                    if staging_path.exists():
                        shutil.rmtree(staging_path)
            manifest = read_json(destination / "manifest.json")
            write_json_atomic(
                self.current_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_artifact_generation_pointer",
                    "generated_at": now_iso(),
                    "resource": self.resource,
                    "generation_id": generation_id,
                    "manifest_sha256": _hash_file(destination / "manifest.json"),
                    "paper_order_created_count": 0,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                },
            )
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
        reference = GenerationReference(
            resource=self.resource,
            generation_id=generation_id,
            path=destination,
            manifest=manifest,
        )
        self.validate_reference(reference)
        return reference

    def resolve_current(self) -> GenerationReference:
        lock = self._publish_lock()
        try:
            pointer = read_json(self.current_path)
            generation_id = str(pointer.get("generation_id") or "")
            if not generation_id:
                raise GenerationError("generation_pointer_missing")
            path = self.generations / generation_id
            manifest = read_json(path / "manifest.json")
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
        reference = GenerationReference(
            resource=self.resource,
            generation_id=generation_id,
            path=path,
            manifest=manifest,
        )
        self.validate_reference(reference)
        return reference

    def lease_current(self) -> GenerationLease:
        return GenerationLease(self, self.resolve_current())

    def validate_reference(self, reference: GenerationReference) -> None:
        if reference.resource != self.resource:
            raise GenerationError("generation_resource_mismatch")
        if not reference.path.is_dir():
            raise GenerationError("generation_directory_missing")
        completion = read_json(reference.path / "completion.json")
        if completion.get("complete") is not True:
            raise GenerationError("generation_incomplete")
        manifest = read_json(reference.path / "manifest.json")
        if manifest.get("generation_id") != reference.generation_id:
            raise GenerationError("generation_manifest_identity_mismatch")
        if completion.get("manifest_sha256") != _hash_file(reference.path / "manifest.json"):
            raise GenerationError("generation_manifest_checksum_mismatch")
        for record in manifest.get("files", []):
            path = reference.path / str(record.get("name") or "")
            if not path.is_file():
                raise GenerationError("generation_file_missing")
            if record.get("sha256") != _hash_file(path):
                raise GenerationError("generation_file_checksum_mismatch")

    def collect(self, *, retain: int = 3) -> list[str]:
        """Remove old unleased generations while retaining current and recent data."""

        retain = max(3, int(retain))
        publish_lock = self._publish_lock()
        removed: list[str] = []
        try:
            current = read_json(self.current_path).get("generation_id")
            candidates = sorted(
                (path for path in self.generations.iterdir() if path.is_dir()),
                key=lambda path: path.stat().st_mtime_ns,
                reverse=True,
            )
            for path in candidates[retain:]:
                if path.name == current:
                    continue
                lease_path = path / ".reader.lock"
                try:
                    handle = lease_path.open("a+b")
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    # macOS may report EDEADLK when this process already holds a
                    # shared reader lease. That is equivalent to a busy lease:
                    # retain the generation and let a later maintenance pass
                    # collect it after the reader releases the lock.
                    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        continue
                    raise
                try:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError as exc:
                        if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                            continue
                        raise
                    shutil.rmtree(path)
                    removed.append(path.name)
                finally:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
                    handle.close()
        finally:
            fcntl.flock(publish_lock.fileno(), fcntl.LOCK_UN)
            publish_lock.close()
        return removed


def bootstrap_registered_generations(
    runtime: Path,
    records: Iterable[Mapping[str, Any]],
    *,
    producer: str = "porr_runtime_migration",
) -> dict[str, Any]:
    """Snapshot all registered hot artifacts into complete generation zero.

    The migration is intentionally independent of provider refreshes and trading
    routes. It preserves the exact bytes of each current artifact, publishes one
    complete generation per logical resource, and refuses partial registries.
    """

    runtime = runtime.resolve()
    grouped: dict[str, dict[str, Path]] = {}
    owners: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    duplicate_artifacts: list[str] = []
    seen: set[str] = set()
    for record in records:
        artifact = str(record.get("artifact") or "").strip()
        resource = str(record.get("logical_resource") or "").strip()
        owner = str(record.get("producer") or "").strip()
        if not artifact or Path(artifact).name != artifact or not resource or not owner:
            raise GenerationError("generation_bootstrap_registry_record_invalid")
        if artifact in seen:
            duplicate_artifacts.append(artifact)
            continue
        seen.add(artifact)
        source = runtime / artifact
        if not source.is_file():
            missing.append(artifact)
            continue
        grouped.setdefault(resource, {})[artifact] = source
        owners.setdefault(resource, {})[artifact] = owner
    if duplicate_artifacts:
        raise GenerationError(
            "generation_bootstrap_duplicate_artifacts:" + ",".join(sorted(duplicate_artifacts))
        )
    if missing:
        raise GenerationError("generation_bootstrap_missing:" + ",".join(sorted(missing)))
    if not grouped:
        raise GenerationError("generation_bootstrap_registry_empty")

    before = {
        artifact: {
            "sha256": _hash_file(path),
            "size_bytes": path.stat().st_size,
        }
        for files in grouped.values()
        for artifact, path in files.items()
    }
    resources = tuple(grouped)
    references: dict[str, GenerationReference] = {}
    with ResourceLease(
        runtime,
        service_id=producer,
        claims=ResourceClaims(writes=resources),
        timeout_seconds=120.0,
    ):
        for resource, files in grouped.items():
            references[resource] = ArtifactGenerationStore(runtime, resource).publish_files(
                files,
                producer=producer,
                provenance={
                    "migration": "generation_zero",
                    "preserves_current_artifact_bytes": True,
                    "artifact_owners": owners[resource],
                    "source_artifact_count": len(files),
                },
                copy_mode="copy",
            )

    after = {
        artifact: {
            "sha256": _hash_file(path),
            "size_bytes": path.stat().st_size,
        }
        for files in grouped.values()
        for artifact, path in files.items()
    }
    changed = sorted(artifact for artifact in before if before[artifact] != after[artifact])
    if changed:
        raise GenerationError("generation_bootstrap_source_changed:" + ",".join(changed))

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_artifact_generation_migration",
        "generated_at": now_iso(),
        "status": "passed",
        "migration_mode": "generation_zero",
        "producer": producer,
        "resource_count": len(references),
        "artifact_count": len(before),
        "source_artifact_changed_count": 0,
        "resources": {
            resource: {
                "generation_id": reference.generation_id,
                "artifact_count": int(reference.manifest.get("file_count") or 0),
                "manifest_sha256": _hash_file(reference.path / "manifest.json"),
            }
            for resource, reference in sorted(references.items())
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
