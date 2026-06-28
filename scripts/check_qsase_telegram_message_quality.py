#!/usr/bin/env python3
"""Run QSASE-14 Telegram message quality checks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_telegram_notification_boundary import (
    build_qsase_telegram_notification_boundary,
    score_qsase_telegram_message,
    validate_qsase_telegram_message_candidate,
)


def main() -> int:
    payload = build_qsase_telegram_notification_boundary(Settings.from_env())
    errors: list[str] = []
    candidates = payload.get("message_candidates", [])
    for candidate in candidates:
        errors.extend(validate_qsase_telegram_message_candidate(candidate))
        if candidate.get("quality", {}).get("specificity_status") != "specific":
            errors.append(f"{candidate.get('message_candidate_id')}_not_specific")
        if candidate.get("quality", {}).get("human_style_status") != "human":
            errors.append(f"{candidate.get('message_candidate_id')}_not_human_style")
        if candidate.get("quality", {}).get("character_count", 999) > 360:
            errors.append(f"{candidate.get('message_candidate_id')}_too_long")

    generic_probe = dict(candidates[0]) if candidates else {}
    generic_probe["body"] = "Qadam Codebase Upgrade\nWhat changed:\nWhy it matters:\nWhat to check:"
    generic_quality = score_qsase_telegram_message(generic_probe)
    command_probe = dict(candidates[0]) if candidates else {}
    command_probe["body"] = "/buy SMH\nState: command\nReason: operator asked\nNext: submit\nOrder: buy SMH"
    command_quality = score_qsase_telegram_message(command_probe)
    if not generic_quality.get("generic_rejected"):
        errors.append("generic_probe_not_rejected")
    if not command_quality.get("unsafe_rejected"):
        errors.append("command_probe_not_rejected")

    print(f"candidate_count={len(candidates)}")
    print(f"specific_count={sum(1 for candidate in candidates if candidate.get('quality', {}).get('specificity_status') == 'specific')}")
    print(f"human_style_count={sum(1 for candidate in candidates if candidate.get('quality', {}).get('human_style_status') == 'human')}")
    print(f"generic_probe_rejected={generic_quality.get('generic_rejected')}")
    print(f"command_probe_rejected={command_quality.get('unsafe_rejected')}")
    print(f"message_sent_count={payload.get('message_sent_count')}")
    print(f"telegram_live_send_allowed={payload.get('telegram_live_send_allowed')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qsase_telegram_message_quality_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
