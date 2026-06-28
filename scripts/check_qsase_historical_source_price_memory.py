#!/usr/bin/env python3
"""Validate and write QSASE-3 historical source-price memory artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_historical_source_price_memory import (
    COVERAGE_MAP_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    MEMORY_JSONL_ARTIFACT,
    MISSING_WINDOWS_ARTIFACT,
    POINT_IN_TIME_REPLAY_INDEX_ARTIFACT,
    PRIMARY_ARTIFACT,
    REPLAY_MANIFEST_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_historical_source_price_memory,
    load_historical_source_price_memory,
    validate_historical_source_price_memory,
    validate_negative_historical_memory_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    memory, written, errors = build_and_write_historical_source_price_memory(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        MEMORY_JSONL_ARTIFACT,
        COVERAGE_MAP_ARTIFACT,
        REPLAY_MANIFEST_ARTIFACT,
        POINT_IN_TIME_REPLAY_INDEX_ARTIFACT,
        MISSING_WINDOWS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    records = _read_jsonl(runtime_dir / MEMORY_JSONL_ARTIFACT)
    missing_windows = _read_jsonl(runtime_dir / MISSING_WINDOWS_ARTIFACT)
    loaded = load_historical_source_price_memory(settings)
    if primary.get("generated_at") != memory.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(records) != memory.get("memory_record_count"):
        validation_errors.append("written_memory_record_count_mismatch")
    if len(missing_windows) != memory.get("missing_window_record_count"):
        validation_errors.append("written_missing_window_count_mismatch")
    validation_errors.extend(validate_historical_source_price_memory(loaded))
    validation_errors.extend(validate_negative_historical_memory_probes())

    print(f"artifact={written.get('memory')}")
    print(f"memory_records={written.get('memory_records')}")
    print(f"coverage_map={written.get('coverage_map')}")
    print(f"replay_manifest={written.get('replay_manifest')}")
    print(f"point_in_time_replay_index={written.get('point_in_time_replay_index')}")
    print(f"missing_windows={written.get('missing_windows')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={memory.get('status')}")
    print(f"memory_record_count={memory.get('memory_record_count')}")
    print(f"point_in_time_safe_record_count={memory.get('point_in_time_safe_record_count')}")
    print(f"missing_window_record_count={memory.get('missing_window_record_count')}")
    print(f"backtest_eligible_record_count={memory.get('backtest_eligible_record_count')}")
    print(f"leakage_rejected_record_count={memory.get('leakage_rejected_record_count')}")
    print(
        "paper_growth_trial_calendar_advanced="
        f"{memory.get('calendar_integrity', {}).get('paper_growth_trial_calendar_advanced')}"
    )
    print(
        "paper_proof_ledger_credit_granted="
        f"{memory.get('calendar_integrity', {}).get('paper_proof_ledger_credit_granted')}"
    )
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_historical_source_price_memory_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
