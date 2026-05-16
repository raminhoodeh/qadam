#!/usr/bin/env python3
"""Check the FRED read-only macro source adapter path."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters import FREDAdapter, fred_adapter_status


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def _csv_arg(prefix: str) -> tuple[str, ...]:
    value = _arg_value(prefix)
    if not value:
        return ()
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


async def main() -> int:
    live = "--live" in sys.argv
    series_ids = _csv_arg("--series=")
    observation_start = _arg_value("--observation-start=")
    limit = int(_arg_value("--limit=") or "45")
    alert_arg = _arg_value("--alert-on-sigma=")
    alert_on_sigma = float(alert_arg) if alert_arg else None
    adapter = FREDAdapter()

    try:
        envelope = (
            await adapter.fetch_live(
                series_ids=series_ids,
                observation_start=observation_start,
                limit=limit,
                alert_on_sigma=alert_on_sigma,
            )
            if live
            else adapter.fetch_sample(series_ids=series_ids, alert_on_sigma=alert_on_sigma)
        )
    except Exception as exc:  # noqa: BLE001 - adapter check should make failures explicit
        print("fred_adapter_status=failed")
        print(f"fred_adapter_error_type={exc.__class__.__name__}")
        print(f"fred_adapter_error={exc!r}")
        return 1

    status = fred_adapter_status()
    print("fred_adapter_status=ok")
    print(f"fred_adapter_mode={'live_read_only' if live else 'sample'}")
    print(f"fred_adapter_source={envelope.source}")
    print(f"fred_adapter_event_count={len(envelope.events)}")
    print(f"fred_adapter_degraded={envelope.degraded}")
    print(f"fred_adapter_degraded_reason={envelope.degraded_reason}")
    print(f"fred_adapter_raw_archive_path={envelope.raw_archive_path}")
    print(f"fred_adapter_archive_exists={status['raw_archive_exists']}")

    if not envelope.events and not envelope.degraded and alert_on_sigma is None:
        print("fred_adapter_event_count_empty=true")
        return 1
    if not envelope.raw_archive_path:
        print("fred_adapter_raw_archive_missing=true")
        return 1

    print("fred_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
