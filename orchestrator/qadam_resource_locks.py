"""Process-wide resource locks for Qadam's autonomous operator services.

The operator previously coordinated work by broad service groups. That was not
enough when unrelated services touched the same evidence plane. This module
coordinates the logical artifacts themselves and is intentionally independent
of broker or trading authority.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import errno
import fcntl
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable

from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_resource_locks.v1"

RESOURCE_ORDER = (
    "source_lake",
    "price_lake",
    "power_market_research",
    "point_in_time_evidence",
    "score_plane",
    "label_plane",
    "edge_registry",
    "learning_plane",
    "paper_state",
    "dashboard_projection",
    "public_status_transport",
)

RESOURCE_ORDER_INDEX = {name: index for index, name in enumerate(RESOURCE_ORDER)}

LOCK_DIRECTORY = ".qadam_resource_locks"
LOCK_EVENTS_ARTIFACT = "qadam_resource_lock_events.jsonl"
LOCK_STATE_ARTIFACT = "qadam_resource_lock_state.json"
LOCK_EVENT_GUARD = ".qadam_resource_lock_events.lock"

RETRYABLE_RESOURCE_ERRNOS = {
    errno.EAGAIN,
    errno.EBUSY,
    errno.EDEADLK,
}
if hasattr(errno, "ESTALE"):
    RETRYABLE_RESOURCE_ERRNOS.add(errno.ESTALE)


class ResourceLockError(RuntimeError):
    """Base error for resource-lock contract failures."""


class ResourceLockBusy(ResourceLockError):
    """Raised when a compatible resource lease cannot be acquired in time."""

    def __init__(self, *, resource: str, service_id: str, timeout_seconds: float):
        super().__init__(f"resource_lock_busy:{resource}:{service_id}:{timeout_seconds:.3f}")
        self.resource = resource
        self.service_id = service_id
        self.timeout_seconds = timeout_seconds


@dataclass(frozen=True)
class ResourceClaims:
    """Declared logical resources read and written by one service."""

    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    appends: tuple[str, ...] = ()

    def validate(self) -> None:
        unknown = (set(self.reads) | set(self.writes) | set(self.appends)) - set(RESOURCE_ORDER)
        if unknown:
            raise ValueError("unknown_qadam_resource:" + ",".join(sorted(unknown)))
        if set(self.reads) & set(self.writes):
            raise ValueError("resource_declared_for_read_and_write")
        if set(self.appends) & (set(self.reads) | set(self.writes)):
            raise ValueError("append_resource_claim_conflict")

    @property
    def resources(self) -> tuple[str, ...]:
        self.validate()
        return tuple(
            sorted(
                set(self.reads) | set(self.writes) | set(self.appends),
                key=RESOURCE_ORDER_INDEX.__getitem__,
            )
        )

    def mode_for(self, resource: str) -> str:
        return "exclusive" if resource in self.writes or resource in self.appends else "shared"

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "reads": list(self.reads),
            "writes": list(self.writes),
            "appends": list(self.appends),
        }


def is_retryable_resource_error(error: BaseException) -> bool:
    return isinstance(error, OSError) and error.errno in RETRYABLE_RESOURCE_ERRNOS


def _lock_root(runtime: Path) -> Path:
    path = runtime / LOCK_DIRECTORY
    path.mkdir(parents=True, exist_ok=True)
    return path


def _append_event(runtime: Path, event: dict[str, Any]) -> None:
    guard_path = runtime / LOCK_EVENT_GUARD
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    with guard_path.open("a+", encoding="utf-8") as guard:
        fcntl.flock(guard.fileno(), fcntl.LOCK_EX)
        try:
            append_jsonl_durable(runtime / LOCK_EVENTS_ARTIFACT, event)
            state = read_json(runtime / LOCK_STATE_ARTIFACT)
            active = state.get("active") if isinstance(state.get("active"), dict) else {}
            lease_id = str(event.get("lease_id") or "")
            if event.get("event") == "acquired" and lease_id:
                active[lease_id] = {
                    key: event.get(key)
                    for key in (
                        "lease_id",
                        "service_id",
                        "owner_pid",
                        "resources",
                        "modes",
                        "acquired_at",
                    )
                }
            elif event.get("event") == "released" and lease_id:
                active.pop(lease_id, None)
            write_json_atomic(
                runtime / LOCK_STATE_ARTIFACT,
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_resource_lock_state",
                    "generated_at": now_iso(),
                    "active_lease_count": len(active),
                    "active": active,
                    "paper_order_created_count": 0,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                },
            )
        finally:
            fcntl.flock(guard.fileno(), fcntl.LOCK_UN)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reconcile_stale_resource_leases(runtime: Path) -> list[str]:
    """Remove diagnostic lease mirrors whose owning process no longer exists.

    Kernel ``flock`` leases are released automatically when a process exits.
    This reconciliation keeps the public diagnostic mirror from claiming that
    a dead process still owns a resource; it never breaks a live kernel lock.
    """

    runtime = runtime.resolve()
    guard_path = runtime / LOCK_EVENT_GUARD
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []
    with guard_path.open("a+", encoding="utf-8") as guard:
        fcntl.flock(guard.fileno(), fcntl.LOCK_EX)
        try:
            state = read_json(runtime / LOCK_STATE_ARTIFACT)
            active = state.get("active") if isinstance(state.get("active"), dict) else {}
            for lease_id, record in list(active.items()):
                if _pid_alive(int(record.get("owner_pid") or 0)):
                    continue
                active.pop(lease_id, None)
                removed.append(lease_id)
                append_jsonl_durable(
                    runtime / LOCK_EVENTS_ARTIFACT,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_resource_lock_event",
                        "generated_at": now_iso(),
                        "event": "stale_mirror_reconciled",
                        "lease_id": lease_id,
                        "service_id": record.get("service_id"),
                        "owner_pid": record.get("owner_pid"),
                        "resources": record.get("resources") or [],
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "authority": authority_flags(),
                    },
                )
            write_json_atomic(
                runtime / LOCK_STATE_ARTIFACT,
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_resource_lock_state",
                    "generated_at": now_iso(),
                    "active_lease_count": len(active),
                    "active": active,
                    "stale_mirror_reconciled_count": len(removed),
                    "paper_order_created_count": 0,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                },
            )
        finally:
            fcntl.flock(guard.fileno(), fcntl.LOCK_UN)
    return removed


class ResourceLease(AbstractContextManager["ResourceLease"]):
    """Acquire resource locks in one global order and release them together."""

    def __init__(
        self,
        runtime: Path,
        *,
        service_id: str,
        claims: ResourceClaims,
        timeout_seconds: float = 30.0,
        poll_seconds: float = 0.05,
    ):
        claims.validate()
        self.runtime = runtime.resolve()
        self.service_id = service_id
        self.claims = claims
        self.timeout_seconds = max(0.0, float(timeout_seconds))
        self.poll_seconds = max(0.01, float(poll_seconds))
        self.lease_id = f"resource-lease:{service_id}:{os.getpid()}:{time.monotonic_ns()}"
        self._handles: list[tuple[str, Any]] = []
        self._acquired_at: str | None = None

    def _acquire_one(self, resource: str) -> None:
        path = _lock_root(self.runtime) / f"{resource}.lock"
        handle = path.open("a+", encoding="utf-8")
        mode = self.claims.mode_for(resource)
        operation = fcntl.LOCK_EX if mode == "exclusive" else fcntl.LOCK_SH
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
                self._handles.append((resource, handle))
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    handle.close()
                    raise ResourceLockBusy(
                        resource=resource,
                        service_id=self.service_id,
                        timeout_seconds=self.timeout_seconds,
                    )
                time.sleep(self.poll_seconds)
            except OSError:
                handle.close()
                raise

    def acquire(self) -> "ResourceLease":
        try:
            for resource in self.claims.resources:
                self._acquire_one(resource)
        except BaseException:
            self.release(record_event=False)
            raise
        self._acquired_at = now_iso()
        _append_event(
            self.runtime,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_resource_lock_event",
                "generated_at": self._acquired_at,
                "event": "acquired",
                "lease_id": self.lease_id,
                "service_id": self.service_id,
                "owner_pid": os.getpid(),
                "resources": list(self.claims.resources),
                "modes": {
                    resource: self.claims.mode_for(resource) for resource in self.claims.resources
                },
                "acquired_at": self._acquired_at,
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "authority": authority_flags(),
            },
        )
        return self

    def release(self, *, record_event: bool = True) -> None:
        while self._handles:
            _resource, handle = self._handles.pop()
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        if record_event and self._acquired_at is not None:
            _append_event(
                self.runtime,
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_resource_lock_event",
                    "generated_at": now_iso(),
                    "event": "released",
                    "lease_id": self.lease_id,
                    "service_id": self.service_id,
                    "owner_pid": os.getpid(),
                    "resources": list(self.claims.resources),
                    "modes": {
                        resource: self.claims.mode_for(resource)
                        for resource in self.claims.resources
                    },
                    "acquired_at": self._acquired_at,
                    "released_at": now_iso(),
                    "paper_order_created_count": 0,
                    "broker_write_count": 0,
                    "authority": authority_flags(),
                },
            )
            self._acquired_at = None

    def __enter__(self) -> "ResourceLease":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def claims_are_compatible(first: ResourceClaims, second: ResourceClaims) -> bool:
    """Return whether two claim sets may execute concurrently."""

    first.validate()
    second.validate()
    first_writes = set(first.writes) | set(first.appends)
    second_writes = set(second.writes) | set(second.appends)
    first_all = set(first.resources)
    second_all = set(second.resources)
    return not ((first_writes & second_all) or (second_writes & first_all))


def validate_resource_order(resources: Iterable[str]) -> bool:
    values = tuple(resources)
    if any(value not in RESOURCE_ORDER_INDEX for value in values):
        return False
    indexes = [RESOURCE_ORDER_INDEX[value] for value in values]
    return indexes == sorted(indexes) and len(indexes) == len(set(indexes))
