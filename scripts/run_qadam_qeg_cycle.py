#!/usr/bin/env python3
"""Run one ordered, resumable QEG research cycle without execution authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import QEG_CYCLE_ARTIFACT, qeg_authority

OPERATIONAL_CHECKS = (
    "scripts/check_qadam_temporal_graph_ingestion.py",
    "scripts/check_qadam_experiment_memory.py",
    "scripts/check_qadam_graph_research_fanout.py",
    "scripts/check_qadam_graph_pattern_discovery.py",
    "scripts/check_qadam_actionability_queue.py",
    "scripts/check_qadam_graph_experiment_bridge.py",
    "scripts/check_qadam_graph_quantum_challenger.py",
    "scripts/check_qadam_strategy_foundry_v4.py",
    "scripts/check_qadam_paper_strategy_admission.py",
    "scripts/check_qadam_graph_active_discovery.py",
)

FULL_PREFIX_CHECKS = (
    "scripts/check_qadam_qeg_baseline.py",
    "scripts/check_qadam_temporal_graph_contracts.py",
    "scripts/check_qadam_temporal_graph_store.py",
    "scripts/check_qadam_claim_reference_registry.py",
)


def _run(script: str, *, timeout_seconds: int = 900) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        (str(ROOT / ".venv/bin/python"), str(ROOT / script)),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "script": script,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 6),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def run_cycle(*, full: bool = False, settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    generated_at = now_iso()
    checks = (*FULL_PREFIX_CHECKS, *OPERATIONAL_CHECKS) if full else OPERATIONAL_CHECKS
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for script in checks:
        try:
            result = _run(script)
        except subprocess.TimeoutExpired:
            result = {
                "script": script,
                "returncode": 124,
                "duration_seconds": 900,
                "stdout_tail": "",
                "stderr_tail": "qeg_cycle_step_timeout",
            }
        results.append(result)
        if result["returncode"] != 0:
            errors.append(f"qeg_cycle_step_failed:{script}")
            break
    payload = {
        "schema_version": "qadam_qeg_cycle.v1",
        "artifact_type": "qadam_qeg_cycle_summary",
        "generated_at": generated_at,
        "completed_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "mode": "full_rebuild" if full else "operational_incremental",
        "ordered_step_count": len(checks),
        "completed_step_count": sum(row["returncode"] == 0 for row in results),
        "results": results,
        "errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "canonical_paperops_invoked": False,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime_dir(active) / QEG_CYCLE_ARTIFACT, payload)
    return payload, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--operational", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args()
    payload, errors = run_cycle(full=args.full)
    print(f"status={payload['status']}")
    print(f"mode={payload['mode']}")
    print(f"completed_step_count={payload['completed_step_count']}")
    print(f"paper_order_created_count={payload['paper_order_created_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
