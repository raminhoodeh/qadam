#!/usr/bin/env python3
"""Build and validate EF-9 dashboard and notification truth."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_evidence_fit_visibility import (  # noqa: E402
    build_and_write_evidence_fit_visibility,
)


def main() -> int:
    state, checks, errors = build_and_write_evidence_fit_visibility()
    dashboard = state["dashboard"]
    print(f"qadam_evidence_fit_visibility_status={checks['status']}")
    print(
        "qadam_evidence_fit_visibility_sources="
        f"{dashboard['registered_source_count']}"
    )
    print(
        "qadam_evidence_fit_visibility_instruments="
        f"{dashboard['watched_instrument_count']}"
    )
    print(
        "qadam_evidence_fit_visibility_funnel_stages="
        f"{checks['conversion_stage_count']}"
    )
    print(
        "qadam_evidence_fit_visibility_notification="
        f"{checks['notification_status']}"
    )
    for error in errors:
        print(f"qadam_evidence_fit_visibility_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
