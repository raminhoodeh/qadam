#!/usr/bin/env python3
"""Validate and write Qadam Phase 13 Telegram VNext artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_telegram_vnext import (
    CANDIDATES_ARTIFACT,
    COMMUNICATIONS_MIRROR_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    DEDUPE_LEDGER_ARTIFACT,
    DELIVERY_RECEIPTS_ARTIFACT,
    EVENTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    QUALITY_ARTIFACT,
    _runtime_dir,
    build_and_write_telegram_vnext,
    load_telegram_vnext,
    validate_negative_telegram_vnext_probes,
    validate_telegram_vnext_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written, errors = build_and_write_telegram_vnext(settings)
    runtime = _runtime_dir(settings)
    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        CANDIDATES_ARTIFACT,
        QUALITY_ARTIFACT,
        COMMUNICATIONS_MIRROR_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        DEDUPE_LEDGER_ARTIFACT,
        DELIVERY_RECEIPTS_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")
    loaded = load_telegram_vnext(settings)
    validation_errors.extend(validate_telegram_vnext_bundle(loaded))
    validation_errors.extend(validate_negative_telegram_vnext_probes())

    primary = bundle.primary
    mirror = bundle.communications_mirror
    print(f"primary={written.get('primary')}")
    print(f"candidates={written.get('candidates')}")
    print(f"quality={written.get('quality')}")
    print(f"dedupe_ledger={written.get('dedupe_ledger')}")
    print(f"delivery_receipts={written.get('delivery_receipts')}")
    print(f"communications_mirror={written.get('communications_mirror')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"status={primary.get('status')}")
    print(f"message_candidate_count={primary.get('message_candidate_count')}")
    print(f"message_ready_count={primary.get('message_ready_count')}")
    print(f"message_rejected_duplicate_count={primary.get('message_rejected_duplicate_count')}")
    print(f"message_rejected_quality_count={primary.get('message_rejected_quality_count')}")
    print(f"message_rejected_unsafe_count={primary.get('message_rejected_unsafe_count')}")
    print(f"quality_pass_count={primary.get('quality_pass_count')}")
    print(f"latest_message_preview={bundle.dashboard_summary.get('latest_message_preview')}")
    print(f"telegram_live_send_allowed={primary.get('telegram_live_send_allowed')}")
    print(f"telegram_command_path_enabled={primary.get('telegram_command_path_enabled')}")
    print(f"trade_candidate_created={primary.get('trade_candidate_created')}")
    print(f"risk_approval_created={primary.get('risk_approval_created')}")
    print(f"execution_approval_created={primary.get('execution_approval_created')}")
    print(f"paper_order_created_count={primary.get('paper_order_created_count')}")
    print(f"broker_write_count={primary.get('broker_write_count')}")
    print(f"proof_credit_allowed={primary.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={primary.get('live_capital_enabled')}")
    print(f"mirror_status={mirror.get('status')}")
    print(f"mirror_latest_message_count={len(mirror.get('latest_messages', []))}")
    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qadam_telegram_vnext_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
