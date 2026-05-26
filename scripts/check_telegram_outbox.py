#!/usr/bin/env python3
"""Validate D8A Telegram dry-run outbox and message templates."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_telegram_notifier import (  # noqa: E402
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    validate_phase5_telegram_notifier_bundle,
)
from orchestrator.telegram_comms import (  # noqa: E402
    TelegramCommunicationsStore,
    ensure_d8a_telegram_dry_run,
)

REQUIRED_SAMPLE_IDS = {
    "d8a-sample-trade-candidate",
    "d8a-sample-blocked-trade",
    "d8a-sample-insight-digest",
    "d8a-sample-system-warning",
}

REQUIRED_MESSAGE_CLASSES = {
    "trade_candidate",
    "blocked_trade",
    "insight_digest",
    "source_degraded",
}

FORBIDDEN_MESSAGE_PATTERNS = (
    re.compile(r"\babout to trade\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\b", re.IGNORECASE),
    re.compile(r"\bsure thing\b", re.IGNORECASE),
    re.compile(r"\brisk[- ]?free\b", re.IGNORECASE),
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
)


def _load_q5_telegram_notifier(settings: Settings) -> dict | None:
    path = Path(settings.runtime_dir) / TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    result = ensure_d8a_telegram_dry_run(settings)
    store = TelegramCommunicationsStore(settings=settings)
    outbox = store.read_outbox()
    status = store.public_status()
    by_id = {message.message_id: message for message in outbox}
    message_classes = {message.message_class for message in outbox}

    print("telegram_outbox_status=" + status["status"])
    print(f"telegram_outbox_created_count={result['created_count']}")
    print(f"telegram_outbox_message_count={len(outbox)}")
    print(f"telegram_outbox_pending_queue_count={status['pending_queue_count']}")
    print(f"telegram_outbox_dry_run_message_count={status['dry_run_message_count']}")
    print("telegram_outbox_classes=" + ",".join(sorted(message_classes)))

    if status["status"] != "dry_run":
        print("telegram_outbox_status_not_dry_run=true")
        return 1
    if not REQUIRED_SAMPLE_IDS.issubset(by_id):
        print("telegram_outbox_required_samples_missing=true")
        return 1
    if not REQUIRED_MESSAGE_CLASSES.issubset(message_classes):
        print("telegram_outbox_required_classes_missing=true")
        return 1
    if status["dry_run_message_count"] < len(REQUIRED_SAMPLE_IDS):
        print("telegram_outbox_dry_run_samples_missing=true")
        return 1
    if status["pending_queue_count"] < len(REQUIRED_SAMPLE_IDS):
        print("telegram_outbox_pending_samples_missing=true")
        return 1

    for message_id in REQUIRED_SAMPLE_IDS:
        message = by_id[message_id]
        if message.mode != "dry_run":
            print(f"telegram_outbox_message_not_dry_run={message_id}")
            return 1
        if message.status != "queued":
            print(f"telegram_outbox_message_not_queued={message_id}")
            return 1
        if message.send_allowed:
            print(f"telegram_outbox_message_send_allowed={message_id}")
            return 1
        if "Dashboard: qadam.trade/dashboard/" not in message.body:
            print(f"telegram_outbox_dashboard_link_missing={message_id}")
            return 1
        if "No Telegram input" in message.body:
            print(f"telegram_outbox_ui_copy_leaked={message_id}")
            return 1
        for pattern in FORBIDDEN_MESSAGE_PATTERNS:
            if pattern.search(message.title) or pattern.search(message.body):
                print(f"telegram_outbox_forbidden_text={message_id}")
                return 1
        if message.message_class == "trade_candidate":
            if "candidate, not an order" not in message.body:
                print("telegram_outbox_candidate_boundary_missing=true")
                return 1
            if "Qadam: considered trade candidate" not in message.body:
                print("telegram_outbox_candidate_state_wrong=true")
                return 1
        if message.message_class == "blocked_trade":
            if "Status: blocked" not in message.body:
                print("telegram_outbox_blocked_state_missing=true")
                return 1
            if "No paper order and no broker action" not in message.body:
                print("telegram_outbox_blocked_boundary_missing=true")
                return 1
        if message.message_class == "insight_digest" and "not a trade signal" not in message.body:
            print("telegram_outbox_digest_boundary_missing=true")
            return 1
        if message.message_class == "source_degraded" and "No trade command is available" not in message.body:
            print("telegram_outbox_system_warning_boundary_missing=true")
            return 1

    q5_notifier = _load_q5_telegram_notifier(settings)
    if q5_notifier is not None:
        q5_errors = validate_phase5_telegram_notifier_bundle(q5_notifier)
        q5_records = [
            record
            for record in q5_notifier.get("records", [])
            if isinstance(record, dict) and record.get("outbox_message_written") is True
        ]
        print("telegram_outbox_q5_10_status=" + str(q5_notifier.get("status")))
        print(f"telegram_outbox_q5_10_written_count={len(q5_records)}")
        print(f"telegram_outbox_q5_10_validation_error_count={len(q5_errors)}")
        if q5_errors:
            print("telegram_outbox_q5_10_validation_errors_present=true")
            return 1
        for record in q5_records:
            message_id = str(record.get("outbox_message_id") or "")
            message = by_id.get(message_id)
            if message is None:
                print(f"telegram_outbox_q5_10_message_missing={message_id}")
                return 1
            if message.mode != "dry_run":
                print(f"telegram_outbox_q5_10_message_not_dry_run={message_id}")
                return 1
            if message.status != "queued":
                print(f"telegram_outbox_q5_10_message_not_queued={message_id}")
                return 1
            if message.send_allowed:
                print(f"telegram_outbox_q5_10_message_send_allowed={message_id}")
                return 1
            if "Dashboard: qadam.trade/dashboard/" not in message.body:
                print(f"telegram_outbox_q5_10_dashboard_link_missing={message_id}")
                return 1
            if "No Telegram input" in message.body:
                print(f"telegram_outbox_q5_10_ui_copy_leaked={message_id}")
                return 1
            for pattern in FORBIDDEN_MESSAGE_PATTERNS:
                if pattern.search(message.title) or pattern.search(message.body):
                    print(f"telegram_outbox_q5_10_forbidden_text={message_id}")
                    return 1
        if q5_notifier.get("outbox_message_written_count") != len(q5_records):
            print("telegram_outbox_q5_10_written_count_mismatch=true")
            return 1

    print("telegram_outbox_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
