#!/usr/bin/env python3
"""Run the Phase 1 source-adapter spine in deterministic test mode."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.ingestion import TestIngestionStore, run_test_ingestion
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


def main() -> int:
    settings = Settings.from_env()
    limit = None if "--all" in sys.argv else 5
    store = TestIngestionStore(ROOT / settings.runtime_dir / "foundation_check_test_ingestion.jsonl", settings)
    event_log = EventLog(ROOT / settings.runtime_dir / "foundation_check_ingestion_event_log.jsonl", echo=False)
    result = run_test_ingestion(limit=limit, store=store, event_log=event_log)

    print(f"test_ingestion_status={result['status']}")
    print(f"test_ingestion_mode={result['mode']}")
    print(f"test_ingestion_selected_count={result['selected_count']}")
    print(f"test_ingestion_expected_source_count={result['expected_source_count']}")
    print(f"test_ingestion_deferred_count={result['deferred_count']}")
    print(f"test_ingestion_store_status={result['store']['status']}")
    print(f"test_ingestion_event_log_status={result['event_log']['status']}")

    if result["status"] != "ok":
        print("test_ingestion_not_ok=true")
        return 1
    if result["expected_source_count"] != EXPECTED_SOURCE_COUNT:
        print("test_ingestion_source_count_mismatch=true")
        return 1
    if result["selected_count"] < 1:
        print("test_ingestion_selected_count_empty=true")
        return 1
    if result["store"]["status"] != "ok" or result["event_log"]["status"] != "ok":
        print("test_ingestion_store_or_event_log_not_ok=true")
        return 1

    print("test_ingestion_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
