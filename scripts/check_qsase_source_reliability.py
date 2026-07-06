#!/usr/bin/env python3
"""Validate and write QSASE source reliability artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_source_reliability import (
    DASHBOARD_SUMMARY_ARTIFACT,
    OUTAGE_LOG_ARTIFACT,
    PRIMARY_ARTIFACT,
    RECORDS_ARTIFACT,
    _runtime_dir,
    build_and_write_source_reliability,
    validate_source_reliability,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    settings = Settings.from_env()
    payload, records, written, errors = build_and_write_source_reliability(settings)
    runtime = _runtime_dir(settings)
    validation_errors = list(errors)

    for filename in (PRIMARY_ARTIFACT, RECORDS_ARTIFACT, OUTAGE_LOG_ARTIFACT, DASHBOARD_SUMMARY_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    written_records = _read_jsonl(runtime / RECORDS_ARTIFACT)
    validation_errors.extend(validate_source_reliability(loaded, written_records))
    if len(written_records) != payload.get("source_count"):
        validation_errors.append("written_record_count_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"records={written.get('records')}")
    print(f"outage_log={written.get('outage_log')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"status={payload.get('status')}")
    print(f"source_count={payload.get('source_count')}")
    print(f"required_source_count={payload.get('required_source_count')}")
    print(f"fresh_required_source_count={payload.get('fresh_required_source_count')}")
    print(f"required_source_freshness_ratio={payload.get('required_source_freshness_ratio')}")
    print(f"target_required_source_freshness_passed={payload.get('target_required_source_freshness_passed')}")
    print(f"quorum_contributing_source_count={payload.get('quorum_contributing_source_count')}")
    print(f"outage_count={payload.get('outage_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_allowed={payload.get('broker_write_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    for blocker in payload.get("blockers", []):
        print(f"blocker={blocker}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_source_reliability_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

