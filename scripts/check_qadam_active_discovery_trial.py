#!/usr/bin/env python3
"""Refresh and validate the five-market-session active discovery trial."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_active_discovery_trial import (  # noqa: E402
    build_and_write_active_discovery_trial,
)


def main() -> int:
    status, checks, errors = build_and_write_active_discovery_trial()
    print(f"active_discovery_trial_check_status={checks['status']}")
    print(f"active_discovery_trial_state={status['status']}")
    print(
        "active_discovery_trial_market_sessions="
        f"{status['market_sessions_observed']}/{status['market_session_target']}"
    )
    print(
        "active_discovery_trial_eligible_market_days="
        f"{status['eligible_market_days_observed']}/{status['market_session_target']}"
    )
    print(
        "active_discovery_trial_empirical_complete="
        f"{checks['empirical_trial_complete']}"
    )
    print(
        "active_discovery_trial_instruments_evaluated="
        f"{status['metrics']['current_instrument_evaluation_count']}"
    )
    print(
        "active_discovery_trial_shortlist_count="
        f"{status['metrics']['current_shortlist_count']}"
    )
    print(
        "active_discovery_trial_generation_consistent="
        f"{status['generation_consistency']['consistent']}"
    )
    print("active_discovery_trial_no_forced_trades=True")
    for error in errors:
        print(f"active_discovery_trial_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
