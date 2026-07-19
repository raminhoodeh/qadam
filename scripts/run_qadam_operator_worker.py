#!/usr/bin/env python3
"""Run one allowlisted resumable OR-18 worker job."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_service import execute_registered_worker  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--receipt-id", required=True)
    args = parser.parse_args()
    try:
        return execute_registered_worker(
            args.service_id,
            args.receipt_id,
            Settings.from_env(),
        )
    except ValueError as exc:
        print("status=blocked")
        print(f"error={exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
