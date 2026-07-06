#!/usr/bin/env python3
"""Validate and write QSASE Phase 7 Strategy Foundry V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase5_to10_completion import (
    REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT,
    STRATEGY_FOUNDRY_V2_ARTIFACT,
    STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT,
    STRATEGY_HYPOTHESES_V2_ARTIFACT,
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
    payload = _load_json(runtime / STRATEGY_FOUNDRY_V2_ARTIFACT)
    hypotheses = _read_jsonl(runtime / STRATEGY_HYPOTHESES_V2_ARTIFACT)
    rejected = _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        STRATEGY_FOUNDRY_V2_ARTIFACT,
        STRATEGY_HYPOTHESES_V2_ARTIFACT,
        REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT,
        STRATEGY_FOUNDRY_V2_DASHBOARD_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_strategy_foundry_v2"))
    if len(hypotheses) != payload.get("strategy_hypothesis_count"):
        validation_errors.append("strategy_hypothesis_count_mismatch")
    if len(rejected) != payload.get("rejected_hypothesis_count"):
        validation_errors.append("rejected_hypothesis_count_mismatch")

    print(f"artifact={written.get(STRATEGY_FOUNDRY_V2_ARTIFACT)}")
    print(f"hypotheses={written.get(STRATEGY_HYPOTHESES_V2_ARTIFACT)}")
    print(f"rejected_hypotheses={written.get(REJECTED_STRATEGY_HYPOTHESES_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"validated_edge_input_count={payload.get('validated_edge_input_count')}")
    print(f"strategy_hypothesis_count={payload.get('strategy_hypothesis_count')}")
    print(f"rejected_hypothesis_count={payload.get('rejected_hypothesis_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("foundry", {}).get("strategy_hypothesis_count") != payload.get("strategy_hypothesis_count"):
        print("error=summary_foundry_count_mismatch")
        return 1
    print("qsase_strategy_foundry_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
