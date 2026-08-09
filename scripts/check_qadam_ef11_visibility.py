#!/usr/bin/env python3
"""Validate public-safe dashboard and Telegram EF11 projections."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    for name in ("visibility", "telegram"):
        artifact = bundle[name]
        if artifact.get("command_disabled") is not True or artifact.get("live_capital_enabled") is not False:
            errors.append(f"unsafe_ef11_surface:{name}")
    telegram = bundle["telegram"]
    if telegram.get("send_candidate") is True and telegram.get("material_event_type") in {
        None,
        "no_material_change",
    }:
        errors.append("ef11_telegram_non_material_candidate")
    if "Paper research update:" in str(telegram.get("message") or ""):
        errors.append("ef11_telegram_generic_message")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"primary_blocker={bundle['visibility']['primary_blocker']}")
    print(f"telegram_send_candidate={bundle['telegram']['send_candidate']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
