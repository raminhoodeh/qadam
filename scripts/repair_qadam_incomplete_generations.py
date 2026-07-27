#!/usr/bin/env python3
"""Quarantine stale incomplete generation staging directories."""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_artifact_generations import GENERATION_ROOT  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum-age-seconds", type=int, default=3600)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    runtime = runtime_dir()
    root = runtime / GENERATION_ROOT
    quarantine = runtime / "archive" / "incomplete-generations"
    stale = []
    cutoff = time.time() - max(60, args.minimum_age_seconds)
    for staging in root.glob("*/staging/*") if root.exists() else ():
        if staging.is_dir() and staging.stat().st_mtime < cutoff:
            stale.append(staging)
    moved = []
    if args.execute:
        quarantine.mkdir(parents=True, exist_ok=True)
        for path in stale:
            destination = quarantine / (
                f"{path.parent.parent.name}-{path.name}-"
                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            )
            shutil.move(str(path), destination)
            moved.append(str(destination))
    print(f"qadam_incomplete_generation_count={len(stale)}")
    print(f"qadam_incomplete_generation_quarantined_count={len(moved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
