#!/usr/bin/env python3
"""Send a controlled Qadam Telegram test message without exposing secrets."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.secrets import secret_value  # noqa: E402
from orchestrator.telegram_comms import render_telegram_message  # noqa: E402


TARGET_KEYS = {
    "private": "TELEGRAM_DEFAULT_CHAT_ID",
    "group": "TELEGRAM_GROUP_CHAT_ID",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _delivery_path(settings: Settings) -> Path:
    path = Path(settings.runtime_dir) / "telegram-deliveries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _archive_delivery(settings: Settings, payload: dict[str, object]) -> None:
    with _delivery_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _target_labels(target: str) -> list[str]:
    if target == "both":
        return ["private", "group"]
    return [target]


def _send_message(token: str, chat_id: str, text: str) -> dict[str, object]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a safe Telegram test message.")
    parser.add_argument("--target", choices=("private", "group", "both"), default="group")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call Telegram sendMessage. Without this, only validates the target.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    if not token:
        print("telegram_test_status=missing_bot_token")
        return 1

    title, body = render_telegram_message(
        "source_degraded",
        {
            "title": "Qadam Telegram test",
            "subject": "member communications rail",
            "why_it_matters": "this confirms the bot can reach the selected Qadam chat",
            "evidence": "manual test from local Qadam runtime",
            "block": "notification only; no trade command is available",
        },
    )
    text = f"{title}\n\n{body}"

    targets = _target_labels(args.target)
    missing = [target for target in targets if not secret_value(TARGET_KEYS[target], settings)]
    if missing:
        print("telegram_test_status=missing_target")
        print("telegram_test_missing_targets=" + ",".join(missing))
        return 1

    print("telegram_test_target=" + args.target)
    print("telegram_test_live=" + str(args.live))
    print("telegram_test_targets_configured=" + str(len(targets)))

    if not args.live:
        print("telegram_test_status=dry_run_ok")
        return 0

    failures = 0
    for target in targets:
        chat_id = secret_value(TARGET_KEYS[target], settings)
        assert chat_id is not None
        try:
            response = _send_message(token, chat_id, text)
            ok = bool(response.get("ok"))
            message_id = response.get("result", {}).get("message_id")
            status = "sent" if ok else "failed"
            print(f"telegram_test_{target}_status={status}")
            if message_id is not None:
                print(f"telegram_test_{target}_message_id={message_id}")
            _archive_delivery(
                settings,
                {
                    "created_at": _now(),
                    "target": target,
                    "status": status,
                    "message_class": "manual_test",
                    "message_id": message_id,
                    "send_allowed_by_script": True,
                    "global_send_gate": "enabled" if settings.telegram_enabled else "disabled",
                    "boundary": "Manual Telegram test only. No trading authority.",
                },
            )
            if not ok:
                failures += 1
        except Exception as exc:  # noqa: BLE001 - keep diagnostics concise for operator.
            failures += 1
            print(f"telegram_test_{target}_status=failed")
            print(f"telegram_test_{target}_error={type(exc).__name__}")
            _archive_delivery(
                settings,
                {
                    "created_at": _now(),
                    "target": target,
                    "status": "failed",
                    "message_class": "manual_test",
                    "message_id": None,
                    "send_allowed_by_script": True,
                    "global_send_gate": "enabled" if settings.telegram_enabled else "disabled",
                    "error_type": type(exc).__name__,
                    "boundary": "Manual Telegram test only. No trading authority.",
                },
            )

    if failures:
        print("telegram_test_status=failed")
        return 1
    print("telegram_test_status=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
