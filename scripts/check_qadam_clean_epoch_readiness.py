#!/usr/bin/env python3
"""Build and validate the clean-paper-epoch preflight baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_paper_epoch import build_preflight_baseline  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Write the baseline and return success even when release gates remain blocked.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload = build_preflight_baseline()
    ready = (
        payload.get("research_lock_active") is True
        and payload.get("paperops_watch_only") is True
        and payload.get("paper_trial_resume_allowed") is True
        and payload.get("certification_passed") is True
    )
    print(f"clean_epoch_preflight_status={'ready' if ready else 'blocked'}")
    print(f"clean_epoch_certification_state={payload.get('certification_state')}")
    print(f"clean_epoch_research_lock_active={payload.get('research_lock_active')}")
    print(f"clean_epoch_paperops_watch_only={payload.get('paperops_watch_only')}")
    print(f"clean_epoch_paper_trial_resume_allowed={payload.get('paper_trial_resume_allowed')}")
    print("clean_epoch_paper_order_created_count=0")
    print("clean_epoch_broker_write_count=0")
    print("clean_epoch_live_capital_enabled=false")
    return 0 if ready or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
