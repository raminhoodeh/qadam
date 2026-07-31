from __future__ import annotations

import multiprocessing
import json
from pathlib import Path
import time

import pytest

from orchestrator.qadam_resource_locks import (
    RESOURCE_ORDER,
    ResourceClaims,
    ResourceLease,
    ResourceLockBusy,
    claims_are_compatible,
    reconcile_stale_resource_leases,
    validate_resource_order,
)


def _hold_lock(root: str, mode: str, ready: multiprocessing.Event) -> None:
    claims = (
        ResourceClaims(writes=("source_lake",))
        if mode == "write"
        else ResourceClaims(reads=("source_lake",))
    )
    with ResourceLease(
        Path(root),
        service_id=f"child-{mode}",
        claims=claims,
        timeout_seconds=1,
    ):
        ready.set()
        time.sleep(2)


def test_readers_are_compatible_and_writer_conflicts() -> None:
    readers = ResourceClaims(reads=("source_lake",))
    writer = ResourceClaims(writes=("source_lake",))
    assert claims_are_compatible(readers, readers) is True
    assert claims_are_compatible(readers, writer) is False


def test_writer_blocks_reader_until_bounded_timeout(tmp_path) -> None:
    ready = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_hold_lock,
        args=(str(tmp_path), "write", ready),
    )
    process.start()
    assert ready.wait(2)
    try:
        with pytest.raises(ResourceLockBusy):
            with ResourceLease(
                tmp_path,
                service_id="parent-reader",
                claims=ResourceClaims(reads=("source_lake",)),
                timeout_seconds=0.1,
            ):
                pass
    finally:
        process.terminate()
        process.join(3)


def test_killed_process_releases_kernel_lock(tmp_path) -> None:
    ready = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_hold_lock,
        args=(str(tmp_path), "write", ready),
    )
    process.start()
    assert ready.wait(2)
    process.terminate()
    process.join(3)
    removed = reconcile_stale_resource_leases(tmp_path)
    state = json.loads((tmp_path / "qadam_resource_lock_state.json").read_text())
    assert removed
    assert state["active_lease_count"] == 0
    with ResourceLease(
        tmp_path,
        service_id="recovery-reader",
        claims=ResourceClaims(reads=("source_lake",)),
        timeout_seconds=1,
    ):
        pass


def test_global_resource_order_is_canonical() -> None:
    assert validate_resource_order(("source_lake", "point_in_time_evidence", "edge_registry"))
    assert not validate_resource_order(("edge_registry", "source_lake"))


def test_power_market_research_is_a_registered_logical_resource() -> None:
    assert "power_market_research" in RESOURCE_ORDER
    ResourceClaims(writes=("power_market_research",)).validate()
