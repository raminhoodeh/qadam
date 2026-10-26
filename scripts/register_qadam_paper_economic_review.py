#!/usr/bin/env python3
"""Explicitly register the current read-only economic review; never submit orders."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_paper_economic_review import register_review  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", action="store_true", required=True)
    args = parser.parse_args()
    result = register_review(Settings.from_env(), reviewed=args.reviewed)
    print("economic_review_registered=" + result["evaluation_id"])
    print("broker_write_count=0")
    print("automatic_risk_increase_allowed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
