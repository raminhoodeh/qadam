#!/usr/bin/env python3
"""Build and validate the RF-0 refactor/dashboard behavior baseline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_refactor_baseline import (  # noqa: E402
    BASELINE_ARTIFACT,
    CHECKS_ARTIFACT,
    DASHBOARD_CONTRACT_ARTIFACT,
    SCOPE_ARTIFACT,
    build_and_write_refactor_baseline,
)


def main() -> int:
    settings = Settings.from_env()
    baseline, checks, errors = build_and_write_refactor_baseline(settings)
    runtime = runtime_dir(settings)
    dashboard = baseline.get("dashboard_contract", {})
    lock = baseline.get("research_lock", {})
    print(f"baseline_artifact={runtime / BASELINE_ARTIFACT}")
    print(f"dashboard_contract_artifact={runtime / DASHBOARD_CONTRACT_ARTIFACT}")
    print(f"scope_artifact={runtime / SCOPE_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECKS_ARTIFACT}")
    print(f"status={checks.get('status')}")
    print(f"root_dirty_file_count={baseline.get('root_worktree', {}).get('dirty_file_count')}")
    print(
        "dashboard_dirty_file_count="
        f"{baseline.get('dashboard_worktree', {}).get('dirty_file_count')}"
    )
    print(f"dashboard_route_count={dashboard.get('route_count')}")
    print(f"legacy_dashboard_checker_debt_count={dashboard.get('legacy_checker_debt_count')}")
    print(f"research_lock_status={lock.get('status')}")
    print(f"paperops_watch_only_mode={lock.get('paperops_watch_only_mode')}")
    print(f"broker_write_allowed={baseline.get('authority', {}).get('broker_write_allowed')}")
    print(f"live_capital_enabled={baseline.get('authority', {}).get('live_capital_enabled')}")
    print(f"proof_credit_allowed={baseline.get('authority', {}).get('proof_credit_allowed')}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_refactor_baseline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
