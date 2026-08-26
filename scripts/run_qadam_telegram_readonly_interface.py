#!/usr/bin/env python3
"""Run one fast, shared-rail Telegram query poll for Qadam."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_telegram_readonly_interface import (  # noqa: E402
    announce_readonly_interface,
    register_readonly_commands,
    validate_interface_status,
    write_interface_status,
)
from orchestrator.telegram_inbound_intake import poll_telegram_inbound_updates  # noqa: E402


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--register-commands",
        action="store_true",
        help="Register the read-only command menu for the configured group before polling.",
    )
    parser.add_argument(
        "--announce",
        action="store_true",
        help="Send one deduplicated interface-ready note to the configured group.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    settings = Settings.from_env()
    registration = register_readonly_commands(settings=settings) if args.register_commands else None
    poll_result = poll_telegram_inbound_updates(settings=settings)
    status = write_interface_status(
        poll_result,
        settings=settings,
        registration_result=registration,
    )
    announcement = announce_readonly_interface(settings=settings) if args.announce else None
    errors = validate_interface_status(status)

    print(f"qadam_telegram_readonly_interface_status={status.get('status')}")
    print(f"qadam_telegram_readonly_interface_poll_status={status.get('poll_status')}")
    print(
        "qadam_telegram_readonly_interface_commands_registered="
        f"{str(status.get('commands_registered') is True).lower()}"
    )
    print(f"qadam_telegram_readonly_interface_query_count={status.get('query_count', 0)}")
    print(
        "qadam_telegram_readonly_interface_query_delivery_count="
        f"{status.get('query_delivery_count', 0)}"
    )
    if registration is not None:
        print(f"qadam_telegram_readonly_interface_registration={registration.get('status')}")
    if announcement is not None:
        print(f"qadam_telegram_readonly_interface_announcement={announcement.get('status')}")
    print("qadam_telegram_readonly_interface_paper_order_created_count=0")
    print("qadam_telegram_readonly_interface_broker_write_count=0")
    print("qadam_telegram_readonly_interface_live_capital_enabled=false")
    for error in errors:
        print(f"error={error}")

    hard_failure = (
        bool(errors)
        or status.get("bot_configured") is not True
        or status.get("group_configured") is not True
        or status.get("bot_username_configured") is not True
        or (registration is not None and registration.get("registered") is not True)
    )
    return 1 if hard_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
