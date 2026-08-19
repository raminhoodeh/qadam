#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_audits import audit_strategy_learning_alignment


def main() -> int:
    payload = audit_strategy_learning_alignment()
    print(f"qadam_strategy_learning_alignment_status={payload['status']}")
    print(f"validated_edge_count={payload['validated_edge_count']}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
