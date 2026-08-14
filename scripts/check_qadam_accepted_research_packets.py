#!/usr/bin/env python3
"""Validate persisted accepted research packets and their critic lineage."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_agent_compiler import build_and_write_agent_compiler_checks


def main() -> int:
    checks, errors = build_and_write_agent_compiler_checks()
    result = {
        "status": "passed" if not errors else "blocked",
        "accepted_packet_count": checks.get("accepted_packet_count", 0),
        "critic_receipt_count": checks.get("critic_receipt_count", 0),
        "self_approval_allowed": checks.get("self_approval_allowed"),
        "validation_errors": errors,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
