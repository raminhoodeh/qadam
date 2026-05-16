#!/usr/bin/env python3
"""Run the source heartbeat once or on an interval."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.source_health import run_source_heartbeat


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def _run_once() -> None:
    result = run_source_heartbeat()
    summary = result["summary"]
    print(
        "source_heartbeat_completed "
        f"source_count={summary['source_count']} "
        f"promoted={summary['promoted_adapter_count']} "
        f"missing_credentials={summary['missing_credential_source_count']} "
        f"map={result['data_environment_map_path']}",
        flush=True,
    )


def main() -> int:
    interval_arg = _arg_value("--interval-seconds=")
    if not interval_arg or "--once" in sys.argv:
        _run_once()
        return 0

    interval = max(30, int(interval_arg))
    while True:
        _run_once()
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
