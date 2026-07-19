#!/usr/bin/env python3
"""Publish the latest validated public-safe status through the one-way bridge."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_public_status_publisher import publish_public_status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-configured", action="store_true")
    args = parser.parse_args()
    receipt = publish_public_status(require_configured=args.require_configured)
    print(f"public_status_publish_status={receipt['status']}")
    print(f"public_status_published={receipt['published']}")
    print(f"public_status_reason={receipt['reason']}")
    return 0 if receipt["status"] in {"published", "disabled_not_configured"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
