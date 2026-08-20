#!/usr/bin/env python3
"""Build and validate layered market judgment and activity-quality artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_layered_market_judgment import (  # noqa: E402
    build_and_write_layered_market_judgment,
)


def main() -> int:
    _state, checks, errors = build_and_write_layered_market_judgment()
    print(f"qadam_layered_market_judgment_status={checks['status']}")
    print(f"implementation_ready={checks['implementation_ready']}")
    print(f"observation_ready={checks['observation_ready']}")
    print(f"judgment_count={checks['judgment_count']}")
    print(f"uncertainty_action_count={checks['uncertainty_action_count']}")
    print(f"delayed_entry_count={checks['delayed_entry_count']}")
    print(f"activity_health={checks['activity_health']}")
    print(f"canary_session_count={checks['canary_session_count']}")
    print(f"canary_session_target={checks['canary_session_target']}")
    print("paper_only=True")
    print("live_capital_enabled=False")
    for error in errors:
        print(f"qadam_layered_market_judgment_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
