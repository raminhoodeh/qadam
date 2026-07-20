#!/usr/bin/env python3
"""Build the complete QBC artifact set without provider or broker writes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_backtest_completion import build_all  # noqa: E402


def main() -> int:
    result = build_all()
    certification = result["certification"]
    print(json.dumps(certification, sort_keys=True))
    return 0 if certification.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
