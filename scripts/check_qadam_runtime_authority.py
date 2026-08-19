#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate CATC runtime authority and supersession rules."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import runtime_dir, write_json_atomic
from orchestrator.qadam_runtime_authority import build_runtime_authority_audit


def main() -> int:
    payload = build_runtime_authority_audit()
    write_json_atomic(
        runtime_dir(Settings.from_env()) / "qadam_runtime_authority_audit.json",
        payload,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
