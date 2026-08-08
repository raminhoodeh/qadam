#!/usr/bin/env python3
"""Build and validate EF-2 strategy-specific triggers."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_trigger_factory import (  # noqa: E402
    DISLOCATION_ARTIFACT,
    EVENT_ARTIFACT,
    REGIME_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT,
    build_and_write_trigger_factory,
)


def main() -> int:
    runtime = runtime_dir()
    _state, checks, errors = build_and_write_trigger_factory()
    for name in (
        EVENT_ARTIFACT,
        REGIME_ARTIFACT,
        DISLOCATION_ARTIFACT,
        REJECTIONS_ARTIFACT,
        SUMMARY_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "event_trigger_count",
        "active_event_trigger_count",
        "regime_observation_count",
        "active_regime_count",
        "market_dislocation_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
