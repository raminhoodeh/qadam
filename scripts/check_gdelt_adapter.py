#!/usr/bin/env python3
"""Check the first real read-only source adapter path: GDELT."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import GDELTAdapter, gdelt_adapter_status


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


async def main() -> int:
    live = "--live" in sys.argv
    query = _arg_value("--query=") or "oil"
    maxrecords = int(_arg_value("--maxrecords=") or "10")
    since_iso = _arg_value("--since=")
    adapter = GDELTAdapter()

    try:
        envelope = (
            await adapter.fetch_live(query=query, since_iso=since_iso, maxrecords=maxrecords)
            if live
            else adapter.fetch_sample(query=query)
        )
    except Exception as exc:  # noqa: BLE001 - adapter check should make failures explicit
        print("gdelt_adapter_status=failed")
        print(f"gdelt_adapter_error_type={exc.__class__.__name__}")
        print(f"gdelt_adapter_error={exc!r}")
        return 1

    status = gdelt_adapter_status()
    print("gdelt_adapter_status=ok")
    print(f"gdelt_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"gdelt_adapter_source={envelope.source}")
    print(f"gdelt_adapter_event_count={len(envelope.events)}")
    print(f"gdelt_adapter_degraded={envelope.degraded}")
    print(f"gdelt_adapter_raw_archive_path={envelope.raw_archive_path}")
    print(f"gdelt_adapter_archive_exists={status['raw_archive_exists']}")

    if not envelope.events and not envelope.degraded:
        print("gdelt_adapter_event_count_empty=true")
        return 1
    if not envelope.raw_archive_path:
        print("gdelt_adapter_raw_archive_missing=true")
        return 1

    print("gdelt_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
