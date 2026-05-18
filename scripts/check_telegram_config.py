#!/usr/bin/env python3
"""Validate D8A Telegram config without printing secrets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.telegram_comms import (  # noqa: E402
    FOUNDING_TELEGRAM_MEMBERS,
    TelegramCommunicationsStore,
)

FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
)


def main() -> int:
    settings = Settings.from_env()
    store = TelegramCommunicationsStore(settings=settings)
    members = store.ensure_member_registry()
    status = store.public_status()
    encoded = json.dumps(status, sort_keys=True)

    print("telegram_config_status=" + status["status"])
    print("telegram_config_mode=" + status["mode"])
    print("telegram_config_send_gate=" + status["send_gate"])
    print(f"telegram_config_bot_configured={status['bot_configured']}")
    print(f"telegram_config_default_chat_configured={status['default_chat_configured']}")
    print(f"telegram_config_member_count={status['member_count']}")
    print(f"telegram_config_verified_member_count={status['verified_member_count']}")
    print(f"telegram_config_pending_member_count={status['pending_member_count']}")

    if settings.telegram_enabled:
        print("telegram_config_enabled_unexpected_for_d8a=true")
        return 1
    if not settings.telegram_dry_run:
        print("telegram_config_dry_run_disabled=true")
        return 1
    if len(members) != len(FOUNDING_TELEGRAM_MEMBERS):
        print("telegram_config_member_count_mismatch=true")
        return 1
    if status["mode"] != "dry_run":
        print("telegram_config_mode_not_dry_run=true")
        return 1
    if status["send_gate"] != "disabled":
        print("telegram_config_send_gate_not_disabled=true")
        return 1
    if status["member_count"] != len(FOUNDING_TELEGRAM_MEMBERS):
        print("telegram_config_public_member_count_mismatch=true")
        return 1
    if status["pending_member_count"] < 1 and not status["verified_member_count"]:
        print("telegram_config_member_state_missing=true")
        return 1
    for pattern in FORBIDDEN_PUBLIC_PATTERNS:
        if pattern.search(encoded):
            print("telegram_config_public_secret_leak=true")
            return 1
    if "chat_id" in encoded or "handle" in encoded:
        print("telegram_config_public_identifier_leak=true")
        return 1

    print("telegram_config_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
