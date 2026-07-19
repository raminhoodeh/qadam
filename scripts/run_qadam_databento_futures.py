#!/usr/bin/env python3
"""Quote, submit, resume, and download the bounded Databento futures baseline."""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_databento_futures import (  # noqa: E402
    DatabentoFuturesRequest,
    acquire_databento_futures,
    api_key_from_environment,
    load_client,
    normalize_local_databento_futures,
    verify_local_databento_downloads,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default=DatabentoFuturesRequest().end)
    parser.add_argument("--budget-usd", type=float, default=150.0)
    parser.add_argument("--monthly-limit-usd", type=float, default=150.0)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--verify-local", action="store_true")
    parser.add_argument("--normalize", action="store_true")
    parser.add_argument("--wait-timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    if args.verify_local or args.normalize:
        state: dict[str, object] = {}
        errors: list[str] = []
        if args.verify_local:
            state, errors = verify_local_databento_downloads()
            print(f"local_verification_status={state.get('status')}")
            print(f"verified_file_count={state.get('file_count')}")
        if args.normalize and not errors:
            state, errors = normalize_local_databento_futures()
            print(f"normalization_status={state.get('status')}")
            print(f"normalized_row_count={state.get('row_count')}")
            print(f"normalized_partition_count={state.get('partition_count')}")
            print(f"roll_count={state.get('roll_count')}")
        print(f"validation_error_count={len(errors)}")
        for error in errors:
            print(f"error={error}")
        return 1 if errors else 0

    key = api_key_from_environment()
    if not key:
        key = getpass("Databento API key (not stored): ").strip()
    request = DatabentoFuturesRequest(
        start=args.start,
        end=args.end,
        budget_usd=args.budget_usd,
        monthly_limit_usd=args.monthly_limit_usd,
        wait_timeout_seconds=max(30, args.wait_timeout_seconds),
    )
    state, errors = acquire_databento_futures(
        load_client(key),
        request,
        submit=args.submit,
        wait=args.wait,
        download=args.download,
    )
    print(f"status={state.get('status')}")
    print(f"quote_total_usd={state.get('quote', {}).get('total_usd')}")
    print(f"within_budget={state.get('quote', {}).get('within_budget')}")
    print(f"job_count={len(state.get('jobs', {}))}")
    print(f"file_count={state.get('file_count')}")
    print(f"credential_persisted={state.get('credential_persisted')}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
