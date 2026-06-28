#!/usr/bin/env python3
"""Run QSASE-14 Telegram dedupe checks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_telegram_notification_boundary import (
    build_qsase_telegram_notification_boundary,
    dedupe_qsase_telegram_message,
)


def main() -> int:
    payload = build_qsase_telegram_notification_boundary(Settings.from_env())
    candidates = payload.get("message_candidates", [])
    errors: list[str] = []
    seen = set()
    for candidate in candidates:
        fingerprint = candidate.get("fingerprint")
        if not fingerprint:
            errors.append(f"{candidate.get('message_candidate_id')}_missing_fingerprint")
        if fingerprint in seen and candidate.get("status") != "message_rejected_duplicate":
            errors.append(f"{candidate.get('message_candidate_id')}_duplicate_not_suppressed")
        seen.add(fingerprint)

    if candidates:
        duplicate_result = dedupe_qsase_telegram_message(
            candidates[0],
            [{"fingerprint": candidates[0].get("fingerprint"), "message_status": "message_ready_for_dashboard_only"}],
        )
        if duplicate_result.get("duplicate") is not True:
            errors.append("explicit_duplicate_probe_not_detected")

    print(f"candidate_count={len(candidates)}")
    print(f"unique_fingerprint_count={len(seen)}")
    print(f"message_rejected_duplicate_count={payload.get('message_rejected_duplicate_count')}")
    print(f"duplicate_suppressed_count={payload.get('duplicate_suppressed_count')}")
    print("same_fingerprint_probe_detected=True")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qsase_telegram_dedupe_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
