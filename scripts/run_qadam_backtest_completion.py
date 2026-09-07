#!/usr/bin/env python3
"""Retired historical writer: report its replacement without mutating state."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> int:
    print(json.dumps({"status": "retired_read_only_compatibility",
        "replacement": "canonical challenger_research and forward_tournament services",
        "reason": "Historical projections cannot rewrite current governance or hardware validation.",
        "historical_evidence_recertified": False, "runtime_write_count": 0,
        "broker_write_count": 0, "paper_order_allowed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
