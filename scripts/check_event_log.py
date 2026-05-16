#!/usr/bin/env python3
"""Exercise the local Event Log fallback and replay contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.event_log import EVENT_LOG_SCHEMA_VERSION, EventLog


def main() -> int:
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    event_log_path = runtime_dir / "foundation_check_event_log.jsonl"
    if event_log_path.exists():
        event_log_path.unlink()

    event_log = EventLog(event_log_path, echo=False)
    first = event_log.write(
        "foundation_event_log_check_started",
        "foundation_check",
        {"mode": settings.mode, "trial_balance_gbp": settings.trial_balance_gbp},
    )
    second = event_log.write(
        "foundation_event_log_check_completed",
        "foundation_check",
        {"previous_correlation_id": first.correlation_id},
        correlation_id=first.correlation_id,
    )
    replay = event_log.replay()
    health = event_log.health()

    print(f"event_log_schema_version={EVENT_LOG_SCHEMA_VERSION}")
    print(f"event_log_path={event_log_path}")
    print(f"event_log_total_events={replay['total_events']}")
    print(f"event_log_last_type={second.event_type}")
    print(f"event_log_health={health['status']}")

    if replay["total_events"] != 2:
        print("event_log_replay_count_mismatch=true")
        return 1
    if replay["by_component"].get("foundation_check") != 2:
        print("event_log_component_replay_mismatch=true")
        return 1
    if health["status"] != "ok":
        print("event_log_health_not_ok=true")
        return 1

    print("event_log_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
