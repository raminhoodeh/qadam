#!/usr/bin/env python3
"""Validate and write QSASE-0 governance safety contract artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    ARTIFACT_FILES,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_qsase_governance_safety_contract,
    build_qsase_governance_safety_contract,
    validate_negative_authority_probes,
    validate_qsase_calendar_boundary,
    validate_qsase_governance_safety_contract,
    validate_qsase_proof_boundary,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_written_artifacts(runtime_dir: Path, payload: dict) -> list[str]:
    errors: list[str] = []
    for artifact_key, filename in ARTIFACT_FILES.items():
        path = runtime_dir / filename
        if not path.exists():
            errors.append(f"{filename}_missing")
            continue
        if filename.endswith(".json") and path.stat().st_size == 0:
            errors.append(f"{filename}_empty")
        if artifact_key == "authority_violations" and payload.get("authority_violation_count") == 0:
            if path.read_text(encoding="utf-8") != "":
                errors.append("authority_violations_jsonl_should_be_empty_when_clean")
    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    if primary.get("generated_at") != payload.get("generated_at"):
        errors.append("written_primary_generated_at_mismatch")
    return errors


def run_governance_component_check(component: str) -> int:
    settings = Settings.from_env()
    runtime_dir = _runtime_dir(settings)
    primary_path = runtime_dir / PRIMARY_ARTIFACT
    if primary_path.exists():
        payload = _load_json(primary_path)
    else:
        payload = build_qsase_governance_safety_contract(settings)
    errors = validate_qsase_governance_safety_contract(payload)
    if component == "authority_flags":
        audit = payload.get("authority_flag_audit", {})
        if audit.get("authority_true_count") != 0:
            errors.append("authority_true_count_nonzero")
        if audit.get("authority_violation_count") != 0:
            errors.append("authority_violation_count_nonzero")
    elif component == "proof_boundary":
        errors.extend(validate_qsase_proof_boundary(payload))
    elif component == "calendar_boundary":
        errors.extend(validate_qsase_calendar_boundary(payload))
    elif component == "authority_violations":
        if payload.get("authority_violation_count") != 0:
            errors.append("authority_violations_present")
    else:
        errors.append(f"unknown_component:{component}")

    print(f"component={component}")
    print(f"status={payload.get('status')}")
    print(f"authority_violation_count={payload.get('authority_violation_count')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print(f"qsase_{component}_check=ok")
    return 0


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_qsase_governance_safety_contract(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    validation_errors.extend(_validate_written_artifacts(runtime_dir, payload))
    validation_errors.extend(validate_qsase_proof_boundary(payload))
    validation_errors.extend(validate_qsase_calendar_boundary(payload))
    validation_errors.extend(validate_negative_authority_probes())

    print(f"artifact={written.get('governance_contract')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"authority_flag_count={payload.get('authority_flag_count')}")
    print(f"authority_false_count={payload.get('authority_false_count')}")
    print(f"authority_violation_count={payload.get('authority_violation_count')}")
    print(f"governance_review_queue_count={payload.get('governance_review_queue_count')}")
    print(f"proposal_applied_count={payload.get('proposal_applied_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_governance_safety_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
