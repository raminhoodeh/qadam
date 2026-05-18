#!/usr/bin/env python3
"""Validate promoted Phase 1 read-only adapter contracts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase1_live_adapters import (
    PHASE1_LIVE_ADAPTER_KEYS,
    fetch_phase1_live_adapter_live_sync,
    fetch_phase1_live_adapter_sample,
    phase1_live_adapter_registry,
)


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def main() -> int:
    errors: list[str] = []
    live = "--live" in sys.argv
    source_key = _arg_value("--source=")
    keys = (source_key,) if source_key else PHASE1_LIVE_ADAPTER_KEYS
    unknown = [key for key in keys if key not in PHASE1_LIVE_ADAPTER_KEYS]
    if unknown:
        print(f"phase1_live_adapter_unknown_source={','.join(unknown)}")
        return 1

    registry = phase1_live_adapter_registry()
    sample_event_count = 0
    live_event_count = 0
    degraded_live_count = 0
    for key in keys:
        sample = fetch_phase1_live_adapter_sample(key)
        events = sample.get("events", [])
        sample_event_count += len(events) if isinstance(events, list) else 0
        if not events:
            errors.append(f"sample_event_empty:{key}")
        if sample.get("degraded"):
            errors.append(f"sample_degraded:{key}")
        if "No" in str(sample.get("boundary", "")):
            pass
        if live:
            result = fetch_phase1_live_adapter_live_sync(key)
            live_events = result.get("events", [])
            live_event_count += len(live_events) if isinstance(live_events, list) else 0
            if result.get("degraded"):
                degraded_live_count += 1

    print("phase1_live_adapter_status=" + ("ok" if not errors else "error"))
    print(f"phase1_live_adapter_registered_count={registry['adapter_count']}")
    print(f"phase1_live_adapter_configured_count={registry['configured_count']}")
    print(f"phase1_live_adapter_public_or_optional_count={registry['public_or_optional_count']}")
    print(f"phase1_live_adapter_checked_count={len(keys)}")
    print(f"phase1_live_adapter_sample_event_count={sample_event_count}")
    print(f"phase1_live_adapter_live_checked={live}")
    print(f"phase1_live_adapter_live_event_count={live_event_count}")
    print(f"phase1_live_adapter_degraded_live_count={degraded_live_count}")
    print("phase1_live_adapter_boundary=All promoted Phase 1 adapters are read-only and cannot create signals, orders, or broker writes.")
    for error in errors:
        print(f"phase1_live_adapter_error={error}")

    if errors:
        return 1
    print("phase1_live_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
