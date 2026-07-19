#!/usr/bin/env python3
"""Check current clean-epoch cutover readiness without changing state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_cutover import (  # noqa: E402
    build_clean_epoch_cutover_readiness,
)


def main() -> int:
    result = build_clean_epoch_cutover_readiness(require_service_paused=False)
    print(f"clean_epoch_cutover_readiness={result['status']}")
    print(f"clean_epoch_cutover_ready={str(result['cutover_ready']).lower()}")
    print(f"clean_epoch_validated_edge_count={result['validated_edge_count']}")
    print(f"clean_epoch_real_soak_session_count={result['real_soak_session_count']}")
    print(
        "clean_epoch_clean_broker_preflight_passed="
        f"{str(result['clean_broker_preflight_passed']).lower()}"
    )
    print("clean_epoch_broker_write_count=0")
    for blocker in result.get("blockers", []):
        print(f"clean_epoch_cutover_blocker={blocker}")
    return 0 if result.get("cutover_ready") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
