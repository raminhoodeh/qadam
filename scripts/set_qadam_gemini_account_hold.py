"""Explicit operator account hold; never buys credit or rotates credentials."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.config import Settings  # noqa: E402
from orchestrator.research.provider_access import record_gemini_account_hold  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--release-reviewed", action="store_true")
    args = parser.parse_args()
    record = record_gemini_account_hold(Settings.from_env(), reason=args.reason,
                                       release_reviewed=args.release_reviewed)
    print("gemini_account_status=" + record["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
