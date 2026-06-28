#!/usr/bin/env python3
"""Validate and write QSASE-14 Telegram Summary Boundary artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_telegram_notification_boundary import (
    DASHBOARD_COMMUNICATIONS_ARTIFACT,
    DEDUPE_LEDGER_ARTIFACT,
    DELIVERY_RECEIPTS_ARTIFACT,
    EVENTS_ARTIFACT,
    INBOUND_READONLY_ARTIFACT,
    MESSAGE_CANDIDATES_ARTIFACT,
    MESSAGE_QUALITY_ARTIFACT,
    MESSAGE_QUEUE_ARTIFACT,
    NOTIFICATION_HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_qsase_telegram_notification_boundary,
    load_qsase_telegram_notification_boundary,
    validate_negative_qsase_telegram_notification_boundary_probes,
    validate_qsase_telegram_notification_boundary,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_qsase_telegram_notification_boundary(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        MESSAGE_CANDIDATES_ARTIFACT,
        MESSAGE_QUEUE_ARTIFACT,
        MESSAGE_QUALITY_ARTIFACT,
        DEDUPE_LEDGER_ARTIFACT,
        DELIVERY_RECEIPTS_ARTIFACT,
        INBOUND_READONLY_ARTIFACT,
        NOTIFICATION_HISTORY_ARTIFACT,
        DASHBOARD_COMMUNICATIONS_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    loaded = load_qsase_telegram_notification_boundary(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    validation_errors.extend(validate_qsase_telegram_notification_boundary(loaded))
    validation_errors.extend(validate_negative_qsase_telegram_notification_boundary_probes())

    print(f"artifact={written.get('notification_boundary')}")
    print(f"message_candidates={written.get('message_candidates')}")
    print(f"message_queue={written.get('message_queue')}")
    print(f"message_quality={written.get('message_quality')}")
    print(f"dedupe_ledger={written.get('dedupe_ledger')}")
    print(f"delivery_receipts={written.get('delivery_receipts')}")
    print(f"inbound_readonly={written.get('inbound_readonly')}")
    print(f"dashboard_communications={written.get('dashboard_communications')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"message_candidate_count={payload.get('message_candidate_count')}")
    print(f"message_ready_count={payload.get('message_ready_count')}")
    print(f"message_sent_count={payload.get('message_sent_count')}")
    print(f"message_rejected_generic_count={payload.get('message_rejected_generic_count')}")
    print(f"message_rejected_duplicate_count={payload.get('message_rejected_duplicate_count')}")
    print(f"message_rejected_unsafe_count={payload.get('message_rejected_unsafe_count')}")
    print(f"delivery_failure_count={payload.get('delivery_failure_count')}")
    print(f"duplicate_suppressed_count={payload.get('duplicate_suppressed_count')}")
    print(f"inbound_record_count={payload.get('inbound_record_count')}")
    print(f"inbound_command_detected_count={payload.get('inbound_command_detected_count')}")
    print(f"inbound_command_ignored_count={payload.get('inbound_command_ignored_count')}")
    print(f"telegram_live_send_allowed={payload.get('telegram_live_send_allowed')}")
    print(f"telegram_command_path_enabled={payload.get('telegram_command_path_enabled')}")
    print(f"telegram_trade_command_enabled={payload.get('telegram_trade_command_enabled')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_telegram_notification_boundary_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
