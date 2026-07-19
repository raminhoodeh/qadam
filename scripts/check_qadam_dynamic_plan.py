#!/usr/bin/env python3
"""Validate DP-0 controlled dynamic-plan governance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_dynamic_plan import (  # noqa: E402
    CHECK_ARTIFACT,
    PHASE_EVIDENCE_ARTIFACT,
    PLAN_STATE_ARTIFACT,
    build_plan_drift,
    initialize_dynamic_plan,
    record_phase_result,
    refresh_dynamic_status,
    validate_dynamic_plan_state,
    validate_negative_dynamic_plan_probes,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    write_json_atomic,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    rf0_checker = runtime / "qadam_refactor_baseline_checks.json"
    rf0_payload = read_json(rf0_checker)
    errors: list[str] = []
    if rf0_payload.get("status") != "passed":
        errors.append("rf0_checker_not_passed")
    else:
        initialize_dynamic_plan(settings)
        record_phase_result("RF-0", rf0_checker, settings=settings)
        refresh_dynamic_status(settings)
    errors.extend(validate_dynamic_plan_state(settings))
    errors.extend(validate_negative_dynamic_plan_probes(settings))
    drift = build_plan_drift(settings)
    if drift.get("drift_detected") is True:
        errors.extend(drift.get("drift_reasons", []))
    errors = unique_errors(errors)
    check = {
        "schema_version": "qadam_dynamic_plan_checks.v1",
        "artifact_type": "qadam_dynamic_plan_checks",
        "phase_id": "DP-0",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "negative_probe_count": 4,
        "normative_edits_automatic": False,
        "phase_evidence_artifact": f"data/runtime/{PHASE_EVIDENCE_ARTIFACT}",
        "plan_state_artifact": f"data/runtime/{PLAN_STATE_ARTIFACT}",
        "drift_status": drift.get("status"),
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, check)
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"plan_state_artifact={runtime / PLAN_STATE_ARTIFACT}")
    print(f"status={check['status']}")
    print(f"drift_status={check['drift_status']}")
    print(f"automatic_normative_edits={check['normative_edits_automatic']}")
    print(f"broker_write_allowed={check['authority']['broker_write_allowed']}")
    print(f"live_capital_enabled={check['authority']['live_capital_enabled']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_dynamic_plan_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
