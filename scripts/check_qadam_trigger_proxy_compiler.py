#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_audits import audit_trigger_and_proxy_compiler


def main() -> int:
    payload = audit_trigger_and_proxy_compiler()
    print(f"qadam_trigger_proxy_compiler_status={payload['status']}")
    print(f"conversion_defect_count={payload['conversion_defect_count']}")
    print(f"mapping_defect_count={payload['mapping_defect_count']}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
