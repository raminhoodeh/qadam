#!/usr/bin/env python3
"""Validate and write QSASE-1 self-model artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_self_model import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_qsase_self_model,
    validate_negative_self_model_probes,
    validate_qsase_self_model,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_qsase_self_model(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        HISTORY_ARTIFACT,
        EVENTS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")
    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    validation_errors.extend(validate_qsase_self_model(primary))
    validation_errors.extend(validate_negative_self_model_probes())

    print(f"artifact={written.get('self_model')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"staleness_status={payload.get('staleness_status', {}).get('status')}")
    print(f"degraded_component_count={payload.get('degraded_component_count')}")
    print(f"missing_component_count={payload.get('missing_component_count')}")
    print(f"repair_request_count={payload.get('repair_request_count')}")
    print(f"why_not_trading_now={payload.get('why_not_trading_now', {}).get('reason')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_self_model_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
