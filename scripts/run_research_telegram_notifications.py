#!/usr/bin/env python3
"""Preview research notifications, or deliver due notifications with --live."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.qadam_research_telegram import run_research_notifications  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    status = run_research_notifications(live=args.live)
    print(json.dumps(status, indent=2))
    return 0 if status["status"] in {"healthy", "already_running"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
