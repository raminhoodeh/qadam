#!/usr/bin/env python3
"""Build and validate EF11 provider-backed market-session truth."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_market_session_truth import build_and_write_market_clock_truth  # noqa: E402


def main() -> int:
    truth, checks, errors = build_and_write_market_clock_truth()
    print(f"status={checks['status']}")
    print(f"session_phase={truth['session_phase']}")
    print(f"provider_fresh={truth['provider_fresh']}")
    print(f"actionable_for_conversion={truth['actionable_for_conversion']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
