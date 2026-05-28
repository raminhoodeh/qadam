#!/usr/bin/env python3
"""Send the once-daily Telegram paper portfolio digest when it is due."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.telegram_daily_portfolio_digest import (  # noqa: E402
    build_daily_portfolio_digest,
    telegram_daily_portfolio_digest_paths,
    validate_daily_portfolio_digest,
    write_daily_portfolio_digest,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Telegram sendMessage if the daily digest is due and live-send gates are enabled.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the local end-of-day time check. Idempotency still prevents duplicate live sends.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    output_path, history_path, event_path = telegram_daily_portfolio_digest_paths(settings)
    if event_path.exists():
        event_path.unlink()
    artifact = build_daily_portfolio_digest(
        settings=settings,
        send_requested=args.live,
        force=args.force,
    )
    output_path, history_path, event_path, written = write_daily_portfolio_digest(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_daily_portfolio_digest(written)

    print(f"telegram_daily_portfolio_digest_status={written['status']}")
    print(f"telegram_daily_portfolio_digest_artifact_path={output_path}")
    print(f"telegram_daily_portfolio_digest_history_path={history_path}")
    print(f"telegram_daily_portfolio_digest_event_log_path={event_path}")
    print(f"telegram_daily_portfolio_digest_local_date={written['local_date']}")
    print(f"telegram_daily_portfolio_digest_timezone={written['timezone']}")
    print(
        "telegram_daily_portfolio_digest_delivery_after_local_time="
        f"{written['delivery_after_local_time']}"
    )
    print(f"telegram_daily_portfolio_digest_due_for_delivery={written['due_for_delivery']}")
    print(f"telegram_daily_portfolio_digest_force_delivery_window={written['force_delivery_window']}")
    print(f"telegram_daily_portfolio_digest_enabled={written['daily_portfolio_digest_enabled']}")
    print(f"telegram_daily_portfolio_digest_dry_run={written['daily_portfolio_digest_dry_run']}")
    print(f"telegram_daily_portfolio_digest_bot_configured={written['bot_configured']}")
    print(
        "telegram_daily_portfolio_digest_group_chat_configured="
        f"{written['group_chat_configured']}"
    )
    print(f"telegram_daily_portfolio_digest_send_requested={written['send_requested']}")
    print(f"telegram_daily_portfolio_digest_already_sent={written['already_sent']}")
    print(
        "telegram_daily_portfolio_digest_portfolio_balance_gbp="
        f"{written['portfolio_balance_gbp']}"
    )
    print(
        "telegram_daily_portfolio_digest_portfolio_total_pnl_gbp="
        f"{written['portfolio_total_pnl_gbp']}"
    )
    print(
        "telegram_daily_portfolio_digest_portfolio_performance_pct="
        f"{written['portfolio_performance_pct']}"
    )
    print(f"telegram_daily_portfolio_digest_daily_trade_count={written['daily_trade_count']}")
    print(f"telegram_daily_portfolio_digest_live_send_attempted={written['live_send_attempted']}")
    print(f"telegram_daily_portfolio_digest_live_send_succeeded={written['live_send_succeeded']}")
    print(
        "telegram_daily_portfolio_digest_telegram_message_id_present="
        f"{written['telegram_message_id_present']}"
    )
    print(
        "telegram_daily_portfolio_digest_delivery_failure_category="
        f"{written['delivery_failure_category']}"
    )
    print(f"telegram_daily_portfolio_digest_validation_errors={validation_errors}")

    if validation_errors:
        print("telegram_daily_portfolio_digest_check=failed")
        return 1
    if written["status"] == "failed":
        print("telegram_daily_portfolio_digest_check=failed")
        return 1
    print("telegram_daily_portfolio_digest_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
