#!/usr/bin/env python3
"""Build the dashboard-safe research progression health contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_research_progression_health import (  # noqa: E402
    build_and_write_research_progression_health,
)


def main() -> int:
    payload, checks, errors = build_and_write_research_progression_health(
        Settings.from_env()
    )
    print(f"status={checks['status']}")
    print(f"progression_state={payload['status']}")
    print(f"material_progress_detected={payload['material_progress_detected']}")
    print(
        "fresh_provider_backed_source_count="
        f"{payload['source_truth']['fresh_provider_backed_count']}"
    )
    print(
        "active_strategy_source_failure_count="
        f"{payload['source_truth']['active_strategy_source_failure_count']}"
    )
    print(
        "validated_edge_count="
        f"{payload['validation_truth']['validated_edge_count']}"
    )
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"validation_error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
