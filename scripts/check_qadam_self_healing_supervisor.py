#!/usr/bin/env python3
"""Validate Qadam's safe self-healing supervisor artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_self_healing_supervisor import (
    PRIMARY_ARTIFACT,
    QUARANTINE_ARTIFACT,
    REPAIR_REQUESTS_ARTIFACT,
    _runtime_dir,
    build_and_write_self_healing_state,
    validate_self_healing,
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
    payload, written, errors = build_and_write_self_healing_state(settings, perform_refresh=True)
    runtime = _runtime_dir(settings)
    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    quarantine = _load_json(runtime / QUARANTINE_ARTIFACT)
    repair_requests = _read_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT)
    validation_errors = list(errors)

    for filename in (PRIMARY_ARTIFACT, QUARANTINE_ARTIFACT, REPAIR_REQUESTS_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_self_healing(loaded, repair_requests))
    if len(repair_requests) != loaded.get("repair_request_tier", {}).get("repair_request_count"):
        validation_errors.append("repair_request_count_mismatch")
    if len(quarantine.get("records", [])) != loaded.get("quarantine_tier", {}).get("quarantine_record_count"):
        validation_errors.append("quarantine_record_count_mismatch")
    if loaded.get("self_healing_passed") is not True:
        validation_errors.append("self_healing_not_passed")

    print(f"artifact={written.get('primary')}")
    print(f"quarantine={written.get('quarantine')}")
    print(f"repair_requests={written.get('repair_requests')}")
    print(f"status={loaded.get('status')}")
    print(f"self_healing_passed={loaded.get('self_healing_passed')}")
    print(f"refresh_success_count={loaded.get('refresh_tier', {}).get('refresh_success_count')}")
    print(f"refresh_failure_count={loaded.get('refresh_tier', {}).get('refresh_failure_count')}")
    print(f"quarantine_record_count={loaded.get('quarantine_tier', {}).get('quarantine_record_count')}")
    print(f"source_quorum_protected={loaded.get('quarantine_tier', {}).get('source_quorum_protected')}")
    print(f"repair_request_count={loaded.get('repair_request_tier', {}).get('repair_request_count')}")
    print(f"critical_repair_request_count={loaded.get('repair_request_tier', {}).get('critical_repair_request_count')}")
    print(f"paper_order_created_count={loaded.get('paper_order_created_count')}")
    print(f"broker_write_count={loaded.get('broker_write_count')}")
    print(f"proof_credit_allowed={loaded.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={loaded.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if payload.get("generated_at") != loaded.get("generated_at"):
        print("error=written_generated_at_mismatch")
        return 1
    print("qadam_self_healing_supervisor_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
