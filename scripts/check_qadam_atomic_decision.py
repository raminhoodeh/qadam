#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_audits import audit_atomic_decisions


def main() -> int:
    payload = audit_atomic_decisions()
    print(f"qadam_atomic_decision_status={payload['status']}")
    print(f"stored_decision_count={payload['stored_decision_count']}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
