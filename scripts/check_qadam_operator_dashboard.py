#!/usr/bin/env python3
"""Build and validate OR-17 operator dashboard and communications state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_dashboard import (  # noqa: E402
    CHECK_ARTIFACT,
    COMMUNICATIONS_ARTIFACT,
    FRESHNESS_ARTIFACT,
    TRUTH_AUDIT_ARTIFACT,
    VIEW_MODEL_ARTIFACT,
    build_and_write_operator_dashboard,
)
from orchestrator.qadam_pattern_dashboard_views import (  # noqa: E402
    PATTERN_DISCOVERY_ARTIFACT,
    QUANTUM_REVIEW_ARTIFACT,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_operator_dashboard(settings)
    for name in (
        VIEW_MODEL_ARTIFACT,
        FRESHNESS_ARTIFACT,
        TRUTH_AUDIT_ARTIFACT,
        COMMUNICATIONS_ARTIFACT,
        PATTERN_DISCOVERY_ARTIFACT,
        QUANTUM_REVIEW_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "runtime_state",
        "protected_route_count",
        "portfolio_values_agree",
        "stale_count",
        "missing_count",
        "displayed_pattern_count",
        "duplicate_pattern_count",
        "raw_score_probability_violation_count",
        "telegram_message_ready_count",
        "telegram_live_send_allowed",
        "command_path_enabled",
        "paper_order_created_count",
        "broker_write_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
