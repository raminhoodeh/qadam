#!/usr/bin/env python3
"""Check the NASA FIRMS read-only physical source adapter path."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import NASAFIRMSAdapter, nasa_firms_adapter_status


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


async def main() -> int:
    live = "--live" in sys.argv
    bbox = _arg_value("--bbox=")
    source = _arg_value("--source=")
    days = int(_arg_value("--days=") or "1")
    adapter = NASAFIRMSAdapter()

    try:
        envelope = (
            await adapter.fetch_live(bbox=bbox, days=days, source=source)
            if live
            else adapter.fetch_sample(bbox=bbox, days=days)
        )
    except Exception as exc:  # noqa: BLE001 - adapter check should make failures explicit
        print("nasa_firms_adapter_status=failed")
        print(f"nasa_firms_adapter_error_type={exc.__class__.__name__}")
        print(f"nasa_firms_adapter_error={exc!r}")
        return 1

    status = nasa_firms_adapter_status()
    print("nasa_firms_adapter_status=ok")
    print(f"nasa_firms_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"nasa_firms_adapter_source={envelope.source}")
    print(f"nasa_firms_adapter_event_count={len(envelope.events)}")
    print(f"nasa_firms_adapter_degraded={envelope.degraded}")
    print(f"nasa_firms_adapter_degraded_reason={envelope.degraded_reason}")
    print(f"nasa_firms_adapter_credential_configured={status['credential_configured']}")
    print(f"nasa_firms_adapter_raw_archive_path={envelope.raw_archive_path}")
    print(f"nasa_firms_adapter_archive_exists={status['raw_archive_exists']}")

    if not envelope.events and not envelope.degraded and not live:
        print("nasa_firms_adapter_event_count_empty=true")
        return 1
    if not envelope.raw_archive_path:
        print("nasa_firms_adapter_raw_archive_missing=true")
        return 1

    print("nasa_firms_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
