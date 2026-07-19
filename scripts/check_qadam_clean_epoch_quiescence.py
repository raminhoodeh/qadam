#!/usr/bin/env python3
"""Report whether Qadam is paused at a safe cutover checkpoint."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_quiescence import (  # noqa: E402
    build_and_write_clean_epoch_quiescence,
)


def main() -> int:
    payload, receipt, errors = build_and_write_clean_epoch_quiescence()
    print(f"clean_epoch_quiescence_status={payload['status']}")
    print(f"clean_epoch_quiescent={str(payload['quiescent']).lower()}")
    print(f"clean_epoch_pause_receipt={receipt['status']}")
    for blocker in payload["blockers"]:
        print(f"clean_epoch_quiescence_blocker={blocker}")
    for error in errors:
        print(f"clean_epoch_quiescence_error={error}")
    return 0 if not errors and payload["quiescent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
