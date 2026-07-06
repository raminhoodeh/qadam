#!/usr/bin/env python3
"""Validate and write QSASE Phase 6 full-universe pattern search V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    PATTERN_SEARCH_V2_ARTIFACT,
    PATTERN_SEARCH_V2_DASHBOARD_ARTIFACT,
    PATTERN_SEARCH_V2_RECORDS_ARTIFACT,
    PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT,
    _runtime_dir,
    build_and_write_phase5_to10_completion,
    validate_payload,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    settings = Settings.from_env()
    summary, written, errors = build_and_write_phase5_to10_completion(settings)
    runtime = _runtime_dir(settings)
    payload = _load_json(runtime / PATTERN_SEARCH_V2_ARTIFACT)
    records = _read_jsonl(runtime / PATTERN_SEARCH_V2_RECORDS_ARTIFACT)
    rejections = _read_jsonl(runtime / PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        PATTERN_SEARCH_V2_ARTIFACT,
        PATTERN_SEARCH_V2_RECORDS_ARTIFACT,
        PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT,
        PATTERN_SEARCH_V2_DASHBOARD_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_full_universe_pattern_search_v2"))
    if len(records) != payload.get("pattern_record_count"):
        validation_errors.append("pattern_record_count_mismatch")
    if len(rejections) != payload.get("rejection_count"):
        validation_errors.append("pattern_rejection_count_mismatch")

    print(f"artifact={written.get(PATTERN_SEARCH_V2_ARTIFACT)}")
    print(f"records={written.get(PATTERN_SEARCH_V2_RECORDS_ARTIFACT)}")
    print(f"rejections={written.get(PATTERN_SEARCH_V2_REJECTIONS_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"pattern_record_count={payload.get('pattern_record_count')}")
    print(f"validated_for_foundry_count={payload.get('validated_for_foundry_count')}")
    print(f"research_pattern_count={payload.get('research_pattern_count')}")
    print(f"rejection_count={payload.get('rejection_count')}")
    print(f"top_pattern_state={payload.get('top_pattern', {}).get('pattern_state')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("pattern", {}).get("pattern_record_count") != payload.get("pattern_record_count"):
        print("error=summary_pattern_count_mismatch")
        return 1
    print("qsase_pattern_search_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
