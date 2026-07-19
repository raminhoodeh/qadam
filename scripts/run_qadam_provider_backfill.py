#!/usr/bin/env python3
"""Run explicit, resumable OR-3 provider acquisition partitions."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_provider_backfill import BackfillOptions, run_provider_backfill  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--provider-terms-reviewed", action="store_true")
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--sleep-between-calls", type=float, default=0.5)
    args = parser.parse_args()
    options = BackfillOptions(
        dry_run=args.dry_run,
        resume=args.resume,
        allow_network=args.allow_network,
        provider_terms_reviewed=args.provider_terms_reviewed,
        start_year=args.start_year,
        end_year=args.end_year or BackfillOptions().end_year,
        max_jobs=args.max_jobs,
        sleep_between_calls=args.sleep_between_calls,
    )
    coverage, _checks, errors = run_provider_backfill(Settings.from_env(), options=options)
    print(f"status={coverage.get('status')}")
    print(f"completed_partition_count={coverage.get('completed_partition_count')}")
    print(f"remaining_partition_count={coverage.get('remaining_partition_count')}")
    print(f"provider_row_count={coverage.get('provider_row_count')}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
