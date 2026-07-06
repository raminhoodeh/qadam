#!/usr/bin/env python3
"""Validate and write QSASE Phase 8 Akber Filter V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    AKBER_STAGE_RECORDS_V2_ARTIFACT,
    AKBER_V2_ARTIFACT,
    AKBER_V2_DASHBOARD_ARTIFACT,
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
    payload = _load_json(runtime / AKBER_V2_ARTIFACT)
    records = _read_jsonl(runtime / AKBER_STAGE_RECORDS_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (AKBER_V2_ARTIFACT, AKBER_STAGE_RECORDS_V2_ARTIFACT, AKBER_V2_DASHBOARD_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_akber_filter_v2"))
    if len(records) != payload.get("stage_record_count"):
        validation_errors.append("akber_stage_record_count_mismatch")

    print(f"artifact={written.get(AKBER_V2_ARTIFACT)}")
    print(f"records={written.get(AKBER_STAGE_RECORDS_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"stage_record_count={payload.get('stage_record_count')}")
    print(f"pass_count={payload.get('pass_count')}")
    print(f"hold_count={payload.get('hold_count')}")
    print(f"missing_context_count={payload.get('missing_context_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("akber", {}).get("pass_count") != payload.get("pass_count"):
        print("error=summary_akber_pass_count_mismatch")
        return 1
    print("qsase_akber_filter_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
