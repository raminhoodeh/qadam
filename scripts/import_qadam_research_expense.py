#!/usr/bin/env python3
"""Import one operator-supplied USD bill receipt; no provider or broker calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.research.economics import record_expense  # noqa: E402
from orchestrator.storage.control_plane import ControlPlaneStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="Single JSON receipt; never a credential file")
    args = parser.parse_args()
    if args.receipt.stat().st_size > 16384:
        parser.error("Receipt exceeds 16 KiB")
    receipt = json.loads(args.receipt.read_text())
    inserted = record_expense(ControlPlaneStore.from_settings(Settings.from_env()), receipt)
    print(json.dumps({"status": "recorded" if inserted else "already_recorded", "broker_write_count": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
