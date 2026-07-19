#!/usr/bin/env python3
"""Build and validate OR-14 deterministic portfolio risk state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_portfolio_risk_engine import (  # noqa: E402
    CHECK_ARTIFACT,
    POLICY_ARTIFACT,
    PROPOSALS_ARTIFACT,
    REJECTIONS_ARTIFACT,
    RISK_STATE_ARTIFACT,
    STRESS_TEST_ARTIFACT,
    build_and_write_portfolio_risk_engine,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_portfolio_risk_engine(settings)
    for name in (
        POLICY_ARTIFACT,
        RISK_STATE_ARTIFACT,
        PROPOSALS_ARTIFACT,
        STRESS_TEST_ARTIFACT,
        REJECTIONS_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "implementation_complete",
        "phase_acceptance_ready",
        "policy_version",
        "absolute_trade_ceiling_usd",
        "portfolio_status",
        "position_count",
        "hypothesis_count",
        "proposal_count",
        "rejection_count",
        "historical_portfolio_simulation_status",
        "historical_portfolio_simulation_eligible_count",
        "forward_shadow_portfolio_simulation_status",
        "forward_shadow_portfolio_simulation_eligible_count",
        "tail_stress_gate_passed",
        "risk_approval_created_count",
        "execution_approval_created_count",
        "paper_order_created_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
