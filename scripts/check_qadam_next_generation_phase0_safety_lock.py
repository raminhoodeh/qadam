#!/usr/bin/env python3
"""Validate Phase 0 safety lock and runtime quiescence for Qadam next-gen flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_next_generation_safety_lock import (
    DASHBOARD_SUMMARY_ARTIFACT,
    LOCK_ARTIFACT,
    PHASE0_ARTIFACT,
    _runtime_dir,
    build_phase0_status,
    validate_negative_phase0_probes,
    validate_phase0_status,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-runtime-hours", type=int, default=120)
    args = parser.parse_args()

    settings = Settings.from_env()
    payload = build_phase0_status(
        settings=settings,
        max_runtime_hours=args.max_runtime_hours,
        write_lock=True,
    )
    runtime = _runtime_dir(settings)
    loaded = _load_json(runtime / PHASE0_ARTIFACT)
    lock = _load_json(runtime / LOCK_ARTIFACT)
    dashboard_summary = _load_json(runtime / DASHBOARD_SUMMARY_ARTIFACT)

    validation_errors = []
    validation_errors.extend(validate_phase0_status(loaded))
    validation_errors.extend(validate_negative_phase0_probes())
    if loaded.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("phase0_written_generated_at_mismatch")
    if lock.get("status") != "active":
        validation_errors.append("long_backtest_lock_not_written_active")
    if dashboard_summary.get("long_backtest_lock_active") is not True:
        validation_errors.append("dashboard_summary_lock_not_active")
    if dashboard_summary.get("paperops_watch_only_mode") is not True:
        validation_errors.append("dashboard_summary_watch_only_missing")

    print(f"artifact={runtime / PHASE0_ARTIFACT}")
    print(f"lock_artifact={runtime / LOCK_ARTIFACT}")
    print(f"dashboard_summary_artifact={runtime / DASHBOARD_SUMMARY_ARTIFACT}")
    print(f"status={loaded.get('status')}")
    print(f"qadam_long_backtest_lock_active={loaded.get('long_backtest_lock_active')}")
    print(f"paperops_watch_only_mode={loaded.get('paperops_watch_only_mode')}")
    print(f"dashboard_backtest_running_state={loaded.get('dashboard_backtest_running_state')}")
    print(f"phase_1_backfill_started={loaded.get('phase_1_backfill_started')}")
    print(f"process_probe_status={loaded.get('process_probe', {}).get('status')}")
    print(f"unsafe_running_process_count={loaded.get('process_probe', {}).get('unsafe_running_process_count')}")
    print(f"paper_order_allowed={loaded.get('authority', {}).get('paper_order_allowed')}")
    print(f"broker_write_allowed={loaded.get('authority', {}).get('broker_write_allowed')}")
    print(f"live_capital_enabled={loaded.get('authority', {}).get('live_capital_enabled')}")
    print(f"proof_credit_allowed={loaded.get('authority', {}).get('proof_credit_allowed')}")
    print(f"validation_error_count={len(set(validation_errors))}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qadam_next_generation_phase0_safety_lock_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
