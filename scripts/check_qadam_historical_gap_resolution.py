#!/usr/bin/env python3
"""Build and validate the clean-epoch historical gap-resolution contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_historical_gap_resolution import (  # noqa: E402
    build_and_write_historical_gap_resolution,
)


def main() -> int:
    state, checks, errors = build_and_write_historical_gap_resolution()
    resolution = state["resolution"]
    recert = state["recertification"]
    print(f"historical_gap_resolution_status={checks['status']}")
    print(
        "historical_gap_provider_partitions="
        f"{resolution['provider_partition_state']['total']}"
    )
    print(
        "historical_gap_provider_partitions_remaining="
        f"{resolution['provider_partition_state']['remaining']}"
    )
    print(
        "historical_gap_legacy_missing_visible="
        f"{resolution['legacy_grid_state']['missing_or_ineligible_count']}"
    )
    print(
        "historical_gap_provider_forward_windows="
        f"{resolution['provider_alignment_state']['eligible_forward_window_count']}"
    )
    print(f"historical_gap_validated_edge_count={recert['validated_edge_count']}")
    print(
        "historical_gap_paper_operator_edge_gate_passed="
        f"{str(recert['paper_operator_edge_gate_passed']).lower()}"
    )
    for error in errors:
        print(f"historical_gap_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
