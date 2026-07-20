#!/usr/bin/env python3
"""Build the research-only past-learning and backtest gap-closure overlay."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_learning_backtest_gap_closure import build_all  # noqa: E402


def main() -> int:
    result = build_all()
    certification = result["certification"]
    print(json.dumps(certification, sort_keys=True))
    # Building classified evidence is successful even when the final evidence
    # certification correctly remains blocked. The checker owns fail-closed CI.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
