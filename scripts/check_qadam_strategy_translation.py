#!/usr/bin/env python3
"""Build and validate EF-3 direction and emerging-strategy translation."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_strategy_foundry_v3 import build_and_write_strategy_foundry_v3  # noqa: E402
from orchestrator.qadam_strategy_translation import (  # noqa: E402
    DIRECTIONS_ARTIFACT,
    FORMATIONS_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT,
    build_and_write_strategy_translation,
)
from orchestrator.qadam_trigger_factory import build_and_write_trigger_factory  # noqa: E402


def main() -> int:
    _trigger_state, _trigger_checks, trigger_errors = build_and_write_trigger_factory()
    state, checks, errors = build_and_write_strategy_translation()
    _foundry_state, foundry_checks, foundry_errors = build_and_write_strategy_foundry_v3()
    all_errors = [*trigger_errors, *errors, *foundry_errors]
    for name in (DIRECTIONS_ARTIFACT, REJECTIONS_ARTIFACT, FORMATIONS_ARTIFACT, SUMMARY_ARTIFACT):
        print(f"artifact={ROOT / 'data' / 'runtime' / name}")
    print(f"status={'passed' if not all_errors else 'blocked'}")
    print(f"direction_resolution_count={checks['direction_resolution_count']}")
    print(f"emerging_strategy_formation_count={checks['emerging_strategy_formation_count']}")
    print(f"foundry_hypothesis_count={foundry_checks['hypothesis_count']}")
    if all_errors:
        for error in all_errors:
            print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
