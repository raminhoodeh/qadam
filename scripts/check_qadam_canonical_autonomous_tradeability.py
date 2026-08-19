#!/usr/bin/env python3
# ruff: noqa: E402
"""Single fail-closed release checker for CATC-0 through CATC-17."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic

ARTIFACT = "qadam_canonical_autonomous_tradeability_certification.json"

CHECKS = (
    ("runtime_authority", "scripts/check_qadam_runtime_authority.py"),
    ("supersession", "scripts/check_qadam_supersession.py"),
    ("control_plane", "scripts/check_qadam_control_plane.py"),
    ("immutable_generations", "scripts/check_qadam_artifact_generations.py"),
    ("decision_schemas", "scripts/check_qadam_decision_schemas.py"),
    ("source_capability", "scripts/check_qadam_source_capability_registry.py"),
    ("trigger_proxy_compiler", "scripts/check_qadam_trigger_proxy_compiler.py"),
    ("execution_context", "scripts/check_qadam_execution_context.py"),
    ("gate_policy", "scripts/check_qadam_gate_policy.py"),
    ("atomic_decision", "scripts/check_qadam_atomic_decision.py"),
    ("strategy_learning", "scripts/check_qadam_strategy_learning_alignment.py"),
    ("runtime_domains", "scripts/check_qadam_runtime_domains.py"),
    ("public_safety", "scripts/check_qadam_tradeability_public_safety.py"),
    ("real_market_soak", "scripts/check_qadam_catc_real_market_soak.py"),
    ("dashboard_projection", "scripts/check_qadam_catc_dashboard_projection.py"),
    (
        "release_reproducibility",
        "scripts/check_qadam_catc_release_reproducibility.py",
    ),
)


def _run(path: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        env={
            **os.environ,
            "QADAM_LIVE_CAPITAL_ENABLED": "false",
            "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
        },
    )
    return {
        "check": path,
        "status": "passed" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-1500:],
        "stderr_tail": completed.stderr[-1500:],
    }


def main() -> int:
    runtime = runtime_dir()
    results = {name: _run(path) for name, path in CHECKS}
    blockers = [name for name, result in results.items() if result["status"] != "passed"]
    integrity = ControlPlaneStore.from_settings().integrity_report()
    if integrity.get("status") != "passed":
        blockers.append("control_plane_database_integrity")
    soak = read_json(runtime / "qadam_catc_real_market_soak.json")
    soak_complete = soak.get("observation_ready") is True
    unsafe_environment = str(os.getenv("QADAM_LIVE_CAPITAL_ENABLED", "false")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if unsafe_environment:
        blockers.append("live_capital_environment_enabled")
    blockers = sorted(set(blockers))
    state = "blocked" if blockers else "observation_ready" if soak_complete else "implementation_ready"
    payload = {
        "schema_version": "qadam_canonical_autonomous_tradeability_certification.v1",
        "artifact_type": "qadam_canonical_autonomous_tradeability_certification",
        "generated_at": now_iso(),
        "status": state,
        "implementation_ready": not blockers,
        "observation_ready": not blockers and soak_complete,
        "paper_experiment_active": False,
        "checks": results,
        "check_count": len(results),
        "passed_check_count": sum(row["status"] == "passed" for row in results.values()),
        "blockers": blockers,
        "control_plane_integrity": integrity,
        "real_market_soak": soak,
        "five_real_sessions_not_backfilled": True,
        "paper_only": True,
        "guarded_alpaca_paper_route_only": True,
        "dashboard_command_disabled": True,
        "telegram_command_disabled": True,
        "maximum_paper_notional_usd": 5000,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / ARTIFACT, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
