#!/usr/bin/env python3
"""Certify Qadam's autonomous bounded edge-research lane."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_active_edge_research import (  # noqa: E402
    CERTIFICATION_ARTIFACT,
    CHECK_ARTIFACT,
    build_and_write_active_edge_research_certification,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    payload, checks, errors = build_and_write_active_edge_research_certification(settings)
    runtime = runtime_dir(settings)
    print(f"artifact={runtime / CERTIFICATION_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"operational={checks['operational']}")
    print(
        "automatic_strategy_progression_operational="
        f"{checks['automatic_strategy_progression_operational']}"
    )
    print(f"empirical_state={checks['empirical_state']}")
    print(f"edge_proven={checks['edge_proven']}")
    print(f"blockers={payload['blockers']}")
    print(f"validation_errors={errors}")
    return 0 if checks["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
