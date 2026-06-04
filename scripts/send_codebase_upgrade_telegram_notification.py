#!/usr/bin/env python3
"""Send a Telegram group update for a Qadam codebase upgrade."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.telegram_codebase_upgrade_notifications import (  # noqa: E402
    build_telegram_codebase_upgrade_notification,
    telegram_codebase_upgrade_paths,
    validate_telegram_codebase_upgrade_notification,
    write_telegram_codebase_upgrade_notification,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Telegram sendMessage when codebase-upgrade notification live gates are enabled.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass delivery-key idempotency for a manual resend.",
    )
    parser.add_argument(
        "--summary",
        default="Qadam codebase and dashboard were upgraded.",
        help="Public-safe one-line summary of what changed.",
    )
    parser.add_argument(
        "--source",
        default="manual",
        help="Public-safe source label such as production_deploy or manual.",
    )
    parser.add_argument(
        "--deployment-url",
        default=None,
        help="Public Vercel deployment URL to mention. Query strings are stripped.",
    )
    parser.add_argument(
        "--alias",
        action="append",
        default=[],
        help="Production alias that was updated. May be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    output_path, history_path, event_path = telegram_codebase_upgrade_paths(settings)
    if event_path.exists():
        event_path.unlink()
    artifact = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=args.live,
        force_send=args.force,
        summary=args.summary,
        source=args.source,
        deployment_url=args.deployment_url,
        aliases=args.alias,
    )
    output_path, history_path, event_path, written = write_telegram_codebase_upgrade_notification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_telegram_codebase_upgrade_notification(written)

    print(f"telegram_codebase_upgrade_status={written['status']}")
    print(f"telegram_codebase_upgrade_artifact_path={output_path}")
    print(f"telegram_codebase_upgrade_history_path={history_path}")
    print(f"telegram_codebase_upgrade_event_log_path={event_path}")
    print(f"telegram_codebase_upgrade_source={written['source']}")
    print(f"telegram_codebase_upgrade_root_commit_short={written['root_commit_short']}")
    print(
        "telegram_codebase_upgrade_dashboard_commit_short="
        f"{written['dashboard_commit_short']}"
    )
    print(f"telegram_codebase_upgrade_deployment_url={written['deployment_url'] or ''}")
    print(
        "telegram_codebase_upgrade_enabled="
        f"{written['codebase_upgrade_notifications_enabled']}"
    )
    print(
        "telegram_codebase_upgrade_dry_run="
        f"{written['codebase_upgrade_notifications_dry_run']}"
    )
    print(f"telegram_codebase_upgrade_bot_configured={written['bot_configured']}")
    print(
        "telegram_codebase_upgrade_group_chat_configured="
        f"{written['group_chat_configured']}"
    )
    print(f"telegram_codebase_upgrade_send_requested={written['send_requested']}")
    print(f"telegram_codebase_upgrade_force_send={written['force_send']}")
    print(f"telegram_codebase_upgrade_already_sent={written['already_sent']}")
    print(f"telegram_codebase_upgrade_live_send_attempted={written['live_send_attempted']}")
    print(f"telegram_codebase_upgrade_live_send_succeeded={written['live_send_succeeded']}")
    print(
        "telegram_codebase_upgrade_telegram_message_id_present="
        f"{written['telegram_message_id_present']}"
    )
    print(
        "telegram_codebase_upgrade_delivery_failure_category="
        f"{written['delivery_failure_category']}"
    )
    print(f"telegram_codebase_upgrade_blockers={written['blockers']}")
    print(f"telegram_codebase_upgrade_validation_errors={validation_errors}")

    if validation_errors:
        print("telegram_codebase_upgrade_check=failed")
        return 1
    if written["status"] == "failed":
        print("telegram_codebase_upgrade_check=failed")
        return 1
    print("telegram_codebase_upgrade_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
