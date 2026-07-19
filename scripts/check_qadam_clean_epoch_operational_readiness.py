#!/usr/bin/env python3
"""Run the final clean-paper-epoch fail-closed certification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_certification import (  # noqa: E402
    build_and_write_clean_epoch_certification,
)


def main() -> int:
    state, checks, errors = build_and_write_clean_epoch_certification()
    cert = state["certification"]
    print(f"clean_epoch_certification_check={checks['status']}")
    print(f"clean_epoch_implementation_complete={cert['implementation_complete']}")
    print(f"clean_epoch_operational_launch_ready={cert['operational_launch_ready']}")
    print(f"clean_epoch_current_waiting_phase={cert['current_waiting_phase']}")
    print(f"clean_epoch_validated_edge_count={cert['validated_edge_count']}")
    print(f"clean_epoch_testing_epoch_archived={cert['testing_epoch_archived']}")
    print(f"clean_epoch_active={cert['clean_epoch_active']}")
    print("clean_epoch_broker_write_count=0")
    for blocker in cert["blockers"]:
        print(
            f"clean_epoch_blocker={blocker['phase_id']}:"
            f"{blocker['reason']}"
        )
    for error in errors:
        print(f"clean_epoch_validation_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
