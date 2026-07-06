#!/usr/bin/env python3
"""Validate and write QSASE Phase 14 Telegram summary V2 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase11_to14_completion import (
    TELEGRAM_CANDIDATES_V2_ARTIFACT,
    TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT,
    TELEGRAM_DEDUPE_V2_ARTIFACT,
    TELEGRAM_RECEIPTS_V2_ARTIFACT,
    TELEGRAM_SUMMARY_V2_ARTIFACT,
    _runtime_dir,
    build_and_write_phase11_to14_completion,
    validate_payload,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    settings = Settings.from_env()
    summary, written, errors = build_and_write_phase11_to14_completion(settings)
    runtime = _runtime_dir(settings)
    payload = _load_json(runtime / TELEGRAM_SUMMARY_V2_ARTIFACT)
    candidates = _load_json(runtime / TELEGRAM_CANDIDATES_V2_ARTIFACT)
    receipts = _read_jsonl(runtime / TELEGRAM_RECEIPTS_V2_ARTIFACT)
    dedupe = _read_jsonl(runtime / TELEGRAM_DEDUPE_V2_ARTIFACT)
    mirror = _load_json(runtime / TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT)
    validation_errors = list(errors)

    for filename in (
        TELEGRAM_SUMMARY_V2_ARTIFACT,
        TELEGRAM_CANDIDATES_V2_ARTIFACT,
        TELEGRAM_RECEIPTS_V2_ARTIFACT,
        TELEGRAM_DEDUPE_V2_ARTIFACT,
        TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_payload(payload, "qsase_telegram_summary_v2"))
    candidate_rows = candidates.get("candidates", [])
    if len(candidate_rows) != payload.get("message_candidate_count"):
        validation_errors.append("telegram_candidate_count_mismatch")
    if len(receipts) != payload.get("delivery_receipt_count"):
        validation_errors.append("telegram_receipt_count_mismatch")
    if len(dedupe) < payload.get("dedupe_record_count", 0):
        validation_errors.append("telegram_dedupe_record_count_too_low")
    if mirror.get("telegram_live_send_allowed") is not False:
        validation_errors.append("telegram_mirror_live_send_allowed")
    if any(candidate.get("telegram_command_path_enabled") is True for candidate in candidate_rows):
        validation_errors.append("telegram_candidate_command_path_enabled")
    if any(candidate.get("quality", {}).get("passed") is not True for candidate in candidate_rows):
        validation_errors.append("telegram_candidate_quality_not_passed")

    print(f"artifact={written.get(TELEGRAM_SUMMARY_V2_ARTIFACT)}")
    print(f"candidates={written.get(TELEGRAM_CANDIDATES_V2_ARTIFACT)}")
    print(f"dedupe={written.get(TELEGRAM_DEDUPE_V2_ARTIFACT)}")
    print(f"receipts={written.get(TELEGRAM_RECEIPTS_V2_ARTIFACT)}")
    print(f"communications_mirror={written.get(TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT)}")
    print(f"status={payload.get('status')}")
    print(f"message_candidate_count={payload.get('message_candidate_count')}")
    print(f"message_ready_count={payload.get('message_ready_count')}")
    print(f"message_rejected_duplicate_count={payload.get('message_rejected_duplicate_count')}")
    print(f"message_rejected_quality_count={payload.get('message_rejected_quality_count')}")
    print(f"telegram_live_send_allowed={payload.get('telegram_live_send_allowed')}")
    print(f"telegram_command_path_enabled={payload.get('telegram_command_path_enabled')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if summary.get("telegram", {}).get("message_candidate_count") != payload.get("message_candidate_count"):
        print("error=summary_telegram_candidate_count_mismatch")
        return 1
    print("qsase_telegram_summary_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
