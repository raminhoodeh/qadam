#!/usr/bin/env python3
"""Validate D8 Fund Manager forum governance comments."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.governance import (  # noqa: E402
    EVENT_LOG_EXPORT_STATUSES,
    VALID_COMMENT_STATUSES,
    VALID_TARGET_TYPES,
    GovernanceStore,
    ensure_d8_sample_governance_comment,
)

REQUIRED_TARGET_TYPES = {"module", "source", "signal", "trade_candidate", "postmortem"}
REQUIRED_STATUSES = {"suggestion", "accepted", "rejected", "implemented"}


def validate_event_export(settings: Settings) -> bool:
    temp_runtime = Path("/private/tmp/qadam-d8-forum-check")
    previous_runtime = os.environ.get("QADAM_RUNTIME_DIR")
    os.environ["QADAM_RUNTIME_DIR"] = str(temp_runtime)
    try:
        temp_settings = Settings.from_env()
        store = GovernanceStore(settings=temp_settings)
        comment = store.add_comment(
            author_email=temp_settings.fund_manager_allowlist[0],
            author_name="D8 Check",
            target_type="trade_candidate",
            target_key="d8-export-check",
            body="D8 check: accepted forum comments export to the local Event Log.",
            tags=("d8", "event_log"),
            status="accepted",
            log_event=True,
        )
        events = EventLog(echo=False).read_entries()
        return any(
            event.event_type == "governance_comment_approved"
            and event.component == "governance_forum"
            and event.payload.get("comment_id") == comment.comment_id
            and event.payload.get("status") == "accepted"
            for event in events
        )
    finally:
        if previous_runtime is None:
            os.environ.pop("QADAM_RUNTIME_DIR", None)
        else:
            os.environ["QADAM_RUNTIME_DIR"] = previous_runtime


def main() -> int:
    settings = Settings.from_env()
    seed_result = ensure_d8_sample_governance_comment(settings)
    store = GovernanceStore(settings=settings)
    comments = store.read_comments()
    health = store.health()

    print("governance_forum_status=" + health["status"])
    print(f"governance_forum_sample_created={seed_result['created']}")
    print(f"governance_forum_comment_count={health.get('comment_count')}")
    print(f"governance_forum_suggestion_count={health.get('suggestion_count')}")
    print(f"governance_forum_accepted_count={health.get('accepted_count')}")
    print(f"governance_forum_event_log_export_count={health.get('event_log_export_count')}")
    print("governance_forum_allowed_targets=" + ",".join(health.get("allowed_target_types", [])))
    print("governance_forum_allowed_statuses=" + ",".join(health.get("allowed_statuses", [])))

    if health["status"] != "ok":
        print("governance_forum_not_ok=true")
        return 1
    if not comments:
        print("governance_forum_comments_missing=true")
        return 1
    if not REQUIRED_TARGET_TYPES.issubset(VALID_TARGET_TYPES):
        print("governance_forum_target_types_missing=true")
        return 1
    if not REQUIRED_STATUSES.issubset(VALID_COMMENT_STATUSES):
        print("governance_forum_statuses_missing=true")
        return 1
    if EVENT_LOG_EXPORT_STATUSES != {"accepted", "implemented"}:
        print("governance_forum_event_export_statuses_wrong=true")
        return 1
    if health.get("visibility") != "founding_fund_managers":
        print("governance_forum_visibility_wrong=true")
        return 1
    if not any(
        comment.target_type == "module"
        and comment.target_key == "trade_layer"
        and comment.status in {"suggestion", "open"}
        and "D8 sample" in comment.body
        for comment in comments
    ):
        print("governance_forum_d8_sample_missing=true")
        return 1
    if not validate_event_export(settings):
        print("governance_forum_event_log_export_missing=true")
        return 1

    print("governance_forum_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
