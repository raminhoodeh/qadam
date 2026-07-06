#!/usr/bin/env python3
"""Validate and write QSASE historical memory completion artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_historical_memory_completion import (
    DASHBOARD_SUMMARY_ARTIFACT,
    FORWARD_WINDOWS_ARTIFACT,
    LEAKAGE_AUDIT_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_historical_memory_completion,
    validate_historical_memory_completion,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def main() -> int:
    settings = Settings.from_env()
    payload, forward_windows, written, errors = build_and_write_historical_memory_completion(settings)
    runtime = _runtime_dir(settings)
    validation_errors = list(errors)

    for filename in (PRIMARY_ARTIFACT, FORWARD_WINDOWS_ARTIFACT, LEAKAGE_AUDIT_ARTIFACT, DASHBOARD_SUMMARY_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    written_windows = _read_jsonl(runtime / FORWARD_WINDOWS_ARTIFACT)
    validation_errors.extend(validate_historical_memory_completion(loaded, written_windows))
    if len(written_windows) != payload.get("memory_record_count"):
        validation_errors.append("written_forward_window_count_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"forward_windows={written.get('forward_windows')}")
    print(f"leakage_audit={written.get('leakage_audit')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"status={payload.get('status')}")
    print(f"memory_record_count={payload.get('memory_record_count')}")
    print(f"complete_forward_window_count={payload.get('complete_forward_window_count')}")
    print(f"missing_forward_window_count={payload.get('missing_forward_window_count')}")
    print(f"complete_forward_window_ratio={payload.get('complete_forward_window_ratio')}")
    print(f"target_complete_forward_window_passed={payload.get('target_complete_forward_window_passed')}")
    print(f"leakage_status={payload.get('leakage_audit', {}).get('status')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    for blocker in payload.get("blockers", []):
        print(f"blocker={blocker}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_historical_memory_completion_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

