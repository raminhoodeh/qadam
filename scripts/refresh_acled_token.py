#!/usr/bin/env python3
"""Refresh ACLED OAuth tokens into the local ignored Qadam secret file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.acled_auth import (  # noqa: E402
    acled_token_input_status,
    refresh_acled_token,
    write_acled_refresh_report,
)
from orchestrator.config import Settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh ACLED tokens without printing token values.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Call ACLED and atomically update the ignored local secret file with the returned tokens.",
    )
    parser.add_argument(
        "--no-password-fallback",
        action="store_true",
        help="Do not fall back to ACLED_EMAIL/ACLED_PASSWORD if the refresh-token grant fails.",
    )
    parser.add_argument(
        "--validate-read",
        action="store_true",
        help="After refresh, run a one-row read-only ACLED data check with the new access token.",
    )
    parser.add_argument(
        "--require-live-read",
        action="store_true",
        help="Fail if --validate-read does not prove the ACLED read endpoint live.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    args = parser.parse_args()

    settings = Settings.from_env()
    status = acled_token_input_status(settings)
    if not args.write:
        print("acled_token_refresh_status=check_only")
        print(f"acled_token_refresh_credential_state={status['credential_state']}")
        print(f"acled_token_refresh_access_token_configured={status['access_token_configured']}")
        print(f"acled_token_refresh_refresh_token_configured={status['refresh_token_configured']}")
        print(f"acled_token_refresh_password_grant_configured={status['password_grant_configured']}")
        print("acled_token_refresh_boundary=Check-only mode performs no provider call and cannot rotate tokens.")
        return 0 if status["credential_state"] != "missing" else 1

    report = refresh_acled_token(
        settings=settings,
        write_secret_file=True,
        allow_password_fallback=not args.no_password_fallback,
        validate_read=args.validate_read,
        timeout_seconds=args.timeout_seconds,
    )
    report_path = write_acled_refresh_report(settings, report)

    print(f"acled_token_refresh_status={report.refresh_status}")
    print(f"acled_token_refresh_grant_type_used={report.grant_type_used or 'none'}")
    print(f"acled_token_refresh_access_token_received={report.access_token_received}")
    print(f"acled_token_refresh_refresh_token_received={report.refresh_token_received}")
    print(f"acled_token_refresh_expires_at={report.expires_at or 'unknown'}")
    print(f"acled_token_refresh_secret_file_updated={report.secret_file_updated}")
    print(f"acled_token_refresh_read_validation_status={report.read_validation_status}")
    print(f"acled_token_refresh_read_validation_status_code={report.read_validation_status_code or 'none'}")
    print(f"acled_token_refresh_report_path={report_path}")
    print(f"acled_token_refresh_boundary={report.boundary}")

    if report.refresh_status != "refreshed":
        return 1
    if args.require_live_read and report.read_validation_status != "live":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
