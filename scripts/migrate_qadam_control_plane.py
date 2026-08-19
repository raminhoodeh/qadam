#!/usr/bin/env python3
# ruff: noqa: E402
"""Run the idempotent CATC control-plane migration."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_control_plane_migration import import_legacy_control_plane


def main() -> int:
    payload = import_legacy_control_plane()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
