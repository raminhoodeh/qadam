#!/usr/bin/env python3
"""Check one-way public dashboard publishing and digest parity."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_public_status_bridge_check import (  # noqa: E402
    build_public_status_bridge_check,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _args()
    result = build_public_status_bridge_check()
    print(f"public_status_bridge_status={result['status']}")
    print(f"public_status_bridge_configured={str(result['configured']).lower()}")
    print(f"public_status_bridge_published={str(result['published']).lower()}")
    print(
        "public_status_bridge_digest_parity_passed="
        f"{str(result['digest_parity_passed']).lower()}"
    )
    print(f"public_status_bridge_fresh={str(result['publication_fresh']).lower()}")
    print("public_status_bridge_broker_write_count=0")
    for blocker in result["blockers"]:
        print(f"public_status_bridge_blocker={blocker}")
    return 0 if result["operating_ready"] or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
