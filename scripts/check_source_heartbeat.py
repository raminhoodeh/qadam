#!/usr/bin/env python3
"""Check the Phase 1C source heartbeat and data environment map."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.source_health import run_source_heartbeat


def main() -> int:
    result = run_source_heartbeat()
    summary = result["summary"]
    print("source_heartbeat_status=ok")
    print(f"source_heartbeat_checked_at={result['checked_at']}")
    print(f"source_heartbeat_source_count={summary['source_count']}")
    print(f"source_heartbeat_expected_source_count={summary['expected_source_count']}")
    print(f"source_heartbeat_promoted_adapter_count={summary['promoted_adapter_count']}")
    print(f"source_heartbeat_deferred_count={summary['deferred_count']}")
    print(f"source_heartbeat_missing_credential_source_count={summary['missing_credential_source_count']}")
    print(f"source_heartbeat_map_path={result['data_environment_map_path']}")
    print(f"source_heartbeat_store_status={result['store']['status']}")

    if summary["source_count"] != summary["expected_source_count"]:
        print("source_heartbeat_count_mismatch=true")
        return 1
    if summary["promoted_adapter_count"] < 4:
        print("source_heartbeat_promoted_adapter_count_too_low=true")
        return 1
    if result["store"]["status"] != "ok":
        print("source_heartbeat_store_not_ok=true")
        return 1

    print("source_heartbeat_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
