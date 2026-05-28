#!/usr/bin/env python3
"""Validate inbound Telegram member research intake."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.strategy_research_intake import (  # noqa: E402
    build_strategy_research_intake,
    validate_strategy_research_intake,
    write_strategy_research_intake,
)
from orchestrator.telegram_inbound_intake import (  # noqa: E402
    TELEGRAM_INBOUND_BOUNDARY,
    TelegramInboundIntakeStore,
    ensure_sample_telegram_inbound_intake,
    poll_telegram_inbound_updates,
    telegram_inbound_intake_public_status,
    validate_telegram_inbound_record,
)

FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
    re.compile(r"chat_id|username|first_name|last_name", re.IGNORECASE),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--poll-live",
        action="store_true",
        help="Call Telegram getUpdates with the configured bot token and ingest returned messages.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    sample_result = ensure_sample_telegram_inbound_intake(settings)
    live_poll_result = poll_telegram_inbound_updates(settings=settings) if args.poll_live else {
        "status": "not_requested",
        "created_count": 0,
    }
    store = TelegramInboundIntakeStore(settings=settings)
    records = store.read_records()
    strategy_rows = store.read_strategy_considerations()
    world_rows = store.read_world_events()
    public_status = telegram_inbound_intake_public_status(settings)
    public_encoded = json.dumps(public_status, sort_keys=True)

    strategy_artifact = build_strategy_research_intake(settings)
    _, _, _, written_strategy = write_strategy_research_intake(
        strategy_artifact,
        settings,
        record_event=True,
    )
    strategy_errors = validate_strategy_research_intake(written_strategy)

    record_errors = [
        error
        for record in records
        for error in validate_telegram_inbound_record(record)
    ]

    print(f"telegram_inbound_intake_status={public_status['status']}")
    print(f"telegram_inbound_intake_enabled={public_status['enabled']}")
    print(f"telegram_inbound_intake_bot_configured={public_status['bot_configured']}")
    print(f"telegram_inbound_intake_sample_created_count={sample_result['created_count']}")
    print(f"telegram_inbound_intake_sample_duplicate_count={sample_result['duplicate_count']}")
    print(f"telegram_inbound_intake_live_poll_status={live_poll_result['status']}")
    print(f"telegram_inbound_intake_live_poll_created_count={live_poll_result.get('created_count', 0)}")
    print(f"telegram_inbound_intake_record_count={len(records)}")
    print(f"telegram_inbound_world_event_datapoint_count={len(world_rows)}")
    print(f"telegram_inbound_strategy_consideration_count={len(strategy_rows)}")
    print(f"telegram_inbound_research_triage_packet_count={public_status['research_triage_packet_count']}")
    print(
        "telegram_inbound_strategy_research_consideration_count="
        f"{written_strategy['user_strategy_consideration_count']}"
    )
    print(f"telegram_inbound_record_validation_error_count={len(record_errors)}")
    print(f"telegram_inbound_strategy_validation_error_count={len(strategy_errors)}")

    if sample_result["status"] != "ok":
        errors.append("sample_intake_not_ok")
    if len(records) < 2:
        errors.append("telegram_inbound_records_missing")
    if len(world_rows) < 1:
        errors.append("telegram_world_event_datapoint_missing")
    if len(strategy_rows) < 1:
        errors.append("telegram_strategy_consideration_missing")
    if public_status["research_triage_packet_count"] < 1:
        errors.append("telegram_world_event_not_queued_for_research")
    if written_strategy["user_strategy_consideration_count"] < 1:
        errors.append("strategy_research_did_not_ingest_telegram_consideration")
    if record_errors:
        errors.extend(record_errors)
    if strategy_errors:
        errors.extend(strategy_errors)
    for field in (
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_command_authority",
        "live_capital_enabled",
    ):
        if public_status.get(field) is not False:
            errors.append(f"telegram_inbound_public_authority_enabled:{field}")
    for pattern in FORBIDDEN_PUBLIC_PATTERNS:
        if pattern.search(public_encoded):
            errors.append("telegram_inbound_public_secret_or_identifier_leak")
            break
    if "read-only member research intake" not in public_status.get("boundary", ""):
        errors.append("telegram_inbound_public_boundary_weak")
    if TELEGRAM_INBOUND_BOUNDARY not in public_status.get("boundary", ""):
        errors.append("telegram_inbound_boundary_mismatch")

    if errors:
        for error in errors:
            print(f"telegram_inbound_intake_error={error}")
        print("telegram_inbound_intake_check=failed")
        return 1

    print("telegram_inbound_intake_check=ok")
    print("telegram_inbound_intake_boundary=read-only member research intake; no trade authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
