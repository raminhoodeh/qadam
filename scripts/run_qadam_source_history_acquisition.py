#!/usr/bin/env python3
"""Run bounded OR-3 source-history acquisition from official providers."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_source_history_acquisition import (  # noqa: E402
    SourceHistoryOptions,
    run_source_history_acquisition,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--provider-terms-reviewed", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--sleep-between-calls", type=float, default=0.25)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--classify-deferred", action="store_true")
    args = parser.parse_args()
    result, errors = run_source_history_acquisition(
        Settings.from_env(),
        options=SourceHistoryOptions(
            allow_network=args.allow_network,
            provider_terms_reviewed=args.provider_terms_reviewed,
            resume=not args.no_resume,
            max_jobs=max(0, args.max_jobs),
            timeout_seconds=max(5, args.timeout_seconds),
            sleep_between_calls=max(0.0, args.sleep_between_calls),
            source_keys=tuple(dict.fromkeys(args.source)),
            classify_deferred=args.classify_deferred,
        ),
    )
    from orchestrator.runtime.command import report_work_result
    report_work_result(result, errors)
    print(f"status={result.get('status')}")
    print(f"processed_job_count={result.get('processed_job_count')}")
    print(f"attempted_job_count={result.get('attempted_job_count')}")
    print(f"status_counts={result.get('status_counts')}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
