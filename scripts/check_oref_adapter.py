#!/usr/bin/env python3
"""Check the Oref read-only source adapter path."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import OrefAdapter, oref_adapter_status


async def main() -> int:
    live = "--live" in sys.argv
    adapter = OrefAdapter()

    try:
        envelope = await adapter.fetch_live() if live else adapter.fetch_sample()
    except Exception as exc:  # noqa: BLE001 - adapter check should make failures explicit
        print("oref_adapter_status=failed")
        print(f"oref_adapter_error_type={exc.__class__.__name__}")
        print(f"oref_adapter_error={exc!r}")
        return 1

    status = oref_adapter_status()
    print("oref_adapter_status=ok")
    print(f"oref_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"oref_adapter_source={envelope.source}")
    print(f"oref_adapter_event_count={len(envelope.events)}")
    print(f"oref_adapter_degraded={envelope.degraded}")
    print(f"oref_adapter_raw_archive_path={envelope.raw_archive_path}")
    print(f"oref_adapter_archive_exists={status['raw_archive_exists']}")

    if not envelope.events and not envelope.degraded and not live:
        print("oref_adapter_event_count_empty=true")
        return 1
    if not envelope.raw_archive_path:
        print("oref_adapter_raw_archive_missing=true")
        return 1

    print("oref_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
