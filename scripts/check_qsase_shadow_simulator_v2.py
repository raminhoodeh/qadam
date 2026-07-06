#!/usr/bin/env python3
"""Validate and write QSASE Phase 9 Shadow Simulator V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    SHADOW_COUNTERFACTUALS_V2_ARTIFACT,
    SHADOW_REJECTIONS_V2_ARTIFACT,
    SHADOW_RESULTS_V2_ARTIFACT,
    SHADOW_V2_ARTIFACT,
    SHADOW_V2_DASHBOARD_ARTIFACT,
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
    payload = _load_json(runtime / SHADOW_V2_ARTIFACT)
    results = _read_jsonl(runtime / SHADOW_RESULTS_V2_ARTIFACT)
    counterfactuals = _read_jsonl(runtime / SHADOW_COUNTERFACTUALS_V2_ARTIFACT)
    rejections = _read_jsonl(runtime / SHADOW_REJECTIONS_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        SHADOW_V2_ARTIFACT,
        SHADOW_RESULTS_V2_ARTIFACT,
        SHADOW_COUNTERFACTUALS_V2_ARTIFACT,
        SHADOW_REJECTIONS_V2_ARTIFACT,
        SHADOW_V2_DASHBOARD_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_shadow_simulator_v2"))
    if len(results) != payload.get("shadow_result_count"):
        validation_errors.append("shadow_result_count_mismatch")
    if len(counterfactuals) != payload.get("counterfactual_count"):
        validation_errors.append("shadow_counterfactual_count_mismatch")
    if len(rejections) != payload.get("shadow_rejection_count"):
        validation_errors.append("shadow_rejection_count_mismatch")

    print(f"artifact={written.get(SHADOW_V2_ARTIFACT)}")
    print(f"results={written.get(SHADOW_RESULTS_V2_ARTIFACT)}")
    print(f"counterfactuals={written.get(SHADOW_COUNTERFACTUALS_V2_ARTIFACT)}")
    print(f"rejections={written.get(SHADOW_REJECTIONS_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"shadow_result_count={payload.get('shadow_result_count')}")
    print(f"counterfactual_count={payload.get('counterfactual_count')}")
    print(f"shadow_support_count={payload.get('shadow_support_count')}")
    print(f"shadow_rejection_count={payload.get('shadow_rejection_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("shadow", {}).get("shadow_support_count") != payload.get("shadow_support_count"):
        print("error=summary_shadow_support_count_mismatch")
        return 1
    print("qsase_shadow_simulator_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
