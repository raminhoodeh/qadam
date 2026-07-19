#!/usr/bin/env python3
"""Refresh and validate Phase 12 clean-epoch operating discipline."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_operating import (  # noqa: E402
    build_and_write_clean_epoch_operating_status,
)


def main() -> int:
    payload, checks, errors = build_and_write_clean_epoch_operating_status()
    print(f"clean_epoch_operating_check={checks['status']}")
    print(f"clean_epoch_operating_implementation_ready={checks['implementation_ready']}")
    print(f"clean_epoch_operating_status={payload['status']}")
    print(f"clean_epoch_post_launch_monitoring_active={payload['post_launch_monitoring_active']}")
    print(f"clean_epoch_current_lineage_count={payload['current_epoch_lineage_count']}")
    print(f"clean_epoch_proof_eligible_count={payload['proof_eligible_count']}")
    for error in errors:
        print(f"clean_epoch_operating_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
