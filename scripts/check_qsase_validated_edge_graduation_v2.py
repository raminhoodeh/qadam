#!/usr/bin/env python3
"""Validate and write QSASE Phase 5 validated-edge graduation V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    EDGE_REJECTIONS_ARTIFACT,
    VALIDATED_EDGE_ARTIFACT,
    VALIDATED_EDGE_DASHBOARD_ARTIFACT,
    VALIDATED_EDGE_RECORDS_ARTIFACT,
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
    payload = _load_json(runtime / VALIDATED_EDGE_ARTIFACT)
    records = _read_jsonl(runtime / VALIDATED_EDGE_RECORDS_ARTIFACT)
    rejections = _read_jsonl(runtime / EDGE_REJECTIONS_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        VALIDATED_EDGE_ARTIFACT,
        VALIDATED_EDGE_RECORDS_ARTIFACT,
        EDGE_REJECTIONS_ARTIFACT,
        VALIDATED_EDGE_DASHBOARD_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_validated_edge_graduation"))
    if len(records) != payload.get("graduation_record_count"):
        validation_errors.append("validated_edge_record_count_mismatch")
    if len(rejections) != payload.get("edge_rejection_count"):
        validation_errors.append("edge_rejection_count_mismatch")

    print(f"artifact={written.get(VALIDATED_EDGE_ARTIFACT)}")
    print(f"records={written.get(VALIDATED_EDGE_RECORDS_ARTIFACT)}")
    print(f"rejections={written.get(EDGE_REJECTIONS_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"input_linear_result_count={payload.get('input_linear_result_count')}")
    print(f"graduation_record_count={payload.get('graduation_record_count')}")
    print(f"validated_edge_count={payload.get('validated_edge_count')}")
    print(f"edge_rejection_count={payload.get('edge_rejection_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    for key, value in payload.get("top_failed_criteria", {}).items():
        print(f"failed_criteria={key}:{value}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("edge", {}).get("validated_edge_count") != payload.get("validated_edge_count"):
        print("error=summary_edge_count_mismatch")
        return 1
    print("qsase_validated_edge_graduation_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
