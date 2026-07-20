#!/usr/bin/env python3
"""Fail-closed PLBG end-to-end certification checker."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_learning_backtest_gap_closure import (  # noqa: E402
    build_certification,
)


def main() -> int:
    certification = build_certification()
    print(json.dumps(certification, sort_keys=True))
    return 0 if certification.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
